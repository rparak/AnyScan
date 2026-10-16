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
# File Name: ../UI/Workers.py
## =========================================================================== ##

# System (Default)
import time
import threading
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QObject, pyqtSignal
# Custom Lib.: AnyScan — the scan's refusal for a moving scene, told apart from a capture failure
#   ../Camera/Core
from Camera.Core import Camera_Motion_Error_Cls

"""
Description:
    The off-thread workers. Long-running work (model inference, a model load, a Basler
    handshake, a scan waiting for a still scene, the live preview's frames) never runs on the GUI thread;
    each worker is moved onto a QThread owned by the window and reports back only through signals. The window quits and
    waits on the thread once a worker's terminal signal fires (Join_Worker_Thread), then
    deletes both.
"""


class Analysis_Stopped_Error_Cls(Exception):
    """
    Description:
        Raised from the analysis worker's progress hook, before the next object, once a stop was
        requested (Analysis_Worker_Cls.Request_Stop). It ends Analyze where it is; the worker reports
        Analysis_Stopped. Never shown to the operator: the stop is the close they asked for.
    """


def Join_Worker_Thread(thread: tp.Any) -> None:
    """
    Description:
        Quit a worker's thread and wait until it has ended — called by the slot that receives
        the worker's terminal signal, BEFORE it drops its references to the worker and the thread.

        The worker lives on that thread, so dropping its last Python reference while the thread
        still runs makes PyQt delete it there (deleteLater), concurrently with the GUI thread.
        That deletion calls PyQt's QThread.disconnectNotify under a Qt signal-slot lock and waits
        for the GIL; the GUI thread holds the GIL and, in the same slot, makes Qt connections
        (a setStyleSheet) that wait for that lock — a deadlock, caught in the test suite as a
        hang about once in thirty runs. QThread.wait releases the GIL, so the thread finishes its
        own clean-up (the worker's deleteLater from 'finished') while the GUI thread is parked,
        and afterwards nothing is destroyed off the GUI thread. The quit is already queued by the
        terminal signal; the wait is the worker returning from Run, so it does not hold the GUI.

    Args:
        (1) thread [QThread(object)]: The worker's thread, or None when there is none.
    """

    if thread is not None:
        thread.quit()
        thread.wait()


class Analysis_Worker_Cls(QObject):
    """
    Description:
        Runs one analysis off the GUI thread. The vision pipeline takes seconds;
        on the GUI thread it would freeze the window and the busy animation with it.
        Moved onto a QThread, it reports progress per crop and hands back the
        finished Analysis_Str — or a failure sentence — through queued signals. It
        never touches a widget directly.

    Initialization of the Class:
        Args:
            (1) vision [Vision_Backend_Cls(object)]: The vision backend.
            (2) image [Matrix<uint8> HxWx3]: The captured frame (RGB ndarray).

        Example:
            Initialization:
                # Assignment of the variables.
                thread = QThread()

                # Initialization of the class.
                Cls = Analysis_Worker_Cls(vision, image_rgb)
                Cls.moveToThread(thread)
                thread.started.connect(Cls.Run)

            Features:
                # Signals of the class.
                Cls.Stage_Changed; Cls.Progress_Changed
                Cls.Analysis_Finished; Cls.Analysis_Failed; Cls.Analysis_Stopped

                # Functions of the class.
                Cls.Run(); Cls.Request_Stop()
    """

    # << SIGNALS >> #
    Stage_Changed = pyqtSignal(str)          # phase text: 'Loading model…', 'Segmenting…'
    Progress_Changed = pyqtSignal(int, int)  # (objects done, total)
    Analysis_Finished = pyqtSignal(object)   # the Analysis_Str
    Analysis_Failed = pyqtSignal(str)        # an actionable sentence for the panel
    Analysis_Stopped = pyqtSignal(int, int)  # stopped on request: (objects described, total)

    def __init__(self, vision: tp.Any, image: tp.List[tp.List[int]]) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__vision = vision
        self.__image = image
        # Set from the GUI thread by Request_Stop, read on the worker thread before each object.
        self.__stop = threading.Event()

    def Request_Stop(self) -> None:
        """
        Description:
            Ask the running analysis to stop before its next object (the window's close). Called
            directly from the GUI thread — the worker's own thread is busy in Analyze, so a queued
            call would arrive only after it. The object being described, or the segmentation before
            the first object, is finished first: neither can be interrupted.
        """

        self.__stop.set()

    def __Progress(self, done: int, total: int) -> None:
        """
        Description:
            The pipeline's progress hook, called before each object (done < total) and once at
            the end: report the progress, or — before an object, once a stop was requested — raise
            Analysis_Stopped_Error_Cls instead.

        Args:
            (1) done [int]: The objects described so far.
            (2) total [int]: The objects in the frame.
        """

        if done < total and self.__stop.is_set():
            raise Analysis_Stopped_Error_Cls(done, total)
        self.Progress_Changed.emit(done, total)

    def Run(self) -> None:
        """
        Description:
            Execute the analysis and emit the result. Runs on the worker thread and
            reports progress and errors through signals only. self.__image is
            already the RGB ndarray the camera captured — the Qt-free backend takes
            it directly. A requested stop ends it before the next object with
            Analysis_Stopped instead.
        """

        try:
            result = self.__vision.Analyze(
                self.__image,
                progress_cb=self.__Progress,
                stage_cb=lambda text: self.Stage_Changed.emit(text),
            )
        except Analysis_Stopped_Error_Cls as stop:
            self.Analysis_Stopped.emit(*stop.args)
        except Exception as exc:                          # noqa: BLE001
            # Every failure is a sentence the operator can act on; the panel prints
            # it verbatim.
            self.Analysis_Failed.emit(str(exc))
        else:
            self.Analysis_Finished.emit(result)


