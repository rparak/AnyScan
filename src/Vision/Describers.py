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
import gc
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the configured stage parameters (weights, prompts, generation)
#   ../Parameters/Configuration
from Parameters.Configuration import Description_Parameters_Str

"""
Description:
    Initialization of constants.

    Stage 4's describer: the model that writes an object's description and the one background
    sentence. A describer answers one call — Describe(crop, purpose, prompt) with purpose 'object' or
    'background' — and maps the purpose to its own input (Gemma: a prompt from the configuration),
    unless the pipeline passes a prompt: a catalogue mode's filled Describer.Prompt for a judged part
    (Reporting.Describer_Prompt). A future model plugs in behind the same interface. The describer
    loads its runtime lazily (Load), so importing this module pulls no heavy library. (Florence-2, the
    previous describer, was removed after the comparison over the seven frames of the previous test
    set, eb00508^ — docs/design-decisions.md.)
"""
# The two things a describer is asked to describe.
#   Unit [string]
CONST_PURPOSE_OBJECT = 'object'
CONST_PURPOSE_BACKGROUND = 'background'

# ---- Gemma 4 ------------------------------------------------------------------ #
# The local Gemma 4 E4B instruction-tuned weights, an MLX 4-bit conversion
# (mlx-community/gemma-4-e4b-it-4bit, from google/gemma-4-E4B-it revision fee6332), run on the
# Metal GPU through MLX / mlx-vlm. Loaded from the directory the configuration names
# (Description.Model), never a hub id.
#
# LICENCE: the Gemma 4 weights are licensed under the Apache License 2.0
# (https://ai.google.dev/gemma/docs/gemma_4_license) — NOT the MIT licence this repository's
# code carries, so the repository's licence does not cover them; anyone shipping them does so
# under Apache 2.0's conditions. models/ is gitignored, so the weights are not in the
# repository. (The mlx-community card's 'license: gemma' tag looks like converter boilerplate;
# see README > Licence note.)
#
# Generation (Description.Temperature, Description.Max_Tokens) is configuration. Temperature 0 is
# greedy decoding: the same crop and prompt give the same text, which the pipeline relies on (a
# description is a property of the object). The weights' own generation_config samples
# (temperature 1.0, top-k 64, top-p 0.95); the configured value overrides it. Measured on Apple
# silicon (Metal): repeated runs on the same crop, runs on other threads, in other processes and
# under memory pressure were identical word for word. Greedy decoding fixes the sampler, not the
# arithmetic: another MLX backend (Linux CUDA / CPU) can differ in floating point and so in text,
# so this is a measured property of that build, not a guarantee that travels (README > Platform).
# Gemma 4's thinking mode stays off: the answer, not a reasoning trace, is the description.
#   Unit [bool]
CONST_GEMMA_THINKING = False

class Describer_Error_Cls(RuntimeError):
    """
    Description:
        Raised when a describer cannot run (runtime missing, weights unreadable). Its message is a full sentence for the Scene Understanding panel.
    """


class Describer_Backend_Cls(object):
    """
    Description:
        The describer interface. Load() once (on a configuration load, the first CONNECT, or
        lazily on the first analysis), then Describe(crop_bgr, purpose) -> the model's text.
        (The Task a reading is labelled with is the configuration's Identity.Task, not the
        describer's.)

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class (a concrete subclass).
                Cls = Gemma_Describer_Cls(Description_Parameters_Str)

            Features:
                # Functions of the class.
                Cls.Load(); Cls.Describe(crop_bgr, CONST_PURPOSE_OBJECT)
    """

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

    def Describe(self, crop_bgr: tp.Any, purpose: str, prompt: str = '') -> str:
        """
        Description:
            Describe one image for a purpose.

        Args:
            (1) crop_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (2) purpose [string]: CONST_PURPOSE_OBJECT or CONST_PURPOSE_BACKGROUND.
            (3) prompt [string]: The prompt for this image instead of the purpose's ('' for the purpose's): a
                                 catalogue mode's filled Describer.Prompt for a judged part.

        Returns:
            (1) parameter [string]: The model's text, stripped.
        """

        raise NotImplementedError

    @property
    def Last_Tokens(self) -> tp.Optional[tp.Tuple[int, int]]:
        """
        Description:
            The token counts of the last Describe: the prompt's (image and text) and the generated
            text's.

        Returns:
            (1) parameter [Tuple<int> 1x2 or None]: (input tokens, output tokens), or None before
                                                   the first Describe.
        """

        raise NotImplementedError


