# Typography

Source: `templates/JIC_SF_UI/Style.py` (`Font`, `Load_Fonts`, `CONST_TYPE_SCALE`), with the sizes taken from AnyScan's
`src/UI/Widgets.py` and `src/UI/Core.py`. The reasoning is in AnyScan's design decisions, the entries *The UI is
set in Public Sans*, *The UI fonts are bundled*, *A 9 pt type floor on a low-density display* and *Type: a scale for
content, chosen sizes for chrome*.

## Faces

- **Public Sans** (SIL OFL 1.1) is used for every word. It is the open face closest to the brand's **GT America
  Standard**. Measured at GT's cap height it has x/cap 0.713 against 0.709, a line width 0.9 % wider, glyph overlap
  0.773 and 5 % more weight, ahead of Libre Franklin and Inter.
- **JetBrains Mono** (SIL OFL 1.1) is used only for machine values: times, sizes, resolutions, latencies,
  percentages in a value slot, and the Log's timestamp and level columns, where fixed-width digits keep a column
  still. Badges, chips, the empty view's instruction and the busy text are words, so they use Public Sans.
- **GT America Standard and GT Super Display are commercial.** Never bundle them, never commit them, and never
  embed them in an SVG or a PDF you ship. They may be read locally (from a designer's folder kept out of git) only to
  compare a candidate face against them.
- **Newsreader** (SIL OFL, opsz 72) is the open face closest to GT Super Display: x/cap 0.713 against 0.722, width
  −0.9 %, overlap 0.551, ahead of Playfair Display and Fraunces. **Do not use it in the application.** The owner left
  the serif out, because the largest heading in the UI is a 15.5 pt card title. Use it only for a display headline in
  a printed or marketing piece where the brand guide sets GT Super Display, such as a poster title or a cover. It is
  not bundled here; fetch it from Google Fonts with its OFL licence if such a piece needs it.
- The fonts ship as **static** files at the four weights the UI requests, Regular 400, Medium 500, SemiBold 600
  (QFont.DemiBold) and Bold 700, together with each family's `*-OFL.txt`. Why static files, and when to register them:
  project-style-rpx `references/ui.md` § *Qt quirks*.
- `Style.Load_Fonts()` registers every `.ttf` in `assets/fonts/`. The candidate lists (`Segoe UI`, `Helvetica Neue`,
  `Arial`, and so on) are only the fallback for a missing folder.

## Building a font

Build every font, painted text included, with `Style.Font(size_pt, weight, mono=False, tracking=0)`; it applies the
9 pt type floor through `Style.Is_Low_Density`, which `Style.Logo_Height` asks too: project-style-rpx `references/ui.md`
§ *One density check*.
`tracking` is percentage letter spacing: +6 to +7 for UPPERCASE chrome, −2 to −4 for titles and big numbers.

## Content: a modular scale, one size per content per view

`CONST_TYPE_SCALE = (9.5, 10.5, 11.5, 12.5, 14.0, 15.5, 16.5, 18.0)` pt. Content is text the application produces and
a person reads to decide something: a reading, a record, a description, a log row. It takes a named step, never a
literal size.

| Token | Step | Use |
|---|---|---|
| `CONST_TYPE_HEADING` | 14.0 | A reading's lead paragraph and each object's label line (DemiBold), read from across a workbench |
| `CONST_TYPE_BODY` | 12.5 | Its descriptions and state lines (state lines in DemiBold); a confidence suffix one step down from its label |
| `CONST_TYPE_INFO_HEADING` / `_LABEL` / `_BODY` / `_META` | 12.5 / 11.5 / 10.5 / 9.5 | The same content in a panel read up close |
| `CONST_TYPE_LOG` | 11.5 | A log row (mono timestamp and level, UI-face message) |

Within a view, one kind of content has one size, and the hierarchy runs heading > label > body > meta. Across views
it deliberately does not: a far set (Live) and a near set (History) are separate tokens, so tuning one cannot move
the other. Everything in the reading is `CONST_INK`; hierarchy comes from size and weight, never colour.

## Chrome: chosen sizes, per widget

Chrome is text that labels, frames or operates the UI. It uses the sizes below. Reuse them as they are; do not
invent new ones.

| Element | Size, weight, tracking | Colour |
|---|---|---|
| Card title | 15.5 Bold, −2 % | `CONST_INK` |
| Action button | 9.5 DemiBold, +6 %, UPPERCASE | per state (`Qss.Tool_Button`) |
| Segment / tab | 9 DemiBold, +2 % | per state (`Qss.Segment`) |
| Header pill | 9 DemiBold (a pill with a name: name 9 DemiBold, state 9 Regular) | status text twin |
| Badge | 8 Bold (9 at DPR 1) | `CONST_INK` on its ground; idle `CONST_INK_MUTE` |
| State marker (LIVE PREVIEW…) | 9.5 DemiBold, +6 %, UPPERCASE | `CONST_ON_INK` on purple |
| Status cell caption | 8 Bold, +7 %, UPPERCASE | `CONST_INK_MUTE` |
| Status cell value: count | 18 Bold, −4 % | `CONST_INK` |
| Status cell value: state | 13.5 DemiBold, −2 % | status text twin |
| Status cell value: machine | 12 Medium, mono | `CONST_INK` |
| Meta row key / value | 10 / 10 Medium (compact: 9.5 / 9.5 Regular; mono values 9) | `CONST_INK_SOFT` / `CONST_INK` |
| Chart card subtitle | 10.5 | `CONST_INK_MUTE` |
| Chart tick labels, legend, guide labels, hover | 9.5 | ticks `CONST_INK_MUTE`, the rest `CONST_DETECTION_INK` |
| Chart axis titles | 10.5 | `CONST_DETECTION_INK` |
| Empty-state instruction, busy step | 9.5 | `CONST_VIEWPORT_TEXT` / `CONST_BUSY_INK` |
| Reading-card empty text, notes | 11.5 | `CONST_INK_MUTE` |
| Live tagline in a lockup | the logo's own size (outlined cap height ÷ 0.723) | `CONST_LOGO_INK` |

## Placeholders and punctuation

- An empty value slot shows `—` (`Style.CONST_NO_VALUE`). The em dash appears only where a number or a time will sit,
  never in prose and never in a label.
- An en dash with spaces joins a kind and its detail (`Warning – Outside area`, `Catalogue inspection – Mounting
  plate`); see `wording.md`.
- `·` (a middle dot with spaces) separates a label from its count or metadata (`NOK · 2`, `Live · 3.7 fps`,
  `Object 1 · Confidence 91%`).
- Use a real ellipsis `…` in working states (`SCANNING…`, `Connecting…`), not three dots.
