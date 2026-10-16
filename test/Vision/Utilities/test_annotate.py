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
# Pytest (Testing framework) [pip3 install pytest]
import pytest
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
        When classification is off (verdict_colored=False, Segment Anything), every object — OK or NOK — is drawn in
        the ONE detect-only colour, the logo purple, so no object's colour depends on a verdict: the NOK orange-red
        appears nowhere, and both objects' bottom edges are the purple. With it on, the NOK object is drawn in the
        verdict orange-red.
    """

    purple = tuple(Theme.Hex_To_Bgr('#640ABA'))
    nok = tuple(Theme.Hex_To_Bgr(Theme.CONST_VERDICT_COLORS['NOK'][0]))
    objects = [__Object(40, 60, 80, 'OK'), __Object(200, 300, 100, 'NOK')]

    def _Has(image, bgr):
        return bool((image == np.array(bgr, np.uint8)).all(axis=2).any())

    plain = Annotate.Draw_Annotated(np.full((CONST_H, CONST_W, 3), 30, np.uint8), objects,
                                    cv2, np, verdict_colored=False)
    assert not _Has(plain, nok)
    for x, y, w, h in (det.Bbox for det in objects):
        assert tuple(int(c) for c in plain[y + h, x + w // 2]) == purple        # the bottom edge is the purple

    verdicted = Annotate.Draw_Annotated(np.full((CONST_H, CONST_W, 3), 30, np.uint8), objects,
                                        cv2, np, verdict_colored=True)
    assert _Has(verdicted, nok)

def test_the_catalogue_states_render_in_their_colours_on_both_images() -> None:
    """
    Description:
        A Warning object is drawn in the amber box on the frame and on the mask, filled with the amber
        tint; an Unspecified one in the neutral box on the frame, and on the mask filled with the neutral
        fill and outlined in the mask's derived neutral — the neutral box misses the floor on the black ground.
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


def __Circle(cx: float, cy: float, r: float) -> tp.List[tp.Tuple[float, float]]:
    """A hole's outline: a circle of 72 points, in frame pixels."""
    return [(cx + r * np.cos(2 * np.pi * k / 72), cy + r * np.sin(2 * np.pi * k / 72)) for k in range(72)]


def __Square(cx: float, cy: float, half: float, degrees: float) -> tp.List[tp.Tuple[float, float]]:
    """A box along a part turned by degrees (clockwise on the frame): its four corners in order, in frame pixels."""
    t = np.radians(degrees)
    u, v = np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])
    return [tuple(np.array([cx, cy]) + u * a + v * b) for a, b in ((-half, -half), (half, -half), (half, half), (-half, half))]


def __Hole(part: str, cx: float, cy: float, r: float, degrees: float = 0.0, **kwargs: tp.Any) -> tp.Any:
    """A hole as the pipeline gives it: its recorded box (its circle, 5 px wider each way) and its outline."""
    from Parameters.Vision import Feature_Str
    return Feature_Str(Part=part, Kind='hole', Name='hole', Corners=__Square(cx, cy, r + 5, degrees),
                       Outlines=[__Circle(cx, cy, r)], **kwargs)


def __Judged(features: tp.List[tp.Any]) -> Detection_Str:
    """A judged plate on a 1920 x 1200 frame, its box (100, 100, 600, 600), carrying the features given."""
    mask = np.zeros((1200, 1920), dtype=bool)
    mask[100:700, 100:700] = True
    return Detection_Str(Label='plate', Bbox=(100, 100, 600, 600), Mask=mask, Verdict='NOK', Features=features)


def __Render(features: tp.List[tp.Any]) -> np.ndarray:
    """The annotated frame of a judged plate carrying the features, on a plain grey 1920 x 1200 scene."""
    return Annotate.Draw_Annotated(np.full((1200, 1920, 3), 90, np.uint8), [__Judged(features)], cv2, np,
                                   verdict_colored=True)


def __Near(image: np.ndarray, bgr: tp.Tuple[int, int, int], tolerance: int = 40) -> np.ndarray:
    """Where the image is within the tolerance of a colour (each channel), as a bool HxW map."""
    return (np.abs(image.astype(int) - np.array(bgr)) <= tolerance).all(axis=2)


def __Along(hits: np.ndarray, points: tp.List[tp.Tuple[float, float]], samples: int = 180) -> tp.List[bool]:
    """For points spread round a closed path, whether a hit lies within 1 px of each."""
    ring = np.float64(list(points) + [points[0]])
    lengths = np.linalg.norm(np.diff(ring, axis=0), axis=1)
    found = []
    for s in np.linspace(0.0, lengths.sum(), samples, endpoint=False):
        k = int(np.searchsorted(np.cumsum(lengths), s, side='right'))
        x, y = ring[k] + (ring[k + 1] - ring[k]) * (s - np.cumsum(lengths)[k - 1] if k else s) / lengths[k]
        found.append(bool(hits[int(round(y)) - 1:int(round(y)) + 2, int(round(x)) - 1:int(round(x)) + 2].any()))
    return found


