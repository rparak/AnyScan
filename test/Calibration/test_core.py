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
import re
import sys
import json
import math
import shutil
import importlib.util
# Typing (Support for type hints)
import typing as tp
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
#   ../Configuration/Core — the configuration layer the calibration is written and read through
from Configuration.Core import (Load_Configuration, Load_Station_Camera, Write_Calibration, Calibration_Directory,
                                Reference_Line, Hardware_Record, Build_Reference_Sidecar, Reference_Sidecar_Path,
                                Configuration_Error_Cls, CONST_DEFAULT_CONFIG_FILE)

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
    detection = Detect_Board(frame, CONST_SQUARES)
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

    detection = Detect_Board(np.full((600, 800, 3), 128, np.uint8), CONST_SQUARES)
    assert not detection.Found and 'no chessboard' in detection.Reason
    assert detection.Corners.shape == (0, 2)


def test_detector_reads_a_board_turned_on_its_side_whole() -> None:
    """
    Description:
        The board's whole grid is asked for in the orientation --board-squares gives (columns x
        rows), and a board lying turned 90 deg in the frame is still read whole, not as a fragment,
        with its corners row-major over the grid reported (every adjacent spacing one square).
    """

    frame = cv2.rotate(_Board_Frame(412, 112), cv2.ROTATE_90_CLOCKWISE)
    detection = Detect_Board(frame, CONST_SQUARES)
    assert detection.Found, detection.Reason
    assert sorted(detection.Grid) == [7, 10] and detection.Corners.shape == (70, 2)
    grid = detection.Corners.reshape(detection.Grid[1], detection.Grid[0], 2)
    for axis in (0, 1):
        assert np.abs(np.linalg.norm(np.diff(grid, axis=axis), axis=2) - CONST_SQUARE_PX).max() < 0.1


def test_detector_refuses_a_grid_larger_than_the_board() -> None:
    """
    Description:
        Told the board is smaller than the one in view, the detector refuses the larger grid it
        finds, naming both: object points for the wrong board would solve a wrong lens model.
    """

    detection = Detect_Board(_Board_Frame(412, 112), (8, 6))
    assert not detection.Found
    assert 'larger than the board' in detection.Reason and '7 x 5' in detection.Reason


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

        def __init__(self, config, resolution, offset):
            self.Applied_Settings = {'resolution': tuple(resolution), 'offset': tuple(offset)}

        def Capture(self):
            return next(frames)

    keys = iter(['f', 'x', 't', 'q'])
    monkeypatch.setattr(calibrate, 'Basler_Cls', _Camera_Cls)
    monkeypatch.setattr('builtins.input', lambda prompt='': next(keys))
    assert calibrate.Capture_Main(str(tmp_path), CONST_DEFAULT_CONFIG_FILE, CONST_SQUARES) == 0

    assert sorted(os.listdir(tmp_path)) == ['capture.json', 'flat_001.png', 'view_002.png']
    manifest = json.loads((tmp_path / 'capture.json').read_text())
    assert manifest['distorted'] is True and 'NOT undistorted' in manifest['note']
    # The camera is identified by the configuration's hardware record, not a separate name field.
    assert manifest['hardware'] == Hardware_Record(Load_Configuration(CONST_DEFAULT_CONFIG_FILE))
    flat, view = manifest['frames']
    assert (flat['kind'], flat['board_found'], flat['corners']) == ('flat', True, 70)
    assert (view['kind'], view['board_found']) == ('view', False) and view['reason']
    # The window the camera read back is recorded, so the solve can record it in the calibration.
    assert manifest['window'] == {'resolution': [1920, 1200], 'offset': [8, 8]}
    # The board is recorded, and a set taken with one board is not extended with another.
    assert manifest['board_squares'] == list(CONST_SQUARES)
    keys = iter(['q'])
    assert calibrate.Capture_Main(str(tmp_path), CONST_DEFAULT_CONFIG_FILE, (9, 7)) == 1

    # A set captured at another window is not extended: its frames would be solved together.
    manifest['window'] = {'resolution': [1936, 1216], 'offset': [0, 0]}
    (tmp_path / 'capture.json').write_text(json.dumps(manifest))
    keys = iter(['q'])
    assert calibrate.Capture_Main(str(tmp_path), CONST_DEFAULT_CONFIG_FILE, CONST_SQUARES) == 1


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
    detection = Detect_Board(_Flats(render)[0][1], CONST_SQUARES)
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


