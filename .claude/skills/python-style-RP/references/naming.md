# Naming — RP

## Casing rules

`Pascal_Snake_Case` means each word capitalised, words joined by underscores:
`Homogeneous_Transformation_Matrix_Cls`, `Get_Angle_Axis_From_Matrix`.
This applies to directories, modules, classes, functions, methods, properties
and dataclass fields. It is **not** PEP 8 and it is intentional.

Only parameters, local variables and private attributes are lower `snake_case`.
Only module constants are `CONST_UPPER_SNAKE`.

## Class suffixes

| Suffix | Meaning | Examples |
| --- | --- | --- |
| `_Cls` | A behaviour class with private state and properties | `Point_Cls`, `Robot_Cls`, `Bezier_Cls`, `AABB_Cls` |
| `_Str` | A `@dataclass` structure — data only, no behaviour | `Robot_Parameters_Str`, `Theta_Parameters_Str`, `Collider_Str` |

A class with methods that does real work gets `_Cls`. A passive bundle of
parameters gets `_Str` and is decorated `@dataclass`. There is no third category.

Acronyms stay uppercase and keep the underscore: `AABB_Cls`, `OBB_Cls`,
`DH_Parameters_Str`, `URDF_Generator_Cls`, `B_Spline_Cls`, `Poly_3D_Cls`.

## Function verb prefixes

Observed across `src/`:

| Prefix | Use | Example |
| --- | --- | --- |
| `Get_` | Compute or retrieve and return a value | `Get_Arc_Length`, `Get_Best_IK_Solution` |
| `Set_` | Mutate state, return `None` or `bool` | `Set_Absolute_Joint_Position` |
| `Generate_` | Produce a new collection or dataset | `Generate_Knot_Vector`, `Generate_Workspace_XYZ` |
| `Check_` | Validate, return `bool` or a `bool` vector | `Check_Theta_Limit`, `Check_Overlap_Objects` |
| `Convert_` | Change representation | `Convert_Ax_Str2Id` |
| `Add_` / `Remove_` | Manage a collection or a scene | `Add_External_Object`, `Remove_Object` |
| `Create_` | Build an external artefact (mesh, object) | `Create_Primitive` |
| `Is_` | Boolean predicate | `Is_Valid` |
| `Reset_` | Return to an initial state | `Reset` |

Mathematical operations skip the verb and use the operation name directly:
`Cross`, `Dot`, `Norm`, `Conjugate`, `Inverse`, `Transpose`, `Diagonal`,
`Exponential`, `Factorial`, `Derivative_1st`.

## Variable naming

Domain-mathematical shorthand is preferred over descriptive English **when the
docstring defines the symbol**:

| Symbol | Meaning |
| --- | --- |
| `theta`, `th` | joint position(s), radians or metres |
| `T` | homogeneous transformation matrix |
| `R` | rotation matrix |
| `p` | position vector |
| `q` | quaternion |
| `e_i` | error vector at iteration `i` |
| `J` | Jacobian |

Suffix conventions:

| Suffix | Meaning | Example |
| --- | --- | --- |
| `_i` | element of the current loop iteration | `th_i`, `e_i` |
| `_aux` | temporary working value, discarded after use | `theta_rand_aux` |
| `_0` | initial value | `t_0`, `T_0` |
| `_n` | new / next value | `p_n` |
| `_err` | error indicator | `th_limit_err` |
| `_desired` / `_current` | target vs actual state | `T_desired`, `T_current` |

Units are carried in the docstring, not in the name — the docstring says
"in radians / meters", the variable stays `theta`.

## Constants

All module-level constants are prefixed `CONST_`. Grouping by topic in the name:

- `CONST_MATH_PI`, `CONST_MATH_HALF_PI` — mathematical values
- `CONST_EPS_32`, `CONST_EPS_64` — numerical tolerances by float width
- `CONST_ROBOT_TYPE`, `CONST_MECHANISM_TYPE`, `CONST_CAMERA_TYPE` — selected configuration
- `CONST_FILE_NAME`, `CONST_FILE_NAME_IN`, `CONST_FILE_NAME_OUT`, `CONST_PROJECT_FOLDER` — paths
- `CONST_NULL`, `CONST_NONE_VALUE` — sentinels
- `CONST_DIMENSION`, `CONST_BOX_SHAPE`, `CONST_SIZE` — dimensions

In evaluation scripts, `CONST_*` at the top of the file **is** the configuration
interface — the user edits those lines rather than passing CLI arguments.

## Private members

`__name` (double underscore) is the **default** and `_name` (single) is the
**deliberate exception** — the choice is not cosmetic. `__name` triggers Python
name mangling to `_ClassName__name`; `_name` does not. So the rule turns on
whether the member takes part in inheritance:

- `__name` — internal state and helpers used **only within the defining class**.
  This is the default. Attributes are `self.__name`, declared in `__init__`
  under a `# << PRIVATE >> #` marker comment; methods and module functions are
  `__Pascal_Snake_Case`.
- `_name` — anything that **participates in inheritance**: a method a subclass
  overrides, a method a base class calls on `self` expecting the subclass's
  version, or an attribute a subclass reads. Mangling would silently break these
  — the override would never be reached, with no import error and no test
  failure unless a test happens to exercise that path. Add a brief comment at the
  definition saying why it is single-underscore.

The worked example is `src/Camera/Core.py`: `Camera_Backend_Cls` keeps
`_Open`/`_Close`/`_Grab` single-underscore precisely because the base calls
`self._Open()` and `File_Camera_Cls` / `Basler_Camera_Cls` override them; its own
`self.__connected` stays double, being base-internal. The class docstring states
this rationale — do the same wherever you choose `_name`.

Do **not** reach for `_name` merely to expose a member. Exposure is via
`@property` with the public `Pascal_Snake_Case` name — the property is often the
capitalised form of the private attribute (`self.__centroid` → `Centroid`).
A subclass reaching parent state should go through that public API (as
`Euler_Angle_Cls` reads `self.Type` / `self.all()` from `Vector3_Cls`), not the
parent's private.

**Tests can pin a member as `__`.** Name-mangling means a test that reaches a
private by its mangled name (`getattr(window, '_AnyScan_Window_Cls__thread')`) is
coupled to that member staying double-underscore under that class name —
`test/UI/` does exactly this for `AnyScan_Window_Cls`. Renaming or re-scoping
such a member silently breaks those tests; grep `_ClassName__` before touching
one.

`check_style.py` flags a `__name` that is overridden in a subclass **defined in
the same file** — the exact mistake this rule prevents. It cannot see
cross-file subclasses (static analysis of one file), so a base class and its
subclass in different modules are on you: apply the rule by hand there.
