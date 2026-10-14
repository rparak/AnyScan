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
    The funding band at the foot of the window shows the EU emblem and its disclaimer side by side, and no other
    logo: the project's (EDIH-DIGIMAT) and the Ministry's are not shown in the application (the owner's decision,
    2026-10-14). Measured on the built band: the images it shows and the text beside them.
"""


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def test_the_band_shows_the_eu_emblem_and_its_disclaimer_alone(qt_app) -> None:
    """
    Description:
        The band holds exactly one image, the EU emblem as Style.Load_Logo draws it, and one text, the EU disclaimer,
        beside it in one row; no label names a missing asset.
    """

    band = Funding_Row_Cls()
    labels = band.findChildren(QLabel)
    images = [label.pixmap() for label in labels if label.pixmap() is not None and not label.pixmap().isNull()]
    texts = [label.text() for label in labels if label.text()]
    name, height = Funding_Row_Cls.EMBLEM
    assert name == 'funder-eu-white.png'
    assert len(images) == 1 and images[0].toImage() == Style.Load_Logo(name, height).toImage()
    assert texts == [Funding_Row_Cls.DISCLAIMER]
