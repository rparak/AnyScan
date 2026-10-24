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
# File Name: ../test/UI/test_pixel_icons.py
## =========================================================================== ##

# System (Default)
import os
import re
# Qt must never open a window during tests: the offscreen platform renders without a display.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QColor, QImage, QRegion
from PyQt5.QtWidgets import QApplication, QLabel, QWidget
# Custom Lib.: AnyScan UI — the window, the icon widget and state marker, the one set of pixel icons, the style tokens
#   ../UI/Core, ../UI/Widgets, ../UI/Utilities/Pixel_Motif, ../UI/Utilities/Style
from UI.Core import AnyScan_Window_Cls
from UI.Widgets import Icon_Cls, State_Marker_Cls
from UI.Utilities.Pixel_Motif import CONST_PIXEL_ICONS
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan — the camera and the configuration layer the window is built from
#   ../Camera/Core, ../Configuration/Core
from Camera.Core import File_Camera_Cls
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Every icon is a pixel icon from one set (design-decisions.md, "Every icon is a pixel icon from one set"): the
    application's heads, its model pill and state markers and the README's architecture diagram all draw
    UI.Utilities.Pixel_Motif.CONST_PIXEL_ICONS, each icon at a whole number of pixels a cell, so it stays crisp. Measured
    on what is painted: the window's grabs and the committed SVG.
"""
# The icon each head and the model pill draw, by the head's title (the pill by its object name): the meaning the
# owner approved, 2026-10-18.
#   Unit [Dict<string, string>]
CONST_EXPECTED = {'Camera View': 'camera', 'Scene Understanding': 'text', 'Detected objects': 'magnifier',
                  'Confidence': 'gauge', 'Captures': 'folder', 'Capture set': 'image', 'Session log': 'log',
                  'Configuration': 'gear', 'modelPill': 'model'}
# The icons the architecture diagram's cards carry.
#   Unit [Set<string>]
CONST_DIAGRAM_ICONS = {'camera', 'magnifier', 'text', 'ruler', 'focus', 'area', 'checklist', 'badge', 'window', 'gear',
                       'station', 'target', 'catalogue', 'image', 'folder'}
# The committed diagram, and the drawn size of its icons' cells.
#   Unit [string] / [px]
CONST_DIAGRAM = os.path.join(os.path.dirname(__file__), '..', '..', 'images', 'anyscan-architecture.svg')
CONST_DIAGRAM_CELL = 3
# The window's configuration: the shipped one, without a scale.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Rgb(image: QImage) -> np.ndarray:
    """An image as an RGB array of its device pixels."""
    image = image.convertToFormat(QImage.Format_RGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    array = np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)
    return array[:, :image.width(), 2::-1].astype(int)


def _Hex(token: str) -> np.ndarray:
    """A '#rrggbb' token as an RGB array."""
    return np.array([int(token[i:i + 2], 16) for i in (1, 3, 5)])


def _Grid(name: str, lit: str = '#') -> np.ndarray:
    """An icon of the shared set as a boolean array of its cells, True where its mark is one of `lit`."""
    return np.array([[mark in lit for mark in line] for line in CONST_PIXEL_ICONS[name]])


def _Ink(pixels: np.ndarray, token: str) -> np.ndarray:
    """Where the pixels are exactly a token's colour."""
    return (pixels == _Hex(token)).all(axis=2)


