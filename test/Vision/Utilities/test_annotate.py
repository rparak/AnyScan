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
# File Name: ../test/Vision/Utilities/test_annotate.py
## =========================================================================== ##

# System (Default)
import itertools
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the annotation renderer and the palette it reads
#   ../Vision/Utilities/Annotate
import Vision.Utilities.Annotate as Annotate
#   ../Parameters/Theme
import Parameters.Theme as Theme
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Tests for the annotation renderer. They build synthetic detections (a filled block
    each) and render at small and large sizes, so the palette keying, the black mask
    ground, the resolution scaling and the annotated/mask colour agreement are checked
    deterministically with no camera and no weights. cv2 and np are injected.
"""
# The synthetic frame size (h, w).
CONST_H = 400
CONST_W = 600


def __Object(top: int, left: int, size: int = 80, verdict: str = 'OK') -> Detection_Str:
    """
    Description:
        A detection with a filled square block mask, its tight box and a verdict.

    Args:
        (1 - 2) top, left [int]: The block's top-left corner.
        (3) size [int]: The block's side length.
        (4) verdict [string]: The per-object verdict ('OK' or 'NOK').

    Returns:
        (1) parameter [Detection_Str(object)]: The detection.
    """

    mask = np.zeros((CONST_H, CONST_W), dtype=bool)
    mask[top:top + size, left:left + size] = True
    return Detection_Str(Label='block', Bbox=(left, top, size, size), Mask=mask, Verdict=verdict)


def __Has_Bgr(image: np.ndarray, bgr: tp.Tuple[int, int, int]) -> bool:
    """
    Description:
        Whether any pixel of the image is exactly the given BGR colour — used to assert
        a verdict stroke is present, unshifted.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The image (BGR).
        (2) bgr [Vector<int> 1x3]: The colour (B, G, R).

    Returns:
        (1) parameter [bool]: True when the colour appears.
    """

    return bool(np.any(np.all(image == np.array(bgr, dtype=np.uint8), axis=-1)))


def test_label_mask_is_white_fill_verdict_contour_dark_numeral() -> None:
    """
    Description:
        The default label mask: a pure-black ground, each object filled WHITE, outlined
        in its VERDICT colour and numbered with the dark theme ink on the white fill. An
        OK object is outlined in the OK colour, a NOK object in the NOK colour.
    """

    objects = [__Object(40, 40, verdict='OK'), __Object(200, 300, verdict='NOK')]
    mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np)
    white = Theme.Hex_To_Bgr(Theme.CONST_CARD)
    ok_bgr = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0])
    nok_bgr = Theme.Hex_To_Bgr(Theme.Verdict_Color('NOK')[0])

    # A corner far from either block is pure black.
    assert tuple(int(c) for c in mask[5, 5]) == (0, 0, 0)
    # Each block's interior is WHITE fill (sampled inside, away from border and numeral).
    assert tuple(int(c) for c in mask[55, 55]) == white
    assert tuple(int(c) for c in mask[215, 315]) == white
    # Each object's contour carries its own verdict colour, unshifted.
    assert __Has_Bgr(mask, ok_bgr) and __Has_Bgr(mask, nok_bgr)
    # The dark numeral ink appears (on the white fill).
    assert __Has_Bgr(mask, Theme.Hex_To_Bgr(Theme.CONST_INK))


def test_verdict_colour_drives_the_stroke_in_both_renderers() -> None:
    """
    Description:
        The verdict, not the index, drives an object's colour in BOTH the annotated frame
        and the label mask: an OK object renders in the OK colour and never the NOK
        colour, and a NOK object the reverse — the same colour across the pair.
    """

    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)
    ok_bgr = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0])
    nok_bgr = Theme.Hex_To_Bgr(Theme.Verdict_Color('NOK')[0])

    ok_only = [__Object(150, 250, verdict='OK')]
    ann_ok = Annotate.Draw_Annotated(scene, ok_only, cv2, np)
    mask_ok = Annotate.Draw_Label_Mask(ok_only, scene.shape, cv2, np)
    assert __Has_Bgr(ann_ok, ok_bgr) and __Has_Bgr(mask_ok, ok_bgr)
    assert not __Has_Bgr(ann_ok, nok_bgr) and not __Has_Bgr(mask_ok, nok_bgr)

    nok_only = [__Object(150, 250, verdict='NOK')]
    ann_nok = Annotate.Draw_Annotated(scene, nok_only, cv2, np)
    mask_nok = Annotate.Draw_Label_Mask(nok_only, scene.shape, cv2, np)
    assert __Has_Bgr(ann_nok, nok_bgr) and __Has_Bgr(mask_nok, nok_bgr)
    assert not __Has_Bgr(ann_nok, ok_bgr) and not __Has_Bgr(mask_nok, ok_bgr)


def test_mask_separates_near_but_distinct_objects() -> None:
    """
    Description:
        Two objects that sit close together but do NOT touch stay separate: each is its
        own white component with its own outline, and the black ground still runs between
        them — the mask reads as two objects, not one.
    """

    objects = [__Object(150, 250, size=60), __Object(150, 330, size=60)]   # a 20px gap
    mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np)
    white = Theme.Hex_To_Bgr(Theme.CONST_CARD)

    # Each block has its own white fill (sampled inside, clear of border and numeral).
    assert tuple(int(c) for c in mask[165, 260]) == white
    assert tuple(int(c) for c in mask[165, 340]) == white
    # The full-height strip through the middle of the gap is black ground — no fill or
    # contour bridges the two, so they are two separate outlined shapes, not one merged.
    gap = mask[150:210, 318:323]
    assert int(np.count_nonzero(np.any(gap != 0, axis=-1))) == 0


def test_chip_numeral_font_is_capped() -> None:
    """
    Description:
        The chip numeral scales only gently with resolution and is clamped, so a 4x
        frame does not get a 4x numeral that would dwarf a small part. (Line widths
        still scale off the raw resolution; only the numeral is capped.)
    """

    chip_font = getattr(Annotate, '__Chip_Font_Scale')
    assert chip_font(0.1) == Annotate.CONST_ANNOTATE_CHIP_FONT_MIN     # clamped at the floor
    assert chip_font(50.0) == Annotate.CONST_ANNOTATE_CHIP_FONT_MAX    # clamped at the cap
    # A 4x resolution gives well under 4x the numeral (it is capped, not proportional).
    assert chip_font(4.0) < chip_font(1.0) * 4


def test_empty_objects_render_cleanly() -> None:
    """
    Description:
        No objects yields an all-black mask and the scene unchanged but for the blend
        of nothing — the zero case does not raise.
    """

    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)
    mask = Annotate.Draw_Label_Mask([], scene.shape, cv2, np)
    assert int(np.count_nonzero(mask)) == 0
    annotated = Annotate.Draw_Annotated(scene, [], cv2, np)
    assert annotated.shape == scene.shape


def __Bgr_Hex(bgr) -> str:
    """
    Description:
        A (B, G, R) stroke colour as '#rrggbb', for the ΔE distance check.

    Args:
        (1) bgr [Vector<int> 1x3]: The colour (B, G, R).

    Returns:
        (1) parameter [string]: The colour as '#rrggbb'.
    """

    return '#%02x%02x%02x' % (int(bgr[2]), int(bgr[1]), int(bgr[0]))


def test_coordinated_strokes_stay_distinct_after_fallback() -> None:
    """
    Description:
        RETAINED — guards the ALTERNATE per-object palette (Stroke_Colors /
        __Assign_Strokes), NOT the default render. The default now draws every object in
        its verdict colour, where two OK objects are deliberately identical; this
        invariant is kept for the diagnostic index-fill mask and any future per-object
        render, so the coordinated assignment is proven still to keep all pairs distinct.
        Twelve objects on a mid-grey part (the worst case: many need the contrast
        fallback), and every pair must stay at least CONST_ANNOTATE_MIN_DELTA_E apart.
    """

    n = 12
    scene = np.full((1000, 1600, 3), 128, np.uint8)     # mid grey — forces the fallback
    objects = []
    for i in range(n):
        row, col = i // 4, i % 4
        top, left = 40 + row * 240, 40 + col * 380
        mask = np.zeros(scene.shape[:2], dtype=bool)
        mask[top:top + 140, left:left + 140] = True
        objects.append(Detection_Str(Label='b', Bbox=(left, top, 140, 140), Mask=mask))

    strokes = [__Bgr_Hex(s) for s in Annotate.Stroke_Colors(scene, objects, cv2, np)]
    for a, b in itertools.combinations(range(n), 2):
        distance = Theme.Delta_E(strokes[a], strokes[b])
        assert distance >= Annotate.CONST_ANNOTATE_MIN_DELTA_E, \
            'objects %d and %d collapse (ΔE=%.1f): %s vs %s' % (a + 1, b + 1, distance,
                                                                strokes[a], strokes[b])


def test_casing_is_derived_by_luminance_and_preserves_hue() -> None:
    """
    Description:
        The contrast casing is DERIVED per stroke colour by luminance — a light casing
        under a dark stroke, a dark casing under a light one — never fixed, so a future
        light verdict colour cannot render an invisible outline. And the stroke's own hue
        is NEVER shifted for contrast: the exact verdict colour appears in the render on
        both a dark and a bright ground; only the casing changes.
    """

    casing = Annotate.__dict__[[k for k in Annotate.__dict__ if 'Casing_Bgr' in k][0]]
    white = Theme.Hex_To_Bgr(Theme.CONST_CARD)
    ink = Theme.Hex_To_Bgr(Theme.CONST_INK)
    assert casing(Theme.Hex_To_Bgr('#6C63B5')) == white     # dark OK stroke -> light casing
    assert casing(Theme.Hex_To_Bgr('#ff005c')) == white     # dark NOK stroke -> light casing
    assert casing(Theme.Hex_To_Bgr('#d9d2ff')) == ink       # a light stroke -> dark casing

    # The verdict colour is drawn unshifted on both a dark plate and bright steel.
    ok_bgr = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0])
    for ground in ((40, 40, 40), (210, 210, 210)):
        scene = np.full((CONST_H, CONST_W, 3), ground, np.uint8)
        annotated = Annotate.Draw_Annotated(scene, [__Object(150, 250, verdict='OK')], cv2, np)
        assert __Has_Bgr(annotated, ok_bgr)


def test_index_fill_mask_mode_is_reachable_by_one_constant() -> None:
    """
    Description:
        The diagnostic label-mask variant is reachable by the single constant
        CONST_ANNOTATE_MASK_FILL: set to 'index' it fills each object in its own
        Index_Color (to reveal a merge), instead of the default white fill.
    """

    objects = [__Object(40, 40), __Object(200, 300)]
    previous = Annotate.CONST_ANNOTATE_MASK_FILL
    try:
        Annotate.CONST_ANNOTATE_MASK_FILL = 'index'
        mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np)
        assert tuple(int(c) for c in mask[70, 70]) == Theme.Hex_To_Bgr(Theme.Index_Color(0)[0])
        assert tuple(int(c) for c in mask[230, 330]) == Theme.Hex_To_Bgr(Theme.Index_Color(1)[0])
    finally:
        Annotate.CONST_ANNOTATE_MASK_FILL = previous


def test_module_is_qt_free() -> None:
    """
    Description:
        The renderer imports no Qt and no OpenCV/NumPy of its own — cv2/np are
        injected, so it renders in the Qt-free vision layer.
    """

    source = open(Annotate.__file__).read()
    assert 'PyQt' not in source
    assert 'import cv2' not in source and 'import numpy' not in source
