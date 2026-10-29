---
name: jic-sf-ui-style
description: >-
  The JIC Smart Factory visual style for PyQt5 desktop applications, taken from AnyScan. It covers
  the palette as theme tokens (one purple #640ABA, OK/NOK/Warning state colours, measured
  contrasts), Public Sans typography, square cards with pixel-icon heads, badges, pills, action
  buttons, the status strip, LIVE PREVIEW / SCANNING… / ANALYZING… markers, the busy overlay and
  analysis grid, the funding band with the EDIH-DIGIMAT / Ministry / EU logos and disclaimer,
  grid-fitted SVG logos, Trends-style charts, image annotation and operator wording. It includes a
  drop-in package, a runnable example app, tests and the fonts and logos. Use this skill whenever
  you build, extend, restyle or review a PyQt (or Qt) desktop UI for JIC, JIC Smart Factory,
  EDIH-DIGIMAT, AnyScan or a sibling station or inspection console, or add any widget, view, chart,
  icon, colour, logo, annotation or wording to AnyScan, even if the request does not mention
  "style".
---

# JIC Smart Factory UI style (PyQt5)

This style is AnyScan's: a white page, purple words in Public Sans, thin grey-lilac rules, **square** corners,
pixel-grid icons, and a purple funding band at the foot. Every colour is a measured token. Every state has one colour
in every view, and every mark is crisp at 1x and at DPR 2. The skill gives you the rules (here), the reasoning and
exact values (`references/`), working code (`templates/`), the fonts and logos (`assets/`) and tools (`scripts/`).

**Read the sources, not memory.** The style was taken from AnyScan. Where AnyScan's code is at hand and disagrees with
this skill, read the code, then correct the skill; elsewhere, this skill and the project's reference are the sources.

## 0. Find the project reference first

`<repo>/.claude/skills/jic-sf-ui-style/references/project.md` holds the project's bindings of this style: which of
its modules does each job (tokens, fonts, widgets, icons, charts, image marks, wording), its views, its state colours
and overlays, its exceptions, and the tests that hold each rule. **It overrides this skill** where they differ. The
repository folder holds no `SKILL.md` (a personal skill wins over a project skill of the same name, so a copy there
would be ignored).

Start the reply with `Mode: new project`, `Mode: bootstrap` or `Mode: maintenance` and the reason:

- **New project** (no UI code yet): mode A below; after the first real views exist, write the project reference.
- **Bootstrap** (UI code in this style, no `project.md`): survey read-only - the theme module, the style module, the
  widgets, icons, charts, image marks and wording, the UI tests - then propose `project.md` from
  [assets/project_reference_template.md](assets/project_reference_template.md) and **wait for approval**.
- **Maintenance**: mode B below, with the project reference.

## Pick the mode

### A. A new PyQt5 project

1. Make an environment, then scaffold. The scaffold copies the package, its fonts and logos, the example app, the
   annotation demo and the style tests, and it refuses to overwrite an existing `JIC_SF_UI/`.
   ```bash
   cd <project_dir>
   <explicit python, 3.10 or newer> -m venv .venv && . .venv/bin/activate
   pip install "PyQt5>=5.15" numpy pytest opencv-python-headless   # OpenCV only for Annotate
   python <this skill>/scripts/scaffold.py .
   ```
   The result: `JIC_SF_UI/` (Theme, Style, Qss, Pixel_Motif, Grid_Fit, Widgets, Charts, Annotate, `assets/`),
   `example_app.py`, `annotate_demo.py` and `tests/`.
2. Run the example and look at it. Run `python example_app.py`, or shoot it offscreen at both densities:
   ```bash
   S=<this skill>/scripts/shoot_both_densities.py
   python $S shots/live   -- python example_app.py --view live
   python $S shots/trends -- python example_app.py --view trends
   python $S shots/grid   -- python example_app.py --demo-frame --state analysis   # the analysis grid over a frame
   python annotate_demo.py shots/annotate.png                                      # every image mark
   ```
   `--size` is a request: the layout's minimum height wins (1600 × 1000 comes out 1600 × 1029 at 1x, as AnyScan's
   own window does), so compare screenshots taken at the same request.
