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
# File Name: ../test/Camera/Utilities/test_image_processing.py
## =========================================================================== ##


# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan domain — the camera's image pipeline
#   ../Camera/Utilities/Image_Processing
from Camera.Utilities.Image_Processing import Process_Image_Cls

"""
Description:
    The camera's per-frame image pipeline, on a committed real frame: a light Gaussian blur and a
    contrast/brightness adjustment, and nothing else.
"""


def test_apply_is_the_blur_then_the_contrast_brightness_step_on_a_real_frame(reference_background) -> None:
    """
    Description:
        Apply is exactly its documented pipeline — a 3x3, sigma 0.5 Gaussian blur, then
        g = 0.95 f + 1 saturated to uint8 — byte for byte on the committed reference frame, and it
        leaves its input untouched. (It used to add a float64 round-trip, multiplying by 1.0 per
        channel, and a copy of the input: ~40 ms a frame for the same bytes.)
    """

    frame = reference_background.copy()
    processed = Process_Image_Cls('real').Apply(frame)

    expected = cv2.convertScaleAbs(cv2.GaussianBlur(reference_background, (3, 3), sigmaX=0.5), alpha=0.95, beta=1)
    assert processed.dtype == np.uint8 and np.array_equal(processed, expected)
    assert np.array_equal(frame, reference_background)                  # the input is not modified
