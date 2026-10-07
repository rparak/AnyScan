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
# File Name: ../test/UI/test_paint_smoke.py
## =========================================================================== ##

# System (Default)
import os
import sys
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QEvent, QPointF
from PyQt5.QtGui import QMouseEvent, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget
# Custom Lib.: AnyScan UI — the painted widgets and the image conversion
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Widgets
from UI.Widgets import Icon_Cls, Viewport_Cls
#   ../UI/Views/Trends
from UI.Views.Trends import Trends_View_Cls
#   ../UI/Views/History
from UI.Views.History import History_Image_Cls
# Custom Lib.: AnyScan domain — the trend accumulator and the structures
#   ../Reporting/Trends
from Reporting.Trends import Trends_Accumulator_Cls
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Confidence_Thresholds_Str

"""
Description:
    Every paintEvent override, run. Coverage showed the Trends charts (series, grid, hover
    read-out), the viewport's image and busy overlay, and the History pane's image and highlight
    had never been painted by any test. That matters twice over: PyQt5 aborts the whole process
    on an unhandled exception inside a Qt override, so a paint error would crash the application
    and the suite would not see it. Each test renders the widget offscreen (grab) in every state
    and asserts the pixels change between states — so a paint path that silently draws nothing
    fails too — while the `paint_errors` fixture turns any exception raised inside a paint into a
    clean test failure instead of an abort.
"""


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def paint_errors(monkeypatch) -> tp.Iterator[tp.List[str]]:
    """
    Description:
        Collect exceptions raised inside Qt overrides and fail the test if there were any. PyQt5
        calls sys.excepthook for them when it has been replaced; left at the default it calls
        qFatal and the process aborts — which would take the whole run down with it.
    """

    errors = []
    monkeypatch.setattr(sys, 'excepthook', lambda kind, value, tb: errors.append('%s: %s' % (kind.__name__, value)))
    yield errors
    assert not errors, 'exceptions raised while painting:\n  ' + '\n  '.join(errors)


def _Grab(widget: QWidget) -> np.ndarray:
    """What the widget paints now, as an HxWx4 array."""
    QApplication.instance().processEvents()
    image = widget.grab().toImage().convertToFormat(4)          # QImage.Format_RGB32
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4).copy()


