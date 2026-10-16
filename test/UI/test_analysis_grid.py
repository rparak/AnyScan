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
## =========================================================================== ##
# Author   : JIC Smart Factory
# File Name: ../test/UI/test_analysis_grid.py
## =========================================================================== ##

# System (Default)
import os
import glob
import threading
import time
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data classes)
import dataclasses
# OpenCV (Computer vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window and the viewport
#   ../UI/Core, ../UI/Widgets
from UI.Core import AnyScan_Window_Cls
from UI.Widgets import Viewport_Cls
# Custom Lib.: AnyScan domain — the camera stand-in, the vision interface and its records, the renderer
#   ../Camera/Core, ../Vision/Core, ../Parameters/Vision, ../Vision/Utilities/Annotate
from Camera.Core import File_Camera_Cls
from Vision.Core import Vision_Backend_Cls
from Parameters.Vision import Analysis_Str, Detection_Str
from Vision.Utilities.Annotate import Render_Views
# Custom Lib.: AnyScan — the configuration and the session logger
#   ../Configuration/Core, ../Logger/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE
from Logger.Core import Session_Logger_Cls

"""
Description:
    The analysis grid (Viewport_Cls.Start_Analysis): a decorative wave of square cells swept over the frame while
    ANALYZE runs — the same drawing over any frame, nothing but the grid drawn over the image, ANALYZING… in the Camera
    View's head with LIVE PREVIEW and SCANNING…, stopped the moment the analysis ends or fails, and never in the images
    written to the logger. Read from grabbed pixels and the written files. Headless (offscreen); no model weights.
"""
CONST_MANGLE = '_AnyScan_Window_Cls'
# The window's configuration: the shipped one without a scale, as test_threading builds it.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
# Two real frames of the test set, with different scenes, at the station's size.
#   Unit [Tuple<string> 1x2]
CONST_FRAMES = tuple(os.path.join(os.path.dirname(__file__), '..', '..', 'Data', 'Images', 'Test', name)
                     for name in ('Image_065.png', 'Image_090.png'))
# The viewport's size in the viewport-level tests: the frames' 16:10, so a frame fills it.
#   Unit [Tuple<int> 1x2] (px)
CONST_SIZE = (600, 375)
# A grid tick in the middle of the sweep, and one in its rest (nothing lit).
#   Unit [int]
CONST_SWEEP_TICK = 6
CONST_REST_TICK = 22
# How long a test waits for the window before it fails.
#   Unit [s]
CONST_WAIT_S = 10.0


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


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


