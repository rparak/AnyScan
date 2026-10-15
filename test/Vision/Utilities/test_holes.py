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
# File Name: ../test/Vision/Utilities/test_holes.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the hole check, the rule that applies it, and the structures they read
#   ../Vision/Utilities/Holes
from Vision.Utilities.Holes import Hole_Candidates, Check_Holes, Seat_Holes, Side_Evidence, Hole_Features
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import Apply_Holes
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Hole_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Hole_Group_Str

"""
Description:
    The catalogue's hole check: round masks inside the crop become hole candidates; each group counts the
    candidates of its diameter (and, with positions, near one) and checks each one's diameter, edge distances
    and pitch; a judged part with a hole missing, extra or out of tolerance becomes NOK. Synthetic discs at
    0.1 mm/px, so every size is known; the real frames are pinned in test_pipeline (slow).
"""

# The mounting plate's front groups, as the shipped item gives them, and a synthetic group with a hole at each of
# its four mirrored positions (on a 50 x 50 mm part): the positioned group's other case, all positions filled.
CONST_PLATE_FRONT = [Catalogue_Hole_Group_Str(Name='countersink', Diameter_Mm=12.0, Count=2, Tolerance_Mm=1.5),
                     Catalogue_Hole_Group_Str(Name='through-hole', Diameter_Mm=6.0, Count=2, From_Long_Edge_Mm=15.0,
                                              From_Short_Edge_Mm=17.5, Pitch_Mm=25.0, Tolerance_Mm=1.5)]
CONST_CORNERS = [Catalogue_Hole_Group_Str(Name='corner hole', Diameter_Mm=2.459, Count=4, From_Long_Edge_Mm=4.0,
                                          From_Short_Edge_Mm=4.0, Pitch_Mm=42.0, Tolerance_Mm=1.0)]


def _Disc(shape: tp.Tuple[int, int], x_mm: float, y_mm: float, diameter_mm: float) -> np.ndarray:
    """A filled disc mask at 0.1 mm/px."""
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.circle(mask, (int(round(x_mm * 10)), int(round(y_mm * 10))), int(round(diameter_mm * 5)), 1, -1)
    return mask.astype(bool)


def _Holes(*holes: tp.Tuple[float, float, float]) -> tp.List[Hole_Str]:
    """Hole candidates as (x, y, diameter) in mm."""
    return [Hole_Str(Diameter_Mm=d, X_Mm=x, Y_Mm=y) for x, y, d in holes]


def test_round_masks_inside_the_crop_are_candidates_in_mm() -> None:
    """
    Description:
        A disc inside the crop is a candidate, its diameter and centre in mm; a square (π/4 round, below the
        threshold that sits under the real holes' 0.881), a disc
        reaching the crop's border (the part's edge), and the same disc returned twice by FastSAM are not.
    """

    shape = (600, 400)
    square = np.zeros(shape, dtype=bool)
    square[300:400, 100:200] = True
    # A whole disc 1 px from the border: round, so only the border rule keeps it out.
    masks = [_Disc(shape, 15.0, 17.5, 6.0), _Disc(shape, 15.0, 17.5, 6.0), square, _Disc(shape, 3.1, 30.0, 6.0)]
    (hole,) = Hole_Candidates(masks, 0.1, cv2, np)
    assert hole.Diameter_Mm == pytest.approx(6.0, abs=0.1)
    assert (hole.X_Mm, hole.Y_Mm) == (pytest.approx(15.0, abs=0.1), pytest.approx(17.5, abs=0.1))


def test_a_plate_with_its_holes_where_the_catalogue_puts_them_passes() -> None:
    """
    Description:
        The mounting plate's front, its holes on either long edge (the part lies either way round): two
        countersinks and two through-holes counted, every diameter, edge distance and the pitch within tolerance.
    """

    for x in (15.0, 25.0):                                  # near the left long edge, or the right one
        candidates = _Holes((x, 17.5, 6.1), (x, 42.5, 6.2), (x, 17.5, 12.2), (x, 42.5, 12.3))
        counts, checks = Check_Holes(candidates, CONST_PLATE_FRONT, 40.0, 60.0)
        assert [(c.Name, c.Found, c.Expected) for c in counts] == [('countersink', 2, 2), ('through-hole', 2, 2)]
        names = [c.Name for c in checks]
        assert names.count('through-hole pitch') == 1 and names.count("through-hole's distance from the long edge") == 2
        assert all(c.Within for c in checks)


