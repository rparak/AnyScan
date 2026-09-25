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
#   ../Configuration/Core
import Configuration.Core as Configuration
#   ../Vision/Utilities/Annotate
import Vision.Utilities.Annotate as Annotate
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Parameters/Theme
from Parameters.Theme import Verdict_Color, Detection_Color, Hex_To_Bgr
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The validation harness must render exactly what the application renders: analyze.py is the
    validator of the logic the app uses. Both now render through ONE function,
    Vision.Utilities.Annotate.Render_Views, so the renderers cannot drift apart; what can still go
    wrong is what once did — a path passing the wrong mode (the harness drew verdict colours on a
    detect-only run) — or a path drawing around the shared function. So these tests hold: that
    neither path draws except through Render_Views; that the mask the WINDOW writes to disk is the
    shared render for its configuration's flag, and so is the mask the HARNESS writes, run end to
    end from a configuration file, for both flag values; that the harness reads its configuration
    through the app's own layer; and that no renderer can be called without stating the mode.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

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


class _Loaded_Vision_Cls(object):
    """A stand-in vision backend whose models are already loaded; it is never asked to analyse."""
    Name, Models_Loaded, Model_Names = 'JIC-AnyScan-v1', True, ('FastSAM-x.pt', 'gemma')


def _Ui_Written_Mask(reference_background_path: str, log_dir: str,
                     classification_enabled: bool) -> np.ndarray:
    """The label mask the WINDOW writes to its capture set for one analysis (BGR, as on disk)."""
    app = QApplication.instance()
    logger = Session_Logger_Cls(config_path=None, log_dir=log_dir, install_handlers=False)
    configuration = dataclasses.replace(CONST_CONFIGURATION, Classification_Enabled=classification_enabled)
    window = AnyScan_Window_Cls(Configuration_Str=configuration, camera=File_Camera_Cls(reference_background_path),
                                logger=logger)
    private = lambda name: getattr(window, CONST_MANGLE + name)
    # The analysis is injected below, so no model runs: a stand-in pipeline reports its models
    # loaded, and CONNECT goes straight to the camera instead of loading ~9 GB of weights.
    setattr(window, CONST_MANGLE + '__vision', _Loaded_Vision_Cls())
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


def _Harness_Written_Mask(monkeypatch, tmp_path, reference_background_path: str,
                          classification_enabled: bool) -> np.ndarray:
    """
    The label mask the HARNESS writes for one frame, run end to end through analyze.main() from a
    configuration file whose classification flag is set — with a stand-in pipeline, so no model
    runs — cropped of its provenance footer (BGR, as rendered).
    """

    import yaml
    hardware = CONST_CONFIGURATION.Hardware
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    data['General']['Classification']['Enabled'] = classification_enabled
    config_dir = tmp_path / 'Configuration'
    config_dir.mkdir()
    config_path = config_dir / os.path.basename(CONST_DEFAULT_CONFIG_FILE)
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    calibration = Configuration.Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, hardware)
    with open(calibration, 'r', encoding='utf-8') as handle:
        (config_dir / os.path.basename(calibration)).write_text(handle.read(), encoding='utf-8')
    frames = tmp_path / 'frames'
    frames.mkdir()
    scene = cv2.imread(reference_background_path)
    cv2.imwrite(str(frames / 'Image_001.png'), scene)

    class _Stand_In_Pipeline_Cls(object):
        """The pipeline, stood in: it returns the one known object and runs no model."""

        def __init__(self, Configuration_Str) -> None:
            pass

        def Analyze(self, image):
            return Analysis_Str(Objects=_Objects(image.shape), Latency_Ms=1, Verdict='1 found',
                                Verdict_Level='ok', Task='caption', Background='A surface.')

    monkeypatch.setattr(analyze, 'Vision_Pipeline_Cls', _Stand_In_Pipeline_Cls)
    out = tmp_path / 'out'
    monkeypatch.setattr('sys.argv', ['analyze.py', '--config', str(config_path), '--input-dir', str(frames),
                                     '--output-dir', str(out)])
    assert analyze.main() == 0
    written = cv2.imread(str(out / 'Image_001_mask.png'))
    return written[:scene.shape[0]]                              # the footer band is below the frame


