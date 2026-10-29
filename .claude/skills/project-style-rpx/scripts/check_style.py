#!/usr/bin/env python3
"""Check Python files against the project style (project-style-rpx). Stdlib only.

Usage: python check_style.py [--root DIR] [<file_or_dir> ...]
Without a path, the project's check_roots are checked.
Exit code 0 if clean, 1 if any violation was found, 2 if a path could not be checked (it does
not exist, is not a .py file, or cannot be read) or the project configuration is missing or
invalid -- never "clean" for something not checked.
A directory is walked for *.py files, skipping hidden directories (.venv, .git, ...).

The project configuration is <root>/.claude/skills/project-style-rpx/references/check_style.json.
The root is --root, or else the nearest directory, from the working directory upwards, that holds
that file. Every field is required (assets/check_style_template.json):
  licence      the first line of the licence text every header carries ("MIT License")
  holder       the copyright holder every header names
  class_roots  the folders whose classes form the project's class map (exception and Qt ancestry)
  test_roots   the top-level folders whose files are pytest modules
  check_roots  the paths checked when none is given
  exclude      [{"path": ..., "reason": ...}]; the summary line names every exclusion applied,
               so nothing is silently out of scope
"""
from __future__ import annotations

import ast
import io
import json
import re
import sys
import tokenize
from pathlib import Path

PASCAL_SNAKE = re.compile(r"^_{0,2}[A-Z][A-Za-z0-9]*(_[A-Z0-9][A-Za-z0-9]*)*$")
SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*$")
CONST = re.compile(r"^CONST_[A-Z0-9_]+$")
MATH_SYMBOL = re.compile(r"^_{0,2}[A-Za-z][A-Za-z0-9]{0,3}(_[A-Za-z0-9]{1,4})*$")
MAX_LINE = 150   # the hard limit; aim for <=120 by hand (references/python.md, Line length)
# The marker a Qt-dispatched method carries on the line above its def (references/ui.md): its
# camelCase name is Qt's, and renaming it would silently stop Qt calling it.
QT_OVERRIDE_MARKER = "# << QT OVERRIDE >> #"
# Where a project keeps its configuration, relative to its root.
CONFIG_RELATIVE = Path(".claude", "skills", "project-style-rpx", "references", "check_style.json")
CONFIG_FIELDS = ("licence", "holder", "class_roots", "test_roots", "check_roots", "exclude")
# The project state, set by configure() from the project configuration. Until then (a function
# called on its own, as the tests do) nothing project-specific is checked: no holder, no class
# map, and a file is a pytest module by its own name only.
REPO_ROOT: Path | None = None
CONFIG_PATH: Path | None = None
LICENCE = "MIT License"
HOLDER: str | None = None
PROJECT_CLASS_FOLDERS: tuple[str, ...] = ()
TEST_FOLDERS: tuple[str, ...] = ()
CHECK_ROOTS: tuple[str, ...] = ()


class Report:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, path: Path, line: int, rule: str, message: str) -> None:
        self.items.append(f"{path}:{line}: [{rule}] {message}")


def _header_text(source: str) -> str | None:
    """Return the file's header text, from either accepted form, or None.

    The header may be a `\"\"\"` module docstring (the form rparak/RoLE uses) or a
    leading `#`-comment block (the form this repository uses, assets/header.txt).
    Both are accepted. A shebang line is ignored.
    """
    # Form A: a module docstring as the first statement.
    try:
        doc = ast.get_docstring(ast.parse(source))
    except SyntaxError:
        return None
    if doc:
        return doc
    # Form B: a leading run of comment lines before the first code/blank.
    lines: list[str] = []
    for raw in source.splitlines():
        stripped = raw.strip()
        if not stripped:
            if lines:                       # a blank ends the header block
                break
            continue                        # skip blanks before the block
        if stripped.startswith("#"):
            if stripped.startswith("#!") and not lines:
                continue                    # ignore a shebang line
            lines.append(stripped.lstrip("#").strip())
        else:
            break                           # first code line ends the search
    text = "\n".join(lines).strip()
    return text or None


