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
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
# Custom Lib.: AnyScan UI — the band, the SVG image widget, the window and the style tokens
#   ../UI/Widgets, ../UI/Core, ../UI/Utilities/Style, ../Configuration/Core
from UI.Widgets import Funding_Row_Cls, Svg_Image_Cls
from UI.Core import AnyScan_Window_Cls
import UI.Utilities.Style as Style
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The funding band at the foot of the window (the owner's decisions, 2026-10-14 and 2026-10-15): one centred group of
    the EDIH-DIGIMAT wordmark, a faint rule, the Ministry of Industry and Trade's logo and the EU emblem, each a white SVG
    traced from its PNG, on the purple, with the brand's pixel motif in the rest of the band, never within the EU
    emblem's protection area of a logo. The EU disclaimer is not in the window's band; the README and the architecture
    diagram's band carry it. Measured on the built band, shown in the window at its default and minimum widths.
"""
# The EU's required disclaimer, word for word.
#   Unit [string]
CONST_EU_DISCLAIMER = ('Funded by the European Union. Views and opinions expressed are however those of the author(s) only '
                       'and do not necessarily reflect those of the European Union or European Commission. Neither the '
                       'European Union nor the granting authority can be held responsible for them.')
# The station's maximised window width (None stands for the window's minimum width), and a band narrower than the
# window allows, where the motif's reach would run into the logos but for their clear space.
#   Unit [px]
CONST_DEFAULT = 1920
CONST_NARROW = 1100
CONST_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module, with the bundled fonts."""
    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


@pytest.fixture(scope='module', params=[CONST_DEFAULT, None, CONST_NARROW],
                ids=['default window', 'minimum window', 'narrow band'])
def shown(qt_app, request) -> tp.Tuple[tp.Optional[AnyScan_Window_Cls], Funding_Row_Cls]:
    """The main window, shown at the default or its minimum width, and its band; or the band alone, narrow."""
    if request.param == CONST_NARROW:
        band = Funding_Row_Cls()
        band.resize(CONST_NARROW, 90)
        band.show()
        for _ in range(10):
            QApplication.processEvents()
        yield None, band
        band.close()
        return
    configuration = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
    window = AnyScan_Window_Cls(Configuration_Str=configuration)
    window.show()
    window.resize(request.param or window.minimumSizeHint().width(), 1000)
    for _ in range(30):
        QApplication.processEvents()
    yield window, window.findChild(Funding_Row_Cls)
    window.close()


def _Logos(band: Funding_Row_Cls) -> tp.List[tp.Tuple[int, int]]:
    """Each logo's left and right edge in the band, from left to right."""
    spans = [(w.mapTo(band, QPoint(0, 0)).x(), w.mapTo(band, QPoint(0, 0)).x() + w.width())
             for w in band.findChildren(Svg_Image_Cls)]
    return sorted(spans)


def _Pixels(band: Funding_Row_Cls) -> np.ndarray:
    """The band as drawn, RGB, in logical pixels (the tests run at DPR 1 here)."""
    image = band.grab().toImage().convertToFormat(QImage.Format_RGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    array = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return array[:, :image.width(), 2::-1].astype(int)


def test_the_band_carries_the_three_traced_logos_and_no_text(shown) -> None:
    """
    Description:
        The band holds exactly three images, in order, each the traced white SVG drawn at its height, the EU emblem at
        least as tall as every other logo (the EU's visibility rules), and no text: the disclaimer is not in it.
    """

    _, band = shown
    logos = sorted(band.findChildren(Svg_Image_Cls), key=lambda w: w.x())
    expected = [(name, height) for name, height in Funding_Row_Cls.LOGOS if name is not None]
    assert [name for name, _ in expected] == ['edih-digimat-white.svg', 'partner-ministry-white.svg', 'funder-eu-white.svg']
    assert [logo.height() for logo in logos] == [height for _, height in expected]
    assert dict(expected)['funder-eu-white.svg'] >= max(height for _, height in expected)
    assert [label for label in band.findChildren(QLabel) if label.text()] == []


def test_the_disclaimer_is_kept_word_for_word_in_the_readme_and_the_diagram() -> None:
    """
    Description:
        The EU disclaimer, out of the window's band, is in the README word for word (across its line breaks) and is the
        text the architecture diagram's band carries.
    """

    assert Funding_Row_Cls.DISCLAIMER == CONST_EU_DISCLAIMER
    with open(os.path.join(CONST_ROOT, 'README.md'), 'r', encoding='utf-8') as handle:
        readme = ' '.join(handle.read().split())
    assert CONST_EU_DISCLAIMER in readme


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


def test_the_logo_group_is_centred_and_the_band_is_as_tall_as_its_logos(shown) -> None:
    """
    Description:
        The logos, the rule among them, are one group centred in the band (within a pixel), so the rule sits left of
        the middle; the band is as tall as its tallest logo and its padding, at either width.
    """

    _, band = shown
    left, right = band.box.getContentsMargins()[0], band.box.getContentsMargins()[2]
    spans = _Logos(band)
    before, after = spans[0][0] - left, band.width() - right - spans[-1][1]
    assert abs(before - after) <= 1
    rule = [w for w in band.findChildren(QWidget) if w.objectName() == 'hairline'][0]
    assert rule.mapTo(band, QPoint(0, 0)).x() < band.width() / 2
    assert band.sizeHint().height() == max(height for _, height in Funding_Row_Cls.LOGOS) + 2 * 16 + 2
    assert Style.CONST_BAND_LINE.upper() == '#FFFFFF' and Style.CONST_BAND_LINE_ALPHA <= 0.25


def test_the_motif_is_faint_squares_at_both_ends_clear_of_every_logo(shown) -> None:
    """
    Description:
        The band, as drawn, is the purple and the motif's squares everywhere but on its logos and rule: each square is
        a whole cell of the grid, white at the motif's low opacities, there are squares at both ends, and within
        CLEAR_SPACE of a logo (the EU emblem's protection area) there is nothing but the purple, the logos and the rule.
    """

    _, band = shown
    drawn = _Pixels(band)
    purple = np.array([int(Style.CONST_BAND[i:i + 2], 16) for i in (1, 3, 5)])
    tints = [np.round(alpha * 255 + (1 - alpha) * purple) for alpha in Funding_Row_Cls.MOTIF_ALPHA]
    assert max(Funding_Row_Cls.MOTIF_ALPHA) <= 0.15
    spans = _Logos(band)
    # The EU emblem's protection area: half the flag's height, the flag as tall as the EU logo.
    required = dict(Funding_Row_Cls.LOGOS)['funder-eu-white.svg'] / 2
    assert Funding_Row_Cls.CLEAR_SPACE >= required
    group = (int(spans[0][0] - required), int(spans[-1][1] + required))
    cell = Funding_Row_Cls.MOTIF_CELL
    outside = np.ones(drawn.shape[1], bool)
    outside[group[0]:group[1]] = False
    for x in np.where(outside)[0]:
        for y in range(drawn.shape[0]):
            pixel = drawn[y, x]
            is_tint = [np.abs(pixel - tint).max() <= 1 for tint in tints]
            assert np.abs(pixel - purple).max() <= 1 or any(is_tint), (x, y, pixel)
            if any(is_tint):
                # A square is a whole cell: the cell it is in is that tint throughout.
                cx = x if x < band.width() / 2 else band.width() - 1 - x
                left = x - cx % cell if x < band.width() / 2 else x + cx % cell - (cell - 1)
                block = drawn[y // cell * cell:(y // cell + 1) * cell, left:left + cell]
                assert (np.abs(block - pixel).max(axis=2) <= 1).all(), (x, y)
    # Within the clear space, every column that is not a logo's or the rule's is the bare purple.
    rule = [w for w in band.findChildren(QWidget) if w.objectName() == 'hairline'][0]
    taken = spans + [(rule.mapTo(band, QPoint(0, 0)).x(), rule.mapTo(band, QPoint(0, 0)).x() + rule.width())]
    bare = [x for x in range(group[0], group[1]) if not any(a <= x < b for a, b in taken)]
    assert len(bare) >= 2 * required
    assert (np.abs(drawn[:, bare] - purple).max(axis=2) <= 1).all(), 'a square within the clear space'
    tinted = np.zeros(drawn.shape[1], bool)
    for tint in tints:
        tinted |= (np.abs(drawn - tint).max(axis=2) <= 1).any(axis=0)
    assert tinted[:group[0]].any() and tinted[group[1]:].any(), 'no squares at one end'
