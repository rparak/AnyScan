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
# File Name: ../test/UI/test_signal_wiring.py
## =========================================================================== ##

# System (Default)
import os
import time
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyYAML (the mode files the dialog lists) [pip3 install PyYAML]
import yaml
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget
# Custom Lib.: AnyScan UI — the window, the dialog module, the views
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Configuration_Dialog
from UI.Configuration_Dialog import Configuration_Dialog_Cls
#   ../UI/Views/History
from UI.Views.History import History_View_Cls
#   ../UI/Views/Log
from UI.Views.Log import Log_View_Cls
#   ../UI/Capture
from UI.Capture import Capture_Writer_Cls, Build_Set_Metadata
# Custom Lib.: AnyScan domain — the camera, the vision interface, the structures, the configuration
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Core
from Vision.Core import Vision_Backend_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str, Detection_Str, Confidence_Thresholds_Str
#   ../Logger/Core
from Logger.Core import CONST_LEVEL_INFO, CONST_LEVEL_WARNING
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Mode_Directory, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Every user-facing signal connection, driven the way the operator drives it: a real mouse
    click (QTest) on the real widget, then an assertion on what that click visibly changed. The
    other UI tests mostly call the slots directly, so deleting a `connect(...)` left them green;
    each test here fails if the connection it names is removed (checked by deleting each one
    once). The worker-thread hand-offs are covered in test_threading.py and the Log's scroll-bar
    wiring in test_log_view.py, both through real signals already. No camera and no weights.
