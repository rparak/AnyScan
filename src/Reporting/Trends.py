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
# File Name: ../Reporting/Trends.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Custom Lib.: AnyScan domain — the detection structure
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str
# Custom Lib.: AnyScan — the frame mean's one computation (the Live panel, the capture record, History)
#   ../Reporting/Core
from Reporting.Core import Frame_Confidence

"""
Description:
    Initialization of constants.

    The Qt-free data model behind the Trends view AND the status-bar aggregates: ONE
    accumulator that both read, so the last point of the run-mean line equals the status
    figure by construction, not by two code paths agreeing. It ingests one analysis at a time
    (only successful ones, so an image index never counts a failed analysis) and exposes, per
    analysed image, the cumulative object counts and the confidence points/means the two charts
    draw. It holds no Qt and no drawing — the plotting maths below (tick placement, value→pixel
    mapping, hover hit-test, label thinning) are pure functions so they can be unit-tested
    without a widget, which is where a hand-drawn chart's bugs hide.
"""


@dataclass
class Trend_Object_Str:
    """
    Description:
        One SCORED object's point for the confidence chart: its confidence percentage and its
        verdict (for the dot colour when classification is on). The image it belongs to is the
        Trend_Image_Str that holds it.
        Unscored objects are NOT represented here — plotting them at 0% would draw a false
        low-confidence point — they are counted in the owning image's Unscored field instead.
    """

    # The confidence percentage (0..100). Always present — an unscored object is not a point.
    #   Unit [int]
    Confidence: int = 0
    # The object's verdict (Parameters.Vision.CONST_VERDICTS), for the dot colour when the run classifies.
    #   Unit [string]
    Verdict: str = 'OK'


@dataclass
class Trend_Image_Str:
    """
    Description:
        One analysed image's row of trend data: the per-image object counts (total, and the OK/NOK
        split for when classification is on), the running cumulative counts the object chart draws,
        the frame mean and the running run mean the confidence chart draws as its two lines,
        and the scored-object points plus the unscored count for that image's hover.
    """

    # The 1-based image index (the x value on both charts).
    #   Unit [int]
    Index: int = 0
    # This image's object counts: total, and the split by verdict — OK, NOK, and in a catalogue mode the
    # Warnings (objects that should not be on the surface) and the Unspecified ones (not judged), so the four
    # add up to the total there.
    #   Unit [int]
    Total: int = 0
    Ok: int = 0
    Nok: int = 0
    Warning: int = 0
    Unspecified: int = 0
    # The cumulative counts up to AND including this image — the object chart's y values.
    #   Unit [int]
    Cumulative_Total: int = 0
    Cumulative_Ok: int = 0
    Cumulative_Nok: int = 0
    Cumulative_Warning: int = 0
    Cumulative_Unspecified: int = 0
    # This frame's mean confidence over its own scored objects, or None when none were scored.
    #   Unit [int]
    Frame_Mean: tp.Optional[int] = None
    # The running run mean over EVERY scored object up to and including this image, or None
    # until one object anywhere in the run is scored. The last image's value equals the status bar.
    #   Unit [int]
    Run_Mean: tp.Optional[int] = None
    # This image's scored-object points (for the confidence dots), and its unscored-object count.
    #   Unit [Vector<Trend_Object_Str(object)>] / [int]
    Objects: tp.List[Trend_Object_Str] = field(default_factory=list)
    Unscored: int = 0


