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
# File Name: ../test/integration/test_pipeline.py
## =========================================================================== ##

# System (Default)
import os
import collections
import dataclasses
# Glob (Unix-style pathname pattern expansion)
import glob
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the camera and vision backends, the result structure
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls
#   ../Configuration/Core — the shipped configuration the pipeline runs with
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE, CONST_CONFIG_DIR
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
#   ../Reporting/Core
from Reporting.Core import Screen_Header

"""
Description:
    End-to-end pipeline integration tests: acquire a frame -> detect -> describe ->
    compose the report, exercising the modules together across their seams. The
    default test is hermetic (a File_Camera_Cls source and a fake backend, no camera
    and no weights). A second test runs the same flow through the real FastSAM (on the
    CPU) and Gemma whenever the weights exist. When they do not, it skips — visibly, naming
    the missing paths — so a fresh clone is not broken; under --runslow, which asks for the
    real path, missing weights fail instead, so that request can never come back green.
"""

# Two rectangles drawn onto the reference to synthesize a frame with real objects.
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]
# The pinned test set's inventory (Evaluation.Frames = Data/Images/Test): how many parts are on each
# frame, counted by looking at the frame — NOT what the pipeline reports, so a wrong count fails.
# Proposed by eye and confirmed by the owner (2026-10-11). The frames are the 2026-10-09 capture
# session's _raw.png files (the application's undistorted frames), numbered from 055: 001-013 belonged
# to the set before (All/, recoverable from 1061966) and 014-054 to the same scenes' _distorted.png files
# (recoverable from 1580e92), which are other images, so no name is reused. Each count was carried
# across from its _distorted scene, paired by content: the frame here equals, pixel for pixel, the
# application's undistortion of the frame it replaces. The blue double triangle, a terminal strip with
# its screws, the flanged bushing and the slit lattice bracket are one part each.
#   Unit [Dict<string, int>]
CONST_INVENTORY = {
    'Image_055.png': 1,     # machined aluminium plate
    'Image_056.png': 1,     # dark rusted plate
    'Image_057.png': 1,     # maze plate
    'Image_058.png': 1,     # SMART FACTORY plate
    'Image_059.png': 6,     # flanged bushing, rust-stained plate, cap screw, washer, terminal strip, hex nut
    'Image_060.png': 7,     # bushing, maze plate, cap screw, washer, terminal strip, triangle, hex nut
    'Image_061.png': 7,     # the same, with the SMART FACTORY plate
    'Image_062.png': 7,     # the same, with the dark rusted plate
    'Image_063.png': 8,     # red block, aluminium plate, cap screw, terminal strip, triangle, hex nut, washer, lattice bracket
    'Image_064.png': 8,     # the same eight, nudged
    'Image_065.png': 8,     # the same, with the dark rusted plate
    'Image_066.png': 7,     # red block, triangle, maze plate, upright cap screw, terminal strip, hex nut, washer
    'Image_067.png': 8,     # red block, large washer, triangle, SMART FACTORY plate, cap screw, terminal strip, hex nut, washer
    'Image_068.png': 8,     # the same, with the maze plate
    'Image_069.png': 8,     # the same, with a worn SMART FACTORY plate
    'Image_070.png': 6,     # red block, large washer, triangle, blank square plate, hex nut, washer
    'Image_071.png': 6,     # the same, with the maze plate
    'Image_072.png': 6,     # the same, with the rust-stained plate
    'Image_073.png': 6,     # the same, with the dark rusted plate
    'Image_074.png': 2,     # rust-stained plate, aluminium plate
    'Image_075.png': 2,     # dark rusted plate, aluminium plate
    'Image_076.png': 2,     # rust-stained plate, dark rusted plate
    'Image_077.png': 1,     # aluminium plate
    'Image_078.png': 1,     # dark rusted plate
    'Image_079.png': 1,     # dark rusted plate, moved
    'Image_080.png': 1,     # rust-stained plate
    'Image_081.png': 1,     # dark rusted plate
    'Image_082.png': 1,     # dark rusted plate, moved slightly
    'Image_083.png': 1,     # aluminium plate
    'Image_084.png': 2,     # maze plate, SMART FACTORY plate
    'Image_085.png': 2,     # two maze plates
    'Image_086.png': 2,     # blank plate, SMART FACTORY plate
    'Image_087.png': 2,     # blank plate, maze plate
    'Image_088.png': 1,     # maze plate
    'Image_089.png': 1,     # maze plate
    'Image_090.png': 1,     # SMART FACTORY plate
    'Image_091.png': 1,     # maze plate
    'Image_092.png': 3,     # maze plate, two SMART FACTORY plates
    'Image_093.png': 4,     # four maze plates in a 2x2 grid, set close together
    'Image_094.png': 4,     # blank, two maze, SMART FACTORY plate in a 2x2 grid
    'Image_095.png': 4,     # two maze, two SMART FACTORY plates in a 2x2 grid
}


