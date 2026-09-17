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
# File Name: ../test/Camera/Utilities/test_configuration.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the camera configuration reader
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Configuration, CONST_REQUIRED_CUSTOM_CFG_KEYS

"""
Description:
    Tests for the camera configuration reader. Each test writes a *.yaml document to a
    pytest tmp_path so the file system is isolated, then reads it back. The focus is the
    required-key validation of the 'Custom_Cfg' block: a configuration missing an
    acquisition setting the Basler camera needs must fail here, at read time, not deep
    inside the Basler SDK.
"""
# A complete, valid 'Custom_Cfg' block for the reference camera, as a *.yaml fragment.
#   Unit [string]
CONST_VALID_CUSTOM_CFG = ('  Custom_Cfg:\n'
                          '    Exposure_Time: 10000\n'
                          '    Gain: 10\n'
                          '    Balance_Ratios:\n'
                          '      Red: 0.95\n'
                          '      Green: 0.9\n'
                          '      Blue: 1.2\n'
                          '    Pixel_Format: BayerRG8\n')
# The nested 'Calibration' block, unchanged across these tests.
#   Unit [string]
CONST_CALIBRATION_BLOCK = ('  Calibration:\n'
                           '    K:\n'
                           '      - [3885.0, 0.0, 160.0]\n'
                           '      - [0.0, 3898.0, 355.0]\n'
                           '      - [0.0, 0.0, 1.0]\n'
                           '    Coefficients:\n'
                           '      k1: -0.18\n'
                           '      k2: 0.54\n'
                           '      p1: 0.003\n'
                           '      p2: 0.018\n'
                           '      k3: -0.87\n'
                           '    Conversion_Factor:\n'
                           '      x: 0.097\n'
                           '      y: 0.097\n')


def _Write_Config(tmp_path: tp.Any, custom_cfg_block: str) -> str:
    """
    Description:
        Write a camera *.yaml document with the given 'Custom_Cfg' block to tmp_path and
        return its path. The camera identity, resolution and calibration are fixed; only
        the acquisition block varies, so a test can drop a required key from it.

    Args:
        (1) tmp_path [pathlib.Path(object)]: The pytest temporary directory.
        (2) custom_cfg_block [string]: The 'Custom_Cfg' *.yaml fragment to embed.

    Returns:
        (1) parameter [string]: The absolute path to the written configuration file.
    """

    document = ('Camera:\n'
                '  Name: Test_Camera\n'
                '  Resolution:\n'
                '    x: 1920\n'
                '    y: 1200\n'
                + custom_cfg_block
                + CONST_CALIBRATION_BLOCK)
    path = os.path.join(str(tmp_path), 'Config_Test.yaml')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(document)
    return path


def test_valid_configuration_is_read(tmp_path: tp.Any) -> None:
    """
    Description:
        A complete configuration is read into a Camera_Configuration_Str, with every
        required acquisition key present and the calibration populated.
    """

    path = _Write_Config(tmp_path, CONST_VALID_CUSTOM_CFG)
    Camera_Cfg_Str = Read_Configuration(path)

    assert Camera_Cfg_Str is not None
    for key in CONST_REQUIRED_CUSTOM_CFG_KEYS:
        assert key in Camera_Cfg_Str.Custom_Cfg
    assert Camera_Cfg_Str.Custom_Cfg['Exposure_Time'] == 10000
    assert Camera_Cfg_Str.Custom_Cfg['Pixel_Format'] == 'BayerRG8'
    assert Camera_Cfg_Str.Calibration.K.shape == (3, 3)


@pytest.mark.parametrize('missing_key', list(CONST_REQUIRED_CUSTOM_CFG_KEYS))
def test_missing_required_custom_cfg_key_returns_none(tmp_path: tp.Any, missing_key: str) -> None:
    """
    Description:
        A configuration whose 'Custom_Cfg' block is missing any one required acquisition
        key fails at read time (returns None), rather than passing an incomplete
        configuration on to the Basler SDK.

    Args:
        (1) tmp_path [pathlib.Path(object)]: The pytest temporary directory.
        (2) missing_key [string]: The required key dropped from the block.
    """

    lines = [line for line in CONST_VALID_CUSTOM_CFG.splitlines(keepends=True)
             if f'{missing_key}:' not in line]
    # Balance_Ratios carries nested lines; drop them too so the fragment stays valid.
    if missing_key == 'Balance_Ratios':
        lines = [line for line in lines
                 if not any(colour in line for colour in ('Red:', 'Green:', 'Blue:'))]

    path = _Write_Config(tmp_path, ''.join(lines))
    assert Read_Configuration(path) is None


def test_missing_file_returns_none(tmp_path: tp.Any) -> None:
    """
    Description:
        A path that does not exist is reported (returns None), not raised.
    """

    assert Read_Configuration(os.path.join(str(tmp_path), 'does_not_exist.yaml')) is None
