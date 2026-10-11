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
import sys
import json
import copy
import glob
import shutil
import subprocess
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
                                Discover_Configurations, Load_Catalogue, Scale_At_Height, Config_Sources_Log_Line,
                                CONST_DEFAULT_CONFIG_FILE, CONST_FIELDS, CONST_CATALOGUE_FIELDS,
                                CONST_CATALOGUE_BLOCK_FIELDS, CONST_STATION_FIELDS, Station_Path_For,
                                CONST_REQUIRED_CUSTOM_CFG_KEYS, CONST_COEFFICIENT_KEYS, CONST_PROJECT_ROOT,
                                CONST_CONFIG_DIR)
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
#   ../Parameters/Camera
from Parameters.Camera import Camera_Calibration_Parameters_Str
#   ../Parameters/Vision
from Parameters.Vision import Scale_Str

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
# The shipped catalogue modes: (the mode file, the item it inspects, the item's thickness and outline).
#   Unit [Vector<Tuple>]
CONST_CATALOGUE_MODES = (
    ('Config_%s_Mode_Mounting_Plate.yaml' % CONST_HARDWARE, 'mounting_plate', 8.0, (60.0, 40.0, 1.5)),
    ('Config_%s_Mode_Labyrinth.yaml' % CONST_HARDWARE, 'labyrinth', 6.0, (50.0, 50.0, 1.0)),
)
# Every shipped mode file.
#   Unit [Vector<string>]
CONST_SHIPPED_MODE_FILES = sorted(glob.glob(os.path.join(CONST_CONFIG_DIR, 'Config_*_Mode_*.yaml')))
CONST_RECORD = {'date': '2026-09-24T10:00:00', 'images': '/tmp/calib',
                'views': {'total': 12, 'flat': 4, 'tilted': 8}, 'rms_px': 0.21,
                'square_mm': 15.0, 'board_height_mm': 3.0}


