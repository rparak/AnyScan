# AnyScan — PyQt5 console

*The camera sees, the model describes.*

One script, `run.py`, reproducing the approved AnyScan design as a desktop
application. Built at JIC within the EDIH-DIGIMAT project.

## Setup

Create an isolated environment and install the runtime + test dependencies
(Python 3.9–3.12; developed and characterized on 3.10):

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`.venv/` is git-ignored. `pypylon` (the Basler SDK) installs a platform wheel and
is only needed for the live camera; the tests and the `--frame` path run without
it.

The vision pipeline loads a local Florence-2 model from
`models/florence2-large-ft/`, which is **not** tracked in git. It is a required
setup step: the weights (Microsoft Florence-2, MIT licensed) must be present at
that path before `python App/run.py`, or ANALYZE fails with a message telling
the operator the runtime is missing. Download them with:

```bash
huggingface-cli download microsoft/Florence-2-large-ft \
    --local-dir models/florence2-large-ft
```

Upstream source: <https://huggingface.co/microsoft/Florence-2-large-ft>. See
`models/.gitkeep` for the expected directory contents and alternative fetch
methods (git-lfs).

## Run

```bash
python App/run.py
```

The console drives a Basler camera and the local Florence-2 model — both real,
no mocks. The window still opens when either is absent and reports an actionable
sentence when a missing component is first used, so **CONNECT → SCAN → ANALYZE**
degrades one step at a time rather than failing at startup. `F11` toggles
fullscreen, `Esc` closes.

For a run without the camera, pass a real frame previously saved from it. The
pipeline differences the frame against the reference background, so the frame
must match that background's resolution — 1920×1200 (ANALYZE still needs the
model weights):

```bash
python App/run.py --frame path/to/frame.png
```

Without Inter and JetBrains Mono installed, the nearest system faces are used.
The layout holds either way; the metrics shift slightly.

## Tests

Two nets, both running with no camera and no model weights.

**Unit suite** (`pytest`), under `test/`, mirroring `src/` as
`test/<Domain>/test_<module>.py`. Tests grow alongside each module as the
single-file app is split into `src/`:

```bash
pytest                 # the default run; needs neither camera nor weights
pytest --runslow       # also runs tests marked `slow` (these need the weights)
```

**Characterization harness**, the coarser end-to-end regression baseline for the
refactor. It exercises the composer, the label distiller, the dataclasses and the
background subtraction on the committed `Data/Camera/` reference and writes a
deterministic `Example/Vision/characterize_baseline.log`:

```bash
.venv/bin/python Example/Vision/characterize.py
git diff Example/Vision/characterize_baseline.log     # expect no change
```

## Repository layout

What is committed, and what you must supply:

```
App/
  run.py                  the application (entry point)
  assets/                 UI images, committed
    brand-jic.png           header mark
    edih-digimat-dark.png   project wordmark, footer
    partner-ministry.png    Ministry of Industry and Trade
    funder-eu.png           Co-funded by the European Union
    anyscan-mark.png        the AI mark shown in the empty viewport
    icon.png / icon.ico     window icon; multi-size Windows icon
    fonts/                  optional: drop Inter.ttf and JetBrainsMono.ttf here
src/                      the project libraries (Basler, Calibration, …)
Example/                  runnable camera scripts (record, scan, calibrate)
Data/                     runtime INPUT consumed by the app — committed
  Camera/                   the reference background and calibration-result images
    Image_Background_001.png  the empty-surface reference ANALYZE subtracts
images/                   documentation illustrations for this README — committed
models/                   model weights — you supply these, NOT committed
  florence2-large-ft/       Florence-2, downloaded per Setup (git-ignored)
```

`Data/` is application input and `images/` is documentation — kept apart on
purpose. `Data/Camera/` holds the reference background and the calibration-result
images `Example/Camera/calibrate.py` writes, and all of it is tracked. Only
`models/` is user-supplied.

If a logo file is missing the console prints its filename in that slot rather
than silently leaving a gap, so a broken asset path is visible immediately.

## Packaging for Windows

```bash
pip install pyinstaller
pyinstaller --noconsole --icon App/assets/icon.ico \
    --add-data "App/assets;assets" App/run.py
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
