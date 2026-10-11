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
# The four states an object takes in a catalogue mode (Vision.Utilities.Classify): OK — the catalogue part,
# every check passed; NOK — the catalogue part, a check failed; Unspecified — an area of at least the mode's
# Unspecified_Area_Ratio times the part's, probably several parts together, not judged; Warning — not the
# catalogue part, found and described but not supposed to be there. A mode without a catalogue judges
# nothing and every object keeps the default, OK, drawn in the neutral colour.
#   Unit [Tuple<string>]
CONST_VERDICTS = ('OK', 'NOK', 'Unspecified', 'Warning')


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
    # The height above the table the factors were corrected to, or None when they are the
    # calibration's own (exact in the plane of its flat boards, Calibration.Solved.Board_Height_Mm).
    # A catalogue mode corrects them to its part's top face (Configuration.Core.Scale_At_Height).
    #   Unit [float] (mm)
    Height_Mm: tp.Optional[float] = None


@dataclass
class Dimension_Check_Str(object):
    """
    Description:
        One dimension of an object checked against the catalogue: what was measured, what the
        catalogue expects, and the tolerance — so a failed check can say all three.
    """

    # Which dimension: 'length' or 'width' of the outline.
    #   Unit [string]
    Name: str = ''
    # The measured value, at full precision, the nominal value and the tolerance (nominal ± this).
    #   Unit [float] (mm)
    Measured_Mm: float = 0.0
    Nominal_Mm: float = 0.0
    Tolerance_Mm: float = 0.0
    # Whether the measured value lies within the tolerance (bounds included).
    #   Unit [bool]
    Within: bool = False


@dataclass
class Hole_Str(object):
    """
    Description:
        One hole found on a catalogue part's upright crop (Vision.Utilities.Holes.Hole_Candidates): its
        diameter and its centre, in mm from the crop's top-left corner, the part's outline.
    """

    # The diameter of a circle of the mask's area, and the centre.
    #   Unit [float] (mm)
    Diameter_Mm: float = 0.0
    X_Mm: float = 0.0
    Y_Mm: float = 0.0


@dataclass
class Stain_Str(object):
    """
    Description:
        One stain found on a judged part's side (Vision.Utilities.Stain): its area and its centre, in mm from
        the upright crop's top-left corner.
    """

    # The stain's area, and its centre.
    #   Unit [float] (mm²) / [float] (mm)
    Area_Mm2: float = 0.0
    X_Mm: float = 0.0
    Y_Mm: float = 0.0


@dataclass
class Logo_Letter_Str(object):
    """
    Description:
        One letter of the logo on a judged part (Vision.Utilities.Logo): which word and letter, its best similarity
        to that letter in the references that registered, its contrast there, and whether it is there.
    """

    # The word ('SMART'), the letter ('R'), its best similarity (-1 to 1), its edges' strength against the part's
    # plate at that fit (1 = as strong as the plate's texture), and whether it is there.
    #   Unit [string] / [string] / [float] / [float] / [bool]
    Word: str = ''
    Letter: str = ''
    Similarity: float = 0.0
    Contrast: float = 0.0
    Present: bool = False


@dataclass
class Logo_Result_Str(object):
    """
    Description:
        The logo check on a judged part: the reference with the most matched features ('' when none reached
        Min_Matches — no inscription), its matches, and each letter.
    """

    # The best-matched reference's name, or '' when none registered, and the features matched with it.
    #   Unit [string] / [int]
    Reference: str = ''
    Matches: int = 0
    # Each letter, in reading order; empty when no reference registered.
    #   Unit [Vector<Logo_Letter_Str(object)>]
    Letters: tp.List[Logo_Letter_Str] = field(default_factory=list)


@dataclass
class Hole_Count_Str(object):
    """
    Description:
        How many holes of one catalogue group were found against how many the part has, so a missing or an
        extra hole can be named.
    """

    # The group's name ('corner hole'), the holes found and the holes the catalogue gives.
    #   Unit [string] / [int] / [int]
    Name: str = ''
    Found: int = 0
    Expected: int = 0