def _Warnings(n: int) -> tp.Tuple[str, ...]:
    """n objects that are not the catalogue item: the labels' shorthand below."""
    return ('Warning',) * n


# The catalogue modes, by the mode-file name's mode part, and the four states an object can take in one.
#   Unit [Tuple<string>]
CONST_CATALOGUE_MODES = ('Mounting_Plate', 'Labyrinth')
CONST_STATES = ('OK', 'NOK', 'Unspecified', 'Warning')
# Each frame's expected verdicts in the catalogue modes, as (mounting-plate mode, labyrinth mode), in no
# particular order. Labelled by eye from the frames, on the owner's rulings (2026-10-11). The parts, by
# the inventory's names above:
#   - mounting plate: the 'aluminium plate' (front, clean) and the 'dark rusted plate' (back) are OK; the
#     'rust-stained plate' (front, brown fingerprint stains) is NOK;
#   - labyrinth: the 'SMART FACTORY plate' (back, the logo complete, the worn one of 069 too) is OK; the
#     'maze plate' (front) is OK with its four corner holes (057, 060, 066, 085's first, 089, 093's last) and
#     NOK without them — six fronts have three, nine have none and another maze layout (068, 071, 084, 085's
#     second, 087, 088, 091, 092, three of 093, two of 094, two of 095; the owner's ruling, 2026-10-11:
#     DINOv2 decides it is the labyrinth, the holes decide OK or NOK, the layout is not checked); the
#     'blank plate' (50 x 50, no logo, no maze) is NOK: the owner's ruling, a back with no logo;
#   - each part is a Warning in the other mode, and every other object is a Warning in both.
# No frame shows two catalogue parts touching (the 2x2 grids of 093-095 lie apart), so none is
# Unspecified; no frame shows a letter missing from a logo (the logo check's erased letters are synthetic,
# test/Vision/Utilities/test_logo.py), and none is labelled for frames that do not exist.
# Every catalogue part here is nominal in size (no calipers; the owner's ruling: a part within tolerance
# reads OK), so no NOK is a size.
#   Unit [Dict<string, Tuple<Tuple<string>>>]
CONST_EXPECTED_VERDICTS = {
    'Image_055.png': (('OK',), _Warnings(1)),
    'Image_056.png': (('OK',), _Warnings(1)),
    'Image_057.png': (_Warnings(1), ('OK',)),
    'Image_058.png': (_Warnings(1), ('OK',)),
    'Image_059.png': (('NOK',) + _Warnings(5), _Warnings(6)),
    'Image_060.png': (_Warnings(7), ('OK',) + _Warnings(6)),
    'Image_061.png': (_Warnings(7), ('OK',) + _Warnings(6)),
    'Image_062.png': (('OK',) + _Warnings(6), _Warnings(7)),
    'Image_063.png': (('OK',) + _Warnings(7), _Warnings(8)),
    'Image_064.png': (('OK',) + _Warnings(7), _Warnings(8)),
    'Image_065.png': (('OK',) + _Warnings(7), _Warnings(8)),
    'Image_066.png': (_Warnings(7), ('OK',) + _Warnings(6)),
    'Image_067.png': (_Warnings(8), ('OK',) + _Warnings(7)),
    'Image_068.png': (_Warnings(8), ('NOK',) + _Warnings(7)),
    'Image_069.png': (_Warnings(8), ('OK',) + _Warnings(7)),
    'Image_070.png': (_Warnings(6), ('NOK',) + _Warnings(5)),
    'Image_071.png': (_Warnings(6), ('NOK',) + _Warnings(5)),
    'Image_072.png': (('NOK',) + _Warnings(5), _Warnings(6)),
    'Image_073.png': (('OK',) + _Warnings(5), _Warnings(6)),
    'Image_074.png': (('NOK', 'OK'), _Warnings(2)),
    'Image_075.png': (('OK', 'OK'), _Warnings(2)),
    'Image_076.png': (('NOK', 'OK'), _Warnings(2)),
    'Image_077.png': (('OK',), _Warnings(1)),
    'Image_078.png': (('OK',), _Warnings(1)),
    'Image_079.png': (('OK',), _Warnings(1)),
    'Image_080.png': (('NOK',), _Warnings(1)),
    'Image_081.png': (('OK',), _Warnings(1)),
    'Image_082.png': (('OK',), _Warnings(1)),
    'Image_083.png': (('OK',), _Warnings(1)),
    'Image_084.png': (_Warnings(2), ('OK', 'NOK')),
    'Image_085.png': (_Warnings(2), ('OK', 'NOK')),
    'Image_086.png': (_Warnings(2), ('NOK', 'OK')),
    'Image_087.png': (_Warnings(2), ('NOK', 'NOK')),
    'Image_088.png': (_Warnings(1), ('NOK',)),
    'Image_089.png': (_Warnings(1), ('OK',)),
    'Image_090.png': (_Warnings(1), ('OK',)),
    'Image_091.png': (_Warnings(1), ('NOK',)),
    'Image_092.png': (_Warnings(3), ('NOK', 'OK', 'OK')),
    'Image_093.png': (_Warnings(4), ('NOK', 'NOK', 'NOK', 'OK')),
    'Image_094.png': (_Warnings(4), ('NOK', 'NOK', 'NOK', 'OK')),
    'Image_095.png': (_Warnings(4), ('NOK', 'NOK', 'OK', 'OK')),
}
# The frames whose expected verdict the checks are known to miss: Image_092's right labyrinth back (dark,
# scratched, glare-lit) is complete but its letters score 0.19 against the references, a known false NOK of
# the logo check (KNOWN_ISSUES; the owner's ruling, 2026-10-11: no letter erased may pass to make it OK).
# Strict xfails: they fail the run the day the frame reads as labelled, so the mark is lifted with it.
#   Unit [Dict<Tuple<string, string>, string>]
CONST_PENDING_VERDICTS = {('Image_092.png', 'Labyrinth'): "the right plate's logo, a known false NOK (KNOWN_ISSUES)"}
# The corner holes on each labyrinth front of a frame, counted by eye on the enlarged corners (2026-10-11), in no
# particular order: four on the reference plate's kind, three on one kind (a corner blank), none on the plates with
# the other maze layout. The hole check must find exactly these.
#   Unit [Dict<string, Tuple<int>>]
CONST_CORNER_HOLES = {
    'Image_057.png': (4,), 'Image_060.png': (4,), 'Image_066.png': (4,), 'Image_068.png': (0,), 'Image_071.png': (3,),
    'Image_084.png': (3,), 'Image_085.png': (4, 3), 'Image_087.png': (0,), 'Image_088.png': (3,), 'Image_089.png': (4,),
    'Image_091.png': (0,), 'Image_092.png': (0,), 'Image_093.png': (3, 0, 0, 4), 'Image_094.png': (0, 0),
    'Image_095.png': (3, 0),
}
# The hole counts the check is known to get wrong: on Image_071 the plate lies in shadow and FastSAM never segments
# one of its three corner holes (two found). Its verdict is NOK either way; its reason says two of four. Strict:
# it fails the run the day the hole is found, so the mark is lifted with it.
#   Unit [Dict<string, string>]
CONST_PENDING_HOLE_COUNTS = {'Image_071.png': 'a corner hole in shadow, never segmented (KNOWN_ISSUES)'}
# The frames that ARE the catalogue items' reference images (Data/Catalogue/<item>/reference_image/, byte
# for byte), per mode. Judging an item on them is circular, so results on them are reported apart:
# analyze.py finds them by content (test_analyze_harness pins which they are), and the verdict tests of
# the catalogue's later phases report them separately from these labels. The logo references' frames are
# apart: each holds one referenced plate among others (Image_069's plate 3, Image_092's left plate).
#   Unit [Dict<string, Tuple<string>>]
CONST_REFERENCE_FRAMES = {'Mounting_Plate': ('Image_055.png', 'Image_056.png'),
                          'Labyrinth': ('Image_057.png', 'Image_058.png')}