class Trends_Accumulator_Cls(object):
    """
    Description:
        The single run accumulator both charts and the status-bar aggregates read. Feed it one
        successful analysis at a time; it appends one Trend_Image_Str and keeps the running totals
        and the pooled scored confidences, so every figure (images analysed, objects detected,
        run mean, and both charts' series) comes from one place and cannot drift.

    Initialization of the Class:
        Args:
            (none)

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Trends_Accumulator_Cls()

            Features:
                # Ingest one successful analysis (a list of Detection_Str).
                Cls.Add_Analysis(objects)
                # Read the aggregates the status bar shows.
                n, total, mean = Cls.Image_Count(), Cls.Object_Count(), Cls.Run_Mean()
                # Read the per-image rows both charts draw.
                rows = Cls.Images()
    """

    def __init__(self) -> None:
        # << PRIVATE >> #
        self.__images = []
        # Every scored object's raw score across the run, pooled, for the running run mean — each
        # object weighted equally, never the mean of per-frame means, and rounded once, at the end.
        self.__scores = []

    def Add_Analysis(self, objects: tp.List[Detection_Str]) -> None:
        """
        Description:
            Ingest ONE successful analysis, appending its image row. A failed analysis must NOT be
            passed here, so the image count never advances on a failure and stays equal to the
            status bar's images-analysed figure.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The analysis' located objects, in order.
        """

        index = len(self.__images) + 1
        row = Trend_Image_Str(Index=index, Total=len(objects))
        for det in objects:
            row.Ok += 1 if det.Verdict == 'OK' else 0
            row.Nok += 1 if det.Verdict == 'NOK' else 0
            row.Warning += 1 if det.Verdict == 'Warning' else 0
            row.Unspecified += 1 if det.Verdict == 'Unspecified' else 0
            if det.Segmenter_Score is None:
                row.Unscored += 1
                continue
            percent = int(round(100.0 * det.Segmenter_Score))
            row.Objects.append(Trend_Object_Str(Confidence=percent, Verdict=det.Verdict))
            self.__scores.append(det.Segmenter_Score)

        # Both means from the raw scores, rounded once: rounding each object first moved them a point
        # away from the Live panel's frame mean (0.569 and 0.802 are 57 and 80, whose mean rounds to 68;
        # the scores' own mean is 69 %).
        row.Frame_Mean = Frame_Confidence(objects)[0]
        row.Run_Mean = self.Run_Mean()

        previous = self.__images[-1] if self.__images else None
        base_total = previous.Cumulative_Total if previous else 0
        base_ok = previous.Cumulative_Ok if previous else 0
        base_nok = previous.Cumulative_Nok if previous else 0
        row.Cumulative_Total = base_total + row.Total
        row.Cumulative_Ok = base_ok + row.Ok
        row.Cumulative_Nok = base_nok + row.Nok
        row.Cumulative_Warning = (previous.Cumulative_Warning if previous else 0) + row.Warning
        row.Cumulative_Unspecified = (previous.Cumulative_Unspecified if previous else 0) + row.Unspecified
        self.__images.append(row)

    def Images(self) -> tp.List[Trend_Image_Str]:
        """
        Description:
            The per-image rows, oldest first — the two charts' data.

        Returns:
            (1) parameter [Vector<Trend_Image_Str(object)>]: One row per analysed image.
        """

        return self.__images

    def Image_Count(self) -> int:
        """
        Description:
            The number of analysed images — the status bar's IMAGES ANALYSED and the last x.

        Returns:
            (1) parameter [int]: The image count.
        """

        return len(self.__images)

    def Object_Count(self) -> int:
        """
        Description:
            The cumulative object total — the status bar's OBJECTS DETECTED and the object chart's
            final Total point.

        Returns:
            (1) parameter [int]: The cumulative object count.
        """

        return self.__images[-1].Cumulative_Total if self.__images else 0

    def Run_Mean(self) -> tp.Optional[int]:
        """
        Description:
            The run mean confidence over every scored object in the run, or None when nothing
            is scored yet — the status bar's run mean and the last point of the chart's
            run-mean line, one value for both.

        Returns:
            (1) parameter [int]: The run mean percentage, or None.
        """

        return int(round(100.0 * sum(self.__scores) / len(self.__scores))) if self.__scores else None

    def Reset(self) -> None:
        """
        Description:
            Clear the accumulator — the run's aggregates and both charts go empty (called on Clear).
        """

        self.__images = []
        self.__scores = []


def Nice_Ticks(low: float, high: float, target: int = 5) -> tp.List[float]:
    """
    Description:
        The axis tick VALUES for a range, on 'nice' steps (1, 2 or 5 times a power of ten) so the
        gridlines land on round numbers a reader expects — the thing a hand-rolled chart most often
        gets wrong. The step is the nice number nearest range/target; the ticks run from the
        multiple of the step at or below `low` to the one at or above `high`, inclusive.

    Args:
        (1) low [float]: The data minimum.
        (2) high [float]: The data maximum.
        (3) target [int]: The desired approximate number of intervals (>= 1).

    Returns:
        (1) parameter [Vector<float>]: The tick values, ascending, spanning the range.
    """

    if high <= low:
        high = low + 1.0
    span = __Nice_Number(high - low, round_it=False)
    step = __Nice_Number(span / max(1, target), round_it=True)
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    ticks, value, guard = [], start, 0
    while value <= end + step * 0.5 and guard < 1000:
        # Snap away tiny binary-float dust so 0.30000000000000004 reads as 0.3.
        ticks.append(round(value, 10))
        value += step
        guard += 1
    return ticks


