"""Regression tests for check_style.py's Args-numbering rule.

Run with:  pytest .claude/skills/python-style-RP/scripts/test_check_style.py
(stdlib + pytest only; not part of the app's test/ suite).

Both the numbered '(1) ...' form and the grouped '(1 - N) a, b ...' form for
consecutive arguments of the same type are valid (see
references/docstrings-comments.md). This guards against the checker regressing to
accepting only the literal '(1)'.
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