CONST_LOGO_REFERENCE_FRAMES = {'Labyrinth': ('Image_069.png', 'Image_092.png')}



def _Configuration(scaled: bool = False) -> tp.Any:
    """
    The shipped configuration with FastSAM on the CPU (portable), unscaled unless asked: every
    stage runs with the parameters the application runs with.
    """
    import dataclasses
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    return config if scaled else dataclasses.replace(config, Scale=None)


def _Analyze_Frame(config: tp.Any, name: str) -> tp.Any:
    """
    The objects the application's pipeline (fallback describer: masks only, no VLM) finds on one
    frame of the pinned test set. A missing frame FAILS: these pins went dead once already by
    skipping on a frame that no longer existed.
    """
    import cv2
    path = os.path.join(config.Evaluation.Frames, name)
    frame = cv2.imread(path)
    if frame is None:
        # pytest.fail, not assert: an AssertionError here would satisfy an xfail(raises=AssertionError)
        # around the caller, and a missing frame would read as the expected failure.
        pytest.fail('%s is missing from the pinned test set (%s)' % (name, config.Evaluation.Frames))
    return Vision_Pipeline_Cls(Configuration_Str=config).Analyze(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).Objects

def test_pipeline_camera_to_reporting(synthetic_frame_path, model_free_backend) -> None:
    """
    Description:
        The full wiring through the REAL pipeline, without weights (model_free_backend):
        File_Camera_Cls captures an RGB frame with two objects on it, Analyze takes it directly,
        and the reading is composed through the real Reporting. Asserts the seams — two objects
        located, each with a composed sentence; the background line; the shared Screen_Header
        stating the count that the object list holds; the model-free task.
    """

    camera = File_Camera_Cls(synthetic_frame_path)
    camera.Connect()
    frame = camera.Capture()

    result = model_free_backend.Analyze(frame)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == 2
    # Reporting composed each sentence: capitalised, one closing stop.
    for obj in result.Objects:
        assert obj.Sentence and obj.Sentence[0].isupper() and obj.Sentence.endswith('.')
    assert result.Background
    # The shared Screen_Header states the count, agreeing with the object list.
    assert 'There are 2 objects on it, described below.' in Screen_Header(result.Objects, result.Background)
    assert result.Task == Vision_Core.CONST_FALLBACK_TASK_LABEL

    camera.Disconnect()
    assert not camera.Connected


