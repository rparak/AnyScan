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
# File Name: ../test/UI/test_camera_view.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window; domain — the camera, the vision base, the result
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Core
from Vision.Core import Vision_Backend_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str, Detection_Str, Heatmap_Str
#   ../Parameters/Theme
import Parameters.Theme as Theme
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Headless (offscreen) tests for the Camera View annotated/mask toggle (§2b), driven
    through the window's completion slot directly (no QThread — the threading guarantees
    live in test_threading.py). They assert: the toggle is hidden before an analysis and
    shown/enabled after; switching swaps the view WITHOUT invoking the pipeline; the
    chosen view persists across a second analysis; and a stale frame (a new scan or a
    disconnect) drops the renders and hides the toggle. No camera and no weights needed.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'


class _Counting_Vision_Cls(Vision_Backend_Cls):
    """A vision backend that counts Analyze calls and returns an empty reading."""

    Name = 'Counting'

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    def Analyze(self, image, progress_cb=None, stage_cb=None) -> Analysis_Str:
        self.calls += 1
        return Analysis_Str(Objects=[], Verdict='Empty',
                            Verdict_Level='idle', Task='count')


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Private(window, name: str):
    """Fetch a name-mangled private attribute or method of the window."""
    return getattr(window, CONST_MANGLE + name)


def _Scanned_Window(reference_background_path):
    """A window with the camera connected, a frame scanned, and a counting backend."""
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    setattr(window, CONST_MANGLE + '__vision', _Counting_Vision_Cls())
    _Private(window, '__camera').Connect()
    _Private(window, '__Sync_Controls')()
    _Private(window, '__On_Scan_Button_Clicked')()
    return window


def _Grab(widget) -> np.ndarray:
    """What the widget paints now, as an HxWx4 array (the pixels, not its state)."""
    QApplication.instance().processEvents()
    image = widget.grab().toImage().convertToFormat(4)          # QImage.Format_RGB32
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4).copy()


def _Result() -> Analysis_Str:
    """An empty finished reading (both renders are valid for zero objects)."""
    return Analysis_Str(Objects=[], Verdict='Empty',
                        Verdict_Level='idle', Task='t')


def test_toggle_hidden_before_analysis_and_shown_after(qt_app, reference_background_path) -> None:
    """
    Description:
        The toggle is nothing to act on before an analysis, so it is hidden; once an
        analysis has delivered both renders it is visible and enabled.
    """

    window = _Scanned_Window(reference_background_path)
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')

    assert toggle.isHidden()
    assert not viewport.Has_Views()

    _Private(window, '__On_Analysis_Finished')(_Result())

    assert viewport.Has_Views()
    assert not toggle.isHidden() and toggle.isEnabled()


def test_switching_view_does_not_invoke_the_pipeline(qt_app, reference_background_path) -> None:
    """
    Description:
        Switching between annotated and mask swaps the held render in place — it must
        never re-run analysis. The backend's Analyze is never called by a view switch.
    """

    window = _Scanned_Window(reference_background_path)
    vision = _Private(window, '__vision')
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())

    assert vision.calls == 0                       # the completion slot was called directly
    annotated = _Grab(viewport)

    _Private(window, '__On_View_Toggle')('mask')
    assert not np.array_equal(_Grab(viewport), annotated)       # the mask render is what is painted
    _Private(window, '__On_View_Toggle')('annotated')
    assert np.array_equal(_Grab(viewport), annotated)           # and the annotated one again, exactly

    assert vision.calls == 0                       # no switch touched the pipeline


def test_selected_view_persists_across_a_second_analysis(qt_app, reference_background_path) -> None:
    """
    Description:
        An operator working in mask view is not thrown back to annotated by the next
        Analyze: the remembered choice is reapplied when the second analysis completes.
    """

    window = _Scanned_Window(reference_background_path)
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())
    annotated = _Grab(viewport)
    _Private(window, '__On_View_Toggle')('mask')
    mask = _Grab(viewport)
    assert not np.array_equal(mask, annotated)

    # A second analysis of the same session: the mask is still what is painted.
    _Private(window, '__On_Analysis_Finished')(_Result())
    assert np.array_equal(_Grab(viewport), mask)


def test_a_new_scan_makes_the_result_stale_and_hides_the_toggle(qt_app, reference_background_path) -> None:
    """
    Description:
        The staleness rule: a new frame's annotations would not line up with the old
        scene, so a new scan drops the renders and hides the toggle rather than showing
        a previous frame's overlay over a new one.
    """

    window = _Scanned_Window(reference_background_path)
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())
    assert not toggle.isHidden()

    _Private(window, '__On_Scan_Button_Clicked')()   # a new frame arrives
    assert not viewport.Has_Views()
    assert toggle.isHidden()


def test_disconnect_drops_the_result_and_hides_the_toggle(qt_app, reference_background_path) -> None:
    """
    Description:
        A camera disconnect clears the frame, so any held analysis is stale: the renders
        are dropped and the toggle hidden.
    """

    window = _Scanned_Window(reference_background_path)
    toggle = _Private(window, '__view_toggle')
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Result())
    assert not toggle.isHidden()

    _Private(window, '__On_Disconnect_Button_Clicked')()
    assert not viewport.Has_Views()
    assert toggle.isHidden()


