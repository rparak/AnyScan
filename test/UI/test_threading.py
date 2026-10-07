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
# File Name: ../test/UI/test_threading.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import re
import sys
import glob
import time
import threading
import subprocess
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QThread, QEventLoop, QTimer, qInstallMessageHandler
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the workers and the window
#   ../UI/Workers
from UI.Workers import Analysis_Worker_Cls, Connect_Worker_Cls
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan domain — the camera, the vision interface, the result
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Logger/Station_Events
from Logger.Station_Events import Read_Events
#   ../Vision/Core
from Vision.Core import Vision_Backend_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str, Detection_Str
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Headless (offscreen) tests for the Qt threading path — the place a
    'QThread: Destroyed while thread is still running' regression would appear and
    nothing else catches. The workers are exercised on real QThreads with the queued
    cross-thread signal handoff, and the window's closeEvent teardown is exercised
    while an analysis is still running. No camera and no model weights are needed.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


class _Recording_Vision_Cls(Vision_Backend_Cls):
    """A vision backend that records the thread it ran on and drives the callbacks."""

    Name = 'Recording'

    def __init__(self) -> None:
        super().__init__()
        self.ran_on = None

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        self.ran_on = threading.current_thread().name
        if stage_cb:
            stage_cb('working')
        if progress_cb:
            progress_cb(0, 1)
            progress_cb(1, 1)
        return Analysis_Str(Objects=[], Verdict='Empty',
                            Verdict_Level='idle', Task='rec')


class _Loaded_Vision_Cls(_Recording_Vision_Cls):
    """
    A recording backend with its models loaded (CONNECT needs them), whose analysis ends as `end` says:
    'finish', 'fail' (Analyze raises), or 'stop' (it waits for `go`, then reports progress before its first
    object, which is where a requested stop takes effect).
    """

    def __init__(self, end: str = 'finish') -> None:
        super().__init__()
        self.Models_Loaded, self.end = True, end
        self.go = threading.Event()

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        if self.end == 'fail':
            raise RuntimeError('The segmenter failed to process the frame.')
        if self.end == 'stop':
            self.go.wait(5)
            progress_cb(0, 2)
        return super().Analyze(image, progress_cb, stage_cb)


class _Blocking_Vision_Cls(Vision_Backend_Cls):
    """A vision backend that blocks, so a worker is still running when the window closes."""

    Name = 'Blocking'

    def __init__(self, seconds: float) -> None:
        super().__init__()
        self.__seconds = seconds
        self.calls = 0

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        self.calls += 1
        time.sleep(self.__seconds)
        return Analysis_Str(Objects=[], Verdict='Empty',
                            Verdict_Level='idle', Task='block')


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def test_analysis_worker_runs_off_thread(qt_app) -> None:
    """
    Description:
        Analysis_Worker_Cls, moved onto a real QThread and started, runs Analyze off
        the GUI thread and hands the result and progress back through queued signals,
        in order.
    """

    vision = _Recording_Vision_Cls()
    thread = QThread()
    worker = Analysis_Worker_Cls(vision, np.zeros((16, 16, 3), dtype=np.uint8))
    worker.moveToThread(thread)

    captured = {'progress': [], 'stages': [], 'result': None, 'failed': None}
    worker.Progress_Changed.connect(lambda d, t: captured['progress'].append((d, t)))
    worker.Stage_Changed.connect(lambda s: captured['stages'].append(s))
    worker.Analysis_Finished.connect(lambda r: captured.__setitem__('result', r))
    worker.Analysis_Failed.connect(lambda m: captured.__setitem__('failed', m))
    thread.started.connect(worker.Run)

    loop = QEventLoop()
    worker.Analysis_Finished.connect(loop.quit)
    worker.Analysis_Failed.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)   # safety timeout
    thread.start()
    loop.exec_()
    thread.quit()
    assert thread.wait(2000)

    assert captured['failed'] is None
    assert isinstance(captured['result'], Analysis_Str)
    assert captured['result'].Task == 'rec'
    # The queued cross-thread signals were delivered, in order.
    assert captured['progress'] == [(0, 1), (1, 1)]
    assert captured['stages'] == ['working']
    # Analyze ran on the worker thread, not the GUI thread.
    assert vision.ran_on is not None
    assert vision.ran_on != threading.current_thread().name


