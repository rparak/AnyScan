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
# File Name: ../test/UI/test_pixel_motif.py
## =========================================================================== ##

# Custom Lib.: AnyScan UI — the funding band's pixel motif (Qt-free)
#   ../UI/Utilities/Pixel_Motif
from UI.Utilities.Pixel_Motif import Motif_Cells, Corner_Cells, CONST_POSTER_CORNER

"""
Description:
    The funding band's pixel motif, laid out without Qt: whole cells on the grid, clustered at the band's two ends and
    thinning to nothing `reach` cells in, never touching a keep-out span, and anchored to the ends so a wider band keeps
    every square it had and only adds new ones next to the logos.
"""
# A band, its cell, and the variant the owner chose (A).
#   Unit [px], [px], [0..1], [cells], [0..1]
CONST_WIDTH, CONST_HEIGHT, CONST_CELL = 1884, 90, 15
CONST_FILL, CONST_REACH, CONST_STRONG = 0.30, 16, 0.4


def test_the_squares_are_whole_cells_in_the_band_within_reach_of_its_ends() -> None:
    """
    Description:
        Every square is a whole cell inside the band, on the grid anchored to its nearer end, and no farther than
        `reach` cells from it; there are squares at both ends.
    """

    cells = Motif_Cells(CONST_WIDTH, CONST_HEIGHT, CONST_CELL, CONST_FILL, CONST_REACH, CONST_STRONG, [])
    assert cells
    for x, y, _ in cells:
        assert 0 <= x and x + CONST_CELL <= CONST_WIDTH and 0 <= y and y + CONST_CELL <= CONST_HEIGHT
        assert y % CONST_CELL == 0
        from_edge = x if x < CONST_WIDTH / 2 else CONST_WIDTH - x - CONST_CELL
        assert from_edge % CONST_CELL == 0 and from_edge // CONST_CELL < CONST_REACH
    assert any(x < CONST_WIDTH / 2 for x, _, _ in cells) and any(x > CONST_WIDTH / 2 for x, _, _ in cells)


def test_the_squares_thin_out_from_the_ends() -> None:
    """
    Description:
        The share of filled cells falls from the band's ends inwards: the outer quarter of the reach is fuller than
        the inner quarter.
    """

    cells = Motif_Cells(CONST_WIDTH, CONST_HEIGHT, CONST_CELL, CONST_FILL, CONST_REACH, CONST_STRONG, [])
    columns = [(x if x < CONST_WIDTH / 2 else CONST_WIDTH - x - CONST_CELL) // CONST_CELL for x, _, _ in cells]
    quarter = CONST_REACH // 4
    assert sum(c < quarter for c in columns) > sum(c >= CONST_REACH - quarter for c in columns)


def test_no_square_touches_a_keep_out_span() -> None:
    """
    Description:
        A cell that would overlap a keep-out span (a logo with its clear space) is left empty, even at a band end.
    """

    keep_out = [(10.0, 70.0), (CONST_WIDTH - 100.0, CONST_WIDTH - 40.0)]
    cells = Motif_Cells(CONST_WIDTH, CONST_HEIGHT, CONST_CELL, 1.0, CONST_REACH, CONST_STRONG, keep_out)
    assert cells
    assert not [x for x, _, _ in cells if any(x < right and x + CONST_CELL > left for left, right in keep_out)]


def test_a_wider_band_keeps_every_square_it_had() -> None:
    """
    Description:
        The pattern is fixed and anchored to each end: widening the band keeps the left half's squares where they were
        and the right half's at the same distance from the right end.
    """

    narrow = Motif_Cells(1461, CONST_HEIGHT, CONST_CELL, CONST_FILL, CONST_REACH, CONST_STRONG, [])
    wide = Motif_Cells(CONST_WIDTH, CONST_HEIGHT, CONST_CELL, CONST_FILL, CONST_REACH, CONST_STRONG, [])
    left = lambda cells, width: {(x, y, s) for x, y, s in cells if x < width / 2}
    right = lambda cells, width: {(width - x, y, s) for x, y, s in cells if x >= width / 2}
    assert left(narrow, 1461) == left(wide, CONST_WIDTH)
    assert right(narrow, 1461) == right(wide, CONST_WIDTH)


def test_the_corner_cluster_is_the_posters_anchored_at_its_top_right() -> None:
    """
    Description:
        Corner_Cells places the poster's cluster, as read off the poster (6 x 4 cells, 9 filled, 5 of them the deeper
        tint), with its top-right corner at the given point.
    """

    assert CONST_POSTER_CORNER == ('....L.', 'L....D', '.D.L.D', '.DD.L.')
    cells = Corner_Cells(500, 40, 16)
    assert len(cells) == 9 and sum(strong for _, _, strong in cells) == 5
    assert max(x for x, _, _ in cells) + 16 == 500 and min(y for _, y, _ in cells) == 40
    assert (500 - 16, 40 + 16, True) in cells and (500 - 6 * 16, 40 + 16, False) in cells
