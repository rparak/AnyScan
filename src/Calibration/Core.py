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
# File Name: ../Calibration/Core.py
## =========================================================================== ##

# System (Default)
import os
import re
import json
# OpenCV library for computer vision tasks
import cv2
# Numpy (Array computing)
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.:
#   ../Parameters/Camera
from Parameters.Camera import Camera_Calibration_Parameters_Str, Board_Detection_Str

"""
Description:
    Initialization of constants.

    Calibration captures are the camera's frames BEFORE undistortion — the only form a lens model
    can be solved from — and every one taken is kept: a pose that is thrown away can never be
    re-examined. They are numbered in one sequence, their kind in the name: 'flat_NNN.png' is a
    board lying flat on the table (it feeds the lens model AND the mm/px factor), 'view_NNN.png' a
    tilted or raised board (it feeds the lens model only). A 'capture.json' manifest beside them
    states that they are distorted and how they were produced, so no reader mistakes them for the
    application's undistorted '<set>_raw.png'.
"""
# The filename prefixes of the two kinds of calibration capture.
#   Unit [string]
CONST_CALIB_FLAT_PREFIX = 'flat_'
CONST_CALIB_VIEW_PREFIX = 'view_'
# The manifest (sidecar) written beside the captures.
#   Unit [string]
CONST_CALIB_MANIFEST = 'capture.json'
# The smallest inner-corner grid (columns, rows) accepted from a board partly outside the frame:
# enough rows and columns to fix a plane's perspective, small enough that a board overhanging a
# corner by a couple of squares still qualifies.
#   Unit [Vector<int> 1x2]
CONST_CALIB_MIN_GRID = (4, 3)
# The sector-based detector's flags. CALIB_CB_LARGER finds whatever part of the grid is visible
# (the classic findChessboardCorners needs the whole board and fails on an overhanging one), and
# CALIB_CB_ACCURACY is the sub-pixel refinement. Measured on six noisy, perspective-warped
# synthetic boards (mean corner error against the true positions): LARGER | ACCURACY 0.031 px,
# LARGER alone 0.041 px; cornerSubPix run AFTER either makes it worse (0.051 px with an 11 x 11
# window, 0.079 px with 5 x 5), so it is not used; CALIB_CB_NORMALIZE_IMAGE costs 0.22 px, so it
# is not used either.
#   Unit [int]
CONST_CALIB_DETECT_FLAGS = cv2.CALIB_CB_LARGER | cv2.CALIB_CB_ACCURACY


def Detect_Board(image: np.ndarray) -> Board_Detection_Str:
    """
    Description:
        Find the chessboard's visible inner-corner grid in one image with
        findChessboardCornersSBWithMeta and CALIB_CB_LARGER, so a board that overhangs the frame
        still yields its visible part. The corners come back row-major over the detected grid.

    Args:
        (1) image [Matrix<uint8> HxW or HxWx3]: The image (BGR or grey).

    Returns:
        (1) parameter [Board_Detection_Str(object)]: The detection, or Found False with a reason.
    """

    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    found, corners, meta = cv2.findChessboardCornersSBWithMeta(grey, CONST_CALIB_MIN_GRID,
                                                               CONST_CALIB_DETECT_FLAGS)
    if not found or corners is None or meta is None:
        return Board_Detection_Str(Reason='no chessboard of at least %d x %d inner corners was '
                                          'found (blurred, glared, or too little of the board '
                                          'in view)' % CONST_CALIB_MIN_GRID)
    rows, columns = meta.shape[:2]
    points = corners.reshape(-1, 2).astype(np.float64)
    if points.shape[0] != rows * columns:
        return Board_Detection_Str(Reason='the detector returned %d corners for a %d x %d grid'
                                          % (points.shape[0], columns, rows))
    return Board_Detection_Str(Found=True, Grid=(int(columns), int(rows)), Corners=points)


