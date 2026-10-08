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
            Populated from the hardware's calibration file (Calibration_<Hardware>.yaml); see
            ../Configuration/Core.py (Load_Configuration).
    """

    # Camera calibration (intrinsic) matrix.
    K: np.ndarray = field(default_factory=lambda: np.zeros((3, 3), dtype=np.float64))
    # Distortion coefficients: [k1, k2, p1, p2, k3].
    Coefficients: tp.Dict[str, float] = field(default_factory=dict)
    # Pixel to millimeter conversion factors for x and y axes.
    Conversion_Factor: tp.Dict[str, float] = field(default_factory=dict)
    # The sensor window the calibration was solved at: its size (width, height) and its offset
    # on the sensor (x, y). K's principal point and the conversion factor are in this window's
    # pixels, so a camera running any other window must not use them. None when the calibration
    # file does not record them (files written before the window was recorded).
    #   Unit [Vector<int> 1x2] (px)
    Resolution: tp.Optional[tp.Tuple[int, int]] = None
    Offset: tp.Optional[tp.Tuple[int, int]] = None

@dataclass
class Camera_Configuration_Str:
    """
    Description:
        The structure of the main parameters of the camera (sensor) object,
        together with its calibration.

        Note:
            The parameter structure mainly focuses on the 2D representation of the
            image. It is populated from a configuration's 'Camera' block and its hardware's
            calibration file; see ../Configuration/Core.py (Load_Configuration).
    """

    # The camera, lens and lighting as a person names them ('Basler a2A1920-51gcPRO', 'Computar
    # M1228-MPW3', 'Effilux EFFI-FD-200-200-000'): named in the Configuration dialog's confirmation
    # and recorded in every capture set. The lighting matters as much as the optics — the colour
    # readings, the background subtraction and the surface-condition descriptions all depend on
    # it. Empty when the configuration does not say.
    Model: str = ''
    Lens: str = ''
    Lighting: str = ''
    # The sensor window the camera is set to on connect: its size (width, height) and its offset
    # on the sensor (x, y). The configuration is the only source — the camera never takes its size
    # from the background reference or from what the device last remembered.
    #   Unit [Vector<int> 1x2] (px)
    Resolution: tp.Tuple[int, int] = (0, 0)
    Offset: tp.Tuple[int, int] = (0, 0)
    # Custom camera configuration.
    #   Note:
    #       Required vendor/API specific settings (e.g., exposure, gain, white balance, pixel format); the
    #       configuration refuses a file without them, and Basler_Cls refuses an empty one.
    Custom_Cfg: tp.Dict[str, tp.Any] = field(default_factory=dict)
    # Calibration of the camera above, or None when the hardware has no calibration file yet: frames
    # are then not undistorted and objects are not measured (a camera being calibrated for the first
    # time has none — Example/Camera/calibrate.py creates it).
    Calibration: tp.Optional[Camera_Calibration_Parameters_Str] = None

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

@dataclass
class Calibration_View_Str:
    """
    Description:
        One image of a multi-view calibration: its kind (a board flat on the table, or tilted),
        what the detector found, and — once solved — how well the model reprojects it, how far
        the board is tilted from facing the camera, and (flat views only) its own mm/px.
    """

    # The image's filename and whether it is a flat view (the 'flat_' prefix).
    #   Unit [string] / [bool]
    Name: str = ''
    Flat: bool = False
    # The detection (Found False with a reason when the image is skipped).
    #   Unit [Board_Detection_Str(object)]
    Detection: Board_Detection_Str = field(default_factory=Board_Detection_Str)
    # The view's reprojection RMS error, and whether it stands far above the set's median.
    #   Unit [float] (px) / [bool]
    Rms_Px: tp.Optional[float] = None
    Outlier: bool = False
    # The board's tilt from facing the camera (angle between its normal and the optical axis).
    #   Unit [float] (degrees)
    Tilt_Deg: tp.Optional[float] = None
    # This flat view's own mm/px (x, y) from its undistorted corners; None for a tilted view.
    #   Unit [Vector<float> 1x2] (mm/px)
    Factor: tp.Optional[tp.Tuple[float, float]] = None


@dataclass
class Calibration_Report_Str:
    """
    Description:
        The result of a multi-view calibration and everything needed to judge it: the per-view
        breakdown, the reprojection error, the principal point's distance from the image centre,
        the spread of board tilts, the distortion's reach at the frame edge, and the mm/px factor
        from the flat views with its spread across images and across the frame. The warnings are
        sentences, empty when there is nothing to warn about.
    """

    # The image size (width, height) and every view, in natural filename order.
    Image_Size: tp.Tuple[int, int] = (0, 0)
    Views: tp.List[Calibration_View_Str] = field(default_factory=list)
    # The solved intrinsics, distortion (k1, k2, p1, p2, k3) and overall reprojection RMS (px).
    K: np.ndarray = field(default_factory=lambda: np.zeros((3, 3), dtype=np.float64), repr=False)
    Coefficients: tp.Dict[str, float] = field(default_factory=dict)
    Rms_Px: float = 0.0
    # The focal lengths of the application's own undistortion (getOptimalNewCameraMatrix) — the
    # pixel space measurement happens in — relative to K's (x, y).
    Undistortion_Rescale: tp.Tuple[float, float] = (1.0, 1.0)
    # The principal point's offset from the image centre (dx, dy) in px, its distance in px, and
    # the offset as a fraction of the frame (dx / width, dy / height).
    Principal_Offset_Px: tp.Tuple[float, float] = (0.0, 0.0)
    Principal_Distance_Px: float = 0.0
    Principal_Offset_Fraction: tp.Tuple[float, float] = (0.0, 0.0)
    # The tilt range over the detected views, and how many are tilted at least the threshold.
    Tilt_Range_Deg: tp.Tuple[float, float] = (0.0, 0.0)
    Tilted_Views: int = 0
    Tilt_Warning: str = ''
    # How far the distortion moves a point at the frame's corners and edge midpoints (px, in K's
    # pixel scale), keyed by position ('top-left', 'top', ...).
    Edge_Distortion_Px: tp.Dict[str, float] = field(default_factory=dict)
    # The mm/px factor (x, y) from the flat views' undistorted corners; its per-axis spread over
    # the flat views and over a grid of frame regions (max - min, % of the factor); the regional
    # map (rows of (x, y) or None where a cell has no data); and a warning when it is not uniform.
    Factor: tp.Tuple[float, float] = (0.0, 0.0)
    Factor_View_Spread_Pct: tp.Tuple[float, float] = (0.0, 0.0)
    Factor_Frame_Spread_Pct: tp.Tuple[float, float] = (0.0, 0.0)
    Factor_Map: tp.List[tp.List[tp.Optional[tp.Tuple[float, float]]]] = field(default_factory=list)
    Factor_Warning: str = ''
    # The board's square size and the flat boards' surface height above the table (mm) — the
    # reference plane the factor belongs to.
    Square_Mm: float = 0.0
    Board_Height_Mm: float = 0.0