def _Merged(mode: tp.Dict[str, tp.Any]) -> tp.Dict[str, tp.Any]:
    """
    A mode file with the shipped station's camera and reference merged in, where a mode file held them
    before the station file (Camera, Segmentation.Background.Reference) — one mapping a test edits; _Write
    splits it back into the mode file and the station file.
    """
    with open(Configuration.Station_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r', encoding='utf-8') as f:
        station = yaml.safe_load(f)
    mode['Camera'] = station['Camera']
    mode['Segmentation']['Background']['Reference'] = station['Background']['Reference']
    return mode


def _Shipped() -> tp.Tuple[tp.Dict[str, tp.Any], tp.Dict[str, tp.Any]]:
    """The shipped mode file, merged with its station (_Merged), and the calibration, parsed."""
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as f:
        mode = _Merged(yaml.safe_load(f))
    with open(Configuration.Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r',
              encoding='utf-8') as f:
        calibration = yaml.safe_load(f)
    return mode, calibration


def _Write(directory: tp.Any, mode: tp.Dict[str, tp.Any], calibration: tp.Optional[tp.Dict[str, tp.Any]],
           name: str = CONST_COPY_NAME, split: bool = True) -> str:
    """
    Write a mode file (and, unless None, the hardware's calibration) into a directory, splitting a merged
    mapping (_Merged) into the mode file and the station file beside it. With split False the mapping is
    written as it is, so a mode file can hold what is the station's.
    """
    path = os.path.join(str(directory), name)
    mode = copy.deepcopy(mode)
    if split:
        station = {'Hardware': CONST_HARDWARE}
        if 'Camera' in mode:
            station['Camera'] = mode.pop('Camera')
        background = (mode.get('Segmentation') or {}).get('Background') or {}
        if 'Reference' in background:
            station['Background'] = {'Reference': background.pop('Reference')}
        with open(os.path.join(str(directory), 'Station_%s.yaml' % CONST_HARDWARE), 'w', encoding='utf-8') as f:
            yaml.safe_dump(station, f, sort_keys=False)
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
    assert config.Classifies is False and config.Catalogue is None    # detect-only, as shipped
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
    # make_reference.py came into force; both now fail the load.
    assert config.Notes == []


@pytest.mark.parametrize('path', [path for path, _a, _k, required in CONST_FIELDS if required]
                         + [('Hardware',), ('Camera', 'Custom_Cfg'), ('Camera', 'Resolution'), ('Camera', 'Offset'),
                            ('Segmentation', 'Background', 'Reference')]
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
    named = {'Segmentation.Background.Reference': 'Background.Reference'}.get(named, named)  # the station's key
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


@pytest.mark.parametrize('mode_file', CONST_SHIPPED_MODE_FILES, ids=os.path.basename)
def test_every_documented_default_in_the_shipped_mode_file_is_the_code_default(mode_file: str) -> None:
    """
    Description:
        The half of the configuration rule the loader cannot see: each shipped mode file documents
        each optional field's default in its comment, and that documented default must be the
        value the code applies when the field is left out (its Parameters/Configuration default).
        A comment that says 'Default: 80' while the code falls back to 70 is a setting that looks
        authoritative and is not. Every optional field documents one; every required field's
        comment says REQUIRED — in every mode file, since the catalogue modes are copies that could
        drift from the first.
    """

    comments = _Field_Comments(mode_file)
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
    assert ('Background.Reference is 1920 × 1200 but Camera.Resolution is 1936 × 1216' in message
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


def test_a_calibration_without_its_window_fails_the_load(tmp_path: tp.Any) -> None:
    """
    Description:
        A calibration that does not record the sensor window it was solved at fails the load: its
        principal point and factor cannot be checked against the camera's window, so measurements could
        be wrong by an unknown amount. The message names the camera's window and says calibrate.py
        records it. (It loaded with a WARNING while the calibration in force predated recorded windows.)
    """

    mode, calibration = _Shipped()
    del calibration['Calibration']['Resolution']
    del calibration['Calibration']['Offset']
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert ('does not record the sensor window it was solved at, so it cannot be checked against the camera '
            '(1920 × 1200 at offset (8, 8))') in str(error.value)
    assert 'Example/Camera/calibrate.py' in str(error.value)


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


def test_a_calibration_write_that_fails_part_way_leaves_the_file_in_force(tmp_path: tp.Any) -> None:
    """
    Description:
        A write that fails part-way, as on a full disk, returns False and leaves the calibration in
        force byte for byte, with nothing else left beside it: "False if refused or failed" means
        nothing was written. Before this, the file in force was opened for writing directly and was
        left truncated, so the next load failed. A fresh interpreter caps the size of any file it
        writes (RLIMIT_FSIZE, below the calibration's size), so the write really fails part-way.
    """

    target = tmp_path / ('Calibration_%s.yaml' % CONST_HARDWARE)
    shutil.copy(Configuration.Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), target)
    before = target.read_bytes()
    script = '\n'.join((
        'import sys, signal, resource, numpy as np',
        'sys.path.insert(0, %r)' % os.path.join(CONST_PROJECT_ROOT, 'src'),
        'from Configuration.Core import Write_Calibration',
        'from Parameters.Camera import Camera_Calibration_Parameters_Str',
        'solved = Camera_Calibration_Parameters_Str(K=np.eye(3), Coefficients={%s},' % ', '.join(
            "'%s': 0.0" % key for key in ('k1', 'k2', 'p1', 'p2', 'k3')),
        "    Conversion_Factor={'x': 0.1, 'y': 0.1}, Resolution=(1920, 1200), Offset=(8, 8))",
        'signal.signal(signal.SIGXFSZ, signal.SIG_IGN)',
        'resource.setrlimit(resource.RLIMIT_FSIZE, (300, resource.RLIM_INFINITY))',
        'sys.exit(0 if Write_Calibration(solved, hardware=%r, header_source=%r, output_path=%r, record=%r) else 3)'
        % (CONST_HARDWARE, str(target), str(target), CONST_RECORD)))
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, cwd=str(tmp_path))
    assert result.returncode == 3, result.stdout + result.stderr          # refused: the write failed
    assert 'File too large' in result.stdout
    assert target.read_bytes() == before
    assert sorted(os.listdir(tmp_path)) == [target.name]


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
    with pytest.raises(Configuration_Error_Cls, match='Background.Reference: the file'):
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


def test_a_reference_without_a_sidecar_fails_the_load_naming_what_is_unknown(tmp_path: tp.Any) -> None:
    """
    Description:
        A reference with no provenance sidecar fails the load: the window, calibration and lighting it
        was shot under are unknown, so background subtraction could be comparing frames against a
        reference from another window, lens model or light. The message says make_reference.py writes
        the record. (It loaded with a WARNING while the reference in force predated sidecars.)
    """

    mode, calibration = _Shipped()
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Reference_Copy(tmp_path, mode, calibration, sidecar=None)[0])
    assert 'Image_Background_002.png has no provenance sidecar (Image_Background_002.json)' in str(error.value)
    assert 'Example/Camera/make_reference.py' in str(error.value)


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
        CONST_PROJECT_ROOT, 'Data', 'Images', 'Test')
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
        an existing calibration added one more copy of it (the calibration of eb00508 carried two).
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


def _Catalogue_Mode(name: str) -> tp.Tuple[tp.Dict[str, tp.Any], tp.Dict[str, tp.Any]]:
    """A shipped catalogue mode file and the calibration, parsed."""
    with open(os.path.join(CONST_CONFIG_DIR, name), 'r', encoding='utf-8') as f:
        mode = _Merged(yaml.safe_load(f))
    return mode, _Shipped()[1]


