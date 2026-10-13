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
# File Name: ../test/Vision/test_describers.py
## =========================================================================== ##

# System (Default)
import sys
import types
# Dataclasses (a configuration copy pointed at the test's weights directory)
import dataclasses
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the describers, the configuration layer and the pipeline
#   ../Vision/Describers
from Vision.Describers import (Gemma_Describer_Cls, Describer_Error_Cls,
                               CONST_PURPOSE_OBJECT, CONST_PURPOSE_BACKGROUND)
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls, Vision_Error_Cls

"""
Description:
    The describer seam without weights: what Gemma is sent (the configuration's prompts and
    generation settings, thinking off, the crop as RGB), what fails loudly (no MLX, no weights),
    and the pipeline's describer switch. A stand-in mlx_vlm module records every call; nothing
    loads a model. (That a configuration without both prompts never loads is the configuration
    layer's test.)
"""
# The shipped configuration: the describer's prompts and generation settings come from it.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)


class _Mlx_Vlm_Cls(object):
    """A stand-in for the mlx_vlm package: records the calls a describer makes. Its methods are
    bound to the module under mlx_vlm's own names (load, generate, apply_chat_template)."""

    def __init__(self) -> None:
        self.loaded, self.templates, self.generated, self.synchronized = [], [], [], 0

    def Load(self, path):
        self.loaded.append(path)
        return types.SimpleNamespace(config='model-config'), 'processor'

    def Apply_Chat_Template(self, processor, config, prompt, **kwargs):
        self.templates.append((prompt, kwargs))
        return 'formatted:' + prompt

    def Generate(self, model, processor, formatted, **kwargs):
        self.generated.append((formatted, kwargs))
        return types.SimpleNamespace(text='  A plate.  \n', prompt_tokens=280, generation_tokens=4)

    def Synchronize(self) -> None:
        self.synchronized += 1


@pytest.fixture
def fake_mlx(monkeypatch, tmp_path):
    """Install the stand-in mlx_vlm (and mlx.core) and point the describer at an (empty) weights directory."""
    fake = _Mlx_Vlm_Cls()
    core = types.ModuleType('mlx.core')
    core.synchronize = fake.Synchronize
    mlx = types.ModuleType('mlx')
    mlx.core = core
    monkeypatch.setitem(sys.modules, 'mlx', mlx)
    monkeypatch.setitem(sys.modules, 'mlx.core', core)
    package = types.ModuleType('mlx_vlm')
    package.load, package.generate = fake.Load, fake.Generate
    utils = types.ModuleType('mlx_vlm.prompt_utils')
    utils.apply_chat_template = fake.Apply_Chat_Template
    monkeypatch.setitem(sys.modules, 'mlx_vlm', package)
    monkeypatch.setitem(sys.modules, 'mlx_vlm.prompt_utils', utils)
    fake.params = dataclasses.replace(CONST_CONFIGURATION.Description, Model_Path=str(tmp_path))
    return fake


def test_gemma_sends_the_configured_prompts_greedily_with_the_crop_as_rgb(fake_mlx) -> None:
    """
    Description:
        Each purpose sends its own prompt, from the configuration (Description.Prompts); the
        crop goes in as an RGB image (the pipeline's BGR converted); decoding uses the configured
        temperature (0: greedy) and token limit with thinking off, so the same crop yields the same
        text; the answer comes back stripped. The weights directory is loaded once, however many
        describes.
    """

    params = fake_mlx.params
    describer = Gemma_Describer_Cls(params)
    describer.Load()
    describer.Load()
    crop = np.zeros((8, 8, 3), np.uint8)
    crop[..., 0] = 200                                            # blue in BGR
    assert describer.Describe(crop, CONST_PURPOSE_OBJECT) == 'A plate.'
    describer.Describe(crop, CONST_PURPOSE_BACKGROUND)

    assert fake_mlx.loaded == [params.Model_Path]
    assert [prompt for prompt, _ in fake_mlx.templates] == [params.Prompt_Object, params.Prompt_Background]
    assert all(kwargs == {'num_images': 1, 'enable_thinking': False} for _, kwargs in fake_mlx.templates)
    for formatted, kwargs in fake_mlx.generated:
        assert kwargs['temperature'] == 0.0 and kwargs['max_tokens'] == 256
        image = kwargs['image'][0]
        assert image.mode == 'RGB' and image.getpixel((0, 0)) == (0, 0, 200)
    assert fake_mlx.generated[0][0] == 'formatted:' + params.Prompt_Object


def test_gemma_follows_another_configurations_prompts_without_reloading(fake_mlx) -> None:
    """
    Description:
        Set_Parameters swaps the prompts and generation settings of a loaded describer with the
        same weights — a mode change that needs no ~9 s reload — and the next describe uses them.
    """

    describer = Gemma_Describer_Cls(fake_mlx.params)
    describer.Load()
    other = dataclasses.replace(fake_mlx.params, Prompt_Object='Name the part.', Max_Tokens=64)
    describer.Set_Parameters(other)
    describer.Describe(np.zeros((8, 8, 3), np.uint8), CONST_PURPOSE_OBJECT)
    assert fake_mlx.loaded == [fake_mlx.params.Model_Path]                # loaded once
    assert fake_mlx.templates[-1][0] == 'Name the part.'
    assert fake_mlx.generated[-1][1]['max_tokens'] == 64


def test_gemma_sends_a_given_prompt_instead_of_the_purposes(fake_mlx) -> None:
    """
    Description:
        A prompt given with the crop (a catalogue mode's filled Describer.Prompt for a judged part) is sent
        instead of the purpose's; without one, the purpose's own prompt is sent as before.
    """

    describer = Gemma_Describer_Cls(fake_mlx.params)
    describer.Load()
    describer.Describe(np.zeros((8, 8, 3), np.uint8), CONST_PURPOSE_OBJECT, 'The part is a mounting plate.')
    describer.Describe(np.zeros((8, 8, 3), np.uint8), CONST_PURPOSE_OBJECT)
    assert [prompt for prompt, _ in fake_mlx.templates] == ['The part is a mounting plate.',
                                                            fake_mlx.params.Prompt_Object]


def test_gemma_fails_loudly_without_mlx_or_weights(fake_mlx, monkeypatch, tmp_path) -> None:
    """
    Description:
        Without the weights directory, or without MLX, the message says where the weights should
        be or what to install.
    """

    absent = dataclasses.replace(fake_mlx.params, Model_Path=str(tmp_path / 'absent'))
    with pytest.raises(Describer_Error_Cls, match='not at'):
        Gemma_Describer_Cls(absent).Load()

    monkeypatch.setitem(sys.modules, 'mlx_vlm', None)             # import now fails
    with pytest.raises(Describer_Error_Cls, match='mlx'):
        Gemma_Describer_Cls(fake_mlx.params).Load()


def test_an_unknown_describer_fails_before_any_work(monkeypatch) -> None:
    """
    Description:
        A describer name that is not one of the known models (or 'fallback') is refused at the
        start of Analyze with a sentence naming the choices — not after segmentation has run.
    """

    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'llava')
    with pytest.raises(Vision_Error_Cls, match='gemma or fallback'):
        Vision_Pipeline_Cls(Configuration_Str=CONST_CONFIGURATION).Analyze(np.zeros((4, 4, 3), np.uint8))
