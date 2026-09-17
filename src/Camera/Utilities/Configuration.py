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
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — camera configuration structures
#   ../Parameters/Camera
from Parameters.Camera import Camera_Configuration_Str, Camera_Calibration_Parameters_Str

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

def Write_Calibration(Camera_Calibration_Parameters_Str: Camera_Calibration_Parameters_Str,
                      file_path: str) -> bool:
    """
    Description:
        Overwrite the 'Calibration' block of a camera *.yaml configuration file with a
        freshly solved result, so the calibration output becomes the project's single
        source of truth. Everything above the 'Calibration:' key (the header, the camera
        identity, its resolution and custom configuration) is preserved; only the
        calibration values, with their inline comments, are regenerated.

        Note:
            The 'Calibration:' block is the last block of the file, so preserving
            everything up to and including its key and regenerating the rest keeps the
            whole human-authored header intact.

    Args:
        (1) Camera_Calibration_Parameters_Str [Camera_Calibration_Parameters_Str(object)]: The
            solved calibration result, holding the intrinsic matrix, distortion coefficients
            and pixel-to-millimeter factors.
        (2) file_path [string]: The absolute path to the *.yaml configuration file.

    Returns:
        (1) parameter [bool]: True if the file was rewritten successfully, False otherwise.
    """

    # The anchor key: everything up to and including it is preserved, the calibration
    # values below it are regenerated from the freshly solved parameters.
    anchor = '  Calibration:'

    try:
        assert os.path.isfile(file_path)

        # 1\ Read the current source and locate the anchor.
        with open(file_path, 'r', encoding='utf-8') as f:
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

        # 3\ Compose the regenerated calibration block, keeping its inline comments.
        block = ('    # Camera calibration (intrinsic) matrix K, 3 x 3, row-major.\n'
                 f'    K:\n{matrix_rows}\n'
                 '    # Distortion coefficients: [k1, k2, p1, p2, k3].\n'
                 f'    Coefficients:\n{coefficients}\n'
                 '    # Pixel-to-millimeter conversion factors for the x and y axes [mm/px].\n'
                 f'    Conversion_Factor:\n{factors}')

        # 4\ Write the preserved head and the regenerated block back to the file.
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(head) + '\n' + block + '\n')

        return True

    except AssertionError as error:
        print(f'[ERROR] Information: {error}')
        print(f'[ERROR] The calibration block could not be written to "{file_path}".')
        return False
