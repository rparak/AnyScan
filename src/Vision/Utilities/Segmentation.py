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
# The top of the fixed scale the Camera View's heatmap shows this difference on (Vision.Core builds its
# Heatmap_Str from it): 0 .. 128 grey levels, linear, a value above saturating to the top colour. Fixed,
# not normalised per frame, so an empty frame's noise never looks as hot as a part. Its basis: the eight
# frames of Data/Images/Test/All (the previous set, no longer in the repository; recoverable from 1061966)
# against the shipped reference (2026-10-07), under the lighting of that time —
# background median 6-7, the busiest frames' 90th percentile 56-75, Otsu thresholds 30-65 (the floor of 28
# never bound), objects up to 156-172. At 128 the band that decides found or missed (shadows from ~10 up to
# the threshold) gets the lower half of the lightness range, and everything above it is at least twice the
# highest threshold seen. RE-CHECK at the side-light session: another light can move both the background
# and the object ranges.
#   Unit [int] (grey level)
CONST_DIFFERENCE_SCALE_MAX = 128


def Background_Difference(bg: tp.List[tp.List[int]], fg: tp.List[tp.List[int]], cv2: tp.Any,
                          np: tp.Any) -> tp.List[tp.List[int]]:
    """
    Description:
        The background cue before thresholding: the per-channel absolute difference between the frame
        and the empty-surface reference, blurred to erase sensor noise, as grey — exactly the image
        Foreground_Mask thresholds, and the image the Camera View's heatmap shows.

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The empty-surface background reference (BGR).
        (2) fg [Matrix<uint8> HxWx3]: The captured frame (BGR).
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller. Unused here, and kept on purpose: the
            (cv2, np) pair is injected together everywhere.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The difference, in grey levels 0 .. 255.
    """

    diff = cv2.absdiff(fg, bg)
    diff = cv2.GaussianBlur(diff, (CONST_BG_BLUR, CONST_BG_BLUR), 0)
    return cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)


def Foreground_Mask(gray: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any, *,
                    Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> tp.Tuple[tp.List[tp.List[int]],
                                                                                          float, float]:
    """
    Description:
        Threshold the background difference into the foreground mask: an Otsu threshold floored at the
        configured Otsu_Floor so a faint shadow is not promoted to foreground, a morphological opening
        that removes the thin shadow halo and speckle, and a small dilation that recovers the object edges
        the opening ate.

    Args:
        (1) gray [Matrix<uint8> HxW]: The background difference (Background_Difference).
        (2) cv2 [module]: The OpenCV module, injected by the caller.
        (3) np [module]: The NumPy module, injected by the caller.
        (4) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: REQUIRED,
            keyword-only: the configured Otsu_Floor, Open_Kernel and Dilate.

    Returns:
        (1) parameter [Matrix<uint8> HxW]: The foreground mask (0 or 1).
        (2) parameter [float]: The threshold applied, max(Otsu, Otsu_Floor), in grey levels.
        (3) parameter [float]: Otsu's own threshold, so a caller can tell which of the two applied.
    """

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
    return mask, thresh, float(otsu)


def Background_Foreground(bg: tp.List[tp.List[int]], fg: tp.List[tp.List[int]],
                          cv2: tp.Any, np: tp.Any, *,
                          Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> tp.List[tp.List[int]]:
    """
    Description:
        The background-subtracted foreground mask: a uint8 {0, 1} mask where 1 marks
        a pixel that differs from the empty-surface reference (an object pixel).

        The chain is Background_Difference (the absolute difference against the reference,
        blurred, as grey) then Foreground_Mask (an Otsu threshold floored at the configured
        Otsu_Floor, an opening, a small dilation). The pipeline calls the two halves itself,
        to keep the difference for the Camera View's heatmap; this composition serves the
        callers that want only the mask. It is illumination-robust and independent
        of the segmenter: it is the second cue stage 3 fuses with the FastSAM masks,
        so a part FastSAM misses still survives if the difference sees it.

        The reference must already match the frame's pixel dimensions; the caller refuses one
        that does not (see Vision.Core.__Load_Background), never resizing it.

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

    mask, _thresh, _otsu = Foreground_Mask(Background_Difference(bg, fg, cv2, np), cv2, np,
                                           Segmentation_Parameters_Str=Segmentation_Parameters_Str)
    return mask