def test_detection_verdict_survives_the_worker_boundary(qt_app) -> None:
    """
    Description:
        The new per-object Verdict must cross the worker->GUI thread handoff intact. A
        verdict that silently reset to OK is the worst failure for this field, so a
        backend returning a NOK detection is run on a real QThread and the delivered
        result must still carry Verdict == 'NOK' (and an OK one stays OK).
    """

    class _Verdict_Vision_Cls(Vision_Backend_Cls):
        """A backend returning one NOK and one OK detection."""

        Name = 'Verdict'

        def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
            return Analysis_Str(Objects=[
                Detection_Str(Label='a', Bbox=(0, 0, 4, 4), Verdict='NOK'),
                Detection_Str(Label='b', Bbox=(4, 4, 4, 4), Verdict='OK')],
                Verdict='2 found', Verdict_Level='ok', Task='v')

    thread = QThread()
    worker = Analysis_Worker_Cls(_Verdict_Vision_Cls(), np.zeros((8, 8, 3), dtype=np.uint8))
    worker.moveToThread(thread)
    captured = {'result': None}
    worker.Analysis_Finished.connect(lambda r: captured.__setitem__('result', r))
    thread.started.connect(worker.Run)

    loop = QEventLoop()
    worker.Analysis_Finished.connect(loop.quit)
    worker.Analysis_Failed.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    thread.start()
    loop.exec_()
    thread.quit()
    assert thread.wait(2000)

    result = captured['result']
    assert result is not None
    # The verdicts crossed the thread intact — not dropped, not defaulted back to OK.
    assert [det.Verdict for det in result.Objects] == ['NOK', 'OK']


def test_connect_worker_runs_off_thread(qt_app, reference_background_path) -> None:
    """
    Description:
        Connect_Worker_Cls opens a File_Camera_Cls off the GUI thread and reports
        Connect_Finished through a queued signal.
    """

    thread = QThread()
    worker = Connect_Worker_Cls(File_Camera_Cls(reference_background_path))
    worker.moveToThread(thread)

    outcome = {'finished': False, 'failed': None}
    worker.Connect_Finished.connect(lambda: outcome.__setitem__('finished', True))
    worker.Connect_Failed.connect(lambda m: outcome.__setitem__('failed', m))
    thread.started.connect(worker.Run)

    loop = QEventLoop()
    worker.Connect_Finished.connect(loop.quit)
    worker.Connect_Failed.connect(loop.quit)
    QTimer.singleShot(5000, loop.quit)
    thread.start()
    loop.exec_()
    thread.quit()
    assert thread.wait(2000)

    assert outcome['failed'] is None
    assert outcome['finished']


class _Object_Vision_Cls(Vision_Backend_Cls):
    """
    A backend that describes `total` objects of `seconds` each, calling the progress hook before each
    one as the real pipeline does, and records how many it described and whether Analyze returned.
    """

    Name, Models_Loaded = 'Objects', True

    def __init__(self, total: int, seconds: float) -> None:
        super().__init__()
        self.total, self.seconds, self.described = total, seconds, 0
        self.returned = threading.Event()

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        for i in range(self.total):
            if progress_cb:
                progress_cb(i, self.total)
            time.sleep(self.seconds)
            self.described += 1
        if progress_cb:
            progress_cb(self.total, self.total)
        self.returned.set()
        return Analysis_Str(Objects=[], Verdict='Empty', Verdict_Level='idle', Task='objects')