@pytest.mark.parametrize('classification_enabled', [False, True])
def test_the_window_writes_the_shared_render_for_its_flag(qt_app, reference_background_path, tmp_path,
                                                          classification_enabled) -> None:
    """
    Description:
        The mask the window writes to its capture set is exactly Render_Views' mask for the
        configuration's flag — the neutral tint when classification is off, the OK tint when on:
        the window passes its configuration's mode, and the writer stores the render unchanged.
    """

    ui_mask = _Ui_Written_Mask(reference_background_path, str(tmp_path), classification_enabled)
    scene = cv2.imread(reference_background_path)
    _annotated, shared = Annotate.Render_Views(scene, _Objects(scene.shape), cv2, np,
                                               verdict_colored=classification_enabled)

    expected = Verdict_Color('OK')[2] if classification_enabled else Detection_Color()[2]
    row, col = CONST_SAMPLE
    assert tuple(int(c) for c in ui_mask[row, col]) == Hex_To_Bgr(expected)
    assert np.array_equal(ui_mask, shared)


@pytest.mark.parametrize('classification_enabled', [False, True])
def test_the_harness_writes_the_shared_render_for_the_configurations_flag(monkeypatch, tmp_path,
                                                                           reference_background_path,
                                                                           classification_enabled) -> None:
    """
    Description:
        Run end to end from a configuration file, the harness writes exactly Render_Views' mask for
        that configuration's flag — the mode the harness once got wrong (verdict colours on a
        detect-only run) is read from the configuration, not chosen by the harness.
    """

    harness_mask = _Harness_Written_Mask(monkeypatch, tmp_path, reference_background_path, classification_enabled)
    scene = cv2.imread(reference_background_path)
    _annotated, shared = Annotate.Render_Views(scene, _Objects(scene.shape), cv2, np,
                                               verdict_colored=classification_enabled)

    expected = Verdict_Color('OK')[2] if classification_enabled else Detection_Color()[2]
    row, col = CONST_SAMPLE
    assert tuple(int(c) for c in harness_mask[row, col]) == Hex_To_Bgr(expected)
    assert np.array_equal(harness_mask, shared)


def test_the_window_and_the_harness_draw_only_through_render_views() -> None:
    """
    Description:
        Parity holds by construction only while both paths render through the one shared function:
        neither the window nor the harness calls Draw_Annotated or Draw_Label_Mask itself, and each
        calls Render_Views.
    """

    import ast
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for relative in (os.path.join('src', 'UI', 'Core.py'), os.path.join('Example', 'Vision', 'analyze.py')):
        with open(os.path.join(root, relative), 'r', encoding='utf-8') as handle:
            tree = ast.parse(handle.read())
        called = {node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
                  for node in ast.walk(tree) if isinstance(node, ast.Call)}
        assert not called & {'Draw_Annotated', 'Draw_Label_Mask'}, '%s draws around Render_Views' % relative
        assert 'Render_Views' in called, '%s does not render through Render_Views' % relative


def test_harness_loads_its_configuration_through_the_application_config_layer() -> None:
    """
    Description:
        The harness loads its configuration — the classification flag, the stage parameters, the
        scale — through the SAME function and the SAME default file as the application launcher:
        not a copy, and not a default.
    """

    assert analyze.Load_Configuration is Configuration.Load_Configuration
    assert analyze.CONST_DEFAULT_CONFIG_FILE == Configuration.CONST_DEFAULT_CONFIG_FILE


def test_renderers_cannot_be_called_without_stating_the_mode() -> None:
    """
    Description:
        verdict_colored has no default and is keyword-only, so a caller that never read the
        configuration fails at the call site instead of silently rendering one mode, and a bare
        positional True/False cannot be passed without naming what it means.
    """

    scene = np.zeros((40, 60, 3), np.uint8)
    with pytest.raises(TypeError):
        Annotate.Render_Views(scene, [], cv2, np)
    with pytest.raises(TypeError):
        Annotate.Render_Views(scene, [], cv2, np, False)
    with pytest.raises(TypeError):
        Annotate.Draw_Annotated(scene, [], cv2, np)
    with pytest.raises(TypeError):
        Annotate.Draw_Label_Mask([], scene.shape, cv2, np)
    with pytest.raises(TypeError):
        Annotate.Draw_Annotated(scene, [], cv2, np, False)
    with pytest.raises(TypeError):
        Annotate.Draw_Label_Mask([], scene.shape, cv2, np, False)