class Connect_Worker_Cls(QObject):
    """
    Description:
        Opens the camera off the GUI thread. A Basler CONNECT enumerates the device,
        configures it and reads the sensor size — seconds of blocking work that
        would freeze the window and its loading animation. Moved onto a QThread, it
        reports only done-or-failed; the sensor size is read back on the GUI thread
        once it succeeds.

    Initialization of the Class:
        Args:
            (1) camera [Camera_Backend_Cls(object)]: The camera backend to open.

        Example:
            Initialization:
                # Assignment of the variables.
                thread = QThread()

                # Initialization of the class.
                Cls = Connect_Worker_Cls(camera)
                Cls.moveToThread(thread)
                thread.started.connect(Cls.Run)

            Features:
                # Signals of the class.
                Cls.Connect_Finished; Cls.Connect_Failed

                # Functions of the class.
                Cls.Run()
    """

    # << SIGNALS >> #
    Connect_Finished = pyqtSignal()
    Connect_Failed = pyqtSignal(str)

    def __init__(self, camera: tp.Any) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__camera = camera

    def Run(self) -> None:
        """
        Description:
            Connect the camera and report done-or-failed through signals only.
        """

        try:
            self.__camera.Connect()
        except Exception as exc:                          # noqa: BLE001
            self.Connect_Failed.emit(str(exc))
        else:
            self.Connect_Finished.emit()


class Frame_Mailbox_Cls(object):
    """
    Description:
        A one-frame mailbox between a worker thread and the window: Put keeps only the newest frame and says
        whether the box was empty (so the worker announces a frame only then, and at most one announcement is
        ever on its way); Take empties it. Frames are dropped, never queued. Thread-safe.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Frame_Mailbox_Cls()

            Features:
                # Properties of the class.
                Cls.Delivered; Cls.Dropped

                # Functions of the class.
                Cls.Put(frame); Cls.Take()
    """

    def __init__(self) -> None:
        # << PRIVATE >> #
        self.__lock = threading.Lock()
        self.__frame = None
        # Frames put in the box, and frames replaced there before they were taken.
        self.__delivered = 0
        self.__dropped = 0

    @property
    def Delivered(self) -> int:
        """
        Description:
            How many frames were put in the box.

        Returns:
            (1) parameter [int]: The frames delivered.
        """

        return self.__delivered

    @property
    def Dropped(self) -> int:
        """
        Description:
            How many frames were replaced in the box by a newer one before they were taken.

        Returns:
            (1) parameter [int]: The frames dropped.
        """

        return self.__dropped

    def Put(self, frame: tp.List[tp.List[int]]) -> bool:
        """
        Description:
            Put the newest frame in the box, replacing one not yet taken.

        Args:
            (1) frame [Matrix<uint8> HxWx3]: The frame (RGB).

        Returns:
            (1) parameter [bool]: True when the box was empty: the frame must be announced.
        """

        with self.__lock:
            waiting = self.__frame is not None
            self.__frame = frame
            self.__delivered += 1
            self.__dropped += int(waiting)
        return not waiting

    def Take(self) -> tp.Optional[tp.List[tp.List[int]]]:
        """
        Description:
            Take the newest frame out of the box, leaving it empty.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3 or None]: The frame (RGB), or None when none waits.
        """

        with self.__lock:
            frame, self.__frame = self.__frame, None
        return frame


