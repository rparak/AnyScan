## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../test/Vision/Utilities/test_heatmap.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the heatmap renderer, its structure and the theme's colours
#   ../Vision/Utilities/Heatmap
import Vision.Utilities.Heatmap as Heatmap
#   ../Parameters/Vision
from Parameters.Vision import Heatmap_Str
#   ../Parameters/Theme
import Parameters.Theme as Theme

"""
Description:
    Tests for the Camera View's heatmap renderer: values coloured on their FIXED scale in the theme's
    heatmap colours. Expectations come from the theme's colours and literal values, never from the
    renderer.
"""


def _Map(values: np.ndarray) -> Heatmap_Str:
    """The background difference's heatmap: 0 .. 128 grey levels."""
    return Heatmap_Str(Values=values, Low=0.0, High=128.0, Title='Difference from the reference', Unit='grey level')


def test_a_value_is_coloured_by_its_place_on_the_fixed_scale() -> None:
    """
    Description:
        The scale is linear from Low (the first colour) to High (the last), and a value above High takes
        the last colour: 0 -> colour 0, 32 -> colour 64, 128 and 200 -> colour 255. Each pixel is that
        theme colour, in BGR.
    """

    values = np.array([[0, 32, 128, 200]], dtype=np.uint8)
    image = Heatmap.Render_Heatmap(_Map(values), cv2, np)
    colors = Theme.Heatmap_Colors()
    expected = [Theme.Hex_To_Bgr(colors[index]) for index in (0, 64, 255, 255)]
    assert [tuple(int(v) for v in image[0, column]) for column in range(4)] == expected


def test_the_same_value_is_the_same_colour_whatever_else_is_in_the_frame() -> None:
    """
    Description:
        Fixed, not normalised per frame: a 30-grey-level shadow is the same colour on a frame whose
        hottest pixel is 40 as on one whose hottest is 170, so an empty frame's noise never looks as hot
        as a part.
    """

    quiet = np.array([[30, 40]], dtype=np.uint8)
    busy = np.array([[30, 170]], dtype=np.uint8)
    assert np.array_equal(Heatmap.Render_Heatmap(_Map(quiet), cv2, np)[0, 0], Heatmap.Render_Heatmap(_Map(busy), cv2, np)[0, 0])
    assert tuple(int(v) for v in Heatmap.Render_Heatmap(_Map(quiet), cv2, np)[0, 0]) == \
        Theme.Hex_To_Bgr(Theme.Heatmap_Colors()[60])                # 30 * 255 / 128 = 59.8 -> 60


def test_module_is_qt_free(top_level_imports) -> None:
    """
    Description:
        The renderer imports no Qt and no heavy runtime — cv2/np are injected, as for the annotation
        renderer.
    """

    assert not top_level_imports(Heatmap.__file__) & {'PyQt5', 'cv2', 'numpy'}


def test_an_overlay_colours_only_the_pixels_it_covers() -> None:
    """
    Description:
        The similarity overlay over the frame: a covered pixel is its value's colour blended over the frame (the
        part stays visible under it), an uncovered one (NaN) is the frame itself, byte for byte.
    """

    frame = np.full((20, 30, 3), 100, np.uint8)
    values = np.full((20, 30), np.nan, np.float32)
    values[5:10, 5:10] = 0.5
    overlay = Heatmap.Render_Overlay(Heatmap_Str(Values=values, Low=0.0, High=0.5), frame, cv2, np)
    assert np.array_equal(overlay[12:, :], frame[12:, :]) and np.array_equal(overlay[:, 12:], frame[:, 12:])
    top = np.array(Heatmap.CONST_HEATMAP_BGR[-1], np.float32)
    expected = np.round(top * Heatmap.CONST_OVERLAY_OPACITY + 100 * (1 - Heatmap.CONST_OVERLAY_OPACITY))
    assert np.abs(overlay[7, 7].astype(np.float32) - expected).max() <= 1.0
