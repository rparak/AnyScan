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
# File Name: ../Configuration/Core.py
## =========================================================================== ##

# System (Default)
import os
import math
# Hashlib (the reference image's and the calibration's fingerprints)
import hashlib
# JSON (quoting a path safely in YAML)
import json
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pillow (Image header reading: the background reference's size, without decoding it) [pip3 install Pillow]
from PIL import Image
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the structures a configuration becomes
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
#   ../Parameters/Camera
from Parameters.Camera import Camera_Calibration_Parameters_Str
#   ../Parameters/Vision
from Parameters.Vision import Scale_Str, CONST_SCALE_UNITS

"""
Description:
    Initialization of constants.

    THE configuration layer: the only code that reads a configuration or calibration file. A
    mode file (Config_<Hardware>_Mode_<Mode>.yaml) is read, validated AS A WHOLE and returned as
    one Configuration_Str — or refused with every problem listed, so a file that is wrong halfway
    through is never partly applied. Every module that needs a setting receives it from that
    structure; none opens the YAML for itself. Qt-free.

    The rules:
        - A REQUIRED field (the hardware, both model paths, the background reference — which must
          exist — both prompts, the identity's display name and model set, the camera's acquisition
          settings and its sensor window) has no default: its absence fails the load, naming the field.
        - The SENSOR WINDOW (Camera.Resolution, Camera.Offset) is set on the camera on connect, and
          what depends on it is checked against it here, at load: a background reference of another
          size fails the load, naming both sizes, and so does a calibration solved at another window.
          The camera never takes its size from the reference — the hardware follows the
          configuration, and the data is validated against it.
        - The BACKGROUND REFERENCE carries its provenance in a sidecar (<reference>.json), written by
          Example/Camera/make_reference.py from a capture set's own record, never by hand. The load
          checks it: the image must be the one the sidecar describes, and its window, calibration
          and lighting must be the configuration's. The window and calibration checks are structural;
          the lighting check compares two fields a person types (see __Check_Reference_Sidecar).
        - The CALIBRATION is optional as a whole: a hardware without a calibration file loads with
          no lens model and no scale (frames are not undistorted, objects are not measured) and a
          warning saying to run calibrate.py — the honest degraded state, and the one a camera
          being calibrated for the first time must be able to start from. A calibration file that
          exists must be complete and valid: K and all five coefficients.
        - An OPTIONAL field falls back to the documented default (the Parameters/Configuration
          field default, which is the value the code ran with as a constant) and the fall-back is
          recorded in Configuration_Str.Notes for the caller to log.
        - A value that is present but invalid fails the load: a wrong value is never replaced by
          a default.
        - An unrecognised key is recorded as a warning, so a misspelt optional field is visible.
"""
# The repository root and its Configuration/ directory. This file lives in src/Configuration/,
# so the root is two levels up. Relative model paths in a configuration resolve against the root.
#   Unit [string]
CONST_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_CONFIG_DIR = os.path.join(CONST_PROJECT_ROOT, 'Configuration')
# The configuration the application loads at startup (App/run.py --config overrides it).
#   Unit [string]
CONST_DEFAULT_CONFIG_FILE = os.path.join(CONST_CONFIG_DIR,
                                         'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Seg_Anything.yaml')
# The mode-file name is 'Config_<Hardware>_Mode_<Mode>.yaml'; the calibration of <Hardware> is
# 'Calibration_<Hardware>.yaml' in the same directory.
#   Unit [string]
CONST_CONFIG_PREFIX = 'Config_'
CONST_MODE_SEPARATOR = '_Mode_'
CONST_CALIBRATION_TEMPLATE = 'Calibration_{hardware}.yaml'
# The acquisition settings the Basler camera cannot start without; each is REQUIRED in
# Camera.Custom_Cfg so a file missing one fails at load and not deep inside the Basler SDK.
# They are the ONLY keys it reads (Basler_Cls.__Configure), so Custom_Cfg is a schema like every
# other block: each value is typed, and any other key is reported as unrecognised — a 'Gamma:'
# line would otherwise do nothing and say nothing.
#   Unit [Tuple<string>]
CONST_REQUIRED_CUSTOM_CFG_KEYS = ('Exposure_Time', 'Gain', 'Balance_Ratios', 'Pixel_Format')
# The kind (see __Check) of each Custom_Cfg setting; Balance_Ratios is a mapping of the channels
# below, each a ratio above 0. The channel names go to the camera's BalanceRatioSelector as they
# are, so they are exactly these.
#   Unit [Dict<string, string>] / [Tuple<string>]
CONST_CUSTOM_CFG_KINDS = {'Exposure_Time': 'positive', 'Gain': 'nonnegative', 'Pixel_Format': 'text'}
CONST_BALANCE_CHANNELS = ('Red', 'Green', 'Blue')
# The distortion coefficients a calibration must hold, in OpenCV's order.
#   Unit [Tuple<string>]
CONST_COEFFICIENT_KEYS = ('k1', 'k2', 'p1', 'p2', 'k3')
# The compute devices a configuration may name.
#   Unit [Tuple<string>]
CONST_DEVICES = ('auto', 'cpu', 'mps', 'cuda')
# The keys the calibration writer owns. It refuses to overwrite a file holding anything else, so
# content someone adds to a calibration file is never silently deleted.
#   Unit [Tuple<string>]
CONST_CALIBRATION_FILE_KEYS = ('Hardware', 'Calibration')
# The comment the calibration writer puts above 'Hardware:'. The header it copies from the file in
# force stops before it — otherwise every write over an existing file added one more copy (the
# calibration of f5cd075 carried two).
#   Unit [string]
CONST_CALIBRATION_HARDWARE_COMMENT = ("# The hardware this calibration belongs to; must equal the hardware part "
                                      "of this file's name.")
CONST_CALIBRATION_BLOCK_KEYS = ('Solved', 'Resolution', 'Offset', 'K', 'Coefficients', 'Conversion_Factor')
# The background reference's sidecar: the same name with this suffix (Image_Background_002.json).
#   Unit [string]
CONST_REFERENCE_SIDECAR_SUFFIX = '.json'
# The sensor window: (the key path, the smallest valid value). Each is an {x, y} pair in pixels,
# REQUIRED in a mode file and recorded in a calibration file. The camera is set to it on connect;
# the background reference and the calibration must match it.
#   Unit [Tuple<Tuple>]
CONST_WINDOW_FIELDS = ((('Camera', 'Resolution'), 1), (('Camera', 'Offset'), 0))


class Configuration_Error_Cls(ValueError):
    """
    Description:
        A configuration that cannot be used. Its message names the file and EVERY problem found,
        as sentences the Configuration dialog shows verbatim.
    """


def Hardware_And_Mode(config_path: str) -> tp.Tuple[str, str]:
    """
    Description:
        Split a mode file's name, 'Config_<Hardware>_Mode_<Mode>.yaml', into its hardware and mode.
        A name without the '_Mode_' part (the pre-mode convention) is all hardware, with no mode.

    Args:
        (1) config_path [string]: The configuration file path.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (hardware, mode); either may be '' when the name does
                                           not follow the convention.
    """

    stem = os.path.splitext(os.path.basename(config_path))[0]
    if stem.startswith(CONST_CONFIG_PREFIX):
        stem = stem[len(CONST_CONFIG_PREFIX):]
    hardware, _separator, mode = stem.partition(CONST_MODE_SEPARATOR)
    return hardware, mode


def Calibration_Path_For(config_path: str, hardware: str) -> str:
    """
    Description:
        The calibration file of a hardware id: 'Calibration_<Hardware>.yaml' beside the mode file.

    Args:
        (1) config_path [string]: The mode file path.
        (2) hardware [string]: The hardware id.

    Returns:
        (1) parameter [string]: The calibration file path (absolute).
    """

    return os.path.join(os.path.dirname(os.path.abspath(config_path)),
                        CONST_CALIBRATION_TEMPLATE.format(hardware=hardware))


def __Resolve_Model_Path(path: str) -> str:
    """
    Description:
        A path from the configuration (a model, the background reference), made absolute: a
        relative path resolves against the repository root, where models/ and Data/ live, not
        against the working directory.

    Args:
        (1) path [string]: The path as written.

    Returns:
        (1) parameter [string]: The absolute path.
    """

    path = os.path.expanduser(path)
    return os.path.normpath(path if os.path.isabs(path) else os.path.join(CONST_PROJECT_ROOT, path))


def __Check(kind: str, value: tp.Any) -> tp.Tuple[bool, tp.Any, str]:
    """
    Description:
        Validate one value against its kind and normalise it. YAML's bool is excluded from every
        number kind (True is not 1), and an integer kind rejects 3.5 rather than truncate it.

    Args:
        (1) kind [string]: The kind: 'bool', 'text', 'path', 'percent', 'unit', 'fraction', 'margin',
                           'grey', 'count', 'size', 'kernel', 'nonnegative', 'positive' or 'device'.
        (2) value [Any]: The value read from the file.

    Returns:
        (1) parameter [Tuple]: (valid, the normalised value, what was expected — for the message).
    """

    is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    is_integer = isinstance(value, int) and not isinstance(value, bool)
    finite = is_number and math.isfinite(float(value))
    rules = {
        'bool':        (isinstance(value, bool), value, 'true or false'),
        'text':        (isinstance(value, str) and bool(value.strip()),
                        ' '.join(str(value).split()), 'non-empty text'),
        'path':        (isinstance(value, str) and bool(value.strip()), str(value).strip(),
                        'a non-empty path'),
        'percent':     (is_integer and 0 <= value <= 100, value, 'a whole number from 0 to 100'),
        'unit':        (finite and 0.0 <= value <= 1.0, float(value) if finite else value,
                        'a number from 0 to 1'),
        'fraction':    (finite and 0.0 < value <= 1.0, float(value) if finite else value,
                        'a number above 0 and at most 1'),
        'margin':      (finite and 0.0 <= value < 0.5, float(value) if finite else value,
                        'a number from 0 up to (not including) 0.5'),
        'grey':        (is_integer and 0 <= value <= 255, value, 'a whole number from 0 to 255'),
        'count':       (is_integer and 1 <= value <= 4, value, 'a whole number from 1 to 4'),
        'size':        (is_integer and value >= 1, value, 'a whole number of at least 1'),
        'kernel':      (is_integer and value >= 0, value, 'a whole number of at least 0'),
        'nonnegative': (finite and value >= 0.0, float(value) if finite else value,
                        'a number of at least 0'),
        'positive':    (finite and value > 0.0, float(value) if finite else value,
                        'a number above 0'),
        'device':      (isinstance(value, str) and (value in CONST_DEVICES or value.startswith('cuda:')),
                        value, 'one of %s (or cuda:N)' % ', '.join(CONST_DEVICES)),
    }
    return rules[kind]


# Every setting a mode file holds, as (the YAML key path, the Configuration_Str attribute path,
# the kind, required). A required setting's default below is never used; an optional one's is the
# field default of its structure (Parameters/Configuration).
#   Unit [Vector<Tuple>]
CONST_FIELDS = (
    (('General', 'Classification', 'Enabled'), ('Classification_Enabled',), 'bool', False),
    (('Identity', 'Display_Name'), ('Identity', 'Display_Name'), 'text', True),
    (('Identity', 'Model_Set'), ('Identity', 'Model_Set'), 'text', True),
    (('Identity', 'Task'), ('Identity', 'Task'), 'text', False),
    (('Confidence', 'Warn_Below'), ('Confidence', 'Warn_Below'), 'percent', False),
    (('Confidence', 'Error_Below'), ('Confidence', 'Error_Below'), 'percent', False),
    (('Segmentation', 'Model'), ('Segmentation', 'Model_Path'), 'path', True),
    (('Segmentation', 'Device'), ('Segmentation', 'Device'), 'device', False),
    (('Segmentation', 'Confidence'), ('Segmentation', 'Confidence'), 'unit', False),
    (('Segmentation', 'IoU'), ('Segmentation', 'IoU'), 'unit', False),
    (('Segmentation', 'Image_Size'), ('Segmentation', 'Image_Size'), 'size', False),
    (('Segmentation', 'Background', 'Reference'), ('Segmentation', 'Background_Reference'), 'path', True),
    (('Segmentation', 'Background', 'Otsu_Floor'), ('Segmentation', 'Otsu_Floor'), 'grey', False),
    (('Segmentation', 'Background', 'Open_Kernel'), ('Segmentation', 'Open_Kernel'), 'kernel', False),
    (('Segmentation', 'Background', 'Dilate'), ('Segmentation', 'Dilate'), 'kernel', False),
    (('Segmentation', 'Fusion', 'Close_Kernel'), ('Segmentation', 'Close_Kernel'), 'kernel', False),
    (('Segmentation', 'Fusion', 'Min_Area_Fraction'), ('Segmentation', 'Min_Area_Fraction'),
     'fraction', False),
    (('Segmentation', 'Fusion', 'Hard_Background_Fraction'), ('Segmentation', 'Hard_Background_Fraction'),
     'fraction', False),
    (('Segmentation', 'Fusion', 'Background_Area_Fraction'), ('Segmentation', 'Background_Area_Fraction'),
     'fraction', False),
    (('Segmentation', 'Fusion', 'Background_Borders'), ('Segmentation', 'Background_Borders'),
     'count', False),
    (('Description', 'Model'), ('Description', 'Model_Path'), 'path', True),
    (('Description', 'Temperature'), ('Description', 'Temperature'), 'nonnegative', False),
    (('Description', 'Max_Tokens'), ('Description', 'Max_Tokens'), 'size', False),
    (('Description', 'Background_Crop_Margin'), ('Description', 'Background_Crop_Margin'),
     'margin', False),
    (('Description', 'Object_Crop_Padding'), ('Description', 'Object_Crop_Padding'), 'nonnegative', False),
    (('Description', 'Background_Max_Words'), ('Description', 'Background_Max_Words'), 'size', False),
    (('Description', 'Background_Max_Sentences'), ('Description', 'Background_Max_Sentences'),
     'size', False),
    (('Description', 'Prompts', 'Object'), ('Description', 'Prompt_Object'), 'text', True),
    (('Description', 'Prompts', 'Background'), ('Description', 'Prompt_Background'), 'text', True),
    (('Camera', 'Model'), ('Camera', 'Model'), 'text', False),
    (('Camera', 'Lens'), ('Camera', 'Lens'), 'text', False),
    (('Camera', 'Lighting'), ('Camera', 'Lighting'), 'text', False),
    (('Evaluation', 'Frames'), ('Evaluation', 'Frames'), 'path', False),
)


def __Lookup(data: tp.Any, path: tp.Tuple[str, ...]) -> tp.Tuple[bool, tp.Any]:
    """
    Description:
        Follow a key path through nested mappings.

    Args:
        (1) data [Any]: The parsed document.
        (2) path [Tuple<string>]: The key path.

    Returns:
        (1) parameter [Tuple<bool, Any>]: (present, value).
    """

    for key in path:
        if not isinstance(data, dict) or key not in data:
            return False, None
        data = data[key]
    return True, data


def __Unknown_Keys(data: tp.Dict[str, tp.Any]) -> tp.List[str]:
    """
    Description:
        The keys in a mode file that no setting reads — usually a misspelt optional field, which
        would otherwise fall back to its default without a word.

    Args:
        (1) data [Dict]: The parsed document.

    Returns:
        (1) parameter [Vector<string>]: The unknown keys as dotted paths.
    """

    known = {('Hardware',)}
    for path, _attribute, _kind, _required in CONST_FIELDS:
        known.update(path[:i] for i in range(1, len(path) + 1))
    custom = ('Camera', 'Custom_Cfg')
    known.update({custom[:1], custom} | {custom + (key,) for key in CONST_REQUIRED_CUSTOM_CFG_KEYS}
                 | {custom + ('Balance_Ratios', channel) for channel in CONST_BALANCE_CHANNELS})
    for path, _minimum in CONST_WINDOW_FIELDS:
        known.update(path[:i] for i in range(1, len(path) + 1))
        known.update({path + ('x',), path + ('y',)})
    unknown = []

    def _Walk(node: tp.Any, prefix: tp.Tuple[str, ...]) -> None:
        """
        Description:
            Record the unknown keys under one node.

        Args:
            (1) node [Any]: The node.
            (2) prefix [Tuple<string>]: Its key path.
        """

        if not isinstance(node, dict):
            return
        for key, child in node.items():
            path = prefix + (str(key),)
            if path not in known:
                unknown.append('.'.join(path))
            else:
                _Walk(child, path)

    _Walk(data, ())
    return unknown


def __Read_Yaml(path: str, what: str, problems: tp.List[str]) -> tp.Optional[tp.Dict[str, tp.Any]]:
    """
    Description:
        Read one YAML mapping, recording (not raising) why it could not be read.

    Args:
        (1) path [string]: The file path.
        (2) what [string]: What the file is, for the message.
        (3) problems [Vector<string>]: The problem list, appended to.

    Returns:
        (1) parameter [Dict or None]: The document, or None when it could not be read.
    """

    if not os.path.isfile(path):
        problems.append('the %s "%s" does not exist' % (what, path))
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except (OSError, yaml.YAMLError) as error:
        problems.append('the %s "%s" could not be read as YAML (%s)'
                        % (what, path, str(error).splitlines()[0]))
        return None
    if not isinstance(data, dict):
        problems.append('the %s "%s" does not hold a YAML mapping' % (what, path))
        return None
    return data


def __Read_Window(block: tp.Any, dotted: str, minimum: int, problems: tp.List[str]) -> tp.Optional[tp.Tuple[int, int]]:
    """
    Description:
        Read one {x, y} pair of whole pixels (a sensor window's size or offset), recording (not
        raising) what is wrong with it.

    Args:
        (1) block [Any]: The value read from the file.
        (2) dotted [string]: Its key path, for the message.
        (3) minimum [int]: The smallest valid value (1 for a size, 0 for an offset).
        (4) problems [Vector<string>]: The problem list, appended to.

    Returns:
        (1) parameter [Tuple<int> 1x2 or None]: (x, y), or None when it is not valid.
    """

    if not isinstance(block, dict):
        problems.append('%s is required but missing (x and y, in pixels)' % dotted)
        return None
    values = []
    for axis in ('x', 'y'):
        value = block.get(axis)
        if isinstance(value, int) and not isinstance(value, bool) and value >= minimum:
            values.append(value)
        else:
            problems.append('%s.%s must be a whole number of at least %d (found %r)' % (dotted, axis, minimum, value))
    return (values[0], values[1]) if len(values) == 2 else None


def __Describe_Window(resolution: tp.Tuple[int, int], offset: tp.Tuple[int, int]) -> str:
    """
    Description:
        A sensor window as a message names it: '1920 × 1200 at offset (8, 8)'.

    Args:
        (1) resolution [Vector<int> 1x2]: (width, height).
        (2) offset [Vector<int> 1x2]: (x, y).

    Returns:
        (1) parameter [string]: The description.
    """

    return '%d × %d at offset (%d, %d)' % (resolution[0], resolution[1], offset[0], offset[1])


def __Image_Size(path: str) -> tp.Optional[tp.Tuple[int, int]]:
    """
    Description:
        An image's (width, height) from its header, without decoding the pixels.

    Args:
        (1) path [string]: The image file.

    Returns:
        (1) parameter [Tuple<int> 1x2 or None]: (width, height), or None when it is not a readable image.
    """

    try:
        with Image.open(path) as image:
            return (int(image.size[0]), int(image.size[1]))
    except (OSError, ValueError):
        return None


def Calibration_Fingerprint(K: tp.Any, coefficients: tp.Dict[str, float]) -> str:
    """
    Description:
        What identifies a lens model: a SHA-256 over K and the five distortion coefficients, as
        exact floats. It is computed from the numbers, not the file, so a comment edit does not
        change it, and it can be computed both from a calibration file and from the undistortion
        record a capture set stores — which is how a reference made from a set says which lens model
        undistorted it.

    Args:
        (1) K [Matrix<float> 3x3]: The camera matrix.
        (2) coefficients [Dict<string, float>]: k1, k2, p1, p2, k3.

    Returns:
        (1) parameter [string]: The hex digest.
    """

    canonical = json.dumps({'K': [[float(value) for value in row] for row in K],
                            'coefficients': [float(coefficients[key]) for key in CONST_COEFFICIENT_KEYS]})
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def File_Sha256(path: str) -> str:
    """
    Description:
        The SHA-256 of a file's bytes: binds a reference's sidecar to the one image it describes.

    Args:
        (1) path [string]: The file.

    Returns:
        (1) parameter [string]: The hex digest.
    """

    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def Reference_Sidecar_Path(reference: str) -> str:
    """
    Description:
        The sidecar of a background reference: the same path with CONST_REFERENCE_SIDECAR_SUFFIX.

    Args:
        (1) reference [string]: The reference image path.

    Returns:
        (1) parameter [string]: The sidecar path.
    """

    return os.path.splitext(reference)[0] + CONST_REFERENCE_SIDECAR_SUFFIX


def __Check_Reference_Sidecar(reference: str, Camera_Configuration_Str: tp.Any, problems: tp.List[str],
                              notes: tp.List[tp.Tuple[str, str]]) -> None:
    """
    Description:
        Check the background reference against its sidecar: the image is the one the sidecar
        describes (its SHA-256), and it was shot at the camera's window, undistorted with the lens
        model in force, and under the lighting the configuration names. Any mismatch fails the load.

        Note:
            The guarantees are not equal. The WINDOW and CALIBRATION checks are structural: both
            sides are recorded by the software (the camera's read-back window, the fingerprint of
            the lens model that undistorted the frame). The LIGHTING check compares Camera.Lighting
            with the lighting the configuration named when the reference was made — two fields a
            person types. It fires only when someone updates Camera.Lighting: whoever changes the
            lamp and not the configuration gets no warning. That is the gap.

    Args:
        (1) reference [string]: The reference image path (it exists).
        (2) Camera_Configuration_Str [Camera_Configuration_Str(object)]: The camera block, with its
            window and its calibration (None when the hardware has none).
        (3) problems [Vector<string>]: The problem list, appended to.
        (4) notes [Vector<Tuple<string> 1x2>]: The (level, message) notes, appended to.
    """

    path = Reference_Sidecar_Path(reference)
    name = os.path.basename(reference)
    if not os.path.isfile(path):
        # LENIENT FOR NOW, deliberately. The reference in force predates sidecars; it is being
        # replaced by one made with Example/Camera/make_reference.py (docs/capture-checklist.md,
        # item 2), which writes one. Once that reference is in force, make a missing sidecar a load
        # failure (a problem, like the mismatches below) so this lenient path does not outlive its
        # reason — the same as the calibration's unrecorded window in __Read_Calibration.
        notes.append(('WARNING', '%s has no provenance sidecar (%s), so the window, calibration and lighting '
                                 'it was shot under are unknown: background subtraction may be comparing '
                                 'frames against a reference from another window, lens model or light. '
                                 'Make references with Example/Camera/make_reference.py, which writes it.'
                                 % (name, os.path.basename(path))))
        return
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            sidecar = json.load(handle)
        assert isinstance(sidecar, dict)
        image_sha256 = str(sidecar['image_sha256'])
        window = (tuple(int(v) for v in sidecar['window']['resolution']),
                  tuple(int(v) for v in sidecar['window']['offset']))
        calibration = sidecar['calibration']
        fingerprint = None if calibration is None else str(calibration['fingerprint'])
        lighting = str((sidecar.get('hardware') or {}).get('lighting', ''))
    except (OSError, ValueError, TypeError, KeyError, AssertionError) as error:
        problems.append('the reference sidecar %s could not be read (%s: %s); remake the reference with '
                        'Example/Camera/make_reference.py' % (os.path.basename(path), type(error).__name__, error))
        return

    if File_Sha256(reference) != image_sha256:
        problems.append('%s is not the image its sidecar %s describes (the file was replaced or edited after the '
                        'sidecar was written); remake the reference with Example/Camera/make_reference.py'
                        % (name, os.path.basename(path)))
        return
    camera_window = (tuple(Camera_Configuration_Str.Resolution), tuple(Camera_Configuration_Str.Offset))
    if window != camera_window:
        problems.append('%s was shot at %s, but Camera.Resolution and Camera.Offset set the camera to %s: '
                        're-shoot the reference at this window' % (name, __Describe_Window(*window),
                                                                  __Describe_Window(*camera_window)))
    calibration_now = Camera_Configuration_Str.Calibration
    fingerprint_now = (None if calibration_now is None or not calibration_now.Coefficients
                       else Calibration_Fingerprint(calibration_now.K, calibration_now.Coefficients))
    if fingerprint != fingerprint_now:
        shot_with = 'no calibration' if fingerprint is None else 'another lens model (%s)' % calibration.get('file', '?')
        now = 'none' if fingerprint_now is None else 'the calibration in force'
        problems.append('%s was undistorted with %s, but this configuration uses %s: its geometry does not match '
                        'the frames it would be compared with. Re-shoot the reference under the calibration in '
                        'force' % (name, shot_with, now))
    if lighting and Camera_Configuration_Str.Lighting and lighting != Camera_Configuration_Str.Lighting:
        problems.append("%s was shot under lighting '%s', but Camera.Lighting is '%s': re-shoot the reference under "
                        'this lighting, or correct Camera.Lighting' % (name, lighting, Camera_Configuration_Str.Lighting))


def Build_Reference_Sidecar(image_path: str, *, source: str, shot: str, configuration: str,
                            window: tp.Dict[str, tp.List[int]], undistortion: tp.Optional[tp.Dict[str, tp.Any]],
                            hardware: tp.Dict[str, str]) -> tp.Dict[str, tp.Any]:
    """
    Description:
        The sidecar of a background reference, from the record of the capture set it was made from —
        the one format __Check_Reference_Sidecar reads, defined beside it so the two cannot drift.

    Args:
        (1) image_path [string]: The reference image (as written: its bytes are hashed).
        (2) source [string]: REQUIRED, keyword-only: the capture-set frame it was copied from.
        (3) shot [string]: REQUIRED, keyword-only: when the set was captured (ISO 8601).
        (4) configuration [string]: REQUIRED, keyword-only: the configuration the set was captured under.
        (5) window [Dict]: REQUIRED, keyword-only: the set's read-back window {'resolution', 'offset'}.
        (6) undistortion [Dict or None]: REQUIRED, keyword-only: the set's undistortion record (K,
                                         coefficients, the calibration file) or None when uncalibrated.
        (7) hardware [Dict<string, string>]: REQUIRED, keyword-only: the set's camera, lens and lighting.

    Returns:
        (1) parameter [Dict]: The sidecar, ready to serialise.
    """

    calibration = None
    if undistortion is not None:
        calibration = {'file': str(undistortion.get('calibration', '')),
                       'fingerprint': Calibration_Fingerprint(undistortion['K'], undistortion['coefficients'])}
    return {'note': ('Provenance of this background reference, written by Example/Camera/make_reference.py from '
                     'the capture set named in source. Do not edit: Load_Configuration checks the image against '
                     'image_sha256 and the window, calibration and lighting against the configuration.'),
            'image_sha256': File_Sha256(image_path), 'source': source, 'shot': shot,
            'configuration': configuration,
            'window': {'resolution': [int(v) for v in window['resolution']],
                       'offset': [int(v) for v in window['offset']]},
            'calibration': calibration, 'hardware': dict(hardware)}


def __Read_Calibration(path: str, hardware: str, resolution: tp.Optional[tp.Tuple[int, int]],
                       offset: tp.Optional[tp.Tuple[int, int]], problems: tp.List[str],
                       notes: tp.List[tp.Tuple[str, str]]) -> tp.Tuple[tp.Optional[Camera_Calibration_Parameters_Str],
                                                                        tp.Optional[Scale_Str]]:
    """
    Description:
        Read and validate a hardware's calibration file. The file itself is optional: without it
        there is no calibration (None) and no scale, with a warning to run calibrate.py. A file that
        exists must hold K (3 x 3) and the five distortion coefficients; its Conversion_Factor is
        optional, and its documented default is 'no scale' — objects are then not measured, never
        measured from an invented factor.

        The sensor window it was solved at (Resolution, Offset) must equal the camera's: K's
        principal point and the factor are in that window's pixels, so a calibration of another
        window fails the load rather than producing wrong millimetres. A file that does not record
        its window loads with a warning (see the note in the code on when that tightens).

    Args:
        (1) path [string]: The calibration file path.
        (2) hardware [string]: The hardware id the mode file names.
        (3 - 4) resolution, offset [Vector<int> 1x2 or None]: The camera's sensor window from the mode
                                                            file (None when invalid there).
        (5) problems [Vector<string>]: The problem list, appended to.
        (6) notes [Vector<Tuple<string> 1x2>]: The (level, message) notes, appended to.

    Returns:
        (1) parameter [Tuple]: (the calibration parameters or None, the scale or None).
    """

    if not os.path.exists(path):
        notes.append(('WARNING', 'no calibration file %s: frames will not be undistorted and objects '
                                 'will not be measured. Run Example/Camera/calibrate.py to create it.'
                                 % os.path.basename(path)))
        return None, None
    calibration = Camera_Calibration_Parameters_Str()
    data = __Read_Yaml(path, 'calibration file', problems)
    if data is None:
        return calibration, None
    name = os.path.basename(path)
    if data.get('Hardware') != hardware:
        problems.append('%s: Hardware is %r but the configuration names %r'
                        % (name, data.get('Hardware'), hardware))
    block = data.get('Calibration')
    if not isinstance(block, dict):
        problems.append('%s: Calibration is required but missing' % name)
        return calibration, None

    # The window the calibration was solved at, against the camera's.
    if 'Resolution' not in block and 'Offset' not in block:
        # LENIENT FOR NOW, deliberately. The calibration in force predates recorded windows and is
        # being replaced by the multi-view recalibration (docs/capture-checklist.md, item 1), which
        # records its window. Once that calibration is in force, make an absent window a load
        # failure (a problem, like the mismatch below) so this lenient path does not outlive its
        # reason: a calibration whose window is unknown can be wrong by an unknown amount.
        camera = __Describe_Window(resolution, offset) if resolution and offset else 'the configured window'
        notes.append(('WARNING', '%s does not record the sensor window it was solved at, so it cannot be '
                                 'checked against the camera (%s). If they differ, its principal point and '
                                 'conversion factor are in the wrong pixels: undistortion and every '
                                 'measurement may be wrong by an unknown amount. Recalibrate with '
                                 'Example/Camera/calibrate.py, which records the window.' % (name, camera)))
    else:
        solved_at = __Read_Window(block.get('Resolution'), '%s: Calibration.Resolution' % name, 1, problems)
        solved_offset = __Read_Window(block.get('Offset'), '%s: Calibration.Offset' % name, 0, problems)
        calibration.Resolution, calibration.Offset = solved_at, solved_offset
        if solved_at and solved_offset and resolution and offset and (solved_at, solved_offset) != (resolution, offset):
            problems.append('%s was solved at %s, but Camera.Resolution and Camera.Offset set the camera to %s: '
                            'its principal point and conversion factor are in the other window\'s pixels. '
                            'Recalibrate at this window, or set the camera back to the one the calibration '
                            'belongs to' % (name, __Describe_Window(solved_at, solved_offset),
                                            __Describe_Window(resolution, offset)))

    try:
        K = np.array(block.get('K'), dtype=np.float64)
        assert K.shape == (3, 3) and np.all(np.isfinite(K))
        calibration.K = K
    except (TypeError, ValueError, AssertionError):
        problems.append('%s: Calibration.K is required and must be a 3 x 3 matrix of numbers' % name)

    coefficients = block.get('Coefficients')
    missing = [key for key in CONST_COEFFICIENT_KEYS
               if not isinstance(coefficients, dict) or key not in coefficients]
    if missing:
        problems.append('%s: Calibration.Coefficients is missing the required %s'
                        % (name, ', '.join(missing)))
    else:
        try:
            calibration.Coefficients = {key: float(coefficients[key]) for key in CONST_COEFFICIENT_KEYS}
            assert all(math.isfinite(v) for v in calibration.Coefficients.values())
        except (TypeError, ValueError, AssertionError):
            problems.append('%s: Calibration.Coefficients must all be numbers' % name)

    factor = block.get('Conversion_Factor')
    if factor is None:
        notes.append(('WARNING', '%s has no Calibration.Conversion_Factor; objects will not be '
                                 'measured.' % name))
        return calibration, None
    try:
        x, y = float(factor['x']), float(factor['y'])
        assert all(math.isfinite(v) and v > 0.0 for v in (x, y))
    except (TypeError, KeyError, ValueError, AssertionError):
        problems.append('%s: Calibration.Conversion_Factor must hold a positive x and y [%s]'
                        % (name, CONST_SCALE_UNITS))
        return calibration, None
    calibration.Conversion_Factor = {'x': x, 'y': y}
    return calibration, Scale_Str(Mm_Per_Px_X=x, Mm_Per_Px_Y=y)


def Load_Configuration(config_path: str) -> Configuration_Str:
    """
    Description:
        Read a mode file and its hardware's calibration, validate them as a whole, and return the
        configuration. Every problem is collected before anything is returned, so the caller gets
        either a configuration that is valid throughout or an error listing everything wrong —
        never a configuration that is right up to the first bad field.

    Args:
        (1) config_path [string]: The mode file, 'Config_<Hardware>_Mode_<Mode>.yaml'.

    Returns:
        (1) parameter [Configuration_Str(object)]: The loaded configuration. Its Notes hold the
                                                   defaulted fields and unknown keys, to be logged.

    Raises:
        Configuration_Error_Cls: The file (or its calibration) is missing, unreadable or invalid;
                                 the message names each problem.
    """

    config_path = os.path.abspath(config_path)
    name = os.path.basename(config_path)
    problems, notes = [], []
    Configuration_Str_i = Configuration_Str(Path=config_path, Name=name)
    data = __Read_Yaml(config_path, 'configuration file', problems)
    if data is None:
        raise Configuration_Error_Cls("Configuration '%s' cannot be used: %s." % (name, '; '.join(problems)))

    # 1\ The file name and the Hardware field must agree.
    hardware, mode = __Read_Hardware(data, config_path, problems)
    Configuration_Str_i.Hardware, Configuration_Str_i.Mode = hardware, mode

    # 2\ Every setting in the field table.
    __Read_Fields(data, Configuration_Str_i, problems, notes)

    # 3\ The cross-field rules, and the paths resolved against the repository.
    reference = __Resolve_And_Cross_Check(Configuration_Str_i, problems)

    # 4\ The camera: the acquisition settings Basler_Cls cannot start without, and the sensor window
    #    it is set to on connect — against which the reference is checked.
    Configuration_Str_i.Camera.Custom_Cfg = __Read_Custom_Cfg(data, problems)
    resolution, offset = __Read_Camera_Window(data, problems)
    Configuration_Str_i.Camera.Resolution = resolution or (0, 0)
    Configuration_Str_i.Camera.Offset = offset or (0, 0)
    if reference and resolution:
        __Check_Reference_Size(reference, resolution, problems)

    # 5\ The hardware's calibration, shared by every mode on it, checked against the sensor window.
    if hardware:
        Configuration_Str_i.Calibration_Path = Calibration_Path_For(config_path, hardware)
        Configuration_Str_i.Camera.Calibration, Configuration_Str_i.Scale = __Read_Calibration(
            Configuration_Str_i.Calibration_Path, hardware, resolution, offset, problems, notes)

    # 6\ The reference's provenance, against the window, the calibration and the lighting — after
    #    the calibration is read, since the reference must have been undistorted with it.
    if reference and resolution and offset and os.path.isfile(reference):
        __Check_Reference_Sidecar(reference, Configuration_Str_i.Camera, problems, notes)

    # 7\ Keys nothing reads — usually a misspelt optional field.
    for key in __Unknown_Keys(data):
        notes.append(('WARNING', 'unrecognised key %s is ignored (misspelt?).' % key))

    if problems:
        raise Configuration_Error_Cls("Configuration '%s' cannot be used: %s."
                                      % (name, '; '.join(problems)))
    Configuration_Str_i.Notes = [(level, "Configuration '%s': %s" % (name, message))
                                 for level, message in notes]
    return Configuration_Str_i


def __Read_Hardware(data: tp.Dict[str, tp.Any], config_path: str,
                    problems: tp.List[str]) -> tp.Tuple[str, str]:
    """
    Description:
        The hardware and mode from the file name, which must agree with the Hardware field: the
        hardware keys the calibration and the run-summary CSV, so a renamed copy that still names
        another camera is refused.

    Args:
        (1) data [Dict]: The parsed mode file.
        (2) config_path [string]: The mode file's absolute path.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [string]: The hardware from the file name ('' when it has none).
        (2) parameter [string]: The mode from the file name ('' when it has none).
    """

    hardware, mode = Hardware_And_Mode(config_path)
    if not (os.path.basename(config_path).startswith(CONST_CONFIG_PREFIX) and hardware and mode):
        problems.append('the file name must be Config_<Hardware>_Mode_<Mode>.yaml')
    present, declared = __Lookup(data, ('Hardware',))
    if not present:
        problems.append('Hardware is required but missing')
    elif declared != hardware:
        problems.append('Hardware is %r but the file name says %r' % (declared, hardware))
    return hardware, mode


def __Read_Fields(data: tp.Dict[str, tp.Any], Configuration_Str: Configuration_Str,
                  problems: tp.List[str], notes: tp.List[tp.Tuple[str, str]]) -> None:
    """
    Description:
        Every setting in CONST_FIELDS into the configuration: a required one must be present, an
        optional one falls back to its default and says so, and a present value must be valid
        either way.

    Args:
        (1) data [Dict]: The parsed mode file.
        (2) Configuration_Str [Configuration_Str(object)]: The configuration being filled.
        (3) problems [Vector<string>]: Collects what is wrong.
        (4) notes [Vector<Tuple<string> 1x2>]: Collects the (level, message) notes to log.
    """

    for path, attribute, kind, required in CONST_FIELDS:
        dotted = '.'.join(path)
        target = Configuration_Str
        for part in attribute[:-1]:
            target = getattr(target, part)
        present, value = __Lookup(data, path)
        if not present or value is None:
            if required:
                problems.append('%s is required but missing' % dotted)
            else:
                notes.append(('INFO', '%s not set; using the default %r.'
                                      % (dotted, getattr(target, attribute[-1]))))
            continue
        valid, value, expected = __Check(kind, value)
        if not valid:
            problems.append('%s must be %s (found %r)' % (dotted, expected, value))
            continue
        setattr(target, attribute[-1], value)


def __Resolve_And_Cross_Check(Configuration_Str: Configuration_Str, problems: tp.List[str]) -> str:
    """
    Description:
        The rules between fields, and the paths resolved against the repository: the error band
        below the warning band; the model paths and the harness's test frames resolved (a model is
        checked when it loads; the frames are the harness's to check, so their absence must not
        stop the application loading); the background reference resolved and required to exist —
        it is data the repository tracks, and without it the pipeline loses a fusion cue.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration being filled.
        (2) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [string]: The resolved reference path, or '' when it is unset or missing.
    """

    if Configuration_Str.Confidence.Error_Below >= Configuration_Str.Confidence.Warn_Below:
        problems.append('Confidence.Error_Below (%d) must be below Confidence.Warn_Below (%d)'
                        % (Configuration_Str.Confidence.Error_Below,
                           Configuration_Str.Confidence.Warn_Below))
    for Parameters_Str in (Configuration_Str.Segmentation, Configuration_Str.Description):
        if Parameters_Str.Model_Path:
            Parameters_Str.Model_Path = __Resolve_Model_Path(Parameters_Str.Model_Path)
    if Configuration_Str.Evaluation.Frames:
        Configuration_Str.Evaluation.Frames = __Resolve_Model_Path(Configuration_Str.Evaluation.Frames)
    reference = Configuration_Str.Segmentation.Background_Reference
    if reference:
        reference = Configuration_Str.Segmentation.Background_Reference = __Resolve_Model_Path(reference)
        if not os.path.isfile(reference):
            problems.append('Segmentation.Background.Reference: the file "%s" does not exist' % reference)
            reference = ''
    return reference


def __Read_Custom_Cfg(data: tp.Dict[str, tp.Any], problems: tp.List[str]) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Camera.Custom_Cfg, the acquisition settings Basler_Cls cannot start without: each of the
        four is required and typed (CONST_CUSTOM_CFG_KINDS), and Balance_Ratios is exactly the
        CONST_BALANCE_CHANNELS, each above 0. Only valid values are kept, so nothing the camera does
        not read is handed to it.

    Args:
        (1) data [Dict]: The parsed mode file.
        (2) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Dict]: The validated settings.
    """

    custom = __Lookup(data, ('Camera', 'Custom_Cfg'))[1]
    if not isinstance(custom, dict):
        problems.append('Camera.Custom_Cfg is required but missing')
        custom = {}
    missing = [key for key in CONST_REQUIRED_CUSTOM_CFG_KEYS if key not in custom]
    if missing and custom:
        problems.append('Camera.Custom_Cfg is missing the required %s' % ', '.join(missing))
    settings = {}
    for key in (key for key in CONST_REQUIRED_CUSTOM_CFG_KEYS if key in custom):
        dotted = 'Camera.Custom_Cfg.%s' % key
        if key == 'Balance_Ratios':
            ratios = __Read_Balance_Ratios(custom[key], dotted, problems)
            if ratios is not None:
                settings[key] = ratios
            continue
        valid, value, expected = __Check(CONST_CUSTOM_CFG_KINDS[key], custom[key])
        if valid:
            settings[key] = value
        else:
            problems.append('%s must be %s (found %r)' % (dotted, expected, custom[key]))
    return settings


def __Read_Balance_Ratios(ratios: tp.Any, dotted: str, problems: tp.List[str]) -> tp.Optional[tp.Dict[str, float]]:
    """
    Description:
        The white-balance ratios: exactly the CONST_BALANCE_CHANNELS, each a number above 0.

    Args:
        (1) ratios [Any]: The value read from the file.
        (2) dotted [string]: Its key path, for the messages.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Dict<string, float> or None]: The valid channels, or None when the value is
                                                     not a mapping at all.
    """

    if not isinstance(ratios, dict):
        problems.append('%s must be a mapping of %s to numbers above 0 (found %r)'
                        % (dotted, ', '.join(CONST_BALANCE_CHANNELS), ratios))
        return None
    absent = [channel for channel in CONST_BALANCE_CHANNELS if channel not in ratios]
    if absent:
        problems.append('%s is missing the required %s' % (dotted, ', '.join(absent)))
    checked = {}
    for channel in (channel for channel in CONST_BALANCE_CHANNELS if channel in ratios):
        valid, value, expected = __Check('positive', ratios[channel])
        if valid:
            checked[channel] = value
        else:
            problems.append('%s.%s must be %s (found %r)' % (dotted, channel, expected, ratios[channel]))
    return checked


def __Read_Camera_Window(data: tp.Dict[str, tp.Any],
                         problems: tp.List[str]) -> tp.Tuple[tp.Optional[tp.Tuple[int, int]],
                                                            tp.Optional[tp.Tuple[int, int]]]:
    """
    Description:
        The sensor window the camera is set to on connect: Camera.Resolution and Camera.Offset.

    Args:
        (1) data [Dict]: The parsed mode file.
        (2) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Vector<int> 1x2 or None]: The resolution, or None when invalid.
        (2) parameter [Vector<int> 1x2 or None]: The offset, or None when invalid.
    """

    window = {}
    for path, minimum in CONST_WINDOW_FIELDS:
        window[path[-1]] = __Read_Window(__Lookup(data, path)[1], '.'.join(path), minimum, problems)
    return window['Resolution'], window['Offset']


def __Check_Reference_Size(reference: str, resolution: tp.Tuple[int, int], problems: tp.List[str]) -> None:
    """
    Description:
        The reference must be the camera's window size. It is validated against the camera's
        resolution — never the other way round: the camera does not read its size from a picture on
        disk, so swapping the reference cannot silently reconfigure the sensor. A mismatch fails
        here, at load, naming both sizes, instead of surfacing at the first ANALYZE.

    Args:
        (1) reference [string]: The resolved reference path (it exists).
        (2) resolution [Vector<int> 1x2]: The camera's window size.
        (3) problems [Vector<string>]: Collects what is wrong.
    """

    size = __Image_Size(reference)
    if size is None:
        problems.append('Segmentation.Background.Reference: the file "%s" could not be read as an image'
                        % reference)
    elif size != resolution:
        problems.append("Segmentation.Background.Reference is %d × %d but Camera.Resolution is %d × %d: this "
                        "configuration's reference does not match its camera resolution. Re-shoot the "
                        'empty-surface reference at %d × %d, or correct Camera.Resolution'
                        % (size + resolution + resolution))


def Discover_Configurations(directory: str) -> tp.List[tp.Tuple[str, tp.Optional[Configuration_Str], str]]:
    """
    Description:
        Every mode file ('Config_*_Mode_*.yaml') in a directory, each loaded through
        Load_Configuration — the one reader — so the Configuration dialog lists them by their display
        name. A file that cannot be loaded is still listed, with the reason, so it is visible and
        not silently missing.

    Args:
        (1) directory [string]: The directory to look in (Configuration/).

    Returns:
        (1) parameter [Vector<Tuple>]: (path, the configuration or None, the error or ''), ordered by
                                       display name (unloadable files last, by file name).
    """

    found = []
    names = sorted(os.listdir(directory)) if os.path.isdir(directory) else []
    for name in names:
        if not (name.startswith(CONST_CONFIG_PREFIX) and CONST_MODE_SEPARATOR in name
                and name.endswith(('.yaml', '.yml'))):
            continue
        path = os.path.join(directory, name)
        try:
            found.append((path, Load_Configuration(path), ''))
        except Configuration_Error_Cls as error:
            found.append((path, None, str(error)))
    return sorted(found, key=lambda entry: (entry[1] is None,
                                            entry[1].Identity.Display_Name if entry[1] else os.path.basename(entry[0])))


def Display_Path(path: str) -> str:
    """
    Description:
        A file path as it is logged and recorded: relative to the repository root when it lies
        inside it (so it reads the same on every checkout), absolute otherwise.

    Args:
        (1) path [string]: The path.

    Returns:
        (1) parameter [string]: The path to show.
    """

    path = os.path.abspath(path)
    inside = os.path.commonpath([path, CONST_PROJECT_ROOT]) == CONST_PROJECT_ROOT
    return os.path.relpath(path, CONST_PROJECT_ROOT) if inside else path


def Config_Sources_Log_Line(Configuration_Str: Configuration_Str) -> str:
    """
    Description:
        What a configuration reads beside itself: the calibration and the background reference,
        logged together on load so a run can be traced to both.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The loaded configuration.

    Returns:
        (1) parameter [string]: The log line.
    """

    calibration = (Display_Path(Configuration_Str.Calibration_Path)
                   if Configuration_Str.Camera.Calibration is not None else 'none (no calibration file)')
    return ("Configuration '%s' reads calibration %s and background reference %s."
            % (Configuration_Str.Name, calibration,
               Display_Path(Configuration_Str.Segmentation.Background_Reference)))


def __Article(noun: str) -> str:
    """
    Description:
        The noun with 'a' or 'an' by its first letter ('a Basler', 'an Allied Vision').

    Args:
        (1) noun [string]: The noun phrase.

    Returns:
        (1) parameter [string]: The phrase with its article.
    """

    return ('an ' if noun[:1].lower() in 'aeiou' else 'a ') + noun


def Describe_Configuration(Configuration_Str: Configuration_Str) -> str:
    """
    Description:
        What a configuration describes, as one sentence built from its own fields: the model set,
        and the camera, lens and lighting when the configuration names them — 'Model set
        JIC_AnyScan_All_v1 on a Basler a2A1920-51gcPRO with a Computar M1228-MPW3 lens, lit by an
        Effilux EFFI-FD-200-200-000.' A field the configuration does not set is left out whole,
        never as a dangling clause.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration.

    Returns:
        (1) parameter [string]: The sentence.
    """

    camera = Configuration_Str.Camera
    sentence = 'Model set %s' % Configuration_Str.Identity.Model_Set
    if camera.Model:
        sentence += ' on %s' % __Article(camera.Model)
    if camera.Lens:
        sentence += ' with %s lens' % __Article(camera.Lens)
    if camera.Lighting:
        sentence += ', lit by %s' % __Article(camera.Lighting)
    return sentence + '.'


def Hardware_Record(Configuration_Str: Configuration_Str) -> tp.Dict[str, str]:
    """
    Description:
        The hardware a configuration names — camera, lens, lighting — as the record a capture set
        stores, so a stored analysis can say what photographed it and what lit it. An unset field
        is stored as '' (the configuration did not say), never guessed.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration.

    Returns:
        (1) parameter [Dict<string, string>]: {'hardware', 'camera', 'lens', 'lighting'}.
    """

    camera = Configuration_Str.Camera
    return {'hardware': Configuration_Str.Hardware, 'camera': camera.Model, 'lens': camera.Lens,
            'lighting': camera.Lighting}


def Config_Offered_Log_Line(Configuration_Str: Configuration_Str) -> str:
    """
    Description:
        The startup line: which configuration the application found and will offer — and only
        that. At startup the file has been READ (to know it is usable and what to call it), not
        LOADED: its calibration, reference, classification and scale are logged when it is loaded
        (Config_Loaded_Log_Line and the lines beside it), so the log never claims more than happened.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration read at startup.

    Returns:
        (1) parameter [string]: The log line.
    """

    return ("Configuration found: '%s' (%s). It is offered in the Configuration dialog; nothing is "
            'loaded until it is loaded there.' % (Configuration_Str.Identity.Display_Name, Configuration_Str.Name))


def Config_Loaded_Log_Line(Configuration_Str: Configuration_Str) -> str:
    """
    Description:
        The one-line configuration-loaded message: which configuration, on which hardware, and
        whether it classifies. This is the answer when someone later asks why the UI shows (or
        does not show) OK/NOK. Pure, so it is testable without launching the app.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The loaded configuration.

    Returns:
        (1) parameter [string]: The log line.
    """

    if Configuration_Str.Classification_Enabled:
        state = ('enabled — the UI shows OK/NOK verdicts (no classifier assigns NOK yet, so '
                 'every object is OK)')
    else:
        state = 'disabled — the UI shows detected objects only, no OK/NOK verdicts'
    return ("Loaded configuration '%s' ('%s': hardware %s, mode %s, model set %s). Classification is %s."
            % (Configuration_Str.Name, Configuration_Str.Identity.Display_Name, Configuration_Str.Hardware,
               Configuration_Str.Mode, Configuration_Str.Identity.Model_Set, state))


def Write_Calibration(Camera_Calibration_Parameters_Str: Camera_Calibration_Parameters_Str, *,
                      hardware: str, header_source: tp.Optional[str], output_path: str,
                      record: tp.Dict[str, tp.Any]) -> bool:
    """
    Description:
        Write a hardware's calibration file from a freshly solved result: the header comment,
        'Hardware', and the 'Calibration' block (how it was solved, K, the coefficients and the
        conversion factor).

        Note:
            The writer can only destroy what it owns. When output_path already exists it is read
            first, and the write is REFUSED if the file holds any top-level key other than
            'Hardware' and 'Calibration', any key in 'Calibration' the writer does not produce, or
            another hardware — so content someone added to a calibration file is never silently
            regenerated away. The existing header comment is kept.

    Args:
        (1) Camera_Calibration_Parameters_Str [Camera_Calibration_Parameters_Str(object)]: The
            solved calibration: K, the distortion coefficients, the mm/px factors, and the sensor
            window it was solved at (Resolution and Offset — REQUIRED: a calibration that does not
            say which pixels it is in is refused).
        (2) hardware [string]: REQUIRED, keyword-only: the hardware id the calibration belongs to.
        (3) header_source [string or None]: REQUIRED, keyword-only: a calibration file whose
            header comment is copied (the one in force); None writes a minimal header.
        (4) output_path [string]: REQUIRED, keyword-only: the file written (may be the one in force).
        (5) record [Dict]: REQUIRED, keyword-only: how the calibration was solved — 'date',
            'images', 'views' {'total', 'flat', 'tilted'}, 'rms_px', 'square_mm' and
            'board_height_mm' (the reference plane: the flat boards' surface above the table).

    Returns:
        (1) parameter [bool]: True if the file was written, False if refused or failed.
    """

    try:
        # 1\ Refuse a calibration that does not record its window, and anything the writer does not own.
        assert (Camera_Calibration_Parameters_Str.Resolution is not None
                and Camera_Calibration_Parameters_Str.Offset is not None), (
            'the calibration does not record the sensor window (Resolution and Offset) it was solved at')
        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                existing = yaml.safe_load(f)
            assert isinstance(existing, dict), 'it does not hold a YAML mapping'
            foreign = [key for key in existing if key not in CONST_CALIBRATION_FILE_KEYS]
            block = existing.get('Calibration') or {}
            foreign += ['Calibration.%s' % key for key in block if key not in CONST_CALIBRATION_BLOCK_KEYS]
            assert not foreign, ('it holds %s, which this writer does not own and would delete'
                                 % ', '.join(foreign))
            assert existing.get('Hardware') in (None, hardware), (
                'it belongs to hardware %r, not %r' % (existing.get('Hardware'), hardware))

        # 2\ The header comment: the leading comment lines of the file in force.
        header = []
        if header_source is not None and os.path.isfile(header_source):
            with open(header_source, 'r', encoding='utf-8') as f:
                for line in f.read().splitlines():
                    if line.strip() and not line.lstrip().startswith('#'):
                        break
                    header.append(line)
        # The file's own header ends where the writer's body begins: the body writes the hardware
        # comment itself, so a copy of it (and the blank lines around it) is not header.
        while header and header[-1].strip() in ('', CONST_CALIBRATION_HARDWARE_COMMENT):
            header.pop()
        if not header:
            header = ['# The calibration of hardware %s.' % hardware,
                      '# Written by Example/Camera/calibrate.py via Configuration.Core.Write_Calibration.', '']

        # 3\ Format the numeric values with repr() to preserve full, round-trippable precision.
        matrix_rows = '\n'.join('    - [' + ', '.join(repr(float(value)) for value in row) + ']'
                                for row in Camera_Calibration_Parameters_Str.K)
        coefficients = '\n'.join(f'    {key}: {repr(float(value))}'
                                 for key, value in Camera_Calibration_Parameters_Str.Coefficients.items())
        factors = '\n'.join(f'    {key}: {repr(float(value))}'
                            for key, value in Camera_Calibration_Parameters_Str.Conversion_Factor.items())
        views = record['views']
        body = (CONST_CALIBRATION_HARDWARE_COMMENT + '\n'
                f'Hardware: {hardware}\n\n'
                'Calibration:\n'
                '  # How this calibration was solved (Example/Camera/calibrate.py --images).\n'
                '  Solved:\n'
                f'    Date: {record["date"]}\n'
                f'    Images: {json.dumps(record["images"])}\n'
                '    # Views used: flat boards (lens model + factor) and tilted ones (lens model).\n'
                f'    Views: {{Total: {int(views["total"])}, Flat: {int(views["flat"])}, '
                f'Tilted: {int(views["tilted"])}}}\n'
                f'    Reprojection_RMS_Px: {repr(float(record["rms_px"]))}\n'
                '    # The board\'s square size [mm], as calipered.\n'
                f'    Square_Size_Mm: {repr(float(record["square_mm"]))}\n'
                '    # The reference plane: the flat boards\' surface height above the table [mm].\n'
                '    # The factor is exact in this plane only.\n'
                f'    Board_Height_Mm: {repr(float(record["board_height_mm"]))}\n'
                '  # The sensor window this calibration was solved at [px]: its size and its offset on the\n'
                '  # sensor. K and the conversion factor are in this window\'s pixels; a configuration that\n'
                '  # sets the camera to any other window fails to load with this calibration.\n'
                '  Resolution: {x: %d, y: %d}\n' % tuple(int(v) for v in Camera_Calibration_Parameters_Str.Resolution) +
                '  Offset: {x: %d, y: %d}\n' % tuple(int(v) for v in Camera_Calibration_Parameters_Str.Offset) +
                '  # Camera calibration (intrinsic) matrix K, 3 x 3, row-major.\n'
                f'  K:\n{matrix_rows}\n'
                '  # Distortion coefficients: [k1, k2, p1, p2, k3].\n'
                f'  Coefficients:\n{coefficients}\n'
                '  # Pixel-to-millimeter conversion factors for the x and y axes [mm/px], in the\n'
                '  # undistorted (alpha = 1) pixel space measurement happens in.\n'
                f'  Conversion_Factor:\n{factors}\n')

        # 4\ Write the header and the regenerated content.
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(header).rstrip('\n') + '\n\n' + body)
        return True

    except (AssertionError, OSError, KeyError, yaml.YAMLError) as error:
        print(f'[ERROR] Information: {error}')
        print(f'[ERROR] The calibration was NOT written to "{output_path}".')
        return False
