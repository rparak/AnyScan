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
# File Name: ../Vision/Describers.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the configuration layer (the Gemma prompts) and Florence's caption pass
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Describer_Prompts, CONST_DESCRIBER_PROMPTS_FILE
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Describe

"""
Description:
    Initialization of constants.

    Stage 4's describers: the model that writes an object's description and the one background
    sentence. Every describer answers the same call — Describe(crop, purpose) with purpose
    'object' or 'background' — and maps the purpose to its own input: Florence-2 to a task
    token, Gemma to a prompt. The pipeline (Vision.Core) never sees a token or a prompt, so it
    reads the same whichever model runs. Each describer loads its runtime lazily (Load), so
    importing this module pulls no heavy library.
"""
# The two things a describer is asked to describe.
#   Unit [string]
CONST_PURPOSE_OBJECT = 'object'
CONST_PURPOSE_BACKGROUND = 'background'

# ---- Gemma 4 (the default describer) ---------------------------------------- #
# The local Gemma 4 E4B instruction-tuned weights, an MLX 4-bit conversion
# (mlx-community/gemma-4-e4b-it-4bit, from google/gemma-4-E4B-it revision fee6332), run on the
# Metal GPU through MLX / mlx-vlm. Loaded from this directory only, never a hub id.
#
# LICENCE: the Gemma weights are governed by the Gemma Terms of Use
# (https://ai.google.dev/gemma/terms) and its Prohibited Use Policy — NOT the MIT licence this
# repository's code carries. They are not redistributable under the repository's licence;
# anyone shipping them must pass on Google's terms. models/ is gitignored, so the weights are
# not in the repository.
CONST_GEMMA_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                 'models', 'gemma-4-e4b-it-4bit'))
# Generation. temperature 0 is greedy decoding: the same crop and prompt give the same text,
# which the pipeline relies on (a description is a property of the object). The weights'
# own generation_config samples (temperature 1.0, top-k 64, top-p 0.95); this overrides it.
# Measured: repeated runs on the same crop, and runs on other threads, were identical.
#   Unit [float] / [int]
CONST_GEMMA_TEMPERATURE = 0.0
CONST_GEMMA_MAX_TOKENS = 256
# Gemma 4's thinking mode stays off: the answer, not a reasoning trace, is the description.
#   Unit [bool]
CONST_GEMMA_THINKING = False

# ---- Florence-2 (kept reachable for the comparison; CONST_DESCRIBER = 'florence') ---- #
# The local Florence-2 weights (MIT licensed — keep Microsoft's notice with the project),
# loaded with local_files_only, never a hub id.
CONST_FLORENCE_MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                 'models', 'florence2-large-ft'))
# Florence's task token per purpose: the detailed paragraph per object, the concise caption
# for the background (on a plain surface the detailed task confabulates).
#   Unit [Dict<string, string>]
CONST_FLORENCE_TASKS = {CONST_PURPOSE_OBJECT: '<MORE_DETAILED_CAPTION>',
                        CONST_PURPOSE_BACKGROUND: '<CAPTION>'}
# Torch device: 'auto' picks cuda, then mps, then cpu. float32 is deliberate — fp16 on
# Apple's MPS backend is unreliable for this model.
CONST_FLORENCE_DEVICE = 'auto'


class Describer_Error_Cls(RuntimeError):
    """
    Description:
        Raised when a describer cannot run (runtime missing, weights unreadable, prompts
        missing). Its message is a full sentence for the Scene Understanding panel.
    """


class Describer_Backend_Cls(object):
    """
    Description:
        The describer interface. Load() once (lazily, on the first analysis), then
        Describe(crop_bgr, purpose) -> the model's text. Name identifies the model in the
        audit; Task_Label is what the reading panel's Task row and each capture set's 'task'
        record — what produced that reading.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class (a concrete subclass).
                Cls = Gemma_Describer_Cls()

            Features:
                # Functions of the class.
                Cls.Load(); Cls.Describe(crop_bgr, CONST_PURPOSE_OBJECT)
    """

    Name = ''
    Task_Label = ''

    @property
    def Loaded(self) -> bool:
        """
        Description:
            Whether the model is loaded.

        Returns:
            (1) parameter [bool]: True once Load has succeeded.
        """

        raise NotImplementedError

    def Load(self) -> None:
        """
        Description:
            Load the model and its runtime, once. Raises Describer_Error_Cls on failure.
        """

        raise NotImplementedError

    def Describe(self, crop_bgr: tp.Any, purpose: str) -> str:
        """
        Description:
            Describe one image for a purpose.

        Args:
            (1) crop_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (2) purpose [string]: CONST_PURPOSE_OBJECT or CONST_PURPOSE_BACKGROUND.

        Returns:
            (1) parameter [string]: The model's text, stripped.
        """

        raise NotImplementedError


