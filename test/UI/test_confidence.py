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
# File Name: ../test/UI/test_confidence.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window and the styling helpers
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import (Confidence_Severity, CONST_CONFIDENCE_WARN_BELOW,
                               CONST_CONFIDENCE_ERROR_BELOW)

"""
Description:
    The confidence severity colouring (§5): the thresholds and the severity bands, the
    number-only rich-text styling that reuses the log palette AND weight, and the status-bar
    run-mean log crossings with hysteresis. No camera and no weights needed.
"""

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


class _Spy_Logger_Cls(object):
    """A logger stand-in that records the info and warning lines the window emits."""

    def __init__(self) -> None:
        self.infos = []
        self.warnings = []

    def Log_Info(self, info: str) -> None:
        self.infos.append(info)

    def Log_Warning(self, info: str) -> None:
        self.warnings.append(info)

    # The other lifecycle calls are recorded as no-ops; no 'Path', so captures stay disabled.
    def Log_Error(self, *args, **kwargs) -> None:
        pass

    def Log_Analysis_Finished(self, *args, **kwargs) -> None:
        pass

    def Log_Object_Detected(self, *args, **kwargs) -> None:
        pass


def test_confidence_severity_bands_at_the_thresholds() -> None:
    """
    Description:
        The severity bands turn exactly at the two thresholds: at or above the warn line is
        INFO, one point below is WARNING; at or above the error line is WARNING, one below is
        ERROR. An unscored value has no severity (INFO, styled plain by the caller).
    """

    assert (CONST_CONFIDENCE_WARN_BELOW, CONST_CONFIDENCE_ERROR_BELOW) == (80, 60)
    assert Confidence_Severity(81) == 'INFO'
    assert Confidence_Severity(80) == 'INFO'
    assert Confidence_Severity(79) == 'WARNING'
    assert Confidence_Severity(61) == 'WARNING'
    assert Confidence_Severity(60) == 'WARNING'
    assert Confidence_Severity(59) == 'ERROR'
    assert Confidence_Severity(None) == 'INFO'


def test_confidence_number_html_colours_and_weights_only_below_the_line() -> None:
    """
    Description:
        A fine value (INFO) and an unscored '—' are returned plain — no markup where nothing
        changes — so they keep the default colour and weight. A WARNING and an ERROR value are
        wrapped in a span carrying the matching log colour and the heavier ramp weight (severity
        on two channels, colour AND weight, for a red-green-deficient viewer).
    """

    assert Style.Confidence_Number_Html('81%', 81) == '81%'
    assert Style.Confidence_Number_Html('—', None) == '—'

    warn = Style.Confidence_Number_Html('79%', 79)
    assert Style.Log_Level_Color('WARNING') in warn and '79%' in warn
    assert 'font-weight: %d' % Style.CONST_LEVEL_CSS_WEIGHTS['WARNING'] in warn

    error = Style.Confidence_Number_Html('59%', 59)
    assert Style.Log_Level_Color('ERROR') in error and '59%' in error
    assert 'font-weight: %d' % Style.CONST_LEVEL_CSS_WEIGHTS['ERROR'] in error
    # The two severities are a different weight, so they stay apart without colour.
    assert Style.CONST_LEVEL_CSS_WEIGHTS['ERROR'] > Style.CONST_LEVEL_CSS_WEIGHTS['WARNING']


def test_run_mean_log_crossings_with_hysteresis(qt_app, reference_background_path) -> None:
    """
    Description:
        The status-bar run mean is logged only when it CROSSES a threshold, not every
        analysis, and a recovery is logged only after the value clears the line by the
        hysteresis margin — so a mean hovering on a line does not emit a record per analysis.
        A fall logs a WARNING, a recovery an INFO, each carrying the value.
    """

    logger = _Spy_Logger_Cls()
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path), logger=logger)
    cross = _Private(window, '__Log_Confidence_Crossing')

    cross(85)                       # stays OK — no log
    assert logger.warnings == [] and logger.infos == []

    cross(79)                       # falls below 80 -> one WARNING
    assert len(logger.warnings) == 1 and '80%' in logger.warnings[0] and '79%' in logger.warnings[0]
    cross(78)                       # still in the warn band — no new log (crossing, not level)
    cross(81)                       # back over 80 but inside hysteresis — no recovery yet
    assert len(logger.warnings) == 1 and logger.infos == []
    cross(82)                       # clears 80 by the margin -> one INFO recovery
    assert len(logger.infos) == 1 and '80%' in logger.infos[0] and '82%' in logger.infos[0]

    cross(59)                       # falls below 60 -> a second WARNING
    assert len(logger.warnings) == 2 and '60%' in logger.warnings[1] and '59%' in logger.warnings[1]
    cross(61)                       # over 60 but inside hysteresis — no recovery yet
    assert len(logger.infos) == 1
    cross(63)                       # clears 60 by the margin -> a second INFO recovery
    assert len(logger.infos) == 2 and '60%' in logger.infos[1] and '63%' in logger.infos[1]