def _Grab(widget: tp.Any) -> np.ndarray:
    """What the widget paints now, as an HxWx3 RGB int array, one pixel per device pixel."""
    QApplication.instance().processEvents()
    image = widget.grab().toImage().convertToFormat(QImage.Format_RGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    array = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return array[:, :image.width(), 2::-1].astype(int)


def _Image(rgb: np.ndarray) -> QImage:
    """An RGB array as a detached QImage."""
    h, w = rgb.shape[:2]
    return QImage(np.ascontiguousarray(rgb).data, w, h, 3 * w, QImage.Format_RGB888).copy()


def _Frame(path: str) -> np.ndarray:
    """A test-set frame as RGB."""
    bgr = cv2.imread(path)
    if bgr is None:
        pytest.fail('The test frame %s is missing.' % path)
    return np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def _Analysing(rgb: np.ndarray, tick: int) -> Viewport_Cls:
    """A viewport of CONST_SIZE showing the frame under the analysis grid at a tick (its timer stopped)."""
    viewport = Viewport_Cls()
    viewport.resize(*CONST_SIZE)
    viewport.Show_Frame(_Image(rgb))
    viewport.Start_Analysis()
    _Private(viewport, '__grid_timer', '_Viewport_Cls').stop()
    setattr(viewport, '_Viewport_Cls__grid_tick', tick)
    return viewport


def test_the_grid_is_the_same_drawing_over_two_different_frames(qt_app) -> None:
    """
    Description:
        The grid is decoration, independent of the frame's content: at the same tick it is one translucent layer laid
        over the frame. Painted over black and over white it gives the layer's colour and coverage per pixel, and over
        each of two different real frames the painted pixels are exactly that layer over the frame (within rounding)
        — the same cells, lines and fills over a part as over the table. It does paint: a large share of each frame is
        changed, and nowhere is the frame covered opaquely.
    """

    size = (1200, 1920, 3)
    black = _Grab(_Analysing(np.zeros(size, np.uint8), CONST_SWEEP_TICK))
    white = _Grab(_Analysing(np.full(size, 255, np.uint8), CONST_SWEEP_TICK))
    for path in CONST_FRAMES:
        rgb = _Frame(path)
        under = _Grab(_Analysing(rgb, CONST_REST_TICK))                 # the same frame, nothing lit
        painted = _Grab(_Analysing(rgb, CONST_SWEEP_TICK))
        expected = black + (white - black) * under / 255.0
        assert np.abs(painted - expected).max() <= 3, path
        changed = (np.abs(painted - under) > 3).any(axis=2)
        assert 0.2 < changed.mean() < 0.9, (path, changed.mean())
    # Translucent everywhere: the layer lets at least 40 % of the frame through in every pixel (a line, the
    # periwinkle at 55 %; a cell's fill lets 70 % through).
    assert ((white - black) >= 0.4 * 255).all()


@pytest.mark.parametrize('state', ['preview', 'scan', 'analysis'])
def test_no_state_label_is_drawn_inside_the_image(qt_app, state) -> None:
    """
    Description:
        While the view shows live frames (the preview's, a scan's) or the frame under analysis, nothing but the frame
        is painted where the image is — no LIVE PREVIEW, SCANNING… or ANALYZING… block, no icon, no words: the grab
        equals a view showing the bare frame (for the analysis, in the wave's rest, when no cell is lit). The state is
        named for the head instead (Marker_Kind and Marker_Changed).
    """

    rgb = _Frame(CONST_FRAMES[0])
    plain = Viewport_Cls()
    plain.resize(*CONST_SIZE)
    plain.Show_Frame(_Image(rgb))
    expected = _Grab(plain)
    named = []
    if state == 'analysis':
        viewport = _Analysing(rgb, CONST_REST_TICK)
    else:
        viewport = Viewport_Cls()
        viewport.resize(*CONST_SIZE)
        viewport.Marker_Changed.connect(named.append)
        viewport.Start_Live(state)
        viewport.Show_Live(_Image(rgb))
    assert viewport.Marker_Kind() == state
    assert named == ([] if state == 'analysis' else [state])
    assert np.abs(_Grab(viewport) - expected).max() <= 3, 'something is drawn over the image'


class _Held_Vision_Cls(Vision_Backend_Cls):
    """A loaded backend whose analysis waits for `go`, then returns one object or, with `fail`, raises."""

    Name, Models_Loaded = 'Held', True

    def __init__(self, fail: bool = False) -> None:
        super().__init__()
        self.fail, self.go, self.started = fail, threading.Event(), threading.Event()

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        self.started.set()
        if not self.go.wait(CONST_WAIT_S):
            raise RuntimeError('the test never released the analysis')
        if self.fail:
            raise RuntimeError('The segmenter failed to process the frame.')
        mask = np.zeros(image.shape[:2], dtype=bool)
        mask[300:560, 400:760] = True
        return Analysis_Str(Objects=[Detection_Str(Label='plate', Bbox=(400, 300, 360, 260), Mask=mask, Cue='both',
                                                   Verdict='OK', Segmenter_Score=0.9, Sentence='A plate.')],
                            Latency_Ms=100, Verdict='1 found', Verdict_Level='ok', Task='caption',
                            Background='A table.')


def _Scanned_Window(tmp_path: tp.Any, vision: Vision_Backend_Cls, wait_for_scan: tp.Callable
                    ) -> tp.Tuple[AnyScan_Window_Cls, Session_Logger_Cls]:
    """A shown window with a real logger in tmp_path, connected to a saved test frame and scanned."""
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(CONST_FRAMES[0]),
                                logger=logger)
    setattr(window, CONST_MANGLE + '__vision', vision)
    _Private(window, '__Sync_Controls')()
    window.resize(1600, 1000)
    window.show()
    _Private(window, '__button_connect').click()
    _Pump(lambda: not _Private(window, '__worker_running'))
    _Private(window, '__button_scan').click()
    wait_for_scan(window)
    assert _Private(window, '__frame') is not None
    return window, logger


