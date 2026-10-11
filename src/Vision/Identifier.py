## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../Vision/Identifier.py
## =========================================================================== ##

# System (Default)
import os
import gc
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The catalogue mode's identifier: DINOv2 (base), run locally, turning an image into one unit vector —
    the class token of its last layer — so two images compare by their dot product (cosine similarity).
    Vision.Utilities.Classify decides with the similarities; this module only embeds.

    Note:
        This module is Qt-free and its bare import is cheap: torch and transformers are imported when
        the model loads, never at module load. The model loads from its local directory only
        (local_files_only), never from the hub.

        The image is resized to the model's input size whole — not resized and centre-cropped, as the
        model card's processor does — because a crop is already the part: centre-cropping a 2:3 plate
        would cut its holes off. The normalisation (mean, std) is the processor's own, read from the
        model directory.
"""
# The model's input size: DINOv2's 224 x 224 (16 x 16 patches of 14 px).
#   Unit [int] (px)
CONST_IDENTIFIER_INPUT_PX = 224
# How many images go through the model at once: a frame's objects times four rotations stay one
# batch on the rig (9 objects, 36 images), and a larger scene is split rather than run out of memory.
#   Unit [int]
CONST_IDENTIFIER_BATCH = 64


class Identifier_Error_Cls(RuntimeError):
    """
    Description:
        The identifier could not load or run. The message is a full sentence the operator sees: what
        failed and what to do.
    """


class Dino_Identifier_Cls(object):
    """
    Description:
        DINOv2 from a local directory: Load once, Embed images (BGR) to unit vectors, Release to hand
        the accelerator memory back.

    Initialization of the Class:
        Args:
            (1) model_path [string]: The DINOv2 weights directory (absolute).
            (2) device [string]: 'auto' (cuda, then mps, then cpu), 'cpu', 'mps', 'cuda' or 'cuda:N'.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Dino_Identifier_Cls('/path/models/dinov2-base', 'auto')

            Features:
                # Properties of the class.
                Cls.Loaded; Cls.Model_Key

                # Functions of the class.
                Cls.Load(stage_cb); Cls.Embed(images_bgr, cv2, np); Cls.Release()
    """

    def __init__(self, model_path: str, device: str) -> None:
        # << PRIVATE >> #
        self.__model_path = model_path
        self.__device_setting = device
        self.__model = None
        self.__device = None
        self.__torch = None
        self.__mean = None
        self.__std = None

    @property
    def Loaded(self) -> bool:
        """
        Description:
            Whether the model is loaded.

        Returns:
            (1) parameter [bool]: True once Load has loaded it.
        """

        return self.__model is not None

    @property
    def Model_Key(self) -> tp.Tuple[str, str]:
        """
        Description:
            What identifies the loaded model: the weights directory and the device setting. Two
            configurations with the same key can share this instance without a reload.

        Returns:
            (1) parameter [Tuple<string> 1x2]: (weights directory, device setting).
        """

        return (self.__model_path, self.__device_setting)

    def Load(self, stage_cb: tp.Optional[tp.Callable] = None) -> None:
        """
        Description:
            Import the runtime and load the model once, on the configured device.

        Args:
            (1) stage_cb [function]: Optional (text) phase hook.

        Raises:
            Identifier_Error_Cls: The weights or the runtime are missing, or the weights do not load.
        """

        if self.__model is not None:
            return
        if not os.path.isfile(os.path.join(self.__model_path, 'config.json')):
            raise Identifier_Error_Cls(
                'The DINOv2 weights at "%s" could not be found. Run ./install.sh, which downloads and '
                'verifies them, or point Catalogue.Identifier in the configuration at them.' % self.__model_path)
        if stage_cb:
            stage_cb('Loading identifier…')
        try:
            import numpy as np
            import torch
            from transformers import AutoImageProcessor, AutoModel
        except ImportError as exc:
            raise Identifier_Error_Cls(
                'The identification runtime is not installed. Install torch and transformers into this '
                'environment (see README > Setup), then load the configuration again.') from exc
        device = self.__device_setting
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else ('mps' if torch.backends.mps.is_available() else 'cpu')
        try:
            processor = AutoImageProcessor.from_pretrained(self.__model_path, local_files_only=True)
            model = AutoModel.from_pretrained(self.__model_path, local_files_only=True).to(device).eval()
        except Exception as exc:                          # noqa: BLE001
            raise Identifier_Error_Cls(
                'The DINOv2 weights at "%s" could not be loaded. Run ./install.sh to download and verify '
                'them again.' % self.__model_path) from exc
        self.__mean = np.array(processor.image_mean, dtype=np.float32)
        self.__std = np.array(processor.image_std, dtype=np.float32)
        self.__torch, self.__model, self.__device = torch, model, device

    def Embed(self, images_bgr: tp.List[tp.Any], cv2: tp.Any, np: tp.Any, patches: bool = False) -> tp.Any:
        """
        Description:
            Each image (BGR) as one unit vector: resized whole to the input size, converted to RGB,
            normalised by the model's processor, and its last layer's class token normalised to length 1.
            With patches, also each image's patch tokens from the same pass, each normalised to length 1
            (16 x 16 at the 224 px input): the similarity overlay's input, at no extra model time.

        Args:
            (1) images_bgr [Vector<Matrix<uint8> hxwx3>]: The images.
            (2) cv2 [module]: The OpenCV module, injected by the caller.
            (3) np [module]: The NumPy module, injected by the caller.
            (4) patches [bool]: Also return the patch tokens.

        Returns:
            (1) parameter [Matrix<float> NxD, or Tuple<Matrix<float> NxD, Array<float> NxPxD>]: One unit row per
                image, in order; with patches, (rows, each image's unit patch rows).
        """

        self.Load()
        torch, size = self.__torch, CONST_IDENTIFIER_INPUT_PX
        rows, patch_rows = [], []
        for start in range(0, len(images_bgr), CONST_IDENTIFIER_BATCH):
            batch = []
            for image in images_bgr[start:start + CONST_IDENTIFIER_BATCH]:
                rgb = cv2.cvtColor(cv2.resize(image, (size, size), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
                batch.append(((rgb.astype(np.float32) / 255.0 - self.__mean) / self.__std).transpose(2, 0, 1))
            with torch.no_grad():
                pixels = torch.from_numpy(np.stack(batch)).to(self.__device)
                hidden = self.__model(pixel_values=pixels).last_hidden_state
                rows.append(torch.nn.functional.normalize(hidden[:, 0], dim=-1).cpu().numpy())
                if patches:
                    patch_rows.append(torch.nn.functional.normalize(hidden[:, 1:], dim=-1).cpu().numpy())
        embedded = np.concatenate(rows) if rows else np.zeros((0, 0), dtype=np.float32)
        if not patches:
            return embedded
        return embedded, (np.concatenate(patch_rows) if patch_rows else np.zeros((0, 0, 0), dtype=np.float32))

    def Release(self) -> None:
        """
        Description:
            Drop the model and return its accelerator memory. Best effort: a missing torch cache API is
            skipped.
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
