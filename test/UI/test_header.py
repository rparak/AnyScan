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
import subprocess
import sys
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
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
# Custom Lib.: AnyScan UI — the logo renderer
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan — the one configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The top bar's brand group — the AnyScan logo, a divider, the JIC mark — measured from a grab of
    the real header: the gaps are the space the eye sees, from the logo's rightmost ink to the divider
    and from the divider to the JIC mark's first ink, found in the grabbed pixels, not in the SVG.

    The logo's height follows the display's density (Style.Logo_Height). The module runs at the
    session's device pixel ratio (1 offscreen) and runs itself once more at DPR 2 in a fresh
    interpreter, so both the height and the gaps are measured at both ratios.
"""
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
# The chosen gap (docs/design-decisions.md, "The logo's text is outlined"): the funding band's 32 px
# around its divider. Pinned here, so a change of the constant is a change of this decision.
#   Unit [px]
CONST_EXPECTED_GAP = 32
# A pixel is ink when it differs from the header background by more than this (sum over R, G, B).
#   Unit [-]
CONST_INK_THRESHOLD = 30
# The logo's heights (docs/design-decisions.md, "The logo is 59 px on a low-density display"), and the
# share of its height that is ink: the viewBox is the ink plus 5 units on each side of 174.
#   Unit [px] / [-]
CONST_LOGO_HEIGHT_LOW_DENSITY = 59
CONST_LOGO_HEIGHT_HIGH_DENSITY = 54
CONST_LOGO_INK_SHARE = (174 - 2 * 5) / 174.0
# How far the grabbed ink height may differ from that share: one anti-aliased row at the top and one at
# the bottom. The two heights' ink differs by 4.7 px, so the check still tells 59 from 54.
#   Unit [px]
CONST_INK_HEIGHT_TOLERANCE = 2
# The ratio the second run uses, standing in for a 2x (Retina) display.
#   Unit [-]
CONST_HIGH_DENSITY_SCALE = '2'


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


def _Shown_Logo(qt_app: QApplication) -> tp.Tuple[AnyScan_Window_Cls, QLabel, float]:
    """
    Description:
        A shown window's header logo, and the height of its ink as grabbed from the window.

    Args:
        (1) qt_app [QApplication(object)]: The application.

    Returns:
        (1) parameter [Tuple<AnyScan_Window_Cls, QLabel, float>]: The window, the logo label and the ink
                                                                   height in logical pixels.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION)
    window.show()
    window.resize(1720, 900)
    for _ in range(20):
        qt_app.processEvents()
    logo = [label for label in window.findChildren(QLabel) if label.pixmap() is not None and not label.pixmap().isNull()][0]
    grab = window.grab(QRect(logo.mapTo(window, QPoint(0, 0)), logo.size()))
    pixels = _Pixels(grab.toImage())
    rows = np.flatnonzero((np.abs(pixels - pixels[0, 0]).sum(axis=2) > CONST_INK_THRESHOLD).any(axis=1))
    return window, logo, (rows[-1] + 1 - rows[0]) / grab.devicePixelRatio()


def test_the_logo_is_59_px_on_a_low_density_display(qt_app) -> None:
    """
    Description:
        Below DPR 1.5 the header logo is drawn 59 px tall: its pixmap is 59 logical pixels, and the ink
        grabbed from the window spans the logo's ink share of 59 px (±CONST_INK_HEIGHT_TOLERANCE), not of 54.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the low-density logo is measured in the DPR 1 run'
                    % qt_app.devicePixelRatio())
    window, logo, ink = _Shown_Logo(qt_app)
    pixmap = logo.pixmap()
    assert pixmap.height() / pixmap.devicePixelRatio() == CONST_LOGO_HEIGHT_LOW_DENSITY
    assert abs(ink - CONST_LOGO_HEIGHT_LOW_DENSITY * CONST_LOGO_INK_SHARE) <= CONST_INK_HEIGHT_TOLERANCE, 'logo ink is %.1f px tall' % ink
    window.close()


def test_the_logo_is_unchanged_on_a_high_density_display(qt_app) -> None:
    """
    Description:
        At DPR 1.5 and above the header logo is the 54 px render it has always been: the same pixels as
        Style.Load_Svg at 54 px, 54 logical pixels tall, and the grabbed ink spans the ink share of 54 px.
    """

    if qt_app.devicePixelRatio() < Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this run is at DPR %g; the high-density logo is measured in the DPR 2 run'
                    % qt_app.devicePixelRatio())
    window, logo, ink = _Shown_Logo(qt_app)
    pixmap = logo.pixmap()
    assert pixmap.height() / pixmap.devicePixelRatio() == CONST_LOGO_HEIGHT_HIGH_DENSITY
    assert pixmap.toImage() == Style.Load_Svg('anyscan-logo.svg', CONST_LOGO_HEIGHT_HIGH_DENSITY).toImage()
    assert abs(ink - CONST_LOGO_HEIGHT_HIGH_DENSITY * CONST_LOGO_INK_SHARE) <= CONST_INK_HEIGHT_TOLERANCE, 'logo ink is %.1f px tall' % ink
    window.close()


def test_the_header_is_measured_again_at_dpr_2(qt_app, project_root) -> None:
    """
    Description:
        This module, run again in a fresh interpreter at DPR 2 (QT_SCALE_FACTOR=2), passes: the high-density
        logo test and both gap tests pass there, and the low-density test is the one that skips.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this is the DPR %g run' % qt_app.devicePixelRatio())
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=CONST_HIGH_DENSITY_SCALE, PYTHONDONTWRITEBYTECODE='1')
    run = subprocess.run([sys.executable, '-m', 'pytest', os.path.abspath(__file__), '-rA', '-p', 'no:cacheprovider'],
                         cwd=project_root, env=env, capture_output=True, text=True, timeout=300)
    report = run.stdout + run.stderr
    assert run.returncode == 0, report[-3000:]
    for passed in ('test_the_logo_is_unchanged_on_a_high_density_display',
                   'test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink[0]',
                   'test_the_brand_marks_are_spaced_by_the_brand_gap_from_ink[1720]'):
        assert 'PASSED test/UI/test_header.py::%s' % passed in report, report[-3000:]
    assert 'SKIPPED' in report and 'the low-density logo is measured in the DPR 1 run' in report, report[-3000:]
