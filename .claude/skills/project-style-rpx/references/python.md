# Python

✅ = enforced by `scripts/check_style.py`, 📄 = documentation only. Examples are generic and
hypothetical; the project reference names its own.

## Header ✅

Every `.py` file opens with the `#`-comment block (copy `assets/header.txt`): the licence text with
`Copyright (c) <year> <holder>`, then `Author   : <author>` and `File Name: ../<path from src/ or
the repo root>`, between `## ===…=== ##` rules: `../Reader/Core.py` for `src/Reader/Core.py`,
`../scripts/run_report.py` for a script, `../test/Reader/test_core.py` for a test. The holder and
the licence's first line come from the project's `check_style.json`; the checker requires both and
compares the file name, skipping a placeholder (`<...>`), so the templates in `assets/` pass as
they are. The checker also accepts a `"""` docstring header; a project uses one form.

The holder owns the copyright (often an institution); the author is the person who wrote the code.
They are the same unless the project reference says otherwise (example: holder *Example Lab*,
author *Jane Doe*). The checker compares the holder, never the author line.

## Names ✅

The checker also checks the Pascal_Snake_Case before a class name's suffix, and that an exception
class (deriving from an exception directly or through a project class) ends in `_Error_Cls`.

| Kind | Convention | Example (hypothetical) |
|---|---|---|
| Behaviour class | `Pascal_Snake_Case_Cls`, explicit base | `Report_Builder_Cls(object)` |
| Dataclass | `Pascal_Snake_Case_Str`, fields `Pascal_Snake_Case` | `Run_Configuration_Str` |
| Exception | `Pascal_Snake_Case_Error_Cls` | `Configuration_Error_Cls(ValueError)` |
| Function / method / property | `Pascal_Snake_Case`, verb-first where it acts | `Load_Configuration`, `Read_Table`, `Check_Limits` |
| Private method / attribute | `__Pascal_Snake_Case` / `self.__snake_case` | `__Apply_Defaults`, `self.__table` |
| Parameter / local | `snake_case`, or a math symbol matching the formula | `config_path`, `x`, `n`, `A_b`, `w_i` |
| Parameter carrying a `*_Str` | named after the structure | `Run_Configuration_Str` |
| Module constant | `CONST_UPPER_SNAKE` | `CONST_MAX_ROWS` |
| Test function / fixture | pytest's convention: `test_<the behaviour as a sentence>`, lowercase fixtures | `test_the_export_round_trips_byte_for_byte`, `tmp_path` |
| Test helper | `_Pascal_Snake_Case` | `_Load` |

## Imports 📄

Each import has a comment line above it naming the library (and its install command for a
third-party one); project imports sit last under `# Custom Lib.:` with a `#   ../<path>` line:

```python
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: the table reader
#   ../Reader/Core
from Reader.Core import Read_Table
```

✅ `import typing as tp` (never `from typing import`), no relative imports, no
`from __future__ import annotations`. There are no `__init__.py` files: `src/` is on `sys.path`
through `test/conftest.py` in tests and, in scripts, through a path built from `__file__`
(`os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')`), never a
working-directory-relative `'../src'`. The order of the standard-library, third-party and `typing`
imports among themselves is *Unsettled* (SKILL.md).

A heavy runtime used by one tool only is imported where that tool needs it, never by a module the
tests import (references/structure.md).

## Constants 📄

Module constants are `CONST_*` under a `"""Description:\n    Initialization of constants.\n"""`
block, each preceded by a comment saying what it means, where the value comes from and why, ending in
`#   Unit [type]`:

```python
# Rows read per chunk; above this the reader's peak memory exceeds 1 GB on the reference input
# (measured 2026-01-12, the method in design-decisions.md).
#   Unit [int]
CONST_CHUNK_ROWS = 100000
```

A value a person changes for a deployment lives in the project's configuration file, not in a
constant; a value with a single legal value is a constant, not a field (references/yaml.md).

## Docstrings ✅ (format) 📄 (content)

The RP format - not Google, NumPy or Sphinx:

```python
def Weighted_Mean(x: np.ndarray, w: np.ndarray) -> float:
    """
    Description:
        The weighted mean sum(w_i x_i) / sum(w_i), summed with math.fsum so that many small terms
        are not lost against one large one.

    Args:
        (1 - 2) x, w [Vector<float> 1xN]: Values and their weights (w >= 0, sum(w) > 0).

    Returns:
        (1) parameter [float]: The weighted mean, in the unit of x.
    """
```

- `Args:` entries are numbered `(1) …`; consecutive arguments of one type may share an entry,
  `(1 - 2) x, w [Vector<float> 1xN]: …`. The return is named `parameter`.
- Types in brackets, in domain notation: `[string]`, `[float]`, `[bool]`, `[Vector<float> 1xN]`,
  `[Matrix<float> 3x3]`, `[Dict<string, float>]`, `[Run_Configuration_Str(object)]`, `[function]`.
  Units follow in brackets: `[m]`, `[s]`.
