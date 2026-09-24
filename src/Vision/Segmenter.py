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
# File Name: ../Vision/Segmenter.py
## =========================================================================== ##

# System (Default)
import os
import gc
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the configured stage parameters
#   ../Parameters/Configuration
from Parameters.Configuration import Segmentation_Parameters_Str

"""
Description:
    Initialization of constants.

    Stage 2 of the pipeline: instance segmentation. A Segmenter_Backend_Cls turns a
    frame plus the stage-1 candidate regions into full-resolution boolean masks and
    per-mask confidences. Fast_Sam_Cls is the concrete backend (FastSAM-x via
    ultralytics); the abstraction is the seam that lets SAM 2 replace it later
    without touching stages 1, 3 or 4 — the same shape Vision_Backend_Cls ->
    Vision_Pipeline_Cls has.

    Note:
        This module is Qt-free and its bare import is cheap. ultralytics (which
        transitively pulls torch, OpenCV and matplotlib) is imported lazily on the
        first Segment call, never at module load, so importing this module — as the
        Qt-free separation test does — pulls no heavy runtime and no Qt backend.
"""
# The backend name presented in logs and the example script.
CONST_SEGMENTER_NAME = 'FastSAM-x'

# retina_masks returns full-resolution masks. (The weights, device, prompting mode and FastSAM's
# confidence / IoU / inference size are configuration: Segmentation_Parameters_Str.)
CONST_SEGMENTER_RETINA_MASKS = True

# Safety valve: the most masks kept from everything-mode (highest confidence
# first), so a busy frame cannot flood stage 3.
CONST_SEGMENTER_MAX_MASKS = 64


class Segmenter_Error_Cls(RuntimeError):
    """
    Description:
        Raised for a segmentation failure the operator needs to see on screen. Its
        message must be a full, actionable sentence.
    """


class Segmenter_Backend_Cls(object):
    """
    Description:
        The instance-segmentation interface. One method matters: Segment(image,
        regions) returns per-instance boolean masks and confidences, so swapping
        FastSAM for SAM 2 never touches the caller.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class (a concrete subclass).
                Cls = Fast_Sam_Cls()

            Features:
                # Functions of the class.
                Cls.Segment(image_bgr, regions)
    """

    Name = 'segmenter'

    def Segment(self, image: tp.List[tp.List[int]], regions: tp.List[tp.Tuple[int, int, int, int]],
                stage_cb: tp.Optional[tp.Callable] = None) -> tp.Tuple[tp.List, tp.List[tp.Optional[float]]]:
        """
        Description:
            Segment one frame into per-instance masks, optionally prompted by the
            stage-1 candidate regions.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame (BGR), full resolution.
            (2) regions [Vector<Tuple<int> 1x4>]: Candidate boxes as (x1, y1, x2, y2).
            (3) stage_cb [function]: Optional (text) phase hook.

        Returns:
            (1) parameter [Tuple]: (masks as a Vector<Matrix<bool> HxW> at the frame
                                   resolution, confidences as a Vector<float or None>
                                   aligned with the masks).
        """

        raise NotImplementedError


