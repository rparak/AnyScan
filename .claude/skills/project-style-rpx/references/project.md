# project-style-rpx: project reference for AnyScan

The conventions of this repository that the generic skill leaves to the project, as the code follows
them. The generic rules - Python, tests, structure, YAML, the installer, Markdown and the
brand-independent UI rules - are the personal skill **project-style-rpx**
(`~/.claude/skills/project-style-rpx/`, private repository `rparak/rp-claude-skills`), with its checker
`scripts/check_style.py`. How the interface looks is the personal skill **jic-sf-ui-style** (the JIC
Smart Factory style, taken from this application). This file overrides both where they differ, and its
rules hold without them: on a machine without the personal skills, the rules are read from this file,
the code and `docs/design-decisions.md` (DD).

This folder has no `SKILL.md` on purpose: a personal skill wins over a project skill of the same name
(Claude Code docs, *Resolve skills that share a name*), so a copy here would be ignored and drift.
✅ = enforced (the checker, a test, the configuration loader); 📄 = documentation only. A practice
followed inconsistently is under **Unsettled**, not written as a rule.

## Header and checker

- Holder: **JIC Smart Factory** - `Copyright (c) <year> JIC Smart Factory`, `Author   : JIC Smart
  Factory`; licence MIT. Each file keeps its own copyright year (DD *File headers carry JIC Smart
  Factory*). The `#`-comment header form; the `"""` form is not used here.
- The naming and docstring style descends from rparak/RoLE; where RoLE differs (no exceptions, no
  tests, a docstring header) this project does not follow it.
- `check_style.json` (this folder): class roots `src`, `App`, `Example`; test root `test`; check
  roots `src`, `App`, `Example`, `test`; one exclusion, `src/Transformation` (below), with its reason.
- Command, from the repository root:
  `.venv/bin/python ~/.claude/skills/project-style-rpx/scripts/check_style.py`. It reports 11 known
  issues (2026-10-23), all listed under Unsettled: 9 Qt overrides without `Args:` and `Style.py`'s
  `FONT_UI` / `FONT_MONO`. A change must add none.

## Layout and layers 📄 (✅ for Qt)

```
src/<Domain>/            Parameters, Camera, Configuration, Reporting, Calibration, Logger, Vision, UI
                         (+ Transformation, inherited)
App/run.py               the application's entry point; App/assets/ its logo, fonts and icons
Example/<Domain>/        the scripts folder (Camera/, Vision/, UI/): harnesses, figure generators
test/<Domain>/           mirroring src/; test/integration/ for cross-module contracts and the pipeline,
                         test/Install/ for the installer
Configuration/           Mode/, Station/, Calibration/ (references > Configuration)
Data/                    the test frames, the catalogue items, results
docs/                    design-decisions.md, capabilities.md, capture-checklist.md (Records)
images/                  the README's figures, generated
```

The imports between `src/` packages (2026-09-24), which is also the rule:

```
Parameters                         data structures and tokens only - imports nothing of the project
Camera, Configuration, Reporting → Parameters
Calibration                      → Camera, Parameters
Logger                           → Configuration     (Logger.Station_Events → Logger.Core)
Vision                           → Camera, Reporting, Parameters
UI                               → everything above          (App/run.py → UI and the domain)
```

- **`Parameters` sits below every other layer**: `*_Str` dataclasses and plain tokens, no behaviour
  that needs another package (a departure: the generic skill keeps structures in each domain's
  `Core.py`). 📄 - true today; no test checks it.
- **Nothing below `UI` imports `UI` or Qt.** ✅ for the 12 modules in
  `test/integration/test_contracts.py` (`CONST_DOMAIN_MODULES`: camera, vision, `Reporting.Core`,
  `Parameters.Vision`) and the per-module `test_module_is_qt_free` tests; 📄 for `Configuration`,
  `Logger`, `Calibration`, `Vision.Describers` and the vision utilities not in that list (all Qt-free
  today). `UI/Capture.py` is Qt-free too, so a capture set can be read without a UI.
- A domain module never holds the UI or the logger: it reports through callbacks injected by the
  caller (`Set_Log_Callback`, `stage_cb`, `progress_cb`), and its failures are `*_Error_Cls` sentences.
- `src/Transformation/` is inherited (rparak/RoLE), under its own convention, reached only from
  `Example/`; the app never imports it (README > Source layout). The checker excludes it.

## Root 📄

The root holds `App`, `Configuration`, `Data`, `Example`, `KNOWN_ISSUES.md`, `LICENSE`, `README.md`,
`docs`, `images`, `install.sh`, `logger`, `models`, `pytest.ini`, `requirements`, `requirements.txt`,
`src`, `test`, `.claude`, `.gitignore`, `.gitattributes`. No test pins it (a departure).

