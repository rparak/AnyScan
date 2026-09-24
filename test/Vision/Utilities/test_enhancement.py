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
# File Name: ../test/Vision/Utilities/test_enhancement.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — stage-4 crop preparation, and the histogram clip
#   ../Vision/Utilities/Enhancement
import Vision.Utilities.Enhancement as Enhancement
#   ../Camera/Utilities/Image_Processing
from Camera.Utilities.Image_Processing import Get_Alpha_Beta_Parameters

"""
Description:
    Tests for the stage-4 crop preparation (Padded_Bbox, Enhance_Crop) and the
    Get_Alpha_Beta_Parameters histogram clip it reuses. They run on small synthetic
    crops built in the test, deterministically, with no camera and no weights. cv2 and
    np are injected, as the module and the pipeline expect.
"""


def test_padded_bbox_grows_and_clamps() -> None:
    """
    Description:
        Padded_Bbox grows a tight box by the configured padding (a fraction of its longer side)
        and never runs past the frame edge; a padding of 0 is the tight box itself.
    """

    assert Enhancement.Padded_Bbox((100, 100, 40, 20), (480, 640, 3), 0.20) == (92, 92, 56, 36)
    assert Enhancement.Padded_Bbox((100, 100, 40, 20), (480, 640, 3), 0.0) == (100, 100, 40, 20)

    # A box already at the top-left corner cannot grow to a negative origin.
    edge = Enhancement.Padded_Bbox((0, 0, 40, 40), (480, 640, 3), 0.20)
    assert edge[0] == 0 and edge[1] == 0


def test_alpha_beta_flat_histogram_is_identity() -> None:
    """
    Description:
        A flat (single-value) image has no spread to stretch, so the clip returns
        (1.0, 0.0) — the identity transform — from its degenerate-histogram guard.
    """

    flat = np.full((32, 32), 128, np.uint8)
    alpha, beta = Get_Alpha_Beta_Parameters(flat, Enhancement.CONST_ENHANCE_CLIP_LIMIT)
    assert (alpha, beta) == (1.0, 0.0)


def test_alpha_beta_narrow_band_stretches() -> None:
    """
    Description:
        A low-contrast image whose values sit in a narrow band is stretched: the gain
        is well above 1 and the bias is negative (it maps the band's floor toward 0),
        following alpha = 255 / (max - min), beta = -min * alpha for the clipped
        min/max of a [100, 120] band.
    """

    band = np.tile(np.arange(100, 120, dtype=np.uint8), (32, 32 // 20 + 1))[:, :32]
    alpha, beta = Get_Alpha_Beta_Parameters(band.copy(), Enhancement.CONST_ENHANCE_CLIP_LIMIT)
    assert 11.0 < alpha < 15.0          # ~255 / 19..20
    assert beta < -1000.0               # ~ -alpha * 100


def test_enhance_masked_sample_differs_from_unmasked() -> None:
    """
    Description:
        The stretch estimated from the object's own pixels differs from the stretch
        estimated from the whole crop, on a crop where a small dark object sits in a
        large uniform bright surround — the deliberate asymmetry (estimate from the
        object, apply to the whole crop) that keeps the surround from washing out the
        stretch.
    """

    crop = np.full((60, 60, 3), 220, np.uint8)     # large bright surround
    crop[24:36, 24:36] = 50                         # small dark object
    mask = np.zeros((60, 60), dtype=bool)
    mask[24:36, 24:36] = True

    unmasked = Enhancement.Enhance_Crop(crop, None, Enhancement.CONST_ENHANCE_CLIP_LIMIT, cv2, np)
    masked = Enhancement.Enhance_Crop(crop, mask, Enhancement.CONST_ENHANCE_CLIP_LIMIT, cv2, np)

    # Same shape, applied to the whole crop, but the two stretches are not identical.
    assert masked.shape == crop.shape == unmasked.shape
    assert not np.array_equal(masked, unmasked)


def test_isolate_crop_replaces_neighbours_with_background() -> None:
    """
    Description:
        Isolate_Crop keeps the object's own pixels and the bare table, but replaces the
        pixels of OTHER objects with the empty-surface reference — so a large object's
        crop holds one part plus table, not its neighbours.
    """

    table = (70, 140, 70)
    frame = np.full((60, 60, 3), table, np.uint8)
    frame[10:30, 10:30] = (200, 50, 50)                  # own object
    frame[40:55, 40:55] = (50, 50, 200)                  # a neighbouring object
    background = np.full((60, 60, 3), table, np.uint8)   # empty table reference
    own = np.zeros((60, 60), dtype=bool); own[10:30, 10:30] = True
    others = np.zeros((60, 60), dtype=bool); others[40:55, 40:55] = True

    out = Enhancement.Isolate_Crop(frame, background, own, others, np)
    assert tuple(int(c) for c in out[20, 20]) == (200, 50, 50)   # own object kept
    assert tuple(int(c) for c in out[47, 47]) == table           # neighbour -> table
    assert tuple(int(c) for c in out[5, 5]) == table             # bare table kept


def test_enhance_leaves_the_surround_as_the_natural_table() -> None:
    """
    Description:
        With the gain estimated from a dark object, the surround is left as the natural
        table rather than pushed to a garish colour — the object is stretched, the table
        it sits on is not.
    """

    table = (94, 103, 34)
    crop = np.full((60, 60, 3), table, np.uint8)
    crop[20:30, 20:40] = (60, 30, 20)                    # a dark object, two tones so it
    crop[30:40, 20:40] = (95, 60, 45)                    # has a range to stretch
    mask = np.zeros((60, 60), dtype=bool); mask[20:40, 20:40] = True

    out = Enhancement.Enhance_Crop(crop, mask, Enhancement.CONST_ENHANCE_CLIP_LIMIT, cv2, np)
    assert tuple(int(c) for c in out[5, 5]) == table    # surround unchanged from the table
    assert not np.array_equal(out[20:40, 20:40], crop[20:40, 20:40])   # object was stretched


def test_enhance_flat_crop_is_unchanged() -> None:
    """
    Description:
        A flat crop has nothing to stretch (alpha 1, beta 0), so Enhance_Crop returns
        it unchanged.
    """

    crop = np.full((40, 40, 3), 128, np.uint8)
    out = Enhancement.Enhance_Crop(crop, None, Enhancement.CONST_ENHANCE_CLIP_LIMIT, cv2, np)
    assert np.array_equal(out, crop)
