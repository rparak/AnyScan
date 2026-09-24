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

# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QObject, pyqtSignal

"""
Description:
    The off-thread workers. Long-running work (a scan, model inference, a Basler
    handshake) never runs on the GUI thread; each worker is moved onto a QThread
    owned by the window and reports back only through signals. The window quits and
    waits on the thread once a worker's terminal signal fires, then deletes both.
"""


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
                Cls.Analysis_Finished; Cls.Analysis_Failed

                # Functions of the class.
                Cls.Run()
    """

    # << SIGNALS >> #
    Stage_Changed = pyqtSignal(str)          # phase text: 'Loading model…', 'Segmenting…'
    Progress_Changed = pyqtSignal(int, int)  # (objects done, total)
    Analysis_Finished = pyqtSignal(object)   # the Analysis_Str
    Analysis_Failed = pyqtSignal(str)        # an actionable sentence for the panel
    Log_Event = pyqtSignal(str, str)         # (level, message) from the Qt-free pipeline

    def __init__(self, vision: tp.Any, image: tp.List[tp.List[int]]) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__vision = vision
        self.__image = image

    def Run(self) -> None:
        """
        Description:
            Execute the analysis and emit the result. Runs on the worker thread and
            reports progress and errors through signals only. self.__image is
            already the RGB ndarray the camera captured — the Qt-free backend takes
            it directly.
        """

        try:
            result = self.__vision.Analyze(
                self.__image,
                progress_cb=lambda done, total: self.Progress_Changed.emit(done, total),
                stage_cb=lambda text: self.Stage_Changed.emit(text),
                log_cb=lambda level, message: self.Log_Event.emit(level, message),
            )
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