def _Item(name: str) -> tp.Dict[str, tp.Any]:
    """A shipped catalogue item file, parsed."""
    with open(os.path.join(CONST_PROJECT_ROOT, 'Data', 'Catalogue', name, name + '.yaml'), 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def _Write_Item(directory: tp.Any, data: tp.Dict[str, tp.Any], name: str = 'test_part',
                file_name: tp.Optional[str] = None, references: str = 'mounting_plate') -> str:
    """Write a catalogue item file into <directory>/<name>/<file_name or name>.yaml, with a shipped item's
    reference images beside it (none when references is '')."""
    folder = os.path.join(str(directory), name)
    os.makedirs(folder, exist_ok=True)
    if references and not os.path.isdir(os.path.join(folder, 'reference_image')):
        shutil.copytree(os.path.join(CONST_PROJECT_ROOT, 'Data', 'Catalogue', references, 'reference_image'),
                        os.path.join(folder, 'reference_image'))
    path = os.path.join(folder, (file_name or name) + '.yaml')
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path


def test_a_mode_without_a_catalogue_block_is_not_a_catalogue_mode() -> None:
    """
    Description:
        Segment Anything has no Catalogue block: no item, and the calibration's scale exactly as the
        calibration states it, not moved to any height — the existing mode is unchanged.
    """

    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    assert config.Catalogue is None
    assert config.Scale == Scale_Str(Mm_Per_Px_X=0.10189853878198323, Mm_Per_Px_Y=0.10207658577821295)


@pytest.mark.parametrize('name, item, thickness, outline', CONST_CATALOGUE_MODES, ids=lambda x: str(x))
def test_each_shipped_catalogue_mode_loads_its_item(name: str, item: str, thickness: float,
                                                   outline: tp.Tuple[float, float, float]) -> None:
    """
    Description:
        Each shipped catalogue mode loads end to end with the item it names: the item's thickness, its
        outline and tolerance as the request states them, and nothing defaulted or unrecognised in
        either file but the outline's tolerance, which falls back to the item's and says so.
    """

    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, name))
    assert config.Catalogue is not None and config.Catalogue.Name == item
    assert config.Catalogue.Thickness_Mm == thickness
    assert (config.Catalogue.Outline.Length_Mm, config.Catalogue.Outline.Width_Mm,
            config.Catalogue.Outline.Tolerance_Mm) == outline
    assert [message for _level, message in config.Notes] == [
        "Configuration '%s': %s.yaml: Checks.Outline.Tolerance_Mm not set; using the item's Tolerance_Mm %r."
        % (name, item, outline[2])]


@pytest.mark.parametrize('name, item, thickness, outline', CONST_CATALOGUE_MODES, ids=lambda x: str(x))
def test_a_catalogue_mode_measures_at_the_parts_top_face(name: str, item: str, thickness: float,
                                                         outline: tp.Tuple[float, float, float]) -> None:
    """
    Description:
        A catalogue mode's scale is the calibration's moved from the board's plane to the part's top
        face: each factor less (thickness - board height) / focal length, per axis — the pinhole model,
        computed here from the calibration file's own numbers.
    """

    _mode, calibration = _Shipped()
    block = calibration['Calibration']
    dh = thickness - block['Solved']['Board_Height_Mm']
    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, name))
    assert config.Scale.Height_Mm == thickness
    assert config.Scale.Mm_Per_Px_X == pytest.approx(block['Conversion_Factor']['x'] - dh / block['K'][0][0], abs=1e-15)
    assert config.Scale.Mm_Per_Px_Y == pytest.approx(block['Conversion_Factor']['y'] - dh / block['K'][1][1], abs=1e-15)


def test_the_scale_at_a_height_follows_the_pinhole_model() -> None:
    """
    Description:
        A factor is the camera's distance over its focal length: at 0.1 mm/px and a 1000 px focal length
        the camera is 100 mm from the plane, so 10 mm closer it is 0.09 mm/px, 10 mm further 0.11, and
        at the plane itself unchanged. Each axis takes its own focal length.
    """

    scale, K = Scale_Str(Mm_Per_Px_X=0.1, Mm_Per_Px_Y=0.2), [[1000.0, 0, 0], [0, 500.0, 0], [0, 0, 1]]
    closer = Scale_At_Height(scale, K, 4.0, 14.0)
    assert (closer.Mm_Per_Px_X, closer.Mm_Per_Px_Y, closer.Height_Mm) == pytest.approx((0.09, 0.18, 14.0))
    further = Scale_At_Height(scale, K, 4.0, -6.0)
    assert (further.Mm_Per_Px_X, further.Mm_Per_Px_Y) == pytest.approx((0.11, 0.22))
    same = Scale_At_Height(scale, K, 4.0, 4.0)
    assert (same.Mm_Per_Px_X, same.Mm_Per_Px_Y) == (0.1, 0.2)


@pytest.mark.parametrize('remove, words', [
    (('Calibration', 'Solved', 'Board_Height_Mm'), 'Calibration.Solved.Board_Height_Mm'),
    (('Calibration', 'Conversion_Factor'), 'Conversion_Factor'),
], ids=['board height', 'conversion factor'])
def test_a_catalogue_mode_needs_a_scale_it_can_move_to_the_top_face(tmp_path: tp.Any, remove: tp.Tuple[str, ...],
                                                                    words: str) -> None:
    """
    Description:
        A catalogue mode checks sizes in millimetres at the part's top face, so a calibration without a
        factor, or without the board height the factor holds at, fails its load naming what is missing —
        where Segment Anything on the same calibration loads (it only measures, or not at all).
    """

    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    _Delete(calibration, remove)
    with pytest.raises(Configuration_Error_Cls, match='catalogue mode') as error:
        Load_Configuration(_Write(tmp_path, mode, calibration))
    assert words in str(error.value)
    plain, _calibration = _Shipped()
    assert Load_Configuration(_Write(tmp_path, plain, None, name='Config_%s_Mode_Plain.yaml' % CONST_HARDWARE))