def test_a_hole_of_the_wrong_size_is_counted_and_fails_its_diameter() -> None:
    """
    Description:
        A through-hole of 8 mm (1.5 over the tolerance, within twice it) is counted, so the report says its
        diameter is wrong, not that a hole is missing.
    """

    counts, checks = Check_Holes(_Holes((15.0, 17.5, 8.0), (15.0, 42.5, 6.0)), CONST_PLATE_FRONT[1:], 40.0, 60.0)
    assert counts[0].Found == 2
    failed = [c for c in checks if not c.Within]
    assert [(c.Name, round(c.Measured_Mm, 2)) for c in failed] == [('through-hole Ø', 8.0)]


def test_a_misplaced_hole_fails_its_edge_distance_and_pitch() -> None:
    """
    Description:
        A through-hole 1.8 mm farther from the short edge than the catalogue says (within the counting gate)
        is counted, and fails its short-edge distance and the pitch.
    """

    counts, checks = Check_Holes(_Holes((15.0, 19.3, 6.0), (15.0, 42.5, 6.0)), CONST_PLATE_FRONT[1:], 40.0, 60.0)
    assert counts[0].Found == 2
    assert sorted(c.Name for c in checks if not c.Within) == ['through-hole pitch',
                                                              "through-hole's distance from the short edge"]


def test_a_hole_at_every_corner_is_counted_and_a_round_mark_beside_one_is_not() -> None:
    """
    Description:
        A group with a hole at each of its four mirrored positions counts all four; a round mark of their size
        5 mm along an edge from a corner is outside the counting gate and is not counted; a missing hole is
        counted missing. Only neighbouring holes, 42 mm apart, are checked as pitch, not the diagonals.
    """

    four = [(4.0, 4.0, 2.8), (46.0, 4.0, 2.8), (4.0, 46.0, 2.8), (46.0, 46.0, 2.8)]
    counts, checks = Check_Holes(_Holes(*four, (9.0, 4.7, 2.9)), CONST_CORNERS, 50.0, 50.0)
    assert (counts[0].Found, counts[0].Expected) == (4, 4)
    assert len([c for c in checks if c.Name == 'corner hole pitch']) == 4 and all(c.Within for c in checks)
    counts, _checks = Check_Holes(_Holes(*four[1:]), CONST_CORNERS, 50.0, 50.0)
    assert (counts[0].Found, counts[0].Expected) == (3, 4)


def test_an_extra_hole_at_a_position_is_counted_over() -> None:
    """
    Description:
        A third through-hole at the mirrored position (the other long edge's) is counted: three found, two
        expected.
    """

    counts, _checks = Check_Holes(_Holes((15.0, 17.5, 6.0), (15.0, 42.5, 6.0), (25.0, 17.5, 6.0)),
                                  CONST_PLATE_FRONT[1:], 40.0, 60.0)
    assert (counts[0].Found, counts[0].Expected) == (3, 2)


@pytest.mark.parametrize('found, within, before, after', [
    (2, True, 'OK', 'OK'), (1, True, 'OK', 'NOK'), (3, True, 'OK', 'NOK'), (2, False, 'OK', 'NOK'), (2, True, 'NOK', 'NOK'),
], ids=['all there', 'one missing', 'one extra', 'out of tolerance', 'already nok'])
def test_a_judged_parts_holes_decide_ok_or_nok(found: int, within: bool, before: str, after: str) -> None:
    """
    Description:
        A part judged OK stays OK only with every group's count right and every hole within tolerance; a hole
        missing, extra or out of tolerance makes it NOK; a part already NOK stays NOK. The counts and checks are
        kept on the object for the report.
    """

    from Parameters.Vision import Hole_Count_Str, Dimension_Check_Str
    det = Detection_Str(Label='plate', Bbox=(0, 0, 1, 1), Verdict=before)
    counts = [Hole_Count_Str(Name='through-hole', Found=found, Expected=2)]
    checks = [Dimension_Check_Str(Name='through-hole Ø', Measured_Mm=6.1, Nominal_Mm=6.0, Tolerance_Mm=1.5, Within=within)]
    Apply_Holes(det, counts, checks)
    assert det.Verdict == after and det.Hole_Counts == counts and det.Hole_Checks == checks


def _Centres(features: tp.List[tp.Any]) -> tp.List[tp.Tuple[float, float, bool]]:
    """Each feature's box centre (mm, one decimal) and whether it was found."""
    return [(round(sum(x for x, _ in f.Corners) / 4, 1), round(sum(y for _, y in f.Corners) / 4, 1), f.Found)
            for f in features]


