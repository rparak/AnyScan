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
# File Name: ../test/UI/test_opencv_check.py
## =========================================================================== ##

# System (Default)
import os
import sys
import subprocess
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan UI — the OpenCV startup check
#   ../UI/Utilities/Opencv_Check
from UI.Utilities.Opencv_Check import Opencv_Problem, Headless_Pin

"""
Description:
    Tests for the OpenCV startup check: OpenCV's GUI build, or its Qt plugins in cv2's folder, stop the
    application with a message naming the fix, before anything imports cv2 and before Qt's core dump.
"""
# The repository root and the application's entry point.
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_RUN = os.path.join(CONST_PROJECT_FOLDER, 'App', 'run.py')


def _Fake_Opencv(root: str, plugins: bool, gui: bool) -> str:
    """
    Description:
        A site directory holding a cv2 package that fails if imported, with or without its Qt plugins folder,
        and with or without opencv-python's distribution record.

    Args:
        (1) root [string]: The pytest tmp_path.
        (2) plugins [bool]: Whether cv2/qt/plugins exists.
        (3) gui [bool]: Whether opencv-python is recorded as installed.

    Returns:
        (1) parameter [string]: The site directory.
    """

    site = os.path.join(str(root), 'site')
    os.makedirs(os.path.join(site, 'cv2'))
    with open(os.path.join(site, 'cv2', '__init__.py'), 'w') as handle:
        handle.write("raise RuntimeError('cv2 was imported before the check')\n")
    if plugins:
        os.makedirs(os.path.join(site, 'cv2', 'qt', 'plugins', 'platforms'))
    if gui:
        record = os.path.join(site, 'opencv_python-5.0.0.93.dist-info')
        os.makedirs(record)
        with open(os.path.join(record, 'METADATA'), 'w') as handle:
            handle.write('Metadata-Version: 2.1\nName: opencv-python\nVersion: 5.0.0.93\n')

    return site


def test_the_problem_names_the_gui_build_and_its_plugins(tmp_path) -> None:
    """
    Description:
        Nothing is wrong with the headless build alone; the GUI build installed, its Qt plugins in cv2's
        folder, or both, are named.
    """

    folder = os.path.join(str(tmp_path), 'cv2')
    os.makedirs(folder)
    assert Opencv_Problem(False, folder) == '' and Opencv_Problem(False, None) == ''
    assert Opencv_Problem(True, folder) == 'opencv-python is installed'
    os.makedirs(os.path.join(folder, 'qt', 'plugins'))
    plugins = os.path.join(folder, 'qt', 'plugins')
    assert Opencv_Problem(False, folder) == '%s exists' % plugins
    assert Opencv_Problem(True, folder) == 'opencv-python is installed and %s exists' % plugins


def test_the_headless_pin_is_read_from_requirements(tmp_path) -> None:
    """
    Description:
        The pin's one home is requirements.txt: the shipped one pins the headless build; a file without the pin,
        or no file, gives ''.
    """

    assert Headless_Pin(os.path.join(CONST_PROJECT_FOLDER, 'requirements.txt')) == '5.0.0.93'
    path = os.path.join(str(tmp_path), 'requirements.txt')
    with open(path, 'w') as handle:
        handle.write('opencv-python>=4.10\nopencv-python-headless>=4.10\n')
    assert Headless_Pin(path) == '' and Headless_Pin(os.path.join(str(tmp_path), 'missing.txt')) == ''


@pytest.mark.parametrize('plugins, gui', [(True, True), (True, False), (False, True)],
                         ids=['both', 'plugins only', 'gui build only'])
def test_the_application_stops_with_the_fix_before_cv2_and_qt(tmp_path, plugins: bool, gui: bool) -> None:
    """
    Description:
        App/run.py started with OpenCV's GUI build installed or its Qt plugins in cv2's folder stops at once
        with exit status 1 and a message naming the two commands, instead of Qt's core dump: cv2 is never
        imported (the fake one raises if it is) and no window is made.
    """

    site = _Fake_Opencv(tmp_path, plugins, gui)
    environment = dict(os.environ, PYTHONPATH=site, QT_QPA_PLATFORM='offscreen')
    process = subprocess.run([sys.executable, CONST_RUN], env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, universal_newlines=True, timeout=60)

    assert process.returncode == 1, process.stdout
    assert process.stdout.startswith('[ERROR] AnyScan cannot open its window: ')
    assert 'python -m pip uninstall -y opencv-python\n' in process.stdout
    assert 'python -m pip install --force-reinstall --no-deps opencv-python-headless==5.0.0.93\n' in process.stdout
    assert 'cv2 was imported' not in process.stdout and 'Traceback' not in process.stdout