- Optional blocks under `Description:`: `Note:`, `Reference:` (a manual page, a SPEC section). A
  keyword-only argument says `REQUIRED, keyword-only:` in its entry.
- A class docstring adds `Initialization of the Class:` with `Args:` and an `Example:` block -
  except exception classes and Qt classes (✅ exempted by the checker; Qt: references/ui.md).
- A test docstring has `Description:` saying what behaviour it pins and why it matters.

Comments are block comments above the code, saying *why*; multi-step bodies number their steps
`# 1\ …`, `# 2\ …`.

A comment is removed only when it is **stale** (describes code that has changed), **false**, or
**restates the code** (`# increment i`). A comment that explains why - above all one recording why a
value was chosen (the measurement behind a threshold, the manual page behind a dimension, the
alternative rejected) - stays, even when it is long and even when the code around it is rewritten.
It is the project's memory of a decision that the code alone cannot show; removing it as "noise" is
how a sourced value gets tuned back. A stale why-comment is corrected, not deleted, when its reason
still holds.

A comment or docstring describes the code as it is, not how it got there: no "was", "until step 4",
"the old version did", "removed in". History is in git; a reason that came from a past mistake is
stated as the reason ("a soft coupling let the part drift"), with the commit or design-decisions
entry to cite when the detail matters.

## Types and data 📄 (✅ annotations present)

- Annotate every parameter and return with `tp.*` (`tp.Optional`, `tp.Tuple`, `tp.Dict`…);
  `__init__` returns `-> None`.
- Data carriers are `@dataclass` `*_Str` classes, every field with a comment ending in
  `#   Unit [type]`. Sequences use `field(default_factory=list)`. Each lives in its domain's `Core.py`;
  every field has a default (a REQUIRED value is enforced by the loader, not by the dataclass).
- Behaviour classes hold state in `self.__private` attributes, introduced by `# << PRIVATE >> #`
  in `__init__`, and expose it through `@property`.
- A keyword-only argument (`*,`) with no default is how a caller is made to state something that
  must not be defaulted.
- **One canonical unit per quantity**, declared in the project reference (*Units*). SI is the
  default, not mandatory: a project whose inputs and outputs are all in °C keeps °C. Code uses the
  canonical unit only; a value in another unit appears only where an input carries it (a
  configuration field marked `[deg]`, a column of an input file) and is converted once, at load.
  No round trip (°C → K → °C): a conversion that a later step undoes is not made.

## Errors and reporting 📄

- A failure the operator must see is a `*_Error_Cls` raised with a full, actionable sentence -
  what is wrong and what to do: *"The cache data/cache.npz was built from a different input than
  data/input.csv. Rerun scripts/build_cache.py."* A script prints it verbatim as an `[ERROR]` line.
- A check that finds a violation names every one with its numbers, never just `False`.
- Wrap a lower-level exception with `raise … from exc`, keeping the operator sentence at the top.
- A validation that can find several problems collects them all and raises once.
- Never a bare `except:`. `except Exception` only at a boundary - re-raising as an operator
  sentence, or deliberately swallowing where the caller must not fail, with a comment saying so - and
  always marked `# noqa: BLE001`.
- ✅ no `logging` module. Scripts print `[INFO]` / `[WARNING]` / `[ERROR]` lines. `src/` modules
  report through return values, exceptions and injected callbacks, and never print.
- **A known warning from a library is filtered by its exact message, nothing broader.** When a
  dependency prints or raises a warning the project has accepted (recorded in KNOWN_ISSUES with its
  cause), one function captures the library's output and its Python warnings around the call that
  causes it, removes exactly that message, passes every other line and warning on unchanged, and
  prints one `[INFO] Known: ...` line naming the KNOWN_ISSUES item. No `warnings.filterwarnings`
  by category or module, and no silenced stderr: a new warning must still be seen. A test pins
  both halves: the known one becomes the INFO line, another one still appears.

## Tests 📄

- pytest. `test/<Domain>/test_<module>.py` mirrors `src/<Domain>/<Module>.py`, with topic files in
  the same domain folder where needed; one `test/<scripts>/test_<script>.py` per script; the
  installer and the README have their own test files (the project reference names them).
- Shared fixtures in `test/conftest.py`, which also puts `src/` on `sys.path`. Several
  `test_core.py` files coexist without `__init__.py` through `--import-mode=importlib`.
- A test states a behaviour in its name and docstring; a stand-in is a small `_Cls` in the test file,
  never a mocking framework.
- **A test calls the code it names, never a copy of its logic.** A test that re-derives the answer
  the way the code does passes whatever the code does. Example (hypothetical): an installer test that
  re-implements the OS detection in Python instead of sourcing the installer and calling it.
