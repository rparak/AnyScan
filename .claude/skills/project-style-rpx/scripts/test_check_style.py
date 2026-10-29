"""Regression tests for check_style.py: Args numbering, mangling, the exception-class exemption
(direct, through a class of the same file and through the project class map), the two Qt
exemptions (a marked Qt override's name, a Qt class's Initialization section), nested returns,
the reasoned exclusions, and the project configuration (root discovery, required fields, holder,
test roots, check roots).

Run with:  <python with pytest> -m pytest <this skill>/scripts/test_check_style.py
(stdlib + pytest only; not part of any project's test suite). Every project is a temporary
directory: no test depends on the repository it is run from.

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
import json
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("check_style", _HERE / "check_style.py")
check_style = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_style)

_STATE = ("REPO_ROOT", "CONFIG_PATH", "LICENCE", "HOLDER", "PROJECT_CLASS_FOLDERS", "TEST_FOLDERS",
          "CHECK_ROOTS", "_CLASS_BASES")
_CONFIG = {"licence": "MIT License", "holder": "Example Holder", "class_roots": ["src"],
           "test_roots": ["test"], "check_roots": ["src", "test"], "exclude": []}
_HEADER = "# MIT License\n# Copyright (c) 2026 {holder}\n# File Name: ../{name}\n"


@pytest.fixture(autouse=True)
def _restore_project_state(monkeypatch):
    # configure() sets module globals; every test starts from, and returns to, the unconfigured state.
    for name in _STATE:
        monkeypatch.setattr(check_style, name, getattr(check_style, name))


def _project(root: Path, **fields) -> Path:
    """Write a project configuration under `root` (the fields of _CONFIG, overridden by `fields`)."""
    config = root / check_style.CONFIG_RELATIVE
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({**_CONFIG, **fields}), encoding="utf-8")
    return config


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
    flags = _file_flags(_PYTEST_TEST, "test/Reader/test_x.py", tmp_path)
    convention = [f for f in flags if "[naming]" in f or "[typing]" in f or "[docstring]" in f]
    assert convention == []


def test_pytest_hook_name_clean_under_test_dir(tmp_path):
    flags = _file_flags(_PYTEST_HOOK, "test/conftest.py", tmp_path)
    assert [f for f in flags if "[naming]" in f] == []


def test_same_function_flagged_outside_test_dir(tmp_path):
    # The identical source under src/ is NOT a test module, so the pytest
    # convention does not apply and the flags fire — the relaxation is path-scoped.
    flags = _file_flags(_PYTEST_TEST, "src/Reader/mod.py", tmp_path)
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


def test_a_class_name_must_be_pascal_snake_case_before_its_suffix(tmp_path):
    bad = _BEHAVIOUR_CLASS.replace("Thing_Cls", "bad_thing_Cls")
    flags = _file_flags(bad, "src/Reader/mod.py", tmp_path / "bad")
    assert [f for f in flags if "Pascal_Snake_Case before its suffix" in f] != []
    flags = _file_flags(_BEHAVIOUR_CLASS, "src/Reader/mod.py", tmp_path / "good")
    assert [f for f in flags if "Pascal_Snake_Case before its suffix" in f] == []


def test_an_exception_class_must_end_with_error_cls(tmp_path):
    # Directly from a builtin exception, and through a project error of the same file.
    for source in ("class Thing_Cls(ValueError):\n    pass\n",
                   _EXCEPTION_CLASS + "\nclass Narrow_Cls(Thing_Error_Cls):\n    pass\n"):
        flags = _file_flags(source, "src/Reader/err.py", tmp_path)
        assert [f for f in flags if "must end with '_Error_Cls'" in f] != [], source
    flags = _file_flags(_EXCEPTION_CLASS, "src/Reader/err.py", tmp_path)
    assert [f for f in flags if "must end with '_Error_Cls'" in f] == []


def test_exception_class_needs_no_initialization_section(tmp_path):
    flags = _file_flags(_EXCEPTION_CLASS, "src/Reader/err.py", tmp_path)
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
    flags = _file_flags(_PROJECT_EXCEPTION_SUBCLASS, "src/Reader/err.py", tmp_path)
    assert [f for f in flags if "Initialization of the Class:" in f] == []


# A class whose base is a class of the same file that subclasses an exception: it is an exception
# too, though neither its own name nor its base's ends in 'Error'.
_EXCEPTION_THROUGH_A_LOCAL_CLASS = '''
class Fault_Base_Cls(ValueError):
    """
    Description:
        A base fault.
    """


class Fault_Detail_Cls(Fault_Base_Cls):
    """
    Description:
        A narrower fault.
    """


class Plain_Cls(object):
    """
    Description:
        Not an exception.
    """
'''


def test_an_exception_through_a_class_of_the_same_file_needs_no_initialization_section(tmp_path):
    flags = [f for f in _file_flags(_EXCEPTION_THROUGH_A_LOCAL_CLASS, "src/Reader/err.py", tmp_path)
             if "Initialization of the Class:" in f]
    assert len(flags) == 1 and "'Plain_Cls'" in flags[0]


def test_an_exception_through_a_project_class_needs_no_initialization_section(tmp_path, monkeypatch):
    # The base lives in another module of the project (here src/Geometry/Core.py of a repository
    # in tmp_path), found through the class map; with a non-exception base the section is required.
    (tmp_path / "src" / "Geometry").mkdir(parents=True)
    base_module = tmp_path / "src" / "Geometry" / "Core.py"
    source = '''
class Fault_Detail_Cls(Fault_Base_Cls):
    """
    Description:
        A narrower fault.
    """
'''
    monkeypatch.setattr(check_style, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_style, "PROJECT_CLASS_FOLDERS", ("src",))
    base_module.write_text("class Fault_Base_Cls(ValueError):\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(check_style, "_CLASS_BASES", None)
    flags = [f for f in _file_flags(source, "src/Writer/err.py", tmp_path) if "Initialization of the Class:" in f]
    assert flags == []
    base_module.write_text("class Fault_Base_Cls(object):\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(check_style, "_CLASS_BASES", None)
    flags = [f for f in _file_flags(source, "src/Writer/err.py", tmp_path) if "Initialization of the Class:" in f]
    assert len(flags) == 1
    monkeypatch.setattr(check_style, "_CLASS_BASES", None)


def test_behaviour_class_still_needs_initialization_section(tmp_path):
    flags = _file_flags(_BEHAVIOUR_CLASS, "src/Reader/thing.py", tmp_path)
    assert [f for f in flags if "Initialization of the Class:" in f] != []



# A Qt override keeps Qt's camelCase name; only the marker on the line above exempts it.
_QT_OVERRIDES = '''
class View_Cls(QWidget):
    """
    Description:
        A view.
    """

    # << QT OVERRIDE >> #
    def paintEvent(self, event: object) -> None:
        """
        Description:
            Paint.

        Args:
            (1) event [QPaintEvent]: The event.
        """

    # << QT OVERRIDE >> #
    @staticmethod
    def sizeHint() -> None:
        """
        Description:
            A decorated override; the marker sits above the decorator.
        """

    def mousePressEvent(self, event: object) -> None:
        """
        Description:
            Not marked.

        Args:
            (1) event [QMouseEvent]: The event.
        """
'''


def test_only_a_marked_qt_override_keeps_its_camelcase_name(tmp_path):
    flags = [f for f in _file_flags(_QT_OVERRIDES, "src/UI/view.py", tmp_path) if "[naming]" in f]
    assert len(flags) == 1 and "'mousePressEvent'" in flags[0]


# Qt classes: directly from a Qt base, through a class of the same file, and a plain class beside them.
_QT_CLASSES = '''
class Card_Cls(QtWidgets.QFrame):
    """
    Description:
        A card.
    """


class Log_View_Cls(Card_Cls):
    """
    Description:
        A card of the same file.
    """


class Plain_Cls(object):
    """
    Description:
        Not a widget.
    """
'''


def test_a_qt_class_needs_no_initialization_section(tmp_path):
    flags = [f for f in _file_flags(_QT_CLASSES, "src/UI/widgets.py", tmp_path) if "Initialization of the Class:" in f]
    assert len(flags) == 1 and "'Plain_Cls'" in flags[0]


def test_a_qt_class_through_a_project_class_needs_no_initialization_section(tmp_path, monkeypatch):
    # The base lives in another module of the project, found through the class map; with a
    # non-Qt base the section is required.
    (tmp_path / "src" / "UI").mkdir(parents=True)
    base_module = tmp_path / "src" / "UI" / "Widgets.py"
    source = '''
class Log_View_Cls(Card_Cls):
    """
    Description:
        A view.
    """
'''
    monkeypatch.setattr(check_style, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_style, "PROJECT_CLASS_FOLDERS", ("src",))
    base_module.write_text("class Card_Cls(QFrame):\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(check_style, "_CLASS_BASES", None)
    flags = [f for f in _file_flags(source, "src/UI/Views/log.py", tmp_path) if "Initialization of the Class:" in f]
    assert flags == []
    base_module.write_text("class Card_Cls(object):\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(check_style, "_CLASS_BASES", None)
    flags = [f for f in _file_flags(source, "src/UI/Views/log.py", tmp_path) if "Initialization of the Class:" in f]
    assert len(flags) == 1
    monkeypatch.setattr(check_style, "_CLASS_BASES", None)

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


def test_an_exclusion_must_give_its_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(check_style, "REPO_ROOT", tmp_path)
    config = tmp_path / "check_style.json"
    config.write_text('{"exclude": [{"path": "src/Generated", "reason": "generated"}]}', encoding="utf-8")
    ((root, reason),) = check_style.load_exclusions(config)
    assert root == (check_style.REPO_ROOT / "src/Generated").resolve() and reason == "generated"
    config.write_text('{"exclude": [{"path": "src/Generated", "reason": " "}]}', encoding="utf-8")
    try:
        check_style.load_exclusions(config)
    except SystemExit as error:
        assert "has no reason" in str(error)
    else:
        raise AssertionError("an exclusion without a reason was accepted")


def test_the_summary_names_every_exclusion(capsys, monkeypatch, tmp_path):
    # A repository of its own (tmp_path) with one reasoned exclusion: the excluded file is not
    # checked, and the summary line names the folder, the file count and the reason.
    (tmp_path / "src" / "Generated").mkdir(parents=True)
    (tmp_path / "src" / "Generated" / "table.py").write_text("x = 1\n", encoding="utf-8")
    _project(tmp_path, exclude=[{"path": "src/Generated", "reason": "generated tables"}])
    monkeypatch.setattr("sys.argv", ["check_style.py", "--root", str(tmp_path), str(tmp_path / "src" / "Generated")])
    assert check_style.main() == 0
    out = capsys.readouterr().out
    assert "0 file(s) checked" in out
    assert "Excluded 1 file(s) in src/Generated (check_style.json): generated tables" in out


def test_a_missing_path_is_refused_not_reported_clean(capsys, monkeypatch, tmp_path):
    _project(tmp_path)
    missing = tmp_path / "no_such_module.py"
    monkeypatch.setattr("sys.argv", ["check_style.py", "--root", str(tmp_path), str(missing)])
    assert check_style.main() == 2
    out = capsys.readouterr().out
    assert "no such file or directory" in out and "1 path(s) refused" in out


def test_a_non_python_file_is_refused_not_parsed(capsys, monkeypatch, tmp_path):
    _project(tmp_path)
    notes = tmp_path / "notes.md"
    notes.write_text("# Notes \u2014 not Python\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["check_style.py", "--root", str(tmp_path), str(notes)])
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
    flags = _file_flags(_PYTEST_TEST, "test/checkout/src/Reader/mod.py", tmp_path)
    assert [f for f in flags if "[naming]" in f] != []


def test_the_root_is_found_from_a_subdirectory(capsys, monkeypatch, tmp_path):
    # Run from deep inside the project without --root: the nearest directory holding the
    # configuration is the root, so the project's test roots apply to its test/ folder.
    _project(tmp_path)
    (tmp_path / "test" / "Domain").mkdir(parents=True)
    helper = tmp_path / "test" / "Domain" / "helpers.py"
    helper.write_text(_HEADER.format(holder="Example Holder", name="test/Domain/helpers.py")
                      + "\ndef helper(x):\n    return x\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path / "test" / "Domain")
    monkeypatch.setattr("sys.argv", ["check_style.py", "helpers.py"])
    check_style.main()
    out = capsys.readouterr().out
    assert check_style.REPO_ROOT == tmp_path.resolve()
    # Under a test root: only naming applies ('helper' is not Pascal_Snake_Case); no docstring or typing.
    assert "[naming]" in out and "[docstring]" not in out and "[typing]" not in out


def test_no_configuration_is_refused_not_reported_clean(capsys, monkeypatch, tmp_path):
    (tmp_path / "mod.py").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["check_style.py", "mod.py"])
    assert check_style.main() == 2
    out = capsys.readouterr().out
    assert "No project configuration" in out and "bootstrap mode" in out and "checked" not in out


def test_every_missing_or_unknown_field_is_named(tmp_path):
    config = tmp_path / "check_style.json"
    config.write_text(json.dumps({"holdr": "Example Holder", "class_roots": []}), encoding="utf-8")
    with pytest.raises(check_style.ConfigError) as error:
        check_style.load_config(config)
    message = str(error.value)
    for name in ("licence", "holder", "test_roots", "check_roots", "exclude"):
        assert f"'{name}' is missing" in message, name
    assert "'class_roots' must be a non-empty list" in message
    assert "'holdr' is not a field" in message


def test_a_header_naming_another_holder_is_flagged(tmp_path):
    _project(tmp_path)
    check_style.configure(tmp_path)
    for holder, flagged in (("Example Holder", False), ("Someone Else", True), ("Example Holder Ltd", True)):
        target = tmp_path / "src" / "mod.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_HEADER.format(holder=holder, name="src/mod.py"), encoding="utf-8")
        report = check_style.Report()
        check_style.check_file(target, report)
        assert bool([item for item in report.items if "does not name the holder" in item]) == flagged, holder


def test_the_test_roots_come_from_the_configuration(tmp_path):
    # A file under spec/ is a pytest module only when the project names spec/ as a test root.
    target = tmp_path / "spec" / "helpers.py"
    target.parent.mkdir(parents=True)
    target.write_text("", encoding="utf-8")
    _project(tmp_path, test_roots=["test"])
    check_style.configure(tmp_path)
    assert not check_style._is_pytest_module(target)
    _project(tmp_path, test_roots=["spec"])
    check_style.configure(tmp_path)
    assert check_style._is_pytest_module(target)


def test_without_a_path_the_check_roots_are_checked(capsys, monkeypatch, tmp_path):
    _project(tmp_path, check_roots=["src"])
    for folder in ("src", "other"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "mod.py").write_text(_HEADER.format(holder="Example Holder", name=f"{folder}/mod.py"),
                                                  encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["check_style.py", "--root", str(tmp_path)])
    assert check_style.main() == 0
    assert "1 file(s) checked, 0 issue(s) found." in capsys.readouterr().out


def test_a_template_file_name_field_is_not_compared(tmp_path):
    # The templates in assets/ name their file with a {{...}} field (or an older <...> one); the
    # checker skips the comparison for it, and still compares a real name.
    for declared, flagged in (("../{{Domain}}/{{Module}}.py", False), ("../<Domain>/<Module>.py", False),
                              ("../Reader/Other.py", True)):
        flags = _file_flags("# MIT License\n# File Name: %s\n" % declared, "src/Reader/Core.py", tmp_path)
        assert bool([f for f in flags if "does not match the actual file" in f]) == flagged, declared
