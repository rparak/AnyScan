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
# File Name: JIC_SF_UI/Annotate.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp
# JIC_SF_UI: the palette (Qt-free)
from .Theme import Hex_To_Bgr, Verdict_Color, CONST_CHIP_NUMERAL

"""
Description:
    Initialization of constants.

    Image annotation in the JIC Smart Factory style, Qt-free (OpenCV and NumPy are passed in, so a headless exporter
    and the window draw the same pixels). Generalised from AnyScan's src/Vision/Utilities/Annotate.py, its detection
    structures removed: a caller passes boxes, corners, outlines and colour tokens. The rules
    (references/annotation.md):
      - an object is its box in its state's colour, unshifted, with its number on a chip of that colour in plain white;
      - a measured, non-symmetric object: a SOLID rotated outline (the measurement) inside a DASHED, half-weight
        axis-aligned outer box (the reference that carries the chip);
      - a feature (a hole, a stain) is a thinner box along the part's axes in its own check's colour, solid when
        found, dashed when expected and missing; its chip ('3.1') sits on the corner nearest the object's chip;
      - no halo, casing, rim or second colour anywhere; every weight scales off the image's larger side.
"""
# Every weight is tuned at a 1000 px larger side and scaled by max(h, w) / 1000.
#   Unit [int]
CONST_REF_DIM = 1000
CONST_BOX_W = 2
CONST_DASH = 10
CONST_DASH_GAP = 7
CONST_DASHED_W_FRACTION = 0.5
CONST_FEATURE_W = 1.0
CONST_FEATURE_DASH = 4
CONST_STAIN_TINT = 0.35
# The chip: a small tab whose numeral grows only gently with the image (clamped), plus its padding.
#   Unit [float] / [int]
CONST_CHIP_FONT = 0.5
CONST_CHIP_FONT_MIN = 0.6
CONST_CHIP_FONT_MAX = 1.1
CONST_CHIP_FONT_W = 2
CONST_CHIP_PAD = 6
# A feature's chip: its numeral at 0.6 of the object chip's (never below 0.4), on the corner nearest the object's chip;
# corners within 3 px count as equally near and the higher is taken; edges within 5 deg as equally level and the one
# running right is taken; a chip keeps 2 px clear of the others and slides along its edge until it does.
#   Unit [float]
CONST_FEATURE_CHIP_FRACTION = 0.6
CONST_FEATURE_CHIP_FONT_MIN = 0.4
CONST_FEATURE_CHIP_TIE_PX = 3.0
CONST_FEATURE_CHIP_TIE_DEG = 5.0
CONST_FEATURE_CHIP_GAP = 2


def Scale(shape: tp.Tuple[int, ...]) -> float:
    """
    Description:
        The drawing scale of an image: its larger side over CONST_REF_DIM (at least 0.6).

    Args:
        (1) shape [Tuple<int>]: The image's (h, w, ...) shape.

    Returns:
        (1) parameter [float]: The scale.
    """

    return max(0.6, max(shape[0], shape[1]) / float(CONST_REF_DIM))


def Chip_Font_Scale(scale: float) -> float:
    """
    Description:
        The chip numeral's cv2 font scale, clamped so the chip stays a small tab.

    Args:
        (1) scale [float]: The drawing scale.

    Returns:
        (1) parameter [float]: The font scale.
    """

    return min(CONST_CHIP_FONT_MAX, max(CONST_CHIP_FONT_MIN, CONST_CHIP_FONT * scale))


