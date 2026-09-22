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
# File Name: ../test/Calibration/test_core.py
## =========================================================================== ##

# System (Default)
import os
import json
import math
import shutil
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
from Calibration.Core import (Detect_Board, Next_Capture_Name, Record_Capture, Calibrate,
                              Report_Lines, Calibration_Error_Cls, Calibration_Parameters)
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import (Read_Configuration, Read_Conversion_Factor,
                                            Write_Calibration, CONST_BASLER_CONFIG_FILE)

"""
Description:
    Tests for the calibration layer: the partial-board detector, the capture numbering that never
    overwrites, the manifest that marks captures as distorted, the --capture harness driven with
    a stand-in camera, and the multi-view solve. Boards are drawn synthetically, so their corner
    positions are exact; the solve's boards are RENDERED through a known lens (K and distortion
    below) at a known distance, so the intrinsics and the true mm/px are known.
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


# The rendering camera for the solve tests: a 960 x 600 frame, a principal point off the centre,
# barrel distortion, and a table plane 360 mm away.
CONST_RENDER_SIZE = (960, 600)
CONST_RENDER_K = np.array([[1750.0, 0.0, 487.0], [0.0, 1750.0, 296.0], [0.0, 0.0, 1.0]])
CONST_RENDER_D = np.array([-0.15, 0.10, 0.0, 0.0, 0.0])
CONST_RENDER_Z, CONST_RENDER_SQUARE = 360.0, 12.0


@pytest.fixture(scope='module')
def render():
    """A renderer of the 11 x 8 board through the known lens: (rotation vector, centre, depth)."""
    width, height, ss = CONST_RENDER_SIZE[0], CONST_RENDER_SIZE[1], 2
    ys, xs = np.mgrid[0:height * ss, 0:width * ss]
    pixels = np.stack([(xs + 0.5) / ss - 0.5, (ys + 0.5) / ss - 0.5], -1).reshape(-1, 1, 2)
    ideal = cv2.undistortPoints(pixels.astype(np.float64), CONST_RENDER_K,
                                CONST_RENDER_D).reshape(height * ss, width * ss, 2)
    columns, rows = CONST_SQUARES

    def _Render(rvec, centre=(0.0, 0.0), depth=CONST_RENDER_Z):
        rotation = cv2.Rodrigues(np.asarray(rvec, float))[0]
        half = np.array([(columns - 2) * CONST_RENDER_SQUARE / 2, (rows - 2) * CONST_RENDER_SQUARE / 2, 0])
        translation = np.array([centre[0], centre[1], depth]) - rotation @ half
        inverse = np.linalg.inv(np.column_stack([rotation[:, 0], rotation[:, 1], translation]))
        x, y = ideal[..., 0], ideal[..., 1]
        w = inverse[2, 0] * x + inverse[2, 1] * y + inverse[2, 2]
        u = (inverse[0, 0] * x + inverse[0, 1] * y + inverse[0, 2]) / w / CONST_RENDER_SQUARE
        v = (inverse[1, 0] * x + inverse[1, 1] * y + inverse[1, 2]) / w / CONST_RENDER_SQUARE
        board = (u >= -1) & (u < columns - 1) & (v >= -1) & (v < rows - 1)
        paper = (u >= -1.6) & (u < columns - 0.4) & (v >= -1.6) & (v < rows - 0.4)
        image = np.full(u.shape, 110.0)
        image[paper] = 225.0
        image[board & ((np.floor(u) + np.floor(v)) % 2 == 0)] = 25.0
        image = image.reshape(height, ss, width, ss).mean(axis=(1, 3))
        return cv2.cvtColor(np.clip(image, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    return _Render


def _Tilt(degrees: float, azimuth: float):
    """A rotation vector tilting the board by 'degrees' about an in-plane axis at 'azimuth'."""
    a = math.radians(azimuth)
    return [math.cos(a) * math.radians(degrees), math.sin(a) * math.radians(degrees), 0.0]


def _Flats(render):
    """Three boards flat on the table (turned a little, as a real board lies) at three places."""
    return [('flat_001.png', render([0, 0, 0.05], (0, 0))),
            ('flat_002.png', render([0, 0, 0.3], (-25, -12))),
            ('flat_003.png', render([0, 0, -0.2], (25, 12)))]


def _Tilted(render):
    """Eight views tilted 15-25 deg in eight directions, raised 20 mm."""
    return [('view_%03d.png' % (i + 4), render(_Tilt(degrees, azimuth), (0, 0), CONST_RENDER_Z + 20))
            for i, (degrees, azimuth) in enumerate([(20, 0), (25, 90), (20, 180), (25, 270),
                                                    (15, 45), (20, 135), (15, 225), (20, 315)])]


@pytest.fixture(scope='module')
def solved(render):
    """The full synthetic set solved once, with an unreadable file and a board-less frame."""
    views = _Flats(render) + _Tilted(render) + [('view_012.png', None),
                                                ('view_013.png', np.full((600, 960, 3), 128, np.uint8))]
    return Calibrate(views, CONST_RENDER_SQUARE, 0.0, CONST_SQUARES)


def _True_Factor():
    """The true mm/px of the table plane in the application's undistorted (alpha = 1) space."""
    new_K, _ = cv2.getOptimalNewCameraMatrix(CONST_RENDER_K, CONST_RENDER_D, CONST_RENDER_SIZE, 1,
                                             CONST_RENDER_SIZE)
    return (CONST_RENDER_Z / new_K[0, 0], CONST_RENDER_Z / new_K[1, 1])


