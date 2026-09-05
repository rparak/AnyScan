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
# Custom Lib.: <Project name>
#   ../<Domain>/<Module>
# import <Domain>.<Module> as <Alias>
#   ../<Domain>/<Module>
# from <Domain>.<Module> import <Name>
#   Example (drawn from this project):
#   import Transformation.Core as Transformation

"""
Description:
    Initialization of constants.
"""
# Set the structure of the main parameters used by the program.
#   Substitute the host project's own preset, e.g. CONST_INPUT_TYPE = <Alias>.<Preset>_Str
# Number of randomly generated samples.
CONST_SIZE = 1000

def main():
    """
    Description:
        A program to <state what the program demonstrates or measures>. The program also checks
        the correctness of the calculation.
    """

    """
    Description:
        Generation of the random input data for the demonstration.
    """
    data = np.random.uniform(0.0, 1.0, CONST_SIZE)

    """
    Description:
        Time evaluation of the calculation method.
    """
    print('[INFO] The calculation is in progress.')

    # 1) <State the step performed here.>
    t_0 = time.time()
    for _, x in enumerate(data):
        # Call into another module of this project (substitute the placeholders):
        #   <Domain>.<Module>.<Function>(x)
        pass
    t = time.time() - t_0
    print(f'[INFO]  1) <Name of the step>')
    print(f'[INFO]      Time: {t:0.05f} in seconds.')

    print('[INFO] The calculation process is complete.')

if __name__ == '__main__':
    sys.exit(main())