@pytest.mark.parametrize('block, words', [
    ({}, 'Catalogue.Item is required'),
    (None, 'Catalogue.Item is required'),
    ({'Item': '  '}, 'Catalogue.Item must be a non-empty path'),
    ({'Item': 'Data/Catalogue/no_such_part/no_such_part.yaml'}, 'does not exist'),
], ids=['empty block', 'null block', 'blank item', 'missing file'])
def test_a_catalogue_block_must_name_an_item_that_exists(tmp_path: tp.Any, block: tp.Any, words: str) -> None:
    """
    Description:
        A Catalogue block makes the mode a catalogue mode, so its Item is REQUIRED and must be a file:
        an empty block, a blank path or a missing file fails the load naming it, never falling back to
        Segment Anything.
    """

    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    mode['Catalogue'] = block
    with pytest.raises(Configuration_Error_Cls, match=words):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_an_invalid_catalogue_item_fails_its_mode(tmp_path: tp.Any) -> None:
    """
    Description:
        The item's problems are the configuration's: a mode naming an item with an invalid thickness
        fails to load, naming the item file and the field.
    """

    data = _Item('mounting_plate')
    data['Thickness_Mm'] = -8
    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    mode['Catalogue']['Item'] = _Write_Item(tmp_path, data)
    with pytest.raises(Configuration_Error_Cls, match=r'test_part\.yaml: Thickness_Mm must be a number above 0'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


@pytest.mark.parametrize('path', [path for path, _a, _k, required in CONST_CATALOGUE_FIELDS if required],
                         ids=lambda p: '.'.join(p))
def test_a_catalogue_item_missing_a_required_field_fails_naming_it(tmp_path: tp.Any, path: tp.Tuple[str, ...]) -> None:
    """
    Description:
        Every field of the item's table is REQUIRED (the thickness, the tolerance, the outline's two
        sides): removing one fails Load_Catalogue, naming the file and the field.
    """

    data = _Item('mounting_plate')
    _Delete(data, path)
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Catalogue(_Write_Item(tmp_path, data))
    assert 'test_part.yaml: %s is required but missing' % '.'.join(path) in str(error.value)


def test_the_outline_tolerance_overrides_the_items(tmp_path: tp.Any) -> None:
    """
    Description:
        The outline takes the item's Tolerance_Mm unless it sets its own: set, the override is used and
        nothing is noted; invalid, the load fails rather than fall back to the item's.
    """

    data = _Item('labyrinth')
    data['Checks']['Outline']['Tolerance_Mm'] = 0.5
    item = Load_Catalogue(_Write_Item(tmp_path, data))
    assert (item.Tolerance_Mm, item.Outline.Tolerance_Mm, item.Notes) == (1.0, 0.5, [])
    data['Checks']['Outline']['Tolerance_Mm'] = 0
    with pytest.raises(Configuration_Error_Cls, match='Checks.Outline.Tolerance_Mm must be a number above 0'):
        Load_Catalogue(_Write_Item(tmp_path, data))


def test_a_catalogue_item_is_refused_when_its_length_is_its_shorter_side(tmp_path: tp.Any) -> None:
    """
    Description:
        The check compares the longer measured side with Length_Mm, so an item that gives the shorter
        side as its length would fail every part it describes: the load refuses it instead.
    """

    data = _Item('mounting_plate')
    data['Checks']['Outline'].update(Length_Mm=40, Width_Mm=60)
    with pytest.raises(Configuration_Error_Cls, match='Length_Mm .* must be at least'):
        Load_Catalogue(_Write_Item(tmp_path, data))


def test_a_catalogue_item_file_is_named_after_its_folder(tmp_path: tp.Any) -> None:
    """
    Description:
        A new item is a copied folder: a file that kept the old name in the renamed folder is refused,
        so it is never inspected under a name it does not have.
    """

    with pytest.raises(Configuration_Error_Cls, match='must be test_part.yaml'):
        Load_Catalogue(_Write_Item(tmp_path, _Item('mounting_plate'), file_name='mounting_plate'))


def test_an_unrecognised_catalogue_key_is_a_warning(tmp_path: tp.Any) -> None:
    """
    Description:
        A misspelt key in the item file is reported as a WARNING naming the file and the key, as in a
        mode file, and the field it was meant to be is still required.
    """

    data = _Item('mounting_plate')
    data['Checks']['Outline']['Tolerence_Mm'] = 1.0
    item = Load_Catalogue(_Write_Item(tmp_path, data))
    assert ('WARNING', 'test_part.yaml: unrecognised key Checks.Outline.Tolerence_Mm is ignored (misspelt?).') \
        in item.Notes


@pytest.mark.parametrize('item', ['mounting_plate', 'labyrinth'])
def test_every_field_of_a_shipped_catalogue_item_says_required_or_its_default(item: str) -> None:
    """
    Description:
        The catalogue files follow the mode file's rule: each required field's comment says REQUIRED, each
        optional one its default (the descriptions: empty); Sides says REQUIRED and Defects that none is the
        default; and the optional outline tolerance, which is commented out because its default is the
        item's own tolerance, says so — a value written there would stay put when the item's changed.
    """

    from Parameters.Catalogue import Catalogue_Item_Str
    path = os.path.join(CONST_PROJECT_ROOT, 'Data', 'Catalogue', item, item + '.yaml')
    comments = _Field_Comments(path)
    for field_path, attribute, _kind, required in CONST_CATALOGUE_FIELDS:
        said = [comments.get(field_path[:i], ('', 0))[0] for i in range(1, len(field_path) + 1)]
        if required:
            assert any('REQUIRED' in comment for comment in said), '.'.join(field_path)
        else:
            text, position = comments[field_path]
            assert _Documented_Default(text, position) == getattr(Catalogue_Item_Str(), attribute[-1]), field_path
    assert 'REQUIRED' in comments[('Sides',)][0] and 'Default: none' in comments[('Defects',)][0]
    with open(path, 'r', encoding='utf-8') as handle:
        text = handle.read()
    assert "Default: the item's Tolerance_Mm." in text and '\n    Tolerance_Mm:' not in text


def test_the_sources_line_names_the_catalogue_item() -> None:
    """
    Description:
        The configuration-loaded line that names what a configuration reads names the catalogue item in
        a catalogue mode, so a run can be traced to the item it checked; Segment Anything's is unchanged.
    """

    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, CONST_CATALOGUE_MODES[0][0]))
    assert Config_Sources_Log_Line(config).endswith(
        'background reference Data/Images/Background/Image_Background_001.png and catalogue item '
        'Data/Catalogue/mounting_plate/mounting_plate.yaml.')
    assert Config_Sources_Log_Line(Load_Configuration(CONST_DEFAULT_CONFIG_FILE)).endswith(
        'and background reference Data/Images/Background/Image_Background_001.png.')