@dataclass
class Catalogue_Result_Str(object):
    """
    Description:
        What the catalogue mode found out about one object beyond its dimension checks: how much it
        looks like the catalogue part and which side, its area against the part's, and where it lies —
        the evidence its verdict rests on, kept so the verdict can be explained.
    """

    # The object's highest DINOv2 similarity to the part's reference images (cosine of the class
    # tokens, over both sides and four rotations), the side that scored it ('front' or 'back'), and
    # the similarity at and above which an object is identified as the part (the mode's).
    #   Unit [float] / [string] / [float]
    Similarity: float = 0.0
    Side: str = ''
    Identify_Similarity: float = 0.0
    # What the catalogue calls that side ('machined front'): the side sentence's words.
    #   Unit [string]
    Side_Name: str = ''
    # The object's mask area over the part's nominal area (Length_Mm x Width_Mm), both in mm at the
    # part's top face, and the ratio from which an object is Unspecified (the mode's).
    #   Unit [float] / [float]
    Area_Ratio: float = 0.0
    Unspecified_Area_Ratio: float = 0.0
    # The object's centre's distance from the frame centre, and the distance up to which the size
    # checks were verified on real frames (Vision.Utilities.Classify.CONST_VERIFIED_RADIUS_MM).
    #   Unit [float] (mm)
    Center_Distance_Mm: float = 0.0
    Verified_Radius_Mm: float = 0.0


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
    # Width (long side) and height (short side) in mm, at full precision (never rounded here: the
    # display rounds, Reporting.Core.Object_Size) — None when symmetric.
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

    # The distilled noun-phrase label: the log's 'Object detected: type=...', and the object's line
    # ('A <label>.') when no description remains.
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
    # The model's full caption, rendered as the object's line (Object_Description).
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
    # The segmenter's own confidence for this mask, or None. Kept DISTINCT from
    # Confidence on purpose: Confidence drives the operator 'Low confidence' verdict
    # and is reserved for a detection/classification score, which the segmenter does
    # not emit. See docs/design-decisions.md, 'Verdict's confidence branch stays dormant'.
    #   Unit [float]
    Segmenter_Score: tp.Optional[float] = None
    # Which of the two fused cues located this object: 'fastsam' (the segmenter only),
    # 'background' (background subtraction only) or 'both'. Set by the fusion stage;
    # it is what the validation harness reports per-cue and never affects the reading.
    #   Unit [string]
    Cue: str = ''
    # The per-object verdict, one of CONST_VERDICTS, that drives this object's render colour in
    # BOTH views (Parameters.Theme.Verdict_Color) when the configuration classifies. Defaults to
    # 'OK': a mode without a catalogue judges nothing, and its objects are drawn in the neutral
    # colour whatever this holds. A catalogue mode sets it (Vision.Utilities.Classify).
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
    # The catalogue's dimension checks on this object, in a catalogue mode; empty otherwise, and for
    # an object that is not measured or is round (a round object has no outline to check).
    #   Unit [Vector<Dimension_Check_Str(object)>]
    Dimension_Checks: tp.List[Dimension_Check_Str] = field(default_factory=list)
    # A judged part's hole checks on the side up (catalogue Checks.Holes): each group's count, and each hole's
    # diameter, edge distances and pitch; empty when the side has no holes to check, or the object is not the part.
    #   Unit [Vector<Hole_Count_Str(object)>] / [Vector<Dimension_Check_Str(object)>]
    Hole_Counts: tp.List[Hole_Count_Str] = field(default_factory=list)
    Hole_Checks: tp.List[Dimension_Check_Str] = field(default_factory=list)
    # A judged part's stain and logo checks on the side up (catalogue Checks.Stain, Checks.Logo): None when the
    # side has no such check or the object is not the part; an empty stain list is a side checked and clean.
    #   Unit [Vector<Stain_Str(object)>] / [Logo_Result_Str(object)]
    Stains: tp.Optional[tp.List[Stain_Str]] = None
    Logo: tp.Optional[Logo_Result_Str] = None
    # The catalogue mode's evidence for this object's verdict, or None outside a catalogue mode.
    #   Unit [Catalogue_Result_Str(object)]
    Catalogue: tp.Optional[Catalogue_Result_Str] = None

# The timed stages of one analysis, in the order they run. Their names are what the timing log line
# prints. Everything between the analysis's start and stop that is not one of them (the model check,
# the RGB->BGR conversion, reading the cached reference, the union of the object masks, the labels)
# is the timing's Other_Ms, never dropped.
#   Unit [string]
CONST_STAGE_BACKGROUND = 'background subtraction'
CONST_STAGE_SEGMENTATION = 'segmentation'
CONST_STAGE_SEGMENTATION_POST = 'segmentation post'
CONST_STAGE_FUSION = 'fusion'
CONST_STAGE_CROPS = 'crops'
CONST_STAGE_DESCRIPTIONS = 'descriptions'
CONST_STAGE_BACKGROUND_SENTENCE = 'background sentence'
CONST_STAGE_COMPOSE = 'compose'
#   Unit [Vector<string>]
CONST_TIMING_STAGES = (CONST_STAGE_BACKGROUND, CONST_STAGE_SEGMENTATION, CONST_STAGE_SEGMENTATION_POST,
                       CONST_STAGE_FUSION, CONST_STAGE_CROPS, CONST_STAGE_DESCRIPTIONS,
                       CONST_STAGE_BACKGROUND_SENTENCE, CONST_STAGE_COMPOSE)


