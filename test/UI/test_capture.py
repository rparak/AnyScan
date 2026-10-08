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


def _Write(writer, session_id, set_id, text='A plain surface.', yolo=None, seg=None,
           metadata=None):
    """Write one set with the injected real cv2/np; returns (evicted, created)."""
    raw, annotated, mask = _Images()
    return writer.Write(session_id, set_id, raw, annotated, mask, text,
                        yolo if yolo is not None else ['0 0.5 0.5 0.1 0.1'],
                        seg if seg is not None else ['0 0.4 0.4 0.6 0.4 0.6 0.6 0.4 0.6'],
                        metadata if metadata is not None else {'set_id': set_id, 'objects': []},
                        'stamp %s' % set_id, cv2, np, distorted_bgr=None, undistortion=None)


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


def test_seg_and_objects_json_are_written(tmp_path) -> None:
    """
    Description:
        A write produces the segmentation '<set>_seg.txt' (the lines it was given) and the
        machine-readable '<set>_objects.json' (the metadata it was given), alongside the box
        file — so History has both geometry files and a structured record.
    """

    import json
    writer = Capture_Writer_Cls(str(tmp_path))
    _Write(writer, 's', 'set1', seg=['0 0.100000 0.100000 0.200000 0.100000 0.200000 0.200000'],
           metadata={'set_id': 'set1', 'task': 'caption', 'objects': [{'index': 0}]})

    assert (tmp_path / 's' / 'set1_seg.txt').read_text() == \
        '0 0.100000 0.100000 0.200000 0.100000 0.200000 0.200000\n'
    data = json.loads((tmp_path / 's' / 'set1_objects.json').read_text())
    assert data['set_id'] == 'set1' and data['task'] == 'caption'