"""
# The window's configuration: the shipped one, unscaled.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

# The shipped hardware id, for the mode files the dialog lists.
#   Unit [string]
CONST_HARDWARE = 'a2A1920_51gcPRO_Computar_M1228_MPW3'

# How long a wait for a worker thread may take before the test gives up.
#   Unit [float] (seconds)
CONST_TIMEOUT = 5.0


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(owner: tp.Any, name: str, mangle: str) -> tp.Any:
    """A name-mangled private attribute of an object."""
    return getattr(owner, mangle + name)


def _Window_Private(window: AnyScan_Window_Cls, name: str) -> tp.Any:
    """A name-mangled private attribute of the window."""
    return _Private(window, name, '_AnyScan_Window_Cls')


def _Pump_Until(condition: tp.Callable[[], bool], timeout: float = CONST_TIMEOUT) -> bool:
    """Run the event loop until the condition holds or the timeout passes; the final state."""
    app, deadline = QApplication.instance(), time.time() + timeout
    while not condition() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    return condition()


def _Click(widget: QWidget, pos: tp.Optional[QPoint] = None) -> None:
    """A left click on a widget (its centre unless a position is given), as the operator makes it."""
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, pos if pos is not None else widget.rect().center())
    QApplication.instance().processEvents()


def _Segment(control: QWidget, key: str) -> QWidget:
    """The button of one segment of a Segmented_Control_Cls."""
    return _Private(control, '__buttons', '_Segmented_Control_Cls')[key]


def _Grab(widget: QWidget) -> np.ndarray:
    """What the widget paints now, as an HxWx4 array (the pixels, not its state)."""
    image = widget.grab().toImage().convertToFormat(4)          # QImage.Format_RGB32
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4).copy()


class _Loaded_Vision_Cls(Vision_Backend_Cls):
    """A backend with its configuration loaded that returns two located objects at once."""

    def __init__(self) -> None:
        super().__init__()
        self.Models_Loaded, self.Name, self.Model_Names = True, 'JIC_AnyScan_All_v1', ('FastSAM-x.pt', 'gemma')

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        h, w = image.shape[:2]
        objects = [Detection_Str(Label='ring', Bbox=(w // 8, h // 8, w // 4, h // 4), Segmenter_Score=0.91,
                                 Sentence='A silver ring.', Cue='both'),
                   Detection_Str(Label='nut', Bbox=(w // 2, h // 2, w // 5, h // 5), Segmenter_Score=0.9,
                                 Sentence='A hex nut.', Cue='both')]
        return Analysis_Str(Objects=objects, Verdict='ok', Verdict_Level='ok', Task='caption', Latency_Ms=5)


class _Configurable_Vision_Cls(Vision_Backend_Cls):
    """A backend whose Configure loads a configuration quickly, on whatever thread runs it."""

    def __init__(self, loaded: bool = False) -> None:
        super().__init__()
        self.Models_Loaded, self.Name, self.Model_Names = loaded, 'JIC_AnyScan_All_v1', ('FastSAM-x.pt', 'gemma')
        self.configured = []

    def Configure(self, Configuration_Str, stage_cb=None) -> None:
        time.sleep(0.05)
        self.configured.append(Configuration_Str.Mode)
        self.Models_Loaded, self.Name = True, Configuration_Str.Identity.Model_Set


def _Shown_Window(reference_background_path: str, vision: Vision_Backend_Cls) -> AnyScan_Window_Cls:
    """The window, shown offscreen, on a file camera with the given backend (no logger: nothing is written)."""
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    setattr(window, '_AnyScan_Window_Cls__vision', vision)
    window.resize(1400, 900)
    window.show()
    _Window_Private(window, '__Sync_Controls')()
    QApplication.instance().processEvents()
    return window


def _Connected_And_Scanned(reference_background_path: str) -> AnyScan_Window_Cls:
    """A window brought to 'frame captured' by clicking CONNECT and then SCAN."""
    window = _Shown_Window(reference_background_path, _Loaded_Vision_Cls())
    _Click(_Window_Private(window, '__button_connect'))
    assert _Pump_Until(lambda: _Window_Private(window, '__camera').Connected
                       and not _Window_Private(window, '__worker_running'))
    _Click(_Window_Private(window, '__button_scan'))
    return window


def _Analyzed(reference_background_path: str) -> AnyScan_Window_Cls:
    """A window brought to 'analysis delivered' by clicking CONNECT, SCAN and ANALYZE."""
    window = _Connected_And_Scanned(reference_background_path)
    _Click(_Window_Private(window, '__button_analyze'))
    assert _Pump_Until(lambda: _Window_Private(window, '__viewport').Has_Views()
                       and not _Window_Private(window, '__worker_running'))
    return window


# ------------------------------------------------------------------ the main window

def test_clicking_connect_opens_the_camera(qt_app, reference_background_path) -> None:
    """
    Description:
        CONNECT (clicked) starts the connect worker and the camera ends up connected.
    """

    window = _Shown_Window(reference_background_path, _Loaded_Vision_Cls())
    camera = _Window_Private(window, '__camera')
    assert not camera.Connected

    _Click(_Window_Private(window, '__button_connect'))

    assert _Pump_Until(lambda: camera.Connected)
    window.close()


def test_clicking_scan_captures_and_shows_the_frame(qt_app, reference_background_path, reference_shape) -> None:
    """
    Description:
        SCAN (clicked) captures a frame and the frame badge states its size.
    """

    window = _Connected_And_Scanned(reference_background_path)

    height, width, _ = reference_shape
    assert _Window_Private(window, '__frame_badge').text() == '%d × %d · RGB' % (width, height)
    window.close()


def test_clicking_analyze_runs_the_analysis_and_delivers_both_renders(qt_app, reference_background_path) -> None:
    """
    Description:
        ANALYZE (clicked) runs the backend on the worker, and the result arrives in the window:
        both renders are held and the object list shows the two objects.
    """

    window = _Analyzed(reference_background_path)

    assert _Window_Private(window, '__viewport').Has_Views()
    blocks = _Private(_Window_Private(window, '__object_list'), '__blocks', '_Object_List_Cls')
    assert len(blocks) == 2
    window.close()


def test_clicking_clear_empties_the_frame(qt_app, reference_background_path) -> None:
    """
    Description:
        CLEAR (clicked) drops the frame: the badge returns to 'No frame'.
    """

    window = _Connected_And_Scanned(reference_background_path)
    assert _Window_Private(window, '__frame_badge').text() != 'No frame'

    _Click(_Window_Private(window, '__button_clear'))

    assert _Window_Private(window, '__frame_badge').text() == 'No frame'
    window.close()


def test_clicking_disconnect_closes_the_camera(qt_app, reference_background_path) -> None:
    """
    Description:
        DISCONNECT (clicked) closes the camera.
    """

    window = _Connected_And_Scanned(reference_background_path)
    camera = _Window_Private(window, '__camera')
    assert camera.Connected

    _Click(_Window_Private(window, '__button_disconnect'))

    assert not camera.Connected
    window.close()


def test_clicking_a_view_segment_switches_the_central_page(qt_app, reference_background_path) -> None:
    """
    Description:
        The header's Live / Trends / History / Log switch (clicked) changes the page the central
        stack shows, and back.
    """

    window = _Shown_Window(reference_background_path, _Loaded_Vision_Cls())
    switch = _Window_Private(window, '__view_switch')
    stack = _Window_Private(window, '__stack')

    for key in ('trends', 'history', 'log', 'live'):
        _Click(_Segment(switch, key))
        assert stack.currentIndex() == AnyScan_Window_Cls.CONST_VIEW_INDEX[key], key
    window.close()


def test_clicking_the_view_toggle_repaints_the_viewport_with_the_other_render(qt_app, reference_background_path) -> None:
    """
    Description:
        The Annotated / Mask toggle (clicked) changes what the viewport PAINTS — the pixels, not a
        state variable — and clicking back restores the annotated picture exactly.
    """

    window = _Analyzed(reference_background_path)
    viewport = _Window_Private(window, '__viewport')
    toggle = _Window_Private(window, '__view_toggle')
    annotated = _Grab(viewport)

    _Click(_Segment(toggle, 'mask'))
    mask = _Grab(viewport)
    assert not np.array_equal(annotated, mask)

    _Click(_Segment(toggle, 'annotated'))
    assert np.array_equal(_Grab(viewport), annotated)
    window.close()


# ------------------------------------------------------------ the Configuration dialog

def _Mode_File(directory: str, mode: str) -> str:
    """A mode file for the shipped hardware (a copy of the shipped one), naming the shipped station."""
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    data['Identity']['Display_Name'] = 'Cfg. %s' % mode
    path = os.path.join(directory, 'Config_%s_Mode_%s.yaml' % (CONST_HARDWARE, mode))
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path


@pytest.fixture
def two_modes(configuration_root) -> tp.List[str]:
    """A Configuration/Mode/ directory the dialog lists: two modes for the shipped hardware."""
    return [_Mode_File(Mode_Directory(), 'Alpha'), _Mode_File(Mode_Directory(), 'Beta')]


def _Item_Point(dialog: Configuration_Dialog_Cls, path: str) -> tp.Tuple[QWidget, QPoint]:
    """Where to click on a listed configuration: the list's viewport and the item's centre."""
    listed = _Private(dialog, '__list', '_Configuration_Dialog_Cls')
    for row in range(listed.count()):
        item = listed.item(row)
        if os.path.abspath(item.data(Qt.UserRole)) == os.path.abspath(path):
            return listed.viewport(), listed.visualItemRect(item).center()
    raise AssertionError('%s is not listed' % path)


def test_clicking_configuration_opens_the_dialog_whose_buttons_load_and_close(qt_app, reference_background_path,
                                                                               two_modes) -> None:
    """
    Description:
        CONFIGURATION (clicked) opens the modal dialog. The configuration in force is loaded, so LOAD
        starts with nothing to do; clicking another configuration selects it (LOAD becomes
        available), LOAD (clicked) loads it on the worker, and CLOSE (clicked) ends the modal loop —
        after which the window runs the loaded configuration.
    """

    vision = _Configurable_Vision_Cls(loaded=True)
    window = AnyScan_Window_Cls(Configuration_Str=Load_Configuration(two_modes[0]),
                                camera=File_Camera_Cls(reference_background_path))
    setattr(window, '_AnyScan_Window_Cls__vision', vision)
    window.show()
    _Window_Private(window, '__Sync_Controls')()
    seen = {}

    def _Inside_The_Modal_Loop() -> None:
        dialog = QApplication.activeModalWidget()
        seen['dialog'] = dialog
        if not isinstance(dialog, Configuration_Dialog_Cls):
            return                                              # the assertion below reports it
        load = _Private(dialog, '__button_load', '_Configuration_Dialog_Cls')
        seen['load_enabled_before_select'] = load.isEnabled()
        _Click(*_Item_Point(dialog, two_modes[1]))
        seen['load_enabled_after_select'] = load.isEnabled()
        _Click(load)
        seen['loaded'] = _Pump_Until(lambda: not dialog.Loading and vision.configured == ['Beta'])
        _Click(_Private(dialog, '__button_close', '_Configuration_Dialog_Cls'))
        if dialog.isVisible():                                  # never leave the modal loop hanging
            seen['closed_by_click'] = False
            dialog.done(0)

    QTimer.singleShot(0, _Inside_The_Modal_Loop)
    _Click(_Window_Private(window, '__button_configuration'))   # returns when the modal loop ends

    assert isinstance(seen.get('dialog'), Configuration_Dialog_Cls)
    assert not seen['load_enabled_before_select']              # the one in force is loaded
    assert seen['load_enabled_after_select']
    assert seen['loaded']
    assert seen.get('closed_by_click', True)
    assert _Window_Private(window, '__config').Mode == 'Beta'
    assert _Window_Private(window, '__button_connect').isEnabled()
    window.close()


def test_double_clicking_a_configuration_loads_it(qt_app, two_modes) -> None:
    """
    Description:
        A double-click on a listed configuration loads it, like selecting it and pressing LOAD.
    """

    vision = _Configurable_Vision_Cls()
    dialog = Configuration_Dialog_Cls(vision, Load_Configuration(two_modes[0]))
    dialog.show()
    viewport, point = _Item_Point(dialog, two_modes[1])

    # A real double-click arrives as press, release, double-click: an item view emits
    # itemDoubleClicked only when the press landed on the same item, so the first click matters.
    QTest.mouseClick(viewport, Qt.LeftButton, Qt.NoModifier, point)
    QTest.mouseDClick(viewport, Qt.LeftButton, Qt.NoModifier, point)

    assert _Pump_Until(lambda: not dialog.Loading and vision.configured == ['Beta'])
    dialog.reject()


# ---------------------------------------------------------------------- the History view

def _Write_Set(writer: Capture_Writer_Cls, set_id: str, classification: bool = False) -> None:
    """Write one full set (a bright annotated image, two objects) through the real writer."""
    raw = np.full((120, 180, 3), 30, np.uint8)
    annotated = np.full((120, 180, 3), 200, np.uint8)
    mask = np.zeros((120, 180, 3), np.uint8)
    objects = [Detection_Str(Label='ring', Bbox=(10, 10, 60, 40), Segmenter_Score=0.91,
                             Sentence='A silver ring.', Verdict='OK', Cue='both'),
               Detection_Str(Label='nut', Bbox=(100, 60, 40, 40), Segmenter_Score=0.9,
                             Sentence='A hex nut.', Verdict='OK', Cue='both')]
    metadata = Build_Set_Metadata('sessionA', set_id, '2026-09-20T10:00:00', objects, (180, 120),
                                  'caption', 1180, 91, '', classification, '', scale=None,
                                  configuration='Config_Test_Mode_A.yaml',
                                  background_reference='Data/Images/Background/Image_Background_001.png',
                                  hardware={}, window=None)
    writer.Write('sessionA', set_id, raw, annotated, mask, 'text', ['0 0.5 0.5 0.1 0.1'],
                 ['0 0.4 0.4 0.6 0.6'], metadata, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)


def _Shown_History(captures_root: str, classification: bool = False, height: int = 780) -> History_View_Cls:
    """The History view over a captures root, shown offscreen and refreshed."""
    view = History_View_Cls(captures_root, classification_enabled=classification,
                            Confidence_Thresholds_Str=Confidence_Thresholds_Str())
    view.resize(1400, height)
    view.show()
    view.Refresh()
    _Pump_Until(lambda: False, timeout=0.05)
    return view


def _History_Private(view: History_View_Cls, name: str) -> tp.Any:
    """A name-mangled private attribute of the History view."""
    return _Private(view, name, '_History_View_Cls')


def test_clicking_a_history_card_selects_that_set(qt_app, tmp_path) -> None:
    """
    Description:
        A click on a capture card shows THAT set in the detail panel.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Set(writer, 'set1')
    _Write_Set(writer, 'set2')
    view = _Shown_History(str(tmp_path))
    cards = _History_Private(view, '__cards')
    shown = _History_Private(view, '__detail_cap').Set_Id
    other = next(card for card in cards if getattr(card, '_Thumb_Card_Cls__cap').Set_Id != shown)

    _Click(other)

    assert _History_Private(view, '__detail_cap').Set_Id == getattr(other, '_Thumb_Card_Cls__cap').Set_Id != shown
    view.close()