3. Replace the product constants at the top of `example_app.py` (lockup file, mark, tagline origin and size,
   `mark_right`, name). **AnyScan's logo is only an example and never ships in another product.** Measure the new
   logo's tagline origin and size from its outlines (`references/layout-components.md` § 2).
4. Build the real views from the widgets. Keep the window skeleton: header, a stacked central area, the status strip,
   the funding band.
5. Run the tests (`QT_QPA_PLATFORM=offscreen python -m pytest tests -q`), which re-run themselves at DPR 2, and
   `python <this skill>/scripts/check_tokens.py <project_dir>`. Then **look** at both
   screenshots.

The brand-independent UI rules (theme tokens only, contrast floors, the density check, pixel-measured tests, Qt quirks)
are in project-style-rpx `references/ui.md`; read it with this skill. If the project follows the RP conventions, the
rest of `project-style-rpx` applies too. The templates already use its naming (`_Cls`, `CONST_*`, `Pascal_Snake_Case`,
numbered docstrings).

### B. Extending a project in this style

Do **not** copy the templates into a project that already has its own modules (AnyScan's are the originals the
templates were generalised from). Use the modules its project reference names for each job, and follow its bindings.
A visible change follows the `feature-manager` skill: a design-decision entry, tests that were broken once, and a
look at the render.

## The rules

These are the rules that make a window look like this family. The why, the measurements and the exact values are in
the reference named after each group.

**Colour** (`references/palette.md`)
- Every colour is a token in the Qt-free `Theme`, never a value in UI code: project-style-rpx `references/ui.md`.
- **One purple, `#640ABA`**, for all text, titles, icons, outlines, the selected segment, the band and the OK state.
  No darker or lighter shade exists. Secondary text is the same purple, and hierarchy comes from size and weight.
  The muted ink `#6F5783` is for labels, captions, empty states and timestamps.
- Surfaces: white page and cards, `#E1DCE6` grey-lilac for rules, hover fill and the image view's ground, `#C2C9FF`
  periwinkle for the pressed fill and the scroll handle.
- **Three states, one colour each in every view**: OK `#640ABA`, NOK `#FF6540`, Warning `#FFC226`. The same colour
  is used for the image mark, the chip, the chart series, the legend, the filter swatch and the outline. No darker
  chart variant exists. A Warning's kind is told in words, never in colour.
- Status colours have a dot twin and a text twin (`Status_Text_Color`). The contrast floors are project-style-rpx
  `references/ui.md`'s; this brand's recorded exceptions are white numerals on the NOK and Warning chips.
- Green `#3DBE4C` is system health only and never marks an object. The log's ERROR `#BE0362` is never the NOK
  colour.

**Type** (`references/typography.md`)
- Public Sans for words and JetBrains Mono for machine values, both bundled as static 400/500/600/700 files with
  their OFL licences, registered by `Style.Load_Fonts()`; every font is built through `Style.Font` (startup order and
  the type floor: project-style-rpx `references/ui.md`).
- GT America and GT Super Display are commercial and never bundled. Newsreader stands in for GT Super Display only
  in printed or marketing display headlines, never in the app.
- Content takes named steps of `CONST_TYPE_SCALE`. Chrome takes the per-widget sizes in the typography table:
  card title 15.5 Bold −2 %, buttons 9.5 DemiBold +6 % UPPERCASE, tabs 9 DemiBold, captions 8 Bold +7 % UPPERCASE.

**Shape and layout** (`references/layout-components.md`)
- **Square corners everywhere.** No radius exists. Borders are 1 px (2 px for the primary button and a selected
  outline).
- Window: margins 18 · 0 · 18 · 18. Header, then a stacked central area (only it changes with the tabs), then the
  status strip, then the funding band, with 16 px gaps everywhere.
- Header: product lockup, a 32 px gap measured from ink, a 34 px grey-lilac rule, 32 px, the JIC Smart Factory
  logo, tabs centred, status pills at the right.
- Cards: white, 1 px grey-lilac, 16 px padding. A head is a 24 px pixel icon (2 px cells), a 15.5 pt Bold purple
  title, and a badge or badge row at the right.
- Container backgrounds use an id selector (project-style-rpx `references/ui.md` § *Qt quirks*).

