## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../Camera/Utilities/Stillness.py
## =========================================================================== ##

# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    Whether anything moved between two consecutive frames of a still camera: the check a scan makes
    before it takes its frame (Camera.Core.Camera_Backend_Cls.Capture_Still). Both frames are reduced
    to grey at a quarter of their size and their absolute difference is blurred, so the sensor's
    per-pixel noise averages out while a moving hand or a sliding part, which changes a patch of
    pixels by far more than the noise, stays. The scene is moving when more than CONST_STILL_AREA_PX
    of that difference exceed CONST_STILL_LEVEL.

    The two thresholds were measured on this camera at the station file's settings (exposure
    10000 us, gain 10 dB, BayerRG8, 1920 x 1200) with Example/Camera/preview_check.py: see
    docs/design-decisions.md, *A scan waits for a still scene*.
"""
# How much smaller each side of a frame is made before the comparison: 1920 x 1200 becomes 480 x 300.
#   Unit [int]
CONST_STILL_SCALE = 4
# The Gaussian blur over the reduced difference image.
#   Unit [Tuple<int> 1x2]
CONST_STILL_BLUR = (5, 5)
# A reduced, blurred difference above this is a change, not noise: twice the largest difference any pixel showed
# between consecutive frames of the still table, 4.55 grey levels over 222 pairs (60 s, 2026-10-16), rounded down.
# A 1 px (0.1 mm) shift of a real test frame exceeds it in 7 of 8 frames of Data/Images/Test, a 2 px shift in all.
#   Unit [grey level]
CONST_STILL_LEVEL = 9.0
# More changed pixels than this (of the reduced 480 x 300 image) is movement: 16 reduced pixels are 16 x 16 frame
# pixels, about 1.6 x 1.6 mm on the table. On the still table no pixel exceeded even 5 grey levels in any pair, so
# the area only keeps one stray speck from refusing a scan; a hand or a sliding part changes hundreds.
#   Unit [px]
CONST_STILL_AREA_PX = 16

def Motion_Image(frame_a: tp.List[tp.List[int]], frame_b: tp.List[tp.List[int]]) -> tp.List[tp.List[float]]:
    """
    Description:
        The blurred absolute difference of two frames, each reduced to grey at 1/CONST_STILL_SCALE of
        its size.

    Args:
        (1) frame_a [Matrix<uint8> HxWx3]: The earlier frame (RGB).
        (2) frame_b [Matrix<uint8> HxWx3]: The later frame (RGB), of the same size.

    Returns:
        (1) parameter [Matrix<float32> hxw]: The difference [grey level].
    """

    if frame_a.shape != frame_b.shape:
        raise ValueError('The two frames compared for movement differ in size: %s and %s.'
                         % (frame_a.shape, frame_b.shape))
    h, w = frame_a.shape[:2]
    size = (w // CONST_STILL_SCALE, h // CONST_STILL_SCALE)
    reduced = [cv2.resize(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), size, interpolation=cv2.INTER_AREA).astype(np.float32)
               for frame in (frame_a, frame_b)]
    return cv2.GaussianBlur(np.abs(reduced[1] - reduced[0]), CONST_STILL_BLUR, 0)


def Moving_Pixels(frame_a: tp.List[tp.List[int]], frame_b: tp.List[tp.List[int]]) -> int:
    """
    Description:
        How many pixels of the reduced difference (Motion_Image) exceed CONST_STILL_LEVEL.

    Args:
        (1) frame_a [Matrix<uint8> HxWx3]: The earlier frame (RGB).
        (2) frame_b [Matrix<uint8> HxWx3]: The later frame (RGB).

    Returns:
        (1) parameter [int]: The changed pixels [px of the reduced image].
    """

    return int(np.count_nonzero(Motion_Image(frame_a, frame_b) > CONST_STILL_LEVEL))


def Is_Still(frame_a: tp.List[tp.List[int]], frame_b: tp.List[tp.List[int]]) -> bool:
    """
    Description:
        Whether nothing moved between two consecutive frames: no more than CONST_STILL_AREA_PX changed
        pixels (Moving_Pixels).

    Args:
        (1) frame_a [Matrix<uint8> HxWx3]: The earlier frame (RGB).
        (2) frame_b [Matrix<uint8> HxWx3]: The later frame (RGB).

    Returns:
        (1) parameter [bool]: True when the scene was still.
    """

    return Moving_Pixels(frame_a, frame_b) <= CONST_STILL_AREA_PX
