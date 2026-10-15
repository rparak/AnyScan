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
# File Name: ../test/UI/test_funding_band.py
## =========================================================================== ##

# System (Default)
import dataclasses
import os
import re
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QFontInfo, QFontMetricsF, QTextDocument
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the band, the SVG image widget and the style tokens
#   ../UI/Widgets, ../UI/Utilities/Style, ../Parameters/Theme
from UI.Widgets import Funding_Row_Cls, Svg_Image_Cls
from UI.Core import AnyScan_Window_Cls
import UI.Utilities.Style as Style
from Parameters.Theme import Contrast_Ratio
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The funding band at the foot of the window, as on the AnyScan poster's footer (the owner's decisions, 2026-10-14
    and 2026-10-15): in one row the EDIH-DIGIMAT wordmark, a rule, the Ministry of Industry and Trade's logo and the EU
    emblem, each a white SVG traced from its PNG, then a rule and the EU disclaimer beside them, on one line when it
    fits and otherwise in the fewest balanced lines, never below 9 pt and never clipped. Measured on the built band.
"""
# The EU's required disclaimer, word for word: the band must carry exactly this.
#   Unit [string]
CONST_EU_DISCLAIMER = ('Funded by the European Union. Views and opinions expressed are however those of the author(s) only '
                       'and do not necessarily reflect those of the European Union or European Commission. Neither the '
                       'European Union nor the granting authority can be held responsible for them.')
# A band wide enough for the disclaimer on one line, and the station's maximised window width.
#   Unit [px]
CONST_WIDE = 3200
CONST_DEFAULT = 1920


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module, with the bundled fonts."""
    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


def _Band(width: int) -> Funding_Row_Cls:
    """
    Description:
        The band, shown and laid out at a width.

    Args:
        (1) width [int]: The band's width, in logical pixels.

    Returns:
        (1) parameter [Funding_Row_Cls(object)]: The band.
    """

    band = Funding_Row_Cls()
    band.resize(width, 200)
    band.show()
    for _ in range(5):
        QApplication.processEvents()
    return band


def _Plain(html: str) -> str:
    """The text a rich-text label shows."""
    document = QTextDocument()
    document.setHtml(html)
    return document.toPlainText()


def _Lines(band: Funding_Row_Cls) -> int:
    """The number of lines the band's disclaimer is drawn in, at its drawn width."""
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setDefaultFont(band.note.font())
    document.setHtml(band.note.text())
    document.setTextWidth(band.note.width())
    document.size()
    block, lines = document.begin(), 0
    while block.isValid():
        lines += block.layout().lineCount()
        block = block.next()
    return lines


def test_the_band_carries_the_three_traced_logos_and_the_disclaimer(qt_app) -> None:
    """
    Description:
        The band holds exactly three images, in the poster's order, each the traced white SVG drawn at its height, and
        one text, the EU disclaimer word for word. The EU emblem is at least as tall as every other logo (the EU's
        visibility rules).
    """

    band = _Band(CONST_WIDE)
    logos = sorted(band.findChildren(Svg_Image_Cls), key=lambda w: w.x())
    expected = [(name, height) for name, height in Funding_Row_Cls.LOGOS if name is not None]
    assert [name for name, _ in expected] == ['edih-digimat-white.svg', 'partner-ministry-white.svg', 'funder-eu-white.svg']
    assert [logo.height() for logo in logos] == [height for _, height in expected]
    assert dict(expected)['funder-eu-white.svg'] >= max(height for _, height in expected)
    assert _Plain(band.note.text()) == Funding_Row_Cls.DISCLAIMER == CONST_EU_DISCLAIMER


def test_each_logo_file_is_one_white_outline_that_says_it_is_traced() -> None:
    """
    Description:
        Each band logo is a single solid white path, and the file says it was traced from a PNG and is not an official
        vector file, so it is replaced when one is delivered.
    """

    for name, _ in Funding_Row_Cls.LOGOS:
        if name is None:
            continue
        with open(os.path.join(Style.CONST_ASSETS, name), 'r', encoding='utf-8') as handle:
            svg = handle.read()
        assert 'Traced from the white PNG' in svg and 'not an official vector file' in svg, name
        assert len(re.findall(r'<path ', svg)) == 1 and re.findall(r'fill="([^"]+)"', svg) == ['#FFFFFF'], name


