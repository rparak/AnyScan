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
# File Name: ../UI/Capture.py
## =========================================================================== ##

# System (Default)
import os
import json
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data Classes)
from dataclasses import dataclass, field
# Custom Lib.: AnyScan domain — the detection structure the metadata is built from
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Scale_Str, Measurement_Str, Feature_Str, Dimension_Check_Str, CONST_SCALE_UNITS

"""
Description:
    Initialization of constants.

    The per-analysis capture writer: on every completed analysis it writes a set of
    artefacts into the current session's directory under logger/captures/<session_id>/ —

        <set_id>_raw.png            the captured frame, UNDISTORTED (optional, keep_raw) — 'raw'
                                    means unannotated; the lens distortion is already removed
        <set_id>_distorted.png      the same frame BEFORE undistortion (keep_raw, when the
                                    camera undistorts) — the form a future calibration can
                                    re-undistort
        <set_id>_distorted.json     its sidecar: marks it distorted and records the exact
                                    undistortion that produced <set_id>_raw.png from it
        <set_id>_annotated.png      the annotated image
        <set_id>_mask.png           the label mask
        <set_id>_thumb.jpg          a small thumbnail of the annotated image (for History)
        <set_id>_understanding.txt  the Scene-Understanding text (shared formatter)
        <set_id>.txt                the YOLO box region records, one line per object
        <set_id>_seg.txt            the YOLO segmentation polygons, one line per object
        <set_id>_objects.json       the machine-readable per-object + set-level metadata

    — each named so a set is obviously one analysis. This module also READS a set back
    (Read_Capture_Set) and discovers every set across sessions (Discover_Capture_Sets) into
    plain structures, Qt-free, so the History view renders them without a second reader and
    the reading is testable without a UI. The '_objects.json' is the ONE machine-readable
    record; no view parses '_understanding.txt', which is prose for humans. The images carry
    NO provenance band:
    they are the image and nothing else (a band would corrupt the raw frame as a record of
    what the camera saw), and the set id already lives in the filename and in every related
    log line. The '_understanding.txt' keeps a one-line stamp header. A classes.txt inside
    the session directory lists the region ids in order.

    Retention is enforced ON WRITE and counts sets GLOBALLY across sessions: the oldest
    are evicted first regardless of which session they belong to (so one long session
    cannot starve the bound while a dozen short ones pile up), and a session directory is
    removed once it holds no more sets.

    Qt-free: OpenCV and NumPy are injected. It does file I/O and may raise on a full disk
    or a permission failure; the caller wraps the call so a write failure logs an ERROR
    and never breaks the analysis. The directory is 'captures', not 'tmp': the files
    persist within the retention bound.
"""
# How many analysis sets to keep across ALL sessions. The oldest are evicted on write, so
# the store is bounded: at ~12 MB/set (raw ~4 MB, distorted ~4 MB, annotated ~4 MB, the rest
# negligible) this caps it near 600 MB. Turning the raw frames off (CONST_CAPTURE_KEEP_RAW)
# drops both frames — about two thirds of the per-set size.
#   Unit [int]
CONST_CAPTURE_RETENTION_SETS = 50

# Whether the captured frames are written — the undistorted '_raw.png' and, when the camera
# undistorts, the '_distorted.png' original. On by default; they are the largest artefacts and
# the ones reconstructible from nothing, so turning them off is the lever for a longer history
# on the same disk.
#   Unit [bool]
CONST_CAPTURE_KEEP_RAW = True

# The raw-frame suffix (separated so it can be skipped), and every artefact suffix of one
# set — longest first, so a set id is recovered from a filename by stripping the first
# suffix that matches ('_understanding.txt' before the bare YOLO '.txt').
#   Unit [Vector<string>]
CONST_CAPTURE_RAW_SUFFIX = '_raw.png'
CONST_CAPTURE_DISTORTED_SUFFIX = '_distorted.png'
CONST_CAPTURE_DISTORTED_RECORD_SUFFIX = '_distorted.json'
CONST_CAPTURE_SUFFIXES = ('_raw.png', '_distorted.png', '_distorted.json', '_annotated.png',
                          '_mask.png', '_thumb.jpg', '_understanding.txt', '_objects.json',
                          '_seg.txt', '.txt')

# The thumbnail's long-edge target (px). A grid of History cards decodes one thumbnail each;
# a fifty-card grid of full 4 MB PNGs would be unusable, so a small JPEG is written once at
# capture time. The long edge is bounded to this; a smaller image is written as-is.
#   Unit [int]
CONST_CAPTURE_THUMB_LONG_EDGE = 320

# The metadata and thumbnail artefact suffixes, named once.
#   Unit [string]
CONST_CAPTURE_THUMB_SUFFIX = '_thumb.jpg'
CONST_CAPTURE_OBJECTS_SUFFIX = '_objects.json'
CONST_CAPTURE_SEG_SUFFIX = '_seg.txt'
CONST_CAPTURE_UNDERSTANDING_SUFFIX = '_understanding.txt'
CONST_CAPTURE_ANNOTATED_SUFFIX = '_annotated.png'
CONST_CAPTURE_MASK_SUFFIX = '_mask.png'

# The classes file beside the captures. Its header says, in the file itself, that the ids
# are per-frame object indices and not classes — the warning travels with the data.
#   Unit [string]
CONST_CAPTURE_CLASSES_FILE = 'classes.txt'
CONST_CAPTURE_CLASSES_HEADER = (
    '# NOT class labels. Each id is a per-frame object INDEX: object N in the Scene\n'
    '# Understanding text is id N-1, a handle for finding and hand-correcting that\n'
    '# object. The SAME id means a DIFFERENT part in every frame, so the YOLO <set>.txt\n'
    '# files must NOT be used for training as-is (see docs/design-decisions.md). They\n'
    '# become a dataset only once ids are reassigned by real class.\n')