def test_a_missing_corner_hole_is_marked_where_the_catalogue_puts_it() -> None:
    """
    Description:
        A four-position group's holes as the frame marks them: the three found, each with its checks and its mask
        score, and the fourth expected at its corner (4 mm from both edges) and not found, failed.
    """

    from Vision.Utilities.Holes import Hole_Features
    holes = [Hole_Str(Diameter_Mm=2.9, X_Mm=4.0, Y_Mm=4.0, Score=0.95), Hole_Str(Diameter_Mm=2.9, X_Mm=46.0, Y_Mm=4.0),
             Hole_Str(Diameter_Mm=2.9, X_Mm=4.0, Y_Mm=46.0)]
    features = Hole_Features(holes, CONST_CORNERS, 50.0, 50.0)
    assert _Centres(features) == [(4.0, 4.0, True), (46.0, 4.0, True), (4.0, 46.0, True), (46.0, 46.0, False)]
    assert [f.Passed for f in features] == [True, True, True, False]
    assert features[0].Score == 0.95 and [c.Name for c in features[0].Checks][:3] == [
        'corner hole Ø', "corner hole's distance from the long edge", "corner hole's distance from the short edge"]
    assert any(c.Name == 'corner hole pitch' for c in features[0].Checks)


def test_a_plates_missing_holes_are_placed_on_the_side_its_holes_are() -> None:
    """
    Description:
        The mounting plate's through-holes sit by one long edge, mirrored either way: with one found, the missing
        one is placed at the pitch from it on the same side, not across the plate; the countersinks missing too are
        placed around both through-holes, the one found and the one placed (the partial case); with none found nothing
        is placed, since either side could be meant.
    """

    from Vision.Utilities.Holes import Hole_Features
    found = [Hole_Str(Diameter_Mm=6.1, X_Mm=15.0, Y_Mm=17.5)]
    features = Hole_Features(found, CONST_PLATE_FRONT, 40.0, 60.0)
    assert _Centres(features) == [(15.0, 17.5, False), (15.0, 42.5, False), (15.0, 17.5, True), (15.0, 42.5, False)]
    assert [f.Name for f in features] == ['countersink', 'countersink', 'through-hole', 'through-hole']
    # By the other long edge (the plate lies the other way round), the missing one is placed there too.
    other = Hole_Features([Hole_Str(Diameter_Mm=6.1, X_Mm=25.0, Y_Mm=17.5)], CONST_PLATE_FRONT[1:], 40.0, 60.0)
    assert _Centres(other) == [(25.0, 17.5, True), (25.0, 42.5, False)]
    assert _Centres(Hole_Features([], CONST_PLATE_FRONT[1:], 40.0, 60.0)) == []


def test_a_hole_too_many_fails_its_group() -> None:
    """
    Description:
        A group with more holes than the part has marks each of them failed, whatever its own checks, so the
        extra one is among the marked.
    """

    from Vision.Utilities.Holes import Hole_Features
    found = [Hole_Str(Diameter_Mm=6.1, X_Mm=15.0, Y_Mm=17.5), Hole_Str(Diameter_Mm=6.1, X_Mm=15.0, Y_Mm=42.5),
             Hole_Str(Diameter_Mm=6.1, X_Mm=25.0, Y_Mm=17.5)]
    features = Hole_Features(found, CONST_PLATE_FRONT[1:], 40.0, 60.0)
    assert len(features) == 3 and not any(f.Passed for f in features)


def test_a_holes_outline_is_its_masks_contour_in_mm_and_the_frame_marks_it() -> None:
    """
    Description:
        A candidate keeps its mask's outer contour, simplified under a pixel, in mm: every point of a 6 mm disc's
        outline lies on its 3 mm radius, and the hole's feature carries that outline for the frame to draw.
    """

    from Vision.Utilities.Holes import Hole_Features
    (hole,) = Hole_Candidates([_Disc((600, 400), 15.0, 17.5, 6.0)], 0.1, cv2, np)
    radii = [np.hypot(x - 15.0, y - 17.5) for x, y in hole.Outline]
    assert len(radii) >= 12 and max(abs(r - 3.0) for r in radii) < 0.15
    features = Hole_Features([hole], CONST_PLATE_FRONT[1:], 40.0, 60.0)
    assert features[0].Found and features[0].Outlines == [hole.Outline]


