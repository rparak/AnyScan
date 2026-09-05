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
# File Name: Scene.py
## =========================================================================== ##

# Numpy (Array computing)
import numpy as np
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Typing (Support for type hints)
import typing as tp
# Custom Lib.:
#   ../Transformation/Core
import Transformation.Core as Transformation 

@dataclass
class Camera_Parameters_Str:
    """
    Description:
        The structure of the main parameters of the camera (sensor) object.

        Note:
            The parameter structure mainly focuses on the 2D representation of the image.
    """

    # Name of the Camera.
    Name: str = 'Camera'
    # Homogeneous transformation matrix of the object.
    T: tp.List[tp.List[float]] = field(default_factory=list)
    # Camera resolution in pixels (x, y) and resolution percentage.
    Resolution: tp.Dict[str, int] = field(default_factory=dict)
    # Projection of the camera's field of view: Perspective = ['PERSP'], Orthographic = ['ORTHO']
    Type: str = 'PERSP'
    # The focal length (lens) of the camera in millimeters.
    f: float = 0.0
    # Spectrum of the camera ('Monochrome' or 'Color'). The color parameter of the output image.
    Spectrum: str = 'Monochrome'
    # Sensor width/height in millimeter and fit type ('HORIZONTAL' or 'VERTICAL').
    Sensor: tp.Dict[str, float] = field(default_factory=dict)
    # Exposure time in microseconds.
    Exposure_Time: int = 10
    # Camera gain to increase the brightness of the images output.
    Gain: float = 1.0
    # RGB balance ratios.
    Balance_Ratios: tp.Tuple[float, float, float] = (1.0, 1.0, 1.0)
    # Aperture (F-stop) value for Depth of Field (DOF).
    Aperture_F_Stop: float = 0.0
    # Focus distance in meters.
    Focus_Distance: float = 0.0
    # Depth of Field usage flag.
    Use_DoF: bool = False
    # Frame rate of the camera.
    FPS: int = 24
    # Orthographic camera zoom level (higher = zoomed out).
    Orthographic_Scale: float = 0.0

    # Custom camera configuration.
    #   Note:
    #       Optional structure for vendor/API specific settings (e.g., exposure, gain, white balance, pixel format).
    Custom_Cfg: tp.Dict[str, tp.Any] = field(default_factory=dict)

    def __post_init__(self):
        # Ensure valid default values for depth of field and focus distance.
        if self.Use_DoF == True and self.Focus_Distance == 0.0:
            raise ValueError('Focus distance must be set if Depth of Field is used.')

@dataclass
class Light_Parameters_Str:
    """
    Description:
        The structure of the main parameters of the light object.
        
        Note:
            The parameter structure mainly focuses on the light's physical and appearance properties.
    """

    # Name of the light.
    Name: str = 'Light'
    # Homogeneous transformation matrix of the object.
    T: tp.List[tp.List[float]] = field(default_factory=list)
    # Energy of the light (in some arbitrary units).
    Energy: float = 1.0 
    # Color of the light (e.g., RGB).
    #   Note: Default to white light (RGB = 1,1,1).
    Color: tp.Tuple[float, float, float] = (1.0, 1.0, 1.0)
    # Size of the light (e.g., diameter or area depending on shape).
    Size: float = 1.0
    # Shape of the light ('POINT', 'SUN', 'SPOT', 'AREA', or 'SQUARE')
    Shape: str = 'POINT'
    
    def __post_init__(self):
        # Ensure valid default values for parameters.
        if self.Energy <= 0:
            raise ValueError('Energy must be a positive value.')
        if self.Size <= 0:
            raise ValueError('Size must be a positive value.')
        if self.Shape not in ['POINT', 'SUN', 'SPOT', 'AREA', 'SQUARE']:
            raise ValueError('Shape must be one of "POINT", "SUN", "SPOT", "AREA", or "SQUARE".')
        
