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
    the part — its holes and an edge band left out — opened to drop single-pixel noise, then joined into regions:
    fragments within Merge_Mm of each other are one region, since a fingerprint's ridges break it into pieces. A
    region holding a fragment of at least Min_Area_Mm2 is a stain, so what makes a part NOK is unchanged by the
    joining; it only decides how the stains are counted, boxed and reported. Colour only: the papillary lines
    are about 5 px apart at this scale and are not used. Qt-free, OpenCV and NumPy injected.

    Measured on the test set's fronts (2026-10-11), with the shipped band (hue 5-30, saturation >= 50, value >= 40):
    the five fingerprinted fronts' largest fragment 144-157 mm², every clean front no band pixel left after the
    opening. Each fingerprinted front shows two fingerprints by eye: fragments joined within 2-4 mm give exactly
    two regions on all five; 1 mm leaves three or four, 5 mm joins the two across the hole on two plates.
    Merge_Mm 3 is the middle. The band depends on the station's light and white balance, fixed in the station
    file.
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
        The stain regions on a judged part's upright crop: the band's pixels inside the part (an Edge_Margin_Mm
        band along the crop's edges and every hole with CONST_STAIN_HOLE_MARGIN_MM left out), opened; the
        fragments joined within Merge_Mm (each grown by half of it); each region holding a fragment of at least
        Min_Area_Mm2 kept, with its fragments' area, centre, rotated box and outlines, largest first.

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
    count, fragments, stats, _centres = cv2.connectedComponentsWithStats(pixels)
    grow = int(round(band.Merge_Mm / 2.0 / mm_per_px))
    joined = (cv2.dilate(pixels, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * grow + 1, 2 * grow + 1)))
              if grow > 0 else pixels)
    _regions, regions = cv2.connectedComponents(joined)
    stains = []
    for region in sorted(set(np.unique(regions[pixels > 0])) - {0}):
        members = sorted(set(np.unique(fragments[(regions == region) & (pixels > 0)])) - {0})
        if not any(stats[i, 4] * mm_per_px ** 2 >= band.Min_Area_Mm2 for i in members):
            continue
        own = np.isin(fragments, members)
        ys, xs = np.nonzero(own)
        corners = cv2.boxPoints(cv2.minAreaRect(np.column_stack([xs, ys]).astype(np.float32)))
        outlines, _hierarchy = cv2.findContours(own.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        stains.append(Stain_Str(Area_Mm2=float(len(xs)) * mm_per_px ** 2, X_Mm=float(xs.mean()) * mm_per_px,
                                Y_Mm=float(ys.mean()) * mm_per_px,
                                Corners=[(float(x) * mm_per_px, float(y) * mm_per_px) for x, y in corners],
                                Outlines=[[(float(x) * mm_per_px, float(y) * mm_per_px) for x, y in outline[:, 0]]
                                          for outline in outlines]))
    return sorted(stains, key=lambda stain: -stain.Area_Mm2)