def test_the_rules_are_faint_and_the_disclaimer_secondary_but_legible() -> None:
    """
    Description:
        The rules are white at a low opacity, and the disclaimer white at an opacity below the logos' solid white that
        still clears 4.5:1 on the purple.
    """

    assert Style.CONST_BAND_LINE.upper() == '#FFFFFF' and Style.CONST_BAND_LINE_ALPHA <= 0.25
    assert Style.CONST_BAND_TEXT.upper() == '#FFFFFF' and Style.CONST_BAND_TEXT_ALPHA < 1.0
    rgb = [int(Style.CONST_BAND[i:i + 2], 16) for i in (1, 3, 5)]
    blended = '#%02X%02X%02X' % tuple(int(round(Style.CONST_BAND_TEXT_ALPHA * 255 + (1 - Style.CONST_BAND_TEXT_ALPHA) * c))
                                      for c in rgb)
    assert Contrast_Ratio(blended, Style.CONST_BAND) >= 4.5


def _Window_Band(width: tp.Optional[int]) -> tp.Tuple[AnyScan_Window_Cls, Funding_Row_Cls]:
    """
    Description:
        The main window, shown at a width (None: its minimum), and its band.

    Args:
        (1) width [int]: The window's width, or None for its minimum.

    Returns:
        (1) parameter [Tuple<AnyScan_Window_Cls, Funding_Row_Cls>]: The window and its band.
    """

    configuration = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
    window = AnyScan_Window_Cls(Configuration_Str=configuration)
    window.show()
    window.resize(width or window.minimumSizeHint().width(), 1000)
    for _ in range(30):
        QApplication.processEvents()
    return window, window.findChild(Funding_Row_Cls)


@pytest.mark.parametrize('where, lines', [('wide band', 1), ('default window', 2), ('minimum window', 3)])
def test_the_disclaimer_takes_the_fewest_lines_never_shrunk_or_clipped(qt_app, where, lines) -> None:
    """
    Description:
        Beside the logos the disclaimer is on one line when the band is wide enough, and wraps to the fewest lines that
        fit otherwise: two in the station's maximised window, three at the window's minimum width, balanced (no line
        much longer than the text's run over the line count). It stays at 9 pt or more, its label is as tall as its
        lines and lies inside the band, and the band asks to be as tall as its logos, or as the disclaimer where that
        is taller (by 2 px, at the minimum width at 100 dpi; at the station's 96 dpi three lines are 54 px, within
        the logos' 56).
    """

    window = None
    if where == 'wide band':
        band = _Band(CONST_WIDE)
    else:
        window, band = _Window_Band(CONST_DEFAULT if where == 'default window' else None)
    assert QFontInfo(band.note.font()).pointSizeF() >= 9.0
    assert _Lines(band) == lines
    run = QFontMetricsF(band.note.font()).horizontalAdvance(Funding_Row_Cls.DISCLAIMER)
    assert band.note.width() <= 1.1 * run / lines + 8
    assert band.note.height() >= band.note.font().pointSizeF() * lines
    right = band.note.mapTo(band, band.note.rect().topRight()).x()
    assert right <= band.width() - band.box.getContentsMargins()[2]
    tallest = max(height for _, height in Funding_Row_Cls.LOGOS)
    assert band.sizeHint().height() == max(tallest, band.note.height()) + 2 * 16 + 2
    if window is not None:
        assert band.height() == band.sizeHint().height()
        window.close()


def test_the_disclaimer_never_holds_the_window_wider(qt_app) -> None:
    """
    Description:
        The band's minimum width does not grow with the disclaimer's fitted width: laid out wide, it can still shrink
        to the window's minimum.
    """

    window, band = _Window_Band(None)
    assert _Band(CONST_WIDE).minimumSizeHint().width() == band.minimumSizeHint().width() < window.width() - 2 * 18
    window.close()


def test_the_band_keeps_one_height_as_the_window_resizes(qt_app) -> None:
    """
    Description:
        The disclaimer's box reserves the height of the lines it takes at the window's minimum width, so the band is
        one height from the minimum width to a wide window, and resizing never shifts the views above it.
    """

    window, band = _Window_Band(None)
    heights = []
    for width in (window.width(), CONST_DEFAULT, CONST_WIDE):
        window.resize(width, 1000)
        for _ in range(10):
            QApplication.processEvents()
        heights.append(band.height())
    window.close()
    assert len(set(heights)) == 1, heights
