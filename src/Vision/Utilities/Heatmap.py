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
# File Name: ../Vision/Utilities/Heatmap.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the heatmap colours and the heatmap structure
#   ../Parameters/Theme
from Parameters.Theme import Heatmap_Colors, Hex_To_Bgr
#   ../Parameters/Vision
from Parameters.Vision import Heatmap_Str

"""
Description:
    Initialization of constants.

    The Camera View's heatmap renderer: a Heatmap_Str's values coloured on their fixed scale, in the
    theme's heatmap colours (Parameters.Theme.Heatmap_Colors) — the map alone, no boxes or outlines.
    Qt-free, like the annotation renderer; cv2 and np are injected. The heatmap is shown only: the
    capture writer and the validation harness never call this.
"""
# The heatmap colours as BGR triples, low to high, built once from the theme.
#   Unit [Vector<Tuple<int> 1x3>]
CONST_HEATMAP_BGR = tuple(Hex_To_Bgr(color) for color in Heatmap_Colors())


def Heatmap_Index(Heatmap_Str: Heatmap_Str, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        Each value's colour index on the fixed scale: Low maps to 0 and High to the last colour, linearly,
        a value outside the scale clipping to its end. Never normalised to the frame's own range, so the
        same value is the same colour on every frame.

    Args:
        (1) Heatmap_Str [Heatmap_Str(object)]: The heatmap.
        (2) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The colour indices.
    """

    last = len(CONST_HEATMAP_BGR) - 1
    span = float(Heatmap_Str.High - Heatmap_Str.Low)
    scaled = (np.asarray(Heatmap_Str.Values, dtype=np.float32) - Heatmap_Str.Low) * (last / span)
    return np.clip(np.rint(scaled), 0, last).astype(np.uint8)


def Render_Heatmap(Heatmap_Str: Heatmap_Str, cv2: tp.Any, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        The heatmap as an image the size of its values: each pixel its value's colour (Heatmap_Index).

    Args:
        (1) Heatmap_Str [Heatmap_Str(object)]: The heatmap.
        (2) cv2 [module]: The OpenCV module, injected by the caller. Unused here, and kept on purpose: the
            (cv2, np) pair is injected together everywhere.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The heatmap image (BGR).
    """

    return np.asarray(CONST_HEATMAP_BGR, dtype=np.uint8)[Heatmap_Index(Heatmap_Str, np)]
