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
# Dataclasses (Data Classes)
import dataclasses
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the hole, count and dimension-check structures, and the catalogue's groups
#   ../Parameters/Vision
from Parameters.Vision import Hole_Str, Hole_Count_Str, Dimension_Check_Str, Feature_Str, Crop_View_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Hole_Group_Str
#   ../Vision/Utilities/Dimensions
from Vision.Utilities.Dimensions import Check_Dimension

"""
Description:
    Initialization of constants.

    The catalogue's hole check on a judged part, on the side found up (Classify.Decide_Side): FastSAM's masks on
    the part's upright crop (Vision.Utilities.Classify.Object_Crop) become hole candidates — round masks inside the
    part — and each catalogue group (Checks.Holes.<side>) counts the candidates of its diameter and, for a
    group with positions, near one of them; each counted hole's diameter, edge distances and pitch are then
    checked against the tolerance. Qt-free, OpenCV and NumPy injected.

    Measured on the 22 mounting plates of the 41 test frames (2026-10-13): FastSAM finds every hole (12 fronts
    with 2 countersinks and 2 through-holes, 10 backs with 2 through-holes, 68 in all), and no other round mask
    of a group's size. The crop's edges are the measured outline, so an edge distance is from
    the silhouette.

    A stepped hole's position is its step's: a hole inside a larger hole of another group (a through-hole in its
    countersink) is seen below the top face, and away from the frame centre its opening shifts towards it (Seat_Holes).
    Measured on the mounting-plate captures of 2026-10-15 (47 fronts, 4.8-66.6 mm from the frame centre): the
    through-hole's centre lay 0.12-0.36 mm from its countersink's within 10 mm of the frame centre, 0.8-1.15 mm at 60 mm
    and 1.30 mm at 66.6 mm, growing with the distance, while every hole stayed round (0.883-0.916) and its diameter
    within 6.12-6.25 mm. Its short-edge distance read up to 19.37 mm against 17.5 ± 1.5; the countersink's, on the top
    face, 17.22-18.59 mm at every distance (design-decisions.md). The bore is then checked for its own offset from
    its step's axis, the camera's shift predicted from the bore's depth taken out (__Concentricity).
"""

# The roundness (4·π·area / perimeter²) at and above which a mask is a hole candidate: a disc is 1. Measured on
# the test set's 22 mounting plates (2026-10-13): every real hole's mask 0.881-0.914 (68 holes), and no mask of a
# hole's size between 0.70 and 0.83. A square is π/4 = 0.785, so 0.83 sits between a square and the least round
# real hole (0.051 below it): a square feature of a hole's size is not a hole.
#   Unit [float]
CONST_HOLE_MIN_CIRCULARITY = 0.83
# The largest offset of a stepped hole's lower step from its step's axis, once the camera's predicted shift is taken out
# (__Concentricity). Measured on the 112 through-holes of every mounting-plate front (the test set and the five capture
# sets, 2026-10-15, 4.8-66.6 mm from the frame centre): 0.204 mm at most, flat with the distance (raw, the offset reached
# 1.30 mm). 0.85 is midway between that and 1.5 mm, the smallest off-centre bore to be caught.
#   Unit [float] (mm)
CONST_HOLE_CONCENTRICITY_MM = 0.85
# A mask this close to the crop's border is the part's edge or the table, not a hole inside the part.
#   Unit [int] (px)
CONST_HOLE_BORDER_PX = 3
# A hole is counted in a group when its diameter is within this many tolerances of the group's: wider than the
# check, so a hole of the wrong size is counted and reported as the wrong size, not as missing. The groups of
# one side must not capture the same diameter (Configuration.Core refuses it).
#   Unit [float]
CONST_HOLE_CAPTURE_TOLERANCES = 2.0
# For a group with positions, a hole is counted when its centre is within √2 × tolerance (a hole off by the
# tolerance on both axes) plus this margin of an expected position: 2.62 mm for the mounting plate's through-holes.
# Measured on the test set's 22 plates (2026-10-13): every through-hole within 1.23 mm of its position. A hole
# drilled anywhere else is not counted, and not reported (KNOWN_ISSUES).
#   Unit [float] (mm)
CONST_HOLE_POSITION_MARGIN_MM = 0.5
# Two candidates with centres this close and diameters this close are one hole found twice.
#   Unit [float] (mm)
CONST_HOLE_DUPLICATE_MM = 1.0
# How much wider than its circle a hole's recorded box is, each way (the part's 'corners' in '_objects.json').
#   Unit [float] (mm)
CONST_HOLE_MARK_MARGIN_MM = 0.5
# The outline a found hole is drawn with is its mask's contour simplified to within this distance (approxPolyDP),
# under a pixel so it keeps the mask's shape, ragged where the mask is.
#   Unit [float] (px)
CONST_HOLE_OUTLINE_EPS_PX = 0.5
# The points of the circle a hole expected and not found is drawn with (the catalogue's diameter, at its position).
#   Unit [int]
CONST_HOLE_CIRCLE_POINTS = 72