class Fast_Sam_Cls(Segmenter_Backend_Cls):
    """
    Description:
        FastSAM-x through ultralytics, loaded from the configured local weights file.

        Note:
            Notes that cost hours if missed:
              (1) ultralytics is imported lazily inside Segment, never at module
                  load, so a bare import of this module stays cheap and Qt-free
                  (ultralytics pulls matplotlib). The one-time 'settings updated'
                  warning ultralytics logs on import is silenced at that boundary.
              (2) The model loads once and is kept: Load() preloads it (the application
                  does, on a configuration load or the first CONNECT), otherwise the first
                  Segment pays the load. Release() drops it so its memory can be reclaimed
                  before another model loads.
              (3) Box-prompting with the stage-1 regions is preferred. The bboxes=
                  keyword arrived in ultralytics 8.2; this probes it once and falls
                  back to everything-mode if it is unsupported or the prompt fails,
                  so it degrades rather than crashing.
              (4) retina_masks=True returns full-resolution masks; each mask is still
                  resized to the exact frame size before it is returned, so stage 3
                  can score it against the change mask pixel for pixel.

    Initialization of the Class:
        Args:
            (1) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: The configured
                weights, device, prompting mode and FastSAM thresholds.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Fast_Sam_Cls(Configuration_Str.Segmentation)

            Features:
                # Properties of the class.
                Cls.Loaded; Cls.Model_Key

                # Functions of the class.
                Cls.Load(stage_cb); Cls.Segment(image_bgr, regions); Cls.Release()
                Cls.Set_Parameters(Segmentation_Parameters_Str)
    """

    Name = CONST_SEGMENTER_NAME

    def __init__(self, Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__params = Segmentation_Parameters_Str
        self.__weights_path = Segmentation_Parameters_Str.Model_Path
        self.__device_setting = Segmentation_Parameters_Str.Device
        self.__model = None
        self.__device = None
        self.__np = None
        self.__cv2 = None
        # Tri-state box-prompt capability: None until probed, then True/False.
        self.__box_prompt_ok = None

    @property
    def Loaded(self) -> bool:
        """
        Description:
            Whether the FastSAM model is loaded.

        Returns:
            (1) parameter [bool]: True once Load (or a Segment) has loaded it.
        """

        return self.__model is not None

    @property
    def Model_Key(self) -> tp.Tuple[str, str]:
        """
        Description:
            What identifies the loaded model: the weights file and the device setting. Two
            configurations with the same key can share this instance without a reload.

        Returns:
            (1) parameter [Tuple<string> 1x2]: (weights path, device setting).
        """

        return (self.__weights_path, self.__device_setting)

    def Set_Parameters(self, Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> None:
        """
        Description:
            Adopt another configuration's per-call parameters (prompting mode, FastSAM
            confidence, IoU, inference size) while keeping the loaded model. Only valid when the
            new parameters have the same Model_Key.

        Args:
            (1) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: The parameters.
        """

        assert (Segmentation_Parameters_Str.Model_Path, Segmentation_Parameters_Str.Device) == self.Model_Key
        self.__params = Segmentation_Parameters_Str

    def Load(self, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Load the model now (once), so the first Segment does not pay for it.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
        """

        self.__Ensure_Loaded(stage_cb)

    def Release(self) -> None:
        """
        Description:
            Drop the loaded model and return its accelerator memory, so another model can load
            without holding both at once. Best effort: a missing torch cache API is skipped.
        """

        self.__model = None
        gc.collect()
        try:
            import torch
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except (ImportError, AttributeError, RuntimeError):
            pass

    def __Pick_Device(self, torch: tp.Any) -> str:
        """
        Description:
            Choose the compute device string ('auto' -> cuda, then mps, then cpu) from the
            configured device setting.

        Args:
            (1) torch [module]: The torch module.

        Returns:
            (1) parameter [string]: The device string for ultralytics.
        """

        device = self.__device_setting
        if device != 'auto':
            return device
        if torch.cuda.is_available():
            return 'cuda'
        if torch.backends.mps.is_available():
            return 'mps'
        return 'cpu'

    def __Ensure_Loaded(self, stage_cb: tp.Optional[tp.Callable]) -> None:
        """
        Description:
            Import the runtime and load the FastSAM model once, caching it. Silences
            ultralytics' one-time settings warning at this boundary and reports the
            cold load through stage_cb.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.
        """

        if self.__model is not None:
            return
        if not os.path.isfile(self.__weights_path):
            raise Segmenter_Error_Cls(
                'The FastSAM weights at "%s" could not be found. Download FastSAM-x.pt '
                '(see README > Setup) and save it there, or point Segmentation.Model in the '
                'configuration at it.'
                % self.__weights_path
            )
        if stage_cb:
            stage_cb('Loading segmenter…')

        # Quiet ultralytics before it is imported. With YOLO_VERBOSE=False it sets
        # its own logger to ERROR at import, which filters the one-time 'settings
        # updated to the latest schema' warning and the per-call predict banners —
        # so that stderr chatter can never be mistaken for a real weights-missing
        # message. setdefault, so a user who wants ultralytics verbose keeps it.
        os.environ.setdefault('YOLO_VERBOSE', 'False')
        try:
            import cv2
            import numpy as np
            import torch
            from ultralytics import FastSAM
        except ImportError as exc:
            raise Segmenter_Error_Cls(
                'The segmentation runtime is not installed. Install ultralytics into '
                'this environment (see README > Setup), then scan again.'
            ) from exc

        device = self.__Pick_Device(torch)
        try:
            model = FastSAM(self.__weights_path)
        except Exception as exc:                          # noqa: BLE001
            raise Segmenter_Error_Cls(
                'The FastSAM weights at "%s" could not be loaded. Check that the file '
                'is a complete FastSAM-x checkpoint.' % self.__weights_path
            ) from exc

        self.__cv2, self.__np = cv2, np
        self.__model = model
        self.__device = device

    def __Predict(self, image: tp.List[tp.List[int]],
                  regions: tp.List[tp.Tuple[int, int, int, int]],
                  log_cb: tp.Optional[tp.Callable] = None) -> tp.Tuple[tp.Any, bool]:
        """
        Description:
            Run FastSAM once. Prefers box-prompting with the candidate regions; if
            the prompt is unsupported on this ultralytics or fails, falls back to
            everything-mode. The box-prompt capability is probed once and cached.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame (BGR).
            (2) regions [Vector<Tuple<int> 1x4>]: Candidate boxes as (x1, y1, x2, y2).
            (3) log_cb [function]: Optional (level, message) log sink for the fallback.

        Returns:
            (1) parameter [Tuple]: (the ultralytics results, was_box_prompted [bool]).
        """

        params = self.__params
        common = dict(device=self.__device, retina_masks=CONST_SEGMENTER_RETINA_MASKS,
                      imgsz=params.Image_Size, conf=params.Confidence,
                      iou=params.IoU, verbose=False)

        want_box = (params.Mode == 'box' and bool(regions)
                    and self.__box_prompt_ok is not False)
        if want_box:
            try:
                boxes = [[int(x1), int(y1), int(x2), int(y2)] for (x1, y1, x2, y2) in regions]
                results = self.__model(image, bboxes=boxes, **common)
                self.__box_prompt_ok = True
                return results, True
            except Exception as exc:                      # noqa: BLE001
                # bboxes= unsupported on this ultralytics, or the prompt failed:
                # degrade to everything-mode rather than crash (and stop retrying).
                self.__box_prompt_ok = False
                message = ('FastSAM box-prompt unavailable (%s); using everything-mode'
                           % type(exc).__name__)
                if log_cb is not None:
                    try:
                        log_cb('WARNING', message)
                    except Exception:                     # noqa: BLE001
                        pass
                else:
                    print('[WARN] ' + message)

        results = self.__model(image, **common)
        return results, False

    def Segment(self, image: tp.List[tp.List[int]], regions: tp.List[tp.Tuple[int, int, int, int]],
                stage_cb: tp.Optional[tp.Callable] = None,
                log_cb: tp.Optional[tp.Callable] = None) -> tp.Tuple[tp.List, tp.List[tp.Optional[float]]]:
        """
        Description:
            Segment one frame into per-instance boolean masks at the frame resolution,
            each with a confidence. Box-prompted by the candidate regions when
            possible; everything-mode is capped at CONST_SEGMENTER_MAX_MASKS.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame (BGR), full resolution.
            (2) regions [Vector<Tuple<int> 1x4>]: Candidate boxes as (x1, y1, x2, y2).
            (3) stage_cb [function]: Optional (text) phase hook.
            (4) log_cb [function]: Optional (level, message) log sink for a mode fallback.

        Returns:
            (1) parameter [Tuple]: (masks as a Vector<Matrix<bool> HxW>, confidences
                                   as a Vector<float or None> aligned with the masks).
        """

        self.__Ensure_Loaded(stage_cb)
        cv2, np = self.__cv2, self.__np
        if stage_cb:
            stage_cb('Segmenting…')

        h, w = image.shape[:2]
        try:
            results, was_box = self.__Predict(image, regions, log_cb)
        except Exception as exc:                          # noqa: BLE001
            raise Segmenter_Error_Cls(
                'The segmenter failed to process the frame. Check the device setting '
                'and the scene, then scan again.'
            ) from exc

        result = results[0] if results else None
        if result is None or result.masks is None:
            return [], []

        mask_data = result.masks.data                      # tensor (N, mh, mw)
        if hasattr(mask_data, 'cpu'):
            mask_data = mask_data.cpu().numpy()
        else:
            mask_data = np.asarray(mask_data)

        confidences = self.__Confidences(result, len(mask_data))

        # Everything-mode can return many masks; keep the most confident few. A
        # box-prompt already returns roughly one mask per region, so it is not capped.
        order = list(range(len(mask_data)))
        if not was_box and len(order) > CONST_SEGMENTER_MAX_MASKS:
            order.sort(key=lambda i: (confidences[i] is not None, confidences[i] or 0.0),
                       reverse=True)
            order = order[:CONST_SEGMENTER_MAX_MASKS]

        masks_out, confs_out = [], []
        for i in order:
            mask = mask_data[i]
            if mask.shape[:2] != (h, w):
                mask = cv2.resize(mask.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
            masks_out.append(mask.astype(bool))
            confs_out.append(confidences[i])
        return masks_out, confs_out

    def __Confidences(self, result: tp.Any, count: int) -> tp.List[tp.Optional[float]]:
        """
        Description:
            Per-mask confidences from an ultralytics result, or None where the
            backend gives none. Length-aligned to the mask count.

        Args:
            (1) result [ultralytics.Results]: One frame's result.
            (2) count [int]: The number of masks to align to.

        Returns:
            (1) parameter [Vector<float or None>]: The confidences.
        """

        boxes = getattr(result, 'boxes', None)
        conf = getattr(boxes, 'conf', None) if boxes is not None else None
        if conf is None:
            return [None] * count
        if hasattr(conf, 'cpu'):
            conf = conf.cpu().numpy()
        values = [float(c) for c in conf]
        if len(values) < count:
            values += [None] * (count - len(values))
        return values[:count]
