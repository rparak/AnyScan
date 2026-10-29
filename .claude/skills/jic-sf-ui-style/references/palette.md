# Palette: theme tokens, roles and measured contrasts

Source of truth: `templates/JIC_SF_UI/Theme.py`, generalised from AnyScan's `src/Parameters/Theme.py`. Every number
here was computed with the theme's own `Contrast_Ratio` (WCAG 2.x) and `Delta_E` (CIE76, D65); recompute any new
pair with `scripts/contrast.py '#fg' '#bg'`.

## Contents
1. The rules
2. Brand colours
3. Surface, text and control tokens
4. The three states (verdicts)
5. Status colours (system health)
6. Neutral and chart greys
7. Overlays, the band and decoration
8. Log severities
9. Adding a colour

## 1. The rules

- Every colour a token in a Qt-free theme (here `Theme`, read through `Style`; `Style.Token_Color` / `Token_Css` at an
  opacity), figures from the theme, and how a new colour is measured: project-style-rpx `references/ui.md` § *Colour
  comes from the theme*.
- **One purple, `#640ABA`.** No darker or lighter shade of it exists. Hierarchy comes from size and weight, and
  secondary text is the same purple (`CONST_INK_SOFT = CONST_INK`). The poster's dark purple `#2D0557` was dropped
  everywhere: hover fills, text on chips and badges, outlines under marks, the band. The purple hover of a filled
  control does not shift its colour.
- **One colour per state, in every view.** OK, NOK and Warning each have one colour, used for the image mark, the
  chip, the chart series, the legend sample, the filter swatch and the set outline. No darker "chart variant" of a
  state exists. A light state reads on white through the 2 px line and the square marker, never through a darker
  edge.
- **A colour is never shifted to gain contrast.** A mark is drawn in its token, unshifted, on any ground. Legibility
  comes from the foreground instead: white numerals on chips, and the `_INK` text twin for status words.
- The 4.5:1 text and 3:1 graphic floors, disabled controls, severity never by colour alone and colour relationships held
  by code or a test: project-style-rpx `references/ui.md` § *Contrast floors, measured*.
- **The brand's recorded exceptions to the floor** are white numerals on the NOK chip (2.92:1) and on the Warning chip
  (1.62:1), the owner's choice for short bold numerals.
- **Corners are square.** No radius exists anywhere. This is a shape rule, recorded here because it travels with
  the palette.

## 2. Brand colours (JIC Smart Factory guide)

| Token | Hex | Role | On white | On grey-lilac | LCh |
|---|---|---|---|---|---|
| `CONST_PURPLE` | `#640ABA` | All text, outlines, icons, the selected segment, the OK state, the band, the logo | 9.15:1 | 6.79:1 | L\*31 C\*96 h312 |
| `CONST_GREY_LILAC` | `#E1DCE6` | Card outlines, dividers, gridlines, control hover, viewport ground | 1.35:1 | — | L\*88 C\*6 |
| `CONST_PERIWINKLE` | `#C2C9FF` | Pressed plain button, scroll handle, OK badge ground, analysis-grid lines | 1.60:1 | 1.19:1 | purple on it 5.71:1 |
| `CONST_ORANGE_RED` | `#FF6540` | NOK | 2.92:1 | 2.17:1 | L\*62 C\*76 h42 |
| `CONST_AMBER` | `#FFC226` | Warning, and the "working" pill outline | 1.62:1 | 1.20:1 | purple on it 5.66:1 |
| `CONST_GREEN` | `#3DBE4C` | System health only (a pill outline); never an object | 2.42:1 | 1.80:1 | |

The guide's yellow `#FFEF85` is decoration and no token. The guide's typefaces are covered in `typography.md`.

## 3. Surface, text and control tokens