def check_header(source: str, path: Path, report: Report) -> None:
    header = _header_text(source)
    if not header:
        report.add(path, 1, "header", "missing module header (\"\"\" docstring or #-comment block)")
        return
    if LICENCE not in header:
        report.add(path, 1, "header", f"module header is missing the {LICENCE} block")
    if HOLDER is not None and not re.search(r"Copyright \(c\) \d{4}(-\d{4})? " + re.escape(HOLDER) + r"\s*$",
                                             header, re.M):
        report.add(path, 1, "header", f"module header does not name the holder: 'Copyright (c) <year> {HOLDER}'")
    if "File Name:" not in header:
        report.add(path, 1, "header", "module header is missing the 'File Name:' line")
    else:
        declared = header.split("File Name:")[1].splitlines()[0].strip()
        if "<" in declared or "{{" in declared:   # a template field (assets/), not a file name
            return
        if path.name not in declared:
            report.add(path, 1, "header",
                       f"'File Name: {declared}' does not match the actual file {path.name}")


def _is_pytest_module(path: Path) -> bool:
    """A file pytest collects is a pytest module: `test_*.py` or `conftest.py` anywhere, or any
    file under a top-level test root of the project (TEST_FOLDERS, from the configuration).

    pytest's own calling convention -- test functions named `test_*`, fixtures
    injected as unannotated parameters -- collides with the RP function rules, so
    in these files the docstring and parameter-typing checks are skipped for every
    function, helpers included, and the naming check for pytest's own names only
    (`test_*`, `pytest_*`, fixtures; see SKILL.md: tests follow the pytest
    convention). Helper functions are checked for naming only.

    The directory test is taken on the path RELATIVE to the repository: a directory named
    `test` above the repository (or anywhere a file is checked from) must not relax the rules
    for every file beneath it.
    """
    if path.name == "conftest.py" or (path.name.startswith("test_") and path.suffix == ".py"):
        return True
    if REPO_ROOT is None:
        return False
    try:
        relative = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] in TEST_FOLDERS


def _decorator_name(decorator) -> str:
    """The trailing name of a decorator node (`pytest.fixture` -> 'fixture')."""
    if isinstance(decorator, ast.Call):
        decorator = decorator.func
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Name):
        return decorator.id
    return ""


def _is_pytest_dispatched(node) -> bool:
    """True for a name pytest calls by convention: `test_*`, a `pytest_*` hook, or
    a `@pytest.fixture`. Renaming any of these to Pascal_Snake_Case would break
    collection, so the naming rule is not applied to them inside a test module.
    """
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if node.name.startswith(("test_", "pytest_")):
        return True
    return any(_decorator_name(d) == "fixture" for d in node.decorator_list)


def _is_qt_override(node, lines: list[str]) -> bool:
    """True for a method whose line above (above its decorators, if any) is the QT OVERRIDE
    marker. Only a marked method is exempt from the naming rule, so the marker is what makes
    the exemption, and an unmarked camelCase method is still reported.
    """
    first = min([node.lineno] + [d.lineno for d in node.decorator_list])
    return first >= 2 and lines[first - 2].strip() == QT_OVERRIDE_MARKER


_CLASS_BASES: dict[str, list[str]] | None = None


def _base_names(node: ast.ClassDef) -> list[str]:
    """The trailing names of a class's bases (`package.Base_Cls` -> 'Base_Cls')."""
    return [base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "") for base in node.bases]


def _class_bases() -> dict[str, list[str]]:
    """Every class defined under the project's PROJECT_CLASS_FOLDERS (class_roots), mapped to
    its base names (built once), so an exception ancestry is followed through the project's own
    classes: a class whose base is a project class that subclasses ValueError is an exception too."""
    global _CLASS_BASES
    if _CLASS_BASES is None:
        _CLASS_BASES = {}
        for folder in PROJECT_CLASS_FOLDERS if REPO_ROOT is not None else ():
            for path in (REPO_ROOT / folder).rglob("*.py"):
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, SyntaxError):
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        _CLASS_BASES[node.name] = _base_names(node)
    return _CLASS_BASES


def _own_returns(node) -> list:
    """The return statements of a function itself, not of the functions and lambdas nested in it."""
    found, stack = [], list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        if isinstance(child, ast.Return):
            found.append(child)
        if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(child))
    return found


def _is_exception_name(name: str, local: dict[str, list[str]], seen: set[str] | None = None) -> bool:
    """True for an exception class name (trailing 'Error', 'Exception' or '_Error_Cls', e.g.
    ValueError or a project *_Error_Cls), or a class that descends from one through the classes
    of the same file (`local`) or of the project (class_roots)."""
    if name.endswith(("Error", "Exception", "_Error_Cls")):
        return True
    seen = seen or set()
    if name in seen:
        return False
    seen.add(name)
    bases = local.get(name, _class_bases().get(name, []))
    return any(_is_exception_name(base, local, seen) for base in bases)


