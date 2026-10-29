# The pixel icon set

Source: `templates/JIC_SF_UI/Pixel_Motif.py` (`CONST_PIXEL_ICONS`, `Icon_Cells`, `Busy_Cells`, `CONST_BUSY_STEPS`), a
copy of AnyScan's `src/UI/Utilities/Pixel_Motif.py`. Drawn by `Widgets.Icon_Cls`, `State_Marker_Cls` and
`Viewport_Cls`. The set follows the pixel style of the JIC Smart Factory guide's IKONY pages.

## The rules

- **Every icon is a pixel icon from the one set**: no icon font, no third-party set (and so no licence to carry), no
  stroked vector icon, and no icon drawn in place. A card head uses `Card_Head_Cls(name, title)`, a dialog title
  `Icon_Cls.Head_Layout(name)`, anything else `Icon_Cls(name, cell, colour)`. If the set lacks an icon, design it on
  the same grid and add it to the set (below). AnyScan's README architecture diagram reads the same set, so the
  figure and the app cannot drift.
- **A 12 × 12 grid**, read row by row: `#` is a cell every drawing fills, `.` is empty, and a digit `d` is an
  animation cell (below).
- **Integer scaling only.** A cell is a whole number of logical pixels on a whole-pixel origin, never antialiased
  (`QPainter.Antialiasing` off, `fillRect` with integers). At DPR 2 each cell is then a whole square of device pixels,
  so an icon renders in exactly two colours, its ground and its ink, at 1x and at 2x. The cell sizes in use are:

  | Where | Cell | Size |
  |---|---|---|
  | Pill (model set) | 1 px | 12 px, in the pill's grey `CONST_INK_MUTE` |
  | Card head, dialog title | 2 px | 24 px beside the 15.5 pt title, a 2 px top margin (`Icon_Cls.CONST_HEAD_DROP`) that drops it 1 px below centred |
  | State marker | 2 px | white on purple, animated |
  | Busy overlay | 5 px | purple on grey-lilac, animated |

  Never use a fractional cell such as 1.5 px, and never scale an icon pixmap.
- **One colour**: the brand purple `#640ABA` (`CONST_INK`), white on a purple block, or a pill's grey when the pill's
  words are grey. An icon never carries a state colour; a state is a swatch, not an icon.
- **The widget is the whole 12-cell square**, whatever the ink's extent, so every head aligns alike.

## The set (18 icons)

```
area           badge          camera         catalogue      checklist      focus
###.####.###   .....##.....   ............   ............   ............   ###......###
#..........#   ...##..##...   ...####.....   ####....####   ..#.........   #..........#
#..........#   .##......##.   .##########.   #...#..#...#   .#..........   #..........#
...######...   .#........#.   .#........#.   #....##....#   #.#..######.   ............
...######...   .#.....#..#.   .#...##...#.   #....#.....#   ............   ....####....
#..######..#   .#....#...#.   .#..#11#..#.   #....#.....#   ............   ....#..#....
#..######..#   .#.#.#....#.   .#..#11#..#.   #....#.....#   ..#.........   ....#..#....
...######...   .#..#.....#.   .#...##...#.   #....#.....#   .#..........   ....####....
...######...   ..#......#..   .#........#.   #....#.....#   #.#..######.   ............
#..........#   ...#....#...   .##########.   ####.#.####.   ............   #..........#
#..........#   ....#..#....   ............   ....###.....   ............   #..........#
###.####.###   .....##.....   ............   ............   ............   ###......###

folder         gauge          gear           image          log            magnifier
............   ............   .....##.....   ............   ............   ............
####........   ...######...   ..#.####.#..   ############   ###.#######.   ..####......
#...#.......   ..#......#..   .##########.   #..........#   ............   .#....#.....
#....######.   .#........#.   ..###..###..   #.##.......#   ###.#####...   #.1....#....
#..........#   #.......#..#   .##......##.   #.##.......#   ............   #..2...#....
#..........#   #......#...#   ###......###   #.......#..#   ###.########   #...3..#....
#..........#   #.....#....#   ###......###   #......###.#   ............   #......#....
#..........#   #....##....#   .##......##.   #..#..#####.   ###.######..   .#....#.....
#..........#   #....##....#   ..###..###..   #.##########   ............   ..####.#....
############   ############   .##########.   ############   ###.####....   ........#...
............   ............   ..#.####.#..   ............   ............   .........#..
............   ............   .....##.....   ............   ............   ..........#.

model          ruler          station        target         text           window
.....#......   ............   ............   .....#......   ............   ............
...##.##....   ............   .######.....   ...#####....   ##########..   ############
.##.....##..   ............   .#....#.....   ..#..#..#...   ............   #..........#
#.##...##.#.   ############   .#...####...   .#...#...#..   ##########..   #.#.#......#
#...###...#.   #.#.#.#.#.##   .#...#..#...   .#..###..#..   ............   ############
#....#....#.   #.#...#....#   .#...####...   ######.#####   ##########..   #..........#
#....#....#.   #..........#   .#....##....   .#..###..#..   ............   #..........#
#....#....#.   ############   .#..........   .#...#...#..   ######......   #..........#
#....#....#.   ............   .#..........   ..#..#..#...   ............   #..........#
.##..#..##..   ............   .#..........   ...#####....   ###.........   #..........#
...##.##....   ............   ############   .....#......   ............   ############
.....#......   ............   ............   ............   ............   ............
```

