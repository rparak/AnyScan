## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# Author   : JIC Smart Factory
# File Name: ../test/UI/test_preview.py
## =========================================================================== ##

# System (Default)
import os
import glob
import threading
import time
# Typing (Support for type hints)
import typing as tp
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QTimer, qInstallMessageHandler
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window and the preview worker
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Workers
from UI.Workers import Preview_Worker_Cls
# Custom Lib.: AnyScan domain — the camera layer, the result, the theme, the configuration, the logger
#   ../Camera/Core
from Camera.Core import Camera_Backend_Cls, Camera_Error_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Parameters/Theme
import Parameters.Theme as Theme
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Mode_Directory
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls

"""
Description:
    The live preview in the window: the state machine of PREVIEW with CONNECT, DISCONNECT, SCAN, ANALYZE, CLEAR and
    CONFIGURATION; the preview's worker (frames dropped, never queued; the GUI thread never waits for the camera);
    the scan's stillness check as the operator meets it; and what the view shows — the table live, the inspection
    area on it and the LIVE marker, read from the grabbed pixels. The camera is a scripted stream backend (no
    hardware) whose frames carry, in their first pixel, the number of the stream that delivered them, so a test can
    tell a preview frame from a scan frame. Headless (offscreen); no model weights.
"""
CONST_MANGLE = '_AnyScan_Window_Cls'
# The catalogue mode file the window is built with, so the inspection area is in force.
CONST_CATALOGUE_MODE_FILE = 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml'
# The scripted frames: the station's size, the green of the table (RGB), and the patch a moving hand changes.
#   Unit [Tuple<int> 1x2] / [Tuple<int> 1x3] / [Tuple<int> 1x4]
CONST_FRAME = (1920, 1200)
CONST_TABLE = (23, 101, 80)
CONST_HAND = (300, 200, 1300, 900)
# How long a test waits for the window to reach a state before it fails.
#   Unit [s]
CONST_WAIT_S = 10.0
# The window's controls, as (label, private name).
CONST_BUTTONS = (('CONFIGURATION', '__button_configuration'), ('CONNECT', '__button_connect'),
                 ('DISCONNECT', '__button_disconnect'), ('PREVIEW', '__button_preview'), ('SCAN', '__button_scan'),
                 ('ANALYZE', '__button_analyze'), ('CLEAR', '__button_clear'))


# Every window a test built (_Window), closed at its teardown whatever the test did, so a failed test never leaves a
# preview's or a scan's thread running into the next.
CONST_WINDOWS = []


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def close_windows() -> tp.Iterator[None]:
    """Close every window the test built and wait until it has closed (its workers ended)."""
    yield
    while CONST_WINDOWS:
        window = CONST_WINDOWS.pop()
        window.close()
        _Pump(lambda: not window.isVisible())


class _Live_Camera_Cls(Camera_Backend_Cls):
    """
    A camera with a stream, thread-safe like pylon's: each frame takes `delay` seconds; `moving` makes every other
    frame show a hand; `failing` makes a grab fail and `removed` reports the device gone. `events` records
    ('start', n), ('stop', n) and ('close',) in order; the first pixel of each frame is its stream's number.
    """

    def __init__(self, delay: float = 0.02) -> None:
        super().__init__()
        self.delay, self.moving, self.failing, self.removed = delay, False, False, False
        self.lock = threading.Lock()
        self.events, self.stream, self.index, self.streaming = [], 0, 0, False

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        with self.lock:
            self.events.append(('close',))

    def _Device_Removed(self) -> bool:
        return self.removed

    def _Start_Stream(self) -> None:
        with self.lock:
            self.stream += 1
            self.index = 0
            self.streaming = True
            self.events.append(('start', self.stream))

    def _Stop_Stream(self) -> None:
        with self.lock:
            self.streaming = False
            self.events.append(('stop', self.stream))

    def _Grab_Stream(self) -> np.ndarray:
        time.sleep(self.delay)
        with self.lock:
            assert self.streaming, 'a frame was taken from a stream that was not running'
            if self.failing:
                raise Camera_Error_Cls('The camera did not return a frame in time.')
            frame = np.empty((CONST_FRAME[1], CONST_FRAME[0], 3), np.uint8)
            frame[:] = CONST_TABLE
            if self.moving and self.index % 2:
                x1, y1, x2, y2 = CONST_HAND
                frame[y1:y2, x1:x2] = (60, 45, 40)
            frame[0, 0, 0] = self.stream
            self.index += 1
            return frame

    def _Grab(self) -> np.ndarray:
        raise AssertionError('the window scans through Capture_Still, never a single grab')

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        return CONST_FRAME

    def Streams_Started(self) -> tp.List[int]:
        """The numbers of the streams started so far."""
        with self.lock:
            return [event[1] for event in self.events if event[0] == 'start']


