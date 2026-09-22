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
# File Name: ../test/Vision/Utilities/test_fusion.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the fusion stage (stage 3)
#   ../Vision/Utilities/Fusion
import Vision.Utilities.Fusion as Fusion

"""
Description:
    Tests for the stage-3 fusion (Foreground_Union + Fuse_Objects). They run on small
    synthetic FastSAM masks and background-foreground masks built in the test, so the
    either-cue survival, the background-like rejection, the component ordering and the
    cue attribution are exercised deterministically with no camera and no weights.
    cv2 and np are injected, as the module and the pipeline expect.
"""
# The synthetic frame size for the fusion tests (h, w). Small, but large enough that
# a 60x60 block clears CONST_FUSE_MIN_AREA_FRAC of it.
CONST_H = 400
CONST_W = 400


def __Block(h: int, w: int, top: int, left: int, size: int = 60) -> np.ndarray:
    """
    Description:
        A boolean HxW mask with one filled square block — a stand-in FastSAM mask or
        a background-foreground region.

    Args:
        (1 - 2) h, w [int]: The mask height and width.
        (3 - 4) top, left [int]: The block's top-left corner.
        (5) size [int]: The block's side length.

    Returns:
        (1) parameter [Matrix<bool> HxW]: The mask.
    """

    mask = np.zeros((h, w), dtype=bool)
    mask[top:top + size, left:left + size] = True
    return mask


def test_union_rejects_full_frame_border_mask() -> None:
    """
    Description:
        A mask covering the whole frame (the table itself, touching every border) is
        excluded from the union.
    """

    full = np.ones((CONST_H, CONST_W), dtype=bool)
    union = Fusion.Foreground_Union([full], CONST_H, CONST_W, np)
    assert int(np.count_nonzero(union)) == 0


def test_union_keeps_large_non_border_mask() -> None:
    """
    Description:
        A large mask (over half the frame) that does not touch the borders is a part,
        not the background plane, so it is kept.
    """

    # ~0.6 of the frame, centred with a clear margin from every border.
    side = int((0.6 * CONST_H * CONST_W) ** 0.5)
    top = (CONST_H - side) // 2
    left = (CONST_W - side) // 2
    big = __Block(CONST_H, CONST_W, top, left, side)
    union = Fusion.Foreground_Union([big], CONST_H, CONST_W, np)
    assert int(np.count_nonzero(union)) > 0


def test_union_hard_bg_frac_rejects_regardless_of_borders() -> None:
    """
    Description:
        A mask above CONST_FUSE_HARD_BG_FRAC of the frame is the background outright,
        even when it touches no border — the hard cap overrides the border test.
    """

    side = int((0.9 * CONST_H * CONST_W) ** 0.5)   # ~0.9 of the frame
    top = (CONST_H - side) // 2
    left = (CONST_W - side) // 2
    huge = __Block(CONST_H, CONST_W, top, left, side)
    union = Fusion.Foreground_Union([huge], CONST_H, CONST_W, np)
    assert int(np.count_nonzero(union)) == 0


def test_object_seen_only_by_fastsam_survives() -> None:
    """
    Description:
        An object the background cue misses but a FastSAM mask sees survives the
        fusion, attributed to the FastSAM cue.
    """

    mask = __Block(CONST_H, CONST_W, 150, 150)
    empty_bg = np.zeros((CONST_H, CONST_W), np.uint8)
    objects = Fusion.Fuse_Objects([mask], [0.9], empty_bg, cv2, np)
    assert len(objects) == 1
    assert objects[0].Cue == 'fastsam'


def test_object_seen_only_by_background_survives() -> None:
    """
    Description:
        An object no FastSAM mask sees but the background difference marks survives
        the fusion, attributed to the background cue.
    """

    bg_fg = __Block(CONST_H, CONST_W, 150, 150).astype(np.uint8)
    objects = Fusion.Fuse_Objects([], [], bg_fg, cv2, np)
    assert len(objects) == 1
    assert objects[0].Cue == 'background'


def test_object_seen_by_both_is_not_double_counted() -> None:
    """
    Description:
        An object both cues see is one object, not two — the union merges the
        overlapping masks — and it is attributed to both cues.
    """

    region = __Block(CONST_H, CONST_W, 150, 150)
    bg_fg = region.astype(np.uint8)
    objects = Fusion.Fuse_Objects([region], [0.9], bg_fg, cv2, np)
    assert len(objects) == 1
    assert objects[0].Cue == 'both'


def test_component_order_is_row_banded_left_to_right() -> None:
    """
    Description:
        The objects are ordered left to right within row bands: two blocks in the top
        band come out left-then-right regardless of the mask order, and a block in a
        lower band comes after both.
    """

    top_right = __Block(CONST_H, CONST_W, 40, 300)
    top_left = __Block(CONST_H, CONST_W, 50, 40)
    lower = __Block(CONST_H, CONST_W, 300, 180)
    # Deliberately out of order on input; the fusion imposes the index order.
    objects = Fusion.Fuse_Objects([top_right, lower, top_left],
                                  [0.9, 0.9, 0.9],
                                  np.zeros((CONST_H, CONST_W), np.uint8), cv2, np)
    assert len(objects) == 3
    lefts = [obj.Bbox[0] for obj in objects]
    # top_left (~40) before top_right (~300), both before the lower-band block.
    assert lefts[0] < lefts[1]
    assert objects[2].Bbox[1] > objects[0].Bbox[1]   # third object is in the lower band