def test_pipeline_real_describer_smoke(require_weights, reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The real four-stage vision path — background subtraction -> FastSAM
        segmentation -> fusion -> description -> compose — through the real
        pipeline on a synthetic two-rectangle frame. FastSAM is forced onto the CPU so it
        is portable; Gemma runs on MLX's Metal GPU, the only place it is verified. It runs in the
        DEFAULT suite whenever the FastSAM and Gemma weights exist; when either is absent
        it skips loudly (fails under --runslow) — never a pass without the real path.

        Structural assertions only — object count and box bounds come from the
        deterministic scene, every described object has a non-empty sentence, and the Task
        row names the describer that wrote the reading. The text itself is not asserted.
    """

    config = _Configuration()
    require_weights([config.Segmentation.Model_Path, config.Description.Model_Path])

    # OpenCV library for computer vision tasks [pip3 install opencv-python]
    import cv2

    frame_bgr = make_synthetic_frame(reference_background, CONST_RECTS)
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = image_rgb.shape[:2]

    result = Vision_Pipeline_Cls(Configuration_Str=config).Analyze(image_rgb)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == len(CONST_RECTS)
    for obj in result.Objects:
        x, y, bw, bh = obj.Bbox
        # Box is inside the image dimensions.
        assert 0 <= x and 0 <= y
        assert x + bw <= w and y + bh <= h
        # A described object always has a sentence; its exact words are not asserted.
        assert obj.Sentence
    assert result.Task == config.Identity.Task
    assert result.Latency_Ms >= 0


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(CONST_INVENTORY))
def test_counts_match_the_inventory(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Every frame of the pinned test set comes back with the number of parts counted on it by eye
        (CONST_INVENTORY) — a merge lowers the count, a split raises it. A frame missing from the set
        fails (pytest.fail, which no xfail(raises=AssertionError) accepts). Slow because it runs FastSAM;
        missing weights fail it under --runslow.
    """

    config = _Configuration()
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    assert len(_Analyze_Frame(config, name)) == CONST_INVENTORY[name]


def test_the_inventory_names_every_frame_of_the_test_set() -> None:
    """
    Description:
        CONST_INVENTORY names exactly the frames in the pinned test set (Evaluation.Frames): a frame
        added without a count, or removed while its count stays, fails here in the default run,
        without the weights. The count test above only notices under --runslow, and twice frames
        moved without the inventory following.
    """

    config = _Configuration()
    frames = sorted(os.path.basename(path) for path in glob.glob(os.path.join(config.Evaluation.Frames,
                                                                             'Image_[0-9]*.png')))
    assert frames == sorted(CONST_INVENTORY)


@pytest.mark.slow
def test_plates_come_back_as_compact_silhouettes_on_a_real_capture(require_weights, monkeypatch) -> None:
    """
    Description:
        On a real capture (Image_072: the machined rust-stained plate and the red block, both thick and
        casting a shadow, beside a large washer, a triangle, a hex nut and a washer) the plate and the
        block each come back as ONE compact silhouette — no shadow or neighbour absorbed into the
        component. Tightness is rectangularity (mask area / bbox area): a clean near-axis-aligned part is
        well above 0.80 (measured 0.968 and 0.949, 2026-10-11); a shadow tail or a bridge to a neighbour
        would extend the box and drop it below. They are the two largest boxes. (It replaces the previous
        set's All/Image_003, no longer in the set, recoverable from 1061966: a tilted plate is not a
        candidate, as its tilt alone lowers the ratio — Image_074's measured 0.71.)
    """

    config = _Configuration()
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    import numpy as np
    objects = _Analyze_Frame(config, 'Image_072.png')
    assert len(objects) == CONST_INVENTORY['Image_072.png']
    by_area = sorted(objects, key=lambda det: det.Bbox[2] * det.Bbox[3])
    for part in (by_area[-1], by_area[-2]):
        x, y, w, h = part.Bbox
        rectangularity = int(np.count_nonzero(part.Mask)) / float(w * h)
        assert rectangularity >= 0.80, 'silhouette is not compact (%.2f)' % rectangularity


@pytest.mark.slow
@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='a shadow far darker/larger than any real capture is still '
                          'absorbed into the component; see KNOWN_ISSUES.md')
