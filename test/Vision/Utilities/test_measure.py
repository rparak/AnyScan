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
# File Name: ../test/Vision/Utilities/test_measure.py
## =========================================================================== ##

# System (Default)
import math
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — measurement, the formatter, the config reader, the renderer, the writer
#   ../Vision/Utilities/Measure
import Vision.Utilities.Measure as Measure
from Vision.Utilities.Measure import Measure_Mask, Measure_Objects, Measure_Decimals
#   ../Reporting/Core
from Reporting.Core import Object_Size, Object_Label_Full
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Conversion_Factor, CONST_BASLER_CONFIG_FILE
#   ../Vision/Utilities/Annotate
import Vision.Utilities.Annotate as Annotate
#   ../UI/Capture
from UI.Capture import Capture_Writer_Cls, Build_Set_Metadata, Discover_Capture_Sets
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Scale_Str, CONST_SCALE_UNITS
#   ../Parameters/Theme
import Parameters.Theme as Theme

"""
Description:
    Object measurement: the rotated rectangle of a mask converted to millimetres through the
    configured mm/px scale, the angle convention, the symmetric (diameter) case and the square
    exception, the label format, the missing-factor degradation, the stored record, and the
    Camera View's solid/dashed drawing. Synthetic masks are built ANALYTICALLY — a pixel is set
    when its centre lies inside the rectangle — so their true size and angle are exact.
"""

# A round-number scale: 0.1 mm per pixel on both axes (so 200 px = 20.0 mm, 1 decimal).
CONST_SCALE = Scale_Str(Mm_Per_Px_X=0.1, Mm_Per_Px_Y=0.1)
# The frame the synthetic masks are drawn on (h, w).
CONST_SHAPE = (700, 900)


def _Rectangle(width_px: float, height_px: float, angle_deg: float) -> np.ndarray:
    """A mask of a width x height rectangle, its width side at angle_deg COUNTER-CLOCKWISE ON
    SCREEN from +x, centred in the frame: a pixel is set when its centre lies inside."""
    cy, cx = CONST_SHAPE[0] / 2.0, CONST_SHAPE[1] / 2.0
    ys, xs = np.mgrid[0:CONST_SHAPE[0], 0:CONST_SHAPE[1]]
    dx, dy = xs + 0.5 - cx, -(ys + 0.5 - cy)                   # screen coordinates, y up
    t = math.radians(angle_deg)
    u = dx * math.cos(t) + dy * math.sin(t)
    v = -dx * math.sin(t) + dy * math.cos(t)
    return (np.abs(u) <= width_px / 2.0) & (np.abs(v) <= height_px / 2.0)


def _Block(width_px: int, height_px: int) -> np.ndarray:
    """An axis-aligned mask of EXACTLY width x height pixels (sliced), for exact sizes."""
    mask = np.zeros(CONST_SHAPE, bool)
    mask[250:250 + height_px, 300:300 + width_px] = True
    return mask


def _Disc(radius_px: float) -> np.ndarray:
    """A mask of a disc of the given radius, centred in the frame."""
    ys, xs = np.mgrid[0:CONST_SHAPE[0], 0:CONST_SHAPE[1]]
    return (xs + 0.5 - CONST_SHAPE[1] / 2.0) ** 2 + (ys + 0.5 - CONST_SHAPE[0] / 2.0) ** 2 <= radius_px ** 2


def test_known_size_and_angle_through_a_known_factor() -> None:
    """
    Description:
        A 200 x 100 px rectangle at 0.1 mm/px is 20.0 x 10.0 mm, long side first, at the angle it
        was drawn — axis-aligned exactly, rotated to within a pixel of the mask's staircase.
    """

    straight = Measure_Mask(_Rectangle(200, 100, 0.0), CONST_SCALE, cv2, np)
    assert (straight.Width_Mm, straight.Height_Mm, straight.Angle_Deg) == (20.0, 10.0, 0.0)
    assert not straight.Symmetric and straight.Diameter_Mm is None

    rotated = Measure_Mask(_Rectangle(200, 100, 30.0), CONST_SCALE, cv2, np)
    assert rotated.Width_Mm == pytest.approx(20.0, abs=0.15)
    assert rotated.Height_Mm == pytest.approx(10.0, abs=0.15)
    assert rotated.Angle_Deg == pytest.approx(30.0, abs=0.5)


