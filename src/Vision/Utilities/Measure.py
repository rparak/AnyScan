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
# File Name: ../Vision/Utilities/Measure.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the detection, scale and measurement structures
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Scale_Str, Measurement_Str, CONST_SCALE_UNITS

"""
Description:
    Initialization of constants.

    Object measurement: the minimum-area rotated rectangle of each object's mask, its sides
    converted to millimetres through the configured scale (mm/px, per axis), and its rotation.
    Qt-free, with OpenCV and NumPy injected, so the application and the validation harness
    measure identically.

    Rotationally symmetric parts (washers, nuts, round heads) have no meaningful orientation:
    minAreaRect still assigns one, it changes between frames on noise alone, and a drawn
    rectangle would appear to spin on a part that has not moved. Such an object is reported as a
    diameter with no angle. 'Symmetric' needs BOTH a low elongation AND a round silhouette — a
    square is just as un-elongated as a disc, but its sides are real edges that minAreaRect finds
    reliably, so it keeps A x B and an angle (folded to [0, 90), since its two sides are
    interchangeable and would otherwise swap on noise).

    A symmetric part's diameter follows one of two stated conventions. A ROUND part reports the
    mean of its rotated rectangle's two sides. A HEXAGONAL part (a nut, a hex head — its
    silhouette's width repeats every 60°) reports ACROSS FLATS, its smallest caliper width: the
    number a nut is specified by, where a mean would sit ~7.5 % from both across-flats and
    across-corners, which differ by 15 %.
"""

# The elongation below which an object is not elongated: the square root of the ratio of its
# mask's second-moment eigenvalues (the axis-length ratio of the equivalent ellipse, 1.0 for a
# disc or a square). Measured on the seven Data/Camera frames: round parts 1.008-1.031, the least
# elongated real part 1.498 (the plates in 002-005), Image_001's elongated parts 1.755-4.35. 1.15
# sits five times the round parts' noise above 1.0 and far below any elongated part.
#   Unit [float]
CONST_MEASURE_SYMMETRIC_ELONGATION = 1.15
# The extent (contour area / rotated-rectangle area) at or above which a non-elongated object is
# square-like, not round: a disc is pi/4 = 0.785 in theory, measured 0.81-0.85 on the round parts;
# the square plate in Image_006/007 measured 0.98-0.99.
#   Unit [float]
CONST_MEASURE_SQUARE_EXTENT = 0.92
# The smallest mask (pixels) that is measured at all; below it the rectangle is noise.
#   Unit [int]
CONST_MEASURE_MIN_AREA_PX = 16
# The hexagonality (the third harmonic of a symmetric part's caliper width over 180° — its 60°
# periodicity — as a fraction of the mean width) at or above which the part is hexagonal and its
# size is reported across flats. A hexagon's across-corners width is 2/sqrt(3) = 1.155 x its
# across-flats, so the mean diameter of a nut sits ~7.5 % from either standard number; a nut is
# specified by its across-flats (the wrench size). Measured: the washers in Image_001 0.0016 and
# 0.0026, the nuts 0.0204 and 0.0254 (their corners are rounded; an ideal hexagon is 0.038-0.057
# down to 20 px across), pixelated ideal discs <= 0.0021 down to 20 px across. 0.0075 sits near the
# geometric mean of the closest washer and nut, ~2.7x from each. Only the 60° harmonic is used:
# a 4-fold one is not evidence of a polygon here — washer 1's own mask is a slightly squared circle
# (4-fold 0.012) — and square parts are already told apart by their extent.
#   Unit [float]
CONST_MEASURE_HEX_HARMONIC = 0.0075
# Caliper directions sampled over 180° for the width profile (0.5° apart; the across-flats minimum
# found on that grid is within 1e-5 of the true one).
#   Unit [int]
CONST_MEASURE_WIDTH_SAMPLES = 360


def Measure_Decimals(scale: Scale_Str) -> int:
    """
    Description:
        The decimal places a size is meaningful to, from the scale: one pixel's size sets the
        resolution, so 0.098 mm/px gives 1 decimal (0.1 mm), 0.5 mm/px gives 0 (whole mm), 0.01
        mm/px gives 2. Printing more is false precision — and the mask edge is itself uncertain by
        about a pixel, so this is already the most the measurement can claim.

    Args:
        (1) scale [Scale_Str(object)]: The image scale.

    Returns:
        (1) parameter [int]: The decimal places (>= 0).
    """

    coarsest = max(scale.Mm_Per_Px_X, scale.Mm_Per_Px_Y)
    return max(0, int(math.floor(-math.log10(coarsest))))


