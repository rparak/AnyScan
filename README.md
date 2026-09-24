# AnyScan — PyQt5 console

*The camera sees, the model describes.*

One script, `run.py`, reproducing the approved AnyScan design as a desktop
application. Built at JIC within the EDIH-DIGIMAT project.

## Setup

**Platform: macOS on Apple silicon** is the supported, measured platform; Linux is a
target, not yet measured (see [Platform](#platform)). The installer does
the whole setup below — the virtual environment, the dependencies matched to the hardware
(Metal on Apple silicon; CUDA 12, CUDA 13 or CPU on Linux, chosen from the NVIDIA driver), and
both models, each verified by checksum and skipped when already present. It is safe to re-run:

```bash
./install.sh                 # or ./install.sh --detect-only to see what it would do
```

**Two installer paths have never run for real, and a fresh install is their first test.**
The installer has been run only on an Apple-silicon Mac that already had both models. There,
it has checked existing files and downloaded FastSAM, but it has never downloaded Gemma (the
5.2 GB `hf download` and its verification), and none of its Linux branches (CUDA 12,
CUDA 13, CPU) has run on a Linux machine. Those paths are covered by tests with stubbed
commands only. If you are the first to install on a fresh machine or on Linux, you are the
first real run of that path: if it fails, or finishes but the application does not start,
please report it with the installer's full output. Only that report can confirm the path.

By hand instead, create an isolated environment and install the runtime + test dependencies
(Python 3.10 or newer; tested on 3.10–3.12, developed and characterized on 3.10):

```bash
python -m venv .venv
source .venv/bin/activate
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
hf download mlx-community/gemma-4-e4b-it-4bit \
    --revision 475b9088d29754a3379866cf5aeb6b41acd313c2 \
    --local-dir models/gemma-4-e4b-it-4bit
```

`hf` is the Hugging Face CLI from `huggingface_hub` (in `requirements.txt`); the older
`huggingface-cli` no longer works. The repository is public and needs no token. The pinned
revision is the one this application was measured with: every file of it was checked
byte-for-byte (SHA-256 / git blob hash) against the local weights, and the command was
dry-run (10 files, 5.2 GB).

The Gemma weights are under the Apache License 2.0, **not** MIT (see [Licence
note](#licence-note)). The describer's prompts live in the configuration file (see
[Configuration](#configuration)).
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
pipeline differences the frame against the configured reference background, so the
frame must match that background's resolution — 1920×1200 (a configuration must still be
loaded, which needs the model weights):

```bash
python App/run.py --frame path/to/frame.png
```

Without Inter and JetBrains Mono installed, the nearest system faces are used.
The layout holds either way; the metrics shift slightly.

## Configuration

Everything a user can change without touching code lives in one file per mode,
`Configuration/Config_<Hardware>_Mode_<Mode>.yaml`, for example
`Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Seg_Anything.yaml`. The hardware comes first so
camera-specific data still separates by camera; the mode comes after, so it is visible. The file
holds:

- **Identity:** the name shown in the Configuration dialog ("Cfg. Segment Anything"), the model set
  shown in the header ("JIC_AnyScan_All_v1"), and the Task a reading is labelled with.
- **Segmentation:**
  - the FastSAM model and its settings (device, mode, confidence, IoU, image size)
  - the **background reference** (`Segmentation.Background.Reference`) every frame is differenced
    against. It carries a provenance sidecar (`Image_Background_NNN.json`), written by
    `Example/Camera/make_reference.py` from the capture set it was made from
  - the background-difference and fusion parameters
- **Description:** the Gemma model, the two prompts, temperature, max tokens, the background crop
  margin and the background-sentence limits.
- **Confidence:** the 80% / 60% warning and error thresholds.
- **General.Classification.**
- **Camera:** acquisition settings; the **sensor window** (`Camera.Resolution`, `Camera.Offset`:
  1920 × 1200 centred at (8, 8) on the 1936 × 1216 sensor), which is set on the camera on every
  connect and read back; and the camera, lens and lighting as a person names them.

The calibration is not in the mode file. It lives once per camera in
`Configuration/Calibration_<Hardware>.yaml`, and every mode on that hardware shares it, as it
shares the run summary (`logger/log_<Hardware>.csv`). A camera with no calibration file yet still
loads, with a warning: frames are not undistorted and sizes are not reported until
`Example/Camera/calibrate.py` has created the file.

`Configuration.Core.Load_Configuration` is the only code that reads these files. It checks the whole
file before anything is applied:

- A missing **required** field (the hardware, a model path, the background reference, a prompt,
  the display name or model set, the camera's acquisition settings or sensor window) fails the
  load and names it.
- What depends on the sensor window is checked against it: a background reference of another size
  fails the load, naming both sizes, and so does a calibration solved at another window. The
  camera never takes its size from the reference. A calibration that does not record its window
  loads with a warning for now (see `docs/design-decisions.md`).
- The background reference is checked against its sidecar: it must be the image the sidecar
  describes, shot at the camera's window, undistorted with the calibration in force, and under the
  lighting `Camera.Lighting` names. The window and calibration checks are structural; the lighting
  check compares two typed fields, so **changing the lamp without updating `Camera.Lighting` goes
  unnoticed**. A reference without a sidecar loads with a warning for now.
- A missing **optional** field takes the default written in the file's comments, and the log says so.
- A value that is present but invalid fails the load; it never falls back to a default.

**Order of a run:**

1. The application starts with its configuration (`--config`, default above) named but **not
   loaded**. The header's model pill reads *Configuration not loaded.* (dashed outline), and
   CONNECT is unavailable until a configuration is loaded.
2. **CONFIGURATION** opens a dialog listing the configurations in `Configuration/` by name, with the
   one in force marked. Pick one and press **Load**: it loads in the background with a progress bar,
   then says what was loaded and closes. On failure it says why, and the previous configuration
   stays in force.
   - Files that cannot be loaded are not listed; the log names each with the reason.
   - Configurations for other hardware are shown greyed; changing camera means restarting with
     `--config`.
3. The header reads *Configuration loaded.* and CONNECT becomes available.
4. After the first CONNECT, the configuration is fixed for the rest of the run. Changing it means
   restarting the application. The configuration's name is on the session-start log line, and every
   capture set records the configuration, its background reference, and the camera, lens and
   lighting.

Recalibrating writes a new `Calibration_<Hardware>_calib-<date>.yaml` beside the one in force; a
camera's first calibration goes straight into place. Pass `--write-calibration` to overwrite the one
in force instead: `python Example/Camera/calibrate.py --images DIR ... [--write-calibration]`.
(`--write-config`, the old name, now fails with a message naming the new one.) The writer refuses to
overwrite a calibration file holding anything it does not own.

## Verifying the measurements

Nothing this application reports about size, and nothing it says about a part's condition, has been
checked against ground truth yet. The captures that would check it can only be taken on the rig;
they are listed, with their protocols and what to record, in
[docs/capture-checklist.md](docs/capture-checklist.md). Read it before trusting — or trying to
verify — a measurement, and read KNOWN_ISSUES (*Measured sizes may carry a systematic error*,
*The describer is not a defect detector*) before building any acceptance decision on the output.

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

`Vision_Pipeline_Cls.Analyze` (`src/Vision/Core.py`) runs one frame through four stages,
each in its own module, then measures the objects. Two cues find the objects and are
**fused, not gated**: background subtraction (stage 1) finds *what changed* against a fixed
empty-surface reference — cheap and class-agnostic — and FastSAM (stage 2) finds object
instances in the frame. Stage 3 ORs the two, so an object survives if **either** cue sees it
(a part FastSAM misses is kept by the difference; a dark part the difference barely sees is
kept by FastSAM), then splits the result into objects. Stage 4 crops each object — padded,
with every *other* object's pixels replaced by the reference so no neighbour is described
with it, contrast-stretched from the object's own pixels — and the Gemma describer, or the
model-free fallback, writes its description.

```
  current frame (RGB)  +  reference background
           |  (RGB -> BGR)
           v
  (1) background subtraction ......... Segmentation.Background_Foreground
           |  the foreground mask: absdiff -> blur -> floored
           |  Otsu -> open -> dilate; one of the two fused cues
           v
  (2) FastSAM segmentation ........... Segmenter.Fast_Sam_Cls
           |  everything-mode instance masks + scores; the
           |  other fused cue
           v
  (3) fusion ......................... Fusion.Fuse_Objects
           |  FastSAM union (background-like masks dropped) OR
           |  the stage-1 mask -> close -> connected components
           |  -> area filter -> left to right in row bands; each
           |  object records the cue(s) that found it
           v
      objects: mask + tight bbox (+ cue, coverage, score)
           |
           v
  (4) description .................... Describers.Gemma_Describer_Cls
           |  padded crop, neighbours removed,  OR Describe_Fallback
           |  contrast-stretched, fed to Gemma  (per CONST_DESCRIBER;
           |  with the object prompt            the fallback reads
           |                                    mask + bbox directly)
           v
      Compose -> per-object lines + verdict  (Reporting.Compose)
           |
           v
      measurement ........................ Measure.Measure_Objects
           |  size and rotation from each mask through the
           |  configured mm/px (A x B, Ø, or A/F for hex parts)
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
  `Parameters/Camera.py` — the camera / calibration structures; `Parameters/Configuration.py`
  — the loaded configuration (`Configuration_Str`) and its documented defaults.
- `Configuration/` — `Configuration/Core.py`, the one reader of `Configuration/*.yaml` (and
  the calibration writer). Every module receives its settings from it.

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
through `Configuration/Core.py`.

## Platform

The describer — Gemma 4 E4B as a 4-bit **MLX** conversion, run through `mlx` / `mlx-vlm` —
is the component that decides where the application runs. Everything else (the Qt UI,
OpenCV, FastSAM on PyTorch, the Basler driver) is portable. There are three distinct states:

| Platform | Status | What is known |
|---|---|---|
| **macOS, Apple silicon** | **Supported, measured** | MLX on the Apple GPU (Metal). 2.22 s per object (warm), 9.41 GB peak for the whole application, and output identical word for word across runs, processes and memory pressure. |
| **Linux** | **Supported target, unmeasured** | MLX runs there on a different backend (CUDA or CPU), and nothing has been run on it. Speed, memory and whether the text comes out identical are all unknown. |
| **Windows** | **Not a target, untested** | Nothing known prevents it — `mlx` publishes Windows wheels — but it is not supported and has never been tried. |

- **Determinism does not travel.** Greedy decoding (`temperature=0`) makes the *sampler*
  deterministic, but a different backend can still produce different text through
  floating-point differences inside the model. Word-for-word identical output is a
  *measured* property of the Apple-silicon build, not a guarantee. On a new platform,
  anything pinned to exact description text — tests and the characterization baseline —
  must be re-verified.
- **Installing on Linux: installable, still unmeasured.** On Linux `mlx` has no compute
  backend of its own; the backend comes from an extra chosen for the machine, kept in one
  selectable file per backend — `requirements/linux-cuda12.txt`, `linux-cuda13.txt` or
  `linux-cpu.txt` (far slower) — installed together with `requirements.txt`, which holds the
  version pin. PyTorch's CUDA build cannot be chosen by a requirements marker, so it comes
  from the matching PyTorch index (`cu126`, `cu130` or `cpu`). `./install.sh` makes both
  choices from the NVIDIA driver it finds. This makes Linux *possible*, not *verified*: no
  Linux machine has run it yet, and that includes the installer. Its Linux branches — driver
  detection, the choice of backend and PyTorch build, and the installs themselves — are
  tested with stubbed commands only, so a working `install.sh` on macOS is no evidence
  that Linux was tested. The first Linux install is the first real run of those branches;
  please report the installer's output either way. Without MLX the describer stops with a message saying so.
- **Making Linux measured** means running the seven `Data/Camera` frames there and
  recording what was recorded for Apple silicon: time per object, peak memory, and
  word-for-word stability — then re-verifying every exact-text pin.
- **Packaging:** the PyInstaller recipe this section used to give was for Windows and no
  longer applies. No packaging recipe has been verified on any platform; run from source
  (`python App/run.py`).

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

The models are presented as the configuration's model set (`Identity.Model_Set`, shipped as
`JIC_AnyScan_All_v1`). The describer's weights are Google's Gemma 4
E4B (via the `mlx-community` 4-bit MLX conversion), licensed under the **Apache License 2.0**
(<https://ai.google.dev/gemma/docs/gemma_4_license>) — **not** the MIT licence of this
repository's code. The repository's licence therefore does not cover them: they are not
redistributed with it (`models/` is git-ignored), and anyone shipping them does so under
Apache 2.0's own conditions (a copy of the licence, retained notices), not under MIT.

Gemma 4 is Apache 2.0, unlike earlier Gemma generations: Google's Gemma Terms of Use
(<https://ai.google.dev/gemma/terms>) state that they do not govern Gemma 4 and point to the
Gemma 4 licence, which is the Apache 2.0 text, and `google/gemma-4-E4B-it` is tagged
`apache-2.0` — including at revision `fee6332`, the one our weights were converted from. The
`license: gemma` tag on `mlx-community/gemma-4-e4b-it-4bit` disagrees; it looks like
converter boilerplate carried over from earlier Gemma conversions, not the upstream licence.
Checked 2026-09-24.
