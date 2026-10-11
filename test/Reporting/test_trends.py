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
# File Name: ../test/Reporting/test_trends.py
## =========================================================================== ##

# Custom Lib.: AnyScan domain — the Qt-free trend model and plotting maths
#   ../Reporting/Trends
import Reporting.Trends as Trends
from Reporting.Trends import (Trends_Accumulator_Cls, Nice_Ticks, Value_To_Pixel, Nearest_Index,
                              Thin_Label_Indices)
#   ../Reporting/Core — the frame mean's one computation
from Reporting.Core import Frame_Confidence
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    The Qt-free half of the Trends view: the run accumulator both charts and the status bar read
    (cumulative counts, the running run mean, unscored objects kept off the confidence chart),
    and the pure plotting maths — nice-stepped ticks, value->pixel mapping, the hover hit-test
    and the x-label thinning — tested without a widget, where a hand-drawn chart's bugs hide.
"""


def _Det(score, verdict: str = 'OK') -> Detection_Str:
    """A detection with a FastSAM score (or None) and a verdict."""
    return Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Segmenter_Score=score, Verdict=verdict)


def test_module_is_qt_free() -> None:
    """
    Description:
        The trend model imports no Qt, like the capture reader — the data model is testable and
        reusable without a UI.
    """

    source = open(Trends.__file__).read()
    assert 'PyQt' not in source


def test_objects_accumulate_per_image() -> None:
    """
    Description:
        The object series is cumulative over analysed images: 4 after the first image, 9 after a
        second with 5. The last x equals the image count and the final total the object count —
        the two figures the status bar shows.
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.9)] * 4)
    acc.Add_Analysis([_Det(0.9)] * 5)
    rows = acc.Images()
    assert [row.Index for row in rows] == [1, 2]
    assert [row.Total for row in rows] == [4, 5]
    assert [row.Cumulative_Total for row in rows] == [4, 9]
    assert rows[-1].Index == acc.Image_Count() == 2
    assert rows[-1].Cumulative_Total == acc.Object_Count() == 9


def test_ok_nok_split_accumulates_with_the_total() -> None:
    """
    Description:
        The OK and NOK series accumulate beside the total, and sum to it when every object is OK or NOK.
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.9, 'OK'), _Det(0.9, 'NOK')])
    acc.Add_Analysis([_Det(0.9, 'NOK')] * 3)
    last = acc.Images()[-1]
    assert (last.Cumulative_Ok, last.Cumulative_Nok) == (1, 4)
    assert last.Cumulative_Ok + last.Cumulative_Nok == last.Cumulative_Total == 5


def test_last_run_mean_point_equals_the_status_mean() -> None:
    """
    Description:
        The running run mean is over every scored OBJECT so far (each weighted equally), and
        its last point is exactly the accumulator's run mean — the value the status bar reads.
        [0.90 x3] then [0.30]: (270 + 30) / 4 = 75, not the mean of frame means (60).
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.90)] * 3)
    acc.Add_Analysis([_Det(0.30)])
    rows = acc.Images()
    assert [row.Frame_Mean for row in rows] == [90, 30]
    assert [row.Run_Mean for row in rows] == [90, 75]
    assert rows[-1].Run_Mean == acc.Run_Mean() == 75


def test_the_means_round_once_from_the_raw_scores() -> None:
    """
    Description:
        The frame mean is Reporting.Core.Frame_Confidence's — the figure the Live panel, the capture
        record and History show — and the run mean is the raw scores' mean, rounded once. Rounding each
        object first moved them: scores 0.569 and 0.802 are 57 % and 80 %, whose mean 68.5 rounds (half
        to even) to 68, while the scores' own mean, 68.55 %, is 69 %. The confidence dots stay whole
        percentages.
    """

    acc = Trends_Accumulator_Cls()
    objects = [_Det(0.569), _Det(0.802)]
    acc.Add_Analysis(objects)
    row = acc.Images()[0]
    assert [obj.Confidence for obj in row.Objects] == [57, 80]
    assert row.Frame_Mean == Frame_Confidence(objects)[0] == 69
    assert row.Run_Mean == acc.Run_Mean() == 69

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.569)])
    acc.Add_Analysis([_Det(0.802), _Det(None)])
    assert [row.Frame_Mean for row in acc.Images()] == [57, 80]
    assert [row.Run_Mean for row in acc.Images()] == [57, 69]
    assert acc.Run_Mean() == 69


def test_unscored_objects_are_not_confidence_points() -> None:
    """
    Description:
        An unscored object is NOT a confidence point — plotting it at 0% would draw a false low
        reading — but it is counted, so the hover can say how many were left off. It still counts
        toward the object totals, and never enters either mean.
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.80), _Det(None), _Det(0.60), _Det(None)])
    row = acc.Images()[0]
    assert [obj.Confidence for obj in row.Objects] == [80, 60]
    assert all(obj.Confidence > 0 for obj in row.Objects)
    assert row.Unscored == 2
    assert row.Total == 4
    assert row.Frame_Mean == 70 and row.Run_Mean == 70


def test_an_all_unscored_image_has_no_mean_and_no_points() -> None:
    """
    Description:
        An image whose objects are all unscored has no points and no frame mean (None, not 0);
        until anything is scored the run mean is None too.
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(None), _Det(None)])
    row = acc.Images()[0]
    assert row.Objects == [] and row.Frame_Mean is None and row.Run_Mean is None
    assert acc.Run_Mean() is None


