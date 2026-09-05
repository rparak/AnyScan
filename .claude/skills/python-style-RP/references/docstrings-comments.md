# Docstrings and comments — RP

The project uses a custom docstring format. It resembles Google style but is not
Google style: arguments are numbered, types use a domain notation in square
brackets, and the summary sits under an explicit `Description:` heading.

## Function docstring

```python
def Check_Theta_Limit(theta: tp.List[float], Robot_Parameters_Str: Parameters.Robot_Parameters_Str) -> tp.List[bool]:
    """
    Description:
        Function to check that the desired absolute joint positions are not out of limit.

    Args:
        (1) theta [Vector<float> 1xn]: Desired absolute joint position in radians / meters.
                                        Note:
                                            Where n is the number of joints.
        (2) Robot_Parameters_Str [Robot_Parameters_Str(object)]: The structure of the main parameters of the robot.

    Returns:
        (1) parameter [Vector<bool> 1xn]: The result is a vector of values with a warning if the limit 
                                      is exceeded.
    """

    th_limit_err = np.zeros(theta.size, dtype=bool)
```

Rules:

- `Description:` always present, indented one level, opening with "Function to
  ..." / "Get ..." / a plain statement of purpose.
- `Args:` entries numbered `(1)`, `(2)`, ... — omit the whole block if there are
  no arguments.
- `Returns:` entry is conventionally named `parameter`, numbered, even when there
  is only one. Omit the block for `-> None`.
- Continuation lines of a long argument description are aligned under the start
  of the description text, not at a fixed indent.
- Nested `Note:` blocks are indented a further level under the entry they qualify.
- One blank line after the closing `"""`, then the first statement.

## Type notation in docstrings

The bracketed type is domain notation, not Python notation:

| Notation | Python value |
| --- | --- |
| `[float]`, `[int]`, `[bool]`, `[string]` | scalar |
| `[Vector<float> 1x3]` | 1-D array of fixed length |
| `[Vector<float> 1xn]` | 1-D array of variable length (define `n` in a `Note:`) |
| `[Matrix<float> 4x4]` | 2-D array |
| `[Robot_Parameters_Str(object)]` | an instance of a project dataclass |
| `[Homogeneous_Transformation_Matrix_Cls(object)]` | an instance of a project class |

The Python annotation and the docstring type are allowed to disagree — the
annotation says `tp.List[float]` while the runtime value is an `np.ndarray` and
the docstring says `[Vector<float> 1x3]`. Follow the existing pattern; do not
"fix" the annotation to `np.ndarray`.

## Class docstring

```python
class Point_Cls(object):
    """
    Description:
        A specific class for working with three-dimensional point as a primitive object.

        Note:
            A point is a location in space whose position is described by the coordinates of a coordinate 
            system given by a reference point, called the centroid (or origin), and several coordinate axes.

            Equation:
                p = (x, y, z)

    Initialization of the Class:
        Args:
            (1) centroid [Vector<float> 1x3]: Center position (X, Y, Z) of the point. 

        Example:
            Initialization:
                # Assignment of the variables.
                p   = [0.0, 0.0, 0.0]
                p_n = [1.0, 0.0, 0.0]

                # Initialization of the class.
                Cls = Point_Cls(p)

            Features:
                # Properties of the class.
                Cls.Centroid

                # Functions of the class.
                Cls.Transformation(p_n)
    """
```

- `Initialization of the Class:` documents `__init__`, so `__init__` itself
  carries no docstring.
- The `Example:` block is expected on every `_Cls`. It shows a variable
  assignment section, the construction call bound to the name `Cls`, then a
  `Features:` section listing the properties and the methods a caller would use.
  Aligned `=` signs in the assignment section are part of the style.
- `@dataclass` `*_Str` classes get a short docstring only — `Description:` plus
  one sentence, no `Args:`, no `Example:`.

## Optional blocks

Indented under `Description:`, in this order when several appear:

| Block | Use |
| --- | --- |
| `Note:` | Clarification, definitions, meaning of symbols such as `n` |
| `Equation:` | The mathematics the implementation follows, in plain text |
| `Reference:` | Paper or book the method comes from, author then title in quotes |

## Comments

Density is roughly one comment line to six code lines (2 600 : 14 311). Match it —
sparse code reads as unfinished in this codebase.

- Block comments above the statement, at the statement's indentation. Inline
  trailing comments are not used.
- Numbered procedure steps: `# 1\ Calculation of position error (e_i_p).` — the
  backslash is the project's separator. Inside a regular comment this is
  harmless; inside a string or docstring it produces a `SyntaxWarning`, so write
  `1)` there instead.
- Sub-notes are indented under the parent comment with three spaces:
  ```python
  # To obtain the centroid, we use the formula:
  #   (1 - t)*a + t*b = (1 - 0.5)*a + 0.5 * b
  #   Note:
  #       t is equal to 0.5, which is half of the line segment.
  ```
- Comments explain the mathematics and the intent, not the syntax.
- Imports each carry a comment: `# Numpy (Array computing) [pip3 install numpy]`
  for third-party, `# Typing (Support for type hints)` for stdlib, and for
  project imports a `# Custom Lib.: Robotics Library for Everyone (RoLE)` group
  header followed by `#   ../RoLE/<Path>/<Module>` above each one.
- Dataclass fields each get a comment ending with a unit line:
  ```python
  # Limits of absolute joint position in radians and meters.
  #   Unit [Vector<float>]
  Limit: tp.List[float] = field(default_factory=list)
  ```
- Section headings inside `main()` are bare triple-quoted strings, not comments:
  ```python
  """
  Description:
      Time evaluation of different calculation methods.
  """
  ```

All comments and docstrings are in English (2 595 of 2 600 comment lines are
pure ASCII).
