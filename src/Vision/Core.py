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
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
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
from Vision.Segmenter import Fast_Sam_Cls, Segmenter_Error_Cls
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
    Vision_Pipeline_Cls):

        (1) background subtraction   Vision.Utilities.Segmentation.Background_Foreground
                                         -> the background-subtracted foreground mask
        (2) instance segmentation    Vision.Segmenter.Fast_Sam_Cls.Segment
                                         -> per-instance masks + confidences
        (3) fusion                   Vision.Utilities.Fusion.Fuse_Objects
                                         -> FastSAM union OR background mask, split
                                            into the objects, left to right
        (4) description              Vision.Describers (Gemma) or
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
    docs/design-decisions.md, 'Verdict's confidence branch stays dormant') and the verdict handles unscored objects.

    Note:
        This module is Qt-free. Analyze accepts an RGB image as a NumPy array; the
        UI owns the QImage <-> array conversion. The describer's runtime (MLX) and
        OpenCV are imported lazily on the first Analyze, so importing this module (as App/run.py does at load time) pulls no
        heavy runtime.
"""
# The empty-surface reference is configuration (Segmentation.Background.Reference): it must come
# from the SAME fixed camera and match the frame's pixel dimensions exactly.

# The reading panel's Task row (and the capture set's 'task') when the model-free fallback
# describer wrote the reading; a model-written reading carries the configuration's Identity.Task.
#   Unit [string]
CONST_FALLBACK_TASK_LABEL = 'model-free description'

# Who writes each object's description (Vision.Describers.CONST_DESCRIBERS): 'gemma' is the
# Gemma 4 vision-language model, prompted; 'fallback' is the model-free describer (size /
# position / aspect / solidity / HSV colour), which lets stages 1-3 run and be judged without
# loading a model (the weight-free tests use it).
CONST_DESCRIBER = 'gemma'

# What the models are presented as to the operator is configuration (Identity.Model_Set). The describer's
# weights carry their own licence, which is NOT the repository's MIT licence: Gemma 4 is under the
# Apache License 2.0 (https://ai.google.dev/gemma/docs/gemma_4_license), which this repository's
# licence does not cover. See Vision.Describers.


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
                Cls = Vision_Pipeline_Cls(Configuration_Str=Configuration_Str)

            Features:
                # Functions of the class.
                Cls.Analyze(image_rgb)
    """

    # What the window reads from any backend: the presented name, the two model names, and whether
    # the models are loaded. A backend with nothing to load (a test stand-in) is always loaded.
    Name = ''
    Model_Names = ('', '')
    Models_Loaded = True

    def Load_Models(self, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Load the models now, so no analysis pays for them. A backend without models does
            nothing.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
        """

    def Configure(self, Configuration_Str: Configuration_Str,
                  stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Put another configuration in force and load its models. A backend without
            configuration does nothing.

        Args:
            (1) Configuration_Str [Configuration_Str(object)]: The configuration.
            (2) stage_cb [function]: Optional (text) phase hook.
        """

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
        """
        Description:
            Analyse one RGB frame and return the finished reading.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame as a contiguous RGB array.
            (2) progress_cb [function]: Optional (done, total) progress hook.
            (3) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Analysis_Str(object)]: The scene reading.
        """

        raise NotImplementedError


class Vision_Pipeline_Cls(Vision_Backend_Cls):
    """
    Description:
        The vision backend. It orchestrates the four-stage pipeline and owns the stage-4
        describer (Vision.Describers: Gemma, or the model-free fallback); the model is
        presented under the configuration's model set (Identity.Model_Set). Every stage reads its parameters
        from the one Configuration_Str it holds; Configure swaps it for another.

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
              Compose -> per-object sentences + note + verdict  (Reporting.Compose)
                   |
                   v
              measurement ........................ Measure.Measure_Objects
                   |  each mask through the configured scale (none without one)
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
              (2) The describer's runtime and OpenCV are imported lazily, so the window
                  still opens on a machine without them.
              (3) The models load once and are kept. The application preloads them
                  (Load_Models / Configure: a configuration load or the first CONNECT), so an
                  analysis never pays the ~9 s cold load; a caller that skips the preload (the
                  harness, a test) pays it on the first Analyze instead.
              (6) Configure releases a model that changes BEFORE loading its replacement, so
                  two describers are never held at once (~9.4 GB each would not fit a 17 GB
                  machine). The cost: when the replacement fails, the previous configuration's
                  model must be loaded again.
              (4) The only score is FastSAM's, carried per object as Segmenter_Score;
                  an object the background cue alone found has None there, and
                  Detection_Str.Confidence stays None for every object. Never invent a
                  number for an unscored object.
              (5) Boxes are in full-frame pixels whichever detector is used; the
                  per-crop pass only describes. Objects are never reordered after
                  Compose.

    Initialization of the Class:
        Args:
            (1) Configuration_Str [Configuration_Str(object)]: REQUIRED, keyword-only: the loaded
                configuration — the stages' parameters, the models, the task label, and the
                scale (mm/px) objects are measured with (None: nothing is measured, never a
                default).

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Vision_Pipeline_Cls(Configuration_Str=Load_Configuration(config_path))

            Features:
                # Properties of the class.
                Cls.Name; Cls.Model_Names; Cls.Models_Loaded

                # Functions of the class.
                Cls.Load_Models(stage_cb); Cls.Configure(Configuration_Str, stage_cb)
                Cls.Analyze(image_rgb, progress_cb, stage_cb)
    """

    def __init__(self, *, Configuration_Str: Configuration_Str) -> None:
        super().__init__()

        # << PRIVATE >> #
        # The configuration in force: every stage's parameters, the models, the scale.
        self.__config = Configuration_Str
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
        # (Load_Models or the first Segment), so this keeps the window and the tests light.
        self.__segmenter = Fast_Sam_Cls(Configuration_Str.Segmentation)

    @property
    def Name(self) -> str:
        """
        Description:
            What the models are presented as: the configuration's model set (Identity.Model_Set).

        Returns:
            (1) parameter [string]: The name.
        """

        return self.__config.Identity.Model_Set

    @property
    def Model_Names(self) -> tp.Tuple[str, str]:
        """
        Description:
            The two models of the configuration in force, by their file / directory names.

        Returns:
            (1) parameter [Tuple<string> 1x2]: (the segmenter's, the describer's).
        """

        return (os.path.basename(self.__config.Segmentation.Model_Path),
                os.path.basename(self.__config.Description.Model_Path))

    @property
    def Models_Loaded(self) -> bool:
        """
        Description:
            Whether every model the configuration needs is loaded (the model-free fallback
            describer needs none), so the next analysis will not pay a cold load.

        Returns:
            (1) parameter [bool]: True when an analysis can start without loading a model.
        """

        describer_ready = (CONST_DESCRIBER == 'fallback'
                           or (CONST_DESCRIBER == self.__describer_name
                               and self.__describer is not None and self.__describer.Loaded))
        return self.__segmenter.Loaded and describer_ready

    def Load_Models(self, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Load the configuration's models now — the segmenter, then the describer — so no
            analysis pays for them. A model already loaded is kept.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook ('Loading segmenter…', …).

        Raises:
            Vision_Error_Cls: A model could not be loaded; the message says which and why.
        """

        try:
            self.__segmenter.Load(stage_cb)
        except Segmenter_Error_Cls as exc:
            raise Vision_Error_Cls(str(exc)) from exc
        self.__Ensure_Loaded(stage_cb)

    def Configure(self, Configuration_Str: Configuration_Str,
                  stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Put another (already validated) configuration in force and load its models. A model
            whose identity is unchanged (the same weights, and for FastSAM the same device) is
            kept and only its per-call parameters change — no reload. A model that changes is
            RELEASED FIRST and its replacement loaded after, so two are never held at once.

            When the new models cannot be loaded, the previous configuration is put back in
            force. Its models are reloaded if they were loaded before (they were released to
            make room, so this costs the load time again), and the error says whether it is loaded.

        Args:
            (1) Configuration_Str [Configuration_Str(object)]: The configuration to put in force.
            (2) stage_cb [function]: Optional (text) phase hook.

        Raises:
            Vision_Error_Cls: The new models could not be loaded. The previous configuration is
                              in force; the message says whether its models were reloaded.
        """

        new = Configuration_Str
        previous = (self.__config, self.__segmenter, self.__describer, self.__describer_name)
        previous_loaded = self.Models_Loaded
        old_config, old_segmenter, old_describer, _old_name = previous

        # 1\ Keep a model whose identity is unchanged; release one that changes BEFORE loading.
        if old_segmenter.Model_Key == (new.Segmentation.Model_Path, new.Segmentation.Device):
            segmenter = old_segmenter
            segmenter.Set_Parameters(new.Segmentation)
        else:
            old_segmenter.Release()
            segmenter = Fast_Sam_Cls(new.Segmentation)
        describer = old_describer
        if describer is not None and describer.Model_Key == new.Description.Model_Path:
            describer.Set_Parameters(new.Description)
        elif describer is not None:
            describer.Release()
            describer = None
        self.__config, self.__segmenter, self.__describer = new, segmenter, describer
        if describer is None:
            self.__describer_name = None

        # 2\ Load the new configuration's models; on failure, put the previous one back.
        try:
            self.Load_Models(stage_cb)
        except Vision_Error_Cls as exc:
            if self.__segmenter is not old_segmenter:
                self.__segmenter.Release()
            if self.__describer is not None and self.__describer is not old_describer:
                self.__describer.Release()
            self.__config, self.__segmenter, self.__describer, self.__describer_name = previous
            old_segmenter.Set_Parameters(old_config.Segmentation)
            if old_describer is not None:
                old_describer.Set_Parameters(old_config.Description)
            # The reason, then what is in force — in configuration terms: the models are how a
            # configuration is loaded, not something the operator chooses.
            reason = str(exc).rstrip('.') + '.'
            previous = old_config.Identity.Display_Name
            if not previous_loaded:
                raise Vision_Error_Cls('%s %s is still in force, not loaded.' % (reason, previous)) from exc
            if stage_cb:
                stage_cb('Reloading the previous configuration…')
            try:
                self.Load_Models(stage_cb)
            except Vision_Error_Cls as again:
                raise Vision_Error_Cls('%s %s is still in force but could not be loaded again (%s).'
                                       % (reason, previous, str(again).rstrip('.'))) from exc
            # Its models were released to make room for the new ones, so they were loaded again —
            # that reload is the extra wait the operator saw.
            raise Vision_Error_Cls('%s %s is still in force and was loaded again.' % (reason, previous)) from exc

        # 3\ Committed: the reference may differ, and the background sentence depends on it, the
        #    prompt, the crop margin and the limits — both are read again under the new configuration.
        self.__background = None
        self.__background_key = self.__background_sentence = None

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
                raise Vision_Error_Cls('Unknown describer "%s": choose %s or fallback.'
                                       % (CONST_DESCRIBER, ', '.join(CONST_DESCRIBERS)))
            self.__describer = (None if CONST_DESCRIBER == 'fallback'
                                else CONST_DESCRIBERS[CONST_DESCRIBER](self.__config.Description))
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
            reference = self.__config.Segmentation.Background_Reference
            bg = cv2.imread(reference)
            if bg is None:
                raise Vision_Error_Cls(
                    'The background reference at "%s" could not be read. It is the '
                    'empty-surface photo the analysis subtracts from the frame; shoot '
                    'one from this camera and set Segmentation.Background.Reference to it.' % reference
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
            individual object crops. The reference is centre-cropped (Background_Crop_Margin)
            to skip the dark vignette and described for the background purpose (the
            background prompt); Reporting.Background_Sentence
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

        h, w = bg_bgr.shape[:2]
        margin = self.__config.Description.Background_Crop_Margin
        crop = bg_bgr[int(h * margin):int(h * (1 - margin)), int(w * margin):int(w * (1 - margin))]
        caption = self.__describer.Describe(crop, CONST_PURPOSE_BACKGROUND)
        sentence, records = Background_Sentence(caption, Description_Parameters_Str=self.__config.Description)
        self.__background_key, self.__background_sentence = key, sentence
        return sentence, records

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
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

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        t0 = time.perf_counter()
        # The describer's model is loaded only when one writes the descriptions; the
        # model-free fallback describer needs none.
        self.__Ensure_Loaded(stage_cb)
        cv2, np = self.__cv2, self.__np

        # RGB -> BGR: the pipeline works in BGR, the exchange format is RGB.
        frame_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # ---- Stage 1 - background subtraction (Vision.Utilities.Segmentation) ----
        # The background-subtracted foreground mask: one of the two cues fused in
        # stage 3. Pure cv2/np differencing, so it lives in Segmentation, not here.
        bg_bgr = self.__Load_Background(cv2, frame_bgr.shape)
        background_fg = Background_Foreground(bg_bgr, frame_bgr, cv2, np,
                                              Segmentation_Parameters_Str=self.__config.Segmentation)

        # ---- Stage 2 - instance segmentation (Vision.Segmenter) ----
        # FastSAM on the whole frame, behind the Segmenter_Backend_Cls seam: the other fused cue.
        # In its own module so the lazy ultralytics import keeps a bare Core import Qt-free and
        # cheap. Segmenting the whole frame is what separates touching parts.
        masks, scores = self.__segmenter.Segment(frame_bgr, stage_cb)

        # ---- Stage 3 - fusion (Vision.Utilities.Fusion) ----
        # The objects: the FastSAM union OR the background mask, closed, split into
        # connected components, area-filtered and ordered left to right. An object
        # survives on EITHER cue; each records the cue(s) that located it.
        objects = Fuse_Objects(masks, scores, background_fg, cv2, np,
                               Segmentation_Parameters_Str=self.__config.Segmentation)

        # ---- Stage 4 - description (Vision.Describers / Vision.Describe_Fallback) ----
        # One caption per object, from the alpha/beta-enhanced padded crop: neighbours
        # are masked out (filled from the reference) so the crop holds one object plus
        # table, and the stretch is estimated from the object's own pixels.
        self.__Describe_Objects(objects, frame_bgr, bg_bgr, progress_cb, stage_cb)

        # The one global background sentence, from the reference (cached across frames).
        background_sentence, background_audit = self.__Describe_Background(bg_bgr)
        result = self.__Compose_Result(objects, t0, len(masks),
                                       background_sentence, background_audit)
        # Measure every masked object through the configured scale (none without one).
        Measure_Objects(result.Objects, self.__config.Scale, cv2, np)
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
            describer — Gemma or the model-free fallback (CONST_DESCRIBER). The
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
            padded = Padded_Bbox(det.Bbox, frame_bgr.shape, self.__config.Description.Object_Crop_Padding)
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

    def __Compose_Result(self, objects: tp.List[Detection_Str],
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
            (2) t0 [float]: The analysis start time (perf_counter).
            (3) raw_mask_count [int]: The raw segmenter mask count (a diagnostic).
            (4) background_sentence [string]: The one global background description.
            (5) background_audit [Vector<Tuple<string> 1x2>]: The background-caption audit.

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        caption = '' if objects else CONST_EMPTY_SCENE_EXPLANATION
        objects, note = Compose(objects, caption=caption)
        badge, level = Verdict(objects)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return Analysis_Str(Objects=objects, Note=note,
                            Latency_Ms=latency_ms, Verdict=badge, Verdict_Level=level,
                            Task=(self.__config.Identity.Task if self.__describer is not None
                                  else CONST_FALLBACK_TASK_LABEL),
                            Raw_Mask_Count=raw_mask_count,
                            Background=background_sentence, Audit=background_audit)