"""
Description:
    Parameters of the Basler camera setup, including resolution, properties, sensor, and lens configuration.

    Camera Setup: Basler a2A1920-51gcPRO with Computar M1228-MPW3 Lens

    Basler Camera Resolution:
        - Resolution: 1920 x 1200 pixels (Width x Height)
        - The camera's resolution is defined as a percentage of its maximum capability:
            - Percentage: 100% (Full resolution)

    Camera Properties and Sensor Parameters:
        - Type: 'PERSP' (Perspective) - This indicates that the camera is set to capture images based on a perspective projection.
        - Focal Length (f): 12 mm - The focal length of the lens. 
        - Spectrum: 'Color' - The camera captures images in full color.
        - Sensor:
            - Width: 6.6 mm - The physical width of the sensor.
            - Height: 4.1 mm - The physical height of the sensor.
            - Fit: 'HORIZONTAL' - The sensor orientation relative to the field of view, indicating that the horizontal axis aligns with the camera's primary viewing direction.

    Custom camera configuration:
        - Exposure time: Specifies how long the image sensor is exposed to light during image acquisition.
        - Gain: Allows to increase the brightness of the images output by the camera.
        - Balance ratios: Allows to manually correct color shifts so that white objects appear white in images acquired (Balance White).
        
    Lens and Focus Configuration:
        - Aperture F-Stop: 2.8 - The aperture size (f-stop) controls the amount of light entering the camera.
"""
Basler_Cam_Str = Camera_Parameters_Str(Name='Basler_a2A1920_51gcPRO_Computar_M1228_MPW3')

# Homogeneous transformation matrix {T} of the object.
Basler_Cam_Str.T = Transformation.Homogeneous_Transformation_Matrix_Cls(None, np.float64).Rotation([0.0, 0.0, 0.0], 
                                                                                         'ZYX').Translation([0.0, -0.00265, 0.3401])

# Camera resolution in pixels.
Basler_Cam_Str.Resolution = {'x': 1920, 'y': 1200, 'Percentage': 100}

# Camera FPS (frames per second).
Basler_Cam_Str.FPS = 51

# Camera and lense properties.
Basler_Cam_Str.Type = 'PERSP'
Basler_Cam_Str.f = 12
Basler_Cam_Str.Spectrum = 'Color'
Basler_Cam_Str.Sensor = {'Width': 6.6, 'Height': 4.1, 'Fit': 'HORIZONTAL'}
Basler_Cam_Str.Gain = 10
Basler_Cam_Str.Exposure_Time = 1000
Basler_Cam_Str.Balance_Ratios = (0.95, 0.9, 0.85)
Basler_Cam_Str.Aperture_F_Stop = 2.8  
Basler_Cam_Str.Focus_Distance = Basler_Cam_Str.T.p.z
Basler_Cam_Str.Use_DoF = True

# Custom camera configuration (vendor/API specific).
Basler_Cam_Str.Custom_Cfg = {
    'Exposure_Time': 10000,
    'Gain': 10,
    'Balance_Ratios': {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2},
    'Pixel_Format': 'BayerRG8'
}

"""
Description:
    Parameters of the Effilux light source, including its energy properties, color, size, and shape.

    Effilux Light:
        - Model: Effilux EFFI-FD-200-200-000

    Light Properties:
        - Energy: 1.2 Watts - The power output of the light source, which influences its brightness and the amount of heat generated.
        - Color: (1.0, 1.0, 1.0) - The light color is defined as an RGB tuple, where (1.0, 1.0, 1.0) represents pure white light.
        - Size: 0.2 meters - The size of the light source, which affects how concentrated or diffuse the light is.
        - Shape: 'SQUARE' - The shape of the light emission. A square-shaped light source provides uniform lighting in a rectangular or square area.
"""
Effilux_Light_Str = Light_Parameters_Str(Name='EFFI-FD-200-200-000')

# Homogeneous transformation matrix {T} of the object.
Effilux_Light_Str.T = Transformation.Homogeneous_Transformation_Matrix_Cls(None, np.float64).Rotation([0.0, 0.0, 0.0], 
                                                                                            'XYZ').Translation([0.0, 0.0, 0.287215])

# Light properties.
Effilux_Light_Str.Energy = 1.2/2.0
Effilux_Light_Str.Color = (1.0, 1.0, 1.0)
Effilux_Light_Str.Size = 0.2
Effilux_Light_Str.Shape = 'SQUARE'