def _is_exception_class(node, local: dict[str, list[str]] | None = None) -> bool:
    """True if the class subclasses an exception, directly or through project classes. Such a
    class carries no custom constructor and nothing a caller initializes, so the
    'Initialization of the Class:' section does not apply to it (e.g. Configuration_Error_Cls).
    """
    return any(_is_exception_name(name, local or {}) for name in _base_names(node))


def _is_qt_name(name: str, local: dict[str, list[str]], seen: set[str] | None = None) -> bool:
    """True for a Qt class name (Q followed by a capital: QWidget, QFrame, QObject ...), or a class
    that descends from one through the classes of the same file (`local`) or of the project
    (class_roots): Log_View_Cls -> Card_Cls -> QFrame."""
    if re.match(r"^Q[A-Z]", name):
        return True
    seen = seen or set()
    if name in seen:
        return False
    seen.add(name)
    bases = local.get(name, _class_bases().get(name, []))
    return any(_is_qt_name(base, local, seen) for base in bases)


def _is_qt_class(node, local: dict[str, list[str]] | None = None) -> bool:
    """True for a class descending from a Qt class, directly or through project classes. The UI
    builds its instances; no caller initializes them from a docstring, so the 'Initialization of
    the Class:' section does not apply to it (e.g. a Card_Cls(QFrame) widget)."""
    return any(_is_qt_name(name, local or {}) for name in _base_names(node))


def check_docstring_format(doc: str, node, path: Path, report: Report, kind: str) -> None:
    if "Description:" not in doc:
        report.add(path, node.lineno, "docstring",
                   f"{kind} '{node.name}' docstring has no 'Description:' section")
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [a.arg for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs
                if a.arg not in {"self", "cls"}]
        if args and "Args:" not in doc:
            report.add(path, node.lineno, "docstring",
                       f"function '{node.name}' takes arguments but has no 'Args:' section")
        # Accept the numbered '(1) ...' form and the grouped '(1 - N) a, b ...'
        # form for consecutive arguments of the same type (see
        # references/python.md, Docstrings); reject only truly unnumbered Args.
        if args and "Args:" in doc and not re.search(r"\(1\s*[-)]", doc):
            report.add(path, node.lineno, "docstring",
                       f"function '{node.name}' Args entries are not numbered "
                       "'(1) ...' or '(1 - N) ...'")
        returns_value = any(n.value is not None for n in _own_returns(node))
        if returns_value and "Returns:" not in doc:
            report.add(path, node.lineno, "docstring",
                       f"function '{node.name}' returns a value but has no 'Returns:' section")


VALID_ESCAPES = set("nrtvfab0\\'\"\n01234567xNuU")