@dataclass
class Object_Timing_Str(object):
    """
    Description:
        The time one object took in the description stage: its crop (pad, isolate, enhance) and its
        description, and the describer's token counts when it reports them. Each value is truncated
        to a whole millisecond on its own, so an object's values can sum a few milliseconds below
        the stage totals, which are truncated once over the unrounded sum.
    """

    # The crop's and the description's time.
    #   Unit [int] (ms)
    Crop_Ms: int = 0
    Describe_Ms: int = 0
    # The describer's prompt (image + text) and generated token counts, or None when the describer
    # reports none (the model-free fallback).
    #   Unit [int]
    Input_Tokens: tp.Optional[int] = None
    Output_Tokens: tp.Optional[int] = None


@dataclass
class Timing_Str(object):
    """
    Description:
        Where one analysis's time went. Total_Ms is the analysis's Latency_Ms — the same interval,
        the same value — and the stages plus Other_Ms add up to it exactly: Other_Ms is Total_Ms
        minus the logged stage values, never measured on its own. A negative Other_Ms means a stage
        was counted twice; it is reported, never clamped (Vision.Utilities.Timing.Build_Timing).
        The measurement runs after Latency_Ms stops, so it is carried beside the total, not in it.
    """

    # The analysis's Latency_Ms.
    #   Unit [int] (ms)
    Total_Ms: int = 0
    # Each timed stage (CONST_TIMING_STAGES) and its truncated time, in the order they run.
    #   Unit [Vector<Tuple<string, int>>] (ms)
    Stages: tp.List[tp.Tuple[str, int]] = field(default_factory=list)
    # Total_Ms minus the sum of Stages: the untimed work. Negative only when a stage was double-counted.
    #   Unit [int] (ms)
    Other_Ms: int = 0
    # One entry per object, aligned with Analysis_Str.Objects.
    #   Unit [Vector<Object_Timing_Str(object)>]
    Objects: tp.List[Object_Timing_Str] = field(default_factory=list)
    # The measurement's time, which is outside Total_Ms (it runs after the latency stops).
    #   Unit [int] (ms)
    Measurement_Ms: int = 0
    # A catalogue mode's identification, verdicts and hole checks (DINOv2 on every object, the rule, FastSAM
    # on each judged part's crop), also outside Total_Ms; None outside a catalogue mode.
    #   Unit [int] (ms)
    Identification_Ms: tp.Optional[int] = None
    # Whether this is the first analysis to finish after the models were put in force — see
    # Vision_Pipeline_Cls.Analyze for the exact rule. The warm-up is meant to make it no slower
    # than the next; the flag lets the log show whether it was.
    #   Unit [bool]
    First_After_Load: bool = False


@dataclass
class Model_Load_Str(object):
    """
    Description:
        One model's part in a configuration load: its name and how long it took to load, or None
        when the model was already loaded and kept (never 0, which would read as a load).
    """

    # The model's file or directory name.
    #   Unit [string]
    Name: str = ''
    # The load time, or None when the model was kept, not reloaded.
    #   Unit [float] (s)
    Seconds: tp.Optional[float] = None


@dataclass
class Load_Timing_Str(object):
    """
    Description:
        Where a configuration load's time went: each model's load (or that it was kept), and the
        warm-up's three parts. A warm-up part is None when it did not run: the warm-up stopped at a
        failure (Warm_Up_Error), or there is no describer to write the background sentence.
    """

    # The segmenter, the identifier (a catalogue mode only), then the describer (none for the model-free
    # fallback).
    #   Unit [Vector<Model_Load_Str(object)>]
    Models: tp.List[Model_Load_Str] = field(default_factory=list)
    # The warm-up: reading the reference, FastSAM's first pass on it, and the background sentence.
    #   Unit [float] (s)
    Reference_S: tp.Optional[float] = None
    First_Segmentation_S: tp.Optional[float] = None
    Background_Sentence_S: tp.Optional[float] = None
    # A catalogue mode's warm-up also embeds the item's reference images (DINOv2's first pass).
    #   Unit [float] (s)
    Reference_Images_S: tp.Optional[float] = None
    # Why the warm-up stopped, or None when it completed.
    #   Unit [string]
    Warm_Up_Error: tp.Optional[str] = None


