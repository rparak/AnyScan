# Python

Every example below is from this repository. ✅ = enforced by `scripts/check_style.py`,
📄 = documentation only.

## Header ✅

Every `.py` file opens with the `#`-comment block (copy `assets/header.txt`): the MIT text, then
`Author   : JIC Smart Factory` and `File Name: ../<path from src/ or the repo root>`, between
`## ===…=== ##` rules. Each file keeps its own copyright year. The checker also accepts a `"""`
docstring header; this repository does not use one.

## Names ✅

| Kind | Convention | Example |
|---|---|---|
| Behaviour class | `Pascal_Snake_Case_Cls`, explicit base | `Basler_Camera_Cls(Camera_Backend_Cls)`, `Fast_Sam_Cls` |
| Dataclass | `Pascal_Snake_Case_Str`, fields `Pascal_Snake_Case` | `Scale_Str`, `Camera_Configuration_Str.Resolution` |
| Exception | `Pascal_Snake_Case_Error_Cls` | `Configuration_Error_Cls(ValueError)` |
| Function / method / property | `Pascal_Snake_Case`, verb-first where it acts | `Load_Configuration`, `Hardware_And_Mode`, `Applied_Settings` |
| Private method / attribute | `__Pascal_Snake_Case` / `self.__snake_case` | `__Read_Calibration`, `self.__resolution` |
| Parameter / local | `snake_case`, or a math symbol matching the formula | `config_path`, `K`, `x, y, w, h` |
| Parameter carrying a `*_Str` | named after the structure | `Segmentation_Parameters_Str` |
| Module constant | `CONST_UPPER_SNAKE` | `CONST_PROJECT_ROOT`, `CONST_WINDOW_FIELDS` |
| Test function / fixture | pytest's convention: `test_<the behaviour as a sentence>`, lowercase fixtures | `test_a_reference_replaced_under_its_sidecar_fails_the_load`, `tmp_path`, `sandbox` |
| Test helper | `_Pascal_Snake_Case` | `_Write`, `_Stub_Linux` |

**Qt-dispatched methods keep Qt's camelCase** (`paintEvent`, `closeEvent`, `eventFilter`,
`reject`) and carry `# << QT OVERRIDE >> #` on the line above; the checker exempts only marked
ones. See references/pyqt.md.

## Imports 📄

Each import has a comment line above it naming the library (and its install command for a
third-party one); project imports sit last under `# Custom Lib.:` with a `#   ../<path>` line:

```python
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the structures a configuration becomes
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
```

✅ `import typing as tp` (never `from typing import`), no relative imports, no
`from __future__ import annotations`. There are no `__init__.py` files: `src/` is on `sys.path`
(tests: `test/conftest.py`; scripts append it themselves). The order of the standard-library,
third-party and `typing` imports among themselves is **unsettled** (SKILL.md).

A heavy runtime (ultralytics, mlx, pypylon) is imported inside the function that needs it, so a
bare import of the module stays cheap and Qt-free (`Segmenter.py`, `Describers.py`, `Camera/Core.py`).

## Constants 📄

Module constants are `CONST_*` under a `"""Description:\n    Initialization of constants.\n"""`
block, each preceded by a comment saying what it means and why, ending in `#   Unit [type]`:

```python
# The sensor window: (the key path, the smallest valid value). ...
#   Unit [Tuple<Tuple>]
CONST_WINDOW_FIELDS = ((('Camera', 'Resolution'), 1), (('Camera', 'Offset'), 0))
```

Settings a person changes live in the configuration YAML, not in constants (references/yaml.md).

## Docstrings ✅ (format) 📄 (content)

The RP format — not Google, NumPy or Sphinx:

```python
def Hardware_And_Mode(config_path: str) -> tp.Tuple[str, str]:
    """
    Description:
        Split a mode file's name, 'Config_<Hardware>_Mode_<Mode>.yaml', into its hardware and mode.
        A name without the '_Mode_' part (the pre-mode convention) is all hardware, with no mode.

    Args:
        (1) config_path [string]: The configuration file path.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (hardware, mode); either may be '' when the name does
                                           not follow the convention.
    """
```

- `Args:` entries are numbered `(1) …`; consecutive arguments of one type may share an entry,
  `(1 - 4) x, y, w, h [float]: …`. The return is named `parameter`.
- Types in brackets, in domain notation: `[string]`, `[float]`, `[bool]`, `[Vector<int> 1x2]`,
  `[Matrix<uint8> HxWx3]`, `[Dict<string, string>]`, `[Scale_Str(object)]`, `[function]`.
- Optional blocks under `Description:`: `Note:`, `Reference:`. A keyword-only argument says
  `REQUIRED, keyword-only:` in its entry.
- A class docstring adds `Initialization of the Class:` with `Args:` and an `Example:` block —
  except exception classes and Qt classes, which the UI builds (✅ exempted by the checker).
- A test docstring has `Description:` saying what behaviour it pins and why it matters.

Comments are block comments above the code, saying *why*; multi-step bodies number their steps
`# 1\ …`, `# 2\ …` (e.g. `Load_Configuration`).

## Types and data 📄 (✅ annotations present)

- Annotate every parameter and return with `tp.*` (`tp.Optional`, `tp.Tuple`, `tp.Dict`…);
  `__init__` returns `-> None`.
- Data carriers are `@dataclass` `*_Str` classes in `src/Parameters/`, every field with a default
  and a comment ending in `#   Unit [type]` (`(mm/px)`, `(px)` for units). Sequences use
  `field(default_factory=list)`.
- Behaviour classes hold state in `self.__private` attributes, introduced by `# << PRIVATE >> #`
  in `__init__` (26 of the 30 constructors that set private state do), and expose it through
  `@property`.
