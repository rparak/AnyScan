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
# File Name: ../test/Vision/Utilities/test_provenance.py
## =========================================================================== ##

# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan — the shared provenance stamp
#   ../Vision/Utilities/Provenance
import Vision.Utilities.Provenance as Provenance

"""
Description:
    Tests for the shared provenance stamp reused by the harness, the demo renderer and the
    capture writer: a content fingerprint that tracks bytes, and a footer-band stamp
    appended below the content without occluding it.
"""


def test_fingerprint_tracks_file_bytes(tmp_path) -> None:
    """
    Description:
        Identical bytes fingerprint the same, different bytes differently, at the fixed
        short length — so an artefact whose stamp no longer matches its source is stale.
    """

    a = tmp_path / 'a.bin'; a.write_bytes(b'same bytes')
    b = tmp_path / 'b.bin'; b.write_bytes(b'same bytes')
    c = tmp_path / 'c.bin'; c.write_bytes(b'other bytes')

    assert Provenance.Fingerprint(str(a)) == Provenance.Fingerprint(str(b))
    assert Provenance.Fingerprint(str(a)) != Provenance.Fingerprint(str(c))
    assert len(Provenance.Fingerprint(str(a))) == Provenance.CONST_FINGERPRINT_LEN


def test_stamp_appends_a_visible_band_below_the_content() -> None:
    """
    Description:
        The stamp is a footer band appended below the image: the content rows are
        untouched and the image grows by the band height, with the drawn text making the
        band non-uniform.
    """

    image = np.full((30, 120, 3), 127, np.uint8)
    stamped = Provenance.Stamp_Image(image, 'set demo | 2026-09-12T14:37:02', cv2, np)

    assert stamped.shape == (30 + Provenance.CONST_STAMP_BAND_H, 120, 3)
    assert np.array_equal(stamped[:30], image)          # content preserved, not drawn over
    assert stamped[30:].std() > 0                        # the stamp text marks the band