def Hole_Candidates(masks: tp.List[tp.Any], mm_per_px: float, cv2: tp.Any, np: tp.Any,
                    scores: tp.Optional[tp.List[float]] = None) -> tp.List[Hole_Str]:
    """
    Description:
        The holes among a crop's masks: each mask's largest outer contour, kept when it is round
        (CONST_HOLE_MIN_CIRCULARITY) and does not reach the crop's border; its diameter is a circle's of the same
        area, its centre the enclosing circle's, its outline the contour simplified. A hole FastSAM returns twice is
        kept once.

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
                        Score=float(scores[index]) if scores is not None else None,
                        Outline=[(float(x) * mm_per_px, float(y) * mm_per_px)
                                 for x, y in cv2.approxPolyDP(contour, CONST_HOLE_OUTLINE_EPS_PX, True).reshape(-1, 2)])
        if not any(math.hypot(hole.X_Mm - other.X_Mm, hole.Y_Mm - other.Y_Mm) < CONST_HOLE_DUPLICATE_MM
                   and abs(hole.Diameter_Mm - other.Diameter_Mm) < CONST_HOLE_DUPLICATE_MM for other in found):
            found.append(hole)
    return found


def __Captures(group: Catalogue_Hole_Group_Str, hole: Hole_Str) -> bool:
    """
    Description:
        Whether a group would count a hole by its diameter: within CONST_HOLE_CAPTURE_TOLERANCES of the group's
        tolerances of its nominal diameter.

    Args:
        (1) group [Catalogue_Hole_Group_Str(object)]: The group.
        (2) hole [Hole_Str(object)]: The hole.

    Returns:
        (1) parameter [bool]: True when its diameter is the group's.
    """

    return abs(hole.Diameter_Mm - group.Diameter_Mm) < CONST_HOLE_CAPTURE_TOLERANCES * group.Tolerance_Mm


def Seat_Holes(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str]) -> tp.List[Hole_Str]:
    """
    Description:
        The candidates as their positions are measured: a hole lying wholly inside a larger candidate that one of the
        side's groups counts by its diameter (a through-hole in its countersink) is a stepped hole's lower step, so it
        is measured at that step's centre, the smallest such when there are several; every other hole is unchanged.
        The step's rim lies on the part's top face. The lower step is seen through it, below the face, and away from
        the frame centre its opening shifts towards it (the module's description): measured at its own centre, a
        through-hole 60 mm out read up to 1.9 mm farther from its short edge than its countersink. Its diameter,
        outline and score stay its own.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.

    Returns:
        (1) parameter [Vector<Hole_Str(object)>]: The candidates in the same order, each lower step at its step's
                                                  centre (a copy; the candidates are not changed).
    """

    return [dataclasses.replace(hole, X_Mm=step.X_Mm, Y_Mm=step.Y_Mm) if step is not None else hole
            for hole, step in zip(candidates, __Steps(candidates, groups))]


def __Steps(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str]) -> tp.List[tp.Optional[Hole_Str]]:
    """
    Description:
        Each candidate's step (Seat_Holes): the smallest larger candidate one of the side's groups counts by its
        diameter that holds it wholly inside, or None.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.

    Returns:
        (1) parameter [Vector<Hole_Str(object) or None>]: The step of each candidate, in the same order.
    """

    steps = [hole for hole in candidates if any(__Captures(group, hole) for group in groups)]
    found = []
    for hole in candidates:
        around = [step for step in steps if step.Diameter_Mm > hole.Diameter_Mm
                  and math.hypot(step.X_Mm - hole.X_Mm, step.Y_Mm - hole.Y_Mm) + hole.Diameter_Mm / 2.0
                  <= step.Diameter_Mm / 2.0]
        found.append(min(around, key=lambda other: other.Diameter_Mm) if around else None)
    return found


def __Concentricity(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str],
                    view: tp.Optional[Crop_View_Str]) -> tp.List[tp.Optional[Dimension_Check_Str]]:
    """
    Description:
        Each stepped hole's lower step checked for its offset from its step's axis: its own centre's distance from
        its step's centre less the shift the camera predicts there, against CONST_HOLE_CONCENTRICITY_MM. The bore is
        seen through its step: what shows of it lies between the step's floor and the part's bottom face, so its
        centre is seen at their mean depth, (thickness + floor) / 2, the floor (step's Ø - its own Ø) / 2 deep for
        a 90° countersink; a point that deep projects towards the principal point by its distance from it times
        depth / (camera distance + depth) (the pinhole model). For the mounting plate (8 mm, 12 and 6 mm) that is
        5.5 mm; fitted to the 112 through-holes measured (2026-10-15), 5.54 mm. None for a hole with no step, or
        without the view (no check).

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (3) view [Crop_View_Str(object) or None]: How the camera sees the crop.

    Returns:
        (1) parameter [Vector<Dimension_Check_Str(object) or None>]: Each candidate's check, in the same order.
    """

    checks = []
    for hole, step in zip(candidates, __Steps(candidates, groups)):
        own = next((group for group in groups if __Captures(group, hole)), None)
        outer = next((group for group in groups if step is not None and __Captures(group, step)), None)
        if view is None or step is None or own is None or outer is None:
            checks.append(None)
            continue
        depth = (view.Thickness_Mm + (outer.Diameter_Mm - own.Diameter_Mm) / 2.0) / 2.0
        shift = depth / (view.Distance_Mm + depth)
        drift_x, drift_y = (view.Axis_X_Mm - step.X_Mm) * shift, (view.Axis_Y_Mm - step.Y_Mm) * shift
        offset = math.hypot(hole.X_Mm - step.X_Mm - drift_x, hole.Y_Mm - step.Y_Mm - drift_y)
        checks.append(Check_Dimension("%s's offset from its %s" % (own.Name, outer.Name), offset, 0.0,
                                      CONST_HOLE_CONCENTRICITY_MM))
    return checks


def __To_Face(candidates: tp.List[Hole_Str], width_mm: float, height_mm: float,
              walls: tp.Tuple[float, float, float, float]) -> tp.Tuple[tp.List[Hole_Str], float, float]:
    """
    Description:
        The candidates and the crop's size in the part's top face's frame: the crop's edges are the measured outline,
        which reaches past the top face by the side wall the camera sees on the edges facing the optical axis
        (Vision.Utilities.Classify.Wall_Widths), and the catalogue gives every position from the top face's edges.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) width_mm [float]: The crop's width.
        (3) height_mm [float]: The crop's height.
        (4) walls [Tuple<float> 1x4]: The wall along the crop's left, top, right and bottom edge, in mm.

    Returns:
        (1) parameter [Tuple]: (the candidates moved, the top face's width, its height), in mm.
    """

    left, top, right, bottom = walls
    moved = [dataclasses.replace(hole, X_Mm=hole.X_Mm - left, Y_Mm=hole.Y_Mm - top,
                                 Outline=[(x - left, y - top) for x, y in hole.Outline]) for hole in candidates]
    return moved, width_mm - left - right, height_mm - top - bottom


def __Prepare(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str], width_mm: float,
              height_mm: float, walls: tp.Tuple[float, float, float, float],
              view: tp.Optional[Crop_View_Str]) -> tp.Tuple[tp.List[Hole_Str], tp.Dict[int, Dimension_Check_Str], float,
                                                           float]:
    """
    Description:
        The candidates as Check_Holes and Hole_Features measure them: seated (Seat_Holes) and moved to the top face's
        frame (__To_Face), with each stepped hole's concentricity check (__Concentricity) keyed by the moved hole.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (3) width_mm [float]: The crop's width.
        (4) height_mm [float]: The crop's height.
        (5) walls [Tuple<float> 1x4]: The side wall along the crop's left, top, right and bottom edge, in mm.
        (6) view [Crop_View_Str(object) or None]: How the camera sees the crop.

    Returns:
        (1) parameter [Tuple]: (the holes moved, {id of a moved hole: its concentricity check}, the top face's width,
                               its height).
    """

    moved, width_mm, height_mm = __To_Face(Seat_Holes(candidates, groups), width_mm, height_mm, walls)
    offsets = {id(hole): check for hole, check in zip(moved, __Concentricity(candidates, groups, view))
               if check is not None}
    return moved, offsets, width_mm, height_mm


def Side_Evidence(candidates: tp.List[Hole_Str], holes_by_side: tp.Dict[str, tp.List[Catalogue_Hole_Group_Str]],
                  width_mm: float, height_mm: float,
                  walls: tp.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)) -> tp.List[str]:
    """
    Description:
        The sides the holes found show to be up: each side with a found hole that its groups count (by diameter and,
        for a positioned group, position) and no group of another side would. The mounting plate's countersinks are
        the front's alone, so finding one shows the front, wherever the part lies in the view; its through-holes are
        on both sides and show neither. Absence is never evidence: a front missing its countersinks shows no side, and
        the side is then DINOv2's (Vision.Utilities.Classify.Decide_Side).

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) holes_by_side [Dict<string, Vector<Catalogue_Hole_Group_Str(object)>>]: The catalogue's groups per side.
        (3) width_mm [float]: The crop's width (the part's short side).
        (4) height_mm [float]: The crop's height (the part's long side).
        (5) walls [Tuple<float> 1x4]: The side wall along the crop's left, top, right and bottom edge, in mm
                                      (Vision.Utilities.Classify.Wall_Widths); none by default.

    Returns:
        (1) parameter [Vector<string>]: The sides shown, in the catalogue's order; empty when no hole tells.
    """

    candidates, width_mm, height_mm = __To_Face(candidates, width_mm, height_mm, walls)
    counted = {}
    for side, groups in holes_by_side.items():
        seated = Seat_Holes(candidates, groups)
        members = [__Members(seated, group, width_mm, height_mm) for group in groups]
        counted[side] = {index for index, hole in enumerate(seated) if any(hole is member for found in members
                                                                             for member in found)}
    return [side for side, own in counted.items()
            if any(all(index not in others for other, others in counted.items() if other != side) for index in own)]


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
    members = [hole for hole in candidates if __Captures(group, hole)]
    if group.From_Long_Edge_Mm:
        gate = math.sqrt(2.0) * tolerance + CONST_HOLE_POSITION_MARGIN_MM
        members = [hole for hole in members
                   if math.hypot(*(measured - nominal for measured, nominal in zip(
                       __Edge_Distances(hole, width_mm, height_mm),
                       (group.From_Long_Edge_Mm, group.From_Short_Edge_Mm)))) <= gate]
    return sorted(members, key=lambda hole: (round(hole.Y_Mm), hole.X_Mm))


def Check_Holes(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str], width_mm: float,
                height_mm: float, walls: tp.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
                view: tp.Optional[Crop_View_Str] = None) -> tp.Tuple[tp.List[Hole_Count_Str], tp.List[Dimension_Check_Str]]:
    """
    Description:
        Each group's holes among the candidates, counted and checked. A candidate counts in a group when its
        diameter is within CONST_HOLE_CAPTURE_TOLERANCES tolerances of the group's and, for a group with positions,
        its centre lies near one — the expected positions mirrored to all four corners, since the part may lie
        either way round. Each counted hole is then checked: its diameter, and for a positioned group its distance
        from its nearer long and short edge; and each pair of counted holes about Pitch_Mm apart, their pitch. A
        stepped hole's lower step is placed and measured at its step's centre (Seat_Holes), and checked for its
        offset from its step's axis with the camera's shift taken out (__Concentricity, with the view); the edges
        are the top face's, the side wall the camera sees left out (walls).

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (3) width_mm [float]: The crop's width (the part's short side).
        (4) height_mm [float]: The crop's height (the part's long side).
        (5) walls [Tuple<float> 1x4]: The side wall along the crop's left, top, right and bottom edge, in mm
                                      (Vision.Utilities.Classify.Wall_Widths); none by default.
        (6) view [Crop_View_Str(object) or None]: How the camera sees the crop (Vision.Utilities.Classify.Crop_View);
                                                  None leaves the concentricity unchecked.

    Returns:
        (1) parameter [Tuple]: (each group's count, every check), in group order.
    """

    candidates, offsets, width_mm, height_mm = __Prepare(candidates, groups, width_mm, height_mm, walls, view)
    counts, checks = [], []
    for group in groups:
        tolerance = group.Tolerance_Mm
        members = __Members(candidates, group, width_mm, height_mm)
        counts.append(Hole_Count_Str(Name=group.Name, Found=len(members), Expected=group.Count))
        for hole in members:
            checks.append(Check_Dimension('%s Ø' % group.Name, hole.Diameter_Mm, group.Diameter_Mm, tolerance))
            checks += [offsets[id(hole)]] if id(hole) in offsets else []
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
        The box a hole is recorded with: a square around its circle, CONST_HOLE_MARK_MARGIN_MM wider each way.

    Args:
        (1) x_mm, y_mm [float]: The centre.
        (2) diameter_mm [float]: The diameter.

    Returns:
        (1) parameter [Vector<Tuple<float> 1x2>]: The four corners, in mm.
    """

    r = diameter_mm / 2.0 + CONST_HOLE_MARK_MARGIN_MM
    return [(x_mm - r, y_mm - r), (x_mm + r, y_mm - r), (x_mm + r, y_mm + r), (x_mm - r, y_mm + r)]


def __Circle(x_mm: float, y_mm: float, diameter_mm: float) -> tp.List[tp.Tuple[float, float]]:
    """
    Description:
        The outline a hole expected and not found is drawn with: a circle of the catalogue's diameter at its
        position, as CONST_HOLE_CIRCLE_POINTS points.

    Args:
        (1) x_mm, y_mm [float]: The centre.
        (2) diameter_mm [float]: The diameter.

    Returns:
        (1) parameter [Vector<Tuple<float> 1x2>]: The points, in mm.
    """

    r = diameter_mm / 2.0
    return [(x_mm + r * math.cos(2.0 * math.pi * k / CONST_HOLE_CIRCLE_POINTS),
             y_mm + r * math.sin(2.0 * math.pi * k / CONST_HOLE_CIRCLE_POINTS)) for k in range(CONST_HOLE_CIRCLE_POINTS)]


def Hole_Features(candidates: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str], width_mm: float,
                  height_mm: float, walls: tp.Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
                  view: tp.Optional[Crop_View_Str] = None) -> tp.List[Feature_Str]:
    """
    Description:
        The holes as the frame marks them, on the upright crop (mm): each counted hole with its outline and checks (diameter;
        edge distances for a positioned group; the pitch to a neighbour, on both holes), failed when one fails or
        when its group holds more holes than the part has; and each hole expected but not found, at its position,
        outlined by a circle of its group's diameter (__Missing_Places). The positioned groups are placed first, so
        an unpositioned group's missing holes can sit at a through-hole that was itself placed, not found. A stepped
        hole's lower step is measured and boxed at its step's centre, its outline its own mask's (Seat_Holes); edge
        distances and missing holes' positions are from the top face's edges (walls), the marks on the crop; with the
        view, a stepped hole carries its concentricity check (Check_Holes).

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes found on the crop.
        (2) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (3) width_mm [float]: The crop's width (the part's short side).
        (4) height_mm [float]: The crop's height (the part's long side).
        (5) walls [Tuple<float> 1x4]: The side wall along the crop's left, top, right and bottom edge, in mm
                                      (Vision.Utilities.Classify.Wall_Widths); none by default.
        (6) view [Crop_View_Str(object) or None]: How the camera sees the crop; None leaves the concentricity
                                                  unchecked.

    Returns:
        (1) parameter [Vector<Feature_Str(object)>]: The holes, group by group, the found before the missing, on the
                                                     crop (mm).
    """

    features = __Face_Features(*__Prepare(candidates, groups, width_mm, height_mm, walls, view), groups)
    left, top = walls[0], walls[1]
    for feature in features:
        feature.Corners = [(x + left, y + top) for x, y in feature.Corners]
        feature.Outlines = [[(x + left, y + top) for x, y in outline] for outline in feature.Outlines]
    return features