def __Gaps(found: tp.List[bool]) -> int:
    """How many gaps a closed path's samples show (a run of misses after a hit)."""
    return sum(1 for a, b in zip(found, found[1:] + found[:1]) if a and not b)


def __Chips(image: np.ndarray, unnumbered: np.ndarray) -> tp.List[np.ndarray]:
    """The chips: where the render differs from the same features' render without numbers, each as its pixels (x, y)."""
    changed = (image != unnumbered).any(axis=2).astype(np.uint8)
    count, labels = cv2.connectedComponents(cv2.morphologyEx(changed, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)))
    return [np.column_stack(np.nonzero(labels == i)[::-1]).astype(float) for i in range(1, count)]


def test_a_found_holes_box_and_outline_are_solid_in_one_colour_thinner_than_the_object_without_a_halo() -> None:
    """
    Description:
        On the annotated frame (rendered pixels, 1920 x 1200), a found hole on a part turned 30°: its box along the
        part's axes, tight round its outline, and its outline are drawn SOLID all the way round, in the pass colour
        (the OK verdict's) for a passing hole and the fail colour (the NOK verdict's) for a failing one, thinner
        than the object's box; nothing else is drawn round the marks (no halo, no second colour); the label mask
        carries none of it.
    """

    passed, failed = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0]), Theme.Hex_To_Bgr(Theme.Verdict_Color('NOK')[0])
    features = [__Hole('1.1', 250, 300, 40, 30.0), __Hole('1.2', 500, 300, 40, 30.0, Passed=False)]
    annotated = __Render(features)
    for cx, bgr in ((250, passed), (500, failed)):
        assert all(__Along(__Near(annotated, bgr), __Circle(cx, 300, 40)))
        assert all(__Along(__Near(annotated, bgr), __Square(cx, 300, 40, 30.0)))       # tight: no margin
        wide = __Along(__Near(annotated, bgr), __Square(cx, 300, 45, 30.0))      # the recorded box: only its chip
        assert sum(wide) < 0.2 * len(wide)
    # No halo: unnumbered (its chip's white numeral aside), every pixel the passing hole changes is its colour,
    # blended into the grey at the line's edges.
    bare = __Render([__Hole('', 250, 300, 40, 30.0)])[220:380, 170:330]
    changed = (bare != 90).any(axis=2)
    assert changed.any() and not (changed & ~__Near(bare, passed, 140)).any()
    assert not __Near(annotated[240:360, 190:310], failed).any()
    weight = __Near(annotated[333:345, 249:252], passed, 10).any(axis=1).sum()    # the outline at its bottom (y 340)
    box = __Near(annotated[93:108, 399:402], failed, 10).any(axis=1).sum()       # the object's box's top (y 100)
    assert 0 < weight < box
    mask = Annotate.Draw_Label_Mask([__Judged(features)], (1200, 1920, 3), cv2, np, verdict_colored=True)
    assert np.array_equal(mask, Annotate.Draw_Label_Mask([__Judged([])], (1200, 1920, 3), cv2, np, verdict_colored=True))


def test_a_missing_hole_is_a_dashed_box_and_circle_where_a_found_one_is_solid() -> None:
    """
    Description:
        A hole expected and not found is drawn at its position in the fail colour, its box and its outline (the
        catalogue's circle) DASHED — gaps round both — the only dashed feature marks, so it never reads as a found
        hole out of tolerance, whose same box and circle are solid all the way round.
    """

    failed = Theme.Hex_To_Bgr(Theme.Verdict_Color('NOK')[0])
    missing = __Near(__Render([__Hole('1.1', 400, 400, 40, 20.0, Passed=False, Found=False)]), failed)
    found = __Near(__Render([__Hole('1.1', 400, 400, 40, 20.0, Passed=False)]), failed)
    for path in (__Circle(400, 400, 40), __Square(400, 400, 40, 20.0)):
        assert any(__Along(missing, path)) and __Gaps(__Along(missing, path)) >= 8
        assert all(__Along(found, path))


def test_a_stains_box_along_the_part_is_solid_and_its_pixels_tinted() -> None:
    """
    Description:
        A stain is drawn as its box along the part's axes (turned 30° with the part), solid in the fail colour all
        the way round, and its pixels tinted with the fail colour.
    """

    from Parameters.Vision import Feature_Str
    failed = Theme.Hex_To_Bgr(Theme.Verdict_Color('NOK')[0])
    box = __Square(400, 400, 60, 30.0)
    annotated = __Render([Feature_Str(Part='1.1', Kind='stain', Name='stain', Passed=False, Corners=box,
                                      Outlines=[[(380, 380), (420, 380), (420, 420), (380, 420)]])])
    assert all(__Along(__Near(annotated, failed), box))
    tinted = annotated[400, 400].astype(int)
    expected = Annotate.CONST_ANNOTATE_STAIN_TINT * np.array(failed) + (1.0 - Annotate.CONST_ANNOTATE_STAIN_TINT) * 90
    assert np.abs(tinted - expected).max() <= 1                                   # the fail colour over the grey


