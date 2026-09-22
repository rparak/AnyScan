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
# File Name: ../test/Vision/test_describe_fallback.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the model-free describer
#   ../Vision/Describe_Fallback
from Vision.Describe_Fallback import Describe_Fallback

"""
Description:
    Tests for the model-free fallback describer. Pure cv2/np on synthetic crops, so
    no FastSAM and no Florence-2 weights are needed — this is the describer that lets
    stages 1-3 run without a VLM. The colour tests pin the HSV classification.
"""

CONST_H, CONST_W = 120, 120


def _Object_Frame(bgr_color, rect=(30, 30, 90, 90)):
    """A frame filled green with a solid rect of bgr_color, and the rect's mask/bbox."""
    frame = np.zeros((CONST_H, CONST_W, 3), dtype=np.uint8)
    frame[:] = (60, 140, 60)                                # a green surface (BGR)
    x1, y1, x2, y2 = rect
    frame[y1:y2, x1:x2] = bgr_color
    mask = np.zeros((CONST_H, CONST_W), dtype=bool)
    mask[y1:y2, x1:x2] = True
    return frame, mask, (x1, y1, x2 - x1, y2 - y1)


@pytest.mark.parametrize('bgr_color, expected', [
    ((0, 0, 255), 'red'),          # pure red
    ((255, 0, 0), 'blue'),         # pure blue
    ((40, 40, 150), 'red'),        # mid-dark saturated red
    ((40, 150, 40), 'green'),
    ((150, 40, 40), 'blue'),
    ((15, 15, 15), 'black'),
    ((120, 120, 120), 'grey'),
])
def test_colour_is_classified_in_hsv(bgr_color, expected) -> None:
    """
    Description:
        The dominant colour is named from the object's hue, not a BGR distance,
        including the pure red and pure blue endpoints.
    """

    frame, mask, bbox = _Object_Frame(bgr_color)
    label, detail = Describe_Fallback(frame, mask, bbox, frame.shape, cv2, np)
    assert expected in label
    assert expected in detail


def test_red_straddling_the_hue_wrap_votes_red_not_blue() -> None:
    """
    Description:
        A real red part scatters its pixels across BOTH ends of the 0..179 hue circle.
        The MEAN/median hue of such a part lands ~90 (a false blue) — this is the bug
        the per-pixel vote fixes. Build a half-hue-2, half-hue-178 red patch (both red)
        and require the describer to vote red, not blue. A flat single-colour patch
        (the other cases above) cannot exercise this, because it never straddles.
    """

    patch_hsv = np.zeros((90, 90, 3), dtype=np.uint8)
    patch_hsv[:, :45] = (2, 200, 200)      # hue 2   — one red lobe
    patch_hsv[:, 45:] = (178, 200, 200)    # hue 178 — the other red lobe
    patch_bgr = cv2.cvtColor(patch_hsv, cv2.COLOR_HSV2BGR)

    # Sanity: the mean hue of the two lobes is ~90, squarely in the blue band — the
    # trap a hue average falls into.
    assert 80 < float(cv2.cvtColor(patch_bgr, cv2.COLOR_BGR2HSV)[:, :, 0].mean()) < 100

    frame = np.full((120, 120, 3), (60, 140, 60), dtype=np.uint8)
    frame[15:105, 15:105] = patch_bgr
    mask = np.zeros((120, 120), dtype=bool)
    mask[15:105, 15:105] = True
    label, _ = Describe_Fallback(frame, mask, (15, 15, 90, 90), frame.shape, cv2, np)
    assert 'red' in label


def test_weak_metallic_cast_reads_grey_not_blue() -> None:
    """
    Description:
        Bare machined steel carries a weak colour cast (a saturation well below a real
        coloured part), so it must read grey/white, not blue. Pins the neutral
        saturation cutoff that separates metal from a genuine colour.
    """

    frame, mask, bbox = _Object_Frame((135, 126, 93))     # steel-like BGR, saturation ~79
    label, _ = Describe_Fallback(frame, mask, bbox, frame.shape, cv2, np)
    assert 'grey' in label or 'white' in label


def test_dark_red_is_red_in_hsv_but_brown_by_bgr_distance() -> None:
    """
    Description:
        Pin the reason HSV is used: a mid-dark saturated red is nearer a 'brown'
        anchor than a 'red' anchor in BGR space, yet the describer calls it red. If
        this ever fails, the classifier reverted to a BGR distance.
    """

    dark_red = np.array([40, 40, 150], dtype=np.float64)    # BGR
    red_anchor = np.array([0, 0, 255], dtype=np.float64)
    brown_anchor = np.array([19, 69, 139], dtype=np.float64)  # a common 'brown'
    # In BGR, dark red is closer to brown than to pure red ...
    assert np.linalg.norm(dark_red - brown_anchor) < np.linalg.norm(dark_red - red_anchor)

    # ... yet the HSV describer still names it red.
    frame, mask, bbox = _Object_Frame((40, 40, 150))
    label, _ = Describe_Fallback(frame, mask, bbox, frame.shape, cv2, np)
    assert 'red' in label


def test_detail_reports_size_and_position() -> None:
    """
    Description:
        The detail sentence carries the geometry — a large object filling the frame
        centre reads as such.
    """

    frame, mask, bbox = _Object_Frame((40, 40, 150), rect=(10, 10, 110, 110))
    _, detail = Describe_Fallback(frame, mask, bbox, frame.shape, cv2, np)
    assert 'large' in detail
    assert 'centre' in detail
