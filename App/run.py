"""
AnyScan — Vision-Language Industrial Inspection Console
The camera sees, the model describes.

Launcher for the AnyScan PyQt5 console. Built at JIC within the EDIH-DIGIMAT
project.

The application is split into Qt-free domain modules under ../src (Camera,
Vision, Reporting, Parameters) and the Qt UI under ../src/UI. This file only
parses the developer command line, builds the QApplication and the main window,
and starts the event loop.

The console runs on real hardware only: a Basler camera for capture and the
local Florence-2 vision-language model for analysis. Both sit behind small,
Qt-free interfaces (Camera_Backend_Cls, Vision_Backend_Cls), so the window opens
without the camera or the model present and reports a usable sentence when a real
component is missing.

For coordinate checks without hardware, `--frame path/to/frame.png` loads a real
frame previously saved from this camera (matching the reference background's
resolution) and runs the full pipeline on it. See File_Camera_Cls and main().
"""

import argparse
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# The project's src/ directory holds every Qt-free domain module and the UI. Put
# it on the path so they import by domain name.
_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# Custom Lib.: AnyScan — camera backends, the vision config, the UI, the window.
#   ../Camera/Core
from Camera.Core import File_Camera_Cls, Basler_Camera_Cls
#   ../Vision/Core
import Vision.Core as Vision_Core
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls


def _parse_args(argv):
    """Developer-only command line. Absent all flags, this is the console."""
    ap = argparse.ArgumentParser(
        description="AnyScan console. With no arguments it runs the Basler "
                    "camera and the Florence-2 model.")
    ap.add_argument(
        "--frame", metavar="PNG", default=None,
        help="Developer path: run the pipeline on a real frame previously saved "
             "from this camera instead of connecting it. Segmentation differences "
             "the frame against the reference background, so the frame must match "
             "that background's resolution (1920x1200). Real data, no hardware.")
    ap.add_argument(
        "--background", metavar="PNG", default=None,
        help="Override the empty-surface reference (default: the reference "
             "background under Data/Camera/).")
    # parse_known_args so Qt's own flags (-style, -platform, …) pass through.
    args, _ = ap.parse_known_args(argv[1:])
    return args


def main():
    args = _parse_args(sys.argv)
    if args.background:
        Vision_Core.CONST_BACKGROUND_REF = os.path.abspath(args.background)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    Style.Load_Fonts()

    icon = Style.App_Icon()
    app.setWindowIcon(icon)

    # On Windows the taskbar groups by AppUserModelID, and a plain Python process
    # inherits python.exe's identity. Without this the title bar shows the AnyScan
    # icon while the taskbar still shows the Python one.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "cz.jic.anyscan.console"
            )
        except Exception:  # noqa: BLE001 - cosmetic only, never worth a crash
            pass

    camera = File_Camera_Cls(os.path.abspath(args.frame)) if args.frame else Basler_Camera_Cls()
    window = AnyScan_Window_Cls(camera=camera)
    window.setWindowIcon(icon)
    window.resize(1720, 1020)
    window.showMaximized()   # F11 toggles fullscreen, Esc closes
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
