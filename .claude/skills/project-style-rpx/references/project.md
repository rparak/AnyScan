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

## UI - Qt code and the brand-independent UI rules

The rules are project-style-rpx `references/ui.md`. How the interface looks - the state colours, the
overlays, the wording, the logos and band, the type scale, the icons - is AnyScan's binding of
jic-sf-ui-style, in `.claude/skills/jic-sf-ui-style/references/project.md`.

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

### Colour comes from the theme ✅

- The tokens are in `src/Parameters/Theme.py`, so the application and the vision renderer (the
  exported annotated image and label mask) share one palette.
- The README's architecture diagram takes its colours from the theme and its type scale and font
  fallbacks from `Style.py`, through `Example/UI/architecture_diagram.py`; it is regenerated, never
  edited by hand (✅ `test/UI/test_brand_figures.py`).
- ✅ `test/UI/test_colour_tokens.py` scans every UI module (except `Style.py`).

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

### Severity is never carried by colour alone ✅

- The Log's level field reads INFO / WARNING / ERROR with the weight ramp `Style.Log_Level_Weight`,
  which the confidence numbers at that severity share (the WARNING amber and ERROR red: ΔE ~8 under
  deuteranopia, measured; `Style.py`).
- ✅ `test/UI/test_log_view.py::test_level_field_weight_ramps_with_severity`.

### One density check 📄 (✅ by the header test)

- 📄 `Style.Is_Low_Density` (`CONST_LOW_DENSITY_DPR`, 1.5) is the one density check; `Style.Logo_Height`
  and the 9 pt floor in `Style.Font` (`CONST_TYPE_FLOOR_LOW_DENSITY`) read it (DD *The logo is taller
  on a low-density display, so its tagline is 9 pt*). ✅ `test/UI/test_header.py` measures the logo at
  DPR 1 and runs itself again at DPR 2.

### A colour relationship is held by code or a test ✅

- **By derivation**, failing loudly: the neutral mask pair is computed from the neutral box at import
  (`Theme.Neutral_Mask_Colors`), and raises a `ValueError` naming the violated floors when no valid
  pair exists or rounding breaks one.
- **Or by a test on the floors**, for colours tuned by eye: the verdict fills are fixed tokens, and
  `test_theme.py` holds them to the same floors (ΔE from the box and from white, 4.5:1 on the ground,
  the hue within 5°).
- ✅ `test/Parameters/test_theme.py::test_neutral_mask_pair_ignores_box_lightness_and_fails_loudly_on_floors`,
  `::test_label_mask_fill_is_a_visible_tint_of_its_box`.

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
- **Derivation or test**: both hold colour relationships today (the neutral pair derived, the verdict
  fills tested); there is no rule for which a new pair should use.