**Components** (`references/layout-components.md`)
- Badges are 24 px, 8 pt Bold, purple words on the state's ground (periwinkle, `#FFD9D0`, amber). The words carry the
  state (`NOK · 2`, `Warning · 1`, `All OK`). Show one badge per state that needs the person, wrapping rather than
  clipping.
- Action buttons are 48 px, outlined in purple, with **one primary per row**. Every state rule names fill, border and
  label (`Qss.py`; why: project-style-rpx `references/ui.md`). A disabled control signals through its fill and outline
  and has a tooltip saying what enables it.
- There is one segmented control for every tab, toggle or filter: 30 px, shared 1 px rules, the checked segment
  purple under white.
- Status pills are 31 px and differ on dot, colour and outline at once (●/◐/○, green/amber/grey, solid/dashed).
- Status strip: hairline-divided cells, UPPERCASE captions, counts 18 pt Bold, states with a dot, machine values in
  mono. Widths are reserved so nothing shifts. Derived figures name their scope (`Inference (run median)`).
- An image view's state is named **in its card head**, never inside the image: a purple block with white words,
  `●  LIVE PREVIEW`, `SCANNING…` (blinking camera) or `ANALYZING…` (magnifier glint), one fixed size.
- Busy overlay: the view's grey-lilac at 70 %, a 5 px-cell pixel icon and the step in purple. It is used only for
  steps that are not over a frame being judged. Analysis grid: 48 square cells, periwinkle lines at 55 %, `#CC9EF1`
  at 30 %, a diagonal wave of about 1 s. It is decoration, identical over any frame, and stops at once.
- Empty view: the product mark, an instruction naming the next step, and the poster's 6 × 4 pixel cluster in the
  top-right corner (purple at 7 and 12 %). Brand squares appear only there and in the funding band, never in a data
  area.
- Funding band: 90 px of purple, a centred group of white logos (EDIH-DIGIMAT 24 px, a rule at 20 %, the Ministry
  46 px, the EU 46 px), a white pixel motif at the ends, nothing within 28 px of a logo. The **EU disclaimer** is
  kept word for word in one constant and carried by the README and any printed or generated band, not by the
  window's band.

**Icons and crispness** (`references/pixel-icons.md`, `references/grid-fit.md`)
- Every icon is a 12 × 12 pixel icon from the **one set** (`CONST_PIXEL_ICONS`), drawn in whole-pixel cells (1, 2
  or 5 px) unantialiased and in one colour. A missing icon is designed on the same grid and added to the set, never
  drawn in place or taken from an icon font.
- Every logo is an SVG rendered as vectors at paint time, never a scaled pixmap. At DPR 1 its mark's straight edges
  are grid-fitted to whole pixels (`Fit_Svg`) and its small tagline is live text.

**Charts** (`references/charts.md`)
- Charts are hand-drawn on one base. Every series is a **2 px line** with a **7 px square marker**. A derived series
  is **dashed with hollow squares**, drawn on top. State series use the state colours, a total the muted ink, and
  neutral series `#655E6D` (dark) and `#9890A0` (light).
- **Threshold guides are 1 px, dashed, neutral grey and labelled** ("Warning below 80 %"). Chart text is the neutral
  grey. The legend is line samples above the plot. Ticks fall on nice numbers, and missing values break the line.

