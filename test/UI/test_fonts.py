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
# File Name: ../test/UI/test_fonts.py
## =========================================================================== ##

# System (Default)
import glob
import os
import re
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QFont, QFontInfo, QRawFont
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the font loader
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style

"""
Description:
    The bundled UI fonts (docs/design-decisions.md, "The UI fonts are bundled"): after Style.Load_Fonts the
    UI family resolves to Inter and the monospace family to JetBrains Mono, from App/assets/fonts/, and every
    weight the UI code requests draws its own face of each, with the matching style name. The weights are
    read from the UI source, so a weight added to the code without a face fails here. The display cut
    (Inter Display, the header's wordmark) resolves to its own bundled face, never to the text cut.
"""
# The source the UI's font weights are read from, and the QFont weight names it may use.
#   Unit [string]
CONST_UI_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src', 'UI')
CONST_WEIGHT_PATTERN = r'QFont\.(Thin|ExtraLight|Light|Normal|Medium|DemiBold|Bold|ExtraBold|Black)\b'
# The face each weight must draw: the style name its static file carries.
#   Unit [Dict<string, string>]
CONST_STYLE_OF_WEIGHT = {'Normal': 'Regular', 'Medium': 'Medium', 'DemiBold': 'SemiBold', 'Bold': 'Bold'}
# The families the bundle provides, and each one's licence file beside it.
#   Unit [Dict<string, string>]
CONST_FAMILIES = {'Inter': 'Inter-OFL.txt', 'Inter Display': 'Inter-OFL.txt', 'JetBrains Mono': 'JetBrainsMono-OFL.txt'}


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """
    A single offscreen QApplication for the module, with the fonts loaded as the application loads them.
    """
    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


def _Requested_Weights() -> list:
    """
    Description:
        Every QFont weight name the UI source uses, plus Normal (Style.Font's default).

    Returns:
        (1) parameter [Vector<string>]: The weight names, sorted.
    """

    names = {'Normal'}
    for path in glob.glob(os.path.join(CONST_UI_SOURCE, '**', '*.py'), recursive=True):
        with open(path, 'r', encoding='utf-8') as handle:
            names.update(re.findall(CONST_WEIGHT_PATTERN, handle.read()))
    return sorted(names)


def test_the_ui_and_monospace_families_resolve_to_the_bundled_fonts(qt_app) -> None:
    """
    Description:
        After Load_Fonts, FONT_UI is Inter and FONT_MONO is JetBrains Mono, and a font built from each resolves
        to that family (QFontInfo), not to a platform substitute.
    """

    assert (Style.FONT_UI, Style.FONT_MONO) == ('Inter', 'JetBrains Mono')
    assert QFontInfo(QFont(Style.FONT_UI)).family() == 'Inter'
    assert QFontInfo(QFont(Style.FONT_MONO)).family() == 'JetBrains Mono'


@pytest.mark.parametrize('mono', [False, True], ids=['ui', 'mono'])
def test_every_requested_weight_draws_its_own_face(qt_app, mono) -> None:
    """
    Description:
        Each weight the UI requests draws the face with its style name (500 Medium, 600 SemiBold, ...) in the
        bundled family, and no two weights draw the same face.
    """

    weights = _Requested_Weights()
    assert set(weights) <= set(CONST_STYLE_OF_WEIGHT), 'a weight with no bundled face: %s' % weights
    drawn = {}
    for name in weights:
        raw = QRawFont.fromFont(Style.Font(10, getattr(QFont, name), mono=mono))
        drawn[name] = (raw.familyName(), raw.styleName())
    expected = {name: (Style.FONT_MONO if mono else Style.FONT_UI, CONST_STYLE_OF_WEIGHT[name]) for name in weights}
    wrong = {name: drawn[name] for name in weights if drawn[name] != expected[name]}
    assert not wrong, 'drawn instead of the expected face: %s' % wrong
    assert len(set(drawn.values())) == len(weights)


def test_the_display_cut_is_its_own_bundled_face(qt_app) -> None:
    """
    Description:
        Style.Font(display=True) resolves (QFontInfo) to Inter Display Regular, and the face drawn is
        App/assets/fonts/InterDisplay-Regular.ttf (its name table is that file's), not the text cut's.
    """

    font = Style.Font(30, display=True)
    info = QFontInfo(font)
    assert (info.family(), info.styleName()) == (Style.CONST_FONT_DISPLAY, 'Regular')
    fonts = os.path.join(Style.CONST_ASSETS, 'fonts')
    drawn = QRawFont.fromFont(font).fontTable('name')
    assert drawn == QRawFont(os.path.join(fonts, 'InterDisplay-Regular.ttf'), 12).fontTable('name')
    assert drawn != QRawFont(os.path.join(fonts, 'Inter-Regular.ttf'), 12).fontTable('name')


def test_each_bundled_family_ships_its_licence() -> None:
    """
    Description:
        The SIL Open Font License each bundled family is distributed under sits beside its fonts.
    """

    directory = os.path.join(Style.CONST_ASSETS, 'fonts')
    for family, licence in CONST_FAMILIES.items():
        path = os.path.join(directory, licence)
        assert os.path.isfile(path), 'missing %s' % path
        with open(path, 'r', encoding='utf-8') as handle:
            assert 'SIL Open Font License, Version 1.1' in handle.read()
        assert glob.glob(os.path.join(directory, '%s-*.ttf' % family.replace(' ', '')))
