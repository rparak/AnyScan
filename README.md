# AnyScan — PyQt5 console

*The camera sees, the model describes.*

One script, `run.py`, reproducing the approved AnyScan design as a desktop
application. Built at JIC within the EDIH-DIGIMAT project.

![AnyScan architecture: the configuration file, the pipeline (background subtraction and FastSAM fused, then crop enhancement, Gemma 4, the composer and the measurement), the shared outputs, and the import layers](images/anyscan-architecture.svg)

The diagram shows how a frame becomes a reading. Two independent cues are fused, so an object
is kept if **either** one finds it. It also shows where each configuration section enters, and
which layer may import which. [Detection logic](#detection-logic) walks through the same stages
in text.

## Setup

**Platform: macOS on Apple silicon** is the supported, measured platform; Linux is a
target, not yet measured (see [Platform](#platform)). The installer does
the whole setup below — the virtual environment, the dependencies matched to the hardware
(Metal on Apple silicon; on Linux, MLX's CUDA 12 or CUDA 13 backend chosen from the NVIDIA
driver, on a card whose memory it reads), and both models, each verified by checksum and
skipped when already present. It is safe to re-run:

```bash
./install.sh                 # or ./install.sh --detect-only to see what it would do
```

On Linux it stops, naming the card and its memory, when GPU 0 has less than 11 GB or there
is no usable NVIDIA GPU; `--cpu` installs the CPU builds instead (unmeasured, expected to be
far slower). `--model 12b` installs Gemma 4 12B in place of E4B. It prints what that choice
means and the configuration field to set; it never edits a configuration. See
[Platform](#platform) for the model matrix.

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
from `models/FastSAM/FastSAM-x.pt` (~140 MB), likewise **not** tracked in git.
Fetch it with ultralytics and move it into place:

```bash
python -c "from ultralytics import FastSAM; FastSAM('FastSAM-x.pt')"
mkdir -p models/FastSAM && mv FastSAM-x.pt models/FastSAM/
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
  - the FastSAM model and its settings (device, confidence, IoU, image size)
  - the **background reference** (`Segmentation.Background.Reference`) every frame is differenced
    against. It carries a provenance sidecar (`Image_Background_NNN.json`), written by
    `Example/Camera/make_reference.py` from the capture set it was made from
  - the background-difference and fusion parameters
- **Description:** the Gemma model, the two prompts, temperature, max tokens, the background crop
  margin and the background-sentence limits.
- **Confidence:** the 80% / 60% warning and error thresholds.
- **Evaluation (harness-only):** `Evaluation.Frames`, the test frames `Example/Vision/analyze.py` runs
  on (`Data/Images/Test`). The application never reads it, so the loader only resolves the path and a
  missing directory never stops it loading; `analyze.py` checks the directory and each frame's size
  against `Camera.Resolution`.
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

## Limitations

Two limitations affect any decision built on this application's output. Both stand **unverified in
this version**: nothing here checks them against ground truth, and none of the captures in
[docs/capture-checklist.md](docs/capture-checklist.md) changes that. Behaviours that show up in the
text but decide nothing are in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

### Measurements are repeatable, not absolute

**Don't build a tolerance on these numbers.** A part's size varies with its thickness and with where
it lies in the frame: a 12 mm hex nut, 6 mm thick, reads about 0.2 mm large at the frame centre and
about 1.5 mm large near the edge, so a fixed tolerance would pass the part in one place and reject it
in another. Nothing in this version verifies the absolute scale either, so the overall error's
magnitude is unknown. Comparing like parts in like positions works; deciding whether a part is within
a stated tolerance does not.

- **Repeatable:** the same plate in `Image_002`–`005`, placed differently, measures 57.7–58.5 ×
  37.9–39.1 mm. Repeatability says nothing about correctness — a wrong scale is the same in every frame.
- **Position and thickness:** one camera with an ordinary lens, looking down, sees a thick part's
  outline partly above the plane it was calibrated in, and off the optical axis sees its side wall
  too. Along the direction away from the axis a size reads **W + X · t / (Z − t)** — footprint width W,
  thickness t, the far edge X from the axis, the lens Z above the table (~360 mm). The excess grows
  with the distance from the axis, not with the part's size: the nut above gains ≈ 1.5 mm at X ≈ 90 mm,
  and even centred it gains W · t / (Z − t) ≈ 0.2 mm, so a 0.1 mm tolerance cannot be held for it
  anywhere in the frame. An across-flats width is largely spared; a round Ø takes about half. Only a
  telecentric lens removes this.
- **Scale unverified:** the calibration in force was solved from a single image, and its principal
  point, (160.7, 355.5), sits about 800 px from the frame centre. The multi-view recalibration
  (checklist item 1) replaces the lens model, but nothing in this version checks the resulting scale
  against parts of known size.
- Sizes are shown to 0.1 mm because that is one pixel at 0.098 mm/px, not because they are accurate
  to 0.1 mm.

### The describer is not a defect detector

**A description without a stain is not evidence there isn't one.** Whether a stain, scratch or
corrosion is reported depends on how the part is framed, and nothing in the output marks a miss: a
clean-sounding description of a stained part looks exactly like a correct description of a clean
one. Treat surface condition in the text as a hint that may be absent, never as a finding.

- **Evidence:** the rust on `Image_002`'s plate — the stain the object prompt was written to catch —
  is named at crop paddings 0.20 and 0.36 and missed at 0.00–0.12 and 0.28. The text is identical on
  every run at a given padding, so this is a step with the framing, not sampling noise. The shipped
  padding (0.20) happens to report it. It rests on one stain on one frame, which is a reason for more
  caution, not less.
- **Why:** a stain is a texture on a surface, not an object with a boundary, and describing a part is
  not detecting a defect on it. The route for defects is anomaly detection inside the part's mask,
  feeding the classification switch (`General.Classification.Enabled`) that is already wired and has
  no rule yet. It is not built in this version.

## Captures on the rig

Three captures only the rig can produce, in this order: a **multi-view calibration set**, then the
**empty-surface reference** shot under the new calibration (made with `make_reference.py`, which
writes its provenance sidecar), then a **parts session** — defective parts with clean controls,
low-contrast parts, and a harsh shadow. The procedures, the conditions and what to record alongside
each frame are in [docs/capture-checklist.md](docs/capture-checklist.md). None of them verifies the
measurements (see [Limitations](#limitations)).

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
(`models/FastSAM/FastSAM-x.pt` and `models/gemma-4-e4b-it-4bit/`). When either is absent it prints an unmissable
`REAL VISION PATH NOT VERIFIED` banner and passes,
so a fresh clone is never broken — but that path is then unverified. To verify it,
download the weights (see [Setup](#setup)) and run:

```bash
pytest                 # the real-model smoke now runs
```

**Characterization golden file.** `test/Vision/test_characterize.py` snapshots the logic that
needs no camera and no model — the report composer's sentences for three scenes, the label
distiller on Gemma's own descriptions, the dataclass defaults, and background subtraction's object
count on the committed reference — and compares it with `test/Vision/data/characterization.txt` in
every `pytest` run. It holds no toolchain detail (versions, pixel counts, box coordinates), so a
dependency bump does not fail it. For an intended behaviour change, regenerate it and review the diff:

```bash
pytest test/Vision/test_characterize.py --update-golden
git diff test/Vision/data/characterization.txt
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
Example/                  runnable scripts (scan, calibrate, make_reference, analyze, architecture_diagram)
Data/Images/Test/         the seven frames analyze.py runs on, and the tests' pinned set — committed
Data/Images/Background/   the empty-surface reference(s) and their provenance sidecars — committed
Data/Images/Calibration/  calibration capture sets (calibrate.py --capture) — git-ignored
Data/Results/             analyze.py and scan.py output — git-ignored
  Camera/                   the reference background and calibration-result images
    Image_Background_001.png  the empty-surface reference ANALYZE subtracts
images/                   documentation illustrations for this README — committed
models/                   model weights — you supply these, NOT committed
  gemma-4-e4b-it-4bit/      Gemma 4 E4B (MLX), downloaded per Setup (git-ignored)
  FastSAM/FastSAM-x.pt      FastSAM, downloaded per Setup (git-ignored)
```

`Data/` is input and output and `images/` is documentation — kept apart on purpose. The test
frames and the reference are tracked; the calibration captures (about 4 MB a frame, 20+ a set) and
the analysis output are not — a calibration records the directory it was solved from. Adding a
frame to `Data/Images/Test/` changes what "the seven frames" means for every pinned expectation, so
it is a deliberate move, never a side effect of a tool. Only `models/` is user-supplied.

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
| **Linux** | **Supported target, never run** | MLX's CUDA backend on an NVIDIA GPU with at least 11 GB (the installer reads GPU 0's memory and refuses below it; `--cpu` opts into the CPU backend). **Nothing has run on Linux:** not the application, not the installer, not either model. Speed, memory and whether the text comes out identical are all unknown; the ~8.5 GB (E4B) and ~10.5 GB (12B) GPU figures are estimates. The prompts were tuned for E4B on MLX; a different model reads them differently (measured for the 12B, below). |
| **Windows** | **Not a target, untested** | Nothing known prevents it — `mlx` publishes Windows wheels — but it is not supported and has never been tried. |

**The describer models.** Both are 4-bit MLX conversions, so the same describer loads either
on every backend. Only the configuration's `Description.Model` chooses between them.

| Model | Repository @ revision | Download | Provenance | Status |
|---|---|---|---|---|
| **Gemma 4 E4B** (default) | `mlx-community/gemma-4-e4b-it-4bit` @ `475b908` | 5.2 GB | **Named:** its card gives its source, `google/gemma-4-E4B-it` at revision `fee6332`, where the licence was checked | The measured describer: 2.20 s per object, 9.35 GB pipeline peak on Apple silicon. The prompts were tuned on it. Installed on every platform unless `--model 12b`. |
| Gemma 4 12B (`--model 12b`) | `mlx-community/gemma-4-12B-it-4bit` @ `73bcf09` | 6.8 GB | **Weaker, plausible not proven:** the card names no base model, revision or licence. Its `tokenizer.json` is byte-identical to `google/gemma-4-12B-it`'s and its text configuration matches field for field. | Measured on Apple silicon against E4B: 5.46 s per object (2.5×), 10.45 GB peak. It names rust and one hex nut E4B misses, but reads three of `Image_001`'s four plastic parts as metal. **Not recommended.** On Linux it needs a card with at least 15 GB. |

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
  choices from the NVIDIA driver it finds, after checking GPU 0's memory (11 GB minimum; 15 GB
  for `--model 12b`), and it warns when the card already has more than 1.5 GB in use. With
  no usable GPU it stops, naming the reason, unless `--cpu` is given. This makes Linux
  *possible*, not *verified*: no
  Linux machine has run it yet, and that includes the installer. Its Linux branches — driver
  detection, the choice of backend and PyTorch build, and the installs themselves — are
  tested with stubbed commands only, so a working `install.sh` on macOS is no evidence
  that Linux was tested. The first Linux install is the first real run of those branches;
  please report the installer's output either way. Without MLX the describer stops with a message saying so.
- **Making Linux measured** means running the seven `Data/Images/Test` frames there, with E4B so
  that the backend is the only thing that differs from the Mac, and recording what was recorded
  for Apple silicon: time per object, peak memory, and
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