def test_reset_empties_the_run() -> None:
    """
    Description:
        Reset (Clear) empties the accumulator: no images, no objects, no run mean.
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.9)] * 3)
    acc.Reset()
    assert acc.Images() == [] and acc.Image_Count() == 0
    assert acc.Object_Count() == 0 and acc.Run_Mean() is None


def test_nice_ticks_land_on_one_two_five_steps() -> None:
    """
    Description:
        Ticks fall on 1, 2 or 5 times a power of ten and span the data range — never an awkward
        step like 3 or 7, and never leaving the maximum above the top tick.
    """

    assert Nice_Ticks(0, 100, 5) == [0, 20, 40, 60, 80, 100]
    assert Nice_Ticks(0, 9, 5) == [0, 2, 4, 6, 8, 10]
    assert Nice_Ticks(0, 437, 5) == [0, 100, 200, 300, 400, 500]
    assert Nice_Ticks(0, 0.7, 5) == [0, 0.2, 0.4, 0.6, 0.8]   # no float dust (0.6, not 0.6000…1)
    for high in (3, 7, 13, 58, 99, 250, 1234):
        ticks = Nice_Ticks(0, high, 5)
        step = ticks[1] - ticks[0]
        mantissa = step / (10 ** int(f'{step:e}'.split('e')[1]))
        assert round(mantissa, 6) in (1.0, 2.0, 5.0), (high, ticks)
        assert ticks[0] <= 0 and ticks[-1] >= high


def test_nice_ticks_handle_a_degenerate_range() -> None:
    """
    Description:
        A zero-width range (every value the same) still yields a usable, increasing tick list.
    """

    ticks = Nice_Ticks(5, 5, 5)
    assert len(ticks) >= 2 and ticks == sorted(ticks)


def test_value_to_pixel_maps_linearly_and_inverts_for_y() -> None:
    """
    Description:
        Values map linearly onto the pixel range; an inverted range (a y axis growing up on screen)
        puts the minimum at the bottom; a zero-width value range maps to the midpoint.
    """

    assert Value_To_Pixel(0, 0, 100, 10, 210) == 10
    assert Value_To_Pixel(50, 0, 100, 10, 210) == 110
    assert Value_To_Pixel(100, 0, 100, 10, 210) == 210
    assert Value_To_Pixel(0, 0, 100, 300, 100) == 300        # y: minimum at the bottom
    assert Value_To_Pixel(100, 0, 100, 300, 100) == 100      # y: maximum at the top
    assert Value_To_Pixel(7, 7, 7, 0, 40) == 20              # degenerate range -> midpoint


def test_hover_hit_test_picks_the_nearest_column() -> None:
    """
    Description:
        The hover picks the column nearest the cursor, ties resolve to the first, and a cursor off
        to either side snaps to the end column (by design: the read-out always shows the nearest
        image); only an empty chart reads nothing.
    """

    xs = [10.0, 30.0, 50.0, 70.0]
    assert Nearest_Index(29, xs) == 1
    assert Nearest_Index(41, xs) == 2
    assert Nearest_Index(40, xs) == 1                        # tie -> the first
    assert Nearest_Index(-100, xs) == 0
    assert Nearest_Index(200, xs) == 3
    assert Nearest_Index(5, []) is None


def test_x_labels_thin_onto_round_numbers_without_overlap() -> None:
    """
    Description:
        With a few hundred images the x labels thin to what fits and land on round numbers — image
        1, then multiples of a 1/2/5 step (never 1, 11, 21 …) — adding the last image only when it
        clears the previous label by half a step. When they all fit, every one is kept.
    """

    assert Thin_Label_Indices(5, 10) == [0, 1, 2, 3, 4]
    assert Thin_Label_Indices(0, 10) == []
    assert [i + 1 for i in Thin_Label_Indices(300, 12)] == [1, 50, 100, 150, 200, 250, 300]
    assert [i + 1 for i in Thin_Label_Indices(437, 9)] == [1, 100, 200, 300, 400]
    for count, fit in ((300, 29), (437, 9), (101, 11), (57, 10), (999, 14)):
        numbers = [i + 1 for i in Thin_Label_Indices(count, fit)]
        assert numbers[0] == 1 and numbers == sorted(set(numbers))
        assert len(numbers) <= fit + 1, (count, fit, numbers)
        step = numbers[2] - numbers[1]
        mantissa = step / (10 ** (len(str(step)) - 1))
        assert mantissa in (1, 2, 5), (count, fit, numbers)
        # Every label between image 1 and the (possibly off-step) last image is a step multiple.
        assert all(n % step == 0 for n in numbers[1:-1]), (count, fit, numbers)
        # No two labels closer than half a step — the kept last image never collides.
        assert all(b - a >= step / 2.0 for a, b in zip(numbers, numbers[1:])), numbers


def test_a_warning_or_unspecified_object_is_counted_but_neither_ok_nor_nok() -> None:
    """
    Description:
        A catalogue mode's Warning (not the part) and Unspecified (not judged) objects count in the total
        but in neither the OK nor the NOK series — an object that is not the part did not pass — and in
        series of their own, so the four add up to the total and the Warnings found are visible.
    """

    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis([_Det(0.9, 'OK'), _Det(0.9, 'Warning'), _Det(0.9, 'Unspecified'), _Det(0.9, 'NOK')])
    last = acc.Images()[-1]
    assert (last.Cumulative_Total, last.Cumulative_Ok, last.Cumulative_Nok) == (4, 1, 1)
    assert (last.Cumulative_Warning, last.Cumulative_Unspecified) == (1, 1)
    acc.Add_Analysis([_Det(0.9, 'Warning')] * 2)
    last = acc.Images()[-1]
    assert (last.Warning, last.Cumulative_Warning) == (2, 3)
    assert last.Cumulative_Ok + last.Cumulative_Nok + last.Cumulative_Warning + last.Cumulative_Unspecified == \
        last.Cumulative_Total
