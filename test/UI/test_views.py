## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../test/UI/test_views.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window; domain — the camera, the result, the logger
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str, Detection_Str
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls

"""
Description:
    Headless (offscreen) tests for the Live / History / Log view switch. They assert that the
    switch only changes the central view (the status strip keeps updating and each view keeps
    its state across a switch), that switching back to Live still shows the last result, and
    that the Log view is seeded from the file at startup and then follows live via the logger
    sink. No weights needed.
"""
# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def _Framed_Window(reference_background_path, logger=None) -> AnyScan_Window_Cls:
    """A window with a frame set, ready to receive completed analyses."""
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path), logger=logger)
    setattr(window, CONST_MANGLE + '__frame', np.zeros((20, 30, 3), dtype=np.uint8))
    return window


def _Result(objects=0) -> Analysis_Str:
    """A finished reading carrying `objects` scored detections."""
    dets = [Detection_Str(Label='p', Bbox=(0, 0, 4, 4), Segmenter_Score=0.9)
            for _ in range(objects)]
    return Analysis_Str(Objects=dets, Background='A plain surface.', Latency_Ms=100,
                        Verdict='ok', Verdict_Level='ok', Task='t')


def test_startup_is_live_and_the_switch_changes_only_the_central_view(qt_app, reference_background_path) -> None:
    """
    Description:
        Live is selected at startup (the first segment, stack page 0). Selecting a view moves
        the stack to that page and nothing else — the switch drives only the central area.
    """

    window = _Framed_Window(reference_background_path)
    stack = _Private(window, '__stack')
    switch = _Private(window, '__view_switch')

    assert stack.count() == 3
    assert stack.currentIndex() == 0
    assert switch.Selection() == 'live'

    _Private(window, '__On_View_Selected')('log')
    assert stack.currentIndex() == 2
    _Private(window, '__On_View_Selected')('history')
    assert stack.currentIndex() == 1
    _Private(window, '__On_View_Selected')('live')
    assert stack.currentIndex() == 0


def test_status_bar_stays_live_on_another_view_and_live_keeps_its_result(qt_app, reference_background_path) -> None:
    """
    Description:
        An analysis that completes while the operator is on another view still drives the
        fixed status strip, and switching back to Live shows its result — not a blank card.
        One analysis runs on Live, then the view switches to Log and a second analysis runs;
        the status counter advances to 2 while on Log, and the Live reading is populated (not
        cleared) when Live is selected again.
    """

    window = _Framed_Window(reference_background_path)
    status = _Private(window, '__status')

    _Private(window, '__On_Analysis_Finished')(_Result(objects=1))
    assert status.images.Value() == '1'

    _Private(window, '__On_View_Selected')('log')
    _Private(window, '__On_Analysis_Finished')(_Result(objects=2))
    # The status strip updated while Log was the visible view.
    assert status.images.Value() == '2'
    assert status.objects.Value() == '3'                 # 1 + 2 across the two analyses

    _Private(window, '__On_View_Selected')('live')
    lead = _Private(window, '__reading_lead')
    # The Live reading survived the switch — it is shown and non-empty, not a blank card.
    assert not lead.isHidden()
    assert lead.text() != ''
    # The two objects from the second analysis are still rendered in the Live panel.
    assert _Private(window, '__object_list').box.count() == 2


def test_each_view_keeps_its_state_across_a_switch(qt_app, reference_background_path) -> None:
    """
    Description:
        Switching is a page change, so a view keeps its state. The Log view's filter selection
        is set to 'Error', the view is switched away and back, and the filter is still 'Error'
        with the same shown-count — the view was not rebuilt.
    """

    window = _Framed_Window(reference_background_path)
    log_view = _Private(window, '__log_view')
    log_view.Append_Line('2026-09-12 08:00:01 [INFO   ] One.')
    log_view.Append_Line('2026-09-12 08:00:02 [ERROR  ] Two.')

    log_filter = getattr(log_view, '_Log_View_Cls__filter')
    log_filter.Set_Selection('error')
    getattr(log_view, '_Log_View_Cls__Apply_Filter')()
    assert log_view.Shown_Count() == 1

    _Private(window, '__On_View_Selected')('log')
    _Private(window, '__On_View_Selected')('live')
    _Private(window, '__On_View_Selected')('log')

    # The filter and the shown-count are exactly as left — no rebuild on switch.
    assert log_filter.Selection() == 'error'
    assert log_view.Shown_Count() == 1


def test_log_view_seeds_from_the_file_and_then_follows_the_sink(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        The Log view's source of truth is the logger: lines written before the window exists
        are seeded from the file once, and lines written afterwards arrive live through the
        sink. Two seed lines then one live line give three rendered rows, with the live line
        rendered by the same path as the seed.
    """

    logger = Session_Logger_Cls(log_dir=str(tmp_path), install_handlers=False)
    logger.Log_Info('Seed line one.')
    logger.Log_Warning('Seed line two.')

    window = _Framed_Window(reference_background_path, logger=logger)
    log_view = _Private(window, '__log_view')
    assert log_view.Shown_Count() == 2                   # both seed lines rendered

    logger.Log_Error('A live line.')                     # arrives via the sink
    for _ in range(2):
        qt_app.processEvents()
    assert log_view.Shown_Count() == 3

    logger.Set_Line_Sink(None)                           # detach before the tmp logger is gone
    logger.Close()


def test_evicting_the_displayed_history_set_is_logged(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        When retention evicts the set currently shown in History, the reason is findable: the
        window logs the eviction of the displayed set at INFO (and refreshes History, which
        clears it). Here the History selection is set and __Refresh_History is told that set was
        evicted; the log must record it by id.
    """

    logger = Session_Logger_Cls(log_dir=str(tmp_path), install_handlers=False)
    window = _Framed_Window(reference_background_path, logger=logger)
    history = _Private(window, '__history_view')
    setattr(history, '_History_View_Cls__selected_id', 'setX')   # pretend it is on display

    _Private(window, '__Refresh_History')(['setX', 'setY'])      # setX was evicted
    logger.Close()

    content = open(logger.Path, 'r', encoding='utf-8').read()
    assert 'shown in History (setX) was evicted' in content