class _Slow_Camera_Cls(File_Camera_Cls):
    """A file camera whose CONNECT blocks until `answer` is set — a Basler handshake that takes its time."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.answer = threading.Event()

    def _Open(self) -> None:
        self.answer.wait()
        super()._Open()


def _Logged_Window(tmp_path, vision, camera) -> tp.Tuple[AnyScan_Window_Cls, Session_Logger_Cls, tp.List[str]]:
    """A shown window with a real logger in tmp_path, the given backend and camera; the close callback's calls."""
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    exported = []
    logger.Set_Close_Callback(exported.append)
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=camera, logger=logger)
    setattr(window, CONST_MANGLE + '__vision', vision)
    _Private(window, '__Sync_Controls')()
    window.show()
    return window, logger, exported


def _Pump(qt_app, condition, seconds: float = 5.0) -> None:
    """Run the event loop until the condition holds (or the time passes)."""
    deadline = time.time() + seconds
    while not condition() and time.time() < deadline:
        qt_app.processEvents()
        time.sleep(0.005)


def test_closing_during_an_analysis_stops_it_before_its_next_object_then_closes(qt_app, tmp_path,
                                                                               reference_background_path) -> None:
    """
    Description:
        A close during an eight-object analysis does not block and does not leave the thread running:
        the window stays open saying it is stopping, the analysis stops before its next object, and only
        then does the window close — the thread ended, Qt never logging 'Destroyed while thread is still
        running'. The log says how far it got on a line that ends its cycle, a partial capture set (the
        raw frame and a note) is written, and the close then runs the logger's close: the export runs
        once, and the daily events pair the cycle before STATION_OFF.
    """

    vision = _Object_Vision_Cls(total=8, seconds=0.2)
    window, logger, exported = _Logged_Window(tmp_path, vision, File_Camera_Cls(reference_background_path))
    messages = []
    qInstallMessageHandler(lambda mode, ctx, message: messages.append(message))
    try:
        _Private(window, '__button_connect').click()
        _Pump(qt_app, lambda: not _Private(window, '__worker_running'))
        _Private(window, '__button_scan').click()
        _Private(window, '__button_analyze').click()
        thread = _Private(window, '__thread')
        _Pump(qt_app, lambda: vision.described >= 1)
        window.close()
        assert window.isVisible() and thread.isRunning(), 'the close did not wait for the analysis'
        # While the object under way finishes (0.2 s), the worker's own progress and stage reports do not
        # replace the line saying the window is stopping. Emitted here, on the GUI thread, they reach the
        # window's slots directly. (The text the viewport holds: the overlay is painted, and nothing reads
        # painted text back.)
        worker = _Private(window, '__worker')
        worker.Progress_Changed.emit(2, 8)
        worker.Stage_Changed.emit('Describing…')
        assert getattr(_Private(window, '__viewport'), '_Viewport_Cls__busy_text').startswith('Stopping the analysis')
        _Pump(qt_app, lambda: not window.isVisible())
        assert not window.isVisible() and thread.isFinished()
    finally:
        qInstallMessageHandler(None)
    assert not vision.returned.is_set() and vision.described < 8
    assert not any('Destroyed while thread is still running' in message for message in messages), messages
    log = open(logger.Path, encoding='utf-8').read()
    assert re.search(r'Analysis 1 stopped at close after %d of 8 objects\. Capture set \S+\. #analysis-end'
                     % vision.described, log)
    assert exported == [logger.Path] and log.rstrip().endswith('Application stopped. #run-stop')
    assert [event.Event_Type for event in Read_Events(logger.Path)] == ['STATION_ON', 'CYCLE_START', 'CYCLE_DONE',
                                                                        'STATION_OFF']
    (note,) = glob.glob(os.path.join(str(tmp_path), 'captures', '*', '*_understanding.txt'))
    assert 'Analysis STOPPED at close after %d of 8 objects' % vision.described in open(note, encoding='utf-8').read()
    assert glob.glob(os.path.join(str(tmp_path), 'captures', '*', '*_raw.png'))


