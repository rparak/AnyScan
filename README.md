# AnyScan

*The camera sees, the model describes.*

AnyScan is a desktop inspection station for one Basler camera looking down at a work surface. It finds every
object on the table, describes each one with a local vision-language model, measures it in mm and records the
analysis; a catalogue mode also recognises the catalogued part, checks it and gives a state: OK, NOK or Warning.

![AnyScan architecture: in every mode the camera shows a live preview, then takes a fresh frame once nothing moves, two cues, fused, find every object, and each object is described in words and measured in mm. The desktop app shows Live, Trends, History and Log. A catalogue mode adds, for each object found, recognising the catalogued part, the inspection area (only a part wholly inside is judged, one outside is a part or a foreign object by similarity, size and colour), the checks on the side that is up (size, holes with each bore centred in its countersink, stains) and a state: OK, NOK or Warning, a Warning with its kind. It describes each object after its state and drops a sentence that contradicts the checks. The mode names the station, the station the calibration, and the catalogue item and empty-surface reference set the stages up too. Every analysis is recorded, with the session log, a run summary and the daily station events](images/anyscan-architecture.svg)

**Figure 1:** AnyScan's architecture, generated from the theme by `Example/UI/architecture_diagram.py` and never
edited by hand. Read it top to bottom: the frame, the two cues and their fusion, then each object's description and
measurement, and in a catalogue mode its state.

