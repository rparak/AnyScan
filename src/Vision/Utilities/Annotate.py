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
# File Name: ../Vision/Utilities/Annotate.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the shared colour palette and the detection structure
#   ../Parameters/Theme
from Parameters.Theme import (Verdict_Color, Detection_Color, Detection_Mask_Outline, Mask_Outline_Color,
                              Hex_To_Bgr, CONST_CARD, CONST_INK)
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Initialization of constants.

    The annotation renderer: draws the annotated frame and the label mask from a list
    of detections, in the console's own palette (Parameters.Theme, the same tokens the
    UI reads). It is Qt-free — OpenCV and NumPy are injected — so the harness and the
    Qt-free vision layer render exactly what the UI would, keyed by each object's VERDICT
    colour (Theme.Verdict_Color) or the one neutral detection colour when a configuration
    only detects. The UI shows these same renders (Render_Views), so the harness, the
    capture set and the screen agree by construction.

    Note:
        Everything scales with resolution — line widths, font size, chip padding — off the
        frame's larger side (CONST_ANNOTATE_REF_DIM), so a stroke tuned for a preview is not
        a hairline on a 1920x1200 export.
"""
# The reference larger-side dimension the drawing weights are tuned at; every weight
# below is multiplied by max(h, w) / this.
#   Unit [int]
CONST_ANNOTATE_REF_DIM = 1000

# The bounding-box line weight at the reference dimension (scaled up on a larger frame),
# so a box tuned for a preview is not a hairline on a 1920x1200 export.
#   Unit [int]
CONST_ANNOTATE_BOX_W = 2          # bounding-box stroke

# The Camera View draws a measured, non-symmetric object TWICE, in its one verdict colour: the
# rotated rectangle (the measurement) SOLID at the full box weight, and the axis-aligned box (now
# only the reference frame that carries the number chip) as a THIN DASHED line — so the two read
# as 'measurement' and 'reference', not as one confused shape. Symmetric and unmeasured objects
# keep the single solid axis-aligned box. Dash, gap and the dashed weight are at the reference
# dimension and scale with the frame like every other weight.
#   Unit [int/float]
CONST_ANNOTATE_DASH = 10
CONST_ANNOTATE_DASH_GAP = 7
CONST_ANNOTATE_DASHED_W_FRACTION = 0.5
# A judged part's feature marks (holes, stains): their line weight and the dash of a hole expected and
# not found, at the reference dimension; the tint laid over a stain's pixels.
#   Unit [float] (px) / [float] (px) / [float] (0-1)
CONST_ANNOTATE_FEATURE_W = 1.5
CONST_ANNOTATE_FEATURE_DASH = 4
CONST_ANNOTATE_STAIN_TINT = 0.35
# The light halo each side of a feature mark, so it holds on a dark plate (Image_092's right one) as on a light one.
#   Unit [int] (px)
CONST_ANNOTATE_HALO_PX = 2

# The index chip's numeral. Its font scales only gently with resolution and is capped
# (CONST_ANNOTATE_CHIP_FONT_MIN/MAX), so the chip stays a small tab — legible at 100%
# zoom and no larger — rather than growing with the frame until it dwarfs a small
# part. The chip itself is then sized from the numeral's text extent plus this padding.
#   Unit [float/int]
CONST_ANNOTATE_CHIP_FONT = 0.5    # cv2 font scale per unit __Scale
CONST_ANNOTATE_CHIP_FONT_MIN = 0.6
CONST_ANNOTATE_CHIP_FONT_MAX = 1.1
CONST_ANNOTATE_CHIP_FONT_W = 2    # cv2 font thickness
CONST_ANNOTATE_CHIP_PAD = 6       # padding (px, at font scale 1) around the numeral

# The perceptual distinctness floor (CIE76 ΔE) for the annotation colours: the minimum
# distance at which two colours read as different marks rather than a near-repeat. The renderer
# does not read it: it is the CONTRACT the annotation colours must meet — a box against its own
# fill, the neutral detection colour against the surfaces it is drawn on — enforced by
# test/Parameters/test_theme.py::test_neutral_detection_colour_is_distinct_and_off_the_indigo_axis.
# It lives beside the renderer it constrains, not in the test, so the two cannot drift apart.
#   Unit [float]
CONST_ANNOTATE_MIN_DELTA_E = 12.0

# The label-mask FILL floors (box/fill ΔE, fill/white ΔE, contrast against the black ground, hue
# and chroma) live in Parameters.Theme as CONST_MASK_FILL_*, because Theme derives the neutral fill
# from them and the parameters layer must not import this one.

# The black ground of the label mask. Deliberately NOT a theme surface colour: the
# mask is a diagnostic image, and on black the tinted object fills (each >= 4.5:1 against
# it) and their boxes separate cleanly and every silhouette edge stays sharp (§1c).
#   Unit [Vector<int> 1x3]
CONST_ANNOTATE_MASK_GROUND = (0, 0, 0)

# The segmentation-polygon simplification. approxPolyDP's epsilon is this FRACTION of the
# contour's own perimeter, so the tolerance is proportional to the object's size — a big part
# and a small part keep comparable relative fidelity, and a raw 1920x1200 contour of thousands
# of points collapses to a few dozen. The coordinates are written normalised at this many
# decimals, matching the YOLO box file.
#   Unit [float/int]
CONST_SEG_APPROX_EPS_FRAC = 0.01
CONST_SEG_DECIMALS = 6

def __Scale(shape: tp.Tuple[int, int, int]) -> float:
    """
    Description:
        The drawing scale for a frame — its larger side over the reference dimension —
        so every weight is derived from the resolution, never a fixed pixel count.

    Args:
        (1) shape [Tuple<int>]: The frame's (h, w, c) shape.

    Returns:
        (1) parameter [float]: The scale factor (>= a small floor).
    """

    return max(0.6, max(shape[0], shape[1]) / float(CONST_ANNOTATE_REF_DIM))


def __Luminance(bgr: tp.Tuple[float, float, float]) -> float:
    """
    Description:
        The relative luminance (0..1) of a BGR colour, for the contrast test.

    Args:
        (1) bgr [Vector<float> 1x3]: The colour as (B, G, R), 0..255.

    Returns:
        (1) parameter [float]: The relative luminance (0..1).
    """

    b, g, r = bgr[0] / 255.0, bgr[1] / 255.0, bgr[2] / 255.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def __Chip_Font_Scale(scale: float) -> float:
    """
    Description:
        The chip numeral's font scale: it tracks the drawing scale only gently and is
        clamped, so the chip stays a small legible tab instead of growing with the
        frame until it dwarfs a small part.

    Args:
        (1) scale [float]: The drawing scale (from __Scale).

    Returns:
        (1) parameter [float]: The clamped cv2 font scale.
    """

    return min(CONST_ANNOTATE_CHIP_FONT_MAX,
               max(CONST_ANNOTATE_CHIP_FONT_MIN, CONST_ANNOTATE_CHIP_FONT * scale))


def __Draw_Index_Chip(image: tp.Any, bbox: tp.Tuple[int, int, int, int], index: int,
                      chip_bgr: tp.Tuple[int, int, int], scale: float, cv2: tp.Any) -> None:
    """
    Description:
        Draw the index chip as a tab on the object's box: a filled rectangle in the SAME
        verdict colour as the box (chip_bgr is the object's verdict colour, so the label
        never stops matching its box), with ONLY the numeral in a contrasting tone. There
        is no outline or casing around the chip — a chip in one colour with a contrasting
        numeral reads as one thing, where an added casing read as two. The chip is sized
        from the numeral's text extent plus a small padding, seated flush against the
        box's top-left corner so it reads as a tab; when the box is too near the top of
        the frame for the tab to sit above it, the chip flips INSIDE the box rather than
        clipping off-frame. The numeral takes whichever theme foreground (white or ink)
        keeps it legible against the chip's own colour.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (3) index [int]: The 0-based object index.
        (4) chip_bgr [Vector<int> 1x3]: The chip colour — the object's verdict colour.
        (5) scale [float]: The drawing scale.
        (6) cv2 [module]: The OpenCV module, injected by the caller.
    """

    label = str(index + 1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = __Chip_Font_Scale(scale)
    thickness = max(1, int(round(CONST_ANNOTATE_CHIP_FONT_W * font_scale)))
    pad = max(2, int(round(CONST_ANNOTATE_CHIP_PAD * font_scale)))
    (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
    chip_w, chip_h = tw + 2 * pad, th + baseline + 2 * pad

    x, y, _, _ = bbox
    top = y - chip_h                     # a tab whose bottom sits on the box's top edge
    if top < 0:                          # box near the top: flip the tab inside the box
        top = y
    # The numeral's tone contrasts the chip's own verdict colour, so it stays legible
    # (both verdict colours are dark, so the numeral is the light theme card colour).
    text_bgr = Hex_To_Bgr(CONST_CARD) if __Luminance(chip_bgr) < 0.5 else Hex_To_Bgr(CONST_INK)
    cv2.rectangle(image, (x, top), (x + chip_w, top + chip_h), chip_bgr, thickness=-1)
    cv2.putText(image, label, (x + pad, top + pad + th), font, font_scale,
                text_bgr, thickness, cv2.LINE_AA)


def Draw_Annotated(scene_bgr: tp.Any, objects: tp.List[Detection_Str],
                   cv2: tp.Any, np: tp.Any, *, verdict_colored: bool) -> tp.Any:
    """
    Description:
        The scene with each object marked by its BOUNDING BOX (and, for a measured,
        non-symmetric object, its rotated rectangle, the box then dashed) and INDEX number
        ONLY — no mask fill and no contour on the real image, because the mask has its own view and
        its own file (Draw_Label_Mask). When verdict_colored, the box and chip are the object's
        VERDICT colour (Theme.Verdict_Color) — pass or fail; when not (a configuration that only
        DETECTS), every object is one NEUTRAL colour (Theme.Detection_Color), since there is no
        pass/fail to encode. Only the numeral is a contrasting tone against its chip. Line widths
        and font scale with the frame's resolution.

    Args:
        (1) scene_bgr [Matrix<uint8> HxWx3]: The scene (BGR).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.
        (5) verdict_colored [bool]: True to colour by verdict, False for the neutral colour.
                                    REQUIRED and keyword-only, with no default: the value is
                                    the configuration's General.Classification.Enabled, and a
                                    silent default renders one mode for a caller that never read
                                    the config — which is how the harness came to paint verdict
                                    colours on a detect-only run. Every caller states its intent.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The annotated scene (BGR).
    """

    scale = __Scale(scene_bgr.shape)
    annotated = scene_bgr.copy()
    __Draw_Boxes(annotated, objects, scale, cv2, verdict_colored, Detection_Color()[0],
                 draw_rotated=True)
    __Draw_Features(annotated, objects, scale, cv2, np)
    return annotated


def __Draw_Features(image: tp.Any, objects: tp.List[Detection_Str], scale: float, cv2: tp.Any, np: tp.Any) -> None:
    """
    Description:
        A judged part's features on the annotated frame (Detection_Str.Features): each hole and stain region as
        its rotated box, in the pass colour (the OK verdict's) or the fail colour (the NOK verdict's) — the
        same two colours that mark the objects, so a feature's colour means what an object's does; a hole expected
        and not found as a dashed box at its position; each stain's pixels under a tint of the fail colour, so its
        shape shows. Every mark is drawn over a light halo (the theme's card colour), so it holds on a dark plate as
        on a light one. No numbers or tags (the owner's ruling, 2026-10-11: they cluttered the frame); the parts'
        numbers are in the log.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The annotated frame (mutated).
        (2) objects [Vector<Detection_Str(object)>]: The objects, in order.
        (3) scale [float]: The drawing scale.
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) np [module]: The NumPy module, injected by the caller.
    """

    passed, failed = Hex_To_Bgr(Verdict_Color('OK')[0]), Hex_To_Bgr(Verdict_Color('NOK')[0])
    halo = Hex_To_Bgr(CONST_CARD)
    weight = max(1, int(round(CONST_ANNOTATE_FEATURE_W * scale)))
    dash, gap = CONST_ANNOTATE_FEATURE_DASH * scale, CONST_ANNOTATE_FEATURE_DASH * scale
    outlines = [np.int32(np.round(outline)) for det in objects for feature in det.Features if feature.Kind == 'stain'
                for outline in feature.Outlines]
    if outlines:
        tint = image.copy()
        cv2.fillPoly(tint, outlines, failed)
        cv2.addWeighted(tint, CONST_ANNOTATE_STAIN_TINT, image, 1.0 - CONST_ANNOTATE_STAIN_TINT, 0.0, dst=image)
    for det in objects:
        for feature in det.Features:
            corners = [(float(x), float(y)) for x, y in feature.Corners]
            if len(corners) < 3:
                continue
            color = passed if feature.Passed else failed
            edges = list(zip(corners, corners[1:] + corners[:1]))
            for line_w, line_color in ((weight + 2 * CONST_ANNOTATE_HALO_PX, halo), (weight, color)):
                for start, end in edges:
                    if feature.Found:
                        cv2.line(image, (int(round(start[0])), int(round(start[1]))),
                                 (int(round(end[0])), int(round(end[1]))), line_color, line_w, cv2.LINE_AA)
                    else:
                        __Draw_Dashed_Line(image, start, end, line_color, line_w, dash, gap, cv2)


def __Draw_Dashed_Line(image: tp.Any, start: tp.Tuple[float, float], end: tp.Tuple[float, float],
                       color_bgr: tp.Tuple[int, int, int], thickness: int, dash: float, gap: float,
                       cv2: tp.Any) -> None:
    """
    Description:
        A dashed straight line (OpenCV has none): dashes of `dash` px separated by `gap` px, the
        last dash clipped to the end point.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2 - 3) start, end [Vector<float> 1x2]: The end points (x, y) in pixels.
        (4) color_bgr [Vector<int> 1x3]: The line colour (B, G, R).
        (5) thickness [int]: The line weight in pixels.
        (6 - 7) dash, gap [float]: The dash and gap lengths in pixels.
        (8) cv2 [module]: The OpenCV module, injected by the caller.
    """

    length = math.hypot(end[0] - start[0], end[1] - start[1])
    if length <= 0.0:
        return
    ux, uy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
    position = 0.0
    while position < length:
        stop = min(position + dash, length)
        cv2.line(image, (int(round(start[0] + ux * position)), int(round(start[1] + uy * position))),
                 (int(round(start[0] + ux * stop)), int(round(start[1] + uy * stop))),
                 color_bgr, thickness, cv2.LINE_AA)
        position = stop + gap


def __Draw_Boxes(image: tp.Any, objects: tp.List[Detection_Str], scale: float,
                 cv2: tp.Any, verdict_colored: bool, neutral_hex: str,
                 draw_rotated: bool = False, on_mask: bool = False) -> None:
    """
    Description:
        Draw each object's bounding box and index chip on the image given — the same boxes and
        labels in the same places for the annotated frame and the label mask. The colour is each
        object's verdict colour (verdict_colored), or the neutral colour the caller passes: the
        frame's box on the annotated frame, and the mask's own darker outline on the label mask,
        where the outline sits only on the fill and on black and so must stand off a LIGHT fill.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (3) scale [float]: The drawing scale (from __Scale).
        (4) cv2 [module]: The OpenCV module, injected by the caller.
        (5) verdict_colored [bool]: True to colour by verdict, False for the neutral colour.
        (6) neutral_hex [string]: The neutral outline for this image (frame box or mask outline).
        (7) draw_rotated [bool]: Also draw each measured, non-symmetric object's rotated rectangle
                                 (solid), demoting its axis-aligned box to a thin dashed line. The
                                 Camera View's annotated frame does; the label mask does not.
        (8) on_mask [bool]: The image is the label mask: a verdict drawn in the neutral colour
                            (Unspecified) takes the mask's darker neutral outline (Mask_Outline_Color).
    """

    box_w = max(1, int(round(CONST_ANNOTATE_BOX_W * scale)))
    dashed_w = max(1, int(round(box_w * CONST_ANNOTATE_DASHED_W_FRACTION)))
    dash, gap = CONST_ANNOTATE_DASH * scale, CONST_ANNOTATE_DASH_GAP * scale
    neutral_bgr = Hex_To_Bgr(neutral_hex)
    for i, det in enumerate(objects):
        x, y, w, h = det.Bbox
        outline = Mask_Outline_Color(det.Verdict) if on_mask else Verdict_Color(det.Verdict)[0]
        color_bgr = Hex_To_Bgr(outline) if verdict_colored else neutral_bgr
        measurement = det.Measurement
        if draw_rotated and measurement is not None and not measurement.Symmetric \
                and measurement.Box_Points:
            corners = measurement.Box_Points
            for k in range(4):
                __Draw_Dashed_Line(image, ((x, y), (x + w, y), (x + w, y + h), (x, y + h))[k],
                                   ((x + w, y), (x + w, y + h), (x, y + h), (x, y))[k],
                                   color_bgr, dashed_w, dash, gap, cv2)
            for k in range(4):
                (x0, y0), (x1, y1) = corners[k], corners[(k + 1) % 4]
                cv2.line(image, (int(round(x0)), int(round(y0))), (int(round(x1)), int(round(y1))),
                         color_bgr, box_w, cv2.LINE_AA)
        else:
            cv2.rectangle(image, (x, y), (x + w, y + h), color_bgr, box_w)
        __Draw_Index_Chip(image, det.Bbox, i, color_bgr, scale, cv2)


def Draw_Label_Mask(objects: tp.List[Detection_Str], shape: tp.Tuple[int, int, int],
                    cv2: tp.Any, np: tp.Any, *, verdict_colored: bool) -> tp.Any:
    """
    Description:
        The segmentation result as a LABEL mask on a pure-black ground: each accepted
        object filled with a TINT of its own box colour (its silhouette), with
        EVERYTHING ELSE exactly as the annotated view — the same verdict-coloured bounding
        box and index chip, in the same place and the same colour. So the mask view is the
        annotated view with the real frame replaced by the segmentation: the operator
        compares the segmentation against the boxes without switching what the marks mean.
        Filling with a tint of the box (not flat white) makes the silhouette and its outline
        read as ONE object of the same hue, and the box outline still stands out because the
        tint is far from the box in ΔE (measured on the colour tokens). When classification
        is off the fill is the light neutral mask fill and the boxes and chips take the mask's
        own DARKER neutral outline (Theme.Detection_Mask_Outline) rather than the frame's box —
        the outline sits only on the fill and on black here, so it gives up the frame box's
        lightness to stand clear of a light fill — implying no verdict nobody made. Each
        object is filled from its OWN component mask, so two parts that sit close but do not
        touch stay separate shapes; two parts that TOUCH are already one component here
        (Fuse_Objects), so they render as one shape — see KNOWN_ISSUES.md.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) shape [Tuple<int>]: The source frame's (h, w, c) shape.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.
        (5) verdict_colored [bool]: True to colour the boxes and fills by verdict, False for
                                    the neutral detection colour. REQUIRED and keyword-only, like
                                    Draw_Annotated's — the caller passes the configuration's flag.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The label mask (BGR) at the source size.
    """

    h, w = shape[:2]
    scale = __Scale(shape)
    mask_image = np.zeros((h, w, 3), dtype=np.uint8)
    mask_image[:] = CONST_ANNOTATE_MASK_GROUND

    # The fill: a light tint of each object's own box colour (its verdict fill, or the
    # neutral detection fill when classification is off), so silhouette and box read as one
    # object.
    neutral_fill = Hex_To_Bgr(Detection_Color()[2])
    for det in objects:
        if det.Mask is None:
            continue
        fill_bgr = Hex_To_Bgr(Verdict_Color(det.Verdict)[2]) if verdict_colored else neutral_fill
        mask_image[det.Mask.astype(bool)] = fill_bgr

    # Then the same boxes and index chips as the annotated view, in the verdict colour — or, when
    # classification is off, in the mask's own darker neutral outline, which stays clear of the
    # light neutral fill (the frame's lighter box would all but vanish on it).
    __Draw_Boxes(mask_image, objects, scale, cv2, verdict_colored, Detection_Mask_Outline(), on_mask=True)
    return mask_image


def Render_Views(scene_bgr: tp.Any, objects: tp.List[Detection_Str], cv2: tp.Any, np: tp.Any, *,
                 verdict_colored: bool) -> tp.Tuple[tp.Any, tp.Any]:
    """
    Description:
        The two views of an analysis — the annotated frame and the label mask — rendered in one
        mode. The application window and the validation harness both render through this one
        function, so what the harness validates is by construction what the application shows and
        stores; only the mode (the configuration's classification flag) is theirs to pass.

    Args:
        (1) scene_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.
        (5) verdict_colored [bool]: REQUIRED, keyword-only: Configuration_Str.Classifies of the
            configuration in force — verdict colours when True, the neutral detection colour when
            False. No default, so a caller that never read the configuration fails at the call.

    Returns:
        (1) parameter [Tuple<Matrix<uint8> HxWx3> 1x2]: The (annotated, mask) images (BGR).
    """

    annotated = Draw_Annotated(scene_bgr, objects, cv2, np, verdict_colored=verdict_colored)
    mask = Draw_Label_Mask(objects, scene_bgr.shape, cv2, np, verdict_colored=verdict_colored)
    return annotated, mask


def __Object_Polygon(det: Detection_Str, cv2: tp.Any, np: tp.Any) -> tp.List[tp.Tuple[int, int]]:
    """
    Description:
        The simplified OUTER polygon of one object, in frame pixels. It comes from the
        contour of the SAME per-object mask the label mask fills — not recomputed — so the
        seg file, the YOLO file and both images describe identical objects. Only the outer
        contour is kept: a washer or the lattice bracket has holes, and YOLO segmentation is a
        single ring per instance, so the holes are dropped (documented in design-decisions).
        The contour is simplified with approxPolyDP at an epsilon proportional to its own
        perimeter, so a raw thousands-of-point contour becomes a few dozen. An object with no
        mask falls back to its bounding box as a rectangle, so every object still has a polygon
        in the same order as the boxes. The fusion stage gives every object its component mask —
        one found by the background cue alone included — so this guards other producers.

    Args:
        (1) det [Detection_Str(object)]: The object.
        (2) cv2 [module]: The OpenCV module, injected by the caller.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Tuple<int> 1x2>]: The polygon vertices (x, y) in pixels.
    """

    x, y, w, h = det.Bbox
    box_polygon = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if det.Mask is None:
        return box_polygon
    contours, _ = cv2.findContours(det.Mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return box_polygon
    contour = max(contours, key=cv2.contourArea)         # the outer boundary; holes ignored
    epsilon = CONST_SEG_APPROX_EPS_FRAC * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    return [(int(point[0][0]), int(point[0][1])) for point in approx]


def Seg_Lines(objects: tp.List[Detection_Str], size: tp.Tuple[int, int],
              cv2: tp.Any, np: tp.Any) -> tp.List[str]:
    """
    Description:
        One YOLO-segmentation line per object — '<class_id> <x1> <y1> <x2> <y2> … <xn> <yn>' —
        the object's simplified outer polygon, normalised to 0..1 against the frame at six
        decimals. The polygons come from the SAME ordered object list and the SAME per-object
        masks that drive the numbering, the boxes, the label mask and the Screen-Understanding
        text, so every artefact describes the same objects in the same order.

        The class id is the object's 0-BASED index, exactly as in the box file (Yolo_Lines):
        a per-frame handle, not a class — the same warning and caveat apply, so these files
        must not be used for training as-is (see docs/design-decisions.md).

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<string>]: One segmentation line per object, in order.
    """

    width, height = float(size[0]), float(size[1])
    lines = []
    for index, det in enumerate(objects):
        coordinates = []
        for (px, py) in __Object_Polygon(det, cv2, np):
            nx = min(1.0, max(0.0, px / width))
            ny = min(1.0, max(0.0, py / height))
            coordinates.append('%.*f' % (CONST_SEG_DECIMALS, nx))
            coordinates.append('%.*f' % (CONST_SEG_DECIMALS, ny))
        lines.append('%d %s' % (index, ' '.join(coordinates)))
    return lines
