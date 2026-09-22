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
# File Name: ../Camera/Utilities/Configuration.py
## =========================================================================== ##

# System (Default)
import os
# JSON (quoting a path safely in YAML)
import json
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — camera configuration structures
#   ../Parameters/Camera
from Parameters.Camera import Camera_Configuration_Str, Camera_Calibration_Parameters_Str
#   ../Parameters/General — the single default for the classification flag
from Parameters.General import CONST_CLASSIFICATION_ENABLED_DEFAULT
#   ../Parameters/Vision
from Parameters.Vision import Scale_Str

"""
Description:
    Initialization of constants.
"""
# Absolute path to the repository-level Configuration/ directory that stores the
# camera *.yaml configuration files. This file lives in src/Camera/Utilities/, so
# the directory is three levels up.
CONST_CONFIG_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                '..', '..', '..', 'Configuration'))
# The default Basler a2A1920-51gcPRO (Computar M1228-MPW3 lens) configuration file.
CONST_BASLER_CONFIG_FILE = os.path.join(CONST_CONFIG_DIR,
                                        'Config_a2A1920_51gcPRO_Computar_M1228_MPW3.yaml')
# The acquisition settings the Basler camera cannot start without. Read_Configuration
# requires every one of these keys in the 'Custom_Cfg' block, so a *.yaml missing one
# fails at read time rather than deep inside the Basler SDK.
#   Unit [Tuple<string>]
CONST_REQUIRED_CUSTOM_CFG_KEYS = ('Exposure_Time', 'Gain', 'Balance_Ratios', 'Pixel_Format')

def Read_Configuration(file_path: str) -> tp.Optional[Camera_Configuration_Str]:
    """
    Description:
        Read a camera configuration (with calibration) from a *.yaml file and return
        it as a Camera_Configuration_Str. The 'Camera' block maps onto the structure
        one-for-one, and its nested 'Calibration' block onto Calibration.

    Args:
        (1) file_path [string]: The absolute path to the *.yaml configuration file.

    Returns:
        (1) parameter [Camera_Configuration_Str(object)]: The parsed camera
            configuration, or None if the file could not be read.
    """

    try:
        assert os.path.isfile(file_path), f'the configuration file "{file_path}" does not exist'

        # 1\ Load the raw YAML document.
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 2\ Map the 'Camera' block onto the configuration structure.
        camera_block = data['Camera']
        camera_cfg = Camera_Configuration_Str(Name=camera_block.get('Name', 'Camera'))
        camera_cfg.Resolution = dict(camera_block.get('Resolution', {}))
        camera_cfg.Custom_Cfg = dict(camera_block.get('Custom_Cfg', {}))

        # 3\ The acquisition settings Basler_Cls needs must all be present, so a *.yaml
        #    missing one fails here and not deep inside the Basler SDK.
        missing_keys = [key for key in CONST_REQUIRED_CUSTOM_CFG_KEYS
                        if key not in camera_cfg.Custom_Cfg]
        assert not missing_keys, ('the "Custom_Cfg" block is missing the required '
                                  f'key(s): {", ".join(missing_keys)}')

        # 4\ Map the nested 'Calibration' block onto the calibration structure.
        calibration_block = camera_block['Calibration']
        camera_cfg.Calibration.K = np.array(calibration_block['K'], dtype=np.float64)
        camera_cfg.Calibration.Coefficients = dict(calibration_block['Coefficients'])
        camera_cfg.Calibration.Conversion_Factor = dict(calibration_block['Conversion_Factor'])

        return camera_cfg

    except AssertionError as error:
        print(f'[ERROR] Information: {error}')
        print(f'[ERROR] The configuration file "{file_path}" is missing or invalid.')

def Read_Classification_Enabled(file_path: str) -> bool:
    """
    Description:
        Read the 'General.Classification.Enabled' flag from a *.yaml configuration file — does
        this configuration perform OK/NOK classification, or only detect objects? It is read
        through this ONE configuration layer (no module parses the YAML for itself), and it never
        raises: a missing file, a missing 'General' block, or a malformed value all fall back to
        the single default (CONST_CLASSIFICATION_ENABLED_DEFAULT = False), so a configuration that
        does not mention classification simply does not classify.

    Args:
        (1) file_path [string]: The absolute path to the *.yaml configuration file.

    Returns:
        (1) parameter [bool]: True when classification is enabled, else the default (False).
    """

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        value = (data or {}).get('General', {}).get('Classification', {}).get('Enabled')
        return bool(value) if isinstance(value, bool) else CONST_CLASSIFICATION_ENABLED_DEFAULT
    except (OSError, yaml.YAMLError, AttributeError):
        return CONST_CLASSIFICATION_ENABLED_DEFAULT


