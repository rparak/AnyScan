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
# File Name: ../test/UI/test_station_event_paths.py
## =========================================================================== ##

# System (Default)
import os
import time
import importlib.util
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
import dataclasses
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QTextDocument
from PyQt5.QtWidgets import QApplication, QLabel
# Custom Lib.: AnyScan UI — the main window under test
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan domain — the camera, the logger, the export, the configuration
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Logger/Station_Events
from Logger.Station_Events import Export_Pending
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE, CONST_PROJECT_ROOT

"""
Description:
    Every way the application ends a camera connection reaches the station event file — through the
    window's real handlers and the launcher's real export wiring (App/run.py, Export_Station_Events),
    read back from the files on disk: closing while connected, and a CONNECT that fails (which writes
    nothing). And a failure
    exporting an earlier log at startup reaches the status strip as a logged error.
"""
# The shipped configuration, unscaled.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope='module')
def run() -> tp.Any:
    """The launcher module (App/run.py), whose Export_Station_Events wires the export."""
    spec = importlib.util.spec_from_file_location('anyscan_run', os.path.join(CONST_PROJECT_ROOT, 'App', 'run.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Vision_Cls(object):
    """A stand-in backend with its models loaded (CONNECT needs them), never asked to analyse."""

    Name, Models_Loaded, Model_Names = 'JIC_AnyScan_All_v1', True, ('FastSAM-x.pt', 'gemma')


def _Private(window: AnyScan_Window_Cls, name: str) -> tp.Any:
    """A name-mangled private attribute of the window."""
    return getattr(window, '_AnyScan_Window_Cls' + name)


def _Pump_Until(condition: tp.Callable[[], bool], timeout: float = 5.0) -> None:
    """Run the event loop until the condition holds (or the timeout passes)."""
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        QApplication.instance().processEvents()
        time.sleep(0.01)


def _Station(tmp_path: tp.Any, run: tp.Any, frame: str) -> tp.Tuple[AnyScan_Window_Cls, Session_Logger_Cls, str]:
    """
    A window started as the launcher starts it: a real logger, a file camera on the given frame, and the
    station event export wired by run.Export_Station_Events into tmp_path/events.
    """
    events = tmp_path / 'events'
    events.mkdir()
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path / 'log'), install_handlers=False)
    configuration = dataclasses.replace(CONST_CONFIGURATION, Station_Events_Directory=str(events))
    window = AnyScan_Window_Cls(Configuration_Str=configuration, camera=File_Camera_Cls(frame), logger=logger)
    setattr(window, '_AnyScan_Window_Cls__vision', _Vision_Cls())
    run.Export_Station_Events(logger, window, str(events))
    _Private(window, '__Sync_Controls')()
    return window, logger, str(events)


def _Connect(window: AnyScan_Window_Cls) -> None:
    """CONNECT the way the operator does — the button and its worker — and wait for it to end."""
    _Private(window, '__button_connect').click()
    _Pump_Until(lambda: not _Private(window, '__worker_running'))


def _Exported(events: str) -> tp.List[str]:
    """The event types in the daily files, oldest file first, as written."""
    rows = []
    for name in sorted(os.listdir(events)):
        with open(os.path.join(events, name), 'r', encoding='utf-8') as handle:
            rows += [line.split(',')[1] for line in handle.read().splitlines()[1:]]
    return rows


def _Cell_Text(window: AnyScan_Window_Cls, name: str) -> str:
    """A status cell's value as it renders (rich text rendered to plain)."""
    cell = getattr(_Private(window, '__status'), name)
    value = [label for label in cell.findChildren(QLabel) if label.text().upper() != name.upper()][0]
    document = QTextDocument()
    document.setHtml(value.text())
    return ' '.join(document.toPlainText().replace('\xa0', ' ').split())


def test_closing_the_window_while_connected_writes_cycle_done_before_station_off(qt_app, run, tmp_path,
                                                                                reference_background_path) -> None:
    """
    Description:
        The operator closes the application with the camera still connected: the window's close ends the
        run, and the export written at that close pairs every CYCLE_START — CYCLE_DONE, then STATION_OFF.
    """

    window, logger, events = _Station(tmp_path, run, reference_background_path)
    _Connect(window)
    assert _Private(window, '__camera').Connected
    window.close()
    assert _Exported(events) == ['STATION_ON', 'CYCLE_START', 'CYCLE_DONE', 'STATION_OFF']


def test_a_failed_connect_writes_no_cycle(qt_app, run, tmp_path) -> None:
    """
    Description:
        A CONNECT that fails started nothing: the attempt and its error are logged, but no CYCLE_START
        is written, so there is no CYCLE_DONE to pair.
    """

    window, logger, events = _Station(tmp_path, run, str(tmp_path / 'no_such_frame.png'))
    _Connect(window)
    assert not _Private(window, '__camera').Connected
    window.close()
    with open(logger.Path, 'r', encoding='utf-8') as handle:
        assert 'Connecting to the camera.' in handle.read()
    assert _Exported(events) == ['STATION_ON', 'STATION_OFF']


def test_a_failure_exporting_an_earlier_log_at_startup_is_a_logged_error_on_the_strip(qt_app, run, tmp_path,
                                                                                     reference_background_path) -> None:
    """
    Description:
        An earlier run crashed, and at this start its export fails (here the log cannot be read): the
        failure is logged as an ERROR in this run's log and counted in the System cell, and the crashed
        log stays out of the ledger for the next start to retry.
    """

    log_dir = tmp_path / 'log'
    log_dir.mkdir()
    Export_Pending(str(log_dir), str(log_dir), '')                     # a ledger already exists
    crashed = Session_Logger_Cls(config_path=None, log_dir=str(log_dir), install_handlers=False)
    getattr(crashed, '_Session_Logger_Cls__file').close()              # the process died
    os.chmod(crashed.Path, 0o000)
    try:
        window, logger, events = _Station(tmp_path, run, reference_background_path)
    finally:
        os.chmod(crashed.Path, 0o644)
    assert _Cell_Text(window, 'system') == '● Error logged'
    with open(logger.Path, 'r', encoding='utf-8') as handle:
        log = handle.read()
    assert '[ERROR  ] The station events of %s could not be exported' % os.path.basename(crashed.Path) in log
    window.close()
    with open(os.path.join(str(log_dir), 'station_events_exported.txt'), 'r', encoding='utf-8') as ledger:
        assert ledger.read().split() == [os.path.basename(logger.Path)]
