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
# File Name: ../test/UI/test_logging_coverage.py
## =========================================================================== ##

# System (Default)
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan — the window, the logger, the camera base, the result, the formatter
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Camera/Core
from Camera.Core import Camera_Backend_Cls, Camera_Error_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
from Reporting.Core import Screen_Understanding

"""
Description:
    Headless (offscreen) tests for the logging-coverage extensions: per-analysis captures
    written under logger/captures with the set id linking the log to the files, the
    partial-confidence and re-analysis-in-flight warnings, the capture write-failure path
    (logs an ERROR, never raises), the camera->logger event sink, and the mid-session
    connection-lost ERROR. A real logger writes to tmp_path so the lines and files are read
    back. No camera hardware and no weights.
"""

CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


class _Idle_Camera_Cls(Camera_Backend_Cls):
    """A camera whose grab returns a fixed frame; used where scanning must succeed."""

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        pass

    def _Grab(self):
        return np.zeros((40, 60, 3), dtype=np.uint8)

    @property
    def Resolution(self):
        return (60, 40)


class _Lost_Camera_Cls(_Idle_Camera_Cls):
    """A camera whose Capture drops the connection and fails — a mid-session loss."""

    def Capture(self):
        self.Disconnect()
        raise Camera_Error_Cls('device connection lost')


class _Transient_Camera_Cls(_Idle_Camera_Cls):
    """A camera whose Capture fails but stays connected — a transient error."""

    def Capture(self):
        raise Camera_Error_Cls('capture timeout')


def _Window(tmp_path, camera=None):
    """A window with a real logger writing to tmp_path and a working idle camera."""
    os.makedirs(str(tmp_path), exist_ok=True)
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = AnyScan_Window_Cls(camera=camera or _Idle_Camera_Cls(), logger=logger)
    return window, logger


def _Objects():
    """Two objects: one scored (FastSAM), one unscored (background cue only)."""
    return [Detection_Str(Label='ring', Bbox=(1, 1, 4, 4), Sentence='A ring.',
                          Segmenter_Score=0.9, Cue='both'),
            Detection_Str(Label='nut', Bbox=(8, 8, 4, 4), Sentence='A nut.',
                          Segmenter_Score=None, Cue='background')]


def _Log_Text(logger) -> str:
    """The current log file content."""
    with open(logger.Path, 'r', encoding='utf-8') as handle:
        return handle.read()


def test_analysis_writes_a_capture_set_linked_by_id(qt_app, tmp_path) -> None:
    """
    Description:
        A completed analysis writes the four capture artefacts under logger/captures, and
        the analysis log lines carry the same set id so the log points at the files. The
        '.txt' is exactly the shared Screen-Understanding text the panel shows.
    """

    window, logger = _Window(tmp_path)
    setattr(window, CONST_MANGLE + '__frame', np.zeros((40, 60, 3), dtype=np.uint8))
    setattr(window, CONST_MANGLE + '__current_set_id', '20260912-143202_1')
    setattr(window, CONST_MANGLE + '__session_id', '20260912-143000_s1')
    objects = _Objects()
    result = Analysis_Str(Objects=objects, Background='A plain surface.', Latency_Ms=100,
                          Verdict='2 found', Verdict_Level='ok', Task='caption')

    _Private(window, '__On_Analysis_Finished')(result)
    logger.Close()

    session = tmp_path / 'captures' / '20260912-143000_s1'
    for suffix in ('_raw.png', '_annotated.png', '_mask.png', '_understanding.txt', '.txt'):
        assert (session / ('20260912-143202_1' + suffix)).exists()
    # The '_understanding.txt' is exactly the shared formatter's text (the panel's text).
    txt = (session / '20260912-143202_1_understanding.txt').read_text()
    assert txt.split('\n', 1)[1].rstrip('\n') == Screen_Understanding(objects, 'A plain surface.')

    content = _Log_Text(logger)
    # The set id links the log to the files, as prose on the started/finished lines.
    assert 'Capture set 20260912-143202_1.' in content
    assert 'finished in' in content
    assert 'Created the capture directory for connection 20260912-143000_s1.' in content
    assert 'Capture set 20260912-143202_1 written.' in content
    # The finished-analysis line carries the confidence coverage (1 of 2 scored).
    assert 'mean confidence' in content and 'over 1 of 2 scored' in content


def test_capture_write_failure_logs_error_and_does_not_raise(qt_app, tmp_path) -> None:
    """
    Description:
        Writing four files must never break the analysis: a write failure is caught,
        logged as an ERROR, and the UI carries on.
    """

    window, logger = _Window(tmp_path)
    setattr(window, CONST_MANGLE + '__frame', np.zeros((40, 60, 3), dtype=np.uint8))
    setattr(window, CONST_MANGLE + '__current_set_id', '20260912-143202_1')
    setattr(window, CONST_MANGLE + '__session_id', '20260912-143000_s1')

    class _Failing_Writer_Cls(object):
        """A capture writer whose Write always fails, to exercise the error path."""

        Retention = 50

        def Write(self, *args, **kwargs):
            raise OSError('disk full')

    setattr(window, CONST_MANGLE + '__capture_writer', _Failing_Writer_Cls())
    result = Analysis_Str(Objects=[], Background='A plain surface.', Latency_Ms=100,
                          Verdict='Empty', Verdict_Level='idle', Task='caption')

    _Private(window, '__On_Analysis_Finished')(result)   # must not raise
    logger.Close()
    assert '[ERROR  ] failed to write capture set 20260912-143202_1: disk full' in _Log_Text(logger)


