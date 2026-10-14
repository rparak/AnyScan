# AnyScan

*The camera sees, the model describes.*

One script, `run.py`, reproducing the approved AnyScan design as a desktop
application. Built at JIC within the EDIH-DIGIMAT project.

![AnyScan architecture: in every mode the camera takes a frame, two cues, fused, find every object, and each object is described in words and measured in mm. The desktop app shows Live, Trends, History and Log. A catalogue mode adds, for each object found, recognising the catalogued part, the checks its item defines and a verdict: OK, NOK, Warning or Unspecified, and describes each object after its verdict. The mode, station, calibration, catalogue item and empty-surface reference set the stages up. Every analysis is recorded, with the session log, a run summary and the daily station events](images/anyscan-architecture.svg)

The diagram shows how a frame becomes a reading in both modes, at the top level. Two independent cues are
fused, so an object is kept if **either** one finds it. [Detection logic](#detection-logic)
walks through the same stages in detail, and [Source layout](#source-layout--the-app-and-the-shared-library)
says what each part of `src/` holds.

What the application does — its stages, modes, views, configuration sections, calibration, records,
and what has and has not been verified on hardware — is mapped in
[docs/capabilities.md](docs/capabilities.md), which links back here for setup.

## Setup

**Platform: macOS on Apple silicon and Linux with an NVIDIA GPU** are the supported platforms,
both measured; Linux on one machine, on 2026-09-29 (see [Platform](#platform)). The installer does
the whole setup below — the virtual environment, the dependencies matched to the hardware
(Metal on Apple silicon; on Linux, MLX's CUDA 12 or CUDA 13 backend chosen from the NVIDIA
driver, on a card whose memory it reads), and both models, each verified by checksum and
skipped when already present. It is safe to re-run:

```bash
./install.sh                 # or ./install.sh --detect-only to see what it would do
```

On Linux it stops, naming the card and its memory, when GPU 0 has less than 11 GB or there
is no usable NVIDIA GPU; `--cpu` installs the CPU builds instead (unmeasured, expected to be
far slower). See [Describer model](#describer-model) for what the model needs.

**Some installer paths have never run for real, and a fresh install is their first test.**
On an Apple-silicon Mac that already had both models, the installer has checked the existing
files and downloaded FastSAM. On the measured Linux machine (2026-09-29) its detection ran, on the
CUDA 13 path, and its Gemma step downloaded and verified E4B (see [Platform](#platform)). The full
install has not run on Linux, the Gemma download has not run on macOS, and the CUDA 12 and CPU
branches have not run on any machine. Those paths are covered by tests with stubbed commands only.
If you are the first to take one of them, you are its first real run: if it fails, or finishes but
the application does not start, please report it with the installer's full output. Only that
report can confirm the path. What ran on Linux, and what did not, is recorded in
docs/design-decisions.md, *The installer on Linux: detection and the Gemma download ran, the rest
did not*.

By hand instead, create an isolated environment and install the runtime + test dependencies
(Python 3.10 or newer; tested on 3.10–3.12, developed and characterized on 3.10):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip uninstall -y opencv-python
pip install --force-reinstall --no-deps opencv-python-headless==5.0.0.93
```

The last two lines leave OpenCV's headless build only. ultralytics and mlx-vlm require OpenCV's GUI
build (`opencv-python`), so pip installs it beside the headless one; its Qt plugins
(`cv2/qt/plugins`) make the window abort with "Could not load the Qt platform plugin xcb".
Uninstalling it also deletes files the two builds share, so the headless build is reinstalled whole,
at the version `requirements.txt` pins. `./install.sh` does this after every install, and
`App/run.py` refuses to start, naming these two commands, while the GUI build or its plugins are there.

`.venv/` is git-ignored. `pypylon` (the Basler SDK) installs a platform wheel and
is only needed for the live camera; the tests and the `--frame` path run without
it.

The vision pipeline describes each object with a local **Gemma 4 E4B** model,
`gemma-4-e4b-it-4bit` (4-bit MLX), from `models/gemma-4-e4b-it-4bit/`, which is **not** tracked
in git. It runs through MLX: Metal on Apple silicon, which `requirements.txt` installs there, and
CUDA on Linux, whose backend is a separate requirements file (see [Platform](#platform)). It is a
required setup step: the weights (5.2 GB) must be present at that path before
`python App/run.py`, or ANALYZE fails with a message naming the missing directory. Download them
with:

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

The catalogue modes also load **DINOv2 base** from `models/dinov2-base/` (346 MB, Apache 2.0), not
tracked in git; `./install.sh` downloads and verifies it. By hand, at the pinned revision:

```bash
hf download facebook/dinov2-base README.md config.json preprocessor_config.json model.safetensors --revision f9e44c814b77203eaa57a6bdbbd535f21ede1415 --local-dir models/dinov2-base
```

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

The console draws its text in Public Sans and JetBrains Mono, which ship with it in `App/assets/fonts/`
(static Regular, Medium, SemiBold and Bold of each, built by `Example/UI/build_fonts.py`), so it looks
the same on every platform whatever fonts the machine has. Only if that directory is missing does it
fall back to the nearest system faces.

## Configuration

The configuration is three kinds of file, each in its own folder, linked by name:

```
Configuration/Mode/Config_<Hardware>_Mode_<Mode>.yaml      Station: Station_<...>.yaml
Configuration/Station/Station_<Hardware>[_<Name>].yaml     Calibration: Calibration_<...>.yaml
Configuration/Calibration/Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml
```

A mode file names its station, and the station file names its calibration. A reference is a file
name, never a path, and resolves in its kind's folder of this repository wherever the file holding it
is. A new station or a new calibration is a new file and one changed reference; no code changes.

Everything a user can change without touching code lives in one file per mode,
`Configuration/Mode/Config_<Hardware>_Mode_<Mode>.yaml`, for example
`Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Seg_Anything.yaml`. A catalogue mode's file also names
its catalogue item, `Data/Catalogue/<item>/<item>.yaml`, which the loader reads by the same rules. The
hardware comes first so
camera-specific data still separates by camera; the mode comes after, so it is visible. What each
section of the file controls is in [docs/capabilities.md](docs/capabilities.md#configuration), and the
file's own comments give every field's default and unit.

**A station sets its own station-event directory in a local copy of the mode file, never in the
shipped one.** The shipped file keeps `logger/Station_Events`. A station copies the mode file to a
directory outside the repository, keeping its name, and changes only
`General.Station_Events.Directory` to the station's path; the station starts with
`--config <that copy>`. The copy's `Station` line resolves in this repository's
`Configuration/Station/`, and that station's `Calibration` in `Configuration/Calibration/`, so nothing
is copied or symlinked beside it, and a calibration switched in the repository is the copy's too. The
Configuration dialog lists only `Configuration/Mode/`, whose modes name `logger/Station_Events`, so on
such a station the dialog refuses them: another mode needs its own local copy too. A copy made before
2026-10-13 has no `Station` line and fails to load, naming the line to add; its symlinks are no longer
read.

The camera is not in the mode file either. Its settings — the camera, lens and lighting as a person
names them, the acquisition settings, the sensor window — the empty-surface reference and the
calibration in force live in the station file the mode names, `Configuration/Station/`: they belong to
the camera, the light and the table, so every mode naming that station shares them. A mode file never
overrides them: one that holds `Camera`, `Calibration` or a background reference fails to load and names
the station file. The station file is written by hand and committed, so it holds nothing true of one
machine only; the station-event directory stays in the local copy of the mode file.

The calibration is not in the station file. Each calibration is a file of its own in
`Configuration/Calibration/`, written by `Example/Camera/calibrate.py`, and the station's `Calibration`
line says which one is in force. Older calibrations stay beside it, so switching back is that one line.
Nothing loads without a calibration: a station that names none fails to load and says the line to add.

`Configuration.Core.Load_Configuration` is the only code that reads these files. It checks the mode
file, its station and its calibration as a whole before anything is applied:

- A missing **required** field (the hardware, the station, the station-event directory, a model path, a
  prompt, the display name or model set; in the station file, the calibration, the background reference
  and the camera's acquisition settings and sensor window) fails the load and names it, with the file it
  belongs in. A missing `Station` or `Calibration` names the line to add.
- Each link must agree: the station's `Hardware` is the mode's, and the calibration's `Hardware` and
  sensor window are the station's. A mismatch fails the load, naming both files.
- What depends on the sensor window is checked against it: a background reference of another size
  fails the load, naming both sizes, and so does a calibration solved at another window. The
  camera never takes its size from the reference. A calibration that does not record its window
  fails the load too: it cannot be checked.
- The background reference is checked against its sidecar: it must be the image the sidecar
  describes, shot at the camera's window, undistorted with the calibration in force, and under the
  lighting `Camera.Lighting` names. The window and calibration checks are structural; the lighting
  check compares two typed fields, so **changing the lamp without updating `Camera.Lighting` goes
  unnoticed**. A reference without a sidecar fails the load.
- A missing **optional** field takes the default written in the file's comments, and the log says so.
- A value that is present but invalid fails the load; it never falls back to a default.

**Order of a run:**

1. The application starts with its configuration (`--config`, default above) named but **not
   loaded**. The header's model pill reads *Configuration not loaded.* (dashed outline), and
   CONNECT is unavailable until a configuration is loaded.
2. **CONFIGURATION** opens a dialog listing the configurations in `Configuration/Mode/` by name, with the
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

Recalibrating (`python Example/Camera/calibrate.py --images DIR ...`) always writes a new
`Configuration/Calibration/Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml` and never writes over a file.
It does not edit the station file: it prints the station file's `Calibration` line, by number, and the
text to set it to (on a station with no calibration yet, the line to add below `Hardware:`). Make that
edit and restart to use the new calibration. It reads only the station's camera, so it runs on a camera
with no calibration yet. `--write-calibration` and `--write-config` are removed and fail with a message
saying so.

## Limitations

Two limitations affect any decision built on this application's output. Both stand **unverified in
this version**: nothing here checks them against ground truth, and none of the captures in
[docs/capture-checklist.md](docs/capture-checklist.md) changes that. Behaviours that show up in the
text but decide nothing are in [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

### Measurements are repeatable, not absolute

**Outside a catalogue mode, don't build a tolerance on these numbers. Inside one, trust its outline
check only for its two parts, within 75 mm of the frame centre.** A part's size varies with its
thickness and with where it lies in the frame: a 12 mm hex nut, 6 mm thick, reads about 0.2 mm large
at the frame centre and about 1.5 mm large near the edge, so a fixed tolerance would pass the part in
one place and reject it in another. Nothing in this version verifies the absolute scale either, so the
overall error's magnitude is unknown. Comparing like parts in like positions works; deciding whether a
part is within a stated tolerance does not, except where the catalogue bullet below measured it.

- **Repeatable:** on the previous test set (`Data/Images/Test/All`, 2026-09-28; no longer in the repository,
  recoverable from `1061966`), the large washer in six frames
  measures Ø 22.79–23.10 mm, and the rust-stained plate in three placements 60.92–61.10 × 39.98–40.55 mm
  (`Image_007`, and `010` and `013`, which have since left the set — recoverable from `b5ca788^`). Repeatability says nothing about correctness — a wrong scale is
  the same in every frame.
- **Position and thickness:** one camera with an ordinary lens, looking down, sees a thick part's
  outline partly above the plane it was calibrated in, and off the optical axis sees its side wall
  too. Along the direction away from the axis a size reads **W + X · t / (Z − t)** — footprint width W,
  thickness t, the far edge X from the axis, the lens Z above the table (~360 mm). The excess grows
  with the distance from the axis, not with the part's size: the nut above gains ≈ 1.5 mm at X ≈ 90 mm,
  and even centred it gains W · t / (Z − t) ≈ 0.2 mm, so a 0.1 mm tolerance cannot be held for it
  anywhere in the frame. An across-flats width is largely spared; a round Ø takes about half. Only a
  telecentric lens removes this.
- **Scale unverified:** the calibration in force is a multi-view solve from 2026-09-28. It used 63
  views (22 flat, 41 tilted) at a reprojection RMS of 0.45 px. Its principal point lies about 25 px
  from the frame centre, and its factor is 0.102 mm/px. It replaced a single-image calibration whose
  principal point sat about 800 px off centre. Nothing in this version checks the resulting scale
  against parts of known size. A good fit shows that the lens model is consistent, not that the sizes
  are right.
- **Catalogue mode:** the owner chose to check the catalogue part's outline against tolerances
  anyway, with the scale moved to the part's top face
  ([*A catalogue mode measures at its part's top face*](docs/design-decisions.md#a-catalogue-mode-measures-at-its-parts-top-face)).
  On the current test set, every instance reads within: the 22 mounting plates −0.77 to +0.76 mm off
  60 × 40 (tolerance ±1.5), with their centres up to 46.3 mm from the frame centre. **Not verified:** the
  parts were not calipered, so "within" means consistent with nominal, not a measured truth. **Not
  measured:** a plate farther from the frame centre than 46.4 mm, where the side-wall term above predicts up
  to about 1 mm more, beyond the plates' 0.73 mm margin; a size checked there carries a note.
- Sizes are shown to 0.01 mm as a formatting choice: one pixel is about 0.10 mm, and the error above
  is up to about 1.5 mm, so the second decimal — and the first — says nothing about accuracy.

### The describer is not a defect detector

**A description without a stain is not evidence there isn't one.** Whether a stain, scratch or
corrosion is reported depends on how the part is framed, and nothing in the output marks a miss: a
clean-sounding description of a stained part looks exactly like a correct description of a clean
one. Treat surface condition in the text as a hint that may be absent, never as a finding.

- **Evidence** (the previous test set, `eb00508^`; not re-run on `All/`): the rust on its `Image_002`
  plate — the stain the object prompt was written to catch —
  is named at crop paddings 0.20 and 0.36 and missed at 0.00–0.12 and 0.28. The text is identical on
  every run at a given padding, so this is a step with the framing, not sampling noise. The shipped
  padding (0.20) happens to report it. It rests on one stain on one frame, which is a reason for more
  caution, not less.
- **Why:** a stain is a texture on a surface, not an object with a boundary, and describing a part is
  not detecting a defect on it. A catalogue mode's verdict comes from named checks instead — identity,
  the outline, the holes, a stain by its colour — and the describer is told
  their findings. A defect no check names (a scratch, a dent) is detected by nothing: anomaly detection
  inside the part's mask is not built in this version.

### A catalogue mode checks only what its item lists

**An OK means the part passed the checks its catalogue item lists — not that nothing else is wrong.**
What a catalogue mode does not check, it cannot fail:

- **A hole drilled where the catalogue puts none is not reported** (KNOWN_ISSUES): holes are counted near
  their expected positions only.
- **A stain is caught by its colour, measured under this light** (KNOWN_ISSUES): a yellow-brown area of
  1 mm² or more on the mounting plate's front. A stain of another colour, or this colour under another light,
  is not verified.
- **The Similarity tab is not a defect map.** It shows where a judged part looks unlike its reference to
  DINOv2: the fingerprints show, but so does glare, and missing holes do not.
  No verdict reads it.
- **The describer's words are guarded, not trusted.** In a catalogue mode it is told what the checks found
  and given no number; a sentence with a number or contradicting a check is dropped and logged, by word
  patterns (KNOWN_ISSUES). The verdict and its reasons never come from it.

Verified on the 41 test frames only (2026-10-11), with every hole within tolerance.

## Captures on the rig

The rig's captures, in order. The first two were made on 2026-09-28 (the reference re-shot on 2026-10-12) and are in force:

1. a **multi-view calibration set**;
2. the **empty-surface reference**, shot under that calibration with `make_reference.py`,
   which writes its provenance sidecar.

Two are still to do:

3. a **parts session**: defective parts with clean controls, low-contrast parts, and a harsh shadow;
4. the **cable pull**, which checks that a lost connection is detected.

The procedures, the conditions and what to record alongside each frame are in
[docs/capture-checklist.md](docs/capture-checklist.md). Items 1 and 2 are repeated when the camera,
the lens or the mount changes. None of them verifies the
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
    anyscan-logo.svg          the AnyScan logo, a copy of images/anyscan-logo.svg; built
    anyscan-logo-wordmark.svg the logo without its tagline, which the topbar draws beside the live tagline; built
    anyscan-mark.svg          the mark alone, shown in the empty viewport; built
    anyscan-mark.ico          the window / taskbar icon: the mark on a white square, 16-256 px; built
    jic-smart-factory.svg     the JIC Smart Factory logo beside the AnyScan logo
    edih-digimat-white.png    project wordmark, funding band
    partner-ministry-white.png  Ministry of Industry and Trade
    funder-eu-white.png       Funded by the European Union
    fonts/                    Public Sans and JetBrains Mono, static, with their OFL licences; built by
                              Example/UI/build_fonts.py
src/                      Qt-free domain modules + the UI (see "Source layout")
Example/                  runnable scripts (scan, calibrate, calibration_tilt_study, generate_checkerboard,
                          make_reference, analyze, evaluate_describer, architecture_diagram, build_logo,
                          build_fonts)
Data/Images/Test/         the 41 frames analyze.py runs on (Image_055-095, each a capture set's
                          _raw.png, the undistorted frame — never its _distorted.png), and the tests' pinned set —
                          committed. No answer key yet: the previous set's named objects on frames
                          that are gone, and is kept as the scoring tests' data
                          (test/Vision/Utilities/data/answer_key_1061966.json)
Data/Images/Background/   the empty-surface reference(s) and their provenance sidecars — committed
Data/Images/Calibration/  calibration capture sets (calibrate.py --capture) — git-ignored
Data/Results/             analyze.py and scan.py output — git-ignored
images/                   documentation illustrations for this README — committed
  anyscan-logo.svg          the AnyScan logo as the JIC Smart Factory designer delivered it (outlined)
models/                   model weights — you supply these, NOT committed
  gemma-4-e4b-it-4bit/      Gemma 4 E4B (MLX), downloaded per Setup (git-ignored)
  FastSAM/FastSAM-x.pt      FastSAM, downloaded per Setup (git-ignored)
```

`Data/` is input and output and `images/` is documentation — kept apart on purpose. The test
frames and the reference are tracked; the calibration captures (about 4 MB a frame, 40+ a set) and
the analysis output are not — a calibration records the directory it was solved from. Adding a
frame to, or renumbering one in, `Data/Images/Test/` changes what every pinned expectation refers
to, so it is a deliberate move made with the pins, never a side effect of a tool — and a frame is
added under a new name, never written over an old one (docs/design-decisions.md, *A replaced image
never keeps its name*). Only `models/` is user-supplied.

**Changing the logo.** Replace `images/anyscan-logo.svg` with the delivered file, then rebuild in this
order. The diagram embeds the logo, so regenerating it before the logo is rebuilt would copy the old one.
`build_logo.py` writes the logo's copy in `App/assets/`, the logo without its tagline, the mark and the icon.

```bash
python Example/UI/build_logo.py
```

```bash
python Example/UI/architecture_diagram.py
```

`test/UI/test_brand_figures.py` fails if the three copies of the logo, or the diagram and its
generator, disagree.

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
- `Configuration/` — `Configuration/Core.py`, the one reader of `Configuration/*/*.yaml` (and
  the calibration writer). Every module receives its settings from it.

These are the Qt-free domain modules plus the Qt UI; `App/run.py` imports only
these, and the domain half imports with PyQt5 unavailable (a tested contract).

**Outside the application** — the app itself never imports these two:

- `Transformation/` — homogeneous transforms, Euler angles, quaternions: a robotics
  library inherited and not touched, so it is excluded from the style check. Nothing in
  the repository imports it today.
- `Calibration/` — the multi-view checkerboard calibration, written in this project's
  style. `Example/Camera/calibrate.py` drives the real camera and calibrates through it;
  `Example/Vision/analyze.py` uses its natural sort key. The camera setup itself lives in `Configuration/Station/` and
`Configuration/Calibration/`, read and written through `Configuration/Core.py`.

## Platform

The describer — Gemma 4 E4B as a 4-bit **MLX** conversion, run through `mlx` / `mlx-vlm` —
is the component that decides where the application runs. Everything else (the Qt UI,
OpenCV, FastSAM on PyTorch, the Basler driver) is portable. There are three distinct states:

| Platform | Status | What is known |
|---|---|---|
| **macOS, Apple silicon** | **Supported, measured** | MLX on the Apple GPU (Metal). 2.20 s per object (warm), 9.35 GB pipeline peak, and output identical word for word across runs, processes and memory pressure. |
| **Linux** | **Supported, measured on one machine** | MLX's CUDA backend on an NVIDIA GPU with at least 11 GB (the installer reads GPU 0's memory and refuses below it; `--cpu` opts into the CPU backend). Measured 2026-09-29 on Ubuntu with an RTX 5070 Ti (16 GB, driver 595.91.07), MLX 0.32.2 with the CUDA 13 backend (`mlx[cuda13]`) and PyTorch 2.14.0+cu130 (FastSAM on CUDA): E4B describes in **0.65 s per object** (warm; 0.51–0.93 s over the 37 objects of `Data/Images/Test/All`), loads in 3.9 s, and the whole application peaks at 9.5 GB of GPU memory (MLX 6.99 GB) and 4.0 GB of RAM. Output identical word for word between two processes. Not compared with the Mac's text. |
| **Windows** | **Not a target, untested** | Nothing known prevents it — `mlx` publishes Windows wheels — but it is not supported and has never been tried. |

- **Determinism does not travel.** Greedy decoding (`temperature=0`) makes the *sampler*
  deterministic, but a different backend can still produce different text through
  floating-point differences inside the model. Word-for-word identical output is a
  *measured* property of each build (Apple silicon; the Linux CUDA machine below), not a
  guarantee across them: the Linux text has not been compared with the Mac's. No test pins
  live describer text (the characterization baseline feeds stored text), so the suite passes
  on both; a new pin on exact model output would have to be verified per platform.
- **Installing on Linux.** On Linux `mlx` has no compute
  backend of its own; the backend comes from an extra chosen for the machine, kept in one
  selectable file per backend — `requirements/linux-cuda12.txt`, `linux-cuda13.txt` or
  `linux-cpu.txt` (far slower) — installed together with `requirements.txt`, which holds the
  version pin. PyTorch's CUDA build cannot be chosen by a requirements marker, so it comes
  from the matching PyTorch index (`cu126`, `cu130` or `cpu`). `./install.sh` makes both
  choices from the NVIDIA driver it finds, after checking GPU 0's memory (11 GB minimum), and it
  warns when the card already has more than 1.5 GB in use. With no usable GPU it stops, naming
  the reason, unless `--cpu` is given. On the measured Linux machine (2026-09-29) its detection
  ran for real (`--detect-only`: driver 595.91.07, the CUDA 13 backend and the `cu130` PyTorch
  build, 15.9 GB on GPU 0) and so did its Gemma step, which downloaded and verified E4B. The full install was not run there: that machine's environment
  was set up by hand with `opencv-python-headless`, and the requirements install would add
  `opencv-python` beside it (since 2026-10-13 the installer removes it again). The installer's other Linux branches are still tested with stubbed
  commands only. Without MLX the describer stops with a message saying so.
- **Linux measured** (2026-09-29, the machine in the table): AMD Ryzen 9 9950X3D, 29 GiB RAM,
  NVIDIA GeForce RTX 5070 Ti (16 GB, compute capability 12.0), driver 595.91.07 (CUDA 13.2),
  Python 3.11.16, MLX 0.32.2 + `mlx-cuda-13`, mlx-vlm 0.7.2, PyTorch 2.14.0+cu130. Through the
  application's path (`Load_Configuration` -> `Configure` -> `Analyze`) on the eight
  `Data/Images/Test/All` frames (the previous set, no longer in the repository; recoverable from
  `1061966`; not re-run on the current one) with the shipped configuration: E4B 0.65 s per object (mean of
  37; 0.64-0.66 s over two processes), model load 3.9 s, configure (load and warm-up) 4.8 s (9.4 s
  once, on the first run after the download, when the warm-up sentence took 5.1 s instead of
  0.5 s); FastSAM loads in 0.08 s and segments a frame in 34-55 ms on CUDA. Peaks: 6.99 GB MLX,
  9.5 GB GPU for the whole application (`nvidia-smi`), 4.0 GB process RSS. The first analysis
  after a load is no slower than the next. Every description and background sentence was
  identical word for word between two processes, and the full suite passes with and without
  `--runslow`. `Example/Vision/evaluate_describer.py` scores the configured describer against
  a confirmed answer key on any machine with the weights; the current test set has none yet (the
  previous set's, `Data/Images/Test/All/answer_key.json`, is recoverable from `1061966`).
- **Packaging:** the PyInstaller recipe this section used to give was for Windows and no
  longer applies. No packaging recipe has been verified on any platform; run from source
  (`python App/run.py`).

### Describer model

AnyScan describes objects with one model: **Gemma 4 E4B**, instruction-tuned, as the 4-bit MLX
conversion `mlx-community/gemma-4-e4b-it-4bit` at revision `475b908`. The prompts were tuned on
it, and the configuration's `Description.Model` names its directory.

| | Apple silicon (Metal) | Linux (CUDA) |
|---|---|---|
| Time per object (warm, mean) | 2.20 s | 0.65 s |
| Peak memory | 9.35 GB, the pipeline | 9.5 GB of GPU memory, the whole application (MLX 6.99 GB) |
| Memory it needs | Measured on a 16 GB M2 Pro; no minimum is set | 11 GB on GPU 0; the installer reads it and stops below |

- **Download:** 5.2 GB, 10 files, into `models/gemma-4-e4b-it-4bit/`.
- **Install:** `./install.sh` downloads it and checks every file against the published hashes;
  by hand, use the `hf download` command in [Setup](#setup).
- **Run:** `python App/run.py`, then load a configuration and ANALYZE. The shipped configuration
  already names this model.
- **Provenance:** its model card gives its source, `google/gemma-4-E4B-it` at revision `fee6332`,
  where the licence was checked (Apache 2.0; see [Licence note](#licence-note)).
- **The catalogue modes' identifier** is a second model, DINOv2 base (`facebook/dinov2-base` at revision
  `f9e44c8`, 346 MB, PyTorch on the segmenter's device), named by `Catalogue.Identifier`. It only compares
  each object with the item's reference images; it describes nothing.
- **Scoring it:** `python Example/Vision/evaluate_describer.py` runs it through the application's
  path and scores its descriptions against the test set's answer key. The current set has none yet;
  the previous set's (`Data/Images/Test/All/answer_key.json`) is recoverable from `1061966`.

## Swapping a component

Both hardware-facing parts sit behind an interface, so a replacement touches one class:

- **Camera** — subclass `Camera_Backend_Cls` (`src/Camera/Core.py`) and implement `_Open`,
  `_Close` and `_Grab`; `_Grab` returns an **RGB NumPy array**, the exchange format for the
  whole application.
- **Describer** — subclass `Describer_Backend_Cls` (`src/Vision/Describers.py`), implement
  `Load` and `Describe(crop, purpose)`, and create it where `Vision.Core` creates
  `Gemma_Describer_Cls` (one describer ships, so there is no registry to add it to). The pipeline
  never sees a prompt or a task token.

## What the design encodes

- **The index is a contract.** The position of a detection in the list is the
  number drawn on the frame *and* at the start of its sentence, in the same
  hue. Never reorder `objects` after `Compose()`.
- **Colour means something.** Green, red and amber are pass, fail and degraded,
  which is why green and red are absent from the object palette. Magenta marks a
  failed (NOK) object; amber marks a Warning object, one that should not be there. The primary button is black, so the strongest control reads
  as structural.
- **One voice.** Every sentence the operator reads is written by the report
  composer (`src/Reporting/Core.py`), so swapping the model never changes how
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

The catalogue modes' identifier, Meta's DINOv2 base (`facebook/dinov2-base`), is licensed under the
**Apache License 2.0** as its model card states (tag `apache-2.0` at the pinned revision `f9e44c8`, checked
2026-10-11) — likewise not MIT, not redistributed with this repository, and shipped by anyone under Apache
2.0's conditions.

The bundled fonts in `App/assets/fonts/`, Public Sans and JetBrains Mono, are under the **SIL Open Font
License 1.1**, not MIT; each family's licence text ships beside its files (`PublicSans-OFL.txt`,
`JetBrainsMono-OFL.txt`) as the OFL requires. They are static instances of the families' variable
fonts from google/fonts; neither family declares a Reserved Font Name.
