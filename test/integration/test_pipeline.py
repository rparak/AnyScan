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
from Configuration.Core import Load_Configuration, Mode_Directory, CONST_DEFAULT_CONFIG_FILE
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
    'Image_057.png': 1,     # milled square plate
    'Image_058.png': 1,     # engraved square plate
    'Image_059.png': 6,     # flanged bushing, rust-stained plate, cap screw, washer, terminal strip, hex nut
    'Image_060.png': 7,     # bushing, milled square plate, cap screw, washer, terminal strip, triangle, hex nut
    'Image_061.png': 7,     # the same, with an engraved square plate
    'Image_062.png': 7,     # the same, with the dark rusted plate
    'Image_063.png': 8,     # red block, aluminium plate, cap screw, terminal strip, triangle, hex nut, washer, lattice bracket
    'Image_064.png': 8,     # the same eight, nudged
    'Image_065.png': 8,     # the same, with the dark rusted plate
    'Image_066.png': 7,     # red block, triangle, milled square plate, upright cap screw, terminal strip, hex nut, washer
    'Image_067.png': 8,     # red block, large washer, triangle, engraved square plate, cap screw, terminal strip, hex nut, washer
    'Image_068.png': 8,     # the same, with a milled square plate
    'Image_069.png': 8,     # the same, with a worn engraved square plate
    'Image_070.png': 6,     # red block, large washer, triangle, blank square plate, hex nut, washer
    'Image_071.png': 6,     # the same, with a milled square plate
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
    'Image_084.png': 2,     # milled square plate, engraved square plate
    'Image_085.png': 2,     # two milled square plates
    'Image_086.png': 2,     # blank plate, engraved square plate
    'Image_087.png': 2,     # blank plate, milled square plate
    'Image_088.png': 1,     # milled square plate
    'Image_089.png': 1,     # milled square plate
    'Image_090.png': 1,     # engraved square plate
    'Image_091.png': 1,     # milled square plate
    'Image_092.png': 3,     # milled square plate, two engraved square plates
    'Image_093.png': 4,     # four milled square plates in a 2x2 grid, set close together
    'Image_094.png': 4,     # blank, two milled, one engraved square plate in a 2x2 grid
    'Image_095.png': 4,     # two milled, two engraved square plates in a 2x2 grid
}


def _Warnings(n: int) -> tp.Tuple[str, ...]:
    """n objects that are not the catalogue item: the labels' shorthand below."""
    return ('Warning',) * n


