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
# File Name: ../test/UI/test_trends_view.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
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
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The Trends view wired into the window (§6): the charts and the status bar read ONE
    accumulator, so the last point of each series equals the matching status figure exactly; a
    failed analysis advances neither; unscored objects never reach the confidence chart; and
    Clear empties the charts with the aggregates. No camera and no weights needed.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

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
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
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
        Unscored objects never enter the confidence means (a 0% would be a false low reading); they
        are carried only as a count for the hover, beside the scored objects the means are taken over.
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


# The dark edges the chart markers and legend swatches had until 2026-10-18 (each state's hue at L* 25): OK, NOK,
# Warning. None may be painted now.
#   Unit [Tuple<string>] (hex colour)
CONST_OLD_EDGES = ('#5300A3', '#7A0E00', '#4D3800')


def test_a_catalogue_run_charts_ok_nok_and_warning(qt_app, tmp_path) -> None:
    """
    Description:
        In a catalogue mode the objects chart draws a series per state beside the total — OK, NOK and Warning, every
        kind of Warning in the one series — named in its legend and its hover, so the three add up to the total;
        rendered, every state's series paints exactly its frame mark's colour (the owner's rule: one colour per state),
        its markers and legend swatches edged in that same colour (the owner's rule of 2026-10-18: no darker edge), and
        neither the retired grey and blue nor a darker chart variant appears. Segment Anything charts the total alone.
    """

    from Reporting.Trends import Trends_Accumulator_Cls
    from UI.Views.Trends import Objects_Chart_Cls
    from PyQt5.QtGui import QColor
    from Parameters.Theme import Verdict_Color
    from Parameters.Vision import Catalogue_Result_Str
    objects = [Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=0.9, Verdict=verdict.partition('-')[0],
                             Catalogue=Catalogue_Result_Str(Warning_Kind=verdict.partition('-')[2]))
               for verdict in ('OK', 'Warning-outside', 'Warning-foreign', 'NOK', 'Warning-several_parts',
                               'Warning-side_unknown')]
    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis(objects)
    chart = Objects_Chart_Cls()
    chart.resize(600, 300)
    chart.Set_Data(acc.Images(), True)
    assert [label for label, _color in chart._legend] == ['Total', 'OK', 'NOK', 'Warning']
    assert chart._Hover_Lines(0)[-1][0] == 'OK 1 · NOK 1 · Warning 4'
    image = chart.grab().toImage()
    painted = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())}
    for state in ('OK', 'NOK', 'Warning'):
        assert Verdict_Color(state)[0].lower() in painted, state                  # the frame mark's colour itself
    for retired in ('#B4A6BE', '#33A3FF', '#42374B', '#003E6C', '#7C5B00', '#4F4952', '#0065A9', '#BA260B') + CONST_OLD_EDGES:
        assert retired.lower() not in painted, retired
    assert dict(chart._legend)['Warning'] == '#FFC226'
    # The marker's edge is its fill: round the Warning point (image 1, four objects), its edge included, no pixel is
    # darker than the amber (relative luminance; the old edge #4D3800 was 0.04 against the amber's 0.62).
    from Parameters.Theme import Relative_Luminance
    rect = chart._Plot_Rect()
    cx, cy = int(round(chart._Px_X(1.0, rect))), int(round(chart._Px_Y(4.0, rect)))
    amber = QColor(Verdict_Color('Warning')[0])
    around = [image.pixelColor(x, y) for x in range(cx - 6, cx + 7) for y in range(cy - 6, cy + 7)]
    assert sum(c == amber for c in around) >= 20
    floor = Relative_Luminance(amber.name()) - 0.02
    assert all(Relative_Luminance(c.name()) >= floor for c in around), sorted({c.name() for c in around})
    chart.Set_Data(acc.Images(), False)
    assert [label for label, _color in chart._legend] == ['Total']


