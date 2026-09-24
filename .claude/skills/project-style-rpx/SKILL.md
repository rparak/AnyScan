---
name: project-style-rpx
description: The anyscan-pyqt project's conventions — Python (RP naming with _Cls/_Str/CONST_*, the #-comment MIT header, tp.* hints, numbered Description/Args/Returns docstrings, *_Error_Cls exceptions carrying operator sentences, pytest layout, the Qt-override exemptions), the shell installer, the YAML configuration and calibration files, the design-decisions Markdown, and the structural rules (layer boundaries, one reader per file format, no parameter or configuration field that cannot take effect). Use it for any change in this repository — new or edited Python, a new script, a configuration field, a design-decision entry, a review — even when style is not mentioned. It describes what this codebase does, and says which rules check_style.py enforces and which are documentation only.
---

# project-style-rpx

The conventions of this repository, taken from what its code does — not from another
project. Where a practice is followed inconsistently it is listed under **Unsettled**, not
written as a rule. Every rule says whether something **enforces** it (✅ the checker, a test, the
configuration loader) or whether it is **documentation only** (📄).

The naming and docstring style descends from rparak/RoLE (the "RP" style), credited in the
file headers' history (docs/design-decisions.md, *File headers carry JIC Smart Factory*). The
rules below are this project's own; where RoLE differs (it has no exceptions, no tests, a
docstring-form header) this project does not follow it.

## Run the checker before every commit

```bash
.venv/bin/python .claude/skills/project-style-rpx/scripts/check_style.py src App Example test
```