@dataclass
class Capture_Object_Str:
    """
    Description:
        One object of a capture set, as read back from '_objects.json' — the machine-readable
        record the History view renders, distinct from the human prose in '_understanding.txt'.
    """

    # The 0-based object index (its position in the ordered list, the number on the box).
    Index: int = 0
    # The bounding box in frame pixels as (x, y, w, h).
    Bbox: tp.Tuple[int, int, int, int] = (0, 0, 0, 0)
    # The confidence percentage, or None when the object carries no score.
    Confidence: tp.Optional[int] = None
    # Which fused cue located it ('fastsam' | 'background' | 'both').
    Cue: str = ''
    # The per-object verdict (one of Parameters.Vision.CONST_VERDICTS: 'OK' | 'NOK' | 'Warning'); an older set's
    # 'Unspecified' is read as a Warning (__Read_State).
    Verdict: str = 'OK'
    # A Warning's kind as recorded ('warning_kind', Parameters.Vision.CONST_WARNING_KINDS), kept as written; 'unspecified'
    # for an object a set written before the three states recorded as Unspecified, whose cause it did not record; ''
    # for any other verdict and for a Warning in a set written before kinds were recorded.
    Warning_Kind: str = ''
    # The composed description sentence (the shared formatter's output for this object).
    Description: str = ''
    # The stored measurement (sizes in mm, angle), or None when the object was not measured.
    Measurement: tp.Optional[Measurement_Str] = None
    # A judged part's features (holes, stains), its Parts; empty for any other object and for a set written
    # before 2026-10-11, which has none. A set's other kinds of part are read as stored (Kind, Name, box).
    Parts: tp.List[Feature_Str] = field(default_factory=list)


@dataclass
class Capture_Set_Str:
    """
    Description:
        One capture set as read back from disk — the set-level fields, its objects, the paths
        of the images that exist, and whether it is partial (an analysis that failed, or was
        stopped at close, and left only a raw frame). This is the plain structure the History view renders; building it does no
        Qt work, so it is testable without a UI.
    """

    # The session the set belongs to (its subdirectory name; matches the log lines).
    Session_Id: str = ''
    # The APPLICATION-run id the set was written in (stable across camera connections). History
    # lists only the current run's sets by matching it. Empty for a set written before run ids
    # (or a partial set), which no current run matches, so it simply does not show.
    Run_Id: str = ''
    # The set identifier (<timestamp>_<n>), the filename stem.
    Set_Id: str = ''
    # The capture timestamp (ISO 8601) from the metadata, empty for a partial set.
    Timestamp: str = ''
    # The frame dimensions in pixels.
    Frame_Width: int = 0
    Frame_Height: int = 0
    # The model task, the analysis latency and the frame mean confidence (or None).
    Task: str = ''
    Inference_Ms: int = 0
    Frame_Mean_Confidence: tp.Optional[int] = None
    # The one global background sentence (for the Scene-Understanding lead), empty when absent.
    Background: str = ''
    # The scale (mm/px) the set's measurements were computed with, or None when it had none.
    Scale: tp.Optional[Scale_Str] = None
    # Whether classification was enabled when this set was written — so History renders the
    # verdict UI (filter, outline colour) per set, not by the current config. False when absent.
    Classification: bool = False
    # The configuration file the set was analysed under — the mode and hardware, so a History
    # holding sets from several configurations says which is which. Empty for a set written
    # before configurations were recorded.
    Configuration: str = ''
    # The station file and the calibration file the set was analysed under (their file names). Empty for a set
    # written before 2026-10-13, when they were first recorded.
    Station: str = ''
    Calibration: str = ''
    # The empty-surface reference the frame was differenced against. Empty for an older set.
    Background_Reference: str = ''
    # The camera, lens and lighting the set was captured with ({} for an older set).
    Hardware: tp.Dict[str, str] = field(default_factory=dict)
    # The sensor window the camera read back ({'resolution': [w, h], 'offset': [x, y]}), or None
    # for a set from a saved frame or written before sets recorded it.
    Window: tp.Optional[tp.Dict[str, tp.List[int]]] = None
    # The undistortion applied to the frame (the '_distorted.json' record: the calibration file,
    # K, the coefficients, ...), or None when the camera did not undistort.
    Undistortion: tp.Optional[tp.Dict[str, tp.Any]] = None
    # The objects, in order.
    Objects: tp.List[Capture_Object_Str] = field(default_factory=list)
    # The absolute paths of the artefacts that exist (None when absent).
    Raw_Path: tp.Optional[str] = None
    Annotated_Path: tp.Optional[str] = None
    Mask_Path: tp.Optional[str] = None
    Thumb_Path: tp.Optional[str] = None
    # True when the set has no '_objects.json' — a failed or stopped analysis (raw frame only) or
    # an unreadable metadata file. Note carries the reason, and the set is shown, never hidden.
    Partial: bool = False
    Note: str = ''
    # The newest file mtime in the set, for sorting newest-first.
    Mtime: float = 0.0

    def States(self) -> tp.Set[str]:
        """
        Description:
            The states its objects took: their verdicts, 'OK', 'NOK' or 'Warning' (any kind, an older set's Unspecified
            included); empty for a partial set.

        Returns:
            (1) parameter [Set<string>]: The states.
        """

        return {obj.Verdict for obj in self.Objects}

    def Worst_State(self) -> str:
        """
        Description:
            The worst state among its objects, in the status badges' order: NOK, then Warning, then OK (also for a set
            with no objects).

        Returns:
            (1) parameter [string]: The state ('OK', 'NOK' or 'Warning').
        """

        states = self.States()
        return next((state for state in ('NOK', 'Warning') if state in states), 'OK')


def Set_Id_From_Name(name: str) -> tp.Optional[str]:
    """
    Description:
        The set id a capture filename belongs to — the name with its artefact suffix stripped —
        or None when the name is not a capture artefact. Suffixes are tried longest-specific
        first, so '<set>_understanding.txt', '<set>_seg.txt' and '<set>_objects.json' are
        matched before the bare YOLO '<set>.txt'. The single source both the writer and the
        reader use, so they agree on what one set's files are.

    Args:
        (1) name [string]: The file name.

    Returns:
        (1) parameter [string]: The set id, or None.
    """

    if name == CONST_CAPTURE_CLASSES_FILE:               # the per-session classes file is not a set
        return None
    for suffix in CONST_CAPTURE_SUFFIXES:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return None


