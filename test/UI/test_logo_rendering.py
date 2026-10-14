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
# File Name: ../test/UI/test_logo_rendering.py
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
from PyQt5.QtCore import QPoint, QRect, QRectF, QSize
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
# Custom Lib.: AnyScan UI — the main window, its widgets and the asset folder
#   ../UI/Core, ../UI/Widgets, ../UI/Utilities/Style
from UI.Core import AnyScan_Window_Cls
import UI.Widgets as Widgets
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan — the one configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Every SVG logo the window shows is rendered as vectors at its final size in device pixels, never drawn from a
    pixmap, scaled or not (docs/design-decisions.md, "Logos are rendered as vectors at paint time"): the AnyScan lockup's
    mark and wordmark, the JIC Smart Factory logo and the mark in the empty Camera View. Each is grabbed from the shown
    window and compared with the same SVG rendered directly into an image of the grabbed size; a raster scaled to fit,
    or one rounded to a whole-pixel width, differs (measured before this rule: up to 76, 229 and 70 levels at DPR 1).
    The module runs at the session's device pixel ratio and once more at DPR 2 in a fresh interpreter.
"""
# The largest per-channel difference allowed between the drawn logo and the direct render.
#   Unit [-] (0-255)
CONST_TOLERANCE = 2
# The device pixel ratio the second run uses.
#   Unit [string]
CONST_HIGH_DENSITY_SCALE = '2'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module, with the bundled fonts."""
    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app


@pytest.fixture(scope='module')
def window(qt_app) -> AnyScan_Window_Cls:
    """The main window, shown idle at 1720 x 1000, laid out and painted."""
    shown = AnyScan_Window_Cls(Configuration_Str=dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None))
    shown.resize(1720, 1000)
    shown.show()
    for _ in range(30):
        qt_app.processEvents()
    yield shown
    shown.close()


def _Pixels(image: QImage) -> np.ndarray:
    """
    Description:
        An image's RGB pixels as an array.

    Args:
        (1) image [QImage(object)]: The image.

    Returns:
        (1) parameter [Matrix<int> HxWx3]: Its pixels.
    """

    image = image.convertToFormat(QImage.Format_RGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :image.width(), 2::-1].astype(int)


def _Drawn_And_Direct(window: QWidget, widget: QWidget, rect: QRect, name: str, opacity: float = 1.0) -> tp.Tuple[np.ndarray, np.ndarray]:
    """
    Description:
        A region of a shown widget as the window draws it, and the SVG asset rendered directly into an image of the same
        device size on the same ground, filling it as the widget's rectangle is filled.

    Args:
        (1) window [QWidget(object)]: The shown window.
        (2) widget [QWidget(object)]: The widget the logo is drawn in.
        (3) rect [QRect(object)]: The logo's rectangle in the widget, in logical pixels.
        (4) name [string]: The SVG asset.
        (5) opacity [float]: The opacity the widget draws it at.

    Returns:
        (1) parameter [Tuple<Matrix, Matrix>]: (drawn, direct) RGB pixels.
    """

    grab = window.grab(QRect(widget.mapTo(window, rect.topLeft()), rect.size()))
    drawn = _Pixels(grab.toImage())
    ground = window.grab(QRect(widget.mapTo(window, QPoint(widget.width() - 2, 1)), QSize(1, 1)))
    ground = _Pixels(ground.toImage())[0, 0]
    image = QImage(drawn.shape[1], drawn.shape[0], QImage.Format_RGB32)
    image.fill(QColor(*[int(c) for c in ground]))
    painter = QPainter(image)
    painter.setOpacity(opacity)
    renderer = QSvgRenderer(os.path.join(Style.CONST_ASSETS, name))
    box = renderer.viewBoxF()
    renderer.render(painter, QRectF(0, 0, drawn.shape[0] * box.width() / box.height(), drawn.shape[0]))
    painter.end()
    return drawn, _Pixels(image)


