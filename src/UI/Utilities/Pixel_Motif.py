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

# System (Default)
import math
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
    CONST_PIXEL_ICONS is the one set of pixel icons, read by the application and by the architecture diagram's
    generator (Example/UI/architecture_diagram.py): Icon_Cells gives an icon's cells drawn still, Busy_Cells the cells
    of a busy icon (CONST_BUSY_STEPS) at an animation tick. Grid_Shape and Wave_Diagonals lay out the analysis grid and
    its wave (CONST_WAVE_*).

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


# The brand's pixel icons, the ONE set the application and the architecture diagram draw (docs/design-decisions.md,
# "Every icon is a pixel icon from one set"): in the JIC Smart Factory guide's pixel style (its IKONY pages), each a
# 12 x 12 grid read row by row, one square cell per mark, drawn in one colour (no icon font, no third-party set, so no
# licence to carry). '#' is a cell every drawing fills, '.' an empty one. A digit d is a cell only the busy icons draw
# (Busy_Cells), lit on step d - 1 of the icon's cycle and dim otherwise; a still drawing (Icon_Cells, the diagram, a
# card head) leaves it empty: the camera's lens centre blinks, the magnifier's glint crosses its lens. Drawn at a whole
# number of pixels a cell (CONST_ICON_GRID), so every cell stays a crisp square at 1x and at a device pixel ratio of 2.
# gauge, log and model were added for the application (2026-10-18): the diagram had no icon for a confidence, a log
# or a model.
#   Unit [Dict<string, Tuple<string>>]
CONST_PIXEL_ICONS = {
    'camera': ('............', '...####.....', '.##########.', '.#........#.', '.#...##...#.', '.#..#11#..#.',
               '.#..#11#..#.', '.#...##...#.', '.#........#.', '.##########.', '............', '............'),
    'magnifier': ('............', '..####......', '.#....#.....', '#.1....#....', '#..2...#....', '#...3..#....',
                  '#......#....', '.#....#.....', '..####.#....', '........#...', '.........#..', '..........#.'),
    'text': ('............', '##########..', '............', '##########..', '............', '##########..',
             '............', '######......', '............', '###.........', '............', '............'),
    'ruler': ('............', '............', '............', '############', '#.#.#.#.#.##', '#.#...#....#',
              '#..........#', '############', '............', '............', '............', '............'),
    'window': ('............', '############', '#..........#', '#.#.#......#', '############', '#..........#',
               '#..........#', '#..........#', '#..........#', '#..........#', '############', '............'),
    'focus': ('###......###', '#..........#', '#..........#', '............', '....####....', '....#..#....',
              '....#..#....', '....####....', '............', '#..........#', '#..........#', '###......###'),
    'checklist': ('............', '..#.........', '.#..........', '#.#..######.', '............', '............',
                  '..#.........', '.#..........', '#.#..######.', '............', '............', '............'),
    'badge': ('.....##.....', '...##..##...', '.##......##.', '.#........#.', '.#.....#..#.', '.#....#...#.',
              '.#.#.#....#.', '.#..#.....#.', '..#......#..', '...#....#...', '....#..#....', '.....##.....'),
    'gear': ('.....##.....', '..#.####.#..', '.##########.', '..###..###..', '.##......##.', '###......###',
             '###......###', '.##......##.', '..###..###..', '.##########.', '..#.####.#..', '.....##.....'),
    'station': ('............', '.######.....', '.#....#.....', '.#...####...', '.#...#..#...', '.#...####...',
                '.#....##....', '.#..........', '.#..........', '.#..........', '############', '............'),
    'target': ('.....#......', '...#####....', '..#..#..#...', '.#...#...#..', '.#..###..#..', '######.#####',
               '.#..###..#..', '.#...#...#..', '..#..#..#...', '...#####....', '.....#......', '............'),
    'area': ('###.####.###', '#..........#', '#..........#', '...######...', '...######...', '#..######..#',
             '#..######..#', '...######...', '...######...', '#..........#', '#..........#', '###.####.###'),
    'catalogue': ('............', '####....####', '#...#..#...#', '#....##....#', '#....#.....#', '#....#.....#',
                  '#....#.....#', '#....#.....#', '#....#.....#', '####.#.####.', '....###.....', '............'),
    'image': ('............', '############', '#..........#', '#.##.......#', '#.##.......#', '#.......#..#',
              '#......###.#', '#..#..#####.', '#.##########', '############', '............', '............'),
    'folder': ('............', '####........', '#...#.......', '#....######.', '#..........#', '#..........#',
               '#..........#', '#..........#', '#..........#', '############', '............', '............'),
    'gauge': ('............', '...######...', '..#......#..', '.#........#.', '#.......#..#', '#......#...#',
              '#.....#....#', '#....##....#', '#....##....#', '############', '............', '............'),
    'log': ('............', '###.#######.', '............', '###.#####...', '............', '###.########',
            '............', '###.######..', '............', '###.####....', '............', '............'),
    'model': ('.....#......', '...##.##....', '.##.....##..', '#.##...##.#.', '#...###...#.', '#....#....#.',
              '#....#....#.', '#....#....#.', '#....#....#.', '.##..#..##..', '...##.##....', '.....#......')}