def test_a_close_arriving_as_the_analysis_finishes_closes_once_with_the_whole_result(qt_app, tmp_path,
                                                                                      reference_background_path) -> None:
    """
    Description:
        The analysis has finished on its thread but its result has not reached the window when the close
        arrives: the stop request finds nothing left to stop, the result is taken in full (the finished
        line, not a stopped one), and the window closes exactly once — one export, one 'Application
        stopped'.
    """

    vision = _Object_Vision_Cls(total=2, seconds=0.0)
    window, logger, exported = _Logged_Window(tmp_path, vision, File_Camera_Cls(reference_background_path))
    _Private(window, '__button_connect').click()
    _Pump(qt_app, lambda: not _Private(window, '__worker_running'))
    _Private(window, '__button_scan').click()
    _Private(window, '__button_analyze').click()
    assert vision.returned.wait(5)
    window.close()                                         # the result is still queued
    assert window.isVisible()
    _Pump(qt_app, lambda: not window.isVisible())
    log = open(logger.Path, encoding='utf-8').read()
    assert 'Analysis 1 finished in ' in log and 'stopped at close' not in log
    assert exported == [logger.Path] and log.count('Application stopped.') == 1


def test_closing_while_connecting_waits_for_the_camera_then_closes(qt_app, tmp_path, reference_background_path) -> None:
    """
    Description:
        A CONNECT cannot be interrupted, so a close during it waits: the window stays open saying it
        closes when the camera answers, and closes once the CONNECT has ended — its thread finished, the
        export run once.
    """

    camera = _Slow_Camera_Cls(reference_background_path)
    window, logger, exported = _Logged_Window(tmp_path, _Object_Vision_Cls(total=1, seconds=0.0), camera)
    _Private(window, '__button_connect').click()
    thread = _Private(window, '__conn_thread')
    window.close()
    _Pump(qt_app, lambda: False, seconds=0.3)
    assert window.isVisible() and thread.isRunning()
    assert 'Close requested while connecting to the camera' in open(logger.Path, encoding='utf-8').read()
    camera.answer.set()
    _Pump(qt_app, lambda: not window.isVisible())
    assert not window.isVisible() and thread.isFinished() and exported == [logger.Path]


# The application as the launcher runs it, in its own interpreter: a window with a real logger whose
# close callback prints, closed during an analysis or a CONNECT. argv: repository root, log directory,
# frame, case ('analysis', 'connect twice', 'connect timeout').
CONST_CLOSE_SCRIPT = r"""
import os, sys, time, threading, dataclasses
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
root, log_dir, frame, case = sys.argv[1:5]
sys.path[:0] = [os.path.join(root, 'src')]
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from UI.Core import AnyScan_Window_Cls
from Camera.Core import File_Camera_Cls
from Logger.Core import Session_Logger_Cls
from Vision.Core import Vision_Backend_Cls
from Parameters.Vision import Analysis_Str
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

class Vision(Vision_Backend_Cls):
    Name, Models_Loaded = 'Objects', True
    def Analyze(self, image, progress_cb=None, stage_cb=None):
        for i in range(8):
            progress_cb(i, 8)
            time.sleep(0.5)
        return Analysis_Str(Objects=[], Verdict='Empty', Verdict_Level='idle', Task='objects')

class Hung_Camera(File_Camera_Cls):
    def _Open(self):
        threading.Event().wait()                     # the camera never answers

if case == 'connect timeout':
    AnyScan_Window_Cls.CONST_CLOSE_ESCAPE_MS = 500
app = QApplication([])
logger = Session_Logger_Cls(config_path=None, log_dir=log_dir, install_handlers=False)
logger.Set_Close_Callback(lambda path: print('exported', flush=True))
config = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
camera = File_Camera_Cls(frame) if case == 'analysis' else Hung_Camera(frame)
window = AnyScan_Window_Cls(Configuration_Str=config, camera=camera, logger=logger)
setattr(window, '_AnyScan_Window_Cls__vision', Vision())
window.show()
press = lambda name: getattr(window, '_AnyScan_Window_Cls__button_' + name).click()
if case == 'analysis':
    camera.Connect()
    window._AnyScan_Window_Cls__frame = camera.Capture()
    window._AnyScan_Window_Cls__Sync_Controls()
    press('analyze')
    QTimer.singleShot(700, window.close)
else:
    window._AnyScan_Window_Cls__Sync_Controls()
    press('connect')
    QTimer.singleShot(200, window.close)
    if case == 'connect twice':
        QTimer.singleShot(400, window.close)
try:
    app.exec_()
finally:
    logger.Close()
print('left the event loop', flush=True)
"""