def Chip_Size(label: str, font_scale: float, cv2: tp.Any) -> tp.Tuple[int, int, int, int, int]:
    """
    Description:
        A chip's size for its numeral.

    Args:
        (1) label [string]: The numeral.
        (2) font_scale [float]: The font scale.
        (3) cv2 [module]: OpenCV.

    Returns:
        (1) parameter [Tuple<int> 1x5]: (width, height, thickness, padding, text height).
    """

    thickness = max(1, int(round(CONST_CHIP_FONT_W * font_scale)))
    pad = max(2, int(round(CONST_CHIP_PAD * font_scale)))
    (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    return tw + 2 * pad, th + baseline + 2 * pad, thickness, pad, th


def Draw_Chip(image: tp.Any, x: int, top: int, label: str, color: str, font_scale: float, cv2: tp.Any) -> None:
    """
    Description:
        A chip at (x, top): filled with its box's colour, the numeral in plain white.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The BGR image (mutated).
        (2) x, top [int]: The top-left corner.
        (3) label [string]: The numeral.
        (4) color [string]: The box's token.
        (5) font_scale [float]: The font scale.
        (6) cv2 [module]: OpenCV.
    """

    chip_w, chip_h, thickness, pad, th = Chip_Size(label, font_scale, cv2)
    cv2.rectangle(image, (x, top), (x + chip_w, top + chip_h), Hex_To_Bgr(color), thickness=-1)
    cv2.putText(image, label, (x + pad, top + pad + th), cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                Hex_To_Bgr(CONST_CHIP_NUMERAL), thickness, cv2.LINE_AA)


def Index_Chip_Rect(bbox: tp.Tuple[int, int, int, int], label: str, scale: float,
                    cv2: tp.Any) -> tp.Tuple[int, int, int, int]:
    """
    Description:
        Where an object's chip sits: a tab whose bottom is on the box's top edge at its top-left corner, flipped
        inside the box when the box is too near the image's top.

    Args:
        (1) bbox [Vector<int> 1x4]: (x, y, w, h).
        (2) label [string]: The numeral.
        (3) scale [float]: The drawing scale.
        (4) cv2 [module]: OpenCV.

    Returns:
        (1) parameter [Vector<int> 1x4]: (x, top, width, height).
    """

    chip_w, chip_h, _, _, _ = Chip_Size(label, Chip_Font_Scale(scale), cv2)
    x, y = bbox[0], bbox[1]
    top = y - chip_h if y - chip_h >= 0 else y
    return x, top, chip_w, chip_h


def Draw_Dashed_Line(image: tp.Any, start: tp.Tuple[float, float], end: tp.Tuple[float, float], color: str,
                     thickness: int, dash: float, gap: float, cv2: tp.Any) -> None:
    """
    Description:
        A dashed straight line (OpenCV has none).

    Args:
        (1) image [Matrix<uint8> HxWx3]: The BGR image (mutated).
        (2 - 3) start, end [Vector<float> 1x2]: The end points.
        (4) color [string]: The token.
        (5) thickness [int]: The weight in px.
        (6 - 7) dash, gap [float]: Dash and gap in px.
        (8) cv2 [module]: OpenCV.
    """

    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= 0.0:
        return
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    position, bgr = 0.0, Hex_To_Bgr(color)
    while position < length:
        stop = min(position + dash, length)
        cv2.line(image, (int(round(start[0] + ux * position)), int(round(start[1] + uy * position))),
                 (int(round(start[0] + ux * stop)), int(round(start[1] + uy * stop))), bgr, thickness, cv2.LINE_AA)
        position = stop + gap


def Draw_Dashed_Path(image: tp.Any, points: tp.List[tp.Tuple[float, float]], color: str, thickness: int,
                     dash: float, gap: float, cv2: tp.Any) -> None:
    """
    Description:
        A closed path dashed as ONE line: the dash runs on round a vertex, so a many-sided circle is dashed, not solid.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The BGR image (mutated).
        (2) points [Vector<Tuple<float> 1x2>]: The vertices; closed back to the first.
        (3) color [string]: The token.
        (4) thickness [int]: The weight.
        (5 - 6) dash, gap [float]: Dash and gap in px.
        (7) cv2 [module]: OpenCV.
    """

    bgr = Hex_To_Bgr(color)

    def Piece(piece: tp.List[tp.Tuple[float, float]]) -> None:
        for (x0, y0), (x1, y1) in zip(piece, piece[1:]):
            cv2.line(image, (int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1))), bgr, thickness,
                     cv2.LINE_AA)

    ring = list(points) + [points[0]]
    drawing, left, piece = True, dash, [ring[0]]
    for (x0, y0), (x1, y1) in zip(ring, ring[1:]):
        length, along = math.hypot(x1 - x0, y1 - y0), 0.0
        while length - along > left:
            along += left
            point = (x0 + (x1 - x0) * along / length, y0 + (y1 - y0) * along / length)
            if drawing:
                Piece(piece + [point])
            drawing, left, piece = not drawing, dash if not drawing else gap, [point]
        left -= length - along
        piece.append((x1, y1))
    if drawing:
        Piece(piece)


