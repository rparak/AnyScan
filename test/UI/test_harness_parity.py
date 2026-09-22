## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../test/UI/test_harness_parity.py
## =========================================================================== ##

# System (Default)
import os
import glob
import time
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: the validation harness (Example/Vision is on the import path)
#   ../Example/Vision/analyze
import analyze
# Custom Lib.: AnyScan UI, logger, camera, configuration layer, renderer and structures
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Camera/Utilities/Configuration
import Camera.Utilities.Configuration as Configuration
#   ../Vision/Utilities/Annotate
import Vision.Utilities.Annotate as Annotate
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Parameters/Theme
from Parameters.Theme import Verdict_Color, Detection_Color, Hex_To_Bgr

"""
Description:
    The validation harness must render exactly what the application renders: analyze.py is the
    validator of the logic the app uses, so a harness drawing in a different mode (it drew verdict
    colours on a detect-only run) would be that guarantee quietly breaking. These tests hold the
    harness's render path against the mask the WINDOW actually writes, for both flag values; that
    the harness reads the flag through the app's own configuration layer; and that the renderers
    cannot be called without stating the mode.
"""

# The window's name-mangling prefix, for reaching its private state.
CONST_MANGLE = '_AnyScan_Window_Cls'
# The synthetic object's box (x, y, w, h) on the reference frame, and a pixel well inside it
# (clear of the box stroke and the index chip) where the fill is sampled.
CONST_BOX = (400, 300, 360, 260)
CONST_SAMPLE = (430, 580)          # (row, col)


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


def _Objects(shape) -> list:
    """One OK object with a filled mask over CONST_BOX, on a frame of the given shape."""
    x, y, w, h = CONST_BOX
    mask = np.zeros(shape[:2], dtype=bool)
    mask[y:y + h, x:x + w] = True
    return [Detection_Str(Label='p', Bbox=CONST_BOX, Mask=mask, Cue='both', Verdict='OK',
                          Segmenter_Score=0.9, Sentence='A part.')]


def _Ui_Written_Mask(reference_background_path: str, log_dir: str,
                     classification_enabled: bool) -> np.ndarray:
    """The label mask the WINDOW writes to its capture set for one analysis (BGR, as on disk)."""
    app = QApplication.instance()
    logger = Session_Logger_Cls(config_path=None, log_dir=log_dir, install_handlers=False)
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference_background_path), logger=logger,
                                classification_enabled=classification_enabled)
    private = lambda name: getattr(window, CONST_MANGLE + name)
    private('__On_Connect_Button_Clicked')()
    deadline = time.time() + 10
    while private('__conn_thread') is not None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)
    private('__On_Scan_Button_Clicked')()
    app.processEvents()
    setattr(window, CONST_MANGLE + '__current_set_id', 'parity_1')
    frame_shape = private('__frame').shape
    private('__On_Analysis_Finished')(Analysis_Str(Objects=_Objects(frame_shape), Latency_Ms=100,
                                                   Verdict='1 found', Verdict_Level='ok',
                                                   Task='caption', Background='A surface.'))
    app.processEvents()
    logger.Close()
    written = glob.glob(os.path.join(log_dir, 'captures', '*', 'parity_1_mask.png'))
    assert len(written) == 1, 'the window wrote no mask for the set'
    return cv2.imread(written[0])


@pytest.mark.parametrize('classification_enabled', [False, True])
def test_harness_mask_fill_matches_the_window_for_the_same_flag(qt_app, reference_background_path,
                                                                tmp_path, classification_enabled) -> None:
    """
    Description:
        For the same flag value, the harness's render path fills the object with the SAME colour
        as the mask the window writes — the neutral tint when classification is off, the OK tint
        when it is on — and the two whole masks are identical, not merely similar.
    """

    ui_mask = _Ui_Written_Mask(reference_background_path, str(tmp_path), classification_enabled)
    scene = cv2.imread(reference_background_path)
    _annotated, harness_mask = analyze.Render_Views(scene, _Objects(scene.shape),
                                                    classification_enabled)

    expected = Verdict_Color('OK')[2] if classification_enabled else Detection_Color()[2]
    row, col = CONST_SAMPLE
    assert tuple(int(c) for c in harness_mask[row, col]) == Hex_To_Bgr(expected)
    assert tuple(int(c) for c in ui_mask[row, col]) == Hex_To_Bgr(expected)
    assert np.array_equal(harness_mask, ui_mask)


def test_harness_reads_the_flag_through_the_application_config_layer() -> None:
    """
    Description:
        The harness reads General.Classification.Enabled through the SAME function and the SAME
        default configuration file as the application launcher — not a copy, and not a default.
    """

    assert analyze.Read_Classification_Enabled is Configuration.Read_Classification_Enabled
    assert analyze.CONST_BASLER_CONFIG_FILE == Configuration.CONST_BASLER_CONFIG_FILE


def test_renderers_cannot_be_called_without_stating_the_mode() -> None:
    """
    Description:
        verdict_colored has no default and is keyword-only, so a caller that never read the
        configuration fails at the call site instead of silently rendering one mode, and a bare
        positional True/False cannot be passed without naming what it means.
    """

    scene = np.zeros((40, 60, 3), np.uint8)
    with pytest.raises(TypeError):
        Annotate.Draw_Annotated(scene, [], cv2, np)
    with pytest.raises(TypeError):
        Annotate.Draw_Label_Mask([], scene.shape, cv2, np)
    with pytest.raises(TypeError):
        Annotate.Draw_Annotated(scene, [], cv2, np, False)
    with pytest.raises(TypeError):
        Annotate.Draw_Label_Mask([], scene.shape, cv2, np, False)
