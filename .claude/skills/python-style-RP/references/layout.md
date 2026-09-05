# Layout — RP

## The three source trees

```
src/
├── RoLE/        Pure algorithms. Depends only on numpy / scipy / stdlib.
├── Blender/     Blender bindings. Imports RoLE. Runs inside Blender's Python.
└── PyBullet/    PyBullet bindings. Imports RoLE. Runs in normal CPython.
```

Dependency direction is strictly one-way. `src/RoLE/**` must never import
`Blender` or `PyBullet`, or `bpy` / `pybullet`. If an algorithm needs a
simulator, the simulator-specific part goes in the corresponding tree and calls
into `RoLE`.

`Blender/` and `PyBullet/` mirror each other's internal shape:

```
src/<Backend>/
├── Configuration/Environment.py   # scene / world constants and setup
├── Mechanism/Core.py              # Mechanism_Cls for that backend
├── Robot/Core.py                  # Robot_Cls for that backend
├── Parameters/                    # backend-specific *_Str dataclasses
└── Utilities.py                   # backend helper functions
```

## Inside `src/RoLE/`

```
src/RoLE/
├── <Domain>/
│   ├── Core.py                # the classes and primary functions of the domain
│   └── Utilities/             # free functions supporting Core, split by theme
│       ├── <Theme>.py
│       └── ...
└── Parameters/                # dataclass *_Str definitions, one file per subject
    ├── Robot.py
    └── Mechanism.py
```

Existing domains: `Transformation`, `Kinematics`, `Collider`, `Primitives`,
`Interpolation` (with `Bezier/` and `B_Spline/` subdomains), `Trajectory`,
`Simplification`, `Workspace`, `URDF`, `Utilities`, `Parameters`.

**`RoLE` here is the source repository's own package name, not a fixed part of
the style.** That repo wrapped its domains in a `src/RoLE/` package; a new
project substitutes its own. Some projects have no wrapping package at all — the
domains sit directly under `src/` and modules import each other as
`<Domain>.<Module>` (e.g. `from Transformation.Core import ...`), with `src/`
placed on `sys.path`. The `assets/` templates use `<Package>/<Domain>/<Module>`
placeholders precisely so the first segment is filled in per project rather than
hardcoded to `RoLE`.

Rules:

- `Core.py` holds the domain's classes and its headline functions. When a domain
  grows past roughly 900 lines, split supporting free functions into
  `Utilities/<Theme>.py` rather than adding another `Core`-level file.
  `Transformation/Core.py` at 2 163 lines is the outlier, not the target.
- A subdomain with its own algorithm family gets its own directory with its own
  `Core.py` (`Interpolation/Bezier/Core.py`).
- `Utilities.py` (singular file) is used when the domain needs only one helper
  module; `Utilities/` (directory) when it needs several.
- Data structures never live next to the algorithms that use them — they go in
  `Parameters/`.

## `Example/`

Holds runnable demonstration scripts. `Example/` mirrors `src/` the same way
`Evaluation/` did in the source repository — this project renamed the convention
from `Evaluation/` to `Example/`, and that name stays:

```
Example/
├── Kinematics/{FK,IK,Collider}/
├── Blender/{Robot,Mechanism,Collider,Helpers,Workspace}/
├── PyBullet/{Control,Environment}/{Robot,Mechanism}/
├── URDF/
└── Workspace/
```

Script names describe the action: `test_fk.py`, `test_analytical_ik.py`,
`collect_analytical_ik.py`, `generate_workspace.py`. Note that `test_*.py` here
means "a script that exercises and reports", not a `pytest` test.

## No packages

There are no `__init__.py` files anywhere. Modules are found because every
script inserts `src` on `sys.path` before importing:

```python
import sys
if '../../../../' + 'src' not in sys.path:
    sys.path.append('../../../../' + 'src')
```

The number of `../` segments matches the script's depth below the repository
root. Count it from the script's own location; get this wrong and the import
fails at runtime with no other symptom.

Do not add `__init__.py`, do not introduce relative imports, and do not add a
`pyproject.toml` to make the library installable unless the user explicitly asks
for that change — it would alter how every script in `Example/` resolves its
imports.

## Non-code directories

| Directory | Contents |
| --- | --- |
| `Data/` | Generated datasets, organised `Data/<Purpose>/<Robot_Name>/` |
| `URDFs/` | Robot description files |
| `Textures/`, `images/` | Assets for rendering and documentation |
| `Blender/` (root level) | `.blend` scene files — distinct from `src/Blender/` |

New generated data goes under `Data/<Purpose>/<Robot_Name>/`, matching the robot
identifiers already in use: `ABB_IRB_120`, `ABB_IRB_120_L_Ax`,
`ABB_IRB_14000_L`, `ABB_IRB_14000_R`, `EPSON_LS3_B401S`,
`Universal_Robots_UR3`.
