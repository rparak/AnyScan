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
# File Name: ../test/UI/test_colour_tokens.py
## =========================================================================== ##

# System (Default)
import os
import re
import sys
import tokenize
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Every colour the UI paints comes from a theme token (Parameters/Theme.py, re-exported by
    UI/Utilities/Style.py) — never a literal at the call site. A literal is how a token's value gets
    hand-copied (the busy overlay once filled with QColor(43, 36, 85, 158): the ink token's value at
    another opacity) and then drifts from it. This scans the UI modules' source for a hex colour
    string or a QColor built from numbers; Style.py, which builds colours from tokens, is exempt.
"""
# The UI package, and the one module allowed to turn tokens into colours.
#   Unit [string]
CONST_UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'UI')
CONST_EXEMPT = os.path.join('Utilities', 'Style.py')
# A hex colour (#rgb, #rrggbb or #rrggbbaa) anywhere inside a string, a stylesheet included;
# '#scrim'-style object names do not match, since their letters are not hex digits.
#   Unit [Pattern]
CONST_HEX_COLOUR = re.compile(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9A-Za-z_])')


def _Literals() -> tp.List[str]:
    """
    Description:
        Every colour literal in a UI module outside Style.py, as 'path:line: text': a hex colour in a
        string token, or a QColor( whose first argument is a number or a string. Read with the Python
        tokenizer, so comments and docstrings are told apart from code.

    Returns:
        (1) parameter [Vector<string>]: The offending lines; empty when every colour is a token.
    """

    found = []
    for root, _dirs, files in os.walk(CONST_UI_DIR):
        for name in sorted(files):
            path = os.path.join(root, name)
            relative = os.path.relpath(path, CONST_UI_DIR)
            if not name.endswith('.py') or relative == CONST_EXEMPT:
                continue
            with open(path, 'r', encoding='utf-8') as handle:
                tokens = [token for token in tokenize.generate_tokens(handle.readline)
                          if token.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                                                tokenize.INDENT, tokenize.DEDENT)]
            for i, token in enumerate(tokens):
                docstring = token.type == tokenize.STRING and (i == 0 or tokens[i - 1].string in (':', '')) \
                    and token.string.lstrip('rbuRBU').startswith(('"""', "'''"))
                hex_colour = token.type == tokenize.STRING and not docstring and CONST_HEX_COLOUR.search(token.string)
                qcolor = (token.string == 'QColor' and i + 2 < len(tokens) and tokens[i + 1].string == '('
                          and tokens[i + 2].type in (tokenize.NUMBER, tokenize.STRING))
                if hex_colour or qcolor:
                    found.append('%s:%d: %s' % (relative, token.start[0], token.line.strip()))
    return found


def test_the_ui_paints_only_theme_tokens() -> None:
    """
    Description:
        No UI module outside Style.py names a colour by value: each comes from a Style / Theme
        token (Style.Token_Color for an opacity). A new colour is a new token in Parameters/Theme.py.
    """

    assert _Literals() == []


def test_the_scan_would_catch_a_literal(tmp_path, monkeypatch) -> None:
    """
    Description:
        The scan is not vacuous: a UI module holding either form of literal is reported.
    """

    (tmp_path / 'Widget.py').write_text("pen = QPen(QColor(43, 36, 85, 158))\nlabel.setStyleSheet('color: #c9c5d8;')\n"
                                        "ok = Style.Token_Color(Style.CONST_INK)\n")
    monkeypatch.setattr(sys.modules[__name__], 'CONST_UI_DIR', str(tmp_path))
    assert [line.split(':')[1] for line in _Literals()] == ['1', '2']
