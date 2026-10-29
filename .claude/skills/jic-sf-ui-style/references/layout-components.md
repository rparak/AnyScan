# Layout and components

Every component here exists in `templates/JIC_SF_UI/Widgets.py` (with its stylesheet in `Qss.py`), generalised
from AnyScan's `src/UI/Widgets.py` and `src/UI/Core.py`. The sizes are AnyScan's; keep them unless a decision says
otherwise.

## Contents
1. Window layout
2. Header: lockup, rule, JIC logo, tabs, pills
3. Cards and card heads
4. Badges and the badge row
5. Action buttons and their states
6. Segmented controls (tabs, toggles, filters)
7. Status strip cells
8. Image view: state marker, empty view, busy overlay, analysis grid, inspection area
9. Funding band, logos and the EU disclaimer
10. Smaller pieces: meta rows, scroll areas, hairlines, dialogs

## 1. Window layout

```
┌ root (#root, white) ── margins 18 · 0 · 18 · 18 ─────────────────────────────────────┐
│ Header_Cls        lockup │ JIC logo        [Live|Trends|…]         (pill) (pill)       │
│ ┌ QStackedWidget: only this area changes when a tab is chosen ──────────────────────┐ │
│ │ Live: Card (image, stretch 55) │16│ Card (reading, stretch 45)                       │ │
│ └────────────────────────────────────────────────────────────────────────────────────┘ │
│ 16 px                                                                                  │
│ Status_Strip_Cls (hairline-divided cells)                                              │
│ 16 px                                                                                  │
│ Funding_Row_Cls (90 px purple band)                                                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

- Gaps between cards are always 16 px (`Style.CONST_GAP`). Card padding is 16 px.
- Style the root with an id selector (`Qss.Root('root')`): project-style-rpx `references/ui.md` § *Qt quirks*.
- The header, the status strip and the band stay fixed. A tab only changes the stacked page, and each page keeps its
  state.
- Open the window with `showMaximized()`. F11 toggles full screen and Esc closes: these are AnyScan's keys, kept for
  a station console.
- Startup order (high-DPI attributes, then the `QApplication`, then `Style.Load_Fonts()`): project-style-rpx
  `references/ui.md` § *Qt quirks*.

## 2. Header (`Header_Cls`)

Left to right: the **product lockup** (`Logo_Lockup_Cls`), 32 px from its ink to a **34 px grey-lilac rule**, 32 px
from the rule to the **JIC Smart Factory logo** (`jic-smart-factory.svg`, the purple horizontal lockup, 26 px tall
beside a 54 px product lockup and scaled with it), a stretch, the **view tabs** (a `Segmented_Control_Cls`, centred
between two stretches), and the **status pills** at the right. Margins are 4 · 20 · 4 · 18 and spacing is 16.

- **Space from ink, not from boxes.** `Style.Ink_Insets(widget.Render())` measures a render's transparent margins,
  and the layout subtracts them from the 32 px gap.
- **The lockup** is the delivered, *outlined* logo without its tagline, drawn as an SVG, with the tagline set as live
  Public Sans Regular text exactly where the outlines place it. Derive the position from the outlined logo: the pen
  origin is the "T"'s ink left minus 0.023 em, the baseline is the outlined baseline, and the size is the outlined
  cap height ÷ 0.723 (Public Sans' cap height). Outlined small text is soft at DPR 1 (0.009 of its ink at full
  contrast at 54 px); live text is hinted at 9 pt and above. Test the live tagline against the outlined one to within
  1 device px at both densities.
- **Lockup height.** It is 54 px on a high-density display. On a low-density display it is the smallest whole
  height at which the tagline reaches 9 pt (`Style.Logo_Height`): 69 px at 96 dpi.
- **Both logos' marks are grid-fitted at DPR 1** (see `grid-fit.md`). For the JIC logo, the J-I-C bars end at 449.44
  viewBox units and the lettering starts at 516, so `mark_right` is 452 with the default thin-gap threshold of 10 px.
- **The window title** is `Product  ·  Tagline` (two spaces each side of the middle dot).
- **Status pills** (`Status_Pill_Cls`, 31 px tall, square, padding 0 12 px, 9 pt DemiBold). Each state differs on
  three channels at once: dot, colour and outline.

  | State | Words | Border | Words colour |
  |---|---|---|---|
  | Offline / idle | `●  Camera offline` | `#E1DCE6` solid | `CONST_INK_MUTE` |
  | Connected / ready | `●  Camera connected` | `#3DBE4C` solid | `CONST_OK_INK` |
  | Working | `◐  Loading configuration…` | `#FFC226` solid | `CONST_WARN_INK` |
  | Not loaded | `○  Configuration not loaded.` | `#640ABA` **dashed** (Qt draws a 1 px dashed border as dots, as in AnyScan) | `CONST_INK_MUTE` |

  A pill that also names something (the model set) shows a 1 px-cell pixel icon (`model`) and the name in 9 pt
  DemiBold before the state, which is 9 pt Regular. Until the thing is in force, the name is `—`.

