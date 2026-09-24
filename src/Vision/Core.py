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
# File Name: ../Vision/Core.py
## =========================================================================== ##

# System (Default)
import os
import time
import hashlib
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — data structures, composer, and vision utilities
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str, Scale_Str
#   ../Reporting/Core
from Reporting.Core import (Compose, Verdict, Background_Sentence,
                            CONST_EMPTY_SCENE_EXPLANATION, CONST_BACKGROUND_FALLBACK)
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Background_Foreground
#   ../Vision/Utilities/Fusion
from Vision.Utilities.Fusion import Fuse_Objects
#   ../Vision/Utilities/Enhancement
from Vision.Utilities.Enhancement import (Padded_Bbox, Crop, Enhance_Crop, Isolate_Crop,
                                          CONST_ENHANCE_CLIP_LIMIT, CONST_ENHANCE_NEIGHBOUR_DILATE)
#   ../Vision/Segmenter
from Vision.Segmenter import Fast_Sam_Cls
#   ../Vision/Describe_Fallback
from Vision.Describe_Fallback import Describe_Fallback
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Condense_Label
#   ../Vision/Describers
from Vision.Describers import (CONST_DESCRIBERS, CONST_PURPOSE_OBJECT, CONST_PURPOSE_BACKGROUND,
                               Describer_Error_Cls)
#   ../Vision/Utilities/Measure
from Vision.Utilities.Measure import Measure_Objects

"""
Description:
    Initialization of constants.

    The vision pipeline — four stages, one module each (see the flow diagram on
    Florence_Vision_Cls):

        (1) background subtraction   Vision.Utilities.Segmentation.Background_Foreground
                                         -> the background-subtracted foreground mask
        (2) instance segmentation    Vision.Segmenter.Fast_Sam_Cls.Segment
                                         -> per-instance masks + confidences
        (3) fusion                   Vision.Utilities.Fusion.Fuse_Objects
                                         -> FastSAM union OR background mask, split
                                            into the objects, left to right
        (4) description              Vision.Describers (Gemma / Florence) or
                                     Vision.Describe_Fallback.Describe_Fallback
                                         -> a label + sentence per object, from the
                                            alpha/beta-enhanced padded crop
                -> Compose  the numbered lines the panel renders

    The two cues are FUSED, not gated: an object survives if EITHER the FastSAM masks
    or the background-subtracted mask sees it (stage 3), so a part FastSAM misses is
    kept by the difference and a dark part the difference barely sees is kept by
    FastSAM. Every analysis differences the frame against a reference background
    (stage 1), so a reference capture must exist. Masks and boxes are in full-frame
    pixels, so there is no crop-to-frame remap to get wrong. Each object records the
    cue(s) that located it in Detection_Str.Cue; Confidence stays None (see
    KNOWN_ISSUES) and the verdict handles unscored objects.

    Note:
        This module is Qt-free. Analyze accepts an RGB image as a NumPy array; the
        UI owns the QImage <-> array conversion. The describer's runtime (MLX for Gemma,
        torch/transformers for Florence) and OpenCV are imported lazily on the first
        Analyze, so importing this module (as App/run.py does at load time) pulls no
        heavy runtime.
"""
# The empty-surface reference photo. Segmentation is the difference between the
# captured frame and this image, so it must come from the SAME fixed camera and
# match the frame's pixel dimensions exactly. Overridable at runtime (the app's
# --background flag reassigns this module attribute).
CONST_BACKGROUND_REF = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                 'Data', 'Camera', 'Image_Background_001.png'))

# The reading panel's Task row (and the capture set's 'task') when the model-free fallback
# describer wrote the reading; a model describer states its own (Describer_Backend_Cls.Task_Label).
#   Unit [string]
CONST_FALLBACK_TASK_LABEL = 'model-free description'

# The reference is centre-cropped by this margin (fraction per side) before the
# background is described, so the dark vignette at the frame edge does not leak into
# the description of the surface itself.
CONST_BG_CROP_MARGIN = 0.12

# Who writes each object's description (Vision.Describers.CONST_DESCRIBERS): 'gemma' is the
# Gemma 4 vision-language model, prompted; 'florence' is Florence-2, kept reachable so both can
# run over the same frames; 'fallback' is the model-free describer (size / position / aspect /
# solidity / HSV colour), which lets stages 1-3 run and be judged without loading a model.
CONST_DESCRIBER = 'gemma'

