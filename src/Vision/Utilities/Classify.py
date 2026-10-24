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
# File Name: ../Vision/Utilities/Classify.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the detection, scale, catalogue and identification structures
#   ../Parameters/Vision
from Parameters.Vision import (Detection_Str, Scale_Str, Catalogue_Result_Str, Hole_Count_Str, Dimension_Check_Str,
                               Stain_Str, Crop_View_Str, CONST_PART_WARNING_KINDS)
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Item_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Identification_Parameters_Str

"""
Description:
    Initialization of constants.

    The catalogue mode's verdict on each object, from its similarity to the item's reference images
    (Vision.Identifier), its area and its dimension checks (Vision.Utilities.Dimensions). Qt-free, OpenCV
    and NumPy injected. The rule, in order (design-decisions.md, "A catalogue mode identifies by
    similarity, and an object of the part's shape that does not look like it is NOK"):

        (1) area >= Unspecified_Area_Ratio x the part's      -> Warning, several parts (touching or close)
        (2) similarity >= Identify_Similarity                  -> the part: OK when every dimension
                                                                  check passes, else NOK
        (3) outline within the part's tolerance (below (2))    -> the part, NOK: its shape, not its look
        (4) anything else                                      -> Warning, a foreign object (not the part)

    Then a part judged OK or NOK has its holes checked on the side up (Vision.Utilities.Holes, Apply_Holes):
    a missing or extra hole, or a hole out of tolerance, makes it NOK; and its stains, on a side that has the
    check (Apply_Stain). The side up is DINOv2's when its margin tells, or shown by a hole only that side has
    (Decide_Side); when neither tells, the part is judged on every side and a verdict that differs by side is a
    Warning, its side unclear, as is one whose holes and look show different sides, a side mismatch (Settle_Side).
    Last, any object whose outline leaves the station's inspection area (a rectangle inset from the frame's edges,
    Inspection_Area_Px) is a Warning, never judged (Settle_Area), outside the area or foreign; a part identified
    there is not checked. Whether an object resembles the part (Resembles_Part) is told apart from
    where it lies: an object the rule identified does, and outside the area, where a cut or far plate scores lower,
    an object that resembles it by its similarity, colour and visible extent; any other is a foreign object.

    (3) has no lower similarity bound, on purpose: an object of the part's size that does not look like
    it reads NOK, not Warning — in quality control the safer error — and a floor between the blank plate
    (0.54) and the other objects (at most 0.49) would have had 0.05 of margin.
"""

# How far from the frame centre the size checks were verified on real frames: the farthest centre of a
# judged mounting plate on the 41 frames of Data/Images/Test, measured with Center_Distance_Mm at the plate's
# top face (2026-10-13), 46.32 mm (Image_072), rounded up to the next 0.1 mm so that plate is inside. Plates
# placed farther out, in the corners of the view, would widen it (capture-checklist.md). Beyond it the
# side wall is predicted to add up to about 1 mm (README > Limitations), so a size check there carries a note
# that it is not verified.
#   Unit [float] (mm)
CONST_VERIFIED_RADIUS_MM = 46.4
# Whether an object outside the inspection area resembles the catalogue part, by cues that do not depend on where it
# lies (Resembles_Part), measured on 2026-10-16 on every object outside the area or cut by the frame's border in the
# test set and the five mounting-plate captures on disk (86: 43 plates, 43 foreign objects). The similarity: plates
# 0.668 at least (a stained front cut by the right border, 88.5 mm out), foreign objects 0.645 at most (the red
# block cut by the top border), so 0.657, midway; the other foreign objects score 0.433 at most. The colour, the mean
# saturation over the object's mask eroded by CONST_SATURATION_ERODE_PX: every one of the 73 plates measured, inside
# and out, fronts and backs, 20.2-40.4; the red block, wherever it lay (20 frames, similarity up to 0.673 inside the
# area), 112.3-134.1, so 76.3, midway. The visible extent (the largest distance across the mask) at most the part's
# diagonal plus its outline tolerance: plates 72.6 mm at most. A fully visible side was not used: by the frame's edge
# a cut plate's read up to 1.73 mm off 40 or 60 (the side wall), past the 1.5 tolerance, and a screw's 1.83 mm.
#   Unit [float] / [float] (OpenCV saturation, 0-255) / [int] (px)
CONST_OUTSIDE_SIMILARITY = 0.657
CONST_PART_MAX_SATURATION = 76.3
CONST_SATURATION_ERODE_PX = 15
# The margin of DINOv2's best side over the other at and above which it tells the side up. Measured on the same 72
# frames (2026-10-15): every back -0.455 to -0.554 at any distance (13); fronts +0.50 near the centre, falling with
# the distance and their stains to +0.004 at 59 mm, and the wrong side, -0.030 to -0.075, on 8 stained fronts 57-67 mm
# out. 0.265 is midway between the largest wrong margin and the smallest back's. Below it the side is the holes'
# (Holes.Side_Evidence) or, with none, judged on every side.
#   Unit [float]
CONST_SIDE_MARGIN = 0.265


