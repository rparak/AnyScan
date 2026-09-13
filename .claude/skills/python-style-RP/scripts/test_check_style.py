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


def _file_flags(source: str, relpath: str, tmp_path) -> list:
    """Run check_file on `source` written at `relpath` under tmp_path, so the
    pytest-module detection (which reads the path) sees a realistic location."""
    target = tmp_path / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    report = check_style.Report()
    check_style.check_file(target, report)
    return report.items


# A pytest test function: name is test_*, the fixture param is unannotated, and the
# docstring documents no Args. All three are the pytest convention, not RP slips.
_PYTEST_TEST = '''
def test_something(tmp_path) -> None:
    """
    Description:
        A test.
    """
    assert tmp_path
'''

# A pytest hook: pytest calls it by this exact name.
_PYTEST_HOOK = '''
def pytest_configure(config) -> None:
    """
    Description:
        A hook.
    """
    return None
'''


def test_pytest_test_function_clean_under_test_dir(tmp_path):
    flags = _file_flags(_PYTEST_TEST, "test/Vision/test_x.py", tmp_path)
    convention = [f for f in flags if "[naming]" in f or "[typing]" in f or "[docstring]" in f]
    assert convention == []


def test_pytest_hook_name_clean_under_test_dir(tmp_path):
    flags = _file_flags(_PYTEST_HOOK, "test/conftest.py", tmp_path)
    assert [f for f in flags if "[naming]" in f] == []


def test_same_function_flagged_outside_test_dir(tmp_path):
    # The identical source under src/ is NOT a test module, so the pytest
    # convention does not apply and the flags fire — the relaxation is path-scoped.
    flags = _file_flags(_PYTEST_TEST, "src/Vision/mod.py", tmp_path)
    assert [f for f in flags if "[naming]" in f] != []


# An exception class has no constructor to initialize, so it needs no
# 'Initialization of the Class:' section.
_EXCEPTION_CLASS = '''
class Thing_Error_Cls(RuntimeError):
    """
    Description:
        An error.
    """
'''

# A behaviour class DOES need the Initialization section.
_BEHAVIOUR_CLASS = '''
class Thing_Cls(object):
    """
    Description:
        A thing.
    """
'''


def test_exception_class_needs_no_initialization_section(tmp_path):
    flags = _file_flags(_EXCEPTION_CLASS, "src/Vision/err.py", tmp_path)
    assert [f for f in flags if "Initialization of the Class:" in f] == []


def test_behaviour_class_still_needs_initialization_section(tmp_path):
    flags = _file_flags(_BEHAVIOUR_CLASS, "src/Vision/thing.py", tmp_path)
    assert [f for f in flags if "Initialization of the Class:" in f] != []


# A structural rule (mutable default) must still fire inside a test module: the
# relaxation is scoped to the pytest naming/docstring/typing convention only.
_TEST_WITH_MUTABLE_DEFAULT = '''
def test_helper_reuse(values=[]) -> None:
    """
    Description:
        A test whose helper takes a mutable default.
    """
    assert values == []
'''


def test_structural_rule_still_fires_in_test_dir(tmp_path):
    flags = _file_flags(_TEST_WITH_MUTABLE_DEFAULT, "test/test_y.py", tmp_path)
    assert [f for f in flags if "[mutable-default]" in f] != []


def test_mangled_override_flagged():
    assert _mangling_flags(_MANGLED_OVERRIDE) != []


def test_single_underscore_hook_not_flagged():
    assert _mangling_flags(_SINGLE_UNDERSCORE_HOOK) == []


def test_dunder_override_not_flagged():
    assert _mangling_flags(_DUNDER_OVERRIDE) == []


def test_unrelated_same_name_not_flagged():
    assert _mangling_flags(_UNRELATED_SAME_NAME) == []
