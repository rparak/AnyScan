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
# File Name: ../test/Vision/Utilities/test_classify.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the catalogue verdict rule and the structures it reads
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import (Classify, Object_Crop, Reference_Crop, Rotations, Best_Match, Object_Area_Mm2,
                                       Center_Distance_Mm, CONST_VERIFIED_RADIUS_MM, CONST_SIDE_MARGIN,
                                       Side_Similarities, Decide_Side, Settle_Side, Settle_Area, Inspection_Area_Px,
                                       Inside_Area, Resembles_Part, CONST_OUTSIDE_SIMILARITY,
                                       CONST_PART_MAX_SATURATION, Mean_Saturation, Visible_Extent_Mm, Wall_Widths)
#   ../Vision/Utilities/Measure
from Vision.Utilities.Measure import Measure_Mask
#   ../Vision/Utilities/Dimensions
from Vision.Utilities.Dimensions import Check_Outline
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Scale_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Item_Str, Catalogue_Outline_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Identification_Parameters_Str

"""
Description:
    The catalogue mode's verdict rule, one branch per test — a Warning, several parts, by area, identified by
    similarity (OK, or NOK on a dimension), identified by outline below the similarity (NOK, with no
    lower bound), Warning — and the geometry it rests on: the crop turned upright, the reference cut out
    by its box, the best match and its side, the area and the distance from the frame centre. Synthetic
    masks at a round 0.1 mm/px, drawn analytically, so every size is exact.
"""

# A round-number scale (0.1 mm/px), the frame (w, h), the mounting plate's outline and the shipped thresholds.
CONST_SCALE = Scale_Str(Mm_Per_Px_X=0.1, Mm_Per_Px_Y=0.1)
CONST_FRAME = (1920, 1200)
CONST_ITEM = Catalogue_Item_Str(Name='mounting_plate', Thickness_Mm=8.0, Tolerance_Mm=1.5,
                                Outline=Catalogue_Outline_Str(Length_Mm=60.0, Width_Mm=40.0, Tolerance_Mm=1.5))
CONST_THRESHOLDS = Identification_Parameters_Str(Model_Path='/x', Identify_Similarity=0.75, Unspecified_Area_Ratio=1.7)


def _Part(rects: tp.List[tp.Tuple[int, int, int, int]]) -> Detection_Str:
    """One object made of filled rectangles (x0, y0, x1, y1, exclusive), measured and outline-checked."""
    mask = np.zeros((CONST_FRAME[1], CONST_FRAME[0]), dtype=bool)
    for x0, y0, x1, y1 in rects:
        mask[y0:y1, x0:x1] = True
    ys, xs = np.nonzero(mask)
    det = Detection_Str(Label='part', Bbox=(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1),
                                            int(ys.max() - ys.min() + 1)), Mask=mask)
    det.Measurement = Measure_Mask(mask, CONST_SCALE, cv2, np)
    det.Dimension_Checks = Check_Outline(det.Measurement, CONST_ITEM.Outline)
    return det


@pytest.mark.parametrize('rects, similarity, verdict, kind', [
    ([(660, 400, 1260, 800)], 0.95, 'OK', ''),                      # 60 x 40 mm, looks like it
    ([(660, 400, 1260, 800)], 0.75, 'OK', ''),                      # ...at the threshold itself
    ([(660, 400, 1300, 800)], 0.95, 'NOK', ''),                     # 64 x 40 mm: identified, too long
    ([(660, 400, 1260, 800)], 0.74, 'NOK', ''),                     # its outline, not its look
    ([(660, 400, 1260, 800)], 0.0, 'NOK', ''),                      # ...with no lower bound on the look
    ([(660, 400, 1060, 500)], 0.40, 'Warning', 'foreign'),          # 40 x 10 mm, does not look like it
    ([(660, 400, 1300, 800)], 0.74, 'Warning', 'foreign'),          # neither its look nor its outline
    ([(200, 200, 800, 600), (800, 200, 1400, 600)], 0.95, 'Warning', 'several_parts'),   # two plates side by side, 2.0x
    ([(200, 200, 800, 600), (800, 200, 1400, 600)], 0.10, 'Warning', 'several_parts'),   # area decides first
], ids=['ok', 'ok-at-threshold', 'nok-size', 'nok-look', 'nok-no-floor', 'warning', 'warning-wrong-size',
        'several-parts', 'several-parts-first'])
