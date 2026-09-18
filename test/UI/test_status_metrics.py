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
# File Name: ../test/UI/test_status_metrics.py
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
# Custom Lib.: AnyScan UI — the window; style; domain — the camera and the result
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str

"""
Description:
    Headless (offscreen) tests for the status-strip aggregate fields and the panel table's
    per-frame confidence. The status strip carries the SESSION figures — the rolling MEDIAN
    inference latency and the MEAN detector confidence over every scored object in every
    analysis; the panel table carries the FRAME figures — this analysis's latency and the
    mean over this frame's objects. These tests assert the empty-session state, the median
    rolling across analyses, the mean computed over EXACTLY the scored objects, the no-
    confidence case, that the frame mean and the session mean are computed over their own
    scopes (and so can differ), and the reset on Clear. No camera and no weights needed.
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


def _Object(score) -> Detection_Str:
    """A detection carrying (or not) a FastSAM confidence score."""
    return Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=score)


def _Result(latency, scores) -> Analysis_Str:
    """A reading with the given latency and per-object scores (None = the bg cue only)."""
    return Analysis_Str(Objects=[_Object(s) for s in scores], Latency_Ms=latency,
                        Verdict='ok', Verdict_Level='ok', Task='t')


def _Window(reference_background_path) -> AnyScan_Window_Cls:
    """A window with a frame set, ready to receive completed analyses."""
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path))
    setattr(window, CONST_MANGLE + '__frame', np.zeros((20, 30, 3), dtype=np.uint8))
    return window


def test_empty_session_shows_no_value(qt_app, reference_background_path) -> None:
    """
    Description:
        Before any analysis, both performance cells read the no-value placeholder — there
        is nothing to average yet.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    assert status.inference.Value() == Style.CONST_NO_VALUE
    assert status.confidence.Value() == Style.CONST_NO_VALUE


def test_inference_is_a_rolling_median_across_analyses(qt_app, reference_background_path) -> None:
    """
    Description:
        The inference cell is the MEDIAN latency across the session's analyses, not the
        last frame's — so one slow frame does not swing it. Three analyses of 100, 300,
        200 ms read a median of 200 ms.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    for latency in (100, 300, 200):
        _Private(window, '__On_Analysis_Finished')(_Result(latency, [0.9]))
    assert status.inference.Value() == '200 ms'


def test_status_confidence_is_the_session_mean_over_scored_objects(qt_app, reference_background_path) -> None:
    """
    Description:
        The status confidence cell is the SESSION mean over EXACTLY the objects that carry a
        score — a partial set is never averaged silently: the mean's denominator is the
        number of scored objects (not the total) and the summed set is exactly those objects
        (an unscored object is not counted as zero). For one analysis of [0.90, 0.80, None]
        the session mean is 85% = mean(0.90, 0.80), denominator 2.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.90, 0.80, None]))

    # 85% = mean(0.90, 0.80) — denominator 2 (the scored count), NOT 3.
    assert status.confidence.Value() == '85%'


def test_status_confidence_denominator_is_the_scored_count_not_the_total(qt_app, reference_background_path) -> None:
    """
    Description:
        Guards averaging over the whole set. With one high score and two unscored objects,
        the mean must be the single score (100%), not that score divided by three.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    _Private(window, '__On_Analysis_Finished')(_Result(100, [1.0, None, None]))
    assert status.confidence.Value() == '100%'


def test_status_confidence_is_no_value_when_no_object_has_a_score(qt_app, reference_background_path) -> None:
    """
    Description:
        When every object across the session was found by the background cue alone (no
        FastSAM score), the confidence cell is the no-value placeholder — never '0%', which
        would misstate an absent measurement as a zero confidence.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    _Private(window, '__On_Analysis_Finished')(_Result(100, [None, None]))
    assert status.confidence.Value() == Style.CONST_NO_VALUE


def test_frame_mean_and_session_mean_are_over_their_own_scopes(qt_app, reference_background_path) -> None:
    """
    Description:
        The panel table's per-frame confidence and the status strip's per-session confidence
        are computed over DIFFERENT scopes and read different numbers at the same time — the
        fixture's two analyses carry different confidence so the two figures cannot
        coincidentally agree and hide a wiring error. After analyses of [0.90] then [0.50]:
        the frame table shows the last frame alone (50%), the status strip the session mean
        (70% = mean(0.90, 0.50)).
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    meta = _Private(window, '__meta_confidence')

    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.90]))
    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.50]))

    assert meta.text() == '50%'                 # the frame: the last analysis alone
    assert status.confidence.Value() == '70%'   # the session: every scored object
    assert meta.text() != status.confidence.Value()


def test_session_mean_weights_each_object_equally_not_each_frame(qt_app, reference_background_path) -> None:
    """
    Description:
        The session mean is over every scored OBJECT across all analyses, not the mean of the
        per-frame means — the two differ whenever frames hold different object counts, and a
        nine-object frame must not count the same as a one-object frame. A three-object frame
        of [0.90, 0.90, 0.90] then a one-object frame of [0.30]: per object the mean is
        (0.90·3 + 0.30) / 4 = 0.75 → 75%; the mean of frame means would be (0.90 + 0.30) / 2
        = 0.60 → 60%. The cell must read 75%.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.90, 0.90, 0.90]))
    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.30]))

    assert status.confidence.Value() == '75%'   # per object; the mean-of-means 60% is wrong
    assert _Private(window, '__session_scores') == [0.90, 0.90, 0.90, 0.30]


def test_frame_confidence_shows_coverage_when_partial_and_dash_when_none(qt_app, reference_background_path) -> None:
    """
    Description:
        The panel table's frame confidence shows the coverage when the frame is only
        partially scored ('X% over K of M'), the percentage alone when every object is
        scored, and the no-value placeholder when nothing is scored — never '0%'. The object
        list directly below shows which objects lack a score, so the coverage reconciles.
    """

    window = _Window(reference_background_path)
    meta = _Private(window, '__meta_confidence')

    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.90, 0.80, None]))
    assert meta.text() == '85% over 2 of 3'       # partial: coverage shown

    _Private(window, '__On_Analysis_Finished')(_Result(100, [0.90, 0.80]))
    assert meta.text() == '85%'                    # fully scored: percentage alone

    _Private(window, '__On_Analysis_Finished')(_Result(100, [None, None]))
    assert meta.text() == Style.CONST_NO_VALUE     # nothing scored: '—', not '0%'


def test_clear_resets_the_performance_fields(qt_app, reference_background_path) -> None:
    """
    Description:
        Clear resets the rolling median, the session confidence and its accumulator, and the
        frame table's confidence — consistent with the session counters it already resets, so
        a new session starts from a clean slate.
    """

    window = _Window(reference_background_path)
    status = _Private(window, '__status')
    _Private(window, '__On_Analysis_Finished')(_Result(150, [0.9]))
    assert status.inference.Value() != Style.CONST_NO_VALUE

    _Private(window, '__On_Clear_Button_Clicked')()
    assert status.inference.Value() == Style.CONST_NO_VALUE
    assert status.confidence.Value() == Style.CONST_NO_VALUE
    assert _Private(window, '__meta_confidence').text() == Style.CONST_NO_VALUE
    assert _Private(window, '__latencies') == []
    assert _Private(window, '__session_scores') == []
