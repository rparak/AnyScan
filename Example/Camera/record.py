# System (Default)
import sys
#   Add access if it is not in the system path.
if '../../' + 'src' not in sys.path:
    sys.path.append('../../' + 'src')
# OpenCV library for computer vision tasks
import cv2
# Numpy (Array computing)
import numpy as np
# Custom Lib.:
#   ../Basler/Camera
from Basler.Core import Camera_Cls
#   ../Calibration/Parameters
from Calibration.Parameters import Basler_Calib_Param_Str
#   ../Utilities/Image_Processing
import Utilities.Image_Processing
#   ../Parameters/Scene
import Parameters.Scene

def main():
    """
    Description:
        A program to configure a Basler camera (a2A1920-51gcPRO) with custom settings for continuous image capture. The system is equipped
        with the EFFI-FD-200-200-000 lighting for optimal illumination in the vision stand.

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """
        
    # Initialize and configure the Basler camera.
    Basler_Cam_Id_1 = Camera_Cls(config=Parameters.Scene.Basler_Cam_Str.Custom_Cfg)

    # Full screen window.
    window_name = 'Captured Image'
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        # Capture a single image.
        img_raw = Basler_Cam_Id_1.Capture()
        if img_raw is None:
            raise ValueError('[ERROR] No image captured!')
        
        # Initialize the class for custom image processing.
        Process_Image_Cls = Utilities.Image_Processing.Process_Image_Cls('real')

        # Apply the image processing pipeline.
        img_raw_processed = Process_Image_Cls.Apply(img_raw)

        # Undistort the image using camera calibration parameters.
        h, w = img_raw_processed.shape[:2]
        new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(Basler_Calib_Param_Str.K, np.array(list(Basler_Calib_Param_Str.Coefficients.values()), dtype=np.float64), 
                                                             (w, h), 1, (w, h))
        img_undistorted = cv2.undistort(img_raw_processed, Basler_Calib_Param_Str.K, np.array(list(Basler_Calib_Param_Str.Coefficients.values()), dtype=np.float64), 
                                        None, new_camera_matrix)

        # Show the captured image.
        cv2.imshow('Captured Image', img_undistorted)
        
        # Wait for the user to press the 'c' key to exit the loop or stop if the camera is no longer grabbing.
        key = cv2.waitKey(100) & 0xFF
        if key == ord('c') or Basler_Cam_Id_1.Is_Grabbing == True:
            print('[INFO] Exiting the capture loop.')
            break

    # Release the camera resources and close the OpenCV window.
    cv2.destroyAllWindows()

    # Release the classes.
    del Basler_Cam_Id_1; del Process_Image_Cls

if __name__ == '__main__':
    sys.exit(main())