def test_the_verdict_follows_the_rule(rects: tp.List[tp.Tuple[int, int, int, int]], similarity: float,
                                      verdict: str, kind: str) -> None:
    """
    Description:
        Each branch, in order: an area of 1.7 x the part's or more is a Warning, several parts, whatever it looks
        like; a similarity of 0.75 or more is the part, OK when its outline is within tolerance and NOK when not;
        below 0.75 an object with the part's outline is still the part, and NOK — at any similarity, even
        0, the owner's ruling (a same-sized foreign object reads NOK, the safer error); anything else is a
        Warning, a foreign object.
    """

    det = _Part(rects)
    Classify(det, similarity, 'front', CONST_ITEM, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    assert (det.Verdict, det.Catalogue.Warning_Kind) == (verdict, kind)
    assert (det.Catalogue.Similarity, det.Catalogue.Side) == (similarity, 'front')


@pytest.mark.parametrize('rects, verdict', [
    ([(660, 400, 1260, 800)], 'OK'),                                # 60 x 40 mm
    ([(660, 400, 1300, 800)], 'NOK'),                               # 64 x 40 mm, too long
], ids=['ok', 'nok-size'])
def test_the_verdict_does_not_depend_on_where_the_part_lies(rects: tp.List[tp.Tuple[int, int, int, int]],
                                                            verdict: str) -> None:
    """
    Description:
        A part's size is checked, and its verdict given, the same at the frame centre and beyond the radius the size
        checks were verified to (CONST_VERIFIED_RADIUS_MM): the distance is evidence for the log, never a branch of
        the rule.
    """

    shift = (-560, -330)                                            # 64 to 69 mm out at 0.1 mm/px
    centred = _Part(rects)
    outside = _Part([(x0 + shift[0], y0 + shift[1], x1 + shift[0], y1 + shift[1]) for x0, y0, x1, y1 in rects])
    for det in (centred, outside):
        Classify(det, 0.9, 'front', CONST_ITEM, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    assert centred.Catalogue.Center_Distance_Mm < CONST_VERIFIED_RADIUS_MM < outside.Catalogue.Center_Distance_Mm
    assert centred.Verdict == outside.Verdict == verdict


def test_the_evidence_is_kept_with_the_thresholds_it_was_judged_by() -> None:
    """
    Description:
        The verdict's evidence carries what explains it: the area as a multiple of the part's, the centre's
        distance from the frame centre, and the thresholds and verified radius in force — so the report can
        say why without being handed the configuration.
    """

    det = _Part([(660, 400, 1260, 800)])                           # 60 x 40 mm, centred at (960, 600)
    Classify(det, 0.9, 'back', CONST_ITEM, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    result = det.Catalogue
    assert result.Area_Ratio == pytest.approx(1.0)
    assert result.Center_Distance_Mm == pytest.approx(np.hypot(0.05, 0.05))     # pixel centres: 959.5, 599.5
    assert (result.Identify_Similarity, result.Unspecified_Area_Ratio, result.Verified_Radius_Mm) == \
        (0.75, 1.7, CONST_VERIFIED_RADIUS_MM)


def test_area_and_distance_are_in_mm_at_the_scale() -> None:
    """
    Description:
        The area is the mask's pixels times both factors; the distance runs from the frame centre to the
        centre of the measured rectangle, each axis through its own factor.
    """

    det = _Part([(1760, 1000, 1860, 1100)])                        # 10 x 10 mm; pixel centres 1760..1859 -> 1809.5
    assert Object_Area_Mm2(det, CONST_SCALE) == pytest.approx(100.0)
    assert Center_Distance_Mm(det, CONST_FRAME, Scale_Str(Mm_Per_Px_X=0.1, Mm_Per_Px_Y=0.2)) == \
        pytest.approx(np.hypot(84.95, 89.9))


def test_the_crop_is_turned_upright_whatever_the_part_lies() -> None:
    """
    Description:
        The identifier compares crops the way the references show the parts: long side vertical. A plate
        lying flat (wide) and one rotated by 30° both come out as a 40 x 60 mm upright crop of the part
        alone, so a match does not depend on how the part lies.
    """

    frame = np.zeros((CONST_FRAME[1], CONST_FRAME[0], 3), dtype=np.uint8)
    flat = _Part([(660, 400, 1260, 800)])
    frame[flat.Mask] = 200
    crop = Object_Crop(frame, flat, cv2, np)
    assert crop.shape[:2] == (600, 400) and crop.mean() > 195

    rotated_frame = np.zeros_like(frame)
    corners = cv2.boxPoints(((960.0, 600.0), (600.0, 400.0), 30.0)).astype(np.int32)
    cv2.fillConvexPoly(rotated_frame, corners, (200, 200, 200))
    rotated = Detection_Str(Label='part', Bbox=tuple(int(v) for v in cv2.boundingRect(corners)),
                            Mask=rotated_frame[:, :, 0] > 0)
    rotated.Measurement = Measure_Mask(rotated.Mask, CONST_SCALE, cv2, np)
    crop = Object_Crop(rotated_frame, rotated, cv2, np)
    assert crop.shape[0] > crop.shape[1] and abs(crop.shape[0] - 600) <= 3 and abs(crop.shape[1] - 400) <= 3
    assert crop[5:-5, 5:-5].mean() > 195


def test_a_round_object_is_cropped_by_its_box() -> None:
    """
    Description:
        A round object has no rectangle worth turning (its orientation is noise): it is cut out by its box.
    """

    frame = np.zeros((CONST_FRAME[1], CONST_FRAME[0], 3), dtype=np.uint8)
    disc = np.zeros(frame.shape[:2], dtype=np.uint8)
    cv2.circle(disc, (500, 500), 80, 1, -1)
    det = Detection_Str(Label='washer', Bbox=(420, 420, 161, 161), Mask=disc.astype(bool))
    det.Measurement = Measure_Mask(det.Mask, CONST_SCALE, cv2, np)
    assert det.Measurement.Symmetric
    assert Object_Crop(frame, det, cv2, np).shape[:2] == (161, 161)


def test_the_reference_is_cut_out_by_its_yolo_box() -> None:
    """
    Description:
        A YOLO box is centre x, centre y, width and height as fractions of the image: (0.5, 0.5, 0.25, 0.5)
        on 1920 x 1200 is the 480 x 600 px block around the centre.
    """

    image = np.zeros((1200, 1920, 3), dtype=np.uint8)
    assert Reference_Crop(image, (0.5, 0.5, 0.25, 0.5)).shape[:2] == (600, 480)


def test_the_best_match_is_the_highest_over_turns_and_sides() -> None:
    """
    Description:
        An object's similarity is its highest cosine over its four turns and both references, and its side
        is that reference's — here the back, matched by the third turn.
    """

    references = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    turns = np.array([[0.0, 0.0, 1.0], [0.6, 0.0, 0.8], [0.0, 0.9, 0.43588989], [0.0, 0.0, 1.0]])
    assert Best_Match(turns, references, ['front', 'back']) == (pytest.approx(0.9), 'back')
    assert len(Rotations(np.zeros((6, 4, 3), dtype=np.uint8), cv2)) == 4


def test_the_side_is_named_in_the_catalogues_words() -> None:
    """
    Description:
        The evidence keeps the side DINOv2 matched and the catalogue's name for it, which the side sentence
        uses: 'back' is the mounting plate's 'unmachined back'.
    """

    from Configuration.Core import Load_Catalogue
    item = Load_Catalogue('Data/Catalogue/mounting_plate/mounting_plate.yaml')
    det = _Part([(660, 400, 1260, 800)])
    Classify(det, 0.9, 'back', item, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    assert (det.Catalogue.Side, det.Catalogue.Side_Name) == ('back', 'unmachined back')


def test_a_point_on_the_upright_crop_goes_back_to_where_it_is_on_the_frame() -> None:
    """
    Description:
        The frame marks a part's features at their places on the frame: a mark on the upright crop of a part
        lying at 30° goes back, through the inverse of the crop's warp, onto the same pixel of the frame; a part
        cropped by its box (round) by the box's offset.
    """

    from Vision.Utilities.Classify import Crop_To_Frame
    frame = np.zeros((CONST_FRAME[1], CONST_FRAME[0], 3), dtype=np.uint8)
    corners = cv2.boxPoints(((960.0, 600.0), (600.0, 400.0), 30.0)).astype(np.int32)
    cv2.fillConvexPoly(frame, corners, (200, 200, 200))
    cv2.circle(frame, (1000, 640), 6, (0, 0, 255), -1)
    det = Detection_Str(Label='part', Bbox=tuple(int(v) for v in cv2.boundingRect(corners)), Mask=frame[:, :, 1] > 0)
    det.Measurement = Measure_Mask(det.Mask, CONST_SCALE, cv2, np)
    crop = Object_Crop(frame, det, cv2, np)
    ys, xs = np.nonzero((crop[:, :, 2] > 128) & (crop[:, :, 1] < 64))
    (x, y), = Crop_To_Frame(det, [(float(xs.mean()), float(ys.mean()))], cv2, np)
    assert abs(x - 1000) < 1.5 and abs(y - 640) < 1.5
    round_part = Detection_Str(Label='washer', Bbox=(100, 200, 50, 50))
    assert Crop_To_Frame(round_part, [(10.0, 20.0)], cv2, np) == [(110.0, 220.0)]


def test_the_similarity_grid_is_the_best_turn_turned_back_upright() -> None:
    """
    Description:
        The overlay's grid: the rotation that matched the judged side best (Best_Turn), each patch's unlikeness
        (1 - its highest cosine to the reference's patches), turned back to the upright crop; a patch alike to
        the reference is 0, one orthogonal to all of it 1.
    """

    from Vision.Utilities.Classify import Best_Turn, Similarity_Grid
    rows = np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8], [0.0, -1.0]])
    references = np.array([[0.0, 1.0], [1.0, 0.0]])
    assert Best_Turn(rows, references, ['front', 'back'], 'front') == 1
    assert Best_Turn(rows, references, ['front', 'back'], 'back') == 0
    reference = np.array([[1.0, 0.0]] * 4)
    patches = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [1.0, 0.0]])       # the top-right patch unlike it
    assert np.allclose(Similarity_Grid(patches, reference, 0, np), [[0.0, 1.0], [0.0, 0.0]])
    # Turned once clockwise for the match, so turned back counter-clockwise: top-right moves to top-left.
    assert np.allclose(Similarity_Grid(patches, reference, 1, np), [[1.0, 0.0], [0.0, 0.0]])


