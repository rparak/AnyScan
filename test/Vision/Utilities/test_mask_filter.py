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
# File Name: ../test/Vision/Utilities/test_mask_filter.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the stage-3 mask filter
#   ../Vision/Utilities/Mask_Filter
import Vision.Utilities.Mask_Filter as Mask_Filter

"""
Description:
    Tests for stage-3 mask filtering. Masks and the change mask are built directly
    as numpy arrays, so no FastSAM and no weights are needed: the filter's logic is
    what is under test, not the segmenter. cv2 and np are injected, as the module
    expects.
"""

# A small frame the synthetic masks live in.
CONST_H, CONST_W = 200, 200


def _Rect_Mask(x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
    """A boolean HxW mask, True inside the rectangle (x1, y1)-(x2, y2)."""
    mask = np.zeros((CONST_H, CONST_W), dtype=bool)
    mask[y1:y2, x1:x2] = True
    return mask


def _Change_Mask(rects) -> np.ndarray:
    """A uint8 change mask (0/255), 255 inside each (x1, y1, x2, y2) rectangle."""
    change = np.zeros((CONST_H, CONST_W), dtype=np.uint8)
    for (x1, y1, x2, y2) in rects:
        change[y1:y2, x1:x2] = 255
    return change


def test_static_scene_mask_is_rejected() -> None:
    """
    Description:
        A mask that does not overlap the change mask (a static-scene object, or a
        cast shadow the change mask never lit) falls under the change-coverage gate
        and is dropped.
    """

    mask = _Rect_Mask(120, 120, 170, 170)          # 50x50, elsewhere
    change = _Change_Mask([(20, 20, 70, 70)])       # change is far away
    kept = Mask_Filter.Filter_Masks([mask], [0.9], change, cv2, np)
    assert kept == []


def test_whole_frame_mask_is_rejected() -> None:
    """
    Description:
        A mask covering (almost) the entire frame exceeds CONST_FILTER_MAX_AREA_FRAC
        and is rejected, even with full change coverage — it is the scene, not an
        object.
    """

    mask = _Rect_Mask(0, 0, CONST_W, CONST_H)
    change = _Change_Mask([(0, 0, CONST_W, CONST_H)])
    kept = Mask_Filter.Filter_Masks([mask], [0.99], change, cv2, np)
    assert kept == []


def test_border_hugging_mask_is_rejected() -> None:
    """
    Description:
        A mask that lies almost entirely in the frame-edge band is read as the
        background plane and rejected, even with change coverage.
    """

    mask = _Rect_Mask(0, 0, CONST_W, 3)             # a thin strip along the top edge
    change = _Change_Mask([(0, 0, CONST_W, 3)])
    kept = Mask_Filter.Filter_Masks([mask], [0.9], change, cv2, np)
    assert kept == []


def test_identical_frames_yield_no_objects() -> None:
    """
    Description:
        With an empty change mask (identical background and current frames), every
        mask fails the coverage gate: no objects.
    """

    mask = _Rect_Mask(40, 40, 100, 100)
    change = np.zeros((CONST_H, CONST_W), dtype=np.uint8)
    kept = Mask_Filter.Filter_Masks([mask], [0.9], change, cv2, np)
    assert kept == []


def test_nested_duplicate_masks_are_suppressed() -> None:
    """
    Description:
        A part fully inside its whole is the pair FastSAM routinely returns. Their
        IoU is low but the containment is near-total, so the mask NMS suppresses the
        lower-ranked one and keeps the higher-ranked whole.
    """

    whole = _Rect_Mask(20, 20, 120, 120)            # 100x100
    part = _Rect_Mask(40, 40, 80, 80)               # 40x40, entirely inside whole
    change = _Change_Mask([(20, 20, 120, 120)])     # both are fully covered
    # Equal coverage, so the score breaks the tie: the whole outranks the part.
    kept = Mask_Filter.Filter_Masks([part, whole], [0.80, 0.90], change, cv2, np)

    assert len(kept) == 1
    # The survivor is the whole (its tight box spans the 100x100 rectangle).
    x, y, w, h = kept[0].Bbox
    assert (x, y, w, h) == (20, 20, 100, 100)


def test_survivors_are_ordered_left_to_right_regardless_of_input_order() -> None:
    """
    Description:
        The operator index contract: survivors come out left to right, never in the
        segmenter's order and never in rank order. Masks are fed right-to-left and
        the highest-coverage mask is the rightmost, so a filter that inherited either
        order would fail this.
    """

    left = _Rect_Mask(10, 80, 60, 130)
    middle = _Rect_Mask(80, 80, 130, 130)
    right = _Rect_Mask(150, 80, 195, 130)
    # Change covers all three, but the rightmost most fully — so rank order puts it
    # first. Input order is right, middle, left.
    change = _Change_Mask([(10, 80, 60, 130), (80, 80, 130, 130), (150, 80, 195, 130)])
    kept = Mask_Filter.Filter_Masks([right, middle, left], [0.9, 0.9, 0.9], change, cv2, np)

    assert len(kept) == 3
    xs = [d.Bbox[0] for d in kept]
    assert xs == sorted(xs)             # strictly left to right
    assert xs[0] < xs[1] < xs[2]


def test_survivor_carries_mask_coverage_and_score() -> None:
    """
    Description:
        A survivor's Detection_Str carries its mask, its change coverage and the
        segmenter score — distinct from Confidence, which stays None.
    """

    mask = _Rect_Mask(40, 40, 100, 100)
    change = _Change_Mask([(40, 40, 100, 100)])
    kept = Mask_Filter.Filter_Masks([mask], [0.77], change, cv2, np)

    assert len(kept) == 1
    det = kept[0]
    assert det.Mask is mask
    assert det.Segmenter_Score == 0.77
    assert det.Confidence is None
    assert det.Change_Coverage > 0.9      # the mask sits entirely on changed pixels


def test_padded_bbox_pads_and_clamps() -> None:
    """
    Description:
        Padded_Bbox grows a tight box by the crop pad and never runs past the frame.
    """

    padded = Mask_Filter.Padded_Bbox((10, 10, 20, 20), (CONST_H, CONST_W, 3))
    px, py, pw, ph = padded
    assert px < 10 and py < 10 and pw > 20 and ph > 20
    edge = Mask_Filter.Padded_Bbox((0, 0, 20, 20), (CONST_H, CONST_W, 3))
    assert edge[0] == 0 and edge[1] == 0        # clamped at the origin


def test_masked_crop_flattens_non_mask_pixels() -> None:
    """
    Description:
        Masked_Crop keeps the object's pixels and replaces everything else in the
        box with the flat fill colour.
    """

    image = np.full((CONST_H, CONST_W, 3), 200, dtype=np.uint8)
    mask = _Rect_Mask(50, 50, 90, 90)
    bbox = (50, 50, 40, 40)
    crop = Mask_Filter.Masked_Crop(image, mask, bbox, np)

    # Inside the mask, the original pixels survive; the whole crop is masked here.
    assert (crop == 200).all()
    # A box larger than the mask leaves flattened borders.
    wide = Mask_Filter.Masked_Crop(image, mask, (40, 40, 60, 60), np)
    assert (wide[0, 0] == np.array(Mask_Filter.CONST_FILTER_MASK_FILL)).all()
