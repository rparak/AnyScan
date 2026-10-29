# Crisp rendering: vectors at paint time, grid-fitting at 1x, whole-pixel cells

Sources: `templates/JIC_SF_UI/Grid_Fit.py` (a copy of AnyScan's `src/UI/Utilities/Grid_Fit.py`, Qt-free) and
`Widgets.Svg_Renderer_For`, `Svg_Image_Cls` and `Logo_Lockup_Cls`. The reasoning is in AnyScan's design decisions
*Logos are rendered as vectors at paint time* and *The header logos are grid-fitted on a 1x display*.

## 1. Every logo is an SVG, rendered as vectors at paint time

- Render with a `QSvgRenderer` into the widget's own painter in `paintEvent` (`Svg_Image_Cls`). Never draw a logo
  from a `QPixmap`, scaled or not. A pixmap rendered at the application's ratio and drawn on a screen of another
  ratio gets rescaled by Qt. A 256 px raster scaled to 210 px measured 0.818 of its ink at full contrast, against
  0.894 as vectors.
- Read the aspect from `viewBoxF()`. `defaultSize()` truncates to whole units (609.8 → 609, which squeezed AnyScan's
  logo by 0.13 %).
- A pixmap of a logo is rendered only to **measure** its ink (`Render()` → `Style.Ink_Insets`), never to draw it.
- A logo supplied only as a raster is traced to a solid SVG, compared with its source by overlay (IoU ≥ 0.98, every
  differing pixel on an edge), and its file says it is traced, so the official file can replace it.

## 2. Grid-fitting a mark at DPR 1 (`Grid_Fit.Fit_Svg`)

An SVG drawn at an arbitrary scale puts its edges between pixels, where they are drawn half-covered and look soft.
No single scale puts an irregular set of edges on whole pixels: the best heights near the header put 50 % of
AnyScan's mark edges within 0.1 px, against 23 % at the height it actually uses. So the **mark's straight edges are
moved to whole device pixels at the exact drawn height**, once, and the result is rendered as vectors.

```python
fitted_svg = Fit_Svg(svg_text, scale=drawn_height / viewbox_height, mark_right=MARK_RIGHT, thin_px=THIN)
```

- **What is fitted:** `rect`, `polygon` and `path` elements made only of straight segments (M, L, H, V, Z, absolute
  or relative, under translated groups), lying wholly left of `mark_right` (viewBox units), filled or stroked.
- **What is left as delivered:** curves (lettering) and anything reaching right of `mark_right`. Set `mark_right` to
  just past the mark's last edge and before the lettering starts (AnyScan: ink ends at 140.0 and the wordmark starts
  at 165.5, so 152; JIC: bars end at 449.44 and lettering starts at 516, so 452). A traced logo (all curves) uses
  `mark_right = 0`, which fits nothing.
- **Filled edges** share one map per axis across the mark, so an edge two shapes share stays shared. The lowest edge
  goes to its nearest pixel; across a gap narrower than `thin_px` on screen the far edge keeps the gap's rounded
  width, so equal strokes stay equal (the J-I-C bars: each 6 px at 33 px, feet level); across a wider gap an edge
  goes to its own nearest pixel, so no error carries far.
- **`thin_px`:** use 10 px (`CONST_THIN_PX`) for a mark of a few wide strokes, such as the JIC bars. Use **0** (every
  edge to its own nearest pixel) for a mark of many thin gaps or for a small window icon (16–32 px). Chaining rounded
  widths across many gaps ran AnyScan's mark to 71 × 69 px at 69 px; with 0 it stays 69 × 69, with every edge within
  0.5 px, at the cost of one 5 px bar beside two of 6.
- **Stroked shapes** get a whole-pixel stroke (at least 1) and a centre line placed so both of its edges land on
  pixels.
- **Only at DPR 1.** `Svg_Renderer_For` returns the delivered SVG on any other ratio. At DPR 2 the edges are fine as
  delivered, and fitting would move them for nothing. Fitting runs once per drawn height, and the result is cached.
- The caller renders the fitted SVG **at exactly the scale it was fitted for**, with the viewBox origin on a whole
  device pixel. Never place a logo widget at a fractional position.
- Measured result: AnyScan's mark at 69 px went from 0.68 of its ink fully covered and 0.33 partial to 1.00 and 0.00;
  the J-I-C bars at 33 px went from 0.72/0.28 to 1.00/0.00.

## 3. The lockup's tagline as live text

Small outlined text cannot be grid-fitted, because it is curves. Set it as live Public Sans at the outlines' position
and size (`Logo_Lockup_Cls`; see `layout-components.md` § 2), so the platform rasteriser hints it, and grow the lockup
on a 1x display until the tagline is 9 pt (`Style.Logo_Height`).

## 4. Whole-pixel drawing everywhere else

- **Pixel icons and motifs:** integer cells, antialiasing off (`pixel-icons.md`).
- **Chart markers:** `Charts.Marker_Rect` snaps a 7 px square to whole pixels round the pixel its centre falls in,
  and is drawn unantialiased. Lines stay antialiased.
- **The inspection area, the analysis grid's lines and hairlines** are 1 px on whole pixels, unantialiased.
- **Swatches** are drawn at 2x into a pixmap tagged with its ratio.
- **Layouts:** keep sizes integral, and measure gaps from ink (`Ink_Insets`) rather than from image boxes.

## 5. Checking it

- Render each logo widget offscreen at DPR 1 and DPR 2 (`QT_SCALE_FACTOR=2`) and compare it with a direct
  `QSvgRenderer` render of the same file at the same device size. At DPR 2 they must be identical. At DPR 1 the
  mark's ink must have no half-covered pixel: count the pixels whose alpha is strictly between 0 and 255 inside the
  mark's columns.
- Hold every fitted edge within 0.5 px of the delivered edge and the mark's bounding box square, by parsing
  `Fit_Svg`'s output.
- Look at the 1x screenshot. A soft logo is obvious by eye and invisible to a region-average test.