@pytest.mark.parametrize('similarities, evidence, decided', [
    ({'front': 0.95, 'back': 0.50}, [], ('front', 'similarity')),            # DINOv2 tells by its margin
    ({'front': 0.50, 'back': 0.99}, [], ('back', 'similarity')),             # a back, 0.49 ahead
    ({'front': 0.95, 'back': 0.50}, ['front'], ('front', 'similarity')),     # ...and the holes agree
    ({'front': 0.716, 'back': 0.753}, ['front'], ('front', 'holes')),        # 20261015-170816_17: the back by 0.037
    ({'front': 0.75, 'back': 0.73}, ['front'], ('front', 'holes')),          # a margin that does not tell
    ({'front': 0.40, 'back': 0.95}, ['front'], ('back', 'conflict')),        # the holes against a decisive look
    ({'front': 0.55, 'back': 0.35}, [], ('front', 'undecided')),             # neither tells
    ({'front': 0.72, 'back': 0.75}, ['front', 'back'], ('back', 'undecided')),  # holes of both sides tell nothing
], ids=['look', 'look-back', 'both', 'holes-over-look', 'holes-close', 'conflict', 'undecided', 'both-sides-holes'])
def test_the_side_is_dinov2s_by_its_margin_else_the_holes(similarities: tp.Dict[str, float], evidence: tp.List[str],
                                                           decided: tp.Tuple[str, str]) -> None:
    """
    Description:
        DINOv2's best side when its margin over the other is at least CONST_SIDE_MARGIN; below it, a hole only one
        side has decides; against a decisive margin the two conflict; with neither the side is undecided (DINOv2's
        best kept for the report). On eight stained fronts 57-67 mm out DINOv2 chose the back by 0.030-0.075.
    """

    assert CONST_SIDE_MARGIN == pytest.approx(0.265)
    assert Decide_Side(similarities, evidence) == decided


