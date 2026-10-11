## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../test/Vision/test_identifier.py
## =========================================================================== ##

# System (Default)
import os
import sys
import subprocess
# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the identifier under test, and the catalogue it compares against
#   ../Vision/Identifier
import Vision.Identifier as Identifier
from Vision.Identifier import Dino_Identifier_Cls, Identifier_Error_Cls
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import Reference_Crop, Rotations
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_CONFIG_DIR

"""
Description:
    The catalogue mode's identifier: its bare import pulls no heavy runtime and no Qt; missing weights
    stop it with a sentence that says what to do; and, with the weights, it turns images into unit
    vectors, the same image always into the same one, and tells an item's two sides apart.
"""


def _Catalogue_Configuration(mode: str = 'Mounting_Plate') -> tp.Any:
    """A shipped catalogue mode, loaded."""
    return Load_Configuration(os.path.join(CONST_CONFIG_DIR, 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_%s.yaml'
                                           % mode))


def test_the_bare_import_pulls_no_heavy_runtime_and_no_qt() -> None:
    """
    Description:
        Importing the module (as Vision.Core does at startup) loads neither torch nor transformers nor
        Qt: the runtime arrives when the model loads.
    """

    code = ('import sys; sys.path.insert(0, %r); import Vision.Identifier; '
            "print(sorted(m for m in ('torch', 'transformers', 'PyQt5') if m in sys.modules))"
            % os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(Identifier.__file__)))), 'src'))
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == '[]'


def test_missing_weights_say_what_to_do(tmp_path: tp.Any) -> None:
    """
    Description:
        An identifier pointed at a directory without the weights fails with a sentence naming the path
        and the fix (install.sh, or Catalogue.Identifier), not a library traceback.
    """

    identifier = Dino_Identifier_Cls(str(tmp_path / 'dinov2-base'), 'cpu')
    with pytest.raises(Identifier_Error_Cls, match=r'could not be found\. Run \./install\.sh.*Catalogue\.Identifier'):
        identifier.Load()
    assert not identifier.Loaded and identifier.Model_Key == (str(tmp_path / 'dinov2-base'), 'cpu')


@pytest.mark.slow
def test_the_references_embed_to_unit_vectors_that_tell_the_sides_apart(require_weights) -> None:
    """
    Description:
        With the pinned weights, on the CPU: each reference crop is a unit vector; embedding the same crops
        again gives the same vectors; a crop matches itself turned upright better than its other side; and
        the front and back of each item are told apart (the measured side margin on the test set is at
        least 0.08, docs/design-decisions.md). Slow because it runs DINOv2.
    """

    for mode in ('Mounting_Plate', 'Labyrinth'):
        config = _Catalogue_Configuration(mode)
        require_weights([config.Identification.Model_Path])
        identifier = Dino_Identifier_Cls(config.Identification.Model_Path, 'cpu')
        crops = [Reference_Crop(cv2.imread(r.Image_Path), r.Box) for r in config.Catalogue.References]
        rows = identifier.Embed(crops, cv2, np)
        assert rows.shape[0] == 2 and np.allclose(np.linalg.norm(rows, axis=1), 1.0, atol=1e-5)
        assert np.allclose(identifier.Embed(crops, cv2, np), rows, atol=1e-5)
        turned = identifier.Embed(Rotations(crops[0], cv2), cv2, np)
        assert (turned @ rows[0]).max() > 0.99 and float(rows[0] @ rows[1]) < 0.6
        identifier.Release()
        assert not identifier.Loaded