# The states an object can take in the catalogue mode.
#   Unit [Tuple<string>]
CONST_STATES = ('OK', 'NOK', 'Warning')
# Each frame's expected verdicts in the mounting-plate mode, in no particular order. Labelled by eye from the
# frames, on the owner's rulings (2026-10-11): the 'aluminium plate' (front, clean) and the 'dark rusted plate'
# (back) are OK; the 'rust-stained plate' (front, brown fingerprint stains) is NOK; every other object, the
# 50 x 50 square plates among them, is a Warning. No frame shows two plates touching, so none is a Warning of kind
# several parts.
# Every plate here is nominal in size (no calipers; the owner's ruling: a part within tolerance reads OK), so no
# NOK is a size. Since 2026-10-16 a part is judged only wholly inside the station's inspection area: Image_062's clean
# front (20.8 mm out, its long side upright) reaches into the band along the top edge, so it is a Warning, not
# checked (CONST_PLATES_OUTSIDE_THE_AREA).
#   Unit [Dict<string, Tuple<string>>]
CONST_EXPECTED_VERDICTS = {
    'Image_055.png': ('OK',),
    'Image_056.png': ('OK',),
    'Image_057.png': _Warnings(1),
    'Image_058.png': _Warnings(1),
    'Image_059.png': ('NOK',) + _Warnings(5),
    'Image_060.png': _Warnings(7),
    'Image_061.png': _Warnings(7),
    'Image_062.png': _Warnings(7),
    'Image_063.png': ('OK',) + _Warnings(7),
    'Image_064.png': ('OK',) + _Warnings(7),
    'Image_065.png': ('OK',) + _Warnings(7),
    'Image_066.png': _Warnings(7),
    'Image_067.png': _Warnings(8),
    'Image_068.png': _Warnings(8),
    'Image_069.png': _Warnings(8),
    'Image_070.png': _Warnings(6),
    'Image_071.png': _Warnings(6),
    'Image_072.png': ('NOK',) + _Warnings(5),
    'Image_073.png': ('OK',) + _Warnings(5),
    'Image_074.png': ('NOK', 'OK'),
    'Image_075.png': ('OK', 'OK'),
    'Image_076.png': ('NOK', 'OK'),
    'Image_077.png': ('OK',),
    'Image_078.png': ('OK',),
    'Image_079.png': ('OK',),
    'Image_080.png': ('NOK',),
    'Image_081.png': ('OK',),
    'Image_082.png': ('OK',),
    'Image_083.png': ('OK',),
    'Image_084.png': _Warnings(2),
    'Image_085.png': _Warnings(2),
    'Image_086.png': _Warnings(2),
    'Image_087.png': _Warnings(2),
    'Image_088.png': _Warnings(1),
    'Image_089.png': _Warnings(1),
    'Image_090.png': _Warnings(1),
    'Image_091.png': _Warnings(1),
    'Image_092.png': _Warnings(3),
    'Image_093.png': _Warnings(4),
    'Image_094.png': _Warnings(4),
    'Image_095.png': _Warnings(4),
}
# The frames whose mounting plate lies over the inspection area's edge, identified there: a Warning, not checked.
#   Unit [Tuple<string>]
CONST_PLATES_OUTSIDE_THE_AREA = ('Image_062.png',)
# The frames that ARE the catalogue item's reference images (Data/Catalogue/mounting_plate/reference_image/, byte
# for byte). Judging the item on them is circular, so results on them are reported apart: analyze.py finds them
# by content (test_analyze_harness pins which they are).
#   Unit [Tuple<string>]
CONST_REFERENCE_FRAMES = ('Image_055.png', 'Image_056.png')



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
        The catalogue labels cover exactly the inventory: every frame, one state per counted object, each one of
        the four states — so a frame added, removed or recounted without its labels fails here, in the default run.
    """

    assert sorted(CONST_EXPECTED_VERDICTS) == sorted(CONST_INVENTORY)
    for name, states in CONST_EXPECTED_VERDICTS.items():
        assert len(states) == CONST_INVENTORY[name] and set(states) <= set(CONST_STATES), name


def test_the_reference_frames_are_labelled_ok() -> None:
    """
    Description:
        A reference image shows the part in its OK state (the request), so each reference frame is one OK object.
    """

    for name in CONST_REFERENCE_FRAMES:
        assert CONST_EXPECTED_VERDICTS[name] == ('OK',), name


# The catalogue mode's file.
#   Unit [string]
CONST_CATALOGUE_MODE_FILE = 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml'


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(CONST_EXPECTED_VERDICTS))
def test_the_outline_passes_exactly_the_catalogue_parts(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Through the application's pipeline (FastSAM on the CPU, the model-free describer) in the mounting-plate
        mode, the objects whose outline is within the item's tolerance are exactly as many as the labels' OK and
        NOK objects and the plates outside the inspection area: every nominal plate reads within tolerance at its
        top face, and no other object is its size. Slow because it runs FastSAM; missing weights fail it under
        --runslow.
    """

    config = Load_Configuration(os.path.join(Mode_Directory(), CONST_CATALOGUE_MODE_FILE))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    objects = _Analyze_Frame(config, name)
    within = [det for det in objects if det.Dimension_Checks and all(check.Within for check in det.Dimension_Checks)]
    states = collections.Counter(CONST_EXPECTED_VERDICTS[name])
    assert len(within) == states['OK'] + states['NOK'] + (name in CONST_PLATES_OUTSIDE_THE_AREA)


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(CONST_EXPECTED_VERDICTS))
def test_each_frame_gets_its_expected_verdicts(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Through the application's pipeline (FastSAM and DINOv2 on the CPU, the model-free describer) in the
        mounting-plate mode, every frame's objects take exactly the labelled states — OK, NOK, Warning, counted,
        since the labels are in no particular order — and every Warning carries a kind the record knows. The reference frames are in the run like
        any other; the harness reports them apart. Slow because it runs both models; missing weights fail it
        under --runslow.
    """

    objects = _Catalogue_Objects(name, require_weights, monkeypatch)
    assert collections.Counter(det.Verdict for det in objects) == collections.Counter(CONST_EXPECTED_VERDICTS[name])
    from Parameters.Vision import CONST_WARNING_KINDS
    assert all(det.Catalogue.Warning_Kind in dict(CONST_WARNING_KINDS) for det in objects if det.Verdict == 'Warning')


def _Catalogue_Objects(name: str, require_weights, monkeypatch) -> tp.List[tp.Any]:
    """A frame through the application's pipeline in the mounting-plate mode (FastSAM and DINOv2 on the CPU)."""
    config = Load_Configuration(os.path.join(Mode_Directory(), CONST_CATALOGUE_MODE_FILE))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path, config.Identification.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    return _Analyze_Frame(config, name)


# The mounting plates with fingerprints on the front, each showing two by eye (2026-10-11), either side of a hole.
#   Unit [Tuple<string>]
CONST_STAINED_FRONTS = ('Image_059.png', 'Image_072.png', 'Image_074.png', 'Image_076.png', 'Image_080.png')


@pytest.mark.slow
@pytest.mark.parametrize('name', CONST_STAINED_FRONTS)
def test_each_stained_front_shows_its_two_fingerprints_as_two_stains(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        In the mounting-plate mode, the fingerprinted front of each frame is NOK with exactly two stain regions —
        the two fingerprints seen by eye, their fragments joined within Merge_Mm — each a failed feature on the
        frame and named in the one reason ('There are two stains on the machined front.'). Slow because it runs
        FastSAM and DINOv2; missing weights fail it under --runslow.
    """

    from Reporting.Core import Reason_Sentence
    objects = _Catalogue_Objects(name, require_weights, monkeypatch)
    (stained,) = [det for det in objects if det.Stains]
    assert len(stained.Stains) == 2 and stained.Verdict == 'NOK'
    assert sum(1 for feature in stained.Features if feature.Kind == 'stain' and not feature.Passed) == 2
    assert Reason_Sentence(stained) == 'There are two stains on the machined front.'


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(name for name, states in CONST_EXPECTED_VERDICTS.items()
                                        if set(states) & {'OK', 'NOK'}))
def test_every_mounting_plate_shows_all_its_holes_within_tolerance(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        In the mounting-plate mode, every judged plate of the test set shows its holes as the catalogue gives them —
        a front two countersinks and two through-holes, a back two through-holes — each diameter, edge distance
        and the pitch within tolerance. Slow because it runs FastSAM and DINOv2.
    """

    objects = _Catalogue_Objects(name, require_weights, monkeypatch)
    judged = [det for det in objects if det.Verdict in ('OK', 'NOK')]
    assert judged
    for det in judged:
        expected = ([('countersink', 2, 2), ('through-hole', 2, 2)] if det.Catalogue.Side == 'front'
                    else [('through-hole', 2, 2)])
        assert [(c.Name, c.Found, c.Expected) for c in det.Hole_Counts] == expected
        assert det.Hole_Checks and all(check.Within for check in det.Hole_Checks), \
            [(c.Name, round(c.Measured_Mm, 2)) for c in det.Hole_Checks if not c.Within]


@pytest.mark.slow
@pytest.mark.parametrize('name', CONST_PLATES_OUTSIDE_THE_AREA)
def test_a_plate_outside_the_area_is_not_checked(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        The plate of the test set that reaches over the inspection area's edge is the amber Warning outside the area,
        and no hole or stain check runs on it: no hole, stain or feature, its reason only to move it inside.
    """

    from Reporting.Core import Outside_Part, Reason_Sentence
    (plate,) = [det for det in _Catalogue_Objects(name, require_weights, monkeypatch) if Outside_Part(det)]
    assert (plate.Features, plate.Hole_Counts, plate.Stains) == ([], [], None)
    assert Reason_Sentence(plate) == ('It lies outside the inspection area, so it is not judged: move it fully inside '
                                      'the area and scan again.')
