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
    Tests for the per-analysis capture writer: a complete set is written into the session
    directory, the raw frame is optional, the YOLO file and classes file are written, the
    session directory is created (and reported), retention evicts the oldest sets first
    ACROSS sessions and removes an emptied session directory, and a write failure raises
    (so the caller can log an ERROR and continue). No Qt, no camera, no weights.
"""


def _Images():
    """A small raw / annotated / mask triple (BGR)."""
    return (np.full((12, 16, 3), 30, np.uint8), np.full((12, 16, 3), 60, np.uint8),
            np.zeros((12, 16, 3), np.uint8))


def _Write(writer, session_id, set_id, text='A plain surface.', yolo=None):
    """Write one set with the injected real cv2/np; returns (evicted, created)."""
    raw, annotated, mask = _Images()
    return writer.Write(session_id, set_id, raw, annotated, mask, text,
                        yolo if yolo is not None else ['0 0.5 0.5 0.1 0.1'], 'stamp %s' % set_id,
                        cv2, np)


def test_a_complete_set_is_written_into_the_session_directory(tmp_path) -> None:
    """
    Description:
        A write produces the set's artefacts inside the session directory — the raw frame,
        the annotated image, the label mask, the Scene-Understanding text and the YOLO
        records — plus a classes file beside the captures. The session directory is
        reported as created on the first write.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    evicted, created = _Write(writer, '20260912-143202_s1', '20260912-143722_1')
    assert created == '20260912-143202_s1' and evicted == []

    session = tmp_path / '20260912-143202_s1'
    for suffix in ('_raw.png', '_annotated.png', '_mask.png', '_understanding.txt', '.txt'):
        assert (session / ('20260912-143722_1' + suffix)).exists()
    assert (session / 'classes.txt').exists()

    # A second write into the same session does not re-report the directory.
    _, created2 = _Write(writer, '20260912-143202_s1', '20260912-143725_2')
    assert created2 is None


def test_yolo_file_holds_the_given_lines_and_classes_has_a_header(tmp_path) -> None:
    """
    Description:
        The '<set>.txt' is exactly the YOLO lines it was given, one per line; the classes
        file carries the header warning plus one id per object index.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    yolo = ['0 0.250000 0.500000 0.100000 0.200000', '1 0.750000 0.500000 0.100000 0.200000']
    _Write(writer, 's', 'set1', yolo=yolo)

    assert (tmp_path / 's' / 'set1.txt').read_text() == '\n'.join(yolo) + '\n'
    classes = (tmp_path / 's' / 'classes.txt').read_text()
    assert classes.startswith('#') and 'not be used for training' in classes.lower()
    assert [line for line in classes.splitlines() if not line.startswith('#')] == ['0', '1']


def test_raw_frame_is_optional(tmp_path) -> None:
    """
    Description:
        With keep_raw off the raw frame is not written; the other artefacts still are.
    """

    writer = Capture_Writer_Cls(str(tmp_path), keep_raw=False)
    _Write(writer, 's', 'set1')
    assert not (tmp_path / 's' / 'set1_raw.png').exists()
    assert (tmp_path / 's' / 'set1_annotated.png').exists()
    assert (tmp_path / 's' / 'set1.txt').exists()


def test_understanding_txt_is_the_given_text_under_a_stamp(tmp_path) -> None:
    """
    Description:
        The '_understanding.txt' is a stamp comment line followed by exactly the
        Scene-Understanding text it was given (the shared formatter's output).
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    text = ('A green background. There are 2 objects on it, described below.'
            '\n\nObject 1 · Confidence 91% - A ring.')
    _Write(writer, 's', 'set1', text=text)
    body = (tmp_path / 's' / 'set1_understanding.txt').read_text()
    assert body == '# stamp set1\n' + text + '\n'


def test_retention_evicts_oldest_across_sessions_and_removes_empty_dirs(tmp_path) -> None:
    """
    Description:
        Retention counts sets GLOBALLY across sessions and evicts oldest-first: with a
        bound of 2, a set in session A and one in B fill the bound; a third (in B) evicts
        A's set — the oldest — even though it is in a different session, and A's now-empty
        directory is removed.
    """

    writer = Capture_Writer_Cls(str(tmp_path), retention_sets=2)
    _Write(writer, 'A', 'a1')
    _Write(writer, 'B', 'b1')

    # Make A's set unambiguously the oldest and B's next.
    for session, set_id, when in (('A', 'a1', 1000), ('B', 'b1', 2000)):
        for name in os.listdir(str(tmp_path / session)):
            os.utime(str(tmp_path / session / name), (when, when))

    evicted, _ = _Write(writer, 'B', 'b2')
    assert evicted == ['a1']                                # oldest across sessions
    assert not (tmp_path / 'A').exists()                    # emptied session dir removed
    assert (tmp_path / 'B' / 'b1_raw.png').exists()
    assert (tmp_path / 'B' / 'b2_raw.png').exists()


def test_a_write_failure_raises(tmp_path, monkeypatch) -> None:
    """
    Description:
        A PNG that does not land (cv2.imwrite reports failure) raises, rather than passing
        silently as a success; the caller wraps this to log an ERROR and continue.
    """

    monkeypatch.setattr(cv2, 'imwrite', lambda *args, **kwargs: False)
    writer = Capture_Writer_Cls(str(tmp_path))
    raw, annotated, mask = _Images()
    with pytest.raises(OSError):
        writer.Write('s', 'set1', raw, annotated, mask, 'text', ['0 0.5 0.5 0.1 0.1'], 'stamp',
                     cv2, np)
