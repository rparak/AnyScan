# Charts

Source: `templates/JIC_SF_UI/Charts.py` (`Line_Chart_Cls`, `Series_Str`, `Guide_Str`, `Chart_Card`, `Draw_Marker`,
`Nice_Ticks`, `Thin_Label_Indices`), generalised from AnyScan's Trends view (`src/UI/Views/Trends.py`) and its
Qt-free maths (`src/Reporting/Trends.py`). The reasoning is in AnyScan's design decisions *Trends draws square
markers, 2 px lines, and the run mean as hollow squares on top*, *The Confidence chart draws the two means, told
apart by their form* and *Each state has one colour in every view*.

Charts are hand-drawn with QPainter on one chart base. Do not use a chart library: its defaults (round markers, its
own palette, rounded legends, anti-aliased markers) break most of the rules below.

**Scope.** These rules are for charts inside a JIC Smart Factory Qt window. A data figure made with matplotlib for a
report, a paper or a README follows project-style-rpx `references/figures.md` (one style module, two themes, a
colour-blind-safe categorical palette, PNG and SVG): this page gives no categorical palette and no matplotlib style. In
such a figure the brand purple may be one series colour where it meets the contrast floor on the background; on a dark
background that usually means a lighter tint of it, recorded in the project reference.

## The rules

| Element | Rule |
|---|---|
| Series line | **2 px** (`CONST_SERIES_LINE_W`), solid, flat caps, antialiased; the same width for every series in a view |
| Marker | A **7 px SQUARE** (`CONST_SERIES_MARKER_PX`) at every point, on whole pixels, unantialiased, filled in the series' colour to its edge, with **no darker edge** |
| Derived series (running mean, smoothed, predicted) | **Dashed**: 6 px dash, 4 px gap (`CONST_DERIVED_DASH` [3, 2] line widths). **Hollow squares**: a 2 px ring round a transparent inside, with its own line clipped out of the squares (`Outside_Markers`) so the inside shows the card. **Drawn on top**: where it equals its source, each point reads as a dark square inside a light outline |
| Markers on dense data | Drawn only while points are at least 10 px apart; the hover still reads each point |
| State series | Exactly the state's colour, `Theme.Verdict_Color(state)[0]`: OK `#640ABA`, NOK `#FF6540`, Warning `#FFC226`. **One colour per state across all views**, the same as its image mark, legend sample, filter swatch and set outline. A light state reads on white through the 2 px line and the square, never through a darker variant |
| A total / sum | `CONST_INK_MUTE` `#6F5783` (OK already uses the purple) |
| Neutral series (no state) | The dark neutral `CONST_DETECTION_INK` `#655E6D` (6.22:1) and the light neutral `CONST_CHART_LIGHT_INK` `#9890A0` (3.07:1, the light one for a derived series). They are told apart by **pattern, colour and fill**, not width. A neutral chart **draws no state colour** |
| Threshold guides | **1 px**, dashed, in the neutral grey `#655E6D`, never a state colour nor the log's error red. The milder threshold gets a long dash (6, 4); the severe one a short dash (2, 3) (`CONST_GUIDE_DASH_LONG` / `_SHORT`). Each is **labelled** above its right end with what it means, from the values in force: `Warning below 80 %`, `Error below 60 %` |
| Guides vs data | Guides are drawn first, behind the series. The short (2, 3) dash reads as dotted at 1 px; that is the intended contrast with the long dash. A guide's label sits above the right end of its line and **can be crossed by a series** running near the threshold there (AnyScan draws it the same way). If that matters for a project's data, move the label left of the last point, and record the change |
| Chart text | Axis titles (10.5 pt), legend labels, guide labels and hover secondaries (9.5 pt) are the **neutral grey** `#655E6D`: next to data the purple would read as OK. Tick labels (9.5 pt) are `CONST_INK_MUTE`. The hover's first line (the point's index) is the purple |
| Gridlines | 1 px `CONST_LINE` at each y tick; the x base line and tick marks (4 px) in `CONST_CARD_BORDER` |
| Ticks | y on "nice" steps (1, 2 or 5 × 10ⁿ, `Nice_Ticks`), with the axis ending **on** the top tick so no point sits above the last gridline. x labels thinned to nice multiples (`Thin_Label_Indices`): the first always, the last when it clears the previous by half a step, never overlapping (46 px each) |
| Axis titles | Always with the unit in brackets: `Confidence (%)`, `Objects (cumulative)`, `Analysed image` |
| Legend | One row **above the plot, top-right**, never on the data. Each entry is a **line sample** of its series (26 px: three dashes and two gaps of the derived dash), with its square marker in the middle and its label 5 px after; entries 14 px apart; order = series order. Never use a square swatch alone |
| Hover | A 1 px dashed grey-lilac guide at the nearest column; a square read-out box (white, 1 px grey-lilac border, 7 px padding, 15 px lines) near the plot's top, kept inside the plot. Lines: the index in purple, then each series' value in the neutral grey; `—` where a value is missing |
| Missing value | Breaks the line (`None`), never plotted as 0 |
| Margins | left 60, bottom 52, top 34 (legend room), right 18; minimum height 240 |
| Empty | Centred `No analyses in this run yet.` (11.5 pt, `CONST_INK_MUTE`) |
| Card | A chart sits in a card whose head carries a pixel icon and title, with a one-sentence subtitle in 10.5 pt `CONST_INK_MUTE` saying what is plotted (`Chart_Card`) |

## Using it

```python
from JIC_SF_UI import Theme, Style
from JIC_SF_UI.Charts import Line_Chart_Cls, Series_Str, Guide_Str, Chart_Card, CONST_GUIDE_DASH_LONG, CONST_GUIDE_DASH_SHORT

chart = Line_Chart_Cls('Analysed image', 'Objects (cumulative)', empty_text='No analyses in this run yet.')
chart.Set_Data([Series_Str('Total', Style.CONST_INK_MUTE, totals),
                Series_Str('OK', Theme.Verdict_Color('OK')[0], ok),
                Series_Str('NOK', Theme.Verdict_Color('NOK')[0], nok),
                Series_Str('Warning', Theme.Verdict_Color('Warning')[0], warning)])

confidence = Line_Chart_Cls('Analysed image', 'Confidence (%)')
confidence.Set_Data([Series_Str('Frame mean', Style.CONST_DETECTION_INK, frame_means),
                     Series_Str('Run mean', Style.CONST_CHART_LIGHT_INK, run_means, Derived=True)],
                    [Guide_Str(80, 'Warning below 80 %', CONST_GUIDE_DASH_LONG),
                     Guide_Str(60, 'Error below 60 %', CONST_GUIDE_DASH_SHORT)], y_range=(0.0, 100.0))
layout.addWidget(Chart_Card('gauge', 'Confidence', 'The mean confidence of each image and the running mean of the run.', confidence))
```

## Data discipline (from AnyScan)

- A chart and a status figure that show the same number read **one source** (one accumulator), so the last point and
  the status cell are the same number.
- A failed run never advances x; x counts successful items.
- An unscored item is in no mean (a false 0 % would draw a low point). Count it in the hover instead.
- A per-item cloud jittered within its column reached past the last column, so AnyScan removed it. Plot aggregates.

## Checking a chart

Render offscreen and assert from pixels: every series' line is 2 px wide where it is horizontal; each marker is a 7 ×
7 block of the series' colour (or a 2 px ring with the card inside); a guide is 1 px of `#655E6D`; no state colour
appears in a neutral chart; and the legend samples match their series' width and marker. Then **look** at the chart,
at 1x and DPR 2.
