# jic-sf-ui-style: project reference for AnyScan

AnyScan's bindings of the JIC Smart Factory style (the personal skill **jic-sf-ui-style**, which was
taken from this application): which module does each job, its views and their state colours, its
vision overlays and their measurements, its catalogue wording, its logos and band, and the test that
holds each rule here (✅ a test, 📄 documentation only). Each section names the skill page that holds
the rule; this file does not repeat it. The brand-independent UI rules and their bindings here (Qt
code, the token test, contrast, density, colour relationships) are project-style-rpx
`references/ui.md` and `.claude/skills/project-style-rpx/references/project.md` > *UI*. Where the
skill and this code disagree, the code is the truth; correct the skill. On a machine without the
personal skill, the rules are read from this file, the code and `.claude/project-docs/design-decisions.md` (DD).

This folder has no `SKILL.md` on purpose: a personal skill wins over a project skill of the same name,
so a copy here would be ignored and drift.

## Modules

Do not copy the skill's templates here: they were generalised from these modules.

| Need | AnyScan module |
|---|---|
| A colour token | `src/Parameters/Theme.py` (Qt-free), re-exported by `src/UI/Utilities/Style.py` |
| Font, density, `Token_Color`, hairline, scroll style | `src/UI/Utilities/Style.py` |
| Card, head, badge, marker, button, segment, stat cell, viewport, logo, band | `src/UI/Widgets.py` |
| Header and window layout | `src/UI/Core.py` (`__Build_Topbar`, `__Build_Ui`) |
| Pixel icons, motif, analysis-grid wave | `src/UI/Utilities/Pixel_Motif.py` |
| Grid-fitting | `src/UI/Utilities/Grid_Fit.py` |
| Charts | `src/UI/Views/Trends.py` (+ `src/Reporting/Trends.py` maths) |
| History, Log views | `src/UI/Views/History.py`, `Log.py` |
| Image marks | `src/Vision/Utilities/Annotate.py` |
| Operator wording | `src/Reporting/Core.py` |

## AnyScan's state colours and the views that carry them ✅ - jic-sf-ui-style: `palette.md`, `charts.md`, `annotation.md`

- **One colour per state, in every view** (the owner's rule, 2026-10-16): a state's frame mark in the
  Camera View, its Trends series and legend sample, its History filter swatch and set outline are the
  same token (`Theme.Verdict_Color`, whose ink is its box). Three states (the owner's rule,
  2026-10-16): OK, NOK and Warning, every Warning whatever its kind. Trends' 2 px lines and 7 px square
  markers are `CONST_SERIES_LINE_W` and `CONST_SERIES_MARKER_PX` in `UI/Views/Trends.py` (the owner's
  rule, 2026-10-18); `Theme.Chart_Edge`, the 1.25 px dark edge at L* 25, is removed. Every colour of a
  catalogue mode:

  | Use | Token | Value | On white |
  |---|---|---|---|
  | OK | `CONST_INK` | `#640ABA` | 9.15:1 |
  | NOK | `CONST_NOK_BOX` | `#FF6540` | 2.92:1 |
  | Warning (every kind) | `CONST_WARNING_BOX` | `#FFC226` | 1.62:1 |
  | Trends Total (no state) | `CONST_INK_MUTE` | `#6F5783` | 6.24:1 |
  | Confidence: Frame mean (no state) | `CONST_DETECTION_INK` | `#655E6D`, 2 px solid, a filled 7 px square per image | 6.22:1 |
  | Confidence: Run mean (no state) | `CONST_CHART_LIGHT_INK` | `#9890A0`, 2 px dashed (6 px dash, 4 px gap), a hollow 7 px square (2 px ring) per image, drawn on top | 3.07:1 (2.02:1 against the frame mean's) |
  | Badge grounds | OK `#C2C9FF`, NOK `#FFD9D0`, Warning `#FFC226` | | purple words ≥ 5.66:1 |
  | Mask fills | OK `#CC9EF1`, NOK `#CD7157`, Warning `#B28508` (outline the amber) | | |
  | Inspection area | `CONST_INSPECTION_AREA` / `_EMPTY` | `#FFD880` on images / `#640ABA` on the empty view | 4.71:1 on the table / 6.79:1 on `#E1DCE6` |

  Retired as verdict colours on 2026-10-16: the foreign object's grey `#B4A6BE` (badge `#CAC0D3`, mask
  `#DBCCE5` / `#897C93`) and Unspecified's blue `#33A3FF` (badge `#C6E4FF`, mask `#748DB1`). The grey
  stays only as the disabled label's token (`CONST_CONTROL_DISABLED_TEXT`,
  `CONST_PRIMARY_DISABLED_TEXT`), never a state's nor in Trends; the blue is no token at all (DD *Three
  states for the operator, a Warning with its kind*).