@dataclass
class Heatmap_Str(object):
    """
    Description:
        A per-pixel map for the Camera View's heatmap, with everything its legend shows, from whatever
        stage computed it. The view only renders this (Vision.Utilities.Heatmap, then the viewport), so
        another source — a similarity to a reference part — fills the same structure and changes no UI.
        Shown only, never saved: not in the capture set, not in History.

    Initialization of the Class:
        Args:
            (1) Values [Matrix<number> HxW]: The per-pixel values.

        Example:
            Initialization:
                # Initialization of the structure.
                Cls = Heatmap_Str(Values=gray, High=128.0, Title='Difference from the reference')

            Features:
                # Access the fields of the structure.
                Cls.Values; Cls.Low; Cls.High; Cls.Title; Cls.Unit; Cls.Marks
    """

    # The per-pixel values, the frame's size.
    #   Unit [Matrix<number> HxW]
    Values: tp.Any = None
    # The fixed scale the colours span: Low maps to the map's first colour, High (and above) to its last.
    #   Unit [float] (in Unit)
    Low: float = 0.0
    High: float = 1.0
    # What the values are, for the legend ('Difference from the reference', 'grey level').
    #   Unit [string]
    Title: str = ''
    Unit: str = ''
    # Values marked on the legend, each with its label (the threshold applied: 'Otsu 51').
    #   Unit [Vector<Tuple<float, string>>]
    Marks: tp.List[tp.Tuple[float, str]] = field(default_factory=list)


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
    # The human-readable name of what produced the reading — the describer's task
    # (Vision.Describers.*.Task_Label, or the fallback's). Empty by default: a reading nothing has
    # produced names no model.
    #   Unit [string]
    Task: str = ''
    # The number of raw segmenter masks the frame produced before fusion — a
    # diagnostic (like Latency_Ms) the validation harness reports alongside the
    # object count, never shown to the operator.
    #   Unit [int]
    Raw_Mask_Count: int = 0
    # The one global background description, generated once from the reference frame
    # (not from any crop), shown as the first line of the Screen-Understanding text.
    #   Unit [string]
    Background: str = ''
    # The pipeline's audit records, as (level, message): today only the background sentence's, a
    # warning when the neutral fallback sentence stood in for the model's. The UI logs these to the
    # session log; the harness prints them, so nothing put in the model's place is silent. 'level'
    # is 'info' or 'warning'.
    #   Unit [Vector<Tuple<string> 1x2>]
    Audit: tp.List[tp.Tuple[str, str]] = field(default_factory=list)
    # Where the time went (Timing_Str), or None when the backend does not time its stages.
    #   Unit [Timing_Str(object)]
    Timing: tp.Optional[Timing_Str] = None
    # The Camera View's heatmap (Heatmap_Str), or None when the backend computes none.
    #   Unit [Heatmap_Str(object)]
    Heatmap: tp.Optional[Heatmap_Str] = None


# The hysteresis margin, in percent, for the status-bar session-mean LOG crossings only: after
# a threshold is crossed downward, the mean must climb this far back ABOVE it before a recovery
# is logged, so a value hovering on a line does not emit a log record per analysis.
#   Unit [int] (percent)
CONST_CONFIDENCE_LOG_HYSTERESIS = 2


@dataclass
class Confidence_Thresholds_Str(object):
    """
    Description:
        The confidence severity thresholds, in PERCENT, from the configuration's 'Confidence'
        block — ONE pair that every place a confidence number is shown or logged reads (the object
        labels, the frame mean, the session mean and its log crossings, the Trends reference
        lines). A number AT or ABOVE the warn line is fine; below it is a warning; below the error
        line it is an error.

        Note:
            They are a VIEWING preference, applied to whatever is on screen: a past capture set
            shown in History is coloured by the thresholds in force now, not the ones in force
            when it was captured (docs/design-decisions.md).
    """

    # Below this a confidence is a warning.
    #   Unit [int] (percent)
    Warn_Below: int = 80
    # Below this a confidence is an error.
    #   Unit [int] (percent)
    Error_Below: int = 60


def Confidence_Severity(percent: tp.Optional[float],
                        Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> str:
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
        (2) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: The thresholds in force.

    Returns:
        (1) parameter [string]: The severity level ('INFO', 'WARNING' or 'ERROR').
    """

    if percent is None:
        return 'INFO'
    if percent < Confidence_Thresholds_Str.Error_Below:
        return 'ERROR'
    if percent < Confidence_Thresholds_Str.Warn_Below:
        return 'WARNING'
    return 'INFO'
