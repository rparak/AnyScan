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
# File Name: ../Parameters/Camera.py
## =========================================================================== ##

# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Typing (Support for type hints)
import typing as tp

@dataclass
class Camera_Calibration_Parameters_Str:
    """
    Description:
        The structure of the main parameters of the camera calibration.

        Note:
            Populated from a *.yaml configuration file; see
            ../Camera/Utilities/Configuration.py (Read_Configuration).
    """

    # Camera calibration (intrinsic) matrix.
    K: np.ndarray = field(default_factory=lambda: np.zeros((3, 3), dtype=np.float64))
    # Distortion coefficients: [k1, k2, p1, p2, k3].
    Coefficients: tp.Dict[str, float] = field(default_factory=dict)
    # Pixel to millimeter conversion factors for x and y axes.
    Conversion_Factor: tp.Dict[str, float] = field(default_factory=dict)

@dataclass
class Camera_Configuration_Str:
    """
    Description:
        The structure of the main parameters of the camera (sensor) object,
        together with its calibration.

        Note:
            The parameter structure mainly focuses on the 2D representation of the
            image. It is populated from a *.yaml configuration file; see
            ../Camera/Utilities/Configuration.py (Read_Configuration).
    """

    # Name of the camera (sensor + lens identifier).
    Name: str = 'Camera'
    # Camera resolution in pixels (x, y).
    Resolution: tp.Dict[str, int] = field(default_factory=dict)
    # Custom camera configuration.
    #   Note:
    #       Optional structure for vendor/API specific settings (e.g., exposure, gain, white balance, pixel format).
    Custom_Cfg: tp.Dict[str, tp.Any] = field(default_factory=dict)
    # Calibration of the camera above.
    Calibration: Camera_Calibration_Parameters_Str = field(default_factory=Camera_Calibration_Parameters_Str)

@dataclass
class Board_Detection_Str:
    """
    Description:
        The chessboard found in one image: its inner-corner grid (which may be only the visible
        part of a board that overhangs the frame), the corners in pixels, and — when nothing
        usable was found — why.
    """

    # Whether a usable grid was found.
    #   Unit [bool]
    Found: bool = False
    # The detected inner-corner grid as (columns, rows) — the visible part of the board.
    #   Unit [Vector<int> 1x2]
    Grid: tp.Tuple[int, int] = (0, 0)
    # The corners in pixels, row-major over Grid (rows x columns, then x/y).
    #   Unit [Matrix<float> Nx2]
    Corners: np.ndarray = field(default_factory=lambda: np.zeros((0, 2), dtype=np.float64),
                                repr=False)
    # Why nothing was found (empty when Found).
    #   Unit [string]
    Reason: str = ''