def test_multi_view_calibration_recovers_known_intrinsics(solved) -> None:
    """
    Description:
        Eleven rendered views (three flat, eight tilted 15-25 deg) solved together recover the
        principal point within 1 px and the focal length within 0.5 %, with a sub-0.2 px
        reprojection; the principal point's reported offset is its distance from the image
        centre; the set is tilted enough, so no tilt warning.
    """

    K = solved.K
    assert abs(K[0, 2] - 487.0) < 1.0 and abs(K[1, 2] - 296.0) < 1.0
    assert abs(K[0, 0] / 1750.0 - 1.0) < 0.005 and abs(K[1, 1] / 1750.0 - 1.0) < 0.005
    assert solved.Rms_Px < 0.2
    assert solved.Principal_Distance_Px == pytest.approx(math.hypot(487.0 - 479.5, 296.0 - 299.5),
                                                         abs=1.0)
    assert solved.Tilted_Views == 8 and solved.Tilt_Warning == ''
    assert solved.Tilt_Range_Deg[1] == pytest.approx(25.0, abs=0.5)
    assert any(line.startswith('[INFO] PRINCIPAL POINT') for line in Report_Lines(solved))


def test_failing_images_are_named_and_skipped_not_fatal(solved) -> None:
    """
    Description:
        An unreadable file and a frame with no board are skipped with their reasons and named in
        the report; the calibration still completes from the rest, and the report counts each kind.
    """

    skipped = {view.Name: view.Detection.Reason for view in solved.Views if not view.Detection.Found}
    assert set(skipped) == {'view_012.png', 'view_013.png'}
    assert 'could not be read' in skipped['view_012.png']
    assert 'no chessboard' in skipped['view_013.png']
    lines = Report_Lines(solved)
    assert any('view_013.png' in line and 'SKIPPED' in line for line in lines)
    assert lines[0].startswith('[INFO] Images: 13') and '3 flat' in lines[0] and '8 tilted' in lines[0]
    assert 'skipped: 2' in lines[0]


def test_an_all_frontal_set_warns_that_it_is_unreliable(render) -> None:
    """
    Description:
        Five flat boards at different places — many views, none tilted — trigger the tilt
        warning: the principal point is not determined by frontal views, however many.
    """

    views = _Flats(render) + [('flat_004.png', render([0, 0, 0.1], (-25, 12))),
                              ('flat_005.png', render([0, 0, -0.1], (25, -12)))]
    report = Calibrate(views, CONST_RENDER_SQUARE, 0.0, CONST_SQUARES)
    assert report.Tilted_Views == 0 and 'unreliable' in report.Tilt_Warning
    assert any(line.startswith('[WARNING]') and 'tilted' in line for line in Report_Lines(report))


