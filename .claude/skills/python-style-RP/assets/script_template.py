"""
## =========================================================================== ## 
MIT License
Copyright (c) 2023 Roman Parak
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
## =========================================================================== ## 
Author   : Roman Parak
Email    : Roman.Parak@outlook.com
Github   : https://github.com/rparak
File Name: ../Example/<Domain>/<script_name>.py
## =========================================================================== ## 
"""

# System (Default)
import sys
if '../../../' + 'src' not in sys.path:
    sys.path.append('../../../' + 'src')
# Time (Time access and conversions)
import time
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: Robotics Library for Everyone (RoLE)
#   ../RoLE/Parameters/Robot
import RoLE.Parameters.Robot as Parameters
#   ../RoLE/Kinematics/Core
import RoLE.Kinematics.Core

"""
Description:
    Initialization of constants.
"""
# Set the structure of the main parameters of the robot.
CONST_ROBOT_TYPE = Parameters.Universal_Robots_UR3_Str
# Number of randomly generated samples.
CONST_SIZE = 1000

def main():
    """
    Description:
        A program to <state what the program demonstrates or measures>. The program also checks
        the correctness of the calculation.
    """

    # Initialization of the structure of the main parameters of the robot.
    Robot_Str = CONST_ROBOT_TYPE

    """
    Description:
        Generation of random joint orientations in radians.
    """
    theta_rand_aux = [0.0] * len(Robot_Str.Theta.Limit)
    for i, th_limit in enumerate(Robot_Str.Theta.Limit):
        theta_rand_aux[i] = np.random.uniform(th_limit[0], th_limit[1], CONST_SIZE)

    theta_rand = np.transpose(theta_rand_aux)

    """
    Description:
        Time evaluation of the calculation method.
    """
    print('[INFO] The calculation is in progress.')

    # 1) Forward Kinematics (Standard)
    t_0 = time.time()
    for _, th in enumerate(theta_rand):
        RoLE.Kinematics.Core.Forward_Kinematics(th, 'Standard', Robot_Str)
    t = time.time() - t_0
    print(f'[INFO]  1) Forward Kinematics (Standard)')
    print(f'[INFO]      Time: {t:0.05f} in seconds.')

    """
    Description:
        Evaluation of the correctness of the calculation.
    """
    tolerance = 2
    for _, th in enumerate(theta_rand):
        th_limit_err = RoLE.Kinematics.Utilities.General.Check_Theta_Limit(th, Robot_Str)
        if th_limit_err.any():
            # Warning: Something wrong!
            print('[WARNING] The desired absolute joint positions are out of limit!')
            break

    print('[INFO] The calculation process is complete.')

if __name__ == '__main__':
    sys.exit(main())
