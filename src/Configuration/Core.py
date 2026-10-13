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
import re
import math
import string
import tempfile
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
#   ../Parameters/Catalogue
from Parameters.Catalogue import (Catalogue_Item_Str, Catalogue_Reference_Str, Catalogue_Side_Str,
                                  Catalogue_Defect_Str, Catalogue_Hole_Group_Str, Catalogue_Stain_Str)

"""
Description:
    Initialization of constants.

    THE configuration layer: the only code that reads a configuration or calibration file. A
    mode file (Config_<Hardware>_Mode_<Mode>.yaml) is read, validated AS A WHOLE and returned as
    one Configuration_Str — or refused with every problem listed, so a file that is wrong halfway
    through is never partly applied. Every module that needs a setting receives it from that
    structure; none opens the YAML for itself. Qt-free.

    The rules:
        - A REQUIRED field (the hardware, the station, both model paths, the station-event directory —
          which must exist and be writable — both prompts, the identity's display name and model set; and
          in the station file, the calibration, the background reference — which must exist — the
          camera's acquisition settings and its sensor window) has no default: its absence fails the
          load, naming the field.
        - The configuration is a CHAIN OF REFERENCES, each kind in its own folder: a mode file
          (Configuration/Mode/) names its station file (Station, in Configuration/Station/), and the
          station names its calibration (Calibration, in Configuration/Calibration/). A reference is a
          file name, never a path, resolved in its kind's folder of the repository wherever the file
          holding it is — so a local copy of a mode file reads the shipped station and calibration. Each
          link must agree: the station's Hardware is the mode's, and the calibration's Hardware and
          sensor window are the station's; a mismatch fails the load, naming both files. A missing
          reference fails it too, naming the line to add.
        - The STATION file holds the camera, the reference and the calibration in force, shared by every
          mode that names it, and a mode file never overrides it: one holding Camera, Calibration or a
          background reference fails the load, naming the station file.
        - The SENSOR WINDOW (Camera.Resolution, Camera.Offset) is set on the camera on connect, and
          what depends on it is checked against it here, at load: a background reference of another
          size fails the load, naming both sizes, and so does a calibration solved at another window.
          The camera never takes its size from the reference — the hardware follows the
          configuration, and the data is validated against it.
        - The BACKGROUND REFERENCE carries its provenance in a sidecar (<reference>.json), written by
          Example/Camera/make_reference.py from what the camera reported, never by hand. The load
          checks it: the image must be the one the sidecar describes, and its window, calibration
          and lighting must be the configuration's. The window and calibration checks are structural;
          the lighting check compares two fields a person types (see __Check_Reference_Sidecar).
        - The CALIBRATION is required: nothing loads uncalibrated. It must be complete and valid: K and
          all five coefficients. A camera calibrated for the first time is read by Load_Station_Camera,
          which reads the station's camera alone, for Example/Camera/calibrate.py.
        - An OPTIONAL field falls back to the documented default (the Parameters/Configuration
          field default, which is the value the code ran with as a constant) and the fall-back is
          recorded in Configuration_Str.Notes for the caller to log.
        - A value that is present but invalid fails the load: a wrong value is never replaced by
          a default.
        - An unrecognised key is recorded as a warning, so a misspelt optional field is visible.
        - A CATALOGUE block (Catalogue.Item) makes the mode a catalogue mode: the item file
          (Data/Catalogue/<item>/<item>.yaml) is read here too, by the same rules, and its problems
          fail the configuration. A catalogue mode measures, so it needs a calibration with a
          Conversion_Factor and the board height that factor holds at; its scale is corrected to the
          part's top face (Scale_At_Height).
"""
# The repository root and its Configuration/ directory. This file lives in src/Configuration/,
# so the root is two levels up. Relative model paths in a configuration resolve against the root.
#   Unit [string]
CONST_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_CONFIG_DIR = os.path.join(CONST_PROJECT_ROOT, 'Configuration')
# One folder per kind under CONST_CONFIG_DIR: the mode files, the station files and the calibrations. A
# reference (a mode's Station, a station's Calibration) is a file name resolved in its kind's folder of
# the repository, wherever the file holding it is — so a local copy of a mode file kept elsewhere reads
# the shipped station and calibration (Mode_Directory, Station_Directory, Calibration_Directory).
#   Unit [string]
CONST_MODE_FOLDER = 'Mode'
CONST_STATION_FOLDER = 'Station'
CONST_CALIBRATION_FOLDER = 'Calibration'
# The configuration the application loads at startup (App/run.py --config overrides it).
#   Unit [string]
CONST_DEFAULT_CONFIG_FILE = os.path.join(CONST_CONFIG_DIR, CONST_MODE_FOLDER,
                                         'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Seg_Anything.yaml')
# The mode-file name is 'Config_<Hardware>_Mode_<Mode>.yaml'.
#   Unit [string]
CONST_CONFIG_PREFIX = 'Config_'
CONST_MODE_SEPARATOR = '_Mode_'
# The chain of references: a mode file's Station names its station file, and the station file's
# Calibration names the calibration in force. Each is REQUIRED, and is a file name of its kind
# ('<prefix>*.yaml') in its kind's folder, never a path.
#   Unit [Tuple<string>]
CONST_STATION_REFERENCE = ('Station', CONST_STATION_FOLDER, 'Station_')
CONST_CALIBRATION_REFERENCE = ('Calibration', CONST_CALIBRATION_FOLDER, 'Calibration_')
# The name calibrate.py gives a new calibration: the hardware and the time it was solved, so every
# calibration of a hardware is kept beside the others and none is ever written over.
#   Unit [string]
CONST_CALIBRATION_FILE_TEMPLATE = 'Calibration_{hardware}_{stamp}.yaml'
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
# The optional Custom_Cfg pins: values the camera is read for on connect, never set, and refused when it reads
# otherwise (Camera.Basler); absent, the value is read and logged only.
#   Unit [Dict<string, string>]
CONST_PINNED_CUSTOM_CFG_KINDS = {'Gamma': 'positive', 'Light_Source_Preset': 'text'}
CONST_BALANCE_CHANNELS = ('Red', 'Green', 'Blue')
# The distortion coefficients a calibration must hold, in OpenCV's order.
#   Unit [Tuple<string>]
CONST_COEFFICIENT_KEYS = ('k1', 'k2', 'p1', 'p2', 'k3')
# The compute devices a configuration may name.
#   Unit [Tuple<string>]
CONST_DEVICES = ('auto', 'cpu', 'mps', 'cuda')
# The comment the calibration writer puts above 'Hardware:'. The header it copies from the file in
# force stops before it — otherwise every write added one more copy (the calibration of eb00508
# carried two).
#   Unit [string]
CONST_CALIBRATION_HARDWARE_COMMENT = ("# The hardware this calibration belongs to; must equal the Hardware of the "
                                      "station that names it.")
# The background reference's sidecar: the same name with this suffix (Image_Background_002.json).
#   Unit [string]
CONST_REFERENCE_SIDECAR_SUFFIX = '.json'
# The mode file's catalogue block: the item file a catalogue mode inspects, REQUIRED within the block.
# A mode file without the block is not a catalogue mode.
#   Unit [Tuple<string>]
CONST_CATALOGUE_ITEM_PATH = ('Catalogue', 'Item')
# The board height in the calibration file: the height above the table at which its
# Conversion_Factor is exact, written by calibrate.py. Read only by a catalogue mode.
#   Unit [Tuple<string>]
CONST_BOARD_HEIGHT_PATH = ('Calibration', 'Solved', 'Board_Height_Mm')
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


def Mode_Directory() -> str:
    """
    Description:
        The folder of the shipped mode files, Configuration/Mode/: what the Configuration dialog lists.

    Returns:
        (1) parameter [string]: The folder path (absolute).
    """

    return os.path.join(CONST_CONFIG_DIR, CONST_MODE_FOLDER)


def Station_Directory() -> str:
    """
    Description:
        The folder every mode file's Station is resolved in, Configuration/Station/, wherever the mode
        file is.

    Returns:
        (1) parameter [string]: The folder path (absolute).
    """

    return os.path.join(CONST_CONFIG_DIR, CONST_STATION_FOLDER)


def Calibration_Directory() -> str:
    """
    Description:
        The folder every station file's Calibration is resolved in, Configuration/Calibration/, and the
        one calibrate.py writes into.

    Returns:
        (1) parameter [string]: The folder path (absolute).
    """

    return os.path.join(CONST_CONFIG_DIR, CONST_CALIBRATION_FOLDER)


def Reference_Line(path: str, key: str) -> tp.Optional[int]:
    """
    Description:
        The line of a file's key, counted from 1: where a person changes a reference, or adds one below. The
        key is a top-level one ('Station', 'Calibration', 'Hardware') or a dotted path into a block
        ('Background.Reference': the first 'Reference:' inside the top-level 'Background:' block). Only the
        configuration layer reads these files, so a tool that tells the user which line to edit asks here.

    Args:
        (1) path [string]: The YAML file.
        (2) key [string]: The top-level key, or a dotted path of keys.

    Returns:
        (1) parameter [int or None]: The line number, or None when the file has no such key or cannot be read.
    """

    parts = key.split('.')
    # The indentation of the block being searched (-1: the top level, whose keys start at column 0).
    depth, indent = 0, -1
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for number, line in enumerate(f, start=1):
                stripped = line.lstrip(' ')
                if not stripped.strip() or stripped.startswith('#'):
                    continue
                leading = len(line) - len(stripped)
                if depth > 0 and leading <= indent:
                    return None                                 # the block ended without the key
                if (leading == 0 if depth == 0 else leading > indent) \
                        and re.match(r'%s\s*:' % re.escape(parts[depth]), stripped):
                    if depth == len(parts) - 1:
                        return number
                    depth, indent = depth + 1, leading
    except OSError:
        return None
    return None


