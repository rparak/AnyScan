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
# Custom Lib.: AnyScan — vision backend (for the --background override)
#   ../Vision/Core
import Vision.Core as Vision_Core
# Custom Lib.: AnyScan UI — style helpers and the main window
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan — the session logger
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls

# The Windows AppUserModelID: without it the taskbar groups the app under
# python.exe's identity, so the title bar shows the AnyScan icon while the taskbar
# still shows the Python one.
CONST_APP_USER_MODEL_ID = 'cz.jic.anyscan.console'


def Parse_Args(argv: tp.List[str]) -> argparse.Namespace:
    """
    Description:
        Parse the developer-only command line. Absent all flags, this is the
        console: the Basler camera and the Florence-2 model.

    Args:
        (1) argv [Vector<string>]: The process argument vector (sys.argv).

    Returns:
        (1) parameter [argparse.Namespace(object)]: The parsed --frame / --background.
    """

    ap = argparse.ArgumentParser(
        description='AnyScan console. With no arguments it runs the Basler camera '
                    'and the Florence-2 model.')
    ap.add_argument(
        '--frame', metavar='PNG', default=None,
        help='Developer path: run the pipeline on a real frame previously saved '
             'from this camera instead of connecting it. Segmentation differences '
             'the frame against the reference background, so the frame must match '
             "that background's resolution (1920x1200). Real data, no hardware.")
    ap.add_argument(
        '--background', metavar='PNG', default=None,
        help='Override the empty-surface reference (default: the reference '
             'background under Data/Camera/).')
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
        camera and the local Florence-2 model — but the window opens without either
        present and reports a usable sentence when a real component is missing.

    Returns:
        (1) parameter [int]: The Qt application's exit code.
    """

    args = Parse_Args(sys.argv)
    if args.background:
        Vision_Core.CONST_BACKGROUND_REF = os.path.abspath(args.background)

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
    logger = Session_Logger_Cls()
    logger.Log_Info('Application started.')

    # A File_Camera_Cls (developer --frame) or the real Basler_Camera_Cls.
    camera = File_Camera_Cls(os.path.abspath(args.frame)) if args.frame else Basler_Camera_Cls()
    window = AnyScan_Window_Cls(camera=camera, logger=logger)
    window.setWindowIcon(icon)
    window.resize(1720, 1020)
    window.showMaximized()   # F11 toggles fullscreen, Esc closes
    try:
        return app.exec_()
    finally:
        logger.Close()


if __name__ == '__main__':
    sys.exit(main())
