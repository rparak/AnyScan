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
# File Name: ../test/Vision/Utilities/test_dimensions.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the dimension checks, their text, and the structures they read
#   ../Vision/Utilities/Dimensions
from Vision.Utilities.Dimensions import Check_Dimension, Check_Outline, Check_Objects
#   ../Reporting/Core
from Reporting.Core import Dimension_Check_Text
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Measurement_Str, Dimension_Check_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Outline_Str, Catalogue_Item_Str

"""
Description:
    The catalogue's dimension checks: a size against its nominal value and tolerance (bounds
    included), the outline compared whatever the part's rotation, round and unmeasured objects left
    unchecked, and the text a check is reported in.
"""

# The mounting plate's outline: 60 x 40 mm, ±1.5 mm.
CONST_OUTLINE = Catalogue_Outline_Str(Length_Mm=60.0, Width_Mm=40.0, Tolerance_Mm=1.5)


@pytest.mark.parametrize('measured, within', [
    (60.0, True), (61.5, True), (58.5, True), (61.5 + 1e-12, True),
    (61.51, False), (58.49, False), (0.0, False),
])
def test_a_dimension_is_within_its_tolerance_bounds_included(measured: float, within: bool) -> None:
    """
    Description:
        A size passes within nominal ± tolerance, the bounds themselves included (a size that equals
        a bound in exact arithmetic and lands an ulp past it in floating point still does), and fails
        a hundredth of a millimetre outside them. The check keeps all three numbers it compared.
    """

    check = Check_Dimension('length', measured, 60.0, 1.5)
    assert check == Dimension_Check_Str(Name='length', Measured_Mm=measured, Nominal_Mm=60.0, Tolerance_Mm=1.5,
                                        Within=within)


def test_the_outline_compares_the_longer_side_with_the_length() -> None:
    """
    Description:
        A measurement's Width_Mm is its longer side and Height_Mm its shorter, whatever the part's
        rotation; the outline checks the longer against Length_Mm and the shorter against Width_Mm, so
        a plate lying either way round gets the same two checks.
    """

    checks = Check_Outline(Measurement_Str(Width_Mm=60.4, Height_Mm=40.2, Angle_Deg=90.0), CONST_OUTLINE)
    assert [(c.Name, c.Measured_Mm, c.Nominal_Mm, c.Within) for c in checks] == [
        ('length', 60.4, 60.0, True), ('width', 40.2, 40.0, True)]
    checks = Check_Outline(Measurement_Str(Width_Mm=60.4, Height_Mm=42.0, Angle_Deg=0.0), CONST_OUTLINE)
    assert [c.Within for c in checks] == [True, False]


@pytest.mark.parametrize('measurement', [None, Measurement_Str(Symmetric=True, Diameter_Mm=60.0)],
                         ids=['not measured', 'round'])
def test_an_object_without_sides_has_no_outline_to_check(measurement: tp.Any) -> None:
    """
    Description:
        An object that is not measured, or is round (a diameter and no sides), has no outline: no
        checks, rather than a check that passes or fails on numbers it does not have.
    """

    assert Check_Outline(measurement, CONST_OUTLINE) == []


def test_every_object_is_checked_against_the_item() -> None:
    """
    Description:
        Check_Objects runs the outline check on every object, in place: which object is the catalogue
        part is not decided yet, so a washer is checked as much as the plate.
    """

    item = Catalogue_Item_Str(Name='mounting_plate', Thickness_Mm=8.0, Tolerance_Mm=1.5, Outline=CONST_OUTLINE)
    plate = Detection_Str(Label='plate', Bbox=(0, 0, 1, 1), Measurement=Measurement_Str(Width_Mm=60.3, Height_Mm=40.1))
    washer = Detection_Str(Label='washer', Bbox=(0, 0, 1, 1), Measurement=Measurement_Str(Symmetric=True, Diameter_Mm=16.0))
    screw = Detection_Str(Label='screw', Bbox=(0, 0, 1, 1), Measurement=Measurement_Str(Width_Mm=40.0, Height_Mm=8.0))
    Check_Objects([plate, washer, screw], item)
    assert [c.Within for c in plate.Dimension_Checks] == [True, True]
    assert washer.Dimension_Checks == []
    assert [c.Within for c in screw.Dimension_Checks] == [False, False]


def test_a_check_is_reported_with_what_was_measured_expected_and_allowed() -> None:
    """
    Description:
        A check's text names the dimension, the measured value, the nominal value with its tolerance and
        the outcome, each size at the display's two decimals — so a failed check needs nothing else to
        be understood.
    """

    assert Dimension_Check_Text(Check_Dimension('length', 60.254, 60.0, 1.5)) == \
        'length 60.25 mm, expected 60.00 ± 1.50 mm: within'
    assert Dimension_Check_Text(Check_Dimension('width', 41.6, 40.0, 1.5)) == \
        'width 41.60 mm, expected 40.00 ± 1.50 mm: OUT OF TOLERANCE'
