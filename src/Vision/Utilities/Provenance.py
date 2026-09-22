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
# File Name: ../Vision/Utilities/Provenance.py
## =========================================================================== ##

# System (Default)
import hashlib
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The ONE provenance stamp shared by everything that writes a review image — the
    validation harness (Example/Vision/analyze.py), the demo renderer
    (Example/UI/screenshot.py) and the per-analysis capture writer (UI.Capture). A stamp
    is a slim footer band appended below the image naming the run and the source, so a
    file left over from an earlier or failed run, or two renders that look alike, are told
    apart by looking at the image rather than by remembering which script produced it.

    Qt-free: OpenCV and NumPy are injected by the caller (the drawing side), so the same
    stamp is reachable from the Qt-free vision layer and from the UI without dragging Qt
    into either. Fingerprinting needs neither and is pure standard library.
"""
# The stamp footer band (px tall) and its text scale.
#   Unit [int]
CONST_STAMP_BAND_H = 26
#   Unit [float]
CONST_STAMP_FONT_SCALE = 0.5
# The number of leading hex digits taken from a file's MD5 digest as its fingerprint.
#   Unit [int]
CONST_FINGERPRINT_LEN = 10


def Fingerprint(path: str) -> str:
    """
    Description:
        The short content fingerprint of a file: the first CONST_FINGERPRINT_LEN hex
        digits of its MD5 digest. Two runs over the same bytes fingerprint the same, so an
        artefact whose fingerprint no longer matches its source is stale on sight. This is
        provenance, not security — MD5 is used only as a fast content digest.

    Args:
        (1) path [string]: The file to fingerprint.

    Returns:
        (1) parameter [string]: The short hex fingerprint.
    """

    with open(path, 'rb') as handle:
        return hashlib.md5(handle.read()).hexdigest()[:CONST_FINGERPRINT_LEN]


def Stamp_Image(image: tp.Any, text: str, cv2: tp.Any, np: tp.Any) -> tp.Any:
    """
    Description:
        Return the image with the provenance stamp on a slim footer band appended BELOW
        it — never drawn over the content, so it labels the artefact without occluding
        anything under review.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The artefact image (BGR).
        (2) text [string]: The provenance line.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Matrix<uint8> (H+band)xWx3]: The stamped image.
    """

    band = np.full((CONST_STAMP_BAND_H, image.shape[1], 3), 24, np.uint8)
    cv2.putText(band, text, (8, CONST_STAMP_BAND_H - 9), cv2.FONT_HERSHEY_SIMPLEX,
                CONST_STAMP_FONT_SCALE, (210, 210, 210), 1, cv2.LINE_AA)
    return np.vstack([image, band])
