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
# File Name: ../test/Camera/test_reference_harnesses.py
## =========================================================================== ##

# System (Default)
import os
import re
import json
import shutil
import hashlib
import importlib.util
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Custom Lib.: AnyScan
#   ../Configuration/Core
from Configuration.Core import (Load_Configuration, Load_Configuration_For_Reference, Load_Station_Camera,
                                Build_Reference_Sidecar, Reference_Sidecar_Path, Configuration_Error_Cls,
                                CONST_DEFAULT_CONFIG_FILE)

"""
Description:
    Tests for the two harnesses a reference or a test frame could come from.

    make_reference.py shoots a background reference through the application's camera path, checks it with
    the application's own stages 1 to 3, and writes it with its sidecar. A stand-in camera delivers the frames
    and a stand-in FastSAM finds nothing (as the real one does on the empty table); the slow test runs the
    real FastSAM. Its first run on the rig is checklist item 2.

    scan.py now captures through the application's camera path; a stand-in camera checks that it
    does, and that it saves what that path delivers.
"""
# The project root, the hardware, and a small window for the stand-in capture set.
#   Unit [string] / [Vector<int> 1x2]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONST_HARDWARE = 'a2A1920_51gcPRO_Computar_M1228_MPW3'
CONST_WINDOW = {'resolution': [64, 40], 'offset': [8, 8]}
CONST_HARDWARE_RECORD = {'hardware': CONST_HARDWARE, 'camera': 'Basler a2A1920-51gcPRO',
                         'lens': 'Computar M1228-MPW3', 'lighting': 'Effilux EFFI-FD-200-200-000'}


def _Load_Script(name: str) -> tp.Any:
    """Load an Example/Camera script as a module."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Camera',
                                                                     name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _Shipped_Calibration() -> tp.Dict[str, tp.Any]:
    """The shipped calibration's block (K and coefficients): the one the shipped station names."""
    with open(Load_Station_Camera(CONST_DEFAULT_CONFIG_FILE).Calibration_Path, 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)['Calibration']