def test_synthetic_harsh_shadow_not_absorbed_xfail(require_weights, monkeypatch) -> None:
    """
    Description:
        The open residual, pinned as a STRICT xfail. On a synthetic scene with a
        shadow far harsher than any real capture — a large 40%-darkening ellipse the
        5px opening cannot remove — the fusion absorbs the shadow into the object's
        component, so the object's mask extends below the parts into the shadow band.

        The assertion states the DESIRED behaviour (no object reaches into the shadow
        band); it currently fails, which is why this is xfail. strict=True means the
        day the pipeline stops absorbing the shadow, this test XPASSes and the suite
        fails — the signal to promote it to a plain pass and close the KNOWN_ISSUES
        entry. The weights go through require_weights (a loud skip, a failure under
        --runslow — never an early return), so a skip is never mistaken for an
        unexpected pass.

        Only the documented failure is expected: raises=AssertionError (measured: the
        real run fails 'assert 641 <= 545'). Anything else — require_weights refusing a
        stand-in runtime (pytest's Failed), a crash — reports as a FAILURE, not as the
        known residual. That matters because on leaked stand-ins this test fails the
        same assertion with the same number (the background cue alone absorbs the
        shadow), so only the guard can tell the two apart.
    """

    params = _Configuration().Segmentation
    require_weights([params.Model_Path])

    import cv2
    import numpy as np
    from Vision.Utilities.Segmentation import Background_Foreground
    from Vision.Utilities.Fusion import Fuse_Objects
    from Vision.Segmenter import Fast_Sam_Cls

    # Two objects 10 px apart (separate components; the closing no longer joins them), with a harsh cast
    # shadow abutting their lower edges — the parts end at y=520, the shadow reaches
    # to ~y=640.
    w, h = 1000, 800
    bg = np.zeros((h, w, 3), dtype=np.uint8)
    bg[:] = (70, 150, 70)
    scene = bg.copy()
    cv2.rectangle(scene, (300, 300), (510, 520), (40, 40, 200), thickness=-1)   # red
    cv2.rectangle(scene, (520, 300), (730, 520), (200, 60, 40), thickness=-1)   # blue
    shadow_layer = scene.copy()
    cv2.ellipse(shadow_layer, (515, 560), (200, 80), 0, 0, 360, (0, 0, 0), thickness=-1)
    scene = cv2.addWeighted(scene, 0.6, shadow_layer, 0.4, 0.0)

    background_fg = Background_Foreground(bg, scene, cv2, np, Segmentation_Parameters_Str=params)
    masks, scores = Fast_Sam_Cls(params).Segment(scene)
    objects = Fuse_Objects(masks, scores, background_fg, cv2, np, Segmentation_Parameters_Str=params)

    # Desired: no object's mask reaches past the parts (bottom edge y=520) into the
    # shadow band. Currently one object extends to ~y=641, so this fails (xfail).
    bottom = max((y + bh for (x, y, bw, bh) in (o.Bbox for o in objects)), default=0)
    assert bottom <= 545