def test_the_warning_threshold_line_is_not_the_warning_verdicts_amber(qt_app, reference_background_path) -> None:
    """
    Description:
        The confidence chart's dashed warning-threshold line is painted in the neutral mid ink, not the amber a
        catalogue mode's Warning dots take, so an amber dot is never read as part of the line (the clash recorded
        in KNOWN_ISSUES until 2026-10-11): rendered, the chart holds the ink and no amber.
    """

    import Parameters.Theme as Theme
    window = _Window(reference_background_path)
    for scores in ([0.91, 0.72], [0.88, 0.95]):
        _Private(window, '__On_Analysis_Finished')(_Result(scores))
    view = _Private(window, '__trends_view')
    chart = _Private(view, '__confidence_chart', '_Trends_View_Cls')
    chart.resize(600, 320)
    image = chart.grab().toImage().convertToFormat(4)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    pixels = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :, :3]
    # By hue, not exact colour: the one-pixel dashed lines are antialiased. Amber (and its blends with the card)
    # is red well over green well over blue; the error line's deep red has green and blue alike.
    b, g, r = (pixels.reshape(-1, 3).astype(int)[:, k] for k in range(3))
    amber = int(((r - g > 40) & (g - b > 30)).sum())
    ink = int((np.abs(pixels.reshape(-1, 3).astype(int) - np.array(Theme.Hex_To_Bgr(Theme.CONST_INK_SOFT))).max(axis=1)
               <= 40).sum())
    assert ink > 0 and amber == 0


def _Confidence(frames: tp.List[tp.List[tp.Tuple[float, str]]], width: int = 900, height: int = 320) -> tp.Tuple:
    """The confidence chart, alone, after one analysis per frame of (score, verdict) objects, rendered."""
    from Reporting.Trends import Trends_Accumulator_Cls
    from UI.Views.Trends import Confidence_Chart_Cls
    from Parameters.Vision import Catalogue_Result_Str, Confidence_Thresholds_Str
    acc = Trends_Accumulator_Cls()
    for objects in frames:
        acc.Add_Analysis([Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=score, Verdict=verdict,
                                        Catalogue=Catalogue_Result_Str(Warning_Kind='foreign' if verdict == 'Warning' else ''))
                          for score, verdict in objects])
    chart = Confidence_Chart_Cls()
    chart.resize(width, height)
    chart.Set_Data(acc.Images(), Confidence_Thresholds_Str=Confidence_Thresholds_Str())
    return chart, chart.grab().toImage(), acc.Images()


def _Near(image, x: float, y: float, hex_color: str, tolerance: int = 12, reach: int = 0) -> bool:
    """Whether a pixel within `reach` of (x, y) is the colour, each channel within the tolerance."""
    target = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    for dx in range(-reach, reach + 1):
        for dy in range(-reach, reach + 1):
            rgb = image.pixelColor(int(round(x)) + dx, int(round(y)) + dy).getRgb()[:3]
            if max(abs(a - b) for a, b in zip(rgb, target)) <= tolerance:
                return True
    return False


def test_the_confidence_chart_draws_only_the_frame_and_run_means(qt_app) -> None:
    """
    Description:
        The confidence chart draws two series and nothing per object (the owner's rule of 2026-10-18): the frame
        mean and the run mean, in the theme's neutral colours (CONST_INK_MUTE, Detection_Mask_Outline), never a verdict
        colour, and its legend names exactly those two in those colours. Rendered on a catalogue run of OK, NOK and
        Warning objects scored far from their means: no verdict colour is painted, and nothing is painted at an
        object's own score away from the mean lines (the old dots), nor beyond the last analysed image.
    """

    import Parameters.Theme as Theme
    frames = [[(0.95, 'OK'), (0.40, 'NOK'), (0.30, 'Warning')], [(0.96, 'Warning'), (0.42, 'OK')],
              [(0.94, 'NOK'), (0.38, 'Warning')]]
    chart, image, rows = _Confidence(frames)
    assert chart._legend == [('Frame mean', Theme.CONST_INK_MUTE), ('Run mean', Theme.Detection_Mask_Outline())]
    assert chart._legend_marks == {'Frame mean': 'line_marker', 'Run mean': 'dashed'}
    # The legend draws each series as its line, not a 9 px swatch: along the legend's row, a horizontal run of 12 px
    # or more in each colour (the frame mean's solid sample, a dash of the run mean's).
    top = chart._Plot_Rect().top()

    def Longest(colour: str) -> int:
        best = 0
        for y in range(int(top) - 26, int(top) - 8):
            run = 0
            for x in range(image.width()):
                run = run + 1 if _Near(image, x, y, colour, 10) else 0
                best = max(best, run)
        return best

    assert Longest(Theme.CONST_INK_MUTE) >= 12 and Longest(Theme.Detection_Mask_Outline()) >= 12
    assert not {colour for _label, colour in chart._legend} & {Theme.Verdict_Color(v)[0] for v in ('OK', 'NOK', 'Warning')}
    rect = chart._Plot_Rect()
    painted = {image.pixelColor(x, y).name() for x in range(image.width()) for y in range(image.height())}
    for verdict in ('NOK', 'Warning'):
        assert Theme.Verdict_Color(verdict)[0].lower() not in painted, verdict
    for row, objects in zip(rows, frames):
        for score, _verdict in objects:
            y = chart._Px_Y(100 * score, rect)
            # Each score lies 25 points or more from its frame's mean: nothing is drawn there, in its column.
            for dx in range(-30, 31, 3):
                assert not _Near(image, chart._Px_X(row.Index, rect) + dx, y, Theme.CONST_INK_MUTE, 40), (row.Index, score)
                assert not _Near(image, chart._Px_X(row.Index, rect) + dx, y, Theme.Detection_Mask_Outline(), 40), (row.Index, score)
    beyond = chart._Px_X(len(rows), rect) + 8
    for x in range(int(beyond), int(rect.right()) - 1):
        for y in range(int(rect.top()) + 2, int(rect.bottom()) - 2):
            colour = image.pixelColor(x, y)
            assert not (_Near(image, x, y, Theme.CONST_INK_MUTE, 30) or _Near(image, x, y, Theme.Detection_Mask_Outline(), 30)), \
                (x, y, colour.name())