def test_every_icon_in_the_window_comes_from_the_shared_set(qt_app, reference_background_path) -> None:
    """
    Description:
        Every icon the window and its configuration dialog show is an Icon_Cls of the shared set, the one the owner
        approved for its place (CONST_EXPECTED, and none more), and is painted as that set draws it: the grabbed icon's
        purple pixels are the set's '#' cells at its cell size. The state markers' icons are the set's too: SCANNING…
        paints the camera's cells and ANALYZING… the magnifier's, in white at their cell size.
    """

    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(reference_background_path))
    dialog = getattr(window, '_AnyScan_Window_Cls__Make_Configuration_Dialog')()
    window.show()
    dialog.show()
    shown = {}
    for icon in window.findChildren(Icon_Cls):
        owner = icon.parentWidget()
        titles = [label.text() for label in owner.findChildren(QLabel, options=Qt.FindDirectChildrenOnly)
                  if label.text() in CONST_EXPECTED]
        place = owner.objectName() if owner.objectName() in CONST_EXPECTED else titles[0]
        assert place not in shown, place
        shown[place] = icon.Name()
        cell = icon.width() // 12
        pixels = _Rgb(icon.grab().toImage())
        color = Style.CONST_INK_MUTE if place == 'modelPill' else Style.CONST_INK
        expected = np.kron(_Grid(icon.Name()), np.ones((cell, cell), dtype=bool))
        assert np.array_equal(_Ink(pixels, color), expected), place
    assert shown == CONST_EXPECTED
    for state, kind in (('scan', 'camera'), ('analysis', 'magnifier')):
        marker = State_Marker_Cls()
        marker.Set_State(state)
        marker.show()
        cell = State_Marker_Cls.CONST_ICON_CELL
        pixels = _Rgb(marker.grab().toImage())[:, :State_Marker_Cls.CONST_PAD_X + 12 * cell]
        ys, xs = np.nonzero(_Ink(pixels, Style.CONST_ON_INK))
        lit = _Grid(kind, '#1')                                       # step 1's cells are lit at the first tick
        rows, columns = np.nonzero(lit)
        lit = lit[rows.min():rows.max() + 1, columns.min():columns.max() + 1]
        drawn = _Ink(pixels, Style.CONST_ON_INK)[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        assert np.array_equal(drawn, np.kron(lit, np.ones((cell, cell), dtype=bool))), state
        marker.close()
    dialog.close()
    window.close()


def test_every_icon_is_crisp_at_1x_and_at_a_device_pixel_ratio_of_2(qt_app) -> None:
    """
    Description:
        Every icon of the shared set, at the heads' cell and at the model pill's, paints only two colours, its ground
        and its purple (no antialiased edge), and its purple pixels are exactly its cells as whole squares: at 1x the
        cell's side in pixels, at a device pixel ratio of 2 twice it.
    """

    for cell in (Icon_Cls.CONST_HEAD_CELL, 1):
        for name in CONST_PIXEL_ICONS:
            icon = Icon_Cls(name, cell)
            for ratio in (1, 2):
                image = QImage(icon.width() * ratio, icon.height() * ratio, QImage.Format_ARGB32_Premultiplied)
                image.setDevicePixelRatio(ratio)
                image.fill(QColor(Style.CONST_CARD))
                icon.render(image, QPoint(), QRegion(), QWidget.DrawChildren)     # the icon alone, no window ground
                pixels = _Rgb(image)
                ink = _Ink(pixels, Style.CONST_INK)
                assert (ink | _Ink(pixels, Style.CONST_CARD)).all(), (name, cell, ratio)
                side = cell * ratio
                assert np.array_equal(ink, np.kron(_Grid(name), np.ones((side, side), dtype=bool))), (name, cell, ratio)
            icon.close()


def test_the_diagram_draws_its_icons_from_the_shared_set() -> None:
    """
    Description:
        Each icon in the committed architecture diagram (one crisp-edged path of 3 px squares) is one of the shared
        set's icons, cell for cell, and the diagram carries the fifteen its cards name: the README's figure and the
        application cannot draw two versions of one icon.
    """

    with open(CONST_DIAGRAM, 'r', encoding='utf-8') as handle:
        paths = re.findall(r'<path d="([^"]+)" fill="[^"]+" shape-rendering="crispEdges"/>', handle.read())
    shapes = {}
    for name in CONST_PIXEL_ICONS:
        rows, columns = np.nonzero(_Grid(name))
        shapes[frozenset(zip(columns - columns.min(), rows - rows.min()))] = name
    drawn = []
    for path in paths:
        corners = [(float(x), float(y)) for x, y in re.findall(r'M([\d.]+) ([\d.]+) ', path)]
        left, top = min(x for x, _ in corners), min(y for _, y in corners)
        cells = frozenset((round((x - left) / CONST_DIAGRAM_CELL), round((y - top) / CONST_DIAGRAM_CELL))
                          for x, y in corners)
        assert cells in shapes, 'a diagram icon is not in the shared set: %s' % path[:60]
        drawn.append(shapes[cells])
    assert sorted(drawn) == sorted(CONST_DIAGRAM_ICONS)