@pytest.mark.slow
def test_symmetric_parts_measure_as_diameters_on_real_captures(require_weights, monkeypatch) -> None:
    """
    Description:
        The symmetric decision on real captures, through the application's own pipeline and the
        shipped scale: in Image_059 (in index order: flanged bushing, rust-stained plate, cap screw,
        terminal strip, washer, hex nut) the bushing, the washer and the nut (1, 5, 6) are measured as
        diameters with no angle, the plate, the screw and the strip (2, 3, 4) as A x B with an angle;
        the nut reports across flats, the round parts a round diameter. The square blank plate in
        Image_070 (object 4: large washer, red block, triangle, blank plate, hex nut, washer) is NOT
        reported as a diameter (it is un-elongated, but its extent marks it square). (It replaces the
        previous set's All/Image_005 and 008, no longer in the set, recoverable from 1061966.) Slow
        because it runs FastSAM; missing weights fail it (it only runs under --runslow, which asks for them).
    """

    config = _Configuration(scaled=True)
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')   # masks only, no VLM

    objects = _Analyze_Frame(config, 'Image_059.png')
    assert len(objects) == CONST_INVENTORY['Image_059.png']
    symmetric = [i + 1 for i, det in enumerate(objects) if det.Measurement.Symmetric]
    assert symmetric == [1, 5, 6]
    across_flats = [i + 1 for i, det in enumerate(objects) if det.Measurement.Across_Flats]
    assert across_flats == [6]
    for det in objects:
        m = det.Measurement
        if m.Symmetric:
            assert m.Diameter_Mm is not None and m.Angle_Deg is None
        else:
            assert m.Width_Mm >= m.Height_Mm and m.Angle_Deg is not None

    objects = _Analyze_Frame(config, 'Image_070.png')
    assert len(objects) == CONST_INVENTORY['Image_070.png']
    square = objects[3].Measurement                                    # the blank square plate
    assert not square.Symmetric and square.Angle_Deg is not None and square.Angle_Deg < 90.0


