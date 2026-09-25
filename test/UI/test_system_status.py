## =========================================================================== ##
# MIT License
# Copyright (c) 2025 JIC Smart Factory
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
# File Name: ../test/UI/test_system_status.py
## =========================================================================== ##


# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QColor, QTextDocument
from PyQt5.QtWidgets import QApplication, QLabel
# Custom Lib.: AnyScan UI — the window and the theme
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan domain — the camera, the logger, the result structure, the configuration
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The status strip's System cell reports the application's real state instead of a standing
    green 'Ready': the latest analysis failed; errors were logged since the last CLEAR; no models
    are loaded; the camera is not connected; otherwise Ready. Each test reads what the cell
    RENDERS — its text through Qt's rich-text rendering, and the state's colour in its pixels.
"""
# The shipped configuration, unscaled.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


class _Vision_Cls(object):
    """A stand-in backend: loaded or not, never asked to analyse."""

    def __init__(self, loaded: bool) -> None:
        self.Name, self.Models_Loaded, self.Model_Names = 'JIC_AnyScan_All_v1', loaded, ('FastSAM-x.pt', 'gemma')


def _Private(window: AnyScan_Window_Cls, name: str) -> tp.Any:
    """A name-mangled private attribute of the window."""
    return getattr(window, '_AnyScan_Window_Cls' + name)


def _Window(reference_background_path: str, tmp_path: tp.Any, loaded: bool, connected: bool) -> AnyScan_Window_Cls:
    """The window with a real logger (errors are logged, and counted), a file camera and a stand-in backend."""
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path),
                                logger=logger)
    setattr(window, '_AnyScan_Window_Cls__vision', _Vision_Cls(loaded))
    if connected:
        _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    window.resize(1400, 900)
    window.show()
    QApplication.instance().processEvents()
    return window


def _System(window: AnyScan_Window_Cls) -> tp.Tuple[str, np.ndarray]:
    """The System cell as it renders: its value text (rich text rendered to plain) and its pixels."""
    cell = _Private(window, '__status').system
    value = [label for label in cell.findChildren(QLabel) if label.text().upper() != 'SYSTEM'][0]
    document = QTextDocument()
    document.setHtml(value.text())
    image = cell.grab().toImage().convertToFormat(4)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    pixels = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return ' '.join(document.toPlainText().replace('\xa0', ' ').split()), pixels.copy()


def _Shows(pixels: np.ndarray, hex_colour: str) -> bool:
    """Whether the colour is painted in the cell (the dot is drawn solid in the state's colour)."""
    r, g, b = QColor(hex_colour).getRgb()[:3]
    return bool(np.any(np.all(pixels[..., :3] == (b, g, r), axis=-1)))


@pytest.mark.parametrize('loaded, connected, text, colour', [
    (False, False, '● Models not loaded', Style.CONST_WARN),
    (True, False, '● Camera disconnected', Style.CONST_INK_MUTE),
    (True, True, '● Ready', Style.CONST_OK),
])
def test_the_system_cell_says_what_is_missing_before_it_says_ready(qt_app, reference_background_path, tmp_path,
                                                                   loaded, connected, text, colour) -> None:
    """
    Description:
        A freshly started window is not 'Ready': without loaded models the cell says so (warning),
        with models but no camera it says the camera is disconnected, and only with both it reads
        Ready in green.
    """

    window = _Window(reference_background_path, tmp_path, loaded, connected)
    shown, pixels = _System(window)
    assert shown == text and _Shows(pixels, colour)
    window.close()


def test_a_failed_analysis_then_the_logged_error_then_clear(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        A failed analysis turns the cell to 'Analysis failed' (error colour). A later successful
        analysis clears that, but the error it logged still stands: 'Error logged'. CLEAR resets
        both, and the cell is back to Ready.
    """

    window = _Window(reference_background_path, tmp_path, loaded=True, connected=True)
    _Private(window, '__On_Scan_Button_Clicked')()

    _Private(window, '__On_Analysis_Failed')('The describer could not run.')
    shown, pixels = _System(window)
    assert shown == '● Analysis failed' and _Shows(pixels, Style.CONST_LOG_ERROR)

    _Private(window, '__On_Analysis_Finished')(Analysis_Str(Objects=[], Verdict='Empty', Verdict_Level='idle',
                                                            Task='caption', Background='A surface.'))
    assert _System(window)[0] == '● Error logged'

    _Private(window, '__On_Clear_Button_Clicked')()
    shown, pixels = _System(window)
    assert shown == '● Ready' and _Shows(pixels, Style.CONST_OK)
    window.close()


def test_every_logged_error_counts_until_clear(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        Errors the window logs — here a lost camera connection and a failed configuration load —
        are counted in the cell until CLEAR: '2 errors logged'.
    """

    window = _Window(reference_background_path, tmp_path, loaded=True, connected=True)
    camera = _Private(window, '__camera')

    def _Lost():
        camera.Disconnect()
        raise __import__('Camera.Core', fromlist=['Camera_Error_Cls']).Camera_Error_Cls('The camera went away.')

    camera.Capture = _Lost
    _Private(window, '__On_Scan_Button_Clicked')()
    assert _System(window)[0] == '● Error logged'

    _Private(window, '__On_Configuration_Load_Failed')('The FastSAM weights are missing.')
    shown, pixels = _System(window)
    assert shown == '● 2 errors logged' and _Shows(pixels, Style.CONST_LOG_ERROR)
    window.close()


def _Cell_Text(window: AnyScan_Window_Cls, name: str) -> str:
    """A status cell's value as it renders (rich text rendered to plain)."""
    cell = getattr(_Private(window, '__status'), name)
    heading = name.upper()
    value = [label for label in cell.findChildren(QLabel) if label.text().upper() != heading][0]
    document = QTextDocument()
    document.setHtml(value.text())
    return ' '.join(document.toPlainText().replace('\xa0', ' ').split())


def _Connect_Through_Connect(window: AnyScan_Window_Cls) -> None:
    """Connect the way the operator does — the CONNECT button and its worker — and wait for it."""
    import time
    _Private(window, '__button_connect').click()
    deadline = time.time() + 5
    while (_Private(window, '__worker_running') or not _Private(window, '__camera').Connected) \
            and time.time() < deadline:
        QApplication.instance().processEvents()
        time.sleep(0.01)
    QApplication.instance().processEvents()


def test_a_lost_connection_reads_disconnected_in_the_camera_cell_too(qt_app, reference_background_path,
                                                                     tmp_path) -> None:
    """
    Description:
        The Camera cell reports the camera's state, not the last button pressed: when the
        connection is lost mid-session it reads Disconnected, as the header pill does — the strip
        and the header never contradict each other — and the Resolution cell is cleared, as it is
        after DISCONNECT.
    """

    window = _Window(reference_background_path, tmp_path, loaded=True, connected=False)
    _Connect_Through_Connect(window)
    assert _Cell_Text(window, 'camera') == '● Connected'
    assert _Cell_Text(window, 'resolution') == '1920 × 1200'
    camera = _Private(window, '__camera')

    def _Lost():
        camera.Disconnect()
        raise __import__('Camera.Core', fromlist=['Camera_Error_Cls']).Camera_Error_Cls('The camera went away.')

    camera.Capture = _Lost
    _Private(window, '__On_Scan_Button_Clicked')()
    assert _Cell_Text(window, 'camera') == '● Disconnected'
    assert 'offline' in _Private(window, '__pill_camera').text()
    assert _Cell_Text(window, 'resolution') == Style.CONST_NO_VALUE     # no size left standing
    window.close()


def test_disconnect_clears_the_camera_and_resolution_cells(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        DISCONNECT leaves the strip exactly as a lost connection does: Camera Disconnected, no
        resolution — the two ways a connection ends are indistinguishable in the strip.
    """

    window = _Window(reference_background_path, tmp_path, loaded=True, connected=False)
    _Connect_Through_Connect(window)
    assert _Cell_Text(window, 'resolution') == '1920 × 1200'
    _Private(window, '__button_disconnect').click()
    QApplication.instance().processEvents()
    assert _Cell_Text(window, 'camera') == '● Disconnected'
    assert _Cell_Text(window, 'resolution') == Style.CONST_NO_VALUE
    window.close()


def test_the_camera_cell_reads_connecting_while_a_connect_runs(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        While CONNECT runs on its worker the Camera cell reads 'Connecting…', and Connected once the
        camera is open.
    """

    import time
    window = _Window(reference_background_path, tmp_path, loaded=True, connected=False)
    camera = _Private(window, '__camera')
    opened = camera._Open

    def _Slow_Open():
        time.sleep(0.3)
        opened()

    camera._Open = _Slow_Open
    _Private(window, '__button_connect').click()
    QApplication.instance().processEvents()
    assert _Cell_Text(window, 'camera') == '● Connecting…'
    deadline = time.time() + 5
    while not (camera.Connected and not _Private(window, '__worker_running')) and time.time() < deadline:
        QApplication.instance().processEvents()
        time.sleep(0.01)
    QApplication.instance().processEvents()
    assert _Cell_Text(window, 'camera') == '● Connected'
    window.close()


def test_no_column_of_the_strip_moves_when_a_state_changes(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        The Camera and System cells reserve the width of their longest state, so whatever they say
        — every system state, connected or not — every cell of the strip keeps its place and width.
    """

    geometries = []

    def _Record(window):
        QApplication.instance().processEvents()
        status = _Private(window, '__status')
        geometries.append([(cell.x(), cell.width()) for cell in (status.camera, status.resolution, status.system,
                                                                 status.updated, status.images, status.objects,
                                                                 status.inference, status.confidence)])

    for loaded, connected in ((False, False), (True, False), (True, True)):
        window = _Window(reference_background_path, tmp_path / ('%s%s' % (loaded, connected)), loaded, connected)
        _Record(window)
        if loaded and connected:
            _Private(window, '__On_Scan_Button_Clicked')()
            _Private(window, '__On_Analysis_Failed')('The describer could not run.')
            _Record(window)
            _Private(window, '__On_Configuration_Load_Failed')('The FastSAM weights are missing.')
            _Private(window, '__On_Analysis_Finished')(Analysis_Str(Objects=[], Verdict='Empty', Verdict_Level='idle',
                                                                    Task='caption', Background='A surface.'))
            _Record(window)
        window.close()
    assert all(geometry == geometries[0] for geometry in geometries), geometries
