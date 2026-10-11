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
# File Name: ../test/Vision/Utilities/test_stain.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the stain check, the rule that applies it, and the structures they read
#   ../Vision/Utilities/Stain
from Vision.Utilities.Stain import Check_Stain
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import Apply_Stain
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Hole_Str, Stain_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Stain_Str

"""
Description:
    The catalogue's stain check: the pixels of the colour band inside the part — an edge band and its holes
    left out — opened, and each area of at least Min_Area_Mm2 a stain; a judged part with a stain becomes NOK.
    Synthetic crops at 0.1 mm/px (100 px to the mm²), a grey plate with yellow-brown squares, so every area is
    known; the real fronts (five fingerprinted, the rest clean) are pinned in test_pipeline (slow).
"""

# The mounting plate front's band, as the shipped item gives it; the crop's scale.
CONST_BAND = Catalogue_Stain_Str(Hue_Min=5, Hue_Max=30, Saturation_Min=50, Value_Min=40, Min_Area_Mm2=1.0,
                                 Edge_Margin_Mm=1.0)
CONST_MM_PER_PX = 0.1


def _Colour(hue: int, saturation: int, value: int) -> tp.Tuple[int, int, int]:
    """One OpenCV HSV colour as BGR."""
    return tuple(int(v) for v in cv2.cvtColor(np.uint8([[[hue, saturation, value]]]), cv2.COLOR_HSV2BGR)[0, 0])


# A fingerprint's yellow-brown, inside the band; the plate's grey, outside it (no saturation).
CONST_BROWN = _Colour(15, 150, 150)
CONST_GREY = (150, 150, 150)


def _Plate(*squares: tp.Tuple[int, int, int, tp.Tuple[int, int, int]]) -> np.ndarray:
    """A 600 x 400 px grey plate crop with squares (x, y, side px, BGR) painted on it."""
    crop = np.full((400, 600, 3), CONST_GREY, dtype=np.uint8)
    for x, y, side, colour in squares:
        crop[y:y + side, x:x + side] = colour
    return crop


def test_a_stain_of_the_least_area_is_found_and_a_smaller_one_is_not() -> None:
    """
    Description:
        An 11 x 11 px yellow-brown square (1.21 mm²) is a stain, its area and centre in mm; a 9 x 9 one
        (0.81 mm²) is under Min_Area_Mm2 (1 mm², the owner's threshold) and is not.
    """

    stains = Check_Stain(_Plate((200, 150, 11, CONST_BROWN), (400, 150, 9, CONST_BROWN)), [], CONST_BAND,
                         CONST_MM_PER_PX, cv2, np)
    assert len(stains) == 1
    assert stains[0].Area_Mm2 == pytest.approx(1.21) and (stains[0].X_Mm, stains[0].Y_Mm) == pytest.approx((20.5, 15.5))


def test_the_edge_band_and_the_holes_are_left_out() -> None:
    """
    Description:
        The same stain counts in the open plate but not inside the Edge_Margin_Mm band along the crop's edge
        (the part's rim and the table beyond it), nor over a hole the hole check found (its diameter with half
        a millimetre more: the bore's wall).
    """

    holes = [Hole_Str(Diameter_Mm=6.0, X_Mm=40.0, Y_Mm=20.0)]
    crop = _Plate((0, 150, 11, CONST_BROWN), (395, 195, 11, CONST_BROWN), (100, 100, 11, CONST_BROWN))
    stains = Check_Stain(crop, holes, CONST_BAND, CONST_MM_PER_PX, cv2, np)
    assert [(s.X_Mm, s.Y_Mm) for s in stains] == [pytest.approx((10.5, 10.5))]


def test_hairlines_of_the_colour_are_not_a_stain() -> None:
    """
    Description:
        Lines one pixel wide of the colour — a hairline, the noise along an edge — are opened away, though each is
        connected and over five square millimetres: a stain is an area, not a line.
    """

    crop = _Plate()
    crop[20:380:4, 20:580] = CONST_BROWN
    assert Check_Stain(crop, [], CONST_BAND, CONST_MM_PER_PX, cv2, np) == []


@pytest.mark.parametrize('colour', [_Colour(60, 150, 150), _Colour(15, 30, 150), _Colour(15, 150, 30), _Colour(40, 150, 150)],
                         ids=['green', 'unsaturated', 'too dark', 'past the hue band'])
def test_colours_outside_the_band_are_not_stains(colour: tp.Tuple[int, int, int]) -> None:
    """
    Description:
        A large square of a colour outside the band — the table's green, a grey too unsaturated, a shadow too
        dark, a yellow past Hue_Max — is not a stain.
    """

    assert Check_Stain(_Plate((200, 150, 50, colour)), [], CONST_BAND, CONST_MM_PER_PX, cv2, np) == []


def test_stains_come_largest_first() -> None:
    """
    Description:
        Several stains come largest first, so the report names the largest.
    """

    crop = _Plate((50, 50, 12, CONST_BROWN), (200, 200, 30, CONST_BROWN), (400, 100, 20, CONST_BROWN))
    assert [round(s.Area_Mm2, 2) for s in Check_Stain(crop, [], CONST_BAND, CONST_MM_PER_PX, cv2, np)] == [9.0, 4.0, 1.44]


@pytest.mark.parametrize('stains, before, after', [
    ([], 'OK', 'OK'), ([Stain_Str(Area_Mm2=1.2)], 'OK', 'NOK'), ([], 'NOK', 'NOK'),
], ids=['clean', 'one stain', 'already nok'])
def test_a_judged_parts_stains_decide_ok_or_nok(stains: tp.List[Stain_Str], before: str, after: str) -> None:
    """
    Description:
        A part judged OK stays OK only with no stain; any stain makes it NOK; a part already NOK stays NOK. The
        stains are kept on the object for the report.
    """

    det = Detection_Str(Label='plate', Bbox=(0, 0, 1, 1), Verdict=before)
    Apply_Stain(det, stains)
    assert det.Verdict == after and det.Stains == stains
