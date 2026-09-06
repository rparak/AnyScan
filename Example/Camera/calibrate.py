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
# File Name: ../Example/Camera/calibrate.py
## =========================================================================== ##

# System (Default)
import sys
#   Add access if it is not in the system path.
if '../../' + 'src' not in sys.path:
    sys.path.append('../../' + 'src')
# OS (Operating system interfaces)
import os
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Custom Library:
#   ../Camera/Utilities/Image_Processing
import Camera.Utilities.Image_Processing
#   ../Camera/Basler
from Camera.Basler import Basler_Cls
#   ../Parameters/Scene
import Parameters.Scene
#   ../Calibration/Core
import Calibration.Core

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
        A program to capture images of a checkerboard pattern using a Basler a2A1920-51gcPRO camera and perform camera calibration based
        on the captured images. The system is equipped with EFFI-FD-200-200-000 lighting to ensure optimal illumination.

        The calibration computes the camera matrix, distortion coefficients, and pixel-to-millimeter conversion factors
        to correct image distortions.

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """

    # Locate the path to the project folder.
    project_folder = os.getcwd().split('anyscan-pyqt')[0] + 'anyscan-pyqt'

    # Custom camera configuration.
    custom_cfg = {
        'exposure_time': 10000,
        'gain': 10,
        'balance_ratios': {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2},
        'pixel_format': 'BayerRG8'
    }

    # Initialize and configure the Basler camera.
    Basler_Cam_Id_1 = Basler_Cls(config=custom_cfg)

    # Capture a single image.
    image_raw = Basler_Cam_Id_1.Capture()
    if image_raw is None:
        raise ValueError('[ERROR] No image captured!')

    # Release the camera resources.
    del Basler_Cam_Id_1

    # The camera's calibration folder, and the output image path within it.
    camera_folder = f'{project_folder}/Data/Camera/{Parameters.Scene.Basler_Cam_Str.Name}'
    output_path = os.path.join(f'{camera_folder}/', f'Image_Checkerboard_{(CONST_INIT_INDEX):03}.png')

    # Initialize the class for custom image processing.
    Process_Image_Cls = Camera.Utilities.Image_Processing.Process_Image_Cls('real')

    # Apply the image processing pipeline.
    image_raw_processed = Process_Image_Cls.Apply(image_raw)

    # Function to adjust the contrast and brightness parameters of the input image
    # by clipping the histogram.
    (alpha_custom, beta_custom) = Camera.Utilities.Image_Processing.Get_Alpha_Beta_Parameters(image_raw_processed, 1.0)

    # Adjust the contrast and brightness of the image using the alpha and beta parameters.
    #   Equation:
    #       g(i, j) = alpha * f(i, j) + beta
    image_out = cv2.convertScaleAbs(image_raw_processed, alpha=alpha_custom, beta=beta_custom)

    # Initialize the checkerboard calibration class with checkerboard dimensions and square size (in mm).
    Checkerboard_Calib_Cls = Calibration.Core.Checkerboard_Calibration_Cls(inner_corners=(11, 8), square_size=12.0)

    # Perform camera calibration using the provided checkerboard image.
    flag, x = Checkerboard_Calib_Cls.Solve(image_out, False, camera_folder)

    # Check whether calibration was successful.
    if flag:
        # Display the camera calibration results: intrinsic matrix, distortion coefficients, and scaling factor.
        print(f'[INFO] Intrinsic Matrix (K):\n{x.K}')
        print(f'[INFO] Distortion Coefficients:\n{x.Coefficients}')
        print(f'[INFO] Pixel-to-mm Conversion Factor:\n{x.Conversion_Factor}')

        # Save the image after successful calibration to the specified output path.
        cv2.imwrite(output_path, image_out)
        print('[INFO] The data processing was completed successfully.')
        print(f'[INFO] Output image saved to: {output_path}')
    else:
        # Inform user that checkerboard detection or calibration failed.
        print('[WARNING] Data processing was not completed successfully. An error occurred.')

    # Release the classes.
    del Process_Image_Cls

if __name__ == '__main__':
    sys.exit(main())
