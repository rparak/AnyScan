## =========================================================================== ##
# MIT License
# Copyright (c) 2025 JIC Smart Factory
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
## =========================================================================== ##
# Author   : JIC Smart Factory
# File Name: ../test/UI/test_square_corners.py
## =========================================================================== ##

# System (Default)
import glob
import os
import re
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Every corner the UI draws is square, as the JIC Smart Factory brand draws its blocks, buttons and rules
    (docs/design-decisions.md, "Corners are square, as the brand draws them"). This scans the UI modules' code for a
    stylesheet 'border-radius' or a painted rounded rectangle (drawRoundedRect, addRoundedRect); a comment may name
    them. The architecture diagram's generator is held the same way, for an SVG 'rx'.
"""
# The UI package and the diagram's generator.
#   Unit [string]
CONST_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
CONST_UI_DIR = os.path.join(CONST_ROOT, 'src', 'UI')
CONST_GENERATOR = os.path.join(CONST_ROOT, 'Example', 'UI', 'architecture_diagram.py')
# What rounds a corner: a stylesheet radius, a painted rounded rectangle, an SVG rectangle's radius in the
# diagram's own drawing calls (its icon set aside: its shapes are artwork on a 24-unit grid).
#   Unit [Pattern]
CONST_ROUNDED = re.compile(r'border-[a-z-]*radius|drawRoundedRect|addRoundedRect')
CONST_SVG_RADIUS = re.compile(r'\brx\s*=')


def _Code_Lines(path: str) -> tp.List[tp.Tuple[int, str]]:
    """
    Description:
        A source file's lines with their numbers, each cut at a '#' comment that starts the line.

    Args:
        (1) path [string]: The file.

    Returns:
        (1) parameter [Vector<Tuple<int, string>>]: (line number, text) for every line that is not a comment.
    """

    with open(path, 'r', encoding='utf-8') as handle:
        return [(number, line) for number, line in enumerate(handle, 1) if not line.lstrip().startswith('#')]


def test_no_ui_corner_is_rounded() -> None:
    """
    Description:
        No UI module sets a border radius in a stylesheet or paints a rounded rectangle.
    """

    found = ['%s:%d: %s' % (os.path.relpath(path, CONST_ROOT), number, line.strip())
             for path in glob.glob(os.path.join(CONST_UI_DIR, '**', '*.py'), recursive=True)
             for number, line in _Code_Lines(path) if CONST_ROUNDED.search(line)]
    assert found == [], 'rounded corners:\n' + '\n'.join(found)


def test_no_diagram_rectangle_is_rounded() -> None:
    """
    Description:
        The architecture diagram's generator gives no rectangle a corner radius.
    """

    found = [(number, line.strip()) for number, line in _Code_Lines(CONST_GENERATOR)
             if CONST_SVG_RADIUS.search(line) and 'CONST_ICONS' not in line and not line.lstrip().startswith(("'", '"'))]
    assert found == [], 'rounded rectangles in the diagram: %s' % found