def _Heatmap_Result(window, right: int, marks: tp.Sequence[tp.Tuple[float, str]] = ((51.0, 'Otsu 51'),),
                    objects: tp.Sequence[Detection_Str] = ()) -> Analysis_Str:
    """A finished reading whose heatmap is 0 on the frame's left half and `right` on its right half."""
    height, width = _Private(window, '__frame').shape[:2]
    values = np.zeros((height, width), dtype=np.uint8)
    values[:, width // 2:] = right
    return Analysis_Str(Objects=list(objects), Verdict='Empty', Verdict_Level='idle', Task='t',
                        Heatmap=Heatmap_Str(Values=values, Low=0.0, High=128.0, Title='Difference from the reference',
                                            Unit='grey level', Marks=list(marks)))


def _Painted(viewport, grab: np.ndarray, fx: float, fy: float) -> tp.Tuple[int, int, int]:
    """The BGR painted at a fraction (fx, fy) of where the viewport draws its image."""
    rect = getattr(viewport, '_Viewport_Cls__Draw_Rect')()
    scale = grab.shape[0] / viewport.height()
    x, y = int((rect.left() + fx * rect.width()) * scale), int((rect.top() + fy * rect.height()) * scale)
    return tuple(int(v) for v in grab[y, x, :3])


def _Close(painted: tp.Tuple[int, int, int], hex_color: str) -> bool:
    """Whether a painted BGR is the theme colour, within smooth scaling's rounding."""
    return max(abs(a - b) for a, b in zip(painted, Theme.Hex_To_Bgr(hex_color))) <= 3


def _Legend(grab: np.ndarray, viewport) -> np.ndarray:
    """The viewport's bottom-left corner, where the legend is painted (320 x 110 px)."""
    scale = grab.shape[0] / viewport.height()
    return grab[grab.shape[0] - int(110 * scale):, :int(320 * scale)]


def test_the_heatmap_view_paints_each_value_in_its_colour_on_the_fixed_scale(qt_app, reference_background_path) -> None:
    """
    Description:
        Choosing Heatmap paints the heatmap: a difference of 0 in the theme's first heatmap colour, 64 in
        its middle one, 128 in its last — on a FIXED scale, so the half that stays 0 keeps its colour when
        the other half gets hotter, and 64 is never stretched to the top colour because it is the frame's
        maximum.
    """

    window = _Scanned_Window(reference_background_path)
    viewport = _Private(window, '__viewport')
    colors = Theme.Heatmap_Colors()
    _Private(window, '__On_Analysis_Finished')(_Heatmap_Result(window, right=64))
    _Private(window, '__On_View_Toggle')('heatmap')
    grab = _Grab(viewport)
    assert _Close(_Painted(viewport, grab, 0.25, 0.4), colors[0])
    assert _Close(_Painted(viewport, grab, 0.75, 0.4), colors[128])

    _Private(window, '__On_Analysis_Finished')(_Heatmap_Result(window, right=128))
    grab = _Grab(viewport)
    assert _Close(_Painted(viewport, grab, 0.25, 0.4), colors[0])
    assert _Close(_Painted(viewport, grab, 0.75, 0.4), colors[255])


def test_the_legend_marks_the_threshold_and_shows_only_on_the_heatmap(qt_app, reference_background_path) -> None:
    """
    Description:
        Two readings that differ only in the threshold marked on the legend render differently in the
        legend's corner of the heatmap view, and identically above it; the same threshold renders
        identically. In the annotated view the two are identical everywhere: the legend belongs to the
        heatmap.
    """

    window = _Scanned_Window(reference_background_path)
    viewport = _Private(window, '__viewport')
    finished = _Private(window, '__On_Analysis_Finished')
    _Private(window, '__On_View_Toggle')('heatmap')
    grabs = {}
    for name, marks in (('30', ((30.0, 'Otsu 30'),)), ('60', ((60.0, 'Otsu 60'),)), ('60 again', ((60.0, 'Otsu 60'),))):
        finished(_Heatmap_Result(window, right=64, marks=marks))
        _Private(window, '__On_View_Toggle')('heatmap')
        heatmap = _Grab(viewport)
        _Private(window, '__On_View_Toggle')('annotated')
        grabs[name] = (heatmap, _Grab(viewport))
    (heat_30, annotated_30), (heat_60, annotated_60), (heat_again, annotated_again) = grabs['30'], grabs['60'], grabs['60 again']
    assert not np.array_equal(_Legend(heat_30, viewport), _Legend(heat_60, viewport))
    half = heat_30.shape[0] // 2
    assert np.array_equal(heat_30[:half], heat_60[:half])
    assert np.array_equal(heat_60, heat_again)
    assert np.array_equal(annotated_30, annotated_60)
    assert np.array_equal(annotated_60, annotated_again)


def test_the_legend_labels_are_the_purple_on_its_grey_lilac_panel(qt_app, reference_background_path) -> None:
    """
    Description:
        The legend's labels under the colour bar (its two ends and the threshold's name) are the purple on the
        legend's grey-lilac panel, where white read at 1.35:1: the strip they are printed in carries the purple and
        no white pixel, though the threshold's white tick crosses the bar above it.
    """

    window = _Scanned_Window(reference_background_path)
    viewport = _Private(window, '__viewport')
    _Private(window, '__On_Analysis_Finished')(_Heatmap_Result(window, right=64, marks=((60.0, 'Otsu 60'),)))
    _Private(window, '__On_View_Toggle')('heatmap')
    legend = _Legend(_Grab(viewport), viewport)[:, :, 2::-1].astype(int)          # RGB
    tick = np.nonzero((legend >= 245).all(axis=2).any(axis=1))[0]                # the white tick's rows
    assert len(tick)                                                             # the tick is still drawn
    labels = legend[tick.max() + 1:tick.max() + 21]                              # the label line under the bar
    purple = np.array(Theme.Hex_To_Rgb(Theme.CONST_VIEWPORT_TEXT))
    assert np.abs(labels - purple).max(axis=2).min() <= 40
    assert not (labels >= 245).all(axis=2).any()


def test_the_heatmap_shows_the_difference_alone_with_no_boxes(qt_app, reference_background_path) -> None:
    """
    Description:
        The heatmap is the difference image alone: a reading with a located object renders the same
        heatmap as one without, while its annotated view does show the object's box.
    """

    window = _Scanned_Window(reference_background_path)
    viewport = _Private(window, '__viewport')
    part = Detection_Str(Label='ring', Bbox=(300, 300, 400, 300), Sentence='A ring.', Segmenter_Score=0.9, Cue='both')
    grabs = []
    for objects in ((), (part,)):
        _Private(window, '__On_Analysis_Finished')(_Heatmap_Result(window, right=64, objects=objects))
        _Private(window, '__On_View_Toggle')('heatmap')
        heatmap = _Grab(viewport)
        _Private(window, '__On_View_Toggle')('annotated')
        grabs.append((heatmap, _Grab(viewport)))
    (heat_empty, annotated_empty), (heat_part, annotated_part) = grabs
    assert np.array_equal(heat_empty, heat_part)
    assert not np.array_equal(annotated_empty, annotated_part)


def test_without_a_heatmap_its_segment_is_unavailable_and_the_choice_waits(qt_app, reference_background_path) -> None:
    """
    Description:
        A reading that brought no heatmap paints the annotated view even when the operator had chosen the
        heatmap, and the toggle renders differently (its heatmap segment disabled). The choice is kept:
        the next reading with a heatmap is shown as a heatmap again.
    """

    window = _Scanned_Window(reference_background_path)
    viewport, toggle = _Private(window, '__viewport'), _Private(window, '__view_toggle')
    finished = _Private(window, '__On_Analysis_Finished')
    finished(_Heatmap_Result(window, right=64))
    _Private(window, '__On_View_Toggle')('heatmap')
    toggle_available = _Grab(toggle)

    finished(_Result())
    shown = _Grab(viewport)
    assert not np.array_equal(_Grab(toggle), toggle_available)

    finished(_Heatmap_Result(window, right=128))                    # no toggle between: the choice was kept
    assert _Close(_Painted(viewport, _Grab(viewport), 0.75, 0.4), Theme.Heatmap_Colors()[255])

    finished(_Result())
    _Private(window, '__On_View_Toggle')('annotated')
    assert np.array_equal(shown, _Grab(viewport))                   # what was shown was the annotated view


def test_the_similarity_view_overlays_the_frame_and_needs_a_catalogue_reading(qt_app, reference_background_path) -> None:
    """
    Description:
        A catalogue reading's similarity map is its own view: Similarity paints the frame with the map's colours
        over the covered half only (the other half is the frame), under its own legend; a reading without one
        leaves its segment disabled and shows the annotated view, keeping the choice for the next.
    """

    window = _Scanned_Window(reference_background_path)
    viewport, toggle = _Private(window, '__viewport'), _Private(window, '__view_toggle')
    finished = _Private(window, '__On_Analysis_Finished')
    height, width = _Private(window, '__frame').shape[:2]
    values = np.full((height, width), np.nan, dtype=np.float32)
    values[:, width // 2:] = 0.5
    reading = _Result()
    reading.Similarity = Heatmap_Str(Values=values, Low=0.0, High=0.5, Title='Unlike the reference — not a defect map',
                                     Unit='1 − cosine')
    finished(_Result())
    _Private(window, '__On_View_Toggle')('similarity')
    without = (_Grab(viewport), _Grab(toggle))
    finished(reading)
    _Private(window, '__On_View_Toggle')('similarity')
    grab = _Grab(viewport)
    assert not np.array_equal(_Grab(toggle), without[1])                 # the segment became available
    assert _Painted(viewport, grab, 0.25, 0.3) == _Painted(viewport, without[0], 0.25, 0.3)   # the frame itself
    assert _Painted(viewport, grab, 0.75, 0.3) != _Painted(viewport, without[0], 0.75, 0.3)   # the overlay
    assert not np.array_equal(_Legend(grab, viewport), _Legend(without[0], viewport))         # its legend