def _Close(window: AnyScan_Window_Cls) -> None:
    window.close()
    _Pump(lambda: not window.isVisible())


def _Plain_Grab(window: AnyScan_Window_Cls, with_views: bool) -> np.ndarray:
    """What a view of the window's size shows for its frame (and, with_views, its held renders), with no grid."""
    viewport = _Private(window, '__viewport')
    plain = Viewport_Cls()
    plain.resize(viewport.size())
    plain.Set_Inspection_Area(getattr(viewport, '_Viewport_Cls__area'))
    plain.Show_Frame(getattr(viewport, '_Viewport_Cls__image'))
    if with_views:
        plain.Show_Views(getattr(viewport, '_Viewport_Cls__annotated'), getattr(viewport, '_Viewport_Cls__mask'),
                         'annotated', heatmap=None, legend=None)
    return _Grab(plain)


def test_analyze_starts_the_grid_and_marks_analyzing_in_the_head(qt_app, tmp_path, wait_for_scan) -> None:
    """
    Description:
        Pressing ANALYZE starts the grid at once: the view sweeps it (its timer running, cells painted over the
        frame), with no busy overlay; the head's state marker reads ANALYZING…, above the view, and the head's
        badge carries the step.
    """

    vision = _Held_Vision_Cls()
    window, _ = _Scanned_Window(tmp_path, vision, wait_for_scan)
    viewport, marker = _Private(window, '__viewport'), _Private(window, '__state_marker')
    try:
        frame_only = _Grab(viewport)
        _Private(window, '__button_analyze').click()
        assert vision.started.wait(CONST_WAIT_S)
        assert viewport.Is_Analysing() and _Private(viewport, '__grid_timer', '_Viewport_Cls').isActive()
        assert not getattr(viewport, '_Viewport_Cls__busy')
        assert marker.isVisible() and marker.Text() == 'ANALYZING…'
        assert marker.mapTo(window, marker.rect().bottomLeft()).y() < viewport.mapTo(window, viewport.rect().topLeft()).y()
        assert _Private(window, '__frame_badge').text() == 'Preparing…'
        _Pump(lambda: getattr(viewport, '_Viewport_Cls__grid_tick') >= 3)
        changed = (np.abs(_Grab(viewport) - frame_only) > 3).any(axis=2)
        assert changed.mean() > 0.05, 'the grid is not painted'
    finally:
        vision.go.set()
        _Pump(lambda: not _Private(window, '__worker_running'))
        _Close(window)


