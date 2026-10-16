# UI design — how the interface looks

`pyqt.md` covers how the UI code is written; this page covers how the interface looks. Each rule
states the practice, what enforces it (✅ a test, 📄 documentation only), and where the reasoning
lives in `docs/design-decisions.md` (DD). Everything here is something the code already does;
practices followed inconsistently are under **Unsettled**.

## Colour comes from the theme, never from a literal ✅

- Every colour is a token in `src/Parameters/Theme.py` — Qt-free, so the application and the vision
  renderer (the exported annotated image and label mask) share one palette. UI code reaches the
  tokens through `UI/Utilities/Style.py` and never names a colour by value: not a hex string (in a
  stylesheet or elsewhere), not a `QColor` built from numbers.
- A token at an opacity is `Style.Token_Color(token, alpha)`, with the alpha a named theme constant
  (`CONST_BUSY_SCRIM_ALPHA`) — never the token's value copied into a `QColor(r, g, b, a)`. That copy
  is how drift starts: the busy overlay once filled with `QColor(43, 36, 85, 158)`, the ink token's
  value at another opacity, which nothing would have kept in step with the ink.
- A new colour is a new token, commented with what it is for.
- The same holds outside the application: the README's architecture diagram takes every colour from
  the theme, and its type scale and font fallbacks from `Style.py`, through its generator
  (`Example/UI/architecture_diagram.py`). It is regenerated, never edited by hand
  (`test/UI/test_brand_figures.py`).
- ✅ `test/UI/test_colour_tokens.py` scans every UI module (except `Style.py`) with the Python tokenizer
  for a hex colour in a string or a numeric `QColor(`.

## A verdict colour never changes; its foreground carries legibility ✅

