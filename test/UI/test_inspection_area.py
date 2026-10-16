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
# File Name: ../test/UI/test_inspection_area.py

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window and the Camera View's viewport
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Widgets
from UI.Widgets import Viewport_Cls
# Custom Lib.: AnyScan — the camera, the theme, the configuration layer
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Parameters/Theme
import Parameters.Theme as Theme
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Mode_Directory, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The Camera View's inspection area, read from rendered pixels: a catalogue mode's rectangle is drawn over the empty
    state, the scanned frame and the annotated result, never over the mask, and never into the images the analysis
    produces (they go to the logger as they are); a mode without a catalogue (Segment Anything) draws none.
"""

# The frame's size and an area on it (the shipped insets at 0.1 mm/px: 130 px from the left and right, 100 from the
# top and bottom), and the viewport's size: half the frame, so the area's left edge is at x 65 and its top at y 50.
CONST_FRAME = (1920, 1200)
CONST_AREA = (130.0, 100.0, 1789.0, 1099.0)
CONST_VIEW = (960, 600)
# The catalogue mode file the window is built with for the area.
CONST_CATALOGUE_MODE_FILE = 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml'


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Grab(widget) -> np.ndarray:
    """What the widget paints now, as an HxWx3 BGR array (the pixels, not its state)."""
    QApplication.instance().processEvents()
    image = widget.grab().toImage().convertToFormat(QImage.Format_RGB32)
    pointer = image.constBits()
    pointer.setsize(image.byteCount())
    return np.frombuffer(pointer, np.uint8).reshape(image.height(), image.bytesPerLine() // 4, 4)[:, :, :3].copy()


def _Line(pixels: np.ndarray) -> np.ndarray:
    """Where the pixels are the area's colour, within a blend of its antialiased edge, as a bool HxW map."""
    r, g, b = Theme.Hex_To_Rgb(Theme.CONST_INSPECTION_AREA)
    return (np.abs(pixels.astype(int) - np.array([b, g, r])) <= 45).all(axis=2)


def _Area_Drawn(pixels: np.ndarray, left: int, top: int, right: int, bottom: int) -> bool:
    """Whether the area's four edges are drawn, solid, where they belong (within a pixel), and nothing else."""
    line = _Line(pixels)
    edges = [line[top - 1:top + 2, left:right + 1].any(axis=0), line[bottom - 1:bottom + 2, left:right + 1].any(axis=0),
             line[top:bottom + 1, left - 1:left + 2].any(axis=1), line[top:bottom + 1, right - 1:right + 2].any(axis=1)]
    inner = line[top + 3:bottom - 2, left + 3:right - 2]
    return all(edge.mean() > 0.98 for edge in edges) and not inner.any()


def _Viewport(area: tp.Any) -> Viewport_Cls:
    """A viewport of CONST_VIEW, showing the area given (or none)."""
    viewport = Viewport_Cls()
    viewport.resize(*CONST_VIEW)
    viewport.Set_Inspection_Area(area)
    return viewport


def _Image(bgr: tp.Tuple[int, int, int]) -> QImage:
    """A frame of CONST_FRAME in one colour."""
    pixels = np.full((CONST_FRAME[1], CONST_FRAME[0], 4), 255, np.uint8)
    pixels[:, :, :3] = bgr
    return QImage(pixels.data, CONST_FRAME[0], CONST_FRAME[1], CONST_FRAME[0] * 4, QImage.Format_RGB32).copy()


def test_the_area_is_drawn_on_the_empty_view_the_scanned_frame_and_the_annotated_result_only(qt_app) -> None:
    """
    Description:
        With an area set, the viewport draws it as a thin solid rectangle with square corners and no fill where it lies
        on the letterboxed frame: over the empty state (before any scan), over a scanned frame (the green table) and
        over the annotated result, but not over the mask. Without one it draws none.
    """

    left, top, right, bottom = 65, 50, 895, 550
    viewport = _Viewport((CONST_FRAME, CONST_AREA))
    assert _Area_Drawn(_Grab(viewport), left, top, right, bottom)
    table = _Image((80, 101, 23))
    viewport.Show_Frame(table)
    assert _Area_Drawn(_Grab(viewport), left, top, right, bottom)
    viewport.Show_Views(_Image((80, 101, 23)), _Image((0, 0, 0)), 'annotated', heatmap=None, legend=None)
    assert _Area_Drawn(_Grab(viewport), left, top, right, bottom)
    viewport.Set_View('mask')
    assert not _Line(_Grab(viewport)).any()
    viewport.Set_View('annotated')
    viewport.Set_Inspection_Area(None)
    assert not _Line(_Grab(viewport)).any()


def test_the_area_is_painted_on_the_screen_never_into_the_analysis_images(qt_app) -> None:
    """
    Description:
        The area is painted over the held images at paint time: the annotated image the viewport holds, which is the
        one handed to the capture writer, carries none of it where the screen shows it.
    """

    viewport = _Viewport((CONST_FRAME, CONST_AREA))
    annotated = _Image((80, 101, 23))
    viewport.Show_Views(annotated, _Image((0, 0, 0)), 'annotated', heatmap=None, legend=None)
    assert _Area_Drawn(_Grab(viewport), 65, 50, 895, 550)
    held = getattr(viewport, '_Viewport_Cls__annotated').convertToFormat(QImage.Format_RGB32)
    pointer = held.constBits()
    pointer.setsize(held.byteCount())
    pixels = np.frombuffer(pointer, np.uint8).reshape(CONST_FRAME[1], CONST_FRAME[0], 4)[:, :, :3]
    assert not _Line(pixels).any()


@pytest.mark.parametrize('mode_file, shown', [(CONST_CATALOGUE_MODE_FILE, True),
                                             (os.path.basename(CONST_DEFAULT_CONFIG_FILE), False)],
                         ids=['catalogue', 'segment-anything'])
def test_a_catalogue_mode_shows_its_stations_area_and_segment_anything_none(qt_app, reference_background_path,
                                                                             mode_file: str, shown: bool) -> None:
    """
    Description:
        The window puts a catalogue mode's area in force from its station's insets at its scale, so the empty Camera
        View already shows where to place parts; Segment Anything, which judges nothing, shows none.
    """

    from Vision.Utilities.Classify import Inspection_Area_Px
    config = Load_Configuration(os.path.join(Mode_Directory(), mode_file))
    window = AnyScan_Window_Cls(Configuration_Str=config, camera=File_Camera_Cls(reference_background_path))
    viewport = getattr(window, '_AnyScan_Window_Cls__viewport')
    area = getattr(viewport, '_Viewport_Cls__area')
    if not shown:
        assert area is None and not _Line(_Grab(viewport)).any()
        return
    inset = config.Inspection_Area
    expected = Inspection_Area_Px(CONST_FRAME, config.Scale, inset.Long_Edge_Inset_Mm, inset.Short_Edge_Inset_Mm)
    assert area == (CONST_FRAME, expected)
    pixels = _Grab(viewport)
    scale = min(pixels.shape[1] / CONST_FRAME[0], pixels.shape[0] / CONST_FRAME[1])
    x0, y0 = int((pixels.shape[1] - CONST_FRAME[0] * scale) / 2), int((pixels.shape[0] - CONST_FRAME[1] * scale) / 2)
    left, top, right, bottom = expected
    assert _Area_Drawn(pixels, int(round(x0 + left * scale)), int(round(y0 + top * scale)),
                       int(round(x0 + right * scale)), int(round(y0 + bottom * scale)))