class Preview_Worker_Cls(QObject):
    """
    Description:
        Runs the live preview off the GUI thread: starts the camera's stream, takes its frames one after
        another until asked to stop, then stops the stream — on every path, a failure included. Frames are
        dropped, never queued: the newest waits in a one-frame mailbox, and Frame_Ready is emitted only
        when the mailbox was empty, so at most one notification is ever on its way to the window, and a
        window busy painting takes the newest frame when it gets there (Take_Frame). The camera's stream
        keeps only its newest frame too (Camera.Basler.Basler_Cls.Start_Stream). Preview frames go to the
        window only: nothing here analyses, records or counts them.

    Initialization of the Class:
        Args:
            (1) camera [Camera_Backend_Cls(object)]: The connected camera.

        Example:
            Initialization:
                # Assignment of the variables.
                thread = QThread()

                # Initialization of the class.
                Cls = Preview_Worker_Cls(camera)
                Cls.moveToThread(thread)
                thread.started.connect(Cls.Run)

            Features:
                # Properties of the class.
                Cls.Delivered; Cls.Dropped

                # Signals of the class.
                Cls.Frame_Ready; Cls.Preview_Stopped

                # Functions of the class.
                Cls.Run(); Cls.Take_Frame(); Cls.Request_Stop()
    """

    # The shortest time between two frames the worker hands on: a backend with no frame rate of its own (a
    # saved frame) would otherwise loop as fast as it can. Far below the rig's 270 ms frame period, so the
    # camera's own rate is never limited by it.
    #   Unit [s]
    CONST_MIN_INTERVAL_S = 0.05

    # << SIGNALS >> #
    Frame_Ready = pyqtSignal()               # a new frame waits in the mailbox (Take_Frame)
    Preview_Stopped = pyqtSignal(str)        # '' when asked to stop, otherwise the failure sentence

    def __init__(self, camera: tp.Any) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__camera = camera
        # Set from the GUI thread by Request_Stop, read on the worker thread before each frame.
        self.__stop = threading.Event()
        # The one-frame mailbox the two threads share.
        self.__mailbox = Frame_Mailbox_Cls()

    @property
    def Delivered(self) -> int:
        """
        Description:
            How many frames the worker has put in the mailbox.

        Returns:
            (1) parameter [int]: The frames delivered.
        """

        return self.__mailbox.Delivered

    @property
    def Dropped(self) -> int:
        """
        Description:
            How many frames were replaced in the mailbox by a newer one before the window took them.

        Returns:
            (1) parameter [int]: The frames dropped.
        """

        return self.__mailbox.Dropped

    def Request_Stop(self) -> None:
        """
        Description:
            Ask the preview to stop after the frame it is waiting for (at most one frame period, or the
            camera's stream timeout on a camera that stopped sending). Called directly from the GUI thread.
        """

        self.__stop.set()

    def Take_Frame(self) -> tp.Optional[tp.List[tp.List[int]]]:
        """
        Description:
            Take the newest frame out of the mailbox (GUI thread), leaving it empty.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3 or None]: The frame (RGB), or None when none waits.
        """

        return self.__mailbox.Take()

    def Run(self) -> None:
        """
        Description:
            Start the stream, hand on frames until asked to stop or until the camera fails, stop the stream,
            and report how it ended through Preview_Stopped.
        """

        message = ''
        try:
            self.__camera.Start_Preview()
            while not self.__stop.is_set():
                start = time.monotonic()
                frame = self.__camera.Preview_Frame()
                if frame is None:
                    continue
                if self.__mailbox.Put(frame):
                    self.Frame_Ready.emit()
                self.__stop.wait(max(0.0, self.CONST_MIN_INTERVAL_S - (time.monotonic() - start)))
        except Exception as exc:                          # noqa: BLE001
            message = str(exc)
        finally:
            self.__camera.Stop_Preview()
        self.Preview_Stopped.emit(message)


