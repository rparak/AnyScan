## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../Vision/Utilities/Annotate.py
## =========================================================================== ##

# System (Default)
import colorsys
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the shared colour palette and the detection structure
#   ../Parameters/Theme
from Parameters.Theme import (Index_Color, Verdict_Color, Hex_To_Bgr, Delta_E,
                              CONST_CARD, CONST_INK)
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Initialization of constants.

    The annotation renderer: draws the annotated frame and the label mask from a list
    of detections, in the console's own palette (Parameters.Theme, the same tokens the
    UI reads). It is Qt-free — OpenCV and NumPy are injected — so the harness and the
    Qt-free vision layer render exactly what the UI would, keyed by the same
    Index_Color per object index. The live UI viewport paints its overlay with Qt from
    the SAME palette; the two agree because they share the tokens, not the primitives.

    Note:
        Two rules the drawing obeys, both from §1d:
          (1) Everything scales with resolution — line widths, font size, chip padding —
              off the frame's larger side (CONST_ANNOTATE_REF_DIM), so a stroke tuned
              for a preview is not a hairline on a 1920x1200 export.
          (2) A stroke colour that is too low-contrast against the object it outlines
              (a dark accent on a dark 003/005 part) falls back to the theme's
              contrasting foreground (white or ink), rather than inventing a colour.
