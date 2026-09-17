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
# File Name: ../test/UI/test_capture.py
## =========================================================================== ##

# System (Default)
import os
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the per-analysis capture writer
#   ../UI/Capture
from UI.Capture import Capture_Writer_Cls

"""
Description:
    Tests for the per-analysis capture writer: a complete set is written, the raw frame is
    optional, retention evicts the oldest sets first (on write, bounded), the '.txt' holds
    exactly the given Scene-Understanding text under a stamp header, and a write failure
    raises (so the caller can log an ERROR and continue). No Qt, no camera, no weights —
    small synthetic images and a tmp directory.
"""


def _Images():
    """A small raw / annotated / mask triple (BGR)."""
    raw = np.full((12, 16, 3), 30, np.uint8)
    annotated = np.full((12, 16, 3), 60, np.uint8)
    mask = np.zeros((12, 16, 3), np.uint8)
    return raw, annotated, mask


def _Write(writer: Capture_Writer_Cls, set_id: str, text: str = 'A plain surface.'):
    """Write one set with the injected real cv2/np."""
    raw, annotated, mask = _Images()
    return writer.Write(set_id, raw, annotated, mask, text, 'stamp %s' % set_id, cv2, np)


def test_a_complete_set_is_written(tmp_path) -> None:
    """
    Description:
        A write produces exactly the four artefacts of one set, named so the set is
        obvious, each stamped (the images gain the footer band, the text a header).
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write(writer, '20260912-143202_1')

    for suffix in ('_raw.png', '_annotated.png', '_mask.png', '_understanding.txt'):
        assert (tmp_path / ('20260912-143202_1' + suffix)).exists()
    # The images are taller than the source by the stamp band (26 px).
    stamped = cv2.imread(str(tmp_path / '20260912-143202_1_annotated.png'))
    assert stamped.shape[0] == 12 + 26


def test_raw_frame_is_optional(tmp_path) -> None:
    """
    Description:
        With keep_raw off the raw frame is not written; the other three artefacts still
        are — the lever for a longer history on the same disk.
    """

    writer = Capture_Writer_Cls(str(tmp_path), keep_raw=False)
    _Write(writer, '20260912-143202_1')

    assert not (tmp_path / '20260912-143202_1_raw.png').exists()
    assert (tmp_path / '20260912-143202_1_annotated.png').exists()
    assert (tmp_path / '20260912-143202_1_understanding.txt').exists()


def test_understanding_txt_is_exactly_the_given_text_under_a_stamp(tmp_path) -> None:
    """
    Description:
        The '.txt' is a stamp comment line followed by exactly the Scene-Understanding
        text it was given — the caller passes the shared formatter's output, so the file
        matches the panel, not a second string build.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    text = 'A green background. There are 2 objects on it, described below.\n\nObj. 1 - A ring.'
    _Write(writer, '20260912-143202_1', text)

    lines = (tmp_path / '20260912-143202_1_understanding.txt').read_text()
    assert lines.startswith('# stamp 20260912-143202_1\n')
    assert lines[len('# stamp 20260912-143202_1\n'):] == text + '\n'


def test_retention_evicts_the_oldest_sets_first(tmp_path) -> None:
    """
    Description:
        The retention bound is enforced on write, oldest evicted first: with a bound of 2,
        writing a third set removes the oldest one's files and returns its id; the two
        newest survive.
    """

    writer = Capture_Writer_Cls(str(tmp_path), retention_sets=2)
    assert _Write(writer, 'a') == []                    # 1 set, nothing evicted
    assert _Write(writer, 'b') == []                    # 2 sets, still at the bound

    # Make 'a' unambiguously the oldest and 'b' next, so the eviction order is by age.
    for set_id, when in (('a', 1000), ('b', 2000)):
        for suffix in ('_raw.png', '_annotated.png', '_mask.png', '_understanding.txt'):
            os.utime(str(tmp_path / (set_id + suffix)), (when, when))

    evicted = _Write(writer, 'c')                       # 3 sets -> evict the oldest
    assert evicted == ['a']
    assert not (tmp_path / 'a_raw.png').exists()
    assert (tmp_path / 'b_raw.png').exists()
    assert (tmp_path / 'c_raw.png').exists()


def test_a_write_failure_raises(tmp_path, monkeypatch) -> None:
    """
    Description:
        A PNG that does not land (cv2.imwrite reports failure — a full disk or a
        permission error) raises, rather than passing silently as a success; the caller
        wraps this to log an ERROR and continue.
    """

    monkeypatch.setattr(cv2, 'imwrite', lambda *args, **kwargs: False)
    writer = Capture_Writer_Cls(str(tmp_path))
    raw, annotated, mask = _Images()
    with pytest.raises(OSError):
        writer.Write('20260912-143202_1', raw, annotated, mask, 'text', 'stamp', cv2, np)