- **Trends' Confidence chart draws no verdict** (the owner's rule, 2026-10-18): the frame mean and the
  run mean only, nothing per object, in the two neutrals of the table above; its threshold lines are
  the configuration's `Confidence.Warn_Below` and `Error_Below`, labelled 'Warning below 80 %' and
  'Error below 60 %'. The charts' own secondary text is the neutral grey; `CONST_INK_SOFT` elsewhere
  stays the purple (DD *The Confidence chart draws the two means, told apart by their form*; *Trends
  draws square markers, 2 px lines, and the run mean as hollow squares on top*).
- OK is the JIC purple and NOK the JIC orange-red (DD *The fail marker is the JIC orange-red*; *The
  palette is the JIC Smart Factory brand's*). The neutral ink `#655E6D` is no verdict's colour: it
  marks only a detect-only mode's words and dots, its derived mask pair and History's outline of a
  detect-only set.

## The vision overlays: annotated frame, label mask, inspection area ✅ - jic-sf-ui-style: `annotation.md`

- **Detect-only** (Segment Anything) draws every object in the logo purple `#640ABA`
  (`CONST_DETECTION_BOX = CONST_LOGO_INK`, white numeral 9.15:1; table 1.31:1 at ΔE 121, aluminium
  3.53:1, rust-stained metal 3.02:1, steel 2.32:1). It equals OK, the owner's ruling of 2026-10-15:
  that mode shows no verdict (DD *Every chip carries a white numeral*).
- **Every Warning has one look**, whatever its kind (outside the area, a foreign object, several
  parts, side unclear, side mismatch): its rotated outline, dashed outer box and chip in the amber
  with the white numeral, filled and outlined in the amber's pair on the mask, and no feature mark,
  though a part whose side could not be told was checked and keeps its features in the record
  (`Annotate.__Draw_Features` draws only OK and NOK parts' marks).
- **A judged part (OK, NOK)** colours its marks by their own check on the frame: the dashed outer box
  and the chip the verdict, the solid rotated outline the size check alone (`Annotate.__Outline_Color`),
  each feature mark its own check (DD *A judged part's marks each carry their own check*).
- **The inspection area** (`UI.Widgets.Paint_Inspection_Area`, on screen only):
  `Theme.CONST_INSPECTION_AREA` over a camera image (4.71:1 on the table, median `#236A56`; 1.18:1
  against the Warning amber), `CONST_INSPECTION_AREA_EMPTY` over the empty Camera View (the amber
  1.01:1 there; the purple 6.79:1). The owner's choice of 2026-10-16 from renders. Chips:
  `Theme.CONST_CHIP_NUMERAL`; badge words: `Theme.Label_Ground`; the diagram's verdict labels follow
  the badge's rule.
- **The label mask** (DD *The label mask is black ground, tinted fill, verdict contour*): the fills
  keep their box's hue, held by the tests below and by `Theme`'s `CONST_MASK_FILL_*` floors.
- ✅ `test/Vision/Utilities/test_annotate.py::test_annotated_is_box_and_numeral_only_in_the_unshifted_verdict_colour`,
  `::test_each_chip_is_its_box_colour_with_a_white_numeral`,
  `::test_the_catalogue_states_render_in_their_colours_on_both_images`,
  `::test_a_warning_shows_only_its_outline_outer_box_and_chip`,
  `::test_a_judged_parts_outline_carries_its_size_and_its_outer_box_and_chip_its_verdict`,
  `test/UI/test_inspection_area.py::test_the_area_is_drawn_on_the_empty_view_the_scanned_frame_and_the_annotated_result_only`,
  `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box`,
  `::test_verdict_colour_comes_from_the_one_constant`, `::test_every_chip_numeral_is_white`,
  `::test_the_palette_keeps_the_brands_rules`.

## The catalogue's wording ✅ - jic-sf-ui-style: `wording.md`

- A Warning's kind is told in words, never in colour: `State: Warning – <kind>.` in Scene
  Understanding (`Reporting.State_Word`, `Verdict_Lines`), the `warning_kind` in the record; the kinds
  and their names are `Parameters.Vision.CONST_WARNING_KINDS` (DD *Three states for the operator, a
  Warning with its kind*).
- A detect-only run shows no OK / NOK words at all, only detected objects.
- ✅ `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`,
  `test/Parameters/test_theme.py::test_the_detect_only_box_is_the_logo_purple`,
  `::test_every_warning_is_the_amber_and_the_retired_state_colours_are_gone`,
  `::test_neutral_mask_pair_is_derived_light_fill_and_darker_outline`.

## The Camera View names its state in its head; nothing but the analysis grid lies over the frame ✅ - jic-sf-ui-style: `layout-components.md` § 8

- The marker (`●  LIVE PREVIEW`, `SCANNING…`, `ANALYZING…`) is `UI.Widgets.State_Marker_Cls`, fed by
  `Viewport_Cls.Marker_Changed`; a new state the view must name joins `CONST_STATES` (DD *ANALYZE
  sweeps a decorative pixel grid over the frame…*). The grid and the busy overlay are `Viewport_Cls`
  (`Start_Analysis`, `Start_Busy`), their values in `Theme.CONST_GRID_*`, `CONST_BUSY_*` and
  `Pixel_Motif.CONST_WAVE_*`.
- ✅ `test/UI/test_analysis_grid.py::test_the_grid_is_the_same_drawing_over_two_different_frames`,
  `::test_no_state_label_is_drawn_inside_the_image`, `::test_the_three_states_share_one_marker_in_the_head`,
  `::test_the_grid_stops_when_the_analysis_ends`.

## The header, the logos and the funding band - jic-sf-ui-style: `grid-fit.md`, `layout-components.md` §§ 2, 9

- The density check and the type floor are bound in project-style-rpx `project.md` > *One density check*.
- The header's lockup is `Widgets.Logo_Lockup_Cls`: `App/assets/anyscan-logo-wordmark.svg` plus the
  live tagline at `Style.CONST_LOGO_TAGLINE_ORIGIN` and `CONST_LOGO_TAGLINE_SIZE`, in
  `CONST_LOGO_INK`. The logo's copies are derived from `images/anyscan-logo.svg` by
  `Example/UI/build_logo.py`; never hand-edit them or move the tagline's constants apart from the
  outlines (DD *The header draws the delivered logo and sets its tagline as live text*).
  ✅ `test/UI/test_header.py` holds the live lockup to the outlined logo within 1 device px at both
  densities; `test/UI/test_brand_figures.py` holds the derived files to the logo.
- Logos are vectors at paint time (`Widgets.Svg_Image_Cls`; DD *Logos are rendered as vectors at
  paint time*), ✅ `test/UI/test_logo_rendering.py`; the header marks are grid-fitted at 1x
  (`UI.Utilities.Grid_Fit`, `Style.CONST_LOGO_MARK_RIGHT`, `CONST_LOGO_MARK_THIN_PX`,
  `AnyScan_Window_Cls.CONST_JIC_MARK_RIGHT`; DD *The header logos are grid-fitted on a 1x display*),
  ✅ `test/UI/test_grid_fit.py`.
- The band's three logos are traced SVGs (DD *The band's logos are traced SVGs*),
  ✅ `test/UI/test_funding_band.py`, `test_logo_rendering.py::test_no_logo_is_a_pixmap`. The EU
  disclaimer is `Funding_Row_Cls.DISCLAIMER`, carried by the README and the architecture diagram's
  band, not the window's (DD *The funding band carries the project's, the Ministry's and the EU's
  logos*); the motif keeps out of every logo's clear space (DD *The funding band carries the brand's
  pixel motif*); ✅ `test/UI/test_funding_band.py`.
