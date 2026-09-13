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
# File Name: ../test/Vision/Utilities/test_segmentation.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — background-subtraction (stage 1)
#   ../Vision/Utilities/Segmentation
import Vision.Utilities.Segmentation as Segmentation

"""
Description:
    Tests for the stage-1 background-subtracted foreground mask (Background_Foreground).
    They run on small synthetic (background, frame) pairs built in the test, so the
    absdiff -> floored-Otsu -> opening -> dilation chain is exercised deterministically
    with no camera and no weights. cv2 and np are injected, as the module and the
    pipeline expect.
"""


def test_identical_frame_finds_no_foreground() -> None:
    """
    Description:
        Differencing a flat background against itself yields an empty mask — the
        guard that an unchanged surface reads as empty.
    """

    bg = np.full((200, 200, 3), 100, np.uint8)
    mask = Segmentation.Background_Foreground(bg, bg.copy(), cv2, np)
    assert mask.shape == (200, 200)
    assert int(np.count_nonzero(mask)) == 0


def test_known_difference_marks_the_object() -> None:
    """
    Description:
        A bright block painted on a flat background comes back as foreground: the
        block interior is marked, the far background is not, and the mask is a {0, 1}
        uint8 mask.
    """

    bg = np.full((200, 200, 3), 100, np.uint8)
    fg = bg.copy()
    fg[70:130, 70:130] = 200
    mask = Segmentation.Background_Foreground(bg, fg, cv2, np)

    assert mask.dtype == np.uint8 and int(mask.max()) == 1
    assert float(mask[80:120, 80:120].mean()) > 0.95   # block interior is foreground
    assert int(mask[10, 10]) == 0                       # far background is not


def test_opening_removes_a_thin_halo() -> None:
    """
    Description:
        The morphological opening erases a thin structure (a shadow halo is thin)
        while a solid block of the same contrast survives — so a 1-pixel line all but
        vanishes and a filled block does not.
    """

    bg = np.full((200, 200, 3), 100, np.uint8)

    solid = bg.copy()
    solid[70:130, 70:130] = 200
    solid_mask = Segmentation.Background_Foreground(bg, solid, cv2, np)

    thin = bg.copy()
    thin[100, 40:160] = 200            # a 1-pixel-tall line of the same contrast
    thin_mask = Segmentation.Background_Foreground(bg, thin, cv2, np)

    assert int(np.count_nonzero(solid_mask)) > 2000     # the block survives
    assert int(np.count_nonzero(thin_mask)) < 200       # the thin line is opened away


def test_diff_floor_rejects_a_faint_change() -> None:
    """
    Description:
        A change fainter than CONST_BG_DIFF_FLOOR is rejected even though Otsu, on a
        near-empty frame, would threshold below it — while a strong change of the same
        shape is kept. This is the floor keeping a faint shadow out of the foreground.
    """

    bg = np.full((200, 200, 3), 100, np.uint8)

    faint = bg.copy()
    faint[70:130, 70:130] = 100 + (Segmentation.CONST_BG_DIFF_FLOOR // 2)   # below the floor
    faint_mask = Segmentation.Background_Foreground(bg, faint, cv2, np)

    strong = bg.copy()
    strong[70:130, 70:130] = 200                                           # well above it
    strong_mask = Segmentation.Background_Foreground(bg, strong, cv2, np)

    assert int(np.count_nonzero(faint_mask)) == 0       # floored out
    assert int(np.count_nonzero(strong_mask)) > 2000    # kept


def test_module_is_qt_free() -> None:
    """
    Description:
        Segmentation imports no Qt and no heavy runtime — cv2/np are injected. The
        module must import with only stdlib present.
    """

    source = open(Segmentation.__file__).read()
    assert 'import PyQt' not in source and 'from PyQt' not in source
    assert 'import cv2' not in source and 'import numpy' not in source