@pytest.mark.parametrize('case', ['analysis', 'connect twice', 'connect timeout'])
def test_closing_never_destroys_a_running_thread_and_exits_cleanly(tmp_path, reference_background_path, case) -> None:
    """
    Description:
        The application in its own interpreter, as the launcher runs it — the abort happens at exit, so
        only the process's exit status shows it. Closed during an analysis, it stops the analysis and
        leaves the event loop normally. Closed during a CONNECT whose camera never answers — a second
        close, or the escape's bound passing — it exits at once without the hung thread (the CONNECT
        escape): the warning says so, the CSV row and the export are written first, and no thread is
        destroyed. Every case exits 0, never with Qt's 'Destroyed while thread is still running' abort.
    """

    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    script = tmp_path / 'close.py'
    script.write_text(CONST_CLOSE_SCRIPT)
    started = time.time()
    run = subprocess.run([sys.executable, str(script), root, str(tmp_path / 'log'), reference_background_path, case],
                         capture_output=True, text=True, timeout=60, cwd=str(tmp_path))
    assert 'Destroyed while thread is still running' not in run.stderr, run.stderr
    assert run.returncode == 0, (run.returncode, run.stderr[-2000:])
    assert run.stdout.split().count('exported') == 1
    (log,) = glob.glob(str(tmp_path / 'log' / 'log_*.txt'))
    text = open(log, encoding='utf-8').read()
    assert text.rstrip().endswith('Application stopped. #run-stop')
    with open(glob.glob(str(tmp_path / 'log' / '*.csv'))[0], encoding='utf-8-sig') as summary:
        assert len(summary.read().splitlines()) == 2                        # the header and this run's row
    if case == 'analysis':
        assert 'left the event loop' in run.stdout and 'stopped at close after ' in text
        assert time.time() - started < 20
    else:
        reason = 'close was requested again' if case == 'connect twice' else 'it had not ended 0.5 s after'
        assert '[WARNING] Closing without waiting for the camera connection: %s' % reason in text
        assert 'left the event loop' not in run.stdout                     # exited from the escape


@pytest.mark.parametrize('slot, frame, end', [('__On_Connect_Finished', 'reference', 'finish'),
                                              ('__On_Connect_Failed', 'missing', 'finish'),
                                              ('__On_Analysis_Finished', 'reference', 'finish'),
                                              ('__On_Analysis_Failed', 'reference', 'fail'),
                                              ('__On_Analysis_Stopped', 'reference', 'stop')],
                         ids=['connect finished', 'connect failed', 'analysis finished', 'analysis failed',
                              'analysis stopped'])