- The brand's squares are in the funding band and the empty Camera View's corner only, never in Scene
  Understanding, the Log, Trends or History (DD *The empty Camera View carries the poster's pixel
  cluster*); ✅ `test/UI/test_empty_view_motif.py`.
- The README's funding logo row (`images/anyscan-funding.svg`) is generated with the architecture
  diagram; ✅ `test/UI/test_brand_figures.py`.

## Content type comes from the scale; one content, one size ✅ (content) 📄 (chrome) - jic-sf-ui-style: `typography.md`

- AnyScan's content is the Scene Understanding reading (background paragraph, object labels,
  confidences, descriptions), History's info panel and the Log's rows, sized by the named steps of
  `CONST_TYPE_SCALE` in `Style.py`: `CONST_TYPE_SCENE_BACKGROUND`, `CONST_TYPE_OBJECT_LABEL`,
  `CONST_TYPE_OBJECT_CONFIDENCE`, `CONST_TYPE_OBJECT_BODY` (Live), `CONST_TYPE_INFO_HEADING`,
  `CONST_TYPE_INFO_LABEL`, `CONST_TYPE_INFO_BODY`, `CONST_TYPE_INFO_META` (History), `CONST_TYPE_LOG`.
  Live and History are separate sets on purpose (a description 12.5 pt in one, 10.5 pt in the other).
  Chrome is sized per widget; see Unsettled.