def _Make_Reference_Sidecar(mode: str) -> None:
    """
    Description:
        Write the reference sidecar of the station a mode file names, as make_reference.py would for a
        reference shot now: at the station's window, undistorted with the calibration it names (or none),
        under its lighting. A configuration whose reference has no sidecar, or one made under another
        calibration, does not load, so a test that puts a new calibration in force makes the reference again.

    Args:
        (1) mode [string]: The mode file.
    """

    import yaml
    station = Load_Station_Camera(mode)
    with open(station.Station_Path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    camera = data['Camera']
    reference = data['Background']['Reference']
    reference = reference if os.path.isabs(reference) else os.path.join(CONST_PROJECT_FOLDER, reference)
    undistortion = None
    if station.Calibration_Path:
        with open(station.Calibration_Path, 'r', encoding='utf-8') as handle:
            block = yaml.safe_load(handle)['Calibration']
        undistortion = {'calibration': os.path.basename(station.Calibration_Path), 'K': block['K'],
                        'coefficients': block['Coefficients']}
    sidecar = Build_Reference_Sidecar(
        reference, source='camera', frames=1, shot='2026-10-08T09:00:00',
        configuration=os.path.basename(mode), station=os.path.basename(station.Station_Path),
        window={'resolution': [camera['Resolution']['x'], camera['Resolution']['y']],
                'offset': [camera['Offset']['x'], camera['Offset']['y']]},
        undistortion=undistortion,
        hardware={'camera': camera.get('Model', ''), 'lens': camera.get('Lens', ''),
                  'lighting': camera.get('Lighting', '')}, compared_with=None, not_compared='test')
    with open(Reference_Sidecar_Path(reference), 'w', encoding='utf-8') as handle:
        json.dump(sidecar, handle)


def _Configuration_Copy(directory: tp.Any, window: tp.Tuple[int, int]) -> tp.Tuple[str, str, str]:
    """
    A copy of the shipped mode file in a directory, naming the shipped station, which — like the calibration
    it names — lives in the test's Configuration/ (configuration_root): (mode, station, calibration). The
    station sets the camera, and the calibration its recorded window, to the window (width, height) at offset
    (0, 0), with a grey background reference of that size and its sidecar — the configuration the rendered
    960 x 600 boards belong to.
    """
    import yaml
    mode = os.path.join(str(directory), 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Test.yaml')
    shutil.copy(CONST_DEFAULT_CONFIG_FILE, mode)
    shipped = Load_Station_Camera(mode)
    with open(shipped.Station_Path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    reference = os.path.join(str(directory), 'Background_%dx%d.png' % window)
    cv2.imwrite(reference, np.full((window[1], window[0], 3), 90, np.uint8))
    data['Camera']['Resolution'] = {'x': window[0], 'y': window[1]}
    data['Camera']['Offset'] = {'x': 0, 'y': 0}
    data['Background']['Reference'] = reference
    with open(shipped.Station_Path, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    # The calibration records the window it was solved at; a station setting the camera to another is
    # refused, so the copy is recorded at the same window.
    with open(shipped.Calibration_Path, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    data['Calibration']['Resolution'] = {'x': window[0], 'y': window[1]}
    data['Calibration']['Offset'] = {'x': 0, 'y': 0}
    with open(shipped.Calibration_Path, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    _Make_Reference_Sidecar(mode)
    return mode, shipped.Station_Path, shipped.Calibration_Path


def _Name_Calibration(station: str, name: str) -> None:
    """Do what the harness tells the user: set (or add, below Hardware) the station's Calibration line."""
    with open(station, 'r', encoding='utf-8') as handle:
        lines = handle.read().splitlines(True)
    line = Reference_Line(station, 'Calibration') or Reference_Line(station, 'Hardware') + 1
    if Reference_Line(station, 'Calibration'):
        lines[line - 1] = 'Calibration: %s\n' % name
    else:
        lines.insert(line - 1, 'Calibration: %s\n' % name)
    with open(station, 'w', encoding='utf-8') as handle:
        handle.write(''.join(lines))


def _Calibrate_Script() -> tp.Any:
    """Example/Camera/calibrate.py, loaded as a module."""
    spec = importlib.util.spec_from_file_location(
        'calibrate', os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Camera', 'calibrate.py'))
    calibrate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calibrate)
    return calibrate


def test_result_goes_to_a_new_calibration_file_and_leaves_the_one_in_force(tmp_path, configuration_root,
                                                                           solved) -> None:
    """
    Description:
        Writing a solved calibration to a new file copies the header of the calibration in force,
        regenerates the block with the solve's record (views, RMS, square size, board height), and
        leaves the calibration in force, the station file and the mode file byte-for-byte unchanged.
        Named by the station, it reads back through the configuration layer.
    """

    import yaml
    mode, station, in_force = _Configuration_Copy(tmp_path, CONST_RENDER_SIZE)
    before = [open(path, 'rb').read() for path in (mode, station, in_force)]
    output = os.path.join(Calibration_Directory(), 'Calibration_a2A1920_51gcPRO_Computar_M1228_MPW3_20260923-100000.yaml')
    record = {'date': '2026-09-23T10:00:00', 'images': str(tmp_path), 'rms_px': solved.Rms_Px,
              'views': {'total': 11, 'flat': 3, 'tilted': 8}, 'square_mm': 12.0, 'board_height_mm': 4.5}
    assert Write_Calibration(Calibration_Parameters(solved, (0, 0)), hardware='a2A1920_51gcPRO_Computar_M1228_MPW3',
                             header_source=in_force, output_path=output, record=record)
    assert [open(path, 'rb').read() for path in (mode, station, in_force)] == before
    with open(output, 'r', encoding='utf-8') as handle:
        written = yaml.safe_load(handle)['Calibration']
    assert written['Solved']['Views'] == {'Total': 11, 'Flat': 3, 'Tilted': 8}
    # The window the images were solved at: their own size, and the offset they were captured at.
    assert (written['Resolution'], written['Offset']) == ({'x': 960, 'y': 600}, {'x': 0, 'y': 0})
    assert written['Solved']['Board_Height_Mm'] == 4.5 and written['Solved']['Square_Size_Mm'] == 12.0

    _Name_Calibration(station, os.path.basename(output))         # adopt it: the one changed line
    _Make_Reference_Sidecar(mode)                                 # a new calibration needs a new reference
    config = Load_Configuration(mode)
    assert (config.Scale.Mm_Per_Px_X, config.Scale.Mm_Per_Px_Y) == pytest.approx(solved.Factor)
    assert config.Camera.Calibration.K[0, 2] == pytest.approx(solved.K[0, 2])


def test_images_harness_writes_a_new_calibration_and_prints_the_station_line(tmp_path, configuration_root, render,
                                                                            capsys) -> None:
    """
    Description:
        'calibrate.py --images DIR' prints the report and writes the result as a new
        'Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml' in Configuration/Calibration/ — and nothing else: the
        calibration in force, the station file and the mode file are untouched. It prints the station file's
        Calibration line, by number, and the text to set it to; doing exactly that puts the new calibration
        in force. An all-tilted directory fails with exit code 1 and no file.
    """

    calibrate = _Calibrate_Script()
    mode, station, in_force = _Configuration_Copy(tmp_path, CONST_RENDER_SIZE)
    before = [open(path, 'rb').read() for path in (mode, station, in_force)]
    existing = sorted(os.listdir(Calibration_Directory()))
    images = tmp_path / 'images'
    images.mkdir()
    for name, image in _Flats(render) + _Tilted(render):
        cv2.imwrite(str(images / name), image)

    assert calibrate.Images_Main(str(images), CONST_SQUARES, 12.0, 0.0, mode) == 0
    out = capsys.readouterr().out
    assert [open(path, 'rb').read() for path in (mode, station, in_force)] == before
    (written,) = sorted(set(os.listdir(Calibration_Directory())) - set(existing))
    assert re.fullmatch(r'Calibration_a2A1920_51gcPRO_Computar_M1228_MPW3_\d{8}-\d{6}\.yaml', written)
    assert 'PRINCIPAL POINT' in out and 'Caliper' in out
    assert 'The station file was NOT edited: the calibration in force is unchanged (%s).' % os.path.basename(in_force) in out
    assert ('To use the new calibration, change line %d of %s to:\n        Calibration: %s\n'
            % (Reference_Line(station, 'Calibration'), station, written)) in out

    _Name_Calibration(station, written)                           # what the harness said to do
    _Make_Reference_Sidecar(mode)
    assert Load_Configuration(mode).Calibration_Path == os.path.join(Calibration_Directory(), written)

    for name in os.listdir(images):
        if name.startswith('flat_'):
            os.remove(images / name)
    assert calibrate.Images_Main(str(images), CONST_SQUARES, 12.0, 0.0, mode) == 1
    assert '[ERROR]' in capsys.readouterr().out
    assert sorted(os.listdir(Calibration_Directory())) == sorted(existing + [written])


def test_a_set_captured_with_another_board_is_not_solved(tmp_path, capsys) -> None:
    """
    Description:
        capture.json records the board a set was taken with; solving it as another board is refused
        before anything is detected or written, naming both boards.
    """

    calibrate = _Calibrate_Script()
    (tmp_path / 'capture.json').write_text(json.dumps({'board_squares': [9, 7], 'frames': []}))
    assert calibrate.Images_Main(str(tmp_path), CONST_SQUARES, 12.0, 0.0, CONST_DEFAULT_CONFIG_FILE) == 1
    output = capsys.readouterr().out
    assert '9 x 7 board' in output and '11 x 8' in output and 'nothing was solved' in output
    assert sorted(os.listdir(tmp_path)) == ['capture.json']


def test_a_first_calibration_is_a_new_file_and_the_harness_says_the_line_to_add(tmp_path, configuration_root, render,
                                                                               capsys) -> None:
    """
    Description:
        A station with no calibration yet cannot load a mode (nothing loads uncalibrated), but
        'calibrate.py --images' still runs on it: it reads the station's camera alone. It writes the result
        as a new file, leaves the station file unedited, and prints the line to add below Hardware — which,
        added, makes the configuration load calibrated. This is the loop a new camera starts from.
    """

    calibrate = _Calibrate_Script()
    mode, station, in_force = _Configuration_Copy(tmp_path, CONST_RENDER_SIZE)
    with open(station, 'r', encoding='utf-8') as handle:
        text = re.sub(r'(?m)^Calibration: .*\n', '', handle.read())
    with open(station, 'w', encoding='utf-8') as handle:
        handle.write(text)
    for name in os.listdir(Calibration_Directory()):
        os.remove(os.path.join(Calibration_Directory(), name))
    _Make_Reference_Sidecar(mode)                                 # the reference of an uncalibrated camera
    with pytest.raises(Configuration_Error_Cls, match='names no calibration'):
        Load_Configuration(mode)
    images = tmp_path / 'images'
    images.mkdir()
    for name, image in _Flats(render) + _Tilted(render):
        cv2.imwrite(str(images / name), image)

    assert calibrate.Images_Main(str(images), CONST_SQUARES, 12.0, 0.0, mode) == 0
    out = capsys.readouterr().out
    with open(station, 'r', encoding='utf-8') as handle:
        assert handle.read() == text
    (written,) = os.listdir(Calibration_Directory())
    assert ("To use the new calibration, add this line to %s below 'Hardware:' (line %d):\n        Calibration: %s\n"
            % (station, Reference_Line(station, 'Hardware'), written)) in out
    _Name_Calibration(station, written)
    _Make_Reference_Sidecar(mode)                                 # a new calibration needs a new reference
    assert Load_Configuration(mode).Scale is not None


@pytest.mark.parametrize('flag', ['--write-config', '--write-calibration'])
def test_a_removed_flag_says_what_replaced_it(monkeypatch, capsys, flag) -> None:
    """
    Description:
        '--write-config' and '--write-calibration' may be in someone's shell history: each fails with a
        message saying a calibration is never written over and what the harness does instead, not with an
        unrecognised-argument error, and nothing is solved or written.
    """

    calibrate = _Calibrate_Script()
    monkeypatch.setattr(sys, 'argv', ['calibrate.py', '--images', 'x', flag])
    with pytest.raises(SystemExit):
        calibrate.main()
    error = capsys.readouterr().err
    assert '%s was removed: a calibration is never written over' % flag in error
    assert 'prints the line of the station file to change' in error