AnyScan's meanings: `camera` is the live camera view, `image` a stored frame, `text` a reading or description,
`magnifier` finding objects (and analysing, animated), `gauge` confidence, `folder` records, `log` a session log,
`gear` mode or configuration, `model` a model set, `ruler` measurement, `target` a reference point, `area` an
inspection area, `catalogue` a catalogue of parts, `station` a station, `window` the desktop app, `focus` focusing,
`checklist` checks, and `badge` a verdict.

## Animation

`CONST_BUSY_STEPS = {'camera': (2, 5), 'magnifier': (4, 3)}` gives the steps per cycle and ticks per step, with ticks
of `Style.CONST_BUSY_TICK_MS` = 120 ms. A digit cell `d` is lit on step `d − 1` and drawn at
`CONST_BUSY_DIM_ALPHA` (18 %) otherwise. The camera's 2 × 2 lens blinks over 600 ms per state; the magnifier's glint
crosses its lens in three cells. A still drawing (`Icon_Cells`) leaves digit cells empty. `Busy_Cells` counts cells
from the icon's ink, so an animated icon centres on its ink rather than its grid. The timer runs only while the
animation shows.

## Designing and adding an icon so it stays in the family

1. **Start from a meaning, not a picture**, and check the set first. Reuse an icon whose meaning fits before drawing a
   new one. AnyScan's `log` is lines with a short stamp before each, so it is told apart from `text`.
2. **Draw on the 12 × 12 grid** in the same vocabulary:
   - Strokes are **one cell** wide. Solid areas (`area`'s centre, `camera`'s body edge, a gauge's base) are used
     sparingly, for one emphasis per icon.
   - Ink spans about 10–12 cells on its long axis; leave empty rows or columns rather than shrinking it.
   - Use only orthogonal lines and 45° diagonals made of single cells (as in `magnifier`, `badge` and `model`).
     There are no curves other than stepped ones (`gear`, `gauge`) and no isolated single-cell noise, except as a
     deliberate detail such as `window`'s title-bar dots.
   - Use square corners, as everywhere in the brand.
   - Prefer open outlines with one interior detail over filled silhouettes; the set reads as line drawings.
3. **Check it at 1 px cells** (12 px). It must still read at pill size. Render a contact sheet with the whole family:

   `python scripts/icon_sheet.py <project_dir> sheet.png`

   Then look at it beside its neighbours: equal visual weight, equal margins, the same stroke.
4. **Add it** to `CONST_PIXEL_ICONS` with a comment saying where it is used and why the set lacked it. If it animates,
   mark its animation cells with digits and add its `(steps, ticks_per_step)` to `CONST_BUSY_STEPS`.
5. **Test it.** `tests/test_style.py::test_every_icon_is_a_twelve_grid_drawn_in_two_colours` is parametrised over the
   set, so a new icon is checked at 1x and DPR 2 automatically. In AnyScan, a figure that draws the set must be
   regenerated, not hand-edited.

## Patterns that are not icons

The funding band's motif (`Motif_Cells`) and the empty view's corner cluster (`Corner_Cells`, `CONST_POSTER_CORNER`)
are **patterns**: decoration, no meaning, and never in a data area. A state's swatch (`Swatch_Icon`) is a **marker**
of a colour, not an icon. The analysis grid (`Grid_Shape`, `Wave_Diagonals`) is decoration over a frame. See
`layout-components.md` for their exact parameters.