def __Face_Features(candidates: tp.List[Hole_Str], offsets: tp.Dict[int, Dimension_Check_Str], width_mm: float,
                    height_mm: float, groups: tp.List[Catalogue_Hole_Group_Str]) -> tp.List[Feature_Str]:
    """
    Description:
        Hole_Features in the top face's frame: the holes seated and moved there, the face's size.

    Args:
        (1) candidates [Vector<Hole_Str(object)>]: The holes, seated, in the top face's frame.
        (2) offsets [Dict<int, Dimension_Check_Str(object)>]: Each stepped hole's concentricity check, by id.
        (3) width_mm [float]: The top face's width.
        (4) height_mm [float]: The top face's height.
        (5) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.

    Returns:
        (1) parameter [Vector<Feature_Str(object)>]: The holes, in the top face's frame (mm).
    """

    members = [__Members(candidates, group, width_mm, height_mm) for group in groups]
    places = {}
    for positioned in (True, False):
        placed = [(x, y) for group in groups if group.Name in places for x, y in places[group.Name]]
        for group, holes in zip(groups, members):
            if bool(group.From_Long_Edge_Mm) == positioned:
                places[group.Name] = __Missing_Places(group, holes, groups, members, placed, width_mm, height_mm)
    features = []
    for group, holes in zip(groups, members):
        features += __Found_Holes(group, holes, offsets, width_mm, height_mm)
        features += [Feature_Str(Kind='hole', Name=group.Name, Corners=__Square(x, y, group.Diameter_Mm),
                                 Outlines=[__Circle(x, y, group.Diameter_Mm)], Passed=False, Found=False)
                     for x, y in places[group.Name]]
    return features