class _Loaded_Vision_Cls(object):
    """A stand-in pipeline whose models are loaded; an analysis is recorded, so a test can see none ran."""
    Name, Models_Loaded, Model_Names = 'JIC-AnyScan-v1', True, ('FastSAM-x.pt', 'gemma')

    def __init__(self) -> None:
        self.analysed = []

    def Analyze(self, image: np.ndarray, **callbacks: tp.Any) -> Analysis_Str:
        self.analysed.append(image)
        return _Result(image.shape)


def _Result(shape: tp.Tuple[int, ...]) -> Analysis_Str:
    """One OK object, as an analysis of a frame of the given shape returns it."""
    mask = np.zeros(shape[:2], dtype=bool)
    mask[300:560, 400:760] = True
    return Analysis_Str(Objects=[Detection_Str(Label='plate', Bbox=(400, 300, 360, 260), Mask=mask, Cue='both',
                                               Verdict='OK', Segmenter_Score=0.9, Sentence='A plate.')],
                        Latency_Ms=100, Verdict='1 found', Verdict_Level='ok', Task='caption', Background='A table.')


def _Private(obj: tp.Any, name: str, mangle: str = CONST_MANGLE) -> tp.Any:
    return getattr(obj, mangle + name)


def _Pump(condition: tp.Callable[[], bool], timeout: float = CONST_WAIT_S) -> None:
    """Process Qt events until the condition holds; fail the test if it does not within the timeout."""
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail('The window did not reach the expected state within %g s.' % timeout)
        QApplication.processEvents()
        time.sleep(0.002)


def _Window(tmp_path: tp.Any, camera: _Live_Camera_Cls, connect: bool = True,
            loaded: bool = True) -> tp.Tuple[AnyScan_Window_Cls, Session_Logger_Cls, _Loaded_Vision_Cls]:
    """A catalogue-mode window on the scripted camera with a real logger in tmp_path, connected unless asked not to."""
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    config = Load_Configuration(os.path.join(Mode_Directory(), CONST_CATALOGUE_MODE_FILE))
    window = AnyScan_Window_Cls(Configuration_Str=config, camera=camera, logger=logger)
    vision = _Loaded_Vision_Cls()
    if loaded:
        setattr(window, CONST_MANGLE + '__vision', vision)
    window.resize(1600, 1000)
    window.show()
    CONST_WINDOWS.append(window)
    _Private(window, '__Sync_Controls')()
    if connect:
        _Private(window, '__button_connect').click()
        _Pump(lambda: camera.Connected and not _Private(window, '__worker_running'))
    return window, logger, vision


def _Preview(window: AnyScan_Window_Cls, frames: int = 1) -> None:
    """Press PREVIEW and wait until the worker has delivered the given number of frames and one is painted."""
    _Private(window, '__button_preview').click()
    _Pump(lambda: _Private(window, '__preview_worker') is not None
          and _Private(window, '__preview_worker').Delivered >= frames
          and getattr(_Private(window, '__viewport'), '_Viewport_Cls__live') is not None)


def _Idle(window: AnyScan_Window_Cls) -> None:
    """Wait until no worker runs and the preview, if any, is not stopping."""
    _Pump(lambda: not _Private(window, '__worker_running') and _Private(window, '__preview_pending') is None
          and (_Private(window, '__preview_thread') is None or _Private(window, '__preview_worker').Delivered > 0))


def _Enabled(window: AnyScan_Window_Cls) -> tp.Set[str]:
    """The labels of the enabled controls."""
    return {label for label, name in CONST_BUTTONS if _Private(window, name).isEnabled()}


def _Shown(window: AnyScan_Window_Cls) -> tp.Optional[QImage]:
    """The image the Camera View paints now (the live frame, the selected render or the frame), or None."""
    return getattr(_Private(window, '__viewport'), '_Viewport_Cls__Displayed')()


def _Shown_Stream(window: AnyScan_Window_Cls) -> tp.Optional[int]:
    """The number of the camera stream the shown image came from (its first pixel), or None when none is shown."""
    image = _Shown(window)
    return None if image is None else image.pixelColor(0, 0).red()


def _Analysed(window: AnyScan_Window_Cls) -> None:
    """Scan through the button and hand the window an analysis of the frame, as the worker does."""
    _Private(window, '__button_scan').click()
    _Idle(window)
    setattr(window, CONST_MANGLE + '__current_set_id', 'set_%d' % id(window))
    _Private(window, '__On_Analysis_Finished')(_Result(_Private(window, '__frame').shape))
    assert _Private(window, '__viewport').Has_Views() and not _Private(window, '__reading_lead').isHidden()