def test_a_missing_holes_outline_is_a_circle_of_its_groups_diameter_at_its_position() -> None:
    """
    Description:
        A hole expected and not found is outlined by a circle of its group's diameter at its expected position:
        the through-hole missing at the pitch from the one found (6 mm, at 15, 42.5) and the countersinks missing
        around the through-hole found and the one placed (12 mm, at 15, 17.5 and 15, 42.5), so the frame draws both
        circles of a stepped hole, as it draws a found one.
    """

    from Vision.Utilities.Holes import Hole_Features
    features = Hole_Features([Hole_Str(Diameter_Mm=6.1, X_Mm=15.0, Y_Mm=17.5)], CONST_PLATE_FRONT, 40.0, 60.0)
    missing = [(f.Name, f.Outlines) for f in features if not f.Found]
    assert [name for name, _ in missing] == ['countersink', 'countersink', 'through-hole']
    for (_name, (outline,)), (cx, cy, d) in zip(missing, ((15.0, 17.5, 12.0), (15.0, 42.5, 12.0), (15.0, 42.5, 6.0))):
        assert len(outline) >= 36
        assert all(np.hypot(x - cx, y - cy) == pytest.approx(d / 2.0) for x, y in outline)


def test_through_holes_missing_under_found_countersinks_are_placed_at_their_centres() -> None:
    """
    Description:
        A front whose countersinks are found and whose through-holes are not: the countersinks' centres sit at two of
        the through-holes' mirrored positions, so they anchor the through-holes, which are placed there (6 mm, at 15,
        17.5 and 15, 42.5), on the side the countersinks are. With nothing of its own to anchor on, the group once
        placed none, and a front showing two stepped holes with no bore drew no through-hole mark.
    """

    from Vision.Utilities.Holes import Hole_Features
    countersinks = [Hole_Str(Diameter_Mm=12.1, X_Mm=15.3, Y_Mm=17.7), Hole_Str(Diameter_Mm=12.2, X_Mm=15.2, Y_Mm=42.4)]
    features = Hole_Features(countersinks, CONST_PLATE_FRONT, 40.0, 60.0)
    missing = [f for f in features if not f.Found]
    assert [f.Name for f in missing] == ['through-hole', 'through-hole']
    assert _Centres(missing) == [(15.0, 17.5, False), (15.0, 42.5, False)]
    for feature, (cx, cy) in zip(missing, ((15.0, 17.5), (15.0, 42.5))):
        assert all(np.hypot(x - cx, y - cy) == pytest.approx(3.0) for x, y in feature.Outlines[0])
    # By the other long edge, the other side.
    turned = [Hole_Str(Diameter_Mm=12.1, X_Mm=24.8, Y_Mm=17.6), Hole_Str(Diameter_Mm=12.2, X_Mm=24.9, Y_Mm=42.3)]
    assert _Centres([f for f in Hole_Features(turned, CONST_PLATE_FRONT, 40.0, 60.0) if not f.Found]) == \
        [(25.0, 17.5, False), (25.0, 42.5, False)]


def test_a_side_with_no_hole_found_places_none_since_its_end_cannot_be_told() -> None:
    """
    Description:
        A side with no hole of any group found (capture 20261015-143622_s1's object 3, a back with no holes): the
        through-holes' mirrored positions are not centred on the part, and with nothing found the outline does not
        say which end is which (DINOv2's best turn against the reference picked the wrong end on 3 of 21 plates
        (the test set and the capture's front) even with their holes in view; docs/design-decisions.md), so no position is invented. Reporting.Core
        says so in the object's note.
    """

    from Vision.Utilities.Holes import Hole_Features
    assert Hole_Features([], CONST_PLATE_FRONT, 40.0, 60.0) == []
    assert Hole_Features([], CONST_PLATE_FRONT[1:], 40.0, 60.0) == []


# The mounting plate's back, as the shipped item gives it: its through-holes only.
CONST_PLATE_BACK = [Catalogue_Hole_Group_Str(Name='through-hole', Diameter_Mm=6.0, Count=2, From_Long_Edge_Mm=15.0,
                                             From_Short_Edge_Mm=17.5, Pitch_Mm=25.0, Tolerance_Mm=1.5)]