# The model name presented to the operator. The describer's weights carry their own licence,
# which is NOT the repository's MIT licence: Gemma is under the Gemma Terms of Use
# (https://ai.google.dev/gemma/terms) and is not redistributable under this repository's
# licence; Florence-2 is MIT (keep Microsoft's notice). See Vision.Describers.
CONST_MODEL_NAME = 'JIC-AnyScan-v1'


class Vision_Error_Cls(RuntimeError):
    """
    Description:
        Raised for anything the operator needs to see on screen. Its message must
        be a full, actionable sentence: it is printed straight into the Scene
        Understanding panel.
    """


class Vision_Backend_Cls(object):
    """
    Description:
        The vision-backend interface. One method matters: Analyze(image) returns
        an Analysis_Str, so a backend swap never touches the caller. progress_cb
        (done, total) and stage_cb(text) are optional hooks the worker thread uses
        to drive the busy indicator; a backend may ignore them.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class (a concrete subclass).
                Cls = Florence_Vision_Cls(scale=scale)

            Features:
                # Functions of the class.
                Cls.Analyze(image_rgb)
    """

    Name = CONST_MODEL_NAME

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None,
                log_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
        """
        Description:
            Analyse one RGB frame and return the finished reading.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame as a contiguous RGB array.
            (2) progress_cb [function]: Optional (done, total) progress hook.
            (3) stage_cb [function]: Optional (text) phase hook.
            (4) log_cb [function]: Optional (level, message) log sink for events worth
                                   recording (e.g. a segmenter mode fallback). The Qt-free
                                   layer emits through it rather than holding the logger.

        Returns:
            (1) parameter [Analysis_Str(object)]: The scene reading.
        """

        raise NotImplementedError


