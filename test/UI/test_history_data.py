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
# File Name: ../test/UI/test_history_data.py
## =========================================================================== ##

# System (Default)
import os
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan — the capture writer, the metadata builder and the Qt-free reader
#   ../UI/Capture
from UI.Capture import (Capture_Writer_Cls, Build_Set_Metadata, Read_Capture_Set,
                        Discover_Capture_Sets)
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Tests for the Qt-free capture-set reader — metadata build/round-trip, discovery across
    sessions, newest-first sorting, and the partial and malformed cases. No Qt: the reader
    returns plain structures, so the History view is testable without a UI. cv2 and np are used
    only to write the fixture sets through the real writer.
"""


def _Detections():
    """A detection list mixing a scored/OK object and an unscored one, with masks."""
    mask_a = np.zeros((40, 60), dtype=bool)
    mask_a[5:20, 5:25] = True
    mask_b = np.zeros((40, 60), dtype=bool)
    mask_b[25:35, 30:50] = True
    return [Detection_Str(Label='ring', Bbox=(5, 5, 20, 15), Mask=mask_a, Segmenter_Score=0.91,
                          Sentence='A silver ring.', Verdict='OK', Cue='both'),
            Detection_Str(Label='screw', Bbox=(30, 25, 20, 10), Segmenter_Score=None,
                          Sentence='A small screw.', Verdict='OK', Cue='background')]


def _Write_Set(writer, session_id, set_id, objects, task='caption', latency=1180, mean=91,
               classification=False):
    """Write one full set through the real writer, with metadata built from the detections."""
    raw = np.full((40, 60, 3), 30, np.uint8)
    annotated = np.full((40, 60, 3), 60, np.uint8)
    mask = np.zeros((40, 60, 3), np.uint8)
    size = (60, 40)
    metadata = Build_Set_Metadata(session_id, set_id, '2026-09-20T10:00:00', objects, size,
                                  task, latency, mean, '', classification, scale=None)
    writer.Write(session_id, set_id, raw, annotated, mask, 'text', ['0 0.5 0.5 0.1 0.1'],
                 ['0 0.4 0.4 0.6 0.6'], metadata, 'stamp', cv2, np, distorted_bgr=None, undistortion=None)


def test_metadata_round_trips_and_matches_the_detection_list(tmp_path) -> None:
    """
    Description:
        The metadata written from a detection list reads back as the same objects, in order,
        with the confidence expressed as the rounded percentage (or None), and the set-level
        fields preserved. This is the record History renders — it must match what was detected.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    objects = _Detections()
    _Write_Set(writer, 'sessionA', 'set1', objects, task='caption', latency=1180, mean=91)

    cap = Read_Capture_Set(str(tmp_path / 'sessionA'), 'sessionA', 'set1')
    assert not cap.Partial
    assert (cap.Session_Id, cap.Set_Id, cap.Task, cap.Inference_Ms) == \
        ('sessionA', 'set1', 'caption', 1180)
    assert (cap.Frame_Width, cap.Frame_Height, cap.Frame_Mean_Confidence) == (60, 40, 91)
    assert cap.Classification is False                    # detect-only by default
    assert len(cap.Objects) == len(objects)
    for i, (read, det) in enumerate(zip(cap.Objects, objects)):
        expected_conf = (int(round(100.0 * det.Segmenter_Score))
                         if det.Segmenter_Score is not None else None)
        assert read.Index == i
        assert read.Bbox == tuple(det.Bbox)
        assert read.Confidence == expected_conf
        assert read.Cue == det.Cue
        assert read.Verdict == det.Verdict
        assert read.Description == det.Sentence