def test_a_workers_thread_has_ended_when_the_window_has_taken_its_result(qt_app, monkeypatch, tmp_path,
                                                                        reference_background_path, slot, frame,
                                                                        end) -> None:
    """
    Description:
        The slot that takes a worker's result joins the worker's thread before it lets the worker go
        (UI.Workers.Join_Worker_Thread), so the thread has ENDED when the slot returns. Without the join
        the thread is still running then — its quit is queued behind the slot — and letting the worker go
        makes PyQt delete it on that thread, concurrently with the GUI thread: the deadlock the UI suite
        hung on about once in thirty runs (the worker thread waiting for the GIL under a Qt lock, the GUI
        thread holding the GIL and waiting for that lock in a setStyleSheet). Checked for both ends of
        CONNECT and every end of an analysis: finished, failed, and stopped (the close's stop).
    """

    path = reference_background_path if frame == 'reference' else str(tmp_path / 'no_such_frame.png')
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(path))
    vision = _Loaded_Vision_Cls(end)
    setattr(window, CONST_MANGLE + '__vision', vision)
    seen = {'thread': None, 'running after the slot': []}
    original = getattr(AnyScan_Window_Cls, CONST_MANGLE + slot)

    def _Observed(self, *args) -> None:
        original(self, *args)
        seen['running after the slot'].append(seen['thread'].isRunning())

    monkeypatch.setattr(AnyScan_Window_Cls, CONST_MANGLE + slot, _Observed)
    if slot.startswith('__On_Connect'):
        _Private(window, '__On_Connect_Button_Clicked')()
        seen['thread'] = _Private(window, '__conn_thread')
    else:
        camera = _Private(window, '__camera')
        camera.Connect()
        setattr(window, CONST_MANGLE + '__frame', camera.Capture())
        _Private(window, '__On_Analyze_Button_Clicked')()
        seen['thread'] = _Private(window, '__thread')
        if end == 'stop':
            _Private(window, '__worker').Request_Stop()
            vision.go.set()
    deadline = time.time() + 5
    while not seen['running after the slot'] and time.time() < deadline:
        qt_app.processEvents()
        time.sleep(0.005)
    window.close()
    assert seen['running after the slot'] == [False]


def _Wait_Idle(qt_app, window, seconds: float = 3.0) -> None:
    """Pump the GUI event loop until the analysis worker is no longer running."""
    deadline = time.time() + seconds
    while _Private(window, '__worker_running') and time.time() < deadline:
        qt_app.processEvents()
        time.sleep(0.01)
    qt_app.processEvents()


def test_view_toggle_available_only_after_the_worker_delivers(qt_app, reference_background_path) -> None:
    """
    Description:
        The §2b threading contract: while the analysis runs off the GUI thread the toggle
        is not available (the previous run's renders are dropped on start), and it becomes
        available only once the completion slot has delivered both renders on the UI
        thread — never mid-flight.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    setattr(window, CONST_MANGLE + '__vision', _Blocking_Vision_Cls(0.2))
    camera = _Private(window, '__camera')
    camera.Connect()
    setattr(window, CONST_MANGLE + '__frame', camera.Capture())
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')

    _Private(window, '__On_Analyze_Button_Clicked')()
    qt_app.processEvents()
    time.sleep(0.05)
    qt_app.processEvents()

    # Mid-run: the worker has not delivered, so there is nothing to toggle.
    assert _Private(window, '__worker_running')
    assert not viewport.Has_Views()
    assert not toggle.isEnabled()

    _Wait_Idle(qt_app, window)

    # Delivered on the UI thread: both renders are held and the toggle is available.
    assert not _Private(window, '__worker_running')
    assert viewport.Has_Views()
    assert toggle.isEnabled() and not toggle.isHidden()


def test_two_analyses_in_quick_succession_do_not_mix(qt_app, reference_background_path) -> None:
    """
    Description:
        Pressing Analyze twice in quick succession must not leave the view showing a mix
        of two runs. The second press, arriving while the first run is still off-thread,
        is ignored (a single run is serviced), so both held renders come from one run.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    vision = _Blocking_Vision_Cls(0.2)
    setattr(window, CONST_MANGLE + '__vision', vision)
    camera = _Private(window, '__camera')
    camera.Connect()
    setattr(window, CONST_MANGLE + '__frame', camera.Capture())
    viewport = _Private(window, '__viewport')

    _Private(window, '__On_Analyze_Button_Clicked')()   # run 1 starts, off-thread
    qt_app.processEvents()
    time.sleep(0.03)
    _Private(window, '__On_Analyze_Button_Clicked')()   # second press while run 1 runs
    qt_app.processEvents()

    _Wait_Idle(qt_app, window)

    # Only one run was serviced — the second press could not start a concurrent run — so
    # the annotated and mask renders both come from that one run.
    assert vision.calls == 1
    assert viewport.Has_Views()
