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
#   ../Parameters/Scene
import Parameters.Scene
#   ../Calibration/Parameters
from Calibration.Parameters import Basler_Calib_Param_Str

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

    # Initialize and configure the Basler camera.
    Basler_Cam_Id_1 = Basler_Cls(config=Parameters.Scene.Basler_Cam_Str.Custom_Cfg)

    # Capture a single image.
    img = Basler_Cam_Id_1.Capture()
    if img is None:
        raise ValueError('[ERROR] No image captured!')

    # Release the camera resources.
    del Basler_Cam_Id_1

    # Define output image path.
    output_path = os.path.join(f'{project_folder}/Data/', f'Image_{(CONST_INIT_INDEX):03}.png')

    # Undistort the image using camera calibration parameters.
    h, w = img.shape[:2]
    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(Basler_Calib_Param_Str.K, np.array(list(Basler_Calib_Param_Str.Coefficients.values()), dtype=np.float64), 
                                                         (w, h), 1, (w, h))
    img_undistorted = cv2.undistort(img, Basler_Calib_Param_Str.K, np.array(list(Basler_Calib_Param_Str.Coefficients.values()), dtype=np.float64), 
                                    None, new_camera_matrix)

    # Save the image with bounding boxes.
    cv2.imwrite(output_path, img_undistorted)
    print(f'[INFO] Result saved at: {output_path}')

if __name__ == '__main__':
    sys.exit(main())