def Read_Conversion_Factor(file_path: str) -> tp.Optional[Scale_Str]:
    """
    Description:
        Read the image scale from 'Camera.Calibration.Conversion_Factor' — MILLIMETRES PER PIXEL
        along x and y (the calibration computes square_size_mm / corner spacing in px, and the
        file labels it [mm/px]; Calibration.Core.Calibrate takes that spacing from flat boards'
        corners undistorted into the application's pixel space). It is read through this ONE configuration layer, once, and passed
        to whatever measures. It never raises, and it has NO default: a missing file, a missing
        block, or an axis that is not a positive finite number yields None, and the caller measures
        nothing (and warns) rather than computing a size from an invented scale.

    Args:
        (1) file_path [string]: The absolute path to the *.yaml configuration file.

    Returns:
        (1) parameter [Scale_Str(object) or None]: The scale, or None when it is absent or invalid.
    """

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        factor = (data or {}).get('Camera', {}).get('Calibration', {}).get('Conversion_Factor')
        x, y = float(factor['x']), float(factor['y'])
    except (OSError, yaml.YAMLError, AttributeError, KeyError, TypeError, ValueError):
        return None
    if not all(np.isfinite(v) and v > 0.0 for v in (x, y)):
        return None
    return Scale_Str(Mm_Per_Px_X=x, Mm_Per_Px_Y=y)


def Write_Calibration(Camera_Calibration_Parameters_Str: Camera_Calibration_Parameters_Str,
                      source_path: str, *, output_path: str,
                      record: tp.Dict[str, tp.Any]) -> bool:
    """
    Description:
        Write a camera *.yaml configuration whose 'Calibration' block holds a freshly solved
        result: everything above the 'Calibration:' key of the SOURCE file (the header, the camera
        identity, its resolution and custom configuration) is copied, and the calibration values,
        with their inline comments and the record of how they were solved, are regenerated. The
        output may be a new file (the default the calibration harness uses, so the configuration
        in force is untouched until someone adopts the new one) or the source itself (an explicit
        choice).

        Note:
            The 'Calibration:' block is the last block of the file, so preserving
            everything up to and including its key and regenerating the rest keeps the
            whole human-authored header intact.

    Args:
        (1) Camera_Calibration_Parameters_Str [Camera_Calibration_Parameters_Str(object)]: The
            solved calibration result, holding the intrinsic matrix, distortion coefficients
            and pixel-to-millimeter factors.
        (2) source_path [string]: The configuration the header is copied from.
        (3) output_path [string]: REQUIRED, keyword-only: the file written (may equal source_path).
        (4) record [Dict]: REQUIRED, keyword-only: how the calibration was solved — 'date',
            'images', 'views' {'total', 'flat', 'tilted'}, 'rms_px', 'square_mm' and
            'board_height_mm' (the reference plane: the flat boards' surface above the table).

    Returns:
        (1) parameter [bool]: True if the file was written successfully, False otherwise.
    """

    # The anchor key: everything up to and including it is preserved, the calibration
    # values below it are regenerated from the freshly solved parameters.
    anchor = '  Calibration:'

    try:
        assert os.path.isfile(source_path)

        # 1\ Read the source and locate the anchor.
        with open(source_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
        anchor_i = next((i for i, line in enumerate(lines) if line.rstrip() == anchor), None)
        assert anchor_i is not None

        # Keep the header / camera identity / resolution / custom configuration above the block.
        head = lines[:anchor_i + 1]

        # 2\ Format the numeric values with repr() to preserve full, round-trippable precision.
        #   Intrinsic matrix (K): one indented row per line.
        matrix_rows = '\n'.join('      - [' + ', '.join(repr(float(value)) for value in row) + ']'
                                for row in Camera_Calibration_Parameters_Str.K)
        #   Distortion coefficients and pixel-to-millimeter factors: one indented key per line.
        coefficients = '\n'.join(f'      {key}: {repr(float(value))}'
                                 for key, value in Camera_Calibration_Parameters_Str.Coefficients.items())
        factors = '\n'.join(f'      {key}: {repr(float(value))}'
                            for key, value in Camera_Calibration_Parameters_Str.Conversion_Factor.items())
        views = record['views']

        # 3\ Compose the regenerated calibration block, keeping its inline comments.
        block = ('    # How this calibration was solved (Example/Camera/calibrate.py --images).\n'
                 '    Solved:\n'
                 f'      Date: {record["date"]}\n'
                 f'      Images: {json.dumps(record["images"])}\n'
                 '      # Views used: flat boards (lens model + factor) and tilted ones (lens model).\n'
                 f'      Views: {{Total: {int(views["total"])}, Flat: {int(views["flat"])}, '
                 f'Tilted: {int(views["tilted"])}}}\n'
                 f'      Reprojection_RMS_Px: {repr(float(record["rms_px"]))}\n'
                 '      # The board\'s square size [mm], as calipered.\n'
                 f'      Square_Size_Mm: {repr(float(record["square_mm"]))}\n'
                 '      # The reference plane: the flat boards\' surface height above the table [mm].\n'
                 '      # The factor is exact in this plane only.\n'
                 f'      Board_Height_Mm: {repr(float(record["board_height_mm"]))}\n'
                 '    # Camera calibration (intrinsic) matrix K, 3 x 3, row-major.\n'
                 f'    K:\n{matrix_rows}\n'
                 '    # Distortion coefficients: [k1, k2, p1, p2, k3].\n'
                 f'    Coefficients:\n{coefficients}\n'
                 '    # Pixel-to-millimeter conversion factors for the x and y axes [mm/px], in the\n'
                 '    # undistorted (alpha = 1) pixel space measurement happens in.\n'
                 f'    Conversion_Factor:\n{factors}')

        # 4\ Write the preserved head and the regenerated block to the output file.
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(head) + '\n' + block + '\n')

        return True

    except (AssertionError, OSError, KeyError) as error:
        print(f'[ERROR] Information: {error}')
        print(f'[ERROR] The calibration could not be written to "{output_path}".')
        return False
