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
# File Name: ../Vision/Utilities/Segmentation.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the configured stage parameters
#   ../Parameters/Configuration
from Parameters.Configuration import Segmentation_Parameters_Str

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
# The Otsu floor and the opening/dilation kernels are configuration, not constants: they arrive
# in Segmentation_Parameters_Str (the 'Segmentation.Background' block).


def Background_Foreground(bg: tp.List[tp.List[int]], fg: tp.List[tp.List[int]],
                          cv2: tp.Any, np: tp.Any, *,
                          Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> tp.List[tp.List[int]]:
    """
    Description:
        The background-subtracted foreground mask: a uint8 {0, 1} mask where 1 marks
        a pixel that differs from the empty-surface reference (an object pixel).

        The chain is the absolute difference against the reference, a Gaussian blur
        to erase sensor noise, an Otsu threshold floored at the configured Otsu_Floor so a
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
        (5) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: REQUIRED,
            keyword-only: the configured Otsu_Floor, Open_Kernel and Dilate.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The foreground mask (0 or 1).
    """

    diff = cv2.absdiff(fg, bg)
    diff = cv2.GaussianBlur(diff, (CONST_BG_BLUR, CONST_BG_BLUR), 0)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # Otsu picks the split automatically; the floor keeps a faint shadow out when
    # Otsu (on a near-empty frame) lands below it.
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thresh = max(float(otsu), float(Segmentation_Parameters_Str.Otsu_Floor))
    mask = (gray >= thresh).astype(np.uint8)

    # Remove the thin shadow halo / speckle, then grow slightly to recover the object
    # edges eroded by the opening.
    open_size, dilate_size = Segmentation_Parameters_Str.Open_Kernel, Segmentation_Parameters_Str.Dilate
    if open_size > 0:
        open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_size, open_size))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
    if dilate_size > 0:
        dilate_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_size, dilate_size))
        mask = cv2.dilate(mask, dilate_kernel)
    return mask
