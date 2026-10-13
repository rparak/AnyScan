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
# File Name: ../UI/Utilities/Opencv_Check.py
## =========================================================================== ##

# System (Default)
import os
import re
import importlib.util
import importlib.metadata
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The OpenCV the window can live with, checked at startup before anything imports cv2 (App/run.py). The
    application needs the headless build only: the window is PyQt5's, and nothing calls OpenCV's own GUI.
    ultralytics and mlx-vlm require the GUI build (opencv-python), so a requirements install brings it in
    beside the headless one. The two share the cv2 folder, and the GUI build adds Qt plugins there
    (cv2/qt/plugins): PyQt5 then loads OpenCV's xcb plugin and the process aborts with a Qt core dump.
    install.sh removes it after every install (Ensure_Headless_Opencv); this check names the fix when a
    later pip command brought it back. Qt-free, and it never imports cv2.
"""

# The GUI build's distribution name, the headless build's, and the folder the GUI build's Qt plugins sit in,
# under cv2's package folder.
#   Unit [string] / [string] / [Vector<string>]
CONST_OPENCV_GUI = 'opencv-python'
CONST_OPENCV_HEADLESS = 'opencv-python-headless'
CONST_OPENCV_QT_PLUGINS = ('qt', 'plugins')
# The headless build's pin in requirements.txt ('opencv-python-headless==5.0.0.93'), its one home.
#   Unit [string] (regular expression)
CONST_OPENCV_PIN_PATTERN = r'^opencv-python-headless==([^\s;#]+)'


def Installed_Opencv() -> tp.Tuple[bool, tp.Optional[str]]:
    """
    Description:
        What is installed, read without importing cv2: whether the GUI build's distribution is installed, and
        cv2's package folder (None when cv2 cannot be found).

    Returns:
        (1) parameter [Tuple<bool, string or None>]: (the GUI build installed, cv2's folder).
    """

    try:
        importlib.metadata.version(CONST_OPENCV_GUI)
        gui = True
    except importlib.metadata.PackageNotFoundError:
        gui = False
    spec = importlib.util.find_spec('cv2')
    folders = list(spec.submodule_search_locations or []) if spec is not None else []

    return gui, (folders[0] if folders else None)


def Opencv_Problem(gui_installed: bool, cv2_folder: tp.Optional[str]) -> str:
    """
    Description:
        What is wrong with the installed OpenCV for the window, in words: the GUI build installed, its Qt
        plugins in cv2's folder, or both; '' when neither.

    Args:
        (1) gui_installed [bool]: Whether opencv-python is installed.
        (2) cv2_folder [string or None]: cv2's package folder.

    Returns:
        (1) parameter [string]: The problem, or ''.
    """

    found = []
    if gui_installed:
        found.append('%s is installed' % CONST_OPENCV_GUI)
    if cv2_folder is not None and os.path.isdir(os.path.join(cv2_folder, *CONST_OPENCV_QT_PLUGINS)):
        found.append('%s exists' % os.path.join(cv2_folder, *CONST_OPENCV_QT_PLUGINS))

    return ' and '.join(found)


def Headless_Pin(requirements_path: str) -> str:
    """
    Description:
        The headless build's pinned version, read from requirements.txt.

    Args:
        (1) requirements_path [string]: requirements.txt.

    Returns:
        (1) parameter [string]: The version; '' when the file or the pin is missing.
    """

    try:
        with open(requirements_path, 'r', encoding='utf-8') as handle:
            for line in handle:
                match = re.match(CONST_OPENCV_PIN_PATTERN, line.strip())
                if match:
                    return match.group(1)
    except OSError:
        pass

    return ''


def Opencv_Startup_Message(requirements_path: str) -> str:
    """
    Description:
        The message the application stops with instead of the Qt core dump the GUI build's plugins cause:
        what is wrong and the two commands that fix it inside the .venv; '' when the OpenCV installed is fine.

    Args:
        (1) requirements_path [string]: requirements.txt, for the headless build's pin.

    Returns:
        (1) parameter [string]: The message, or ''.
    """

    problem = Opencv_Problem(*Installed_Opencv())
    if not problem:
        return ''
    pin = Headless_Pin(requirements_path)
    headless = '%s==%s' % (CONST_OPENCV_HEADLESS, pin) if pin else CONST_OPENCV_HEADLESS

    return ('[ERROR] AnyScan cannot open its window: %s. OpenCV\'s GUI build ships Qt plugins that make the window '
            'abort ("Could not load the Qt platform plugin xcb"); the application needs the headless build only. '
            'With the .venv active, run:\n'
            '    python -m pip uninstall -y %s\n'
            '    python -m pip install --force-reinstall --no-deps %s\n'
            'or re-run ./install.sh, which does both.' % (problem, CONST_OPENCV_GUI, headless))
