# AnyScan — PyQt5 console

*The camera sees, the model describes.*

One script, `run.py`, reproducing the approved AnyScan design as a desktop
application. Built at JIC within the EDIH-DIGIMAT project.

## Setup

```bash
pip install -r requirements.txt
```

The vision pipeline loads a local Florence-2 model from
`models/florence2-large-ft/`, which is **not** tracked in git. Download the
weights (Microsoft Florence-2, MIT licensed) before running with the model
enabled:

```bash
huggingface-cli download microsoft/Florence-2-large-ft \
    --local-dir models/florence2-large-ft
```

See `models/.gitkeep` for the expected layout and alternative fetch methods.

## Run

```bash
pip install PyQt5
python run.py
```

Nothing else is needed. The camera and the model are both mocked, so the whole
console works with no hardware and no weights: **CONNECT → SCAN → ANALYZE**.
`F11` toggles fullscreen, `Esc` closes.

## Files

```
run.py                    the entire application
assets/
  brand-jic.png           header mark
  edih-digimat-dark.png   project wordmark, footer
  partner-ministry.png    Ministry of Industry and Trade
  funder-eu.png           Co-funded by the European Union
  anyscan-mark.png        the AI mark shown in the empty viewport
  icon.png                square 256px version, used as the window icon
  icon.ico                multi-size Windows icon, for a PyInstaller build
  fonts/                  optional: drop Inter.ttf and JetBrainsMono.ttf here
```

If a logo file is missing the console prints its filename in that slot rather
than silently leaving a gap, so a broken asset path is visible immediately.

Without Inter and JetBrains Mono installed, the nearest system faces are used.
The layout holds either way; the metrics shift slightly.

## Packaging for Windows

```bash
pip install pyinstaller
pyinstaller --noconsole --icon assets/icon.ico --add-data "assets;assets" run.py
```

`--add-data` matters: without it the executable starts with no logos and no
mark, because `assets/` is resolved next to the script.

## Wiring in the real components

Two classes, both marked `PLUG IN HERE`:

**`BaslerCamera`** — implement `_open`, `_close`, `_grab` against
`src/Basler/Core.py`, following the sequence in `Example/Camera/Scan.py`. Then
set `CAMERA_BACKEND = "basler"` near the bottom of the file. `_grab` returns a
**QImage in RGB**; that is the exchange format for the whole application.

**`FlorenceVision`** — implement `analyze(image, truth) -> Analysis`. Then set
`VISION_BACKEND = "florence"`.

Nothing else changes. That is the point of the two interfaces.

The traps that cost the most time are written into the docstrings of both
classes — read them before starting, not after.

## What the design encodes

- **The index is a contract.** The position of a detection in the list is the
  number drawn on the frame *and* at the start of its sentence, in the same
  hue. Never reorder `objects` after `compose()`.
- **Colour means something.** Green, red and amber are pass, fail and degraded,
  which is why they are absent from the object palette. Magenta marks a
  detected object. The primary button is black, so the strongest control reads
  as structural.
- **One voice.** Every sentence the operator reads is written by the report
  composer near the top of the file, so swapping the model never changes how
  the console talks.

## Licence note

The model is presented as `JIC-AnyScan-VLM-v1`. The weights are Florence-2,
MIT licensed — keep Microsoft's copyright notice with the project.
