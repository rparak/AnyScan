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
# File Name: ../test/Vision/Utilities/test_annotate.py
## =========================================================================== ##

# System (Default)
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


def test_label_mask_fills_each_object_with_a_tint_of_its_box_colour() -> None:
    """
    Description:
        The default label mask: a pure-black ground, each object filled with a light TINT
        of its own box colour (not flat white), with the SAME verdict-coloured bounding box
        as the annotated view. An OK object's fill is the OK fill and its box the OK box; a
        NOK object's fill is the NOK fill and its box the NOK box. The ground stays black.
    """

    objects = [__Object(40, 40, verdict='OK'), __Object(200, 300, verdict='NOK')]
    mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np, verdict_colored=True)
    ok_box, _, ok_fill = Theme.Verdict_Color('OK')
    nok_box, _, nok_fill = Theme.Verdict_Color('NOK')

    # A corner far from either block is pure black.
    assert tuple(int(c) for c in mask[5, 5]) == (0, 0, 0)
    # Each block's interior is its OWN verdict fill (sampled inside, away from the box edge).
    assert tuple(int(c) for c in mask[70, 70]) == Theme.Hex_To_Bgr(ok_fill)
    assert tuple(int(c) for c in mask[240, 340]) == Theme.Hex_To_Bgr(nok_fill)
    # Each object's box carries its own verdict colour, unshifted.
    assert __Has_Bgr(mask, Theme.Hex_To_Bgr(ok_box)) and __Has_Bgr(mask, Theme.Hex_To_Bgr(nok_box))


def test_detect_only_label_mask_fills_with_the_neutral_tint() -> None:
    """
    Description:
        With classification off (verdict_colored False) the label mask fills every object with the
        light neutral fill and draws its box in the mask's own DARKER neutral outline — not the
        frame's box colour, which the annotated frame keeps — so the outline stands clear of the
        light fill. No verdict fill or box leaks into either image.
    """

    objects = [__Object(40, 40, verdict='OK')]
    mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np, verdict_colored=False)
    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)
    annotated = Annotate.Draw_Annotated(scene, objects, cv2, np, verdict_colored=False)
    frame_box, _, neutral_fill = Theme.Detection_Color()
    mask_outline = Theme.Detection_Mask_Outline()

    assert tuple(int(c) for c in mask[70, 70]) == Theme.Hex_To_Bgr(neutral_fill)
    assert __Has_Bgr(mask, Theme.Hex_To_Bgr(mask_outline))          # the mask's own outline
    assert not __Has_Bgr(mask, Theme.Hex_To_Bgr(frame_box))         # not the frame's box
    assert __Has_Bgr(annotated, Theme.Hex_To_Bgr(frame_box))        # the frame keeps its box
    assert not __Has_Bgr(annotated, Theme.Hex_To_Bgr(mask_outline))
    # No verdict fill or box leaks in.
    assert not __Has_Bgr(mask, Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[2]))
    assert not __Has_Bgr(mask, Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0]))


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
    ann_ok = Annotate.Draw_Annotated(scene, ok_only, cv2, np, verdict_colored=True)
    mask_ok = Annotate.Draw_Label_Mask(ok_only, scene.shape, cv2, np, verdict_colored=True)
    assert __Has_Bgr(ann_ok, ok_bgr) and __Has_Bgr(mask_ok, ok_bgr)
    assert not __Has_Bgr(ann_ok, nok_bgr) and not __Has_Bgr(mask_ok, nok_bgr)

    nok_only = [__Object(150, 250, verdict='NOK')]
    ann_nok = Annotate.Draw_Annotated(scene, nok_only, cv2, np, verdict_colored=True)
    mask_nok = Annotate.Draw_Label_Mask(nok_only, scene.shape, cv2, np, verdict_colored=True)
    assert __Has_Bgr(ann_nok, nok_bgr) and __Has_Bgr(mask_nok, nok_bgr)
    assert not __Has_Bgr(ann_nok, ok_bgr) and not __Has_Bgr(mask_nok, ok_bgr)


def test_mask_separates_near_but_distinct_objects() -> None:
    """
    Description:
        Two objects that sit close together but do NOT touch stay separate: each is its
        own tinted component with its own outline, and the black ground still runs between
        them — the mask reads as two objects, not one.
    """

    objects = [__Object(150, 250, size=60), __Object(150, 330, size=60)]   # a 20px gap
    mask = Annotate.Draw_Label_Mask(objects, (CONST_H, CONST_W, 3), cv2, np, verdict_colored=True)
    ok_fill = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[2])

    # Each block has its own tinted fill (sampled inside, clear of border and numeral).
    assert tuple(int(c) for c in mask[165, 260]) == ok_fill
    assert tuple(int(c) for c in mask[165, 340]) == ok_fill
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
    mask = Annotate.Draw_Label_Mask([], scene.shape, cv2, np, verdict_colored=True)
    assert int(np.count_nonzero(mask)) == 0
    annotated = Annotate.Draw_Annotated(scene, [], cv2, np, verdict_colored=True)
    assert annotated.shape == scene.shape