def Next_Capture_Name(directory: str, flat: bool) -> str:
    """
    Description:
        The filename for the next calibration capture in a directory: one running number across
        both kinds (so the capture order survives), never reusing a number already on disk — an
        existing frame is never overwritten.

    Args:
        (1) directory [string]: The capture directory.
        (2) flat [bool]: True for a board lying flat on the table, False for a tilted view.

    Returns:
        (1) parameter [string]: 'flat_NNN.png' or 'view_NNN.png'.
    """

    pattern = re.compile(r'^(?:%s|%s)(\d+)\.png$' % (CONST_CALIB_FLAT_PREFIX, CONST_CALIB_VIEW_PREFIX))
    taken = [int(m.group(1)) for m in map(pattern.match, os.listdir(directory)) if m]
    prefix = CONST_CALIB_FLAT_PREFIX if flat else CONST_CALIB_VIEW_PREFIX
    return '%s%03d.png' % (prefix, max(taken, default=0) + 1)


def Record_Capture(directory: str, header: tp.Dict[str, tp.Any],
                   entry: tp.Dict[str, tp.Any]) -> str:
    """
    Description:
        Add one capture to the directory's manifest, creating it from the header the first time.
        The manifest is rewritten whole through a temporary file and an atomic replace, so an
        interrupted session leaves the previous, consistent manifest rather than a torn one.

    Args:
        (1) directory [string]: The capture directory.
        (2) header [Dict]: The manifest's fixed part (used only when the manifest is new).
        (3) entry [Dict]: The capture's record (file, kind, time, detection).

    Returns:
        (1) parameter [string]: The manifest path.
    """

    path = os.path.join(directory, CONST_CALIB_MANIFEST)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)
    else:
        manifest = dict(header, frames=[])
    manifest['frames'].append(entry)
    temporary = path + '.writing'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    os.replace(temporary, path)
    return path

