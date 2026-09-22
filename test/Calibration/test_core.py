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
# File Name: ../test/Calibration/test_core.py
## =========================================================================== ##

# System (Default)
import os
import json
import importlib.util
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the calibration layer
#   ../Calibration/Core
import Calibration.Core as Calibration_Core
from Calibration.Core import Detect_Board, Next_Capture_Name, Record_Capture

"""
Description:
    Tests for the calibration layer: the partial-board detector, the capture numbering that never
    overwrites, the manifest that marks captures as distorted, and the --capture harness driven
    with a stand-in camera. Boards are drawn synthetically, so their corner positions are exact.
"""

# The project root, for loading the Example harness by path.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# The synthetic board: 11 x 8 squares (10 x 7 inner corners), 122 px each (~12 mm at 0.098 mm/px).
CONST_SQUARES, CONST_SQUARE_PX = (11, 8), 122


def _Board_Frame(origin_x: int, origin_y: int, size=(1200, 1920)) -> np.ndarray:
    """A grey frame with an axis-aligned chessboard whose top-left square starts at origin (BGR)."""
    image = np.full(size, 170, np.uint8)
    for row in range(CONST_SQUARES[1]):
        for column in range(CONST_SQUARES[0]):
            if (row + column) % 2 == 0:
                x0, y0 = origin_x + column * CONST_SQUARE_PX, origin_y + row * CONST_SQUARE_PX
                cv2.rectangle(image, (x0, y0), (x0 + CONST_SQUARE_PX - 1, y0 + CONST_SQUARE_PX - 1),
                              20, -1)
    return cv2.cvtColor(cv2.GaussianBlur(image, (5, 5), 1.2), cv2.COLOR_GRAY2BGR)


@pytest.mark.parametrize('origin, visible', [((412, 112), (10, 7)),          # whole board
                                             ((-274, -152), (8, 6)),        # 2 cols + 1 row cut
                                             ((-518, -396), (6, 4))])       # 4 cols + 3 rows cut
def test_detector_finds_the_visible_part_of_an_overhanging_board(origin, visible) -> None:
    """
    Description:
        The whole board yields its 10 x 7 inner corners; a board overhanging the frame's corner
        yields exactly its visible grid — the classic detector finds nothing there — with every
        adjacent-corner spacing within 0.1 px of the drawn square along both grid directions.
    """

    frame = _Board_Frame(*origin)
    detection = Detect_Board(frame)
    assert detection.Found, detection.Reason
    assert sorted(detection.Grid) == sorted(visible)
    grid = detection.Corners.reshape(detection.Grid[1], detection.Grid[0], 2)
    for axis in (0, 1):
        spacing = np.linalg.norm(np.diff(grid, axis=axis), axis=2)
        assert np.abs(spacing - CONST_SQUARE_PX).max() < 0.1
    if visible != (10, 7):
        assert not cv2.findChessboardCorners(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (10, 7))[0]


def test_detector_reports_why_when_there_is_no_board() -> None:
    """
    Description:
        A frame with no board is not an exception: the detection says not found and why.
    """

    detection = Detect_Board(np.full((600, 800, 3), 128, np.uint8))
    assert not detection.Found and 'no chessboard' in detection.Reason
    assert detection.Corners.shape == (0, 2)


def test_capture_numbers_run_across_kinds_and_never_overwrite(tmp_path) -> None:
    """
    Description:
        Captures are numbered in one sequence across the two kinds, continuing after whatever is
        already in the directory — so a second session never overwrites the first's frames.
    """

    assert Next_Capture_Name(str(tmp_path), flat=True) == 'flat_001.png'
    (tmp_path / 'flat_001.png').write_bytes(b'')
    (tmp_path / 'view_007.png').write_bytes(b'')
    (tmp_path / 'notes.png').write_bytes(b'')
    assert Next_Capture_Name(str(tmp_path), flat=False) == 'view_008.png'
    assert Next_Capture_Name(str(tmp_path), flat=True) == 'flat_008.png'


def test_manifest_accumulates_and_keeps_its_header(tmp_path) -> None:
    """
    Description:
        The manifest is created from the header on the first capture and only appended to after
        that: a later header cannot rewrite what the first session recorded.
    """

    Record_Capture(str(tmp_path), {'distorted': True, 'camera': 'A'}, {'file': 'flat_001.png'})
    Record_Capture(str(tmp_path), {'distorted': True, 'camera': 'B'}, {'file': 'view_002.png'})
    manifest = json.loads((tmp_path / Calibration_Core.CONST_CALIB_MANIFEST).read_text())
    assert manifest['camera'] == 'A' and manifest['distorted'] is True
    assert [f['file'] for f in manifest['frames']] == ['flat_001.png', 'view_002.png']
    assert not (tmp_path / (Calibration_Core.CONST_CALIB_MANIFEST + '.writing')).exists()


def test_capture_harness_keeps_every_frame_and_marks_them_distorted(tmp_path, monkeypatch) -> None:
    """
    Description:
        'calibrate.py --capture DIR' with a stand-in camera: 'f' and 't' each write a frame under
        its kind's prefix, an unknown key writes nothing, a frame with no board is KEPT and
        recorded with the reason, and the manifest says the frames are distorted.
    """

    spec = importlib.util.spec_from_file_location(
        'calibrate', os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Camera', 'calibrate.py'))
    calibrate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calibrate)

    frames = iter([_Board_Frame(412, 112), np.full((1200, 1920, 3), 128, np.uint8)])

    class _Camera_Cls:
        """A stand-in for Basler_Cls that hands out the scripted frames."""

        def __init__(self, config):
            pass

        def Capture(self):
            return next(frames)

    keys = iter(['f', 'x', 't', 'q'])
    monkeypatch.setattr(calibrate, 'Basler_Cls', _Camera_Cls)
    monkeypatch.setattr('builtins.input', lambda prompt='': next(keys))
    assert calibrate.Capture_Main(str(tmp_path)) == 0

    assert sorted(os.listdir(tmp_path)) == ['capture.json', 'flat_001.png', 'view_002.png']
    manifest = json.loads((tmp_path / 'capture.json').read_text())
    assert manifest['distorted'] is True and 'NOT undistorted' in manifest['note']
    flat, view = manifest['frames']
    assert (flat['kind'], flat['board_found'], flat['corners']) == ('flat', True, 70)
    assert (view['kind'], view['board_found']) == ('view', False) and view['reason']
