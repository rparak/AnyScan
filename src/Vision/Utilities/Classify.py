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
from Parameters.Vision import Detection_Str, Scale_Str, Catalogue_Result_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Item_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Identification_Parameters_Str

"""
Description:
    Initialization of constants.

    The catalogue mode's verdict on each object, from its similarity to the item's reference images
    (Vision.Identifier), its area and its dimension checks (Vision.Utilities.Dimensions). Qt-free, OpenCV
    and NumPy injected. The rule, in order (docs/design-decisions.md, "A catalogue mode identifies by
    similarity, and an object of the part's shape that does not look like it is NOK"):

        (1) area >= Unspecified_Area_Ratio x the part's      -> Unspecified (probably several parts)
        (2) similarity >= Identify_Similarity                  -> the part: OK when every dimension
                                                                  check passes, else NOK
        (3) outline within the part's tolerance (below (2))    -> the part, NOK: its shape, not its look
        (4) anything else                                      -> Warning (not the part)

    (3) has no lower similarity bound, on purpose: an object of the part's size that does not look like
    it reads NOK, not Warning — in quality control the safer error — and a floor between the blank plate
    (0.54) and the other objects (at most 0.49) would have had 0.05 of margin.
"""

# How far from the frame centre the size checks were verified on real frames: the farthest centre of a
# catalogue part on the 41 frames of Data/Images/Test, measured with Center_Distance_Mm at the part's top
# face (2026-10-11), 74.24 mm, rounded up to the next 0.1 mm so that part is inside. (The request said
# 75 mm, from the frame-centre distances at the boards' scale; this is the same parts measured the way
# the check measures.) Beyond it the side wall is predicted to add up to about 1 mm (README >
# Limitations), so a size check there carries a note that it is not verified.
#   Unit [float] (mm)
CONST_VERIFIED_RADIUS_MM = 74.3
# The rotations each object's crop is compared in: the crop is turned upright (long side vertical) but
# not which end is up, nor which side of a square, so all four quarter turns are compared.
#   Unit [int]
CONST_CLASSIFY_ROTATIONS = 4


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
    corners = np.array(measurement.Box_Points, dtype=np.float32)
    side_a = float(np.linalg.norm(corners[1] - corners[0]))
    side_b = float(np.linalg.norm(corners[2] - corners[1]))
    if side_a >= side_b:
        # Corner 0 -> 1 is a long side: it becomes the left edge, running upwards.
        width, height = side_b, side_a
        target = np.array([[0, height], [0, 0], [width, 0], [width, height]], dtype=np.float32)
    else:
        width, height = side_a, side_b
        target = np.array([[0, 0], [width, 0], [width, height], [0, height]], dtype=np.float32)
    warp = cv2.getPerspectiveTransform(corners, target)
    return cv2.warpPerspective(frame_bgr, warp, (max(1, int(round(width))), max(1, int(round(height)))))


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
        A crop in its CONST_CLASSIFY_ROTATIONS quarter turns, the unturned one first.

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
        det.Verdict = 'Unspecified'
    elif similarity >= thresholds.Identify_Similarity:
        det.Verdict = 'OK' if outline_within else 'NOK'
    elif outline_within:
        det.Verdict = 'NOK'
    else:
        det.Verdict = 'Warning'
