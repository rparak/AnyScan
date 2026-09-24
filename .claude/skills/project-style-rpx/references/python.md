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
  DISCONNECT) with a comment saying so — and always marked `# noqa: BLE001` (all 15 in `src/`
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
