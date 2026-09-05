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
        boxes — the guard that an empty surface reads as empty.
    """

    mask = Segmentation.Build_Mask(reference_background, reference_background, cv2, np)
    assert int(np.count_nonzero(mask)) == 0
    assert Segmentation.Find_Objects(mask, cv2, np) == []


def test_synthetic_frame_finds_ordered_boxes(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        Two drawn rectangles come back as two boxes, ordered left to right, each
        overlapping the region it was drawn in — the index contract.
    """

    frame = make_synthetic_frame(reference_background, CONST_RECTS)
    mask = Segmentation.Build_Mask(reference_background, frame, cv2, np)
    boxes = Segmentation.Find_Objects(mask, cv2, np)

    assert len(boxes) == 2
    # Left-to-right order.
    assert boxes[0][0] < boxes[1][0]
    # Each detected box brackets the rectangle it came from (morphology shifts the
    # edges by a pixel or two, so allow a small margin).
    for detected, drawn in zip(boxes, CONST_RECTS):
        dx1, dy1, dx2, dy2 = detected
        rx1, ry1, rx2, ry2 = drawn
        assert abs(dx1 - rx1) <= 3 and abs(dy1 - ry1) <= 3
        assert abs(dx2 - rx2) <= 3 and abs(dy2 - ry2) <= 3


def test_crop_with_pad_stays_in_bounds() -> None:
    """
    Description:
        A box at the image edge crops with a margin but never past the bounds.
    """

    img = np.zeros((100, 120, 3), dtype=np.uint8)
    crop = Segmentation.Crop_With_Pad(img, (0, 0, 20, 20))
    # pad = 0.2 * 20 = 4; the crop starts clamped at 0 and extends by the pad.
    assert crop.shape[0] <= img.shape[0] and crop.shape[1] <= img.shape[1]
    assert crop.shape[0] == 24 and crop.shape[1] == 24


def test_module_is_qt_free() -> None:
    """
    Description:
        Segmentation imports no Qt and no heavy runtime — cv2/np are injected.
    """

    source = open(Segmentation.__file__).read()
    assert 'PyQt' not in source
    assert '\nimport cv2' not in source
    assert '\nimport torch' not in source
