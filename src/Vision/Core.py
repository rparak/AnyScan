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
from Reporting.Core import Compose, Verdict, CONST_EMPTY_SCENE_EXPLANATION, CONST_LABEL_MAX_WORDS
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import (Build_Mask, Find_Objects, Crop_With_Pad,
                                           CONST_SEG_MAX_AREA_FRAC, CONST_SEG_MAX_OBJECTS)
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Describe, Condense_Label, CONST_VISION_NUM_BEAMS

"""
Description:
    Initialization of constants.

    The vision pipeline. CONST_DETECTOR selects how the boxes are found:

        frame  --detect-->  N boxes in FULL-FRAME pixels
          'segment':  frame + background reference -> Build_Mask -> Find_Objects
          'florence': Florence-2 detection on the full frame -> __Detect_Florence
               -> Crop_With_Pad   crop each box from the ORIGINAL frame
                    -> Describe    one Florence-2 caption per crop (the 'what')
                         -> Detection_Str(Label, Bbox, Detail)
                              -> Compose  the numbered lines the panel renders

    Boxes are in full-frame pixels either way, so there is no crop-to-frame
    remap to get wrong. Florence-2 emits no confidence, so it stays None and the
    verdict handles unscored objects.

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

# How object boxes are found before any per-crop description. 'segment' is
# background subtraction against CONST_BACKGROUND_REF — class-agnostic and the
# proven method; 'florence' is Florence-2's own detection on the full frame.
CONST_DETECTOR = 'segment'

# The Florence-2 detection task used when CONST_DETECTOR == 'florence', its token
# budget, and the min box area (fraction of frame) that drops stray specks.
CONST_FLORENCE_DETECT_TASK = '<REGION_PROPOSAL>'
CONST_FLORENCE_DETECT_MAX_TOKENS = 1024
CONST_FLORENCE_MIN_AREA_FRAC = 0.0005

# The model name presented to the operator. The weights are Florence-2, MIT
# licensed — keep Microsoft's notice with the project.
CONST_MODEL_NAME = 'JIC-AnyScan-VLM-v1'


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
        The real vision-language model. Presented as JIC-AnyScan-VLM-v1; the
        weights are Florence-2, MIT licensed — keep Microsoft's notice with the
        project.

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

    def __Ensure_Loaded(self, stage_cb: tp.Optional[tp.Callable]) -> None:
        """
        Description:
            Import the runtime and load the model and processor once, caching both.
            Reports the cold-load through stage_cb.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
        """

        if self.__model is not None:
            return
        if stage_cb:
            stage_cb('Loading model…')
        try:
            import cv2
            import numpy as np
            import torch
            from PIL import Image as PILImage
            from transformers import (AutoProcessor,
                                      Florence2ForConditionalGeneration)
        except ImportError as exc:
            raise Vision_Error_Cls(
                'The vision runtime is not installed. Install torch, transformers, '
                'OpenCV and Pillow into this environment, then scan again.'
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

        self.__cv2, self.__np, self.__torch, self.__pil = cv2, np, torch, PILImage
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

    def __Detect_Florence(self, frame_bgr: tp.List[tp.List[int]],
                          stage_cb: tp.Optional[tp.Callable]) -> tp.Tuple[tp.List, tp.List]:
        """
        Description:
            Florence-2's own detection on the full frame. Returns (boxes_xyxy,
            det_labels) in full-frame pixels, filtered by area, capped, and ordered
            left to right — the same contract Find_Objects returns, plus the model's
            own per-box label for a fallback name.

        Args:
            (1) frame_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
            (2) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Tuple]: (boxes as (x1,y1,x2,y2), per-box labels or None).
        """

        cv2, torch, pil = self.__cv2, self.__torch, self.__pil
        if stage_cb:
            stage_cb('Detecting objects…')

        frame_rgb = pil.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        inputs = self.__processor(text=CONST_FLORENCE_DETECT_TASK, images=frame_rgb,
                                  return_tensors='pt')
        inputs = {k: (v.to(self.__device, self.__dtype) if v.is_floating_point()
                      else v.to(self.__device)) for k, v in inputs.items()}
        with torch.inference_mode():
            ids = self.__model.generate(
                **inputs, max_new_tokens=CONST_FLORENCE_DETECT_MAX_TOKENS,
                num_beams=CONST_VISION_NUM_BEAMS, do_sample=False)
        raw = self.__processor.batch_decode(ids, skip_special_tokens=False)[0]
        parsed = self.__processor.post_process_generation(
            raw, task=CONST_FLORENCE_DETECT_TASK, image_size=frame_rgb.size)

        block = parsed.get(CONST_FLORENCE_DETECT_TASK, {}) if isinstance(parsed, dict) else {}
        bboxes = block.get('bboxes', []) if isinstance(block, dict) else []
        labels = (block.get('labels') if isinstance(block, dict) else None) or []

        h, w = frame_bgr.shape[:2]
        area_total = float(h * w)
        items = []
        for i, box in enumerate(bboxes):
            x1, y1, x2, y2 = (int(round(v)) for v in box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            frac = ((x2 - x1) * (y2 - y1)) / area_total
            if frac < CONST_FLORENCE_MIN_AREA_FRAC or frac > CONST_SEG_MAX_AREA_FRAC:
                continue
            label = labels[i] if i < len(labels) else None
            items.append(((x1, y1, x2, y2), label, frac))

        # Keep the largest N, then present them left to right (the index contract).
        items.sort(key=lambda it: it[2], reverse=True)
        items = items[:CONST_SEG_MAX_OBJECTS]
        items.sort(key=lambda it: it[0][0])
        return [it[0] for it in items], [it[1] for it in items]

    def __Detect(self, frame_bgr: tp.List[tp.List[int]], cv2: tp.Any, np: tp.Any,
                 stage_cb: tp.Optional[tp.Callable]) -> tp.Tuple[tp.List, tp.List]:
        """
        Description:
            Boxes (xyxy) and optional per-box labels, from the chosen detector.

        Args:
            (1) frame_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
            (2) cv2 [module]: The OpenCV module.
            (3) np [module]: The NumPy module.
            (4) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Tuple]: (boxes, per-box labels or None).
        """

        if CONST_DETECTOR == 'segment':
            if stage_cb:
                stage_cb('Segmenting…')
            bg_bgr = self.__Load_Background(cv2, frame_bgr.shape)
            # Stage-2 FastSAM will consume the candidate regions; the legacy
            # 'segment' path still derives its boxes from the mask via Find_Objects.
            mask, _regions = Build_Mask(bg_bgr, frame_bgr, cv2, np)
            boxes = Find_Objects(mask, cv2, np)
            return boxes, [None] * len(boxes)
        return self.__Detect_Florence(frame_bgr, stage_cb)

    def Analyze(self, image: tp.List[tp.List[int]], progress_cb: tp.Optional[tp.Callable] = None,
                stage_cb: tp.Optional[tp.Callable] = None) -> Analysis_Str:
        """
        Description:
            Analyse one RGB frame: detect the object boxes, describe each crop, and
            compose the panel's reading. The frame is a contiguous RGB array (the UI
            converts the QImage), so this method never touches Qt.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame as a contiguous RGB array.
            (2) progress_cb [function]: Optional (done, total) progress hook.
            (3) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Analysis_Str(object)]: The finished scene reading.
        """

        t0 = time.perf_counter()
        self.__Ensure_Loaded(stage_cb)
        cv2, np, torch, pil = self.__cv2, self.__np, self.__torch, self.__pil
        size = (image.shape[1], image.shape[0])   # (width, height)

        # RGB -> BGR: the pipeline works in BGR, the exchange format is RGB.
        frame_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        boxes, det_labels = self.__Detect(frame_bgr, cv2, np, stage_cb)

        objects = []
        total = len(boxes)
        for i, box in enumerate(boxes):
            if progress_cb:
                progress_cb(i, total)
            crop = Crop_With_Pad(frame_bgr, box)
            caption = Describe(self.__model, self.__processor, self.__device,
                               self.__dtype, crop, cv2, np, torch, pil)
            label = Condense_Label(caption)
            # If the caption gave nothing usable, fall back to the detector's own
            # class label (e.g. <OD>'s 'screw') rather than the 'object' default.
            if label == 'object' and det_labels[i]:
                label = ' '.join(det_labels[i].split()[:CONST_LABEL_MAX_WORDS]).lower()
            x1, y1, x2, y2 = box
            objects.append(Detection_Str(
                Label=label,
                Bbox=(x1, y1, x2 - x1, y2 - y1),   # xyxy -> xywh, frame pixels
                Confidence=None,                   # Florence-2 emits no score
                Detail=caption,
            ))
        if progress_cb:
            progress_cb(total, total)

        caption = '' if objects else CONST_EMPTY_SCENE_EXPLANATION
        objects, summary, note = Compose(objects, size, caption=caption)
        badge, level = Verdict(objects)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return Analysis_Str(Summary=summary, Objects=objects, Note=note,
                            Latency_Ms=latency_ms, Verdict=badge, Verdict_Level=level,
                            Task=CONST_VISION_TASK_LABEL)
