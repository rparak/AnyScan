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
import json
import shutil
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
from Configuration.Core import (Load_Configuration, Reference_Sidecar_Path, Calibration_Path_For, Station_Path_For,
                                CONST_DEFAULT_CONFIG_FILE)
#   ../UI/Capture — the capture set's records, as the application writes them
from UI.Capture import Build_Set_Metadata, Distorted_Frame_Record

"""
Description:
    Tests for the two harnesses a reference or a test frame could come from.

    make_reference.py turns a capture set into a background reference and writes its sidecar from the
    set's own records. The sets here are built with the application's record builders
    (Build_Set_Metadata, Distorted_Frame_Record), so the tool reads the format the application writes.
    Its first run on a real set is checklist item 2.

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
    """The shipped calibration's block (K and coefficients)."""
    with open(Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r', encoding='utf-8') as handle:
        return yaml.safe_load(handle)['Calibration']


def _Capture_Set(directory: tp.Any, window: tp.Optional[tp.Dict] = CONST_WINDOW, objects: int = 0,
                 calibrated: bool = True) -> str:
    """
    Description:
        A capture set of the empty table, written as the application writes one: '_raw.png',
        '_objects.json' (Build_Set_Metadata) and, when calibrated, '_distorted.json' with the shipped
        calibration's undistortion record.

    Returns:
        (1) parameter [string]: The set's '_raw.png'.
    """

    from Parameters.Vision import Detection_Str
    prefix = os.path.join(str(directory), '20260925-090000_1')
    size = (64, 40) if window is None else tuple(window['resolution'])
    cv2.imwrite(prefix + '_raw.png', np.full((size[1], size[0], 3), 70, np.uint8))
    found = [Detection_Str(Label='object', Bbox=(1, 1, 5, 5), Sentence='a speck') for _ in range(objects)]
    metadata = Build_Set_Metadata('s1', '20260925-090000_1', '2026-09-25T09:00:00', found, size, 'task', 10, None,
                                  scale=None, configuration='Config_%s_Mode_Test.yaml' % CONST_HARDWARE,
                                  background_reference='Data/Images/Background/Image_Background_001.png',
                                  hardware=CONST_HARDWARE_RECORD, window=window)
    with open(prefix + '_objects.json', 'w', encoding='utf-8') as handle:
        json.dump(metadata, handle)
    if calibrated:
        block = _Shipped_Calibration()
        undistortion = {'configuration': 'Config_%s_Mode_Test.yaml' % CONST_HARDWARE,
                        'calibration': 'Calibration_%s.yaml' % CONST_HARDWARE, 'frame_size': list(size),
                        'K': block['K'], 'coefficients': block['Coefficients'], 'alpha': 1,
                        'new_camera_matrix': block['K']}
        with open(prefix + '_distorted.json', 'w', encoding='utf-8') as handle:
            json.dump(Distorted_Frame_Record('20260925-090000_1', undistortion), handle)
    return prefix + '_raw.png'


def _Configuration_For(directory: tp.Any, reference: str) -> str:
    """The shipped mode file, station file and calibration copied into a directory, the station and the
    calibration set to CONST_WINDOW, and the station naming the reference."""
    with open(Station_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r', encoding='utf-8') as handle:
        station = yaml.safe_load(handle)
    station['Camera']['Resolution'] = dict(zip('xy', CONST_WINDOW['resolution']))
    station['Camera']['Offset'] = dict(zip('xy', CONST_WINDOW['offset']))
    station['Background']['Reference'] = reference
    path = os.path.join(str(directory), 'Config_%s_Mode_Test.yaml' % CONST_HARDWARE)
    shutil.copy(CONST_DEFAULT_CONFIG_FILE, path)
    with open(Station_Path_For(path, CONST_HARDWARE), 'w', encoding='utf-8') as handle:
        yaml.safe_dump(station, handle, sort_keys=False)
    # The shipped lens model, recorded as solved at CONST_WINDOW: a calibration records its window,
    # and a configuration setting the camera to another one is refused.
    with open(Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r', encoding='utf-8') as handle:
        calibration = yaml.safe_load(handle)
    calibration['Calibration']['Resolution'] = dict(zip('xy', CONST_WINDOW['resolution']))
    calibration['Calibration']['Offset'] = dict(zip('xy', CONST_WINDOW['offset']))
    with open(Calibration_Path_For(path, CONST_HARDWARE), 'w', encoding='utf-8') as handle:
        yaml.safe_dump(calibration, handle, sort_keys=False)
    return path


def test_a_reference_made_from_a_capture_set_loads_with_its_provenance(tmp_path) -> None:
    """
    Description:
        From a set of the empty table the tool copies the frame byte for byte and writes a sidecar that
        the configuration layer accepts: the window, the lens model and the lighting come from the set's
        own records, and a configuration pointing at the new reference loads with no sidecar note.
    """

    make_reference = _Load_Script('make_reference')
    raw = _Capture_Set(tmp_path)
    output = str(tmp_path / 'Image_Background_002.png')
    sidecar = make_reference.Make_Reference(raw.replace('_raw.png', '_objects.json'), output)
    assert open(output, 'rb').read() == open(raw, 'rb').read()
    assert sidecar['window'] == CONST_WINDOW and sidecar['hardware']['lighting'] == 'Effilux EFFI-FD-200-200-000'
    assert sidecar['calibration']['file'] == 'Calibration_%s.yaml' % CONST_HARDWARE
    assert json.loads(open(Reference_Sidecar_Path(output)).read()) == sidecar

    config = Load_Configuration(_Configuration_For(tmp_path, output))
    assert not [message for _level, message in config.Notes if 'Image_Background_002' in message]


@pytest.mark.parametrize('arrange, words', [
    (dict(window=None), 'records no sensor window'),
    (dict(objects=2), 'found 2 object(s):\n  - 5 × 5 px (0.98 % of the frame) at (1, 1), top-left')],
    ids=['no-window', 'objects'])
def test_a_set_that_cannot_be_a_reference_is_refused_with_nothing_written(tmp_path, arrange, words) -> None:
    """
    Description:
        A set that records no window (older, or a saved frame) cannot say where on the sensor it was
        shot; a set whose analysis found objects was probably not of an empty table. Both are refused,
        and nothing is written.
    """

    make_reference = _Load_Script('make_reference')
    raw = _Capture_Set(tmp_path, **arrange)
    output = str(tmp_path / 'Image_Background_002.png')
    with pytest.raises(make_reference.Reference_Error_Cls) as error:
        make_reference.Make_Reference(raw, output)
    assert words in str(error.value)
    assert not os.path.exists(output) and not os.path.exists(Reference_Sidecar_Path(output))


def test_spurious_objects_can_be_accepted_and_an_uncalibrated_set_says_so(tmp_path) -> None:
    """
    Description:
        --accept-objects makes the reference anyway; a set from an uncalibrated camera records no lens
        model, so its sidecar's calibration is null (and a calibrated configuration would refuse it).
    """

    make_reference = _Load_Script('make_reference')
    raw = _Capture_Set(tmp_path, objects=1, calibrated=False)
    sidecar = make_reference.Make_Reference(raw, str(tmp_path / 'Image_Background_002.png'), accept_objects=True)
    assert sidecar['calibration'] is None
    # The override is part of the provenance: what was found, and that it was accepted.
    assert sidecar['accepted_objects'] == ['5 × 5 px (0.98 % of the frame) at (1, 1), top-left']


def test_found_objects_are_described_so_an_override_is_informed(tmp_path) -> None:
    """
    Description:
        Noise and a forgotten part read differently: small boxes scattered at the edges against one
        large box in the centre. Each line gives the box, its share of the frame and its region,
        largest first.
    """

    make_reference = _Load_Script('make_reference')
    from UI.Capture import Capture_Object_Str
    lines = make_reference.Describe_Objects([Capture_Object_Str(Bbox=(1900, 10, 12, 9)),
                                             Capture_Object_Str(Bbox=(760, 400, 400, 100)),
                                             Capture_Object_Str(Bbox=(3, 1180, 10, 14))], [1920, 1200])
    assert lines == ['400 × 100 px (1.74 % of the frame) at (760, 400), centre',
                     '10 × 14 px (0.01 % of the frame) at (3, 1180), bottom-left',
                     '12 × 9 px (0.00 % of the frame) at (1900, 10), top-right']


def test_an_existing_reference_is_never_overwritten_and_the_next_name_is_free(tmp_path) -> None:
    """
    Description:
        References are never overwritten — analyses were made against them — and the default output is
        one above the highest Image_Background_NNN.png.
    """

    make_reference = _Load_Script('make_reference')
    for name in ('Image_Background_001.png', 'Image_Background_004.png', 'Image_Background_note.png'):
        (tmp_path / name).write_bytes(b'x')
    assert make_reference.Next_Reference_Path(str(tmp_path)) == str(tmp_path / 'Image_Background_005.png')
    raw = _Capture_Set(tmp_path)
    with pytest.raises(make_reference.Reference_Error_Cls, match='already exists'):
        make_reference.Make_Reference(raw, str(tmp_path / 'Image_Background_004.png'))
    assert (tmp_path / 'Image_Background_004.png').read_bytes() == b'x'


def test_scan_captures_through_the_application_camera_path(tmp_path, monkeypatch) -> None:
    """
    Description:
        scan.py no longer undistorts on its own without the processing step: it hands the configuration
        to the application's camera (Basler_Camera_Cls — window, processing, undistortion) and saves
        exactly the frame that path delivers, converted from RGB for OpenCV — as a timestamped
        Scan_*.png in its output directory, never into the pinned test set.
    """

    import Camera.Core
    scan = _Load_Script('scan')
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