def test_the_anyscan_logo_is_rendered_as_vectors_at_its_size(window) -> None:
    """
    Description:
        The lockup's mark and wordmark (its rows above the live tagline) are the wordmark SVG rendered directly at the
        lockup's device size, within CONST_TOLERANCE.
    """

    lockup = window.findChild(Widgets.Logo_Lockup_Cls)
    drawn, direct = _Drawn_And_Direct(window, lockup, QRect(0, 0, lockup.width(), lockup.height()), Style.CONST_LOGO_WORDMARK_FILE)
    rows = int(drawn.shape[0] * 107.5 / 140)
    assert np.abs(drawn[:rows] - direct[:rows]).max() <= CONST_TOLERANCE


def test_the_jic_logo_is_rendered_as_vectors_at_its_size(window) -> None:
    """
    Description:
        The JIC Smart Factory logo is its SVG rendered directly at its device size, within CONST_TOLERANCE.
    """

    jic = window.findChild(QWidget, 'jicLogo')
    drawn, direct = _Drawn_And_Direct(window, jic, QRect(0, 0, jic.width(), jic.height()), 'jic-smart-factory.svg')
    assert np.abs(drawn - direct).max() <= CONST_TOLERANCE


def test_the_empty_camera_view_mark_is_rendered_as_vectors_at_its_size(window) -> None:
    """
    Description:
        The mark in the empty Camera View, at the size and opacity the viewport draws it (the smaller of 210 px and
        0.44 of its width, 0.92), is its SVG rendered directly at that device size, within CONST_TOLERANCE.
    """

    viewport = window.findChild(Widgets.Viewport_Cls)
    size = min(210, int(viewport.width() * 0.44))
    rect = QRect((viewport.width() - size) // 2, viewport.height() // 2 - size // 2 - 20, size, size)
    drawn, direct = _Drawn_And_Direct(window, viewport, rect, 'anyscan-mark.svg', opacity=0.92)
    assert np.abs(drawn - direct).max() <= CONST_TOLERANCE


def test_only_the_funding_bands_raster_logos_are_pixmaps(window) -> None:
    """
    Description:
        No label in the window shows a pixmap but the funding band's three logos, which exist only as PNG: an SVG logo
        set on a label as a pixmap would be a raster again.
    """

    pixmapped = [label for label in window.findChildren(QLabel) if label.pixmap() is not None and not label.pixmap().isNull()]
    band = window.findChild(Widgets.Funding_Row_Cls)
    assert len(pixmapped) == 3 and all(band.isAncestorOf(label) for label in pixmapped)


def test_the_logos_are_checked_again_at_dpr_2(qt_app, project_root) -> None:
    """
    Description:
        This module, run again in a fresh interpreter at DPR 2 (QT_SCALE_FACTOR=2), passes there too.
    """

    if qt_app.devicePixelRatio() >= Style.CONST_LOW_DENSITY_DPR:
        pytest.skip('this is the DPR %g run' % qt_app.devicePixelRatio())
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_SCALE_FACTOR=CONST_HIGH_DENSITY_SCALE, PYTHONDONTWRITEBYTECODE='1')
    run = subprocess.run([sys.executable, '-m', 'pytest', os.path.abspath(__file__), '-rA', '-p', 'no:cacheprovider'],
                         cwd=project_root, env=env, capture_output=True, text=True, timeout=300)
    report = run.stdout + run.stderr
    assert run.returncode == 0, report[-3000:]
    for passed in ('test_the_anyscan_logo_is_rendered_as_vectors_at_its_size',
                   'test_the_jic_logo_is_rendered_as_vectors_at_its_size',
                   'test_the_empty_camera_view_mark_is_rendered_as_vectors_at_its_size',
                   'test_only_the_funding_bands_raster_logos_are_pixmaps'):
        assert 'PASSED test/UI/test_logo_rendering.py::%s' % passed in report, report[-3000:]
