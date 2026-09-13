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
# File Name: ../test/integration/test_pipeline.py
## =========================================================================== ##

# System (Default)
import os
import warnings
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the camera and vision backends, the result structure
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Florence_Vision_Cls
#   ../Vision/Segmenter
import Vision.Segmenter as Vision_Segmenter
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str

"""
Description:
    End-to-end pipeline integration tests: acquire a frame -> detect -> describe ->
    compose the report, exercising the modules together across their seams. The
    default test is hermetic (a File_Camera_Cls source and a fake backend, no camera
    and no weights). A second test runs the same flow through the real Florence-2 on
    the CPU whenever the weights exist, and warns loudly (never fails) when they do
    not, so the real path is covered by default without breaking a fresh clone.
"""

# Two rectangles drawn onto the reference to synthesize a frame with real objects.
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]


def test_pipeline_camera_to_reporting(reference_background_path, fake_backend) -> None:
    """
    Description:
        The full wiring with the hermetic fake backend: File_Camera_Cls captures an
        RGB frame, the backend accepts it directly, and the reading is composed
        through the real Reporting. Asserts the seams — the composed sentences (the
        fake's Florence-style detail is cleaned by Reporting) and the verdict from
        the low-confidence object.
    """

    camera = File_Camera_Cls(reference_background_path)
    camera.Connect()
    frame = camera.Capture()

    result = fake_backend.Analyze(frame)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == 2
    # Reporting composed each sentence, stripping the Florence lead-in.
    assert result.Objects[0].Sentence == 'A hex bolt on a green surface.'
    assert all(o.Sentence for o in result.Objects)
    assert result.Summary == 'The frame contains two objects, which are described as follows:'
    # The 0.2-confidence object drives the verdict.
    assert (result.Verdict, result.Verdict_Level) == ('Low confidence', 'warn')

    camera.Disconnect()
    assert not camera.Connected


def _Warn_Weights_Absent(request) -> None:
    """
    Description:
        Emit an impossible-to-miss warning that the real vision path was not verified
        because the model weights are absent — a loud banner written straight to the
        terminal (uncaptured) plus a pytest warning, not a quiet skip line.

    Args:
        (1) request [pytest.FixtureRequest(object)]: The request, for the terminal reporter.
    """

    message = ('MODEL WEIGHTS ABSENT: the real FastSAM + Florence-2 vision path was NOT '
               'verified. Download them (see README > Setup), then re-run `pytest` to cover Analyze().')
    warnings.warn(UserWarning(message))
    reporter = request.config.pluginmanager.getplugin('terminalreporter')
    if reporter is not None:
        reporter.write_line('')
        reporter.write_sep('!', 'REAL VISION PATH NOT VERIFIED - model weights absent',
                           red=True, bold=True)
        reporter.write_line('  ' + message, yellow=True)
        reporter.write_sep('!', red=True, bold=True)


def test_pipeline_real_florence_smoke(request, reference_background, make_synthetic_frame,
                                      monkeypatch) -> None:
    """
    Description:
        The real four-stage vision path — background subtraction -> FastSAM
        segmentation -> mask filtering -> Florence-2 description -> compose — through
        the real Florence_Vision_Cls on a synthetic two-rectangle frame, forced onto
        the CPU so it is portable and deterministic (no CUDA/MPS dependency). It runs
        in the DEFAULT suite whenever BOTH the FastSAM and Florence-2 weights exist;
        when either is absent it warns loudly and passes, so a fresh clone is never
        broken before the weights are downloaded.

        Structural assertions only — object count and box bounds come from the
        deterministic scene, and every described object has a non-empty sentence. The
        caption text itself is never asserted (it is not deterministic).
    """

    if not (os.path.isdir(Vision_Core.CONST_MODEL_DIR)
            and os.path.isfile(Vision_Segmenter.CONST_SEGMENTER_WEIGHTS)):
        _Warn_Weights_Absent(request)
        return

    # Force the CPU so the smoke behaves identically on every machine — both the
    # Florence describer and the FastSAM segmenter.
    monkeypatch.setattr(Vision_Core, 'CONST_VISION_DEVICE', 'cpu')
    monkeypatch.setattr(Vision_Segmenter, 'CONST_SEGMENTER_DEVICE', 'cpu')

    # OpenCV library for computer vision tasks [pip3 install opencv-python]
    import cv2

    frame_bgr = make_synthetic_frame(reference_background, CONST_RECTS)
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = image_rgb.shape[:2]

    result = Florence_Vision_Cls().Analyze(image_rgb)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == len(CONST_RECTS)
    for obj in result.Objects:
        x, y, bw, bh = obj.Bbox
        # Box is inside the image dimensions.
        assert 0 <= x and 0 <= y
        assert x + bw <= w and y + bh <= h
        # A described object always has a sentence; its exact words are not asserted.
        assert obj.Sentence
    assert result.Summary
    assert result.Latency_Ms >= 0


@pytest.mark.slow
def test_shadow_rejected_on_real_capture(request, monkeypatch, reference_background_path) -> None:
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
        because it runs FastSAM; skips when the weights or the frame are absent.
    """

    if not os.path.isfile(Vision_Segmenter.CONST_SEGMENTER_WEIGHTS):
        _Warn_Weights_Absent(request)
        return
    frame_path = os.path.join(os.path.dirname(reference_background_path), 'Image_004.png')
    if not os.path.isfile(frame_path):
        pytest.skip('Image_004.png not present at %s' % frame_path)

    import cv2
    import numpy as np
    monkeypatch.setattr(Vision_Segmenter, 'CONST_SEGMENTER_DEVICE', 'cpu')
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')   # count/mask only, no VLM

    scene_bgr = cv2.imread(frame_path)
    result = Florence_Vision_Cls().Analyze(cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2RGB))

    assert len(result.Objects) == 1
    det = result.Objects[0]
    x, y, w, h = det.Bbox
    rectangularity = int(np.count_nonzero(det.Mask)) / float(w * h)
    assert rectangularity >= 0.80, 'silhouette is not a compact plate (%.2f) — shadow absorbed?' % rectangularity


@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason='a shadow far darker/larger than any real capture is still '
                                       'absorbed into the component; see KNOWN_ISSUES.md')
def test_synthetic_harsh_shadow_not_absorbed_xfail(monkeypatch) -> None:
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
        entry. Uses pytest.skip (not an early return) when weights are absent, so a
        skip is never mistaken for an unexpected pass.
    """

    if not os.path.isfile(Vision_Segmenter.CONST_SEGMENTER_WEIGHTS):
        pytest.skip('FastSAM weights absent')

    import cv2
    import numpy as np
    from Vision.Utilities.Segmentation import Background_Foreground
    from Vision.Utilities.Fusion import Fuse_Objects
    from Vision.Segmenter import Fast_Sam_Cls
    monkeypatch.setattr(Vision_Segmenter, 'CONST_SEGMENTER_DEVICE', 'cpu')

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

    background_fg = Background_Foreground(bg, scene, cv2, np)
    masks, scores = Fast_Sam_Cls(device='cpu').Segment(scene, [])
    objects = Fuse_Objects(masks, scores, background_fg, cv2, np)

    # Desired: no object's mask reaches past the parts (bottom edge y=520) into the
    # shadow band. Currently one object extends to ~y=641, so this fails (xfail).
    bottom = max((y + bh for (x, y, bw, bh) in (o.Bbox for o in objects)), default=0)
    assert bottom <= 545
