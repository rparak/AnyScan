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
# File Name: ../test/UI/test_busy_overlay.py
## =========================================================================== ##

# System (Default)
import os
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QColor, QImage
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the viewport, the busy icons and the style tokens
#   ../UI/Widgets, ../UI/Utilities/Pixel_Motif, ../UI/Utilities/Style
from UI.Widgets import Viewport_Cls
from UI.Utilities.Pixel_Motif import CONST_BUSY_ICONS
import UI.Utilities.Style as Style

"""
Description:
    The Camera View's busy overlay (the owner's choice, 2026-10-15): the view's grey-lilac at 70 % over the frame, so the
    frame shows through, with the task's pixel icon and the step's words in the purple directly on it, and nothing of
    the empty view's mark or instruction under it. Measured on the painted viewport.
"""
# The viewport's size in the tests, and the frame shown in it: the same 3:2 shape, so the frame fills the view.
#   Unit [Tuple<int> 1x2] (px) / [string] (hex colour, the green table's median)
CONST_SIZE = (600, 400)
CONST_TABLE = '#186550'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Pixels(viewport: Viewport_Cls) -> np.ndarray:
    """
    The viewport as painted, RGB, one pixel per logical pixel: at a DPR of n the grab holds n x n device pixels for
    each, and the top-left one is taken (the fills sit on whole logical pixels, so each block is one colour).
    """
    image = viewport.grab().toImage().convertToFormat(QImage.Format_RGB32)
    ratio = max(1, round(image.devicePixelRatio()))
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    array = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return array[::ratio, :image.width():ratio, 2::-1].astype(int)


def _Hex(token: str) -> np.ndarray:
    """A '#rrggbb' token as an RGB array."""
    return np.array([int(token[i:i + 2], 16) for i in (1, 3, 5)])


def _Viewport(frame: tp.Optional[str]) -> Viewport_Cls:
    """A viewport of CONST_SIZE showing a frame of one colour, or empty when frame is None."""
    viewport = Viewport_Cls()
    viewport.resize(*CONST_SIZE)
    if frame is not None:
        image = QImage(CONST_SIZE[0], CONST_SIZE[1], QImage.Format_RGB32)
        image.fill(QColor(frame))
        viewport.Show_Frame(image)
    return viewport


def _Icon_Box(pixels: np.ndarray) -> tp.Tuple[int, int, int, int]:
    """The bounding box (left, top, right, bottom) of the purple cells above the view's centre."""
    upper = pixels[:CONST_SIZE[1] // 2]
    ys, xs = np.nonzero(np.abs(upper - _Hex(Style.CONST_BUSY_INK)).max(axis=2) <= 2)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def test_the_overlay_is_the_grey_lilac_with_the_frame_showing_through(qt_app) -> None:
    """
    Description:
        Away from the icon and the words, the busy view is the grey-lilac at 70 % over the frame: the frame shows
        through (the pixel is not the grey-lilac) and the blend is the token's opacity, within rounding.
    """

    viewport = _Viewport(CONST_TABLE)
    viewport.Start_Busy('Analysing object 1 of 2…', 'magnifier')
    corner = _Pixels(viewport)[10, 10]
    viewport.Stop_Busy()
    expected = 0.70 * _Hex(Style.CONST_VIEWPORT) + 0.30 * _Hex(CONST_TABLE)
    assert Style.CONST_BUSY_SCRIM == Style.CONST_VIEWPORT and Style.CONST_BUSY_SCRIM_ALPHA == 0.70
    assert np.abs(corner - expected).max() <= 2, corner
    assert np.abs(corner - _Hex(Style.CONST_VIEWPORT)).max() > 20


def test_the_task_icon_is_painted_cell_for_cell_in_the_purple_above_the_step(qt_app) -> None:
    """
    Description:
        The busy view paints the named task's pixel icon in the purple: its solid cells are whole squares of
        CONST_BUSY_CELL, laid out as the icon's rows, above the line the step is printed on; the camera and the
        magnifier are different pictures; the step's words are purple and nothing on the overlay is white.
    """

    cell = Viewport_Cls.CONST_BUSY_CELL
    for kind, (rows, _steps, _ticks) in CONST_BUSY_ICONS.items():
        viewport = _Viewport(CONST_TABLE)
        viewport.Start_Busy('Connecting to camera…', kind)
        pixels = _Pixels(viewport)
        viewport.Stop_Busy()
        left, top, right, bottom = _Icon_Box(pixels)
        assert (right - left, bottom - top) == (len(rows[0]) * cell, len(rows) * cell), kind
        assert bottom <= CONST_SIZE[1] // 2 + 14, kind                             # above the step's line
        for row, line in enumerate(rows):
            for column, mark in enumerate(line):
                square = pixels[top + row * cell:top + (row + 1) * cell, left + column * cell:left + (column + 1) * cell]
                is_purple = np.abs(square - _Hex(Style.CONST_BUSY_INK)).max() <= 2
                assert is_purple == (mark == '#') or mark.isdigit(), (kind, row, column)
        band = pixels[CONST_SIZE[1] // 2 + 14:CONST_SIZE[1] // 2 + 54]
        assert np.abs(band - _Hex(Style.CONST_BUSY_INK)).max(axis=2).min() <= 40, kind     # the words, antialiased
        assert not (pixels >= 245).all(axis=2).any(), kind                                     # no white anywhere


def test_the_icon_steps_with_the_timer_and_a_static_step_stays_still(qt_app) -> None:
    """
    Description:
        While animated, the icon changes as the timer ticks (the camera's lens goes dim after 5 ticks and is back
        after 10); a static step (Set_Busy, the capture on the GUI thread) does not start the timer.
    """

    viewport = _Viewport(CONST_TABLE)
    viewport.Start_Busy('Connecting to camera…', 'camera')
    tick = getattr(viewport, '_Viewport_Cls__Tick')
    shown = [_Pixels(viewport)]
    for _ in range(2):
        for _ in range(5):
            tick()
        shown.append(_Pixels(viewport))
    viewport.Stop_Busy()
    assert not np.array_equal(shown[0], shown[1]) and np.array_equal(shown[0], shown[2])
    viewport.Set_Busy('Capturing frame…', 'camera')
    assert not getattr(viewport, '_Viewport_Cls__timer').isActive()
    viewport.Set_Busy('')


def test_while_busy_the_empty_view_keeps_only_its_corner_cluster(qt_app) -> None:
    """
    Description:
        Busy over the empty view (connecting), the overlay's icon and step take the empty state's place: the empty
        instruction is not painted under them (two different instructions paint the same busy view), while the
        poster's corner cluster still shows through.
    """

    grabs = []
    for text in ('Connect a camera, then press Scan to capture a frame.', 'Another instruction entirely.'):
        viewport = _Viewport(None)
        viewport.Set_Empty_Text(text)
        viewport.Start_Busy('Connecting to camera…', 'camera')
        grabs.append(_Pixels(viewport))
        viewport.Stop_Busy()
        idle = _Pixels(viewport)
    assert np.array_equal(grabs[0], grabs[1])
    cell = Viewport_Cls.CONST_CORNER_CELL
    corner = grabs[0][:4 * cell, CONST_SIZE[0] - 6 * cell:]
    assert len(np.unique(corner.reshape(-1, 3), axis=0)) >= 3                  # the cluster's two tints and the ground
    assert not np.array_equal(idle[CONST_SIZE[1] // 2:], grabs[0][CONST_SIZE[1] // 2:])
