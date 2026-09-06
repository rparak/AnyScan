"""Regression tests for check_style.py's Args-numbering and mangling rules.

Run with:  pytest .claude/skills/python-style-RP/scripts/test_check_style.py
(stdlib + pytest only; not part of the app's test/ suite).

Both the numbered '(1) ...' form and the grouped '(1 - N) a, b ...' form for
consecutive arguments of the same type are valid (see
references/docstrings-comments.md). This guards against the checker regressing to
accepting only the literal '(1)'.

The mangling tests guard the private-member rule (see references/naming.md): a
`__name` method a subclass in the same file redefines is a dead override and must
be flagged; the single-underscore `_name` hook form must not be.
"""
import ast
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_style", _HERE / "check_style.py")
check_style = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_style)


def _numbering_flags(source: str) -> list:
    """Return the 'Args entries are not numbered' flags for a source snippet."""
    report = check_style.Report()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            if doc:
                check_style.check_docstring_format(doc, node, Path("snippet.py"), report, "function")
    return [item for item in report.items if "not numbered" in item]


_NUMBERED = '''
def f(a: float, b: float) -> float:
    """
    Description:
        A function.

    Args:
        (1) a [float]: The first number.
        (2) b [float]: The second number.

    Returns:
        (1) parameter [float]: The result.
    """
    return a + b
'''

_GROUPED = '''
def f(a: float, b: float) -> float:
    """
    Description:
        A function.

    Args:
        (1 - 2) a, b [float]: Two numbers of the same type.

    Returns:
        (1 - 2) parameter [float]: Two results.
    """
    return a + b
'''

_UNNUMBERED = '''
def f(a: float, b: float) -> float:
    """
    Description:
        A function.

    Args:
        a, b [float]: Two numbers.

    Returns:
        parameter [float]: The result.
    """
    return a + b
'''


def test_numbered_args_accepted():
    assert _numbering_flags(_NUMBERED) == []


def test_grouped_args_accepted():
    assert _numbering_flags(_GROUPED) == []


def test_unnumbered_args_flagged():
    assert _numbering_flags(_UNNUMBERED) != []


def _mangling_flags(source: str) -> list:
    """Return the 'mangling' flags for a source snippet."""
    report = check_style.Report()
    check_style.check_mangled_overrides(ast.parse(source), Path("snippet.py"), report)
    return [item for item in report.items if "[mangling]" in item]


# A subclass redefining a base's `__name` method: the override is dead.
_MANGLED_OVERRIDE = '''
class Base_Cls(object):
    def Run(self) -> None:
        self.__step()

    def __step(self) -> None:
        pass


class Sub_Cls(Base_Cls):
    def __step(self) -> None:   # dead: mangles to _Sub_Cls__step
        pass
'''

# The correct form: a single-underscore hook the subclass overrides.
_SINGLE_UNDERSCORE_HOOK = '''
class Base_Cls(object):
    def Run(self) -> None:
        self._Step()

    def _Step(self) -> None:
        pass


class Sub_Cls(Base_Cls):
    def _Step(self) -> None:
        pass
'''

# A dunder in both classes is not mangled and is a legitimate override.
_DUNDER_OVERRIDE = '''
class Base_Cls(object):
    def __eq__(self, other: object) -> bool:
        return True


class Sub_Cls(Base_Cls):
    def __eq__(self, other: object) -> bool:
        return False
'''

# Same `__name` in two UNRELATED classes is fine - each is independently mangled.
_UNRELATED_SAME_NAME = '''
class A_Cls(object):
    def __helper(self) -> None:
        pass


class B_Cls(object):
    def __helper(self) -> None:
        pass
'''


def test_mangled_override_flagged():
    assert _mangling_flags(_MANGLED_OVERRIDE) != []


def test_single_underscore_hook_not_flagged():
    assert _mangling_flags(_SINGLE_UNDERSCORE_HOOK) == []


def test_dunder_override_not_flagged():
    assert _mangling_flags(_DUNDER_OVERRIDE) == []


def test_unrelated_same_name_not_flagged():
    assert _mangling_flags(_UNRELATED_SAME_NAME) == []