def test_annotated_is_box_and_numeral_only_in_the_unshifted_verdict_colour() -> None:
    """
    Description:
        The annotated view marks each object with its bounding box and index chip ONLY —
        no mask fill and no contour on the real frame — in the exact verdict colour,
        unshifted (there is no casing to alter it). On a green scene the object's interior
        still shows the scene (not a fill), and the verdict colour appears (the box/chip).
    """

    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)   # green table
    annotated = Annotate.Draw_Annotated(scene, [__Object(150, 250, size=80, verdict='OK')], cv2, np, verdict_colored=True)
    ok_bgr = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0])

    # The verdict colour appears (the box and chip), unshifted.
    assert __Has_Bgr(annotated, ok_bgr)
    # The object's interior is NOT filled — it still shows the scene, unchanged.
    assert tuple(int(c) for c in annotated[185, 285]) == (70, 150, 70)


def test_module_is_qt_free(top_level_imports) -> None:
    """
    Description:
        The renderer imports no Qt and no OpenCV/NumPy of its own — cv2/np are
        injected, so it renders in the Qt-free vision layer.
    """

    assert not top_level_imports(Annotate.__file__) & {'PyQt5', 'cv2', 'numpy'}


def __Coords(line: str) -> tp.List[float]:
    """The normalised coordinate floats of a seg line (everything after the class id)."""
    return [float(v) for v in line.split()[1:]]


def test_seg_lines_format_and_normalisation() -> None:
    """
    Description:
        Each segmentation line is '<class_id> x1 y1 x2 y2 …', the class id the object's 0-based
        index (as in the box file), the coordinates normalised to 0..1 at six decimals, and an
        even number of them (whole x,y pairs). Objects are emitted in list order.
    """

    objects = [__Object(40, 60, 80), __Object(200, 300, 100)]
    lines = Annotate.Seg_Lines(objects, (CONST_W, CONST_H), cv2, np)

    assert len(lines) == 2
    for index, line in enumerate(lines):
        parts = line.split()
        assert parts[0] == str(index)                    # class id is the object index
        coords = __Coords(line)
        assert len(coords) >= 6 and len(coords) % 2 == 0  # at least a triangle, whole pairs
        assert all(0.0 <= value <= 1.0 for value in coords)
        assert all(len(token.split('.')[1]) == 6 for token in parts[1:])  # six decimals


def test_seg_polygon_is_simplified_not_thousands_of_points() -> None:
    """
    Description:
        A curved contour is simplified with approxPolyDP so the file is usable: a filled circle,
        whose raw contour is hundreds of points, collapses to a few dozen while staying a valid
        polygon.
    """

    mask = np.zeros((CONST_H, CONST_W), dtype=np.uint8)
    cv2.circle(mask, (300, 200), 150, 1, -1)
    det = Detection_Str(Label='disc', Bbox=(150, 50, 300, 300), Mask=mask.astype(bool))

    (line,) = Annotate.Seg_Lines([det], (CONST_W, CONST_H), cv2, np)
    points = len(__Coords(line)) // 2
    assert 3 <= points <= 40                              # simplified, not the raw contour


def test_seg_keeps_only_the_outer_contour_for_a_holed_object() -> None:
    """
    Description:
        An object with a hole (a washer, the lattice bracket) keeps ONLY its outer contour —
        YOLO segmentation is one ring per instance. A square annulus yields a single polygon
        whose bounding box is the OUTER square (the hole is not carved out).
    """

    mask = np.zeros((CONST_H, CONST_W), dtype=np.uint8)
    mask[60:260, 60:260] = 1                              # outer 200x200 square
    mask[120:200, 120:200] = 0                            # an 80x80 hole in the middle
    det = Detection_Str(Label='washer', Bbox=(60, 60, 200, 200), Mask=mask.astype(bool))

    (line,) = Annotate.Seg_Lines([det], (CONST_W, CONST_H), cv2, np)
    coords = __Coords(line)
    xs = [coords[i] * CONST_W for i in range(0, len(coords), 2)]
    ys = [coords[i] * CONST_H for i in range(1, len(coords), 2)]
    # The polygon spans the OUTER square, so the hole was not emitted as a second ring.
    assert min(xs) <= 62 and max(xs) >= 258
    assert min(ys) <= 62 and max(ys) >= 258