class Gemma_Describer_Cls(Describer_Backend_Cls):
    """
    Description:
        Gemma 4 E4B (4-bit MLX) prompted in natural language: the per-object and background
        prompts come from Configuration/Describer_Prompts.yaml (data, iterated without
        touching code), the crop goes in as an RGB image, and generation is greedy
        (CONST_GEMMA_TEMPERATURE = 0) with thinking off, so the same crop yields the same text.

        Note:
            mlx / mlx-vlm are imported inside Load, never at module level, so the window and
            the tests import this module without them. A model loaded on one thread generates
            on another (measured: the app loads on the first analysis's worker thread and
            describes on later ones).

    Initialization of the Class:
        Args:
            (1) model_dir [string or None]: The weights directory (None: CONST_GEMMA_MODEL_DIR).
            (2) prompts_file [string or None]: The prompts file (None: CONST_DESCRIBER_PROMPTS_FILE).

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Gemma_Describer_Cls()
    """

    Name = 'gemma-4-e4b-it-4bit'
    Task_Label = 'part inspection'

    def __init__(self, model_dir: tp.Optional[str] = None,
                 prompts_file: tp.Optional[str] = None) -> None:
        # << PRIVATE >> #
        # The module constants are read here, not bound as argument defaults, so a caller (or a
        # test) that repoints them before construction is honoured.
        self.__model_dir = model_dir or CONST_GEMMA_MODEL_DIR
        self.__prompts_file = prompts_file or CONST_DESCRIBER_PROMPTS_FILE
        self.__model = None
        self.__processor = None
        self.__prompts = None
        self.__generate = None
        self.__template = None
        self.__pil = None
        self.__cv2 = None

    @property
    def Loaded(self) -> bool:
        """
        Description:
            Whether the model is loaded.

        Returns:
            (1) parameter [bool]: True once Load has succeeded.
        """

        return self.__model is not None

    def Load(self) -> None:
        """
        Description:
            Read the prompts, import MLX / mlx-vlm and load the weights, once. The prompts are
            read first, so a missing prompt fails before a 5 GB load.
        """

        if self.__model is not None:
            return
        prompts = Read_Describer_Prompts(self.__prompts_file)
        if prompts is None:
            raise Describer_Error_Cls(
                'The describer prompts at "%s" are missing or incomplete: it must hold a non-empty '
                '"Object" and "Background" prompt.' % self.__prompts_file)
        try:
            import cv2
            from PIL import Image as PILImage
            from mlx_vlm import load, generate
            from mlx_vlm.prompt_utils import apply_chat_template
        except ImportError as exc:
            raise Describer_Error_Cls(
                'The Gemma describer needs MLX: install mlx and mlx-vlm (requirements.txt) on this '
                'Apple-silicon Mac, then analyse again.') from exc
        if not os.path.isdir(self.__model_dir):
            raise Describer_Error_Cls('The model weights are not at "%s". Check that the directory '
                                      'is complete and readable.' % self.__model_dir)
        try:
            model, processor = load(self.__model_dir)
        except Exception as exc:                          # noqa: BLE001
            raise Describer_Error_Cls('The model weights at "%s" could not be loaded. Check that the '
                                      'directory is complete and readable.' % self.__model_dir) from exc
        self.__prompts, self.__generate, self.__template = prompts, generate, apply_chat_template
        self.__pil, self.__cv2 = PILImage, cv2
        self.__model, self.__processor = model, processor

    def Describe(self, crop_bgr: tp.Any, purpose: str) -> str:
        """
        Description:
            One greedy generation for the purpose's prompt on one image.

        Args:
            (1) crop_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (2) purpose [string]: CONST_PURPOSE_OBJECT or CONST_PURPOSE_BACKGROUND.

        Returns:
            (1) parameter [string]: The model's text, stripped.
        """

        prompt = self.__prompts['Object' if purpose == CONST_PURPOSE_OBJECT else 'Background']
        image = self.__pil.fromarray(self.__cv2.cvtColor(crop_bgr, self.__cv2.COLOR_BGR2RGB))
        formatted = self.__template(self.__processor, self.__model.config, prompt, num_images=1,
                                    enable_thinking=CONST_GEMMA_THINKING)
        result = self.__generate(self.__model, self.__processor, formatted, image=[image],
                                 max_tokens=CONST_GEMMA_MAX_TOKENS,
                                 temperature=CONST_GEMMA_TEMPERATURE, verbose=False)
        return result.text.strip()


