"""Regression tests for check_style.py: Args numbering, mangling, the Qt-override and Qt-class exemptions,
nested returns and the reasoned exclusions.

Run with:  pytest .claude/skills/project-style-rpx/scripts/test_check_style.py
(stdlib + pytest only; not part of the app's test/ suite).

Both the numbered '(1) ...' form and the grouped '(1 - N) a, b ...' form for
consecutive arguments of the same type are valid (see
references/python.md, Docstrings). This guards against the checker regressing to
accepting only the literal '(1)'.

The mangling tests guard the private-member rule (see references/python.md, Names): a
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


# A narrower error of a project's own, subclassing its *_Error_Cls so every handler of that error catches it.
_PROJECT_EXCEPTION_SUBCLASS = '''
class Thing_Busy_Error_Cls(Thing_Error_Cls):
    """
    Description:
        A narrower error.
    """
'''


def test_subclass_of_a_project_error_needs_no_initialization_section(tmp_path):
    flags = _file_flags(_PROJECT_EXCEPTION_SUBCLASS, "src/Vision/err.py", tmp_path)
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


# A Qt-dispatched method: camelCase because Qt calls it by that name. Marked, it is exempt from
# the naming rule; unmarked, it is reported, so the marker is what grants the exemption.
_QT_OVERRIDE = '''
class Panel_Cls(QWidget):
    """
    Description:
        A panel.
    """

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Paint it.

        Args:
            (1) event [QPaintEvent(object)]: The event.
        """

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Description:
            Unmarked.

        Args:
            (1) event [QResizeEvent(object)]: The event.
        """
'''


def test_only_a_marked_qt_override_is_exempt_from_naming(tmp_path):
    naming = [item for item in _file_flags(_QT_OVERRIDE, "src/UI/panel.py", tmp_path) if "[naming]" in item]
    assert len(naming) == 1 and "'resizeEvent'" in naming[0]


def test_a_qt_class_needs_no_initialization_section_directly_or_through_project_classes(tmp_path):
    # Directly (QWidget), and through the project's own Card_Cls (-> QFrame), which the checker
    # follows via the repository's class map; a plain class still needs the section.
    source = _QT_OVERRIDE.replace("    def resizeEvent", "    # << QT OVERRIDE >> #\n    def resizeEvent")
    source += '''

class Card_Panel_Cls(Card_Cls):
    """
    Description:
        A card.
    """


class Plain_Cls(object):
    """
    Description:
        Not a widget.
    """
'''
    flags = [item for item in _file_flags(source, "src/UI/panel.py", tmp_path) if "Initialization" in item]
    assert len(flags) == 1 and "'Plain_Cls'" in flags[0]


def test_a_nested_helpers_return_is_not_the_outer_functions(tmp_path):
    source = '''
def Outer(x: float) -> None:
    """
    Description:
        Returns nothing itself; its helper does.

    Args:
        (1) x [float]: A value.
    """

    def _Inner(y: float) -> float:
        """
        Description:
            The helper.

        Args:
            (1) y [float]: A value.

        Returns:
            (1) parameter [float]: The value.
        """

        return y
'''
    assert not [item for item in _file_flags(source, "src/x.py", tmp_path) if "Returns:" in item]


def test_an_exclusion_must_give_its_reason(tmp_path):
    config = tmp_path / "check_style.json"
    config.write_text('{"exclude": [{"path": "src/Transformation", "reason": "inherited"}]}', encoding="utf-8")
    ((root, reason),) = check_style.load_exclusions(config)
    assert root == (check_style.REPO_ROOT / "src/Transformation").resolve() and reason == "inherited"
    config.write_text('{"exclude": [{"path": "src/Transformation", "reason": " "}]}', encoding="utf-8")
    try:
        check_style.load_exclusions(config)
    except SystemExit as error:
        assert "has no reason" in str(error)
    else:
        raise AssertionError("an exclusion without a reason was accepted")


def test_the_summary_names_every_exclusion(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["check_style.py", str(check_style.REPO_ROOT / "src" / "Transformation")])
    assert check_style.main() == 0
    out = capsys.readouterr().out
    assert "0 file(s) checked" in out and "Excluded" in out and "src/Transformation (check_style.json)" in out


def test_a_missing_path_is_refused_not_reported_clean(capsys, monkeypatch, tmp_path):
    missing = tmp_path / "no_such_module.py"
    monkeypatch.setattr("sys.argv", ["check_style.py", str(missing)])
    assert check_style.main() == 2
    out = capsys.readouterr().out
    assert "no such file or directory" in out and "1 path(s) refused" in out


def test_a_non_python_file_is_refused_not_parsed(capsys, monkeypatch, tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text("# Notes \u2014 not Python\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["check_style.py", str(notes)])
    assert check_style.main() == 2
    out = capsys.readouterr().out
    assert "not a .py file" in out and "[syntax]" not in out


def test_help_prints_the_usage_and_checks_nothing(capsys, monkeypatch):
    monkeypatch.setattr("sys.argv", ["check_style.py", "--help"])
    assert check_style.main() == 0
    out = capsys.readouterr().out
    assert out.lstrip().startswith("Check Python files") and "file(s) checked" not in out


def test_an_unreadable_file_is_reported_not_skipped(tmp_path):
    target = tmp_path / "src" / "broken.py"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"\xff\xfe not utf-8")
    report = check_style.Report()
    check_style.check_file(target, report)
    assert [item for item in report.items if "[unreadable]" in item]


def test_a_directory_walk_skips_hidden_directories(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / "pkg" / ".venv" / "lib" / "site.py").write_text("", encoding="utf-8")
    assert check_style._python_files(tmp_path) == [tmp_path / "pkg" / "mod.py"]


def test_a_test_directory_above_the_file_does_not_relax_the_rules(tmp_path):
    # A directory named 'test' ABOVE the checked file (here, outside the repository) must not make
    # it a pytest module: only pytest's own file names, or the repository's top-level test/, do.
    flags = _file_flags(_PYTEST_TEST, "test/checkout/src/Vision/mod.py", tmp_path)
    assert [f for f in flags if "[naming]" in f] != []
