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
# File Name: ../Example/Camera/scan.py
## =========================================================================== ##

# System (Default)
import sys
#   Add access if it is not in the system path.
if '../../' + 'src' not in sys.path:
    sys.path.append('../../' + 'src')
# OpenCV library for computer vision tasks
import cv2
# Numpy (Array computing)
import numpy as np
# OS module for file handling and accessing directories
import os
# Custom Lib.:
#   ../Camera/Basler
from Camera.Basler import Basler_Cls
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Configuration, CONST_BASLER_CONFIG_FILE

"""
Description:
    Initialization of constants.
"""
# The identification number of the iteration to save the image. It starts with the number 1.
#   1 = 'Image_001', 2 = 'Image_002', etc.
CONST_INIT_INDEX = 1

def main():
    """
    Description:
        A program to configure a Basler camera (a2A1920-51gcPRO) with custom settings to capture an image. The system is equipped
        with the EFFI-FD-200-200-000 lighting for optimal illumination in the vision stand.

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """

    # Locate the path to the project folder.
    project_folder = os.getcwd().split('anyscan-pyqt')[0] + 'anyscan-pyqt'

    # Read the camera configuration (with calibration) from the *.yaml file.
    Basler_Cfg_Str = Read_Configuration(CONST_BASLER_CONFIG_FILE)

    # Initialize and configure the Basler camera.
    Basler_Cam_Id_1 = Basler_Cls(config=Basler_Cfg_Str.Custom_Cfg)

    # Capture a single image.
    image = Basler_Cam_Id_1.Capture()
    if image is None:
        raise ValueError('[ERROR] No image captured!')

    # Release the camera resources.
    del Basler_Cam_Id_1

    # Define output image path.
    output_path = os.path.join(f'{project_folder}/Data/', f'Image_{(CONST_INIT_INDEX):03}.png')

    # Undistort the image using camera calibration parameters.
    h, w = image.shape[:2]
    coeffs = np.array(list(Basler_Cfg_Str.Calibration.Coefficients.values()), dtype=np.float64)
    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(Basler_Cfg_Str.Calibration.K, coeffs,
                                                         (w, h), 1, (w, h))
    image_undistorted = cv2.undistort(image, Basler_Cfg_Str.Calibration.K, coeffs, None, new_camera_matrix)

    # Save the image with bounding boxes.
    cv2.imwrite(output_path, image_undistorted)
    print(f'[INFO] Result saved at: {output_path}')

if __name__ == '__main__':
    sys.exit(main())