class Scan_Worker_Cls(QObject):
    """
    Description:
        Takes the scan's frame off the GUI thread: Capture_Still waits for a still scene (up to about a
        second) before it takes one fresh frame. Every fresh frame the check grabs is handed on as the preview's
        are (a one-frame mailbox, Frame_Ready, Take_Frame), so the window shows the scene while the scan waits;
        the last of them stays readable (Last_Frame), for a scan refused for movement. Reports the frame with its
        distorted original and undistortion record, read on this thread right after the capture so they belong
        to that frame — or a failure, saying whether it was a moving scene (a refusal, the camera fine) or a
        capture failure.

    Initialization of the Class:
        Args:
            (1) camera [Camera_Backend_Cls(object)]: The connected camera, its preview stopped.

        Example:
            Initialization:
                # Assignment of the variables.
                thread = QThread()

                # Initialization of the class.
                Cls = Scan_Worker_Cls(camera)
                Cls.moveToThread(thread)
                thread.started.connect(Cls.Run)

            Features:
                # Properties of the class.
                Cls.Last_Frame

                # Signals of the class.
                Cls.Frame_Ready; Cls.Scan_Finished; Cls.Scan_Failed

                # Functions of the class.
                Cls.Run(); Cls.Take_Frame()
    """

    # << SIGNALS >> #
    Frame_Ready = pyqtSignal()                          # a fresh frame waits in the mailbox (Take_Frame)
    Scan_Finished = pyqtSignal(object, object, object)  # (frame, distorted original or None, undistortion or None)
    Scan_Failed = pyqtSignal(str, bool)                 # (the sentence, whether the scene was moving)

    def __init__(self, camera: tp.Any) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__camera = camera
        self.__mailbox = Frame_Mailbox_Cls()
        # The last fresh frame the check grabbed, None before the first.
        self.__last = None

    @property
    def Last_Frame(self) -> tp.Optional[tp.List[tp.List[int]]]:
        """
        Description:
            The last fresh frame the stillness check grabbed — what a scan refused for movement leaves on screen.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3 or None]: The frame (RGB), or None when none was grabbed.
        """

        return self.__last

    def Take_Frame(self) -> tp.Optional[tp.List[tp.List[int]]]:
        """
        Description:
            Take the newest fresh frame out of the mailbox (GUI thread), leaving it empty.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3 or None]: The frame (RGB), or None when none waits.
        """

        return self.__mailbox.Take()

    def __Hand_On(self, frame: tp.List[tp.List[int]]) -> None:
        """
        Description:
            Capture_Still's frame callback (this thread): keep the frame as the last, and announce it when the
            mailbox was empty.

        Args:
            (1) frame [Matrix<uint8> HxWx3]: A fresh frame (RGB).
        """

        self.__last = frame
        if self.__mailbox.Put(frame):
            self.Frame_Ready.emit()

    def Run(self) -> None:
        """
        Description:
            Take the scan's frame and report it, or the failure, through signals only.
        """

        try:
            frame = self.__camera.Capture_Still(frame_cb=self.__Hand_On)
        except Camera_Motion_Error_Cls as exc:
            self.Scan_Failed.emit(str(exc), True)
        except Exception as exc:                          # noqa: BLE001
            self.Scan_Failed.emit(str(exc), False)
        else:
            self.Scan_Finished.emit(frame, self.__camera.Last_Distorted_Frame, self.__camera.Last_Undistortion)


class Model_Load_Worker_Cls(QObject):
    """
    Description:
        Loads a configuration off the GUI thread — its models take about 9 s — so the window and
        its progress indication stay live. It puts the configuration in force through
        Vision_Pipeline_Cls.Configure (keep unchanged models, release changed ones first, restore
        the previous configuration on failure). Used by the Configuration dialog, the one place a
        configuration is loaded. It never touches a widget.

    Initialization of the Class:
        Args:
            (1) vision [Vision_Pipeline_Cls(object)]: The vision backend.
            (2) Configuration_Str [Configuration_Str(object)]: The configuration to put in force.

        Example:
            Initialization:
                # Assignment of the variables.
                thread = QThread()

                # Initialization of the class.
                Cls = Model_Load_Worker_Cls(vision, Configuration_Str)
                Cls.moveToThread(thread)
                thread.started.connect(Cls.Run)

            Features:
                # Signals of the class.
                Cls.Stage_Changed; Cls.Load_Finished; Cls.Load_Failed

                # Functions of the class.
                Cls.Run()
    """

    # << SIGNALS >> #
    Stage_Changed = pyqtSignal(str)          # phase text: 'Loading segmenter…', 'Loading model…', 'Warming up…'
    Load_Finished = pyqtSignal(float)        # the load time in seconds
    Load_Failed = pyqtSignal(str)            # a sentence naming what failed and what is in force

    def __init__(self, vision: tp.Any, Configuration_Str: tp.Any) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__vision = vision
        self.__config = Configuration_Str

    def Run(self) -> None:
        """
        Description:
            Load, then report done-or-failed through signals only.
        """

        stage_cb = lambda text: self.Stage_Changed.emit(text)
        started = time.perf_counter()
        try:
            self.__vision.Configure(self.__config, stage_cb)
        except Exception as exc:                          # noqa: BLE001
            self.Load_Failed.emit(str(exc))
        else:
            self.Load_Finished.emit(time.perf_counter() - started)