@pytest.mark.parametrize('drawn, expected', [(0.0, 0.0), (30.0, 30.0), (-30.0, 150.0),
                                             (60.0, 60.0), (90.0, 90.0), (135.0, 135.0),
                                             (179.0, 179.0), (181.0, 1.0)])
def test_angle_convention_is_pinned(drawn: float, expected: float) -> None:
    """
    Description:
        The angle is the LONG side's direction from the image +x axis, counter-clockwise AS SEEN
        ON SCREEN, in [0, 180): a side rising to the right is below 90, one falling to the right
        (drawn clockwise, -30°) is 150. It is computed from the rectangle's corners, not taken from
        minAreaRect, so neither its sign nor its origin can flip with an OpenCV release.
    """

    measured = Measure_Mask(_Rectangle(240, 80, drawn), CONST_SCALE, cv2, np).Angle_Deg
    assert 0.0 <= measured < 180.0
    difference = abs((measured - expected + 90.0) % 180.0 - 90.0)   # compare modulo 180
    assert difference <= 0.5, (drawn, measured)


def test_rotationally_symmetric_object_reports_a_diameter_and_no_angle() -> None:
    """
    Description:
        A disc is not elongated and not square-like: it reports a diameter (Ø 2r at the scale), no
        width, no height and NO angle — minAreaRect's orientation on a disc is noise.
    """

    disc = Measure_Mask(_Disc(80.0), CONST_SCALE, cv2, np)
    assert disc.Symmetric
    assert disc.Diameter_Mm == pytest.approx(16.0, abs=0.15)
    assert disc.Angle_Deg is None and disc.Width_Mm is None and disc.Height_Mm is None
    assert disc.Elongation < Measure.CONST_MEASURE_SYMMETRIC_ELONGATION
    assert disc.Extent < Measure.CONST_MEASURE_SQUARE_EXTENT


def test_a_square_is_not_symmetric_and_its_angle_folds_to_ninety() -> None:
    """
    Description:
        A square is as un-elongated as a disc, but its sides are real edges: it keeps A x B and an
        angle, folded to [0, 90) because its two sides are interchangeable — so 20° and 110° (the
        same square) read the same, instead of flipping by 90° on noise.
    """

    for drawn in (20.0, 110.0):
        square = Measure_Mask(_Rectangle(150, 150, drawn), CONST_SCALE, cv2, np)
        assert not square.Symmetric
        assert square.Extent >= Measure.CONST_MEASURE_SQUARE_EXTENT
        assert square.Width_Mm == pytest.approx(15.0, abs=0.2)
        assert square.Angle_Deg == pytest.approx(20.0, abs=0.5)


def test_each_axis_uses_its_own_factor() -> None:
    """
    Description:
        The scale is per axis (mm = px x factor along each axis): an axis-aligned 200 x 100 px block
        at (0.1, 0.12) mm/px is 20.0 mm along x and 12.0 mm along y.
    """

    mask = np.zeros(CONST_SHAPE, bool)
    mask[300:400, 350:550] = True
    measured = Measure_Mask(mask, Scale_Str(Mm_Per_Px_X=0.1, Mm_Per_Px_Y=0.12), cv2, np)
    assert (measured.Width_Mm, measured.Height_Mm) == (20.0, 12.0)


def test_decimals_follow_the_scale_resolution() -> None:
    """
    Description:
        Sizes are shown to the resolution one pixel supports — 0.098 mm/px to 0.1 mm, 0.5 mm/px to
        whole millimetres, 0.01 mm/px to 0.01 mm — never three decimals on a coarse scale.
    """

    assert Measure_Decimals(Scale_Str(0.098, 0.098)) == 1
    assert Measure_Decimals(Scale_Str(0.5, 0.5)) == 0
    assert Measure_Decimals(Scale_Str(0.01, 0.01)) == 2
    coarse = Measure_Mask(_Rectangle(200, 100, 0.0), Scale_Str(0.5, 0.5), cv2, np)
    assert Object_Size(Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Measurement=coarse)) == '100 × 50 mm'


