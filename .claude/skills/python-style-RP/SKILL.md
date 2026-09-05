---
name: python-style-RP
description: Write Python in the exact RP house style (the Python house style of Roman Parak) — MIT header docstring in every file, Pascal_Snake_Case names with _Cls and _Str suffixes, tp.* type hints on every parameter, name-mangled private attributes, CONST_* module constants, the RP custom docstring format (Description / Args with numbered (1) entries / Returns), annotated imports, and print('[INFO] ...') instead of logging. Use this skill for any Python work in an RP-style repository, whenever the user asks for code matching the RP style, adds a module, class, function, property or evaluation script, ports code into RP, bootstraps a new project on RP conventions, or reviews Python code for RP style compliance. Apply it even when the user does not mention style explicitly — this codebase deliberately departs from PEP 8 and consistency is the point.
---

# RP Python Style

Derived from https://github.com/rparak/RoLE @ `ee0e67a` (2026-08-16), 68 `.py`
files, 17 278 lines. MIT License, © 2023 Roman Parak.

**This project deliberately does not follow PEP 8 naming.** Do not "correct" it.
There is no formatter, linter or type checker configured, so nothing will
mechanically fix a deviation — the rules below are the only enforcement.

Rules are marked **[strong]** (≥80% of cases) or **[weak]** (a preference).
No rule here is **[enforced]**, because the repository has no `pyproject.toml`,
no pre-commit hooks and no CI.

## Non-negotiables

1. Every `.py` file opens with the MIT + author header docstring. Copy
   `assets/header.txt` and fix the `File Name:` line. [strong: 68/68]
2. Classes are `Pascal_Snake_Case_Cls`; `@dataclass` structures are
   `Pascal_Snake_Case_Str`. [strong: 34/34]
3. Functions, methods and properties are `Pascal_Snake_Case` —
   `Get_Angle_Axis_Error`, `Forward_Kinematics`, `Check_Theta_Limit`. [strong]
4. Parameters and local variables are `snake_case`, or terse mathematical
   symbols matching the equation in the docstring (`theta`, `th_i`, `T`, `R`,
   `p`, `e_i`). [strong: 376/482]
5. Annotate **every** parameter and return using `import typing as tp` —
   `tp.List[float]`, not `list[float]`, not `List[float]`. [strong: 481/482]
6. Every class, method, property and function gets a docstring in the RP
   format (§ Docstrings). Coverage is 34/34 classes and 392/413 functions.
7. Private state is name-mangled `self.__x` and introduced by a
   `# << PRIVATE >> #` marker comment in `__init__`. [strong]
8. Module constants are `CONST_*`, declared under a
   `"""Description:\n    Initialization of constants.\n"""` block. [strong: 112]
9. Every import carries a comment naming the library and its install command.
   [strong: 406/406 import statements are absolute; 0 relative]
10. Report status with `print(f'[INFO] ...')` / `[WARNING]` / `[ERROR]`. The
    `logging` module is not used anywhere. [strong: 317 prints, 0 loggers]
11. Single quotes for strings, `f'...'` for interpolation (715 f-strings, 2 `%`,
    0 `.format`). Triple-double `"""` for docstrings only. [strong]
12. One blank line between top-level classes and functions — not two. [strong]
13. Two tightly-coupled assignments may share a line with `;` —
    `p = T.p.all(); q = T.Get_Rotation('QUATERNION')`. This is deliberate here
    (289 occurrences), not a slip. Never more than two. [strong]
14. Pre-configured dataclass instances at module level are named
    `<Subject>_Str` in `Pascal_Snake_Case`, **not** `CONST_*` —
    `Universal_Robots_UR3_Str`, `ABB_IRB_120_Env_ID_0_Str`. `CONST_*` is for
    plain values only. [strong]
15. A parameter that carries a `*_Str` structure is named after the structure:
    `def Forward_Kinematics(theta, method, Robot_Parameters_Str)`. This
    overrides the snake_case rule for parameters. [strong: 60 occurrences]

## Layout

```
src/
├── RoLE/                 # the core library — pure algorithms, no simulator deps
│   ├── <Domain>/
│   │   ├── Core.py       # the classes and main entry functions of the domain
│   │   └── Utilities/    # supporting free functions, split by theme
│   │       └── <Theme>.py
│   └── Parameters/       # @dataclass *_Str definitions only
├── Blender/              # Blender-specific bindings, mirrors RoLE/ structure
└── PyBullet/             # PyBullet-specific bindings, mirrors RoLE/ structure
Example/                  # runnable scripts, tree mirrors src/
Data/  URDFs/  Textures/  Blender/   # non-code assets
```