def Draw_Object(image: tp.Any, bbox: tp.Tuple[int, int, int, int], number: int, color: str, cv2: tp.Any,
                rotated: tp.Optional[tp.List[tp.Tuple[float, float]]] = None,
                outline_color: tp.Optional[str] = None) -> None:
    """
    Description:
        One object: without a rotated outline, a solid box at the full weight; with one (a measured, non-symmetric
        part), the outline SOLID at the full weight in outline_color (its own check's colour, default the box's) and
        the axis-aligned box DASHED at half weight. Then its number on a chip of the box's colour.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The BGR image (mutated).
        (2) bbox [Vector<int> 1x4]: (x, y, w, h).
        (3) number [int]: The 1-based object number.
        (4) color [string]: The state's token (Theme.Verdict_Color(state)[0]), or CONST_DETECTION_BOX.
        (5) cv2 [module]: OpenCV.
        (6) rotated [Vector<Tuple<float> 1x2> or None]: The rotated outline's four corners.
        (7) outline_color [string or None]: The outline's own check colour.
    """

    scale = Scale(image.shape)
    box_w = max(1, int(round(CONST_BOX_W * scale)))
    x, y, w, h = bbox
    if rotated:
        dashed_w = max(1, int(round(box_w * CONST_DASHED_W_FRACTION)))
        corners = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
        for k in range(4):
            Draw_Dashed_Line(image, corners[k], corners[(k + 1) % 4], color, dashed_w, CONST_DASH * scale,
                             CONST_DASH_GAP * scale, cv2)
        bgr = Hex_To_Bgr(outline_color or color)
        for k in range(4):
            (x0, y0), (x1, y1) = rotated[k], rotated[(k + 1) % 4]
            cv2.line(image, (int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1))), bgr, box_w,
                     cv2.LINE_AA)
    else:
        cv2.rectangle(image, (x, y), (x + w, y + h), Hex_To_Bgr(color), box_w)
    cx, top, _, _ = Index_Chip_Rect(bbox, str(number), scale, cv2)
    Draw_Chip(image, cx, top, str(number), color, Chip_Font_Scale(scale), cv2)


def Tint_Regions(image: tp.Any, polygons: tp.List[tp.Any], color: str, cv2: tp.Any, np: tp.Any,
                 alpha: float = CONST_STAIN_TINT) -> None:
    """
    Description:
        Lay a translucent tint of a colour over regions (a stain's pixels under the fail colour), so their shape shows.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The BGR image (mutated).
        (2) polygons [Vector<Matrix<float> Nx2>]: The regions' outlines.
        (3) color [string]: The token.
        (4) cv2 [module]: OpenCV.
        (5) np [module]: NumPy.
        (6) alpha [float]: The tint's opacity.
    """

    if not polygons:
        return
    tint = image.copy()
    cv2.fillPoly(tint, [np.int32(np.round(p)) for p in polygons], Hex_To_Bgr(color))
    cv2.addWeighted(tint, alpha, image, 1.0 - alpha, 0.0, dst=image)


def __Chip_Corner(box: tp.Any, anchor: tp.Tuple[float, float], scale: float, np: tp.Any) -> int:
    distance = np.linalg.norm(box - np.float64(anchor), axis=1)
    near = [k for k in range(4) if distance[k] <= distance.min() + CONST_FEATURE_CHIP_TIE_PX * scale]
    return min(near, key=lambda k: (box[k][1], distance[k]))


def __Chip_Edge(box: tp.Any, corner: int, np: tp.Any) -> tp.Any:
    edges = [np.float64([box[corner], box[(corner + 1) % 4]]), np.float64([box[corner], box[(corner - 1) % 4]])]
    tilt = [math.degrees(math.atan2(abs(e[1][1] - e[0][1]), abs(e[1][0] - e[0][0]))) for e in edges]
    if abs(tilt[0] - tilt[1]) > CONST_FEATURE_CHIP_TIE_DEG:
        return edges[0] if tilt[0] < tilt[1] else edges[1]
    return min(edges, key=lambda e: (e[1][0] <= e[0][0], e[1][1] >= e[0][1]))


def __Draw_Turned_Chip(image: tp.Any, quad: tp.Any, label: str, color: str, font_scale: float, cv2: tp.Any,
                       np: tp.Any) -> None:
    chip_w, chip_h, _, _, _ = Chip_Size(label, font_scale, cv2)
    patch = np.zeros((chip_h + 1, chip_w + 1, 3), np.uint8)
    Draw_Chip(patch, 0, 0, label, color, font_scale, cv2)
    h, w = image.shape[:2]
    x0, y0 = max(0, int(math.floor(quad[:, 0].min())) - 1), max(0, int(math.floor(quad[:, 1].min())) - 1)
    x1, y1 = min(w, int(math.ceil(quad[:, 0].max())) + 2), min(h, int(math.ceil(quad[:, 1].max())) + 2)
    if x1 <= x0 or y1 <= y0:
        return
    warp = cv2.getAffineTransform(np.float32([[0, 0], [chip_w, 0], [0, chip_h]]),
                                  np.float32([quad[0], quad[1], quad[3]]) - np.float32([x0, y0]))
    size = (x1 - x0, y1 - y0)
    chip = cv2.warpAffine(patch, warp, size, flags=cv2.INTER_LINEAR).astype(np.float32)
    alpha = cv2.warpAffine(np.full(patch.shape[:2], 255, np.uint8), warp, size, flags=cv2.INTER_LINEAR)
    alpha = alpha.astype(np.float32)[..., None] / 255.0
    region = image[y0:y1, x0:x1].astype(np.float32)
    image[y0:y1, x0:x1] = np.round(chip * alpha + region * (1.0 - alpha)).astype(np.uint8)