It must report 0 issues for the files you changed. `src/Transformation/` is excluded in
`scripts/check_style.json`, with its reason, and the summary line names the exclusion.
Its own tests: `.venv/bin/python -m pytest .claude/skills/project-style-rpx/scripts/test_check_style.py`
(not part of the app's `test/` suite).

## What is enforced, and by what

| Rule | Enforced by |
|---|---|
| MIT header with a `File Name:` line matching the file | ✅ checker |
| Class `_Cls`, dataclass `_Str`, functions Pascal_Snake_Case, parameters snake_case or math symbols, module-level names `CONST_*` or a `*_Str` preset | ✅ checker |
| Every parameter and return annotated | ✅ checker (relaxed for pytest functions) |
| Docstring with `Description:`, numbered `Args:` when there are arguments, `Returns:` when a value is returned | ✅ checker (relaxed for pytest functions) |
| `Initialization of the Class:` in a `_Cls` docstring | ✅ checker — except exception classes and Qt classes (direct or through project classes) |
| Qt-dispatched camelCase methods exempt from naming **only when marked** `# << QT OVERRIDE >> #` | ✅ checker |
| Lines ≤ 150, ≤ 2 statements per `;` line, no mutable defaults, no `== True/False`, no invalid escapes, no `logging`, no relative imports, `import typing as tp`, no `from __future__ import annotations`, no dead `__name` override | ✅ checker |
| The domain layers import no Qt | ✅ for the 12 modules in `test/integration/test_contracts.py` `CONST_DOMAIN_MODULES` (camera, vision, `Reporting.Core`, `Parameters.Vision`) + per-module `test_module_is_qt_free`; 📄 for the rest (`Configuration`, `Logger`, `Calibration`, `Vision.Describers`, `Vision.Utilities.Measure` …, Qt-free today but not in the list) |
| A configuration key the loader does not know is reported | ✅ `Load_Configuration` (a WARNING, not a failure) |
| Required configuration fields present, values valid | ✅ `Load_Configuration` |
| UI colours only from theme tokens (no hex string, no numeric `QColor`) | ✅ `test/UI/test_colour_tokens.py` |
| Every enabled control state ≥ 4.5:1, measured from rendered pixels | ✅ `test/UI/test_control_contrast.py` |
| Installer log lines in the application's log format | ✅ `test/Install/test_install.py` (every line of the tested paths) |
| A comment above every import; `# Custom Lib.:` group with `#   ../path` lines | 📄 |
| `# << PRIVATE >> #` marker, private state as `self.__name` | 📄 |
| `*_Error_Cls` messages are full operator sentences | 📄 |
| A configuration field is read by something that can change behaviour | 📄 — the loader cannot see it (see references/structure.md) |
| No parameter with a single legal value | 📄 |
| One reader per file format | 📄 |
| `Parameters` imports only `Parameters` | 📄 (true today; no test) |
| design-decisions entries carry **Revisit if** | 📄 (required for new entries) |
| Shell, YAML and Markdown shape | 📄 |

## Python — the essentials

Full rules with examples from this repository: **references/python.md**; Qt code: **references/pyqt.md**;
how the interface looks (colour, contrast, severity, type): **references/ui-design.md**.

1. Every `.py` file opens with the `#`-comment MIT header (all 91 files use it; the checker also
   accepts a `"""` docstring header, which this repository does not use). Copy it from
   `assets/header.txt` and set `File Name:` to the real path.
2. Names: `Pascal_Snake_Case_Cls`, `Pascal_Snake_Case_Str` dataclasses, `Pascal_Snake_Case`
   functions and methods (verb-first), `snake_case` parameters and locals (or math symbols),
   `CONST_*` module constants. A parameter carrying a `*_Str` is named after it.
3. `import typing as tp` and annotate everything; dataclass fields carry a comment ending in a
   `#   Unit [type]` line.
4. Docstrings: `Description:`, numbered `Args:` `(1) name [type]: ...`, `Returns:`
   `(1) parameter [type]: ...` — the RP format, not Google/NumPy/Sphinx.
5. Errors: a module that can fail in a way the operator must see defines a `*_Error_Cls`
   (`Configuration_Error_Cls`, `Camera_Error_Cls`, `Segmenter_Error_Cls`, …) and raises it with a
   full, actionable sentence. The UI shows it verbatim. The assert-inside-try-then-print pattern
   is used where a function reports and returns False (`Write_Calibration`), not as the rule.
6. Reporting: the application logs through the session logger and injected callbacks
   (`Set_Log_Callback`, `stage_cb`, `progress_cb`) — the Qt-free layers never hold the logger.
   Scripts in `Example/` print `[INFO]` / `[WARNING]` / `[ERROR]` lines. No `logging` module.
7. Tests: pytest, `test/<Domain>/test_<module>.py` mirroring `src/`, a `Description:` docstring
   per test saying what behaviour it pins, `slow` for tests needing model weights.
8. Line length: aim ≤ 120, the checker errors above 150.

## Shell, YAML, Markdown, structure

- **references/shell.md** — `install.sh`, the only shell file: header, log format, `Die`, re-runnability.
- **references/yaml.md** — the configuration and calibration files: header block, field comments,
  REQUIRED / Default, units, and the rule that a field must be read or not exist.
- **references/markdown.md** — `docs/design-decisions.md` entries; KNOWN_ISSUES and README > Limitations.
- **references/structure.md** — layer boundaries, one reader per format, injected runtimes (vision
  utilities), no parameter or field that cannot take effect.

## Unsettled — not rules yet

Followed inconsistently; ask before writing new code either way.

- **Import group order.** 65 of 88 files order standard library → third-party → `# Custom Lib.:`;
  23 do not (usually `typing` or `dataclasses` after a third-party import). Only the comment per
  import and the custom group are consistent.
- **`Args:` in Qt-override docstrings.** 6 of 16 marked overrides document their `event`; 10 do not
  (the checker reports those 10).
- **Runtime-resolved module state.** `UI/Utilities/Style.py`'s `FONT_UI` / `FONT_MONO` are resolved at
  startup, so they are not constants and do not fit `CONST_*` (the checker reports them).
- **One method connecting a widget's signals.** Two UI classes connect in a `__Connect_Signals`; the
  others connect where the widget is built. Explicit connection (no `connectSlotsByName`) is settled.
- **How a script reaches `src/`.** `scan.py`, `calibrate.py` and `make_reference.py` append the
  working-directory-relative `'../../' + 'src'` (so they must be run from their own directory);
  `analyze.py` builds the path from `__file__`, which works from anywhere.