def test_clicking_info_opens_the_info_panel(qt_app, tmp_path) -> None:
    """
    Description:
        The Info button (clicked) opens the side panel beside the images.
    """

    _Write_Set(Capture_Writer_Cls(str(tmp_path)), 'set1')
    view = _Shown_History(str(tmp_path))
    assert not view.Is_Info_Open()

    _Click(_History_Private(view, '__info_button'))

    assert view.Is_Info_Open()
    view.close()


def test_clicking_an_object_row_paints_its_highlight_on_the_annotated_pane(qt_app, tmp_path) -> None:
    """
    Description:
        With the Info panel open, clicking an object row changes what the Annotated pane PAINTS
        (its highlight box), while the mask pane is left as it was.
    """

    _Write_Set(Capture_Writer_Cls(str(tmp_path)), 'set1')
    view = _Shown_History(str(tmp_path))
    _Click(_History_Private(view, '__info_button'))
    _Pump_Until(lambda: False, timeout=0.4)                     # let the slide-in finish
    pane_a, pane_b = _History_Private(view, '__image_a'), _History_Private(view, '__image_b')
    before_a, before_b = _Grab(pane_a), _Grab(pane_b)
    blocks = _Private(_History_Private(view, '__object_list'), '__blocks', '_Object_List_Cls')

    _Click(blocks[1])

    assert not np.array_equal(_Grab(pane_a), before_a)
    assert np.array_equal(_Grab(pane_b), before_b)
    view.close()