- A keyword-only argument (`*,`) with no default is how a caller is made to state something that
  must not be defaulted (`Build_Set_Metadata(..., scale, configuration, window)`,
  `Write_Calibration(..., hardware, header_source, output_path, record)`).

## Errors and reporting 📄

- A failure the operator must see is a `*_Error_Cls` raised with a full, actionable sentence —
  what is wrong and what to do: *"No configuration has been loaded, so the camera settings are
  unknown. Load a configuration, then connect."* The UI prints it verbatim. 9 such classes exist.
- Wrap a lower-level exception with `raise … from exc`, keeping the operator sentence at the top.
  A settings failure is not reported as a missing device (`Basler_Settings_Error_Cls`).
- A validation that can find several problems collects them all and raises once
  (`Load_Configuration` → `Configuration_Error_Cls` listing every problem).
- Assert-inside-try-then-print is used where a function reports and returns False instead of
  raising (`Write_Calibration`): `except AssertionError as error: print(f'[ERROR] …')`.
- Never a bare `except:`. `except Exception` only at a boundary — re-raising as an operator
  sentence, or deliberately swallowing where the caller must not fail (a log sink, a close on
  DISCONNECT) with a comment saying so — and always marked `# noqa: BLE001` (all 16 in `src/`
  outside the inherited `Basler.py` are).
- The application logs through the session logger (`src/Logger/Core.py`); the Qt-free layers
  emit through injected callbacks (`Set_Log_Callback`, `stage_cb`, `progress_cb`) and never hold
  the logger. Scripts print `[INFO]` / `[WARNING]` / `[ERROR]` lines. ✅ no `logging` module.

## Tests 📄

- pytest. `test/<Domain>/test_<module>.py` mirrors `src/<Domain>/<Module>.py`;
  `test/integration/` for cross-module contracts and the pipeline; `pytest.ini` uses
  `--import-mode=importlib`, so two `test_core.py` files coexist without `__init__.py`.
- Shared fixtures in `test/conftest.py` (the repository root, the reference frame and its shape).
- `@pytest.mark.slow` for a test that needs the model weights; skipped unless `--runslow`.
- A test states a behaviour in its name and docstring; a stand-in for hardware or a model is a
  small `_Cls` in the test file, never a mocking framework.
- **A test calls the code it names, never a copy of its logic.** A test that re-derives the answer
  the way the code does passes whatever the code does. Instances: the installer check re-implemented
  in Python instead of sourcing `install.sh`; `Screen_Understanding` compared against the same
  helpers re-assembled (it now pins the exact text); the reading's Task "tested" by comparing
  constants to literals, never running the code that chooses it.
- **A UI test asserts what is rendered, not the value handed to the widget.** Grab the widget
  (`widget.grab()`) and compare pixels, or render a rich-text label through `QTextDocument`, and
  measure on a SHOWN, laid-out widget. Instances: the hover state that never rendered; the log
  columns compared on unshown labels (all 640 px wide by default); the object label compared as
  its source string while the screen showed `Object 1· Confidence 91%` (rich text drops a leading
  space). `test/UI/test_paint_smoke.py` and `test/UI/test_signal_wiring.py` show the pattern.
- **A fixed test is proven, not asserted.** Break the thing it names once — delete the line,
  disconnect the signal, swap the branch — and watch it fail; a test that stays green was not
  testing it. Do it in a subprocess on a byte-exact copy, restore the file in `finally`, and check
  `git status` afterwards. Run the subprocess with `PYTHONDONTWRITEBYTECODE=1`: a mutation of the
  same byte length, restored within the same second, leaves a `.pyc` that still looks current
  (it is keyed on the source's size and whole-second mtime), so later runs execute the mutant — the
  symptom is a test failing for a reason no longer in the source. Clearing `__pycache__` fixes it.
- **A script test runs the script the way a person does.** Tests that load an `Example/` script
  inside pytest inherit `test/conftest.py`'s import setup (src/, App/ already on the path), so
  they exercise it under conditions no user has: the camera scripts' working-directory-relative
  `'../../src'` failed for anyone following the README from the repository root, and every such
  test stayed green. Load or run it in a fresh interpreter (`subprocess`, `sys.executable`) from an
  unrelated working directory — `test/Camera/test_reference_harnesses.py` has the pattern.
- **A static-analysis hit is a candidate, not a finding.** vulture, pyflakes and coverage say where
  to look; the check is finding the reader. For UI code the reader is often a paint path or a
  rich-text render that a grep does not obviously connect: vulture called the status cell's
  `dot_color` dead, and `Set_Value` draws the ● with it. Only what survives that check is removed.
- A test that needs the weights asks `require_weights` (`test/conftest.py`): it runs when they are
  there, skips loudly naming the missing path when they are not, and fails under `--runslow`. An
  early `return` reads as a pass.
- The checker relaxes naming, docstring completeness and typing for pytest-dispatched names
  (`test_*`, `pytest_*`, fixtures); helpers in a test file are checked in full.

## Scripts (`Example/`) 📄

A runnable script: header, a `sys.path` append reaching `src/` (two idioms coexist — **unsettled**,
see SKILL.md), annotated imports, a
`CONST_*` block, `def main():` with a `Description:` docstring, `[INFO]` progress lines, and
`if __name__ == '__main__': sys.exit(main())`. A harness that captures or renders what the app
does goes through the app's own path (`scan.py` → `Basler_Camera_Cls`; `analyze.py` reads the
configuration's flags) — the only exception is stated where it is (`calibrate.py --capture`).

## Line length ✅ (150) 📄 (120)

Aim for ≤ 120 characters; wrap by aligning continuation lines under the opening bracket. The
checker errors above 150.
