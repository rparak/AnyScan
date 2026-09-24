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
# OS module for file handling and accessing directories
import os
# Custom Lib.:
#   ../Camera/Core — the application's own camera path (window, processing, undistortion)
from Camera.Core import Basler_Camera_Cls, Camera_Error_Cls
#   ../Configuration/Core — the one configuration layer
from Configuration.Core import Load_Configuration, Display_Path, CONST_DEFAULT_CONFIG_FILE, CONST_PROJECT_ROOT

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
        Capture one frame from the Basler camera (a2A1920-51gcPRO, lit by the EFFI-FD-200-200-000)
        and save it as Data/Image_<NNN>.png.

        The frame goes through the APPLICATION's own camera path, Camera.Core.Basler_Camera_Cls —
        the sensor window set and read back, the image processing step, and the undistortion under
        the calibration in force — so it is the frame the pipeline sees, not a harness's
        approximation of it. (This harness used to undistort without the processing step; its frames
        then differed from the pipeline's.)

        Note:
            The saved frame carries no provenance: nothing records the window, calibration or
            lighting it was shot under. Do NOT use it as a background reference. References are made
            from a capture set with Example/Camera/make_reference.py, which writes that record.

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """

    # The shipped configuration: the camera block (acquisition settings, window, calibration).
    configuration = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    for level, message in configuration.Notes:
        print(f'[{level}] {message}')

    # Connect through the application's camera, capture one frame (RGB), and release the camera.
    camera = Basler_Camera_Cls()
    camera.Set_Configuration(configuration.Camera, configuration.Name,
                             os.path.basename(configuration.Calibration_Path) if configuration.Camera.Calibration else '')
    camera.Set_Log_Callback(lambda level, message: print(f'[{level}] {message}'))
    try:
        camera.Connect()
        image_rgb = camera.Capture()
    except Camera_Error_Cls as error:
        print(f'[ERROR] {error}')
        return 1
    finally:
        camera.Disconnect()

    # Save the image (OpenCV writes BGR).
    output_path = os.path.join(CONST_PROJECT_ROOT, 'Data', f'Image_{CONST_INIT_INDEX:03}.png')
    cv2.imwrite(output_path, cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
    print(f'[INFO] Frame saved at: {Display_Path(output_path)} (the pipeline\'s frame; not a reference - see '
          f'make_reference.py)')
    return 0

if __name__ == '__main__':
    sys.exit(main())