def test_seg_falls_back_to_the_bbox_for_a_maskless_object() -> None:
    """
    Description:
        An object without a mask still gets a polygon — its bounding box as a four-point
        rectangle — so the seg file has one line per object, in the same order as the box file.
        (Fusion gives every object a mask, one found by the background cue alone included; this
        pins the guard for any other producer of a Detection_Str.)
    """

    det = Detection_Str(Label='bg', Bbox=(30, 40, 120, 60))   # no Mask
    (line,) = Annotate.Seg_Lines([det], (CONST_W, CONST_H), cv2, np)
    assert len(__Coords(line)) // 2 == 4                  # a rectangle


def test_verdict_colored_false_draws_one_neutral_colour_not_verdicts() -> None:
    """
    Description:
        When classification is off (verdict_colored=False), every object — OK or NOK — is drawn in
        the ONE neutral detection colour, and no verdict colour appears: not the OK indigo and,
        crucially, not the NOK magenta. With it on, the NOK object is drawn in the verdict magenta.
    """

    neutral = tuple(Theme.Hex_To_Bgr(Theme.CONST_DETECTION_COLORS[0]))
    nok = tuple(Theme.Hex_To_Bgr(Theme.CONST_VERDICT_COLORS['NOK'][0]))
    ok = tuple(Theme.Hex_To_Bgr(Theme.CONST_VERDICT_COLORS['OK'][0]))
    objects = [__Object(40, 60, 80, 'OK'), __Object(200, 300, 100, 'NOK')]

    def _Has(image, bgr):
        return bool((image == np.array(bgr, np.uint8)).all(axis=2).any())

    # Off: neutral present; neither verdict colour present.
    plain = Annotate.Draw_Annotated(np.full((CONST_H, CONST_W, 3), 30, np.uint8), objects,
                                    cv2, np, verdict_colored=False)
    assert _Has(plain, neutral)
    assert not _Has(plain, nok) and not _Has(plain, ok)

    # On: the NOK object is drawn in the verdict magenta; the neutral colour is not used.
    verdicted = Annotate.Draw_Annotated(np.full((CONST_H, CONST_W, 3), 30, np.uint8), objects,
                                        cv2, np, verdict_colored=True)
    assert _Has(verdicted, nok)
    assert not _Has(verdicted, neutral)


def test_neutral_detection_colour_is_a_distinct_token_from_the_verdicts() -> None:
    """
    Description:
        The neutral detection colour is its own token, not an alias of the OK verdict colour — the
        two mean different things and must be free to diverge.
    """

    assert Theme.CONST_DETECTION_COLORS != Theme.CONST_VERDICT_COLORS['OK']
    assert Theme.CONST_DETECTION_COLORS != Theme.CONST_VERDICT_COLORS['NOK']
    assert Theme.Detection_Color() == Theme.CONST_DETECTION_COLORS


def test_the_catalogue_states_render_in_their_colours_on_both_images() -> None:
    """
    Description:
        A Warning object is drawn in the amber box on the frame and on the mask, filled with the amber
        tint; an Unspecified one in the neutral box on the frame, and on the mask filled with the neutral
        fill and outlined in the mask's darker neutral — the neutral box would vanish on that fill.
    """

    scene = np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8)
    objects = [__Object(40, 40, verdict='Warning'), __Object(200, 300, verdict='Unspecified')]
    annotated = Annotate.Draw_Annotated(scene, objects, cv2, np, verdict_colored=True)
    mask = Annotate.Draw_Label_Mask(objects, scene.shape, cv2, np, verdict_colored=True)
    warn_box, _, warn_fill = Theme.Verdict_Color('Warning')
    neutral_box, _, neutral_fill = Theme.Verdict_Color('Unspecified')

    assert __Has_Bgr(annotated, Theme.Hex_To_Bgr(warn_box)) and __Has_Bgr(mask, Theme.Hex_To_Bgr(warn_box))
    assert tuple(int(c) for c in mask[70, 70]) == Theme.Hex_To_Bgr(warn_fill)
    assert __Has_Bgr(annotated, Theme.Hex_To_Bgr(neutral_box))
    assert tuple(int(c) for c in mask[240, 340]) == Theme.Hex_To_Bgr(neutral_fill)
    assert __Has_Bgr(mask, Theme.Hex_To_Bgr(Theme.Detection_Mask_Outline()))
    assert not __Has_Bgr(mask, Theme.Hex_To_Bgr(neutral_box))