def _Assert_Result_Gone(window: AnyScan_Window_Cls) -> None:
    """Nothing of the previous scan or its analysis is held or shown: no frame, no render, no reading."""
    viewport = _Private(window, '__viewport')
    assert _Private(window, '__frame') is None and not viewport.Has_Frame() and not viewport.Has_Views()
    assert _Private(window, '__reading_lead').isHidden() and _Private(window, '__object_list').box.count() == 0
    assert _Private(window, '__reading_empty').text() == window.CONST_READING_SCANNING
    assert [badge.text() for badge in _Private(window, '__stage_badges').Badges()] == ['Scanning']


def _Log(logger: Session_Logger_Cls) -> str:
    with open(logger.Path, encoding='utf-8') as handle:
        return handle.read()


def _Grab(widget: tp.Any) -> np.ndarray:
    """What the widget paints now, as an HxWx3 BGR array (the pixels, not its state)."""
    QApplication.instance().processEvents()
    image = widget.grab().toImage().convertToFormat(QImage.Format_RGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :, :3].copy()


def _Is(pixels: np.ndarray, colour: str, tolerance: int = 45) -> np.ndarray:
    """Where the pixels are the colour (a theme token), within a small blend, as a bool HxW map."""
    r, g, b = Theme.Hex_To_Rgb(colour)
    return (np.abs(pixels.astype(int) - np.array([b, g, r])) <= tolerance).all(axis=2)


def _Area_On_Screen(window: AnyScan_Window_Cls) -> tp.Tuple[int, int, int, int]:
    """Where the inspection area lies in the viewport's pixels: its frame rectangle, letterboxed."""
    viewport = _Private(window, '__viewport')
    (width, height), (left, top, right, bottom) = getattr(viewport, '_Viewport_Cls__area')
    scale = min(viewport.width() / width, viewport.height() / height)
    x0, y0 = int((viewport.width() - width * scale) / 2), int((viewport.height() - height * scale) / 2)
    return tuple(int(round(v)) for v in (x0 + left * scale, y0 + top * scale, x0 + right * scale, y0 + bottom * scale))


def test_the_controls_in_every_state_of_the_preview(qt_app, tmp_path) -> None:
    """
    Description:
        The full table, each state read from the buttons themselves: PREVIEW is disabled without a connected camera
        (its tooltip says so); connected, it is available beside SCAN; while the preview runs, SCAN, PREVIEW,
        DISCONNECT and CLEAR are available and ANALYZE is not (it would analyse a frame other than the one in view);
        while the preview stops or a scan runs, nothing is; CONFIGURATION is fixed from the first CONNECT on.
    """

    window, _, _ = _Window(tmp_path / 'a', _Live_Camera_Cls(), connect=False, loaded=False)
    assert _Enabled(window) == {'CONFIGURATION', 'CLEAR'}
    assert _Private(window, '__button_preview').toolTip() == 'Connect the camera first.'
    window.close()

    camera = _Live_Camera_Cls(delay=0.15)
    window, _, _ = _Window(tmp_path / 'b', camera, connect=False)
    assert _Enabled(window) == {'CONFIGURATION', 'CONNECT', 'CLEAR'}
    _Private(window, '__button_connect').click()
    _Pump(lambda: camera.Connected and not _Private(window, '__worker_running'))
    assert _Enabled(window) == {'DISCONNECT', 'PREVIEW', 'SCAN', 'CLEAR'}
    assert _Private(window, '__button_preview').toolTip() == ''

    _Preview(window)
    assert _Enabled(window) == {'DISCONNECT', 'PREVIEW', 'SCAN', 'CLEAR'}
    _Private(window, '__button_scan').click()                            # the preview is stopping, then the scan
    assert _Enabled(window) == set()
    _Pump(lambda: _Private(window, '__scanning'))
    assert _Enabled(window) == set()
    _Idle(window)
    assert _Enabled(window) == {'DISCONNECT', 'PREVIEW', 'SCAN', 'ANALYZE', 'CLEAR'}
    _Preview(window)
    assert _Enabled(window) == {'DISCONNECT', 'PREVIEW', 'SCAN', 'CLEAR'}
    _Private(window, '__button_disconnect').click()
    _Pump(lambda: not camera.Connected)
    assert _Enabled(window) == {'CONNECT', 'CLEAR'}
    window.close()