@pytest.mark.parametrize('degrees', [0.0, 30.0, 135.0, 200.0])
def test_a_chip_sits_outside_its_box_on_the_corner_nearest_the_objects_chip_and_reads_near_level(degrees: float) -> None:
    """
    Description:
        A feature's chip belongs to its box at any turn of the part: it touches the corner of the box nearest the
        object's chip (the object box's top-left, (100, 100)), lies outside the box, and runs along an edge within
        45° of level (its longer side), so its number is never upside down or sideways.
    """

    box = __Square(400, 400, 45, degrees)                                         # the tight box round r 45
    chips = __Chips(__Render([__Hole('1.1', 400, 400, 45, degrees)]), __Render([__Hole('', 400, 400, 45, degrees)]))
    assert len(chips) == 1
    (pixels,) = chips
    corner = min(np.float64(box), key=lambda c: np.hypot(c[0] - 100, c[1] - 100))
    assert np.min(np.hypot(*(pixels - corner).T)) <= 3.0                         # it touches that corner
    inside = cv2.pointPolygonTest(np.float32(box), tuple(float(c) for c in pixels.mean(axis=0)), False)
    assert inside < 0                                                             # outside the box
    (_, _), (w, h), angle = cv2.minAreaRect(np.float32(pixels))
    long_side = angle if w >= h else angle + 90.0                                 # the chip's length, from level
    assert min(abs(long_side % 180.0), 180.0 - long_side % 180.0) <= 45.5


def test_a_near_tie_takes_the_higher_corner_and_the_edge_running_right() -> None:
    """
    Description:
        A box turned 45°, its top and left corners equally near the object's chip: the chip takes the higher (top)
        corner, and of its two edges, equally level, the one running right from it — the chip lies right of the top
        corner and above that edge, so it does not jump or swap between frames.
    """

    box = np.float64(__Square(400, 400, 45, 45.0))
    top = box[np.argmin(box[:, 1])]
    left = box[np.argmin(box[:, 0])]
    assert abs(np.hypot(*(top - 100)) - np.hypot(*(left - 100))) < 1e-6
    (pixels,) = __Chips(__Render([__Hole('1.1', 400, 400, 45, 45.0)]), __Render([__Hole('', 400, 400, 45, 45.0)]))
    centre = pixels.mean(axis=0)
    assert np.min(np.hypot(*(pixels - top).T)) <= 3.0
    assert centre[0] > top[0] and centre[1] < top[1] + 45.0
    assert np.min(np.hypot(*(pixels - left).T)) > 10.0


def test_a_concentric_pair_at_the_tolerance_limits_has_its_chips_apart_each_on_its_own_box() -> None:
    """
    Description:
        The mounting plate's front at its tolerance limits (a 10.5 mm countersink round a 7.5 mm through-hole, at
        9.9 px/mm): the through-hole's chip, which would lie on the countersink's, slides along its own box's top
        edge until the two are apart, so each chip still sits on its own box; a feature without a number has no chip,
        and the chip shows the Part given.
    """

    countersink, through = (__Hole(part, 400, 400, r) for part, r in (('1.1', 52), ('1.3', 37)))
    unnumbered = __Render([__Hole('', 400, 400, 52), __Hole('', 400, 400, 37)])
    annotated = __Render([countersink, through])
    chips = sorted(__Chips(annotated, unnumbered), key=lambda p: p[:, 1].max())
    assert len(chips) == 2
    outer, inner = chips
    gap_x = max(inner[:, 0].min() - outer[:, 0].max(), outer[:, 0].min() - inner[:, 0].max())
    gap_y = max(inner[:, 1].min() - outer[:, 1].max(), outer[:, 1].min() - inner[:, 1].max())
    assert max(gap_x, gap_y) >= 2.0                                               # apart, by the gap
    # Each on its own top edge (y 348 and 363): its last rows are on its box's line, of its own colour, so unchanged.
    assert 0 <= 348 - outer[:, 1].max() <= 3 and 0 <= 363 - inner[:, 1].max() <= 3
    assert 363 <= inner[:, 0].min() and inner[:, 0].max() <= 437 + 1             # within the inner box's edge
    assert len(__Chips(__Render([countersink, __Hole('', 400, 400, 37)]), unnumbered)) == 1
    assert not np.array_equal(__Render([countersink, __Hole('1.9', 400, 400, 37)]), annotated)


