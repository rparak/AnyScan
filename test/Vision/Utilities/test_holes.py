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
from Vision.Utilities.Holes import Hole_Candidates, Check_Holes
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

# The mounting plate's front groups and the labyrinth's corner holes, as the shipped items give them.
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
        threshold that sits under the real holes' 0.875), a disc
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


def test_corner_holes_are_counted_at_the_corners_and_the_maze_marks_are_not() -> None:
    """
    Description:
        The labyrinth's corner holes are counted at all four corners; a round mark of their size 5 mm along an
        edge from a corner (where the maze's start and finish lie, 4.9 mm or more on the test set) is outside the
        counting gate and is not counted; a missing corner hole is counted missing. Only neighbouring holes,
        42 mm apart, are checked as pitch, not the diagonals.
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
