## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../Vision/Utilities/Dimensions.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the detection, measurement and catalogue structures
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Measurement_Str, Dimension_Check_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Outline_Str, Catalogue_Item_Str

"""
Description:
    Initialization of constants.

    The catalogue's dimension checks: an object's measured sizes against the nominal values and
    tolerances of a catalogue item, each check keeping what was measured, what was expected and the
    tolerance, so a failed one can say all three. Qt-free and dependency-free: the sizes come from
    Vision.Utilities.Measure, already in millimetres at the catalogue part's top face.
"""

# How far past a tolerance bound a measured value may sit and still count as on the bound: the bounds
# are included, and a size computed in floating point lands a few ulps either side of a bound it
# equals in exact arithmetic. Nine orders of magnitude below the 0.1 mm a pixel spans here.
#   Unit [float] (mm)
CONST_DIMENSION_BOUND_EPSILON = 1e-9


def Check_Dimension(name: str, measured_mm: float, nominal_mm: float, tolerance_mm: float) -> Dimension_Check_Str:
    """
    Description:
        One dimension against its nominal value: within when it lies in nominal ± tolerance, bounds
        included.

    Args:
        (1) name [string]: Which dimension ('length', 'width').
        (2) measured_mm [float]: The measured value.
        (3) nominal_mm [float]: The nominal value.
        (4) tolerance_mm [float]: The tolerance.

    Returns:
        (1) parameter [Dimension_Check_Str(object)]: The check.
    """

    within = abs(measured_mm - nominal_mm) <= tolerance_mm + CONST_DIMENSION_BOUND_EPSILON
    return Dimension_Check_Str(Name=name, Measured_Mm=measured_mm, Nominal_Mm=nominal_mm,
                               Tolerance_Mm=tolerance_mm, Within=within)


def Check_Outline(measurement: tp.Optional[Measurement_Str],
                  Catalogue_Outline_Str: Catalogue_Outline_Str) -> tp.List[Dimension_Check_Str]:
    """
    Description:
        An object's outline against the catalogue's: the longer measured side (Measurement_Str's
        Width_Mm) against Length_Mm, the shorter (Height_Mm) against Width_Mm, so the part's rotation
        does not matter. An object that is not measured, or is round (a diameter, no sides), has no
        outline to check: no checks.

    Args:
        (1) measurement [Measurement_Str(object) or None]: The object's measurement.
        (2) Catalogue_Outline_Str [Catalogue_Outline_Str(object)]: The catalogue's outline.

    Returns:
        (1) parameter [Vector<Dimension_Check_Str(object)>]: The length and width checks, or [].
    """

    if measurement is None or measurement.Symmetric:
        return []
    outline = Catalogue_Outline_Str
    return [Check_Dimension('length', measurement.Width_Mm, outline.Length_Mm, outline.Tolerance_Mm),
            Check_Dimension('width', measurement.Height_Mm, outline.Width_Mm, outline.Tolerance_Mm)]


def Check_Objects(objects: tp.List[Detection_Str], Catalogue_Item_Str: Catalogue_Item_Str) -> None:
    """
    Description:
        Run the catalogue's dimension checks on every object, in place (det.Dimension_Checks). Every
        object is checked: which one is the catalogue part is not decided yet, so an object whose
        outline passes is one the size of the part, not one known to be it.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The measured objects.
        (2) Catalogue_Item_Str [Catalogue_Item_Str(object)]: The catalogue item.
    """

    for det in objects:
        det.Dimension_Checks = Check_Outline(det.Measurement, Catalogue_Item_Str.Outline)