def test_classification_flag_round_trips_per_set(tmp_path) -> None:
    """
    Description:
        Each set records whether classification was enabled when it was written, so History knows
        how each set's colours were baked — a set written with classification reads back True, one
        written without reads False. This is what lets a toggled config not hide old data.
    """

    writer = Capture_Writer_Cls(str(tmp_path), retention_sets=10)
    _Write_Set(writer, 'sessionA', 'classified', _Detections(), classification=True)
    _Write_Set(writer, 'sessionA', 'detected', _Detections(), classification=False)

    on = Read_Capture_Set(str(tmp_path / 'sessionA'), 'sessionA', 'classified')
    off = Read_Capture_Set(str(tmp_path / 'sessionA'), 'sessionA', 'detected')
    assert on.Classification is True and off.Classification is False


def test_discovery_across_sessions_and_newest_first_sorting(tmp_path) -> None:
    """
    Description:
        Discovery finds every set across session directories and returns them newest-first by
        the newest file each set holds. Two sets in one session and one in another, given
        distinct mtimes, come back in strict newest-first order regardless of session.
    """

    writer = Capture_Writer_Cls(str(tmp_path), retention_sets=10)
    objects = _Detections()
    _Write_Set(writer, 'sessionA', 'a1', objects)
    _Write_Set(writer, 'sessionA', 'a2', objects)
    _Write_Set(writer, 'sessionB', 'b1', objects)

    # Stamp distinct mtimes: b1 newest, then a2, then a1.
    stamps = {'sessionA/a1': 1000, 'sessionA/a2': 2000, 'sessionB/b1': 3000}
    for rel, when in stamps.items():
        session, set_id = rel.split('/')
        for name in os.listdir(str(tmp_path / session)):
            if name.startswith(set_id):
                os.utime(str(tmp_path / session / name), (when, when))

    sets = Discover_Capture_Sets(str(tmp_path))
    assert [cap.Set_Id for cap in sets] == ['b1', 'a2', 'a1']   # newest first, across sessions
    assert {cap.Session_Id for cap in sets} == {'sessionA', 'sessionB'}


def test_partial_set_reads_as_partial_with_a_note(tmp_path) -> None:
    """
    Description:
        A partial set (a failed analysis: raw frame and a note, no metadata) reads as partial,
        with no objects, the raw path present and the failure note carried through — so History
        can show it rather than hide it.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    raw = np.full((40, 60, 3), 30, np.uint8)
    writer.Write_Partial('sessionA', 'failset', raw,
                         'Analysis FAILED — partial capture (raw frame only). Failure: boom',
                         'stamp', cv2, np, distorted_bgr=None, undistortion=None)

    cap = Read_Capture_Set(str(tmp_path / 'sessionA'), 'sessionA', 'failset')
    assert cap.Partial and cap.Objects == []
    assert cap.Raw_Path is not None and cap.Annotated_Path is None
    assert 'FAILED' in cap.Note and 'boom' in cap.Note


def test_malformed_metadata_reads_as_partial_not_a_crash(tmp_path) -> None:
    """
    Description:
        A set whose '_objects.json' is corrupt reads as partial with an explanatory note rather
        than raising — the reader is defensive because the file could be truncated by a crash
        mid-write or hand-edited. The images it has are still reported.
    """

    writer = Capture_Writer_Cls(str(tmp_path))
    _Write_Set(writer, 'sessionA', 'set1', _Detections())
    (tmp_path / 'sessionA' / 'set1_objects.json').write_text('{ this is not valid json ]')

    cap = Read_Capture_Set(str(tmp_path / 'sessionA'), 'sessionA', 'set1')
    assert cap.Partial and cap.Objects == []
    assert 'malformed' in cap.Note.lower()
    assert cap.Annotated_Path is not None                # the images it has are still reported


def test_discovery_of_a_missing_root_is_empty_not_an_error(tmp_path) -> None:
    """
    Description:
        Discovering a captures root that does not exist yet returns an empty list, never raises —
        History with no captures shows an empty grid, not a crash.
    """

    assert Discover_Capture_Sets(str(tmp_path / 'does_not_exist')) == []
