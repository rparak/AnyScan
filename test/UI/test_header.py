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
# File Name: ../test/UI/test_header.py
## =========================================================================== ##

# System (Default)
import dataclasses
import os
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
# Custom Lib.: AnyScan UI — the main window
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
# Custom Lib.: AnyScan — the one configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The top bar's brand group — the AnyScan logo, a divider, the JIC mark — measured from a grab of
    the real header: the gaps are the space the eye sees, from the logo's rightmost ink to the divider
    and from the divider to the JIC mark's first ink, found in the grabbed pixels, not in the SVG.
"""
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
# The chosen gap (docs/design-decisions.md, "The logo's text is outlined"): the funding band's 32 px
# around its divider. Pinned here, so a change of the constant is a change of this decision.
#   Unit [px]
CONST_EXPECTED_GAP = 32
# A pixel is ink when it differs from the header background by more than this (sum over R, G, B).
#   Unit [-]
CONST_INK_THRESHOLD = 30


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """
    A single offscreen QApplication for the module. Style.Load_Fonts is not called: the marks measured
    here are outlines and a PNG, and Load_Fonts would change the UI font for every later test module.
    """
    return QApplication.instance() or QApplication([])


def _Pixels(image: QImage) -> np.ndarray:
    """
    Description:
        An image's RGB pixels as an array.

    Args:
        (1) image [QImage(object)]: The image.

    Returns:
        (1) parameter [Matrix<int> HxWx3]: Its pixels.
    """

    image = image.convertToFormat(QImage.Format_ARGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), :3].astype(int)


@pytest.mark.parametrize('width', [0, 1720])
def test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink(qt_app, width) -> None:
    """
    Description:
        In the shown header, at the minimum window width and at 1720 px, the logo's rightmost ink sits
        CONST_EXPECTED_GAP (±1 px) left of the divider, and the JIC mark's first ink CONST_EXPECTED_GAP
        right of it. A margin inside an image is space the eye sees, so it counts.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION)
    window.show()
    window.resize(width or window.minimumSizeHint().width(), 900)
    for _ in range(20):
        qt_app.processEvents()
    labels = [label for label in window.findChildren(QLabel) if label.pixmap() is not None and not label.pixmap().isNull()]
    logo, jic = labels[0], labels[1]
    bar = logo.parentWidget()
    divider = [w for w in bar.findChildren(QWidget) if w.objectName() == 'hairline' and w.parentWidget() is bar][0]

    grab = window.grab(QRect(bar.mapTo(window, QPoint(0, 0)), bar.size()))
    ratio = grab.devicePixelRatio()
    pixels = _Pixels(grab.toImage())
    ink = np.abs(pixels - pixels[1, 1]).sum(axis=2) > CONST_INK_THRESHOLD

    def Left(widget: QWidget) -> int:
        return widget.mapTo(bar, QPoint(0, 0)).x()

    logo_columns = np.flatnonzero(ink[:, int(Left(logo) * ratio):int((Left(logo) + logo.width()) * ratio)].any(axis=0))
    logo_ink_right = Left(logo) + (logo_columns[-1] + 1) / ratio
    jic_columns = np.flatnonzero(ink[:, int(Left(jic) * ratio):int((Left(jic) + jic.width()) * ratio)].any(axis=0))
    jic_ink_left = Left(jic) + jic_columns[0] / ratio

    gap = CONST_EXPECTED_GAP
    assert abs((Left(divider) - logo_ink_right) - gap) <= 1, \
        'logo ink -> divider is %.1f px, expected %d' % (Left(divider) - logo_ink_right, gap)
    assert abs((jic_ink_left - (Left(divider) + divider.width())) - gap) <= 1, \
        'divider -> JIC ink is %.1f px, expected %d' % (jic_ink_left - Left(divider) - divider.width(), gap)
    window.close()
