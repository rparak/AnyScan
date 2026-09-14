## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../test/Vision/Utilities/test_annotate.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the annotation renderer and the palette it reads
#   ../Vision/Utilities/Annotate
import Vision.Utilities.Annotate as Annotate
#   ../Parameters/Theme
import Parameters.Theme as Theme
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Tests for the annotation renderer. They build synthetic detections (a filled block
    each) and render at small and large sizes, so the palette keying, the black mask
    ground, the resolution scaling and the annotated/mask colour agreement are checked
    deterministically with no camera and no weights. cv2 and np are injected.
"""
# The synthetic frame size (h, w).
CONST_H = 400
CONST_W = 600


def __Object(top: int, left: int, size: int = 80) -> Detection_Str:
    """
    Description:
        A detection with a filled square block mask and its tight box.

    Args:
        (1 - 2) top, left [int]: The block's top-left corner.
        (3) size [int]: The block's side length.

    Returns:
        (1) parameter [Detection_Str(object)]: The detection.
    """

    mask = np.zeros((CONST_H, CONST_W), dtype=bool)
    mask[top:top + size, left:left + size] = True
    return Detection_Str(Label='block', Bbox=(left, top, size, size), Mask=mask)


def test_label_mask_ground_is_black_and_objects_are_index_colours() -> None:
    """
    Description:
        The label mask is a pure-black ground with each object filled in its
        Index_Color box colour — the black ground is the §1c diagnostic exception, and
        the colours are the shared palette so they match the annotated image.
    """

    objects = [__Object(40, 40), __Object(200, 300)]
    mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np)

    # A corner far from either block is pure black.
    assert tuple(int(c) for c in mask[5, 5]) == (0, 0, 0)
    # Each block's interior is that index's box colour (BGR).
    assert tuple(int(c) for c in mask[70, 70]) == Theme.Hex_To_Bgr(Theme.Index_Color(0)[0])
    assert tuple(int(c) for c in mask[230, 330]) == Theme.Hex_To_Bgr(Theme.Index_Color(1)[0])


def test_annotated_uses_the_same_index_colours_as_the_mask() -> None:
    """
    Description:
        An object's fill in the annotated image is the same Index_Color as its region
        in the label mask, so object N is one colour across the pair. (The annotated
        fill is translucent, so the tint leans toward the box colour rather than equals it.)
    """

    objects = [__Object(150, 250)]
    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)   # green table
    annotated = Annotate.Draw_Annotated(scene, objects, cv2, np)
    mask = Annotate.Draw_Label_Mask(objects, scene.shape, cv2, np)

    box_bgr = np.array(Theme.Hex_To_Bgr(Theme.Index_Color(0)[0]), dtype=float)
    # Sample near the block's top-left, away from the white index numeral at its centre.
    row, col = 160, 260
    # The label mask is exactly the box colour there.
    assert tuple(int(c) for c in mask[row, col]) == tuple(int(c) for c in box_bgr)
    # The annotated fill has moved the green pixel toward the box colour.
    assert np.linalg.norm(annotated[row, col].astype(float) - box_bgr) < \
        np.linalg.norm(np.array([70, 150, 70], dtype=float) - box_bgr)


def test_chip_numeral_font_is_capped() -> None:
    """
    Description:
        The chip numeral scales only gently with resolution and is clamped, so a 4x
        frame does not get a 4x numeral that would dwarf a small part. (Line widths
        still scale off the raw resolution; only the numeral is capped.)
    """

    chip_font = getattr(Annotate, '__Chip_Font_Scale')
    assert chip_font(0.1) == Annotate.CONST_ANNOTATE_CHIP_FONT_MIN     # clamped at the floor
    assert chip_font(50.0) == Annotate.CONST_ANNOTATE_CHIP_FONT_MAX    # clamped at the cap
    # A 4x resolution gives well under 4x the numeral (it is capped, not proportional).
    assert chip_font(4.0) < chip_font(1.0) * 4


def test_empty_objects_render_cleanly() -> None:
    """
    Description:
        No objects yields an all-black mask and the scene unchanged but for the blend
        of nothing — the zero case does not raise.
    """

    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)
    mask = Annotate.Draw_Label_Mask([], scene.shape, cv2, np)
    assert int(np.count_nonzero(mask)) == 0
    annotated = Annotate.Draw_Annotated(scene, [], cv2, np)
    assert annotated.shape == scene.shape


def test_module_is_qt_free() -> None:
    """
    Description:
        The renderer imports no Qt and no OpenCV/NumPy of its own — cv2/np are
        injected, so it renders in the Qt-free vision layer.
    """

    source = open(Annotate.__file__).read()
    assert 'PyQt' not in source
    assert 'import cv2' not in source and 'import numpy' not in source