def test_clicking_a_history_filter_segment_narrows_the_cards(qt_app, tmp_path) -> None:
    """
    Description:
        In a classified run the filter (clicked) narrows the grid: 'NOK' shows no card (nothing is
        NOK today), 'All' brings them back.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Set(writer, 'set1', classification=True)
    _Write_Set(writer, 'set2', classification=True)
    view = _Shown_History(str(tmp_path), classification=True)
    control = _History_Private(view, '__filter')
    assert len(_History_Private(view, '__cards')) == 2

    _Click(_Segment(control, 'nok'))
    assert len(_History_Private(view, '__cards')) == 0

    _Click(_Segment(control, 'all'))
    assert len(_History_Private(view, '__cards')) == 2
    view.close()


def test_scrolling_the_history_list_loads_the_thumbnails_that_come_into_view(qt_app, tmp_path) -> None:
    """
    Description:
        Thumbnails load lazily: in a short view the bottom cards are not loaded until the list is
        scrolled to them, and then they are.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    for i in range(12):
        _Write_Set(writer, 'set%02d' % i)
    view = _Shown_History(str(tmp_path), height=420)
    cards = _History_Private(view, '__cards')
    assert not cards[-1].Loaded()                               # below the fold

    bar = _History_Private(view, '__list_scroll').verticalScrollBar()
    assert bar.maximum() > 0
    bar.setValue(bar.maximum())
    QApplication.instance().processEvents()

    assert cards[-1].Loaded()
    view.close()


