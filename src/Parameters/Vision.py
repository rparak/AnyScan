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
# File Name: ../Parameters/Vision.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field

# The units of Scale_Str — millimetres PER PIXEL. The calibration derives the factor from
# square_size_mm over the corner spacing, in px, of boards lying flat on the table, their corners
# undistorted into the application's pixel space (Calibration.Core.Calibrate), so a length in
# pixels TIMES the factor is millimetres. Written beside every stored measurement so a
# number can always be traced to the scale and direction that produced it.
#   Unit [string]
CONST_SCALE_UNITS = 'mm/px'


@dataclass
class Scale_Str(object):
    """
    Description:
        The image scale from the configuration's Calibration.Conversion_Factor: millimetres per
        pixel along the image x and y axes (mm = px * factor, per axis). Read once, through the
        configuration layer, and passed to whatever measures; there is no default — a
        configuration without a factor yields None, and nothing is measured.
    """

    # Millimetres per pixel along the image x (column) and y (row) axes.
    #   Unit [float] (mm/px)
    Mm_Per_Px_X: float = 0.0
    Mm_Per_Px_Y: float = 0.0


@dataclass
class Measurement_Str(object):
    """
    Description:
        One object's physical measurement from the minimum-area rotated rectangle of its mask.
        An ELONGATED (or square-like) object has a width (the long side), a height (the short
        side) and a rotation angle; a rotationally SYMMETRIC one (round, not elongated) has a
        diameter and no angle, because its rectangle's orientation is noise.
    """

    # Whether the object is rotationally symmetric (report a diameter, no angle).
    #   Unit [bool]
    Symmetric: bool = False
    # Width (long side) and height (short side) in mm — None when symmetric.
    #   Unit [float] (mm)
    Width_Mm: tp.Optional[float] = None
    Height_Mm: tp.Optional[float] = None
    # Diameter in mm — only when symmetric. For a round part it is the mean of the rotated
    # rectangle's two sides; for a hexagonal part (Across_Flats) it is the across-flats width,
    # the part's smallest caliper width.
    #   Unit [float] (mm)
    Diameter_Mm: tp.Optional[float] = None
    # Whether Diameter_Mm is an across-flats width (a hexagonal symmetric part, e.g. a nut)
    # rather than a round part's diameter.
    #   Unit [bool]
    Across_Flats: bool = False
    # The strength of the silhouette's 60° periodicity (the third harmonic of its caliper width
    # over 180°, as a fraction of the mean width) — the number Across_Flats rests on. None when
    # not symmetric (it is only evaluated for symmetric parts).
    #   Unit [float]
    Hexagonality: tp.Optional[float] = None
    # The long side's angle from the image +x axis, counter-clockwise AS SEEN ON SCREEN, in
    # [0, 180) — or [0, 90) for a square-like object, whose two sides are interchangeable. None
    # when symmetric.
    #   Unit [float] (degrees)
    Angle_Deg: tp.Optional[float] = None
    # The mask's elongation (square root of the second-moment eigenvalue ratio, >= 1) and extent
    # (contour area / rotated-rectangle area) — the two numbers the symmetric decision rests on.
    #   Unit [float]
    Elongation: float = 1.0
    Extent: float = 1.0
    # The decimal places the sizes are meaningful to, from the scale (one pixel's size).
    #   Unit [int]
    Decimals: int = 1
    # The rotated rectangle's four corners in pixels, for drawing (not stored in the capture set).
    #   Unit [Vector<Tuple<float> 1x2>]
    Box_Points: tp.List[tp.Tuple[float, float]] = field(default_factory=list, repr=False,
                                                          compare=False)


@dataclass
class Detection_Str(object):
    """
    Description:
        The structure of one object the vision pipeline located in a frame.

        Note:
            Order is meaningful: the position of a Detection_Str in the analysis'
            object list is the number the operator sees, both on the box drawn
            over the frame and at the start of the matching line of text. Never
            reorder the list after composing.

    Initialization of the Class:
        Args:
            (1) Label [string]: The distilled noun-phrase label (e.g. 'hex bolt').
            (2) Bbox [Vector<int> 1x4]: The box as (x, y, w, h) in frame pixels.

        Example:
            Initialization:
                # Initialization of the structure.
                Cls = Detection_Str(Label='hex bolt', Bbox=(10, 20, 30, 40))

            Features:
                # Access the fields of the structure.
                Cls.Label; Cls.Bbox; Cls.Detail; Cls.Sentence
    """

    # The distilled noun-phrase label shown at the start of the object's line.
    #   Unit [string]
    Label: str
    # The bounding box as (x, y, w, h) in full-frame pixels.
    #   Unit [Vector<int> 1x4]
    Bbox: tp.Tuple[int, int, int, int]
    # The detector's confidence score, or None when the backend emits none.
    #   Unit [float]
    Confidence: tp.Optional[float] = None
    # Any text read off the object (e.g. a marking), or None.
    #   Unit [string]
    Text: tp.Optional[str] = None
    # The model's full caption, rendered as the object line's second sentence.
    #   Unit [string]
    Detail: str = ''
    # The final composed sentence the panel prints for this object.
    #   Unit [string]
    Sentence: str = ''
    # The instance mask for this object (boolean, frame resolution), or None when
    # the backend is not mask-based. Excluded from repr and equality: it is a large
    # array, and two detections are equal on their described fields, not on pixels.
    #   Unit [Matrix<bool> HxW]
    Mask: tp.Optional[tp.Any] = field(default=None, repr=False, compare=False)
    # The fraction of this object's mask that overlaps the stage-1 change mask
    # (0..1) — the gate that separates a real object from the static scene.
    #   Unit [float]
    Change_Coverage: float = 0.0
    # The segmenter's own confidence for this mask, or None. Kept DISTINCT from
    # Confidence on purpose: Confidence drives the operator 'Low confidence' verdict
    # and is reserved for a detection/classification score, which the segmenter does
    # not emit. See KNOWN_ISSUES.md, 'Verdict confidence branch is dormant'.
    #   Unit [float]
    Segmenter_Score: tp.Optional[float] = None
    # Which of the two fused cues located this object: 'fastsam' (the segmenter only),
    # 'background' (background subtraction only) or 'both'. Set by the fusion stage;
    # it is what the validation harness reports per-cue and never affects the reading.
    #   Unit [string]
    Cue: str = ''
    # The per-object verdict — 'OK' (pass) or 'NOK' (fail) — that drives this object's
    # render colour in BOTH views (Parameters.Theme.Verdict_Color). Defaults to 'OK':
    # classification is not in use yet, so every object is OK and renders in the OK
    # colour. When classification lands it sets this field — a data change, not a
    # rendering change.
    #   Unit [string]
    Verdict: str = 'OK'
    # The alpha/beta-stretched padded crop that was fed to the describer (BGR), kept
    # only so the debug montage can tile exactly what the model received — not
    # re-enhanced downstream. Excluded from repr and equality: it is a large array,
    # and two detections are equal on their described fields, not on pixels.
    #   Unit [Matrix<uint8> hxwx3]
    Enhanced_Crop: tp.Optional[tp.Any] = field(default=None, repr=False, compare=False)
    # The physical measurement from the mask's rotated rectangle, or None when the object has no
    # mask or no scale was configured (never a size computed from a default).
    #   Unit [Measurement_Str(object)]
    Measurement: tp.Optional[Measurement_Str] = None