def test_factor_from_undistorted_corners_is_right_where_raw_corners_are_not(render, solved) -> None:
    """
    Description:
        The factor from the flat views' UNDISTORTED corners matches the table plane's true mm/px in
        the application's alpha = 1 pixel space within 0.1 %; the old method — mean raw corner
        spacing on the distorted board — is off by more than 0.5 % on the same view.
    """

    truth = _True_Factor()
    for measured, true in zip(solved.Factor, truth):
        assert abs(measured / true - 1.0) < 0.001
    detection = Detect_Board(_Flats(render)[0][1])
    grid = detection.Corners.reshape(detection.Grid[1], detection.Grid[0], 2)
    spacing = np.concatenate([np.linalg.norm(np.diff(grid, axis=a), axis=2).ravel() for a in (0, 1)])
    raw = CONST_RENDER_SQUARE / spacing.mean()
    assert abs(raw / truth[0] - 1.0) > 0.005
    assert all(view.Factor is not None for view in solved.Views if view.Flat and view.Detection.Found)
    assert all(view.Factor is None for view in solved.Views if not view.Flat)


def test_no_flat_view_fails_loudly(render) -> None:
    """
    Description:
        A set with only tilted views raises instead of deriving a factor from tilted boards.
    """

    with pytest.raises(Calibration_Error_Cls, match='flat'):
        Calibrate(_Tilted(render), CONST_RENDER_SQUARE, 0.0, CONST_SQUARES)


def test_result_goes_to_a_new_file_and_leaves_the_configuration_in_force(tmp_path, solved) -> None:
    """
    Description:
        Writing a solved calibration to a new file copies the source's header, regenerates the
        block with the solve's record (views, RMS, square size, board height), reads back through
        the configuration layer, and leaves the source byte-for-byte unchanged.
    """

    import yaml
    source = tmp_path / 'Config_test.yaml'
    shutil.copy(CONST_BASLER_CONFIG_FILE, source)
    before = source.read_bytes()
    output = tmp_path / 'Config_test_calib-1.yaml'
    record = {'date': '2026-09-23T10:00:00', 'images': str(tmp_path), 'rms_px': solved.Rms_Px,
              'views': {'total': 11, 'flat': 3, 'tilted': 8}, 'square_mm': 12.0, 'board_height_mm': 4.5}
    assert Write_Calibration(Calibration_Parameters(solved), str(source), output_path=str(output),
                             record=record)
    assert source.read_bytes() == before
    written = yaml.safe_load(output.read_text())['Camera']['Calibration']
    assert written['Solved']['Views'] == {'Total': 11, 'Flat': 3, 'Tilted': 8}
    assert written['Solved']['Board_Height_Mm'] == 4.5 and written['Solved']['Square_Size_Mm'] == 12.0
    scale = Read_Conversion_Factor(str(output))
    assert (scale.Mm_Per_Px_X, scale.Mm_Per_Px_Y) == pytest.approx(solved.Factor)
    assert Read_Configuration(str(output)).Calibration.K[0, 2] == pytest.approx(solved.K[0, 2])


def test_images_harness_writes_a_new_file_and_says_adoption_is_separate(tmp_path, monkeypatch,
                                                                        render, capsys) -> None:
    """
    Description:
        'calibrate.py --images DIR' prints the report, writes the result to a new
        '<config>_calib-<date>.yaml', leaves the configuration in force untouched and says that
        adopting it is a separate step (run.py hardcodes its path). An all-tilted directory fails
        with exit code 1 and no file.
    """

    spec = importlib.util.spec_from_file_location(
        'calibrate', os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Camera', 'calibrate.py'))
    calibrate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calibrate)
    config = tmp_path / 'Config_test.yaml'
    shutil.copy(CONST_BASLER_CONFIG_FILE, config)
    before = config.read_bytes()
    monkeypatch.setattr(calibrate, 'CONST_BASLER_CONFIG_FILE', str(config))
    images = tmp_path / 'images'
    images.mkdir()
    for name, image in _Flats(render) + _Tilted(render):
        cv2.imwrite(str(images / name), image)

    assert calibrate.Images_Main(str(images), CONST_SQUARES, 12.0, 0.0, False) == 0
    out = capsys.readouterr().out
    assert 'PRINCIPAL POINT' in out and 'run.py hardcodes its path' in out and 'Caliper' in out
    assert config.read_bytes() == before
    written = [name for name in os.listdir(tmp_path) if name.startswith('Config_test_calib-')]
    assert len(written) == 1

    for name in os.listdir(images):
        if name.startswith('flat_'):
            os.remove(images / name)
    assert calibrate.Images_Main(str(images), CONST_SQUARES, 12.0, 0.0, False) == 1
    assert '[ERROR]' in capsys.readouterr().out
    assert len([n for n in os.listdir(tmp_path) if n.startswith('Config_test_calib-')]) == 1
