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

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the shared colour palette and the detection structure
#   ../Parameters/Theme
from Parameters.Theme import (Index_Color, Hex_To_Bgr, CONST_CARD, CONST_INK)
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

# Drawing weights at the reference dimension (scaled up on a larger frame).
#   Unit [int/float]
CONST_ANNOTATE_CONTOUR_W = 3      # object contour stroke
CONST_ANNOTATE_BOX_W = 2          # bounding-box stroke
CONST_ANNOTATE_FONT = 1.1         # cv2 font scale
CONST_ANNOTATE_FONT_W = 2         # cv2 font thickness
CONST_ANNOTATE_CHIP_PAD = 8       # padding inside the index chip

# The translucent fill opacity of the object overlay. A blend ratio, not a pixel
# measure, so it does not scale with resolution.
#   Unit [float]
CONST_ANNOTATE_FILL_ALPHA = 0.40

# The minimum luminance-contrast ratio a stroke colour must clear against the object
# it outlines; below it the stroke falls back to a contrasting theme foreground.
#   Unit [float]
CONST_ANNOTATE_CONTRAST_MIN = 1.7

# The black ground of the label mask. Deliberately NOT a theme surface colour: the
# mask is a diagnostic image, and on black the object colours separate cleanly and
# every silhouette edge stays sharp (§1c).
#   Unit [Vector<int> 1x3]
CONST_ANNOTATE_MASK_GROUND = (0, 0, 0)


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


def __Stroke_Color(box_bgr: tp.Tuple[int, int, int], region_mean: tp.Any,
                   np: tp.Any) -> tp.Tuple[int, int, int]:
    """
    Description:
        The stroke colour for one object: its box colour, unless that is too low in
        contrast against the object's own pixels (a dark accent on a dark part), in
        which case it falls back to the theme's contrasting foreground — white on a
        dark object, ink on a light one — rather than inventing a colour.

    Args:
        (1) box_bgr [Vector<int> 1x3]: The object's box colour (B, G, R).
        (2) region_mean [Vector<float> 1x3]: The mean BGR of the object's pixels.
        (3) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Vector<int> 1x3]: The stroke colour (B, G, R).
    """

    region = tuple(float(c) for c in region_mean)
    if __Contrast(box_bgr, region) >= CONST_ANNOTATE_CONTRAST_MIN:
        return box_bgr
    return Hex_To_Bgr(CONST_CARD) if __Luminance(region) < 0.5 else Hex_To_Bgr(CONST_INK)


def __Draw_Index_Chip(image: tp.Any, top_left: tp.Tuple[int, int], index: int,
                      box_bgr: tp.Tuple[int, int, int], scale: float, cv2: tp.Any) -> None:
    """
    Description:
        Draw the index chip: a filled rounded-ish rectangle in the object's colour with
        the 1-based index in white, so the number is legible wherever it lands — on the
        green table or on a bright machined surface. The chip is a theme accent (an
        Index_Color), not a raw surface colour, because a white chip disappears on a
        bright plate; white text on the accent stays readable on either.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image to draw on (mutated).
        (2) top_left [Vector<int> 1x2]: The object box's (x, y) top-left corner.
        (3) index [int]: The 0-based object index.
        (4) box_bgr [Vector<int> 1x3]: The object's box colour (B, G, R).
        (5) scale [float]: The drawing scale.
        (6) cv2 [module]: The OpenCV module, injected by the caller.
    """

    label = str(index + 1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = CONST_ANNOTATE_FONT * scale
    thickness = max(1, int(round(CONST_ANNOTATE_FONT_W * scale)))
    pad = int(round(CONST_ANNOTATE_CHIP_PAD * scale))
    (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)

    x, y = top_left
    chip_h = th + baseline + 2 * pad
    top = max(0, y - chip_h)
    cv2.rectangle(image, (x, top), (x + tw + 2 * pad, top + chip_h), box_bgr, thickness=-1)
    cv2.putText(image, label, (x + pad, top + pad + th), font, font_scale,
                Hex_To_Bgr(CONST_CARD), thickness, cv2.LINE_AA)


def Draw_Annotated(scene_bgr: tp.Any, objects: tp.List[Detection_Str],
                   cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        The scene with each object drawn in the console palette: a translucent fill,
        the mask contour, the bounding box and the index chip, colour-keyed by index
        with Index_Color (the same colours the label mask and the UI use). Line widths,
        font and chip scale with the frame's resolution, and a low-contrast stroke
        falls back to a contrasting theme foreground.

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

    # The translucent fill on its own layer, blended once at the end.
    overlay = scene_bgr.copy()
    for i, det in enumerate(objects):
        if det.Mask is None:
            continue
        overlay[det.Mask.astype(bool)] = Hex_To_Bgr(Index_Color(i)[0])
    annotated = cv2.addWeighted(overlay, CONST_ANNOTATE_FILL_ALPHA, scene_bgr,
                                1.0 - CONST_ANNOTATE_FILL_ALPHA, 0.0)

    for i, det in enumerate(objects):
        box_bgr = Hex_To_Bgr(Index_Color(i)[0])
        x, y, w, h = det.Bbox
        if det.Mask is not None:
            mask_u8 = det.Mask.astype(np.uint8)
            region_mean = scene_bgr[det.Mask.astype(bool)].mean(axis=0) if int(mask_u8.sum()) else (0, 0, 0)
            stroke = __Stroke_Color(box_bgr, region_mean, np)
            contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(annotated, contours, -1, stroke, contour_w)
        else:
            stroke = box_bgr
        cv2.rectangle(annotated, (x, y), (x + w, y + h), stroke, box_w)
        __Draw_Index_Chip(annotated, (x, y), i, box_bgr, scale, cv2)
    return annotated


def Draw_Label_Mask(objects: tp.List[Detection_Str], shape: tp.Tuple[int, int, int],
                    cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        The segmentation result as a LABEL mask: a pure-black ground with each accepted
        object filled in its own Index_Color (the same colour as the annotated image,
        so object 3 matches between the two) and its 1-based index drawn on it. On black
        the object colours separate cleanly, so under-segmentation (two parts one
        colour) and over-segmentation (one part two colours) are visible at a glance.
        Written from the final component masks, so it shows exactly what the
        descriptions were generated from.

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
    mask_image = np.zeros((h, w, 3), dtype=np.uint8)
    mask_image[:] = CONST_ANNOTATE_MASK_GROUND

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = CONST_ANNOTATE_FONT * scale
    thickness = max(1, int(round(CONST_ANNOTATE_FONT_W * scale)))
    for i, det in enumerate(objects):
        if det.Mask is None:
            continue
        mask_image[det.Mask.astype(bool)] = Hex_To_Bgr(Index_Color(i)[0])
        x, y, bw, bh = det.Bbox
        label = str(i + 1)
        (tw, th), _ = cv2.getTextSize(label, font, font_scale, thickness)
        cx, cy = x + bw // 2 - tw // 2, y + bh // 2 + th // 2
        cv2.putText(mask_image, label, (cx, cy), font, font_scale,
                    Hex_To_Bgr(CONST_CARD), thickness, cv2.LINE_AA)
    return mask_image