def Scale_Log_Line(config_name: str, scale: tp.Optional[Scale_Str]) -> tp.Tuple[str, str]:
    """
    Description:
        The configuration-loaded line for the measurement scale: at INFO, the scale in mm/px and
        the precision sizes are shown to; at WARNING, when the configuration's calibration has no
        Conversion_Factor — objects are then not measured at all, and this line says why, instead
        of a size silently computed from a default.

    Args:
        (1) config_name [string]: The configuration file's name.
        (2) scale [Scale_Str(object) or None]: Its scale, or None.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (level 'INFO' or 'WARNING', the log line).
    """

    if scale is None:
        return ('WARNING', "Configuration '%s' has no calibration Conversion_Factor; objects "
                           "will not be measured." % config_name)
    decimals = Measure_Decimals(scale)
    return ('INFO', 'Measuring objects at %.5f x %.5f %s (sizes to %s mm).'
            % (scale.Mm_Per_Px_X, scale.Mm_Per_Px_Y, CONST_SCALE_UNITS,
               '%.*f' % (decimals, 10.0 ** -decimals)))


def __Edge_Mm(vector: tp.Tuple[float, float], scale: Scale_Str) -> tp.Tuple[float, float]:
    """
    Description:
        A pixel-space vector in millimetres, each component through its own axis' factor.

    Args:
        (1) vector [Vector<float> 1x2]: The (dx, dy) vector in pixels.
        (2) scale [Scale_Str(object)]: The image scale.

    Returns:
        (1) parameter [Vector<float> 1x2]: The (dx, dy) vector in millimetres.
    """

    return (vector[0] * scale.Mm_Per_Px_X, vector[1] * scale.Mm_Per_Px_Y)


def __Screen_Angle(vector_mm: tp.Tuple[float, float], period: float) -> float:
    """
    Description:
        The angle of a direction from the image +x axis, COUNTER-CLOCKWISE AS SEEN ON SCREEN (image
        y points down, so its sign is flipped), folded into [0, period) and rounded to 0.1°. This
        is the project's own convention, computed from the rectangle's corners — independent of
        minAreaRect's angle, whose convention has changed between OpenCV versions.

    Args:
        (1) vector_mm [Vector<float> 1x2]: The direction (dx, dy) in image axes.
        (2) period [float]: 180 for a rectangle (a line has no head), 90 for a square.

    Returns:
        (1) parameter [float]: The angle in degrees, in [0, period).
    """

    angle = round(math.degrees(math.atan2(-vector_mm[1], vector_mm[0])) % period, 1)
    return 0.0 if angle >= period else angle


def __Width_Profile(points: tp.Any, cv2: tp.Any, np: tp.Any) -> tp.Tuple[tp.Any, tp.Any]:
    """
    Description:
        The caliper (Feret) width of a silhouette in each of CONST_MEASURE_WIDTH_SAMPLES directions
        over 180°, from its convex hull, in pixels — lengthened by one pixel like the rectangle's
        sides, because contour points sit on pixel centres.

    Args:
        (1) points [Matrix<int> Nx1x2]: The outer contour points.
        (2) cv2 [module]: The OpenCV module.
        (3) np [module]: The NumPy module.

    Returns:
        (1) parameter [Tuple<Vector<float>, Vector<float>>]: The directions (radians, image axes)
                                                             and the width in each (pixels).
    """

    hull = cv2.convexHull(points).reshape(-1, 2).astype(np.float64)
    theta = np.arange(CONST_MEASURE_WIDTH_SAMPLES) * (math.pi / CONST_MEASURE_WIDTH_SAMPLES)
    projection = hull @ np.stack([np.cos(theta), np.sin(theta)])
    return theta, projection.max(axis=0) - projection.min(axis=0) + 1.0