# The side of every icon's grid.
#   Unit [int] (cells)
CONST_ICON_GRID = 12
# The busy icons (docs/design-decisions.md, "The busy overlay is the Camera View's grey-lilac"), drawn large on the busy
# overlay and small in the Camera View head's state marker: each a key of CONST_PIXEL_ICONS with its cycle. The camera
# (connecting, scanning) blinks its lens; the magnifier (a close stopping an analysis, the ANALYZING… marker) moves a
# glint across its lens.
#   Unit [Dict<string, Tuple<int, int>>] (steps in a cycle, ticks per step)
CONST_BUSY_STEPS = {'camera': (2, 5), 'magnifier': (4, 3)}


def Icon_Cells(name: str) -> tp.List[tp.Tuple[int, int]]:
    """
    Description:
        The filled cells of an icon drawn still (a card head, the diagram): its '#' cells, row by row, at their place in
        the CONST_ICON_GRID square, so every icon takes the same square whatever its ink.

    Args:
        (1) name [string]: The icon, a key of CONST_PIXEL_ICONS.

    Returns:
        (1) parameter [List<Tuple<int, int>>]: Each filled cell's column and row.
    """

    return [(column, row) for row, line in enumerate(CONST_PIXEL_ICONS[name]) for column, mark in enumerate(line)
            if mark == '#']


