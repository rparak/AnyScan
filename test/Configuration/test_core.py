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
# File Name: ../test/Configuration/test_core.py
## =========================================================================== ##

# System (Default)
import os
import re
import json
import shutil
# Typing (Support for type hints)
import typing as tp
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the configuration layer under test, and its structures
#   ../Configuration/Core
import Configuration.Core as Configuration
from Configuration.Core import (Load_Configuration, Configuration_Error_Cls, Write_Calibration,
                                Hardware_And_Mode, Describe_Configuration, Hardware_Record,
                                Discover_Configurations, CONST_DEFAULT_CONFIG_FILE, CONST_FIELDS,
                                CONST_REQUIRED_CUSTOM_CFG_KEYS, CONST_COEFFICIENT_KEYS, CONST_PROJECT_ROOT)
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
#   ../Parameters/Camera
from Parameters.Camera import Camera_Calibration_Parameters_Str

"""
Description:
    Tests for the configuration layer. Each test copies the shipped mode file and its calibration
    into tmp_path, edits the copy, and loads it — so the rules are checked against the real schema:
    a valid file loads end to end; a missing REQUIRED field fails naming it; a missing OPTIONAL
    field takes its documented default and says so; a present but invalid value fails instead of
    defaulting; every problem is reported at once; and the calibration writer cannot delete content
    it does not own.
"""
# The hardware and mode of the shipped configuration, and a copy's file name in tmp_path.
#   Unit [string]
CONST_HARDWARE = 'a2A1920_51gcPRO_Computar_M1228_MPW3'
CONST_COPY_NAME = 'Config_%s_Mode_Test.yaml' % CONST_HARDWARE
# A record of how a calibration was solved, for the writer.
#   Unit [Dict]
CONST_RECORD = {'date': '2026-09-24T10:00:00', 'images': '/tmp/calib',
                'views': {'total': 12, 'flat': 4, 'tilted': 8}, 'rms_px': 0.21,
                'square_mm': 15.0, 'board_height_mm': 3.0}


def _Shipped() -> tp.Tuple[tp.Dict[str, tp.Any], tp.Dict[str, tp.Any]]:
    """The shipped mode file and calibration, parsed."""
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
        mode = yaml.safe_load(f)
    with open(Configuration.Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r',
              encoding='utf-8') as f:
        calibration = yaml.safe_load(f)
    return mode, calibration


def _Write(directory: tp.Any, mode: tp.Dict[str, tp.Any], calibration: tp.Optional[tp.Dict[str, tp.Any]],
           name: str = CONST_COPY_NAME) -> str:
    """Write a mode file (and, unless None, the hardware's calibration) into a directory."""
    path = os.path.join(str(directory), name)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(mode, f, sort_keys=False)
    if calibration is not None:
        with open(os.path.join(str(directory), 'Calibration_%s.yaml' % CONST_HARDWARE), 'w',
                  encoding='utf-8') as f:
            yaml.safe_dump(calibration, f, sort_keys=False)
    return path


def _Delete(data: tp.Dict[str, tp.Any], path: tp.Tuple[str, ...]) -> None:
    """Remove the key at a path from a nested mapping."""
    for key in path[:-1]:
        data = data[key]
    del data[path[-1]]


def _Set(data: tp.Dict[str, tp.Any], path: tp.Tuple[str, ...], value: tp.Any) -> None:
    """Set the key at a path in a nested mapping."""
    for key in path[:-1]:
        data = data[key]
    data[path[-1]] = value


def _Reference_For(directory: tp.Any, mode: tp.Dict[str, tp.Any], K: tp.Optional[tp.Any],
                   coefficients: tp.Optional[tp.Dict[str, float]]) -> None:
    """
    Point a mode file at a copy of the shipped reference image whose sidecar says it was undistorted
    with the given lens model (or, with K None, not undistorted), written by the application's own
    Build_Reference_Sidecar — the reference a configuration with that calibration can use.
    """
    reference = os.path.join(str(directory), 'Image_Background_Test.png')
    shutil.copy(mode['Segmentation']['Background']['Reference']
                if os.path.isabs(mode['Segmentation']['Background']['Reference'])
                else os.path.join(CONST_PROJECT_ROOT, mode['Segmentation']['Background']['Reference']), reference)
    undistortion = None if K is None else {'calibration': 'Calibration_%s.yaml' % CONST_HARDWARE,
                                           'K': [[float(v) for v in row] for row in K],
                                           'coefficients': dict(coefficients)}
    camera = mode['Camera']
    sidecar = Configuration.Build_Reference_Sidecar(
        reference, source='test', shot='2026-09-28T10:00:00', configuration=CONST_COPY_NAME,
        window={'resolution': [camera['Resolution']['x'], camera['Resolution']['y']],
                'offset': [camera['Offset']['x'], camera['Offset']['y']]},
        undistortion=undistortion, hardware={'lighting': camera['Lighting']})
    with open(Configuration.Reference_Sidecar_Path(reference), 'w', encoding='utf-8') as handle:
        json.dump(sidecar, handle)
    mode['Segmentation']['Background']['Reference'] = reference