def Draw_Feature(image: tp.Any, corners: tp.Any, color: str, found: bool, label: str,
                 object_bbox: tp.Tuple[int, int, int, int], placed: tp.List[tp.Any], cv2: tp.Any, np: tp.Any,
                 outline: tp.Optional[tp.Any] = None) -> tp.Optional[tp.Any]:
    """
    Description:
        One feature of a judged part: its box along the part's axes (and its outline, a hole's contour or a missing
        hole's expected circle) at half the object's weight, solid when found and dashed when expected and missing, in
        its own check's colour (Verdict_Color('OK' or 'NOK')[0]); then its chip on the box's corner nearest the
        object's chip, along that corner's more level edge, turned with it, sliding along the edge until it keeps
        CONST_FEATURE_CHIP_GAP from the object's earlier chips.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The BGR image (mutated).
        (2) corners [Matrix<float> 4x2]: The feature's box, in order round it.
        (3) color [string]: Its check's token.
        (4) found [bool]: Found (solid) or expected and missing (dashed).
        (5) label [string]: Its number ('3.1'), or '' for no chip.
        (6) object_bbox [Vector<int> 1x4]: The object's (x, y, w, h): its chip's corner anchors the placement.
        (7) placed [Vector<Matrix<float> 4x2>]: The object's chips so far (appended to).
        (8) cv2 [module]: OpenCV.
        (9) np [module]: NumPy.
        (10) outline [Matrix<float> Nx2 or None]: The feature's own outline.

    Returns:
        (1) parameter [Matrix<float> 4x2 or None]: The chip grown by the gap, or None without a chip.
    """

    scale = Scale(image.shape)
    weight = max(1, int(round(CONST_FEATURE_W * scale)))
    dash = CONST_FEATURE_DASH * scale
    box = np.float64(corners)
    for path in [box] + ([np.float64(outline)] if outline is not None else []):
        if found:
            cv2.polylines(image, [np.int32(np.round(path))], True, Hex_To_Bgr(color), weight, cv2.LINE_AA)
        else:
            Draw_Dashed_Path(image, [(float(x), float(y)) for x, y in path], color, weight, dash, dash, cv2)
    if not label:
        return None
    font_scale = max(CONST_FEATURE_CHIP_FONT_MIN, CONST_FEATURE_CHIP_FRACTION * Chip_Font_Scale(scale))
    chip_w, chip_h, _, _, _ = Chip_Size(label, font_scale, cv2)
    corner = __Chip_Corner(box, (float(object_bbox[0]), float(object_bbox[1])), scale, np)
    start, end = __Chip_Edge(box, corner, np)
    length = float(np.linalg.norm(end - start))
    slide = (end - start) / length
    across = slide if slide[0] >= 0.0 else -slide
    up = np.float64([across[1], -across[0]])
    above = float((box.mean(axis=0) - start) @ up) < 0.0
    gap = CONST_FEATURE_CHIP_GAP * scale

    def Quad(offset: float, grow: float) -> tp.Any:
        foot = start + slide * offset - (across * chip_w if slide[0] < 0.0 else 0.0)
        top_left = foot + up * chip_h if above else foot
        return np.float32([top_left - (across - up) * grow, top_left + across * chip_w + (across + up) * grow,
                           top_left + across * chip_w - up * chip_h + (across - up) * grow,
                           top_left - up * chip_h - (across + up) * grow])

    offset = 0.0
    while offset < length and any(cv2.intersectConvexConvex(Quad(offset, 0.0), other)[0] > 0.0 for other in placed):
        offset += 1.0
    __Draw_Turned_Chip(image, Quad(offset, 0.0), label, color, font_scale, cv2, np)
    grown = Quad(offset, gap)
    placed.append(grown)
    return grown


def Fill_Mask(mask_image: tp.Any, mask: tp.Any, state: str) -> None:
    """
    Description:
        A label-mask silhouette: the object's pixels on the black ground in its state's fill, a tint in the box's own
        hue (within 5 deg, >= 40 % of its chroma), so the silhouette and its box outline read as one object.

    Args:
        (1) mask_image [Matrix<uint8> HxWx3]: The BGR mask image on black (mutated).
        (2) mask [Matrix<bool> HxW]: The object's pixels.
        (3) state [string]: 'OK', 'NOK' or 'Warning'.
    """

    mask_image[mask.astype(bool)] = Hex_To_Bgr(Verdict_Color(state)[2])