def __Kind_Files(directory: str, prefix: str, hardware: str) -> tp.List[str]:
    """
    Description:
        The files of one kind for one hardware ('<prefix><Hardware>*.yaml' in its folder), named when a
        reference is missing so the message can say which line to add.

    Args:
        (1) directory [string]: The kind's folder.
        (2) prefix [string]: 'Station_' or 'Calibration_'.
        (3) hardware [string]: The hardware id.

    Returns:
        (1) parameter [Vector<string>]: The file names, sorted.
    """

    names = sorted(os.listdir(directory)) if os.path.isdir(directory) else []
    return [name for name in names if name.startswith(prefix + hardware) and name.endswith('.yaml')]


def __Read_Reference(data: tp.Dict[str, tp.Any], reference: tp.Tuple[str, str, str], owner: str, hardware: str,
                     problems: tp.List[str]) -> tp.Optional[str]:
    """
    Description:
        Resolve one link of the chain: a mode's Station, or a station's Calibration. It is REQUIRED, and is a
        file name of its kind in its kind's folder of the repository, never a path, so a copy of the file
        holding it, kept anywhere, resolves to the same file. A missing reference names the line to add and
        the files that could fill it; a wrong one names the file holding it and the line.

    Args:
        (1) data [Dict]: The parsed file holding the reference.
        (2) reference [Tuple<string> 1x3]: (the key, the kind's folder name, the file-name prefix), e.g.
                                           CONST_STATION_REFERENCE.
        (3) owner [string]: The path of the file holding the reference.
        (4) hardware [string]: The hardware the referenced file must be of, for the candidates named.
        (5) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [string or None]: The referenced file (absolute, existing), or None when it is wrong.
    """

    key, folder, prefix = reference
    directory = os.path.join(CONST_CONFIG_DIR, folder)
    shown = Display_Path(directory) + os.sep
    owner_name = os.path.basename(owner)
    present, value = __Lookup(data, (key,))
    if not present:
        below = Reference_Line(owner, 'Hardware')
        where = "below 'Hardware:' (line %d)" % below if below else 'at the top level'
        candidates = __Kind_Files(directory, prefix, hardware)
        if candidates:
            # The newest: dated names sort in time.
            line, choice = candidates[-1], 'the files for %s are %s' % (hardware, ', '.join(candidates))
        else:
            line, choice = '%s<...>.yaml' % prefix, 'there is none for %s yet' % hardware
            if key == CONST_CALIBRATION_REFERENCE[0]:
                choice += '; Example/Camera/calibrate.py writes one'
        problems.append("%s names no %s, which is required: add the line '%s: %s' %s, naming a file in %s (%s)"
                        % (owner_name, key.lower(), key, line, where, shown, choice))
        return None
    line = Reference_Line(owner, key)
    at = '%s line %d' % (owner_name, line) if line else owner_name
    if (not isinstance(value, str) or value != os.path.basename(value) or '/' in value or '\\' in value
            or not value.startswith(prefix) or not value.endswith('.yaml')):
        problems.append("%s: %s must be the name of a file in %s ('%s*.yaml'), not a path or another kind of file; "
                        "it is %r" % (at, key, shown, prefix, value))
        return None
    path = os.path.join(directory, value)
    if not os.path.isfile(path):
        problems.append('%s names the %s %s, which does not exist in %s' % (at, key.lower(), value, shown))
        return None
    return path


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
                           'grey', 'count', 'size', 'kernel', 'nonnegative', 'positive', 'hue' or
                           'device'.
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
        'hue':         (is_integer and 0 <= value <= 179, value, "a whole number from 0 to 179 (OpenCV's hue)"),
        'device':      (isinstance(value, str) and (value in CONST_DEVICES or value.startswith('cuda:')),
                        value, 'one of %s (or cuda:N)' % ', '.join(CONST_DEVICES)),
    }
    return rules[kind]


# Every setting a mode file holds, as (the YAML key path, the Configuration_Str attribute path,
# the kind, required). A required setting's default below is never used; an optional one's is the
# field default of its structure (Parameters/Configuration).
#   Unit [Vector<Tuple>]
CONST_FIELDS = (
    (('General', 'Station_Events', 'Directory'), ('Station_Events_Directory',), 'path', True),
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
    (('Evaluation', 'Frames'), ('Evaluation', 'Frames'), 'path', False),
)
# Every setting a station file holds beside its acquisition settings and sensor window (read by their own
# readers), in the same form (attributes of Configuration_Str).
#   Unit [Vector<Tuple>]
CONST_STATION_CAMERA_FIELDS = (
    (('Camera', 'Model'), ('Camera', 'Model'), 'text', False),
    (('Camera', 'Lens'), ('Camera', 'Lens'), 'text', False),
    (('Camera', 'Lighting'), ('Camera', 'Lighting'), 'text', False),
)
CONST_STATION_FIELDS = CONST_STATION_CAMERA_FIELDS + (
    (('Background', 'Reference'), ('Segmentation', 'Background_Reference'), 'path', True),
)
# What a mode file may not hold because the station file holds it: the whole Camera block, the
# reference (Segmentation.Background.Reference before 2026-10-11), and the calibration the station names.
#   Unit [Tuple<Tuple<string>>]
CONST_STATION_ONLY_PATHS = (('Camera',), ('Segmentation', 'Background', 'Reference'), ('Calibration',))
# Every setting a catalogue item file holds, in the same form (attributes of Catalogue_Item_Str).
# Checks.Outline.Tolerance_Mm is optional and not listed: its default is the item's Tolerance_Mm, not
# a constant (__Read_Catalogue).
#   Unit [Vector<Tuple>]
CONST_CATALOGUE_FIELDS = (
    (('Name',), ('Display_Name',), 'text', True),
    (('Description',), ('Description',), 'text', False),
    (('Measurement_Rules',), ('Measurement_Rules',), 'text', False),
    (('Thickness_Mm',), ('Thickness_Mm',), 'positive', True),
    (('Tolerance_Mm',), ('Tolerance_Mm',), 'positive', True),
    (('Checks', 'Outline', 'Length_Mm'), ('Outline', 'Length_Mm'), 'positive', True),
    (('Checks', 'Outline', 'Width_Mm'), ('Outline', 'Width_Mm'), 'positive', True),
)
# The mode file's Catalogue block beside its Item, in the same form (attributes of Configuration_Str),
# read only when the block is there.
#   Unit [Vector<Tuple>]
CONST_CATALOGUE_BLOCK_FIELDS = (
    (('Catalogue', 'Identifier'), ('Identification', 'Model_Path'), 'path', True),
    (('Catalogue', 'Identify_Similarity'), ('Identification', 'Identify_Similarity'), 'unit', False),
    (('Catalogue', 'Unspecified_Area_Ratio'), ('Identification', 'Unspecified_Area_Ratio'), 'positive', False),
)
# The block that once switched the verdict UI on. It is no longer read: a configuration classifies when
# it has a Catalogue block. A file that still holds it is told so, not just warned of a misspelling.
#   Unit [Tuple<string>]
CONST_REMOVED_CLASSIFICATION_PATH = ('General', 'Classification')
# The sides a catalogue item has reference images of, in order, under <item>/reference_image/.
#   Unit [Tuple<string>]
CONST_CATALOGUE_SIDES = ('front', 'back')
# A catalogue item's side and defect entries: the keys each may hold, (key, kind, required). A side's Name is
# read now; the rest waits for the describer (phase D), validated meanwhile.
#   Unit [Tuple<Tuple>]
CONST_SIDE_KEYS = (('Name', 'text', True), ('Description', 'text', False))
CONST_DEFECT_KEYS = (('Name', 'text', True), ('Side', 'text', True), ('Looks_Like', 'text', True),
                     ('Not_A_Defect', 'text', False))
# A hole group's keys (Checks.Holes.<side>[i]), in the same form as the side and defect entries.
#   Unit [Tuple<Tuple>]
CONST_HOLE_KEYS = (('Name', 'text', True), ('Diameter_Mm', 'positive', True), ('Count', 'size', True),
                   ('From_Long_Edge_Mm', 'positive', False), ('From_Short_Edge_Mm', 'positive', False),
                   ('Pitch_Mm', 'positive', False), ('Tolerance_Mm', 'positive', False))
# A stain check's keys (Checks.Stain.<side>), every one REQUIRED: the colour band and the two sizes.
#   Unit [Tuple<Tuple>]
CONST_STAIN_KEYS = (('Hue_Min', 'hue', True), ('Hue_Max', 'hue', True), ('Saturation_Min', 'grey', True),
                    ('Value_Min', 'grey', True), ('Min_Area_Mm2', 'positive', True), ('Edge_Margin_Mm', 'nonnegative', True),
                    ('Merge_Mm', 'nonnegative', True))
# The placeholders the describer's prompt may hold, filled per judged part (Reporting.Describer_Prompt).
#   Unit [Tuple<string>]
CONST_DESCRIBER_PLACEHOLDERS = ('side', 'side_description', 'defects', 'findings')
# The words that state a number, refused with the digits in what the describer is given: given a count, it
# recited it as seen ('four small blind holes in the corners' on fronts with three or none).
#   Unit [Tuple<string>]
CONST_NUMBER_WORDS = ('two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve',
                      'dozen', 'pair', 'twice', 'double', 'half')
# The catalogue's outline tolerance override.
#   Unit [Tuple<string>]
CONST_OUTLINE_TOLERANCE_PATH = ('Checks', 'Outline', 'Tolerance_Mm')


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


def __Known_Paths(paths: tp.Iterable[tp.Tuple[str, ...]]) -> tp.Set[tp.Tuple[str, ...]]:
    """
    Description:
        Every key path a set of settings makes known: each setting's path and every block above it.

    Args:
        (1) paths [Vector<Tuple<string>>]: The settings' key paths.

    Returns:
        (1) parameter [Set<Tuple<string>>]: The known key paths.
    """

    return {path[:i] for path in paths for i in range(1, len(path) + 1)}


