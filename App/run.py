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
# File Name: ../App/run.py
## =========================================================================== ##

# System (Default)
import argparse
import os
import sys
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

# The project's src/ directory holds every Qt-free domain module (Camera, Vision,
# Reporting, Parameters) and the Qt UI (UI). Put it on the path so they import by
# domain name.
CONST_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
if CONST_SRC not in sys.path:
    sys.path.insert(0, CONST_SRC)
# Custom Lib.: AnyScan — the OpenCV check, run before anything below imports cv2
#   ../UI/Utilities/Opencv_Check
from UI.Utilities.Opencv_Check import Opencv_Startup_Message
# OpenCV's GUI build (opencv-python, which ultralytics and mlx-vlm require) puts Qt plugins in cv2's folder,
# and the window then aborts with a Qt core dump. Stop first, naming the fix.
CONST_OPENCV_MESSAGE = Opencv_Startup_Message(os.path.join(os.path.dirname(CONST_SRC), 'requirements.txt'))
if CONST_OPENCV_MESSAGE:
    sys.exit(CONST_OPENCV_MESSAGE)
# Custom Lib.: AnyScan — camera backends
#   ../Camera/Core
from Camera.Core import File_Camera_Cls, Basler_Camera_Cls
#   ../Configuration/Core — the one configuration layer
from Configuration.Core import (Load_Configuration, Configuration_Error_Cls, Config_Offered_Log_Line,
                                CONST_DEFAULT_CONFIG_FILE)
# Custom Lib.: AnyScan UI — style helpers and the main window
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan — the session logger
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Logger/Station_Events — the daily station event files, exported from the session logs
import Logger.Station_Events as Station_Events

# The Windows AppUserModelID: without it the taskbar groups the app under
# python.exe's identity, so the title bar shows the AnyScan icon while the taskbar
# still shows the Python one.
CONST_APP_USER_MODEL_ID = 'cz.jic.anyscan.console'

# How often the event loop hands control to the interpreter so a pending signal is acted on. Python
# runs a signal handler (the logger's SIGINT/SIGTERM close) only when it next runs, and an idle Qt
# loop runs none: without this, SIGTERM waited for the next mouse move or repaint, and a supervisor's
# SIGKILL could come first. A no-op every 250 ms bounds the delay; it costs ~11 ms of CPU per 30 s
# idle (0.04 % of one core; 0.3 ms without it), measured on an M2 Pro, offscreen, over 3 runs.
#   Unit [int] (ms)
CONST_SIGNAL_WAKE_MS = 250


def Parse_Args(argv: tp.List[str]) -> argparse.Namespace:
    """
    Description:
        Parse the developer-only command line. Absent all flags, this is the
        console: the Basler camera and the Gemma describer.

    Args:
        (1) argv [Vector<string>]: The process argument vector (sys.argv).

    Returns:
        (1) parameter [argparse.Namespace(object)]: The parsed --frame / --config.
    """

    ap = argparse.ArgumentParser(
        description='AnyScan console. With no arguments it runs the Basler camera '
                    'and the Gemma describer.')
    ap.add_argument(
        '--frame', metavar='PNG', default=None,
        help='Developer path: run the pipeline on a real frame previously saved '
             'from this camera instead of connecting it. Segmentation differences '
             'the frame against the reference background, so the frame must match '
             "that background's resolution (1920x1200). Real data, no hardware.")
    ap.add_argument(
        '--config', metavar='YAML', default=CONST_DEFAULT_CONFIG_FILE,
        help='The configuration loaded at startup (default: %(default)s). The Configuration '
             'dialog can replace it with another mode on the same hardware; a different camera '
             'means restarting with this flag.')
    # parse_known_args so Qt's own flags (-style, -platform, …) pass through.
    args, _ = ap.parse_known_args(argv[1:])
    return args


