# Operator-facing wording

Every example is quoted from AnyScan (`src/UI/Core.py`, `src/Reporting/Core.py`, `src/UI/Views/*`, the mode
configurations). The person reading is an operator at a station, often glancing from across a workbench: say what
the state is and what to do next, in full sentences, in the same words everywhere.

## State lines

- A judged object's state is its own line, ending in a full stop:
  `State: OK.` · `State: NOK.` · `State: Warning – Outside area.`
- A Warning carries its **kind** after an en dash with spaces (` – `): `Outside area`, `Foreign object`,
  `Several parts`, `Side unclear`, `Side mismatch`. The kind is told in words because the colour is the same amber
  for every kind.
- Any state other than OK is followed by **one** `Reason:` sentence. For a Warning, that sentence states why the
  object was not judged and **the operator's action**:
  - `Reason: It lies outside the inspection area, so it is not judged: move it fully inside the area and scan again.`
  - `Reason: It is not the part, so it should not be there: remove it from the surface.`
  - `Reason: Its area is 1.99 times the part's, probably several parts touching or lying close together, so it cannot
    be judged: separate the parts and scan again.`
- For a NOK, the reason is one sentence of clauses, one per kind of finding, in a fixed order, joined `A, b, and c.`
  Counts up to ten are written as words: `Reason: There are two stains on the machined front.` Measured values go to
  the log, not to this sentence.
- A note may follow as `Note: …` when something could not be shown.
- A new Warning kind needs a name and an action, never a colour.
- A **detect-only** mode (no classification) shows no OK / NOK words at all, only the objects it found: the
  difference from a judged run is carried by wording as well as colour.

## Names: "kind – detail"

A task, a configuration's job or anything that is a kind with a specialisation is written `Kind – detail`, with an en
dash and spaces, the kind first in sentence case:

- `Catalogue inspection – Mounting plate`
- `Object detection – Any object`
- `Warning – Outside area`

Configuration display names are short and prefixed `Cfg.`: `Cfg. Mounting Plate`, `Cfg. Segment Anything`. A model
set shows its name as given (`JIC_AnyScan_Catalogue_v1`).

## Badges and counts

- The word carries the state: `All OK`, `NOK · 2`, `Warning · 3` (every kind counted together), `Empty`, `Idle`,
  `No frame`, `Error`, `Moving`, `Low confidence`, `3 found`.
- Frame metadata: `1920 × 1200 · RGB`. A live rate: `Live · 3.7 fps`. Use `×` (not `x`) and `·` with spaces.

## Status words

- Header pills: `●  Camera offline`, `●  Camera connected`, `◐  Loading configuration…`, `●  Configuration loaded.`,
  `○  Configuration not loaded.` (two spaces after the glyph).
- Status cells: `Connecting…`, `Connected`, `Disconnected`; `Analysis failed`, `Error logged`, `12 errors logged`,
  `Models not loaded`, `Camera disconnected`, `Ready`. **Never `Ready` just because the app started**: show the most
  pressing real state.
- Captions are UPPERCASE in the widget only (written in sentence case in code): `Images analysed`,
  `Inference (run median)`, `Confidence (run mean)`. **A derived figure names its scope and statistic.** A
  per-frame value carries no qualifier (`Inference time`, `Confidence (mean)`).

## State markers and working states

`●  LIVE PREVIEW`, `SCANNING…`, `ANALYZING…`, in UPPERCASE, with a real ellipsis. The step goes in the head's badge:
`Segmenting…`, `Analysing object 3 of 8…`. On the busy overlay: `Connecting to the camera…`, or a close waiting for
a worker, saying so.

## Empty states are instructions

They name the step available **now** and change as the person progresses:

- `Connect a camera, then press Scan to capture a frame.`
- `Connect a camera and scan a frame, then press Analyze. The model’s reading of the scene appears here as plain
  English text.`
- `Press Scan to capture a frame, then Analyze. …` → `Frame captured. Press Analyze to read the scene. …`
- `No analyses in this run yet.` · `No captures in this run yet. Analyse an image to begin.` · `No NOK part in this
  run.`

## Errors and refusals

An error is an **actionable sentence**: what happened, the likely cause, and what to press or do. It names the
button in capitals as it is labelled:

- `The camera is no longer reachable: it was unplugged, lost power or its GigE link went down. Check the camera and
  its cable, then press CONNECT.`
- `The live preview stopped: <the camera's own sentence> Press PREVIEW to start it again.`

A disabled control's tooltip says what enables it: `Connect the camera first.` · `Load a configuration first.` ·
`Restart to change configuration.`

## Buttons and tabs

- Buttons are one verb or noun in UPPERCASE, the label the operator's documents use: `CONFIGURATION`, `CONNECT`,
  `DISCONNECT`, `PREVIEW`, `SCAN`, `ANALYZE`, `CLEAR`. Do not reuse a tab's name for a button (AnyScan's live-view
  button is `PREVIEW` because a `Live` tab exists).
- Tabs and segments are Title-case nouns: `Live`, `Trends`, `History`, `Log`; `All`, `OK`, `NOK`, `Warning`;
  `Annotated`, `Mask`, `Heatmap`, `Similarity`.

## Typography of words

- `—` only in an empty value slot, never in prose. ` – ` (en dash with spaces) joins a kind and its detail. `·`
  separates a label from its metadata. Use typographic apostrophes (`’`) and `…` in UI strings.
- Product title: `Product  ·  Tagline` (AnyScan: `AnyScan  ·  The camera sees, the model describes.`).
- Spelling: AnyScan writes the actions in US form (`ANALYZE`, `ANALYZING…`) and the prose in British form
  (`analysed`, `Analysing object 3 of 8…`, `colour`). Keep whatever a project already uses and be consistent within
  each kind of text; a new project should pick one.