def test_the_two_means_are_told_apart_when_they_are_equal(qt_app) -> None:
    """
    Description:
        When every frame scores alike the frame mean and the run mean are equal at every image, and both still read:
        the frame mean is a thin solid line with a marker at every analysed image, its edge the marker's own colour
        (no darker ring); the run mean a thicker dashed line without markers, drawn under it, so its dashes show past
        the thin line on either side, broken by gaps. Rendered, at the means' height.
    """

    import Parameters.Theme as Theme
    from Parameters.Theme import Relative_Luminance
    chart, image, rows = _Confidence([[(0.9, 'OK'), (0.9, 'OK')]] * 4)
    assert {row.Frame_Mean for row in rows} == {row.Run_Mean for row in rows} == {90}
    rect = chart._Plot_Rect()
    y = chart._Px_Y(90, rect)
    frame, run = Theme.CONST_INK_MUTE, Theme.Detection_Mask_Outline()
    for row in rows:
        x = chart._Px_X(row.Index, rect)
        # A marker: the frame mean's colour over at least 5 px in its column (the 1.5 px line alone covers about 2).
        extent = sum(_Near(image, x, y + dy, frame, 20) for dy in range(-6, 7))
        assert extent >= 5, (row.Index, extent)
        floor = Relative_Luminance(frame) - 0.02
        around = [image.pixelColor(int(round(x)) + dx, int(round(y)) + dy).name()
                  for dx in range(-5, 6) for dy in range(-5, 6)]
        assert all(Relative_Luminance(c) >= floor for c in around), (row.Index, sorted(set(around)))
    # Between images 1 and 2, 2 px above the line (outside the thin frame line, inside the 5 px run line): the run
    # mean's own colour in its dashes, and in the gaps between them the chart's plain ground (read 6 px above).
    left, right = int(chart._Px_X(1, rect)) + 8, int(chart._Px_X(2, rect)) - 8
    dashes = sum(_Near(image, x, y - 2, run, 10) for x in range(left, right))
    gaps = sum(_Near(image, x, y - 2, image.pixelColor(x, int(round(y - 6))).name(), 6) for x in range(left, right))
    assert dashes > 20 and gaps > 10, (dashes, gaps)


def test_each_threshold_line_is_labelled_with_what_it_means(qt_app) -> None:
    """
    Description:
        The two dashed reference lines are the configuration's confidence thresholds, which colour every confidence
        number in the application: each is labelled at the plot's right end, just above the line and in its colour,
        'Warning below 80 %' and 'Error below 60 %' (the thresholds in force). Rendered: text in each line's colour
        stands above its right end, where the line alone drew one dashed pixel row.
    """

    import Parameters.Theme as Theme
    chart, image, _rows = _Confidence([[(0.9, 'OK')]])
    assert chart._Reference_Labels() == [(80, 'Warning below 80 %', Theme.CONST_INK_SOFT),
                                         (60, 'Error below 60 %', Theme.CONST_LOG_ERROR)]
    rect = chart._Plot_Rect()
    for value, _text, colour in chart._Reference_Labels():
        y = int(round(chart._Px_Y(value, rect)))
        ink = sum(_Near(image, x, yy, colour, 60) for x in range(int(rect.right()) - 140, int(rect.right()))
                  for yy in range(y - 14, y - 2))
        assert ink > 40, (value, ink)