def check_tokens(source: str, path: Path, report: Report) -> None:
    """Semicolon and escape-sequence checks that ignore string and comment content."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return
    semis: dict[int, int] = {}
    for tok in tokens:
        if tok.type == tokenize.OP and tok.string == ";":
            semis[tok.start[0]] = semis.get(tok.start[0], 0) + 1
        elif tok.type == tokenize.STRING:
            prefix = tok.string[:len(tok.string) - len(tok.string.lstrip("rbfuRBFU"))]
            if "r" in prefix.lower():
                continue
            body = tok.string[len(prefix):]
            j = 0
            while j < len(body) - 1:
                if body[j] == "\\":
                    if body[j + 1] not in VALID_ESCAPES:
                        report.add(path, tok.start[0], "escape",
                                   f"invalid escape sequence '\\{body[j + 1]}' - "
                                   "write '1)' or use a raw string")
                        break
                    j += 1
                j += 1
    for lineno, count in semis.items():
        if count > 1:
            report.add(path, lineno, "semicolon",
                       "at most two statements may share a line with ';'")


def check_mangled_overrides(tree: ast.Module, path: Path, report: Report) -> None:
    """Flag a `__name` method a subclass in the SAME file redefines.

    A `__name` method mangles to `_ClassName__name`, so a subclass that defines
    the same `__name` does not override the base's version: if the base calls
    `self.__name`, it keeps calling its own, and the subclass copy is dead. A
    member meant to be overridden must be single-underscore `_name`. This is the
    exact error the private-member rule prevents (see references/python.md, Names).

    Scope: only inheritance visible within one file. A base and subclass in
    different modules cannot be resolved by a per-file static check, so those are
    not caught here - the rule still holds, it just is not machine-verified.
    """
    classes = {node.name: node for node in ast.walk(tree)
               if isinstance(node, ast.ClassDef)}

    def mangled_methods(cls: ast.ClassDef) -> dict:
        # A `__name` that does not end in `__` mangles; a `__dunder__` does not.
        found = {}
        for item in cls.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name.startswith("__") and not item.name.endswith("__"):
                    found[item.name] = item.lineno
        return found

    def ancestor_mangled(cls: ast.ClassDef, seen: set) -> set:
        names: set = set()
        for base in cls.bases:
            if isinstance(base, ast.Name) and base.id in classes and base.id not in seen:
                seen.add(base.id)
                parent = classes[base.id]
                names |= set(mangled_methods(parent))
                names |= ancestor_mangled(parent, seen)
        return names

    for cls in classes.values():
        own = mangled_methods(cls)
        if not own:
            continue
        inherited = ancestor_mangled(cls, {cls.name})
        for name, lineno in sorted(own.items(), key=lambda kv: kv[1]):
            if name in inherited:
                report.add(path, lineno, "mangling",
                           f"'{cls.name}.{name}' redefines a name-mangled '{name}' "
                           "from a base class in this file; mangling makes it a "
                           "different attribute, so the override is dead. Rename the "
                           f"member meant to be overridden to '_{name.lstrip('_')}'")


def check_file(path: Path, report: Report) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        report.add(path, 0, "unreadable", f"the file could not be read as UTF-8 text ({error.__class__.__name__})")
        return

    pytest_module = _is_pytest_module(path)

    check_header(source, path, report)

    for i, line in enumerate(source.splitlines(), start=1):
        if len(line) > MAX_LINE:
            report.add(path, i, "length", f"line is {len(line)} chars (limit {MAX_LINE})")
        if re.search(r"==\s*(False|True)\b", line):
            report.add(path, i, "comparison", "use 'not x' / 'x' instead of '== False' / '== True'")

    check_tokens(source, path, report)

    if "import logging" in source:
        report.add(path, 1, "logging", "src/ modules report through return values, exceptions and injected "
                   "callbacks, scripts print('[INFO] ...') lines; the logging module is not used")
    if re.search(r"^\s*from\s+\.", source, re.M):
        report.add(path, 1, "imports", "relative imports are not used in this project")
    if re.search(r"^\s*from\s+typing\s+import", source, re.M) or \
       re.search(r"^\s*import\s+typing\s*$", source, re.M):
        report.add(path, 1, "imports", "use 'import typing as tp' and write hints as tp.List[...]")
    if re.search(r"from\s+__future__\s+import\s+annotations", source):
        report.add(path, 1, "imports", "'from __future__ import annotations' is not used here")

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        report.add(path, exc.lineno or 1, "syntax", str(exc))
        return

    lines = source.splitlines()
    local_bases = {node.name: _base_names(node) for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            is_dataclass = any(
                (isinstance(d, ast.Name) and d.id == "dataclass")
                or (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass")
                for d in node.decorator_list
            )
            if is_dataclass and not node.name.endswith("_Str"):
                report.add(path, node.lineno, "naming",
                           f"dataclass '{node.name}' must end with '_Str'")
            if not is_dataclass and not node.name.endswith(("_Cls", "_Str")):
                report.add(path, node.lineno, "naming",
                           f"class '{node.name}' must end with '_Cls'")
            if node.name.endswith(("_Cls", "_Str")) and not PASCAL_SNAKE.match(node.name[:-4]):
                report.add(path, node.lineno, "naming",
                           f"class '{node.name}' must be Pascal_Snake_Case before its suffix")
            if _is_exception_class(node, local_bases) and not node.name.endswith("_Error_Cls"):
                report.add(path, node.lineno, "naming",
                           f"exception class '{node.name}' must end with '_Error_Cls'")
            doc = ast.get_docstring(node)
            if not doc:
                report.add(path, node.lineno, "docstring",
                           f"class '{node.name}' has no docstring")
            elif not pytest_module:
                # Test doubles in a test module follow the lighter test convention;
                # their docstring completeness is not checked (only its presence,
                # above). Everywhere else the full class docstring is required.
                check_docstring_format(doc, node, path, report, "class")
                if (node.name.endswith("_Cls") and not _is_exception_class(node, local_bases)
                        and not _is_qt_class(node, local_bases)
                        and "Initialization of the Class:" not in doc):
                    report.add(path, node.lineno, "docstring",
                               f"class '{node.name}' docstring has no "
                               "'Initialization of the Class:' section")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "main":
                continue
            # In a test module the pytest convention governs: names pytest
            # dispatches (test_*, pytest_* hooks, fixtures) are exempt from the
            # naming rule, and the docstring-completeness and parameter/return
            # typing rules are relaxed for test functions and their terse support
            # helpers. Every structural rule (header, line length, semicolons,
            # mutable defaults, mangling, imports, class naming) still applies, so a
            # future flag on a test file means something.
            if (not node.name.startswith("__") and not (pytest_module and _is_pytest_dispatched(node))
                    and not _is_qt_override(node, lines)):
                if not PASCAL_SNAKE.match(node.name):
                    report.add(path, node.lineno, "naming",
                               f"function '{node.name}' should be Pascal_Snake_Case")
            doc = ast.get_docstring(node)
            if node.name != "__init__" and not pytest_module:
                if not doc:
                    report.add(path, node.lineno, "docstring",
                               f"function '{node.name}' has no docstring")
                else:
                    check_docstring_format(doc, node, path, report, "function")
            all_args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            for arg in all_args:
                if arg.arg in {"self", "cls"}:
                    continue
                if arg.annotation is None and not pytest_module:
                    report.add(path, node.lineno, "typing",
                               f"parameter '{arg.arg}' of '{node.name}' is not annotated")
                if arg.arg.endswith("_Str") and PASCAL_SNAKE.match(arg.arg):
                    continue   # parameter named after the structure it carries
                if not (SNAKE.match(arg.arg) or MATH_SYMBOL.match(arg.arg)):
                    report.add(path, node.lineno, "naming",
                               f"parameter '{arg.arg}' should be snake_case or a math symbol")
            if node.returns is None and not pytest_module:
                report.add(path, node.lineno, "typing",
                           f"function '{node.name}' has no return annotation")
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)) or (
                    isinstance(default, ast.BinOp) and isinstance(default.left, ast.List)
                ):
                    report.add(path, node.lineno, "mutable-default",
                               f"'{node.name}' has a mutable default argument - use None instead")

    check_mangled_overrides(tree, path, report)

    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target]
        for target in targets:
            if target.id.startswith("_") or CONST.match(target.id):
                continue
            if target.id.endswith("_Str") and PASCAL_SNAKE.match(target.id):
                continue   # preset dataclass instance, e.g. Default_Limits_Str
            report.add(path, node.lineno, "naming",
                       f"module-level '{target.id}' should be CONST_* "
                       "or a Pascal_Snake_Case *_Str preset")


class ConfigError(Exception):
    """The project configuration is missing or invalid; the message says what to do."""


def find_root(start: Path) -> Path | None:
    """The nearest directory, from `start` upwards, that holds the project configuration."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / CONFIG_RELATIVE).is_file():
            return directory
    return None