def __Mode_File_Known_Paths() -> tp.Set[tp.Tuple[str, ...]]:
    """
    Description:
        Every key path a mode file may hold: the field table and the catalogue block. The camera is the
        station file's (__Station_File_Known_Paths).

    Returns:
        (1) parameter [Set<Tuple<string>>]: The known key paths.
    """

    return __Known_Paths([('Hardware',), CONST_STATION_REFERENCE[:1], CONST_CATALOGUE_ITEM_PATH]
                         + [path for path, _a, _k, _r in CONST_FIELDS + CONST_CATALOGUE_BLOCK_FIELDS])


def __Station_File_Known_Paths() -> tp.Set[tp.Tuple[str, ...]]:
    """
    Description:
        Every key path a station file may hold: the hardware, the calibration it names, the station field
        table, the camera's acquisition settings and its sensor window.

    Returns:
        (1) parameter [Set<Tuple<string>>]: The known key paths.
    """

    known = __Known_Paths([('Hardware',), CONST_CALIBRATION_REFERENCE[:1]]
                          + [path for path, _a, _k, _r in CONST_STATION_FIELDS])
    custom = ('Camera', 'Custom_Cfg')
    known.update({custom[:1], custom} | {custom + (key,) for key in CONST_REQUIRED_CUSTOM_CFG_KEYS}
                 | {custom + (key,) for key in CONST_PINNED_CUSTOM_CFG_KINDS}
                 | {custom + ('Balance_Ratios', channel) for channel in CONST_BALANCE_CHANNELS})
    for path, _minimum in CONST_WINDOW_FIELDS:
        known.update(__Known_Paths([path + ('x',), path + ('y',)]))
    return known


def __Unknown_Keys(data: tp.Dict[str, tp.Any], known: tp.Set[tp.Tuple[str, ...]]) -> tp.List[str]:
    """
    Description:
        The keys in a file that no setting reads — usually a misspelt optional field, which would
        otherwise fall back to its default without a word.

    Args:
        (1) data [Dict]: The parsed document.
        (2) known [Set<Tuple<string>>]: The key paths the file may hold.

    Returns:
        (1) parameter [Vector<string>]: The unknown keys as dotted paths.
    """

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


def __Check_Reference_Sidecar(reference: str, Camera_Configuration_Str: tp.Any, problems: tp.List[str]) -> None:
    """
    Description:
        Check the background reference against its sidecar: the image is the one the sidecar
        describes (its SHA-256), and it was shot at the camera's window, undistorted with the lens
        model in force, and under the lighting the configuration names. Any mismatch fails the load,
        and so does a missing sidecar.

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
    """

    path = Reference_Sidecar_Path(reference)
    name = os.path.basename(reference)
    if not os.path.isfile(path):
        problems.append('%s has no provenance sidecar (%s), so the window, calibration and lighting it was '
                        'shot under are unknown: background subtraction may be comparing frames against a '
                        'reference from another window, lens model or light. Make the reference with '
                        'Example/Camera/make_reference.py, which writes it' % (name, os.path.basename(path)))
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


def Build_Reference_Sidecar(image_path: str, *, source: str, frames: int, shot: str, configuration: str, station: str,
                            window: tp.Dict[str, tp.List[int]], undistortion: tp.Optional[tp.Dict[str, tp.Any]],
                            hardware: tp.Dict[str, str], compared_with: tp.Optional[tp.Dict[str, tp.Any]],
                            not_compared: str) -> tp.Dict[str, tp.Any]:
    """
    Description:
        The sidecar of a background reference, from what the camera reported when it was shot — the one
        format __Check_Reference_Sidecar reads, defined beside it so the two cannot drift. Only image_sha256,
        window, calibration and the lighting are checked at load; the rest is the reference's provenance.

    Args:
        (1) image_path [string]: The reference image (as written: its bytes are hashed).
        (2) source [string]: REQUIRED, keyword-only: where the image came from ('camera').
        (3) frames [int]: REQUIRED, keyword-only: how many frames it is the mean of.
        (4) shot [string]: REQUIRED, keyword-only: when it was shot (ISO 8601).
        (5) configuration [string]: REQUIRED, keyword-only: the mode file it was shot under.
        (6) station [string]: REQUIRED, keyword-only: the station file whose camera settings were used.
        (7) window [Dict]: REQUIRED, keyword-only: the read-back window {'resolution', 'offset'}.
        (8) undistortion [Dict or None]: REQUIRED, keyword-only: the camera's undistortion record (K,
                                         coefficients, the calibration file) or None when uncalibrated.
        (9) hardware [Dict<string, string>]: REQUIRED, keyword-only: the camera, lens and lighting.
        (10) compared_with [Dict or None]: REQUIRED, keyword-only: the reference in force it was checked
                                           against ({'reference', 'image_sha256'}), or None when that reference
                                           no longer matched the camera.
        (11) not_compared [string]: REQUIRED, keyword-only: why it was not compared (recorded when
                                    compared_with is None).

    Returns:
        (1) parameter [Dict]: The sidecar, ready to serialise.
    """

    calibration = None
    if undistortion is not None:
        calibration = {'file': str(undistortion.get('calibration', '')),
                       'fingerprint': Calibration_Fingerprint(undistortion['K'], undistortion['coefficients'])}
    return {'note': ('Provenance of this background reference, written by Example/Camera/make_reference.py: the '
                     'mean of the frames it names, shot by the camera. Do not edit: Load_Configuration checks the '
                     'image against image_sha256 and the window, calibration and lighting against the '
                     'configuration.'),
            'image_sha256': File_Sha256(image_path), 'source': source, 'frames': int(frames), 'shot': shot,
            'configuration': configuration, 'station': station,
            'window': {'resolution': [int(v) for v in window['resolution']],
                       'offset': [int(v) for v in window['offset']]},
            'calibration': calibration, 'hardware': dict(hardware),
            'compared_with': None if compared_with is None else dict(compared_with),
            **({'not_compared': not_compared} if compared_with is None else {})}