"""
# The reference larger-side dimension the drawing weights are tuned at; every weight
# below is multiplied by max(h, w) / this.
#   Unit [int]
CONST_ANNOTATE_REF_DIM = 1000

# Line weights at the reference dimension (scaled up on a larger frame), so a stroke
# tuned for a preview is not a hairline on a 1920x1200 export.
#   Unit [int]
CONST_ANNOTATE_CONTOUR_W = 3      # object contour stroke
CONST_ANNOTATE_BOX_W = 2          # bounding-box stroke

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

# The translucent fill opacity of the object overlay. A blend ratio, not a pixel
# measure, so it does not scale with resolution.
#   Unit [float]
CONST_ANNOTATE_FILL_ALPHA = 0.40

# The minimum luminance-contrast ratio a stroke colour must clear against the object
# it outlines; below it the stroke is re-lit (see __Candidate_Strokes).
#   Unit [float]
CONST_ANNOTATE_CONTRAST_MIN = 1.7

# RETAINED (alternate mode). The minimum perceptual distance (CIE76 ΔE) between any two
# objects' coordinated stroke colours in the diagnostic index-fill mask mode. It no
# longer describes the default render, where every object is drawn in its verdict colour
# and two OK objects are deliberately identical; it guards Index_Color / __Assign_Strokes,
# kept for CONST_ANNOTATE_MASK_FILL == 'index'.
#   Unit [float]
CONST_ANNOTATE_MIN_DELTA_E = 12.0

# The half-width (px at the reference dimension, scaled) of the contrasting CASING drawn
# under every verdict stroke — a thin outline in the opposite luminance (white under a
# dark stroke, ink under a light one) so the stroke's edge stays defined on bright steel,
# on a dark plate, on the mask's white fill and on its black ground. The casing NEVER
# shifts the stroke's hue: a verdict colour that changed colour to gain contrast would
# stop reading as a verdict. Only the casing changes; the verdict colour is untouched.
#   Unit [int]
CONST_ANNOTATE_CASING_W = 1

# The black ground of the label mask. Deliberately NOT a theme surface colour: the
# mask is a diagnostic image, and on black the white object fills and their verdict
# contours separate cleanly and every silhouette edge stays sharp (§1c).
#   Unit [Vector<int> 1x3]
CONST_ANNOTATE_MASK_GROUND = (0, 0, 0)

# The label-mask fill mode. 'verdict' (default): every object is filled WHITE with a
# verdict-coloured contour and a dark numeral — the operator-facing result, coloured by
# pass/fail. 'index': the diagnostic variant that fills each object in its own
# Index_Color instead, so a merge (two parts sharing one colour) or an over-segmentation
# (one part in two colours) is visible; this is the one constant that switches the mask
# back to the per-object palette (see KNOWN_ISSUES.md).
#   Unit [string]
CONST_ANNOTATE_MASK_FILL = 'verdict'


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


def __Contrast(a: tp.Tuple[float, float, float], b: tp.Tuple[float, float, float]) -> float:
    """
    Description:
        The luminance-contrast ratio between two BGR colours (>= 1.0).

    Args:
        (1) a [Vector<float> 1x3]: The first colour (B, G, R).
        (2) b [Vector<float> 1x3]: The second colour (B, G, R).

    Returns:
        (1) parameter [float]: The contrast ratio.
    """

    la, lb = __Luminance(a), __Luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def __Relight(box_bgr: tp.Tuple[int, int, int], lightness: float) -> tp.Tuple[int, int, int]:
    """
    Description:
        The colour with its HUE and saturation held but its lightness set to `lightness`
        — a lighter or darker shade of the same colour.

    Args:
        (1) box_bgr [Vector<int> 1x3]: The colour (B, G, R).
        (2) lightness [float]: The target lightness (0..1).

    Returns:
        (1) parameter [Vector<int> 1x3]: The re-lit colour (B, G, R).
    """

    b, g, r = box_bgr[0] / 255.0, box_bgr[1] / 255.0, box_bgr[2] / 255.0
    hue, _, sat = colorsys.rgb_to_hls(r, g, b)
    nr, ng, nb = colorsys.hls_to_rgb(hue, lightness, sat)
    return (int(round(nb * 255)), int(round(ng * 255)), int(round(nr * 255)))


def __Bgr_Hex(bgr: tp.Tuple[int, int, int]) -> str:
    """
    Description:
        A (B, G, R) colour as a '#rrggbb' string, for the ΔE distance check.

    Args:
        (1) bgr [Vector<int> 1x3]: The colour (B, G, R).

    Returns:
        (1) parameter [string]: The colour as '#rrggbb'.
    """

    return '#%02x%02x%02x' % (int(bgr[2]), int(bgr[1]), int(bgr[0]))


def __Casing_Bgr(stroke_bgr: tp.Tuple[int, int, int]) -> tp.Tuple[int, int, int]:
    """
    Description:
        The casing colour drawn UNDER a verdict stroke: white when the stroke is dark,
        the theme ink when the stroke is light — the opposite luminance, so the stroke is
        always bounded by an edge that separates it from any ground. It is a neutral,
        never the verdict colour, and never a hue shift of the stroke: the casing carries
        no verdict meaning, only the stroke does.

    Args:
        (1) stroke_bgr [Vector<int> 1x3]: The verdict stroke colour (B, G, R).

    Returns:
        (1) parameter [Vector<int> 1x3]: The casing colour (B, G, R).
    """

    return Hex_To_Bgr(CONST_CARD) if __Luminance(stroke_bgr) < 0.5 else Hex_To_Bgr(CONST_INK)


def __Draw_Cased_Contours(image: tp.Any, contours: tp.Any, stroke_bgr: tp.Tuple[int, int, int],
                          width: int, casing_w: int, cv2: tp.Any) -> None:
    """
    Description:
        Draw contours as a verdict stroke over a thin contrasting casing: the casing
        first, wider by casing_w on each side, then the stroke on top. The stroke keeps
        its exact hue; the casing gives its edge local contrast on any ground.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2) contours [Vector]: The OpenCV contours.
        (3) stroke_bgr [Vector<int> 1x3]: The verdict stroke colour (B, G, R).
        (4) width [int]: The stroke width (px).
        (5) casing_w [int]: The casing half-width added on each side (px).
        (6) cv2 [module]: The OpenCV module, injected by the caller.
    """

    cv2.drawContours(image, contours, -1, __Casing_Bgr(stroke_bgr), width + 2 * casing_w)
    cv2.drawContours(image, contours, -1, stroke_bgr, width)


def __Draw_Cased_Rect(image: tp.Any, p1: tp.Tuple[int, int], p2: tp.Tuple[int, int],
                      stroke_bgr: tp.Tuple[int, int, int], width: int, casing_w: int,
                      cv2: tp.Any) -> None:
    """
    Description:
        Draw a rectangle as a verdict stroke over a thin contrasting casing — the casing
        wider by casing_w on each side, then the stroke on top — so the box edge stays
        defined on any ground without shifting the stroke's hue.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2) p1 [Vector<int> 1x2]: The top-left corner (x, y).
        (3) p2 [Vector<int> 1x2]: The bottom-right corner (x, y).
        (4) stroke_bgr [Vector<int> 1x3]: The verdict stroke colour (B, G, R).
        (5) width [int]: The stroke width (px).
        (6) casing_w [int]: The casing half-width added on each side (px).
        (7) cv2 [module]: The OpenCV module, injected by the caller.
    """

    cv2.rectangle(image, p1, p2, __Casing_Bgr(stroke_bgr), width + 2 * casing_w)
    cv2.rectangle(image, p1, p2, stroke_bgr, width)


def __Candidate_Strokes(box_bgr: tp.Tuple[int, int, int],
                        region_mean: tp.Any) -> tp.List[tp.Tuple[int, int, int]]:
    """
    Description:
        Every shade of the object's colour that clears the contrast against its part,
        ordered by nearness to the object's own lightness — the box colour itself first
        if it already clears. Keeping the hue and saturation and only moving the
        lightness means a re-lit stroke is still recognisably the object's colour, so
        the coordinated assignment can pick a distinct one without discarding identity.

    Args:
        (1) box_bgr [Vector<int> 1x3]: The object's box colour (B, G, R).
        (2) region_mean [Vector<float> 1x3]: The mean BGR of the object's pixels.

    Returns:
        (1) parameter [Vector<Tuple<int> 1x3>]: The contrast-clearing shades, nearest first.
    """

    region = tuple(float(c) for c in region_mean)
    own_lightness = colorsys.rgb_to_hls(box_bgr[2] / 255.0, box_bgr[1] / 255.0, box_bgr[0] / 255.0)[1]
    passing = []
    if __Contrast(box_bgr, region) >= CONST_ANNOTATE_CONTRAST_MIN:
        passing.append((0.0, tuple(int(c) for c in box_bgr)))
    for step in range(3, 98, 2):
        candidate = __Relight(box_bgr, step / 100.0)
        if __Contrast(candidate, region) >= CONST_ANNOTATE_CONTRAST_MIN:
            passing.append((abs(step / 100.0 - own_lightness) + 1e-3, candidate))
    passing.sort(key=lambda item: item[0])
    return [colour for _, colour in passing]


def Stroke_Colors(scene_bgr: tp.Any, objects: tp.List[Detection_Str],
                  cv2: tp.Any, np: tp.Any) -> tp.List[tp.Tuple[int, int, int]]:
    """
    Description:
        RETAINED (alternate mode) — NOT the default render, which draws every object in
        its verdict colour (Draw_Annotated). This is the per-object coordinated palette
        kept for the diagnostic index-fill mask (CONST_ANNOTATE_MASK_FILL == 'index') and
        any future per-object render: the colour its contour, box and chip would share,
        after the contrast fallback and the distinctness coordination. Exposed so the
        invariant (no two objects within CONST_ANNOTATE_MIN_DELTA_E) can be checked on a
        real frame, since the fallback is what could collapse two distinct colours.

    Args:
        (1) scene_bgr [Matrix<uint8> HxWx3]: The scene (BGR).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Tuple<int> 1x3>]: One stroke colour per object.
    """

    return [colour for colour, _ in __Assign_Strokes(scene_bgr, objects, np)]


def __Assign_Strokes(scene_bgr: tp.Any, objects: tp.List[Detection_Str],
                     np: tp.Any) -> tp.List[tp.Tuple[tp.Tuple[int, int, int], bool]]:
    """
    Description:
        Assign every object a stroke colour that both clears the contrast against its
        part AND stays at least CONST_ANNOTATE_MIN_DELTA_E from every already-assigned
        stroke, so no two objects ever render in near-identical colours. Each object
        takes the nearest contrast-clearing shade of its own colour that is still
        distinct from those placed before it; only when no shade is both is it forced to
        flat white (flagged, so the caller can log how often the palette is overridden).

    Args:
        (1) scene_bgr [Matrix<uint8> HxWx3]: The scene (BGR).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<Tuple>]: One (colour (B, G, R), forced_white [bool]) per object.
    """

    assigned, result = [], []
    for index, det in enumerate(objects):
        box_bgr = tuple(int(c) for c in Hex_To_Bgr(Index_Color(index)[0]))
        if det.Mask is None or int(np.count_nonzero(det.Mask)) == 0:
            candidates = [box_bgr]
        else:
            candidates = __Candidate_Strokes(box_bgr, scene_bgr[det.Mask.astype(bool)].mean(axis=0))
        chosen = next((colour for colour in candidates
                       if all(Delta_E(__Bgr_Hex(colour), __Bgr_Hex(other)) >= CONST_ANNOTATE_MIN_DELTA_E
                              for other in assigned)), None)
        forced = chosen is None
        if forced:
            chosen = tuple(int(c) for c in Hex_To_Bgr(CONST_CARD))
        assigned.append(chosen)
        result.append((chosen, forced))
    return result


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
        Draw the index chip as a tab on the object's box: a filled rectangle in the
        SAME colour as the box and contour (chip_bgr is the object's stroke colour, so
        it follows the contrast fallback — if the box goes white on a low-contrast
        part, so does the chip, and the label never stops matching its box). The chip
        is sized from the numeral's text extent plus a small padding, and seated flush
        against the box's top-left corner — its bottom on the box's top edge, left
        edges aligned — so it reads as a tab, not a floating marker. When the box is
        too near the top of the frame for the tab to sit above it, the chip flips
        INSIDE the box rather than clipping off-frame. The numeral takes whichever
        theme foreground (white or ink) contrasts with the chip's own colour, so a
        pale-variant chip gets dark text, not unreadable white.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2) bbox [Vector<int> 1x4]: The object's box as (x, y, w, h).
        (3) index [int]: The 0-based object index.
        (4) chip_bgr [Vector<int> 1x3]: The chip colour — the object's stroke colour.
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
    text_bgr = Hex_To_Bgr(CONST_CARD) if __Luminance(chip_bgr) < 0.5 else Hex_To_Bgr(CONST_INK)
    cv2.rectangle(image, (x, top), (x + chip_w, top + chip_h), chip_bgr, thickness=-1)
    # A thin casing outline around the chip, so its edge is defined on any ground the box
    # lands on — the same contrasting-casing rule the contour and box use.
    casing_w = max(1, int(round(CONST_ANNOTATE_CASING_W * scale)))
    cv2.rectangle(image, (x, top), (x + chip_w, top + chip_h), __Casing_Bgr(chip_bgr), casing_w)
    cv2.putText(image, label, (x + pad, top + pad + th), font, font_scale,
                text_bgr, thickness, cv2.LINE_AA)


def Draw_Annotated(scene_bgr: tp.Any, objects: tp.List[Detection_Str],
                   cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        The scene with each object drawn in its VERDICT colour (Theme.Verdict_Color):
        a translucent fill, the mask contour, the bounding box and the index chip, all in
        the one colour that its verdict decides — pass or fail — never a per-object or
        literal colour. Every object is OK until classification lands, so today they all
        render in the OK colour. Line widths, font and chip scale with the frame's
        resolution, and every stroke is drawn over a thin contrasting casing so it stays
        visible on bright steel and on the dark 003/005 plates WITHOUT shifting its hue.

    Args:
        (1) scene_bgr [Matrix<uint8> HxWx3]: The scene (BGR).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The annotated scene (BGR).
    """

    scale = __Scale(scene_bgr.shape)
    contour_w = max(1, int(round(CONST_ANNOTATE_CONTOUR_W * scale)))
    box_w = max(1, int(round(CONST_ANNOTATE_BOX_W * scale)))
    casing_w = max(1, int(round(CONST_ANNOTATE_CASING_W * scale)))

    # The translucent fill on its own layer, blended once at the end — in each object's
    # verdict colour.
    overlay = scene_bgr.copy()
    for det in objects:
        if det.Mask is None:
            continue
        overlay[det.Mask.astype(bool)] = Hex_To_Bgr(Verdict_Color(det.Verdict)[0])
    annotated = cv2.addWeighted(overlay, CONST_ANNOTATE_FILL_ALPHA, scene_bgr,
                                1.0 - CONST_ANNOTATE_FILL_ALPHA, 0.0)

    # The verdict colour drives the contour, box AND chip together, so an object's outline
    # and its label can never disagree, and its pass/fail reads the same in every part of
    # the annotation. Each is cased for contrast (see __Draw_Cased_*).
    for i, det in enumerate(objects):
        x, y, w, h = det.Bbox
        stroke = Hex_To_Bgr(Verdict_Color(det.Verdict)[0])
        if det.Mask is not None:
            contours, _ = cv2.findContours(det.Mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            __Draw_Cased_Contours(annotated, contours, stroke, contour_w, casing_w, cv2)
        __Draw_Cased_Rect(annotated, (x, y), (x + w, y + h), stroke, box_w, casing_w, cv2)
        __Draw_Index_Chip(annotated, det.Bbox, i, stroke, scale, cv2)
    return annotated


def Draw_Label_Mask(objects: tp.List[Detection_Str], shape: tp.Tuple[int, int, int],
                    cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        The segmentation result as a LABEL mask on a pure-black ground. In the default
        'verdict' mode each accepted object is filled WHITE, outlined with its
        verdict-coloured contour (over a contrasting casing) and numbered with a dark
        1-based index on the white fill. Each object is drawn from its OWN component mask,
        so two parts that sit close together but do not touch stay separate white shapes,
        each with its own outline — the mask reads as distinct objects. Two parts that
        TOUCH are already one component by the time they arrive here (Fuse_Objects), so
        they render as one shape with one contour; see KNOWN_ISSUES.md.

        The diagnostic 'index' mode (CONST_ANNOTATE_MASK_FILL == 'index') instead fills
        each object in its own Index_Color, so a merge (two parts one colour) or an
        over-segmentation (one part two colours) is visible at a glance — the one constant
        that switches the mask back to the per-object palette.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) shape [Tuple<int>]: The source frame's (h, w, c) shape.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The label mask (BGR) at the source size.
    """

    h, w = shape[:2]
    scale = __Scale(shape)
    contour_w = max(1, int(round(CONST_ANNOTATE_CONTOUR_W * scale)))
    casing_w = max(1, int(round(CONST_ANNOTATE_CASING_W * scale)))
    mask_image = np.zeros((h, w, 3), dtype=np.uint8)
    mask_image[:] = CONST_ANNOTATE_MASK_GROUND

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = __Chip_Font_Scale(scale)
    thickness = max(1, int(round(CONST_ANNOTATE_CHIP_FONT_W * font_scale)))
    white = Hex_To_Bgr(CONST_CARD)
    for i, det in enumerate(objects):
        if det.Mask is None:
            continue
        boolean = det.Mask.astype(bool)
        if CONST_ANNOTATE_MASK_FILL == 'index':
            # Diagnostic: fill each object in its own colour; the numeral contrasts it.
            fill_bgr = Hex_To_Bgr(Index_Color(i)[0])
            mask_image[boolean] = fill_bgr
            numeral_bgr = white if __Luminance(fill_bgr) < 0.5 else Hex_To_Bgr(CONST_INK)
        else:
            # Default: white fill, a verdict-coloured cased contour, a dark numeral.
            mask_image[boolean] = white
            contours, _ = cv2.findContours(det.Mask.astype(np.uint8), cv2.RETR_EXTERNAL,
                                           cv2.CHAIN_APPROX_SIMPLE)
            __Draw_Cased_Contours(mask_image, contours, Hex_To_Bgr(Verdict_Color(det.Verdict)[0]),
                                  contour_w, casing_w, cv2)
            numeral_bgr = Hex_To_Bgr(CONST_INK)
        x, y, bw, bh = det.Bbox
        label = str(i + 1)
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        cx, cy = x + bw // 2 - tw // 2, y + bh // 2 + th // 2
        cv2.putText(mask_image, label, (cx, cy), font, font_scale, numeral_bgr, thickness, cv2.LINE_AA)
    return mask_image
