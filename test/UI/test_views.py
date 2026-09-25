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
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Headless (offscreen) tests for the Live / History / Log view switch. They assert that the
    switch only changes the central view (the status strip keeps updating and each view keeps
    its state across a switch), that switching back to Live still shows the last result, and
    that the Log view is seeded from the file at startup and then follows live via the logger
    sink. No weights needed.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
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
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path), logger=logger)
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

    assert stack.count() == 4
    assert stack.currentIndex() == 0
    assert switch.Selection() == 'live'
    # The switch order is Live · Trends · History · Log.
    assert [key for key, _label in window.CONST_VIEW_SEGMENTS] == ['live', 'trends', 'history', 'log']

    _Private(window, '__On_View_Selected')('log')
    assert stack.currentIndex() == 3
    _Private(window, '__On_View_Selected')('history')
    assert stack.currentIndex() == 2
    _Private(window, '__On_View_Selected')('trends')
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

    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
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
        window logs the eviction of the displayed set at INFO (History clears it when it is next
        rebuilt — at once if on screen, else when shown). Here the History selection is set and
        __Refresh_History is told that set was evicted; the log must record it by id.
    """

    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = _Framed_Window(reference_background_path, logger=logger)
    history = _Private(window, '__history_view')
    setattr(history, '_History_View_Cls__selected_id', 'setX')   # pretend it is on display

    _Private(window, '__Refresh_History')(['setX', 'setY'])      # setX was evicted
    logger.Close()

    content = open(logger.Path, 'r', encoding='utf-8').read()
    assert 'shown in History (setX) was evicted' in content


def _Writing_Window(reference_background_path, tmp_path, monkeypatch):
    """A window that writes capture sets (a real logger), and a record of every disk rescan History makes."""
    import UI.Views.History as History_Module
    rescans = []
    discover = History_Module.Discover_Capture_Sets
    monkeypatch.setattr(History_Module, 'Discover_Capture_Sets', lambda root: rescans.append(root) or discover(root))
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = _Framed_Window(reference_background_path, logger=logger)
    setattr(window, CONST_MANGLE + '__session_id', 'sess1')
    return window, logger, rescans


def _Listed(window) -> list:
    """The set ids History lists now."""
    return sorted(cap.Set_Id for cap in getattr(_Private(window, '__history_view'), '_History_View_Cls__sets'))


def test_a_set_written_while_history_is_hidden_costs_no_rescan_and_is_listed_when_shown(
        qt_app, reference_background_path, tmp_path, monkeypatch) -> None:
    """
    Description:
        A capture written while another view is on screen does not rescan the disk or rebuild the
        History grid (a scan, thumbnails and two full-resolution decodes, for a view nobody is
        looking at); showing History rebuilds it, and the new set is there.
    """

    window, logger, rescans = _Writing_Window(reference_background_path, tmp_path, monkeypatch)
    rescans.clear()
    setattr(window, CONST_MANGLE + '__current_set_id', 'set1')
    _Private(window, '__On_Analysis_Finished')(_Result(objects=1))
    assert rescans == []                                           # Live is on screen: no rebuild

    _Private(window, '__On_View_Selected')('history')
    assert len(rescans) == 1 and _Listed(window) == ['set1']
    logger.Close()


def test_a_set_written_while_history_is_shown_is_listed_at_once(qt_app, reference_background_path, tmp_path,
                                                                monkeypatch) -> None:
    """
    Description:
        With History on screen, a capture written by the next analysis appears in its list at once,
        without switching away and back.
    """

    window, logger, rescans = _Writing_Window(reference_background_path, tmp_path, monkeypatch)
    _Private(window, '__On_View_Selected')('history')
    assert _Listed(window) == []
    setattr(window, CONST_MANGLE + '__current_set_id', 'set1')
    _Private(window, '__On_Analysis_Finished')(_Result(objects=1))
    assert _Listed(window) == ['set1']
    logger.Close()


def test_classification_flag_flows_to_the_written_set(qt_app, reference_background_path, tmp_path) -> None:
    """
    Description:
        The window records the classification flag it was given on each new capture set, so
        History later knows how the set was written. A window built with classification on writes
        classification:true into the set's metadata; one built off writes false.
    """

    import json
    for enabled in (True, False):
        root = tmp_path / ('on' if enabled else 'off')
        logger = Session_Logger_Cls(config_path=None, log_dir=str(root), install_handlers=False)
        window = _Framed_Window(reference_background_path, logger=logger)
        setattr(window, CONST_MANGLE + '__classification_enabled', enabled)
        setattr(window, CONST_MANGLE + '__session_id', 'sess1')
        setattr(window, CONST_MANGLE + '__current_set_id', 'set1')
        _Private(window, '__On_Analysis_Finished')(_Result(objects=1))

        path = os.path.join(os.path.dirname(logger.Path), 'captures', 'sess1',
                            'set1_objects.json')
        data = json.loads(open(path, 'r', encoding='utf-8').read())
        assert data['classification'] is enabled
        logger.Close()


def test_config_loaded_log_line_carries_the_state() -> None:
    """
    Description:
        The startup configuration-loaded line names the configuration and the classification state
        in both directions — this is the line that answers 'why is there no OK/NOK in the UI?'.
    """

    from Configuration.Core import Config_Loaded_Log_Line
    on = Config_Loaded_Log_Line(dataclasses.replace(CONST_CONFIGURATION, Classification_Enabled=True))
    off = Config_Loaded_Log_Line(CONST_CONFIGURATION)
    for line in (on, off):
        assert CONST_CONFIGURATION.Name in line and 'a2A1920_51gcPRO_Computar_M1228_MPW3' in line
        assert 'Seg_Anything' in line
    assert 'enabled' in on and 'OK/NOK' in on
    assert 'disabled' in off and 'detected objects only' in off


def test_startup_names_the_configuration_it_offers_and_claims_nothing_loaded(tmp_path) -> None:
    """
    Description:
        At startup the configuration file is READ, not loaded: the log names the configuration it
        will offer and nothing more — no 'Loaded configuration', no calibration or reference line,
        no classification state and no 'Measuring objects' scale line, all of which describe a
        configuration in force. The launcher itself is run (in a subprocess, offscreen, quitting at
        once) so this is the log the application really writes.
    """

    import subprocess
    import sys
    import glob as _glob
    project = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    driver = (
        "import os, sys, functools\n"
        "os.environ['QT_QPA_PLATFORM'] = 'offscreen'\n"
        "sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
        "import run\n"
        "from PyQt5.QtCore import QTimer\n"
        "from PyQt5.QtWidgets import QApplication\n"
        "run.Session_Logger_Cls = functools.partial(run.Session_Logger_Cls, log_dir=%r, install_handlers=False)\n"
        "original = QApplication.exec_\n"
        "QApplication.exec_ = lambda self: (QTimer.singleShot(200, self.quit), original())[1]\n"
        "sys.argv = ['run.py']\n"
        "sys.exit(run.main())\n") % (os.path.join(project, 'App'), os.path.join(project, 'src'), str(tmp_path))
    result = subprocess.run([sys.executable, '-c', driver], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    (log_path,) = _glob.glob(os.path.join(str(tmp_path), '*.txt'))
    log = open(log_path, encoding='utf-8').read()
    assert "Configuration found: 'Cfg. Segment Anything' (%s)" % CONST_CONFIGURATION.Name in log
    for claim in ('Loaded configuration', 'reads calibration', 'Classification is', 'Measuring objects',
                  'will not be measured'):
        assert claim not in log, claim
