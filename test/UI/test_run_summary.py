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
# File Name: ../test/UI/test_run_summary.py
## =========================================================================== ##

# System (Default)
import os
import csv
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI, logger, camera and structures
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str

"""
Description:
    The run-summary CSV row as the WINDOW produces it: its figures agree with the status bar
    while nothing has been cleared, it carries the same run id as the capture sets, and after a
    Clear it keeps the whole-run figures while clears_count records why the status bar differs.
"""

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Run(window, scores) -> None:
    """Finish one analysis with one object per score (None = unscored)."""
    objects = [Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=s) for s in scores]
    getattr(window, CONST_MANGLE + '__On_Analysis_Finished')(
        Analysis_Str(Objects=objects, Latency_Ms=1000, Verdict='ok', Verdict_Level='ok', Task='t'))


def _Summary_Row(logger) -> dict:
    """Close the run and read its summary row back."""
    logger.Close()
    with open(logger.Csv_Path, 'r', newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))[-1]


def _Window(reference_background_path, logger) -> AnyScan_Window_Cls:
    """A window with a frame, logging to the given logger."""
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path), logger=logger)
    setattr(window, CONST_MANGLE + '__frame', np.zeros((20, 30, 3), dtype=np.uint8))
    return window


def test_summary_row_matches_the_status_bar_before_any_clear(qt_app, reference_background_path,
                                                             tmp_path) -> None:
    """
    Description:
        Without a Clear, the CSV's images, objects and mean confidence equal what the status bar
        shows, computed the same way (each scored object weighted once), and the row's run id is
        the window's run id — the one in every capture set.
    """

    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = _Window(reference_background_path, logger)
    _Run(window, [0.91, 0.72, None])
    _Run(window, [0.55, 0.88])
    status = getattr(window, CONST_MANGLE + '__status')
    shown = (status.images.Value(), status.objects.Value(), status.confidence.Value())

    row = _Summary_Row(logger)
    assert (row['analyzed_images'], row['analyzed_objects']) == shown[:2]
    assert row['mean_confidence'] + '%' == shown[2]
    assert row['run_id'] == getattr(window, CONST_MANGLE + '__run_id')
    assert row['classification_enabled'] == 'false' and row['clears_count'] == '0'


def test_summary_row_stays_whole_run_across_a_clear(qt_app, reference_background_path,
                                                    tmp_path) -> None:
    """
    Description:
        Clear resets what the status bar shows, not the run summary: after a Clear the CSV still
        counts every analysis of the run, and clears_count says a Clear happened, so the
        difference from the status bar reads as expected rather than as a bug.
    """

    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path), install_handlers=False)
    window = _Window(reference_background_path, logger)
    _Run(window, [0.9, 0.8])
    getattr(window, CONST_MANGLE + '__On_Clear_Button_Clicked')()
    setattr(window, CONST_MANGLE + '__frame', np.zeros((20, 30, 3), dtype=np.uint8))
    _Run(window, [0.7])
    status = getattr(window, CONST_MANGLE + '__status')
    assert (status.images.Value(), status.objects.Value()) == ('1', '1')     # since the Clear

    row = _Summary_Row(logger)
    assert (row['analyzed_images'], row['analyzed_objects']) == ('2', '3')  # the whole run
    assert row['clears_count'] == '1'
    assert row['mean_confidence'] == '80'