## Formats - one reader and writer each 📄

Each on-disk format is parsed by exactly one module - the one that writes it - and everything else
goes through that module's reader.

| Format | Written and read by |
|---|---|
| Mode, station and calibration YAML (`Configuration/{Mode,Station,Calibration}/*.yaml`), catalogue items (`Data/Catalogue/<item>/<item>.yaml`, with their reference boxes) | `Configuration.Core` (`Load_Configuration`, `Load_Catalogue`, `Write_Calibration`) |
| Background-reference sidecar (`Image_Background_NNN.json`) | `Configuration.Core` (`Build_Reference_Sidecar`, and the load check) |
| Capture set: `<set>_objects.json`, `<set>_distorted.json` | `UI.Capture` (`Build_Set_Metadata`, `Distorted_Frame_Record`, `Read_Capture_Set`) |
| Calibration capture manifest (`capture.json`) | `Calibration.Core` (`Record_Capture`, `Captured_Window`) |
| Session log lines and the run-summary CSV | `Logger.Core` (`Parse_Line` is the only log-line parser; the Log view uses it) |
| Daily station event files (`<Station_Events.Directory>/YYYY-MM-DD.csv`) and their export ledger (`logger/station_events_exported.txt`) | `Logger.Station_Events` (the daily files are written, never read back; the ledger is written and read. It reads the session log only through `Parse_Line` and the logger's event markers, never sentence wording) |
| Describer answer key (`answer_key.json` beside the test frames; the current set has none yet, the previous set's is kept as test data in `test/Vision/Utilities/data/answer_key_1061966.json`) | `Vision.Utilities.Evaluation` (`Load_Answer_Key`; written by hand, confirmed by the owner) |

No module parses YAML for itself; tools in `Example/` go through these readers too
(`make_reference.py` → `Build_Reference_Sidecar`; `calibrate.py` → `Calibration.Core.Captured_Window`).

## Heavy and injected runtimes 📄

- Heavy runtimes (ultralytics, mlx / mlx-vlm, pypylon) are imported inside the function that first
  needs them, in every layer, so a bare import stays cheap and Qt-free (`Segmenter.py`,
  `Describers.py`, `Camera/Core.py`).
- `src/Vision/Utilities/` functions take `cv2` and `np` as parameters rather than importing them
  (`Draw_Annotated(..., cv2, np, ...)`, `Fuse_Objects`, `Measure`), and so do the `Vision` functions
  that call them: those modules stay importable and testable without OpenCV. **Elsewhere a
  module-level `import cv2` / `import numpy as np` is the norm** (`UI/Core.py`,
  `Camera/Utilities/Image_Processing.py`, `Configuration/Core.py`) - not a violation.

## No parameter or field that cannot take effect 📄 - the instances

The rule is the generic skill's (structure.md, yaml.md). Here:

- **In code:** `verdict_colored` has no default, so a harness cannot render differently from the app;
  `CONST_DETECTOR` (`'florence'`, which no code set) and `CONST_ANNOTATE_MASK_FILL` (`'index'`, whose
  only consumer was one diagnostic) were removed; `Segmenter.Segment`'s `regions` and `Analyze`'s
  `log_cb` went with `Segmentation.Mode`, since they existed only for its `box` value.
- **A harness takes the application's path**: `scan.py` captures with `Basler_Camera_Cls`,
  `analyze.py` reads the configuration's classification flag. The one exception, stated where it is:
  `calibrate.py --capture` drives `Basler_Cls` directly because a lens model is solved from frames
  that were not undistorted.

## Configuration

Three kinds under `Configuration/`, each in its own folder and linked by name: a mode file,
`Mode/Config_<Hardware>_Mode_<Mode>.yaml` (one per mode), names its station (`Station`); a station
file, `Station/Station_<Hardware>[_<Name>].yaml` (the camera, its acquisition settings and window, the
background reference - shared by the modes naming it, never overridden by one; written by hand), names
its calibration (`Calibration`); and a calibration,
`Calibration/Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml` (one per solve, written by `calibrate.py`,
never written over). A reference is a file name, never a path, resolved in its kind's folder of the
repository. A catalogue mode also reads a catalogue item, `Data/Catalogue/<item>/<item>.yaml`, by the
same rules. ✅ = enforced by `Configuration.Core.Load_Configuration` / `Write_Calibration`.

- **One reader, one writer** ✅ (in practice): `Configuration/Core.py` alone parses these files and
  alone writes a calibration; every setting reaches its user through `Configuration_Str`. The writer
  refuses any file that exists. No tool writes a mode or station file: `calibrate.py` prints the
  station line to change instead.
- **Shape** 📄: the header block's sections say what the file is, who reads and writes it, the
  file-name convention, what REQUIRED means and the hardware setup. Keys nest by stage or concern
  (`Segmentation.Background.*`, `Segmentation.Fusion.*`). Units in brackets: `[px]`, `[us]`, `[%]`.
  Text the model receives (the prompts) lives here as data, with the reasoning behind the wording in
  the comment above it - iterated here, never in code.
- Every field in the shipped mode file says `REQUIRED.` or its default, and a documented default
  equals the code's ✅
  `test/Configuration/test_core.py::test_every_documented_default_in_the_shipped_mode_file_is_the_code_default`.
- Section order: the mode file's is `Hardware, Station, General, Identity, Confidence, Segmentation,
  Description, Evaluation`, a catalogue mode's `Catalogue` block after `Identity` (shared because the
  catalogue modes were copied from the first; nothing checks it). The station file's is `Hardware,
  Calibration, Camera, Background`; the calibration's is fixed by its writer.
- **Loading** ✅, beyond the generic rules: a **harness-only** field (the `Evaluation` block:
  `Evaluation.Frames`, read by `analyze.py`, never by the application) is optional, and the loader only
  resolves it - data the application never touches must not stop it loading; the harness that reads
  it checks it. What depends on the camera's sensor window is checked against it at load: the
  background reference's size and its provenance sidecar, and the window the calibration was solved at.

### A field must be read by something that can change behaviour 📄

The loader catches unknown keys, not known ones that nothing uses. All three instances so far were
found by hand:

- A hardware-id constant in `Logger/Core.py` that looked like the setting for which camera's run
  summary is written, while the configuration's file name already said it (DD *The run-summary CSV is
  named after the loaded configuration*).
- `Camera.Resolution` - loaded into `Camera_Configuration_Str`, never read; the camera ran at whatever
  it last remembered (fixed: the window is now set on connect and read back).
- `Segmentation.Mode` - read, but its `box` value could not take effect (no region prompts were ever
  passed); removed, with the box path and the parameters that only served it.

**One dated exception** (2026-10-11): a catalogue item's descriptions (`Description`,
`Measurement_Rules`, each side's `Description`, `Defects`) are loaded and validated but read by nothing
until the describer uses them in phase D of the catalogue mode - the owner chose validated fields over
comments so the item file is the one tracked source for the part. The exception ends when phase D
reads them; a field phase D does not read is removed (DD *A catalogue item is the single tracked
source…*). It is not a precedent for any other field.

### Machine-specific values stay out of the repository 📄

Instance: `8d8a13c` put the station's `/home/sf4/sf4/events/` into the shipped
`General.Station_Events.Directory`. The loader requires that directory to exist, so everywhere else
the shipped configuration stopped loading and 17 test modules failed before any test ran. `9d44669`
put back `logger/Station_Events`; README > Configuration says how a station keeps its own copy (same
file name, started with `--config`; its `Station` resolves in the repository, so nothing is copied
beside it). Only a **required** path is caught, and only indirectly: the suite loads the shipped file.

## Errors

The `*_Error_Cls` classes (14 in `src/`: `Configuration_Error_Cls`, `Camera_Error_Cls`,
`Segmenter_Error_Cls`, `Basler_Settings_Error_Cls`, …) carry operator sentences that the UI shows
verbatim. A settings failure is not reported as a missing device (`Basler_Settings_Error_Cls`).

- Where a function reports and returns False instead of raising (`Write_Calibration`), it asserts
  inside a `try` and prints: `except AssertionError as error: print(f'[ERROR] …')`. Not the rule
  elsewhere.
- `except Exception` at a boundary is marked `# noqa: BLE001` - all in `src/` outside the inherited
  `Basler.py` are.
- The application logs through the session logger (`src/Logger/Core.py`); scripts in `Example/` print
  `[INFO]` / `[WARNING]` / `[ERROR]` lines.

## Installer - `install.sh`

The only shell file, so the rules are those of one file; a second script follows it, and a
disagreement is a question, not a new rule. ✅ = `test/Install/test_install.py`.

- Targets: macOS on Apple silicon (verified) and Linux with an NVIDIA GPU (verified on one machine,
  2026-09-29); Windows is not a target, so there is no `.bat` (README > Platform).
- Written for bash 3.2 (macOS's): no associative arrays, no `mapfile`, no `${var,,}`.
- Every line in the application's log format, through one `Log` function, the level padded to
  `CONST_LEVEL_WIDTH` (7, the logger's own constant) ✅:
  `2026-09-24 13:05:07 [INFO   ] Detected macOS 26.6.2 on Apple silicon (Apple M2 Pro).`
  pip's output is kept and its tail logged as ERROR lines on failure; a download shows only a progress
  bar on a terminal.
- `Die` for a failure; an ERR trap (`On_Unexpected_Error`) names the line and command of anything
  unanticipated; INT/TERM (`On_Interrupt`) says re-running is safe. Checks run cheapest first (the
  Python version, the platform, then a 5 GB download); detection lines and a `Plan:` line come before
  any action, and `--detect-only` stops there.
- A download goes to a `.part` file, is verified, and only then replaces anything. A broken `.venv`
  is reported with the command to remove it, never deleted.
- The test sources the script in a fresh `/bin/bash` with a hermetic `PATH` (stubs for the commands
  that describe the machine, ahead of links to the real coreutils) and checks every log line; its
  docstring states which paths ran for real and which only against stubs.

## Tests

- `pytest.ini`: `testpaths = test`, `--import-mode=importlib`, the `slow` marker.
- Shared fixtures in `test/conftest.py`: the repository root, the reference frame and its shape;
  `src/`, `App/` and `Example/Vision` are on the path, so tests import harness code.
- A test that needs the model weights goes through **`require_weights`** (`test/conftest.py`): it runs
  when they are there, skips loudly naming the missing path when they are not, and fails under
  `--runslow`. Never an early `return`. 📄 - nothing forces its use.
- The Qt-callback guard (project-style-rpx `references/ui.md` > Tests) is `test/conftest.py`, every
  test phase ✅.
- A pinned data set has a default-run guard that its inventory names exactly its files
  (`test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set`) ✅.
  Instance behind the xfail rule: `b5ca788` removed `All/Image_009`-`013`, and three strict xfails
  reported XFAIL on the missing frames' `AssertionError`.
- Equivalence proofs compare the characterization golden file
  (`test/Vision/data/characterization.txt`), an analysed frame's capture set, a CSV row or rendered
  pixels.
- Script tests run the script in a fresh interpreter from an unrelated working directory
  (`test/Camera/test_reference_harnesses.py` has the pattern).
- The skills' frontmatter and this file are held by `test/integration/test_skills.py`.

## Records - `docs/`, `README.md`, `KNOWN_ISSUES.md`

A departure: the records are not in `.claude/project-docs/`.

| File | Records |
|---|---|
| `docs/design-decisions.md` | Deliberate choices whose reason is not visible in the code |
| `README.md` > *Limitations* | The limitations that affect a decision built on the output: a `###` heading, **the consequence first**, bold, then the evidence with the measured numbers, then plainly whether it is verified; the section links `KNOWN_ISSUES.md` |
| `KNOWN_ISSUES.md` | Open behaviours that show up in the text or numbers but decide nothing: **Impact:**, **Pinned by:**, **Not fixed here:**, **What would answer it:**; on a fix the entry goes and the resolution moves to the DD |

**Revisit if** is required for every new DD entry; the older entries are not backfilled (about half
have one). Their labels vary (a bold **Why.** in some, a plain paragraph in most).

## UI - AnyScan's bindings

The rules are project-style-rpx `references/ui.md` (Qt code, tokens, contrast, density, tests, Qt
quirks) and jic-sf-ui-style (the look; its `references/<page>.md` is named per section below). This
section keeps what is AnyScan's: where each rule lives in this code, the test that holds it here,
AnyScan's views, its vision overlays and their measurements, and its catalogue wording. Where a skill
and this code disagree, the code is the truth; correct the skill.

### Qt code 📄

- 32 Qt overrides carry `# << QT OVERRIDE >> #` (`paintEvent`, `closeEvent`, `eventFilter`,
  `keyPressEvent`, `mousePressEvent`, `resizeEvent`, `showEvent`, `leaveEvent`, `reject`, the
  `QLayout` methods of a flow layout …) ✅ checker.
- 26 custom signals (`Stage_Changed = pyqtSignal(str)`, `Analysis_Finished = pyqtSignal(object)`),
  33 `__On_*` slots. The workers are `Analysis_Worker_Cls`, `Connect_Worker_Cls` and
  `Model_Load_Worker_Cls` in `UI/Workers.py`.
- The domain modules a UI class calls: `Camera`, `Vision`, `Configuration`, `Reporting`, `Logger`.
- Colours and fonts come from `UI/Utilities/Style.py` (tokens defined in the Qt-free
  `Parameters/Theme.py`); stylesheets are built inline where they are applied, from those tokens
  (`'color: %s;' % Style.CONST_INK`); a token at an opacity is `Style.Token_Color(token, alpha)`.

### Colour comes from the theme ✅ - jic-sf-ui-style: `palette.md`

- The tokens are in `src/Parameters/Theme.py`, so the application and the vision renderer (the
  exported annotated image and label mask) share one palette.
- The README's architecture diagram takes its colours from the theme and its type scale and font
  fallbacks from `Style.py`, through `Example/UI/architecture_diagram.py`; it is regenerated, never
  edited by hand (✅ `test/UI/test_brand_figures.py`).
- ✅ `test/UI/test_colour_tokens.py` scans every UI module (except `Style.py`).

### AnyScan's state colours and the views that carry them ✅ - jic-sf-ui-style: `palette.md`, `charts.md`, `annotation.md`

- **One colour per state, in every view** (the owner's rule, 2026-10-16): a state's frame mark in the
  Camera View, its Trends series and legend sample, its History filter swatch and set outline are the
  same token (`Theme.Verdict_Color`, whose ink is its box). Three states (the owner's rule,
  2026-10-16): OK, NOK and Warning, every Warning whatever its kind. Trends' 2 px lines and 7 px square
  markers are `CONST_SERIES_LINE_W` and `CONST_SERIES_MARKER_PX` in `UI/Views/Trends.py` (the owner's
  rule, 2026-10-18); `Theme.Chart_Edge`, the 1.25 px dark edge at L* 25, is removed. Every colour of a
  catalogue mode:

  | Use | Token | Value | On white |
  |---|---|---|---|
  | OK | `CONST_INK` | `#640ABA` | 9.15:1 |
  | NOK | `CONST_NOK_BOX` | `#FF6540` | 2.92:1 |
  | Warning (every kind) | `CONST_WARNING_BOX` | `#FFC226` | 1.62:1 |
  | Trends Total (no state) | `CONST_INK_MUTE` | `#6F5783` | 6.24:1 |
  | Confidence: Frame mean (no state) | `CONST_DETECTION_INK` | `#655E6D`, 2 px solid, a filled 7 px square per image | 6.22:1 |
  | Confidence: Run mean (no state) | `CONST_CHART_LIGHT_INK` | `#9890A0`, 2 px dashed (6 px dash, 4 px gap), a hollow 7 px square (2 px ring) per image, drawn on top | 3.07:1 (2.02:1 against the frame mean's) |
  | Badge grounds | OK `#C2C9FF`, NOK `#FFD9D0`, Warning `#FFC226` | | purple words ≥ 5.66:1 |
  | Mask fills | OK `#CC9EF1`, NOK `#CD7157`, Warning `#B28508` (outline the amber) | | |
  | Inspection area | `CONST_INSPECTION_AREA` / `_EMPTY` | `#FFD880` on images / `#640ABA` on the empty view | 4.71:1 on the table / 6.79:1 on `#E1DCE6` |

  Retired as verdict colours on 2026-10-16: the foreign object's grey `#B4A6BE` (badge `#CAC0D3`, mask
  `#DBCCE5` / `#897C93`) and Unspecified's blue `#33A3FF` (badge `#C6E4FF`, mask `#748DB1`). The grey
  stays only as the disabled label's token (`CONST_CONTROL_DISABLED_TEXT`,
  `CONST_PRIMARY_DISABLED_TEXT`), never a state's nor in Trends; the blue is no token at all (DD *Three
  states for the operator, a Warning with its kind*).
- **Trends' Confidence chart draws no verdict** (the owner's rule, 2026-10-18): the frame mean and the
  run mean only, nothing per object, in the two neutrals of the table above; its threshold lines are
  the configuration's `Confidence.Warn_Below` and `Error_Below`, labelled 'Warning below 80 %' and
  'Error below 60 %'. The charts' own secondary text is the neutral grey; `CONST_INK_SOFT` elsewhere
  stays the purple (DD *The Confidence chart draws the two means, told apart by their form*; *Trends
  draws square markers, 2 px lines, and the run mean as hollow squares on top*).
- OK is the JIC purple and NOK the JIC orange-red (DD *The fail marker is the JIC orange-red*; *The
  palette is the JIC Smart Factory brand's*). The neutral ink `#655E6D` is no verdict's colour: it
  marks only a detect-only mode's words and dots, its derived mask pair and History's outline of a
  detect-only set.

### The vision overlays: annotated frame, label mask, inspection area ✅ - jic-sf-ui-style: `annotation.md`

- **Detect-only** (Segment Anything) draws every object in the logo purple `#640ABA`
  (`CONST_DETECTION_BOX = CONST_LOGO_INK`, white numeral 9.15:1; table 1.31:1 at ΔE 121, aluminium
  3.53:1, rust-stained metal 3.02:1, steel 2.32:1). It equals OK, the owner's ruling of 2026-10-15:
  that mode shows no verdict (DD *Every chip carries a white numeral*).
- **Every Warning has one look**, whatever its kind (outside the area, a foreign object, several
  parts, side unclear, side mismatch): its rotated outline, dashed outer box and chip in the amber
  with the white numeral, filled and outlined in the amber's pair on the mask, and no feature mark,
  though a part whose side could not be told was checked and keeps its features in the record
  (`Annotate.__Draw_Features` draws only OK and NOK parts' marks).
- **A judged part (OK, NOK)** colours its marks by their own check on the frame: the dashed outer box
  and the chip the verdict, the solid rotated outline the size check alone (`Annotate.__Outline_Color`),
  each feature mark its own check (DD *A judged part's marks each carry their own check*).
- **The inspection area** (`UI.Widgets.Paint_Inspection_Area`, on screen only):
  `Theme.CONST_INSPECTION_AREA` over a camera image (4.71:1 on the table, median `#236A56`; 1.18:1
  against the Warning amber), `CONST_INSPECTION_AREA_EMPTY` over the empty Camera View (the amber
  1.01:1 there; the purple 6.79:1). The owner's choice of 2026-10-16 from renders. Chips:
  `Theme.CONST_CHIP_NUMERAL`; badge words: `Theme.Label_Ground`; the diagram's verdict labels follow
  the badge's rule.
- **The label mask** (DD *The label mask is black ground, tinted fill, verdict contour*): the fills
  keep their box's hue, held by the tests below and by `Theme`'s `CONST_MASK_FILL_*` floors.
- ✅ `test/Vision/Utilities/test_annotate.py::test_annotated_is_box_and_numeral_only_in_the_unshifted_verdict_colour`,
  `::test_each_chip_is_its_box_colour_with_a_white_numeral`,
  `::test_the_catalogue_states_render_in_their_colours_on_both_images`,
  `::test_a_warning_shows_only_its_outline_outer_box_and_chip`,
  `::test_a_judged_parts_outline_carries_its_size_and_its_outer_box_and_chip_its_verdict`,
  `test/UI/test_inspection_area.py::test_the_area_is_drawn_on_the_empty_view_the_scanned_frame_and_the_annotated_result_only`,
  `test/Parameters/test_theme.py::test_label_mask_fill_is_a_visible_tint_of_its_box`,
  `::test_verdict_colour_comes_from_the_one_constant`, `::test_every_chip_numeral_is_white`,
  `::test_the_palette_keeps_the_brands_rules`.

### The catalogue's wording ✅ - jic-sf-ui-style: `wording.md`

- A Warning's kind is told in words, never in colour: `State: Warning – <kind>.` in Scene
  Understanding (`Reporting.State_Word`, `Verdict_Lines`), the `warning_kind` in the record; the kinds
  and their names are `Parameters.Vision.CONST_WARNING_KINDS` (DD *Three states for the operator, a
  Warning with its kind*).
- A detect-only run shows no OK / NOK words at all, only detected objects.
- ✅ `test/Vision/Utilities/test_annotate.py::test_verdict_colored_false_draws_one_neutral_colour_not_verdicts`,
  `test/Parameters/test_theme.py::test_the_detect_only_box_is_the_logo_purple`,
  `::test_every_warning_is_the_amber_and_the_retired_state_colours_are_gone`,
  `::test_neutral_mask_pair_is_derived_light_fill_and_darker_outline`.

### Severity is never carried by colour alone ✅ - jic-sf-ui-style: `palette.md` § 8

- The Log's level field reads INFO / WARNING / ERROR with the weight ramp `Style.Log_Level_Weight`,
  which the confidence numbers at that severity share (the WARNING amber and ERROR red: ΔE ~8 under
  deuteranopia, measured; `Style.py`).
- ✅ `test/UI/test_log_view.py::test_level_field_weight_ramps_with_severity`.

### Controls and text clear 4.5:1, measured ✅

- Every state rule names its fill and its label (DD *Control stylesheets: every state rule names its
  fill and its label*); text clears 4.5:1 on its ground, one palette at every density (DD *Text clears
  4.5:1 on its ground*).
- Status words take `Theme.Status_Text_Color` (`CONST_OK` → `CONST_OK_INK`, `CONST_WARN` →
  `CONST_WARN_INK`) in `Stat_Cell_Cls.Set_Value` and the header pill; a dot keeps the bright colour.
  Text on the viewport is `CONST_VIEWPORT_TEXT`; error text there is `CONST_LOG_ERROR` (4.61:1).
- ✅ `test/UI/test_control_contrast.py` (`test_no_enabled_state_falls_below_the_text_contrast_floor`,
  `test_disabled_states_are_exempt_but_distinguishable_from_enabled`,
  `test_every_state_of_every_control_was_measured`, and a self-check that hover really rendered);
  `test/UI/test_text_contrast.py` builds the window in its states and measures every visible label,
  rich-text span and painted text against the ground grabbed under it (which must be a theme token);
  disabled text is exempt.

### The Camera View names its state in its head; nothing but the analysis grid lies over the frame ✅ - jic-sf-ui-style: `layout-components.md` § 8

- The marker (`●  LIVE PREVIEW`, `SCANNING…`, `ANALYZING…`) is `UI.Widgets.State_Marker_Cls`, fed by
  `Viewport_Cls.Marker_Changed`; a new state the view must name joins `CONST_STATES` (DD *ANALYZE
  sweeps a decorative pixel grid over the frame…*). The grid and the busy overlay are `Viewport_Cls`
  (`Start_Analysis`, `Start_Busy`), their values in `Theme.CONST_GRID_*`, `CONST_BUSY_*` and
  `Pixel_Motif.CONST_WAVE_*`.
- ✅ `test/UI/test_analysis_grid.py::test_the_grid_is_the_same_drawing_over_two_different_frames`,
  `::test_no_state_label_is_drawn_inside_the_image`, `::test_the_three_states_share_one_marker_in_the_head`,
  `::test_the_grid_stops_when_the_analysis_ends`.

### Density, the header, the logos and the funding band - jic-sf-ui-style: `typography.md`, `grid-fit.md`, `layout-components.md` §§ 2, 9

- 📄 `Style.Is_Low_Density` (`CONST_LOW_DENSITY_DPR`, 1.5) is the one density check; `Style.Logo_Height`
  and the 9 pt floor in `Style.Font` (`CONST_TYPE_FLOOR_LOW_DENSITY`) read it (DD *The logo is taller
  on a low-density display, so its tagline is 9 pt*). ✅ `test/UI/test_header.py` measures the logo at
  DPR 1 and runs itself again at DPR 2.
- The header's lockup is `Widgets.Logo_Lockup_Cls`: `App/assets/anyscan-logo-wordmark.svg` plus the
  live tagline at `Style.CONST_LOGO_TAGLINE_ORIGIN` and `CONST_LOGO_TAGLINE_SIZE`, in
  `CONST_LOGO_INK`. The logo's copies are derived from `images/anyscan-logo.svg` by
  `Example/UI/build_logo.py`; never hand-edit them or move the tagline's constants apart from the
  outlines (DD *The header draws the delivered logo and sets its tagline as live text*).
  ✅ `test/UI/test_header.py` holds the live lockup to the outlined logo within 1 device px at both
  densities; `test/UI/test_brand_figures.py` holds the derived files to the logo.
- Logos are vectors at paint time (`Widgets.Svg_Image_Cls`; DD *Logos are rendered as vectors at
  paint time*), ✅ `test/UI/test_logo_rendering.py`; the header marks are grid-fitted at 1x
  (`UI.Utilities.Grid_Fit`, `Style.CONST_LOGO_MARK_RIGHT`, `CONST_LOGO_MARK_THIN_PX`,
  `AnyScan_Window_Cls.CONST_JIC_MARK_RIGHT`; DD *The header logos are grid-fitted on a 1x display*),
  ✅ `test/UI/test_grid_fit.py`.
- The band's three logos are traced SVGs (DD *The band's logos are traced SVGs*),
  ✅ `test/UI/test_funding_band.py`, `test_logo_rendering.py::test_no_logo_is_a_pixmap`. The EU
  disclaimer is `Funding_Row_Cls.DISCLAIMER`, carried by the README and the architecture diagram's
  band, not the window's (DD *The funding band carries the project's, the Ministry's and the EU's
  logos*); the motif keeps out of every logo's clear space (DD *The funding band carries the brand's
  pixel motif*); ✅ `test/UI/test_funding_band.py`.
- The brand's squares are in the funding band and the empty Camera View's corner only, never in Scene
  Understanding, the Log, Trends or History (DD *The empty Camera View carries the poster's pixel
  cluster*); ✅ `test/UI/test_empty_view_motif.py`.
- The README's funding logo row (`images/anyscan-funding.svg`) is generated with the architecture
  diagram; ✅ `test/UI/test_brand_figures.py`.

### Content type comes from the scale; one content, one size ✅ (content) 📄 (chrome) - jic-sf-ui-style: `typography.md`

- AnyScan's content is the Scene Understanding reading (background paragraph, object labels,
  confidences, descriptions), History's info panel and the Log's rows, sized by the named steps of
  `CONST_TYPE_SCALE` in `Style.py`: `CONST_TYPE_SCENE_BACKGROUND`, `CONST_TYPE_OBJECT_LABEL`,
  `CONST_TYPE_OBJECT_CONFIDENCE`, `CONST_TYPE_OBJECT_BODY` (Live), `CONST_TYPE_INFO_HEADING`,
  `CONST_TYPE_INFO_LABEL`, `CONST_TYPE_INFO_BODY`, `CONST_TYPE_INFO_META` (History), `CONST_TYPE_LOG`.
  Live and History are separate sets on purpose (a description 12.5 pt in one, 10.5 pt in the other).
  Chrome is sized per widget; see Unsettled.
- DD *Type: a scale for content, chosen sizes for chrome*.
- ✅ `test/UI/test_history.py::test_info_panel_type_hierarchy_heading_is_largest`.

### A colour relationship is held by code or a test ✅

- **By derivation**, failing loudly: the neutral mask pair is computed from the neutral box at import
  (`Theme.Neutral_Mask_Colors`), and raises a `ValueError` naming the violated floors when no valid
  pair exists or rounding breaks one.
- **Or by a test on the floors**, for colours tuned by eye: the verdict fills are fixed tokens, and
  `test_theme.py` holds them to the same floors (ΔE from the box and from white, 4.5:1 on the ground,
  the hue within 5°).
- ✅ `test/Parameters/test_theme.py::test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors`,
  `::test_label_mask_fill_is_a_visible_tint_of_its_box`.

### Every icon is a pixel icon from one set ✅ - jic-sf-ui-style: `pixel-icons.md`

- The set is `UI.Utilities.Pixel_Motif.CONST_PIXEL_ICONS`, which the README's architecture diagram
  draws too. A card head takes `Card_Head_Cls(<name>, title)`, a dialog's title
  `Icon_Cls.Head_Layout(<name>)`, anything else `Icon_Cls(<name>, cell, colour)`; a head's 2 px top
  margin is `Icon_Cls.CONST_HEAD_DROP`; an animated icon steps through `Busy_Cells`. The model pill's
  icon is its grey, as the pill's words are (DD *Every icon is a pixel icon from one set*, which has
  the table of which icon is where).
