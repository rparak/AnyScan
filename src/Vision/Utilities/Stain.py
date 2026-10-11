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
# File Name: ../Vision/Utilities/Stain.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the stain and hole structures, and the catalogue's stain check
#   ../Parameters/Vision
from Parameters.Vision import Stain_Str, Hole_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Stain_Str

"""
Description:
    Initialization of constants.

    The catalogue's stain check on a judged part's side (Checks.Stain.<side>): the pixels of a colour band inside
    the part — its holes and an edge band left out — opened to drop single-pixel noise, and each connected area of
    at least Min_Area_Mm2 a stain. Colour only: a fingerprint's papillary lines are about 5 px apart at this scale
    and are not used. Qt-free, OpenCV and NumPy injected.

    Measured on the test set's 22 mounting plates (2026-10-11), with the shipped band (hue 5-30, saturation >= 50,
    value >= 40): the 5 stained fronts' largest stain 145-182 mm², the 7 clean fronts 0.00, the 10 backs at most
    0.30 mm². Stain pixels' saturation has a median of 82 (5th percentile 71), clean metal's 99.9th percentile is
    57: the band depends on the station's light and white balance, fixed in the station file.
"""

# The opening that drops single pixels of the band (machining glints, sensor noise) before areas are counted.
#   Unit [int] (px, kernel size)
CONST_STAIN_OPEN_PX = 3
# Each hole is left out with this margin around it: its rim's shading is not the part's surface.
#   Unit [float] (mm)
CONST_STAIN_HOLE_MARGIN_MM = 0.5


def Check_Stain(crop_bgr: tp.Any, holes: tp.List[Hole_Str], Catalogue_Stain_Str: Catalogue_Stain_Str, mm_per_px: float,
                cv2: tp.Any, np: tp.Any) -> tp.List[Stain_Str]:
    """
    Description:
        The stains on a judged part's upright crop: the band's pixels inside the part (an Edge_Margin_Mm band along
        the crop's edges and every hole with CONST_STAIN_HOLE_MARGIN_MM left out), opened, and each connected area of
        at least Min_Area_Mm2, largest first.

    Args:
        (1) crop_bgr [Matrix<uint8> hxwx3]: The part's upright crop.
        (2) holes [Vector<Hole_Str(object)>]: The hole candidates found on it (mm from its top-left corner).
        (3) Catalogue_Stain_Str [Catalogue_Stain_Str(object)]: The side's stain check.
        (4) mm_per_px [float]: The crop's scale.
        (5) cv2 [module]: The OpenCV module, injected by the caller.
        (6) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Stain_Str(object)>]: The stains; empty when the side is clean.
    """

    band = Catalogue_Stain_Str
    h, w = crop_bgr.shape[:2]
    inside = np.zeros((h, w), dtype=np.uint8)
    margin = int(round(band.Edge_Margin_Mm / mm_per_px))
    inside[margin:h - margin, margin:w - margin] = 1
    for hole in holes:
        radius = int(round((hole.Diameter_Mm / 2.0 + CONST_STAIN_HOLE_MARGIN_MM) / mm_per_px))
        cv2.circle(inside, (int(round(hole.X_Mm / mm_per_px)), int(round(hole.Y_Mm / mm_per_px))), radius, 0, -1)
    hue, saturation, value = cv2.split(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV))
    pixels = ((hue >= band.Hue_Min) & (hue <= band.Hue_Max) & (saturation >= band.Saturation_Min)
              & (value >= band.Value_Min) & (inside > 0)).astype(np.uint8)
    pixels = cv2.morphologyEx(pixels, cv2.MORPH_OPEN, np.ones((CONST_STAIN_OPEN_PX, CONST_STAIN_OPEN_PX), np.uint8))
    count, _labels, stats, centres = cv2.connectedComponentsWithStats(pixels)
    stains = [Stain_Str(Area_Mm2=float(stats[i, 4]) * mm_per_px ** 2, X_Mm=float(centres[i][0]) * mm_per_px,
                        Y_Mm=float(centres[i][1]) * mm_per_px) for i in range(1, count)]
    return sorted((stain for stain in stains if stain.Area_Mm2 >= band.Min_Area_Mm2), key=lambda s: -s.Area_Mm2)