def test_mid_analysis_failure_tags_the_error_and_writes_a_partial_set(qt_app, tmp_path) -> None:
    """
    Description:
        An error raised inside an analysis belongs to that analysis: the Log_Error carries
        the set id, and a PARTIAL capture (the raw frame plus a note) is written so the
        frame that caused the failure is on disk — the case where the link matters most.
        An error genuinely outside any analysis stays untagged.
    """

    window, logger = _Window(tmp_path)
    setattr(window, CONST_MANGLE + '__frame', np.zeros((40, 60, 3), dtype=np.uint8))
    setattr(window, CONST_MANGLE + '__current_set_id', '20260912-143202_1')
    setattr(window, CONST_MANGLE + '__session_id', '20260912-143000_s1')

    _Private(window, '__On_Analysis_Failed')('the segmenter failed to process the frame')
    logger.Close()

    content = _Log_Text(logger)
    # The failure error carries the set id.
    assert '[ERROR  ] the segmenter failed to process the frame (set=20260912-143202_1)' in content
    # A partial set is announced and the raw frame lands in the right session directory.
    assert '[WARNING] Wrote a partial capture set 20260912-143202_1 for the failed analysis. It holds the raw frame only.' in content
    session = tmp_path / 'captures' / '20260912-143000_s1'
    assert (session / '20260912-143202_1_raw.png').exists()
    txt = (session / '20260912-143202_1_understanding.txt').read_text()
    assert 'Analysis FAILED' in txt and 'partial capture' in txt
    # No annotated/mask/YOLO were rendered for a failed analysis.
    assert not (session / '20260912-143202_1_annotated.png').exists()
    assert not (session / '20260912-143202_1.txt').exists()


def test_reanalysis_in_flight_is_warned(qt_app, tmp_path) -> None:
    """
    Description:
        Pressing Analyze while an analysis is in flight is dropped, not queued, and the
        ignored press is recorded as a WARNING rather than passing silently.
    """

    window, logger = _Window(tmp_path)
    setattr(window, CONST_MANGLE + '__frame', np.zeros((40, 60, 3), dtype=np.uint8))
    setattr(window, CONST_MANGLE + '__worker_running', True)

    _Private(window, '__On_Analyze_Button_Clicked')()
    logger.Close()
    assert '[WARNING] Analyze was pressed while an analysis was already running. The request was ignored.' in _Log_Text(logger)


def test_each_session_gets_a_distinct_capture_id_across_reconnects(qt_app, tmp_path) -> None:
    """
    Description:
        The capture-session id matches the logger's session (its start plus index), so
        reconnecting in the same run yields a DISTINCT session — the second directory does
        not collide with the first, and ids stay distinguishable across sessions.
    """

    window, logger = _Window(tmp_path)
    camera = _Private(window, '__camera')

    camera.Connect()
    _Private(window, '__On_Connect_Finished')()
    first = _Private(window, '__session_id')

    _Private(window, '__On_Disconnect_Button_Clicked')()
    camera.Connect()
    _Private(window, '__On_Connect_Finished')()
    second = _Private(window, '__session_id')
    logger.Close()

    assert first is not None and second is not None and first != second
    assert first.endswith('_s1') and second.endswith('_s2')     # the logger's session index


def test_camera_events_reach_the_log_through_the_sink(qt_app, tmp_path) -> None:
    """
    Description:
        The Qt-free camera emits events through the injected sink, which the window routes
        to the logger by level — so a frame drop or a config note reaches the log without
        the camera holding the logger.
    """

    window, logger = _Window(tmp_path)
    camera = _Private(window, '__camera')
    # The camera's sink is wired to the window; emitting through it reaches the log.
    camera._Log('WARNING', '3 frame(s) dropped during capture (retried)')
    camera._Log('INFO', 'camera configuration loaded')
    logger.Close()

    content = _Log_Text(logger)
    assert '[WARNING] 3 frame(s) dropped during capture (retried)' in content
    assert '[INFO   ] camera configuration loaded' in content


def test_mid_session_connection_loss_is_an_error(qt_app, tmp_path) -> None:
    """
    Description:
        A capture that fails AND leaves the camera disconnected is a mid-session
        connection LOSS (ERROR), distinct from a transient capture failure while still
        connected (a tracked ERROR a later scan can resolve).
    """

    window, logger = _Window(tmp_path, camera=_Lost_Camera_Cls())
    _Private(window, '__camera').Connect()
    _Private(window, '__On_Scan_Button_Clicked')()
    logger.Close()
    assert '[ERROR  ] The camera connection was lost' in _Log_Text(logger)

    window2, logger2 = _Window(tmp_path / 'b', camera=_Transient_Camera_Cls())
    _Private(window2, '__camera').Connect()
    _Private(window2, '__On_Scan_Button_Clicked')()
    logger2.Close()
    content = _Log_Text(logger2)
    assert 'The camera connection was lost' not in content
    assert '[ERROR  ] capture timeout (error_id=' in content
