# Typing, classes and data structures — RoLE

## Type hints

- `import typing as tp` in every module that annotates anything. All hints are
  written through the alias: `tp.List[float]`, `tp.Tuple[bool, float]`,
  `tp.Union[str, int]`, `tp.Optional[str]`, `tp.Dict[str, float]`, `tp.TypeVar`.
- Never `list[float]`, never `from typing import List`, never
  `from __future__ import annotations` (0 of 68 files use it).
- Coverage is effectively total: 481 of 482 parameters annotated, 360 of 413
  returns. Annotate returns too; the 53 gaps are oversights, not a convention.
- `__init__` is annotated `-> None`.
- Arrays: the annotation is `tp.List[float]` or `tp.List[tp.List[float]]` even
  when the value is an `np.ndarray`. The docstring carries the real shape.
- `tp.TypeVar` is used where a method returns its own class type.

## Behaviour classes — `*_Cls`

```python
class Line_Segment_Cls(object):
    """
    Description:
        ...
    Initialization of the Class:
        Args:
            (1) a [Vector<float> 1x3]: Start point of the line segment (ray).
            (2) b [Vector<float> 1x3]: End point of the line segment (ray).
        Example:
            ...
    """

    def __init__(self, a: tp.List[float] = None, b: tp.List[float] = None) -> None:
        # << PRIVATE >> #
        self.__a = np.array(a if a is not None else [0.0] * CONST_DIMENSION, dtype=np.float64)
        self.__b = np.array(b if b is not None else [0.0] * CONST_DIMENSION, dtype=np.float64)

    @property
    def a(self) -> tp.List[float]:
        """
        Description:
            Get the start point of the line segment.

        Returns:
            (1) parameter [Vector<float> 1x3]: Start point (X, Y, Z).
        """

        return self.__a
```

- Explicit `(object)` base — 23 of 34 classes declare a base, and plain classes
  declare `object` rather than leaving the parentheses empty.
- All state is private and name-mangled `self.__x`, introduced by the
  `# << PRIVATE >> #` marker on the first line of `__init__`.
- Access goes through `@property`. There are 82 properties across 34 classes;
  a public attribute is the exception, not the norm.
- Property names are `Pascal_Snake_Case` (`Centroid`, `Direction`, `Shape`) or a
  bare mathematical symbol matching the docstring (`T`, `R`, `p`, `a`, `b`,
  `N`, `S`). The symbol form is correct here even though it breaks the general
  casing rule — the equation in the docstring is the naming authority.
- Setters are written as explicit `Set_*` methods, not `@x.setter`.
- Factory-style construction is a plain function or a classmethod named
  `Get_*` / `Generate_*`, not `from_*`.
- No `__slots__`, no `__repr__`, no `__eq__` — none are defined anywhere.

**Note on the source:** the repository writes mutable defaults directly
(`def __init__(self, centroid: tp.List[float] = [0.0] * CONST_DIMENSION)`).
This is a real bug — the list is shared across all instances. The template above
uses the `None` sentinel instead. Keep every other aspect of the pattern.

## Data structures — `*_Str`

```python
@dataclass
class Theta_Parameters_Str(object):
    """
    Description:
        The auxiliary structure of the joint (theta) parameters.
    """

    # Zero absolute position of each joint.
    #   Unit [float]
    Zero: float = 0.0
    # Limits of absolute joint position in radians and meters.
    #   Unit [Vector<float>]
    Limit: tp.List[float] = field(default_factory=list)
    #   Identification of the type of joint.
    #       Note: R - Revolute, P - Prismatic
    #       Unit [string]
    Type: str = ''
```

- `from dataclasses import dataclass, field`.
- Plain `@dataclass` — no `frozen=True`, no `slots=True`, no `eq=False`.
- Field names are `Pascal_Snake_Case`, matching the class-attribute style rather
  than PEP 8 (`Zero`, `Home`, `Limit`, `Name`, `Type`, `Axis`, `Direction`).
- Every field has a default. Scalars get a literal, sequences get
  `field(default_factory=list)`.
- Every field is preceded by a comment block ending in a `#   Unit [type]` line.
  Enumerated values are documented in a `#       Note:` line rather than an
  `Enum`.
- Structures nest: `Robot_Parameters_Str` contains `Theta_Parameters_Str`,
  `DH_Parameters_Str`, `T_Parameters_Str`, `Collider_Str`.
- `(object)` on the class line is optional here — both forms appear.

Not used anywhere in the project: `pydantic`, `attrs`, `NamedTuple`,
`TypedDict`, `Enum`, `Protocol`, `ABC`, `@abstractmethod`. Do not introduce them.

## Constants block

Every module that defines constants opens the group with a description string:

```python
"""
Description:
    Initialization of constants.
"""
# The calculation will be performed in three-dimensional (3D) space.
CONST_DIMENSION = 3
# Shape (Box):
#   Vertices: 8; Space: 3D;
CONST_BOX_SHAPE = (8, CONST_DIMENSION)
```

Constants may be built from other constants. Composite configuration is a plain
`dict` literal, not a class:

```python
CONST_IK_PROPERTIES = {'delta_time': 0.2, 'num_of_iteration': 500, 
                       'tolerance': 1e-30}
```

Continuation lines align under the opening brace.

## Numeric conventions

- `np.float64` is the working precision: `np.array(x, dtype=np.float64)`,
  `np.zeros(n, dtype=np.float64)`.
- Tolerances come from `CONST_EPS_32` / `CONST_EPS_64` rather than literals.
- Angles are radians internally; conversion helpers are `Degree_To_Radian` and
  `Radian_To_Degree`.
- Comparisons against zero use the epsilon constants, not `== 0.0`.
