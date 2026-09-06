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
# File Name: ../test/integration/conftest.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the vision interface, the composer, the structures
#   ../Vision/Core
from Vision.Core import Vision_Backend_Cls
#   ../Reporting/Core
from Reporting.Core import Compose, Verdict
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str

"""
Description:
    Shared fixtures for the pipeline integration tests. The path and image fixtures
    come from the top-level test/conftest.py; this adds the hermetic fake vision
    backend used to exercise the camera -> vision -> reporting seams without the
    Florence-2 weights.
"""


class Fake_Vision_Cls(Vision_Backend_Cls):
    """
    Description:
        A hermetic stand-in for the model that implements the Vision_Backend_Cls
        interface. It returns a fixed set of detections and composes them through
        the REAL Reporting, so a test exercises the camera -> vision contract and
        the vision -> reporting seam without loading any weights.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Fake_Vision_Cls()

            Features:
                # Functions of the class.
                Cls.Analyze(image_rgb)
    """

    Name = 'Fake-Vision'

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
        """
        Description:
            Accept the camera's RGB ndarray directly (the contract), attach fixed
            detections, and compose the reading through Reporting.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The captured frame (RGB ndarray).
            (2) progress_cb [function]: Optional (done, total) hook.
            (3) stage_cb [function]: Optional (text) hook.

        Returns:
            (1) parameter [Analysis_Str(object)]: The composed reading.
        """

        # The camera -> vision contract: a contiguous RGB ndarray arrives directly,
        # no QImage in sight.
        assert hasattr(image, 'shape') and image.ndim == 3 and image.shape[2] == 3
        size = (image.shape[1], image.shape[0])

        if stage_cb:
            stage_cb('Analysing…')
        objects = [
            Detection_Str(Label='hex bolt', Bbox=(10, 20, 60, 60),
                          Detail='In this image we can see a hex bolt on a green surface.'),
            Detection_Str(Label='washer', Bbox=(200, 120, 50, 50),
                          Detail='A metal washer.', Confidence=0.2),
        ]
        objects, summary, note = Compose(objects, size)
        badge, level = Verdict(objects)
        if progress_cb:
            progress_cb(len(objects), len(objects))
        return Analysis_Str(Summary=summary, Objects=objects, Note=note,
                            Verdict=badge, Verdict_Level=level, Task='fake')


@pytest.fixture
def fake_backend() -> Fake_Vision_Cls:
    """
    Description:
        A ready fake vision backend for the wiring tests.

    Returns:
        (1) parameter [Fake_Vision_Cls(object)]: The fake backend.
    """

    return Fake_Vision_Cls()
