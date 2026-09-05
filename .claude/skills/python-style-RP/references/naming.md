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

- Attributes: `self.__name` (double underscore, name-mangled), declared in
  `__init__` under a `# << PRIVATE >> #` marker comment.
- Methods and module functions: `__Pascal_Snake_Case`.
- Exposure is via `@property` with the public `Pascal_Snake_Case` name — the
  property is often the capitalised form of the private attribute
  (`self.__centroid` → `Centroid`).