class Florence_Describer_Cls(Describer_Backend_Cls):
    """
    Description:
        Florence-2 (large, fine-tuned) driven by task tokens (CONST_FLORENCE_TASKS), run through
        transformers on torch. Kept reachable (CONST_DESCRIBER = 'florence') so both models can
        be run over the same frames; the caption pass itself is Vision.Utilities.Caption.Describe.

    Initialization of the Class:
        Args:
            (1) model_dir [string or None]: The weights directory (None: CONST_FLORENCE_MODEL_DIR).

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Florence_Describer_Cls()
    """

    Name = 'florence2-large-ft'
    Task_Label = 'detailed caption'

    def __init__(self, model_dir: tp.Optional[str] = None) -> None:
        # << PRIVATE >> #
        self.__model_dir = model_dir or CONST_FLORENCE_MODEL_DIR
        self.__model = None
        self.__processor = None
        self.__device = None
        self.__dtype = None
        self.__torch = None
        self.__pil = None
        self.__cv2 = None
        self.__np = None

    @property
    def Loaded(self) -> bool:
        """
        Description:
            Whether the model is loaded.

        Returns:
            (1) parameter [bool]: True once Load has succeeded.
        """

        return self.__model is not None

    def __Pick_Device(self, torch: tp.Any) -> tp.Any:
        """
        Description:
            Choose the torch device from CONST_FLORENCE_DEVICE ('auto' -> cuda, then mps, then cpu).

        Args:
            (1) torch [module]: The torch module.

        Returns:
            (1) parameter [torch.device]: The selected device.
        """

        if CONST_FLORENCE_DEVICE != 'auto':
            return torch.device(CONST_FLORENCE_DEVICE)
        if torch.cuda.is_available():
            return torch.device('cuda')
        if torch.backends.mps.is_available():
            return torch.device('mps')
        return torch.device('cpu')

    def Load(self) -> None:
        """
        Description:
            Import torch / transformers and load the native Florence2ForConditionalGeneration
            weights (local_files_only, no trust_remote_code), once.
        """

        if self.__model is not None:
            return
        try:
            import cv2
            import numpy as np
            import torch
            from PIL import Image as PILImage
            from transformers import AutoProcessor, Florence2ForConditionalGeneration
        except ImportError as exc:
            raise Describer_Error_Cls(
                'The vision runtime is not installed. Install torch, transformers '
                'and Pillow into this environment, then scan again.') from exc
        device = self.__Pick_Device(torch)
        dtype = torch.float32  # fp16 on MPS is unreliable for this model
        try:
            model = Florence2ForConditionalGeneration.from_pretrained(
                self.__model_dir, dtype=dtype, local_files_only=True)
            model.to(device)
            model.eval()
            processor = AutoProcessor.from_pretrained(self.__model_dir, local_files_only=True)
        except Exception as exc:                          # noqa: BLE001
            raise Describer_Error_Cls('The model weights at "%s" could not be loaded. Check that the '
                                      'directory is complete and readable.' % self.__model_dir) from exc
        self.__torch, self.__pil, self.__cv2, self.__np = torch, PILImage, cv2, np
        self.__model, self.__processor = model, processor
        self.__device, self.__dtype = device, dtype

    def Describe(self, crop_bgr: tp.Any, purpose: str) -> str:
        """
        Description:
            One Florence-2 caption pass with the purpose's task token.

        Args:
            (1) crop_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (2) purpose [string]: CONST_PURPOSE_OBJECT or CONST_PURPOSE_BACKGROUND.

        Returns:
            (1) parameter [string]: The raw caption.
        """

        return Describe(self.__model, self.__processor, self.__device, self.__dtype, crop_bgr,
                        self.__cv2, self.__np, self.__torch, self.__pil,
                        task=CONST_FLORENCE_TASKS[purpose])


# The describers by the name CONST_DESCRIBER selects them with ('fallback' is model-free and
# lives in Vision.Describe_Fallback).
#   Unit [Dict<string, class>]
CONST_DESCRIBERS = {'gemma': Gemma_Describer_Cls, 'florence': Florence_Describer_Cls}