def Export_Station_Events(logger: Session_Logger_Cls, window: AnyScan_Window_Cls, directory: str) -> None:
    """
    Description:
        Wire the station event export: register this run's export at close, then export the earlier
        logs not yet exported, logging what happened — a failure as an ERROR the System cell counts. A
        failure at close cannot reach the closed log, so it is printed; the log stays out of the ledger
        and the next start exports it.

    Args:
        (1) logger [Session_Logger_Cls(object)]: This run's session logger.
        (2) window [AnyScan_Window_Cls(object)]: The main window, which counts a reported error.
        (3) directory [string]: The daily files' directory, from the startup configuration.
    """

    def _At_Close(log_path: str) -> None:
        """
        Description:
            Export this run's log once it is closed.

        Args:
            (1) log_path [string]: The closed session log.
        """

        try:
            Station_Events.Export_Log(log_path, directory)
        except Station_Events.Station_Events_Error_Cls as error:
            print('[ERROR] %s' % error)

    logger.Set_Close_Callback(_At_Close)
    log_dir = os.path.dirname(logger.Path)
    try:
        Pending_Export_Str = Station_Events.Export_Pending(log_dir, directory, logger.Path)
    except Station_Events.Station_Events_Error_Cls as error:
        window.Report_Error(str(error))
        return
    if Pending_Export_Str.Baselined:
        logger.Log_Info('Station events: no export ledger existed, so the %d session log(s) already in %s were '
                        'recorded as exported without exporting them; the export history starts with this run.'
                        % (Pending_Export_Str.Baselined, log_dir))
    for name in Pending_Export_Str.Exported:
        logger.Log_Info('Station events of the earlier session log %s exported to %s (it had not been exported: '
                        'the run did not close cleanly, or its export failed).' % (name, directory))
    for name in Pending_Export_Str.Live:
        logger.Log_Info('Station events of %s left for the instance still running it to export.' % name)
    for _name, message in Pending_Export_Str.Failed:
        window.Report_Error(message)


def main() -> int:
    """
    Description:
        Launch the AnyScan console. Parse the command line, build the QApplication
        and the main window, and start the Qt event loop.

        The application is split into Qt-free domain modules under ../src (Camera,
        Vision, Reporting, Parameters) and the Qt UI under ../src/UI; this launcher
        only wires them together. The console runs on real hardware — a Basler
        camera and the local Gemma model — but the window opens without either
        present and reports a usable sentence when a real component is missing.

    Returns:
        (1) parameter [int]: The Qt application's exit code.
    """

    args = Parse_Args(sys.argv)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    Style.Load_Fonts()

    icon = Style.App_Icon()
    app.setWindowIcon(icon)

    if sys.platform == 'win32':
        try:
            # Ctypes (C-compatible data types) [Python standard library]
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(CONST_APP_USER_MODEL_ID)
        except Exception:  # noqa: BLE001 - cosmetic only, never worth a crash
            pass

    # One session logger per application start. It records the run to ../logger/ and
    # writes the statistical summary when the run ends. The try/finally guarantees the
    # summary is written even if the event loop raises; a normal window close and the
    # logger's own atexit/signal hooks are the other, idempotent, shutdown paths.
    # The startup configuration names the run-summary CSV by its HARDWARE, so the CSV is fixed for
    # the run: the Configuration dialog may change the mode, never the hardware.
    config_path = os.path.abspath(args.config)
    logger = Session_Logger_Cls(config_path=config_path)

    # Load the startup configuration through the one configuration layer, validated as a whole.
    # The application is usable at once (History, Log, Trends); its models are NOT loaded here —
    # that waits for the Configuration dialog's Load (CONNECT requires it), so a launch to browse History costs
    # no ~9 s and no ~9.4 GB. A startup configuration that is invalid stops the launch with every
    # problem named: there is no previous configuration to fall back to, and a partly valid one is
    # never used.
    try:
        configuration = Load_Configuration(config_path)
    except Configuration_Error_Cls as error:
        logger.Log_Error('Startup configuration refused: %s' % error)
        logger.Close()
        print('[ERROR] %s' % error)
        print('[ERROR] Fix the file, or start with --config pointing at a valid configuration.')
        return 1
    # The file was READ, to know it is usable and what to offer — nothing is loaded yet. Its
    # calibration, reference, classification and scale are logged when it is loaded (the window,
    # on the dialog's Load), so the log never says more than has happened.
    logger.Log_Info(Config_Offered_Log_Line(configuration))

    # A File_Camera_Cls (developer --frame) or the real Basler_Camera_Cls.
    camera = File_Camera_Cls(os.path.abspath(args.frame)) if args.frame else Basler_Camera_Cls()
    window = AnyScan_Window_Cls(camera=camera, logger=logger, Configuration_Str=configuration)
    window.setWindowIcon(icon)

    # The daily station event files go to the startup configuration's directory, fixed for the run (a
    # mode naming another is refused). This run's log is exported when it closes, on every close path;
    # the logs of earlier runs that were not — a crash, or a failed export — are exported now.
    Export_Station_Events(logger, window, configuration.Station_Events_Directory)

    window.resize(1720, 1020)
    window.showMaximized()   # F11 toggles fullscreen, Esc closes
    signal_wake = QTimer()
    signal_wake.timeout.connect(lambda: None)
    signal_wake.start(CONST_SIGNAL_WAKE_MS)
    try:
        return app.exec_()
    finally:
        logger.Close()


if __name__ == '__main__':
    sys.exit(main())