class Gemma_Describer_Cls(Describer_Backend_Cls):
    """
    Description:
        Gemma 4 E4B (4-bit MLX) prompted in natural language: the per-object and background
        prompts come from the configuration (Description.Prompts — data, iterated without
        touching code), the crop goes in as an RGB image, and generation runs at the configured
        temperature (0: greedy) with thinking off, so the same crop yields the same text.

        Note:
            mlx / mlx-vlm are imported inside Load, never at module level, so the window and
            the tests import this module without them. Each generation is followed by
            mx.synchronize(), so Describe returns with its GPU work complete and the time it is
            charged is its own (measured: generate already returns with nothing pending, so the
            sync costs nothing today). A model loaded on one thread generates
            on another (measured: the app loads on the model-load worker's thread and
            describes on the analysis workers').

    Initialization of the Class:
        Args:
            (1) Description_Parameters_Str [Description_Parameters_Str(object)]: The configured
                weights directory, prompts and generation settings.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Gemma_Describer_Cls(Configuration_Str.Description)

            Features:
                # Properties of the class.
                Cls.Loaded; Cls.Model_Key; Cls.Last_Tokens

                # Functions of the class.
                Cls.Load(); Cls.Describe(crop_bgr, CONST_PURPOSE_OBJECT); Cls.Release()
                Cls.Set_Parameters(Description_Parameters_Str)
    """

    def __init__(self, Description_Parameters_Str: Description_Parameters_Str) -> None:
        # << PRIVATE >> #
        self.__params = Description_Parameters_Str
        self.__model_dir = Description_Parameters_Str.Model_Path
        self.__model = None
        self.__processor = None
        self.__generate = None
        self.__template = None
        self.__pil = None
        self.__cv2 = None
        self.__mx = None
        self.__last_tokens = None

    @property
    def Loaded(self) -> bool:
        """
        Description:
            Whether the model is loaded.

        Returns:
            (1) parameter [bool]: True once Load has succeeded.
        """

        return self.__model is not None

    @property
    def Model_Key(self) -> str:
        """
        Description:
            What identifies the loaded model: its weights directory. Two configurations with the
            same key can share this instance without a reload.

        Returns:
            (1) parameter [string]: The weights directory.
        """

        return self.__model_dir

    @property
    def Last_Tokens(self) -> tp.Optional[tp.Tuple[int, int]]:
        """
        Description:
            The token counts mlx-vlm reported for the last Describe.

        Returns:
            (1) parameter [Tuple<int> 1x2 or None]: (prompt tokens, generated tokens), or None
                                                   before the first Describe.
        """

        return self.__last_tokens

    def Set_Parameters(self, Description_Parameters_Str: Description_Parameters_Str) -> None:
        """
        Description:
            Adopt another configuration's prompts and generation settings while keeping the
            loaded model. Only valid when the new parameters have the same Model_Key.

        Args:
            (1) Description_Parameters_Str [Description_Parameters_Str(object)]: The parameters.
        """

        assert Description_Parameters_Str.Model_Path == self.Model_Key
        self.__params = Description_Parameters_Str

    def Release(self) -> None:
        """
        Description:
            Drop the loaded model and return its GPU memory, so another model can load without
            holding both at once. Best effort: a missing MLX cache API is skipped.
        """

        self.__model = self.__processor = None
        gc.collect()
        try:
            import mlx.core as mx
            (getattr(mx, 'clear_cache', None) or mx.metal.clear_cache)()
        except (ImportError, AttributeError, RuntimeError):
            pass

    def Load(self) -> None:
        """
        Description:
            Import MLX / mlx-vlm and load the weights, once. (The prompts are validated with
            the configuration, before any model is touched.)
        """

        if self.__model is not None:
            return
        try:
            import cv2
            from PIL import Image as PILImage
            import mlx.core as mx
            from mlx_vlm import load, generate
            from mlx_vlm.prompt_utils import apply_chat_template
        except ImportError as exc:
            raise Describer_Error_Cls(
                'The Gemma describer needs MLX (mlx and mlx-vlm). requirements.txt installs them on '
                'macOS on Apple silicon; on Linux install mlx with the backend extra for the '
                'machine (README > Platform).') from exc
        if not os.path.isdir(self.__model_dir):
            raise Describer_Error_Cls('The model weights are not at "%s". Check that the directory '
                                      'is complete and readable.' % self.__model_dir)
        try:
            model, processor = load(self.__model_dir)
        except Exception as exc:                          # noqa: BLE001
            raise Describer_Error_Cls('The model weights at "%s" could not be loaded. Check that the '
                                      'directory is complete and readable.' % self.__model_dir) from exc
        self.__generate, self.__template = generate, apply_chat_template
        self.__pil, self.__cv2, self.__mx = PILImage, cv2, mx
        self.__model, self.__processor = model, processor

    def Describe(self, crop_bgr: tp.Any, purpose: str, prompt: str = '') -> str:
        """
        Description:
            One generation for the purpose's prompt (or the given one) on one image, at the configured
            Description.Temperature (0, the shipped value, is greedy).

        Args:
            (1) crop_bgr [Matrix<uint8> HxWx3]: The image (BGR).
            (2) purpose [string]: CONST_PURPOSE_OBJECT or CONST_PURPOSE_BACKGROUND.
            (3) prompt [string]: The prompt for this image instead of the purpose's ('' for the purpose's).

        Returns:
            (1) parameter [string]: The model's text, stripped.
        """

        params = self.__params
        prompt = prompt or (params.Prompt_Object if purpose == CONST_PURPOSE_OBJECT else params.Prompt_Background)
        image = self.__pil.fromarray(self.__cv2.cvtColor(crop_bgr, self.__cv2.COLOR_BGR2RGB))
        formatted = self.__template(self.__processor, self.__model.config, prompt, num_images=1,
                                    enable_thinking=CONST_GEMMA_THINKING)
        result = self.__generate(self.__model, self.__processor, formatted, image=[image],
                                 max_tokens=params.Max_Tokens,
                                 temperature=params.Temperature, verbose=False)
        self.__mx.synchronize()
        self.__last_tokens = (int(result.prompt_tokens), int(result.generation_tokens))
        return result.text.strip()

