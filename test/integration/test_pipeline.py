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



def _Configuration(scaled: bool = False) -> tp.Any:
    """
    The shipped configuration with FastSAM on the CPU (portable), unscaled unless asked: every
    stage runs with the parameters the application runs with.
    """
    import dataclasses
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    return config if scaled else dataclasses.replace(config, Scale=None)

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
def test_shadow_rejected_on_real_capture(require_weights, monkeypatch) -> None:
    """
    Description:
        The real cast-shadow frame (Image_004): one two-hole plate with a soft shadow
        along its lower edge. The fusion pipeline must report exactly ONE object whose
        silhouette is a compact plate — the shadow rejected by the opening, not
        absorbed into the component. Silhouette tightness is checked by rectangularity
        (mask area / bbox area): a clean rotated plate with two holes measures ~0.88;
        a shadow tail would extend the box and drop it well below the 0.80 bound.

        This is the real-capture counterpart to the KNOWN_ISSUES shadow entry: it
        passes because the over-segmentation defect is fixed on real frames. Slow
        because it runs FastSAM; missing weights fail it (it only runs under --runslow, which
        asks for them), a missing frame skips it.
    """

    config = _Configuration()
    require_weights([config.Segmentation.Model_Path])
    frame_path = os.path.join(config.Evaluation.Frames, 'Image_004.png')
    if not os.path.isfile(frame_path):
        pytest.skip('Image_004.png not present at %s' % frame_path)

    import cv2
    import numpy as np
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')   # count/mask only, no VLM

    scene_bgr = cv2.imread(frame_path)
    result = Vision_Pipeline_Cls(Configuration_Str=config).Analyze(cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2RGB))

    assert len(result.Objects) == 1
    det = result.Objects[0]
    x, y, w, h = det.Bbox
    rectangularity = int(np.count_nonzero(det.Mask)) / float(w * h)
    assert rectangularity >= 0.80, 'silhouette is not a compact plate (%.2f) — shadow absorbed?' % rectangularity


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

    # Two objects 10 px apart (they merge after the closing), with a harsh cast
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
        shipped scale: in Image_001 the round washers and nuts (objects 1, 3, 7, 8) are measured
        as diameters with no angle, and the elongated parts — the blue shape, the red block, the
        terminal strip, the screw and the lattice bracket (2, 4, 5, 6, 9) — as A x B with an angle.
        Of the symmetric four, the two hex nuts (7, 8) report across flats and the two washers
        (1, 3) a round diameter.
        The square plate in Image_006 is NOT reported as a diameter (it is un-elongated, but its
        extent marks it square). Slow because it runs FastSAM; missing weights fail it (it only
        runs under --runslow, which asks for them).
    """

    config = _Configuration(scaled=True)
    require_weights([config.Segmentation.Model_Path])
    import cv2
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')   # masks only, no VLM
    backend = Vision_Pipeline_Cls(Configuration_Str=config)
    folder = config.Evaluation.Frames

    def _Analyze(name):
        frame = cv2.imread(os.path.join(folder, name))
        if frame is None:
            pytest.skip('%s not present in %s' % (name, folder))
        return backend.Analyze(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).Objects

    objects = _Analyze('Image_001.png')
    assert len(objects) == 9
    symmetric = [i + 1 for i, det in enumerate(objects) if det.Measurement.Symmetric]
    assert symmetric == [1, 3, 7, 8]
    across_flats = [i + 1 for i, det in enumerate(objects) if det.Measurement.Across_Flats]
    assert across_flats == [7, 8]
    for det in objects:
        m = det.Measurement
        if m.Symmetric:
            assert m.Diameter_Mm is not None and m.Angle_Deg is None
        else:
            assert m.Width_Mm >= m.Height_Mm and m.Angle_Deg is not None

    square = _Analyze('Image_006.png')[0].Measurement
    assert not square.Symmetric and square.Angle_Deg is not None and square.Angle_Deg < 90.0