- The verdict colours are fixed tokens from the JIC Smart Factory palette: OK the purple `#640ABA`, NOK the
  orange-red `#FF6540` (DD *The fail marker is the JIC orange-red*), Warning the amber `#FFC226`, and Unspecified
  the sky blue `#33A3FF` (`Theme.CONST_UNSPECIFIED_BOX`, the owner's choice of 2026-10-16), a verdict colour outside
  the brand palette like NOK and Warning, with its own text twin `#0065A9` (its hue at L* 41, 6.11:1 on white), mask
  fill `#748DB1` and badge ground `#C6E4FF`: 2.39:1 on the table, its white numeral 2.68:1 (an accepted exception like
  the orange-red's and the amber's), ΔE ≥ 74 from OK, NOK and Warning, 45 from the foreign grey, 105 from the area's
  amber (DD *Unspecified is a sky blue, a verdict colour outside the brand palette*). The neutral ink `#655E6D` is no
  verdict's colour: it marks only a detect-only mode's words and dots, its derived mask pair and History's outline of
  a detect-only set. A detect-only run (Segment Anything) draws every object in one colour, the logo purple
  `#640ABA` (`CONST_DETECTION_BOX = CONST_LOGO_INK`, white numeral 9.15:1; table 1.31:1 at ΔE 121, aluminium 3.53:1,
  rust-stained metal 3.02:1, steel 2.32:1). It equals OK, the owner's ruling of 2026-10-15: that mode shows no verdict
  (DD *Every chip carries a white numeral*). One purple: no darker shade of it exists in the theme (DD
  *The palette is the JIC Smart Factory brand's*).
- A Warning has two looks on the frame, never on the mask: a catalogued part that only lies outside the
  inspection area keeps the amber, its rotated outline, dashed outer box and chip only, with no feature mark, since
  no check runs on it (DD *A part outside the inspection area is not checked*); a **foreign object** (a Warning that does not resemble the part, wherever it
  lies, cut by the border or not: `Catalogue_Result_Str.Resembles`) is drawn, outline, box and chip, in a grey of the
  brand's grey-lilac family, `Theme.CONST_FOREIGN_BOX`, with the white numeral (`Annotate.Foreign`). The colour
  follows what the object is, never only where it lies. Candidates against the table #236A56 / white / #655E6D: `#C9BFD2`
  3.63 / 1.77 / 3.52:1, `#B4A6BE` (the disabled label's token) 2.80 / 2.30 / 2.71:1, `#A396AE` 2.30 / 2.79 /
  2.23:1, the owner choosing by eye (DD *A catalogue mode judges only inside the inspection area*). The label mask
  keeps the Warning colours for both: no fill in that hue clears the mask's floors against a box that light.
- The inspection area's line (`UI.Widgets.Paint_Inspection_Area`, 1 px, solid, square corners, no fill, on screen
  only) is the amber `Theme.CONST_INSPECTION_AREA` `#FFD880` over a camera image (4.71:1 on the table, 1.18:1 against
  the Warning amber, told from a Warning frame by its 1 px against the frame's 2 px) and the purple
  `Theme.CONST_INSPECTION_AREA_EMPTY` (`CONST_INK`) over the empty Camera View, whose grey-lilac hides the amber
  (1.01:1; the purple 6.79:1). The owner's choice of 2026-10-16 from renders.
- A judged part (OK, NOK) colours its marks by their own check on the frame: the dashed outer box and the chip
  carry the verdict, the solid rotated outline the size check alone (orange-red only when out of tolerance), and each
  feature mark its own check (DD *A judged part's marks each carry their own check*). Warnings and Unspecified
  objects keep one colour.
- The box, the chip and the mask outline are drawn in the verdict colour itself, unshifted, on any
  background. A colour is never lightened, darkened or rotated to gain contrast against a frame.
- Legibility comes from the foreground: a chip is its box's colour and its numeral is plain white
  (`Theme.CONST_CHIP_NUMERAL`) on every chip, in every state and mode. White on the NOK orange-red (2.92:1) and on
  Warning's amber (1.62:1) are the owner's recorded exceptions to 4.5:1 (DD *Every chip carries a white numeral*).
  There is no casing or outline around a chip, a mark or a numeral (the owner's ruling, kept after an outline and a
  numeral rim were measured).
- Words on a verdict (the badge, the diagram's labels) are the purple on `Theme.Label_Ground`: the verdict's
  colour where the purple clears 4.5:1 on it, the poster's tint of it otherwise.
- The label-mask fill is a tint that keeps its box's hue (within 5°, at ≥ 40 % of its chroma), so the
  silhouette and its outline read as one object (DD *The label mask is black ground, tinted fill,
  verdict contour*).
- ✅ `test/Vision/Utilities/test_annotate.py::test_annotated_is_box_and_numeral_only_in_the_unshifted_verdict_colour`,
  `::test_each_chip_is_its_box_colour_with_a_white_numeral`,
  `::test_a_foreign_object_is_grey_and_a_part_outside_the_area_amber_on_the_frame`,
  `::test_a_judged_parts_outline_carries_its_size_and_its_outer_box_and_chip_its_verdict`,
  `test/UI/test_inspection_area.py::test_the_area_is_drawn_on_the_empty_view_the_scanned_frame_and_the_annotated_result_only`,
  `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box`,
  `::test_verdict_colour_comes_from_the_one_constant`, `::test_every_chip_numeral_is_white`,
  `::test_the_palette_keeps_the_brands_rules`.

## Severity is never carried by colour alone ✅

- A severity level has a word and a weight as well as a colour: the Log's level field reads INFO /
  WARNING / ERROR, and its weight ramps INFO < WARNING < ERROR from one shared ramp
  (`Style.Log_Level_Weight`), which the confidence numbers at that severity use too — so a reader who
  cannot tell the colours apart still reads the level. It matters in practice: the WARNING amber and
  ERROR red collapse to nearly one colour under deuteranopia (ΔE ~8, measured; `Style.py`).
- Detect-only versus classified is carried by wording as well as colour: a detect-only run shows no
  OK / NOK words at all, only detected objects.
- ✅ `test/UI/test_log_view.py::test_level_field_weight_ramps_with_severity`,
  `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`,
  `test/Parameters/test_theme.py::test_the_detect_only_box_is_the_logo_purple_and_unspecified_keeps_its_own`,
  `::test_neutral_detection_colour_is_distinct_and_near_achromatic`.

## Controls: every state clears 4.5:1, measured; disabled speaks through its fill ✅

- Every enabled state of every control — rest, hover, pressed, selected, focus — keeps its label at
  ≥ 4.5:1 against its fill, and a stylesheet rule for a state names both its fill and its label
  (DD *Control stylesheets: every state rule names its fill and its label*).
- The contrast is measured from rendered pixels — the widget rendered at 2×, the label's highest-
  contrast pixel against the fill — not read back from the stylesheet, because Qt resolved one
  correct-looking stylesheet to 1.08:1 on screen.
- A disabled control signals through its fill (and outline), not by making its label vanish. It is
  exempt from the 4.5:1 floor — its lower contrast is what says "not available" — but it must stay
  distinguishable from its enabled state, and disabled-hover must look like disabled. Qt's stylesheet
  engine never matches `:hover` on a disabled widget, so no stylesheet can break the last one; a paint
  path keyed on `underMouse()` would need its own test.
- ✅ `test/UI/test_control_contrast.py` (`test_no_enabled_state_falls_below_the_text_contrast_floor`,
  `test_disabled_states_are_exempt_but_distinguishable_from_enabled`,
  `test_every_state_of_every_control_was_measured`, and a self-check that hover really rendered).

## Text: every enabled text clears 4.5:1 against its ground ✅

- Contrast is a property of the colour pair, so it holds at every density; a 1x screen only makes it
  worse (anti-aliasing leaves small text below its token's contrast). A density-dependent palette is not
  used: the theme is one palette (DD *Text clears 4.5:1 on its ground*).
- A status word is drawn in its colour's text twin: `Theme.Status_Text_Color` (`CONST_OK` → `CONST_OK_INK`,
  `CONST_WARN` → `CONST_WARN_INK`). A call site passes the status colour; the widget that draws words
  (`Stat_Cell_Cls.Set_Value`, the header pill) asks for the text colour. A dot keeps the bright colour and
  is held to 3:1, as a graphic.
- Text on the viewport (the grey-lilac) is `CONST_VIEWPORT_TEXT`, the purple (6.79:1); error text there is the
  Log's `CONST_LOG_ERROR` (4.61:1).
- ✅ `test/UI/test_text_contrast.py` builds the window in its states, measures every visible label, rich-text
  span and painted text against the ground grabbed under it (which must be a theme token); disabled text is
  exempt. Buttons are measured by `test_control_contrast.py`.

## A density-dependent style asks the one density check 📄

- `Style.Is_Low_Density(widget)` (device pixel ratio below `CONST_LOW_DENSITY_DPR`, 1.5) is the only place
  density is decided; the logo height (`Style.Logo_Height`) and the 9 pt type floor in `Style.Font`
  (`CONST_TYPE_FLOOR_LOW_DENSITY`) read it. A chrome size below 9 pt is raised to 9 pt at DPR 1 and kept
  on a 2x display. The ratio is read when a
  widget is built, which for the window is before it is shown (Qt 5 then reports the highest ratio of all
  screens), and nothing re-reads it on a screen change (DD *The logo is taller on a low-density display, so its
  tagline is 9 pt*).
- ✅ `test/UI/test_header.py` measures the logo at DPR 1 and runs itself again at DPR 2.
- The header draws the delivered, outlined logo without its tagline (`App/assets/anyscan-logo-wordmark.svg`) and
  sets the tagline as live text where the logo outlines it (`Widgets.Logo_Lockup_Cls`;
  `Style.CONST_LOGO_TAGLINE_ORIGIN`, `CONST_LOGO_TAGLINE_SIZE`, in the logo's colour `CONST_LOGO_INK`). The logo's
  copies are derived from `images/anyscan-logo.svg` by `Example/UI/build_logo.py`; never hand-edit them or move the
  tagline's constants apart from the outlines (DD *The header draws the delivered logo and sets its tagline as live
  text*).
- ✅ `test/UI/test_header.py` holds the live lockup's offsets to the outlined logo's within 1 device px at
  both densities; `test/UI/test_brand_figures.py` holds the derived files to the logo.
- An SVG logo is rendered as vectors at paint time (`QSvgRenderer` into the widget's painter, `Widgets.Svg_Image_Cls`
  for a plain one), never drawn from a pixmap, scaled or not (DD *Logos are rendered as vectors at paint time*).
- ✅ `test/UI/test_logo_rendering.py` compares each drawn logo with a direct render at DPR 1 and DPR 2.
- On a 1x display the header logos' marks are grid-fitted to whole pixels (`UI.Utilities.Grid_Fit`), the lettering left
  as delivered (DD *The header logos are grid-fitted on a 1x display*); ✅ `test/UI/test_grid_fit.py`.
- Every logo is an SVG. A logo supplied only as a raster is traced to a solid SVG, compared with its source by overlay,
  and its file and design-decisions say it is traced, so the official file replaces it when supplied (DD *The band's
  logos are traced SVGs*); ✅ `test/UI/test_funding_band.py`, `test_logo_rendering.py::test_no_logo_is_a_pixmap`.
- The EU disclaimer is kept word for word in one place (`Funding_Row_Cls.DISCLAIMER`), carried by the README and the
  architecture diagram's band, not by the window's band (DD *The funding band carries the project's, the Ministry's
  and the EU's logos*); ✅ `test/UI/test_funding_band.py`.
- Decoration (the band's pixel motif) never enters a logo's clear space, at least the EU emblem's protection area,
  half the flag's height (DD *The funding band carries the brand's pixel motif*); ✅ `test/UI/test_funding_band.py`.
- The brand's squares appear in two places only, the funding band and the empty Camera View's top-right corner (gone
  with the empty state), never in a data area: Scene Understanding, the Log, Trends, History (DD *The empty Camera View
  carries the poster's pixel cluster*); ✅ `test/UI/test_empty_view_motif.py`.
- The README's funding logo row (`images/anyscan-funding.svg`) is generated with the architecture diagram, never
  edited by hand; ✅ `test/UI/test_brand_figures.py`.

## Content type comes from the scale; one content, one size ✅ (content) 📄 (chrome)

- **Content typography** — text the analysis produces, read as the result: the Scene Understanding
  reading (background paragraph, object labels, confidences, descriptions), History's info panel, the
  Log's rows — is sized by named tokens on the modular scale (`CONST_TYPE_SCALE` in `Style.py`;
  `CONST_TYPE_OBJECT_LABEL`, `CONST_TYPE_INFO_BODY`, `CONST_TYPE_LOG` …), never a literal size. A size
  change moves a token to another step.
- **Within a view, one content has one size**: the background paragraph and the object descriptions
  share one, and the hierarchy runs heading > label > body > meta. Across views it deliberately does
  not: Live (glanced at across a workbench) and History (read up close) have separate token sets, so a
  description is 12.5 pt in one and 10.5 pt in the other, and tuning one cannot move the other.
- **Chrome** — the frame around the content: button and pill labels, status-strip labels and values,
  card metadata, captions, empty-state and status messages, overlays — is sized per widget (literal
  sizes, or raw steps of the scale). It is not held to the scale; see Unsettled.
- **Which side a new widget falls on:** if the text is part of what the analysis says (a reading, a
  record, a description), it is content and takes a named token; if it labels, frames or operates
  the UI, it is chrome.
- The reasoning: DD *Type: a scale for content, chosen sizes for chrome*.
- ✅ `test/UI/test_history.py::test_info_panel_type_hierarchy_heading_is_largest`.

## A colour relationship is held by code or a test, never by a comment ✅

- Where two colours must keep a relationship — a mask fill against its box, against white, against
  the black ground — the relationship is enforced, not merely noted:
  - **by derivation**, failing loudly: the neutral mask pair is computed from the neutral box at
    import (`Theme.Neutral_Mask_Colors`), and raises a `ValueError` naming the violated floors when no
    valid pair exists or rounding breaks one;
  - **or by a test on the floors**, for colours tuned by eye: the verdict fills are fixed tokens,
    and `test_theme.py` holds them to the same floors (ΔE from the box and from white, 4.5:1 on the
    ground, the hue within 5°).
- ✅ `test/Parameters/test_theme.py::test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors`,
  `::test_label_mask_fill_is_a_visible_tint_of_its_box`.

## Unsettled

- **Chrome type sizes.** 32 chrome `Font(...)` calls use literal sizes, most of them off the scale
  (7.5, 8, 8.5, 9, 10, 11, 12, 13.5). The rule above covers content only.
- **One content label outside the scale:** the Scene Understanding card's note (`UI/Core.py`,
  `__reading_note`, the composer's note under the objects) is content set at a literal 11.5 (a scale
  step, but not a named token).
- **Derivation or test.** Both hold colour relationships today (the neutral pair derived, the verdict
  fills tested); there is no rule for which a new pair should use.
- **The label mask's black ground** is `Annotate.CONST_ANNOTATE_MASK_GROUND` — by a documented choice
  not a theme surface colour — while `Theme.Ground_Contrast` separately assumes `'#000000'`: one colour
  with two sources.