## 3. Cards (`Card_Cls`) and card heads (`Card_Head_Cls`)

- A card is white with a 1 px `#E1DCE6` outline, **square corners** and 16 px padding. It exposes `card.box`.
- A head holds a **24 px pixel icon** (2 px cells, a 2 px top margin that drops it 1 px below centred, so its ink centres 1.5 px above the title's capitals),
  a 10 px gap, the **title** in 15.5 pt Bold tracked −2 % in the purple, a stretch, and at most one badge, or a
  `badge_row`. Its margins are 2 · 2 · 2 · 14. `head.box` takes extra widgets: insert a state marker after the title
  with `head.box.insertSpacing(2, 6); head.box.insertWidget(2, marker)`, or add a right-aligned toggle at the end.
- Every card head has an icon from the one pixel set (`pixel-icons.md`). Pick the icon by meaning, as AnyScan does:
  `camera` for a live camera view, `image` for a stored frame, `text` for a reading, `magnifier` for detection,
  `gauge` for confidence, `folder` for records, `log` for a session log, `gear` for configuration, `checklist`,
  `ruler`, `target`, `area`, `catalogue`, `station`, `window` and `focus` where they fit.
- Content sits in a **framed scroll area** (`Style.Scroll_Style(framed=True)`: a hairline border, a 9 px trackless
  bar with a square periwinkle handle) with 18 · 18 · 18 · 16 inner margins. **Meta rows** go under it (section 10).
- A chart card adds a subtitle of one sentence in 10.5 pt `CONST_INK_MUTE` under the head (`Charts.Chart_Card`).

## 4. Badges (`Badge_Cls`) and the badge row (`Badge_Row_Cls`)

- A badge is 24 px tall, 8 pt Bold, padded 0 9 px, square, with a 1 px border the colour of its ground. The words are
  always the purple, on the state's ground: `ok` on the periwinkle `#C2C9FF`, `fail` on `#FFD9D0`, `warn` on the amber
  `#FFC226`. Any other level is **idle**: muted words on the white card inside a grey-lilac rule.
- The words carry the state as well as the colour, so the badge still reads without colour: `All OK`, `NOK · 2`,
  `Warning · 1`, `No frame`, `Idle`, `Empty`, `Live · 3.7 fps`, `1920 × 1200 · RGB`.
- **One badge per state that needs the person, all at once**: NOK first, then Warning (every kind counted together),
  and `All OK` when there is neither. A Warning is never hidden behind a NOK. The row is right-aligned and wraps onto
  a second row (`Flow_Layout_Cls`) rather than clipping. A badge row takes all the width the title leaves.
- A swatch beside a filter segment or a legend entry (`Swatch_Icon`, 10 px) is the state's colour edged in that same
  colour, never a darker one.

## 5. Action buttons (`Tool_Button_Cls`)

- 48 px tall, label UPPERCASE in 9.5 pt DemiBold tracked +6 %, with a minimum width of the label plus 10 px each side.
  Buttons expand to share the row, with 12 px spacing and 16 px above the row. They use a pointing-hand cursor.
- **Exactly one primary per row** (AnyScan's ANALYZE): a 2 px purple rule where the others have 1 px.

  | State | Plain | Primary |
  |---|---|---|
  | Rest | white, 1 px purple rule, purple label (9.15:1) | white, 2 px purple rule, purple label |
  | Hover | grey-lilac fill, purple rule and label (6.79:1) | purple fill and rule, white label (9.15:1) |
  | Pressed | periwinkle fill, purple label (5.71:1) | purple fill, white label |
  | Disabled | white, grey-lilac rule, `#B4A6BE` label (2.30:1, exempt) | the same, outlined on the card |

- Every state rule names its fill, border and label (`Qss.py`, rule 1); why: project-style-rpx `references/ui.md` § *Qt
  quirks*.
- A disabled control says "not available" through its fill and outline, and stays visible. Give a disabled button a
  tooltip naming what enables it (`Connect the camera first.`, `Load a configuration first.`).
- The order of the row follows the order an operator uses the buttons in (configuration, connect, disconnect,
  preview, scan, the primary action, clear in AnyScan). Name a button for its action in one word.

## 6. Segmented controls (`Segmented_Control_Cls`)

There is one segmented control for every selector: header tabs, a view toggle (Annotated / Mask / …), a filter
(All / OK / NOK / Warning). It is 30 px tall, 9 pt DemiBold tracked +2 %, and each segment has 0 16 px padding.
Neighbours share one 1 px rule, so each segment after the first has no left border. The checked segment is purple
under white. An unchecked hover is grey-lilac with a purple label; a checked hover keeps purple under white. The
first segment starts selected. `Segment_Selected` fires on user clicks only, and `Set_Selection` restores a choice
without emitting. A state filter puts each state's `Swatch_Icon` before its label. An unavailable choice stays
visible but disabled.

## 7. Status strip (`Status_Strip_Cls`, `Stat_Cell_Cls`)

- The strip is a card with no padding, whose cells are separated by 1 px vertical hairlines and stretch equally.
  Each cell has margins of 20 · 13 · 20 · 13 and 5 px spacing.
- Each cell has an UPPERCASE caption (8 pt Bold, +7 %, `CONST_INK_MUTE`) over its value: a **count** in 18 pt Bold
  (read from the back of a room), a **state** in 13.5 pt DemiBold with a coloured dot (`Set_Value(text, color,
  dot_color)`, the words in the colour's text twin), or a **machine value** in 12 pt JetBrains Mono Medium.
- **Order:** device state first (camera, resolution, system, last update), then run counts (images analysed, objects
  detected), then derived aggregates last. An aggregate's label names its scope and statistic: `Inference (run
  median)`, `Confidence (run mean)`.
- **Reserve widths** (`Reserve_Width`) for the widest value each cell can show, with every digit standing for any
  digit, so a changing value never moves the columns beside it.
- Values that are not known yet show `—`. The System cell is never green just because the app started: it shows the
  most pressing real state (`Analysis failed`, `Error logged`, `Models not loaded`, `Camera disconnected`, `Ready`).

## 8. Image view (`Viewport_Cls`) and its state

- **Ground** is the grey-lilac `#E1DCE6`. The image is letterboxed and centred, with the draw rectangle recomputed on
  every paint, and that maths lives in one place. The minimum height is 320 px.
- **The state marker** (`State_Marker_Cls`) sits in the image card's head, right after the title, never inside the
  image. It is white on a solid purple block (9.15:1), 9.5 pt DemiBold +6 %, with padding 12 · 6 and the width of its
  widest state, so it never jumps. It shows:
  - `●  LIVE PREVIEW` while live frames show;
  - `SCANNING…` with the `camera` pixel icon (2 px cells, the lens blinking) while a capture waits;
  - `ANALYZING…` with the `magnifier` icon (the glint stepping) while analysis runs.

  Unlit animation cells are white at 18 %. A new state joins `CONST_STATES` and is never painted into the view.
  `Viewport_Cls.Marker_Changed` feeds it. The step's progress (`Segmenting…`, `Analysing object 3 of 8…`) goes in
  the head's badge.
- **Empty view.** The product mark (an SVG rendered as vectors at paint time, up to 210 px or 44 % of the width) sits
  centred above an instruction in 9.5 pt purple, both at 92 % opacity (the purple at 92 % on the grey-lilac is
  6.08:1). The instruction names the step available now (`Connect a
  camera, then press Scan to capture a frame.`). In the top-right corner sits the **poster's pixel cluster**: 6 × 4
  cells of 16 px, 9 filled (`....L.`, `L....D`, `.D.L.D`, `.DD.L.`), the purple at 7 % (L) and 12 % (D). It is
  decoration, gone the instant a frame shows. The brand's squares appear only here and in the funding band, never in
  a data area (a reading, a log, a chart, a history list).
- **Busy overlay** (`Start_Busy(text, icon)`), used only for a threaded step that is not over a frame being judged,
  such as connecting or a close waiting for a worker. It lays the view's grey-lilac at 70 % over everything, then the
  task's pixel icon in **5 px cells** centred with its bottom 6 px above the view's centre, and the step in 9.5 pt
  purple 14 px below the centre. The camera icon blinks its lens (2 steps × 5 ticks of 120 ms); the magnifier moves
  its glint (4 steps × 3 ticks). Over the empty view the mark and instruction are hidden, but the corner cluster
  stays. The timer runs only while the overlay shows.
- **Analysis grid** (`Start_Analysis` / `Stop_Analysis`) is the only thing drawn over a frame while it is worked on,
  and it is decoration: the same drawing over any frame, never tinted by what lies under it. It has 48 square cells
  across the image, 1 px periwinkle lines at 55 % on whole pixels, and cells filled with `#CC9EF1` at 30 %. A band of
  30 % of the diagonals enters at the top-left and crosses in 0.5 s, fading behind in two steps (55 %, 25 %, each 8 %
  of the diagonals), then the frame rests clean for 0.25 s and the loop repeats (≈ 1 s). It repaints every 40 ms,
  and only the cells the wave covered or covers. The grid is rendered once per size and clipped per step. It stops at
  once when the work ends: the next paint is the result. It is painted on screen only, never into a saved image.
- **Every animation** (the grid, a busy icon, a marker's icon) repaints only while it runs and only what changes: its
  timer stops when it ends, and a tick repaints the cells it changed, not the whole view.
- **Inspection area** (`Paint_Inspection_Area`): 1 px, solid, square, unfilled, on whole pixels, unantialiased, and on
  screen only. It is light amber `#FFD880` over a camera image and the purple over the empty view.

## 9. Funding band (`Funding_Row_Cls`) and the EU disclaimer

- **What it is.** The project and funding obligation, shown as part of the product. It is a solid purple band, 90 px
  tall (six 15 px motif cells) at every width, at the foot of the window under the status strip, 16 px below it, the
  full content width, square. Its border is the purple itself.
- **Logos**, in one group centred as a whole, 32 px apart, all solid white SVGs rendered as vectors: the
  **EDIH-DIGIMAT** wordmark at 24 px, a **vertical rule** (white at 20 %, 75 % of the tallest logo = 34 px), the
  **Ministry of Industry and Trade** of the Czech Republic at 46 px (its lion white without its field, as Czech
  ministries show it on dark grounds), and the **EU emblem with "Funded by the European Union"** at 46 px. The
  heights were chosen so the three look equal by eye. The EU emblem must be at least as tall as the largest other
  logo, as the EU visibility rules require. Because the group is centred as a whole, the rule falls slightly left of
  the band's middle.
- **Pixel motif.** White squares at 7 % and 12 % (40 % of squares in the stronger tint) on a 15 px grid, densest at
  the band's two ends (a 30 % chance at the edge, falling linearly to zero 16 cells in), from a fixed hash, so the
  pattern is the same on every machine and a resize adds or removes squares next to the logos without reshuffling.
  **No square comes within 28 px of any logo** (`CLEAR_SPACE`). This is at least the EU emblem's protection area,
  half the flag's height (23 px at 46 px), which "must remain free of competing texts, logos, images or any other
  visual element".
- **The EU disclaimer**, word for word, is kept once in code (`Funding_Row_Cls.DISCLAIMER`):

  > Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not
  > necessarily reflect those of the European Union or European Commission. Neither the European Union nor the
  > granting authority can be held responsible for them.

  **Usage rules:**
  - Never paraphrase, shorten, translate or re-wrap it into other words; copy it from the one constant.
  - It is **not** shown in the window's band (the owner's choice for the station screen). It **is** carried by the
    README's Funding section (under the band image) and by any generated or printed band: an architecture diagram, a
    poster or a slide. There it sits under the logos and a faint rule, in two lines, white at 76 % (5.72:1).
  - If the funding's publicity rules change to require it on screen, add it to the band; do not move it elsewhere.
  - The README's band image is generated from the same logo list, sizes, rule, clear space and motif, never drawn by
    hand. It is 1000 × 90 on its own purple, so it reads on GitHub's light and dark themes alike.
- The band's three logos are **traced** SVGs (potrace from the official white PNGs), not official vector files. Each
  file says so in a comment. Replace them when official vectors are supplied. See `assets/logos/USAGE.md`.

## 10. Smaller pieces

- **Meta rows** (`Meta_Row`) are key/value rows under a 1 px rule. The key is 10 pt purple; the value is right-aligned,
  10 pt Medium, or 9 pt JetBrains Mono for a machine value. Each row has 9 px vertical padding, or 6 px when compact.
  A value starts as `—`. Label each value with the scope it covers (`Inference time` is this frame;
  `Inference (run median)` is the run).
- **Hairlines** (`Style.Hairline`) are filled 1 px widgets, never a `QFrame.VLine` (project-style-rpx `references/ui.md`
  § *Qt quirks*).
- **Scroll areas** take `Style.Scroll_Style(framed)`, the one scroll style.
- **A modal dialog** dims the window with `Style.Scrim_Color()` (the purple at 16 %) on a child widget
  (`WA_StyledBackground`). The dialog's title carries a pixel icon through `Icon_Cls.Head_Layout(name)`.
- **Empty states are instructions.** They name the step available now, change as the person progresses, and never
  show a standing "Ready" before something is actually ready.
- **A thumbnail or list item when selected** gets a 2 px outline in its worst state's colour (NOK, then Warning, then
  OK). A detect-only item uses the neutral `#655E6D`, and a failed item the muted ink. Otherwise it has a 1 px
  grey-lilac outline.
