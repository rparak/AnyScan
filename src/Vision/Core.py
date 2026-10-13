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
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — data structures, composer, and vision utilities
#   ../Parameters/Vision
from Parameters.Vision import (Detection_Str, Analysis_Str, Heatmap_Str, Load_Timing_Str, Model_Load_Str, Feature_Str,
                               CONST_STAGE_BACKGROUND, CONST_STAGE_SEGMENTATION, CONST_STAGE_SEGMENTATION_POST,
                               CONST_STAGE_FUSION, CONST_STAGE_CROPS, CONST_STAGE_DESCRIPTIONS,
                               CONST_STAGE_BACKGROUND_SENTENCE, CONST_STAGE_COMPOSE)
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
#   ../Reporting/Core
from Reporting.Core import (Compose, Verdict, Background_Sentence, Side_Sentence, Describer_Prompt, Guard_Description,
                            CONST_EMPTY_SCENE_EXPLANATION, CONST_BACKGROUND_FALLBACK)
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Background_Difference, Foreground_Mask, CONST_DIFFERENCE_SCALE_MAX
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
from Vision.Describers import (Gemma_Describer_Cls, CONST_PURPOSE_OBJECT, CONST_PURPOSE_BACKGROUND,
                               Describer_Error_Cls)
#   ../Vision/Utilities/Measure
from Vision.Utilities.Measure import Measure_Objects
#   ../Vision/Utilities/Dimensions
from Vision.Utilities.Dimensions import Check_Objects
#   ../Vision/Identifier
from Vision.Identifier import Dino_Identifier_Cls, Identifier_Error_Cls
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import (Object_Crop, Reference_Crop, Rotations, Best_Match, Best_Turn, Similarity_Grid,
                                       Classify, Apply_Holes, Apply_Stain, Crop_To_Frame)
#   ../Vision/Utilities/Holes
from Vision.Utilities.Holes import Hole_Candidates, Check_Holes, Hole_Features
#   ../Vision/Utilities/Stain
from Vision.Utilities.Stain import Check_Stain
#   ../Vision/Utilities/Timing
from Vision.Utilities.Timing import Build_Timing

"""
Description:
    Initialization of constants.

    The vision pipeline — four stages, one module each (see the flow diagram on
    Vision_Pipeline_Cls):

        (1) background subtraction   Vision.Utilities.Segmentation (Background_Difference, Foreground_Mask)
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
        OpenCV are imported when the models load (Load_Models / Configure), so importing
        this module (as App/run.py does at load time) pulls no heavy runtime.
"""
# The empty-surface reference is the station's (Background.Reference in its station file): it must come
# from the SAME fixed camera and match the frame's pixel dimensions exactly.

# The reading panel's Task row (and the capture set's 'task') when the model-free fallback
# describer wrote the reading; a model-written reading carries the configuration's Identity.Task.
#   Unit [string]
CONST_FALLBACK_TASK_LABEL = 'model-free description'

