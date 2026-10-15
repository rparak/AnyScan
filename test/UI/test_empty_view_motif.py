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
# File Name: ../test/UI/test_empty_view_motif.py
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
# Custom Lib.: AnyScan UI — the viewport, the poster's cluster and the style tokens
#   ../UI/Widgets, ../UI/Utilities/Pixel_Motif, ../UI/Utilities/Style
from UI.Widgets import Viewport_Cls
from UI.Utilities.Pixel_Motif import CONST_POSTER_CORNER
import UI.Utilities.Style as Style

"""
Description:
    The empty Camera View carries the AnyScan poster's pixel cluster in its top-right corner (the owner's choice,
    2026-10-15): the poster's 6 x 4 cells, cell for cell, tone on tone (the purple at two low opacities on the view's
    grey-lilac), decoration only, gone the instant a frame is shown. Measured on the painted viewport.
"""


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


def _Tints() -> tp.List[np.ndarray]:
    """The cluster's two tints as painted: the motif's colour at each opacity over the view's ground."""
    ground, ink = _Hex(Style.CONST_VIEWPORT), _Hex(Style.CONST_CORNER_MOTIF)
    return [np.round(alpha * ink + (1 - alpha) * ground) for alpha in Style.CONST_CORNER_MOTIF_ALPHA]


def test_the_empty_view_carries_the_posters_cluster_cell_for_cell(qt_app) -> None:
    """
    Description:
        Empty, the viewport's top-right 6 x 4 cells are the poster's cluster: each filled cell wholly its tint (the
        purple at the lighter or the stronger low opacity, in the ground's own hue), each empty one the ground. The
        tints stay a texture: no more than 12 % of the purple.
    """

    viewport = Viewport_Cls()
    viewport.resize(993, 617)
    viewport.show()
    QApplication.processEvents()
    drawn = _Pixels(viewport)
    cell, columns = Viewport_Cls.CONST_CORNER_CELL, len(CONST_POSTER_CORNER[0])
    assert Style.CONST_CORNER_MOTIF == Style.CONST_INK and max(Style.CONST_CORNER_MOTIF_ALPHA) <= 0.12
    light, strong = _Tints()
    expected = {'L': light, 'D': strong, '.': _Hex(Style.CONST_VIEWPORT)}
    for row, line in enumerate(CONST_POSTER_CORNER):
        for column, mark in enumerate(line):
            x = viewport.width() - (columns - column) * cell
            block = drawn[row * cell:(row + 1) * cell, x:x + cell]
            assert (np.abs(block - expected[mark]).max(axis=2) <= 1).all(), (row, column, mark)
    viewport.close()


def test_the_cluster_is_gone_once_a_frame_is_shown(qt_app) -> None:
    """
    Description:
        With a frame shown, no pixel of the corner is either tint: the cluster belongs to the empty state only and
        never covers an image.
    """

    viewport = Viewport_Cls()
    viewport.resize(993, 617)
    viewport.show()
    frame = QImage(1600, 1000, QImage.Format_RGB32)
    frame.fill(QColor(90, 90, 90))
    viewport.Show_Frame(frame)
    QApplication.processEvents()
    drawn = _Pixels(viewport)
    corner = drawn[:4 * Viewport_Cls.CONST_CORNER_CELL, -6 * Viewport_Cls.CONST_CORNER_CELL:]
    for tint in _Tints():
        assert not (np.abs(corner - tint).max(axis=2) <= 1).any()
    viewport.close()