| Token | Value | Role and measurement |
|---|---|---|
| `CONST_BG`, `CONST_CARD` | `#FFFFFF` | Page and card |
| `CONST_CARD_BORDER`, `CONST_LINE` | `#E1DCE6` | 1 px card outline, dividers, chart gridlines |
| `CONST_INK`, `CONST_INK_SOFT` | `#640ABA` | Every word, title, value and icon |
| `CONST_INK_MUTE` | `#6F5783` | Labels, empty states, timestamps, status-cell captions, chart tick labels and a chart's Total: 6.24:1 on white, 4.63:1 on grey-lilac (the purple's hue at C\*28, L\*41) |
| `CONST_ON_INK` | `#FFFFFF` | Words and icons on any purple fill: 9.15:1 |
| `CONST_CONTROL_BORDER` | `#640ABA` | Resting 1 px outline of a plain button or segment |
| `CONST_CONTROL_HOVER` | `#E1DCE6` | Plain hover fill; the label stays purple (6.79:1) |
| `CONST_CONTROL_PRESSED` | `#C2C9FF` | Plain pressed fill; the label stays purple (5.71:1) |
| `CONST_INK_HOVER`, `CONST_INK_PRESSED` | `#640ABA` | Primary and selected hover and pressed fills, under white (9.15:1) |
| `CONST_CONTROL_DISABLED_TEXT` | `#B4A6BE` | Disabled label: 2.30:1, exempt from the floor (the purple's hue at L\*70) |
| `CONST_CONTROL_DISABLED_BORDER` | `#E1DCE6` | Disabled outline (it fades to the divider) |
| `CONST_PRIMARY_DISABLED_FILL` | `#FFFFFF` | A disabled primary button stays outlined on the card |
| `CONST_LOGO_INK` | `#640ABA` | The logo's fill, and a live tagline beside it |
| `CONST_VIEWPORT` | `#E1DCE6` | An image view's ground, empty or letterboxed |
| `CONST_VIEWPORT_TEXT` | `#640ABA` | Text on the viewport: 6.79:1 |
| `CONST_TOPBAR_DIVIDER` | `#E1DCE6` | The 34 px rule between the product lockup and the JIC logo |
| `CONST_SCROLLBAR_HANDLE` | `#C2C9FF` | The square scroll handle |

A control state is always a (fill, label) pair. `Qss.py` names both in every state rule (see `layout-components.md`).

## 4. The three states (verdicts)

`Theme.Verdict_Color(state)` returns `(box, ink, fill)`. The box is the stroke on an image, the chip, every chart
series, legend sample, filter swatch and set outline of that state. The ink is the same colour. The fill is a
label-mask tint in the box's own hue (within 5°, at ≥ 40 % of its chroma).

| State | Box = ink | White numeral | Mask fill | Badge ground (purple words) |
|---|---|---|---|---|
| OK | `#640ABA` | 9.15:1 | `#CC9EF1` | `#C2C9FF`, 5.71:1 |
| NOK | `#FF6540` | 2.92:1 (accepted exception) | `#CD7157` | `#FFD9D0`, 7.01:1 (purple on the solid orange-red would be 3.13:1) |
| Warning | `#FFC226` | 1.62:1 (accepted exception) | `#B28508` | the amber itself, 5.66:1 |

- The states lie ΔE 125.5 (OK–NOK), 58.1 (NOK–Warning) and 166.7 (OK–Warning) apart. Under deuteranopia NOK and
  Warning are ΔE 27 apart, so the words and the weights carry the difference.
- **Warning is one family with a kind** (outside the area, a foreign object, several parts, side unclear, side
  mismatch, or your project's own kinds). Every kind is the amber. The kind is told in words (`State: Warning –
  Outside area.`), never in colour, and a new kind needs a name and an action, never a colour.
- A **detect-only** mode, which shows no verdict, draws every object in `CONST_DETECTION_BOX` (`#640ABA`). Its words
  and its set outline use the neutral `CONST_DETECTION_INK`.
- Retired as state colours, so do not reintroduce them: the foreign grey `#B4A6BE` (it remains only as the disabled
  label) and a sky blue `#33A3FF`.
- `CONST_CHIP_NUMERAL` `#FFFFFF`: every chip numeral is plain white, in every state and mode, with no rim and no
  casing.

## 5. Status colours (system health, never an object)

Green and amber are too light for a dot on white, so each has a dot twin at L\*60.5 (≈ 3.1:1, the graphic floor), a
text twin at L\*41 (≈ 6.2:1), and the brand colour itself for a pill's outline.

| Meaning | Dot | Words (`Theme.Status_Text_Color`) | Pill outline |
|---|---|---|---|
| Connected, ready | `CONST_OK` `#1EA838`, 3.13:1 | `CONST_OK_INK` `#00711B`, 6.22:1 | `#3DBE4C` |
| Degraded, working | `CONST_WARN` `#B98B00`, 3.11:1 | `CONST_WARN_INK` `#7C5B00`, 6.26:1 | `#FFC226` |
| Idle, offline | `CONST_INK_MUTE` | `CONST_INK_MUTE` | `#E1DCE6` |
| Not loaded | hollow `○` in `CONST_INK_MUTE` | `CONST_INK_MUTE` | dashed `#640ABA` |
| Failed (application) | `CONST_LOG_ERROR` | `CONST_LOG_ERROR` `#BE0362` | — |

Green never marks an object. A widget that draws status words takes the status colour from its caller and asks
`Status_Text_Color` for the words, so the call site passes one colour.

## 6. Neutral and chart greys

| Token | Hex | Role | Measured |
|---|---|---|---|
| `CONST_DETECTION_INK` | `#655E6D` | Chart text (axis titles, legend labels, guide labels, hover secondaries), the dark neutral series, threshold guides, a detect-only mode's words and set outline | 6.22:1 on white; ΔE 80–95 from every state (87.0 from the purple) |
| `CONST_CHART_LIGHT_INK` | `#9890A0` | The light neutral series: a derived running value drawn dashed with hollow squares | 3.07:1 on white, the lightest of the dark neutral's hue (L\*61, C\*10) that clears 3:1; 2.02:1 and ΔE 19.9 from `#655E6D` |
| `CONST_INK_MUTE` | `#6F5783` | A chart's Total series and tick labels | 6.24:1 |
| `CONST_LINE` | `#E1DCE6` | Gridlines and the plot's base line | |

In charts the secondary text is the neutral grey rather than the purple: next to data, the purple would read as OK.
Everywhere else secondary text stays the purple, by the one-purple rule.

## 7. Overlays, the band and decoration

| Token | Value | Use |
|---|---|---|
| `CONST_SCRIM` / `_ALPHA` | `#640ABA` at 0.16 | Behind a modal dialog |
| `CONST_BUSY_SCRIM` / `_ALPHA` | `#E1DCE6` at 0.70 | The busy overlay over an image view (the frame shows through faintly); its words and icon are `CONST_BUSY_INK` `#640ABA`, and unlit icon cells sit at `CONST_BUSY_DIM_ALPHA` 0.18. Over dark frames the words fall to ~4.4:1, by the owner's choice (78 % would reach 4.5:1). |
| `CONST_GRID_LINE` / `_ALPHA` | `#C2C9FF` at 0.55 | Analysis-grid lines (1 px) |
| `CONST_GRID_FILL` / `_ALPHA` | `#CC9EF1` at 0.30 | Analysis-grid cell fill: at least 40 % of the frame shows through every pixel |
| `CONST_BAND` | `#640ABA` | The funding band |
| `CONST_BAND_LINE` / `_ALPHA` | `#FFFFFF` at 0.20 | The band's rule |
| `CONST_BAND_TEXT` / `_ALPHA` | `#FFFFFF` at 0.76 | The disclaimer, where a band carries one (5.72:1) |
| `CONST_CORNER_MOTIF` / `_ALPHA` | `#640ABA` at 0.07 and 0.12 | The empty view's corner pixel cluster |
| `CONST_INSPECTION_AREA` | `#FFD880` | A screen-only area line over a camera image (4.71:1 on AnyScan's green table, 1.18:1 against the Warning amber; told apart by its 1 px against a frame's 2 px) |
| `CONST_INSPECTION_AREA_EMPTY` | `#640ABA` | The same line over the empty grey-lilac view, where the amber vanishes (1.01:1); the purple reaches 6.79:1 |

## 8. Log severities

| Level | Colour | Weight |
|---|---|---|
| INFO | `#640ABA` | Normal 400 |
| WARNING | `#7C5B00` (`CONST_WARN_INK`) | DemiBold 600 |
| ERROR | `#BE0362`: 6.22:1 on white, 4.61:1 on grey-lilac | Bold 700 |

The log ERROR is **deliberately not** the NOK orange-red. A faulty part is not a software fault; the two are ΔE 55
apart, so do not unify them. The timestamp stays `CONST_INK_MUTE` so the eye lands on severity first. The same
weight ramp (`Style.CONST_LEVEL_WEIGHTS`) colours and weights a number at that severity anywhere.

## 9. Adding a colour

1. Ask whether an existing token already plays the role. Most new needs are the purple, the muted ink or a state.
2. If not, derive it: keep the hue of a brand colour and move L\*/C\* in LCh (`Theme.Lch_Of`). Text twins sit at
   L\*41.
3. Measure and register it as project-style-rpx `references/ui.md` § *Colour comes from the theme* says, with
   `scripts/contrast.py`, in `Theme.py` and `tests/test_style.py::test_every_pair_clears_its_floor`.
4. Never add a second purple or a darker state variant. If a light colour does not read, raise the line width or the
   marker before considering a new colour.
