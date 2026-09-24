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
# File Name: ../test/integration/test_failure_paths.py
## =========================================================================== ##

# System (Default)
import os
# Dataclasses (a configuration copy pointed at a missing model)
import dataclasses
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the vision backend and its error type
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls, Vision_Error_Cls
# Custom Lib.: AnyScan — the configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The failure paths users actually hit. Both run the real Vision_Pipeline_Cls
    path (loading the runtime), so both are slow. Each asserts the failure surfaces
    as a Vision_Error_Cls with an actionable message, rather than crashing with a
    raw traceback the panel could not print.
"""



def _Configuration() -> tp.Any:
    """The shipped configuration, unscaled — the pipeline runs with the application's parameters."""
    return dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)

@pytest.mark.slow
def test_missing_model_directory_surfaces_cleanly(reference_background) -> None:
    """
    Description:
        A missing/unreadable model directory raises Vision_Error_Cls, not a raw
        library exception. (Point the model dir at a path that does not exist; the
        runtime imports fine but the weights cannot be loaded.)
    """

    import cv2

    image_rgb = cv2.cvtColor(reference_background, cv2.COLOR_BGR2RGB)

    config = _Configuration()
    config = dataclasses.replace(config, Description=dataclasses.replace(
        config.Description, Model_Path='/no/such/model/directory'))
    with pytest.raises(Vision_Error_Cls, match='/no/such/model/directory'):
        Vision_Pipeline_Cls(Configuration_Str=config).Analyze(image_rgb)


@pytest.mark.slow
def test_frame_size_mismatch_surfaces_cleanly(reference_background) -> None:
    """
    Description:
        A frame whose resolution does not match the reference background raises
        Vision_Error_Cls (the size guard in the background subtraction), not a raw
        NumPy broadcast error. Needs the weights, because the size check runs after
        the model has loaded; skipped otherwise.
    """

    config = _Configuration()
    if not os.path.isdir(config.Description.Model_Path):
        pytest.skip(f'model weights not present at {config.Description.Model_Path}')

    # A frame deliberately a different size from the reference background.
    h, w, _ = reference_background.shape
    wrong_size = np.zeros((h // 2, w // 2, 3), dtype=np.uint8)

    with pytest.raises(Vision_Error_Cls):
        Vision_Pipeline_Cls(Configuration_Str=config).Analyze(wrong_size)