def test_a_catalogue_mode_needs_its_identifier() -> None:
    """
    Description:
        The DINOv2 directory is REQUIRED in a Catalogue block: without it the mode fails to load naming
        Catalogue.Identifier, and the path is resolved against the repository root like every model.
    """

    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, CONST_CATALOGUE_MODES[0][0]))
    assert config.Identification.Model_Path == os.path.join(CONST_PROJECT_ROOT, 'models', 'dinov2-base')


def test_a_catalogue_block_without_its_identifier_fails(tmp_path: tp.Any) -> None:
    """
    Description:
        Removing Catalogue.Identifier fails the load, naming it: there is no default model.
    """

    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    del mode['Catalogue']['Identifier']
    with pytest.raises(Configuration_Error_Cls, match='Catalogue.Identifier is required but missing'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


@pytest.mark.parametrize('key, value, words', [
    ('Identify_Similarity', 1.5, 'Catalogue.Identify_Similarity must be a number from 0 to 1'),
    ('Unspecified_Area_Ratio', 1.0, 'Catalogue.Unspecified_Area_Ratio must be above 1'),
    ('Unspecified_Area_Ratio', -2, 'Catalogue.Unspecified_Area_Ratio must be a number above 0'),
])
def test_an_invalid_identification_threshold_fails(tmp_path: tp.Any, key: str, value: tp.Any, words: str) -> None:
    """
    Description:
        The thresholds are validated: a similarity outside 0..1 fails, and an Unspecified ratio of 1 or
        less fails too — at 1 the part itself would be Unspecified.
    """

    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    mode['Catalogue'][key] = value
    with pytest.raises(Configuration_Error_Cls, match=words):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_the_identification_thresholds_default_to_the_measured_values(tmp_path: tp.Any) -> None:
    """
    Description:
        Left out, the similarity takes 0.75 and the ratio 1.7, and the load says so for each.
    """

    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    del mode['Catalogue']['Identify_Similarity'], mode['Catalogue']['Unspecified_Area_Ratio']
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert (config.Identification.Identify_Similarity, config.Identification.Unspecified_Area_Ratio) == (0.75, 1.7)
    notes = [message for _level, message in config.Notes]
    assert any('Catalogue.Identify_Similarity not set; using the default 0.75' in m for m in notes)
    assert any('Catalogue.Unspecified_Area_Ratio not set; using the default 1.7' in m for m in notes)


@pytest.mark.parametrize('name, item', [(n, i) for n, i, _t, _o in CONST_CATALOGUE_MODES], ids=lambda x: str(x))
def test_the_catalogue_blocks_document_their_defaults(name: str, item: str) -> None:
    """
    Description:
        The Catalogue block's fields follow the mode file's rule: Identifier says REQUIRED, and each
        optional threshold's comment states the default the code applies.
    """

    comments = _Field_Comments(os.path.join(CONST_CONFIG_DIR, name))
    code = Configuration_Str()
    for path, attribute, _kind, required in CONST_CATALOGUE_BLOCK_FIELDS:
        text, position = comments[path]
        if required:
            assert 'REQUIRED' in text, path
            continue
        expected = code
        for part in attribute:
            expected = getattr(expected, part)
        assert _Documented_Default(text, position) == expected, path


def test_the_item_carries_its_reference_images() -> None:
    """
    Description:
        A catalogue item's reference images are read with it, front then back, each with the part's YOLO
        box from its .txt — the shipped files' boxes.
    """

    item = Load_Catalogue('Data/Catalogue/mounting_plate/mounting_plate.yaml')
    assert [(r.Side, os.path.basename(r.Image_Path)) for r in item.References] == [('front', 'front.png'),
                                                                                    ('back', 'back.png')]
    assert item.References[0].Box == (0.472917, 0.460417, 0.203125, 0.4925)


@pytest.mark.parametrize('damage, words', [
    ('missing image', 'the back reference needs reference_image/back.png and reference_image/back.txt'),
    ('two lines', 'reference_image/back.txt must hold one YOLO line'),
    ('out of range', 'reference_image/back.txt must hold one YOLO line'),
], ids=lambda x: x if ' ' in str(x) else None)
def test_a_damaged_reference_fails_the_item(tmp_path: tp.Any, damage: str, words: str) -> None:
    """
    Description:
        A reference the identifier could not use fails the item, naming the side and what is wrong: a
        missing image, a box file that is not one YOLO line, or a box outside the image.
    """

    path = _Write_Item(tmp_path, _Item('mounting_plate'))
    folder = os.path.join(os.path.dirname(path), 'reference_image')
    if damage == 'missing image':
        os.remove(os.path.join(folder, 'back.png'))
    else:
        with open(os.path.join(folder, 'back.txt'), 'w', encoding='utf-8') as handle:
            handle.write('0 0.5 0.5 0.2 0.4\n0 0.5 0.5 0.2 0.4\n' if damage == 'two lines' else '0 0.5 0.5 1.2 0.4\n')
    with pytest.raises(Configuration_Error_Cls, match=words):
        Load_Catalogue(path)


def test_a_reference_of_another_window_fails_the_mode(tmp_path: tp.Any) -> None:
    """
    Description:
        A reference image must be a frame of the camera's window, since the part's box is in its pixels and
        the reference is cropped as a frame is: one of another size fails the mode's load, naming both.
    """

    import cv2
    path = _Write_Item(tmp_path, _Item('mounting_plate'))
    front = os.path.join(os.path.dirname(path), 'reference_image', 'front.png')
    cv2.imwrite(front, cv2.resize(cv2.imread(front), (960, 600)))
    mode, calibration = _Catalogue_Mode(CONST_CATALOGUE_MODES[0][0])
    mode['Catalogue']['Item'] = path
    with pytest.raises(Configuration_Error_Cls, match='reference_image/front.png is 960 × 600, but Camera.Resolution '
                                                      'is 1920 × 1200'):
        Load_Configuration(_Write(tmp_path, mode, calibration))


def test_the_removed_classification_switch_is_named_when_a_file_still_has_it(tmp_path: tp.Any) -> None:
    """
    Description:
        General.Classification is no longer read: a configuration classifies when it has a Catalogue block.
        A file that still holds the switch loads, with a WARNING that says so — not the generic 'misspelt?'
        — and it decides nothing: Segment Anything with it set true still does not classify.
    """

    mode, calibration = _Shipped()
    mode['General']['Classification'] = {'Enabled': True}
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert config.Classifies is False
    assert ('WARNING', "Configuration '%s': General.Classification is no longer read and is ignored: a configuration "
                       'classifies when it has a Catalogue block.' % CONST_COPY_NAME) in config.Notes


@pytest.mark.parametrize('path', [('Camera',), ('Segmentation', 'Background', 'Reference')], ids=lambda p: '.'.join(p))
def test_a_mode_file_never_overrides_the_station(tmp_path: tp.Any, path: tp.Tuple[str, ...]) -> None:
    """
    Description:
        The camera and the reference are the station's: a mode file that still holds the Camera block or a
        background reference fails to load, naming the key and the station file to set it in — even when
        its value equals the station's, since a second copy is a second source.
    """

    mode, calibration = _Shipped()
    _Write(tmp_path, mode, calibration)                    # the station file, from the merged mapping
    with pytest.raises(Configuration_Error_Cls) as error:
        Load_Configuration(_Write(tmp_path, mode, None, split=False))
    assert ("%s is the station's, not the mode's: remove it from this file and set it in Station_%s.yaml"
            % ('.'.join(path), CONST_HARDWARE)) in str(error.value)


def test_a_mode_without_its_station_file_fails(tmp_path: tp.Any) -> None:
    """
    Description:
        The station file is REQUIRED — without it there is no camera to configure: a mode whose hardware has
        none beside it fails to load, naming the file it looked for.
    """

    mode, calibration = _Shipped()
    path = _Write(tmp_path, mode, calibration)
    os.remove(Station_Path_For(path, CONST_HARDWARE))
    with pytest.raises(Configuration_Error_Cls, match=r'the station file ".*Station_%s\.yaml" does not exist'
                       % CONST_HARDWARE):
        Load_Configuration(path)


def test_the_station_file_must_be_the_modes_hardware(tmp_path: tp.Any) -> None:
    """
    Description:
        The station file repeats its hardware, and it must be the mode's: a copied file that still names
        another camera is refused.
    """

    mode, calibration = _Shipped()
    path = _Write(tmp_path, mode, calibration)
    station = Station_Path_For(path, CONST_HARDWARE)
    with open(station, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    data['Hardware'] = 'Other_Camera'
    with open(station, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f)
    with pytest.raises(Configuration_Error_Cls, match="Station_%s.yaml: Hardware is 'Other_Camera'" % CONST_HARDWARE):
        Load_Configuration(path)


def test_an_unrecognised_station_key_is_a_warning_naming_the_station_file(tmp_path: tp.Any) -> None:
    """
    Description:
        A key the station file does not hold is reported like the mode file's, naming the station file.
    """

    mode, calibration = _Shipped()
    mode['Camera']['Gamma_Correction'] = 1.2
    config = Load_Configuration(_Write(tmp_path, mode, calibration))
    assert any(level == 'WARNING' and 'Station_%s.yaml: unrecognised key Camera.Gamma_Correction' % CONST_HARDWARE
               in message for level, message in config.Notes)


def test_every_mode_reads_the_one_station() -> None:
    """
    Description:
        The shipped modes share one station: each loads the same camera, window, acquisition settings and
        reference, from the same file.
    """

    configs = [Load_Configuration(path) for path in CONST_SHIPPED_MODE_FILES]
    assert len({config.Station_Path for config in configs}) == 1
    assert configs[0].Station_Path == os.path.join(CONST_CONFIG_DIR, 'Station_%s.yaml' % CONST_HARDWARE)
    first = configs[0]
    for config in configs[1:]:
        for name in ('Model', 'Lens', 'Lighting', 'Resolution', 'Offset', 'Custom_Cfg'):
            assert getattr(config.Camera, name) == getattr(first.Camera, name), name
        assert config.Segmentation.Background_Reference == first.Segmentation.Background_Reference


def test_every_station_field_says_required_or_its_default() -> None:
    """
    Description:
        The shipped station file follows the mode file's rule: each required field's comment says REQUIRED
        (the reference, the acquisition settings, the window), each optional one states the default the code
        applies (the camera, lens and lighting: empty).
    """

    comments = _Field_Comments(Station_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE))
    code = Configuration_Str()
    for path, attribute, _kind, required in CONST_STATION_FIELDS:
        text, position = comments[path]
        if required:
            said = [comments.get(path[:i], ('', 0))[0] for i in range(1, len(path))] + [text]
            assert any('REQUIRED' in comment for comment in said), path
            continue
        expected = code
        for part in attribute:
            expected = getattr(expected, part)
        assert _Documented_Default(text, position) == expected, path
    for path in (('Hardware',), ('Camera', 'Resolution'), ('Camera', 'Custom_Cfg')):
        said = [comments.get(path[:i], ('', 0))[0] for i in range(1, len(path) + 1)]
        assert any('REQUIRED' in comment for comment in said), path
    # The window's two halves share one comment, above Resolution, which says both are required.
    assert 'its size and its offset' in comments[('Camera', 'Resolution')][0]


def test_the_item_carries_its_description_sides_and_defects() -> None:
    """
    Description:
        Each shipped item is the single tracked source for its part: its name, its description and
        measurement rules, both sides with their names and descriptions, and its defects, each on a side —
        the request's text, loaded and validated.
    """

    plate = Load_Catalogue('Data/Catalogue/mounting_plate/mounting_plate.yaml')
    assert plate.Display_Name == 'Mounting plate' and plate.Description.startswith('A metal mounting plate')
    assert 'symmetric lengthwise' in plate.Measurement_Rules
    assert [(side.Side, side.Name) for side in plate.Sides] == [('front', 'machined front'), ('back', 'unmachined back')]
    assert 'tool marks' in plate.Sides[0].Description and 'whitish to silver' in plate.Sides[1].Description
    assert [(d.Name, d.Side) for d in plate.Defects] == [('fingerprint', 'front')]
    assert 'papillary lines' in plate.Defects[0].Looks_Like and plate.Defects[0].Not_A_Defect
    labyrinth = Load_Catalogue('Data/Catalogue/labyrinth/labyrinth.yaml')
    assert [(side.Side, side.Name) for side in labyrinth.Sides] == [('front', 'maze side'), ('back', 'logo side')]
    assert [(d.Name, d.Side) for d in labyrinth.Defects] == [('corner hole count', 'front'), ('incomplete logo', 'back')]


@pytest.mark.parametrize('change, words', [
    (lambda d: d.pop('Sides'), 'Sides is required and must hold exactly front and back'),
    (lambda d: d['Sides'].pop('back'), 'Sides is required and must hold exactly front and back'),
    (lambda d: d['Sides']['front'].pop('Name'), 'Sides.front.Name is required but missing'),
    (lambda d: d['Sides']['back'].update(Colour='dark'), 'Sides.back.Colour is not a key it may hold'),
    (lambda d: d['Defects'][0].update(Side='left'), r'Defects\[1\]\.Side must be front or back'),
    (lambda d: d['Defects'][0].pop('Looks_Like'), r'Defects\[1\]\.Looks_Like is required but missing'),
    (lambda d: d.update(Defects='fingerprint'), 'Defects must be a list of defects'),
], ids=['no sides', 'one side', 'side without name', 'unknown side key', 'defect side', 'defect look', 'defects not a list'])
def test_an_invalid_description_fails_the_item(tmp_path: tp.Any, change: tp.Callable, words: str) -> None:
    """
    Description:
        The descriptive fields are validated now though the describer reads them only from phase D: both sides,
        each named; each defect named, on a side, with what it looks like; a key a side or defect may not hold.
        A mistake here fails the item instead of waiting to mislead the describer.
    """

    data = _Item('mounting_plate')
    change(data)
    with pytest.raises(Configuration_Error_Cls, match=words):
        Load_Catalogue(_Write_Item(tmp_path, data))


def test_an_item_with_no_defects_described_loads() -> None:
    """
    Description:
        Defects are optional: an item whose defective parts do not exist yet describes none, and loads.
    """

    import tempfile
    data = _Item('labyrinth')
    del data['Defects']
    with tempfile.TemporaryDirectory() as directory:
        assert Load_Catalogue(_Write_Item(directory, data, references='labyrinth')).Defects == []


def test_the_items_carry_their_hole_groups() -> None:
    """
    Description:
        The shipped items' holes, per side: the mounting plate's front, two countersinks and two positioned
        through-holes at a 25 mm pitch, and its back's two through-holes; the labyrinth's four corner holes on the
        front and no hole check on its back (blind holes). Each group takes the item's tolerance.
    """

    plate = Load_Catalogue('Data/Catalogue/mounting_plate/mounting_plate.yaml')
    assert sorted(plate.Holes) == ['back', 'front']
    assert [(g.Name, g.Diameter_Mm, g.Count, g.From_Long_Edge_Mm, g.From_Short_Edge_Mm, g.Pitch_Mm, g.Tolerance_Mm)
            for g in plate.Holes['front']] == [('countersink', 12.0, 2, 0.0, 0.0, 0.0, 1.5),
                                               ('through-hole', 6.0, 2, 15.0, 17.5, 25.0, 1.5)]
    assert [(g.Name, g.Count) for g in plate.Holes['back']] == [('through-hole', 2)]
    labyrinth = Load_Catalogue('Data/Catalogue/labyrinth/labyrinth.yaml')
    assert list(labyrinth.Holes) == ['front']
    assert [(g.Name, g.Diameter_Mm, g.Count, g.From_Long_Edge_Mm, g.Pitch_Mm, g.Tolerance_Mm)
            for g in labyrinth.Holes['front']] == [('corner hole', 2.459, 4, 4.0, 42.0, 1.0)]


@pytest.mark.parametrize('change, words', [
    (lambda h: h.update(left=[{'Name': 'x', 'Diameter_Mm': 6, 'Count': 2}]), 'Checks.Holes must map front and/or back'),
    (lambda h: h.update(back=[]), 'Checks.Holes.back must be a non-empty list'),
    (lambda h: h['front'][1].pop('Count'), r'Checks.Holes.front\[2\].Count is required but missing'),
    (lambda h: h['front'][1].update(Count=0), r'Checks.Holes.front\[2\].Count must be a whole number of at least 1'),
    (lambda h: h['front'][1].pop('From_Short_Edge_Mm'), r'front\[2\] sets one edge distance without the other'),
    (lambda h: h['front'][0].update(Diameter_Mm=8), 'through-hole and countersink capture the same diameters'),
    (lambda h: h['front'][0].update(Depth_Mm=3), r'Checks.Holes.front\[1\].Depth_Mm is not a key it may hold'),
], ids=['unknown side', 'empty side', 'no count', 'zero count', 'one edge distance', 'overlapping groups', 'unknown key'])
def test_an_invalid_hole_group_fails_the_item(tmp_path: tp.Any, change: tp.Callable, words: str) -> None:
    """
    Description:
        The hole groups are validated at load: a side the part does not have, an empty side, a group without
        its count or with none, a position with one edge distance, a key a group may not hold, and two groups of
        one side capturing the same diameters (a hole would count in both).
    """

    data = _Item('mounting_plate')
    change(data['Checks']['Holes'])
    with pytest.raises(Configuration_Error_Cls, match=words):
        Load_Catalogue(_Write_Item(tmp_path, data))


def test_an_item_without_holes_has_no_hole_check(tmp_path: tp.Any) -> None:
    """
    Description:
        Checks.Holes is optional: an item without it loads with no hole check on either side.
    """

    data = _Item('mounting_plate')
    del data['Checks']['Holes']
    assert Load_Catalogue(_Write_Item(tmp_path, data)).Holes == {}