def Distorted_Frame_Record(set_id: str, undistortion: tp.Dict[str, tp.Any]) -> tp.Dict[str, tp.Any]:
    """
    Description:
        The '<set>_distorted.json' sidecar of a distorted frame: says in so many words that the
        frame still carries the lens distortion (so no reader mistakes it for '<set>_raw.png'),
        names its undistorted counterpart, and records the exact undistortion that produced that
        counterpart — the configuration, K, the coefficients, alpha and the new camera matrix —
        so the pair can be checked, and the distorted frame re-undistorted under any later
        calibration.

    Args:
        (1) set_id [string]: The set identifier.
        (2) undistortion [Dict]: The camera's undistortion record (Last_Undistortion).

    Returns:
        (1) parameter [Dict]: The JSON-ready sidecar.
    """

    return {'frame': set_id + CONST_CAPTURE_DISTORTED_SUFFIX, 'distorted': True,
            'note': ('Lens distortion NOT removed. Processed exactly as the application\'s '
                     'frames (the same blur and colour step) but not undistorted. '
                     + set_id + CONST_CAPTURE_RAW_SUFFIX + ' is this frame after the '
                     'undistortion below.'),
            'undistorted_counterpart': set_id + CONST_CAPTURE_RAW_SUFFIX,
            'undistortion': undistortion}


def Measurement_Record(measurement: tp.Optional[Measurement_Str]) -> tp.Optional[tp.Dict[str, tp.Any]]:
    """
    Description:
        One object's measurement as its '_objects.json' record: sizes in millimetres as computed
        (full precision — the displayed decimals are the UI's, Reporting.Core.Object_Size), the
        angle in degrees (screen counter-clockwise from +x; null when symmetric), the symmetric
        flag and the two numbers it rests on, and whether the diameter is across flats and the
        hexagonality that decides it (null when not symmetric). None when the object was not
        measured. (Records written before sizes kept full precision also carry a 'decimals' key
        and sizes rounded to it; the reader ignores the key.)

    Args:
        (1) measurement [Measurement_Str(object) or None]: The measurement.

    Returns:
        (1) parameter [Dict or None]: The JSON-ready record, or None.
    """

    if measurement is None:
        return None
    return {'symmetric': measurement.Symmetric, 'width_mm': measurement.Width_Mm,
            'height_mm': measurement.Height_Mm, 'diameter_mm': measurement.Diameter_Mm,
            'across_flats': measurement.Across_Flats, 'hexagonality': measurement.Hexagonality,
            'angle_deg': measurement.Angle_Deg, 'elongation': measurement.Elongation,
            'extent': measurement.Extent}


def __Record_Number(record: tp.Dict[str, tp.Any], key: str) -> tp.Optional[float]:
    """
    Description:
        A numeric field of a stored record, or None when it is missing or not a number (a bool
        is not accepted as a number).

    Args:
        (1) record [Dict]: The record.
        (2) key [string]: The field name.

    Returns:
        (1) parameter [float or None]: The value, or None.
    """

    value = record.get(key)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def __Read_Measurement(record: tp.Any) -> tp.Optional[Measurement_Str]:
    """
    Description:
        A stored measurement record read back defensively; anything missing or malformed reads as
        not measured (None), never as a made-up size.

    Args:
        (1) record [Dict or None]: The 'measurement' record.

    Returns:
        (1) parameter [Measurement_Str(object) or None]: The measurement, or None.
    """

    if not isinstance(record, dict):
        return None
    measurement = Measurement_Str(Symmetric=bool(record.get('symmetric', False)),
                                  Width_Mm=__Record_Number(record, 'width_mm'),
                                  Height_Mm=__Record_Number(record, 'height_mm'),
                                  Diameter_Mm=__Record_Number(record, 'diameter_mm'),
                                  Across_Flats=record.get('across_flats') is True,
                                  Hexagonality=__Record_Number(record, 'hexagonality'),
                                  Angle_Deg=__Record_Number(record, 'angle_deg'),
                                  Elongation=__Record_Number(record, 'elongation') or 1.0,
                                  Extent=__Record_Number(record, 'extent') or 1.0)
    complete = (measurement.Diameter_Mm is not None if measurement.Symmetric
                else measurement.Width_Mm is not None and measurement.Height_Mm is not None)
    return measurement if complete else None


def Part_Record(Feature_Str: Feature_Str) -> tp.Dict[str, tp.Any]:
    """
    Description:
        One feature of a judged part as its '_objects.json' record (the object's 'parts', an additive field since
        2026-10-11): its part number, kind, name, whether it passed and was found, its box in frame pixels, its
        checks in millimetres, a stain's area, and its check's score.

    Args:
        (1) Feature_Str [Feature_Str(object)]: The feature.

    Returns:
        (1) parameter [Dict]: The record.
    """

    feature = Feature_Str
    return {'part': feature.Part, 'kind': feature.Kind, 'name': feature.Name, 'passed': bool(feature.Passed),
            'found': bool(feature.Found), 'corners': [[round(float(x), 2), round(float(y), 2)] for x, y in feature.Corners],
            'checks': [{'name': check.Name, 'measured_mm': check.Measured_Mm, 'nominal_mm': check.Nominal_Mm,
                        'tolerance_mm': check.Tolerance_Mm, 'within': bool(check.Within)} for check in feature.Checks],
            'area_mm2': feature.Area_Mm2, 'score': feature.Score}


def __Read_Parts(records: tp.Any) -> tp.List[Feature_Str]:
    """
    Description:
        An object's stored parts read back defensively: absent (a set written before parts were recorded) or
        malformed reads as none, a malformed part is skipped, and nothing is made up. A key this version no longer
        writes (a word part's expected_text and read_text, until 2026-10-13) is ignored; the part itself is kept.

    Args:
        (1) records [Vector<Dict> or None]: The 'parts' records.

    Returns:
        (1) parameter [Vector<Feature_Str(object)>]: The parts.
    """

    parts = []
    for record in records if isinstance(records, list) else []:
        try:
            parts.append(Feature_Str(
                Part=str(record['part']), Kind=str(record['kind']), Name=str(record['name']),
                Passed=bool(record['passed']), Found=bool(record.get('found', True)),
                Corners=[(float(x), float(y)) for x, y in record.get('corners', [])],
                Checks=[Dimension_Check_Str(Name=str(c['name']), Measured_Mm=float(c['measured_mm']),
                                            Nominal_Mm=float(c['nominal_mm']), Tolerance_Mm=float(c['tolerance_mm']),
                                            Within=bool(c['within'])) for c in record.get('checks', [])],
                Area_Mm2=float(record.get('area_mm2') or 0.0),
                Score=None if record.get('score') is None else float(record['score'])))
        except (KeyError, TypeError, ValueError):
            continue
    return parts