def test_the_shipped_configuration_loads_end_to_end_with_the_values_the_code_ran_with() -> None:
    """
    Description:
        The shipped mode file and its calibration load into one Configuration_Str, and every value
        that moved from a module constant into the file is the value the constant held — so the
        move changed no behaviour. The file sets every field, so nothing is defaulted and nothing
        is unrecognised.
    """

    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    assert isinstance(config, Configuration_Str)
    assert (config.Hardware, config.Mode) == (CONST_HARDWARE, 'Seg_Anything')
    assert config.Classification_Enabled is False                     # detect-only, as shipped
    assert (config.Identity.Display_Name, config.Identity.Model_Set, config.Identity.Task) == \
        ('Cfg. Segment Anything', 'JIC_AnyScan_All_v1', 'part inspection')
    assert (config.Camera.Model, config.Camera.Lens, config.Camera.Lighting) == \
        ('Basler a2A1920-51gcPRO', 'Computar M1228-MPW3', 'Effilux EFFI-FD-200-200-000')
    assert config.Segmentation.Background_Reference == os.path.join(CONST_PROJECT_ROOT, 'Data', 'Images', 'Background',
                                                                    'Image_Background_001.png')
    assert (config.Confidence.Warn_Below, config.Confidence.Error_Below) == (80, 60)
    seg = config.Segmentation
    assert seg.Model_Path == os.path.join(CONST_PROJECT_ROOT, 'models', 'FastSAM', 'FastSAM-x.pt')
    assert (seg.Device, seg.Confidence, seg.IoU, seg.Image_Size) == ('auto', 0.4, 0.9, 1024)
    assert (seg.Otsu_Floor, seg.Open_Kernel, seg.Dilate, seg.Close_Kernel) == (28, 5, 3, 15)
    assert (seg.Min_Area_Fraction, seg.Hard_Background_Fraction, seg.Background_Area_Fraction,
            seg.Background_Borders) == (5e-4, 0.85, 0.50, 3)
    desc = config.Description
    assert desc.Model_Path == os.path.join(CONST_PROJECT_ROOT, 'models', 'gemma-4-e4b-it-4bit')
    assert (desc.Temperature, desc.Max_Tokens, desc.Background_Crop_Margin,
            desc.Background_Max_Words, desc.Background_Max_Sentences) == (0.0, 256, 0.12, 20, 1)
    assert desc.Prompt_Object.startswith('You are inspecting a single part') and '\n' not in desc.Prompt_Object
    assert desc.Prompt_Background.startswith('This photograph shows an empty work surface')
    assert config.Camera.Custom_Cfg['Exposure_Time'] == 10000
    assert config.Camera.Calibration.K.shape == (3, 3)
    assert set(config.Camera.Calibration.Coefficients) == set(CONST_COEFFICIENT_KEYS)
    assert config.Scale is not None
    assert (config.Scale.Mm_Per_Px_X, config.Scale.Mm_Per_Px_Y) == (0.10189853878198323, 0.10207658577821295)
    assert (config.Camera.Resolution, config.Camera.Offset) == ((1920, 1200), (8, 8))
    assert config.Station_Events_Directory == os.path.join(CONST_PROJECT_ROOT, 'logger', 'Station_Events')
    assert (config.Camera.Calibration.Resolution, config.Camera.Calibration.Offset) == ((1920, 1200), (8, 8))
    # No notes. The two lenient paths this used to expect (a calibration that does not record its window,
    # a reference with no provenance sidecar) ended when the recalibration and the reference made by
    # make_reference.py came into force: a note here now means one of them regressed.
    assert config.Notes == []


@pytest.mark.parametrize('path', [path for path, _a, _k, required in CONST_FIELDS if required]
                         + [('Hardware',), ('Camera', 'Custom_Cfg'), ('Camera', 'Resolution'), ('Camera', 'Offset')]
                         + [('Camera', 'Custom_Cfg', key) for key in CONST_REQUIRED_CUSTOM_CFG_KEYS],
                         ids=lambda path: '.'.join(path))
def test_a_missing_required_field_fails_the_load_naming_it(tmp_path: tp.Any, path: tp.Tuple[str, ...]) -> None:
    """
    Description:
        Removing any REQUIRED field — the hardware, a model path, a prompt, the camera's
        acquisition block or one of its settings — fails the load, and the message names the field.
        There is no default to fall back to.
    """

    mode, calibration = _Shipped()
    _Delete(mode, path)
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    named = path[-1] if path[:2] == ('Camera', 'Custom_Cfg') and len(path) == 3 else '.'.join(path)
    assert named in str(error.value)


