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
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the describers, the configuration layer and the pipeline
#   ../Vision/Describers
import Vision.Describers as Describers
from Vision.Describers import (Gemma_Describer_Cls, Florence_Describer_Cls, Describer_Error_Cls,
                               CONST_PURPOSE_OBJECT, CONST_PURPOSE_BACKGROUND)
#   ../Camera/Utilities/Configuration
from Camera.Utilities.Configuration import Read_Describer_Prompts, CONST_DESCRIBER_PROMPTS_FILE
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Florence_Vision_Cls, Vision_Error_Cls

"""
Description:
    The describer seam without weights: what Gemma is sent (the prompts from their data file,
    greedy decoding, thinking off, the crop as RGB), what fails loudly (no prompts, no MLX, no
    weights), Florence's purpose-to-task-token mapping, and the pipeline's describer switch. A
    stand-in mlx_vlm module records every call; nothing loads a model.
"""


class _Mlx_Vlm_Cls(object):
    """A stand-in for the mlx_vlm package: records the calls a describer makes. Its methods are
    bound to the module under mlx_vlm's own names (load, generate, apply_chat_template)."""

    def __init__(self) -> None:
        self.loaded, self.templates, self.generated = [], [], []

    def Load(self, path):
        self.loaded.append(path)
        return types.SimpleNamespace(config='model-config'), 'processor'

    def Apply_Chat_Template(self, processor, config, prompt, **kwargs):
        self.templates.append((prompt, kwargs))
        return 'formatted:' + prompt

    def Generate(self, model, processor, formatted, **kwargs):
        self.generated.append((formatted, kwargs))
        return types.SimpleNamespace(text='  A plate.  \n')


@pytest.fixture
def fake_mlx(monkeypatch, tmp_path):
    """Install the stand-in mlx_vlm and point the describer at an (empty) weights directory."""
    fake = _Mlx_Vlm_Cls()
    package = types.ModuleType('mlx_vlm')
    package.load, package.generate = fake.Load, fake.Generate
    utils = types.ModuleType('mlx_vlm.prompt_utils')
    utils.apply_chat_template = fake.Apply_Chat_Template
    monkeypatch.setitem(sys.modules, 'mlx_vlm', package)
    monkeypatch.setitem(sys.modules, 'mlx_vlm.prompt_utils', utils)
    monkeypatch.setattr(Describers, 'CONST_GEMMA_MODEL_DIR', str(tmp_path))
    return fake


def test_gemma_sends_the_data_file_prompts_greedily_with_the_crop_as_rgb(fake_mlx) -> None:
    """
    Description:
        Each purpose sends its own prompt, read from Configuration/Describer_Prompts.yaml; the
        crop goes in as an RGB image (the pipeline's BGR converted); decoding is greedy
        (temperature 0) with thinking off, so the same crop yields the same text; the answer
        comes back stripped. The weights directory is loaded once, however many describes.
    """

    prompts = Read_Describer_Prompts(CONST_DESCRIBER_PROMPTS_FILE)
    describer = Gemma_Describer_Cls()
    describer.Load()
    describer.Load()
    crop = np.zeros((8, 8, 3), np.uint8)
    crop[..., 0] = 200                                            # blue in BGR
    assert describer.Describe(crop, CONST_PURPOSE_OBJECT) == 'A plate.'
    describer.Describe(crop, CONST_PURPOSE_BACKGROUND)

    assert fake_mlx.loaded == [Describers.CONST_GEMMA_MODEL_DIR]
    assert [prompt for prompt, _ in fake_mlx.templates] == [prompts['Object'], prompts['Background']]
    assert all(kwargs == {'num_images': 1, 'enable_thinking': False} for _, kwargs in fake_mlx.templates)
    for formatted, kwargs in fake_mlx.generated:
        assert kwargs['temperature'] == 0.0 and kwargs['max_tokens'] == Describers.CONST_GEMMA_MAX_TOKENS
        image = kwargs['image'][0]
        assert image.mode == 'RGB' and image.getpixel((0, 0)) == (0, 0, 200)
    assert fake_mlx.generated[0][0] == 'formatted:' + prompts['Object']


def test_gemma_fails_loudly_without_prompts_mlx_or_weights(fake_mlx, monkeypatch, tmp_path) -> None:
    """
    Description:
        No prompt is sent that nobody wrote: a prompts file missing a purpose stops the load
        BEFORE the weights are touched. Without MLX, or without the weights directory, the
        message says what to install or where the weights should be.
    """

    incomplete = tmp_path / 'prompts.yaml'
    incomplete.write_text('Object: Describe the part.\n', encoding='utf-8')
    with pytest.raises(Describer_Error_Cls, match='prompts'):
        Gemma_Describer_Cls(prompts_file=str(incomplete)).Load()
    assert fake_mlx.loaded == []

    with pytest.raises(Describer_Error_Cls, match='not at'):
        Gemma_Describer_Cls(model_dir=str(tmp_path / 'absent')).Load()

    monkeypatch.setitem(sys.modules, 'mlx_vlm', None)             # import now fails
    with pytest.raises(Describer_Error_Cls, match='mlx'):
        Gemma_Describer_Cls().Load()


def test_prompts_reader_has_no_default_wording(tmp_path) -> None:
    """
    Description:
        The shipped file holds both prompts; a missing file, a missing key or an empty prompt
        reads as None, never as a built-in fallback prompt.
    """

    shipped = Read_Describer_Prompts(CONST_DESCRIBER_PROMPTS_FILE)
    assert set(shipped) == {'Object', 'Background'} and all(shipped.values())
    empty = tmp_path / 'empty.yaml'
    empty.write_text('Object: ""\nBackground: A surface.\n', encoding='utf-8')
    assert Read_Describer_Prompts(str(empty)) is None
    assert Read_Describer_Prompts(str(tmp_path / 'none.yaml')) is None


def test_florence_maps_each_purpose_to_its_task_token(monkeypatch) -> None:
    """
    Description:
        Florence is driven by task tokens, not prompts: the object purpose is the detailed
        caption, the background purpose the concise one — the seam keeps both out of the
        pipeline.
    """

    tasks = []
    monkeypatch.setattr(Describers, 'Describe', lambda *args, task: tasks.append(task) or 'x')
    describer = Florence_Describer_Cls()
    describer.Describe(None, CONST_PURPOSE_OBJECT)
    describer.Describe(None, CONST_PURPOSE_BACKGROUND)
    assert tasks == ['<MORE_DETAILED_CAPTION>', '<CAPTION>']


def test_each_describer_names_its_own_task() -> None:
    """
    Description:
        The Task row and each capture set's 'task' record what produced the reading: Gemma
        'part inspection', Florence 'detailed caption', the model-free fallback its own.
    """

    assert Gemma_Describer_Cls.Task_Label == 'part inspection'
    assert Florence_Describer_Cls.Task_Label == 'detailed caption'
    assert Vision_Core.CONST_FALLBACK_TASK_LABEL == 'model-free description'


def test_an_unknown_describer_fails_before_any_work(monkeypatch) -> None:
    """
    Description:
        A describer name that is not one of the known models (or 'fallback') is refused at the
        start of Analyze with a sentence naming the choices — not after segmentation has run.
    """

    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'llava')
    with pytest.raises(Vision_Error_Cls, match='gemma, florence or fallback'):
        Florence_Vision_Cls(scale=None).Analyze(np.zeros((4, 4, 3), np.uint8))