def test_the_preview_shows_the_table_live_with_the_area_and_the_live_marker(qt_app, tmp_path) -> None:
    """
    Description:
        PREVIEW paints the camera's frames as they come: the view shows the table, the station's inspection area on
        it in the amber (the same overlay as on a scanned frame), and the LIVE marker — white on the solid brand
        purple, a pair that clears 4.5:1 — in its top-left corner, all read from the grabbed pixels. No busy overlay
        covers the live view, and the badge gives the frame rate.
    """

    window, _, _ = _Window(tmp_path, _Live_Camera_Cls())
    viewport = _Private(window, '__viewport')
    _Preview(window, frames=3)
    pixels = _Grab(viewport)
    left, top, right, bottom = _Area_On_Screen(window)
    line = _Is(pixels, Theme.CONST_INSPECTION_AREA)
    assert line[top - 1:top + 2, left:right + 1].any(axis=0).mean() > 0.98
    assert line[top:bottom + 1, right - 1:right + 2].any(axis=1).mean() > 0.98
    table = (np.abs(pixels[(top + bottom) // 2, (left + right) // 2].astype(int) - CONST_TABLE[::-1]) <= 3).all()
    assert table, 'the live frame is not what the view paints'
    margin = viewport.CONST_LIVE_MARGIN
    block = pixels[margin + 1:margin + 20, margin + 1:margin + 60]
    assert _Is(block, Theme.CONST_INK, 2).mean() > 0.6 and _Is(block, Theme.CONST_ON_INK, 2).any()
    assert Theme.Contrast_Ratio(Theme.CONST_INK, Theme.CONST_ON_INK) >= 4.5
    assert not getattr(viewport, '_Viewport_Cls__busy') and not getattr(viewport, '_Viewport_Cls__timer').isActive()
    assert _Private(window, '__frame_badge').text().startswith('Live · ')
    _Private(window, '__button_preview').click()
    _Pump(lambda: _Private(window, '__preview_thread') is None)
    assert not _Is(_Grab(viewport)[margin + 1:margin + 20, margin + 1:margin + 60], Theme.CONST_INK, 2).any()
    window.close()


def test_preview_frames_are_never_analysed_recorded_or_counted(qt_app, tmp_path) -> None:
    """
    Description:
        Many preview frames later, nothing of them exists outside the view: no frame for ANALYZE (the slot does
        nothing while the preview runs, and the stand-in pipeline was never called), no scan or analysis line and
        no capture set in the logger, and the run statistics at zero. The log says only that the preview started.
    """

    window, logger, vision = _Window(tmp_path, _Live_Camera_Cls())
    _Preview(window, frames=8)
    assert _Private(window, '__frame') is None
    _Private(window, '__On_Analyze_Button_Clicked')()
    assert not _Private(window, '__worker_running') and vision.analysed == []
    status = _Private(window, '__status')
    assert status.images.Value() == '0' and status.objects.Value() == '0'
    log = _Log(logger)
    assert 'Live preview started.' in log
    assert not any(marker in log for marker in ('#scan-start', '#scan-end', '#scan-failed', '#analysis-start'))
    assert not glob.glob(os.path.join(str(tmp_path), 'captures', '*', '*'))
    window.close()


def test_scan_during_the_preview_stops_it_and_takes_a_fresh_frame_from_its_own_stream(qt_app, tmp_path) -> None:
    """
    Description:
        SCAN during the preview stops the preview's stream before the scan starts its own, and the frame the scan
        keeps came from the scan's stream — never a frame the preview buffered. The view then shows the scanned
        frame (no LIVE marker), and the scan is logged as a scan, the preview's end as an INFO line before it.
    """

    camera = _Live_Camera_Cls()
    window, logger, _ = _Window(tmp_path, camera)
    _Preview(window, frames=3)
    _Private(window, '__button_scan').click()
    _Idle(window)
    preview_stream, scan_stream = camera.Streams_Started()
    assert camera.events.index(('stop', preview_stream)) < camera.events.index(('start', scan_stream))
    frame = _Private(window, '__frame')
    assert frame[0, 0, 0] == scan_stream
    assert not _Private(window, '__viewport').Is_Live() and _Private(window, '__preview_thread') is None
    assert _Private(window, '__frame_badge').text() == '1920 × 1200 · RGB'
    log = _Log(logger)
    assert log.index('Live preview stopped: SCAN pressed.') < log.index('#scan-start') < log.index('#scan-end')
    window.close()


def test_preview_again_leaves_the_last_result_and_stopping_it_brings_the_result_back(qt_app, tmp_path) -> None:
    """
    Description:
        After a scan and its analysis, PREVIEW goes back to the live view and leaves the last result: the scanned
        frame, the reading and the statistics stay as they were, the view toggle hides (the renders are not on
        screen) and ANALYZE waits. PREVIEW again stops the preview and the analysed result shows again.
    """

    window, _, _ = _Window(tmp_path, _Live_Camera_Cls())
    _Private(window, '__button_scan').click()
    _Idle(window)
    frame = _Private(window, '__frame')
    setattr(window, CONST_MANGLE + '__current_set_id', 'preview_1')
    _Private(window, '__On_Analysis_Finished')(_Result(frame.shape))
    lead = _Private(window, '__reading_lead').text()
    viewport = _Private(window, '__viewport')
    assert viewport.Has_Views() and _Private(window, '__view_toggle').isVisible()

    _Preview(window, frames=2)
    assert _Private(window, '__frame') is frame and _Private(window, '__reading_lead').text() == lead
    assert _Private(window, '__status').images.Value() == '1'
    assert not _Private(window, '__view_toggle').isVisible() and 'ANALYZE' not in _Enabled(window)

    _Private(window, '__button_preview').click()
    _Pump(lambda: _Private(window, '__preview_thread') is None)
    assert not viewport.Is_Live() and viewport.Has_Views() and _Private(window, '__view_toggle').isVisible()
    assert 'ANALYZE' in _Enabled(window) and _Private(window, '__frame') is frame
    window.close()


def test_disconnect_during_the_preview_stops_it_cleanly(qt_app, tmp_path) -> None:
    """
    Description:
        DISCONNECT during the preview stops the preview's stream, joins its worker and only then closes the camera;
        the log says the preview stopped for DISCONNECT, then that the camera disconnected, and the controls are
        those of a disconnected camera.
    """

    camera = _Live_Camera_Cls()
    window, logger, _ = _Window(tmp_path, camera)
    _Preview(window, frames=2)
    thread = _Private(window, '__preview_thread')
    _Private(window, '__button_disconnect').click()
    _Pump(lambda: not camera.Connected)
    assert thread.isFinished() and _Private(window, '__preview_thread') is None
    assert camera.events[-2:] == [('stop', 1), ('close',)]
    log = _Log(logger)
    assert log.index('Live preview stopped: DISCONNECT pressed.') < log.index('Camera disconnected')
    assert _Enabled(window) == {'CONNECT', 'CLEAR'} and not _Private(window, '__viewport').Is_Live()
    window.close()


def test_a_camera_lost_during_the_preview_is_disconnected_and_reported(qt_app, tmp_path) -> None:
    """
    Description:
        The camera is unplugged during the preview: its grab fails and its device reads removed. The preview's
        worker ends, the window closes the camera, logs the lost connection as an ERROR and says in the reading
        panel that the live preview stopped because the camera is no longer reachable.
    """

    camera = _Live_Camera_Cls()
    window, logger, _ = _Window(tmp_path, camera)
    _Preview(window, frames=2)
    camera.removed = camera.failing = True
    _Pump(lambda: not camera.Connected)
    assert _Private(window, '__preview_thread') is None and camera.events[-2:] == [('stop', 1), ('close',)]
    assert _Private(window, '__reading_empty').text() == window.CONST_PREVIEW_LOST_MESSAGE
    assert window.CONST_PREVIEW_LOST_MESSAGE.startswith('The live preview stopped. The camera is no longer reachable')
    assert '[ERROR  ] The camera connection was lost' in _Log(logger)
    assert _Enabled(window) == {'CONNECT', 'CLEAR'}
    window.close()


def test_a_loss_found_by_the_connection_check_stops_the_preview_before_closing(qt_app, tmp_path) -> None:
    """
    Description:
        The connection check finds the device gone while the preview still has frames on their way: it closes
        nothing under the running worker — the preview is stopped first, and the camera is closed once the worker
        has ended — and the loss is reported as above.
    """

    camera = _Live_Camera_Cls(delay=0.1)
    window, _, _ = _Window(tmp_path, camera)
    _Preview(window, frames=1)
    camera.removed = True
    _Private(window, '__On_Connection_Check')()
    assert camera.Connected and ('close',) not in camera.events
    _Pump(lambda: not camera.Connected)
    assert camera.events[-2:] == [('stop', 1), ('close',)]
    assert _Private(window, '__reading_empty').text() == window.CONST_PREVIEW_LOST_MESSAGE
    window.close()


def test_a_preview_that_fails_on_a_camera_still_there_says_so_and_stays_connected(qt_app, tmp_path) -> None:
    """
    Description:
        A preview grab that fails while the device is still there ends the preview with the camera's sentence and
        the way back (PREVIEW), logged and counted as an error; the camera stays connected and PREVIEW available.
    """

    camera = _Live_Camera_Cls()
    window, logger, _ = _Window(tmp_path, camera)
    _Preview(window, frames=1)
    camera.failing = True
    _Pump(lambda: _Private(window, '__preview_thread') is None)
    text = window.CONST_PREVIEW_FAILED_FORMAT % 'The camera did not return a frame in time.'
    assert camera.Connected and _Private(window, '__reading_empty').text() == text
    assert '[ERROR  ] %s' % text in _Log(logger) and _Private(window, '__errors_since_clear') == 1
    assert 'PREVIEW' in _Enabled(window)
    window.close()


def test_a_scan_while_something_moves_is_refused_and_the_preview_comes_back(qt_app, tmp_path) -> None:
    """
    Description:
        SCAN during the preview while a hand moves over the table: the scan waits about a second for a still scene,
        then takes no frame — the reading says something is moving (a 'Moving' badge, not an error), the log has a
        WARNING and the scan's failed marker, no error is counted, and the preview comes back so the operator sees
        the table. Once the scene is still, SCAN takes a frame.
    """

    camera = _Live_Camera_Cls()
    window, logger, _ = _Window(tmp_path, camera)
    _Preview(window, frames=1)
    camera.moving = True
    start = time.monotonic()
    _Private(window, '__button_scan').click()
    _Pump(lambda: _Private(window, '__scanning'))
    _Pump(lambda: not _Private(window, '__scanning'))
    assert 0.9 < time.monotonic() - start < 3.0
    assert _Private(window, '__frame') is None
    assert _Private(window, '__reading_empty').text().startswith('Something is moving in the view')
    assert [badge.text() for badge in _Private(window, '__stage_badges').Badges()] == ['Moving']
    log = _Log(logger)
    assert '[WARNING] Something is moving in the view' in log and '#scan-failed' in log
    assert _Private(window, '__errors_since_clear') == 0
    _Pump(lambda: _Private(window, '__preview_thread') is not None and _Private(window, '__viewport').Is_Live())

    camera.moving = False
    _Private(window, '__button_scan').click()
    _Idle(window)
    _Pump(lambda: _Private(window, '__frame') is not None)
    assert _Private(window, '__preview_thread') is None
    window.close()


def test_a_scan_without_the_preview_while_something_moves_does_not_start_it(qt_app, tmp_path, scan) -> None:
    """
    Description:
        The same refusal for a SCAN pressed without the preview: the message is shown over the last fresh frame
        the check grabbed — the previous scanned frame is gone, so ANALYZE has none — and the preview stays off; it
        comes back only when the scan came from it.
    """

    camera = _Live_Camera_Cls()
    window, _, _ = _Window(tmp_path, camera)
    scan(window)
    camera.moving = True
    scan(window)
    assert _Private(window, '__frame') is None and _Private(window, '__preview_thread') is None
    assert _Shown_Stream(window) == 2 and _Private(window, '__frame_badge').text() == 'Not scanned'
    assert _Private(window, '__reading_empty').text().startswith('Something is moving in the view')
    assert 'ANALYZE' not in _Enabled(window)
    window.close()


def test_the_preview_worker_drops_frames_rather_than_queue_them(qt_app) -> None:
    """
    Description:
        While the window does not take frames, the worker keeps only the newest: it announces a frame once (one
        Frame_Ready, however many frames arrive), counts every replaced one as dropped, and hands over the newest
        when asked; the next frame is announced again. Run on a plain thread so no event is processed meanwhile.
    """

    camera = _Live_Camera_Cls(delay=0.0)
    camera.Connect()
    worker = Preview_Worker_Cls(camera)
    announced = []
    worker.Frame_Ready.connect(lambda: announced.append(worker.Delivered), Qt.DirectConnection)
    runner = threading.Thread(target=worker.Run, daemon=True)
    runner.start()
    try:
        deadline = time.monotonic() + CONST_WAIT_S
        while worker.Delivered < 6 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert announced == [1] and worker.Dropped == worker.Delivered - 1 >= 5
        newest = worker.Take_Frame()
        assert newest is not None and worker.Take_Frame() is None
        delivered = worker.Delivered
        while len(announced) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
    finally:
        worker.Request_Stop()
        runner.join(CONST_WAIT_S)
    assert not runner.is_alive() and announced[1] == delivered + 1
    assert camera.events[-1] == ('stop', 1) and not camera.Previewing


def test_the_gui_thread_never_waits_for_the_camera(qt_app, tmp_path) -> None:
    """
    Description:
        With a camera that takes 0.3 s per frame, pressing PREVIEW, then SCAN during the preview, returns at once,
        and a 10 ms timer on the GUI thread keeps firing throughout — the grabs, the stop and the still-scene scan
        all happen off the GUI thread.
    """

    camera = _Live_Camera_Cls(delay=0.3)
    window, _, _ = _Window(tmp_path, camera)
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(time.monotonic()))
    timer.start()
    start = time.monotonic()
    _Private(window, '__button_preview').click()
    assert time.monotonic() - start < 0.1
    _Pump(lambda: _Private(window, '__preview_worker').Delivered >= 1)
    start = time.monotonic()
    _Private(window, '__button_scan').click()
    assert time.monotonic() - start < 0.1
    _Idle(window)
    # The wait up to now counts too: a GUI thread blocked until just before this line left no tick after the block.
    ticks.append(time.monotonic())
    timer.stop()
    assert _Private(window, '__frame') is not None
    assert len(ticks) > 50 and max(np.diff(ticks)) < 0.15
    window.close()


def test_clear_during_the_preview_keeps_it_live(qt_app, tmp_path) -> None:
    """
    Description:
        CLEAR during the preview clears the last frame, the reading and the statistics, and leaves the preview
        running with its badge.
    """

    window, _, _ = _Window(tmp_path, _Live_Camera_Cls())
    _Private(window, '__button_scan').click()
    _Idle(window)
    _Preview(window, frames=2)
    _Private(window, '__button_clear').click()
    assert _Private(window, '__frame') is None and _Private(window, '__preview_thread') is not None
    delivered = _Private(window, '__preview_worker').Delivered
    _Pump(lambda: _Private(window, '__preview_worker').Delivered > delivered + 1)
    assert _Private(window, '__viewport').Is_Live() and _Private(window, '__frame_badge').text().startswith('Live')
    window.close()


def test_closing_during_the_preview_stops_it_then_closes(qt_app, tmp_path) -> None:
    """
    Description:
        Closing the window during the preview does not destroy a running thread: the close waits for the preview's
        worker to stop its stream and end, then goes through — Qt never logs 'Destroyed while thread is still
        running'.
    """

    camera = _Live_Camera_Cls(delay=0.1)
    window, _, _ = _Window(tmp_path, camera)
    _Preview(window, frames=1)
    thread = _Private(window, '__preview_thread')
    messages = []
    qInstallMessageHandler(lambda mode, ctx, message: messages.append(message))
    try:
        window.close()
        assert window.isVisible()
        _Pump(lambda: not window.isVisible())
    finally:
        qInstallMessageHandler(None)
    assert thread.isFinished() and ('stop', 1) in camera.events
    assert not any('Destroyed while thread is still running' in message for message in messages), messages


def test_closing_during_a_scan_waits_for_it(qt_app, tmp_path) -> None:
    """
    Description:
        A close during a scan is deferred until the scan's worker has ended (about a second at most), then goes
        through, with the scan's frame taken.
    """

    camera = _Live_Camera_Cls(delay=0.15)
    window, logger, _ = _Window(tmp_path, camera)
    _Private(window, '__button_scan').click()
    thread = _Private(window, '__scan_thread')
    window.close()
    assert window.isVisible() and thread.isRunning()
    _Pump(lambda: not window.isVisible())
    assert thread.isFinished() and '#scan-end' in _Log(logger)


def test_the_connection_check_leaves_a_scanning_camera_alone(qt_app, tmp_path) -> None:
    """
    Description:
        The connection check never closes the camera under a running scan: the scan finds the loss itself, at its
        next grab.
    """

    camera = _Live_Camera_Cls(delay=0.15)
    window, _, _ = _Window(tmp_path, camera)
    _Private(window, '__button_scan').click()
    camera.removed = True
    _Private(window, '__On_Connection_Check')()
    assert camera.Connected and ('close',) not in camera.events
    _Idle(window)
    window.close()


@pytest.mark.parametrize('previewing', [False, True], ids=['without-preview', 'during-preview'])
def test_scan_after_analyze_never_shows_the_old_result(qt_app, tmp_path, previewing: bool) -> None:
    """
    Description:
        The rig's case: SCAN, ANALYZE, the part moved, SCAN again — with and without the preview running. The moment
        SCAN is pressed the previous frame and its result leave the Camera View and Scene Understanding (the reading
        says a scan is under way); at no point of the scan does the view paint the old frame or its analysis — it
        shows the fresh frames the stillness check grabs, from the scan's own stream; then the new scanned frame.
    """

    camera = _Live_Camera_Cls(delay=0.12)
    window, _, _ = _Window(tmp_path, camera)
    _Analysed(window)
    if previewing:
        _Preview(window, frames=1)
    _Private(window, '__button_scan').click()
    _Assert_Result_Gone(window)
    scan_stream = camera.stream + 1
    shown = []
    _Pump(lambda: shown.append(_Shown_Stream(window)) or (_Private(window, '__frame') is not None
                                                         and not _Private(window, '__worker_running')))
    seen = [stream for stream in shown if stream is not None]
    assert scan_stream in seen and set(seen) <= ({2, scan_stream} if previewing else {scan_stream}), seen
    assert seen[-1] == scan_stream and not _Private(window, '__viewport').Has_Views()
    assert _Private(window, '__frame')[0, 0, 0] == scan_stream and 'ANALYZE' in _Enabled(window)


def test_the_scan_shows_its_fresh_frames_under_the_scanning_marker_without_a_scrim(qt_app, tmp_path) -> None:
    """
    Description:
        While the scan waits for a still scene, the view paints the fresh frames as they come: the table at its own
        colour (no busy scrim over it, no busy overlay), with the inspection area, and in the corner the SCANNING
        marker — the busy overlay's camera icon and the word in white on the purple block. The badge says
        Scanning….
    """

    camera = _Live_Camera_Cls(delay=0.2)
    camera.moving = True
    window, _, _ = _Window(tmp_path, camera)
    viewport = _Private(window, '__viewport')
    _Private(window, '__button_scan').click()
    _Pump(lambda: getattr(viewport, '_Viewport_Cls__live') is not None)
    assert viewport.Live_Kind() == 'scan' and _Private(window, '__frame_badge').text() == 'Scanning…'
    assert not getattr(viewport, '_Viewport_Cls__busy')
    pixels = _Grab(viewport)
    left, top, right, bottom = _Area_On_Screen(window)
    centre = pixels[(top + bottom) // 2 + 150, (left + right) // 2 + 300]
    assert (np.abs(centre.astype(int) - CONST_TABLE[::-1]) <= 3).all(), 'the fresh frame is covered'
    assert _Is(pixels, Theme.CONST_INSPECTION_AREA)[top - 1:top + 2, left:right + 1].any(axis=0).mean() > 0.98
    margin = viewport.CONST_LIVE_MARGIN
    block = pixels[margin + 1:margin + 26, margin + 1:margin + 140]
    assert _Is(block, Theme.CONST_INK, 2).mean() > 0.5
    # The icon first: its 11 cells of 2 px make an unbroken run of white columns, which no letter makes.
    white = np.flatnonzero(_Is(block, Theme.CONST_ON_INK, 2).any(axis=0))
    run = np.argmax(np.diff(white) != 1) + 1 if white.size > 1 else white.size
    assert white.size and white[0] < 16 and run >= 18, white[:40]
    _Idle(window)


def test_a_scan_refused_after_analyze_keeps_the_last_fresh_frame_never_the_old_result(qt_app, tmp_path) -> None:
    """
    Description:
        After SCAN and ANALYZE, a SCAN during the preview while something moves is refused: the view keeps the last
        fresh frame the check grabbed (from the scan's stream) with the Moving message, ANALYZE has no frame, and the
        preview comes back. Stopping the preview then shows that fresh frame — never the old frame or its result.
    """

    camera = _Live_Camera_Cls(delay=0.1)
    window, _, _ = _Window(tmp_path, camera)
    _Analysed(window)
    _Preview(window, frames=1)
    camera.moving = True
    _Private(window, '__button_scan').click()
    _Pump(lambda: _Private(window, '__scanning'))
    _Pump(lambda: not _Private(window, '__scanning'))
    assert _Private(window, '__reading_empty').text().startswith('Something is moving in the view')
    assert _Private(window, '__frame') is None and 'ANALYZE' not in _Enabled(window)
    _Pump(lambda: _Private(window, '__viewport').Live_Kind() == 'preview')
    _Private(window, '__button_preview').click()
    _Pump(lambda: _Private(window, '__preview_thread') is None)
    viewport = _Private(window, '__viewport')
    assert not viewport.Has_Views() and _Shown_Stream(window) == 3
    assert _Private(window, '__frame_badge').text() == 'Not scanned'


def test_the_header_pill_says_connected_and_live_means_only_the_preview(qt_app, tmp_path) -> None:
    """
    Description:
        The header's camera pill reads Camera connected while the camera is connected and Camera offline otherwise;
        'live' is said only by the preview's marker.
    """

    camera = _Live_Camera_Cls()
    window, _, _ = _Window(tmp_path, camera, connect=False)
    pill = _Private(window, '__pill_camera')
    assert pill.text() == '●  Camera offline'
    _Private(window, '__button_connect').click()
    _Pump(lambda: camera.Connected and not _Private(window, '__worker_running'))
    assert pill.text() == '●  Camera connected' and 'live' not in pill.text().lower()