- DD *Type: a scale for content, chosen sizes for chrome*.
- ✅ `test/UI/test_history.py::test_info_panel_type_hierarchy_heading_is_largest`.

## Every icon is a pixel icon from one set ✅ - jic-sf-ui-style: `pixel-icons.md`

- The set is `UI.Utilities.Pixel_Motif.CONST_PIXEL_ICONS`, which the README's architecture diagram
  draws too. A card head takes `Card_Head_Cls(<name>, title)`, a dialog's title
  `Icon_Cls.Head_Layout(<name>)`, anything else `Icon_Cls(<name>, cell, colour)`; a head's 2 px top
  margin is `Icon_Cls.CONST_HEAD_DROP`; an animated icon steps through `Busy_Cells`. The model pill's
  icon is its grey, as the pill's words are (DD *Every icon is a pixel icon from one set*, which has
  the table of which icon is where).
- ✅ `test/UI/test_pixel_icons.py` reads every icon off the window's and the dialog's grabs against the
  set and the meaning approved for its place, renders every icon at 1x and at DPR 2 (two colours,
  whole cells), and decodes the committed diagram's icons back to the set.

## Unsettled - not rules yet

- **Chrome type sizes**: 34 `Font(<number>` calls in `src/UI/` use literal sizes, most of them off
  the scale (7.5, 8, 8.5, 9, 10, 11, 12, 13.5). The content rule covers content only.
- **One content label outside the scale**: the Scene Understanding card's note (`UI/Core.py`,
  `__reading_note`, the composer's note under the objects) is content set at a literal 11.5 (a scale
  step, but not a named token).
- **The label mask's black ground** is `Annotate.CONST_ANNOTATE_MASK_GROUND` - by a documented choice
  not a theme surface colour - while `Theme.Ground_Contrast` separately assumes `'#000000'`: one colour
  with two sources.
