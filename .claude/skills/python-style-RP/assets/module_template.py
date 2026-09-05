# TEMPLATE NOTE (delete this block): the header below is the `"""` docstring
#   form the source repository (RoLE) uses. If the host repo opens its files
#   with a `#`-comment block instead (e.g. anyscan-pyqt), use Form B from
#   assets/header.txt — same content, each line prefixed `#`. Match the repo's
#   existing form; consistency within the repo wins. See SKILL.md Non-negotiable 1.
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
File Name: ../<Domain>/<Module>.py
## =========================================================================== ## 
"""

# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Custom Lib.: <Project name>
#   ../<Domain>/<Module>
# from <Domain>.<Module> import <Name>
#   Example (drawn from this project):
#   from Transformation.Core import Homogeneous_Transformation_Matrix_Cls as HTM_Cls

"""
Description:
    Initialization of constants.
"""
# The calculation will be performed in three-dimensional (3D) space.
CONST_DIMENSION = 3
# Numerical tolerance of the calculation.
CONST_EPS_64 = 1e-64

@dataclass
class Example_Parameters_Str(object):
    """
    Description:
        The auxiliary structure of the example parameters.
    """

    # The name of the object.
    #   Unit [string]
    Name: str = ''
    # Center position (X, Y, Z) of the object.
    #   Unit [Vector<float> 1x3]
    Centroid: tp.List[float] = field(default_factory=list)
    # Identification of the type of the object.
    #   Note: 'Static', 'Dynamic'
    #   Unit [string]
    Type: str = ''

class Example_Cls(object):
    """
    Description:
        A specific class for working with an example object.

        Note:
            State here what the object is, in one or two sentences.

            Equation:
                y(t) = a * t + b, where t can take values 0.0 <= t <= 1.0.

    Initialization of the Class:
        Args:
            (1) centroid [Vector<float> 1x3]: Center position (X, Y, Z) of the object.
            (2) name [string]: The name of the object.

        Example:
            Initialization:
                # Assignment of the variables.
                p    = [0.0, 0.0, 0.0]
                name = 'Object_ID_0'

                # Initialization of the class.
                Cls = Example_Cls(p, name)

            Features:
                # Properties of the class.
                Cls.Centroid; Cls.Name

                # Functions of the class.
                Cls.Transformation(p)
    """

    def __init__(self, centroid: tp.List[float] = None, name: str = '') -> None:
        # << PRIVATE >> #
        self.__centroid = np.array(centroid if centroid is not None else [0.0] * CONST_DIMENSION,
                                   dtype=np.float64)
        self.__name = name

    @property
    def Centroid(self) -> tp.List[float]:
        """
        Description:
            Get the center position (centroid) of the object.

        Returns:
            (1) parameter [Vector<float> 1x3]: Center position (X, Y, Z) of the object.
        """

        return self.__centroid

    @property
    def Name(self) -> str:
        """
        Description:
            Get the name of the object.

        Returns:
            (1) parameter [string]: The name of the object.
        """

        return self.__name

    def Transformation(self, centroid: tp.List[float]) -> None:
        """
        Description:
            Transformation of the object position in X, Y, Z axes.

        Args:
            (1) centroid [Vector<float> 1x3]: The desired center position (X, Y, Z) of the object.
        """

        self.__centroid = np.array(centroid, dtype=np.float64)

def Get_Example_Distance(p_0: tp.List[float], p_1: tp.List[float]) -> float:
    """
    Description:
        Get the Euclidean distance between two points in three-dimensional (3D) space.

        Equation:
            d = ||p_1 - p_0||

    Args:
        (1) p_0 [Vector<float> 1x3]: Start point (X, Y, Z).
        (2) p_1 [Vector<float> 1x3]: End point (X, Y, Z).

    Returns:
        (1) parameter [float]: The Euclidean distance between the two points.
    """

    # 1) Calculation of the difference vector between the points.
    d_p = np.array(p_1, dtype=np.float64) - np.array(p_0, dtype=np.float64)

    # 2) Calculation of the norm of the difference vector.
    return np.linalg.norm(d_p)
