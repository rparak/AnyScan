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
# File Name: ../Vision/Utilities/Holes.py
## =========================================================================== ##

# System (Default)
import math
import itertools
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the hole, count and dimension-check structures, and the catalogue's groups
#   ../Parameters/Vision
from Parameters.Vision import Hole_Str, Hole_Count_Str, Dimension_Check_Str, Feature_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Hole_Group_Str
#   ../Vision/Utilities/Dimensions
from Vision.Utilities.Dimensions import Check_Dimension

"""
Description:
    Initialization of constants.

    The catalogue's hole check on a judged part, on the side DINOv2 found up: FastSAM's masks on the part's
    upright crop (Vision.Utilities.Classify.Object_Crop) become hole candidates — round masks inside the
    part — and each catalogue group (Checks.Holes.<side>) counts the candidates of its diameter and, for a
    group with positions, near one of them; each counted hole's diameter, edge distances and pitch are then
    checked against the tolerance. Qt-free, OpenCV and NumPy injected.

    Measured on the 59 identified parts of the 41 test frames (2026-10-11): FastSAM finds every mounting-plate
    hole (12 fronts with 2 countersinks and 2 through-holes, 10 backs with 2 through-holes) and 41 of the 42
    labyrinth corner holes that exist (one missed on the shadowed plate of Image_071), with no false corner
    hole on the plates that have none. The crop's edges are the measured outline, so an edge distance is from
    the silhouette.
"""

# The roundness (4·π·area / perimeter²) at and above which a mask is a hole candidate: a disc is 1. Measured on
# the test set's identified parts (2026-10-11): every real hole's mask 0.875-0.926 (68 on the mounting plates, 41
# corner holes). A square is π/4 = 0.785, so 0.83 sits between a square and the least round real hole (0.045
# below it): a square feature of a hole's size is not a hole. The corner hole missed on Image_071 was never
# segmented — no mask near that corner at any roundness — so no threshold would have found it.
#   Unit [float]
CONST_HOLE_MIN_CIRCULARITY = 0.83
# A mask this close to the crop's border is the part's edge or the table, not a hole inside the part.
#   Unit [int] (px)
CONST_HOLE_BORDER_PX = 3
# A hole is counted in a group when its diameter is within this many tolerances of the group's: wider than the
# check, so a hole of the wrong size is counted and reported as the wrong size, not as missing. The groups of
# one side must not capture the same diameter (Configuration.Core refuses it).
#   Unit [float]
CONST_HOLE_CAPTURE_TOLERANCES = 2.0
# For a group with positions, a hole is counted when its centre is within √2 × tolerance (a hole off by the
# tolerance on both axes) plus this margin of an expected position. The maze's start and finish marks, round and
# of the corner holes' size, lie at least 4.9 mm from every corner position (the test set's labyrinths): outside
# the labyrinth's 1.91 mm. A hole drilled anywhere else is not counted, and not reported (KNOWN_ISSUES).
#   Unit [float] (mm)
CONST_HOLE_POSITION_MARGIN_MM = 0.5
# Two candidates with centres this close and diameters this close are one hole found twice.
#   Unit [float] (mm)
CONST_HOLE_DUPLICATE_MM = 1.0
# How much wider than its circle a hole's mark is, each way, so the mark sits beside the hole's edge, not on it.
#   Unit [float] (mm)
CONST_HOLE_MARK_MARGIN_MM = 0.5


