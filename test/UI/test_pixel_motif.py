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
from UI.Utilities.Pixel_Motif import (Motif_Cells, Corner_Cells, Busy_Cells, Grid_Shape, Wave_Diagonals, CONST_POSTER_CORNER,
                                     CONST_PIXEL_ICONS, CONST_BUSY_STEPS, CONST_WAVE_CROSS_MS, CONST_WAVE_REST_MS)

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


def test_a_busy_icon_animates_only_its_step_cells() -> None:
    """
    Description:
        A task's busy icon keeps every solid cell lit at every tick and lights a step cell only on its own step: the
        camera's lens is lit for 5 ticks and dim for the next 5, and the magnifier's glint crosses its lens over three
        steps of 3 ticks each, then rests for one. The cells are counted from the icon's ink: the camera's first marked
        column and row are 1 and 1 of its 12 x 12 grid, the magnifier's 0 and 1.
    """

    ink = {'camera': (1, 1), 'magnifier': (0, 1)}

    def Lit(kind: str, tick: int) -> set:
        return {(column, row) for column, row, alpha in Busy_Cells(kind, tick, 0.2) if alpha == 1.0}

    assert set(CONST_BUSY_STEPS) == set(ink)
    for kind in CONST_BUSY_STEPS:
        rows, (left, top) = CONST_PIXEL_ICONS[kind], ink[kind]
        solid = {(column - left, row - top) for row, line in enumerate(rows) for column, mark in enumerate(line)
                 if mark == '#'}
        everything = {(column - left, row - top) for row, line in enumerate(rows) for column, mark in enumerate(line)
                      if mark != '.'}
        for tick in range(24):
            assert solid <= Lit(kind, tick), (kind, tick)
            assert {(column, row) for column, row, _ in Busy_Cells(kind, tick, 0.2)} == everything
    lens = (4, 4)
    assert [lens in Lit('camera', tick) for tick in (0, 4, 5, 9, 10)] == [True, True, False, False, True]
    glint = {1: (2, 2), 2: (3, 3), 3: (4, 4)}
    for tick, expected in ((0, glint[1]), (3, glint[2]), (6, glint[3])):
        assert Lit('magnifier', tick) - {(c, r - 1) for r, line in enumerate(CONST_PIXEL_ICONS['magnifier'])
                                         for c, mark in enumerate(line) if mark == '#'} == {expected}, tick
    assert not set(glint.values()) & Lit('magnifier', 9)                       # the fourth step rests


def test_the_grid_is_square_cells_across_the_frame() -> None:
    """
    Description:
        The analysis grid over the station's 1920 x 1200 frame is 48 x 30 cells of 40 px; a frame whose height is no
        whole number of cells gets one more row, cut by its bottom edge.
    """

    assert Grid_Shape(1920, 1200, 48) == (48, 30, 40.0)
    assert Grid_Shape(1920, 1210, 48) == (48, 31, 40.0)


def test_the_wave_crosses_from_the_top_left_in_half_a_second_fades_behind_and_repeats() -> None:
    """
    Description:
        The wave starts at the top-left cell (diagonal 0), its front reaches the last diagonal after the crossing time
        (about 0.5 s), every lit range lies on the grid, the band is lit fully and the steps behind it fade in turn;
        once the fade has left the grid the frame rests clean for the rest time, and then the loop starts again, the
        same as at its start.
    """

    columns, rows = 48, 30
    diagonals = columns + rows - 1
    assert 400 <= CONST_WAVE_CROSS_MS <= 600
    assert Wave_Diagonals(columns, rows, 0) == [(0, 1, 1.0)]
    band = Wave_Diagonals(columns, rows, CONST_WAVE_CROSS_MS)
    assert band[0][1] == diagonals and band[0][2] == 1.0
    opacities = [opacity for _, _, opacity in band]
    assert opacities == sorted(opacities, reverse=True) and len(set(opacities)) == len(opacities) >= 3
    for elapsed in range(0, 2000, 20):
        for first, after, opacity in Wave_Diagonals(columns, rows, elapsed):
            assert 0 <= first < after <= diagonals and 0 < opacity <= 1.0
    # The first empty time after the crossing starts the rest; after it the loop repeats.
    rest = next(t for t in range(CONST_WAVE_CROSS_MS, 3000) if not Wave_Diagonals(columns, rows, t))
    assert all(not Wave_Diagonals(columns, rows, t) for t in range(rest, rest + CONST_WAVE_REST_MS - 1))
    period = next(t for t in range(rest, rest + 2 * CONST_WAVE_REST_MS) if Wave_Diagonals(columns, rows, t))
    assert period <= 1200
    for elapsed in range(0, 1000, 20):
        assert Wave_Diagonals(columns, rows, elapsed + period) == Wave_Diagonals(columns, rows, elapsed + 0)