# Who writes each object's description: 'gemma' is the
# Gemma 4 vision-language model, prompted; 'fallback' is the model-free describer (size /
# position / aspect / solidity / HSV colour), which lets stages 1-3 run and be judged without
# loading a model. A code constant, deliberately not configuration: one describer ships. The
# harness (analyze.py --no-describe) and the weight-free tests set it; the application never does.
CONST_DESCRIBER = 'gemma'
# The similarity overlay's colour scale, unlikeness (1 - cosine) from 0 to this. Measured at the 224 px input
# on the test set's 22 mounting plates (2026-10-13): a clean plate's patches' mean 0.01-0.16, a stained one's
# 0.19-0.25, the fingerprints' up to 0.63 (their 99th percentile 0.55-0.61); 0.5 keeps them apart without
# saturating.
#   Unit [float]
CONST_SIMILARITY_SCALE_MAX = 0.5

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

    # What the window reads from any backend: the presented name, the two model names, whether
    # the models are loaded, and where the last load's time went (None: not timed). A backend with
    # nothing to load (a test stand-in) is always loaded.
    Name = ''
    Model_Names = ('', '')
    Models_Loaded = True
    Load_Timing = None

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
          (1) background subtraction ......... Segmentation.Background_Difference, Foreground_Mask
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
              objects: component mask + tight bbox (+ cue, score)
                   |
                   v
          (4) description .................... Describers.<describer>.Describe
                   |  the alpha/beta-enhanced padded      OR Describe_Fallback
                   |  crop (estimated from and given to   (per CONST_DESCRIBER;
                   |  the object's pixels, the surround   the fallback reads
                   |  left natural) feeds the describer;  mask + bbox directly)
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
                Cls.Name; Cls.Model_Names; Cls.Models_Loaded; Cls.Load_Timing

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
        # loaded by Load_Models (or by the first analysis, when never preloaded), and the name it
        # was created for.
        self.__describer = None
        self.__describer_name = None
        self.__cv2 = None
        self.__np = None
        # Cached BGR reference array, and the one global background sentence derived from it.
        # Both are cleared by Configure and the sentence by a change of describer, so a new
        # reference (or another model) re-describes but the same one never re-runs. The sentence's
        # audit records wait here until the first analysis that carries the sentence.
        self.__background = None
        self.__background_sentence = None
        self.__background_audit = []
        # The stage-2 segmenter. Constructing it is cheap — ultralytics loads lazily
        # (Load_Models or the first Segment), so this keeps the window and the tests light.
        self.__segmenter = Fast_Sam_Cls(Configuration_Str.Segmentation)
        # A catalogue mode's identifier (None in any other mode), as cheap to construct, and the catalogue
        # item's reference images as unit rows with their sides — embedded once per configuration
        # (__Reference_Rows), cleared by Configure.
        self.__identifier = self.__New_Identifier(Configuration_Str)
        self.__reference_rows = None
        self.__reference_patches = None
        self.__reference_sides = []
        # Where the last Load_Models (and the warm-up after it) spent its time, and whether the next
        # analysis is the first since the models were put in force (see Analyze).
        self.__load_timing = None
        self.__first_after_load = True

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
        identifier_ready = self.__identifier is None or self.__identifier.Loaded
        return self.__segmenter.Loaded and describer_ready and identifier_ready

    @property
    def Load_Timing(self) -> tp.Optional[Load_Timing_Str]:
        """
        Description:
            Where the last successful Load_Models spent its time — each model's load, or that it was
            kept — and, after a Configure, the warm-up's parts. The window logs it when a
            configuration has loaded.

        Returns:
            (1) parameter [Load_Timing_Str(object) or None]: The timing, or None before any load.
        """

        return self.__load_timing

    def Load_Models(self, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Load the configuration's models now — the segmenter, then the describer — so no
            analysis pays for them. A model already loaded is kept, and recorded as kept (no time),
            never as a load. A successful call starts a fresh Load_Timing and marks the next
            analysis as the first after a load.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook ('Loading segmenter…', …).

        Raises:
            Vision_Error_Cls: A model could not be loaded; the message says which and why.
        """

        segmenter_name, describer_name = self.Model_Names
        segmenter_kept = self.__segmenter.Loaded
        started = time.perf_counter()
        try:
            self.__segmenter.Load(stage_cb)
        except Segmenter_Error_Cls as exc:
            raise Vision_Error_Cls(str(exc)) from exc
        timing = Load_Timing_Str(Models=[Model_Load_Str(
            Name=segmenter_name, Seconds=None if segmenter_kept else time.perf_counter() - started)])
        if self.__identifier is not None:
            identifier_kept = self.__identifier.Loaded
            started = time.perf_counter()
            try:
                self.__identifier.Load(stage_cb)
            except Identifier_Error_Cls as exc:
                raise Vision_Error_Cls(str(exc)) from exc
            timing.Models.append(Model_Load_Str(Name=os.path.basename(self.__config.Identification.Model_Path),
                                                Seconds=None if identifier_kept else time.perf_counter() - started))
        describer_s = self.__Ensure_Loaded(stage_cb)
        if self.__describer is not None:
            timing.Models.append(Model_Load_Str(Name=describer_name, Seconds=describer_s))
        self.__load_timing = timing
        self.__first_after_load = True

    def Configure(self, Configuration_Str: Configuration_Str,
                  stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Put another (already validated) configuration in force and load its models. A model
            whose identity is unchanged (the same weights, and for FastSAM the same device) is
            kept and only its per-call parameters change — no reload. A model that changes is
            RELEASED FIRST and its replacement loaded after, so two are never held at once.

            Once the models are in force it warms them up (Warming up…): see __Warm_Up.

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
        old_identifier = self.__identifier

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
        identifier = old_identifier
        new_identifier = self.__New_Identifier(new)
        if identifier is not None and (new_identifier is None or identifier.Model_Key != new_identifier.Model_Key):
            identifier.Release()
            identifier = None
        if identifier is None:
            identifier = new_identifier
        self.__config, self.__segmenter, self.__describer = new, segmenter, describer
        self.__identifier = identifier
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
            if self.__identifier is not None and self.__identifier is not old_identifier:
                self.__identifier.Release()
            self.__config, self.__segmenter, self.__describer, self.__describer_name = previous
            # A released identifier reloads with the previous configuration's models, like the others.
            self.__identifier = old_identifier
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
            # The reload is a load: warm it up like one, so a slow first analysis does not read as a
            # second fault. A released and reloaded Gemma has no kept sentence (__Ensure_Loaded cleared
            # it with the failed describer), so describing it again is the cold Gemma's first generation.
            self.__Warm_Up(stage_cb)
            # Its models were released to make room for the new ones, so they were loaded again —
            # that reload is the extra wait the operator saw.
            raise Vision_Error_Cls('%s %s is still in force and was loaded again.' % (reason, previous)) from exc

        # 3\ Committed: the reference may differ, and the background sentence depends on it, the
        #    prompt, the crop margin and the limits — both are read again under the new configuration.
        self.__background = None
        self.__background_sentence = None
        self.__background_audit = []
        self.__reference_rows = None
        self.__reference_patches = None
        self.__reference_sides = []

        # 4\ Then pay here, under the load's progress, what the first analysis would otherwise pay.
        self.__Warm_Up(stage_cb)

    def __Warm_Up(self, stage_cb: tp.Optional[tp.Callable]) -> None:
        """
        Description:
            Do the once-per-configuration work the first analysis would otherwise pay for, while
            the operator is already waiting on the load. Measured on the previous test set's
            Image_001 (9 objects; eb00508^, not re-run on a later set), the
            first analysis after a load took 2.6-2.9 s longer than the next one on the same frame:

                the background sentence (one Gemma call on the reference)   +1.08 s
                Gemma's first generation (kernels built on the first pass)  +0.84-1.14 s
                FastSAM's first pass (predictor set-up, first device pass)  +0.64 s
                reading the reference                                        +0.03 s

            So the reference is read and cached, FastSAM segments it (the result is discarded; it
            has the frame's size, which Analyze enforces), and the background sentence is described
            from it — which is also Gemma's first generation. The new reference is read after
            Configure has cleared the old one, so a reconfiguration describes its own reference.

            Best effort: a failure here does not fail the load (see the except below).

            Each part's time is recorded in Load_Timing (reference, first FastSAM pass, background
            sentence); a part that did not run stays None, and a failure is recorded as its reason.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
        """

        if stage_cb:
            stage_cb('Warming up…')
        timing = self.__load_timing
        try:
            started = time.perf_counter()
            bg_bgr = self.__Read_Reference(self.__cv2)
            timing.Reference_S = time.perf_counter() - started
            started = time.perf_counter()
            self.__segmenter.Segment(bg_bgr)
            timing.First_Segmentation_S = time.perf_counter() - started
            if self.__describer is not None:
                started = time.perf_counter()
                self.__Compute_Background_Sentence(bg_bgr)
                timing.Background_Sentence_S = time.perf_counter() - started
            if self.__identifier is not None:
                started = time.perf_counter()
                self.__Reference_Rows(self.__cv2, self.__np)
                timing.Reference_Images_S = time.perf_counter() - started
        except Exception as exc:                          # noqa: BLE001
            # Swallowed on purpose: the configuration is already in force, so this is not a failed
            # load. Nothing half-done is kept; the first analysis meets the failure and reports it.
            # The reason is kept in Load_Timing, which the window logs as a warning at the load.
            self.__background = None
            self.__background_sentence = None
            self.__background_audit = []
            timing.Warm_Up_Error = str(exc)

    def __Ensure_Loaded(self, stage_cb: tp.Optional[tp.Callable]) -> tp.Optional[float]:
        """
        Description:
            Ensure the runtime the selected pipeline needs is imported and cached. cv2/numpy
            are always required (stages 1-3). The describer CONST_DESCRIBER names is created
            and loaded once — the model-free fallback loads none — so stages 1-3 can run
            without a model. Selecting another describer between analyses replaces it. Reports
            the cold load through stage_cb.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [float or None]: How long the describer took to load, or None when it was
                                           already loaded (kept) or there is none (the fallback).
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
            if CONST_DESCRIBER not in ('gemma', 'fallback'):
                raise Vision_Error_Cls('Unknown describer "%s": choose gemma or fallback.' % CONST_DESCRIBER)
            self.__describer = (None if CONST_DESCRIBER == 'fallback'
                                else Gemma_Describer_Cls(self.__config.Description))
            self.__describer_name = CONST_DESCRIBER
            self.__background_sentence = None
            self.__background_audit = []
        if self.__describer is None or self.__describer.Loaded:
            return None
        if stage_cb:
            stage_cb('Loading model…')
        started = time.perf_counter()
        try:
            self.__describer.Load()
        except Describer_Error_Cls as exc:
            raise Vision_Error_Cls(str(exc)) from exc
        return time.perf_counter() - started

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

        self.__Read_Reference(cv2)
        if self.__background.shape != frame_shape:
            bh, bw = self.__background.shape[:2]
            fh, fw = frame_shape[:2]
            raise Vision_Error_Cls(
                'The background reference is %d×%d but the frame is %d×%d. '
                'Re-shoot the empty-surface reference from this camera so the two '
                'match.' % (bw, bh, fw, fh)
            )
        return self.__background

    def __Read_Reference(self, cv2: tp.Any) -> tp.List[tp.List[int]]:
        """
        Description:
            Read and cache the configuration's empty-surface reference, once.

        Args:
            (1) cv2 [module]: The OpenCV module.

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
                    'one from this camera and set Background.Reference in the station file to it.' % reference
                )
            self.__background = bg
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

            The sentence is computed once and kept: the reference is loaded once per
            configuration, and Configure (or a change of describer) clears the sentence with it,
            so a changed reference, prompt, margin or limit is described afresh. Configure then
            computes it straight away (__Warm_Up); its audit records are held and returned once,
            with the first analysis that carries the sentence. No per-frame
            check is needed — hashing the 6.9 MB reference each frame could never see a change
            the pipeline did not already make.
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
        self.__Compute_Background_Sentence(bg_bgr)
        records, self.__background_audit = self.__background_audit, []
        return self.__background_sentence, records

    def __Compute_Background_Sentence(self, bg_bgr: tp.List[tp.List[int]]) -> None:
        """
        Description:
            Describe the centre-cropped reference and keep the cleaned sentence and its audit
            records, unless a sentence is already kept. The records wait for __Describe_Background
            to hand them to an analysis.

        Args:
            (1) bg_bgr [Matrix<uint8> HxWx3]: The empty-surface reference (BGR).
        """

        if self.__background_sentence is not None:
            return
        h, w = bg_bgr.shape[:2]
        margin = self.__config.Description.Background_Crop_Margin
        crop = bg_bgr[int(h * margin):int(h * (1 - margin)), int(w * margin):int(w * (1 - margin))]
        caption = self.__describer.Describe(crop, CONST_PURPOSE_BACKGROUND)
        self.__background_sentence, self.__background_audit = Background_Sentence(
            caption, Description_Parameters_Str=self.__config.Description)

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
        """
        Description:
            Analyse one RGB frame and return the finished reading. The default path is
            the four-stage pipeline below, read top to bottom; each stage delegates to
            its own module (see the class docstring's pipeline overview). The frame is
            a contiguous RGB array (the UI converts the QImage), so this never touches Qt.

            Latency_Ms runs from the start of this call (before the models are checked, so a
            pipeline that was never preloaded pays its load inside it) to the end of Compose and
            Verdict; the measurement runs after it stops. A catalogue mode measures, checks and judges the
            objects before it describes them (the describer is told what the checks found), and that time is
            left out of it the same way: the start is moved on by it. Timing breaks that same interval into
            its stages (Parameters.Vision.CONST_TIMING_STAGES), each timed around completed work:
            the segmenter and the describer sync their devices before they return.

            What is NOT a stage lands in 'other' or in the stage that contains it:
              other:              the model check (__Ensure_Loaded and segmenter.Load); RGB->BGR;
                                  reading and size-checking the reference (cached after the first
                                  read); the describe setup (the union of the object masks and the
                                  dilate kernel) and the 'Describing…' hook; each object's progress
                                  hook and Condense_Label (the Gemma path's label).
              segmentation post:  Segment's own loaded check and its 'Segmenting…' hook, with the
                                  masks' read-back, resize and ranking.
              crops:              each object's neighbour mask (the dilate of the other objects).
              descriptions:       the fallback describer's label, which it writes with the detail.
            So in a pipeline that was never preloaded (the harness, a test) 'other' absorbs the cold
            load — about 6 s for Gemma and 1 s for FastSAM on the development machine — and the
            first analysis also pays in its own stages what the warm-up would have paid: FastSAM's
            first pass in 'segmentation', the background sentence's first generation in
            'background sentence'. First_After_Load marks that analysis.

            The per-object times are each truncated to a whole millisecond, the crops and
            descriptions stages once over the unrounded sum, so the per-object values can add up
            to up to one millisecond per object less than their stage (Parameters.Vision
            Object_Timing_Str).

            First_After_Load is True for the first analysis to FINISH after the models were put in
            force by Load_Models — which every Configure goes through, whether it loaded a model or
            kept it (a reload of a configuration with the same models still counts: it warms up
            again, and the flag shows whether that left the next analysis as fast as the one after),
            and which the restore after a failed Configure goes through too. A pipeline that was
            never preloaded starts with it set: its first analysis pays the load. An analysis that
            fails leaves it set, so the next one to finish carries it.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame as a contiguous RGB array.
            (2) progress_cb [function]: Optional (done, total) progress hook.
            (3) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        t0 = time.perf_counter()
        # The models are checked (loaded, when nothing preloaded them) inside the latency and
        # outside every stage, so a cold load lands in the timing's remainder, not in a stage.
        # The describer's model is loaded only when one writes the descriptions; the
        # model-free fallback describer needs none.
        self.__Ensure_Loaded(stage_cb)
        self.__segmenter.Load(stage_cb)
        cv2, np = self.__cv2, self.__np
        stage_s = {}

        # RGB -> BGR: the pipeline works in BGR, the exchange format is RGB.
        frame_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        # ---- Stage 1 - background subtraction (Vision.Utilities.Segmentation) ----
        # The background-subtracted foreground mask: one of the two cues fused in
        # stage 3. Pure cv2/np differencing, so it lives in Segmentation, not here. The
        # difference before thresholding is kept for the Camera View's heatmap.
        bg_bgr = self.__Load_Background(cv2, frame_bgr.shape)
        started = time.perf_counter()
        difference = Background_Difference(bg_bgr, frame_bgr, cv2, np)
        background_fg, threshold, otsu = Foreground_Mask(difference, cv2, np,
                                                         Segmentation_Parameters_Str=self.__config.Segmentation)
        stage_s[CONST_STAGE_BACKGROUND] = time.perf_counter() - started

        # ---- Stage 2 - instance segmentation (Vision.Segmenter) ----
        # FastSAM on the whole frame, behind the Segmenter_Backend_Cls seam: the other fused cue.
        # In its own module so the lazy ultralytics import keeps a bare Core import Qt-free and
        # cheap. Segmenting the whole frame is what separates touching parts.
        # The model call (with its device sync) is the segmentation; the rest of Segment is its
        # post-processing.
        started = time.perf_counter()
        masks, scores = self.__segmenter.Segment(frame_bgr, stage_cb)
        segment_s = time.perf_counter() - started
        stage_s[CONST_STAGE_SEGMENTATION] = self.__segmenter.Last_Inference_S
        stage_s[CONST_STAGE_SEGMENTATION_POST] = segment_s - self.__segmenter.Last_Inference_S

        # ---- Stage 3 - fusion (Vision.Utilities.Fusion) ----
        # The objects: the FastSAM union OR the background mask, closed, split into
        # connected components, area-filtered and ordered left to right. An object
        # survives on EITHER cue; each records the cue(s) that located it.
        started = time.perf_counter()
        objects = Fuse_Objects(masks, scores, background_fg, cv2, np,
                               Segmentation_Parameters_Str=self.__config.Segmentation)
        stage_s[CONST_STAGE_FUSION] = time.perf_counter() - started

        # ---- A catalogue mode judges before it describes ----
        # Measured, checked against the catalogue, identified and judged, so the describer can be told the side
        # and what the checks found (Reporting.Describer_Prompt). Outside the latency, as the measurement is in
        # every mode: its time is carried beside the total, and the start is moved on by it.
        catalogue = self.__config.Catalogue
        if catalogue is not None:
            started = time.perf_counter()
            Measure_Objects(objects, self.__config.Scale, cv2, np)
            Check_Objects(objects, catalogue)
            measurement_s = time.perf_counter() - started
            started = time.perf_counter()
            unlike = self.__Classify_Objects(objects, frame_bgr, cv2, np)
            identification_s = time.perf_counter() - started
            t0 += measurement_s + identification_s

        # ---- Stage 4 - description (Vision.Describers / Vision.Describe_Fallback) ----
        # One caption per object, from the alpha/beta-enhanced padded crop: neighbours
        # are masked out (filled from the reference) so the crop holds one object plus
        # table, and the stretch is estimated from the object's own pixels.
        object_times, guard_audit = self.__Describe_Objects(objects, frame_bgr, bg_bgr, progress_cb, stage_cb)
        stage_s[CONST_STAGE_CROPS] = sum(crop_s for crop_s, _describe_s, _tokens in object_times)
        stage_s[CONST_STAGE_DESCRIPTIONS] = sum(describe_s for _crop_s, describe_s, _tokens in object_times)

        # The one global background sentence, from the reference (cached across frames).
        started = time.perf_counter()
        background_sentence, background_audit = self.__Describe_Background(bg_bgr)
        stage_s[CONST_STAGE_BACKGROUND_SENTENCE] = time.perf_counter() - started
        result = self.__Compose_Result(objects, t0, len(masks), background_sentence, background_audit + guard_audit,
                                       stage_s, object_times)
        # The heatmap's source today: the background difference on its fixed scale, with the threshold
        # applied — named by what set it — marked on the legend.
        result.Heatmap = Heatmap_Str(Values=difference, Low=0.0, High=float(CONST_DIFFERENCE_SCALE_MAX),
                                     Title='Difference from the reference', Unit='grey level',
                                     Marks=[(threshold, ('Otsu %d' if otsu >= threshold else 'floor %d') % threshold)])
        if catalogue is not None:
            result.Similarity = Heatmap_Str(Values=unlike, Low=0.0, High=CONST_SIMILARITY_SCALE_MAX,
                                            Title='Unlike the reference (DINOv2 patches) — not a defect map',
                                            Unit='1 − cosine')
            result.Timing.Measurement_Ms = int(measurement_s * 1000)
            result.Timing.Identification_Ms = int(identification_s * 1000)
            # A judged part's description says which side is up, from DINOv2's side, in the catalogue's words.
            for det in result.Objects:
                side_sentence = Side_Sentence(det)
                if side_sentence:
                    det.Sentence = ('%s %s' % (det.Sentence, side_sentence)).strip()
        else:
            # Measure every masked object through the configured scale (none without one). It runs after
            # Latency_Ms has stopped, so its time is carried beside the total, not in it.
            started = time.perf_counter()
            Measure_Objects(result.Objects, self.__config.Scale, cv2, np)
            result.Timing.Measurement_Ms = int((time.perf_counter() - started) * 1000)
        self.__first_after_load = False
        return result

    @staticmethod
    def __New_Identifier(Configuration_Str: Configuration_Str) -> tp.Optional[Dino_Identifier_Cls]:
        """
        Description:
            The identifier a configuration needs: DINOv2 on the segmenter's device in a catalogue mode,
            none otherwise. Not loaded: constructing it is cheap.

        Args:
            (1) Configuration_Str [Configuration_Str(object)]: The configuration.

        Returns:
            (1) parameter [Dino_Identifier_Cls(object) or None]: The identifier, or None.
        """

        if Configuration_Str.Catalogue is None:
            return None
        return Dino_Identifier_Cls(Configuration_Str.Identification.Model_Path, Configuration_Str.Segmentation.Device)

    def __Reference_Rows(self, cv2: tp.Any, np: tp.Any) -> tp.Any:
        """
        Description:
            The catalogue item's reference images as unit rows (one per side, cut out by their boxes),
            embedded once per configuration and kept.

        Args:
            (1) cv2 [module]: The OpenCV module.
            (2) np [module]: The NumPy module.

        Returns:
            (1) parameter [Matrix<float> SxD]: One row per side, in the item's side order.

        Raises:
            Vision_Error_Cls: A reference image cannot be read, or the identifier cannot run.
        """

        if self.__reference_rows is None:
            crops = []
            for reference in self.__config.Catalogue.References:
                image = cv2.imread(reference.Image_Path)
                if image is None:
                    raise Vision_Error_Cls('The %s reference image "%s" could not be read; restore the catalogue '
                                           'item\'s reference_image folder.' % (reference.Side, reference.Image_Path))
                crops.append(Reference_Crop(image, reference.Box))
            try:
                self.__reference_rows, self.__reference_patches = self.__identifier.Embed(crops, cv2, np, patches=True)
            except Identifier_Error_Cls as exc:
                raise Vision_Error_Cls(str(exc)) from exc
            self.__reference_sides = [reference.Side for reference in self.__config.Catalogue.References]
        return self.__reference_rows

    def __Classify_Objects(self, objects: tp.List[Detection_Str], frame_bgr: tp.Any, cv2: tp.Any, np: tp.Any) -> tp.Any:
        """
        Description:
            A catalogue mode's judgement, before the objects are described: every object's crop, turned
            upright, in four quarter turns, through DINOv2 in one pass, its best match to the item's
            references, and its verdict (Vision.Utilities.Classify); then each judged part's checks on the
            side up, on its upright crop: its holes (FastSAM again, Vision.Utilities.Holes) and its stains
            (Vision.Utilities.Stain), each found defect making it NOK. The crop's scale is the mean of the two
            factors (they differ by 0.17 %). Each judged part's features are taken to the frame and numbered as
            its parts, and its patches' unlikeness to its matched reference is laid on the frame's similarity map.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The measured, checked objects (mutated).
            (2) frame_bgr [Matrix<uint8> HxWx3]: The frame.
            (3) cv2 [module]: The OpenCV module.
            (4) np [module]: The NumPy module.

        Returns:
            (1) parameter [Matrix<float32> HxW]: The similarity map: each judged part's pixels its patch's
                                                 unlikeness (1 - cosine), NaN elsewhere.

        Raises:
            Vision_Error_Cls: The identifier cannot run.
        """

        if not objects:
            return np.full(frame_bgr.shape[:2], np.nan, dtype=np.float32)
        references = self.__Reference_Rows(cv2, np)
        uprights = [Object_Crop(frame_bgr, det, cv2, np) for det in objects]
        crops = [turn for upright in uprights for turn in Rotations(upright, cv2)]
        try:
            rows, patches = self.__identifier.Embed(crops, cv2, np, patches=True)
        except Identifier_Error_Cls as exc:
            raise Vision_Error_Cls(str(exc)) from exc
        turns = len(crops) // len(objects)
        frame_size = (frame_bgr.shape[1], frame_bgr.shape[0])
        unlike = np.full(frame_bgr.shape[:2], np.nan, dtype=np.float32)
        for index, det in enumerate(objects):
            own = rows[index * turns:(index + 1) * turns]
            similarity, side = Best_Match(own, references, self.__reference_sides)
            Classify(det, similarity, side, self.__config.Catalogue, self.__config.Identification,
                     self.__config.Scale, frame_size)
            if det.Verdict not in ('OK', 'NOK'):
                continue
            # The similarity overlay (a diagnostic, never a verdict): each patch's unlikeness to the matched
            # reference, from the identification's own pass, laid on the part's pixels.
            turn = Best_Turn(own, references, self.__reference_sides, side)
            grid = Similarity_Grid(patches[index * turns + turn],
                                   self.__reference_patches[self.__reference_sides.index(side)], turn, np)
            self.__Lay_Grid(unlike, grid, det, uprights[index].shape, cv2, np)
            item, upright = self.__config.Catalogue, uprights[index]
            mm_per_px = (self.__config.Scale.Mm_Per_Px_X + self.__config.Scale.Mm_Per_Px_Y) / 2.0
            # A judged part's holes, on the side up: FastSAM again, on its upright crop. The stain check
            # leaves the holes it finds out, so they run for either.
            groups, stain = item.Holes.get(side), item.Stain.get(side)
            holes, features = [], []
            if groups or stain is not None:
                masks, scores = self.__segmenter.Segment(upright)
                holes = Hole_Candidates(masks, mm_per_px, cv2, np, scores=scores)
            if groups:
                height_px, width_px = upright.shape[:2]
                Apply_Holes(det, *Check_Holes(holes, groups, width_px * mm_per_px, height_px * mm_per_px))
                features += Hole_Features(holes, groups, width_px * mm_per_px, height_px * mm_per_px)
            # Its stains, on the side up.
            if stain is not None:
                Apply_Stain(det, Check_Stain(upright, holes, stain, mm_per_px, cv2, np))
                features += [Feature_Str(Kind='stain', Name='stain', Passed=False, Corners=found.Corners,
                                         Outlines=found.Outlines, Area_Mm2=found.Area_Mm2) for found in det.Stains]
            # Each feature to the frame (holes and stains are in mm on the crop), numbered as the object's parts.
            scale = 1.0 / mm_per_px
            for number, feature in enumerate(features, 1):
                feature.Part = '%d.%d' % (index + 1, number)
                feature.Corners = Crop_To_Frame(det, [(x * scale, y * scale) for x, y in feature.Corners], cv2, np)
                feature.Outlines = [Crop_To_Frame(det, [(x * scale, y * scale) for x, y in outline], cv2, np)
                                    for outline in feature.Outlines]
            det.Features = features
        return unlike

    @staticmethod
    def __Lay_Grid(unlike: tp.Any, grid: tp.Any, det: Detection_Str, crop_shape: tp.Tuple[int, ...], cv2: tp.Any,
                   np: tp.Any) -> None:
        """
        Description:
            A judged part's patch grid laid on the frame's map: each patch over its share of the upright crop, taken
            back to the frame through the crop's corners, and kept only on the part's own pixels.

        Args:
            (1) unlike [Matrix<float32> HxW]: The frame's map, NaN where nothing is laid (mutated).
            (2) grid [Matrix<float> nxn]: The part's dissimilarity per patch, upright.
            (3) det [Detection_Str(object)]: The part.
            (4) crop_shape [Tuple<int>]: Its upright crop's shape.
            (5) cv2 [module]: The OpenCV module.
            (6) np [module]: The NumPy module.
        """

        height, width = crop_shape[:2]
        corners = Crop_To_Frame(det, [(0.0, 0.0), (float(width), 0.0), (float(width), float(height)),
                                      (0.0, float(height))], cv2, np)
        warp = cv2.getPerspectiveTransform(np.float32([[0, 0], [width, 0], [width, height], [0, height]]),
                                           np.float32(corners))
        cells = cv2.resize(np.ascontiguousarray(grid, dtype=np.float32), (width, height), interpolation=cv2.INTER_NEAREST)
        laid = cv2.warpPerspective(cells, warp, (unlike.shape[1], unlike.shape[0]), flags=cv2.INTER_NEAREST,
                                   borderMode=cv2.BORDER_CONSTANT, borderValue=float('nan'))
        own = det.Mask.astype(bool) & np.isfinite(laid)
        unlike[own] = laid[own]

    def __Describe_Objects(self, objects: tp.List[Detection_Str], frame_bgr: tp.List[tp.List[int]],
                           bg_bgr: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable],
                           stage_cb: tp.Optional[tp.Callable]) -> tp.Tuple[tp.List[tp.Tuple[float, float,
                                                                                            tp.Optional[tp.Tuple[int, int]]]],
                                                                           tp.List[tp.Tuple[str, str]]]:
        """
        Description:
            Stage 4: fill each object's Label and Detail from its crop. The padded crop
            has every OTHER object's pixels replaced by the empty-surface reference, so
            it holds one object plus the table and no neighbours, then it is contrast/
            brightness-stretched (the gain/bias estimated from and given to the object's
            own pixels; the surround left as the natural table) and fed to the
            describer — Gemma or the model-free fallback (CONST_DESCRIBER). The
            enhanced crop is retained on the object (Enhanced_Crop) so the debug montage
            shows exactly what the model received, without re-enhancing it.

            The objects are described one after another on this thread (no batching), so their
            times add up to the crops and descriptions stages.

            In a catalogue mode a judged part (OK, NOK) is described with the item's Describer.Prompt filled
            for it (Reporting.Describer_Prompt: its side, that side's description and defects, what the checks
            found, no number), and the describer's text then goes through the guard
            (Reporting.Guard_Description): a sentence with a number or contradicting a check is dropped, and
            each drop is an audit record with the describer's full text.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The stage-3 objects (mutated).
            (2) frame_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
            (3) bg_bgr [Matrix<uint8> HxWx3]: The empty-surface reference (BGR).
            (4) progress_cb [function]: Optional (done, total) progress hook.
            (5) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Tuple<Vector<Tuple>, Vector<Tuple<string> 1x2>>]: Per object, in order: (crop seconds,
                                           description seconds, (input tokens, output tokens) or None); and
                                           the guard's audit records, (level, message).
        """

        cv2, np = self.__cv2, self.__np
        audit = []
        if stage_cb and objects:
            stage_cb('Describing…')

        # The union of every object's mask, so each crop can subtract its neighbours.
        all_mask = np.zeros(frame_bgr.shape[:2], dtype=bool)
        for det in objects:
            all_mask |= det.Mask.astype(bool)
        dilate_kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (CONST_ENHANCE_NEIGHBOUR_DILATE, CONST_ENHANCE_NEIGHBOUR_DILATE))

        total = len(objects)
        times = []
        for i, det in enumerate(objects):
            if progress_cb:
                progress_cb(i, total)
            started = time.perf_counter()
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
            crop_s = time.perf_counter() - started
            started = time.perf_counter()
            if self.__describer is None:
                det.Label, det.Detail = Describe_Fallback(
                    frame_bgr, det.Mask, det.Bbox, frame_bgr.shape, cv2, np)
                describe_s, tokens = time.perf_counter() - started, None
            else:
                catalogue = self.__config.Catalogue
                prompt = Describer_Prompt(det, catalogue) if catalogue is not None else ''
                det.Detail = self.__describer.Describe(enhanced, CONST_PURPOSE_OBJECT, prompt)
                describe_s, tokens = time.perf_counter() - started, self.__describer.Last_Tokens
                if catalogue is not None and det.Verdict in ('OK', 'NOK'):
                    full = det.Detail
                    det.Detail, dropped = Guard_Description(full, det)
                    for sentence, why in dropped:
                        audit.append(('warning', 'Object %d: the describer\'s sentence "%s" was left out: %s. '
                                                 'Its full text: "%s"' % (i + 1, sentence, why, full)))
                det.Label = Condense_Label(det.Detail)
            times.append((crop_s, describe_s, tokens))
        if progress_cb:
            progress_cb(total, total)
        return times, audit

    def __Compose_Result(self, objects: tp.List[Detection_Str],
                         t0: float, raw_mask_count: int, background_sentence: str,
                         background_audit: tp.List[tp.Tuple[str, str]], stage_s: tp.Dict[str, float],
                         object_times: tp.List[tp.Tuple[float, float, tp.Optional[tp.Tuple[int, int]]]]
                         ) -> Analysis_Str:
        """
        Description:
            Compose the panel's reading from the described objects: the per-object
            sentences, the note, the verdict badge, the latency, the global
            background sentence and its audit, and the timing of the stages. The objects are
            never reordered here — their order is the index contract, and the per-object timing
            follows it.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The described objects, in order.
            (2) t0 [float]: The analysis start time (perf_counter).
            (3) raw_mask_count [int]: The raw segmenter mask count (a diagnostic).
            (4) background_sentence [string]: The one global background description.
            (5) background_audit [Vector<Tuple<string> 1x2>]: The background-caption audit.
            (6) stage_s [Dict<string, float>]: The seconds of the stages timed so far (mutated:
                                               the compose stage is added).
            (7) object_times [Vector<Tuple>]: Per object: (crop s, description s, tokens or None).

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        caption = '' if objects else CONST_EMPTY_SCENE_EXPLANATION
        started = time.perf_counter()
        objects, note = Compose(objects, caption=caption)
        badge, level = Verdict(objects)
        stage_s[CONST_STAGE_COMPOSE] = time.perf_counter() - started
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return Analysis_Str(Objects=objects, Note=note,
                            Latency_Ms=latency_ms, Verdict=badge, Verdict_Level=level,
                            Task=(self.__config.Identity.Task if self.__describer is not None
                                  else CONST_FALLBACK_TASK_LABEL),
                            Raw_Mask_Count=raw_mask_count,
                            Background=background_sentence, Audit=background_audit,
                            Timing=Build_Timing(latency_ms, stage_s, object_times, self.__first_after_load))
