#!/usr/bin/env python3
"""Check Python files against the RP house style. Stdlib only.

Usage: python check_style.py <file_or_dir> [...]
Exit code 0 if clean, 1 if any violation was found.
"""
from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from pathlib import Path

PASCAL_SNAKE = re.compile(r"^_{0,2}[A-Z][A-Za-z0-9]*(_[A-Z0-9][A-Za-z0-9]*)*$")
SNAKE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*$")
CONST = re.compile(r"^CONST_[A-Z0-9_]+$")
MATH_SYMBOL = re.compile(r"^_{0,2}[A-Za-z][A-Za-z0-9]{0,3}(_[A-Za-z0-9]{1,4})*$")
MAX_LINE = 150   # p95 of the source is 122, p99 is 167; aim for <=120 by hand


class Report:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, path: Path, line: int, rule: str, message: str) -> None:
        self.items.append(f"{path}:{line}: [{rule}] {message}")


def check_header(source: str, path: Path, report: Report) -> None:
    tree_doc = None
    try:
        tree_doc = ast.get_docstring(ast.parse(source))
    except SyntaxError:
        return
    if not tree_doc:
        report.add(path, 1, "header", "missing module header docstring")
        return
    if "MIT License" not in tree_doc:
        report.add(path, 1, "header", "module docstring is missing the MIT License block")
    if "File Name:" not in tree_doc:
        report.add(path, 1, "header", "module docstring is missing the 'File Name:' line")
    else:
        declared = tree_doc.split("File Name:")[1].splitlines()[0].strip()
        if "<" in declared:
            return
        if path.name not in declared:
            report.add(path, 1, "header",
                       f"'File Name: {declared}' does not match the actual file {path.name}")


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
        if args and "Args:" in doc and "(1)" not in doc:
            report.add(path, node.lineno, "docstring",
                       f"function '{node.name}' Args entries are not numbered '(1) ...'")
        returns_value = any(isinstance(n, ast.Return) and n.value is not None
                            for n in ast.walk(node))
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


def check_file(path: Path, report: Report) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return

    check_header(source, path, report)

    for i, line in enumerate(source.splitlines(), start=1):
        if len(line) > MAX_LINE:
            report.add(path, i, "length", f"line is {len(line)} chars (limit {MAX_LINE})")
        if re.search(r"==\s*(False|True)\b", line):
            report.add(path, i, "comparison", "use 'not x' / 'x' instead of '== False' / '== True'")

    check_tokens(source, path, report)

    if "import logging" in source:
        report.add(path, 1, "logging", "the project uses print('[INFO] ...'), not the logging module")
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
            if not PASCAL_SNAKE.match(node.name.rsplit("_", 1)[0] + "_X"):
                pass
            doc = ast.get_docstring(node)
            if not doc:
                report.add(path, node.lineno, "docstring",
                           f"class '{node.name}' has no docstring")
            else:
                check_docstring_format(doc, node, path, report, "class")
                if node.name.endswith("_Cls") and "Initialization of the Class:" not in doc:
                    report.add(path, node.lineno, "docstring",
                               f"class '{node.name}' docstring has no "
                               "'Initialization of the Class:' section")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "main":
                continue
            if not node.name.startswith("__"):
                if not PASCAL_SNAKE.match(node.name):
                    report.add(path, node.lineno, "naming",
                               f"function '{node.name}' should be Pascal_Snake_Case")
            doc = ast.get_docstring(node)
            if node.name != "__init__":
                if not doc:
                    report.add(path, node.lineno, "docstring",
                               f"function '{node.name}' has no docstring")
                else:
                    check_docstring_format(doc, node, path, report, "function")
            all_args = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
            for arg in all_args:
                if arg.arg in {"self", "cls"}:
                    continue
                if arg.annotation is None:
                    report.add(path, node.lineno, "typing",
                               f"parameter '{arg.arg}' of '{node.name}' is not annotated")
                if arg.arg.endswith("_Str") and PASCAL_SNAKE.match(arg.arg):
                    continue   # parameter named after the structure it carries
                if not (SNAKE.match(arg.arg) or MATH_SYMBOL.match(arg.arg)):
                    report.add(path, node.lineno, "naming",
                               f"parameter '{arg.arg}' should be snake_case or a math symbol")
            if node.returns is None:
                report.add(path, node.lineno, "typing",
                           f"function '{node.name}' has no return annotation")
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d]:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)) or (
                    isinstance(default, ast.BinOp) and isinstance(default.left, ast.List)
                ):
                    report.add(path, node.lineno, "mutable-default",
                               f"'{node.name}' has a mutable default argument - use None instead")

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
                continue   # preset dataclass instance, e.g. Universal_Robots_UR3_Str
            report.add(path, node.lineno, "naming",
                       f"module-level '{target.id}' should be CONST_* "
                       "or a Pascal_Snake_Case *_Str preset")


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]]
    if not paths:
        print(__doc__)
        return 1
    files: list[Path] = []
    for p in paths:
        files.extend(sorted(p.rglob("*.py")) if p.is_dir() else [p])

    report = Report()
    for f in files:
        check_file(f, report)

    for item in report.items:
        print(item)
    print(f"\n{len(files)} file(s) checked, {len(report.items)} issue(s) found.")
    return 1 if report.items else 0


if __name__ == "__main__":
    raise SystemExit(main())
