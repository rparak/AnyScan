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
# File Name: ../test/integration/test_pipeline.py
## =========================================================================== ##

# System (Default)
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the camera and vision backends, the result structure
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Florence_Vision_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str

"""
Description:
    End-to-end pipeline integration tests: acquire a frame -> detect -> describe ->
    compose the report, exercising the modules together across their seams. The
    default test is hermetic (a File_Camera_Cls source and a fake backend, no camera
    and no weights); the slow test runs the same flow through the real Florence-2.
"""

# Two rectangles drawn onto the reference to synthesize a frame with real objects.
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]


def test_pipeline_camera_to_reporting(reference_background_path, fake_backend) -> None:
    """
    Description:
        The full wiring with the hermetic fake backend: File_Camera_Cls captures an
        RGB frame, the backend accepts it directly, and the reading is composed
        through the real Reporting. Asserts the seams — the composed sentences (the
        fake's Florence-style detail is cleaned by Reporting) and the verdict from
        the low-confidence object.
    """

    camera = File_Camera_Cls(reference_background_path)
    camera.Connect()
    frame = camera.Capture()

    result = fake_backend.Analyze(frame)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == 2
    # Reporting composed each sentence, stripping the Florence lead-in.
    assert result.Objects[0].Sentence == 'A hex bolt on a green surface.'
    assert all(o.Sentence for o in result.Objects)
    assert result.Summary == 'The frame contains two objects, which are described as follows:'
    # The 0.2-confidence object drives the verdict.
    assert (result.Verdict, result.Verdict_Level) == ('Low confidence', 'warn')

    camera.Disconnect()
    assert not camera.Connected


@pytest.mark.slow
def test_pipeline_real_florence(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The same flow through the real Florence_Vision_Cls on a synthetic frame (the
        reference with two rectangles). Structural assertions only — object count,
        boxes within the image, non-empty sentences — never the exact caption text,
        which is not deterministic. Needs the weights; skipped otherwise.
    """

    if not os.path.isdir(Vision_Core.CONST_MODEL_DIR):
        pytest.skip(f'model weights not present at {Vision_Core.CONST_MODEL_DIR}')

    # OpenCV library for computer vision tasks [pip3 install opencv-python]
    import cv2

    frame_bgr = make_synthetic_frame(reference_background, CONST_RECTS)
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = image_rgb.shape[:2]

    result = Florence_Vision_Cls().Analyze(image_rgb)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == len(CONST_RECTS)
    for obj in result.Objects:
        x, y, bw, bh = obj.Bbox
        # Box is inside the image dimensions.
        assert 0 <= x and 0 <= y
        assert x + bw <= w and y + bh <= h
        # A described object always has a sentence; its exact words are not asserted.
        assert obj.Sentence
    assert result.Summary
    assert result.Latency_Ms >= 0