@dataclass
class Analysis_Str(object):
    """
    Description:
        The structure of a completed scene analysis — everything the Scene
        Understanding panel renders from a single backend call.

        The lead line is NOT a field here: the panel and the descriptions file both
        render it from the shared Reporting.Screen_Header, so there is one source for it.

    Initialization of the Class:
        Args:
            (1) Objects [Vector<Detection_Str(object)>]: The located objects, in order.

        Example:
            Initialization:
                # Initialization of the structure.
                Cls = Analysis_Str(Objects=[], Verdict='Empty')

            Features:
                # Access the fields of the structure.
                Cls.Objects; Cls.Note; Cls.Verdict; Cls.Verdict_Level; Cls.Task
    """

    # The located objects, in the order the operator reads them.
    #   Unit [Vector<Detection_Str(object)>]
    Objects: tp.List[Detection_Str] = field(default_factory=list)
    # A closing note — the empty-scene explanation and its next action, if any.
    #   Unit [string]
    Note: str = ''
    # The wall-clock latency of the analysis, in milliseconds.
    #   Unit [int]
    Latency_Ms: int = 0
    # The verdict-badge wording (e.g. 'Empty', '1 found', 'Low confidence').
    #   Unit [string]
    Verdict: str = 'Idle'
    # The verdict severity that drives the badge colour: 'ok' | 'warn' | 'idle'.
    #   Unit [string]
    Verdict_Level: str = 'idle'
    # The human-readable name of the model task that produced the reading.
    #   Unit [string]
    Task: str = 'detailed caption'
    # The number of raw segmenter masks the frame produced before fusion — a
    # diagnostic (like Latency_Ms) the validation harness reports alongside the
    # object count, never shown to the operator.
    #   Unit [int]
    Raw_Mask_Count: int = 0
    # The one global background description, generated once from the reference frame
    # (not from any crop), shown as the first line of the Screen-Understanding text.
    #   Unit [string]
    Background: str = ''
    # The post-processing audit: one (level, message) record per background strip and
    # substance substitution the composer made, each tagged with the object index. The
    # UI logs these to the session log; the harness prints them, so nothing the
    # composer rewrote is silent. 'level' is 'info' or 'warning'.
    #   Unit [Vector<Tuple<string> 1x2>]
    Audit: tp.List[tp.Tuple[str, str]] = field(default_factory=list)


# The confidence severity thresholds, in PERCENT, defined ONCE here so every place a
# confidence number is shown or logged (the object labels, the frame mean, the session mean,
# the Trends reference lines) reads the same two lines. A number AT or ABOVE the warn line is
# fine; below it is a warning; below the error line it is an error.
#   Unit [int] (percent)
CONST_CONFIDENCE_WARN_BELOW = 80
CONST_CONFIDENCE_ERROR_BELOW = 60
# The hysteresis margin, in percent, for the status-bar session-mean LOG crossings only: after
# a threshold is crossed downward, the mean must climb this far back ABOVE it before a recovery
# is logged, so a value hovering on a line does not emit a log record per analysis.
#   Unit [int] (percent)
CONST_CONFIDENCE_LOG_HYSTERESIS = 2


def Confidence_Severity(percent: tp.Optional[float]) -> str:
    """
    Description:
        The severity band of a confidence percentage, as the LOG-LEVEL string that names it
        ('INFO' above the warn line, 'WARNING' below it, 'ERROR' below the error line). The
        strings are deliberately the log levels so the UI can reuse the one log palette and
        weight ramp for the confidence colouring — colour is not invented per view. An
        unscored value (None) has no severity and reads 'INFO' (the default), though callers
        showing '—' style it as the plain default rather than a measured pass.

    Args:
        (1) percent [float]: The confidence in percent (0..100), or None when unscored.

    Returns:
        (1) parameter [string]: The severity level ('INFO', 'WARNING' or 'ERROR').
    """

    if percent is None:
        return 'INFO'
    if percent < CONST_CONFIDENCE_ERROR_BELOW:
        return 'ERROR'
    if percent < CONST_CONFIDENCE_WARN_BELOW:
        return 'WARNING'
    return 'INFO'