def Busy_Cells(kind: str, tick: int, dim: float) -> tp.List[tp.Tuple[int, int, float]]:
    """
    Description:
        The cells of a busy icon (a key of CONST_BUSY_STEPS) at an animation tick, each with its opacity: a '#' cell
        always lit, a digit cell lit only on its step of the icon's cycle and dim otherwise. The cells are counted from
        the icon's ink (its first marked column and row), so the icon centres on its ink, not on its grid.

    Args:
        (1) kind [string]: The task's icon, a key of CONST_BUSY_STEPS ('camera', 'magnifier').
        (2) tick [int]: The animation tick (0 for a static icon).
        (3) dim [float]: The opacity of an unlit cell.

    Returns:
        (1) parameter [List<Tuple<int, int, float>>]: Each cell's column, row and opacity (0..1).
    """

    steps, ticks_per_step = CONST_BUSY_STEPS[kind]
    step = (tick // ticks_per_step) % steps
    marked = [(column, row, mark) for row, line in enumerate(CONST_PIXEL_ICONS[kind]) for column, mark in enumerate(line)
              if mark != '.']
    left, top = min(column for column, _, _ in marked), min(row for _, row, _ in marked)
    return [(column - left, row - top, 1.0 if mark == '#' or int(mark) - 1 == step else dim)
            for column, row, mark in marked]


# The analysis grid's wave (docs/design-decisions.md, "ANALYZE sweeps a decorative pixel grid over the frame"): square
# cells on the frame, lit along a band of diagonals that enters at the top-left corner and leaves at the bottom-right,
# fading behind it in steps, then a short rest on the clean frame, as in the reference animation. Decoration only: it
# never depends on the frame. The band and each fade step are fractions of the grid's diagonals, so the wave looks the
# same on any frame. The front crosses the frame (its first to its last diagonal) in CONST_WAVE_CROSS_MS, as the
# reference's does (about ten 50 ms frames); band and fade then leave at the same speed, and the frame rests clean for
# CONST_WAVE_REST_MS: a loop of about 1 s, repeated while the analysis runs.
#   Unit [float] (fraction of the diagonals) / [Tuple<float>] (opacity of each fade step, 0..1) / [int] (ms)
CONST_WAVE_BAND = 0.30
CONST_WAVE_FADE_STEP = 0.08
CONST_WAVE_FADE = (0.55, 0.25)
CONST_WAVE_CROSS_MS = 500
CONST_WAVE_REST_MS = 250


def Grid_Shape(width: int, height: int, columns: int) -> tp.Tuple[int, int, float]:
    """
    Description:
        The analysis grid laid over a frame: `columns` square cells across, as many rows as cover its height (the last
        row cut by the frame's bottom edge when the height is not a whole number of cells).

    Args:
        (1) width [int]: The frame's width.
        (2) height [int]: The frame's height.
        (3) columns [int]: The cells across.

    Returns:
        (1) parameter [int]: The columns.
        (2) parameter [int]: The rows.
        (3) parameter [float]: A cell's side, in the frame's pixels.
    """

    cell = width / float(columns)
    return columns, max(1, math.ceil(height / cell - 1e-9)), cell


def Wave_Diagonals(columns: int, rows: int, elapsed_ms: int) -> tp.List[tp.Tuple[int, int, float]]:
    """
    Description:
        The diagonals (column + row) of the analysis grid lit a time into the animation, as ranges with their opacity:
        the wave's front moves one grid's worth of diagonals per CONST_WAVE_CROSS_MS; a cell lights when the front
        reaches its diagonal, stays fully lit for CONST_WAVE_BAND of the diagonals, then fades through
        CONST_WAVE_FADE, CONST_WAVE_FADE_STEP of the diagonals each, and goes out. Once the last fade step has left the
        grid nothing is lit for CONST_WAVE_REST_MS, and the loop starts again.

    Args:
        (1) columns [int]: The grid's columns.
        (2) rows [int]: The grid's rows.
        (3) elapsed_ms [int]: The time since the animation started.

    Returns:
        (1) parameter [List<Tuple<int, int, float>>]: Each lit range's first diagonal, the diagonal after its last
            (clipped to the grid's) and opacity (0..1): the band first, then each fade step; empty ranges left out.
    """

    diagonals = columns + rows - 1
    band = max(1, round(CONST_WAVE_BAND * diagonals))
    step = max(1, round(CONST_WAVE_FADE_STEP * diagonals))
    travel = diagonals + band + step * len(CONST_WAVE_FADE)
    # The time the front takes to run until the last fade step has left the grid, at one grid per CONST_WAVE_CROSS_MS,
    # in whole milliseconds, so every loop is the same.
    sweep_ms = round(travel * CONST_WAVE_CROSS_MS / float(diagonals))
    elapsed = elapsed_ms % (sweep_ms + CONST_WAVE_REST_MS)
    if elapsed >= sweep_ms:
        return []
    front = int(elapsed * diagonals / CONST_WAVE_CROSS_MS)
    ranges = [(front - band + 1, front + 1, 1.0)]
    for index, opacity in enumerate(CONST_WAVE_FADE):
        after = front - band - step * index + 1
        ranges.append((after - step, after, opacity))
    return [(max(first, 0), min(after, diagonals), opacity) for first, after, opacity in ranges
            if max(first, 0) < min(after, diagonals)]