def load_config(config_path: Path) -> dict:
    """Read and validate the project configuration. Every problem is collected, then refused at
    once: a missing or wrongly typed field is never defaulted, so a field the project forgot is
    named instead of silently replaced."""
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError(f"{config_path} cannot be read as JSON ({error}). Fix it from "
                          "assets/check_style_template.json of the project-style-rpx skill.") from error
    if not isinstance(config, dict):
        raise ConfigError(f"{config_path} must hold a JSON object.")
    problems = [f"'{name}' is missing" for name in CONFIG_FIELDS if name not in config]
    for name in ("licence", "holder"):
        if name in config and not (isinstance(config[name], str) and config[name].strip()):
            problems.append(f"'{name}' must be a non-empty string")
    for name in ("class_roots", "test_roots", "check_roots"):
        if name in config and not (isinstance(config[name], list) and config[name]
                                   and all(isinstance(item, str) and item.strip() for item in config[name])):
            problems.append(f"'{name}' must be a non-empty list of folder names")
    if "exclude" in config and not isinstance(config["exclude"], list):
        problems.append("'exclude' must be a list (empty when nothing is excluded)")
    for name in sorted(set(config) - set(CONFIG_FIELDS)):
        problems.append(f"'{name}' is not a field (misspelt?)")
    if problems:
        raise ConfigError(f"{config_path}: " + "; ".join(problems) + ". Every field is required "
                          "(see assets/check_style_template.json of the project-style-rpx skill).")
    return config


