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
# File Name: ../Vision/Utilities/Segmentation.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    Stage 1 of the pipeline: the background-subtracted foreground mask. The absolute
    difference between the frame and the empty-surface reference marks the object
    pixels; it is one of the two cues fused in stage 3 (the other being FastSAM), so
    an object survives if EITHER cue sees it. This module holds only the
    background-subtraction chain and its tunables; the fusion, the background-like
    rejection and the connected-component splitting live in Vision.Utilities.Fusion.

    Note:
        OpenCV (cv2) and NumPy (np) are passed in to every function rather than
        imported here. That is deliberate: App/run.py imports this module at load
        time, but the heavy runtime (OpenCV) is imported lazily so the window opens
        without it. The caller — which has already loaded cv2/np by the time an
        analysis runs — injects them.
"""
# Gaussian blur kernel applied to the difference image, to erase sensor noise
# before thresholding. Odd, as OpenCV requires.
CONST_BG_BLUR = 5
# Minimum grayscale difference that counts as foreground. Otsu picks the split
# automatically, but on a near-empty frame it can land absurdly low and promote the
# faint shadow halo / sensor noise to foreground; this floor keeps those out.
CONST_BG_DIFF_FLOOR = 28
# Opening kernel that erases the thin shadow halo and speckle left around a part
# after thresholding (a hue-preserving cast shadow that survived the difference).
CONST_BG_OPEN_KERNEL = 5
# Small dilation after the opening, so object edges eroded by the opening are
# recovered before the mask is fused. 0 disables it.
CONST_BG_DILATE = 3


def Background_Foreground(bg: tp.List[tp.List[int]], fg: tp.List[tp.List[int]],
                          cv2: tp.Any, np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        The background-subtracted foreground mask: a uint8 {0, 1} mask where 1 marks
        a pixel that differs from the empty-surface reference (an object pixel).

        The chain is the absolute difference against the reference, a Gaussian blur
        to erase sensor noise, an Otsu threshold floored at CONST_BG_DIFF_FLOOR so a
        faint shadow is not promoted to foreground, a morphological opening that
        removes the thin shadow halo and speckle, and a small dilation that recovers
        the object edges the opening ate. It is illumination-robust and independent
        of the segmenter: it is the second cue stage 3 fuses with the FastSAM masks,
        so a part FastSAM misses still survives if the difference sees it.

        The reference must already match the frame's pixel dimensions; the caller
        resizes it once (see Vision.Core.__Load_Background).

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The empty-surface background reference (BGR).
        (2) fg [Matrix<uint8> HxWx3]: The captured frame (BGR).
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The foreground mask (0 or 1).
    """

    diff = cv2.absdiff(fg, bg)
    diff = cv2.GaussianBlur(diff, (CONST_BG_BLUR, CONST_BG_BLUR), 0)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Otsu picks the split automatically; the floor keeps a faint shadow out when
    # Otsu (on a near-empty frame) lands below it.
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = max(float(otsu), float(CONST_BG_DIFF_FLOOR))
    mask = (gray >= thresh).astype(np.uint8)

    # Remove the thin shadow halo / speckle, then grow slightly to recover the object
    # edges eroded by the opening.
    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (CONST_BG_OPEN_KERNEL, CONST_BG_OPEN_KERNEL))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
    if CONST_BG_DILATE > 0:
        dilate_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (CONST_BG_DILATE, CONST_BG_DILATE))
        mask = cv2.dilate(mask, dilate_kernel)
    return mask
