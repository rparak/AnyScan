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

# Custom Lib.: AnyScan — the stage parameters (their documented defaults: the shipped values)
#   ../Parameters/Configuration
from Parameters.Configuration import Segmentation_Parameters_Str
"""
Description:
    Tests for the stage-3 fusion (Foreground_Union + Fuse_Objects). They run on small
    synthetic FastSAM masks and background-foreground masks built in the test, so the
    either-cue survival, the background-like rejection, the component ordering and the
    cue attribution are exercised deterministically with no camera and no weights.
    cv2 and np are injected, as the module and the pipeline expect.
"""
# The stage parameters: the documented defaults, which are the values the shipped configuration sets.
#   Unit [Segmentation_Parameters_Str(object)]
CONST_PARAMETERS = Segmentation_Parameters_Str()
# The synthetic frame size for the fusion tests (h, w). Small, but large enough that
# a 60x60 block clears the configured Min_Area_Fraction of it.
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


def test_union_rejects_a_large_mask_touching_the_configured_number_of_borders() -> None:
    """
    Description:
        The border rule on its own: a mask over Background_Area_Fraction of the frame (0.6 — under
        the Hard_Background_Fraction cap, so the cap cannot be what rejects it) that touches
        Background_Borders (3) of the four borders is the table, and is excluded from the union.
    """

    band = np.zeros((CONST_H, CONST_W), dtype=bool)
    band[:int(0.6 * CONST_H), :] = True                   # top, left and right borders
    assert CONST_PARAMETERS.Background_Area_Fraction < 0.6 < CONST_PARAMETERS.Hard_Background_Fraction
    assert CONST_PARAMETERS.Background_Borders == 3
    union = Fusion.Foreground_Union([band], CONST_H, CONST_W, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert int(np.count_nonzero(union)) == 0


def test_union_keeps_a_large_mask_touching_fewer_borders() -> None:
    """
    Description:
        The same area touching only two borders (a block in the corner) is below Background_Borders,
        so the border rule does not apply and the mask is kept — a large part in a corner is a part.
    """

    corner = np.zeros((CONST_H, CONST_W), dtype=bool)
    side = int((0.6 * CONST_H * CONST_W) ** 0.5)
    corner[:side, :side] = True                           # top and left borders only
    union = Fusion.Foreground_Union([corner], CONST_H, CONST_W, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert int(np.count_nonzero(union)) == int(np.count_nonzero(corner))


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
    union = Fusion.Foreground_Union([big], CONST_H, CONST_W, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert int(np.count_nonzero(union)) > 0


def test_union_hard_bg_frac_rejects_regardless_of_borders() -> None:
    """
    Description:
        A mask above the configured Hard_Background_Fraction of the frame is the background outright,
        even when it touches no border — the hard cap overrides the border test.
    """

    side = int((0.9 * CONST_H * CONST_W) ** 0.5)   # ~0.9 of the frame
    top = (CONST_H - side) // 2
    left = (CONST_W - side) // 2
    huge = __Block(CONST_H, CONST_W, top, left, side)
    union = Fusion.Foreground_Union([huge], CONST_H, CONST_W, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert int(np.count_nonzero(union)) == 0


def test_object_seen_only_by_fastsam_survives() -> None:
    """
    Description:
        An object the background cue misses but a FastSAM mask sees survives the
        fusion, attributed to the FastSAM cue.
    """

    mask = __Block(CONST_H, CONST_W, 150, 150)
    empty_bg = np.zeros((CONST_H, CONST_W), np.uint8)
    objects = Fusion.Fuse_Objects([mask], [0.9], empty_bg, cv2, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert len(objects) == 1
    assert objects[0].Cue == 'fastsam'


def test_object_seen_only_by_background_survives() -> None:
    """
    Description:
        An object no FastSAM mask sees but the background difference marks survives
        the fusion, attributed to the background cue.
    """

    bg_fg = __Block(CONST_H, CONST_W, 150, 150).astype(np.uint8)
    objects = Fusion.Fuse_Objects([], [], bg_fg, cv2, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
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
    objects = Fusion.Fuse_Objects([region], [0.9], bg_fg, cv2, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
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
                                  np.zeros((CONST_H, CONST_W), np.uint8), cv2, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert len(objects) == 3
    lefts = [obj.Bbox[0] for obj in objects]
    # top_left (~40) before top_right (~300), both before the lower-band block.
    assert lefts[0] < lefts[1]
    assert objects[2].Bbox[1] > objects[0].Bbox[1]   # third object is in the lower band


def test_each_object_carries_the_best_overlapping_fastsam_score() -> None:
    """
    Description:
        An object's Segmenter_Score is the best score among the FastSAM masks that overlap it: an
        object made of two masks (0.6 and 0.9) and an unscored one carries 0.9, not the 0.99 of a
        mask elsewhere in the frame; a lone mask carries its own 0.99; an object the background cue
        alone found carries no score.
    """

    first = __Block(CONST_H, CONST_W, 100, 40)
    second = __Block(CONST_H, CONST_W, 130, 70)                  # overlaps first: one object
    unscored = __Block(CONST_H, CONST_W, 110, 50, size=20)       # inside it, no score
    far = __Block(CONST_H, CONST_W, 60, 300)                     # its own object
    background = np.zeros((CONST_H, CONST_W), np.uint8)
    background[300:360, 200:260] = 1                             # found by the background cue alone

    objects = Fusion.Fuse_Objects([first, second, unscored, far], [0.6, 0.9, None, 0.99], background, cv2, np,
                                  Segmentation_Parameters_Str=CONST_PARAMETERS)

    by_left = {obj.Bbox[0]: obj for obj in objects}
    assert len(objects) == 3
    assert by_left[40].Segmenter_Score == 0.9
    assert by_left[300].Segmenter_Score == 0.99
    assert by_left[200].Segmenter_Score is None


def __Notched_Block(top: int, left: int, notch_from_right: bool) -> np.ndarray:
    """
    Description:
        A 60 x 60 block with a 4 px wide, 30 px deep slot cut in from its left or right edge: a gap
        inside one part, which the closing (15 px) must fill.

    Args:
        (1 - 2) top, left [int]: The block's top-left corner.
        (3) notch_from_right [bool]: Cut the slot in from the right edge (else the left).

    Returns:
        (1) parameter [Matrix<bool> HxW]: The mask.
    """

    mask = __Block(CONST_H, CONST_W, top, left)
    if notch_from_right:
        mask[top + 28:top + 32, left + 30:left + 60] = False
    else:
        mask[top + 28:top + 32, left:left + 30] = False
    return mask


def test_the_closing_never_joins_components_that_were_separate() -> None:
    """
    Description:
        Two parts 8 px apart — well inside the 15 px closing kernel, which used to bridge them into
        one object (the two plates of All/Image_010 and Image_013, 10.8 and 9.8 px apart; both frames
        have left the set, recoverable from 2d163a6^, so this is the rule's only pin) — stay two
        objects, and no pixel of the gap between them is given to either. Each part's own slot, which
        faces the other part, is still filled: the closing works inside a component, never across two.
    """

    left_part = __Notched_Block(150, 100, notch_from_right=True)
    right_part = __Notched_Block(150, 168, notch_from_right=False)          # 8 px gap: 160..167
    assert CONST_PARAMETERS.Close_Kernel > 8
    bg_fg = (left_part | right_part).astype(np.uint8)
    objects = Fusion.Fuse_Objects([], [], bg_fg, cv2, np, Segmentation_Parameters_Str=CONST_PARAMETERS)

    assert len(objects) == 2
    assert [obj.Bbox for obj in objects] == [(100, 150, 60, 60), (168, 150, 60, 60)]
    for obj in objects:
        assert int(np.count_nonzero(obj.Mask)) == 60 * 60               # its slot filled
        assert not obj.Mask[150:210, 160:168].any()                     # nothing of the gap


def test_the_closing_still_fills_a_gap_inside_one_component() -> None:
    """
    Description:
        A part with a narrow slot is one component; its closing fills the slot, so the object's mask
        is the whole block — the closing is still applied, only never across components.
    """

    part = __Notched_Block(150, 150, notch_from_right=True)
    objects = Fusion.Fuse_Objects([], [], part.astype(np.uint8), cv2, np, Segmentation_Parameters_Str=CONST_PARAMETERS)
    assert len(objects) == 1
    assert int(np.count_nonzero(objects[0].Mask)) == 60 * 60