# -------------------------------------------------------------------------- the Log view

def _Log_Line(time_text: str, level: str, message: str) -> str:
    """One formatted log line, exactly as the logger writes it."""
    return '2026-09-12 %s [%-7s] %s' % (time_text, level, message)


def test_clicking_a_log_filter_segment_filters_the_rows(qt_app) -> None:
    """
    Description:
        The level filter (clicked) hides the other levels' rows; 'All' shows every row again.
    """

    view = Log_View_Cls()
    view.show()
    view.Append_Line(_Log_Line('08:00:01', CONST_LEVEL_INFO, 'One.'))
    view.Append_Line(_Log_Line('08:00:02', CONST_LEVEL_WARNING, 'Two.'))
    control = _Private(view, '__filter', '_Log_View_Cls')

    _Click(_Segment(control, 'warning'))
    assert view.Shown_Count() == 1

    _Click(_Segment(control, 'all'))
    assert view.Shown_Count() == 2
    view.close()


def test_clicking_the_new_lines_indicator_returns_to_the_tail(qt_app) -> None:
    """
    Description:
        Scrolled up, a new line raises the 'new lines' indicator; clicking it jumps to the bottom
        and resumes following.
    """

    view = Log_View_Cls()
    view.resize(700, 200)
    view.show()
    for i in range(80):
        view.Append_Line(_Log_Line('08:00:%02d' % (i % 60), CONST_LEVEL_INFO, 'Line %d.' % i))
    _Pump_Until(lambda: False, timeout=0.05)
    bar = _Private(view, '__scroll', '_Log_View_Cls').verticalScrollBar()
    bar.setValue(0)
    view.Append_Line(_Log_Line('09:00:00', CONST_LEVEL_WARNING, 'While scrolled up.'))
    _Pump_Until(lambda: False, timeout=0.05)
    indicator = _Private(view, '__new_indicator', '_Log_View_Cls')
    assert indicator.isVisible() and not view.Is_Following()

    _Click(indicator)

    assert bar.value() == bar.maximum()
    assert view.Is_Following()
    view.close()
