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
# File Name: ../Vision/Core.py
## =========================================================================== ##

# System (Default)
import os
import time
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — data structures, composer, and vision utilities
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
from Reporting.Core import Compose, Verdict, CONST_EMPTY_SCENE_EXPLANATION
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Background_Foreground
#   ../Vision/Utilities/Fusion
from Vision.Utilities.Fusion import Fuse_Objects
#   ../Vision/Utilities/Enhancement
from Vision.Utilities.Enhancement import Padded_Bbox, Crop, Enhance_Crop, CONST_ENHANCE_CLIP_LIMIT
#   ../Vision/Segmenter
from Vision.Segmenter import Fast_Sam_Cls
#   ../Vision/Describe_Fallback
from Vision.Describe_Fallback import Describe_Fallback
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Describe, Condense_Label

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
        (4) description              Vision.Utilities.Caption.Describe or
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
        UI owns the QImage <-> array conversion. torch, transformers and OpenCV are
        imported lazily on the first Analyze, so importing this module (as App/run.py
        does at load time) pulls no heavy runtime.
"""
# The local Florence-2 weights, presented to the operator as CONST_MODEL_NAME.
# Loaded from this directory only, never a hub id, so there is no network call at
# runtime. Derived from this file's location (src/Vision -> ../../models/...).
CONST_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                 'models', 'florence2-large-ft'))

# The empty-surface reference photo. Segmentation is the difference between the
# captured frame and this image, so it must come from the SAME fixed camera and
# match the frame's pixel dimensions exactly. Overridable at runtime (the app's
# --background flag reassigns this module attribute).
CONST_BACKGROUND_REF = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                 'Data', 'Camera', 'Image_Background_001.png'))

# Torch device: 'auto' picks cuda, then mps, then cpu. float32 is deliberate —
# fp16 on Apple's MPS backend is unreliable for this model.
CONST_VISION_DEVICE = 'auto'

# The human-readable task name shown in the reading panel's meta row.
CONST_VISION_TASK_LABEL = 'detailed caption'

# Who writes each object's caption. 'florence' is the Florence-2 VLM; 'fallback' is
# the model-free describer (size / position / aspect / solidity / HSV colour), which
# lets stages 1-3 run and be judged without loading a VLM.
CONST_DESCRIBER = 'florence'

# The model name presented to the operator. The weights are Florence-2, MIT
# licensed — keep Microsoft's notice with the project.
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
                Cls = Florence_Vision_Cls()

            Features:
                # Functions of the class.
                Cls.Analyze(image_rgb)
    """

    Name = CONST_MODEL_NAME

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