- **A test never takes its expectation from the thing under test.** An expected value read back
  from the code or data being checked moves with it, so the error the test exists for cancels out.
  Derive the expectation from the rule or a measurement, independently (the SPEC's measured facts,
  the configuration). Example (hypothetical): a required-field test that builds its list from the
  loader's own field table stops testing a field the moment that table makes it optional; name each
  field in the test.
- **A fixed test is proven, not asserted.** Break the thing it names once - delete the line, swap
  the branch, perturb a constant - and watch it fail; a test that stays green was not testing it.
  Do it in a subprocess on a byte-exact copy, restore the file in `finally`, and check `git status`
  afterwards. Run the subprocess with `PYTHONDONTWRITEBYTECODE=1`: a mutation of the same byte length,
  restored within the same second, leaves a `.pyc` that still looks current (it is keyed on the
  source's size and whole-second mtime), so later runs execute the mutant. Clearing `__pycache__`
  fixes it.
- **A mutation counts only when pytest exits 1 with the named test failed.** Exit 4 or 5 (usage
  error, no tests collected - a misspelt node id) is not a failure of the test. A mutation that
  leaves the test green because it is off the path the test exercises says nothing about the test:
  move it onto that path before concluding the test is weak. A mutation that breaks nothing (removing
  a redundant rule changes no output) is a finding about the code, not about the test; say which.
- **A rewrite of tests is checked by its collected count.** When you replace or rewrite tests, compare
  `pytest --collect-only -q` before and after with the count you expect: tests removed, plus tests
  added, parametrized cases each counted. A green run cannot show that a test was deleted.
- **A behaviour-preserving change is proven equivalent.** A refactor, a deduplication or a
  performance change claims the output is unchanged, so show it. First write pinning tests for the
  behaviour the change touches and run them on the **old** code - a pin written after the change can
  only describe the new behaviour. Then compare the output byte for byte before and after on the same
  inputs and a fixed seed (the project reference names the outputs). A difference is either a bug in
  the change or a behaviour change, which is then reported and decided as one, not absorbed into the
  refactor.
- **A bound is tested on both sides of it.** One case just inside passes, one just beyond fails
  (example: a 0.10 mm limit tested with 0.09 and 0.11 mm). For a list of criteria, each criterion has
  a case that fails exactly that criterion while the others pass, so a criterion that never fires
  is found.
- **A regression pin and a sanity bound are different tests.** A pin holds a measured value in a
  narrow band to detect any change; it says nothing about acceptability. A bound comes from the rule
  and is enforced at runtime. Neither is widened to make a failing change pass; a failing pin
  reports its numbers.
- **An expected failure must not be satisfiable by a missing input.** A strict `xfail` with
  `raises=AssertionError` accepts *any* `AssertionError`, including one raised because a fixture file
  is missing. Check an xfail's inputs with `pytest.fail`, and let only the documented assertion raise
  what `raises=` names.
- **A script test runs the script the way a person does.** A test that loads a script inside pytest
  inherits `test/conftest.py`'s `sys.path`, so it passes under conditions no user has. Run it in a
  fresh interpreter (`subprocess`, `sys.executable`) from an unrelated working directory.
- **A static-analysis hit is a candidate, not a finding.** vulture, pyflakes and coverage say where
  to look; the check is finding the reader. Only what survives that check is removed.
- **A slow test is marked**, so the everyday run deselects it (`-m "not slow"`). The full suite runs
  where the project's `CLAUDE.md` puts it: by default before every commit; a project with two tiers
  of checks (per commit, per accepted feature; project-optimize designs them) runs it with the
  second tier.
- In a pytest module (`test_*.py`, `conftest.py`, any file under a test root) the checker skips the
  docstring and typing checks for every function, helpers included; naming is still checked, except
  for pytest's own names (`test_*`, `pytest_*`, fixtures).

## Scripts 📄

A runnable script lives in the project's scripts folder (copy `assets/script_template.py`): header,
a `sys.path` append reaching `src/` built from `__file__`, annotated imports, a `CONST_*` block,
`def main():` with a `Description:` docstring, `[INFO]` / `[WARNING]` / `[ERROR]` lines, and
`if __name__ == '__main__': sys.exit(main())`. A script that writes takes `--out DIR` and writes
`DIR/<configured file name>` (the configuration names the file, the option moves it). A script that
checks or shows what the project
computes goes through the project's own code (references/structure.md > *A harness takes the
project's path*). A script that needs a special launcher on some platform exits with an `[ERROR]`
line naming the right command when it is started otherwise.

- **A script whose product is a report** prints the report on stdout and its own `[INFO]` /
  `[WARNING]` / `[ERROR]` lines on stderr, so stdout can be compared byte for byte.
- **A script that checks** exits `0` when every check passes, `1` when a check fails (each failure
  named), and `2` when it could not check (a missing input, an unstable run, a refused option) -
  never `0` for something it did not check. The docstring states the codes.

## Line length ✅ (150) 📄 (120)

Aim for ≤ 120 characters; wrap by aligning continuation lines under the opening bracket. The
checker errors above 150.