@pytest.mark.parametrize('fail', [False, True], ids=['success', 'failure'])
def test_the_grid_stops_when_the_analysis_ends(qt_app, tmp_path, wait_for_scan, fail) -> None:
    """
    Description:
        The grid stops the moment the analysis ends, whichever way: once the result is painted (success) or the
        failure reported, the view no longer analyses, its timer is stopped and the head's marker is gone; the view
        shows exactly the analysed result (success) or the bare frame (failure) — the pixels of a view given the
        same images with no grid — and the head's badge is the frame's size again.
    """

    vision = _Held_Vision_Cls(fail=fail)
    window, _ = _Scanned_Window(tmp_path, vision, wait_for_scan)
    viewport, marker = _Private(window, '__viewport'), _Private(window, '__state_marker')
    try:
        _Private(window, '__button_analyze').click()
        _Pump(lambda: getattr(viewport, '_Viewport_Cls__grid_tick') >= 3)
        vision.go.set()
        _Pump(lambda: not _Private(window, '__worker_running'))
        assert not viewport.Is_Analysing() and not _Private(viewport, '__grid_timer', '_Viewport_Cls').isActive()
        assert not marker.isVisible() and marker.State() == ''
        assert viewport.Has_Views() is (not fail)
        assert np.abs(_Grab(viewport) - _Plain_Grab(window, with_views=not fail)).max() <= 3
        assert _Private(window, '__frame_badge').text() == '1920 × 1200 · RGB'
    finally:
        vision.go.set()
        _Close(window)


def test_the_images_written_to_the_logger_carry_nothing_of_the_grid(qt_app, tmp_path, wait_for_scan) -> None:
    """
    Description:
        After an analysis the grid swept for many ticks, the capture set written to the logger holds the analysed
        frame exactly as scanned (the raw image) and the renders of the result exactly as the renderer draws them
        from that frame (the annotated image and the mask) — nothing of the grid in any of them.
    """

    vision = _Held_Vision_Cls()
    window, logger = _Scanned_Window(tmp_path, vision, wait_for_scan)
    viewport = _Private(window, '__viewport')
    frame_rgb = _Private(window, '__frame').copy()
    try:
        _Private(window, '__button_analyze').click()
        _Pump(lambda: getattr(viewport, '_Viewport_Cls__grid_tick') >= 10)
        vision.go.set()
        _Pump(lambda: not _Private(window, '__worker_running'))
    finally:
        vision.go.set()
        _Close(window)
    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
    result = vision.Analyze(frame_rgb)
    annotated, mask = Render_Views(frame_bgr, result.Objects, cv2, np,
                                   verdict_colored=CONST_CONFIGURATION.Classifies)
    written = {}
    for suffix in ('_raw.png', '_annotated.png', '_mask.png'):
        (path,) = glob.glob(os.path.join(str(tmp_path), 'captures', '*', '*' + suffix))
        written[suffix] = cv2.imread(path)
    assert np.array_equal(written['_raw.png'], frame_bgr)
    assert np.array_equal(written['_annotated.png'], annotated)
    assert np.array_equal(written['_mask.png'], mask)


def test_the_three_states_share_one_marker_in_the_head(qt_app, tmp_path, wait_for_scan) -> None:
    """
    Description:
        LIVE PREVIEW, SCANNING… and ANALYZING… are one marker in the Camera View's head: the same place and size in
        each state, above the view (never inside it), and hidden when the view shows a scanned frame.
    """

    window, _ = _Scanned_Window(tmp_path, _Held_Vision_Cls(), wait_for_scan)
    viewport, marker = _Private(window, '__viewport'), _Private(window, '__state_marker')
    try:
        assert not marker.isVisible()
        places = {}
        for state, start, stop in (('preview', lambda: viewport.Start_Live('preview'), viewport.Stop_Live),
                                   ('scan', lambda: viewport.Start_Live('scan'), viewport.Stop_Live),
                                   ('analysis', viewport.Start_Analysis, viewport.Stop_Analysis)):
            start()
            QApplication.processEvents()
            assert marker.isVisible() and marker.State() == state
            places[state] = marker.geometry()
            assert marker.mapTo(window, marker.rect().bottomLeft()).y() < viewport.mapTo(window, viewport.rect().topLeft()).y()
            stop()
            assert not marker.isVisible()
        assert len(set((g.x(), g.y(), g.width(), g.height()) for g in places.values())) == 1, places
        assert [marker.CONST_STATES[state][0] for state in places] == ['●  LIVE PREVIEW', 'SCANNING…', 'ANALYZING…']
    finally:
        _Close(window)