def Hole_Candidates(masks: tp.List[tp.Any], mm_per_px: float, cv2: tp.Any, np: tp.Any,
                    scores: tp.Optional[tp.List[float]] = None) -> tp.List[Hole_Str]:
    """
    Description:
        The holes among a crop's masks: each mask's largest outer contour, kept when it is round
        (CONST_HOLE_MIN_CIRCULARITY) and does not reach the crop's border; its diameter is a circle's of the same
        area, its centre the enclosing circle's. A hole FastSAM returns twice is kept once.

    Args:
        (1) masks [Vector<Matrix<bool> hxw>]: The crop's masks.
        (2) mm_per_px [float]: The crop's scale.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.
        (5) scores [Vector<float>]: FastSAM's score for each mask, kept on its hole (None: not given).

    Returns:
        (1) parameter [Vector<Hole_Str(object)>]: The candidates.
    """

    found = []
    for index, mask in enumerate(masks):
        h, w = mask.shape[:2]
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            continue
        contour = max(contours, key=cv2.contourArea)
        area, perimeter = cv2.contourArea(contour), cv2.arcLength(contour, True)
        if area <= 0.0 or perimeter <= 0.0 or 4.0 * math.pi * area / perimeter ** 2 < CONST_HOLE_MIN_CIRCULARITY:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(contour)
        if (cx - radius < CONST_HOLE_BORDER_PX or cy - radius < CONST_HOLE_BORDER_PX
                or cx + radius > w - CONST_HOLE_BORDER_PX or cy + radius > h - CONST_HOLE_BORDER_PX):
            continue
        hole = Hole_Str(Diameter_Mm=2.0 * math.sqrt(area / math.pi) * mm_per_px, X_Mm=cx * mm_per_px, Y_Mm=cy * mm_per_px,
                        Score=float(scores[index]) if scores is not None else None)
        if not any(math.hypot(hole.X_Mm - other.X_Mm, hole.Y_Mm - other.Y_Mm) < CONST_HOLE_DUPLICATE_MM
                   and abs(hole.Diameter_Mm - other.Diameter_Mm) < CONST_HOLE_DUPLICATE_MM for other in found):
            found.append(hole)
    return found


def __Edge_Distances(hole: Hole_Str, width_mm: float, height_mm: float) -> tp.Tuple[float, float]:
    """
    Description:
        A hole's distance from its nearer long edge and its nearer short edge. The crop is upright: the long
        edges are its left and right sides, the short edges its top and bottom.

    Args:
        (1) hole [Hole_Str(object)]: The hole.
        (2) width_mm [float]: The crop's width (the part's short side).
        (3) height_mm [float]: The crop's height (the part's long side).

    Returns:
        (1) parameter [Tuple<float> 1x2]: (from the long edge, from the short edge).
    """

    return min(hole.X_Mm, width_mm - hole.X_Mm), min(hole.Y_Mm, height_mm - hole.Y_Mm)


def __Members(candidates: tp.List[Hole_Str], group: Catalogue_Hole_Group_Str, width_mm: float,
              height_mm: float) -> tp.List[Hole_Str]:
    """
    Description:
        A group's holes among the candidates: of its diameter within CONST_HOLE_CAPTURE_TOLERANCES tolerances and,
        for a positioned group, near one of its positions (mirrored to all four corners), top to bottom.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) group [Catalogue_Hole_Group_Str(object)]: The group.
        (3) width_mm [float]: The crop's width (the part's short side).
        (4) height_mm [float]: The crop's height (the part's long side).

    Returns:
        (1) parameter [Vector<Hole_Str(object)>]: Its holes.
    """

    tolerance = group.Tolerance_Mm
    members = [hole for hole in candidates
               if abs(hole.Diameter_Mm - group.Diameter_Mm) < CONST_HOLE_CAPTURE_TOLERANCES * tolerance]
    if group.From_Long_Edge_Mm:
        gate = math.sqrt(2.0) * tolerance + CONST_HOLE_POSITION_MARGIN_MM
        members = [hole for hole in members
                   if math.hypot(*(measured - nominal for measured, nominal in zip(
                       __Edge_Distances(hole, width_mm, height_mm),
                       (group.From_Long_Edge_Mm, group.From_Short_Edge_Mm)))) <= gate]
    return sorted(members, key=lambda hole: (round(hole.Y_Mm), hole.X_Mm))


