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
# File Name: ../UI/Utilities/Pixel_Motif.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp

"""
Description:
    The brand's pixel motif for the funding band (docs/design-decisions.md, "The funding band carries the brand's pixel
    motif"): small squares on a square grid, as in the JIC Smart Factory style guide and on the AnyScan poster, where
    whole cells are filled singly or in short runs, densest at the format's edge and thinning towards its content (the
    poster's top-right cluster fills 9 of its 6 x 4 cells, in two tints).

    Motif_Cells lays the cells out for a band: each half of the band is a grid anchored to its own outer edge, so a
    resize adds or removes cells next to the logos and never reshuffles the pattern. A cell is filled where a fixed hash
    of its row and its column from the edge falls under the fill chance at that column, which falls linearly from
    `fill` at the edge to nothing `reach` cells in. No cell touches a keep-out span (each logo with its clear space).
    Corner_Cells places the AnyScan poster's own corner cluster (CONST_POSTER_CORNER) at a corner of a widget.
    Busy_Cells gives the cells of the busy overlay's pixel icons (CONST_BUSY_ICONS) at an animation tick.

    Qt-free.
"""
# The AnyScan poster's top-right cluster (design/Poster AnyScan/AnyScan poster-selection-1.pdf), read cell by cell:
# 6 x 4 cells anchored to the page's top-right corner, L the lighter periwinkle, D the deeper one, '.' empty.
#   Unit [Tuple<string>]
CONST_POSTER_CORNER = ('....L.', 'L....D', '.D.L.D', '.DD.L.')


def __Hash(row: int, column: int, side: int, salt: int) -> float:
    """
    Description:
        A fixed pseudo-random number for a cell, the same on every run and every machine.

    Args:
        (1) row [int]: The cell's row.
        (2) column [int]: The cell's column, counted from its edge.
        (3) side [int]: 0 for the left half, 1 for the right.
        (4) salt [int]: Which number of the cell (0 its fill, 1 its tint).

    Returns:
        (1) parameter [float]: A number in [0, 1).
    """

    h = (row * 73856093) ^ (column * 19349663) ^ (side * 83492791) ^ (salt * 2654435761)
    h &= 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x45D9F3B) & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x45D9F3B) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def Motif_Cells(width: int, height: int, cell: int, fill: float, reach: int, strong: float,
                keep_out: tp.List[tp.Tuple[float, float]]) -> tp.List[tp.Tuple[int, int, bool]]:
    """
    Description:
        The filled cells of the motif in a band.

    Args:
        (1) width, height [int]: The band's size, in logical pixels.
        (3) cell [int]: The cell's side, in logical pixels.
        (4) fill [float]: The chance a cell at the band's edge is filled, 0..1.
        (5) reach [int]: How many cells in from the edge the chance falls to nothing.
        (6) strong [float]: The share of filled cells in the stronger of the two tints, 0..1.
        (7) keep_out [List<Tuple<float, float>>]: The x spans, (left, right), no cell may touch.

    Returns:
        (1) parameter [List<Tuple<int, int, bool>>]: Each filled cell's left x and top y and whether it is in the
                                                     stronger tint.
    """

    cells = []
    rows = height // cell
    for side in (0, 1):
        for column in range(min(reach, (width // 2) // cell)):
            chance = fill * (1.0 - column / reach)
            x = column * cell if side == 0 else width - (column + 1) * cell
            if any(x < right and x + cell > left for left, right in keep_out):
                continue
            for row in range(rows):
                if __Hash(row, column, side, 0) < chance:
                    cells.append((x, row * cell, __Hash(row, column, side, 1) < strong))
    return cells


def Corner_Cells(right: int, top: int, cell: int) -> tp.List[tp.Tuple[int, int, bool]]:
    """
    Description:
        The poster's corner cluster anchored with its top-right corner at a point.

    Args:
        (1) right [int]: The cluster's right edge, in logical pixels.
        (2) top [int]: Its top edge, in logical pixels.
        (3) cell [int]: The cell's side, in logical pixels.

    Returns:
        (1) parameter [List<Tuple<int, int, bool>>]: Each filled cell's left x and top y and whether it is the deeper
                                                     tint.
    """

    columns = len(CONST_POSTER_CORNER[0])
    return [(right - (columns - column) * cell, top + row * cell, mark == 'D')
            for row, line in enumerate(CONST_POSTER_CORNER) for column, mark in enumerate(line) if mark != '.']


# The busy overlay's pixel icons (docs/design-decisions.md, "The busy overlay is the Camera View's grey-lilac"), in the
# brand's style: whole cells on a square grid. A task icon is drawn row by row: '#' a cell always lit, a digit d a cell
# lit only on step d - 1 of the icon's cycle (dim otherwise), '.' empty. The camera (connecting, capturing) blinks its
# lens; the magnifier (preparing, analysing) moves a glint across its lens.
#   Unit [Dict<string, Tuple<Tuple<string>, int, int>>] (rows, steps in a cycle, ticks per step)
CONST_BUSY_ICONS = {
    'camera': (('...###.....',
                '###########',
                '####...####',
                '###.....###',
                '###..1..###',
                '###.....###',
                '####...####',
                '###########'), 2, 5),
    'magnifier': (('.#####....',
                   '#.....#...',
                   '#.1...#...',
                   '#..2..#...',
                   '#...3.#...',
                   '#.....#...',
                   '.#####....',
                   '......##..',
                   '.......##.',
                   '........##'), 4, 3)}
def Busy_Cells(kind: str, tick: int, dim: float) -> tp.List[tp.Tuple[int, int, float]]:
    """
    Description:
        The cells of a task's busy icon (a key of CONST_BUSY_ICONS) at an animation tick, each with its opacity: a '#'
        cell always lit, a digit cell lit only on its step of the icon's cycle and dim otherwise.

    Args:
        (1) kind [string]: The task's icon, a key of CONST_BUSY_ICONS ('camera', 'magnifier').
        (2) tick [int]: The animation tick (0 for a static icon).
        (3) dim [float]: The opacity of an unlit cell.

    Returns:
        (1) parameter [List<Tuple<int, int, float>>]: Each cell's column, row and opacity (0..1).
    """

    rows, steps, ticks_per_step = CONST_BUSY_ICONS[kind]
    step = (tick // ticks_per_step) % steps
    return [(column, row, 1.0 if mark == '#' or int(mark) - 1 == step else dim)
            for row, line in enumerate(rows) for column, mark in enumerate(line) if mark != '.']
