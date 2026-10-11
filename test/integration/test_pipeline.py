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
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE
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
# session, numbered from 014: the names 001-013 belonged to the previous set (All/, recoverable from
# 1061966) and are still cited for its evidence, so they are never reused. The blue double triangle,
# a terminal strip with its screws, the flanged bushing and the slit lattice bracket are one part each.
#   Unit [Dict<string, int>]
CONST_INVENTORY = {
    'Image_014.png': 1,     # machined aluminium plate
    'Image_015.png': 1,     # dark rusted plate
    'Image_016.png': 1,     # maze plate
    'Image_017.png': 1,     # SMART FACTORY plate
    'Image_018.png': 6,     # flanged bushing, rust-stained plate, cap screw, washer, terminal strip, hex nut
    'Image_019.png': 7,     # bushing, maze plate, cap screw, washer, terminal strip, triangle, hex nut
    'Image_020.png': 7,     # the same, with the SMART FACTORY plate
    'Image_021.png': 7,     # the same, with the dark rusted plate
    'Image_022.png': 8,     # red block, aluminium plate, cap screw, terminal strip, triangle, hex nut, washer, lattice bracket
    'Image_023.png': 8,     # the same eight, nudged
    'Image_024.png': 8,     # the same, with the dark rusted plate
    'Image_025.png': 7,     # red block, triangle, maze plate, upright cap screw, terminal strip, hex nut, washer
    'Image_026.png': 8,     # red block, large washer, triangle, SMART FACTORY plate, cap screw, terminal strip, hex nut, washer
    'Image_027.png': 8,     # the same, with the maze plate
    'Image_028.png': 8,     # the same, with a worn SMART FACTORY plate
    'Image_029.png': 6,     # red block, large washer, triangle, blank square plate, hex nut, washer
    'Image_030.png': 6,     # the same, with the maze plate
    'Image_031.png': 6,     # the same, with the rust-stained plate
    'Image_032.png': 6,     # the same, with the dark rusted plate
    'Image_033.png': 2,     # rust-stained plate, aluminium plate
    'Image_034.png': 2,     # dark rusted plate, aluminium plate
    'Image_035.png': 2,     # rust-stained plate, dark rusted plate
    'Image_036.png': 1,     # aluminium plate
    'Image_037.png': 1,     # dark rusted plate
    'Image_038.png': 1,     # dark rusted plate, moved
    'Image_039.png': 1,     # rust-stained plate
    'Image_040.png': 1,     # dark rusted plate
    'Image_041.png': 1,     # dark rusted plate, moved slightly
    'Image_042.png': 1,     # aluminium plate
    'Image_043.png': 2,     # maze plate, SMART FACTORY plate
    'Image_044.png': 2,     # two maze plates
    'Image_045.png': 2,     # blank plate, SMART FACTORY plate
    'Image_046.png': 2,     # blank plate, maze plate
    'Image_047.png': 1,     # maze plate
    'Image_048.png': 1,     # maze plate
    'Image_049.png': 1,     # SMART FACTORY plate
    'Image_050.png': 1,     # maze plate
    'Image_051.png': 3,     # maze plate, two SMART FACTORY plates
    'Image_052.png': 4,     # four maze plates in a 2x2 grid, set close together
    'Image_053.png': 4,     # blank, two maze, SMART FACTORY plate in a 2x2 grid
    'Image_054.png': 4,     # two maze, two SMART FACTORY plates in a 2x2 grid
}
# The reference the frames below are pending against: shot 2026-09-28, before the lighting or exposure
# changed for the 2026-10-09 session. On these frames the pipeline returns every part plus ONE extra
# object in the bottom-right corner (x 1780-1802, y 1007-1024, to the frame's edge), where the reference's
# undistortion border does not line up with the frames'. Strict xfail while this reference is in force;
# once Segmentation.Background.Reference names another (Image_Background_002), the mark lifts and each
# must pass on its count or fail visibly. See KNOWN_ISSUES.md, "Nine frames count one extra object
# against the old reference".
#   Unit [string]
CONST_PENDING_REFERENCE = 'Image_Background_001.png'
#   Unit [Set<string>]
CONST_PENDING_FRAMES = {'Image_015.png', 'Image_024.png', 'Image_032.png', 'Image_034.png', 'Image_035.png',
                        'Image_037.png', 'Image_038.png', 'Image_040.png', 'Image_041.png'}



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


