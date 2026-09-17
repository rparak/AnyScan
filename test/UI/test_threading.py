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
# File Name: ../test/UI/test_threading.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import threading
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
#   ../Vision/Core
from Vision.Core import Vision_Backend_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str

"""
Description:
    Headless (offscreen) tests for the Qt threading path — the place a
    'QThread: Destroyed while thread is still running' regression would appear and
    nothing else catches. The workers are exercised on real QThreads with the queued
    cross-thread signal handoff, and the window's closeEvent teardown is exercised
    while an analysis is still running. No camera and no model weights are needed.
"""

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
        return Analysis_Str(Summary='off-thread ok', Objects=[], Verdict='Empty',
                            Verdict_Level='idle', Task='rec')


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
        return Analysis_Str(Summary='blocked', Objects=[], Verdict='Empty',
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
    assert captured['result'].Summary == 'off-thread ok'
    # The queued cross-thread signals were delivered, in order.
    assert captured['progress'] == [(0, 1), (1, 1)]
    assert captured['stages'] == ['working']
    # Analyze ran on the worker thread, not the GUI thread.
    assert vision.ran_on is not None
    assert vision.ran_on != threading.current_thread().name


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


def test_closeevent_stops_a_running_analysis_thread(qt_app, reference_background_path) -> None:
    """
    Description:
        Closing the window while an analysis is running must quit() and wait() on the
        worker thread (closeEvent), not tear the QThread down mid-run. Guarded by
        capturing Qt's own log: the 'Destroyed while thread is still running' message
        must never appear.
    """

    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
    # Inject a blocking backend and a frame so an analysis genuinely starts and runs.
    setattr(window, CONST_MANGLE + '__vision', _Blocking_Vision_Cls(0.3))
    camera = _Private(window, '__camera')
    camera.Connect()
    setattr(window, CONST_MANGLE + '__frame', camera.Capture())

    messages = []
    qInstallMessageHandler(lambda mode, ctx, message: messages.append(message))
    thread = None
    try:
        # Start the analysis (real QThread + Analysis_Worker_Cls).
        _Private(window, '__On_Analyze_Button_Clicked')()
        # Let the worker thread enter Analyze (the blocking sleep).
        qt_app.processEvents()
        time.sleep(0.05)
        qt_app.processEvents()
        thread = _Private(window, '__thread')
        assert thread is not None and thread.isRunning(), 'the analysis thread is not running'

        # Close while it runs. The primary guard: closeEvent must quit() and wait()
        # the thread, so it is no longer running once close() returns. If the wait
        # were removed this stays True and the test fails.
        window.close()
        assert not thread.isRunning(), 'closeEvent returned while the worker thread was still running'

        # Flush the finished signal that was queued during the wait.
        qt_app.processEvents()
    finally:
        qInstallMessageHandler(None)
        # Belt and braces: never leave a thread running if an assert failed above.
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(2000)

    # Secondary guard: Qt never logged a destroyed-while-running warning.
    assert not any('Destroyed while thread is still running' in m for m in messages), messages


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

    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
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

    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
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