def test_each_chip_is_its_box_colour_with_a_white_numeral() -> None:
    """
    Description:
        On the annotated frame each object's chip is filled with its box colour, as on the poster, and carries a plain
        white numeral in every state and both modes: no other colour is drawn in it (no rim, and not the purple numeral
        Warning once had). Read in the rendered pixels of the chip, which sits above each box's top-left corner: every
        pixel is the box colour, white, or a blend on the line between them.
    """

    boxes = {'OK': '#640ABA', 'NOK': '#FF6540', 'Warning': '#FFC226', 'Unspecified': '#655E6D'}
    objects = [__Object(150, 40 + 140 * i, size=80, verdict=verdict) for i, verdict in enumerate(boxes)]
    for verdict_colored in (True, False):
        annotated = Annotate.Draw_Annotated(np.full((CONST_H, CONST_W, 3), (70, 150, 70), np.uint8), objects, cv2, np,
                                            verdict_colored=verdict_colored)
        for det in objects:
            x, y, _, _ = det.Bbox
            box = Theme.Hex_To_Bgr(boxes[det.Verdict] if verdict_colored else Theme.Detection_Color()[0])
            chip_w, chip_h = __Chip_Extent(annotated, x, y, box)
            chip = annotated[y - chip_h:y, x:x + chip_w].reshape(-1, 3).astype(float)
            assert __Has_Bgr(annotated[y - chip_h:y, x:x + chip_w], box), det.Verdict
            assert __Has_Bgr(annotated[y - chip_h:y, x:x + chip_w], (255, 255, 255)), det.Verdict
            # Each pixel on the segment from the box colour to white: no third colour.
            direction = np.array([255.0, 255.0, 255.0]) - np.array(box, float)
            t = np.clip(((chip - box) @ direction) / (direction @ direction), 0.0, 1.0)
            off = np.abs(chip - (np.array(box, float) + t[:, None] * direction)).max(axis=1)
            assert off.max() <= 2.0, (det.Verdict, verdict_colored, off.max())


def __Chip_Extent(image: np.ndarray, x: int, y: int, box: tp.Tuple[int, int, int]) -> tp.Tuple[int, int]:
    """
    Description:
        The width and height of an object's chip, the run of its box colour along the chip's top row and up its left
        column from the box's top-left corner.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The annotated frame.
        (2) x, y [int]: The box's top-left corner.
        (3) box [Vector<int> 1x3]: The chip colour (BGR).

    Returns:
        (1) parameter [Tuple<int> 1x2]: (width, height) in px.
    """

    colour = np.array(box, np.uint8)
    height = 0
    while y - height - 1 >= 0 and (image[y - height - 1, x] == colour).all():
        height += 1
    width = 0
    while x + width < image.shape[1] and (image[y - height, x + width] == colour).all():
        width += 1
    return width, height


def test_a_part_outside_the_inspection_area_is_marked_only_in_the_warning_colour() -> None:
    """
    Description:
        A part identified outside the inspection area is a Warning, and nothing on it is judged: on the rendered frame
        its found holes (a passing and a failing one), its missing hole and its stain, their chips and the stain's tint
        are all in the Warning colour, never the pass or fail colour; the mark styles stay (the missing hole still
        dashed, the found ones solid).
    """

    from Parameters.Vision import Feature_Str
    warning = Theme.Hex_To_Bgr(Theme.Verdict_Color('Warning')[0])
    passed, failed = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0]), Theme.Hex_To_Bgr(Theme.Verdict_Color('NOK')[0])
    stain = __Square(400, 550, 50, 0.0)
    det = __Judged([__Hole('1.1', 250, 300, 40), __Hole('1.2', 500, 300, 40, Passed=False),
                    __Hole('1.3', 250, 450, 40, Passed=False, Found=False),
                    Feature_Str(Part='1.4', Kind='stain', Name='stain', Passed=False, Corners=stain,
                                Outlines=[[(380, 530), (420, 530), (420, 570), (380, 570)]])])
    det.Verdict = 'Warning'
    annotated = Annotate.Draw_Annotated(np.full((1200, 1920, 3), 90, np.uint8), [det], cv2, np, verdict_colored=True)
    hits = __Near(annotated, warning)
    assert all(__Along(hits, __Circle(250, 300, 40))) and all(__Along(hits, __Circle(500, 300, 40)))
    assert __Gaps(__Along(hits, __Circle(250, 450, 40))) >= 8 and all(__Along(hits, stain))
    assert not __Near(annotated, passed, 30).any() and not __Near(annotated, failed, 30).any()
    expected = Annotate.CONST_ANNOTATE_STAIN_TINT * np.array(warning) + (1.0 - Annotate.CONST_ANNOTATE_STAIN_TINT) * 90
    assert np.abs(annotated[550, 400].astype(int) - expected).max() <= 1
