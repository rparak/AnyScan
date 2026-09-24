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
# File Name: ../test/Vision/test_core.py
## =========================================================================== ##

# System (Default)
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — vision backend and result structure
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Backend_Cls, Vision_Pipeline_Cls, Vision_Error_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str

"""
Description:
    Tests for the vision backend. The interface, the constants and the Qt-freeness
    are checked without the model. The full Analyze path needs the FastSAM and Gemma
    weights, so it is marked `slow` and skipped by default (and skips anyway when
    the weights are not present).
"""


def test_backend_interface() -> None:
    """
    Description:
        Vision_Pipeline_Cls is a Vision_Backend_Cls; the base Analyze is abstract;
        the presented name is the model name.
    """

    assert issubclass(Vision_Pipeline_Cls, Vision_Backend_Cls)
    assert Vision_Pipeline_Cls.Name == Vision_Core.CONST_MODEL_NAME
    with pytest.raises(NotImplementedError):
        Vision_Backend_Cls().Analyze(None)


def test_config_paths_point_where_expected() -> None:
    """
    Description:
        Each describer's model directory, its prompts file and the background reference
        resolve to their repo locations, so a moved file fails loudly rather than silently;
        Gemma is the default describer.
    """

    import Vision.Describers as Describers
    from Camera.Utilities.Configuration import CONST_DESCRIBER_PROMPTS_FILE
    assert Vision_Core.CONST_DESCRIBER == 'gemma'
    assert Describers.CONST_GEMMA_MODEL_DIR.endswith(os.path.join('models', 'gemma-4-e4b-it-4bit'))
    assert set(Describers.CONST_DESCRIBERS) == {'gemma'}
    assert CONST_DESCRIBER_PROMPTS_FILE.endswith(os.path.join('Configuration', 'Describer_Prompts.yaml'))
    assert Vision_Core.CONST_BACKGROUND_REF.endswith(
        os.path.join('Data', 'Camera', 'Image_Background_001.png'))


def test_module_is_qt_free() -> None:
    """
    Description:
        The backend imports no Qt — the separation the migration was for. Analyze
        takes an ndarray image, never a QImage.
    """

    source = open(Vision_Core.__file__).read()
    # No Qt import anywhere (the word QImage may still appear in prose describing
    # the UI boundary; what matters is that nothing imports or constructs it).
    assert 'import PyQt' not in source and 'from PyQt' not in source
    assert 'QImage(' not in source


@pytest.mark.slow
def test_analyze_end_to_end(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The full pipeline on a synthetic frame (the reference with two rectangles
        drawn on it): Analyze takes an RGB array and returns a populated
        Analysis_Str. Needs the default describer's weights; skipped otherwise.
    """

    import Vision.Describers as Describers
    if not os.path.isdir(Describers.CONST_GEMMA_MODEL_DIR):
        pytest.skip(f'model weights not present at {Describers.CONST_GEMMA_MODEL_DIR}')

    import cv2

    rects = [(300, 300, 560, 560), (1200, 700, 1480, 980)]
    frame_bgr = make_synthetic_frame(reference_background, rects)
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    result = Vision_Pipeline_Cls(scale=None).Analyze(image_rgb)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == 2
    assert result.Latency_Ms >= 0