@pytest.mark.parametrize('verdict, kind, verdicts, how, settled, settled_kind', [
    ('OK', '', {}, 'similarity', 'OK', ''),
    ('OK', '', {}, 'holes', 'OK', ''),
    ('NOK', '', {}, 'conflict', 'Warning', 'side_mismatch'),
    ('OK', '', {'front': 'NOK', 'back': 'OK'}, 'undecided', 'Warning', 'side_unknown'),   # a front passed for a clean back
    ('NOK', '', {'front': 'NOK', 'back': 'NOK'}, 'undecided', 'NOK', ''),                 # the hole-less block, NOK either way
    ('Warning', 'several_parts', {'front': 'NOK', 'back': 'OK'}, 'undecided', 'Warning', 'several_parts'),
], ids=['decided', 'by-holes', 'conflict', 'differs', 'agrees', 'already-a-warning'])
def test_a_part_whose_side_cannot_be_told_keeps_only_a_verdict_every_side_gives(
        verdict: str, kind: str, verdicts: tp.Dict[str, str], how: str, settled: str, settled_kind: str) -> None:
    """
    Description:
        A decided side's verdict stands; a conflict is a Warning, a side mismatch; an undecided part keeps a verdict
        every side gives — the hole-less block of the part's outline is NOK on either — and one that differs by side
        is a Warning, its side unclear, never a confident OK on the wrong side. A Warning keeps its kind.
    """

    det = _Part([(660, 400, 1260, 800)])
    Classify(det, 0.9, 'front', CONST_ITEM, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    det.Verdict, det.Catalogue.Warning_Kind = verdict, kind
    Settle_Side(det, verdicts, how)
    assert (det.Verdict, det.Catalogue.Warning_Kind, det.Catalogue.Side_Evidence) == (settled, settled_kind, how)


def test_the_inspection_area_is_the_frame_inset_by_the_stations_insets() -> None:
    """
    Description:
        The area is the frame inset by the long-edge inset from the top and bottom and by the short-edge inset from
        the left and right, converted at the scale per axis: at 0.1 mm/px, 10 and 13 mm are 100 and 130 px, so the
        1920 x 1200 frame's area spans columns 130-1789 and rows 100-1099.
    """

    assert Inspection_Area_Px(CONST_FRAME, CONST_SCALE, 10.0, 13.0) == pytest.approx((130.0, 100.0, 1789.0, 1099.0))
    assert Inspection_Area_Px(CONST_FRAME, Scale_Str(Mm_Per_Px_X=0.1, Mm_Per_Px_Y=0.2), 10.0, 13.0) == \
        pytest.approx((130.0, 50.0, 1789.0, 1149.0))


@pytest.mark.parametrize('rects, similarity, before, after, kind, outside', [
    ([(660, 400, 1260, 800)], 0.95, 'OK', 'OK', '', False),                      # in the middle
    ([(130, 100, 730, 500)], 0.95, 'OK', 'OK', '', False),                       # on the area's top-left corner
    ([(1190, 700, 1790, 1100)], 0.95, 'OK', 'OK', '', False),                    # on its bottom-right corner
    ([(129, 400, 729, 800)], 0.95, 'OK', 'Warning', 'outside', True),            # one column over the left edge
    ([(660, 99, 1260, 499)], 0.95, 'OK', 'Warning', 'outside', True),            # one row over the top edge
    ([(0, 400, 600, 800)], 0.95, 'OK', 'Warning', 'outside', True),              # cut by the frame's border
    ([(1320, 750, 1920, 1150)], 0.95, 'OK', 'Warning', 'outside', True),         # by the corner, 74.7 mm out
    ([(1200, 400, 1840, 800)], 0.95, 'NOK', 'Warning', 'outside', True),         # a NOK is not given there either
    ([(1500, 400, 1900, 500)], 0.30, 'Warning', 'Warning', 'foreign', True),     # a foreign object outside
    ([(1300, 200, 1900, 600), (1300, 600, 1900, 1000)], 0.95, 'Warning', 'Warning', 'outside', True),  # two plates outside
], ids=['middle', 'top-left-corner', 'bottom-right-corner', 'left-edge', 'top-edge', 'border-cut', 'corner',
        'nok-outside', 'foreign-outside', 'merged-outside'])
def test_only_an_object_wholly_inside_the_inspection_area_is_judged(
        rects: tp.List[tp.Tuple[int, int, int, int]], similarity: float, before: str, after: str, kind: str,
        outside: bool) -> None:
    """
    Description:
        An object whose mask lies wholly inside the area keeps its verdict, to the area's last pixel; one with a single
        column or row of its mask outside it, cut by the frame's border, or in a corner of the view, is a Warning
        whatever it was (OK, NOK, a foreign object's Warning, two plates' Warning, several parts) and says it lies
        outside: of kind 'outside' when it resembles the part (Resembles_Part, run first as in the pipeline, on a
        plate's colour and extent), else 'foreign'.
    """

    det = _Part(rects)
    Classify(det, similarity, 'front', CONST_ITEM, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    assert det.Verdict == before
    inside = Inside_Area(det, Inspection_Area_Px(CONST_FRAME, CONST_SCALE, 10.0, 13.0), np)
    det.Catalogue.Outside_Area = not inside
    Resembles_Part(det, 30.0, 70.0, CONST_ITEM)
    Settle_Area(det, inside)
    assert (det.Verdict, det.Catalogue.Warning_Kind, det.Catalogue.Outside_Area) == (after, kind, outside)


@pytest.mark.parametrize('verdict, outside, similarity, saturation, extent, resembles', [
    ('OK', False, 0.95, 30.0, 70.0, True),          # identified by the rule
    ('NOK', True, 0.10, 200.0, 99.0, True),         # identified (by its outline) outside: the cues are not asked
    ('Warning-several_parts', False, 0.95, 30.0, 140.0, True),  # several parts
    ('Warning', False, 0.70, 30.0, 70.0, False),    # inside the area the rule alone identifies
    ('Warning', True, 0.668, 39.6, 66.7, True),     # the most cut plate measured (20261016-070632_8)
    ('Warning', True, 0.645, 129.3, 44.5, False),   # the red block cut by the border (20261016-111333_4)
    ('Warning', True, 0.673, 112.3, 44.1, False),   # the red block at its most plate-like look: its colour
    ('Warning', True, 0.433, 33.0, 67.8, False),    # a square plate: its look
    ('Warning', True, 0.70, 30.0, 94.7, False),     # larger than the plate's diagonal
], ids=['ok', 'identified-outside', 'several', 'inside-warning', 'cut-plate', 'red-block-cut', 'red-block-colour',
        'square-plate', 'too-large'])
def test_an_object_resembles_the_part_by_the_rule_or_outside_by_every_position_free_cue(
        verdict: str, outside: bool, similarity: float, saturation: float, extent: float, resembles: bool) -> None:
    """
    Description:
        An object the verdict rule identified resembles the part wherever it lies; one it did not resembles it only
        outside the inspection area, and only when its similarity reaches 0.657, its mean saturation stays at 76.3 or
        below and its visible extent within the plate's diagonal plus tolerance (73.6 mm): the most cut plate
        measured does, the red block does not by its colour even at its highest similarity (0.673), a square plate does
        not by its look, and an object larger than the plate does not by its extent.
    """

    assert (CONST_OUTSIDE_SIMILARITY, CONST_PART_MAX_SATURATION) == (pytest.approx(0.657), pytest.approx(76.3))
    det = _Part([(660, 400, 1260, 800)])
    Classify(det, similarity, 'front', CONST_ITEM, CONST_THRESHOLDS, CONST_SCALE, CONST_FRAME)
    det.Verdict, det.Catalogue.Outside_Area = verdict.split('-')[0], outside
    det.Catalogue.Warning_Kind = verdict.split('-')[1] if '-' in verdict else ''
    Resembles_Part(det, saturation, extent, CONST_ITEM)
    assert (det.Catalogue.Resembles, det.Catalogue.Saturation, det.Catalogue.Extent_Mm) == (resembles, saturation, extent)


def test_the_colour_and_extent_cues_read_the_mask() -> None:
    """
    Description:
        The colour cue is the mean HSV saturation over the mask eroded off its rim (a grey plate on a saturated table
        reads the plate's, not the table's), and the extent the largest distance across the visible mask (a 60 x 40 mm
        rectangle at 0.1 mm/px: its diagonal, 72.1 mm).
    """

    det = _Part([(660, 400, 1260, 800)])
    frame = np.zeros((CONST_FRAME[1], CONST_FRAME[0], 3), np.uint8)
    frame[:] = (40, 200, 40)                                  # a saturated green table
    frame[400:800, 660:1260] = (128, 128, 128)               # a grey plate
    assert Mean_Saturation(frame, det, cv2, np) == pytest.approx(0.0)
    frame[400:800, 660:1260] = (40, 40, 200)                 # a red one
    assert Mean_Saturation(frame, det, cv2, np) > 150.0
    assert Visible_Extent_Mm(det, CONST_SCALE, cv2, np) == pytest.approx(72.1, abs=0.2)


def test_an_object_without_a_mask_is_never_inside_the_area() -> None:
    """
    Description:
        An object with no mask, or an empty one, has no outline to place inside the area, so it is not inside.
    """

    area = Inspection_Area_Px(CONST_FRAME, CONST_SCALE, 10.0, 13.0)
    assert not Inside_Area(Detection_Str(Label='x', Bbox=(700, 500, 10, 10), Mask=None), area, np)
    assert not Inside_Area(Detection_Str(Label='x', Bbox=(700, 500, 10, 10),
                                         Mask=np.zeros((CONST_FRAME[1], CONST_FRAME[0]), dtype=bool)), area, np)


def test_side_similarities_take_each_sides_best_rotation() -> None:
    """
    Description:
        Each side's similarity is its reference's highest cosine over the object's rotations, so the margin between
        the sides compares like with like.
    """

    rows = np.array([[1.0, 0.0], [0.6, 0.8], [0.0, 1.0], [0.8, 0.6]])
    references = np.array([[1.0, 0.0], [0.0, 1.0]])
    assert Side_Similarities(rows, references, ['front', 'back']) == {'front': 1.0, 'back': 1.0}
    assert Side_Similarities(rows[1:2], references, ['front', 'back']) == {'front': 0.6, 'back': 0.8}


def test_the_side_wall_is_seen_only_on_the_edges_facing_the_optical_axis() -> None:
    """
    Description:
        Under the pinhole model a part's bottom edge projects towards the principal point by its distance from it
        times thickness / (the camera's distance to the table): a plate right of the axis shows its wall on its
        left edge alone, 340 px from the axis, 340 x 8 / (3541 x 0.1 + 8) x 0.1 = 0.751 mm; a plate over the axis
        shows none.
    """

    K = np.array([[3541.0, 0.0, 960.0], [0.0, 3541.0, 600.0], [0.0, 0.0, 1.0]])
    right = _Part([(1300, 400, 1900, 800)])
    walls = Wall_Widths(right, K, CONST_SCALE, 8.0, cv2, np)
    assert sorted(round(wall, 3) for wall in walls) == [0.0, 0.0, 0.0, pytest.approx(0.751, abs=0.002)]
    assert Wall_Widths(_Part([(660, 400, 1260, 800)]), K, CONST_SCALE, 8.0, cv2, np) == (0.0, 0.0, 0.0, 0.0)


def test_the_crop_view_puts_the_optical_axis_on_the_crop() -> None:
    """
    Description:
        The principal point taken onto a part's upright crop, in mm, and the camera's distance to its top face (the
        focal length times the top face's scale, 3541 x 0.1 = 354.1 mm): a plate centred on the axis has it at its
        crop's centre; one right of it, 64 mm away along the plate's long side, has it 64 mm off the centre along the
        crop's long side.
    """

    from Vision.Utilities.Classify import Crop_View
    K = np.array([[3541.0, 0.0, 960.0], [0.0, 3541.0, 600.0], [0.0, 0.0, 1.0]])
    centred = Crop_View(_Part([(660, 400, 1260, 800)]), K, CONST_SCALE, 8.0, cv2, np)
    assert (centred.Axis_X_Mm, centred.Axis_Y_Mm) == (pytest.approx(20.0, abs=0.1), pytest.approx(30.0, abs=0.1))
    assert (centred.Distance_Mm, centred.Thickness_Mm) == (pytest.approx(354.1), 8.0)
    right = Crop_View(_Part([(1300, 400, 1900, 800)]), K, CONST_SCALE, 8.0, cv2, np)
    assert right.Axis_X_Mm == pytest.approx(20.0, abs=0.1)
    assert abs(right.Axis_Y_Mm - 30.0) == pytest.approx(64.0, abs=0.1)