def __Nice_Number(value: float, round_it: bool) -> float:
    """
    Description:
        The 'nice' number near `value`: a 1/2/5 mantissa times a power of ten. Rounds to the
        nearest nice number when round_it, else takes the nice number at or above value (used to
        size the range before the step).

    Args:
        (1) value [float]: The raw number to make nice (> 0).
        (2) round_it [bool]: Round to nearest (True) or ceil to the next nice number (False).

    Returns:
        (1) parameter [float]: The nice number.
    """

    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    fraction = value / (10 ** exponent)
    if round_it:
        nice = 1.0 if fraction < 1.5 else 2.0 if fraction < 3.0 else 5.0 if fraction < 7.0 else 10.0
    else:
        nice = 1.0 if fraction <= 1.0 else 2.0 if fraction <= 2.0 else 5.0 if fraction <= 5.0 else 10.0
    return nice * (10 ** exponent)


def Value_To_Pixel(value: float, v_low: float, v_high: float,
                   px_low: float, px_high: float) -> float:
    """
    Description:
        Map a data value in [v_low, v_high] to a pixel in [px_low, px_high], linearly. The pixel
        range may be inverted (px_low > px_high) for a y axis that grows upward on screen, and a
        zero-width value range maps to the midpoint rather than dividing by zero.

    Args:
        (1) value [float]: The data value.
        (2 - 3) v_low, v_high [float]: The data range.
        (4 - 5) px_low, px_high [float]: The pixel range (px_low is where v_low lands).

    Returns:
        (1) parameter [float]: The pixel position.
    """

    if v_high == v_low:
        return (px_low + px_high) / 2.0
    fraction = (value - v_low) / (v_high - v_low)
    return px_low + fraction * (px_high - px_low)


def Nearest_Index(query_px: float, xs_px: tp.List[float]) -> tp.Optional[int]:
    """
    Description:
        The index of the point whose x pixel is nearest `query_px`, for the hover read-out — the
        columns are evenly spaced, so nearest-by-x picks the image the cursor is over, and anywhere
        on the chart the read-out snaps to the nearest column (by design: there is no distance past
        which it reads nothing). Returns None only for an empty list.

    Args:
        (1) query_px [float]: The cursor x, in pixels.
        (2) xs_px [Vector<float>]: The points' x pixels, in order.

    Returns:
        (1) parameter [int]: The nearest index, or None.
    """

    if not xs_px:
        return None
    best_index, best_distance = 0, abs(xs_px[0] - query_px)
    for index in range(1, len(xs_px)):
        distance = abs(xs_px[index] - query_px)
        if distance < best_distance:
            best_index, best_distance = index, distance
    return best_index


def Thin_Label_Indices(count: int, max_labels: int) -> tp.List[int]:
    """
    Description:
        Which of `count` evenly spaced image positions get an x tick LABEL, so labels never overlap
        on a few-hundred-image run and still land on round numbers. When every label fits, all are
        kept. Otherwise the labelled image NUMBERS are the multiples of a 'nice' step (1, 2 or 5
        times a power of ten — the same rule as the y ticks), the smallest step that fits; image 1
        is always labelled, and the last image is added when it sits at least half a step past the
        previous label (so it never collides with it). A plain integer stride from 1 would label
        1, 11, 21 … — correct but not round, which is what makes a hand-drawn axis look amateur.

    Args:
        (1) count [int]: The number of positions (>= 0); position i is image number i + 1.
        (2) max_labels [int]: The most labels that fit without overlap (>= 2).

    Returns:
        (1) parameter [Vector<int>]: The 0-based indices to label, ascending, the first kept.
    """

    if count <= 0:
        return []
    if count <= max_labels or count <= 2:
        return list(range(count))
    step = __Nice_Number(count / float(max(1, max_labels - 1)), round_it=False)
    step = max(1, int(round(step)))
    numbers = [1] + [n for n in range(step, count + 1, step) if n > 1]
    # Drop a multiple that crowds image 1 (closer than half a step), then add the last image when
    # it clears the previous label by half a step.
    if len(numbers) > 1 and numbers[1] - numbers[0] < step / 2.0:
        numbers.pop(1)
    if count - numbers[-1] >= step / 2.0:
        numbers.append(count)
    return [n - 1 for n in numbers]