def test_a_file_without_the_station_event_directory_fails_the_load(tmp_path: tp.Any) -> None:
    """
    Description:
        General.Station_Events.Directory is REQUIRED — named here, not drawn from the field table, so
        making it optional in the table cannot remove the test with it. There is no default directory
        the external system could be reading.
    """

    mode, calibration = _Shipped()
    _Delete(mode, ('General', 'Station_Events', 'Directory'))
    with pytest.raises(Configuration_Error_Cls, match='General.Station_Events.Directory is required but missing'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_a_missing_station_event_directory_fails_the_load_and_is_not_created(tmp_path: tp.Any) -> None:
    """
    Description:
        The station-event directory must exist when the configuration loads — the external system
        depends on its files, so the problem surfaces before a shift, not after it. The loader never
        creates it.
    """

    mode, calibration = _Shipped()
    missing = os.path.join(str(tmp_path), 'share', 'station')
    mode['General']['Station_Events']['Directory'] = missing
    with pytest.raises(Configuration_Error_Cls, match='General.Station_Events.Directory: the directory "%s" does '
                                                      'not exist' % re.escape(missing)):
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert not os.path.exists(missing)


def test_an_unwritable_station_event_directory_fails_the_load(tmp_path: tp.Any) -> None:
    """
    Description:
        A directory that exists but takes no file fails the load too, checked by creating one (permission
        bits mislead on shares); a writable one loads, keeps no trace of the check, and is absolute.
    """

    mode, calibration = _Shipped()
    directory = tmp_path / 'station'
    directory.mkdir()
    mode['General']['Station_Events']['Directory'] = str(directory)
    path = _Write(tmp_path, mode, calibration)
    assert Load_Configuration(path).Station_Events_Directory == str(directory)
    assert os.listdir(str(directory)) == []
    os.chmod(str(directory), 0o500)
    try:
        with pytest.raises(Configuration_Error_Cls, match='General.Station_Events.Directory: the directory .* is '
                                                          'not writable'):
            Load_Configuration(path)
    finally:
        os.chmod(str(directory), 0o700)


@pytest.mark.parametrize('what', ['K'] + ['Coefficients.%s' % key for key in CONST_COEFFICIENT_KEYS])
def test_an_incomplete_calibration_file_fails_the_load_naming_what_is_missing(tmp_path: tp.Any, what: str) -> None:
    """
    Description:
        A calibration file that exists must be complete: without its K or any distortion
        coefficient the load fails, naming what is missing.
    """

    mode, calibration = _Shipped()
    if what == 'K':
        del calibration['Calibration']['K']
    else:
        del calibration['Calibration']['Coefficients'][what.split('.')[1]]
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    expected = {'K': 'Calibration.K'}.get(what) or what.split('.')[1]
    assert expected in str(error.value)


@pytest.mark.parametrize('field', [field for field in CONST_FIELDS if not field[3]],
                         ids=lambda field: '.'.join(field[0]))
def test_a_missing_optional_field_takes_its_documented_default_and_says_so(tmp_path: tp.Any,
                                                                         field: tp.Tuple) -> None:
    """
    Description:
        Removing any OPTIONAL field still loads: the field takes its documented default (the
        Parameters/Configuration field default) and a note naming the field and the default is
        returned for the caller to log.
    """

    path, attribute, _kind, _required = field
    mode, calibration = _Shipped()
    _Delete(mode, path)
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    target, default = config, Configuration_Str()
    for part in attribute[:-1]:
        target, default = getattr(target, part), getattr(default, part)
    assert getattr(target, attribute[-1]) == getattr(default, attribute[-1])
    dotted = '.'.join(path)
    notes = [message for level, message in config.Notes if level == 'INFO' and dotted in message]
    assert notes and 'default' in notes[0] and repr(getattr(default, attribute[-1])) in notes[0]


def _Field_Comments(path: str) -> tp.Dict[tp.Tuple[str, ...], tp.Tuple[str, int]]:
    """
    Description:
        The comment that documents each field of a mode file, as {YAML key path: (comment text,
        position in its group)}. A field's own comment documents it; a field with none takes the
        comment of the group it follows (a comment may cover consecutive fields: 'Defaults: 0.4
        and 0.9'), or of its parent block when the block's comment is the one above it. A block's
        own comment is recorded under the block's path ('REQUIRED, both.' above Prompts).

    Args:
        (1) path [string]: The mode file.

    Returns:
        (1) parameter [Dict]: The documenting comment and group position per key path.
    """

    comments, stack, block_comment, group = {}, [], [], None
    with open(path, 'r', encoding='utf-8') as handle:
        lines = handle.read().splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            block_comment, group = [], None
            continue
        if stripped.startswith('#'):
            block_comment.append(stripped[1:].strip())
            continue
        match = re.match(r'^( *)([A-Za-z_]+):(.*)$', line)
        if match is None:
            continue
        indent, key, value = len(match.group(1)), match.group(2), match.group(3).strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        key_path = tuple(name for _, name in stack) + (key,)
        if block_comment:
            group = [' '.join(block_comment), key_path[:-1] if value else key_path, 0]
        block_comment = []
        if not value:                                         # a block: its children follow
            if group is not None and group[1] == key_path:
                comments[key_path] = (group[0], 0)
            stack.append((indent, key))
            continue
        if group is not None and group[1] == key_path[:len(group[1])]:
            comments[key_path] = (group[0], group[2])
            group[2] += 1
    return comments


def _Documented_Default(text: str, position: int) -> tp.Any:
    """
    Description:
        The default a field comment states ('Default: 0.20', 'Defaults: 0.4 and 0.9', 'Defaults:
        empty.', 'Default: not set (...)'), parsed to the value the code would hold, or None when
        the comment states none.

    Args:
        (1) text [string]: The comment.
        (2) position [int]: The field's position in the comment's group.

    Returns:
        (1) parameter [object or None]: The documented default.
    """

    match = re.search(r'\bDefaults?: (.*?)(?:\.(?:\s|$)|$)', text)
    if match is None:
        return None
    values = [value.strip() for value in match.group(1).split(' and ')]
    word = values[0] if values == ['empty'] else (values[position] if position < len(values) else None)
    if word is None:
        return None
    if word == 'empty' or word.startswith('not set'):
        return ''
    if word in ('true', 'false'):
        return word == 'true'
    for number in (int, float):
        try:
            return number(word)
        except ValueError:
            pass
    return word


def test_every_documented_default_in_the_shipped_mode_file_is_the_code_default() -> None:
    """
    Description:
        The half of the configuration rule the loader cannot see: the shipped mode file documents
        each optional field's default in its comment, and that documented default must be the
        value the code applies when the field is left out (its Parameters/Configuration default).
        A comment that says 'Default: 80' while the code falls back to 70 is a setting that looks
        authoritative and is not. Every optional field documents one; every required field's
        comment says REQUIRED.
    """

    comments = _Field_Comments(CONST_DEFAULT_CONFIG_FILE)
    code_defaults = Configuration_Str()
    for path, attribute, _kind, required in CONST_FIELDS:
        dotted = '.'.join(path)
        assert path in comments, '%s has no comment in the shipped mode file' % dotted
        text, position = comments[path]
        if required:
            said = [comments.get(path[:i], ('', 0))[0] for i in range(1, len(path))] + [text]
            assert any('REQUIRED' in comment for comment in said), \
                '%s is required but neither its comment nor its block\'s says REQUIRED' % dotted
            continue
        documented = _Documented_Default(text, position)
        assert documented is not None, '%s is optional but its comment states no default' % dotted
        code = code_defaults
        for part in attribute:
            code = getattr(code, part)
        assert documented == code, '%s: the comment says %r, the code defaults to %r' % (dotted, documented, code)


@pytest.mark.parametrize('path, value', [
    (('General', 'Classification', 'Enabled'), 'yes'),
    (('Segmentation', 'Confidence'), 1.5),
    (('Segmentation', 'Image_Size'), 0),
    (('Segmentation', 'Device'), 'gpu'),
    (('Segmentation', 'Background', 'Otsu_Floor'), 300),
    (('Segmentation', 'Fusion', 'Min_Area_Fraction'), 0.0),
    (('Description', 'Max_Tokens'), 12.5),
    (('Description', 'Background_Crop_Margin'), 0.5),
    (('Description', 'Prompts', 'Object'), '   '),
    (('Confidence', 'Warn_Below'), 120),
], ids=lambda x: '.'.join(x) if isinstance(x, tuple) else None)
def test_a_present_but_invalid_value_fails_rather_than_defaulting(tmp_path: tp.Any, path: tp.Tuple[str, ...],
                                                                  value: tp.Any) -> None:
    """
    Description:
        A value that is present but wrong fails the load, naming the field — it is never quietly
        replaced by the default, which would run the application on a setting nobody chose.
    """

    mode, calibration = _Shipped()
    _Set(mode, path, value)
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert '.'.join(path) in str(error.value)


def test_every_problem_is_reported_at_once(tmp_path: tp.Any) -> None:
    """
    Description:
        The file is validated as a whole: two missing required fields and an inconsistent pair of
        thresholds are all named in the one error, not just the first.
    """

    mode, calibration = _Shipped()
    del mode['Segmentation']['Model']
    del mode['Description']['Prompts']['Background']
    mode['Confidence'] = {'Warn_Below': 50, 'Error_Below': 70}
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    message = str(error.value)
    assert 'Segmentation.Model' in message and 'Description.Prompts.Background' in message
    assert 'Confidence.Error_Below (70) must be below Confidence.Warn_Below (50)' in message


def test_an_unrecognised_key_is_a_warning_not_a_silent_default(tmp_path: tp.Any) -> None:
    """
    Description:
        A misspelt optional field would otherwise just take the default. It is reported as a
        WARNING note naming the key (and the real field's default note appears beside it).
    """

    mode, calibration = _Shipped()
    mode['Segmentation']['Confidense'] = mode['Segmentation'].pop('Confidence')
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert any(level == 'WARNING' and 'Segmentation.Confidense' in message for level, message in config.Notes)
    assert any(level == 'INFO' and 'Segmentation.Confidence not set' in message for level, message in config.Notes)


def test_the_file_name_and_the_hardware_field_must_agree(tmp_path: tp.Any) -> None:
    """
    Description:
        The hardware keys the calibration and the run-summary CSV, so a copy renamed for another
        camera that still names this one is refused, as is a name without its hardware and mode.
    """

    mode, calibration = _Shipped()
    with pytest.raises(Configuration_Error_Cls, match='Hardware is'):
        Load_Configuration(_Write(tmp_path, mode, calibration, name='Config_Other_Cam_Mode_Test.yaml'))
    with pytest.raises(Configuration_Error_Cls, match='Config_<Hardware>_Mode_<Mode>'):
        Load_Configuration(_Write(tmp_path, mode, calibration, name='Settings.yaml'))
    assert Hardware_And_Mode('/x/Config_A_B_Mode_Seg_Anything.yaml') == ('A_B', 'Seg_Anything')
    assert Hardware_And_Mode('/x/Config_A_B.yaml') == ('A_B', '')


def test_the_conversion_factor_is_optional_but_never_invented(tmp_path: tp.Any) -> None:
    """
    Description:
        Without a Conversion_Factor the configuration loads with no scale (objects are not
        measured) and a WARNING says so; a factor that is present but not positive fails the load.
    """

    mode, calibration = _Shipped()
    del calibration['Calibration']['Conversion_Factor']
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert config.Scale is None
    assert any(level == 'WARNING' and 'Conversion_Factor' in message for level, message in config.Notes)

    calibration['Calibration']['Conversion_Factor'] = {'x': -0.1, 'y': 0.1}
    with pytest.raises(Configuration_Error_Cls, match='Conversion_Factor'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_two_modes_on_one_hardware_share_its_calibration(tmp_path: tp.Any) -> None:
    """
    Description:
        The calibration lives once, per hardware: two mode files on the same camera read the same
        calibration file, so recalibrating updates both and neither can keep a stale scale.
    """

    mode, calibration = _Shipped()
    first = _Write(tmp_path, mode, calibration, name='Config_%s_Mode_A.yaml' % CONST_HARDWARE)
    second = _Write(tmp_path, mode, None, name='Config_%s_Mode_B.yaml' % CONST_HARDWARE)
    a, b = Load_Configuration(first), Load_Configuration(second)
    assert a.Calibration_Path == b.Calibration_Path
    assert a.Scale == b.Scale and (a.Mode, b.Mode) == ('A', 'B')


def _Solved() -> Camera_Calibration_Parameters_Str:
    """A solved calibration with distinct, recognisable values."""
    return Camera_Calibration_Parameters_Str(
        K=np.array([[4000.0, 0.0, 960.0], [0.0, 4000.0, 600.0], [0.0, 0.0, 1.0]]),
        Coefficients={'k1': -0.1, 'k2': 0.2, 'p1': 0.001, 'p2': 0.002, 'k3': -0.3},
        Conversion_Factor={'x': 0.1, 'y': 0.1001}, Resolution=(1920, 1200), Offset=(8, 8))


def test_the_calibration_writer_output_loads_back(tmp_path: tp.Any) -> None:
    """
    Description:
        A calibration written over the one in force keeps its header comment and loads back through
        the configuration layer with the solved values.
    """

    mode, calibration = _Shipped()
    # The reference must have been undistorted with the lens model written below, or the load is
    # (rightly) refused: a new calibration needs a new reference.
    solved = _Solved()
    _Reference_For(tmp_path, mode, solved.K, solved.Coefficients)
    config_path = _Write(tmp_path, mode, calibration)
    in_force = Configuration.Calibration_Path_For(config_path, CONST_HARDWARE)
    shutil.copy(Configuration.Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), in_force)
    assert Write_Calibration(solved, hardware=CONST_HARDWARE, header_source=in_force,
                             output_path=in_force, record=CONST_RECORD)
    with open(in_force, 'r', encoding='utf-8') as f:
        assert f.read().startswith('## ====')                        # the header survived
    config = Load_Configuration(config_path)
    assert config.Camera.Calibration.K[0, 0] == 4000.0
    assert (config.Scale.Mm_Per_Px_X, config.Scale.Mm_Per_Px_Y) == (0.1, 0.1001)
    # It records its window, which matches the camera's: no warning about an unknown window.
    assert (config.Camera.Calibration.Resolution, config.Camera.Calibration.Offset) == ((1920, 1200), (8, 8))
    assert not [message for _level, message in config.Notes if 'sensor window' in message]


def test_the_calibration_writer_refuses_a_calibration_without_its_window(tmp_path: tp.Any) -> None:
    """
    Description:
        A new calibration must say which pixels it is in: one without Resolution and Offset is
        refused, and nothing is written.
    """

    unrecorded = _Solved()
    unrecorded.Resolution = unrecorded.Offset = None
    target = tmp_path / ('Calibration_%s.yaml' % CONST_HARDWARE)
    assert not Write_Calibration(unrecorded, hardware=CONST_HARDWARE, header_source=None,
                                 output_path=str(target), record=CONST_RECORD)
    assert not target.exists()


@pytest.mark.parametrize('path, value', [
    (('Camera', 'Resolution', 'x'), 0), (('Camera', 'Resolution', 'y'), 1200.5),
    (('Camera', 'Resolution', 'x'), True), (('Camera', 'Offset', 'x'), -8), (('Camera', 'Offset', 'y'), '8')],
    ids=lambda v: str(v))
def test_an_invalid_sensor_window_fails_the_load_naming_it(tmp_path: tp.Any, path: tp.Tuple[str, ...],
                                                           value: tp.Any) -> None:
    """
    Description:
        The window is whole pixels: a size of at least 1, an offset of at least 0. Anything else
        fails the load, naming the field and the value.
    """

    mode, calibration = _Shipped()
    _Set(mode, path, value)
    with pytest.raises(Configuration_Error_Cls, match=r'%s must be a whole number' % re.escape('.'.join(path))):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_a_reference_of_another_size_fails_the_load_naming_both_sizes(tmp_path: tp.Any) -> None:
    """
    Description:
        The reference is validated against the camera's resolution when the configuration loads —
        the camera never takes its size from the reference. A mismatch refuses the configuration
        with both sizes named, instead of surfacing at the first ANALYZE.
    """

    mode, calibration = _Shipped()
    mode['Camera']['Resolution'] = {'x': 1936, 'y': 1216}
    mode['Camera']['Offset'] = {'x': 0, 'y': 0}
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    message = str(error.value)
    assert ('Segmentation.Background.Reference is 1920 × 1200 but Camera.Resolution is 1936 × 1216' in message
            and "reference does not match its camera resolution" in message)


def test_a_calibration_solved_at_another_window_fails_the_load(tmp_path: tp.Any) -> None:
    """
    Description:
        K's principal point and the factor are in the pixels of the window the calibration was
        solved at. Another window — even the same size at another offset — fails the load, naming
        both, rather than producing wrong millimetres.
    """

    mode, calibration = _Shipped()
    calibration['Calibration']['Resolution'] = {'x': 1920, 'y': 1200}
    calibration['Calibration']['Offset'] = {'x': 0, 'y': 0}
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert ('was solved at 1920 × 1200 at offset (0, 0), but Camera.Resolution and Camera.Offset set the '
            'camera to 1920 × 1200 at offset (8, 8)') in str(error.value)

    calibration['Calibration']['Offset'] = {'x': 8, 'y': 8}
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert not [message for _level, message in config.Notes if 'sensor window' in message]

    del calibration['Calibration']['Offset']
    with pytest.raises(Configuration_Error_Cls, match='Calibration.Offset is required'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_a_misspelt_window_key_is_a_warning(tmp_path: tp.Any) -> None:
    """
    Description:
        Resolution and Offset are read key by key, so a stray key inside them is reported like any
        other unrecognised key rather than ignored.
    """

    mode, calibration = _Shipped()
    mode['Camera']['Resolution']['z'] = 3
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert any('Camera.Resolution.z' in message for level, message in config.Notes if level == 'WARNING')


@pytest.mark.parametrize('path', [('Camera', 'Custom_Cfg', 'Gamma'),
                                  ('Camera', 'Custom_Cfg', 'Balance_Ratios', 'Purple')],
                         ids=lambda path: '.'.join(path))
def test_an_acquisition_setting_the_camera_does_not_read_is_a_warning(tmp_path: tp.Any,
                                                                      path: tp.Tuple[str, ...]) -> None:
    """
    Description:
        Custom_Cfg is a schema like every other block: the camera reads four settings and three
        white-balance channels, so any other key — a 'Gamma:' line, a 'Purple' channel — is
        reported as unrecognised instead of being loaded and silently doing nothing.
    """

    mode, calibration = _Shipped()
    _Set(mode, path, 1.0)
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert any('.'.join(path) in message for level, message in config.Notes if level == 'WARNING')
    assert path[-1] not in config.Camera.Custom_Cfg and path[-1] not in config.Camera.Custom_Cfg['Balance_Ratios']


@pytest.mark.parametrize('path, value, expected', [
    (('Camera', 'Custom_Cfg', 'Gain'), '10', 'a number of at least 0'),
    (('Camera', 'Custom_Cfg', 'Gain'), -1, 'a number of at least 0'),
    (('Camera', 'Custom_Cfg', 'Exposure_Time'), 0, 'a number above 0'),
    (('Camera', 'Custom_Cfg', 'Exposure_Time'), True, 'a number above 0'),
    (('Camera', 'Custom_Cfg', 'Pixel_Format'), '  ', 'non-empty text'),
    (('Camera', 'Custom_Cfg', 'Balance_Ratios'), 'warm', 'a mapping of Red, Green, Blue'),
    (('Camera', 'Custom_Cfg', 'Balance_Ratios', 'Red'), 0, 'a number above 0'),
], ids=lambda item: '.'.join(item) if isinstance(item, tuple) else repr(item))
def test_an_acquisition_setting_of_the_wrong_type_fails_the_load_naming_it(tmp_path: tp.Any, path: tp.Tuple[str, ...],
                                                                           value: tp.Any, expected: str) -> None:
    """
    Description:
        Each acquisition setting is typed, so a value the camera SDK would choke on — a quoted
        gain, a zero exposure, a missing pixel format, a white balance that is not three positive
        ratios — fails at load with the field and what it must be, not deep inside pylon.
    """

    mode, calibration = _Shipped()
    _Set(mode, path, value)
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert '.'.join(path) in str(error.value) and expected in str(error.value)


def test_a_white_balance_without_every_channel_fails_the_load_naming_it(tmp_path: tp.Any) -> None:
    """
    Description:
        The camera sets each of Red, Green and Blue; a white balance missing one fails at load,
        naming the channel.
    """

    mode, calibration = _Shipped()
    _Delete(mode, ('Camera', 'Custom_Cfg', 'Balance_Ratios', 'Blue'))
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert 'Camera.Custom_Cfg.Balance_Ratios is missing the required Blue' in str(error.value)


def test_the_calibration_writer_refuses_to_delete_content_it_does_not_own(tmp_path: tp.Any) -> None:
    """
    Description:
        A calibration file holding a key the writer does not produce — a section someone added, or
        one inside the Calibration block — or belonging to other hardware is left byte-for-byte
        untouched: the write is refused, never regenerated over it.
    """

    target = tmp_path / ('Calibration_%s.yaml' % CONST_HARDWARE)
    for content in ('Hardware: %s\nCalibration:\n  K: [[1,0,0],[0,1,0],[0,0,1]]\nNotes:\n  Lens: cleaned\n'
                    % CONST_HARDWARE,
                    'Hardware: %s\nCalibration:\n  Temperature_C: 21\n' % CONST_HARDWARE,
                    'Hardware: another_camera\nCalibration: {}\n'):
        target.write_text(content)
        assert not Write_Calibration(_Solved(), hardware=CONST_HARDWARE, header_source=None,
                                     output_path=str(target), record=CONST_RECORD)
        assert target.read_text() == content


def test_a_camera_without_a_calibration_file_loads_uncalibrated_with_a_warning(tmp_path: tp.Any) -> None:
    """
    Description:
        The calibration file is optional as a whole — a camera being calibrated for the first time
        has none, and calibrate.py must be able to load its configuration. The configuration loads
        with no lens model and no scale, and a WARNING names the missing file and says to run
        calibrate.py.
    """

    mode, _calibration = _Shipped()
    _Reference_For(tmp_path, mode, None, None)          # shot uncalibrated, as a first camera's would be
    config = Load_Configuration(_Write(tmp_path, mode, None))
    assert config.Camera.Calibration is None and config.Scale is None
    (warning,) = [message for level, message in config.Notes if level == 'WARNING' and 'calibration file' in message]
    assert 'Calibration_%s.yaml' % CONST_HARDWARE in warning and 'calibrate.py' in warning


def test_the_background_reference_must_exist(tmp_path: tp.Any) -> None:
    """
    Description:
        The reference decides every background-subtraction result, so it is REQUIRED and its file
        must exist: a path to nothing fails the load, naming the field.
    """

    mode, calibration = _Shipped()
    mode['Segmentation']['Background']['Reference'] = 'Data/Images/Background/Image_Background_999.png'
    with pytest.raises(Configuration_Error_Cls, match='Segmentation.Background.Reference'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


@pytest.mark.parametrize('model, lens, lighting, expected', [
    ('Basler a2A1920-51gcPRO', 'Computar M1228-MPW3', 'Effilux EFFI-FD-200-200-000',
     'Model set JIC_AnyScan_All_v1 on a Basler a2A1920-51gcPRO with a Computar M1228-MPW3 lens, lit by an '
     'Effilux EFFI-FD-200-200-000.'),
    ('Basler a2A1920-51gcPRO', '', '', 'Model set JIC_AnyScan_All_v1 on a Basler a2A1920-51gcPRO.'),
    ('', 'Computar M1228-MPW3', '', 'Model set JIC_AnyScan_All_v1 with a Computar M1228-MPW3 lens.'),
    ('Allied Vision Alvium 1800', '', 'Effilux EFFI-FD', 'Model set JIC_AnyScan_All_v1 on an Allied Vision Alvium '
     '1800, lit by an Effilux EFFI-FD.'),
    ('', '', '', 'Model set JIC_AnyScan_All_v1.'),
])
def test_the_configuration_sentence_leaves_out_what_is_not_set(model: str, lens: str, lighting: str,
                                                               expected: str) -> None:
    """
    Description:
        The dialog's confirmation is built from the configuration's own fields: every clause the
        configuration can fill is there, one it cannot is left out whole — never a dangling
        'with a  lens' — and the article follows the word ('an Allied', 'an Effilux').
    """

    import dataclasses
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    config = dataclasses.replace(config, Camera=dataclasses.replace(config.Camera, Model=model, Lens=lens,
                                                                    Lighting=lighting))
    assert Describe_Configuration(config) == expected
    assert Hardware_Record(config) == {'hardware': CONST_HARDWARE, 'camera': model, 'lens': lens,
                                       'lighting': lighting}


def test_discovery_lists_usable_configurations_and_says_why_the_others_are_not(tmp_path: tp.Any) -> None:
    """
    Description:
        Every Config_*_Mode_*.yaml is loaded through the one reader: the usable ones come back with
        their configuration, ordered by display name; an unloadable one comes back with the reason
        (so the dialog can log it rather than show it); anything else in the directory is ignored.
    """

    mode, calibration = _Shipped()
    _Write(tmp_path, mode, calibration, name='Config_%s_Mode_Zeta.yaml' % CONST_HARDWARE)
    mode['Identity']['Display_Name'] = 'Cfg. Alpha'
    _Write(tmp_path, mode, None, name='Config_%s_Mode_Alpha.yaml' % CONST_HARDWARE)
    del mode['Identity']['Model_Set']
    _Write(tmp_path, mode, None, name='Config_%s_Mode_Broken.yaml' % CONST_HARDWARE)
    (tmp_path / 'notes.yaml').write_text('Hardware: x\n')
    found = Discover_Configurations(str(tmp_path))
    assert [(c.Identity.Display_Name if c else None) for _p, c, _e in found] == \
        ['Cfg. Alpha', 'Cfg. Segment Anything', None]
    assert 'Identity.Model_Set is required but missing' in found[2][2]
    assert Discover_Configurations(str(tmp_path / 'nowhere')) == []


def _Reference_Copy(tmp_path: tp.Any, mode: tp.Dict[str, tp.Any], calibration: tp.Dict[str, tp.Any],
                    sidecar: tp.Optional[tp.Dict[str, tp.Any]] = 'default') -> tp.Tuple[str, str]:
    """
    Description:
        Copy the shipped reference into tmp_path, point the mode file at it and, unless None, write a
        sidecar beside it — by default the one make_reference.py would write for a reference shot at
        the shipped window, undistorted with the shipped calibration, under the shipped lighting.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (the mode file, the reference copy).
    """

    reference = os.path.join(str(tmp_path), 'Image_Background_002.png')
    shutil.copyfile(os.path.join(CONST_PROJECT_ROOT, 'Data', 'Images', 'Background', 'Image_Background_001.png'), reference)
    mode['Segmentation']['Background']['Reference'] = reference
    if sidecar == 'default':
        block = calibration['Calibration']
        sidecar = Configuration.Build_Reference_Sidecar(
            reference, source='logger/captures/c/s_raw.png', shot='2026-09-25T09:00:00', configuration=CONST_COPY_NAME,
            window={'resolution': [1920, 1200], 'offset': [8, 8]},
            undistortion={'calibration': 'Calibration_%s.yaml' % CONST_HARDWARE, 'K': block['K'],
                          'coefficients': block['Coefficients']},
            hardware={'camera': 'Basler a2A1920-51gcPRO', 'lens': 'Computar M1228-MPW3',
                      'lighting': 'Effilux EFFI-FD-200-200-000'})
    if sidecar is not None:
        with open(Configuration.Reference_Sidecar_Path(reference), 'w', encoding='utf-8') as handle:
            json.dump(sidecar, handle)
    return _Write(tmp_path, mode, calibration), reference


def test_a_reference_without_a_sidecar_loads_with_a_warning_naming_what_is_unknown(tmp_path: tp.Any) -> None:
    """
    Description:
        The reference in force predates sidecars: it loads, with a WARNING that the window, calibration
        and lighting it was shot under are unknown and that make_reference.py writes the record. (The
        leniency ends once a reference made by the tool is in force; see __Check_Reference_Sidecar.)
    """

    mode, calibration = _Shipped()
    config = Load_Configuration(_Reference_Copy(tmp_path, mode, calibration, sidecar=None)[0])
    (warning,) = [message for level, message in config.Notes if 'sidecar' in message]
    assert 'no provenance sidecar' in warning and 'make_reference.py' in warning


def test_a_reference_whose_sidecar_matches_loads_silently(tmp_path: tp.Any) -> None:
    """
    Description:
        A reference shot at the camera's window, undistorted with the calibration in force, under the
        configuration's lighting: no sidecar note at all.
    """

    mode, calibration = _Shipped()
    config = Load_Configuration(_Reference_Copy(tmp_path, mode, calibration)[0])
    assert not [message for _level, message in config.Notes if 'Image_Background_002' in message]


@pytest.mark.parametrize('change, words', [
    (lambda s: s['window'].update(offset=[0, 0]),
     'was shot at 1920 × 1200 at offset (0, 0), but Camera.Resolution and Camera.Offset set the camera to 1920 × 1200 '
     'at offset (8, 8)'),
    (lambda s: s.update(calibration={'file': 'Calibration_old.yaml', 'fingerprint': '0' * 64}),
     'was undistorted with another lens model (Calibration_old.yaml), but this configuration uses the calibration in force'),
    (lambda s: s.update(calibration=None), 'was undistorted with no calibration'),
    (lambda s: s['hardware'].update(lighting='Effilux EFFI-FD-200-200-000, 45 degree ring'),
     "was shot under lighting 'Effilux EFFI-FD-200-200-000, 45 degree ring', but Camera.Lighting is"),
    (lambda s: s.pop('window'), 'could not be read (KeyError')],
    ids=['window', 'calibration', 'uncalibrated', 'lighting', 'malformed'])
def test_a_reference_shot_under_other_conditions_fails_the_load(tmp_path: tp.Any, change: tp.Any, words: str) -> None:
    """
    Description:
        The sidecar says what the reference was shot under; a window, a lens model or a lighting
        other than the configuration's fails the load, naming both. (Lighting is the weaker check: it
        compares two typed fields, so it fires only when Camera.Lighting was updated.)
    """

    mode, calibration = _Shipped()
    _config, reference = _Reference_Copy(tmp_path, mode, calibration)
    path = Configuration.Reference_Sidecar_Path(reference)
    with open(path, 'r', encoding='utf-8') as handle:
        sidecar = json.load(handle)
    change(sidecar)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(sidecar, handle)
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(os.path.join(str(tmp_path), CONST_COPY_NAME))
    assert words in str(error.value)


def test_a_reference_replaced_under_its_sidecar_fails_the_load(tmp_path: tp.Any) -> None:
    """
    Description:
        The sidecar is bound to one image by its SHA-256: a different image of the same size put in the
        reference's place (a re-shoot copied over it, an edit) does not inherit the old provenance.
    """

    import cv2
    mode, calibration = _Shipped()
    config_path, reference = _Reference_Copy(tmp_path, mode, calibration)
    cv2.imwrite(reference, np.full((1200, 1920, 3), 90, np.uint8))
    with pytest.raises(Configuration_Error_Cls, match='is not the image its sidecar'):
        Load_Configuration(config_path)


def test_the_lighting_check_is_silent_when_the_configuration_names_no_lighting(tmp_path: tp.Any) -> None:
    """
    Description:
        The lighting check can only compare what was typed: a configuration that names no lighting is
        not checked (the documented gap), rather than failing on an empty field.
    """

    mode, calibration = _Shipped()
    del mode['Camera']['Lighting']
    config = Load_Configuration(_Reference_Copy(tmp_path, mode, calibration)[0])
    assert config.Camera.Lighting == ''


def test_the_test_frames_are_resolved_but_never_checked_at_load(tmp_path: tp.Any) -> None:
    """
    Description:
        Evaluation.Frames is harness-only: the application never reads it, so a missing directory
        must not stop the configuration loading — analyze.py checks it. The loader only resolves a
        relative path against the repository root; an absent field is the documented default ''.
    """

    mode, calibration = _Shipped()
    assert Load_Configuration(CONST_DEFAULT_CONFIG_FILE).Evaluation.Frames == os.path.join(
        CONST_PROJECT_ROOT, 'Data', 'Images', 'Test', 'All')
    mode['Evaluation']['Frames'] = 'Data/Images/No_Such_Directory'
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert config.Evaluation.Frames == os.path.join(CONST_PROJECT_ROOT, 'Data', 'Images', 'No_Such_Directory')
    del mode['Evaluation']
    assert Load_Configuration(_Write(tmp_path, mode, calibration)).Evaluation.Frames == ''


def test_writing_a_calibration_twice_over_the_same_file_gives_the_same_file(tmp_path: tp.Any) -> None:
    """
    Description:
        Write_Calibration copies the header comment of the file it writes over and regenerates the
        rest — including the comment above 'Hardware:', which is therefore not header. Writing the
        same result twice gives the same bytes, with that comment once: before this, every write over
        an existing calibration added one more copy of it (the calibration of f5cd075 carried two).
    """

    target = tmp_path / ('Calibration_%s.yaml' % CONST_HARDWARE)
    shutil.copy(Configuration.Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), target)
    written = []
    for _ in range(2):
        assert Write_Calibration(_Solved(), hardware=CONST_HARDWARE, header_source=str(target),
                                 output_path=str(target), record=CONST_RECORD)
        written.append(target.read_text(encoding='utf-8'))
    assert written[0] == written[1]
    assert written[1].count(Configuration.CONST_CALIBRATION_HARDWARE_COMMENT) == 1
    assert written[1].startswith('## ====') and written[1].endswith('\n')