def _Configuration_For(directory: tp.Any, reference: str) -> str:
    """The shipped mode file copied into a directory, and its station and calibration rewritten in the test's
    Configuration/ (configuration_root): both set to CONST_WINDOW, and the station naming the reference."""
    shipped = Load_Station_Camera(CONST_DEFAULT_CONFIG_FILE)
    with open(shipped.Station_Path, 'r', encoding='utf-8') as handle:
        station = yaml.safe_load(handle)
    station['Camera']['Resolution'] = dict(zip('xy', CONST_WINDOW['resolution']))
    station['Camera']['Offset'] = dict(zip('xy', CONST_WINDOW['offset']))
    station['Background']['Reference'] = reference
    path = os.path.join(str(directory), 'Config_%s_Mode_Test.yaml' % CONST_HARDWARE)
    shutil.copy(CONST_DEFAULT_CONFIG_FILE, path)
    with open(shipped.Station_Path, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(station, handle, sort_keys=False)
    # The shipped lens model, recorded as solved at CONST_WINDOW: a calibration records its window,
    # and a station setting the camera to another one is refused.
    with open(shipped.Calibration_Path, 'r', encoding='utf-8') as handle:
        calibration = yaml.safe_load(handle)
    calibration['Calibration']['Resolution'] = dict(zip('xy', CONST_WINDOW['resolution']))
    calibration['Calibration']['Offset'] = dict(zip('xy', CONST_WINDOW['offset']))
    with open(shipped.Calibration_Path, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(calibration, handle, sort_keys=False)
    return path


def _In_Force(directory: tp.Any, value: int) -> str:
    """
    Description:
        The reference in force: a uniform frame at CONST_WINDOW with the sidecar the configuration accepts
        (written by the configuration layer's own Build_Reference_Sidecar, undistorted with the shipped lens
        model).

    Returns:
        (1) parameter [string]: The image's path.
    """

    path = os.path.join(str(directory), 'Image_Background_001.png')
    cv2.imwrite(path, np.full((CONST_WINDOW['resolution'][1], CONST_WINDOW['resolution'][0], 3), value, np.uint8))
    block = _Shipped_Calibration()
    sidecar = Build_Reference_Sidecar(
        path, source='camera', frames=8, shot='2026-10-13T09:00:00', configuration='test', station='test',
        window=CONST_WINDOW, undistortion={'calibration': 'test', 'K': block['K'], 'coefficients': block['Coefficients']},
        hardware=CONST_HARDWARE_RECORD, compared_with=None, not_compared='test')
    with open(Reference_Sidecar_Path(path), 'w', encoding='utf-8') as handle:
        json.dump(sidecar, handle)
    return path


class _Camera_Cls(object):
    """A stand-in for the application's camera: it delivers the given frames (BGR in, RGB out, as the real one)."""

    def __init__(self, frames: tp.List[tp.Any]) -> None:
        self.frames, self.calls = list(frames), []
        block = _Shipped_Calibration()
        self.Window = {key: list(value) for key, value in CONST_WINDOW.items()}
        self.Last_Undistortion = {'calibration': 'Calibration_%s_Test.yaml' % CONST_HARDWARE, 'K': block['K'],
                                  'coefficients': block['Coefficients']}

    def Set_Configuration(self, Camera_Configuration_Str: tp.Any, configuration_name: str,
                          calibration_name: str) -> None:
        self.calls.append(('configure', tuple(Camera_Configuration_Str.Resolution), calibration_name))

    def Set_Log_Callback(self, callback: tp.Any) -> None:
        pass

    def Connect(self) -> None:
        self.calls.append('connect')

    def Capture(self) -> tp.Any:
        return self.frames.pop(0)[..., ::-1].copy()

    def Disconnect(self) -> None:
        self.calls.append('disconnect')


class _Segmenter_Cls(object):
    """A stand-in FastSAM that finds nothing: the empty table, as the real one returns it (rig, 2026-10-13)."""

    def __init__(self, *args: tp.Any) -> None:
        self.seen = []

    def Load(self) -> None:
        pass

    def Segment(self, image: tp.Any) -> tp.Tuple[tp.List, tp.List]:
        self.seen.append(image)
        return [], []

    def Release(self) -> None:
        pass


def _Frames(value: int = 70, seed: int = 0) -> tp.List[tp.Any]:
    """Eight frames of an empty table at CONST_WINDOW: a uniform grey with sensor noise of a few levels (BGR)."""
    rng = np.random.default_rng(seed)
    w, h = CONST_WINDOW['resolution']
    return [np.clip(value + rng.integers(-3, 4, (h, w, 3)), 0, 255).astype(np.uint8) for _ in range(8)]


def _Station(mode: str) -> str:
    """The station file a mode names (in the test's Configuration/)."""
    return Load_Station_Camera(mode).Station_Path


def test_a_reference_is_the_mean_of_eight_frames_and_loads_with_its_provenance(tmp_path, configuration_root) -> None:
    """
    Description:
        The tool shoots eight frames through the camera, writes their rounded mean as the next free
        Image_Background_NNN.png, and a sidecar recording the camera's window and lens model, the station, the
        frame count and the reference in force it was compared with. A station naming the new reference loads.
    """

    make_reference = _Load_Script('make_reference')
    references = tmp_path / 'Background'
    references.mkdir()
    in_force = _In_Force(references, 70)
    mode = _Configuration_For(tmp_path, in_force)
    configuration, problems = Load_Configuration_For_Reference(mode)
    assert problems == []
    frames = _Frames()
    camera = _Camera_Cls(frames)
    output, sidecar = make_reference.Make_Reference(camera, configuration, problems, _Segmenter_Cls(), str(references))

    assert output == str(references / 'Image_Background_002.png')
    assert camera.calls == ['connect', 'disconnect'] and camera.frames == []
    expected = np.rint(np.stack(frames).astype(np.float64).mean(axis=0)).astype(np.uint8)
    assert np.array_equal(cv2.imread(output), expected)
    with open(Reference_Sidecar_Path(output)) as handle:
        assert json.loads(handle.read()) == sidecar
    assert (sidecar['source'], sidecar['frames'], sidecar['window']) == ('camera', 8, CONST_WINDOW)
    assert sidecar['station'] == os.path.basename(_Station(mode))
    assert sidecar['calibration']['file'] == 'Calibration_%s_Test.yaml' % CONST_HARDWARE
    assert sidecar['compared_with']['reference'].endswith('Image_Background_001.png')
    with open(in_force, 'rb') as handle:
        assert sidecar['compared_with']['image_sha256'] == hashlib.sha256(handle.read()).hexdigest()
    assert 'not_compared' not in sidecar

    Load_Configuration(_Configuration_For(tmp_path, output))


def test_the_mean_is_rounded_and_never_wraps_at_255() -> None:
    """
    Description:
        The mean is summed wide and rounded to the nearest level: three frames of 255, 255 and 254 are 255 (a
        uint8 sum would wrap to 252 and read 84), and 10, 11 and 11 are 11, not the truncated 10.
    """

    make_reference = _Load_Script('make_reference')
    frames = [np.full((2, 2, 3), value, np.uint8) for value in (255, 255, 254)]
    assert make_reference.Average_Frames(frames).tolist() == np.full((2, 2, 3), 255).tolist()
    frames = [np.full((2, 2, 3), value, np.uint8) for value in (10, 11, 11)]
    assert make_reference.Average_Frames(frames).dtype == np.uint8
    assert make_reference.Average_Frames(frames).tolist() == np.full((2, 2, 3), 11).tolist()


@pytest.mark.parametrize('in_frames, words', [((1, 2, 3, 4, 5, 6, 7, 8), 'the mean of the 8 frames shows 1 object(s)'),
                                              ((5,), 'frame 5 of 8 shows 1 object(s)')],
                         ids=['in-every-frame', 'in-one-frame'])
def test_an_object_on_the_table_refuses_the_reference_with_nothing_written(tmp_path, configuration_root, in_frames,
                                                                          words) -> None:
    """
    Description:
        A part left on the table never becomes background. Against the reference in force, the mean is checked
        and so is every frame: a part in all eight is in the mean; one in a single frame (a hand passing) is
        faint in the mean (130 / 8 grey levels, under the floor of 28) and is caught in its frame. The refusal
        names where it was seen and the part's box, and nothing is written.
    """

    make_reference = _Load_Script('make_reference')
    references = tmp_path / 'Background'
    references.mkdir()
    mode = _Configuration_For(tmp_path, _In_Force(references, 70))
    configuration, problems = Load_Configuration_For_Reference(mode)
    frames = _Frames()
    for index in in_frames:
        frames[index - 1][10:30, 20:40] = 200
    before = sorted(os.listdir(references))
    with pytest.raises(make_reference.Reference_Error_Cls) as refused:
        make_reference.Make_Reference(_Camera_Cls(frames), configuration, problems, _Segmenter_Cls(), str(references))
    message = str(refused.value)
    assert 'The table is not empty: ' + words + ' that differ from the reference in force' in message
    assert re.search(r'  - 2\d × 2\d px \(\d+\.\d\d % of the frame\) at \(\d+, \d+\), centre', message)
    assert sorted(os.listdir(references)) == before


def test_a_reference_that_no_longer_matches_the_camera_is_not_compared_and_the_sidecar_says_why(
        tmp_path, configuration_root) -> None:
    """
    Description:
        After a new calibration or window the reference in force fails the load, and comparing with it would
        mean nothing. The tool loads anyway, checks with FastSAM alone (a black reference would otherwise read
        the whole grey table as an object), records compared_with null with the reason, and the next name is
        still free.
    """

    make_reference = _Load_Script('make_reference')
    references = tmp_path / 'Background'
    references.mkdir()
    stale = str(references / 'Image_Background_001.png')
    cv2.imwrite(stale, np.zeros((CONST_WINDOW['resolution'][1], CONST_WINDOW['resolution'][0], 3), np.uint8))
    mode = _Configuration_For(tmp_path, stale)
    with pytest.raises(Configuration_Error_Cls, match='has no provenance sidecar'):
        Load_Configuration(mode)
    configuration, problems = Load_Configuration_For_Reference(mode)
    assert len(problems) == 1 and 'has no provenance sidecar' in problems[0]
    segmenter = _Segmenter_Cls()
    output, sidecar = make_reference.Make_Reference(_Camera_Cls(_Frames()), configuration, problems, segmenter,
                                                    str(references))
    assert os.path.basename(output) == 'Image_Background_002.png'
    assert sidecar['compared_with'] is None and 'has no provenance sidecar' in sidecar['not_compared']
    assert len(segmenter.seen) == 9                                     # the mean and each of the eight frames


def _Run_Main(monkeypatch: tp.Any, mode: str, references: tp.Any, frames: tp.List[tp.Any],
              camera: tp.Any = None) -> tp.Tuple[int, tp.Any]:
    """
    Description:
        Run make_reference.py's main() on a mode, with the camera and FastSAM replaced by stand-ins (or the
        given camera class) and the references written to a directory of the test's.

    Returns:
        (1) parameter [Tuple]: (the exit code, the loaded script).
    """

    make_reference = _Load_Script('make_reference')
    monkeypatch.setattr(make_reference, 'Basler_Camera_Cls', camera or (lambda: _Camera_Cls(frames)))
    monkeypatch.setattr(make_reference, 'Fast_Sam_Cls', _Segmenter_Cls)
    monkeypatch.setattr(make_reference, 'CONST_REFERENCE_DIR', str(references))
    monkeypatch.setattr('sys.argv', ['make_reference.py', '--config', mode])
    return make_reference.main(), make_reference


def test_the_station_file_is_not_edited_and_the_line_to_change_is_printed(tmp_path, configuration_root, monkeypatch,
                                                                           capsys) -> None:
    """
    Description:
        Like calibrate.py, the tool never edits the station file: it prints the line of the station file to
        change (Background.Reference, by its number) and the new value, and the station file is byte for byte
        what it was.
    """

    references = tmp_path / 'Background'
    references.mkdir()
    mode = _Configuration_For(tmp_path, _In_Force(references, 70))
    station = _Station(mode)
    with open(station, 'rb') as handle:
        before = handle.read()
    code, _make_reference = _Run_Main(monkeypatch, mode, references, _Frames())
    out = capsys.readouterr().out
    assert code == 0
    with open(station, 'rb') as handle:
        assert handle.read() == before
    line = [number for number, text in enumerate(before.decode('utf-8').splitlines(), 1)
            if text.strip().startswith('Reference:')][0]
    assert '[INFO] The station file was NOT edited' in out
    assert '[INFO] To use the new reference, change line %d of %s to:' % (line, station) in out
    assert '\n        Reference: %s\n' % (references / 'Image_Background_002.png') in out
    assert '[INFO] The mean of 8 frames' in out


def test_a_camera_held_by_another_program_is_named_and_nothing_is_written(tmp_path, configuration_root, monkeypatch,
                                                                          capsys) -> None:
    """
    Description:
        With the AnyScan application connected, the camera is held: the tool says so, through the
        application's own camera path (Basler_Cls refuses an inaccessible device, the camera layer names it),
        says which program to stop, and writes nothing — not 'No Basler camera was detected'.
    """

    pytest.importorskip('pypylon')
    import Camera.Basler as Basler
    import Camera.Core

    def _Held(*args: tp.Any, **kwargs: tp.Any) -> None:
        raise Basler.Basler_In_Use_Error_Cls('a2A1920-51gcPRO at 192.168.1.11 is in use by another program.')

    monkeypatch.setattr(Basler, 'Basler_Cls', _Held)
    references = tmp_path / 'Background'
    references.mkdir()
    mode = _Configuration_For(tmp_path, _In_Force(references, 70))
    before = sorted(os.listdir(references))
    code, _make_reference = _Run_Main(monkeypatch, mode, references, [], camera=Camera.Core.Basler_Camera_Cls)
    out = capsys.readouterr().out
    assert code == 1
    assert ('[ERROR] The camera a2A1920-51gcPRO at 192.168.1.11 is in use by another program. It is held by the '
            'AnyScan application connected to it, or by a camera script still running: press DISCONNECT in AnyScan '
            '(or close the other program), then try again.') in out
    assert 'No Basler camera' not in out and '[ERROR] No reference was written.' in out
    assert sorted(os.listdir(references)) == before


@pytest.mark.parametrize('flag', [['--from', 'logger/captures/c/s_raw.png'], ['--accept-objects'],
                                  ['--output', 'Image_Background_009.png']], ids=['from', 'accept-objects', 'output'])
def test_a_removed_flag_says_what_replaced_it(monkeypatch, capsys, flag) -> None:
    """
    Description:
        --from, --accept-objects and --output are gone: the tool shoots the reference itself, refuses a table
        that is not empty, and always writes the next free name. Each is in someone's shell history, so it is
        refused naming what replaced it, before any camera or model is touched.
    """

    make_reference = _Load_Script('make_reference')
    monkeypatch.setattr(make_reference, 'Basler_Camera_Cls', None)
    monkeypatch.setattr(make_reference, 'Fast_Sam_Cls', None)
    monkeypatch.setattr('sys.argv', ['make_reference.py'] + flag)
    with pytest.raises(SystemExit) as refused:
        make_reference.main()
    message = ' '.join(capsys.readouterr().err.split())
    assert refused.value.code == 2
    assert '%s was removed: make_reference.py now shoots the reference itself' % flag[0] in message
    assert 'refuses it if anything is on the table' in message


def test_found_objects_are_described_so_the_operator_can_find_them() -> None:
    """
    Description:
        Each object the check found is a line with its box, its share of the frame and its region, largest
        first, so the operator can find it on the table.
    """

    make_reference = _Load_Script('make_reference')
    from Parameters.Vision import Detection_Str
    lines = make_reference.Describe_Objects([Detection_Str(Label='', Bbox=(1900, 10, 12, 9)),
                                             Detection_Str(Label='', Bbox=(760, 400, 400, 100)),
                                             Detection_Str(Label='', Bbox=(3, 1180, 10, 14))], [1920, 1200])
    assert lines == ['400 × 100 px (1.74 % of the frame) at (760, 400), centre',
                     '10 × 14 px (0.01 % of the frame) at (3, 1180), bottom-left',
                     '12 × 9 px (0.00 % of the frame) at (1900, 10), top-right']


def test_an_existing_reference_is_never_overwritten_and_the_next_name_is_free(tmp_path) -> None:
    """
    Description:
        References are never overwritten — analyses were made against them. The next name is one above the
        highest Image_Background_NNN, image or sidecar (an orphaned sidecar still takes its number), and a file
        that appears after the name was chosen is refused with nothing left behind.
    """

    make_reference = _Load_Script('make_reference')
    for name in ('Image_Background_001.png', 'Image_Background_004.png', 'Image_Background_006.json',
                 'Image_Background_note.png'):
        (tmp_path / name).write_bytes(b'x')
    assert make_reference.Next_Reference_Path(str(tmp_path)) == str(tmp_path / 'Image_Background_007.png')
    image = np.full((4, 4, 3), 70, np.uint8)
    with pytest.raises(make_reference.Reference_Error_Cls, match='already exists'):
        make_reference.Write_Reference(image, str(tmp_path / 'Image_Background_004.png'), {})
    assert (tmp_path / 'Image_Background_004.png').read_bytes() == b'x'
    with pytest.raises(make_reference.Reference_Error_Cls, match='already exists'):
        make_reference.Write_Reference(image, str(tmp_path / 'Image_Background_006.png'), {})
    assert not (tmp_path / 'Image_Background_006.png').exists()


@pytest.mark.slow
def test_the_check_finds_what_the_application_finds(require_weights, monkeypatch) -> None:
    """
    Description:
        The check is the application's own stages 1 to 3 with the real FastSAM: on the empty table (the
        shipped reference against itself) it finds nothing; on Image_062 it finds every object the
        application's analysis finds, the same boxes; and FastSAM alone, the check used when the reference in
        force no longer matches the camera, finds them too — including the 60 × 40 mm plate the background
        difference does not see.
    """

    configuration = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    require_weights([configuration.Segmentation.Model_Path])
    make_reference = _Load_Script('make_reference')
    import Vision.Core
    monkeypatch.setattr(Vision.Core, 'CONST_DESCRIBER', 'fallback')
    segmenter = make_reference.Fast_Sam_Cls(configuration.Segmentation)
    reference = cv2.imread(configuration.Segmentation.Background_Reference)
    frame = cv2.imread(os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Images', 'Test', 'Image_062.png'))
    try:
        assert make_reference.Find_Objects(reference, reference, segmenter, configuration.Segmentation) == []
        found = make_reference.Find_Objects(frame, reference, segmenter, configuration.Segmentation)
        alone = make_reference.Find_Objects(frame, None, segmenter, configuration.Segmentation)
    finally:
        segmenter.Release()
    analysis = Vision.Core.Vision_Pipeline_Cls(Configuration_Str=configuration).Analyze(
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    assert analysis.Objects
    assert sorted(det.Bbox for det in found) == sorted(det.Bbox for det in analysis.Objects)
    # Without the background cue's union a box can lose a pixel or two at an edge, never an object.
    def _Iou(a: tp.Tuple[int, ...], b: tp.Tuple[int, ...]) -> float:
        w = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
        h = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
        return w * h / float(a[2] * a[3] + b[2] * b[3] - w * h)

    assert len(alone) == len(analysis.Objects)
    assert all(max(_Iou(det.Bbox, app.Bbox) for app in analysis.Objects) >= 0.9 for det in alone)


def test_scan_captures_through_the_application_camera_path(tmp_path, monkeypatch) -> None:
    """
    Description:
        scan.py no longer undistorts on its own without the processing step: it hands the configuration
        to the application's camera (Basler_Camera_Cls — window, processing, undistortion) and saves
        exactly the frame that path delivers, converted from RGB for OpenCV — as a timestamped
        Scan_*.png in its output directory, never into the pinned test set. It scans as the application's
        SCAN does: through Capture_Still, the stillness check, never a single Capture.
    """

    import Camera.Core
    scan = _Load_Script('scan')
    monkeypatch.setattr('sys.argv', ['scan.py'])
    # The claim itself: the name scan.py captures through IS the application's camera class — checked
    # before it is replaced below by a stand-in for the hardware.
    assert scan.Basler_Camera_Cls is Camera.Core.Basler_Camera_Cls
    # And its default output is Data/Results, never the pinned test frames.
    assert os.path.abspath(scan.CONST_OUTPUT_DIR) != os.path.abspath(Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
                                                                     .Evaluation.Frames)
    frame = np.zeros((40, 64, 3), np.uint8)
    frame[..., 0] = 200                                                   # red in RGB
    seen = {}

    class _Camera_Cls(object):
        """A stand-in for the application's Basler camera."""

        def Set_Configuration(self, Camera_Configuration_Str, configuration_name, calibration_name):
            seen['window'] = (Camera_Configuration_Str.Resolution, Camera_Configuration_Str.Offset)

        def Set_Log_Callback(self, callback):
            pass

        def Connect(self):
            seen['connected'] = True

        def Capture(self):
            raise AssertionError('scan.py took a single frame without the stillness check')

        def Capture_Still(self):
            return frame.copy()

        def Disconnect(self):
            seen['disconnected'] = True

    monkeypatch.setattr(scan, 'Basler_Camera_Cls', _Camera_Cls)
    monkeypatch.setattr(scan, 'CONST_OUTPUT_DIR', str(tmp_path / 'Results'))
    assert scan.main() == 0
    (saved_path,) = (tmp_path / 'Results').iterdir()
    assert saved_path.name.startswith('Scan_') and saved_path.suffix == '.png'
    saved = cv2.imread(str(saved_path))
    assert np.array_equal(saved[..., ::-1], frame)
    assert seen == {'window': ((1920, 1200), (8, 8)), 'connected': True, 'disconnected': True}


class _Scan_Camera_Cls(object):
    """A stand-in for the application's camera in scan.py: records which capture it was asked for, and refuses
    Capture_Still for a moving scene when told to."""

    moving = False
    calls = []

    def Set_Configuration(self, Camera_Configuration_Str: tp.Any, configuration_name: str, calibration_name: str) -> None:
        pass

    def Set_Log_Callback(self, callback: tp.Any) -> None:
        pass

    def Connect(self) -> None:
        pass

    def Capture(self) -> np.ndarray:
        self.calls.append('Capture')
        return np.zeros((40, 64, 3), np.uint8)

    def Capture_Still(self) -> np.ndarray:
        import Camera.Core
        self.calls.append('Capture_Still')
        if self.moving:
            raise Camera.Core.Camera_Motion_Error_Cls('Something is moving in the view, so no frame was taken. Keep '
                                                      'hands and parts still on the table, then press SCAN again.')
        return np.zeros((40, 64, 3), np.uint8)

    def Disconnect(self) -> None:
        pass


def test_scan_refuses_a_moving_scene_with_the_applications_message_and_saves_nothing(tmp_path, monkeypatch,
                                                                                     capsys) -> None:
    """
    Description:
        When the stillness check finds the scene still moving, scan.py takes no frame: it prints the application's
        refusal sentence as a WARNING, saves nothing and exits 1.
    """

    scan = _Load_Script('scan')
    monkeypatch.setattr('sys.argv', ['scan.py'])
    monkeypatch.setattr(_Scan_Camera_Cls, 'moving', True)
    monkeypatch.setattr(_Scan_Camera_Cls, 'calls', [])
    monkeypatch.setattr(scan, 'Basler_Camera_Cls', _Scan_Camera_Cls)
    monkeypatch.setattr(scan, 'CONST_OUTPUT_DIR', str(tmp_path / 'Results'))
    assert scan.main() == 1
    assert '[WARNING] Something is moving in the view, so no frame was taken.' in capsys.readouterr().out
    assert _Scan_Camera_Cls.calls == ['Capture_Still'] and not (tmp_path / 'Results').exists()


def test_scan_without_the_stillness_check_takes_one_frame_at_once(tmp_path, monkeypatch, capsys) -> None:
    """
    Description:
        --no-stillness skips the check: one Capture, never Capture_Still, so a moving scene is saved, not refused;
        the flag is named in the script's help.
    """

    scan = _Load_Script('scan')
    monkeypatch.setattr('sys.argv', ['scan.py', '--no-stillness'])
    monkeypatch.setattr(_Scan_Camera_Cls, 'moving', True)
    monkeypatch.setattr(_Scan_Camera_Cls, 'calls', [])
    monkeypatch.setattr(scan, 'Basler_Camera_Cls', _Scan_Camera_Cls)
    monkeypatch.setattr(scan, 'CONST_OUTPUT_DIR', str(tmp_path / 'Results'))
    assert scan.main() == 0
    assert _Scan_Camera_Cls.calls == ['Capture'] and len(list((tmp_path / 'Results').iterdir())) == 1
    monkeypatch.setattr('sys.argv', ['scan.py', '--help'])
    with pytest.raises(SystemExit):
        scan.main()
    assert '--no-stillness' in capsys.readouterr().out


def test_calibrate_refuses_images_without_the_board_height_and_says_what_it_is(tmp_path, monkeypatch, capsys) -> None:
    """
    Description:
        --images requires --board-height-mm. The refusal names the flag and says what the value is
        for — written into the calibration as the reference plane of its mm/px factor — and does not
        claim it changes the result: it is recorded, never applied to the solve.
    """

    calibrate = _Load_Script('calibrate')
    monkeypatch.setattr('sys.argv', ['calibrate.py', '--images', str(tmp_path), '--board-squares', '11x8',
                                     '--square-mm', '20'])
    with pytest.raises(SystemExit) as refused:
        calibrate.main()
    message = ' '.join(capsys.readouterr().err.split())
    assert refused.value.code == 2
    assert '--board-height-mm' in message and 'reference plane' in message
    assert 'each changes the result' not in message


def test_calibrate_refuses_capture_without_the_board_and_says_why(tmp_path, monkeypatch, capsys) -> None:
    """
    Description:
        --capture requires --board-squares: each frame is checked for the whole board, as the solve
        will read it, and the set records the board. The refusal comes before any camera is opened.
    """

    calibrate = _Load_Script('calibrate')
    monkeypatch.setattr(calibrate, 'Basler_Cls', None)
    monkeypatch.setattr('sys.argv', ['calibrate.py', '--capture', str(tmp_path)])
    with pytest.raises(SystemExit) as refused:
        calibrate.main()
    message = ' '.join(capsys.readouterr().err.split())
    assert refused.value.code == 2
    assert '--capture requires --board-squares' in message and 'whole board' in message
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize('script', ['calibrate', 'scan', 'make_reference', 'generate_checkerboard'])
def test_each_camera_script_imports_from_any_working_directory(tmp_path, script) -> None:
    """
    Description:
        The camera scripts find src/ from their own location, so the README's
        'python Example/Camera/calibrate.py ...' from the repository root works as well as running
        them from Example/Camera/. Each is loaded, in a fresh interpreter whose working directory is
        unrelated (tmp_path), up to but not into main().
    """

    import subprocess
    import sys
    path = os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Camera', script + '.py')
    loader = ('import importlib.util; spec = importlib.util.spec_from_file_location("s", %r); '
              'spec.loader.exec_module(importlib.util.module_from_spec(spec))' % path)
    result = subprocess.run([sys.executable, '-c', loader], cwd=str(tmp_path), capture_output=True, text=True,
                            timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
