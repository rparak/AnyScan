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
import os
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication, QLabel
# Custom Lib.: AnyScan UI — the band and the logo loader
#   ../UI/Widgets, ../UI/Utilities/Style
from UI.Widgets import Funding_Row_Cls
import UI.Utilities.Style as Style

"""
Description:
    The funding band at the foot of the window, as on the AnyScan poster's footer (the owner's decision, 2026-10-14):
    the EDIH-DIGIMAT wordmark, a rule, the Ministry of Industry and Trade's logo and the EU emblem, each its white
    version, then a rule and the EU disclaimer, all white on the purple. Measured on the built band: the images it
    shows, in order, the rules' colour and the text.
"""


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def test_the_band_carries_the_three_logos_and_the_disclaimer_in_white(qt_app) -> None:
    """
    Description:
        The band holds exactly three images, in the poster's order, each the white asset as Style.Load_Logo draws it,
        and one text, the EU disclaimer, drawn in white on the purple; its two rules are white.
    """

    band = Funding_Row_Cls()
    band.resize(1600, 140)
    row = band.box.itemAt(0).layout()
    labels = [row.itemAt(i).widget() for i in range(row.count()) if isinstance(row.itemAt(i).widget(), QLabel)]
    images = [label.pixmap() for label in labels]
    expected = [(name, height) for name, height in Funding_Row_Cls.LOGOS if name is not None]
    assert [name for name, _ in expected] == ['edih-digimat-white.png', 'partner-ministry-white.png', 'funder-eu-white.png']
    assert len(images) == 3 and all(image is not None and not image.isNull() for image in images)
    assert [image.toImage() for image in images] == [Style.Load_Logo(name, height).toImage() for name, height in expected]
    texts = [label for label in band.findChildren(QLabel) if label.text()]
    assert [label.text() for label in texts] == [Funding_Row_Cls.DISCLAIMER]
    assert Style.CONST_BAND_TEXT.upper() == '#FFFFFF' and Style.CONST_BAND_LINE.upper() == '#FFFFFF'
    band.show()
    QApplication.processEvents()
    drawn = texts[0].grab().toImage()
    assert any(drawn.pixelColor(x, y).name() == '#ffffff' for x in range(0, drawn.width(), 2) for y in range(drawn.height())), \
        'the disclaimer is not drawn in white'