def __Read_State(record: tp.Dict[str, tp.Any]) -> tp.Tuple[str, str]:
    """
    Description:
        An object record's state in the three states, without loss: its verdict and, for a Warning, its kind as
        written ('warning_kind', any kind, a later version's too); an older set's 'Unspecified' (written before
        2026-10-16, its cause not recorded) as a Warning of kind 'unspecified'; a Warning without a kind (written before
        kinds were recorded) as a plain Warning.

    Args:
        (1) record [Dict]: One object's record from '_objects.json'.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (the verdict, the Warning's kind or '').
    """

    verdict = str(record.get('verdict', 'OK'))
    if verdict == 'Unspecified':
        return 'Warning', 'unspecified'
    kind = record.get('warning_kind')
    return verdict, (kind if verdict == 'Warning' and isinstance(kind, str) else '')


def Build_Set_Metadata(session_id: str, set_id: str, timestamp: str,
                       objects: tp.List[Detection_Str], size: tp.Tuple[int, int], task: str,
                       inference_ms: int, frame_mean_confidence: tp.Optional[int],
                       background: str = '', classification: bool = False,
                       run_id: str = '', *, scale: tp.Optional[Scale_Str],
                       configuration: str, station: str, calibration: str, background_reference: str,
                       hardware: tp.Dict[str, str],
                       window: tp.Optional[tp.Dict[str, tp.List[int]]]) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Build the machine-readable metadata for one set from the SAME detection list that
        drives every other artefact — so the JSON, the images and the YOLO files describe
        identical objects in identical order, and no view need parse the prose. Per object it
        records the index, the pixel bounding box, the confidence percentage (or None), the
        cue, the verdict (a Warning with its kind, 'warning_kind', Parameters.Vision.CONST_WARNING_KINDS) and the composed
        description; set-wide it records the session, set id, timestamp, frame dimensions, model task, inference
        time and the frame mean confidence.

    Args:
        (1) session_id [string]: The session the set belongs to.
        (2) set_id [string]: The set identifier.
        (3) timestamp [string]: The capture timestamp (ISO 8601).
        (4) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (5) size [Vector<int> 1x2]: The frame size as (width, height).
        (6) task [string]: The model task that produced the reading.
        (7) inference_ms [int]: The analysis latency in milliseconds.
        (8) frame_mean_confidence [int]: The frame mean confidence percentage, or None.
        (9) background [string]: The one global background sentence, so a reader can render the
                                 full Scene-Understanding lead from the JSON alone (never the
                                 prose '_understanding.txt').
        (10) classification [bool]: Whether classification was enabled when the set was written,
                                    so History knows how each set's colours were baked and can
                                    show or hide the verdict UI per set rather than assuming the
                                    current config applies to every set.
        (11) run_id [string]: The APPLICATION-run identifier, generated once at startup and stable
                              across every camera connection in that run. History lists only the
                              sets of the current run by matching it, so earlier runs' sets stay on
                              disk (retention still manages them) but are not shown. Distinct from
                              session_id, which is one camera connection.
        (12) scale [Scale_Str(object) or None]: REQUIRED, keyword-only: the scale the objects'
                                                measurements were computed with, recorded ONCE at
                                                set level with its units ('conversion_factor'), so a
                                                stored size can always be traced back to the scale
                                                that produced it; None (no factor) is recorded as
                                                null and no object carries a measurement.
        (13) configuration [string]: REQUIRED, keyword-only: the name of the configuration file
                                     the set was analysed under, beside the classification flag,
                                     so sets from different configurations stay distinguishable.
        (14 - 15) station, calibration [string]: REQUIRED, keyword-only: the file names of the station
                                                 the configuration named and of the calibration that
                                                 station named. Calibrations are kept side by side and
                                                 switched by one line, so the conversion factor alone
                                                 does not say which one measured the set.
        (16) background_reference [string]: REQUIRED, keyword-only: the empty-surface reference the
                                            frame was differenced against (repository-relative),
                                            so a stored analysis can be traced to it.
        (17) hardware [Dict<string, string>]: REQUIRED, keyword-only: the camera, lens and lighting
                                              the configuration names (Hardware_Record) — what
                                              photographed the set and what lit it.
        (18) window [Dict or None]: REQUIRED, keyword-only: the sensor window the camera read back
                                    on connect ({'resolution': [w, h], 'offset': [x, y]}, the camera's
                                    Window), or None for a frame from no camera (a saved file). The
                                    offset is not in the pixels, so without this record the window a
                                    set was captured at would be a guess.

    Returns:
        (1) parameter [Dict]: The metadata, ready to serialise as '_objects.json'.
    """

    records = []
    for index, det in enumerate(objects):
        confidence = (int(round(100.0 * det.Segmenter_Score))
                      if det.Segmenter_Score is not None else None)
        records.append({'index': index, 'bbox': [int(v) for v in det.Bbox],
                        'confidence': confidence, 'cue': det.Cue, 'verdict': det.Verdict,
                        **({'warning_kind': det.Catalogue.Warning_Kind}
                           if det.Verdict == 'Warning' and det.Catalogue is not None and det.Catalogue.Warning_Kind
                           else {}),
                        'description': det.Sentence,
                        'measurement': Measurement_Record(det.Measurement),
                        'parts': [Part_Record(feature) for feature in det.Features]})
    return {'session_id': session_id, 'run_id': run_id, 'set_id': set_id, 'timestamp': timestamp,
            'frame_width': int(size[0]), 'frame_height': int(size[1]), 'task': task,
            'inference_ms': int(inference_ms), 'frame_mean_confidence': frame_mean_confidence,
            'background': background, 'classification': bool(classification),
            'configuration': configuration, 'station': station, 'calibration': calibration,
            'background_reference': background_reference,
            'hardware': dict(hardware),
            'window': None if window is None else {'resolution': [int(v) for v in window['resolution']],
                                                   'offset': [int(v) for v in window['offset']]},
            'conversion_factor': (None if scale is None else
                                  {'x': scale.Mm_Per_Px_X, 'y': scale.Mm_Per_Px_Y,
                                   'units': CONST_SCALE_UNITS}),
            'objects': records}


def __Existing_Path(session_dir: str, set_id: str, suffix: str) -> tp.Optional[str]:
    """
    Description:
        The absolute path of one of a set's artefacts when it exists, else None.

    Args:
        (1) session_dir [string]: The session directory.
        (2) set_id [string]: The set id.
        (3) suffix [string]: The artefact suffix.

    Returns:
        (1) parameter [string or None]: The path, or None when the file is absent.
    """

    path = os.path.join(session_dir, set_id + suffix)
    return path if os.path.isfile(path) else None


def __Newest_Mtime(session_dir: str, set_id: str) -> float:
    """
    Description:
        The newest modification time across a set's files, for newest-first sorting; 0.0 when
        none can be read.

    Args:
        (1) session_dir [string]: The session directory.
        (2) set_id [string]: The set id.

    Returns:
        (1) parameter [float]: The newest mtime, or 0.0.
    """

    newest = 0.0
    try:
        names = os.listdir(session_dir)
    except OSError:
        return newest
    for name in names:
        if Set_Id_From_Name(name) != set_id:
            continue
        try:
            newest = max(newest, os.path.getmtime(os.path.join(session_dir, name)))
        except OSError:
            continue
    return newest


def __Partial_Note(session_dir: str, set_id: str, reason: str) -> str:
    """
    Description:
        The note shown for a partial set: the reason, and the body of '_understanding.txt' when
        it exists (the failure note the writer left), so the operator sees why the analysis
        failed and can find the set id in the log.

    Args:
        (1) session_dir [string]: The session directory.
        (2) set_id [string]: The set id.
        (3) reason [string]: The fallback reason when no note file is present.

    Returns:
        (1) parameter [string]: The note text.
    """

    path = os.path.join(session_dir, set_id + CONST_CAPTURE_UNDERSTANDING_SUFFIX)
    try:
        with open(path, 'r') as handle:
            # Drop the leading '# stamp …' comment line; the rest is the failure note.
            body = ''.join(line for line in handle if not line.startswith('#')).strip()
        if body:
            return body
    except OSError:
        pass
    return reason


def Read_Capture_Set(session_dir: str, session_id: str, set_id: str) -> Capture_Set_Str:
    """
    Description:
        Read one capture set into a plain structure. When '_objects.json' is present and valid,
        the set-level fields and the objects are populated from it; the image paths that exist
        are recorded. When the metadata is absent (a failed or stopped analysis left only a raw frame) or
        cannot be read/parsed, the set is marked partial with a note — never dropped, because a
        failed set is the one an operator most wants to see. A missing or malformed field never
        raises: every value is read defensively. This is the one reader of a set's '_objects.json'
        and '_distorted.json' — the formats this module writes; nothing else parses them.

    Args:
        (1) session_dir [string]: The session directory holding the set's files.
        (2) session_id [string]: The session id (its directory name).
        (3) set_id [string]: The set identifier.

    Returns:
        (1) parameter [Capture_Set_Str(object)]: The read set.
    """

    cap = Capture_Set_Str(
        Session_Id=session_id, Set_Id=set_id,
        Raw_Path=__Existing_Path(session_dir, set_id, CONST_CAPTURE_RAW_SUFFIX),
        Annotated_Path=__Existing_Path(session_dir, set_id, CONST_CAPTURE_ANNOTATED_SUFFIX),
        Mask_Path=__Existing_Path(session_dir, set_id, CONST_CAPTURE_MASK_SUFFIX),
        Thumb_Path=__Existing_Path(session_dir, set_id, CONST_CAPTURE_THUMB_SUFFIX),
        Mtime=__Newest_Mtime(session_dir, set_id))

    objects_path = __Existing_Path(session_dir, set_id, CONST_CAPTURE_OBJECTS_SUFFIX)
    if objects_path is None:
        cap.Partial = True
        cap.Note = __Partial_Note(session_dir, set_id,
                                  'The analysis failed; only the raw frame was captured.')
        return cap
    try:
        with open(objects_path, 'r') as handle:
            data = json.load(handle)
        cap.Timestamp = str(data.get('timestamp', ''))
        cap.Frame_Width = int(data.get('frame_width', 0))
        cap.Frame_Height = int(data.get('frame_height', 0))
        cap.Task = str(data.get('task', ''))
        cap.Inference_Ms = int(data.get('inference_ms', 0))
        mean = data.get('frame_mean_confidence', None)
        cap.Frame_Mean_Confidence = int(mean) if mean is not None else None
        cap.Background = str(data.get('background', ''))
        cap.Classification = bool(data.get('classification', False))
        cap.Configuration = str(data.get('configuration', ''))
        cap.Station = str(data.get('station', ''))
        cap.Calibration = str(data.get('calibration', ''))
        cap.Background_Reference = str(data.get('background_reference', ''))
        cap.Hardware = {str(k): str(v) for k, v in (data.get('hardware') or {}).items()}
        window = data.get('window')
        if isinstance(window, dict):
            cap.Window = {'resolution': [int(v) for v in window['resolution']][:2],
                          'offset': [int(v) for v in window['offset']][:2]}
        cap.Run_Id = str(data.get('run_id', ''))
        cap.Objects = [Capture_Object_Str(
            Index=int(record.get('index', i)),
            Bbox=tuple(int(v) for v in record.get('bbox', (0, 0, 0, 0))),
            Confidence=(int(record['confidence']) if record.get('confidence') is not None
                        else None),
            Cue=str(record.get('cue', '')), Verdict=__Read_State(record)[0], Warning_Kind=__Read_State(record)[1],
            Description=str(record.get('description', '')),
            Measurement=__Read_Measurement(record.get('measurement')),
            Parts=__Read_Parts(record.get('parts')))
            for i, record in enumerate(data.get('objects', []))]
        factor = data.get('conversion_factor')
        if isinstance(factor, dict) and factor.get('units') == CONST_SCALE_UNITS:
            cap.Scale = Scale_Str(Mm_Per_Px_X=float(factor['x']), Mm_Per_Px_Y=float(factor['y']))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        # A malformed or unreadable metadata file: show the set as partial rather than crash.
        cap.Partial = True
        cap.Objects = []
        cap.Note = ('The set metadata could not be read (a malformed %s%s).'
                    % (set_id, CONST_CAPTURE_OBJECTS_SUFFIX))
        return cap
    # The undistortion record beside a distorted frame: None when there is none, or it is unreadable
    # (a reader of this record must then treat the frame as not undistorted by a known lens model).
    record_path = __Existing_Path(session_dir, set_id, CONST_CAPTURE_DISTORTED_RECORD_SUFFIX)
    if record_path is not None:
        try:
            with open(record_path, 'r') as handle:
                undistortion = json.load(handle).get('undistortion')
            cap.Undistortion = undistortion if isinstance(undistortion, dict) else None
        except (OSError, ValueError, AttributeError):
            cap.Undistortion = None
    return cap


def Discover_Capture_Sets(captures_root: str) -> tp.List[Capture_Set_Str]:
    """
    Description:
        Every capture set under the captures root, across all session directories, read into
        plain structures and ordered NEWEST-FIRST by the newest file each set holds. A missing
        root, an unreadable directory or a stray file is skipped, never raised, so the History
        view always gets a list.

    Args:
        (1) captures_root [string]: The captures root (per-session subdirectories live here).

    Returns:
        (1) parameter [Vector<Capture_Set_Str>]: The sets, newest first.
    """

    sets = []
    try:
        session_ids = os.listdir(captures_root)
    except OSError:
        return sets
    for session_id in session_ids:
        session_dir = os.path.join(captures_root, session_id)
        if not os.path.isdir(session_dir):
            continue
        seen = set()
        try:
            names = os.listdir(session_dir)
        except OSError:
            continue
        for name in names:
            set_id = Set_Id_From_Name(name)
            if set_id is None or set_id in seen:
                continue
            seen.add(set_id)
            sets.append(Read_Capture_Set(session_dir, session_id, set_id))
    sets.sort(key=lambda cap: cap.Mtime, reverse=True)   # newest first
    return sets


class Capture_Writer_Cls(object):
    """
    Description:
        Writes and retention-bounds the per-analysis capture sets, in per-session
        subdirectories of a captures root.

    Initialization of the Class:
        Args:
            (1) captures_dir [string]: The captures root (per-session subdirs live here).
            (2) retention_sets [int]: How many newest sets to keep across all sessions (>= 1).
            (3) keep_raw [bool]: Whether to write the raw frame artefact.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Capture_Writer_Cls('logger/captures', 50, True)

            Features:
                # Write one set into a session; returns (evicted ids, created dir or None).
                evicted, created = Cls.Write(session_id, set_id, raw, annotated, mask, text,
                                             yolo_lines, seg_lines, metadata, stamp, cv2, np,
                                             distorted_bgr=distorted, undistortion=undistortion)
    """

    def __init__(self, captures_dir: str, retention_sets: int = CONST_CAPTURE_RETENTION_SETS,
                 keep_raw: bool = CONST_CAPTURE_KEEP_RAW) -> None:
        # << PRIVATE >> #
        self.__dir = captures_dir
        self.__retention = max(1, int(retention_sets))
        self.__keep_raw = bool(keep_raw)

    @property
    def Retention(self) -> int:
        """
        Description:
            The number of newest sets kept across all sessions (the retention bound).

        Returns:
            (1) parameter [int]: The retention bound.
        """

        return self.__retention

    def Write(self, session_id: str, set_id: str, raw_bgr: tp.Any, annotated_bgr: tp.Any,
              mask_bgr: tp.Any, understanding_text: str, yolo_lines: tp.List[str],
              seg_lines: tp.List[str], metadata: tp.Dict[str, tp.Any], stamp: str,
              cv2: tp.Any, np: tp.Any, *, distorted_bgr: tp.Any,
              undistortion: tp.Optional[tp.Dict[str, tp.Any]]) -> tp.Tuple[tp.List[str], tp.Optional[str]]:
        """
        Description:
            Write one analysis set into the session's directory — the annotated image, the
            label mask, a small thumbnail of the annotated image, the Scene-Understanding
            '.txt', the YOLO box '<set>.txt', the YOLO segmentation '<set>_seg.txt', the
            machine-readable '<set>_objects.json' and (when keep_raw) the raw frame — refresh
            the classes file, then enforce the global retention bound. Raises on a write failure
            (the caller logs it and continues); eviction is best-effort and never raises.

        Args:
            (1) session_id [string]: The session the set belongs to (its subdirectory).
            (2) set_id [string]: The set identifier (<timestamp>_<n>), the filename stem.
            (3) raw_bgr [Matrix<uint8> HxWx3]: The captured frame, undistorted (BGR).
            (4) annotated_bgr [Matrix<uint8> HxWx3]: The annotated image (BGR).
            (5) mask_bgr [Matrix<uint8> HxWx3]: The label mask (BGR).
            (6) understanding_text [string]: The Scene-Understanding text (shared formatter).
            (7) yolo_lines [Vector<string>]: The YOLO box lines, one per object, in order.
            (8) seg_lines [Vector<string>]: The YOLO segmentation lines, one per object.
            (9) metadata [Dict]: The set metadata (Build_Set_Metadata), written as JSON.
            (10) stamp [string]: The provenance stamp for the '_understanding.txt' header.
            (11) cv2 [module]: The OpenCV module, injected by the caller.
            (12) np [module]: The NumPy module, injected by the caller. Unused here, and kept on
                 purpose: every writer and renderer takes the injected (cv2, np) pair, and dropping
                 it would change 17 call sites for no behaviour change (cleanup audit 2026-09-25).
            (13) distorted_bgr [Matrix<uint8> HxWx3 or None]: REQUIRED, keyword-only: the frame
                 BEFORE undistortion (BGR), or None when the camera does not undistort.
            (14) undistortion [Dict or None]: REQUIRED, keyword-only: the undistortion that
                 turned it into raw_bgr (the camera's Last_Undistortion), or None.

        Returns:
            (1) parameter [Tuple]: (evicted set ids oldest-first, the session id if its
                                   directory was created by this write else None).
        """

        session_dir, created = self.__Ensure_Session_Dir(session_id)
        if self.__keep_raw:
            self.__Write_Png(session_dir, set_id + CONST_CAPTURE_RAW_SUFFIX, raw_bgr, cv2)
            self.__Write_Distorted(session_dir, set_id, distorted_bgr, undistortion, cv2)
        self.__Write_Png(session_dir, set_id + CONST_CAPTURE_ANNOTATED_SUFFIX, annotated_bgr, cv2)
        self.__Write_Png(session_dir, set_id + CONST_CAPTURE_MASK_SUFFIX, mask_bgr, cv2)
        # The thumbnail is generated once here (cheap) from the annotated image, so History
        # never decodes a full PNG to fill a grid cell.
        self.__Write_Thumbnail(session_dir, set_id + CONST_CAPTURE_THUMB_SUFFIX, annotated_bgr, cv2)
        # The Scene-Understanding text carries the stamp as a leading comment; the YOLO
        # files are bare region records (their provenance is the set id in the filename).
        self.__Write_Text(session_dir, set_id + CONST_CAPTURE_UNDERSTANDING_SUFFIX,
                          '# ' + stamp + '\n' + understanding_text + '\n')
        self.__Write_Text(session_dir, set_id + '.txt',
                          ''.join(line + '\n' for line in yolo_lines))
        self.__Write_Text(session_dir, set_id + CONST_CAPTURE_SEG_SUFFIX,
                          ''.join(line + '\n' for line in seg_lines))
        # The one machine-readable record of the set; no view parses the prose '.txt'.
        self.__Write_Text(session_dir, set_id + CONST_CAPTURE_OBJECTS_SUFFIX,
                          json.dumps(metadata, indent=2, ensure_ascii=False) + '\n')
        self.__Refresh_Classes(session_dir, len(yolo_lines))
        return self.__Evict(), (session_id if created else None)

    def Write_Partial(self, session_id: str, set_id: str, raw_bgr: tp.Any, note: str,
                      stamp: str, cv2: tp.Any, np: tp.Any, *, distorted_bgr: tp.Any,
                      undistortion: tp.Optional[tp.Dict[str, tp.Any]]) -> tp.Tuple[tp.List[str], tp.Optional[str]]:
        """
        Description:
            Write a PARTIAL set into the session's directory for an analysis that FAILED or was
            STOPPED at close — the raw frame (when kept) and a '.txt' note saying why and that only
            the raw frame is present — so a crash leaves evidence (the frame that caused it)
            rather than nothing. The annotated image, mask and YOLO records do not exist,
            because they are produced only after a successful analysis. Retention is
            enforced as for a full set.

        Args:
            (1) session_id [string]: The session the set belongs to (its subdirectory).
            (2) set_id [string]: The set identifier (filename stem).
            (3) raw_bgr [Matrix<uint8> HxWx3]: The captured frame, undistorted (BGR).
            (4) note [string]: The failure note written into the '_understanding.txt'.
            (5) stamp [string]: The provenance stamp.
            (6) cv2 [module]: The OpenCV module, injected by the caller.
            (7) np [module]: The NumPy module, injected by the caller. Unused here, and kept on
                purpose, like Write's: the (cv2, np) pair is injected together everywhere.
            (8) distorted_bgr [Matrix<uint8> HxWx3 or None]: REQUIRED, keyword-only: the frame
                BEFORE undistortion (BGR), or None — as for Write.
            (9) undistortion [Dict or None]: REQUIRED, keyword-only: its undistortion, or None.

        Returns:
            (1) parameter [Tuple]: (evicted set ids, the session id if its directory was
                                   created by this write else None).
        """

        session_dir, created = self.__Ensure_Session_Dir(session_id)
        if self.__keep_raw:
            self.__Write_Png(session_dir, set_id + CONST_CAPTURE_RAW_SUFFIX, raw_bgr, cv2)
            self.__Write_Distorted(session_dir, set_id, distorted_bgr, undistortion, cv2)
        self.__Write_Text(session_dir, set_id + CONST_CAPTURE_UNDERSTANDING_SUFFIX, '# ' + stamp + '\n'
                          + note + '\n')
        return self.__Evict(), (session_id if created else None)

    def __Write_Distorted(self, session_dir: str, set_id: str, distorted_bgr: tp.Any,
                          undistortion: tp.Optional[tp.Dict[str, tp.Any]], cv2: tp.Any) -> None:
        """
        Description:
            Write the frame as it was BEFORE undistortion, with its sidecar, when the camera
            provided both; nothing when it did not (a saved frame is not undistorted, so it has
            no separate original). The frame and its sidecar are written together or not at all:
            a distorted PNG without the record saying so is the ambiguity the sidecar prevents.

        Args:
            (1) session_dir [string]: The session directory.
            (2) set_id [string]: The set identifier.
            (3) distorted_bgr [Matrix<uint8> HxWx3 or None]: The distorted frame (BGR).
            (4) undistortion [Dict or None]: The undistortion record.
            (5) cv2 [module]: The OpenCV module.
        """

        if distorted_bgr is None or undistortion is None:
            return
        self.__Write_Text(session_dir, set_id + CONST_CAPTURE_DISTORTED_RECORD_SUFFIX,
                          json.dumps(Distorted_Frame_Record(set_id, undistortion), indent=2,
                                     ensure_ascii=False) + '\n')
        self.__Write_Png(session_dir, set_id + CONST_CAPTURE_DISTORTED_SUFFIX, distorted_bgr, cv2)

    def __Ensure_Session_Dir(self, session_id: str) -> tp.Tuple[str, bool]:
        """
        Description:
            The session's capture directory, creating it if absent — so the caller can log
            an INFO line the first time a session writes a capture.

        Args:
            (1) session_id [string]: The session identifier.

        Returns:
            (1) parameter [Tuple]: (the directory path, True when it was created here).
        """

        session_dir = os.path.join(self.__dir, session_id)
        created = not os.path.isdir(session_dir)
        os.makedirs(session_dir, exist_ok=True)
        return session_dir, created

    def __Write_Png(self, session_dir: str, name: str, image_bgr: tp.Any, cv2: tp.Any) -> None:
        """
        Description:
            Write one PNG — the image and nothing else, no provenance band — raising if the
            write does not land (a full disk or a permission failure returns False from
            cv2.imwrite, which must not pass as a success).

        Args:
            (1) session_dir [string]: The session directory to write into.
            (2) name [string]: The file name.
            (3) image_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (4) cv2 [module]: The OpenCV module, injected by the caller.
        """

        path = os.path.join(session_dir, name)
        if not cv2.imwrite(path, image_bgr):
            raise OSError('cv2.imwrite reported failure for %s' % path)

    def __Write_Thumbnail(self, session_dir: str, name: str, image_bgr: tp.Any,
                          cv2: tp.Any) -> None:
        """
        Description:
            Write a small thumbnail of the annotated image — its long edge bounded to
            CONST_CAPTURE_THUMB_LONG_EDGE, area-resampled for a clean downscale — so History
            fills its grid from tiny JPEGs, not full PNGs. A smaller source is written as-is.
            Raises if the write does not land, like the other artefacts.

        Args:
            (1) session_dir [string]: The session directory to write into.
            (2) name [string]: The file name.
            (3) image_bgr [Matrix<uint8> HxWx3]: The annotated image (BGR).
            (4) cv2 [module]: The OpenCV module, injected by the caller.
        """

        height, width = image_bgr.shape[:2]
        long_edge = max(height, width)
        if long_edge > CONST_CAPTURE_THUMB_LONG_EDGE:
            scale = CONST_CAPTURE_THUMB_LONG_EDGE / float(long_edge)
            thumb = cv2.resize(image_bgr, (max(1, int(round(width * scale))),
                                           max(1, int(round(height * scale)))),
                               interpolation=cv2.INTER_AREA)
        else:
            thumb = image_bgr
        path = os.path.join(session_dir, name)
        if not cv2.imwrite(path, thumb):
            raise OSError('cv2.imwrite reported failure for %s' % path)

    def __Write_Text(self, session_dir: str, name: str, content: str) -> None:
        """
        Description:
            Write one text artefact of a set.

        Args:
            (1) session_dir [string]: The session directory to write into.
            (2) name [string]: The file name.
            (3) content [string]: The full file content.
        """

        with open(os.path.join(session_dir, name), 'w') as handle:
            handle.write(content)

    def __Refresh_Classes(self, session_dir: str, count: int) -> None:
        """
        Description:
            Ensure the session's classes file lists at least `count` region ids
            (0..count-1) under its header — the ids grow monotonically as frames with more
            objects arrive. The file lives INSIDE the session directory, so each capture
            session is self-describing; its header, in the file, warns the ids are
            per-frame indices, not classes.

        Args:
            (1) session_dir [string]: The session directory to write the classes file into.
            (2) count [int]: The number of objects in the frame just written.
        """

        path = os.path.join(session_dir, CONST_CAPTURE_CLASSES_FILE)
        have = 0
        if os.path.isfile(path):
            with open(path, 'r') as handle:
                have = sum(1 for line in handle if line.strip() and not line.startswith('#'))
        if count <= have:
            return
        with open(path, 'w') as handle:
            handle.write(CONST_CAPTURE_CLASSES_HEADER)
            handle.write(''.join('%d\n' % i for i in range(count)))

    def __Evict(self) -> tp.List[str]:
        """
        Description:
            Delete the oldest sets beyond the retention bound, counted GLOBALLY across all
            session directories, newest kept. Sets are ordered by their newest file's
            modification time, so eviction is oldest-first regardless of the id's text.
            A session directory left with no sets is removed. Best-effort: a delete that
            fails is skipped, never raised.

        Returns:
            (1) parameter [Vector<string>]: The evicted set ids, oldest first.
        """

        sets = self.__Sets()
        if len(sets) <= self.__retention:
            return []
        evicted = []
        for set_id, _mtime, session_dir, files in sets[:len(sets) - self.__retention]:
            for name in files:
                try:
                    os.remove(os.path.join(session_dir, name))
                except OSError:
                    pass
            evicted.append(set_id)
            self.__Remove_If_Empty(session_dir)
        return evicted

    def __Remove_If_Empty(self, session_dir: str) -> None:
        """
        Description:
            Remove a session directory once it holds no more capture sets — the per-session
            classes file, being the only non-set artefact, is removed with it so an empty
            session leaves nothing behind. Best-effort.

        Args:
            (1) session_dir [string]: The session directory.
        """

        try:
            if any(self.__Set_Id(name) is not None for name in os.listdir(session_dir)):
                return
            for name in os.listdir(session_dir):            # only the classes file remains, if any
                os.remove(os.path.join(session_dir, name))
            os.rmdir(session_dir)
        except OSError:
            pass

    def __Sets(self) -> tp.List[tp.Tuple[str, float, str, tp.List[str]]]:
        """
        Description:
            Every capture set across all session directories as (set_id, newest_mtime,
            session_dir, files), ordered oldest-first by the newest file each set holds.

        Returns:
            (1) parameter [Vector<Tuple>]: The sets, oldest first.
        """

        grouped = {}
        for session_id in self.__Session_Dirs():
            session_dir = os.path.join(self.__dir, session_id)
            try:
                names = os.listdir(session_dir)
            except OSError:
                # Removed since the root was listed (another instance emptied it): nothing to evict.
                continue
            for name in names:
                set_id = self.__Set_Id(name)
                if set_id is None:
                    continue
                try:
                    mtime = os.path.getmtime(os.path.join(session_dir, name))
                except OSError:
                    continue
                entry = grouped.setdefault((session_id, set_id), [0.0, session_dir, []])
                entry[0] = max(entry[0], mtime)
                entry[2].append(name)
        sets = [(set_id, mtime, session_dir, files)
                for (_session, set_id), (mtime, session_dir, files) in grouped.items()]
        sets.sort(key=lambda item: item[1])
        return sets

    def __Session_Dirs(self) -> tp.List[str]:
        """
        Description:
            The session subdirectory names under the captures root (the classes file and
            any stray file are skipped).

        Returns:
            (1) parameter [Vector<string>]: The session directory names.
        """

        try:
            names = os.listdir(self.__dir)
        except OSError:
            return []
        return [name for name in names if os.path.isdir(os.path.join(self.__dir, name))]

    def __Set_Id(self, name: str) -> tp.Optional[str]:
        """
        Description:
            The set id a capture filename belongs to — delegated to the module-level
            Set_Id_From_Name, so the writer and the reader strip suffixes by one rule.

        Args:
            (1) name [string]: The file name.

        Returns:
            (1) parameter [string]: The set id, or None.
        """

        return Set_Id_From_Name(name)
