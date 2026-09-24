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

The vision pipeline describes each object with a local **Gemma 4 E4B** model (4-bit MLX)
from `models/gemma-4-e4b-it-4bit/`, which is **not** tracked in git. It runs through MLX on
Apple silicon (macOS), which `requirements.txt` installs there. It is a required setup step:
the weights (~4.8 GB) must be present at that path before `python App/run.py`, or ANALYZE
fails with a message naming the missing directory. Download them with:

```bash
huggingface-cli download mlx-community/gemma-4-e4b-it-4bit \
    --local-dir models/gemma-4-e4b-it-4bit
```

The Gemma weights are under the Gemma Terms of Use, **not** MIT (see [Licence
note](#licence-note)). The describer's prompts live in `Configuration/Describer_Prompts.yaml`.
See `models/.gitkeep` for the expected directory contents.

The vision pipeline's segmentation stage also loads a local **FastSAM-x** model
from `models/sam-1/FastSAM-x.pt` (~140 MB), likewise **not** tracked in git.
Fetch it with ultralytics and move it into place:

```bash
python -c "from ultralytics import FastSAM; FastSAM('FastSAM-x.pt')"
mkdir -p models/sam-1 && mv FastSAM-x.pt models/sam-1/
```

Upstream: <https://docs.ultralytics.com/models/fast-sam/>. `ultralytics` is in
`requirements.txt`; like the describer, the window and the tests run without the
weights and report an actionable message when a missing one is first used.

## Run

```bash
python App/run.py
```

The console drives a Basler camera and the local Gemma describer — both real,
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

Three layers, none of which need a camera. Only the real-model smoke needs the
FastSAM and Gemma weights, and it degrades to a loud warning when they are absent.

**Unit suite** (`pytest`), under `test/`, mirroring `src/` as
`test/<Domain>/test_<module>.py`, plus pipeline integration tests under
`test/integration/`:

```bash
pytest                 # the default run
pytest --runslow       # also runs the `slow` failure-path tests (need the weights)
```

**Full verification of the real vision path requires the weights.** The default
`pytest` run includes a smoke test through the real `Analyze` (background
subtraction → FastSAM segmentation on the CPU → fusion → Gemma description → compose)
that runs **whenever both the FastSAM and Gemma weights are present**
(`models/sam-1/FastSAM-x.pt` and `models/gemma-4-e4b-it-4bit/`). When either is absent it prints an unmissable
`REAL VISION PATH NOT VERIFIED` banner and passes,
so a fresh clone is never broken — but that path is then unverified. To verify it,
download the weights (see [Setup](#setup)) and run:

```bash
pytest                 # the real-model smoke now runs
```

**Characterization harness**, the coarser end-to-end regression baseline for the
refactor. It exercises the composer, the label distiller, the dataclasses and the
background subtraction on the committed `Data/Camera/` reference and writes a
deterministic `Example/Vision/characterize_baseline.log`:

```bash
.venv/bin/python Example/Vision/characterize.py
git diff Example/Vision/characterize_baseline.log     # expect no change
```

## Detection logic

`Analyze` runs one frame through four stages, each in its own
module. Background subtraction (stage 1) finds *what changed* against a fixed
reference — cheap and class-agnostic — and returns two things: a change **mask**
and padded **candidate regions**. FastSAM (stage 2) turns the scene into precise
per-instance masks, which stage 3 filters down to the real objects. Its
change-coverage gate scores each mask against the stage-1 change mask — which is
why that mask skips stage 2 and reaches stage 3 directly: it is the evidence that
a mask is a genuine change and not the static table or a cast shadow. Stage 4
crops each survivor (masked by default, so a neighbour sharing the box is not
described with it) and the Gemma describer, or the model-free fallback, writes its
sentence.

```
  current frame (RGB)  +  reference background
           |  (RGB -> BGR)
           v
  (1) background subtraction ......... Segmentation.Build_Mask
           |  returns TWO outputs:
           |    - change mask ...... skips stage 2; feeds stage 3's
           |                         coverage gate (below)
           |    - candidate regions  prompt FastSAM only in 'box'
           |                         mode; the default 'everything'
           |                         mode ignores them
           v
  (2) FastSAM segmentation ........... Segmenter.Fast_Sam_Cls
           |
           v
      object masks + segmenter scores
           |
           v
  (3) mask filtering ................. Mask_Filter.Filter_Masks
           |  scores each mask's overlap with the stage-1 CHANGE
           |  MASK (coverage gate), rejects by area/border,
           |  suppresses part/whole (NMS), orders left-to-right
           v
      objects: mask + tight bbox (+ coverage, score)
           |
           v
  (4) description .................... Describers.Gemma_Describer_Cls
           |  padded crop, neighbours removed,  OR Describe_Fallback
           |  contrast-stretched, fed to Gemma  (per CONST_DESCRIBER;
           |  with the object prompt            the fallback reads
           |                                    mask + bbox directly)
           v
      Compose -> summary + per-object sentences + verdict
           |
           v
      Analysis_Str
```

Every analysis needs a reference-background capture; there is no background-free
detection path (see `KNOWN_ISSUES.md`).

## Repository layout

What is committed, and what you must supply:

```
App/
  run.py                  the application (entry point)
  assets/                 UI images, committed
    anyscan-logo.svg          the AnyScan brand lockup (topbar)
    brand-jic-mute.png        the JIC mark beside the lockup
    edih-digimat-white.png    project wordmark, funding band
    partner-ministry-white.png  Ministry of Industry and Trade
    funder-eu-white.png       Funded by the European Union
    anyscan-mark.png          the mark shown in the empty viewport
    anyscan-mark-white.ico    the window / taskbar icon (multi-size, rounded)
    icon.png                  fallback window icon
    fonts/                    optional: drop Inter.ttf and JetBrainsMono.ttf here
src/                      Qt-free domain modules + the UI (see "Source layout")
Example/                  runnable scripts (scan, calibrate, the vision harness)
Data/                     runtime INPUT consumed by the app — committed
  Camera/                   the reference background and calibration-result images
    Image_Background_001.png  the empty-surface reference ANALYZE subtracts
images/                   documentation illustrations for this README — committed
models/                   model weights — you supply these, NOT committed
  gemma-4-e4b-it-4bit/      Gemma 4 E4B (MLX), downloaded per Setup (git-ignored)
  sam-1/FastSAM-x.pt        FastSAM, downloaded per Setup (git-ignored)
```

`Data/` is application input and `images/` is documentation — kept apart on
purpose. `Data/Camera/` holds the reference background and the calibration-result
images `Example/Camera/calibrate.py` writes, and all of it is tracked. Only
`models/` is user-supplied.

If a logo file is missing the console prints its filename in that slot rather
than silently leaving a gap, so a broken asset path is visible immediately.

## Source layout — the app and the shared library

`src/` holds two things a fresh reader should not conflate.

**The AnyScan application** — everything the console at `App/run.py` actually runs:

- `Camera/` — the camera backends (`Camera_Backend_Cls`, `File_Camera_Cls`,
  `Basler_Camera_Cls`) plus the low-level pypylon driver `Camera/Basler.py`.
- `Vision/` — the vision pipeline (`Vision/Core.py`), the FastSAM segmenter, the Gemma
  describer (`Vision/Describers.py`) and the segmentation / crop / label utilities.
- `Reporting/` — the report composer, the panel's one voice.
- `UI/` — the widgets, the window, the threaded workers and the style helpers.
- `Parameters/Vision.py` — the app's data structures (`Detection_Str`, `Analysis_Str`);
  `Parameters/Camera.py` — the camera / calibration structures, populated from
  `Configuration/*.yaml` by `Camera/Utilities/Configuration.py` (the camera backend reads it).

These are the Qt-free domain modules plus the Qt UI; `App/run.py` imports only
these, and the domain half imports with PyQt5 unavailable (a tested contract).

**A shared robotics library** — inherited, reused, and **not** touched by the
application; reached only from `Example/`:

- `Transformation/` — homogeneous transforms, Euler angles, quaternions.
- `Calibration/` — checkerboard camera calibration.

`Example/Camera/scan.py` and `calibrate.py` use both halves — they drive the real
camera and calibrate it — but the app itself never imports `Transformation/` or
`Calibration/`. That is why those modules are held to a lighter style touch than
the app. The camera setup itself lives in `Configuration/*.yaml`, read and written
through `Camera/Utilities/Configuration.py`.

## Packaging for Windows

```bash
pip install pyinstaller
pyinstaller --noconsole --icon App/assets/anyscan-mark-white.ico \
    --add-data "App/assets;assets" App/run.py
```

`--add-data` matters: without it the executable starts with no logos and no
mark, because `assets/` is resolved next to the script.

## Swapping a component

Both hardware-facing parts sit behind an interface, so a replacement touches one class:

- **Camera** — subclass `Camera_Backend_Cls` (`src/Camera/Core.py`) and implement `_Open`,
  `_Close` and `_Grab`; `_Grab` returns an **RGB NumPy array**, the exchange format for the
  whole application.
- **Describer** — subclass `Describer_Backend_Cls` (`src/Vision/Describers.py`), implement
  `Load` and `Describe(crop, purpose)`, register it in `CONST_DESCRIBERS` and select it with
  `Vision.Core.CONST_DESCRIBER`. The pipeline never sees a prompt or a task token.

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

The model is presented as `JIC-AnyScan-v1`. The describer's weights are Google's Gemma 4
E4B (via the `mlx-community` 4-bit MLX conversion), governed by the **Gemma Terms of Use**
(<https://ai.google.dev/gemma/terms>) and its Prohibited Use Policy — **not** the MIT licence
of this repository's code. They are not redistributed with the repository (`models/` is
git-ignored) and are not redistributable under its licence; anyone shipping them must pass
on Google's terms.
