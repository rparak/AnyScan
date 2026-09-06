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
# Custom Lib.: AnyScan domain — segmentation
#   ../Vision/Utilities/Segmentation
import Vision.Utilities.Segmentation as Segmentation

"""
Description:
    Tests for background-subtraction segmentation. They run on the committed 001
    reference and synthetic frames built from it, so no camera and no weights are
    needed. cv2 and np are injected, as the module and the pipeline expect.
"""

# Two well-separated rectangles to paint onto the reference (x1, y1, x2, y2).
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]


def test_identical_frame_finds_no_objects(reference_background) -> None:
    """
    Description:
        Differencing the reference against itself yields an empty mask and no
        candidate regions — the guard that an empty surface reads as empty.
    """

    mask, regions = Segmentation.Build_Mask(reference_background, reference_background, cv2, np)
    assert int(np.count_nonzero(mask)) == 0
    assert regions == []


def test_synthetic_frame_finds_ordered_regions(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        Two drawn rectangles come back as two candidate regions, ordered left to
        right, each padded box enclosing the rectangle it was drawn from — the
        index contract the segmenter is then prompted with.
    """

    frame = make_synthetic_frame(reference_background, CONST_RECTS)
    mask, regions = Segmentation.Build_Mask(reference_background, frame, cv2, np)

    assert len(regions) == 2
    # Left-to-right order.
    assert regions[0][0] < regions[1][0]
    # Each padded region encloses the rectangle it came from (the region is grown
    # by CONST_SEG_REGION_PAD_FRAC, so it sits outside the drawn edges).
    for region, drawn in zip(regions, CONST_RECTS):
        rx1, ry1, rx2, ry2 = region
        dx1, dy1, dx2, dy2 = drawn
        assert rx1 <= dx1 and ry1 <= dy1
        assert rx2 >= dx2 and ry2 >= dy2


def test_module_is_qt_free() -> None:
    """
    Description:
        Segmentation imports no Qt and no heavy runtime — cv2/np are injected.
    """

    source = open(Segmentation.__file__).read()
    assert 'PyQt' not in source
    assert '\nimport cv2' not in source
    assert '\nimport torch' not in source
