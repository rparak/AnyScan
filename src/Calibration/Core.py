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
# File Name: Core.py
## =========================================================================== ##

# OpenCV library for computer vision tasks
import cv2
# Numpy (Array computing)
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.:
#   ../Calibration/Parameters
from Calibration.Parameters import Camera_Calibration_Parameters_Str

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
        
    def __init__(self, inner_corners: tp.Tuple[int, int], square_size: float):
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

    def Solve(self, image: np.ndarray, draw_chessboard_corners: bool = False, path: str = '') -> tp.Tuple[bool, tp.Optional[Camera_Calibration_Parameters_Str]]:
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
        if draw_chessboard_corners == True:
            img_corners = cv2.drawChessboardCorners(image, self.__inner_corners, corners_subpix, ret)
            cv2.imwrite(f'{path}/Image_Checkerboard_Calibrated.png', img_corners)

        return True, self.__Calib_Param_Str