def test_thumbnail_is_written_and_bounded_to_the_long_edge(tmp_path) -> None:
    """
    Description:
        A thumbnail JPEG is written from the annotated image with its long edge bounded to
        CONST_CAPTURE_THUMB_LONG_EDGE (320), aspect preserved — so History fills its grid from
        small images, not full-resolution PNGs. A 1920x1200 annotated image yields a 320x200
        thumbnail.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    big = np.full((1200, 1920, 3), 60, np.uint8)
    writer.Write('s', 'set1', big, big, np.zeros((1200, 1920, 3), np.uint8), 'text',
                 ['0 0.5 0.5 0.1 0.1'], ['0 0.4 0.4 0.6 0.6'], {'set_id': 'set1', 'objects': []},
                 'stamp', cv2, np, distorted_bgr=None, undistortion=None)

    thumb_path = tmp_path / 's' / 'set1_thumb.jpg'
    assert thumb_path.exists()
    thumb = cv2.imread(str(thumb_path))
    assert max(thumb.shape[:2]) == 320                   # long edge bounded
    assert thumb.shape[1] == 320 and thumb.shape[0] == 200   # aspect preserved (1920x1200)


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
        writer.Write('s', 'set1', raw, annotated, mask, 'text', ['0 0.5 0.5 0.1 0.1'],
                     ['0 0.4 0.4 0.6 0.6'], {'set_id': 'set1'}, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)


def test_distorted_frame_is_kept_with_a_sidecar_saying_so(tmp_path) -> None:
    """
    Description:
        When the camera provides the frame before undistortion, the set keeps it as
        '<set>_distorted.png' beside the undistorted '<set>_raw.png', with a sidecar that says it
        is distorted, names its counterpart and records the exact undistortion — so no reader can
        mistake one for the other, and the original can be re-undistorted under a later
        calibration. A partial (failed-analysis) set keeps it too; the pixels are the ones given.
    """

    import json
    undistortion = {'configuration': 'Config_x.yaml', 'frame_size': [16, 12],
                    'K': [[1.0, 0.0, 8.0], [0.0, 1.0, 6.0], [0.0, 0.0, 1.0]],
                    'coefficients': {'k1': -0.1}, 'alpha': 1,
                    'new_camera_matrix': [[1.0, 0.0, 8.0], [0.0, 1.0, 6.0], [0.0, 0.0, 1.0]]}
    distorted = np.full((12, 16, 3), 90, np.uint8)
    raw, annotated, mask = _Images()
    writer = Capture_Writer_Cls(str(tmp_path))
    writer.Write('s', 'set1', raw, annotated, mask, 'text', [], [], {'objects': []}, 'stamp',
                 cv2, np, distorted_bgr=distorted, undistortion=undistortion)
    writer.Write_Partial('s', 'fail1', raw, 'failed', 'stamp', cv2, np,
                         distorted_bgr=distorted, undistortion=undistortion)

    for set_id in ('set1', 'fail1'):
        assert (cv2.imread(str(tmp_path / 's' / (set_id + '_distorted.png'))) == 90).all()
        record = json.loads((tmp_path / 's' / (set_id + '_distorted.json')).read_text())
        assert record['distorted'] is True and 'NOT removed' in record['note']
        assert record['frame'] == set_id + '_distorted.png'
        assert record['undistorted_counterpart'] == set_id + '_raw.png'
        assert record['undistortion'] == undistortion


def test_no_distorted_frame_without_one_and_it_is_evicted_with_its_set(tmp_path) -> None:
    """
    Description:
        A camera that does not undistort (a saved frame) provides no original: nothing distorted
        is written — never the undistorted frame under the distorted name. keep_raw off drops
        both frames. Retention evicts the distorted frame and its sidecar with the rest of the set.
    """

    raw, annotated, mask = _Images()
    distorted, record = np.full((12, 16, 3), 90, np.uint8), {'alpha': 1}
    Capture_Writer_Cls(str(tmp_path / 'a')).Write('s', 'set1', raw, annotated, mask, 'text', [],
                                                  [], {'objects': []}, 'stamp', cv2, np,
                                                  distorted_bgr=None, undistortion=None)
    assert not any('distorted' in name for name in os.listdir(tmp_path / 'a' / 's'))

    Capture_Writer_Cls(str(tmp_path / 'b'), keep_raw=False).Write(
        's', 'set1', raw, annotated, mask, 'text', [], [], {'objects': []}, 'stamp', cv2, np,
        distorted_bgr=distorted, undistortion=record)
    names = os.listdir(tmp_path / 'b' / 's')
    assert not any('distorted' in name or '_raw' in name for name in names)

    writer = Capture_Writer_Cls(str(tmp_path / 'c'), retention_sets=1)
    for set_id in ('old', 'new'):
        writer.Write('s', set_id, raw, annotated, mask, 'text', [], [], {'objects': []}, 'stamp',
                     cv2, np, distorted_bgr=distorted, undistortion=record)
    names = sorted(os.listdir(tmp_path / 'c' / 's'))
    assert not any(name.startswith('old') for name in names)
    assert 'new_distorted.png' in names and 'new_distorted.json' in names


def test_a_session_directory_removed_during_eviction_is_skipped(tmp_path, monkeypatch) -> None:
    """
    Description:
        Eviction is best-effort and never raises. Another instance writing to the same captures root
        can remove an empty session directory between eviction's listing of the root and its
        listing of that directory; the set just written must still be reported written. Before
        this, the FileNotFoundError escaped Write after the set had fully landed, so the window
        logged a write failure for a set that exists.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write(writer, 'A', 'a1')
    vanished = str(tmp_path / 'A')
    listdir = os.listdir

    def Listdir_With_A_Removed(path='.'):
        if os.path.abspath(str(path)) == vanished:
            raise FileNotFoundError(2, 'No such file or directory', vanished)
        return listdir(path)

    monkeypatch.setattr(os, 'listdir', Listdir_With_A_Removed)
    evicted, created = _Write(writer, 'B', 'b1')
    monkeypatch.undo()
    assert (evicted, created) == ([], 'B')
    assert (tmp_path / 'B' / 'b1_raw.png').exists()
