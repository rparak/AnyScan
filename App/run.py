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
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# The project's src/ directory holds every Qt-free domain module (Camera, Vision,
# Reporting, Parameters) and the Qt UI (UI). Put it on the path so they import by
# domain name.
CONST_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
if CONST_SRC not in sys.path:
    sys.path.insert(0, CONST_SRC)
# Custom Lib.: AnyScan — camera backends
#   ../Camera/Core
from Camera.Core import File_Camera_Cls, Basler_Camera_Cls
#   ../Configuration/Core — the one configuration layer
from Configuration.Core import (Load_Configuration, Configuration_Error_Cls, Config_Loaded_Log_Line,
                                Config_Sources_Log_Line, CONST_DEFAULT_CONFIG_FILE)
# Custom Lib.: AnyScan UI — style helpers and the main window
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan — the session logger
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Vision/Utilities/Measure — the scale's configuration-loaded line
from Vision.Utilities.Measure import Scale_Log_Line

# The Windows AppUserModelID: without it the taskbar groups the app under
# python.exe's identity, so the title bar shows the AnyScan icon while the taskbar
# still shows the Python one.
CONST_APP_USER_MODEL_ID = 'cz.jic.anyscan.console'


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
    logger.Log_Info('Application started.')

    # Load the startup configuration through the one configuration layer, validated as a whole.
    # The application is usable at once (History, Log, Trends); its models are NOT loaded here —
    # that waits for the dialog's Load or the first CONNECT, so a launch to browse History costs
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
    logger.Log_Info("Startup configuration: '%s'. Its models load on the Configuration dialog's "
                    'Load or at the first CONNECT.' % configuration.Name)
    # When someone later asks why there is no OK/NOK in the UI, this line is the answer.
    logger.Log_Info(Config_Loaded_Log_Line(configuration))
    logger.Log_Info(Config_Sources_Log_Line(configuration))
    # No factor means no measurement (logged as a warning), never a size from a default.
    level, line = Scale_Log_Line(configuration.Name, configuration.Scale)
    (logger.Log_Warning if level == 'WARNING' else logger.Log_Info)(line)
    for level, note in configuration.Notes:
        (logger.Log_Warning if level == 'WARNING' else logger.Log_Info)(note)

    # A File_Camera_Cls (developer --frame) or the real Basler_Camera_Cls.
    camera = File_Camera_Cls(os.path.abspath(args.frame)) if args.frame else Basler_Camera_Cls()
    window = AnyScan_Window_Cls(camera=camera, logger=logger, Configuration_Str=configuration)
    window.setWindowIcon(icon)
    window.resize(1720, 1020)
    window.showMaximized()   # F11 toggles fullscreen, Esc closes
    try:
        return app.exec_()
    finally:
        logger.Close()


if __name__ == '__main__':
    sys.exit(main())
