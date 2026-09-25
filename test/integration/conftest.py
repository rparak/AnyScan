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
# File Name: ../test/integration/conftest.py
## =========================================================================== ##

# Dataclasses (the shipped configuration, unscaled)
import dataclasses
# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the real vision pipeline and the configuration layer
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Shared fixtures for the pipeline integration tests. The path and image fixtures come from
    the top-level test/conftest.py; this adds the REAL pipeline run without weights — the
    model-free describer, and a FastSAM stand-in that finds nothing, so the objects come from the
    real background cue and every other stage (fusion, crops, description, composition,
    measurement) is the application's own — and a synthetic frame on disk for a file camera.
"""
# Two rectangles drawn onto the reference: a synthetic frame with two real objects.
#   Unit [Vector<Tuple<int> 1x4>]
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]


class _No_Masks_Segmenter_Cls(object):
    """A FastSAM stand-in that loads nothing and returns no masks: stage 2 contributes no cue."""

    def __init__(self, Segmentation_Parameters_Str: tp.Any) -> None:
        self.params = Segmentation_Parameters_Str

    @property
    def Loaded(self) -> bool:
        return True

    @property
    def Model_Key(self) -> tp.Tuple[str, str]:
        return (self.params.Model_Path, self.params.Device)

    def Set_Parameters(self, Segmentation_Parameters_Str: tp.Any) -> None:
        self.params = Segmentation_Parameters_Str

    def Load(self, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        pass

    def Release(self) -> None:
        pass

    def Segment(self, image: tp.Any, stage_cb: tp.Optional[tp.Callable] = None) -> tp.Tuple[list, list]:
        return [], []


@pytest.fixture
def model_free_backend(monkeypatch: pytest.MonkeyPatch) -> Vision_Pipeline_Cls:
    """
    Description:
        The real Vision_Pipeline_Cls on the shipped configuration (unscaled), with no weights: the
        model-free describer and a FastSAM stand-in that returns no masks.

    Returns:
        (1) parameter [Vision_Pipeline_Cls(object)]: The pipeline.
    """

    monkeypatch.setattr(Vision_Core, 'Fast_Sam_Cls', _No_Masks_Segmenter_Cls)
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    config = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
    return Vision_Pipeline_Cls(Configuration_Str=config)


@pytest.fixture
def synthetic_rects() -> tp.List[tp.Tuple[int, int, int, int]]:
    """
    Description:
        The two rectangles drawn on the synthetic frame, as (x1, y1, x2, y2), left to right.

    Returns:
        (1) parameter [Vector<Tuple<int> 1x4>]: The rectangles.
    """

    return list(CONST_RECTS)


@pytest.fixture
def synthetic_frame_path(tmp_path: tp.Any, reference_background: tp.Any,
                         make_synthetic_frame: tp.Callable) -> str:
    """
    Description:
        The reference with the two CONST_RECTS drawn on it, written as a PNG a File_Camera_Cls can
        capture.

    Returns:
        (1) parameter [string]: The frame's path.
    """

    path = str(tmp_path / 'synthetic_frame.png')
    cv2.imwrite(path, make_synthetic_frame(reference_background, CONST_RECTS))
    return path