def Object_Crop(frame_bgr: tp.Any, det: Detection_Str, cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        The image of one object the identifier compares: its measured rotated rectangle warped upright —
        long side vertical, the way the reference images show the parts — so the comparison does not
        depend on how the part lies. A round or unmeasured object has no rectangle to turn; it is cropped
        by its box.

    Args:
        (1) frame_bgr [Matrix<uint8> HxWx3]: The frame.
        (2) det [Detection_Str(object)]: The object.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The crop.
    """

    measurement = det.Measurement
    if measurement is None or measurement.Symmetric or not measurement.Box_Points:
        x, y, w, h = det.Bbox
        return frame_bgr[y:y + h, x:x + w]
    warp, (width, height) = __Upright(det, cv2, np)
    return cv2.warpPerspective(frame_bgr, warp, (max(1, int(round(width))), max(1, int(round(height)))))


def __Upright(det: Detection_Str, cv2: tp.Any, np: tp.Any) -> tp.Tuple[tp.Any, tp.Tuple[float, float]]:
    """
    Description:
        The warp from the frame to a measured object's upright crop (its rotated rectangle, long side vertical),
        and the crop's size.

    Args:
        (1) det [Detection_Str(object)]: The object, measured and not symmetric.
        (2) cv2 [module]: The OpenCV module.
        (3) np [module]: The NumPy module.

    Returns:
        (1) parameter [Tuple<Matrix<float> 3x3, Tuple<float> 1x2>]: (the warp, (width, height) in pixels).
    """

    corners = np.array(det.Measurement.Box_Points, dtype=np.float32)
    side_a = float(np.linalg.norm(corners[1] - corners[0]))
    side_b = float(np.linalg.norm(corners[2] - corners[1]))
    if side_a >= side_b:
        # Corner 0 -> 1 is a long side: it becomes the left edge, running upwards.
        width, height = side_b, side_a
        target = np.array([[0, height], [0, 0], [width, 0], [width, height]], dtype=np.float32)
    else:
        width, height = side_a, side_b
        target = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
    return cv2.getPerspectiveTransform(corners, target), (width, height)


def Crop_To_Frame(det: Detection_Str, points: tp.List[tp.Tuple[float, float]], cv2: tp.Any,
                  np: tp.Any) -> tp.List[tp.Tuple[float, float]]:
    """
    Description:
        Points on an object's crop (Object_Crop's pixels) taken back to the frame: through the inverse of the
        upright warp for a measured object, by the box's offset for one cropped by its box.

    Args:
        (1) det [Detection_Str(object)]: The object.
        (2) points [Vector<Tuple<float> 1x2>]: The points on its crop, in pixels.
        (3) cv2 [module]: The OpenCV module.
        (4) np [module]: The NumPy module.

    Returns:
        (1) parameter [Vector<Tuple<float> 1x2>]: The points in frame pixels.
    """

    if not points:
        return []
    measurement = det.Measurement
    if measurement is None or measurement.Symmetric or not measurement.Box_Points:
        return [(float(x) + det.Bbox[0], float(y) + det.Bbox[1]) for x, y in points]
    warp, _size = __Upright(det, cv2, np)
    back = cv2.perspectiveTransform(np.float32(points).reshape(-1, 1, 2), np.linalg.inv(warp)).reshape(-1, 2)
    return [(float(x), float(y)) for x, y in back]


def Wall_Widths(det: Detection_Str, K: tp.Any, scale: Scale_Str, thickness_mm: float, cv2: tp.Any,
                np: tp.Any) -> tp.Tuple[float, float, float, float]:
    """
    Description:
        How far the part's measured outline reaches past its top face along each edge of its upright crop: the side
        wall the camera sees on the edges facing the optical axis. Under the pinhole model the part's bottom edge
        projects towards the principal point by its distance from it times thickness / (the camera's distance to the
        table), so the silhouette there is the bottom edge; an edge facing away shows no wall. Measured on the
        mounting plate 61.6 mm out (20261015-143626_1): its outline 41.31 mm across against 39.3-40.2 near the
        centre, this predicting 0.93 mm of it. A hole's edge distance is measured from the top face (Holes.Check_Holes),
        where the catalogue gives it. Zero for an object cropped by its box (no rectangle to turn).

    Args:
        (1) det [Detection_Str(object)]: The part, measured.
        (2) K [Matrix<float> 3x3]: The camera matrix (focal lengths, principal point).
        (3) scale [Scale_Str(object)]: The scale at the part's top face.
        (4) thickness_mm [float]: The part's thickness.
        (5) cv2 [module]: The OpenCV module.
        (6) np [module]: The NumPy module.

    Returns:
        (1) parameter [Tuple<float> 1x4]: The wall along the crop's left, top, right and bottom edge, in mm.
    """

    measurement = det.Measurement
    if measurement is None or measurement.Symmetric or not measurement.Box_Points:
        return 0.0, 0.0, 0.0, 0.0
    _warp, (width, height) = __Upright(det, cv2, np)
    centre, *middles = Crop_To_Frame(det, [(width / 2.0, height / 2.0), (0.0, height / 2.0), (width / 2.0, 0.0),
                                           (width, height / 2.0), (width / 2.0, height)], cv2, np)
    mm_per_px = (scale.Mm_Per_Px_X + scale.Mm_Per_Px_Y) / 2.0
    focal = (float(K[0][0]) + float(K[1][1])) / 2.0
    # The camera's distance to the table (the part's bottom face), from the top face's scale: s = Z / f.
    table_mm = focal * mm_per_px + thickness_mm
    principal = (float(K[0][2]), float(K[1][2]))
    walls = []
    for middle in middles:
        normal = np.array(middle) - np.array(centre)
        normal /= max(float(np.linalg.norm(normal)), 1e-9)
        facing = -float(normal @ (np.array(middle) - np.array(principal)))
        walls.append(max(0.0, facing) * thickness_mm / table_mm * mm_per_px)
    return walls[0], walls[1], walls[2], walls[3]


def Crop_View(det: Detection_Str, K: tp.Any, scale: Scale_Str, thickness_mm: float, cv2: tp.Any,
              np: tp.Any) -> Crop_View_Str:
    """
    Description:
        How the camera sees a part's upright crop: the principal point taken onto the crop (through the upright warp,
        or by the box's offset for an object cropped by its box), in mm, and the camera's distance to the part's top
        face (focal length times the top face's scale). With it the shift of a feature below the top face towards the
        axis is predicted (Vision.Utilities.Holes, the concentricity check).

    Args:
        (1) det [Detection_Str(object)]: The part, measured.
        (2) K [Matrix<float> 3x3]: The camera matrix (focal lengths, principal point).
        (3) scale [Scale_Str(object)]: The scale at the part's top face.
        (4) thickness_mm [float]: The part's thickness.
        (5) cv2 [module]: The OpenCV module.
        (6) np [module]: The NumPy module.

    Returns:
        (1) parameter [Crop_View_Str(object)]: The view.
    """

    mm_per_px = (scale.Mm_Per_Px_X + scale.Mm_Per_Px_Y) / 2.0
    principal = (float(K[0][2]), float(K[1][2]))
    measurement = det.Measurement
    if measurement is None or measurement.Symmetric or not measurement.Box_Points:
        axis = (principal[0] - det.Bbox[0], principal[1] - det.Bbox[1])
    else:
        warp, _size = __Upright(det, cv2, np)
        axis = tuple(float(v) for v in cv2.perspectiveTransform(np.float32([[principal]]), warp).reshape(2))
    return Crop_View_Str(Axis_X_Mm=axis[0] * mm_per_px, Axis_Y_Mm=axis[1] * mm_per_px,
                         Distance_Mm=(float(K[0][0]) + float(K[1][1])) / 2.0 * mm_per_px, Thickness_Mm=thickness_mm)


def Reference_Crop(image_bgr: tp.Any, box: tp.Tuple[float, float, float, float]) -> tp.Any:
    """
    Description:
        The part in a reference image, cut out by its YOLO box (centre x, centre y, width, height, as
        fractions of the image).

    Args:
        (1) image_bgr [Matrix<uint8> HxWx3]: The reference image.
        (2) box [Vector<float> 1x4]: The YOLO box.

    Returns:
        (1) parameter [Matrix<uint8> hxwx3]: The crop.
    """

    height, width = image_bgr.shape[:2]
    cx, cy, bw, bh = box
    x0, y0 = int(round((cx - bw / 2.0) * width)), int(round((cy - bh / 2.0) * height))
    x1, y1 = int(round((cx + bw / 2.0) * width)), int(round((cy + bh / 2.0) * height))
    return image_bgr[max(0, y0):min(height, y1), max(0, x0):min(width, x1)]


def Rotations(crop: tp.Any, cv2: tp.Any) -> tp.List[tp.Any]:
    """
    Description:
        A crop in its four quarter turns, the unturned one first: each object's crop is turned upright
        (long side vertical) but not which end is up, nor which side of a square, so all four are compared.

    Args:
        (1) crop [Matrix<uint8> hxwx3]: The crop.
        (2) cv2 [module]: The OpenCV module, injected by the caller.

    Returns:
        (1) parameter [Vector<Matrix<uint8>>]: The four turns.
    """

    return [crop, cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE), cv2.rotate(crop, cv2.ROTATE_180),
            cv2.rotate(crop, cv2.ROTATE_90_COUNTERCLOCKWISE)]


def Best_Match(object_rows: tp.Any, reference_rows: tp.Any, sides: tp.List[str]) -> tp.Tuple[float, str]:
    """
    Description:
        An object's similarity to the part and the side it matched: the highest cosine between any of its
        rotations and any reference, with that reference's side.

    Args:
        (1) object_rows [Matrix<float> RxD]: The object's rotations, as unit rows.
        (2) reference_rows [Matrix<float> SxD]: The references, as unit rows, one per side.
        (3) sides [Vector<string>]: The references' sides, in row order.

    Returns:
        (1) parameter [Tuple<float, string>]: (similarity, side).
    """

    scores = object_rows @ reference_rows.T
    best = scores.max(axis=0)
    index = int(best.argmax())
    return float(best[index]), sides[index]


def Side_Similarities(object_rows: tp.Any, reference_rows: tp.Any, sides: tp.List[str]) -> tp.Dict[str, float]:
    """
    Description:
        An object's similarity to each side: the highest cosine between any of its rotations and that side's
        reference.

    Args:
        (1) object_rows [Matrix<float> RxD]: The object's rotations, as unit rows.
        (2) reference_rows [Matrix<float> SxD]: The references, as unit rows, one per side.
        (3) sides [Vector<string>]: The references' sides, in row order.

    Returns:
        (1) parameter [Dict<string, float>]: The similarity per side, in the references' order.
    """

    best = (object_rows @ reference_rows.T).max(axis=0)
    return {side: float(best[index]) for index, side in enumerate(sides)}


def Decide_Side(similarities: tp.Dict[str, float], evidence: tp.List[str]) -> tp.Tuple[str, str]:
    """
    Description:
        The side a part is checked on, and how it was decided. DINOv2's best side tells when its margin over the
        next is at least CONST_SIDE_MARGIN. A hole only one side has (Holes.Side_Evidence) tells wherever the part
        lies, so it decides when the margin does not; when DINOv2 tells the other side by its margin, the two
        conflict. With neither, the side is undecided: DINOv2's best is kept for the report and the part is judged
        on every side (Settle_Side).

        Measured (CONST_SIDE_MARGIN): DINOv2's margin falls with the distance from the frame centre, and on eight
        stained fronts 57-67 mm out it chose the back (by at most 0.075), which has neither the countersink check
        nor the stain check, so a stained front read OK. Their countersinks were found on every one.

    Args:
        (1) similarities [Dict<string, float>]: The similarity per side (Side_Similarities).
        (2) evidence [Vector<string>]: The sides the holes show (Holes.Side_Evidence).

    Returns:
        (1) parameter [Tuple<string> 1x2]: (the side, 'similarity', 'holes', 'conflict' or 'undecided').
    """

    ranked = sorted(similarities, key=lambda side: -similarities[side])
    best = ranked[0]
    margin = similarities[best] - (similarities[ranked[1]] if len(ranked) > 1 else 0.0)
    told = margin >= CONST_SIDE_MARGIN
    if len(evidence) == 1:
        shown = evidence[0]
        if shown == best and told:
            return best, 'similarity'
        return (best, 'conflict') if told else (shown, 'holes')
    return best, 'similarity' if told else 'undecided'


def Settle_Side(det: Detection_Str, verdicts: tp.Dict[str, str], how: str) -> None:
    """
    Description:
        A judged part's verdict once its side is known or not (Decide_Side), in place. Decided ('similarity',
        'holes'): it stands. Conflicting: a Warning, 'side_mismatch'. Undecided: each side's checks were run on it
        ('verdicts'); a verdict every side gives stands — an object of the part's shape that does not look like it
        is NOK on either — and one that differs by side is a Warning, 'side_unknown', so a front with the side
        unknown is never passed for a clean back. A part already a Warning stays so.

    Args:
        (1) det [Detection_Str(object)]: The part, judged and checked on its decided side (mutated).
        (2) verdicts [Dict<string, string>]: Its verdict as each side's checks give it.
        (3) how [string]: How the side was decided (Decide_Side).
    """

    det.Catalogue.Side_Evidence = how
    if det.Verdict not in ('OK', 'NOK'):
        return
    if how == 'conflict':
        det.Verdict, det.Catalogue.Warning_Kind = 'Warning', 'side_mismatch'
    elif how == 'undecided' and len(set(verdicts.values())) > 1:
        det.Verdict, det.Catalogue.Warning_Kind = 'Warning', 'side_unknown'


def Inspection_Area_Px(frame_size: tp.Tuple[int, int], scale: Scale_Str, long_edge_inset_mm: float,
                       short_edge_inset_mm: float) -> tp.Tuple[float, float, float, float]:
    """
    Description:
        The station's inspection area on the frame: the rectangle inset from the frame's long edges (top and bottom)
        and short edges (left and right) by the station's insets, converted at the scale in force (the part's top
        face in a catalogue mode), so it is centred on the frame centre. The one source of the rectangle: the verdict
        (Inside_Area) and the Camera View's line (UI.Widgets.Paint_Inspection_Area) both take it from here.

    Args:
        (1) frame_size [Vector<int> 1x2]: The frame's (width, height) in pixels.
        (2) scale [Scale_Str(object)]: The scale.
        (3) long_edge_inset_mm [float]: The inset from the top and bottom edges.
        (4) short_edge_inset_mm [float]: The inset from the left and right edges.

    Returns:
        (1) parameter [Tuple<float> 1x4]: (left, top, right, bottom) in pixels; a pixel at x, y is inside when
                                          left <= x <= right and top <= y <= bottom.
    """

    dx, dy = short_edge_inset_mm / scale.Mm_Per_Px_X, long_edge_inset_mm / scale.Mm_Per_Px_Y
    return dx, dy, frame_size[0] - 1 - dx, frame_size[1] - 1 - dy


def Inside_Area(det: Detection_Str, area_px: tp.Tuple[float, float, float, float], np: tp.Any) -> bool:
    """
    Description:
        Whether an object's whole outline lies inside the inspection area: every pixel of its mask, so a part cut by
        the frame's border (the area is inset from it) is never inside.

    Args:
        (1) det [Detection_Str(object)]: The object, with its mask.
        (2) area_px [Tuple<float> 1x4]: The area (Inspection_Area_Px).
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [bool]: True when the mask is non-empty and wholly inside.
    """

    if det.Mask is None:
        return False
    rows, columns = np.nonzero(det.Mask)
    if rows.size == 0:
        return False
    left, top, right, bottom = area_px
    return bool(columns.min() >= left and columns.max() <= right and rows.min() >= top and rows.max() <= bottom)


def Mean_Saturation(frame_bgr: tp.Any, det: Detection_Str, cv2: tp.Any, np: tp.Any) -> float:
    """
    Description:
        An object's colour cue: the mean HSV saturation over its mask eroded by CONST_SATURATION_ERODE_PX, so the table
        at its rim does not count (the whole mask when the eroded one is under 50 px).

    Args:
        (1) frame_bgr [Matrix<uint8> HxWx3]: The frame.
        (2) det [Detection_Str(object)]: The object, with its mask.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float]: The mean saturation, 0-255; 0 without a mask.
    """

    if det.Mask is None or not det.Mask.any():
        return 0.0
    mask = det.Mask.astype(np.uint8)
    core = cv2.erode(mask, np.ones((CONST_SATURATION_ERODE_PX, CONST_SATURATION_ERODE_PX), np.uint8)).astype(bool)
    if core.sum() < 50:
        core = mask.astype(bool)
    return float(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)[..., 1][core].mean())


def Visible_Extent_Mm(det: Detection_Str, scale: Scale_Str, cv2: tp.Any, np: tp.Any) -> float:
    """
    Description:
        An object's size cue that holds when it is cut: the largest distance across what is visible of it (between
        two points of its mask's convex hull), in mm at the scale in force. A plate's never exceeds its diagonal.

    Args:
        (1) det [Detection_Str(object)]: The object, with its mask.
        (2) scale [Scale_Str(object)]: The scale.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [float]: The extent; 0 without a mask.
    """

    if det.Mask is None or not det.Mask.any():
        return 0.0
    contours, _hierarchy = cv2.findContours(det.Mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hull = cv2.convexHull(np.vstack(contours)).reshape(-1, 2).astype(float) * np.array([scale.Mm_Per_Px_X,
                                                                                        scale.Mm_Per_Px_Y])
    gaps = hull[:, None, :] - hull[None, :, :]
    return float(np.sqrt((gaps ** 2).sum(axis=2)).max())


def Resembles_Part(det: Detection_Str, saturation: float, extent_mm: float, Catalogue_Item_Str: Catalogue_Item_Str) -> None:
    """
    Description:
        Whether an object resembles the catalogue part, in place (det.Catalogue.Resembles, with the cues read): one the
        verdict rule identified (OK, NOK, a Warning of a kind in CONST_PART_WARNING_KINDS) does; one it did not,
        outside the inspection area, where a cut or far plate scores lower than the rule's similarity, does when every
        position-free cue says so: its similarity at least CONST_OUTSIDE_SIMILARITY, its mean saturation at most
        CONST_PART_MAX_SATURATION and its visible extent at most the part's diagonal plus its outline tolerance. Inside
        the area an object the rule did not identify never does. Holes are not a cue: a foreign object can have one (the red block's countersink).

    Args:
        (1) det [Detection_Str(object)]: The object, classified, its Outside_Area set (mutated).
        (2) saturation [float]: Its mean saturation (Mean_Saturation).
        (3) extent_mm [float]: Its visible extent (Visible_Extent_Mm).
        (4) Catalogue_Item_Str [Catalogue_Item_Str(object)]: The catalogue item.
    """

    result = det.Catalogue
    result.Saturation, result.Extent_Mm = saturation, extent_mm
    outline = Catalogue_Item_Str.Outline
    if det.Verdict in ('OK', 'NOK') or result.Warning_Kind in CONST_PART_WARNING_KINDS:
        result.Resembles = True
        return
    result.Resembles = (result.Outside_Area and result.Similarity >= CONST_OUTSIDE_SIMILARITY
                        and saturation <= CONST_PART_MAX_SATURATION
                        and extent_mm <= math.hypot(outline.Length_Mm, outline.Width_Mm) + outline.Tolerance_Mm)


def Settle_Area(det: Detection_Str, inside: bool) -> None:
    """
    Description:
        An object's verdict once where it lies is known, in place: one whose outline leaves the inspection area is a
        Warning, whatever it was, since the final verdict is given only inside the area, and no check runs on it
        (Vision.Core): 'outside' when it resembles the part (Resembles_Part, run first), else 'foreign'. Inside the
        area the verdict stands.

    Args:
        (1) det [Detection_Str(object)]: The object, classified, its Resembles set (mutated).
        (2) inside [bool]: Whether its outline lies inside the area (Inside_Area).
    """

    det.Catalogue.Outside_Area = not inside
    if not inside:
        det.Verdict, det.Catalogue.Warning_Kind = 'Warning', 'outside' if det.Catalogue.Resembles else 'foreign'


def Best_Turn(object_rows: tp.Any, reference_rows: tp.Any, sides: tp.List[str], side: str) -> int:
    """
    Description:
        Which of an object's rotations (Rotations' order) matched the reference of the side it was judged on best.

    Args:
        (1) object_rows [Matrix<float> RxD]: The object's rotations, as unit rows.
        (2) reference_rows [Matrix<float> SxD]: The references, as unit rows, one per side.
        (3) sides [Vector<string>]: The references' sides, in row order.
        (4) side [string]: The side it was judged on.

    Returns:
        (1) parameter [int]: The rotation's index.
    """

    return int((object_rows @ reference_rows[sides.index(side)]).argmax())


def Similarity_Grid(object_patches: tp.Any, reference_patches: tp.Any, turn: int, np: tp.Any) -> tp.Any:
    """
    Description:
        How unlike its reference each patch of a judged part looks, for the similarity overlay: per patch of the
        part's best-matched rotation, 1 minus its highest cosine to any patch of the reference, laid out on the
        patch grid and turned back to the upright crop (Rotations turns clockwise; np.rot90 turns back). A
        diagnostic only: it shows where the part looks unlike the reference — a stain, but also glare or another
        engraving — and decides nothing.

    Args:
        (1) object_patches [Matrix<float> PxD]: The rotation's unit patch rows.
        (2) reference_patches [Matrix<float> PxD]: The reference's unit patch rows.
        (3) turn [int]: The rotation's index.
        (4) np [module]: The NumPy module.

    Returns:
        (1) parameter [Matrix<float> nxn]: The dissimilarity, 0 to 2, per patch of the upright crop.
    """

    side = int(round(math.sqrt(object_patches.shape[0])))
    grid = 1.0 - (object_patches @ reference_patches.T).max(axis=1).reshape(side, side)
    return np.rot90(grid, turn)


def Object_Area_Mm2(det: Detection_Str, scale: Scale_Str) -> float:
    """
    Description:
        The area of an object's mask in square millimetres at the scale in force (the part's top face).

    Args:
        (1) det [Detection_Str(object)]: The object, with its mask.
        (2) scale [Scale_Str(object)]: The scale.

    Returns:
        (1) parameter [float]: The area, 0 without a mask.
    """

    if det.Mask is None:
        return 0.0
    return float(det.Mask.sum()) * scale.Mm_Per_Px_X * scale.Mm_Per_Px_Y


def Center_Distance_Mm(det: Detection_Str, frame_size: tp.Tuple[int, int], scale: Scale_Str) -> float:
    """
    Description:
        How far an object's centre lies from the frame centre, in millimetres at the scale in force: the
        centre of its measured rectangle, or of its box when it has none.

    Args:
        (1) det [Detection_Str(object)]: The object.
        (2) frame_size [Vector<int> 1x2]: The frame's (width, height).
        (3) scale [Scale_Str(object)]: The scale.

    Returns:
        (1) parameter [float]: The distance.
    """

    measurement = det.Measurement
    if measurement is not None and measurement.Box_Points:
        cx = sum(x for x, _y in measurement.Box_Points) / len(measurement.Box_Points)
        cy = sum(y for _x, y in measurement.Box_Points) / len(measurement.Box_Points)
    else:
        x, y, w, h = det.Bbox
        cx, cy = x + w / 2.0, y + h / 2.0
    return math.hypot((cx - frame_size[0] / 2.0) * scale.Mm_Per_Px_X, (cy - frame_size[1] / 2.0) * scale.Mm_Per_Px_Y)


def Classify(det: Detection_Str, similarity: float, side: str, Catalogue_Item_Str: Catalogue_Item_Str,
             Identification_Parameters_Str: Identification_Parameters_Str, scale: Scale_Str,
             frame_size: tp.Tuple[int, int]) -> None:
    """
    Description:
        Set one object's verdict and the evidence for it (det.Verdict, det.Catalogue) by the rule in this
        module's description. The object's dimension checks must already be on it.

    Args:
        (1) det [Detection_Str(object)]: The object (mutated).
        (2) similarity [float]: Its similarity to the part (Best_Match).
        (3) side [string]: The side it matched.
        (4) Catalogue_Item_Str [Catalogue_Item_Str(object)]: The catalogue item.
        (5) Identification_Parameters_Str [Identification_Parameters_Str(object)]: The mode's thresholds.
        (6) scale [Scale_Str(object)]: The scale in force (the part's top face).
        (7) frame_size [Vector<int> 1x2]: The frame's (width, height).
    """

    outline = Catalogue_Item_Str.Outline
    thresholds = Identification_Parameters_Str
    area_ratio = Object_Area_Mm2(det, scale) / (outline.Length_Mm * outline.Width_Mm)
    names = {entry.Side: entry.Name for entry in Catalogue_Item_Str.Sides}
    det.Catalogue = Catalogue_Result_Str(Similarity=similarity, Side=side, Side_Name=names.get(side, side),
                                         Identify_Similarity=thresholds.Identify_Similarity,
                                         Area_Ratio=area_ratio, Unspecified_Area_Ratio=thresholds.Unspecified_Area_Ratio,
                                         Center_Distance_Mm=Center_Distance_Mm(det, frame_size, scale),
                                         Verified_Radius_Mm=CONST_VERIFIED_RADIUS_MM)
    outline_within = bool(det.Dimension_Checks) and all(check.Within for check in det.Dimension_Checks)
    if area_ratio >= thresholds.Unspecified_Area_Ratio:
        det.Verdict, det.Catalogue.Warning_Kind = 'Warning', 'several_parts'
    elif similarity >= thresholds.Identify_Similarity:
        det.Verdict = 'OK' if outline_within else 'NOK'
    elif outline_within:
        det.Verdict = 'NOK'
    else:
        det.Verdict, det.Catalogue.Warning_Kind = 'Warning', 'foreign'


def Apply_Holes(det: Detection_Str, counts: tp.List[Hole_Count_Str], checks: tp.List[Dimension_Check_Str]) -> None:
    """
    Description:
        A judged part's hole checks (Vision.Utilities.Holes.Check_Holes), in place: they are kept on the object
        (det.Hole_Counts, det.Hole_Checks), and an OK part with a hole missing or extra, or a hole out of
        tolerance, becomes NOK. A NOK part stays NOK; an object that is not the part is never hole-checked.

    Args:
        (1) det [Detection_Str(object)]: The object, judged OK or NOK (mutated).
        (2) counts [Vector<Hole_Count_Str(object)>]: Each group's count.
        (3) checks [Vector<Dimension_Check_Str(object)>]: Each hole's checks.
    """

    det.Hole_Counts, det.Hole_Checks = counts, checks
    failed = any(count.Found != count.Expected for count in counts) or not all(check.Within for check in checks)
    if det.Verdict == 'OK' and failed:
        det.Verdict = 'NOK'


def Apply_Stain(det: Detection_Str, stains: tp.List[Stain_Str]) -> None:
    """
    Description:
        A judged part's stain check (Vision.Utilities.Stain.Check_Stain), in place: the stains are kept on the
        object (det.Stains), and an OK part with any stain becomes NOK. A NOK part stays NOK.

    Args:
        (1) det [Detection_Str(object)]: The object, judged OK or NOK (mutated).
        (2) stains [Vector<Stain_Str(object)>]: The stains found; empty when the side is clean.
    """

    det.Stains = stains
    if det.Verdict == 'OK' and stains:
        det.Verdict = 'NOK'