class Florence_Vision_Cls(Vision_Backend_Cls):
    """
    Description:
        The vision backend. It orchestrates the four-stage pipeline and owns the stage-4
        describer (Vision.Describers: Gemma by default, Florence-2 reachable, or the
        model-free fallback); the model is presented as JIC-AnyScan-v1. The describer's
        weights carry their own licence (see CONST_MODEL_NAME). The class keeps its
        historical name until the Florence path is removed.

        Pipeline of Analyze(). Read top to bottom; each stage delegates to the
        module named at the right.

          current frame (RGB)  +  reference background
                   |  (RGB -> BGR)
                   v
          (1) background subtraction ......... Segmentation.Background_Foreground
                   |  the background-subtracted foreground mask
                   |  (absdiff -> blur -> floored Otsu -> open -> dilate);
                   |  one of the two cues fused in stage 3
                   v
          (2) FastSAM segmentation ........... Segmenter.Fast_Sam_Cls
                   |  everything-mode; the other fused cue
                   v
              object masks + segmenter scores
                   |
                   v
          (3) fusion ......................... Fusion.Fuse_Objects
                   |  FastSAM union (background-like masks dropped)
                   |  OR the background mask -> close -> connected
                   |  components -> area filter -> left-to-right.
                   |  An object survives on EITHER cue; each records
                   |  the cue(s) that found it
                   v
              objects: component mask + tight bbox (+ cue, coverage, score)
                   |
                   v
          (4) description .................... Describers.<describer>.Describe
                   |  the alpha/beta-enhanced padded      OR Describe_Fallback
                   |  crop (estimated from object         (per CONST_DESCRIBER;
                   |  pixels, applied to the whole        the fallback reads
                   |  crop) feeds the describer;          mask + bbox directly)
                   v
              Compose -> summary + per-object sentences + verdict
                   |
                   v
              Analysis_Str

        The two cues are fused, not gated: an object survives if EITHER stage 1 or
        stage 2 sees it. Every analysis needs a reference background (stage 1); there
        is no background-free path. Each stage lives in its own module so the heavy
        imports (ultralytics, torch, mlx) stay behind their lazy loaders and this class
        reads as the flow.

        Note:
            Notes that cost hours if missed:
              (1) Every model loads from a local directory, never a hub id; nothing
                  here touches the network at runtime.
              (2) The describer's runtime and OpenCV are imported lazily on the first
                  Analyze, so the window still opens on a machine without them.
              (3) The model loads once and is kept; the first analysis pays a
                  cold-load cost the busy indicator must cover ('Loading model…').
              (4) It emits no confidence scores. Confidence stays None — the
                  verdict handles unscored detections. Never invent a number.
              (5) Boxes are in full-frame pixels whichever detector is used; the
                  per-crop pass only describes. Objects are never reordered after
                  Compose.

    Initialization of the Class:
        Args:
            (1) scale [Scale_Str(object) or None]: REQUIRED, keyword-only: the configured image
                scale (mm/px) that every object is measured with, or None when the configuration
                has no Conversion_Factor — then nothing is measured, never a default.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Florence_Vision_Cls(scale=Read_Conversion_Factor(config_path))

            Features:
                # Functions of the class.
                Cls.Analyze(image_rgb, progress_cb, stage_cb)
    """

    def __init__(self, *, scale: tp.Optional[Scale_Str]) -> None:
        super().__init__()

        # << PRIVATE >> #
        # The image scale the objects are measured with (None: measure nothing).
        self.__scale = scale
        # The describer CONST_DESCRIBER selected (None for the model-free fallback), created and
        # loaded on the first analysis, and the name it was created for.
        self.__describer = None
        self.__describer_name = None
        self.__cv2 = None
        self.__np = None
        # Cached BGR reference array, and the one global background sentence derived
        # from it — cached against the reference image's content hash AND the describer, so a
        # new reference (or another model) re-describes but the same one never re-runs.
        self.__background = None
        self.__background_sentence = None
        self.__background_key = None
        # The stage-2 segmenter. Constructing it is cheap — ultralytics loads lazily
        # on the first Segment, so this keeps the window and the tests light.
        self.__segmenter = Fast_Sam_Cls()

    def __Ensure_Loaded(self, stage_cb: tp.Optional[tp.Callable]) -> None:
        """
        Description:
            Ensure the runtime the selected pipeline needs is imported and cached. cv2/numpy
            are always required (stages 1-3). The describer CONST_DESCRIBER names is created
            and loaded once — the model-free fallback loads none — so stages 1-3 can run
            without a model. Selecting another describer between analyses replaces it. Reports
            the cold load through stage_cb.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
        """

        if self.__cv2 is None:
            try:
                import cv2
                import numpy as np
            except ImportError as exc:
                raise Vision_Error_Cls(
                    'The vision runtime is not installed. Install OpenCV and NumPy '
                    'into this environment, then scan again.'
                ) from exc
            self.__cv2, self.__np = cv2, np

        if CONST_DESCRIBER != self.__describer_name:
            if CONST_DESCRIBER != 'fallback' and CONST_DESCRIBER not in CONST_DESCRIBERS:
                raise Vision_Error_Cls('Unknown describer "%s": choose one of %s or fallback.'
                                       % (CONST_DESCRIBER, ', '.join(CONST_DESCRIBERS)))
            self.__describer = (None if CONST_DESCRIBER == 'fallback'
                                else CONST_DESCRIBERS[CONST_DESCRIBER]())
            self.__describer_name = CONST_DESCRIBER
            self.__background_key = self.__background_sentence = None
        if self.__describer is None or self.__describer.Loaded:
            return
        if stage_cb:
            stage_cb('Loading model…')
        try:
            self.__describer.Load()
        except Describer_Error_Cls as exc:
            raise Vision_Error_Cls(str(exc)) from exc

    def __Load_Background(self, cv2: tp.Any, frame_shape: tp.Tuple[int, int, int]) -> tp.List[tp.List[int]]:
        """
        Description:
            Load and cache the empty-surface reference, and check it matches the
            frame size — the size the pipeline subtracts against.

        Args:
            (1) cv2 [module]: The OpenCV module.
            (2) frame_shape [Tuple<int>]: The frame's (h, w, c) shape.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The reference (BGR).
        """

        if self.__background is None:
            bg = cv2.imread(CONST_BACKGROUND_REF)
            if bg is None:
                raise Vision_Error_Cls(
                    'The background reference at "%s" could not be read. It is the '
                    'empty-surface photo the analysis subtracts from the frame; shoot '
                    'one from this camera and save it there.' % CONST_BACKGROUND_REF
                )
            self.__background = bg
        if self.__background.shape != frame_shape:
            bh, bw = self.__background.shape[:2]
            fh, fw = frame_shape[:2]
            raise Vision_Error_Cls(
                'The background reference is %d×%d but the frame is %d×%d. '
                'Re-shoot the empty-surface reference from this camera so the two '
                'match.' % (bw, bh, fw, fh)
            )
        return self.__background

    def __Describe_Background(self, bg_bgr: tp.List[tp.List[int]]) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
        """
        Description:
            The one global background sentence, generated from the reference frame
            (not from any crop), so it is unaffected by what the model reads into
            individual object crops. The reference is centre-cropped (CONST_BG_CROP_MARGIN)
            to skip the dark vignette and described for the background purpose (Florence's
            concise <CAPTION>, Gemma's background prompt); Reporting.Background_Sentence
            cleans it and falls back to a neutral string (recording a warning) when it is
            empty, multi-sentence or too long.

            The result is cached against the reference image's content hash: the same
            reference never re-runs the model, and a changed reference re-describes.
            When no scene model is loaded (the fallback describer) it returns the
            neutral CONST_BACKGROUND_FALLBACK with a warning, never an empty sentence,
            so the reading always has a background line before the count.

        Args:
            (1) bg_bgr [Matrix<uint8> HxWx3]: The empty-surface reference (BGR).

        Returns:
            (1) parameter [Tuple]: (the background sentence, a Vector of (level,
                                   message) audit records — a warning when the neutral
                                   fallback was used, else empty).
        """

        if self.__describer is None:
            # The fallback describer loads no scene model, so there is no caption —
            # but the reading must never show the count line without a background line
            # first. Use the neutral fallback and record why.
            return CONST_BACKGROUND_FALLBACK, [('warning',
                    'no scene model (fallback describer); used the neutral background sentence')]
        key = hashlib.md5(bg_bgr.tobytes()).hexdigest()
        if key == self.__background_key:
            return self.__background_sentence, []

        cv2 = self.__cv2
        h, w = bg_bgr.shape[:2]
        margin = CONST_BG_CROP_MARGIN
        crop = bg_bgr[int(h * margin):int(h * (1 - margin)), int(w * margin):int(w * (1 - margin))]
        caption = self.__describer.Describe(crop, CONST_PURPOSE_BACKGROUND)
        sentence, records = Background_Sentence(caption)
        self.__background_key, self.__background_sentence = key, sentence
        return sentence, records

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None,
                log_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
        """
        Description:
            Analyse one RGB frame and return the finished reading. The default path is
            the four-stage pipeline below, read top to bottom; each stage delegates to
            its own module (see the class docstring's pipeline overview). The frame is
            a contiguous RGB array (the UI converts the QImage), so this never touches Qt.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame as a contiguous RGB array.
            (2) progress_cb [function]: Optional (done, total) progress hook.
            (3) stage_cb [function]: Optional (text) phase hook.
            (4) log_cb [function]: Optional (level, message) log sink.

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        t0 = time.perf_counter()
        # The describer's model is loaded only when one writes the descriptions; the
        # model-free fallback describer needs none.
        self.__Ensure_Loaded(stage_cb)
        cv2, np = self.__cv2, self.__np
        size = (image.shape[1], image.shape[0])   # (width, height)

        # RGB -> BGR: the pipeline works in BGR, the exchange format is RGB.
        frame_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # ---- Stage 1 - background subtraction (Vision.Utilities.Segmentation) ----
        # The background-subtracted foreground mask: one of the two cues fused in
        # stage 3. Pure cv2/np differencing, so it lives in Segmentation, not here.
        bg_bgr = self.__Load_Background(cv2, frame_bgr.shape)
        background_fg = Background_Foreground(bg_bgr, frame_bgr, cv2, np)

        # ---- Stage 2 - instance segmentation (Vision.Segmenter) ----
        # FastSAM in everything-mode behind the Segmenter_Backend_Cls seam: the other
        # fused cue. In its own module so the lazy ultralytics import keeps a bare Core
        # import Qt-free and cheap. No region prompts — everything-mode separates parts.
        masks, scores = self.__segmenter.Segment(frame_bgr, [], stage_cb, log_cb)

        # ---- Stage 3 - fusion (Vision.Utilities.Fusion) ----
        # The objects: the FastSAM union OR the background mask, closed, split into
        # connected components, area-filtered and ordered left to right. An object
        # survives on EITHER cue; each records the cue(s) that located it.
        objects = Fuse_Objects(masks, scores, background_fg, cv2, np)

        # ---- Stage 4 - description (Vision.Describers / Vision.Describe_Fallback) ----
        # One caption per object, from the alpha/beta-enhanced padded crop: neighbours
        # are masked out (filled from the reference) so the crop holds one object plus
        # table, and the stretch is estimated from the object's own pixels.
        self.__Describe_Objects(objects, frame_bgr, bg_bgr, progress_cb, stage_cb)

        # The one global background sentence, from the reference (cached across frames).
        background_sentence, background_audit = self.__Describe_Background(bg_bgr)
        result = self.__Compose_Result(objects, size, t0, len(masks),
                                       background_sentence, background_audit)
        # Measure every masked object through the configured scale (none without one).
        Measure_Objects(result.Objects, self.__scale, cv2, np)
        return result

    def __Describe_Objects(self, objects: tp.List[Detection_Str], frame_bgr: tp.List[tp.List[int]],
                           bg_bgr: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable],
                           stage_cb: tp.Optional[tp.Callable]) -> None:
        """
        Description:
            Stage 4: fill each object's Label and Detail from its crop. The padded crop
            has every OTHER object's pixels replaced by the empty-surface reference, so
            it holds one object plus the table and no neighbours, then it is contrast/
            brightness-stretched (the gain/bias estimated from the object's own pixels,
            the surround blended most of the way back to natural) and fed to the
            describer — Gemma, Florence-2 or the model-free fallback (CONST_DESCRIBER). The
            enhanced crop is retained on the object (Enhanced_Crop) so the debug montage
            shows exactly what the model received, without re-enhancing it.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The stage-3 objects (mutated).
            (2) frame_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
            (3) bg_bgr [Matrix<uint8> HxWx3]: The empty-surface reference (BGR).
            (4) progress_cb [function]: Optional (done, total) progress hook.
            (5) stage_cb [function]: Optional (text) phase hook.
        """

        cv2, np = self.__cv2, self.__np
        if stage_cb and objects:
            stage_cb('Describing…')

        # The union of every object's mask, so each crop can subtract its neighbours.
        all_mask = np.zeros(frame_bgr.shape[:2], dtype=bool)
        for det in objects:
            all_mask |= det.Mask.astype(bool)
        dilate_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (CONST_ENHANCE_NEIGHBOUR_DILATE, CONST_ENHANCE_NEIGHBOUR_DILATE))

        total = len(objects)
        for i, det in enumerate(objects):
            if progress_cb:
                progress_cb(i, total)
            # The padded crop with neighbours removed (filled from the reference), and
            # the object's mask within it, so the stretch is estimated from object
            # pixels and the surround is a clean table, not another part. Each other
            # object's mask is grown before subtracting, so its bright edge goes too.
            own = det.Mask.astype(bool)
            others = cv2.dilate((all_mask & ~own).astype(np.uint8), dilate_kernel).astype(bool) & ~own
            padded = Padded_Bbox(det.Bbox, frame_bgr.shape)
            mask_crop = Crop(det.Mask, padded)
            others_crop = Crop(others, padded)
            isolated = Isolate_Crop(Crop(frame_bgr, padded), Crop(bg_bgr, padded),
                                    mask_crop, others_crop, np)
            enhanced = Enhance_Crop(isolated, mask_crop, CONST_ENHANCE_CLIP_LIMIT, cv2, np)
            det.Enhanced_Crop = enhanced
            if self.__describer is None:
                det.Label, det.Detail = Describe_Fallback(
                    frame_bgr, det.Mask, det.Bbox, frame_bgr.shape, cv2, np)
            else:
                det.Detail = self.__describer.Describe(enhanced, CONST_PURPOSE_OBJECT)
                det.Label = Condense_Label(det.Detail)
        if progress_cb:
            progress_cb(total, total)

    def __Compose_Result(self, objects: tp.List[Detection_Str], size: tp.Tuple[int, int],
                         t0: float, raw_mask_count: int, background_sentence: str,
                         background_audit: tp.List[tp.Tuple[str, str]]) -> Analysis_Str:
        """
        Description:
            Compose the panel's reading from the described objects: the per-object
            sentences, the summary, the note, the verdict badge, the latency, the global
            background sentence and its audit. The objects are never
            reordered here — their order is the index contract.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The described objects, in order.
            (2) size [Vector<int> 1x2]: The frame size as (width, height).
            (3) t0 [float]: The analysis start time (perf_counter).
            (4) raw_mask_count [int]: The raw segmenter mask count (a diagnostic).
            (5) background_sentence [string]: The one global background description.
            (6) background_audit [Vector<Tuple<string> 1x2>]: The background-caption audit.

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        caption = '' if objects else CONST_EMPTY_SCENE_EXPLANATION
        objects, note = Compose(objects, size, caption=caption)
        badge, level = Verdict(objects)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return Analysis_Str(Objects=objects, Note=note,
                            Latency_Ms=latency_ms, Verdict=badge, Verdict_Level=level,
                            Task=(self.__describer.Task_Label if self.__describer is not None
                                  else CONST_FALLBACK_TASK_LABEL),
                            Raw_Mask_Count=raw_mask_count,
                            Background=background_sentence, Audit=background_audit)