Two independent cues are fused, so an object is kept if **either** one finds it; [Detection logic](#detection-logic)
gives the stages. The project poster is [images/anyscan-poster.pdf](images/anyscan-poster.pdf).

> [!IMPORTANT]
> Sizes are repeatable, not absolute, and their scale is not verified. The describer is not a defect detector, and a
> catalogue mode's OK covers only its item's checks. Read [Limitations](#limitations) before building on the output.

**Contents:** [Setup](#setup) · [Run](#run) · [Configuration](#configuration) · [Limitations](#limitations) ·
[Captures on the rig](#captures-on-the-rig) · [Tests](#tests) · [Detection logic](#detection-logic) ·
[Platform](#platform) · [Repository layout](#repository-layout) · [Swapping a component](#swapping-a-component) ·
[Authors](#authors) · [Funding](#funding) · [Licence note](#licence-note)

## Setup

AnyScan runs on **macOS on Apple silicon** (Verified, measured) and on **Linux with an NVIDIA GPU** (Verified on one
machine, 2026-09-29); Windows is Never tried, not a target ([Platform](#platform)). The installer creates the virtual
environment, installs the dependencies for the hardware (Metal; on Linux, MLX's CUDA 12 or 13 backend chosen from the
driver) and downloads the three models, each checksum-verified; it is safe to re-run. Later commands run in its venv:

```bash
./install.sh                 # or ./install.sh --detect-only to see what it would do
source .venv/bin/activate
```

On Linux it stops, naming the card and its memory, when GPU 0 has less than 11 GB or there is no usable NVIDIA GPU;
`--cpu` installs the CPU builds instead (unmeasured, expected to be far slower). **Some installer paths have never
run for real**: the full install on Linux, the Gemma download on macOS, and the CUDA 12 and CPU branches anywhere are
tested with stubbed commands only. If one fails, please report it with the installer's full output.

| Model, in `models/` (not tracked in git) | Used for | Download |
|---|---|---:|
| Gemma 4 E4B, `mlx-community/gemma-4-e4b-it-4bit` (4-bit MLX) | describing each object | 5.2 GB |
| FastSAM-x | segmenting the frame, finding holes | 145 MB |
| DINOv2 base, `facebook/dinov2-base` | recognising the catalogue part (catalogue modes) | 346 MB |

The window and the tests run without the weights; a missing one is reported, with what to do, when first used.

<details>
<summary><b>Setup by hand</b>: the environment, the OpenCV fix and the three model downloads</summary>

Python 3.10 or newer (tested on 3.10–3.12, developed and characterized on 3.10):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip uninstall -y opencv-python
pip install --force-reinstall --no-deps opencv-python-headless==5.0.0.93
```

The last two lines leave OpenCV's headless build only. ultralytics and mlx-vlm pull in OpenCV's GUI build, whose Qt
plugins make the window abort with "Could not load the Qt platform plugin xcb"; uninstalling it also deletes files
the two builds share, so the headless build is reinstalled whole. `./install.sh` does this after every install, and
`App/run.py` refuses to start, naming these two commands, while the GUI build is there. On Linux, `mlx` also needs
its backend, one of `requirements/linux-cuda12.txt`, `linux-cuda13.txt` or `linux-cpu.txt`, and PyTorch from the
matching index (`cu126`, `cu130` or `cpu`); see [Platform](#platform). `pypylon` (the Basler SDK) is needed only for
the live camera.

The describer, Gemma 4 E4B, at the revision the application was measured with (10 files, 5.2 GB; the public
repository needs no token; `hf` is the Hugging Face CLI from `huggingface_hub`):

```bash
hf download mlx-community/gemma-4-e4b-it-4bit \
    --revision 475b9088d29754a3379866cf5aeb6b41acd313c2 \
    --local-dir models/gemma-4-e4b-it-4bit
```

The segmenter, FastSAM-x (upstream: <https://docs.ultralytics.com/models/fast-sam/>):

```bash
python -c "from ultralytics import FastSAM; FastSAM('FastSAM-x.pt')"
mkdir -p models/FastSAM && mv FastSAM-x.pt models/FastSAM/
```

The catalogue modes' identifier, DINOv2 base:

```bash
hf download facebook/dinov2-base README.md config.json preprocessor_config.json model.safetensors --revision f9e44c814b77203eaa57a6bdbbd535f21ede1415 --local-dir models/dinov2-base
```

Without the Gemma weights at `models/gemma-4-e4b-it-4bit/`, ANALYZE fails with a message naming the missing
directory. `models/.gitkeep` lists the expected directory contents.

</details>

## Run

```bash
python App/run.py
```

The console drives a Basler camera and the local Gemma describer, both real; the window still opens without either,
so **CONNECT → SCAN → ANALYZE** degrades one step at a time. PREVIEW shows the table live; SCAN clears the previous
result, stops the preview and takes a frame once nothing moves (about 0.6 s). `F11` toggles fullscreen, `Esc` closes.
Without the camera, pass a saved 1920×1200 frame (a configuration must still be loaded, which needs the weights).
`scan.py` saves one frame to `Data/Results/Scan_<timestamp>.png` while the application is not connected (`--help`):

```bash
python App/run.py --frame path/to/frame.png
python Example/Camera/scan.py                  # as SCAN: waits for a still scene, refuses a moving one (exit 1)
python Example/Camera/scan.py --no-stillness   # one frame at once, without the stillness check
```

## Configuration

Three kinds of file, each in its own folder, linked by name (a reference is a file name, never a path):

```text
Configuration/Mode/Config_<Hardware>_Mode_<Mode>.yaml      Station: Station_<...>.yaml
Configuration/Station/Station_<Hardware>[_<Name>].yaml     Calibration: Calibration_<...>.yaml
Configuration/Calibration/Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml
```

- **Mode**: what a user changes without code (models, prompts, thresholds; a catalogue mode's item,
  `Data/Catalogue/<item>/<item>.yaml`). Its comments give every field's default and unit.
- **Station**: the camera, lens, lighting, sensor window, empty-surface reference, inspection area and the
  calibration in force. A mode file that holds any of these fails to load.
- **Calibration**: a new file from every `Example/Camera/calibrate.py` run, which prints the station line to change.

`Configuration.Core.Load_Configuration` checks the three as a whole: a missing required field, a link that disagrees
or a reference that does not match its sidecar fails the load, naming the file and the line; a missing optional field
takes its default and is logged. **Changing the lamp without updating `Camera.Lighting` goes unnoticed.**

The application starts with its configuration named but not loaded: CONFIGURATION lists `Configuration/Mode/`, and
**Load** applies one (on failure the previous one stays); after the first CONNECT it is fixed for the run. **A station
sets its station-event directory in a local copy of the mode file, never the shipped one**: copy it outside the
repository, keeping its name, change only `General.Station_Events.Directory`, and start with `--config <that copy>`.

## Limitations

Three limitations affect any decision built on this output. They stand **unverified in this version**: nothing
here checks them against ground truth, and none of the [captures on the rig](#captures-on-the-rig) changes that.

### Measurements are repeatable, not absolute

**Outside a catalogue mode, don't build a tolerance on these numbers. Inside one, trust its outline check only for
its part, within 46.4 mm of the frame centre.** A part's size varies with its thickness and with where it lies: a
12 mm hex nut, 6 mm thick, reads about 0.2 mm large at the frame centre and about 1.5 mm large near the edge.

- **Repeatable:** on the 41 test frames, the 22 mounting plates read 60.33–61.40 × 39.64–41.15 mm at the
  calibration's scale. Repeatability says nothing about correctness: a wrong scale is the same in every frame.
- **Position and thickness:** a single ordinary lens looking down sees a thick part's outline above the calibrated
  plane, and off the optical axis its side wall too. Away from the axis a size reads **W + X · t / (Z − t)**
  (footprint W, thickness t, far edge X from the axis, lens height Z). Only a telecentric lens removes this.
- **Scale unverified:** the calibration in force is a multi-view solve from 2026-09-28, 63 views at a reprojection
  RMS of 0.45 px, 0.102 mm/px. A good fit shows that the lens model is consistent, not that the sizes are right.
- **Catalogue mode:** with the scale moved to the part's top face, the 22 plates read −0.77 to +0.76 mm off 60 × 40
  (tolerance ±1.5 mm), their centres up to 46.3 mm from the frame centre. **Not verified:** the parts were not
  calipered. **Not measured:** beyond 46.4 mm, where the side-wall term predicts up to about 1 mm more; a size
  checked there is noted in the session log, not on screen. The 0.01 mm display is formatting: a pixel is ~0.10 mm.

### The describer is not a defect detector

**A description without a stain is not evidence there isn't one.** Whether a stain, scratch or corrosion is reported
depends on how the part is framed, and nothing in the output marks a miss. A defect no check names (a scratch, a
dent) is detected by nothing.

- **Evidence** (the previous test set, not re-run on the current one): one rust stain was named at crop paddings
  0.20 and 0.36 and missed at 0.00–0.12 and 0.28, identically on every run, a step with the framing. The shipped 0.20
  happens to report it; one stain on one frame is a reason for more caution, not less.

### A catalogue mode checks only what its item lists

**An OK means the part passed the checks its catalogue item lists, not that nothing else is wrong.** Verified on the
41 test frames only (2026-10-11), with every hole within tolerance.

- **A hole where the catalogue puts none is not reported**: holes are counted near their expected positions only.
- **A stain is caught by its colour under this light**: a yellow-brown area of 1 mm² or more on the mounting
  plate's front. Another colour, or this colour under another light, is not verified.
- **A part outside the inspection area is never judged**: only one wholly inside the frame inset by 10 mm (top,
  bottom) and 13 mm (sides) gets OK or NOK, the rest a Warning with no hole or stain check. The area is ~101 mm high,
  so an upright plate can move only ~±20 mm; the insets are not verified by the left and bottom edges or corners.
- **The Similarity tab is not a defect map**: glare shows on it too, and no state reads it.
- **The describer's words are guarded, not trusted**: a sentence contradicting the checks, naming them or with a
  number is dropped and logged, by reading words, so a paraphrase can pass. The state never comes from it.

## Captures on the rig

In force since 2026-09-28: (1) a **multi-view calibration set**, and (2) the **empty-surface reference** (re-shot
2026-10-12), shot under that calibration with `make_reference.py`, which writes its sidecar. Still to do:

3. a **parts session**: defective parts with clean controls, low-contrast parts, and a harsh shadow;
4. the **cable pull**, which checks that a lost connection is detected, during the live preview too;
5. a **moving hand under SCAN**, which checks that a scan of a moving scene is refused on the rig.

Each is captured through the application (CONFIGURATION → Load, CONNECT, then SCAN → ANALYZE per frame); every
ANALYZE writes a capture set under `logger/captures/<connection>/` (keep its `_raw.png`). The board is
`Data/Calibration/Checkerboard_11x8_12mm_A4.pdf`; items 1 and 2 are repeated when the camera, lens or mount changes.

## Tests

None needs a camera. They mirror `src/` as `test/<Domain>/test_<module>.py`, plus `test/integration/`:

```bash
pytest                 # the default run
pytest --runslow       # also runs the `slow` failure-path tests (need the weights)
```

With the FastSAM and Gemma weights the default run smoke-tests the real `Analyze`; without them it prints
`REAL VISION PATH NOT VERIFIED` and passes. `test/Vision/test_characterize.py` has a golden file; after an intended change:

```bash
pytest test/Vision/test_characterize.py --update-golden
git diff test/Vision/data/characterization.txt
```

## Detection logic

SCAN stops the preview and calls `Camera_Backend_Cls.Capture_Still` (`src/Camera/Core.py`): the first frame with no
movement since the one before (`Camera.Utilities.Stillness.Is_Still`) is the scan's, undistorted when calibrated; if
something still moves after about a second, none is taken. `Vision_Pipeline_Cls.Analyze` (`src/Vision/Core.py`) then
runs the stages every mode shares (modules under `src/Vision/Utilities/` unless named):

```text
(1) background subtraction  Segmentation.Background_Difference   what changed against the empty-surface reference
(2) FastSAM segmentation    Segmenter.Fast_Sam_Cls               object instances, independent of the reference
(3) fusion                  Fusion.Fuse_Objects                  (1) OR (2), split, area-filtered, left to right
(4) description             Describers.Gemma_Describer_Cls       a padded, isolated, contrast-stretched crop each
```

Then `Reporting.Compose` writes the sentences and `Measure.Measure_Objects` the sizes (A x B, Ø or A/F, in mm). A
**detect-only mode** (Segment Anything) runs these as listed; a **catalogue mode** measures, recognises and checks
each object before stage 4, then describes it with what the checks found. The thresholds are measured, not chosen.

<details>
<summary><b>The catalogue stages</b>: recognition, the inspection area, the side up, holes, stains and the state</summary>

1. **Measurement and outline** (`Measure.Measure_Objects`, `Dimensions.Check_Objects`): the size at the part's top
   face against the item's outline and its tolerance.
2. **Recognition** (`Identifier.Dino_Identifier_Cls`, `Classify.Best_Match`, `Classify.Classify`): each object's
   upright crop against the item's reference image of each side, by DINOv2. An area 1.7× the part's or more is a
   Warning, several parts; a similarity of 0.75 or more is the part, OK or NOK by its outline; the outline alone
   within tolerance is NOK; anything else is a Warning, foreign object.
3. **Inspection area** (`Classify.Inspection_Area_Px`, `Inside_Area`, `Resembles_Part`, `Settle_Area`): only an object
   wholly inside the frame inset by the station's `Inspection_Area` is judged. Outside, it is a Warning: outside area
   when it resembles the part (similarity 0.657 or more, mean saturation 76.3 or less, its extent no larger than the
   part's diagonal plus its tolerance), else foreign object.
4. **Side up** (`Holes.Hole_Candidates`, `Holes.Side_Evidence`, `Classify.Decide_Side`, `Classify.Settle_Side`):
   FastSAM again on the upright crop for holes. DINOv2's side when its margin over the next is 0.265 or more, else
   the side a hole only it has shows. Sides that disagree are a Warning, side unclear; holes against look a Warning,
   side mismatch.
5. **Holes** (`Holes.Check_Holes`, `Classify.Apply_Holes`): each group's count near its positions, diameter, edge
   distances and pitch, and each stepped hole's bore within 0.85 mm of its countersink once the camera's predicted
   shift is taken out. A missing, extra or out-of-tolerance hole makes the part NOK.
6. **Stains** (`Stain.Check_Stain`, `Classify.Apply_Stain`): the item's colour band inside the part, its edge and
   holes left out; a region of 1 mm² or more makes it NOK.
7. **State** (`Reporting.State_Word`, `Reporting.Badges`): OK, NOK or Warning with its kind and the operator's action.
8. **Description, held to the checks** (`Reporting.Describer_Prompt`, `Guard_Description`, `Restated_Prompt`): the
   prompt carries the side and what the checks found, no number. A sentence with a number, naming the checks or
   contradicting them is dropped; on a contradiction it is asked once more. The state is never changed.
   `Classify.Similarity_Grid` draws the Similarity view.

</details>

## Platform

| Platform | Status | What is known |
|---|---|---|
| **macOS, Apple silicon** | **Verified, measured** | MLX on the Apple GPU (Metal), on a 16 GB M2 Pro. 2.20 s per object (warm), 9.35 GB pipeline peak, output identical word for word across runs, processes and memory pressure. |
| **Linux** | **Verified on one machine, 2026-09-29** | MLX's CUDA backend on an NVIDIA GPU with at least 11 GB (the installer refuses below it). On an RTX 5070 Ti with the CUDA 13 backend: 0.65 s per object (warm), 9.5 GB GPU peak for the whole application, output identical word for word between two processes. Not compared with the Mac's text. |
| **Windows** | **Never tried, not a target** | Nothing known prevents it (`mlx` publishes Windows wheels), but it is not supported. |

- **Determinism does not travel**: greedy decoding fixes the sampler, but another backend can still change the text
  through floating-point differences. No test pins live describer text, so the suite passes on both.
- **The models**: the describer, Gemma 4 E4B in 4-bit **MLX** at revision `475b908`, decides where AnyScan runs; the
  rest is portable. DINOv2 base (`f9e44c8`, catalogue modes) only compares objects with the item's reference images.
  No packaging recipe has been verified on any platform; run from source.

<details>
<summary><b>The Linux measurement</b>: the machine, the installer's run and the numbers</summary>

- **The machine** (2026-09-29): AMD Ryzen 9 9950X3D, 29 GiB RAM, NVIDIA GeForce RTX 5070 Ti (16 GB, compute
  capability 12.0), driver 595.91.07 (CUDA 13.2), Ubuntu, Python 3.11.16, MLX 0.32.2 + `mlx-cuda-13`, mlx-vlm 0.7.2,
  PyTorch 2.14.0+cu130.
- **The numbers**, through the application's path (`Load_Configuration` → `Configure` → `Analyze`) on the eight
  frames of the previous test set with the shipped configuration (not re-run on the current one): E4B 0.65 s per
  object (mean of 37; 0.51–0.93 s per object, 0.64–0.66 s over two processes), model load 3.9 s, configure (load and
  warm-up) 4.8 s (9.4 s once, on the first run after the download); FastSAM loads in 0.08 s and segments a frame in
  34–55 ms on CUDA. Peaks: 6.99 GB MLX, 9.5 GB GPU for the whole application (`nvidia-smi`), 4.0 GB process RSS. The
  first analysis after a load is no slower than the next. The full suite passes with and without `--runslow`.
- **The installer**: on Linux the backend comes from one requirements file per backend,
  `requirements/linux-cuda12.txt`, `linux-cuda13.txt` or `linux-cpu.txt`, and PyTorch's CUDA build from the matching
  index (`cu126`, `cu130` or `cpu`). `./install.sh` chooses both from the NVIDIA driver after checking GPU 0's memory
  (11 GB minimum), and warns when more than 1.5 GB of it is already in use. On this machine its detection ran for real
  (`--detect-only`: driver 595.91.07, the CUDA 13 backend and the `cu130` build, 15.9 GB on GPU 0), and so did its
  Gemma step, which downloaded and verified E4B. The full install was not run there; the other Linux branches are
  tested with stubbed commands only.

</details>

## Repository layout

<details>
<summary><b>The folders</b>: what is committed, what is git-ignored, the packages under <code>src/</code>, the figures</summary>

`Data/` is input and output, `images/` is documentation, and only `models/` is supplied by you.

```text
App/run.py                the application (entry point)
App/assets/               the logos, the window icon and the fonts (Public Sans, JetBrains Mono, OFL); built
src/                      the Qt-free domain packages and the Qt UI (below)
Example/                  runnable scripts: scan, calibrate, calibration_tilt_study, generate_checkerboard,
                          make_reference, analyze, evaluate_describer, architecture_diagram, build_logo, build_fonts
Configuration/            the mode, station and calibration files
Data/Images/Test/         the 41 test frames (Image_055-095, each a capture set's undistorted _raw.png); committed
Data/Images/Background/   the empty-surface reference(s) and their provenance sidecars; committed
Data/Images/Calibration/  calibration capture sets (calibrate.py --capture); git-ignored
Data/Calibration/         the calibration board to print, Checkerboard_11x8_12mm_A4.pdf; committed
Data/Results/             analyze.py and scan.py output; git-ignored
images/                   the README's figures, the delivered logo and the project poster; committed
models/                   the model weights, downloaded per Setup; git-ignored
```

Under `src/`, the application is `Camera/` (the camera backends and the pypylon driver), `Vision/` (the pipeline,
the segmenter, the describer, the identifier and their utilities), `Reporting/` (the report composer, the panel's
one voice), `UI/` (the widgets, the window and the workers), `Parameters/` (the data structures) and
`Configuration/` (`Configuration/Core.py`, the one reader of the configuration files). The domain packages import
with PyQt5 unavailable, a tested contract. `Calibration/` holds the multi-view checkerboard calibration that
`calibrate.py` drives; `Transformation/` is an inherited robotics library that nothing imports today.

The figures are regenerated, never edited. After replacing `images/anyscan-logo.svg`, rebuild the logo copies, then
the diagram, which embeds the logo; `test/UI/test_brand_figures.py` fails when they disagree:

```bash
python Example/UI/build_logo.py
python Example/UI/architecture_diagram.py
```

A frame is added to `Data/Images/Test/` under a new name, never over an old one, and only together with the tests'
expectations: they refer to the frames by name.

</details>

## Swapping a component

- **Camera**: subclass `Camera_Backend_Cls` (`src/Camera/Core.py`) and implement `_Open`, `_Close` and `_Grab`,
  which returns an **RGB NumPy array**, the exchange format for the whole application.
- **Describer**: subclass `Describer_Backend_Cls` (`src/Vision/Describers.py`), implement `Load` and
  `Describe(crop, purpose)`, and create it where `Vision.Core` creates `Gemma_Describer_Cls`. Every sentence the
  operator reads is still written by the report composer (`src/Reporting/Core.py`).

## Authors

<table><tr><td align="center"><a href="https://github.com/rparak"><img src="https://avatars.githubusercontent.com/rparak" width="120px;" alt="Roman Parak"/><br /><strong>Roman Parak</strong></a><br />Author</td>
<td align="center"><a href="https://github.com/LukasMoravansky"><img src="https://avatars.githubusercontent.com/LukasMoravansky" width="120px;" alt="Lukas Moravansky"/><br /><strong>Lukas Moravansky</strong></a><br />Contributor</td>
<td align="center"><a href="https://github.com/vojtechmarek13"><img src="https://avatars.githubusercontent.com/vojtechmarek13" width="120px;" alt="Vojtěch Marek"/><br /><strong>Vojtěch Marek</strong></a><br />Contributor</td>
<td align="center"><a href="https://github.com/piifl"><img src="https://avatars.githubusercontent.com/piifl" width="120px;" alt="Filip Rusnak"/><br /><strong>Filip Rusnak</strong></a><br />Contributor</td></tr></table>

## Funding

Developed within internal research at JIC Smart Factory as a demonstrator through which the EDIH-DIGIMAT
project shows small and medium-sized enterprises (SMEs) how AI-based visual inspection can work on their own parts.

![EDIH-DIGIMAT; Ministry of Industry and Trade of the Czech Republic; Funded by the European Union](images/anyscan-funding.svg)

**Figure 2:** The project's, the Ministry's and the EU's logos, generated with Figure 1.

Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not
necessarily reflect those of the European Union or European Commission. Neither the European Union nor the granting
authority can be held responsible for them.

## Licence note

The code is under the MIT licence ([LICENSE](LICENSE)); the models and fonts are not, and no model ships with it.

- **Gemma 4 E4B** (Google, via the `mlx-community` conversion) is under the **Apache License 2.0**
  (<https://ai.google.dev/gemma/docs/gemma_4_license>; the Gemma Terms of Use, <https://ai.google.dev/gemma/terms>,
  do not govern Gemma 4). `google/gemma-4-E4B-it` is tagged `apache-2.0` at `fee6332`, the revision the weights were
  converted from; the conversion's `license: gemma` tag looks like converter boilerplate. Checked 2026-09-24.
- **DINOv2 base** (Meta) is under the **Apache License 2.0**, tagged `apache-2.0` at `f9e44c8` (checked 2026-10-11).
  Anyone shipping either model does so under Apache 2.0's conditions (a copy of the licence, retained notices).
- **Public Sans and JetBrains Mono** (`App/assets/fonts/`): **SIL Open Font License 1.1**, each licence beside its files.
