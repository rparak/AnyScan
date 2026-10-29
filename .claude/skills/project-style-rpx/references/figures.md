# Figures - data figures for reports, papers and READMEs

The brand-independent rules for a figure a project generates (matplotlib or similar): how it is made,
held and checked, and the default look when no brand skill applies. 📄 = documentation only; ✅ = held
by the project's figure tests. The UI's own charts (inside a Qt window) are references/ui.md and the
brand skill's.

Who decides what:

| Question | Where |
|---|---|
| How a figure is generated, themed, checked and saved | this page |
| What a README figure shows: no title inside, caption, alt text, size budget, light/dark `<picture>` | readme-writer `references/figures.md` |
| The look in a branded project | the brand skill (the project reference names it) decides the charts inside its UI; a matplotlib figure there uses the default look below, with the brand colour as one series colour where it meets the contrast floor, unless the brand skill gives a figure look of its own |
| The project's own choices (its colours per entity, its theme backgrounds) | its project reference |

## One style module, two themes ✅

- **One style module** (`src/<Domain>/Style.py` or the project's place) defines everything: fonts,
  sizes, line widths, the palette, and a theme per background (`dark`, `light`) as data. Every figure
  script calls it; no figure sets a colour, font or size of its own.
- **Both themes come from the same drawing code**: a function draws the figure for a theme; the
  script calls it once per theme (`<name>_dark`, `<name>_light`). The dark theme is drawn for its
  background (text, axes and grid light), never an inverted light image.
- **Contrast is measured, not judged**: a test computes each series colour's contrast against each
  theme's background (WCAG ratio) and holds it at the floor the project sets (4.5:1 for text and for a
  colour that carries meaning, unless the project reference records another); an entity whose colour
  fails on one background gets a tint or shade of it there (a generic example: a dark blue that reads
  well on white but falls below the floor on a near-black background is drawn there as a lighter tint
  of the same hue).
- **A label's ink on a filled bar** is black or white by the larger contrast against the fill.

## Content 📄

- **One colour per entity in every figure** (a program, a robot, a variant): the same thing has the
  same colour, marker and name everywhere. Meaning never by colour alone: a line style, a marker, a
  hatch or a direct label carries it too.
- **Units in brackets, symbols as math**: `$t$ [s]`, `$q_2$ [rad]`, `$F$ [N]`.
- **Panel letters** (a, b, c) on multi-panel figures, referred to by the caption.
- **Key values annotated** where the text quotes them (the minimum clearance, the peak torque), so the
  reader finds the number in the figure.
- **No title inside an image that has a caption** (readme-writer); a figure for a slide may keep one.
- Names that contain characters the font lacks (an underscore in a typeset font) go through one helper
  that sets them in math roman, never by hand per label.

## The default look (no brand) 📄

When no brand skill applies, the look of a scientific paper:

- **Type**: matplotlib's own Computer Modern - `mathtext.fontset = "cm"`, serif `cmr10` with
  `axes.formatter.use_mathtext = True` - so no TeX installation and no vendored fonts are needed.
  `cmr10` has no bold face and no underscore glyph: bold through mathtext (`$\mathbf{a}$`), names
  through the helper above.
- **Palette**: Okabe-Ito (orange #E69F00, sky blue #56B4E9, bluish green #009E73, yellow #F0E442,
  blue #0072B2, vermillion #D55E00, reddish purple #CC79A7, black or white), colour-blind safe, at
  most eight categories; pick per theme the members that clear the contrast floor.
- **Themes**: `light` on white; `dark` on the background the figure is shown on (GitHub's dark page is
  `#0D1117`).

## Saving ✅

- **PNG at 300 dpi** for reports and print **and an SVG** (text as paths, so it renders without the
  fonts), unless a brand page sets another resolution. A README copy obeys readme-writer's size
  budget: reduce the figure size or dpi there, never by hand.
- **Deterministic**: the `Agg` backend, fixed seeds, no timestamp in the image or its metadata
  (`metadata={"Date": None}` for SVG, `{"Software": None}` where it varies), pinned plotting versions.
  matplotlib draws random clip-path and marker ids into an SVG; setting `rcParams["svg.hashsalt"]` to
  a fixed string should make them stable - *not yet verified in a project*: until it is, compare SVGs
  with those ids normalised and PNGs byte for byte.
- **Generated, never edited**: one script writes every figure from the project's data into `--out
  DIR`; a test regenerates them into a temporary folder and compares with the committed files.

## Look at it 📄

Open every new or changed figure in both themes at the size it is shown: labels not clipped, legend
off the data, annotated values right, the dark version legible. A passing test does not show a
misplaced label.