def test_the_expected_verdicts_label_every_object_of_every_frame() -> None:
    """
    Description:
        The catalogue labels cover exactly the inventory: every frame, in both catalogue modes, one state
        per counted object, each one of the four states — so a frame added, removed or recounted without
        its labels fails here, in the default run.
    """

    assert sorted(CONST_EXPECTED_VERDICTS) == sorted(CONST_INVENTORY)
    for name, by_mode in CONST_EXPECTED_VERDICTS.items():
        assert len(by_mode) == len(CONST_CATALOGUE_MODES), name
        for states in by_mode:
            assert len(states) == CONST_INVENTORY[name] and set(states) <= set(CONST_STATES), name


def test_no_object_is_labelled_the_item_in_both_modes() -> None:
    """
    Description:
        A mounting plate is a Warning in the labyrinth mode and the reverse: on every frame, the objects
        one mode labels its item (OK or NOK) are no more than the other mode's Warnings.
    """

    for name, (plate, labyrinth) in CONST_EXPECTED_VERDICTS.items():
        for items, other in ((plate, labyrinth), (labyrinth, plate)):
            assert sum(state in ('OK', 'NOK') for state in items) <= other.count('Warning'), name


def test_the_reference_frames_are_labelled_ok_in_their_mode() -> None:
    """
    Description:
        A reference image shows the part in its OK state (the request), so each reference frame is one
        OK object in its own mode, and a logo reference's frame holds an OK object (the referenced plate).
    """

    for mode, names in CONST_REFERENCE_FRAMES.items():
        for name in names:
            assert CONST_EXPECTED_VERDICTS[name][CONST_CATALOGUE_MODES.index(mode)] == ('OK',), name
    for mode, names in CONST_LOGO_REFERENCE_FRAMES.items():
        for name in names:
            assert 'OK' in CONST_EXPECTED_VERDICTS[name][CONST_CATALOGUE_MODES.index(mode)], name


@pytest.mark.slow
@pytest.mark.parametrize('mode', CONST_CATALOGUE_MODES)
@pytest.mark.parametrize('name', sorted(CONST_EXPECTED_VERDICTS))
def test_the_outline_passes_exactly_the_catalogue_parts(name: str, mode: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Through the application's pipeline (FastSAM on the CPU, the model-free describer) in each
        catalogue mode, the objects whose outline is within the item's tolerance are exactly as many as
        the labels' OK and NOK objects: every nominal part reads within tolerance at its top face, and
        no other object is the item's size. Slow because it runs FastSAM; missing weights fail it under
        --runslow.
    """

    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_%s.yaml'
                                             % mode))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    objects = _Analyze_Frame(config, name)
    within = [det for det in objects if det.Dimension_Checks and all(check.Within for check in det.Dimension_Checks)]
    states = collections.Counter(CONST_EXPECTED_VERDICTS[name][CONST_CATALOGUE_MODES.index(mode)])
    assert len(within) == states['OK'] + states['NOK']


def _Verdict_Cases() -> tp.List[tp.Any]:
    """Every (frame, mode) of the labels, a pending one marked as a strict expected failure naming its cause."""
    cases = []
    for name in sorted(CONST_EXPECTED_VERDICTS):
        for mode in CONST_CATALOGUE_MODES:
            reason = CONST_PENDING_VERDICTS.get((name, mode))
            marks = [pytest.mark.xfail(strict=True, raises=AssertionError, reason=reason)] if reason else []
            cases.append(pytest.param(name, mode, marks=marks, id='%s-%s' % (name[:-4], mode)))
    return cases


@pytest.mark.slow
@pytest.mark.parametrize('name, mode', _Verdict_Cases())
def test_each_frame_gets_its_expected_verdicts(name: str, mode: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Through the application's pipeline (FastSAM and DINOv2 on the CPU, the model-free describer) in each
        catalogue mode, every frame's objects take exactly the labelled states — OK, NOK, Unspecified,
        Warning, counted, since the labels are in no particular order; a known miss is a strict expected
        failure (CONST_PENDING_VERDICTS). The reference frames are in the run like any other; the
        harness reports them apart. Slow because it runs both models; missing weights fail it under --runslow.
    """

    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_%s.yaml'
                                             % mode))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path, config.Identification.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    objects = _Analyze_Frame(config, name)
    expected = collections.Counter(CONST_EXPECTED_VERDICTS[name][CONST_CATALOGUE_MODES.index(mode)])
    assert collections.Counter(det.Verdict for det in objects) == expected


