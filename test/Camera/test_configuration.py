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
# File Name: ../test/Camera/test_configuration.py
## =========================================================================== ##

# System (Default)
import typing as tp
# Custom Lib.: AnyScan — the configuration layer and the single classification default
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Classification_Enabled
#   ../Parameters/General
from Parameters.General import CONST_CLASSIFICATION_ENABLED_DEFAULT

"""
Description:
    Tests for the classification flag read through the ONE configuration layer: parsed from the
    'General.Classification.Enabled' block, and defaulting to CONST_CLASSIFICATION_ENABLED_DEFAULT
    (False) — never crashing — when the block, the file or the value is absent or malformed.
"""


def _Write(path: str, text: str) -> str:
    """Write a YAML file and return its path."""
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return path


def test_reads_true_and_false_from_the_general_block(tmp_path: tp.Any) -> None:
    """
    Description:
        The flag is parsed from 'General.Classification.Enabled' — true reads True, false reads
        False.
    """

    enabled = _Write(str(tmp_path / 'on.yaml'),
                     'General:\n  Classification:\n    Enabled: true\nCamera:\n  Name: c\n')
    disabled = _Write(str(tmp_path / 'off.yaml'),
                      'General:\n  Classification:\n    Enabled: false\nCamera:\n  Name: c\n')
    assert Read_Classification_Enabled(enabled) is True
    assert Read_Classification_Enabled(disabled) is False


def test_missing_section_defaults_to_disabled(tmp_path: tp.Any) -> None:
    """
    Description:
        A configuration missing the 'General' block (or the nested keys) defaults to disabled —
        it does not crash and does not assume classification.
    """

    no_general = _Write(str(tmp_path / 'nogeneral.yaml'), 'Camera:\n  Name: c\n')
    partial = _Write(str(tmp_path / 'partial.yaml'), 'General:\n  Other: 1\nCamera:\n  Name: c\n')
    assert Read_Classification_Enabled(no_general) is CONST_CLASSIFICATION_ENABLED_DEFAULT
    assert Read_Classification_Enabled(partial) is CONST_CLASSIFICATION_ENABLED_DEFAULT
    assert CONST_CLASSIFICATION_ENABLED_DEFAULT is False


def test_missing_or_malformed_file_defaults_without_crashing(tmp_path: tp.Any) -> None:
    """
    Description:
        A missing file, an empty file, or a non-boolean value all fall back to the default rather
        than raising.
    """

    empty = _Write(str(tmp_path / 'empty.yaml'), '')
    non_bool = _Write(str(tmp_path / 'nonbool.yaml'),
                      'General:\n  Classification:\n    Enabled: maybe\n')
    assert Read_Classification_Enabled(str(tmp_path / 'does_not_exist.yaml')) is False
    assert Read_Classification_Enabled(empty) is False
    assert Read_Classification_Enabled(non_bool) is False


def test_the_shipped_configuration_defaults_to_disabled() -> None:
    """
    Description:
        The project's shipped configuration must default to detect-only (classification disabled),
        since nothing classifies today.
    """

    from Camera.Utilities.Configuration import CONST_BASLER_CONFIG_FILE
    assert Read_Classification_Enabled(CONST_BASLER_CONFIG_FILE) is False