- ✅ `test/UI/test_pixel_icons.py` reads every icon off the window's and the dialog's grabs against the
  set and the meaning approved for its place, renders every icon at 1x and at DPR 2 (two colours,
  whole cells), and decodes the committed diagram's icons back to the set.

## Departures from the generic skill

- Records in `docs/`, not `.claude/project-docs/` (Records).
- `Parameters` holds the shared `*_Str` structures and tokens (Layout and layers).
- `__init__.py`: none, as the generic skill says; `src/` and `App/` reach `sys.path` through
  `test/conftest.py` and, in scripts, a path built from `__file__`.
- No root-layout test (Root).
- `src/Transformation/` is excluded from the checker (Header and checker).

## Unsettled - not rules yet

Followed inconsistently; ask before writing new code either way.

- **Import group order** among standard library, third-party and `typing`: most files order standard
  library → third-party → `# Custom Lib.:`; some put `typing` or `dataclasses` after a third-party
  import.
- **`Args:` in Qt-override docstrings**: 23 of the 32 marked overrides document their `event`; 9 do
  not (the checker reports those 9).
- **Runtime-resolved module state**: `UI/Utilities/Style.py`'s `FONT_UI` / `FONT_MONO` are resolved
  at startup, so they are not constants and do not fit `CONST_*` (the checker reports them).
- **One method connecting a widget's signals**: two UI classes connect in a `__Connect_Signals`; the
  others connect where the widget is built. Explicit connection is settled.
- **Chrome type sizes**: 34 `Font(<number>` calls in `src/UI/` use literal sizes, most of them off
  the scale (7.5, 8, 8.5, 9, 10, 11, 12, 13.5). The content rule covers content only.
- **One content label outside the scale**: the Scene Understanding card's note (`UI/Core.py`,
  `__reading_note`, the composer's note under the objects) is content set at a literal 11.5 (a scale
  step, but not a named token).
- **Derivation or test**: both hold colour relationships today (the neutral pair derived, the verdict
  fills tested); there is no rule for which a new pair should use.
- **The label mask's black ground** is `Annotate.CONST_ANNOTATE_MASK_GROUND` - by a documented choice
  not a theme surface colour - while `Theme.Ground_Contrast` separately assumes `'#000000'`: one colour
  with two sources.