- Directories are `Pascal_Snake_Case`, matching the domain concept
  (`Transformation`, `Interpolation/B_Spline`, `Kinematics/Utilities`).
- **There are no `__init__.py` files.** Do not add them. Imports resolve because
  scripts append `src` to `sys.path`.
- New algorithm class → `src/RoLE/<Domain>/Core.py`. New free helper →
  `src/RoLE/<Domain>/Utilities/<Theme>.py`. New data structure →
  `src/RoLE/Parameters/<Thing>.py`. New runnable → `Example/<mirror path>/`.
- The core library must not import Blender or PyBullet. The dependency direction
  is one-way: `Blender/` and `PyBullet/` import `RoLE/`, never the reverse.

More: `references/layout.md`

## Naming

| Kind | Convention | Example |
| --- | --- | --- |
| Directory | `Pascal_Snake_Case` | `Transformation/Utilities` |
| Module | `Pascal_Snake_Case` or `Core.py` / `Utilities.py` | `Forward_Kinematics.py` |
| Class | `Pascal_Snake_Case_Cls`, explicit `(object)` base | `Homogeneous_Transformation_Matrix_Cls` |
| Dataclass | `Pascal_Snake_Case_Str` | `Robot_Parameters_Str` |
| Function / method | `Pascal_Snake_Case`, verb-first | `Get_Best_IK_Solution` |
| Property | `Pascal_Snake_Case` or a bare math symbol | `Centroid`, `T_EE`, `R` |
| Private attribute | `self.__snake_case` | `self.__centroid` |
| Private function | `__Pascal_Snake_Case` | `__Get_Matrix_Trace` |
| Parameter / local | `snake_case` or math symbol | `theta`, `th_limit`, `T_desired` |
| Parameter holding a `*_Str` | named after the structure | `Robot_Parameters_Str` |
| Constant (plain value) | `CONST_UPPER_SNAKE` | `CONST_MATH_HALF_PI` |
| Preset `*_Str` instance | `Pascal_Snake_Case_Str` | `Universal_Robots_UR3_Str` |
| Dataclass field | `Pascal_Snake_Case` — **not** snake_case | `Zero`, `Home`, `Limit`, `Type` |

Verb prefixes in use: `Get_`, `Set_`, `Generate_`, `Check_`, `Convert_`,
`Calculate_`, `Add_`, `Remove_`, `Create_`, `Is_`, `Reset_`, `Transformation`.
Suffixes: `_Cls`, `_Str`, `_aux` (temporary working copy), `_i` (loop element),
`_0` (initial value), `_n` (new/next value).

More: `references/naming.md`

## File skeleton

```python
"""
## =========================================================================== ## 
MIT License
... (full text from assets/header.txt) ...
## =========================================================================== ## 
Author   : Roman Parak
Email    : Roman.Parak@outlook.com
Github   : https://github.com/rparak
File Name: ../RoLE/<Domain>/<Module>.py
## =========================================================================== ## 
"""

# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Custom Lib.: Robotics Library for Everyone (RoLE)
#   ../RoLE/Transformation/Core
from RoLE.Transformation.Core import Homogeneous_Transformation_Matrix_Cls as HTM_Cls

"""
Description:
    Initialization of constants.
"""
# Short explanation of what the constant means and why.
CONST_DIMENSION = 3

class Thing_Cls(object):
    ...
```

Order: header docstring → imports (stdlib, then third-party, then
`# Custom Lib.:` group) → constants block → dataclasses → classes → functions.
Each import gets its own comment line above it; custom imports get a second
comment line with the `#   ../RoLE/...` source path.

**The first import segment is whatever sits directly on `sys.path`.** Above,
`RoLE` is the *source repository's* wrapping package, which is why its imports
read `from RoLE.<Domain>...`. This project has no wrapping package: `src/` itself
is the path root, so the first segment is the domain directory
(`from Transformation.Core import ...`). The `assets/` templates therefore use
`<Domain>/<Module>` placeholders in the `# Custom Lib.:` block; fill them in with
the real names. A placeholder is a slot to substitute, not a missing dependency.

## Docstrings

The project uses its own format — **not** Google, NumPy or Sphinx, despite
superficially resembling Google. Reproduce it exactly:

```python
def Get_Angle_Axis_Error(T_desired: tp.List[tp.List[float]], T_current: tp.List[tp.List[float]]) -> tp.List[float]:
    """
    Description:
        One-sentence statement of what the function does, then any longer
        explanation, wrapped at roughly 120 characters.

        The position error is defined as a:
            e_i_p(theta) = d_p_i - p_i(theta),

        where d_p_i is the desired position and p_i is the current position.

        Reference:
            T. Sugihara, "Solvability-Unconcerned Inverse Kinematics by the Levenberg-Marquardt Method."

    Args:
        (1) T_desired [Matrix<float> 4x4]: Homogeneous transformation matrix of the desired position/rotation.
        (2) T_current [Matrix<float> 4x4]: Homogeneous transformation matrix of the current position/rotation.

    Returns:
        (1) parameter [Vector<float> 1x6]: Vector of an error (angle-axis) from current to the desired position/rotation.
    """
```