def Check_Holes(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str], width_mm: float,
                height_mm: float) -> tp.Tuple[tp.List[Hole_Count_Str], tp.List[Dimension_Check_Str]]:
    """
    Description:
        Each group's holes among the candidates, counted and checked. A candidate counts in a group when its
        diameter is within CONST_HOLE_CAPTURE_TOLERANCES tolerances of the group's and, for a group with positions,
        its centre lies near one — the expected positions mirrored to all four corners, since the part may lie
        either way round. Each counted hole is then checked: its diameter, and for a positioned group its distance
        from its nearer long and short edge; and each pair of counted holes about Pitch_Mm apart, their pitch.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (3) width_mm [float]: The crop's width (the part's short side).
        (4) height_mm [float]: The crop's height (the part's long side).

    Returns:
        (1) parameter [Tuple]: (each group's count, every check), in group order.
    """

    counts, checks = [], []
    for group in groups:
        tolerance = group.Tolerance_Mm
        members = __Members(candidates, group, width_mm, height_mm)
        counts.append(Hole_Count_Str(Name=group.Name, Found=len(members), Expected=group.Count))
        for hole in members:
            checks.append(Check_Dimension('%s Ø' % group.Name, hole.Diameter_Mm, group.Diameter_Mm, tolerance))
            if group.From_Long_Edge_Mm:
                long_edge, short_edge = __Edge_Distances(hole, width_mm, height_mm)
                checks.append(Check_Dimension("%s's distance from the long edge" % group.Name, long_edge,
                                              group.From_Long_Edge_Mm, tolerance))
                checks.append(Check_Dimension("%s's distance from the short edge" % group.Name, short_edge,
                                              group.From_Short_Edge_Mm, tolerance))
        if group.Pitch_Mm:
            for i, first in enumerate(members):
                for second in members[i + 1:]:
                    pitch = math.hypot(first.X_Mm - second.X_Mm, first.Y_Mm - second.Y_Mm)
                    if abs(pitch - group.Pitch_Mm) < CONST_HOLE_CAPTURE_TOLERANCES * tolerance:
                        checks.append(Check_Dimension('%s pitch' % group.Name, pitch, group.Pitch_Mm, tolerance))
    return counts, checks


def __Positions(group: Catalogue_Hole_Group_Str, width_mm: float, height_mm: float) -> tp.List[tp.Tuple[float, float]]:
    """
    Description:
        A positioned group's expected centres on the upright crop: its edge distances mirrored to the four
        corners, each once (a centred hole's mirror images coincide).

    Args:
        (1) group [Catalogue_Hole_Group_Str(object)]: The group (with positions).
        (2) width_mm [float]: The crop's width.
        (3) height_mm [float]: The crop's height.

    Returns:
        (1) parameter [Vector<Tuple<float> 1x2>]: The centres (x, y) in mm.
    """

    positions = []
    for x in (group.From_Long_Edge_Mm, width_mm - group.From_Long_Edge_Mm):
        for y in (group.From_Short_Edge_Mm, height_mm - group.From_Short_Edge_Mm):
            if not any(math.hypot(x - px, y - py) < CONST_HOLE_DUPLICATE_MM for px, py in positions):
                positions.append((x, y))
    return positions


def __Square(x_mm: float, y_mm: float, diameter_mm: float) -> tp.List[tp.Tuple[float, float]]:
    """
    Description:
        The box a hole is marked with: a square around its circle, CONST_HOLE_MARK_MARGIN_MM wider each way.

    Args:
        (1) x_mm, y_mm [float]: The centre.
        (2) diameter_mm [float]: The diameter.

    Returns:
        (1) parameter [Vector<Tuple<float> 1x2>]: The four corners, in mm.
    """

    r = diameter_mm / 2.0 + CONST_HOLE_MARK_MARGIN_MM
    return [(x_mm - r, y_mm - r), (x_mm + r, y_mm - r), (x_mm + r, y_mm + r), (x_mm - r, y_mm + r)]


