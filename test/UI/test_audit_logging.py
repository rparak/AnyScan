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
# File Name: ../test/UI/test_audit_logging.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window; domain — the camera and the result
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Headless (offscreen) test that the window logs the post-processing audit (§3): every
    background strip and substance substitution the composer recorded is written to the
    application log — a warning via Log_Warning, otherwise Log_Info — so nothing the
    composer rewrote passes silently, and a view switch is NOT logged. No camera and no
    weights needed.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


class _Spy_Logger_Cls(object):
    """A logger stand-in that records the info and warning lines the window emits."""

    def __init__(self) -> None:
        self.infos = []
        self.warnings = []

    def Log_Info(self, info: str) -> None:
        self.infos.append(info)

    def Log_Warning(self, info: str) -> None:
        self.warnings.append(info)

    # The other lifecycle calls the finished slot makes are recorded as no-ops.
    def Log_Cleared(self, *args, **kwargs) -> None:
        pass

    def Log_Analysis_Finished(self, *args, **kwargs) -> None:
        pass

    def Log_Object_Detected(self, *args, **kwargs) -> None:
        pass



@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def test_analysis_audit_is_logged_by_level(qt_app, reference_background_path) -> None:
    """
    Description:
        Each audit record is logged: an 'info' record (a substitution) through Log_Info
        and a 'warning' record (a fallback strip) through Log_Warning, carrying the
        object index the composer tagged. A view switch afterwards logs nothing.
    """

    spy = _Spy_Logger_Cls()
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path), logger=spy)
    # A frame is needed to render the views; the objects are empty, which both renderers
    # handle, so the test isolates the audit logging.
    setattr(window, CONST_MANGLE + '__frame', np.zeros((20, 30, 3), dtype=np.uint8))

    audit = [('info', 'Obj. 1: substituted a wood guess for metal in "a wooden block"'),
             ('warning', 'Obj. 2: stripping would empty the caption; kept the original')]
    result = Analysis_Str(Objects=[], Background='A plain surface.', Verdict='Empty',
                          Verdict_Level='idle', Task='caption', Audit=audit)

    _Private(window, '__On_Analysis_Finished')(result)

    assert spy.infos == ['Obj. 1: substituted a wood guess for metal in "a wooden block"']
    assert spy.warnings == ['Obj. 2: stripping would empty the caption; kept the original']

    # The view switch is not a logged event.
    before = (list(spy.infos), list(spy.warnings))
    _Private(window, '__On_View_Toggle')('mask')
    assert (spy.infos, spy.warnings) == before