def Measure_Mask(mask: tp.Any, scale: Scale_Str, cv2: tp.Any, np: tp.Any) -> tp.Optional[Measurement_Str]:
    """
    Description:
        Measure one object from its mask. The rotated rectangle comes from the outer contour
        points; contour points sit on pixel CENTRES, so each side is lengthened by one pixel (a
        filled 200 px block spans 199 px between its boundary pixel centres). Each side is then
        converted through the per-axis factor. Elongation (second moments) and extent (area over
        rectangle area) decide the symmetric case: a symmetric object reports no angle and a
        diameter — across flats (its smallest caliper width) when its silhouette is hexagonal, the
        mean of the two sides when it is round; otherwise the long side is the width, the short side the
        height, and the angle is the long side's, folded to [0, 90) for a square-like object.

    Args:
        (1) mask [Matrix<bool> HxW]: The object's mask.
        (2) scale [Scale_Str(object)]: The image scale (mm/px).
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.

    Returns:
        (1) parameter [Measurement_Str(object) or None]: The measurement, or None for an empty or
                                                         tiny mask.
    """

    binary = mask.astype(np.uint8)
    if int(binary.sum()) < CONST_MEASURE_MIN_AREA_PX:
        return None
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    points = np.vstack(contours)
    center, (w_px, h_px), angle_cv = cv2.minAreaRect(points)
    corners = cv2.boxPoints((center, (w_px + 1.0, h_px + 1.0), angle_cv))

    # The two sides as pixel vectors (lengthened to pixel edges above), then in millimetres.
    side_a = __Edge_Mm((corners[1][0] - corners[0][0], corners[1][1] - corners[0][1]), scale)
    side_b = __Edge_Mm((corners[2][0] - corners[1][0], corners[2][1] - corners[1][1]), scale)
    length_a, length_b = math.hypot(*side_a), math.hypot(*side_b)
    long_side, long_mm, short_mm = ((side_a, length_a, length_b) if length_a >= length_b
                                    else (side_b, length_b, length_a))

    moments = cv2.moments(binary, binaryImage=True)
    covariance = np.array([[moments['mu20'], moments['mu11']],
                           [moments['mu11'], moments['mu02']]]) / moments['m00']
    major, minor = sorted(np.linalg.eigvalsh(covariance), reverse=True)
    elongation = min(1000.0, math.sqrt(major / minor)) if minor > 0.0 else 1000.0
    rect_area = max(1e-9, w_px * h_px)
    extent = float(sum(cv2.contourArea(c) for c in contours)) / rect_area

    decimals = Measure_Decimals(scale)
    not_elongated = elongation < CONST_MEASURE_SYMMETRIC_ELONGATION
    measurement = Measurement_Str(Elongation=round(elongation, 3), Extent=round(extent, 3),
                                  Decimals=decimals,
                                  Box_Points=[(float(x), float(y)) for x, y in corners])
    if not_elongated and extent < CONST_MEASURE_SQUARE_EXTENT:
        measurement.Symmetric = True
        theta, widths = __Width_Profile(points, cv2, np)
        harmonics = np.abs(np.fft.rfft(widths)) * (2.0 / len(widths))
        measurement.Hexagonality = round(float(harmonics[3] / widths.mean()), 4)
        if measurement.Hexagonality >= CONST_MEASURE_HEX_HARMONIC:
            # Across flats: the smallest caliper width, converted through the factor along its
            # own direction (exact for equal x/y factors; the configured two differ by 0.004 %).
            i = int(np.argmin(widths))
            mm_per_px = math.hypot(scale.Mm_Per_Px_X * math.cos(theta[i]),
                                   scale.Mm_Per_Px_Y * math.sin(theta[i]))
            measurement.Across_Flats = True
            measurement.Diameter_Mm = round(float(widths[i]) * mm_per_px, decimals)
        else:
            measurement.Diameter_Mm = round((long_mm + short_mm) / 2.0, decimals)
        return measurement
    measurement.Width_Mm = round(long_mm, decimals)
    measurement.Height_Mm = round(short_mm, decimals)
    measurement.Angle_Deg = __Screen_Angle(long_side, 90.0 if not_elongated else 180.0)
    return measurement


def Measure_Objects(objects: tp.List[Detection_Str], scale: tp.Optional[Scale_Str],
                    cv2: tp.Any, np: tp.Any) -> None:
    """
    Description:
        Measure every object that has a mask, in place (det.Measurement). With no scale — the
        configuration has no Conversion_Factor — nothing is measured: every Measurement stays None
        and no size is ever computed from a default. The caller warns once, at configuration load.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) scale [Scale_Str(object) or None]: The image scale, or None when not configured.
        (3) cv2 [module]: The OpenCV module, injected by the caller.
        (4) np [module]: The NumPy module, injected by the caller.
    """

    for det in objects:
        det.Measurement = (Measure_Mask(det.Mask, scale, cv2, np)
                           if scale is not None and det.Mask is not None else None)