def Hole_Features(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str], width_mm: float,
                  height_mm: float) -> tp.List[Feature_Str]:
    """
    Description:
        The holes as the frame marks them, on the upright crop (mm): each counted hole with its checks (diameter;
        edge distances for a positioned group; the pitch to a neighbour, on both holes), failed when one fails or
        when its group holds more holes than the part has; and each hole expected but not found, at its position.
        A positioned group's expected positions are all its mirrored positions when it has as many holes, else
        the set of its size that holds the holes found and best fits its pitch (none placed when it found none).
        An unpositioned group's missing holes are placed at the centres of other groups' holes it would surround
        (a countersink at its through-hole), the first ones without one of its own.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (3) width_mm [float]: The crop's width (the part's short side).
        (4) height_mm [float]: The crop's height (the part's long side).

    Returns:
        (1) parameter [Vector<Feature_Str(object)>]: The holes, group by group, the found before the missing.
    """

    members = [__Members(candidates, group, width_mm, height_mm) for group in groups]
    features = []
    for group, holes in zip(groups, members):
        tolerance = group.Tolerance_Mm
        own = []
        for hole in holes:
            checks = [Check_Dimension('%s Ø' % group.Name, hole.Diameter_Mm, group.Diameter_Mm, tolerance)]
            if group.From_Long_Edge_Mm:
                long_edge, short_edge = __Edge_Distances(hole, width_mm, height_mm)
                checks += [Check_Dimension("%s's distance from the long edge" % group.Name, long_edge,
                                           group.From_Long_Edge_Mm, tolerance),
                           Check_Dimension("%s's distance from the short edge" % group.Name, short_edge,
                                           group.From_Short_Edge_Mm, tolerance)]
            if group.Pitch_Mm:
                for other in holes:
                    pitch = math.hypot(hole.X_Mm - other.X_Mm, hole.Y_Mm - other.Y_Mm)
                    if other is not hole and abs(pitch - group.Pitch_Mm) < CONST_HOLE_CAPTURE_TOLERANCES * tolerance:
                        checks.append(Check_Dimension('%s pitch' % group.Name, pitch, group.Pitch_Mm, tolerance))
            own.append(Feature_Str(Kind='hole', Name=group.Name, Corners=__Square(hole.X_Mm, hole.Y_Mm, hole.Diameter_Mm),
                                   Passed=len(holes) <= group.Count and all(check.Within for check in checks),
                                   Checks=checks, Score=hole.Score))
        missing = max(0, group.Count - len(holes))
        places = []
        if missing and group.From_Long_Edge_Mm:
            positions = __Positions(group, width_mm, height_mm)
            gate = math.sqrt(2.0) * tolerance + CONST_HOLE_POSITION_MARGIN_MM
            taken = [any(math.hypot(hole.X_Mm - x, hole.Y_Mm - y) <= gate for hole in holes) for x, y in positions]
            if len(positions) == group.Count:
                places = [position for position, held in zip(positions, taken) if not held]
            elif holes:
                fits = [subset for subset in itertools.combinations(range(len(positions)), group.Count)
                        if all(i in subset for i, held in enumerate(taken) if held)]
                if fits:
                    best = min(fits, key=lambda subset: sum(
                        abs(math.dist(positions[i], positions[j]) - (group.Pitch_Mm or 0.0))
                        for i, j in itertools.combinations(subset, 2)))
                    places = [positions[i] for i in best if not taken[i]]
        elif missing:
            centres = [(hole.X_Mm, hole.Y_Mm) for other, found in zip(groups, members) if other is not group
                       for hole in found]
            places = [centre for centre in centres
                      if not any(math.hypot(hole.X_Mm - centre[0], hole.Y_Mm - centre[1]) < group.Diameter_Mm / 2.0
                                 for hole in holes)][:missing]
        own += [Feature_Str(Kind='hole', Name=group.Name, Corners=__Square(x, y, group.Diameter_Mm), Passed=False,
                            Found=False) for x, y in places]
        features += own
    return features
