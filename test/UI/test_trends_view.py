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
# File Name: ../test/UI/test_trends_view.py
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
from Parameters.Vision import Detection_Str, Analysis_Str

"""
Description:
    The Trends view wired into the window (§6): the charts and the status bar read ONE
    accumulator, so the last point of each series equals the matching status figure exactly; a
    failed analysis advances neither; unscored objects never reach the confidence chart; and
    Clear empties the charts with the aggregates. No camera and no weights needed.
"""

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(owner, name: str, mangle: str = CONST_MANGLE):
    """Fetch a name-mangled private attribute of an object."""
    return getattr(owner, mangle + name)


def _Result(scores) -> Analysis_Str:
    """A reading with one object per score (None = found by the background cue alone)."""
    return Analysis_Str(Objects=[Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=s)
                                 for s in scores],
                        Latency_Ms=100, Verdict='ok', Verdict_Level='ok', Task='t')


def _Window(reference_background_path) -> AnyScan_Window_Cls:
    """A window with a frame set, ready to receive completed analyses."""
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
    setattr(window, CONST_MANGLE + '__frame', np.zeros((20, 30, 3), dtype=np.uint8))
    return window


def _Chart_Rows(window, chart: str) -> list:
    """The rows a chart is currently drawing (the objects or the confidence chart)."""
    view = _Private(window, '__trends_view')
    widget = _Private(view, '__%s_chart' % chart, '_Trends_View_Cls')
    mangle = '_Objects_Chart_Cls' if chart == 'objects' else '_Confidence_Chart_Cls'
    return _Private(widget, '__rows', mangle)


def test_chart_totals_match_the_status_bar_exactly(qt_app, reference_background_path) -> None:
    """
    Description:
        After several analyses the charts' last points ARE the status figures: the last x equals
        IMAGES ANALYSED, the final Total equals OBJECTS DETECTED, and the last run-mean point
        equals the status run mean — one accumulator, not two code paths that happen to agree.
    """

    window = _Window(reference_background_path)
    for scores in ([0.91, 0.72, 0.55, None], [0.88, 0.95], [0.40, None, 0.66], [0.83] * 5):
        _Private(window, '__On_Analysis_Finished')(_Result(scores))

    status = _Private(window, '__status')
    objects_rows = _Chart_Rows(window, 'objects')
    confidence_rows = _Chart_Rows(window, 'confidence')

    assert objects_rows is confidence_rows                      # both charts: the same rows
    assert str(objects_rows[-1].Index) == status.images.Value() == '4'
    assert str(objects_rows[-1].Cumulative_Total) == status.objects.Value() == '14'
    assert '%d%%' % confidence_rows[-1].Run_Mean == status.confidence.Value()


def test_a_failed_analysis_advances_neither_x_nor_images_analysed(qt_app, reference_background_path) -> None:
    """
    Description:
        A failed analysis is not an analysed image: it advances neither the chart's x nor the
        status bar's IMAGES ANALYSED, so the two agree either way.
    """

    window = _Window(reference_background_path)
    _Private(window, '__On_Analysis_Finished')(_Result([0.9, 0.9]))
    _Private(window, '__On_Analysis_Failed')('The model could not read the frame.')
    _Private(window, '__On_Analysis_Finished')(_Result([0.8]))

    rows = _Chart_Rows(window, 'objects')
    assert [row.Index for row in rows] == [1, 2]
    assert _Private(window, '__status').images.Value() == '2'


def test_unscored_objects_are_absent_from_the_confidence_chart(qt_app, reference_background_path) -> None:
    """
    Description:
        Unscored objects are never drawn as confidence dots (a 0% dot would be a false low
        reading); they are carried only as a count for the hover, and the dots that ARE drawn are
        exactly the scored objects.
    """

    window = _Window(reference_background_path)
    _Private(window, '__On_Analysis_Finished')(_Result([0.91, None, 0.55, None]))

    row = _Chart_Rows(window, 'confidence')[0]
    assert sorted(obj.Confidence for obj in row.Objects) == [55, 91]
    assert row.Unscored == 2
    chart = _Private(_Private(window, '__trends_view'), '__confidence_chart', '_Trends_View_Cls')
    assert 'Unscored: 2' in [text for text, _ in chart._Hover_Lines(0)]


def test_clear_empties_the_charts_with_the_aggregates(qt_app, reference_background_path) -> None:
    """
    Description:
        Clear resets the run: both charts go empty together with the status aggregates, since they
        read the same accumulator.
    """

    window = _Window(reference_background_path)
    _Private(window, '__On_Analysis_Finished')(_Result([0.9, 0.7]))
    _Private(window, '__On_Clear_Button_Clicked')()

    assert _Chart_Rows(window, 'objects') == []
    assert _Chart_Rows(window, 'confidence') == []
    assert _Private(window, '__status').images.Value() == '0'
