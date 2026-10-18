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


def test_the_confidence_dots_take_their_states_frame_colour_with_no_darker_edge(qt_app) -> None:
    """
    Description:
        In a catalogue run each object's confidence dot is drawn in exactly its state's frame colour — every Warning, of
        any kind, the amber — its edge that same colour, no darker ring (the owner's rule of 2026-10-18): across the dot,
        out to its edge, every pixel is the one blend of the amber on the card; neither the retired grey and blue nor a
        darker chart variant is painted.
    """

    from Reporting.Trends import Trends_Accumulator_Cls
    from UI.Views.Trends import Confidence_Chart_Cls
    from Parameters.Theme import Verdict_Color
    from Parameters.Vision import Catalogue_Result_Str, Confidence_Thresholds_Str
    objects = [Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=score, Verdict='Warning',
                             Catalogue=Catalogue_Result_Str(Warning_Kind=kind))
               for score, kind in ((0.95, 'outside'), (0.55, 'foreign'), (0.25, 'several_parts'))]
    acc = Trends_Accumulator_Cls()
    acc.Add_Analysis(objects)
    chart = Confidence_Chart_Cls()
    chart.resize(600, 300)
    chart.Set_Data(acc.Images(), True, Confidence_Thresholds_Str=Confidence_Thresholds_Str())
    image = chart.grab().toImage()
    pixels = [image.pixelColor(x, y).getRgb()[:3] for x in range(image.width()) for y in range(image.height())]

    def Near(hex_color: str, tolerance: int) -> bool:
        target = tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
        return any(max(abs(a - b) for a, b in zip(pixel, target)) <= tolerance for pixel in pixels)

    # A dot is the amber at alpha 220 over the white card.
    amber = tuple(int(Verdict_Color('Warning')[0][i:i + 2], 16) for i in (1, 3, 5))
    dot = tuple(round(c * 220 / 255 + 255 * (1 - 220 / 255)) for c in amber)
    assert Near('#%02X%02X%02X' % dot, 3)
    for retired in ('#B4A6BE', '#33A3FF', '#42374B', '#003E6C', '#7C5B00', '#4F4952', '#0065A9') + CONST_OLD_EDGES:
        assert not Near(retired, 10), retired
    # Round the top dot (0.95), its edge included, no pixel is darker than the dot's fill (relative luminance): no ring.
    from Parameters.Theme import Relative_Luminance
    rect = chart._Plot_Rect()
    cy = int(round(chart._Px_Y(95, rect)))
    hits = [x for x in range(image.width())
            if max(abs(a - b) for a, b in zip(image.pixelColor(x, cy).getRgb()[:3], dot)) <= 3]
    assert hits
    middle = hits[len(hits) // 2]
    floor = Relative_Luminance('#%02X%02X%02X' % dot) - 0.02
    around = [image.pixelColor(x, y).name() for x in range(middle - 6, middle + 7) for y in range(cy - 6, cy + 7)]
    assert all(Relative_Luminance(c) >= floor for c in around), sorted(set(around))