class Checkerboard_Calibration_Cls:
    """
    Description:
        A class for performing camera calibration using a checkerboard pattern.

        Note:
            It estimates calibration parameters (matrix, distortion coefficients) and pixel-to-millimeter 
            conversion factors.
    
    Initialization of the Class:
        Args:
            (1) inner_corners [Vector<float> 1x2]: Number of inner corners per a checkerboard row and column (columns, rows).
            (2) square_size [float]: Size of one square on the checkerboard in mm.

        Example:
            Initialization:
                # Assignment of the variables.
                inner_corners = (11, 8); square_size = 12.0

                # Initialize the class.
                Cls = Checkerboard_Calibration_Cls(inner_corners, square_size)
    """
        
    def __init__(self, inner_corners: tp.Tuple[int, int], square_size: float) -> None:
        # Store the number of inner corners per dimension (adjusting by -1 to match OpenCV expectations).
        self.__inner_corners = [x_i - 1 for x_i in inner_corners]
        self.__square_size = square_size

        # Initialize the calibration parameters container.
        self.__Calib_Param_Str = Camera_Calibration_Parameters_Str()

        # Prepare the object points array for the checkerboard.
        self.__obj_points = np.zeros((self.__inner_corners[0] * self.__inner_corners[1], 3), np.float32)

        # Fill in X and Y coordinates using a grid; Z = 0 as it's a planar board.
        self.__obj_points[:, :2] = np.mgrid[0:self.__inner_corners[0], 0:self.__inner_corners[1]].T.reshape(-1, 2)

        # Scale by square size to convert to real-world units.
        self.__obj_points *= self.__square_size


    def __Get_Pixel_To_MM_Factor(self, corner_subpix: np.ndarray) -> tp.Dict[str, float]:
        """
        Description:
            Computes the pixel-to-millimeter conversion factors in X and Y directions
            based on subpixel corner detections.

        Args:
            (1) corners_subpix [np.ndarray]: Refined corner locations with subpixel accuracy (shape: N x 1 x 2).

        Returns:
            (1) parameter [Dict[str, float]]: Conversion factor in horizontal ('x') and vertical ('y') directions.
        """

        dist_horizontal = []; dist_vertical = []
 
        # Compute average horizontal distances between adjacent corners in each row.
        for row_i in range(self.__inner_corners[1]):
            for column_i in range(self.__inner_corners[0] - 1):
                i = row_i * self.__inner_corners[0] + column_i
                dist_horizontal.append(np.linalg.norm(corner_subpix[i + 1][0] 
                                                      - corner_subpix[i][0]))

        # Compute average vertical distances between adjacent corners in each column.
        for column_i in range(self.__inner_corners[0]):
            for row_i in range(self.__inner_corners[1] - 1):
                i = row_i * self.__inner_corners[0] + column_i
                dist_vertical.append(np.linalg.norm(corner_subpix[i + self.__inner_corners[0]][0] 
                                                    - corner_subpix[i][0]))
        
        return {
            'x': self.__square_size / float(np.mean(dist_horizontal)),
            'y': self.__square_size / float(np.mean(dist_vertical))
        }

    def Solve(self, image: np.ndarray, draw_chessboard_corners: bool = False,
              path: str = '') -> tp.Tuple[bool, tp.Optional[Camera_Calibration_Parameters_Str]]:
        """
        Description:
            Performs camera calibration using a single checkerboard image. It computes camera calibration 
            parameters as matrix, distortion coefficients, and pixel-to-mm conversion factors.

        Args:
            (1) image [np.ndarray]: Input image containing a visible checkerboard pattern.
            (2) draw_chessboard_corners [bool]: Whether to draw and save the image with detected corners.
            (3) path [string]: Directory path to save the visualized checkerboard image (if enabled).

        Returns:
            (1) parameter [Tuple[bool, Camera_Calibration_Parameters_Str or None]]:
                (1a) Success flag indicating whether calibration was successful.
                (1b) Calibration parameters if successful, otherwise None.
        """
                
        # Convert to grayscale if input is a color image.
        if len(image.shape) == 3:
            img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            img_gray = image.copy()

        # Try to find the checkerboard corners.
        ret, corners = cv2.findChessboardCorners(img_gray, self.__inner_corners, None)
        if not ret:
            print('[INFO] Checkerboard not detected.')
            return False, None

        # Refine corner positions to subpixel accuracy.
        criteria = (cv2.TermCriteria_EPS + cv2.TermCriteria_MAX_ITER, 30, 0.001)
        corners_subpix = cv2.cornerSubPix(img_gray, corners, (11, 11), (-1, -1), criteria)

        # Perform camera calibration to obtain the matrix and distortion coefficients
        _, K, dist_coeffs_tmp, _, _ = cv2.calibrateCamera(
            [self.__obj_points], [corners_subpix], img_gray.shape[::-1], None, None
        )
        # Flatten the distortion coefficients
        dist_coeffs = dist_coeffs_tmp.ravel()

        # Store the matrix.
        self.__Calib_Param_Str.K = K

        # Store the distortion coefficients.
        self.__Calib_Param_Str.Coefficients = {
            'k1': dist_coeffs[0],
            'k2': dist_coeffs[1],
            'p1': dist_coeffs[2],
            'p2': dist_coeffs[3],
            'k3': dist_coeffs[4] if dist_coeffs.size > 4 else 0.0
        }

        # Determine the pixel to mm conversion factor in both directions from the actual corners.
        self.__Calib_Param_Str.Conversion_Factor = self.__Get_Pixel_To_MM_Factor(corners_subpix)

        # [Optional] Draw the detected corners and save the image.
        if draw_chessboard_corners:
            img_corners = cv2.drawChessboardCorners(image, self.__inner_corners, corners_subpix, ret)
            cv2.imwrite(f'{path}/Image_Checkerboard_Calibrated.png', img_corners)

        return True, self.__Calib_Param_Str
