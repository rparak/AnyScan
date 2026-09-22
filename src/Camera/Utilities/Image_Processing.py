## =========================================================================== ## 
# MIT License
# Copyright (c) 2024 JIC Smart Factory
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
# File Name: ../Camera/Utilities/Image_Processing.py
## =========================================================================== ##

# Numpy (Array computing)
import numpy as np
# Typing (Support for type hints)
import typing as tp
# OpenCV (Computer Vision)
import cv2

def Get_Alpha_Beta_Parameters(image: tp.List[tp.List[int]], clip_limit: float) -> tp.Tuple[float, float]:
    """
    Description:
        Function to adjust the contrast and brightness parameters of the input image by clipping the histogram.

        The main core of the function is to obtain the alpha and beta parameters 
        to determine the equation:
            g(i, j) = alpha * f(i, j) + beta,

            where g(i, j) are the input (source) pixels of the image, f(i, j) are the output pixels 
            of the image, and alpha, beta are the contrast and brightness parameters.

    Args:
        (1) image [Vector<float> Image Shape {Resolution<x, y>}]: Input raw image.
        (2) clip_limit [float]: Parameter for histogram clipping in percentage.

    Returns:
        (1) parameter [float]: A gain (contrast) parameter called alpha.
        (2) parameter [float]: A bias (brightness) parameter called beta.
    """

    image_copy = image.copy()

    # Calculate the grayscale histogram of the image.
    image_hist = cv2.calcHist([image_copy], [0], None, [256], [0, 256])

    # Get the cumulative sum of the elements (histogram).
    c_hist = np.cumsum(image_hist)

    # Modify the percentage to clip the histogram.
    c_hist_max = c_hist[-1]
    clip_limit_mod = clip_limit * (c_hist_max/float(100.0*2.0))

    # Clip the histogram if the values are outside the limit.
    min_value = 0; max_value = c_hist.size - 1
    for _, c_hist_i in enumerate(c_hist):
        if c_hist_i < clip_limit_mod:
            min_value += 1

        if c_hist_i >= (c_hist_max - clip_limit_mod):
            max_value -= 1

    # Guard against a degenerate (flat) histogram: with no spread to stretch, the
    # clip collapses max_value onto/under min_value, and dividing by it would give a
    # nonsensical negative gain. Return the identity transform (no change) instead.
    if max_value <= min_value:
        return (1.0, 0.0)

    # Express the alpha and beta parameters.
    #   Gain (contrast) parameter.
    alpha = 255 / (max_value - min_value)
    #   Bias (brightness) parameter.
    beta  = (-1) * (min_value * alpha)

    return (alpha, beta)

class Process_Image_Cls:
    """
    Description:
        A class for processing real camera frames.

        Note:
            Includes methods for adjusting colour style and applying Gaussian blur.

    Initialization of the Class:
        Args:
            (1) image_type [string]: Type of the image to process. Must be 'real'.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Process_Image_Cls('real')

            Features:
                # Functions of the class.
                Cls.Apply(image)
    """

    def __init__(self, image_type: str) -> None:
        if image_type != 'real':
            raise ValueError("[ERROR] Image type must be 'real'.")
        self.__image_type = image_type

    def __Color_Style(self, image: np.ndarray, alpha: float = 0.95, beta: int = 5) -> np.ndarray:
        """
        Description:
            Adjusts brightness and contrast, with optional warm filter effect.

        Args:
            (1) image [np.ndarray]: Input image.
            (2) alpha [float]: Contrast factor (1.0 = no change).
            (3) beta [int]: Brightness offset.

        Returns:
            (1) parameter [np.ndarray]: Color-adjusted image.
        """

        adjusted_img = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
        return np.clip(adjusted_img * np.array([[[1.0, 1.0, 1.0]]]), 0, 255).astype(np.uint8)

    def __Blur(self, image: np.ndarray, kernel_size: tp.Tuple[int, int] = (5, 5), sigma: float = 1.0) -> np.ndarray:
        """
        Description:
            Applies Gaussian blur to reduce sharpness and simulate camera effects.

        Args:
            (1) image [np.ndarray]: Input image.
            (2) kernel_size [Tuple[int, int]]: Size of the Gaussian kernel.
            (3) sigma [float]: Gaussian kernel standard deviation.

        Returns:
            (1) parameter [np.ndarray]: Blurred image.
        """

        return cv2.GaussianBlur(image, kernel_size, sigmaX=sigma)

    def Apply(self, image: np.ndarray) -> np.ndarray:
        """
        Description:
            Applies the real-frame image processing pipeline: a light Gaussian blur
            followed by a brightness/contrast colour adjustment.

        Args:
            (1) image [np.ndarray]: Input image in uint8 format.

        Returns:
            (1) parameter [np.ndarray]: Processed image.
        """

        image_tmp = image.copy()
        blurred_img = self.__Blur(image_tmp, kernel_size=(3, 3), sigma=0.5)
        return self.__Color_Style(blurred_img, alpha=0.95, beta=1)