- Arguments and returns are **numbered** `(1)`, `(2)`, ....
- The type sits in square brackets in a domain notation, not Python notation:
  `[Vector<float> 1x3]`, `[Matrix<float> 4x4]`, `[float]`, `[string]`, `[bool]`,
  `[Robot_Parameters_Str(object)]`.
- The return entry is conventionally named `parameter`.
- Optional blocks, indented under `Description:` — `Note:`, `Equation:`,
  `Reference:`.
- Class docstrings add `Initialization of the Class:` with `Args:` and an
  `Example:` block showing `Initialization:` and `Features:` (the properties and
  methods a caller would use).
- One blank line after the closing `"""` before the first statement.
- Arguments of the same type may be grouped: `(1 - 4) theta, a, d, alpha [float]: ...`.
- Matrix and array literals are aligned column-wise by hand, with padding spaces
  so the elements line up. This is why lines run past 120 characters — keep the
  alignment rather than rewrapping.

Comments are dense — 2 600 comment lines to 14 311 code lines, roughly one in
six. They are block comments above the code, never inline. Multi-step procedures
are numbered `# 1\ ...`, `# 2\ ...`. Comments and docstrings are in English.

More, with the class template: `references/docstrings-comments.md`

## Typing, classes and data

- `import typing as tp`; use `tp.List`, `tp.Tuple`, `tp.Union`, `tp.Optional`,
  `tp.Dict`, `tp.TypeVar`. No `from __future__ import annotations` (0 files).
- `__init__` is annotated `-> None`.
- Numeric arrays are `np.array(x, dtype=np.float64)`; the annotation stays
  `tp.List[float]` even when the runtime value is an `np.ndarray`.
- Data carriers are `@dataclass` classes named `*_Str`, with `Pascal_Snake_Case`
  fields, defaults on every field, and `field(default_factory=list)` for
  sequences. Each field is preceded by a comment ending in a `#   Unit [type]`
  line.
- Behaviour classes are plain `class X_Cls(object)` with `self.__private` state
  exposed through `@property`. There are 82 properties across 34 classes —
  prefer a property over a public attribute.
- No `__slots__`, no `attrs`, no `pydantic`, no `Enum`, no `Protocol`/`ABC`.
- Configuration is a module-level `CONST_*` dict or literal, not a settings class.
- Robot and environment presets are module-level `*_Str` instances in
  `src/RoLE/Parameters/Robot.py` and `src/PyBullet/Configuration/Environment.py`.
  A new robot is added by appending another `<Name>_Str = Robot_Parameters_Str(...)`
  there, not by subclassing.

More: `references/typing-and-data.md`

## Errors

The project has **no custom exception classes** and never raises. The house
pattern is assert-inside-try, caught locally and reported by printing:

```python
def Radian_To_Degree(x: tp.Union[float, tp.List[float]]) -> tp.Union[float, tp.List[float]]:
    """
    Description:
        Functions for converting angles from radians to degrees.

    Args:
        (1) x [float or Vector<float>]: Angle in radians.

    Returns:
        (1) parameter [float or Vector<float>]: Angle in degrees.
    """

    try:
        assert isinstance(x, float) or isinstance(x, np.ndarray)

        return x * (180.0 / CONST_MATH_PI)

    except AssertionError as error:
        print(f'[ERROR] Information: {error}')
        print('[ERROR] Incorrect type of input parameters. Input parameter x must be of type float or np.ndarray.')
```

- `assert` the precondition as the first statement in the `try`, then do the work
  inside the same block. [47 handlers across 13 files]
- Catch `AssertionError as error` only — never bare `except`, never `Exception`.
- The handler prints two lines: `f'[ERROR] Information: {error}'` followed by a
  plain-language `[ERROR]` message naming the offending parameter and the valid
  values.
- The function then falls off the end and implicitly returns `None`. Callers are
  expected to notice; there is no sentinel and no re-raise.
- For enumerated arguments, the handler often adds an `if value not in [...]`
  check to print the specific allowed options.

This swallows failures, which is a genuine weakness. Reproduce it for
consistency, but if the user asks for exceptions that propagate, say once that it
departs from the codebase and then do it their way.

## Example scripts

Runnables in `Example/` follow a fixed shape — see
`assets/script_template.py`. Header docstring, `sys.path` append, annotated
imports, `CONST_*` configuration block, `def main():` with its own
`Description:` docstring, `print(f'[INFO] ...')` progress reporting, and:

```python
if __name__ == '__main__':
    sys.exit(main())
```

Inside `main()`, sections are separated by bare `"""Description: ..."""` string
literals used as visual headings. That is unusual Python but it is the house
pattern — reproduce it.

More: `references/scripts-and-examples.md`

## PyQt applications

Qt dispatches some methods by name, so a blind rename to `Pascal_Snake_Case`
silently breaks the UI. Apply the whole RP style, with these Qt-specific rules:

1. Widget and window classes take `_Cls` and keep their Qt base —
   `class Main_Window_Cls(QMainWindow)`. Methods you write and call yourself are
   `Pascal_Snake_Case` (`Initialize_Ui`, `Connect_Signals`). **Qt-dispatched
   names keep their camelCase and are never renamed** — `paintEvent`,
   `closeEvent`, `resizeEvent`, `eventFilter`, `sizeHint`, and the
   `QAbstractItemModel` overrides `rowCount` / `columnCount` / `data` /
   `headerData` / `setData` / `flags`. Mark each with `# << QT OVERRIDE >> #`.
2. No `connectSlotsByName` / `on_<objectName>_<signal>` auto-connection. Connect
   every signal explicitly in a `Connect_Signals` method. Custom signals are
   `Pascal_Snake_Case` class attributes (`Scan_Finished = pyqtSignal(object)`);
   slots are private, prefixed by the trigger (`__On_Scan_Button_Clicked`).
3. Widgets are private, name-mangled attributes under `# << PRIVATE >> #`,
   prefixed by widget type (`self.__button_scan`, `self.__label_status`).
   `__init__` stays short — `super().__init__()`, declare state, then
   `self.__Initialize_Ui()` and `self.__Connect_Signals()`; no inline widget
   construction. Window/widget config lives in `CONST_*` and a
   `*_Parameters_Str` dataclass, and stylesheets are `CONST_*` string constants.
4. UI classes contain no application logic — they read input, call into the
   domain modules under `src/` (which must be callable without Qt imported), and
   render the result. Long-running work never runs on the UI thread: use a
   `<Task>_Worker_Cls(QObject)` moved to a `QThread`, exposing
   `Pascal_Snake_Case` `pyqtSignal`s for progress, result and error.
5. Do not touch any `Ui_*.py` generated by `pyuic`, or any widget attribute name
   that came from a `.ui` file — those names live in the XML.

More: `references/pyqt.md`

## Converting an existing project

When the task is to rewrite code that already works — not to write new code —
read `references/migration.md` first and follow its phase order. Renaming
everything to `Pascal_Snake_Case` in one pass breaks every call site
simultaneously, so cosmetic changes (headers, docstrings, type hints, comments)
come first, structural changes second, renaming third, and layout last. Establish
a way to verify behaviour is unchanged before touching anything.

## Before returning code

1. Reread the Non-negotiables and check the code against each one.
2. Run `python scripts/check_style.py <files>` and fix everything it reports.
3. Confirm the header docstring `File Name:` line matches the real path.
4. Confirm no `__init__.py` was created and no relative import was used.
5. Anything not covered here: copy the surrounding file, not your own defaults.

## Unknowns

The repository gives no signal on these — follow the user's lead, or ask:

- **Line length.** No formatter. Measured on `src/`: p50 = 37, p90 = 102,
  p95 = 122, p99 = 167, max = 538. Aim for ≤ 120 and wrap by aligning
  continuation lines under the opening bracket, which is what the code does by
  hand. `check_style.py` only errors above 150, since 122 is normal here.
- **Unit tests.** Files named `test_*.py` in `Example/` are demonstration
  scripts, not `pytest` tests. There is no test framework, no `conftest.py` and
  no assertions-as-tests. If the user wants real tests, the style is undefined —
  propose `pytest` and note that it is new to the project.
- **Packaging.** No `pyproject.toml`, `setup.py` or `requirements.txt`. Install
  instructions live in import comments (`[pip3 install numpy]`).
- **Python version.** Not declared. The syntax used is compatible with 3.8+.

## Observed anti-patterns — do not reproduce

These appear in the source but should not be carried into new code:

- Mutable default arguments: `def __init__(self, centroid: tp.List[float] = [0.0] * 3)`.
  Use `None` and build the default inside the body.
- Unescaped backslashes in docstrings and f-strings (`'1\ '`) — 19 files raise
  `SyntaxWarning` on Python 3.12. Use a raw string or write `1)`.
- `== False` / `== True` comparisons — use `not x` / `x`. [52 occurrences]
- Lines beyond ~150 characters, including one of 538. [rare but present]