def _Reference_Is_Pending() -> bool:
    """
    The shipped configuration still names the reference CONST_PENDING_FRAMES are pending against.
    Called from the xfail condition below when each test is set up, not at import, so a configuration
    that fails to load fails those tests instead of stopping the collection.
    """
    return os.path.basename(_Configuration().Segmentation.Background_Reference) == CONST_PENDING_REFERENCE


@pytest.mark.slow
@pytest.mark.parametrize('name', [
    pytest.param(name, marks=pytest.mark.xfail('_Reference_Is_Pending()', strict=True, raises=AssertionError,
                                               reason='one extra object in the bottom-right corner against '
                                                      'Image_Background_001; see KNOWN_ISSUES.md'))
    if name in CONST_PENDING_FRAMES else name for name in sorted(CONST_INVENTORY)])
def test_counts_match_the_inventory(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Every frame of the pinned test set comes back with the number of parts counted on it by eye
        (CONST_INVENTORY) — a merge lowers the count, a split raises it. A frame missing from the set
        fails (pytest.fail, which no xfail(raises=AssertionError) accepts). Slow because it runs FastSAM;
        missing weights fail it under --runslow. The CONST_PENDING_FRAMES are strict xfails while the
        reference they are pending against is in force: one that starts passing fails the suite.
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
    # A pending frame that is not in the inventory would mark nothing and hide nothing.
    assert CONST_PENDING_FRAMES <= set(CONST_INVENTORY)


@pytest.mark.slow
def test_plates_come_back_as_compact_silhouettes_on_a_real_capture(require_weights, monkeypatch) -> None:
    """
    Description:
        On a real capture (Image_031: the machined rust-stained plate and the red block, both thick and
        casting a shadow, beside a large washer, a triangle, a hex nut and a washer) the plate and the
        block each come back as ONE compact silhouette — no shadow or neighbour absorbed into the
        component. Tightness is rectangularity (mask area / bbox area): a clean near-axis-aligned part is
        well above 0.80 (measured 0.963 and 0.944, 2026-10-11); a shadow tail or a bridge to a neighbour
        would extend the box and drop it below. They are the two largest boxes. (It replaces the previous
        set's All/Image_003, no longer in the set, recoverable from 1061966: a tilted plate is not a
        candidate, as its tilt alone lowers the ratio — Image_033's measured 0.70.)
    """

    config = _Configuration()
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    import numpy as np
    objects = _Analyze_Frame(config, 'Image_031.png')
    assert len(objects) == CONST_INVENTORY['Image_031.png']
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
        shipped scale: in Image_018 (in index order: flanged bushing, rust-stained plate, cap screw,
        terminal strip, washer, hex nut) the bushing, the washer and the nut (1, 5, 6) are measured as
        diameters with no angle, the plate, the screw and the strip (2, 3, 4) as A x B with an angle;
        the nut reports across flats, the round parts a round diameter. The square blank plate in
        Image_029 (object 4: large washer, red block, triangle, blank plate, hex nut, washer) is NOT
        reported as a diameter (it is un-elongated, but its extent marks it square). (It replaces the
        previous set's All/Image_005 and 008, no longer in the set, recoverable from 1061966.) Slow
        because it runs FastSAM; missing weights fail it (it only runs under --runslow, which asks for them).
    """

    config = _Configuration(scaled=True)
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')   # masks only, no VLM

    objects = _Analyze_Frame(config, 'Image_018.png')
    assert len(objects) == CONST_INVENTORY['Image_018.png']
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

    objects = _Analyze_Frame(config, 'Image_029.png')
    assert len(objects) == CONST_INVENTORY['Image_029.png']
    square = objects[3].Measurement                                    # the blank square plate
    assert not square.Symmetric and square.Angle_Deg is not None and square.Angle_Deg < 90.0