def __Found_Holes(group: Catalogue_Hole_Group_Str, holes: tp.List[Hole_Str], offsets: tp.Dict[int, Dimension_Check_Str],
                  width_mm: float, height_mm: float) -> tp.List[Feature_Str]:
    """
    Description:
        A group's counted holes, each with its outline and checks: its diameter; its offset from its step's axis
        for a stepped hole; its edge distances for a positioned group; the pitch to each neighbour at about the
        group's pitch. A hole fails when one check fails or when its group holds more holes than the part has.

    Args:
        (1) group [Catalogue_Hole_Group_Str(object)]: The group.
        (2) holes [Vector<Hole_Str(object)>]: Its holes (__Members).
        (3) offsets [Dict<int, Dimension_Check_Str(object)>]: Each stepped hole's concentricity check, by id.
        (4) width_mm [float]: The crop's width (the part's short side).
        (5) height_mm [float]: The crop's height (the part's long side).

    Returns:
        (1) parameter [Vector<Feature_Str(object)>]: The holes, in the order given.
    """

    tolerance = group.Tolerance_Mm
    found = []
    for hole in holes:
        checks = [Check_Dimension('%s Ø' % group.Name, hole.Diameter_Mm, group.Diameter_Mm, tolerance)]
        checks += [offsets[id(hole)]] if id(hole) in offsets else []
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
        found.append(Feature_Str(Kind='hole', Name=group.Name, Corners=__Square(hole.X_Mm, hole.Y_Mm, hole.Diameter_Mm),
                                 Outlines=[hole.Outline], Passed=len(holes) <= group.Count and all(check.Within for check in checks),
                                 Checks=checks, Score=hole.Score))
    return found