class Florence_Vision_Cls(Vision_Backend_Cls):
    """
    Description:
        The vision backend. It orchestrates the four-stage pipeline and owns the
        Florence-2 describer; the model is presented as JIC-AnyScan-v1 and the
        weights are Florence-2, MIT licensed — keep Microsoft's notice with the project.

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
          (4) description .................... Caption.Describe  OR
                   |  the alpha/beta-enhanced padded      Describe_Fallback
                   |  crop (estimated from object         (per CONST_DESCRIBER;
                   |  pixels, applied to the whole        the fallback reads
                   |  crop) feeds Florence-2;             mask + bbox directly)
                   v
              Compose -> summary + per-object sentences + verdict
                   |
                   v
              Analysis_Str

        The two cues are fused, not gated: an object survives if EITHER stage 1 or
        stage 2 sees it. Every analysis needs a reference background (stage 1); there
        is no background-free path. Each stage lives in its own module so the heavy
        imports (ultralytics, torch) stay behind their lazy loaders and this class
        reads as the flow.

        Note:
            Notes that cost hours if missed:
              (1) These are the native transformers Florence2ForConditionalGeneration
                  weights (no bundled modelling code, no auto_map), so they load
                  with local_files_only=True and NOT trust_remote_code. Nothing
                  here touches the network at runtime.
              (2) torch, transformers and OpenCV are imported lazily on the first
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
            None.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Florence_Vision_Cls()

            Features:
                # Functions of the class.
                Cls.Analyze(image_rgb, progress_cb, stage_cb)
    """

    def __init__(self) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__model = None
        self.__processor = None
        self.__device = None
        self.__dtype = None
        self.__torch = None
        self.__cv2 = None
        self.__np = None
        self.__pil = None
        # Cached BGR reference array.
        self.__background = None
        # The stage-2 segmenter. Constructing it is cheap — ultralytics loads lazily
        # on the first Segment, so this keeps the window and the tests light.
        self.__segmenter = Fast_Sam_Cls()

    def __Pick_Device(self, torch: tp.Any) -> tp.Any:
        """
        Description:
            Choose the torch device from CONST_VISION_DEVICE ('auto' -> cuda, then
            mps, then cpu).

        Args:
            (1) torch [module]: The torch module.

        Returns:
            (1) parameter [torch.device]: The selected device.
        """

        if CONST_VISION_DEVICE != 'auto':
            return torch.device(CONST_VISION_DEVICE)
        if torch.cuda.is_available():
            return torch.device('cuda')
        if torch.backends.mps.is_available():
            return torch.device('mps')
        return torch.device('cpu')

    def __Ensure_Loaded(self, stage_cb: tp.Optional[tp.Callable], need_florence: bool) -> None:
        """
        Description:
            Ensure the runtime the selected pipeline needs is imported and cached.
            cv2/numpy are always required (stages 1-3). The Florence-2 model is loaded
            only when a Florence path is selected — the fallback describer skips it —
            so stages 1-3 can run without a VLM. Reports the cold load through stage_cb.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
            (2) need_florence [bool]: Load the Florence-2 model and its runtime.
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

        if not need_florence or self.__model is not None:
            return
        if stage_cb:
            stage_cb('Loading model…')
        try:
            import torch
            from PIL import Image as PILImage
            from transformers import (AutoProcessor,
                                      Florence2ForConditionalGeneration)
        except ImportError as exc:
            raise Vision_Error_Cls(
                'The vision runtime is not installed. Install torch, transformers '
                'and Pillow into this environment, then scan again.'
            ) from exc

        device = self.__Pick_Device(torch)
        dtype = torch.float32  # fp16 on MPS is unreliable for this model
        try:
            model = Florence2ForConditionalGeneration.from_pretrained(
                CONST_MODEL_DIR, dtype=dtype, local_files_only=True)
            model.to(device)
            model.eval()
            processor = AutoProcessor.from_pretrained(
                CONST_MODEL_DIR, local_files_only=True)
        except Exception as exc:                          # noqa: BLE001
            raise Vision_Error_Cls(
                'The model weights at "%s" could not be loaded. Check that the '
                'directory is complete and readable.' % CONST_MODEL_DIR
            ) from exc

        self.__torch, self.__pil = torch, PILImage
        self.__model, self.__processor = model, processor
        self.__device, self.__dtype = device, dtype

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
        # The Florence-2 model is loaded only when it writes the captions; the
        # model-free fallback describer needs no VLM.
        self.__Ensure_Loaded(stage_cb, need_florence=(CONST_DESCRIBER == 'florence'))
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
        masks, scores = self.__segmenter.Segment(frame_bgr, [], stage_cb)

        # ---- Stage 3 - fusion (Vision.Utilities.Fusion) ----
        # The objects: the FastSAM union OR the background mask, closed, split into
        # connected components, area-filtered and ordered left to right. An object
        # survives on EITHER cue; each records the cue(s) that located it.
        objects = Fuse_Objects(masks, scores, background_fg, cv2, np)

        # ---- Stage 4 - description (Vision.Utilities.Caption / Vision.Describe_Fallback) ----
        # One caption per object, from the alpha/beta-enhanced padded crop (natural
        # surroundings kept; the stretch is estimated from the object's own pixels).
        self.__Describe_Objects(objects, frame_bgr, progress_cb, stage_cb)

        return self.__Compose_Result(objects, size, t0)

    def __Describe_Objects(self, objects: tp.List[Detection_Str], frame_bgr: tp.List[tp.List[int]],
                           progress_cb: tp.Optional[tp.Callable], stage_cb: tp.Optional[tp.Callable]) -> None:
        """
        Description:
            Stage 4: fill each object's Label and Detail from its crop. The padded
            crop is contrast/brightness-stretched (the gain/bias estimated from the
            object's own pixels, applied to the whole crop so the natural surroundings
            are kept) and the stretched crop is fed to the describer — Florence-2 or
            the model-free fallback (CONST_DESCRIBER). The stretched crop is retained
            on the object (Enhanced_Crop) so the debug montage shows exactly what the
            model received, without re-enhancing it.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The stage-3 objects (mutated).
            (2) frame_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
            (3) progress_cb [function]: Optional (done, total) progress hook.
            (4) stage_cb [function]: Optional (text) phase hook.
        """

        cv2, np = self.__cv2, self.__np
        if stage_cb and objects:
            stage_cb('Describing…')

        total = len(objects)
        for i, det in enumerate(objects):
            if progress_cb:
                progress_cb(i, total)
            # The padded crop, and the object's mask within it, so the stretch is
            # estimated from object pixels only but applied to the whole crop.
            padded = Padded_Bbox(det.Bbox, frame_bgr.shape)
            crop = Crop(frame_bgr, padded)
            mask_crop = Crop(det.Mask, padded)
            enhanced = Enhance_Crop(crop, mask_crop, CONST_ENHANCE_CLIP_LIMIT, cv2, np)
            det.Enhanced_Crop = enhanced
            if CONST_DESCRIBER == 'fallback':
                det.Label, det.Detail = Describe_Fallback(
                    frame_bgr, det.Mask, det.Bbox, frame_bgr.shape, cv2, np)
            else:
                det.Detail = Describe(self.__model, self.__processor, self.__device,
                                      self.__dtype, enhanced, cv2, np, self.__torch, self.__pil)
                det.Label = Condense_Label(det.Detail)
        if progress_cb:
            progress_cb(total, total)

    def __Compose_Result(self, objects: tp.List[Detection_Str], size: tp.Tuple[int, int],
                         t0: float) -> Analysis_Str:
        """
        Description:
            Compose the panel's reading from the described objects: the per-object
            sentences, the summary, the note, the verdict badge and the latency. The
            objects are never reordered here — their order is the index contract.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The described objects, in order.
            (2) size [Vector<int> 1x2]: The frame size as (width, height).
            (3) t0 [float]: The analysis start time (perf_counter).

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        caption = '' if objects else CONST_EMPTY_SCENE_EXPLANATION
        objects, summary, note = Compose(objects, size, caption=caption)
        badge, level = Verdict(objects)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return Analysis_Str(Summary=summary, Objects=objects, Note=note,
                            Latency_Ms=latency_ms, Verdict=badge, Verdict_Level=level,
                            Task=CONST_VISION_TASK_LABEL)
