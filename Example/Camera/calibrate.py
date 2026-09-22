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
# Argparse (Command-line parsing)
import argparse
# Datetime (Timestamps for the capture manifest)
from datetime import datetime
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Custom Library:
#   ../Camera/Utilities/Image_Processing
import Camera.Utilities.Image_Processing
#   ../Camera/Basler
from Camera.Basler import Basler_Cls
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Configuration, Write_Calibration, CONST_BASLER_CONFIG_FILE
#   ../Calibration/Core
import Calibration.Core

"""
Description:
    Initialization of constants.
"""
# The identification number of the iteration to save the image. It starts with the number 1.
#   1 = 'Image_001', 2 = 'Image_002', etc.
CONST_INIT_INDEX = 1


def Capture_Main(directory: str) -> int:
    """
    Description:
        Capture calibration frames interactively into a directory, one per key press, until 'q'.
        Each frame is the camera's image after the application's own processing step and BEFORE
        undistortion (a lens model can only be solved from distorted frames). Every frame taken
        is kept — also one where no board is found, which is reported but never deleted — and
        recorded in the directory's capture.json, which states that the frames are distorted.

    Args:
        (1) directory [string]: The directory the frames are written to (created if missing).

    Returns:
        (1) parameter [int]: The process exit code.
    """

    os.makedirs(directory, exist_ok=True)
    Basler_Cfg_Str = Read_Configuration(CONST_BASLER_CONFIG_FILE)
    Basler_Cam_Id_1 = Basler_Cls(config=Basler_Cfg_Str.Custom_Cfg)
    Process_Image_Cls = Camera.Utilities.Image_Processing.Process_Image_Cls('real')
    header = {'distorted': True,
              'note': ('These frames are NOT undistorted: they are the camera\'s images after the '
                       'application\'s processing step (the same blur and colour adjustment) and '
                       'before undistortion, for solving the lens model. They are not the '
                       'application\'s <set>_raw.png, which is undistorted.'),
              'processing': "Camera.Utilities.Image_Processing.Process_Image_Cls('real')",
              'configuration': os.path.basename(CONST_BASLER_CONFIG_FILE),
              'camera': Basler_Cfg_Str.Name, 'custom_cfg': Basler_Cfg_Str.Custom_Cfg,
              'kinds': {Calibration.Core.CONST_CALIB_FLAT_PREFIX: 'board flat on the table: lens '
                        'model and mm/px factor', Calibration.Core.CONST_CALIB_VIEW_PREFIX: 'board '
                        'tilted or raised: lens model only'},
              'created': datetime.now().isoformat(timespec='seconds')}

    print('[INFO] Capturing distorted calibration frames into: %s' % directory)
    print('[INFO] Keys: f = board FLAT on the table, t = board TILTED (vary the tilt: 20-45 degrees '
          'in several directions), q = quit. Every frame is kept.')
    while True:
        key = input('[f / t / q] > ').strip().lower()
        if key == 'q':
            break
        if key not in ('f', 't'):
            continue
        image_raw = Basler_Cam_Id_1.Capture()
        if image_raw is None:
            print('[WARNING] No image captured; nothing was written. Try again.')
            continue
        image = Process_Image_Cls.Apply(image_raw)
        name = Calibration.Core.Next_Capture_Name(directory, flat=(key == 'f'))
        cv2.imwrite(os.path.join(directory, name), image)
        detection = Calibration.Core.Detect_Board(image)
        Calibration.Core.Record_Capture(directory, header, {
            'file': name, 'kind': 'flat' if key == 'f' else 'view',
            'time': datetime.now().isoformat(timespec='milliseconds'),
            'board_found': detection.Found, 'grid': list(detection.Grid),
            'corners': int(detection.Corners.shape[0]), 'reason': detection.Reason})
        if detection.Found:
            print('[INFO] %s: board found, %d x %d inner corners visible.'
                  % (name, detection.Grid[0], detection.Grid[1]))
        else:
            print('[WARNING] %s: kept, but %s. Consider another pose.' % (name, detection.Reason))

    del Basler_Cam_Id_1, Process_Image_Cls
    return 0


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

    parser = argparse.ArgumentParser(description='Camera calibration from chessboard captures.')
    parser.add_argument('--capture', metavar='DIR', default=None,
                        help='capture distorted calibration frames into DIR, interactively')
    args = parser.parse_args()
    if args.capture is not None:
        return Capture_Main(args.capture)

    # Locate the path to the project folder.
    project_folder = os.getcwd().split('anyscan-pyqt')[0] + 'anyscan-pyqt'

    # Read the camera configuration (with calibration) from the *.yaml file.
    Basler_Cfg_Str = Read_Configuration(CONST_BASLER_CONFIG_FILE)

    # Initialize and configure the Basler camera.
    Basler_Cam_Id_1 = Basler_Cls(config=Basler_Cfg_Str.Custom_Cfg)

    # Capture a single image.
    image_raw = Basler_Cam_Id_1.Capture()
    if image_raw is None:
        raise ValueError('[ERROR] No image captured!')

    # Release the camera resources.
    del Basler_Cam_Id_1

    # The camera's calibration folder, and the output image path within it.
    camera_folder = f'{project_folder}/Data/Camera/{Basler_Cfg_Str.Name}'
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

        # Re-write the 'Calibration' block of the *.yaml configuration file so the freshly
        # solved result becomes the project's single source of truth (used by the camera backend).
        if Write_Calibration(x, CONST_BASLER_CONFIG_FILE):
            print(f'[INFO] Calibration parameters written to: {CONST_BASLER_CONFIG_FILE}')
        else:
            print('[WARNING] Calibration parameters could not be written to the configuration file.')

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