def test_a_through_hole_in_its_countersink_is_measured_at_the_countersinks_centre() -> None:
    """
    Description:
        A stepped hole's bore is seen below the top face, and away from the frame centre its opening shifts towards
        it: on 20261015-170816_17, 60 mm out, a through-hole read 19.04 mm from its short edge against 17.5 ± 1.5 while
        its countersink, on the top face, read 18.0. Measured at its countersink's centre it passes; its diameter is
        still its own. A through-hole with no countersink around it (the back) keeps its own centre.
    """

    shifted = _Holes((15.0, 19.4, 6.1), (15.0, 44.4, 6.1), (15.0, 17.5, 12.2), (15.0, 42.5, 12.2))
    counts, checks = Check_Holes(shifted, CONST_PLATE_FRONT, 40.0, 60.0)
    assert [(c.Name, c.Found) for c in counts] == [('countersink', 2), ('through-hole', 2)]
    assert [(c.Name, round(c.Measured_Mm, 2)) for c in checks if not c.Within] == []
    assert [round(c.Measured_Mm, 2) for c in checks if c.Name == 'through-hole Ø'] == [6.1, 6.1]
    seated = Seat_Holes(shifted, CONST_PLATE_FRONT)
    assert [(h.X_Mm, h.Y_Mm, h.Diameter_Mm) for h in seated[:2]] == [(15.0, 17.5, 6.1), (15.0, 42.5, 6.1)]
    assert [(h.X_Mm, h.Y_Mm) for h in shifted[:2]] == [(15.0, 19.4), (15.0, 44.4)]
    alone = _Holes((15.0, 19.4, 6.1), (15.0, 44.4, 6.1))
    assert Seat_Holes(alone, CONST_PLATE_FRONT) == alone
    assert [c.Name for c in Check_Holes(alone, CONST_PLATE_BACK, 40.0, 60.0)[1] if not c.Within] == [
        "through-hole's distance from the short edge"] * 2


def test_a_hole_only_one_side_has_shows_that_side() -> None:
    """
    Description:
        The countersinks are the front's alone, so a found one shows the front wherever the part lies; the
        through-holes are on both sides and show neither, nor does no hole at all (a front missing its countersinks
        shows no side: absence is never evidence). On the stained front 57-67 mm out DINOv2 chose the back; its
        countersinks were found on every frame.
    """

    sides = {'front': CONST_PLATE_FRONT, 'back': CONST_PLATE_BACK}
    front = _Holes((15.0, 17.5, 6.1), (15.0, 42.5, 6.2), (15.0, 17.5, 12.2), (15.0, 42.5, 12.3))
    assert Side_Evidence(front, sides, 40.0, 60.0) == ['front']
    assert Side_Evidence(front[2:3], sides, 40.0, 60.0) == ['front']
    assert Side_Evidence(front[:2], sides, 40.0, 60.0) == []
    assert Side_Evidence([], sides, 40.0, 60.0) == []


def test_edge_distances_are_from_the_top_face_not_the_side_wall() -> None:
    """
    Description:
        Away from the optical axis the outline takes in the side wall on the edges facing it, so the crop's edge is
        not the top face's (Vision.Utilities.Classify.Wall_Widths): on 20261015-143626_1, 61.6 mm out, the outline
        read 41.31 mm across and a countersink-seated through-hole 16.6 mm from that long edge. With the wall left
        out the distances are the top face's; the marks stay where the holes are on the crop.
    """

    plate = _Holes((16.8, 17.5, 6.1), (16.8, 42.5, 6.1), (16.8, 17.5, 12.2), (16.8, 42.5, 12.2))
    walls = (1.8, 0.0, 0.0, 0.0)
    assert [c.Name for c in Check_Holes(plate, CONST_PLATE_FRONT, 41.8, 60.0)[1] if not c.Within] == [
        "through-hole's distance from the long edge"] * 2
    counts, checks = Check_Holes(plate, CONST_PLATE_FRONT, 41.8, 60.0, walls)
    assert [c.Found for c in counts] == [2, 2] and all(c.Within for c in checks)
    assert [round(c.Measured_Mm, 2) for c in checks if c.Name == "through-hole's distance from the long edge"] == [15.0] * 2
    marks = Hole_Features(plate, CONST_PLATE_FRONT, 41.8, 60.0, walls)
    assert all(f.Passed for f in marks)
    assert [(round(sum(x for x, _y in f.Corners) / 4, 2), round(sum(y for _x, y in f.Corners) / 4, 2)) for f in marks] == [
        (16.8, 17.5), (16.8, 42.5), (16.8, 17.5), (16.8, 42.5)]