def __Missing_Places(group: Catalogue_Hole_Group_Str, holes: tp.List[Hole_Str], groups: tp.List[Catalogue_Hole_Group_Str],
                     members: tp.List[tp.List[Hole_Str]], placed: tp.List[tp.Tuple[float, float]], width_mm: float,
                     height_mm: float) -> tp.List[tp.Tuple[float, float]]:
    """
    Description:
        Where a group's missing holes are expected (none when it found all it has).

        A positioned group's are among its mirrored positions: all of them not holding a hole when it has as many
        holes, else those of the set of its size that holds the positions it is anchored at and best fits its pitch.
        It is anchored at the positions holding its own holes or, with none of its own, at those holding another
        group's found holes (a through-hole at its countersink). With no anchor at all none is placed: the mirrored
        positions are not centred on the part, and which end of the part is which cannot be told from its outline
        (design-decisions.md, KNOWN_ISSUES).

        An unpositioned group's are the centres of other groups' holes it would surround (a countersink at its
        through-hole), found or placed, the first ones without one of its own.

    Args:
        (1) group [Catalogue_Hole_Group_Str(object)]: The group.
        (2) holes [Vector<Hole_Str(object)>]: Its holes (__Members).
        (3) groups [Vector<Catalogue_Hole_Group_Str(object)>]: The side's groups.
        (4) members [Vector<Vector<Hole_Str(object)>>]: Each group's holes, in groups' order.
        (5) placed [Vector<Tuple<float> 1x2>]: The missing holes already placed for the positioned groups, (x, y) in mm.
        (6) width_mm [float]: The crop's width (the part's short side).
        (7) height_mm [float]: The crop's height (the part's long side).

    Returns:
        (1) parameter [Vector<Tuple<float> 1x2>]: The centres (x, y) in mm.
    """

    missing = max(0, group.Count - len(holes))
    if not missing:
        return []
    others = [(hole.X_Mm, hole.Y_Mm) for other, found in zip(groups, members) if other is not group for hole in found]
    if group.From_Long_Edge_Mm:
        positions = __Positions(group, width_mm, height_mm)
        gate = math.sqrt(2.0) * group.Tolerance_Mm + CONST_HOLE_POSITION_MARGIN_MM
        own = [any(math.hypot(hole.X_Mm - x, hole.Y_Mm - y) <= gate for hole in holes) for x, y in positions]
        if len(positions) == group.Count:
            return [position for position, held in zip(positions, own) if not held]
        anchored = own if any(own) else [any(math.hypot(ox - x, oy - y) <= gate for ox, oy in others)
                                         for x, y in positions]
        if not any(anchored):
            return []
        fits = [subset for subset in itertools.combinations(range(len(positions)), group.Count)
                if all(i in subset for i, held in enumerate(anchored) if held)]
        if not fits:
            return []
        best = min(fits, key=lambda subset: sum(abs(math.dist(positions[i], positions[j]) - (group.Pitch_Mm or 0.0))
                                                for i, j in itertools.combinations(subset, 2)))
        return [positions[i] for i in best if not own[i]]
    return [centre for centre in others + placed
            if not any(math.hypot(hole.X_Mm - centre[0], hole.Y_Mm - centre[1]) < group.Diameter_Mm / 2.0
                       for hole in holes)][:missing]