**Annotation** (`references/annotation.md`)
- One Qt-free renderer. A box is drawn in its state's colour, unshifted. A chip is filled with that colour and carries
  a plain white numeral, with no halo or rim. A measured part has a solid rotated outline (its size check's colour)
  inside a dashed half-weight outer box (its verdict). Features are thinner boxes in their own check's colour, solid
  when found and dashed when missing, with chips placed by the nearest-corner rule. A Warning has no feature marks.
  The inspection area is 1 px light amber, drawn on screen only.

**Wording** (`references/wording.md`)
- `State: OK.` / `State: NOK.` / `State: Warning – Outside area.`, then one `Reason:` sentence that, for a Warning,
  ends in the operator's action. Names are "kind – detail" with an en dash (`Catalogue inspection – Mounting plate`).
- Empty states are instructions. Errors are actionable sentences naming the button. `—` appears only in an empty
  value slot.

**Testing** (`references/testing.md`)
- The method (pixels at 2x, the token scan, the DPR 2 re-run, looking at the render) is project-style-rpx
  `references/ui.md`. This brand adds the radius scan, two-colour icons at 1x and DPR 2, and the template's tests.

## Doing a UI change in this style

1. Find the component that already does it (`templates/JIC_SF_UI/Widgets.py`, or the module the project reference names). Reuse it before
   writing a new one, and extend it before forking it.
2. Any new colour, size or icon is a token, constant or set entry with a comment saying its role. Measure contrast
   with `scripts/contrast.py`.
3. Words follow `references/wording.md`.
4. Add or extend a test (pixels, not stylesheets), break it once, and restore.
5. Screenshot at DPR 1 and 2 (`scripts/shoot_both_densities.py`) and look. Compare with AnyScan's window for
   colours, fonts, icons, spacing and chart style.
6. Report what you verified and how, and what you did not.

## Files

- `references/palette.md`: every token with its hex, role and contrast; the one-purple and state rules; the status,
  neutral and chart greys; overlays; log levels; how to add a colour.
- `references/typography.md`: the faces and licences, Newsreader and GT, the content scale and the chrome size table,
  punctuation.
- `references/layout-components.md`: window, header, cards, badges, buttons and their states, segments, status strip,
  state markers, empty view, busy overlay, analysis grid, inspection area, funding band and disclaimer.
- `references/pixel-icons.md`: the 18 grids, cell sizes, animation, and how to design and add an icon.
- `references/grid-fit.md`: vectors at paint time, `Fit_Svg`, `mark_right` and `thin_px`, whole-pixel drawing, checks.
- `references/charts.md`: series, markers, derived series, guides, legend, ticks, hover, data discipline.
- `references/annotation.md`: objects, chips, outlines, features, nearest-corner placement, inspection area, mask.
- `references/wording.md`: state lines, reasons, "kind – detail", badges, pills, empty states, errors, buttons.
- `references/testing.md`: pixel contrast, token and radius scans, DPR 2 re-runs, mutation checks, screenshots.
- `templates/JIC_SF_UI/`: `Theme.py` (Qt-free tokens and colour maths), `Style.py`, `Qss.py` (the stylesheet
  builder), `Pixel_Motif.py`, `Grid_Fit.py` (both Qt-free), `Widgets.py`, `Charts.py`, `Annotate.py` (Qt-free).
- `templates/example_app.py`: header, Live page (two cards, badge row, state lines, meta rows), Trends page (two
  charts), status strip, band; `--view`, `--state`, `--demo-frame`, `--screenshot`, `--size`.
- `templates/annotate_demo.py`: every image mark on a synthetic frame and its label mask (needs OpenCV); run
  `python annotate_demo.py out.png` in the scaffolded project.
- `templates/tests/`: `conftest.py` and `test_style.py`.
- `scripts/scaffold.py`, `scripts/shoot_both_densities.py`, `scripts/check_tokens.py`, `scripts/contrast.py`,
  `scripts/icon_sheet.py`.
- `assets/fonts/` (Public Sans, JetBrains Mono, their OFL texts, `README.md`); `assets/logos/` (the JIC Smart
  Factory, EDIH-DIGIMAT, Ministry and EU logos, AnyScan's logo as an example only, `USAGE.md`);
  `assets/project_reference_template.md` (a project's bindings, section 0).

## Out of scope

- The monochrome Deep-Tech house style (dark and light, PyQt6, web, charts, documents) is the separate skill
  deep-tech-ui-style. A product uses one of the two looks, never both.

- AnyScan's vision, catalogue and camera logic (detection, classification, measurement, capture, workers). The
  templates keep only how results look.
- AnyScan's History and Log views as whole widgets. Their visual rules (filter swatches, set outlines, log columns,
  severity weights) are in the references, and the views are in AnyScan to read.
- The heatmap legend and cividis map, which are AnyScan-specific diagnostics. The rule is in `annotation.md`.
- PyQt6 or Qt 6. The values hold, but Qt 6 draws fractional font sizes and has other high-DPI defaults, so re-measure
  the lockup and the type floor there.