def configure(root: Path, config_path: Path | None = None) -> None:
    """Set the project state from the configuration of the project at `root`."""
    global REPO_ROOT, CONFIG_PATH, LICENCE, HOLDER, PROJECT_CLASS_FOLDERS, TEST_FOLDERS, CHECK_ROOTS, _CLASS_BASES
    config_path = root / CONFIG_RELATIVE if config_path is None else config_path
    if not config_path.is_file():
        raise ConfigError(f"No project configuration at {config_path}. Run the project-style-rpx skill in "
                          "bootstrap mode to create it, or pass --root with the project's root.")
    config = load_config(config_path)
    REPO_ROOT, CONFIG_PATH = root.resolve(), config_path
    LICENCE, HOLDER = config["licence"].strip(), config["holder"].strip()
    PROJECT_CLASS_FOLDERS = tuple(config["class_roots"])
    TEST_FOLDERS = tuple(config["test_roots"])
    CHECK_ROOTS = tuple(config["check_roots"])
    _CLASS_BASES = None


def load_exclusions(config_path: Path | None = None) -> list[tuple[Path, str]]:
    """The excluded paths (absolute, under REPO_ROOT) and their reasons, from the configuration's
    `exclude` list (CONFIG_PATH, read at call time). An entry without a reason is refused: an
    exclusion must say why, or it is a silent scope cut."""
    config_path = CONFIG_PATH if config_path is None else config_path
    if config_path is None or REPO_ROOT is None:
        return []
    entries = json.loads(config_path.read_text(encoding="utf-8")).get("exclude", [])
    exclusions = []
    for entry in entries:
        if not str(entry.get("reason", "")).strip():
            raise SystemExit(f"{config_path.name}: the exclusion of '{entry.get('path')}' has no reason")
        exclusions.append(((REPO_ROOT / entry["path"]).resolve(), entry["reason"].strip()))
    return exclusions


def _python_files(directory: Path) -> list[Path]:
    """Every *.py file under a directory, skipping hidden directories below it (.venv, .git,
    .pytest_cache): a walk of the repository must not descend into an installed environment."""
    return sorted(f for f in directory.rglob("*.py")
                  if not any(part.startswith(".") for part in f.relative_to(directory).parts[:-1]))


def main() -> int:
    arguments = sys.argv[1:]
    if any(a in ("-h", "--help") for a in arguments):
        print(__doc__)
        return 0
    root = None
    if "--root" in arguments:
        index = arguments.index("--root")
        if index + 1 >= len(arguments):
            print("--root needs a directory: check_style.py --root DIR [paths]")
            return 2
        root = Path(arguments[index + 1])
        arguments = arguments[:index] + arguments[index + 2:]
    if root is None:
        root = find_root(Path.cwd())
        if root is None:
            print(f"No project configuration ({CONFIG_RELATIVE}) in {Path.cwd()} or any directory above it. "
                  "Run the project-style-rpx skill in bootstrap mode to create it, or pass --root.")
            return 2
    try:
        configure(root)
    except ConfigError as error:
        print(error)
        return 2
    if not arguments:
        arguments = [str(REPO_ROOT / name) for name in CHECK_ROOTS]
    files: list[Path] = []
    refused: list[str] = []
    for p in (Path(a) for a in arguments):
        if p.is_dir():
            files.extend(_python_files(p))
        elif not p.exists():
            refused.append(f"{p}: no such file or directory -- nothing was checked for it")
        elif p.suffix != ".py":
            refused.append(f"{p}: not a .py file -- this checker reads Python only")
        else:
            files.append(p)
    for message in refused:
        print(message)

    exclusions = load_exclusions()
    excluded: dict[Path, int] = {}
    checked: list[Path] = []
    for f in files:
        root = next((root for root, _reason in exclusions if f.resolve().is_relative_to(root)), None)
        if root is None:
            checked.append(f)
        else:
            excluded[root] = excluded.get(root, 0) + 1

    report = Report()
    for f in checked:
        check_file(f, report)

    for item in report.items:
        print(item)
    refusals = f", {len(refused)} path(s) refused" if refused else ""
    print(f"\n{len(checked)} file(s) checked, {len(report.items)} issue(s) found{refusals}.")
    for root, reason in exclusions:
        if root in excluded:
            print(f"Excluded {excluded[root]} file(s) in {root.relative_to(REPO_ROOT)} (check_style.json): {reason}")
    if refused:
        return 2
    return 1 if report.items else 0


if __name__ == "__main__":
    raise SystemExit(main())