def _Centre_Colours(pixels: np.ndarray) -> int:
    """How many distinct colours the middle half of a grab holds (1 = nothing drawn but a fill; the
    rounded corners and hairline borders, which would count too, are cropped away)."""
    h, w = pixels.shape[:2]
    return len(np.unique(pixels[h // 4: 3 * h // 4, w // 4: 3 * w // 4].reshape(-1, 4), axis=0))


def _Share_Of(pixels: np.ndarray, rgb: tp.Tuple[int, int, int]) -> float:
    """The fraction of a grab's pixels within a hair of one RGB colour (grab bytes are B, G, R, A)."""
    bgr = np.array(rgb[::-1], dtype=np.int16)
    return float(np.mean(np.all(np.abs(pixels[..., :3].astype(np.int16) - bgr) <= 3, axis=-1)))


def _Move(widget: QWidget, x: float, y: float) -> None:
    """A mouse move over a widget (no button held), delivered to its mouseMoveEvent."""
    QApplication.sendEvent(widget, QMouseEvent(QEvent.MouseMove, QPointF(x, y), Qt.NoButton, Qt.NoButton,
                                               Qt.NoModifier))


def _Leave(widget: QWidget) -> None:
    """The cursor leaving a widget, delivered to its leaveEvent."""
    QApplication.sendEvent(widget, QEvent(QEvent.Leave))


# Two runs of four analyses each, with scored and unscored objects, one NOK and one empty frame.
# They share what frames the plot — four images, a final total of 7, one NOK — so the axes, ticks
# and legend come out identical and the two grabs can differ only where the series are drawn.
#   Unit [Vector<Vector<float or None>>]
CONST_RUN_A = ([0.92, 0.81, None], [0.55], [], [0.97, 0.66, 0.74])
CONST_RUN_B = ([0.61], [0.72, None, 0.55], [0.48, 0.85, 0.93], [])


def _Accumulator(run: tp.Sequence[tp.Sequence[tp.Optional[float]]] = CONST_RUN_A) -> Trends_Accumulator_Cls:
    """The trend accumulator fed one run (the 0.55 object is the NOK one)."""
    accumulator = Trends_Accumulator_Cls()
    for scores in run:
        accumulator.Add_Analysis([Detection_Str(Label='p', Bbox=(0, 0, 8, 8), Segmenter_Score=score,
                                                Verdict='NOK' if score == 0.55 else 'OK')
                                  for score in scores])
    return accumulator


def _Shown_Trends(classification: bool, accumulator: tp.Optional[Trends_Accumulator_Cls]) -> Trends_View_Cls:
    """The Trends view at a fixed size, shown offscreen, drawing the accumulator (or nothing)."""
    view = Trends_View_Cls(classification, Confidence_Thresholds_Str=Confidence_Thresholds_Str())
    if accumulator is not None:
        view.Set_Accumulator(accumulator)
    view.Refresh()
    view.resize(900, 760)
    view.show()
    QApplication.instance().processEvents()
    return view


def _Charts(view: Trends_View_Cls) -> tp.List[QWidget]:
    """The view's two chart canvases: objects, then confidence."""
    return [getattr(view, '_Trends_View_Cls__objects_chart'), getattr(view, '_Trends_View_Cls__confidence_chart')]


@pytest.mark.parametrize('classification', [False, True])
def test_trends_charts_paint_the_series_and_the_hover_readout(qt_app, paint_errors, classification) -> None:
    """
    Description:
        Both charts paint their data: against the same chart with no data, and — what isolates the
        series themselves — against a second run whose axes, ticks and legend are identical. The
        hover read-out paints over the plot when the cursor is on it, and leaving the chart removes
        it again. With and without classification (which adds the OK/NOK series and verdict dots).
    """

    empty = _Shown_Trends(classification, None)
    full = _Shown_Trends(classification, _Accumulator(CONST_RUN_A))
    other = _Shown_Trends(classification, _Accumulator(CONST_RUN_B))

    for blank, chart, twin in zip(_Charts(empty), _Charts(full), _Charts(other)):
        drawn = _Grab(chart)
        assert not np.array_equal(drawn, _Grab(blank))
        assert not np.array_equal(drawn, _Grab(twin))           # only the series differ

        _Move(chart, chart.width() / 2.0, chart.height() / 2.0)
        assert chart._hover is not None
        assert not np.array_equal(_Grab(chart), drawn)

        _Leave(chart)
        assert chart._hover is None
        assert np.array_equal(_Grab(chart), drawn)
    for view in (empty, full, other):
        view.close()


def _Qimage(value: tp.Tuple[int, int, int], size: tp.Tuple[int, int] = (320, 200)) -> tp.Any:
    """A solid RGB frame as a QImage, through the application's own conversion."""
    frame = np.zeros((size[1], size[0], 3), np.uint8)
    frame[:] = value
    frame[size[1] // 4: size[1] // 2, size[0] // 4: size[0] // 2] = (255, 255, 255)
    return Style.Rgb_To_Qimage(frame)


def test_viewport_paints_every_state(qt_app, paint_errors) -> None:
    """
    Description:
        The viewport paints its empty state, a frame, the busy overlay with its spinner (removed
        again when busy stops), and the annotated and mask renders — each visibly different.
    """

    viewport = Viewport_Cls()
    viewport.resize(640, 400)
    viewport.show()

    empty = _Grab(viewport)
    assert _Centre_Colours(empty) > 1                           # the mark and prompt, not a bare fill

    viewport.Show_Frame(_Qimage((40, 90, 160)))
    frame = _Grab(viewport)
    assert not np.array_equal(frame, empty)

    viewport.Start_Busy('Analysing…')
    busy = _Grab(viewport)
    assert not np.array_equal(busy, frame)
    viewport.Stop_Busy()
    assert np.array_equal(_Grab(viewport), frame)

    viewport.Show_Views(_Qimage((200, 40, 40)), _Qimage((10, 10, 10)), 'annotated', heatmap=None, legend=None)
    annotated = _Grab(viewport)
    viewport.Set_View('mask')
    mask = _Grab(viewport)
    assert not np.array_equal(annotated, frame)
    assert not np.array_equal(mask, annotated)
    viewport.close()


def test_history_pane_paints_the_message_the_image_and_the_highlight(qt_app, paint_errors) -> None:
    """
    Description:
        A History image pane paints its message when it has no image, the fitted image when it has
        one, and the selected object's highlight box over the image — each visibly different.
    """

    pane = History_Image_Cls()
    pane.resize(480, 320)
    pane.show()

    pane.Set_Image(None, 'No annotated image.')
    message = _Grab(pane)
    assert _Centre_Colours(message) > 1                         # the text, not a bare fill

    pane.Set_Image(QPixmap.fromImage(_Qimage((40, 90, 160))))
    image = _Grab(pane)
    assert not np.array_equal(image, message)
    assert _Share_Of(image, (40, 90, 160)) > 0.25               # the image's own pixels are there

    pane.Set_Highlight((20, 20, 80, 60))
    assert not np.array_equal(_Grab(pane), image)
    pane.Set_Highlight(None)
    assert np.array_equal(_Grab(pane), image)
    pane.close()


def test_card_icons_paint_each_kind(qt_app, paint_errors) -> None:
    """
    Description:
        Every card-head icon kind paints strokes (more than a bare fill), and the kinds differ.
    """

    grabs = {}
    for kind in ('camera', 'reading', 'cube'):
        icon = Icon_Cls(kind, size=44)
        icon.show()
        grabs[kind] = _Grab(icon)
        icon.close()
        assert _Centre_Colours(grabs[kind]) > 1, kind
    assert not np.array_equal(grabs['camera'], grabs['reading'])
    assert not np.array_equal(grabs['reading'], grabs['cube'])