def _Hole_Cases() -> tp.List[tp.Any]:
    """Every labyrinth front's frame, a pending one marked as a strict expected failure naming its cause."""
    return [pytest.param(name, marks=[pytest.mark.xfail(strict=True, raises=AssertionError,
                                                        reason=CONST_PENDING_HOLE_COUNTS[name])]
                         if name in CONST_PENDING_HOLE_COUNTS else [], id=name[:-4])
            for name in sorted(CONST_CORNER_HOLES)]


def _Catalogue_Objects(mode: str, name: str, require_weights, monkeypatch) -> tp.List[tp.Any]:
    """A frame through the application's pipeline in a catalogue mode (FastSAM and DINOv2 on the CPU)."""
    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_%s.yaml'
                                             % mode))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path, config.Identification.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    return _Analyze_Frame(config, name)


@pytest.mark.slow
@pytest.mark.parametrize('name', _Hole_Cases())
def test_the_corner_holes_found_are_the_ones_on_the_plate(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        In the labyrinth mode, the corner holes the check counts on each front of a frame are exactly those
        counted by eye (CONST_CORNER_HOLES): four, three or none, the maze's start and finish marks never among
        them. Slow because it runs FastSAM and DINOv2; missing weights fail it under --runslow.
    """

    objects = _Catalogue_Objects('Labyrinth', name, require_weights, monkeypatch)
    found = [count.Found for det in objects for count in det.Hole_Counts if count.Name == 'corner hole']
    assert sorted(found) == sorted(CONST_CORNER_HOLES[name])


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(name for name, (plate, _labyrinth) in CONST_EXPECTED_VERDICTS.items()
                                        if set(plate) & {'OK', 'NOK'}))
def test_every_mounting_plate_shows_all_its_holes_within_tolerance(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        In the mounting-plate mode, every plate of the test set shows its holes as the catalogue gives them —
        a front two countersinks and two through-holes, a back two through-holes — each diameter, edge distance
        and the pitch within tolerance. Slow because it runs FastSAM and DINOv2.
    """

    objects = _Catalogue_Objects('Mounting_Plate', name, require_weights, monkeypatch)
    judged = [det for det in objects if det.Verdict in ('OK', 'NOK')]
    assert judged
    for det in judged:
        expected = ([('countersink', 2, 2), ('through-hole', 2, 2)] if det.Catalogue.Side == 'front'
                    else [('through-hole', 2, 2)])
        assert [(c.Name, c.Found, c.Expected) for c in det.Hole_Counts] == expected
        assert det.Hole_Checks and all(check.Within for check in det.Hole_Checks), \
            [(c.Name, round(c.Measured_Mm, 2)) for c in det.Hole_Checks if not c.Within]
