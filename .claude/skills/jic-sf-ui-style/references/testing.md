# Testing the style

Template: `templates/tests/test_style.py` (with `conftest.py`), modelled on AnyScan's `test/UI/test_colour_tokens.py`,
`test_control_contrast.py`, `test_text_contrast.py`, `test_pixel_icons.py`, `test_square_corners.py`,
`test_fonts.py`, `test_header.py` and `test_logo_rendering.py`. Run it with
`QT_QPA_PLATFORM=offscreen python -m pytest tests -q`.

## 1. Measure pixels, not stylesheets

The method (render at 2x, drive states through real events, disabled states, text against its ground): project-style-rpx
`references/ui.md` § *Tests of a UI*. The template's versions are `test_every_button_state_clears_four_and_a_half`,
`test_a_hovered_selected_segment_keeps_its_white_label` and `_Hover` in `templates/tests/test_style.py`.

## 2. Hold the palette in tests

- Every pair in `palette.md` is a case of `test_every_pair_clears_its_floor` (project-style-rpx `references/ui.md` §
  *Contrast floors, measured*).
- One purple: no second high-chroma colour within a few degrees of the purple's hue exists among the tokens.
- One colour per state: the image renderer, the charts, the legend and the filters all call `Verdict_Color`, and a
  test asserts each uses that colour for each state.
- Colour relationships are tests: project-style-rpx `references/ui.md` § *Contrast floors, measured*.

## 3. Scan the source

- **No colour by value** outside `Theme.py` (`test_no_colour_is_named_outside_the_theme`, `scripts/check_tokens.py`):
  project-style-rpx `references/ui.md` § *Colour comes from the theme*.
- **No rounded corner**: flag `border-radius`, `drawRoundedRect`, `addRoundedRect`. Removing radii rather than
  zeroing them leaves nothing to re-round.
- **Fonts**: `QFontInfo(Style.Font(10)).family()` is `Public Sans`, and the mono font is `JetBrains Mono`. Every
  requested weight must have its own face: the test reads the weights used in the source and fails on a fifth one.

## 4. Crispness and DPR 2

The template covers the pixel icons, the fonts and the DPR 2 re-run. The logo-identity, half-covered-pixel and
type-floor checks below exist in AnyScan (`test/UI/test_logo_rendering.py`, `test_header.py`,
`test_text_contrast.py`). Write them for a project once it has its own logo and window; read AnyScan's as the model.

- **Pixel icons**: render each icon at 1x and DPR 2 on white and assert the image holds **exactly two colours**
  (white and `#640ABA`): no antialiased edge and no fractional cell. Parametrise over the whole set so a new icon is
  covered automatically.
- **Logos**: compare each logo widget's render with a direct `QSvgRenderer` render at the same device size; they must
  be identical at DPR 2. At DPR 1 the grid-fitted mark must have no half-covered pixel.
- The type-floor check and the DPR 2 re-run of a test module: project-style-rpx `references/ui.md` § *Tests of a UI*.

## 5. Break every test once (mutation checks)

Break every new style test once (project-style-rpx `references/python.md` > Tests). The template's checks, each
confirmed to fail (2026-10-23):

| Mutation | Test that must fail |
|---|---|
| Plain button hover label set to white on the grey-lilac fill | `test_every_button_state_clears_four_and_a_half` (3 cases) |
| Segment hover rule left unscoped and fill-only (`QPushButton:hover:enabled { background: … }`, AnyScan's original bug) | `test_a_hovered_selected_segment_keeps_its_white_label` |
| Icon cells antialiased and offset by half a pixel | `test_every_icon_is_a_twelve_grid_drawn_in_two_colours` (18 cases) |
| A hex colour written in a widget's stylesheet | `test_no_colour_is_named_outside_the_theme` |
| `CONST_INK_MUTE` lightened to `#9A8AA8` | `test_every_pair_clears_its_floor` (2 cases) |
| A `border-radius` added to the badge | `test_no_corner_is_rounded` |
| Fonts not registered | `test_the_bundled_faces_are_used` |

## 6. Look at the render

Why and what to look for: project-style-rpx `references/ui.md` § *Look at the render*. Here: `python
scripts/shoot_both_densities.py out/shot -- python app.py [args]` grabs the window at DPR 1 and DPR 2 (the app takes
`--screenshot`); compare with AnyScan's window for colours, fonts, icons, spacing and chart style.