def __Read_Calibration(path: str, station_path: str, hardware: str, resolution: tp.Optional[tp.Tuple[int, int]],
                       offset: tp.Optional[tp.Tuple[int, int]], problems: tp.List[str],
                       notes: tp.List[tp.Tuple[str, str]]) -> tp.Tuple[Camera_Calibration_Parameters_Str,
                                                                        tp.Optional[Scale_Str], tp.Optional[float]]:
    """
    Description:
        Read and validate the calibration a station names, against that station. It must hold K (3 x 3)
        and the five distortion coefficients; its Conversion_Factor is optional, and its documented
        default is 'no scale' — objects are then not measured, never measured from an invented factor.
        The board height its factor holds at (Solved.Board_Height_Mm) is returned when the file records
        a valid one, and None otherwise: only a catalogue mode needs it, and it says so
        (Load_Configuration).

        It must be the station's camera: the station's Hardware, and the sensor window the station sets
        (Resolution, Offset). K's principal point and the factor are in that window's pixels, so a
        calibration of another window fails the load rather than producing wrong millimetres, and so
        does a file that does not record its window: it cannot be checked. Each mismatch names both
        files.

    Args:
        (1) path [string]: The calibration file path (it exists: its reference was resolved).
        (2) station_path [string]: The station file that names it.
        (3) hardware [string]: The station's hardware id.
        (4 - 5) resolution, offset [Vector<int> 1x2 or None]: The camera's sensor window from the station
                                                            file (None when invalid there).
        (6) problems [Vector<string>]: The problem list, appended to.
        (7) notes [Vector<Tuple<string> 1x2>]: The (level, message) notes, appended to.

    Returns:
        (1) parameter [Tuple]: (the calibration parameters, the scale or None, the board height in mm
                               or None).
    """

    calibration = Camera_Calibration_Parameters_Str()
    data = __Read_Yaml(path, 'calibration file', problems)
    if data is None:
        return calibration, None, None
    _present, board_height = __Lookup(data, CONST_BOARD_HEIGHT_PATH)
    valid, board_height, _expected = __Check('nonnegative', board_height)
    board_height = board_height if valid else None
    name = os.path.basename(path)
    named_by = '%s, the calibration %s names,' % (name, os.path.basename(station_path))
    if data.get('Hardware') != hardware:
        problems.append('%s is of Hardware %r, but the station is %r: a station uses only a calibration of its '
                        'own camera and lens' % (named_by, data.get('Hardware'), hardware))
    block = data.get('Calibration')
    if not isinstance(block, dict):
        problems.append('%s: Calibration is required but missing' % name)
        return calibration, None, None

    # The window the calibration was solved at, against the camera's.
    if 'Resolution' not in block and 'Offset' not in block:
        camera = __Describe_Window(resolution, offset) if resolution and offset else 'the configured window'
        problems.append('%s does not record the sensor window it was solved at, so it cannot be checked '
                        'against the camera (%s). If they differ, its principal point and conversion factor '
                        'are in the wrong pixels: undistortion and every measurement may be wrong by an '
                        'unknown amount. Recalibrate with Example/Camera/calibrate.py, which records the '
                        'window' % (named_by, camera))
    else:
        solved_at = __Read_Window(block.get('Resolution'), '%s: Calibration.Resolution' % name, 1, problems)
        solved_offset = __Read_Window(block.get('Offset'), '%s: Calibration.Offset' % name, 0, problems)
        calibration.Resolution, calibration.Offset = solved_at, solved_offset
        if solved_at and solved_offset and resolution and offset and (solved_at, solved_offset) != (resolution, offset):
            problems.append('%s was solved at %s, but the station\'s Camera.Resolution and Camera.Offset set the '
                            'camera to %s: its principal point and conversion factor are in the other window\'s '
                            'pixels. Recalibrate at this window, name a calibration of it, or set the camera back '
                            'to the one the calibration belongs to'
                            % (named_by, __Describe_Window(solved_at, solved_offset),
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
        return calibration, None, None
    try:
        x, y = float(factor['x']), float(factor['y'])
        assert all(math.isfinite(v) and v > 0.0 for v in (x, y))
    except (TypeError, KeyError, ValueError, AssertionError):
        problems.append('%s: Calibration.Conversion_Factor must hold a positive x and y [%s]'
                        % (name, CONST_SCALE_UNITS))
        return calibration, None, None
    calibration.Conversion_Factor = {'x': x, 'y': y}
    return calibration, Scale_Str(Mm_Per_Px_X=x, Mm_Per_Px_Y=y), board_height


def Scale_At_Height(scale: Scale_Str, K: tp.Any, plane_mm: float, height_mm: float) -> Scale_Str:
    """
    Description:
        The scale moved from the plane the calibration's factor holds in to another height above the
        table. Under the pinhole model a factor is the camera's distance over its focal length
        (s = Z / f), so a plane dh closer to the camera has s' = s - dh / f, per axis: a part's top
        face 3.78 mm above the boards reads 1.06 % too large at the boards' factor (the 8 mm mounting
        plate, measured +0.89 mm on its 60 mm side over 22 instances of the test set before this
        correction).

        The focal lengths are K's, not those of the undistorted pixel space the factor is in
        (getOptimalNewCameraMatrix, Camera.Core): on the shipped calibration they differ by 0.23 % (x)
        and 0.06 % (y), which moves the correction by that fraction of itself, 0.0015 mm on 60 mm.
        Computing the undistorted matrix here would take OpenCV and the camera layer's alpha into the
        configuration layer, which sits below both.

    Args:
        (1) scale [Scale_Str(object)]: The calibration's scale, exact at plane_mm.
        (2) K [Matrix<float> 3x3]: The camera matrix.
        (3) plane_mm [float]: The height above the table the scale holds at (the board height).
        (4) height_mm [float]: The height to move it to (the part's top face).

    Returns:
        (1) parameter [Scale_Str(object)]: The scale at height_mm, its Height_Mm set.
    """

    dh = float(height_mm) - float(plane_mm)
    return Scale_Str(Mm_Per_Px_X=scale.Mm_Per_Px_X - dh / float(K[0][0]),
                     Mm_Per_Px_Y=scale.Mm_Per_Px_Y - dh / float(K[1][1]), Height_Mm=float(height_mm))


def __Read_Catalogue(path: str, problems: tp.List[str],
                     notes: tp.List[tp.Tuple[str, str]]) -> tp.Optional[Catalogue_Item_Str]:
    """
    Description:
        Read and validate one catalogue item file, by the mode file's rules: required fields present,
        present values valid, the outline's tolerance falling back to the item's and saying so, unknown
        keys reported. The file is named after its folder ('mounting_plate/mounting_plate.yaml'), so a
        copied folder whose file was not renamed is refused rather than inspected under the old name.

    Args:
        (1) path [string]: The item file (absolute).
        (2) problems [Vector<string>]: Collects what is wrong.
        (3) notes [Vector<Tuple<string> 1x2>]: Collects the (level, message) notes to log.

    Returns:
        (1) parameter [Catalogue_Item_Str(object) or None]: The item, or None when the file could not
                                                            be read.
    """

    data = __Read_Yaml(path, 'catalogue item', problems)
    if data is None:
        return None
    file_name = os.path.basename(path)
    name = os.path.splitext(file_name)[0]
    folder = os.path.basename(os.path.dirname(path))
    if name != folder:
        problems.append('%s: a catalogue item is named after its folder, so this file must be %s.yaml '
                        '(it is in %s/)' % (file_name, folder, folder))
    item = Catalogue_Item_Str(Path=path, Name=folder)
    prefix = '%s: ' % file_name
    __Read_Fields(data, item, CONST_CATALOGUE_FIELDS, problems, notes, prefix)
    present, tolerance = __Lookup(data, CONST_OUTLINE_TOLERANCE_PATH)
    dotted = prefix + '.'.join(CONST_OUTLINE_TOLERANCE_PATH)
    if not present or tolerance is None:
        item.Outline.Tolerance_Mm = item.Tolerance_Mm
        notes.append(('INFO', "%s not set; using the item's Tolerance_Mm %r." % (dotted, item.Tolerance_Mm)))
    else:
        valid, tolerance, expected = __Check('positive', tolerance)
        if valid:
            item.Outline.Tolerance_Mm = tolerance
        else:
            problems.append('%s must be %s (found %r)' % (dotted, expected, tolerance))
    if item.Outline.Length_Mm < item.Outline.Width_Mm:
        problems.append('%sChecks.Outline.Length_Mm (%r) must be at least Checks.Outline.Width_Mm (%r): the '
                        'length is the longer side' % (prefix, item.Outline.Length_Mm, item.Outline.Width_Mm))
    item.References = __Read_References(os.path.dirname(path), file_name, problems)
    item.Sides = __Read_Sides(data.get('Sides'), prefix, problems)
    item.Holes = __Read_Holes(__Lookup(data, ('Checks', 'Holes'))[1], item.Tolerance_Mm, prefix, problems)
    item.Stain = __Read_Stain(__Lookup(data, ('Checks', 'Stain'))[1], prefix, problems)
    item.Describer_Prompt = __Read_Describer_Prompt(__Lookup(data, ('Describer', 'Prompt')), prefix, problems)
    item.Defects = __Read_Defects(data.get('Defects'), prefix, problems)
    __Check_No_Numbers(item, prefix, problems)
    known = __Known_Paths([CONST_OUTLINE_TOLERANCE_PATH, ('Defects',)]
                          + [('Checks', check, side) for check in ('Holes', 'Stain') for side in CONST_CATALOGUE_SIDES]
                          + [('Checks', 'Stain', side, key) for side in CONST_CATALOGUE_SIDES for key, _k, _r in CONST_STAIN_KEYS]
                          + [('Describer', 'Prompt')]
                          + [('Sides', side, key) for side in CONST_CATALOGUE_SIDES for key, _k, _r in CONST_SIDE_KEYS]
                          + [path for path, _a, _k, _r in CONST_CATALOGUE_FIELDS])
    for key in __Unknown_Keys(data, known):
        notes.append(('WARNING', '%sunrecognised key %s is ignored (misspelt?).' % (prefix, key)))
    return item


def __Read_Entry(entry: tp.Any, keys: tp.Tuple[tp.Tuple[str, str, bool], ...], dotted: str,
                 problems: tp.List[str]) -> tp.Dict[str, str]:
    """
    Description:
        One mapping of a catalogue item (a side, a defect) against its keys: each required key present, each
        present value valid, any other key a problem — an entry is short enough that a misspelling is wrong,
        not a warning.

    Args:
        (1) entry [Any]: The mapping as read.
        (2) keys [Tuple<Tuple>]: (key, kind, required) for each key it may hold.
        (3) dotted [string]: Its place in the file, for the messages ('mounting_plate.yaml: Sides.front').
        (4) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Dict<string, string>]: The valid values, '' for an absent optional one.
    """

    values = {key: '' for key, _kind, _required in keys}
    if not isinstance(entry, dict):
        problems.append('%s must be a mapping of %s' % (dotted, ', '.join(key for key, _k, _r in keys)))
        return values
    for key in entry:
        if key not in values:
            problems.append('%s.%s is not a key it may hold (%s)' % (dotted, key, ', '.join(values)))
    for key, kind, required in keys:
        if key not in entry or entry[key] is None:
            if required:
                problems.append('%s.%s is required but missing' % (dotted, key))
            continue
        valid, value, expected = __Check(kind, entry[key])
        if valid:
            values[key] = value
        else:
            problems.append('%s.%s must be %s (found %r)' % (dotted, key, expected, entry[key]))
    return values


def __Read_Sides(block: tp.Any, prefix: str, problems: tp.List[str]) -> tp.List[Catalogue_Side_Str]:
    """
    Description:
        The item's Sides: exactly CONST_CATALOGUE_SIDES, each a Name (REQUIRED, the side sentence's) and an
        optional Description — the sides the reference images are of, so a side without a description, or a
        description of a side without a reference, is refused.

    Args:
        (1) block [Any]: The Sides block as read.
        (2) prefix [string]: The item file's name and ': '.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Vector<Catalogue_Side_Str(object)>]: The sides, in CONST_CATALOGUE_SIDES order.
    """

    if not isinstance(block, dict) or sorted(block) != sorted(CONST_CATALOGUE_SIDES):
        problems.append('%sSides is required and must hold exactly %s (found %s)'
                        % (prefix, ' and '.join(CONST_CATALOGUE_SIDES),
                           ', '.join(sorted(map(str, block))) if isinstance(block, dict) else repr(block)))
        return []
    sides = []
    for side in CONST_CATALOGUE_SIDES:
        values = __Read_Entry(block[side], CONST_SIDE_KEYS, '%sSides.%s' % (prefix, side), problems)
        sides.append(Catalogue_Side_Str(Side=side, Name=values['Name'], Description=values['Description']))
    return sides


def __Read_Holes(block: tp.Any, tolerance: float, prefix: str,
                 problems: tp.List[str]) -> tp.Dict[str, tp.List[Catalogue_Hole_Group_Str]]:
    """
    Description:
        The item's hole checks, Checks.Holes: per side (one of CONST_CATALOGUE_SIDES), a list of groups, each a
        Name, a Diameter_Mm and a Count (REQUIRED), the two edge distances (both or neither), a Pitch_Mm and its
        own Tolerance_Mm (the item's by default). On one side no two groups may capture the same diameter
        (nominal ± twice the tolerance, Vision.Utilities.Holes), or a hole would count in both. Absent means no
        hole check on any side.

    Args:
        (1) block [Any]: The Holes block as read (None when absent).
        (2) tolerance [float]: The item's Tolerance_Mm.
        (3) prefix [string]: The item file's name and ': '.
        (4) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Dict<string, Vector<Catalogue_Hole_Group_Str(object)>>]: The groups per side.
    """

    if block is None:
        return {}
    if not isinstance(block, dict) or not set(block) <= set(CONST_CATALOGUE_SIDES):
        problems.append('%sChecks.Holes must map %s to lists of hole groups (found %r)'
                        % (prefix, ' and/or '.join(CONST_CATALOGUE_SIDES), block))
        return {}
    holes = {}
    for side in (side for side in CONST_CATALOGUE_SIDES if side in block):
        if not isinstance(block[side], list) or not block[side]:
            problems.append('%sChecks.Holes.%s must be a non-empty list of hole groups' % (prefix, side))
            continue
        groups = []
        for index, entry in enumerate(block[side], 1):
            dotted = '%sChecks.Holes.%s[%d]' % (prefix, side, index)
            values = __Read_Entry(entry, CONST_HOLE_KEYS, dotted, problems)
            if bool(values['From_Long_Edge_Mm']) != bool(values['From_Short_Edge_Mm']):
                problems.append('%s sets one edge distance without the other: a position needs both' % dotted)
            groups.append(Catalogue_Hole_Group_Str(
                Name=values['Name'], Diameter_Mm=values['Diameter_Mm'] or 0.0, Count=values['Count'] or 0,
                From_Long_Edge_Mm=values['From_Long_Edge_Mm'] or 0.0, From_Short_Edge_Mm=values['From_Short_Edge_Mm'] or 0.0,
                Pitch_Mm=values['Pitch_Mm'] or 0.0, Tolerance_Mm=values['Tolerance_Mm'] or tolerance))
        ranges = sorted((g.Diameter_Mm - 2 * g.Tolerance_Mm, g.Diameter_Mm + 2 * g.Tolerance_Mm, g.Name) for g in groups)
        for (_low, high, name), (low, _high, other) in zip(ranges, ranges[1:]):
            if low < high:
                problems.append('%sChecks.Holes.%s: %s and %s capture the same diameters (each nominal ± twice its '
                                'tolerance), so a hole would count in both' % (prefix, side, name, other))
        holes[side] = groups
    return holes


def __Read_Side_Checks(block: tp.Any, name: str, prefix: str, problems: tp.List[str]) -> tp.Dict[str, tp.Any]:
    """
    Description:
        A per-side check block (Checks.Stain): a mapping of sides the part has to each side's entry.

    Args:
        (1) block [Any]: The block as read (None when absent).
        (2) name [string]: The check's name, for the messages.
        (3) prefix [string]: The item file's name and ': '.
        (4) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Dict<string, Any>]: Each side's entry as read; {} when absent or invalid.
    """

    if block is None:
        return {}
    if not isinstance(block, dict) or not set(block) <= set(CONST_CATALOGUE_SIDES):
        problems.append('%sChecks.%s must map %s to its check (found %r)'
                        % (prefix, name, ' and/or '.join(CONST_CATALOGUE_SIDES), block))
        return {}
    return block


def __Read_Stain(block: tp.Any, prefix: str, problems: tp.List[str]) -> tp.Dict[str, Catalogue_Stain_Str]:
    """
    Description:
        The item's stain checks, Checks.Stain: per side, the colour band (hue from and to, least saturation and
        value, OpenCV's HSV units), the smallest stain and the edge band left out, all REQUIRED.

    Args:
        (1) block [Any]: The Stain block as read (None when absent).
        (2) prefix [string]: The item file's name and ': '.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Dict<string, Catalogue_Stain_Str(object)>]: The checks per side.
    """

    stains = {}
    for side, entry in __Read_Side_Checks(block, 'Stain', prefix, problems).items():
        dotted = '%sChecks.Stain.%s' % (prefix, side)
        values = __Read_Entry(entry, CONST_STAIN_KEYS, dotted, problems)
        if isinstance(values['Hue_Min'], int) and isinstance(values['Hue_Max'], int) and values['Hue_Min'] > values['Hue_Max']:
            problems.append('%s: Hue_Min (%d) must not be above Hue_Max (%d)' % (dotted, values['Hue_Min'], values['Hue_Max']))
        stains[side] = Catalogue_Stain_Str(**{key: (values[key] if values[key] != '' else 0) for key in values})
    return stains


def __Read_Describer_Prompt(found: tp.Tuple[bool, tp.Any], prefix: str, problems: tp.List[str]) -> str:
    """
    Description:
        The describer's prompt for a judged part (Describer.Prompt): optional, text, and holding no placeholder
        but CONST_DESCRIBER_PLACEHOLDERS, each filled per part.

    Args:
        (1) found [Tuple<bool, Any>]: (present, value) as looked up.
        (2) prefix [string]: The item file's name and ': '.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [string]: The prompt, '' when absent.
    """

    present, value = found
    if not present or value is None:
        return ''
    valid, value, expected = __Check('text', value)
    if not valid:
        problems.append('%sDescriber.Prompt must be %s' % (prefix, expected))
        return ''
    try:
        names = {name for _text, name, _spec, _conv in string.Formatter().parse(value) if name is not None}
    except ValueError as error:
        problems.append('%sDescriber.Prompt is not a valid template (%s)' % (prefix, error))
        return ''
    unknown = sorted(names - set(CONST_DESCRIBER_PLACEHOLDERS))
    if unknown:
        problems.append('%sDescriber.Prompt holds %s; it may hold only %s' % (
            prefix, ', '.join('{%s}' % n for n in unknown), ', '.join('{%s}' % n for n in CONST_DESCRIBER_PLACEHOLDERS)))
    return value


def __Check_No_Numbers(item: Catalogue_Item_Str, prefix: str, problems: tp.List[str]) -> None:
    """
    Description:
        The texts the describer is given — each side's description, the defects and the describer's prompt — hold
        no digit and no number word (CONST_NUMBER_WORDS): the owner's ruling (2026-10-11) is that the describer
        gets the part's appearance, never a dimension or a number, which it recited as if it had seen them when
        it got them.

    Args:
        (1) item [Catalogue_Item_Str(object)]: The item, read.
        (2) prefix [string]: The item file's name and ': '.
        (3) problems [Vector<string>]: Collects what is wrong.
    """

    texts = [('Sides.%s.Description' % side.Side, side.Description) for side in item.Sides]
    texts += [('Defects[%d].%s' % (i, key), getattr(defect, key)) for i, defect in enumerate(item.Defects, 1)
              for key in ('Name', 'Looks_Like', 'Not_A_Defect')]
    texts.append(('Describer.Prompt', item.Describer_Prompt))
    for where, text in texts:
        words = [word for word in re.findall(r'[a-z]+', text.lower()) if word in CONST_NUMBER_WORDS]
        if any(character.isdigit() for character in text) or words:
            problems.append('%s%s holds a number%s; the describer is given no numbers (only the appearance)'
                            % (prefix, where, " ('%s')" % words[0] if words else ''))


def __Read_Defects(block: tp.Any, prefix: str, problems: tp.List[str]) -> tp.List[Catalogue_Defect_Str]:
    """
    Description:
        The item's Defects: a list, each entry a Name, the Side it is looked for on (one of
        CONST_CATALOGUE_SIDES), what it Looks_Like and optionally what is Not_A_Defect. Absent means none
        described yet — a part whose defective examples may not exist.

    Args:
        (1) block [Any]: The Defects block as read (None when absent).
        (2) prefix [string]: The item file's name and ': '.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Vector<Catalogue_Defect_Str(object)>]: The defects, in file order.
    """

    if block is None:
        return []
    if not isinstance(block, list):
        problems.append('%sDefects must be a list of defects (found %r)' % (prefix, block))
        return []
    defects = []
    for index, entry in enumerate(block, 1):
        dotted = '%sDefects[%d]' % (prefix, index)
        values = __Read_Entry(entry, CONST_DEFECT_KEYS, dotted, problems)
        if values['Side'] and values['Side'] not in CONST_CATALOGUE_SIDES:
            problems.append('%s.Side must be %s (found %r)' % (dotted, ' or '.join(CONST_CATALOGUE_SIDES), values['Side']))
        defects.append(Catalogue_Defect_Str(**values))
    return defects


def __Read_References(folder: str, file_name: str, problems: tp.List[str]) -> tp.List[Catalogue_Reference_Str]:
    """
    Description:
        The item's reference images, one per side (CONST_CATALOGUE_SIDES), from reference_image/ beside the
        item file: <side>.png, and <side>.txt holding the part's box as one YOLO line ('class cx cy w h',
        each of the four a fraction of the image above 0 and at most 1). Each must exist and be valid; the
        images' size is checked against the camera's window by Load_Configuration, which knows it.

    Args:
        (1) folder [string]: The item's folder.
        (2) file_name [string]: The item file's name, for the messages.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Vector<Catalogue_Reference_Str(object)>]: The valid references, in side order.
    """

    references = []
    for side in CONST_CATALOGUE_SIDES:
        image = os.path.join(folder, 'reference_image', side + '.png')
        box_file = os.path.splitext(image)[0] + '.txt'
        if not os.path.isfile(image) or not os.path.isfile(box_file):
            problems.append('%s: the %s reference needs reference_image/%s.png and reference_image/%s.txt beside it'
                            % (file_name, side, side, side))
            continue
        try:
            with open(box_file, 'r', encoding='utf-8') as handle:
                lines = [line.split() for line in handle.read().splitlines() if line.strip()]
            assert len(lines) == 1 and len(lines[0]) == 5
            box = tuple(float(value) for value in lines[0][1:])
            assert all(math.isfinite(v) and 0.0 < v <= 1.0 for v in box)
        except (OSError, ValueError, AssertionError):
            problems.append('%s: reference_image/%s.txt must hold one YOLO line, class and centre x, centre y, width, '
                            'height, each above 0 and at most 1' % (file_name, side))
            continue
        references.append(Catalogue_Reference_Str(Side=side, Image_Path=image, Box=box))
    return references


def Load_Catalogue(path: str) -> Catalogue_Item_Str:
    """
    Description:
        Read one catalogue item file on its own, validated as a whole — what a mode file's
        Catalogue.Item names. Load_Configuration reads the item through the same code.

    Args:
        (1) path [string]: The item file, Data/Catalogue/<item>/<item>.yaml (relative to the repository
                           root, or absolute).

    Returns:
        (1) parameter [Catalogue_Item_Str(object)]: The item. Its Notes hold the defaulted fields and
                                                    unknown keys, to be logged.

    Raises:
        Configuration_Error_Cls: The file is missing, unreadable or invalid; the message names each
                                 problem.
    """

    path = __Resolve_Model_Path(path)
    problems, notes = [], []
    item = __Read_Catalogue(path, problems, notes)
    if problems or item is None:
        raise Configuration_Error_Cls("Catalogue item '%s' cannot be used: %s."
                                      % (os.path.basename(path), '; '.join(problems)))
    item.Notes = notes
    return item


def __Read_Catalogue_Block(block: tp.Any, problems: tp.List[str],
                           notes: tp.List[tp.Tuple[str, str]]) -> tp.Optional[Catalogue_Item_Str]:
    """
    Description:
        A mode file's Catalogue block: Item is REQUIRED within it, and the item it names is read and
        validated here, its problems joining the configuration's.

    Args:
        (1) block [Any]: The Catalogue block as read.
        (2) problems [Vector<string>]: Collects what is wrong.
        (3) notes [Vector<Tuple<string> 1x2>]: Collects the (level, message) notes to log.

    Returns:
        (1) parameter [Catalogue_Item_Str(object) or None]: The item, or None when it cannot be read.
    """

    dotted = '.'.join(CONST_CATALOGUE_ITEM_PATH)
    present, value = __Lookup({CONST_CATALOGUE_ITEM_PATH[0]: block}, CONST_CATALOGUE_ITEM_PATH)
    if not present or value is None:
        problems.append('%s is required in a Catalogue block but missing' % dotted)
        return None
    valid, value, expected = __Check('path', value)
    if not valid:
        problems.append('%s must be %s (found %r)' % (dotted, expected, value))
        return None
    return __Read_Catalogue(__Resolve_Model_Path(value), problems, notes)


def __Check_Identification(Configuration_Str: Configuration_Str, resolution: tp.Optional[tp.Tuple[int, int]],
                           problems: tp.List[str]) -> None:
    """
    Description:
        A catalogue mode's identification, against the rest of the configuration: the DINOv2 path resolved
        (the model itself is checked when it loads, like the others); an Unspecified ratio above 1, since at
        1 or below the part itself would be Unspecified; and each reference image the camera window's size,
        since the part's box in it is in that window's pixels and the reference is cropped from it as a
        frame is.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration being filled.
        (2) resolution [Vector<int> 1x2 or None]: The camera's window size (None when invalid).
        (3) problems [Vector<string>]: Collects what is wrong.
    """

    identification = Configuration_Str.Identification
    if identification.Model_Path:
        identification.Model_Path = __Resolve_Model_Path(identification.Model_Path)
    if identification.Unspecified_Area_Ratio <= 1.0:
        problems.append('Catalogue.Unspecified_Area_Ratio must be above 1, or the part itself would be Unspecified '
                        '(found %r)' % identification.Unspecified_Area_Ratio)
    if Configuration_Str.Catalogue is None or resolution is None:
        return
    for reference in Configuration_Str.Catalogue.References:
        size = __Image_Size(reference.Image_Path)
        if size != tuple(resolution):
            problems.append('%s: reference_image/%s.png is %s, but Camera.Resolution is %d × %d: a reference must be '
                            'a frame of this camera window (a capture set\'s _raw.png)'
                            % (os.path.basename(Configuration_Str.Catalogue.Path), reference.Side,
                               '%d × %d' % size if size else 'not a readable image', resolution[0], resolution[1]))


def __Catalogue_Scale(Configuration_Str: Configuration_Str, board_height: tp.Optional[float],
                      problems: tp.List[str]) -> tp.Optional[Scale_Str]:
    """
    Description:
        A catalogue mode's scale: the calibration's, moved to the catalogue part's top face
        (Scale_At_Height). A catalogue mode checks dimensions in millimetres, so a calibration without
        a factor, or without the board height that factor holds at, fails the load here — it would
        otherwise check every part against a scale the part does not lie in.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration, its calibration and item read.
        (2) board_height [float or None]: The calibration's board height, or None when it records none.
        (3) problems [Vector<string>]: Collects what is wrong.

    Returns:
        (1) parameter [Scale_Str(object) or None]: The corrected scale, or None when it cannot be made.
    """

    calibration = os.path.basename(Configuration_Str.Calibration_Path)
    if Configuration_Str.Scale is None:
        problems.append('a catalogue mode checks dimensions in mm, so it needs %s with a '
                        'Calibration.Conversion_Factor. Run Example/Camera/calibrate.py' % calibration)
        return None
    if board_height is None:
        problems.append('a catalogue mode corrects the scale to the part\'s top face, so it needs the height '
                        'the calibration\'s factor holds at, %s, which %s does not record. Recalibrate with '
                        'Example/Camera/calibrate.py, which records it' % ('.'.join(CONST_BOARD_HEIGHT_PATH), calibration))
        return None
    return Scale_At_Height(Configuration_Str.Scale, Configuration_Str.Camera.Calibration.K, board_height,
                           Configuration_Str.Catalogue.Thickness_Mm)


def Load_Configuration(config_path: str) -> Configuration_Str:
    """
    Description:
        Read a mode file, the station file it names and the calibration the station names, validate them
        as a whole, and return the configuration. Every problem is collected before anything is returned,
        so the caller gets either a configuration that is valid throughout or an error listing everything
        wrong — never a configuration that is right up to the first bad field.

    Args:
        (1) config_path [string]: The mode file, 'Config_<Hardware>_Mode_<Mode>.yaml'.

    Returns:
        (1) parameter [Configuration_Str(object)]: The loaded configuration. Its Notes hold the
                                                   defaulted fields and unknown keys, to be logged.

    Raises:
        Configuration_Error_Cls: The file, its station or its calibration is missing, unreadable or
                                 invalid, or two of them disagree; the message names each problem.
    """

    return __Load_Mode(config_path, None)


def Load_Configuration_For_Reference(config_path: str) -> tp.Tuple[Configuration_Str, tp.List[str]]:
    """
    Description:
        Load_Configuration for Example/Camera/make_reference.py, the one caller that must load a mode whose
        background reference is out of date: a new calibration or sensor window puts the reference in force
        out of date, and the load then fails until a new one is shot. Everything is validated as
        Load_Configuration validates it, except the reference: its problems (missing, another size, a sidecar
        that does not match the window, lens model or lighting) are returned instead of failing the load.

    Args:
        (1) config_path [string]: The mode file, 'Config_<Hardware>_Mode_<Mode>.yaml'.

    Returns:
        (1) parameter [Configuration_Str(object)]: The loaded configuration.
        (2) parameter [Vector<string>]: What is wrong with the reference in force; empty when it matches the
                                        camera, and the configuration is then the one Load_Configuration returns.

    Raises:
        Configuration_Error_Cls: Anything other than the reference is wrong; the message names each problem.
    """

    reference_problems = []
    return __Load_Mode(config_path, reference_problems), reference_problems


def __Load_Mode(config_path: str, reference_problems: tp.Optional[tp.List[str]]) -> Configuration_Str:
    """
    Description:
        Load_Configuration's work: read and validate the mode file, its station and its calibration.

    Args:
        (1) config_path [string]: The mode file.
        (2) reference_problems [Vector<string> or None]: Where the reference's problems go; None puts them
                                                         with every other problem, which fails the load.

    Returns:
        (1) parameter [Configuration_Str(object)]: The loaded configuration.

    Raises:
        Configuration_Error_Cls: The configuration cannot be used; the message names each problem.
    """

    config_path = os.path.abspath(config_path)
    name = os.path.basename(config_path)
    problems, notes = [], []
    Configuration_Str_i = Configuration_Str(Path=config_path, Name=name)
    data = __Read_Yaml(config_path, 'configuration file', problems)
    if data is None:
        raise Configuration_Error_Cls("Configuration '%s' cannot be used: %s." % (name, '; '.join(problems)))
    reference_problems = problems if reference_problems is None else reference_problems

    # 1\ The file name and the Hardware field must agree.
    hardware, mode = __Read_Hardware(data, config_path, problems)
    Configuration_Str_i.Hardware, Configuration_Str_i.Mode = hardware, mode

    # 2\ Every setting in the field table.
    __Read_Fields(data, Configuration_Str_i, CONST_FIELDS, problems, notes)

    # 3\ The station the mode names: the camera, the reference and the calibration, shared by every mode
    #    that names it. A mode file never overrides it, so what it may hold of the station's is refused,
    #    naming the file.
    station, resolution, offset = None, None, None
    if hardware:
        Configuration_Str_i.Station_Path = __Read_Reference(data, CONST_STATION_REFERENCE, config_path, hardware,
                                                            problems) or ''
        station_name = os.path.basename(Configuration_Str_i.Station_Path) or 'the station file'
        for path in CONST_STATION_ONLY_PATHS:
            if __Lookup(data, path)[0]:
                problems.append('%s is the station\'s, not the mode\'s: remove it from this file and set it in %s '
                                '(a mode file never overrides the station)' % ('.'.join(path), station_name))
        if Configuration_Str_i.Station_Path:
            station, resolution, offset = __Read_Station(Configuration_Str_i, CONST_STATION_FIELDS, hardware,
                                                         problems, notes)

    # 4\ The cross-field rules, and the paths resolved against the repository.
    reference = __Resolve_And_Cross_Check(Configuration_Str_i, problems, reference_problems)
    if reference and resolution:
        __Check_Reference_Size(reference, resolution, reference_problems)

    # 5\ The calibration the station names, checked against the station: its hardware and sensor window.
    board_height = None
    if station is not None:
        station_hardware = station.get('Hardware') if isinstance(station.get('Hardware'), str) else hardware
        Configuration_Str_i.Calibration_Path = __Read_Reference(station, CONST_CALIBRATION_REFERENCE,
                                                                Configuration_Str_i.Station_Path, station_hardware,
                                                                problems) or ''
        if Configuration_Str_i.Calibration_Path:
            Configuration_Str_i.Camera.Calibration, Configuration_Str_i.Scale, board_height = __Read_Calibration(
                Configuration_Str_i.Calibration_Path, Configuration_Str_i.Station_Path, station_hardware,
                resolution, offset, problems, notes)
    calibrated = Configuration_Str_i.Camera.Calibration is not None

    # 5b\ A catalogue mode: its item, and the scale corrected to the item's top face — after the
    #     calibration, whose factor and board height the correction starts from.
    present, block = __Lookup(data, CONST_CATALOGUE_ITEM_PATH[:1])
    if present:
        Configuration_Str_i.Catalogue = __Read_Catalogue_Block(block, problems, notes)
        __Read_Fields(data, Configuration_Str_i, CONST_CATALOGUE_BLOCK_FIELDS, problems, notes)
        __Check_Identification(Configuration_Str_i, resolution, problems)
        if Configuration_Str_i.Catalogue is not None and calibrated:
            Configuration_Str_i.Scale = __Catalogue_Scale(Configuration_Str_i, board_height, problems)

    # 6\ The reference's provenance, against the window, the calibration and the lighting — after
    #    the calibration is read, since the reference must have been undistorted with it.
    if reference and resolution and offset and calibrated and os.path.isfile(reference):
        __Check_Reference_Sidecar(reference, Configuration_Str_i.Camera, reference_problems)

    # 7\ Keys nothing reads — usually a misspelt optional field.
    for key in __Unknown_Keys(data, __Mode_File_Known_Paths()):
        if tuple(key.split('.')) == CONST_REMOVED_CLASSIFICATION_PATH:
            notes.append(('WARNING', '%s is no longer read and is ignored: a configuration classifies when it has a '
                                     'Catalogue block.' % key))
        else:
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


def __Read_Fields(data: tp.Dict[str, tp.Any], structure: tp.Any, fields: tp.Tuple[tp.Tuple, ...],
                  problems: tp.List[str], notes: tp.List[tp.Tuple[str, str]], prefix: str = '') -> None:
    """
    Description:
        Every setting in a field table (CONST_FIELDS, CONST_CATALOGUE_FIELDS) into its structure: a
        required one must be present, an optional one falls back to its default and says so, and a
        present value must be valid either way.

    Args:
        (1) data [Dict]: The parsed file.
        (2) structure [Any]: The structure being filled (Configuration_Str, Catalogue_Item_Str).
        (3) fields [Vector<Tuple>]: The field table.
        (4) problems [Vector<string>]: Collects what is wrong.
        (5) notes [Vector<Tuple<string> 1x2>]: Collects the (level, message) notes to log.
        (6) prefix [string]: Put before each message: the file's name and ': ' when it is not the
                             mode file.
    """

    for path, attribute, kind, required in fields:
        dotted = prefix + '.'.join(path)
        target = structure
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


def __Resolve_And_Cross_Check(Configuration_Str: Configuration_Str, problems: tp.List[str],
                              reference_problems: tp.List[str]) -> str:
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
        (3) reference_problems [Vector<string>]: Collects what is wrong with the reference (problems itself,
                                                 except for Load_Configuration_For_Reference).

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
    if Configuration_Str.Station_Events_Directory:
        Configuration_Str.Station_Events_Directory = __Resolve_Model_Path(Configuration_Str.Station_Events_Directory)
        __Check_Writable_Directory(Configuration_Str.Station_Events_Directory, 'General.Station_Events.Directory',
                                   problems)
    reference = Configuration_Str.Segmentation.Background_Reference
    if reference:
        reference = Configuration_Str.Segmentation.Background_Reference = __Resolve_Model_Path(reference)
        if not os.path.isfile(reference):
            reference_problems.append('Background.Reference: the file "%s" does not exist' % reference)
            reference = ''
    return reference


def __Check_Writable_Directory(directory: str, dotted: str, problems: tp.List[str]) -> None:
    """
    Description:
        A directory the application must write to must exist and take a file — checked by creating and
        removing one, since permission bits mislead on network shares and Windows ACLs. It is never
        created here: a missing directory is a setup problem to surface before a shift, not after it.

    Args:
        (1) directory [string]: The resolved directory.
        (2) dotted [string]: Its key path, for the message.
        (3) problems [Vector<string>]: Collects what is wrong.
    """

    if not os.path.isdir(directory):
        problems.append('%s: the directory "%s" does not exist' % (dotted, directory))
        return
    try:
        handle, probe = tempfile.mkstemp(prefix='.anyscan_write_check_', dir=directory)
        os.close(handle)
        os.remove(probe)
    except OSError as error:
        problems.append('%s: the directory "%s" is not writable (%s)' % (dotted, directory, error.strerror or error))


def __Read_Station(Configuration_Str: Configuration_Str, fields: tp.Tuple[tp.Tuple, ...], hardware: str,
                   problems: tp.List[str], notes: tp.List[tp.Tuple[str, str]]) -> tp.Tuple[
                       tp.Optional[tp.Dict[str, tp.Any]], tp.Optional[tp.Tuple[int, int]], tp.Optional[tp.Tuple[int, int]]]:
    """
    Description:
        Read and validate the station file a mode names into the configuration: its Hardware must be the
        mode's; the camera as a person names it and, for the application, the reference (the field
        table); the acquisition settings Basler_Cls cannot start without; and the sensor window the
        camera is set to on connect, against which the reference and the calibration are checked. Its
        messages name the file.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The configuration being filled (Path and
                                                           Station_Path set).
        (2) fields [Vector<Tuple>]: The station settings read: CONST_STATION_FIELDS, or
                                    CONST_STATION_CAMERA_FIELDS for the camera alone (Load_Station_Camera).
        (3) hardware [string]: The hardware id the mode file names.
        (4) problems [Vector<string>]: Collects what is wrong.
        (5) notes [Vector<Tuple<string> 1x2>]: Collects the (level, message) notes to log.

    Returns:
        (1) parameter [Dict or None]: The station file's document (its Calibration is read from it), or None
                                      when it could not be read.
        (2) parameter [Vector<int> 1x2 or None]: The window's size, or None when invalid.
        (3) parameter [Vector<int> 1x2 or None]: The window's offset, or None when invalid.
    """

    data = __Read_Yaml(Configuration_Str.Station_Path, 'station file', problems)
    if data is None:
        return None, None, None
    station_name = os.path.basename(Configuration_Str.Station_Path)
    prefix = '%s: ' % station_name
    if data.get('Hardware') != hardware:
        problems.append('%s (Hardware %r) names the station %s, whose Hardware is %r: a mode runs only on a station '
                        'of its own hardware' % (os.path.basename(Configuration_Str.Path), hardware, station_name,
                                                 data.get('Hardware')))
    __Read_Fields(data, Configuration_Str, fields, problems, notes, prefix)
    Configuration_Str.Camera.Custom_Cfg = __Read_Custom_Cfg(data, problems, prefix)
    resolution, offset = __Read_Camera_Window(data, problems, prefix)
    Configuration_Str.Camera.Resolution = resolution or (0, 0)
    Configuration_Str.Camera.Offset = offset or (0, 0)
    for key in __Unknown_Keys(data, __Station_File_Known_Paths()):
        notes.append(('WARNING', '%sunrecognised key %s is ignored (misspelt?).' % (prefix, key)))
    return data, resolution, offset


def Load_Station_Camera(config_path: str) -> Configuration_Str:
    """
    Description:
        The camera of the station a mode file names, and nothing else: for Example/Camera/calibrate.py,
        which must run on a camera that has no calibration yet, so it cannot go through
        Load_Configuration, which requires one. The mode file's Hardware and Station are read, and the
        station's camera (its names, acquisition settings and sensor window) is validated as
        Load_Configuration validates it; the rest of the mode file, the background reference and the
        calibration are not read. The calibration the station names, when it names one that exists, is
        reported in Calibration_Path, unvalidated: the tool copies its header and says it stays in force.

    Args:
        (1) config_path [string]: The mode file, 'Config_<Hardware>_Mode_<Mode>.yaml'.

    Returns:
        (1) parameter [Configuration_Str(object)]: Path, Name, Hardware, Mode, Station_Path, Camera (without a
                                                   calibration), Calibration_Path ('' when the station names
                                                   none that exists) and Notes are set; nothing else is.

    Raises:
        Configuration_Error_Cls: The mode file, its Station or the station's camera is missing or invalid;
                                 the message names each problem.
    """

    config_path = os.path.abspath(config_path)
    name = os.path.basename(config_path)
    problems, notes = [], []
    Configuration_Str_i = Configuration_Str(Path=config_path, Name=name)
    data = __Read_Yaml(config_path, 'configuration file', problems)
    station = None
    if data is not None:
        hardware, mode = __Read_Hardware(data, config_path, problems)
        Configuration_Str_i.Hardware, Configuration_Str_i.Mode = hardware, mode
        if hardware:
            Configuration_Str_i.Station_Path = __Read_Reference(data, CONST_STATION_REFERENCE, config_path, hardware,
                                                                problems) or ''
        if Configuration_Str_i.Station_Path:
            station, _resolution, _offset = __Read_Station(Configuration_Str_i, CONST_STATION_CAMERA_FIELDS, hardware,
                                                           problems, notes)
    if problems:
        raise Configuration_Error_Cls("The camera of configuration '%s' cannot be read: %s." % (name, '; '.join(problems)))
    Configuration_Str_i.Calibration_Path = __Read_Reference(station, CONST_CALIBRATION_REFERENCE,
                                                            Configuration_Str_i.Station_Path,
                                                            Configuration_Str_i.Hardware, []) or ''
    Configuration_Str_i.Notes = [(level, "Configuration '%s': %s" % (name, message)) for level, message in notes]
    return Configuration_Str_i


def __Read_Custom_Cfg(data: tp.Dict[str, tp.Any], problems: tp.List[str], prefix: str) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Camera.Custom_Cfg, the acquisition settings Basler_Cls cannot start without: each of the
        four is required and typed (CONST_CUSTOM_CFG_KINDS), and Balance_Ratios is exactly the
        CONST_BALANCE_CHANNELS, each above 0. Gamma and Light_Source_Preset are optional pins
        (CONST_PINNED_CUSTOM_CFG_KINDS). Only valid values are kept, so nothing the camera does
        not read is handed to it.

    Args:
        (1) data [Dict]: The parsed station file.
        (2) problems [Vector<string>]: Collects what is wrong.
        (3) prefix [string]: Put before each message: the station file's name and ': '.

    Returns:
        (1) parameter [Dict]: The validated settings.
    """

    custom = __Lookup(data, ('Camera', 'Custom_Cfg'))[1]
    if not isinstance(custom, dict):
        problems.append('%sCamera.Custom_Cfg is required but missing' % prefix)
        custom = {}
    missing = [key for key in CONST_REQUIRED_CUSTOM_CFG_KEYS if key not in custom]
    if missing and custom:
        problems.append('%sCamera.Custom_Cfg is missing the required %s' % (prefix, ', '.join(missing)))
    settings = {}
    for key in (key for key in CONST_REQUIRED_CUSTOM_CFG_KEYS if key in custom):
        dotted = '%sCamera.Custom_Cfg.%s' % (prefix, key)
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
    for key, kind in CONST_PINNED_CUSTOM_CFG_KINDS.items():
        if key in custom:
            valid, value, expected = __Check(kind, custom[key])
            if valid:
                settings[key] = value
            else:
                problems.append('%sCamera.Custom_Cfg.%s must be %s (found %r)' % (prefix, key, expected, custom[key]))
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


def __Read_Camera_Window(data: tp.Dict[str, tp.Any], problems: tp.List[str],
                         prefix: str) -> tp.Tuple[tp.Optional[tp.Tuple[int, int]], tp.Optional[tp.Tuple[int, int]]]:
    """
    Description:
        The sensor window the camera is set to on connect: Camera.Resolution and Camera.Offset.

    Args:
        (1) data [Dict]: The parsed station file.
        (2) problems [Vector<string>]: Collects what is wrong.
        (3) prefix [string]: Put before each message: the station file's name and ': '.

    Returns:
        (1) parameter [Vector<int> 1x2 or None]: The resolution, or None when invalid.
        (2) parameter [Vector<int> 1x2 or None]: The offset, or None when invalid.
    """

    window = {}
    for path, minimum in CONST_WINDOW_FIELDS:
        window[path[-1]] = __Read_Window(__Lookup(data, path)[1], prefix + '.'.join(path), minimum, problems)
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
        problems.append('Background.Reference: the file "%s" could not be read as an image' % reference)
    elif size != resolution:
        problems.append("Background.Reference is %d × %d but Camera.Resolution is %d × %d: the station's "
                        'reference does not match its camera resolution. Re-shoot the empty-surface reference at '
                        '%d × %d, or correct Camera.Resolution' % (size + resolution + resolution))


def Discover_Configurations(directory: str) -> tp.List[tp.Tuple[str, tp.Optional[Configuration_Str], str]]:
    """
    Description:
        Every mode file ('Config_*_Mode_*.yaml') in a directory, each loaded through
        Load_Configuration — the one reader — so the Configuration dialog lists them by their display
        name. A file that cannot be loaded is still listed, with the reason, so it is visible and
        not silently missing.

    Args:
        (1) directory [string]: The directory to look in (Mode_Directory(), Configuration/Mode/).

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
        What a configuration reads beside itself: the station file, the calibration, the background
        reference and, in a catalogue mode, the catalogue item, logged together on load so a run can be
        traced to each.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The loaded configuration.

    Returns:
        (1) parameter [string]: The log line.
    """

    calibration = Display_Path(Configuration_Str.Calibration_Path)
    sources = 'station %s, calibration %s and background reference %s' % (
        Display_Path(Configuration_Str.Station_Path), calibration,
        Display_Path(Configuration_Str.Segmentation.Background_Reference))
    if Configuration_Str.Catalogue is not None:
        sources = 'station %s, calibration %s, background reference %s and catalogue item %s' % (
            Display_Path(Configuration_Str.Station_Path), calibration,
            Display_Path(Configuration_Str.Segmentation.Background_Reference),
            Display_Path(Configuration_Str.Catalogue.Path))
    return "Configuration '%s' reads %s." % (Configuration_Str.Name, sources)


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

    if Configuration_Str.Classifies:
        state = ('enabled — catalogue item %s (%s): each object is OK, NOK, Unspecified or Warning'
                 % (Configuration_Str.Catalogue.Display_Name, Configuration_Str.Catalogue.Name))
    else:
        state = 'disabled — the UI shows detected objects only, no verdicts'
    return ("Loaded configuration '%s' ('%s': hardware %s, mode %s, model set %s). Classification is %s."
            % (Configuration_Str.Name, Configuration_Str.Identity.Display_Name, Configuration_Str.Hardware,
               Configuration_Str.Mode, Configuration_Str.Identity.Model_Set, state))


def __Check_Writable(Camera_Calibration_Parameters_Str: Camera_Calibration_Parameters_Str,
                     output_path: str) -> None:
    """
    Description:
        Step 1 of Write_Calibration: refuse a calibration that does not record its window, and any
        file that exists — a calibration is never written over, so an older one stays available to
        switch back to, and content someone added to one is never regenerated away.

    Args:
        (1) Camera_Calibration_Parameters_Str [Camera_Calibration_Parameters_Str(object)]: The solved
            calibration.
        (2) output_path [string]: The file to be written.

    Raises:
        AssertionError: The write is refused; the message says why.
    """

    assert (Camera_Calibration_Parameters_Str.Resolution is not None
            and Camera_Calibration_Parameters_Str.Offset is not None), (
        'the calibration does not record the sensor window (Resolution and Offset) it was solved at')
    assert not os.path.lexists(output_path), (
        '%s already exists, and a calibration is never written over: the older one stays available to switch '
        'back to' % Display_Path(output_path))


def __Header_Lines(header_source: tp.Optional[str], hardware: str) -> tp.List[str]:
    """
    Description:
        Step 2 of Write_Calibration: the header comment, the leading comment lines of the calibration
        in force, or a minimal one when there is none.

    Args:
        (1) header_source [string or None]: The calibration file whose header is copied.
        (2) hardware [string]: The hardware id, for the minimal header.

    Returns:
        (1) parameter [Vector<string>]: The header lines.
    """

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
    return header


def __Calibration_Body(Camera_Calibration_Parameters_Str: Camera_Calibration_Parameters_Str, hardware: str,
                       record: tp.Dict[str, tp.Any]) -> str:
    """
    Description:
        Step 3 of Write_Calibration: 'Hardware' and the 'Calibration' block as YAML text, the numbers
        formatted with repr() to keep their full, round-trippable precision.

    Args:
        (1) Camera_Calibration_Parameters_Str [Camera_Calibration_Parameters_Str(object)]: The solved
            calibration.
        (2) hardware [string]: The hardware id.
        (3) record [Dict]: How the calibration was solved (see Write_Calibration).

    Returns:
        (1) parameter [string]: The body text.
    """

    matrix_rows = '\n'.join('    - [' + ', '.join(repr(float(value)) for value in row) + ']'
                            for row in Camera_Calibration_Parameters_Str.K)
    coefficients = '\n'.join(f'    {key}: {repr(float(value))}'
                             for key, value in Camera_Calibration_Parameters_Str.Coefficients.items())
    factors = '\n'.join(f'    {key}: {repr(float(value))}'
                        for key, value in Camera_Calibration_Parameters_Str.Conversion_Factor.items())
    views = record['views']
    return (CONST_CALIBRATION_HARDWARE_COMMENT + '\n'
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


def __Write_Whole(path: str, text: str) -> None:
    """
    Description:
        Step 4 of Write_Calibration: write the text beside the target, then move it into place whole,
        so a write that fails part-way (a full disk) leaves no torn calibration for a station to name.

    Args:
        (1) path [string]: The file written.
        (2) text [string]: Its content.

    Raises:
        OSError: The write failed; nothing is left at the target or beside it.
    """

    temporary = path + '.writing'
    try:
        with open(temporary, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


def Write_Calibration(Camera_Calibration_Parameters_Str: Camera_Calibration_Parameters_Str, *,
                      hardware: str, header_source: tp.Optional[str], output_path: str,
                      record: tp.Dict[str, tp.Any]) -> bool:
    """
    Description:
        Write a NEW calibration file from a freshly solved result: the header comment, 'Hardware',
        and the 'Calibration' block (how it was solved, K, the coefficients and the conversion
        factor).

        Note:
            The writer destroys nothing: when output_path exists, the write is REFUSED. A calibration
            is never written over, so every older one stays available to switch back to, by the
            station file's Calibration line — which the writer never edits. The header comment of the
            calibration in force is copied. The file is written whole beside the target and then moved
            into place, so a write that fails part-way leaves no torn file.

    Args:
        (1) Camera_Calibration_Parameters_Str [Camera_Calibration_Parameters_Str(object)]: The
            solved calibration: K, the distortion coefficients, the mm/px factors, and the sensor
            window it was solved at (Resolution and Offset — REQUIRED: a calibration that does not
            say which pixels it is in is refused).
        (2) hardware [string]: REQUIRED, keyword-only: the hardware id the calibration belongs to.
        (3) header_source [string or None]: REQUIRED, keyword-only: a calibration file whose
            header comment is copied (the one in force); None writes a minimal header.
        (4) output_path [string]: REQUIRED, keyword-only: the file written; it must not exist.
        (5) record [Dict]: REQUIRED, keyword-only: how the calibration was solved — 'date',
            'images', 'views' {'total', 'flat', 'tilted'}, 'rms_px', 'square_mm' and
            'board_height_mm' (the reference plane: the flat boards' surface above the table).

    Returns:
        (1) parameter [bool]: True if the file was written, False if refused or failed.
    """

    try:
        __Check_Writable(Camera_Calibration_Parameters_Str, output_path)
        header = __Header_Lines(header_source, hardware)
        body = __Calibration_Body(Camera_Calibration_Parameters_Str, hardware, record)
        __Write_Whole(output_path, '\n'.join(header).rstrip('\n') + '\n\n' + body)
        return True

    except (AssertionError, OSError, KeyError, yaml.YAMLError) as error:
        print(f'[ERROR] Information: {error}')
        print(f'[ERROR] The calibration was NOT written to "{output_path}".')
        return False