def test_label_carries_the_size_after_the_confidence() -> None:
    """
    Description:
        The shared label gains the size after the confidence — 'A × B mm' for an elongated object,
        'Ø D mm' for a symmetric one — and has no size segment at all when unmeasured.
    """

    rectangle = Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Segmenter_Score=0.91,
                              Measurement=Measure_Mask(_Block(243, 187), CONST_SCALE, cv2, np))
    disc = Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Segmenter_Score=0.91,
                         Measurement=Measure_Mask(_Disc(80.0), CONST_SCALE, cv2, np))
    plain = Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Segmenter_Score=0.91)

    assert Object_Label_Full(0, rectangle) == 'Object 1 · Confidence 91% · 24.3 × 18.7 mm'
    import re
    assert re.fullmatch(r'Ø \d+\.\d mm', Object_Size(disc)), Object_Size(disc)   # one decimal
    assert Object_Label_Full(0, disc) == 'Object 1 · Confidence 91% · ' + Object_Size(disc)
    assert Object_Label_Full(0, plain) == 'Object 1 · Confidence 91%'


def test_missing_factor_degrades_to_no_measurement_with_a_warning(tmp_path) -> None:
    """
    Description:
        A configuration without a Conversion_Factor (or with a non-positive one) yields no scale;
        with no scale nothing is measured — every Measurement stays None and the label has no size
        — and the launcher logs a WARNING saying so. Never a number from a default.
    """

    import App.run as run

    shipped = open(CONST_BASLER_CONFIG_FILE, encoding='utf-8').read()
    without = tmp_path / 'no_factor.yaml'
    without.write_text(shipped.replace('Conversion_Factor:', 'Conversion_Factor_Removed:'),
                       encoding='utf-8')
    negative = tmp_path / 'bad_factor.yaml'
    negative.write_text(shipped.replace('x: 0.09797791724417174', 'x: -0.1'), encoding='utf-8')
    assert Read_Conversion_Factor(CONST_BASLER_CONFIG_FILE) is not None
    assert Read_Conversion_Factor(str(without)) is None
    assert Read_Conversion_Factor(str(negative)) is None

    objects = [Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Mask=_Rectangle(200, 100, 0.0))]
    Measure_Objects(objects, None, cv2, np)
    assert objects[0].Measurement is None
    assert Object_Size(objects[0]) == ''

    level, line = run.Scale_Log_Line('no_factor.yaml', None)
    assert level == 'WARNING' and 'will not be measured' in line
    level, line = run.Scale_Log_Line('cfg.yaml', CONST_SCALE)
    assert level == 'INFO' and 'mm/px' in line and '0.1 mm' in line


def test_stored_set_records_the_measurements_and_the_scale_that_produced_them(tmp_path) -> None:
    """
    Description:
        The capture set stores each object's measurement and, once at set level, the conversion
        factor with its units; reading the set back restores both, so the History Info label shows
        the same size. A set written with no scale records null for both.
    """

    measured = Detection_Str(Label='p', Bbox=(0, 0, 1, 1), Sentence='A part.', Segmenter_Score=0.9,
                             Measurement=Measure_Mask(_Rectangle(200, 100, 30.0), CONST_SCALE, cv2, np))
    raw = np.zeros((40, 60, 3), np.uint8)
    writer = Capture_Writer_Cls(str(tmp_path))
    for set_id, scale, objects in (('with', CONST_SCALE, [measured]),
                                   ('without', None, [Detection_Str(Label='p', Bbox=(0, 0, 1, 1))])):
        metadata = Build_Set_Metadata('s', set_id, '2026-09-22T10:00:00', objects, (60, 40), 't', 1,
                                      90, scale=scale)
        writer.Write('s', set_id, raw, raw, raw, 'text', [], [], metadata, 'stamp', cv2, np)

    sets = {cap.Set_Id: cap for cap in Discover_Capture_Sets(str(tmp_path))}
    stored = sets['with']
    assert (stored.Scale.Mm_Per_Px_X, stored.Scale.Mm_Per_Px_Y) == (0.1, 0.1)
    read_back = stored.Objects[0].Measurement
    assert (read_back.Width_Mm, read_back.Height_Mm, read_back.Angle_Deg) == \
        (measured.Measurement.Width_Mm, measured.Measurement.Height_Mm, measured.Measurement.Angle_Deg)
    assert sets['without'].Scale is None and sets['without'].Objects[0].Measurement is None
    import json, glob, os
    record = json.load(open(glob.glob(os.path.join(str(tmp_path), 's', 'with_objects.json'))[0]))
    assert record['conversion_factor']['units'] == CONST_SCALE_UNITS == 'mm/px'


