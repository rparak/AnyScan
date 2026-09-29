# Structure

How the code is divided and what may depend on what. ✅ = enforced by a test; 📄 = documentation
only.

## Layers 📄 (✅ for Qt)

The imports between `src/` packages today (2026-09-24), which is also the rule:

```
Parameters                         data structures and tokens only — imports nothing of the project
Camera, Configuration, Reporting → Parameters
Calibration                      → Camera, Parameters
Logger                           → Configuration
Vision                           → Camera, Reporting, Parameters
UI                               → everything above          (App/run.py → UI and the domain)
```

- **`Parameters` sits below every other layer**: `*_Str` dataclasses and plain tokens, no behaviour
  that needs another package. 📄 — true today; no test checks it.
- **Nothing below `UI` imports `UI` or Qt.** ✅ for the 12 modules in
  `test/integration/test_contracts.py` (`CONST_DOMAIN_MODULES`: camera, vision, `Reporting.Core`,
  `Parameters.Vision`) and the per-module `test_module_is_qt_free` tests; 📄 for `Configuration`,
  `Logger`, `Calibration`, `Vision.Describers` and the vision utilities not in that list (all Qt-free
  today). `UI/Capture.py` is Qt-free too, so a capture set can be read without a UI.
- A domain module never holds the UI or the logger: it reports through callbacks injected by the
  caller (`Set_Log_Callback`, `stage_cb`, `progress_cb`), and its failures are `*_Error_Cls` sentences.
- `src/Transformation/` is inherited (rparak/RoLE), under its own convention, reached only from
  `Example/`; the app never imports it (README > Source layout). The style checker excludes it.

## One reader per file format 📄

Each on-disk format is parsed by exactly one module — the one that writes it — and everything else
goes through that module's reader. A second parser drifts from the writer silently.

| Format | Written and read by |
|---|---|
| Mode and calibration YAML (`Configuration/*.yaml`) | `Configuration.Core` (`Load_Configuration`, `Write_Calibration`) |
| Background-reference sidecar (`Image_Background_NNN.json`) | `Configuration.Core` (`Build_Reference_Sidecar`, and the load check) |
| Capture set: `<set>_objects.json`, `<set>_distorted.json` | `UI.Capture` (`Build_Set_Metadata`, `Distorted_Frame_Record`, `Read_Capture_Set`) |
| Calibration capture manifest (`capture.json`) | `Calibration.Core` (`Record_Capture`, `Captured_Window`) |
| Session log lines and the run-summary CSV | `Logger.Core` (`Parse_Line` is the only log-line parser; the Log view uses it) |
| Describer answer key (`Data/Images/Test/All/answer_key.json`) | `Vision.Utilities.Evaluation` (`Load_Answer_Key`; written by hand, confirmed by the owner) |

No module parses YAML for itself; tools in `Example/` go through these readers too
(`make_reference.py` → `Read_Capture_Set`; `calibrate.py` → `Calibration.Core.Captured_Window`).

## Injected runtimes — in the vision utilities 📄

`src/Vision/Utilities/` functions take `cv2` and `np` as parameters rather than importing them
(`Draw_Annotated(..., cv2, np, ...)`, `Fuse_Objects`, `Measure`), and so do the `Vision` functions
that call them. That keeps those modules importable and testable without OpenCV, and is where the
convention is followed and buys something. **Elsewhere a module-level `import cv2` / `import numpy as
np` is the norm** (`UI/Core.py`, `Camera/Utilities/Image_Processing.py`, `Configuration/Core.py`) —
not a violation.

Heavy runtimes (ultralytics, mlx / mlx-vlm, pypylon) are imported inside the function that first
needs them, in every layer, so a bare import stays cheap.

## No parameter or field that cannot take effect 📄

A parameter with a single legal value, or a configuration field that is accepted but cannot change
what the code does, reads as a choice that is not there. Remove it together with the code path that
made it look configurable.

- **In code:** `verdict_colored` has no default, so a harness cannot render differently from the app;
  `CONST_DETECTOR` (`'florence'`, which no code set) and `CONST_ANNOTATE_MASK_FILL` (`'index'`, whose
  only consumer was one diagnostic) were removed; `Segmenter.Segment`'s `regions` and `Analyze`'s
  `log_cb` went with `Segmentation.Mode`, since they existed only for its `box` value.
- **In configuration:** a field must be read by something that can change behaviour, not merely
  parsed. `Load_Configuration` catches unknown keys but **not known keys that nothing reads** — every
  instance so far (`Camera.Resolution`, `Segmentation.Mode`, and the hardware-id constant that
  duplicated the configuration's) was found by hand. See references/yaml.md.

## A harness takes the application's path 📄

A script that captures, analyses or renders what the application does goes through the
application's own code — `scan.py` captures with `Basler_Camera_Cls`, `analyze.py` reads the
configuration's classification flag — so its output cannot silently differ. An exception is stated
where it is made and why: `calibrate.py --capture` drives `Basler_Cls` directly because a lens model
is solved from frames that were not undistorted.