def test_camera_view_draws_the_rotated_rectangle_solid_and_the_axis_box_dashed() -> None:
    """
    Description:
        For a measured, elongated object the annotated view draws the rotated rectangle SOLID and
        the axis-aligned box DASHED (gaps along its edge), both in the verdict colour; a symmetric
        object keeps a single SOLID axis box (no gaps). The label mask draws neither rotated
        rectangle nor dashes.
    """

    colour = Theme.Hex_To_Bgr(Theme.Verdict_Color('OK')[0])
    scene = np.full(CONST_SHAPE + (3,), (70, 150, 70), np.uint8)

    def _Painted(pixels):
        # Anti-aliased lines blend into the scene: a pixel counts as painted when it is nearer the
        # line colour than the scene colour.
        pixels = pixels.astype(float)
        return (np.linalg.norm(pixels - np.array(colour, float), axis=-1)
                < np.linalg.norm(pixels - np.array((70, 150, 70), float), axis=-1))

    def _Top_Edge_Coverage(image, bbox):
        x, y, w, _h = bbox
        return float(np.mean(_Painted(image[y, x + 20:x + w - 20])))

    rod_mask = _Rectangle(400, 60, 25.0)
    ys, xs = np.nonzero(rod_mask)
    rod = Detection_Str(Label='rod', Bbox=(int(xs.min()), int(ys.min()), int(xs.max() - xs.min()),
                                           int(ys.max() - ys.min())), Mask=rod_mask)
    disc_mask = _Disc(60.0)
    ys, xs = np.nonzero(disc_mask)
    disc = Detection_Str(Label='disc', Bbox=(int(xs.min()), int(ys.min()), int(xs.max() - xs.min()),
                                             int(ys.max() - ys.min())), Mask=disc_mask)
    Measure_Objects([rod, disc], CONST_SCALE, cv2, np)

    annotated_rod = Annotate.Draw_Annotated(scene, [rod], cv2, np, verdict_colored=True)
    assert 0.2 < _Top_Edge_Coverage(annotated_rod, rod.Bbox) < 0.9          # dashed: gaps
    for k in range(4):                                                      # solid rotated edges
        (x0, y0), (x1, y1) = rod.Measurement.Box_Points[k], rod.Measurement.Box_Points[(k + 1) % 4]
        samples = [annotated_rod[int(round(y0 + (y1 - y0) * f)), int(round(x0 + (x1 - x0) * f))]
                   for f in np.linspace(0.1, 0.9, 17)]
        assert np.mean(_Painted(np.array(samples))) == 1.0

    annotated_disc = Annotate.Draw_Annotated(scene, [disc], cv2, np, verdict_colored=True)
    assert _Top_Edge_Coverage(annotated_disc, disc.Bbox) == 1.0              # solid axis box

    mask_rod = Annotate.Draw_Label_Mask([rod], scene.shape, cv2, np, verdict_colored=True)
    assert _Top_Edge_Coverage(mask_rod, rod.Bbox) == 1.0                      # mask: unchanged
