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
# File Name: ../test/Vision/test_core.py
## =========================================================================== ##

# System (Default)
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the vision backend
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Backend_Cls, Vision_Pipeline_Cls, Vision_Error_Cls
# Custom Lib.: AnyScan — the configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Tests for the vision backend. The interface, the constants and the Qt-freeness are checked
    without the model, and Analyze and Configure run with stand-in models. The full path on the
    real FastSAM and Gemma is test/integration/test_pipeline.py's smoke test.
"""


def test_backend_interface() -> None:
    """
    Description:
        Vision_Pipeline_Cls is a Vision_Backend_Cls; the base Analyze is abstract; the presented
        name is the configuration's model set (Identity.Model_Set).
    """

    assert issubclass(Vision_Pipeline_Cls, Vision_Backend_Cls)
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    assert Vision_Pipeline_Cls(Configuration_Str=config).Name == config.Identity.Model_Set == 'JIC_AnyScan_All_v1'
    with pytest.raises(NotImplementedError):
        Vision_Backend_Cls().Analyze(None)


def test_config_paths_point_where_expected() -> None:
    """
    Description:
        The shipped configuration's model paths and its background reference resolve to their repo
        locations, so a moved file fails loudly rather than silently; Gemma is the default describer.
    """

    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    assert Vision_Core.CONST_DESCRIBER == 'gemma'
    assert config.Description.Model_Path.endswith(os.path.join('models', 'gemma-4-e4b-it-4bit'))
    assert config.Segmentation.Model_Path.endswith(os.path.join('models', 'FastSAM', 'FastSAM-x.pt'))
    assert config.Segmentation.Background_Reference.endswith(
        os.path.join('Data', 'Images', 'Background', 'Image_Background_001.png'))
    assert not hasattr(Vision_Core, 'CONST_BACKGROUND_REF')          # the configuration is the one route


def test_module_is_qt_free() -> None:
    """
    Description:
        The backend imports no Qt — the separation the migration was for. Analyze
        takes an ndarray image, never a QImage.
    """

    source = open(Vision_Core.__file__).read()
    # No Qt import anywhere (the word QImage may still appear in prose describing
    # the UI boundary; what matters is that nothing imports or constructs it).
    assert 'import PyQt' not in source and 'from PyQt' not in source
    assert 'QImage(' not in source


class _Fake_Segmenter_Cls(object):
    """A stand-in FastSAM: records Load / Release, fails to load when its weights path says so."""
    Name = 'FastSAM-x'
    # The load / release events of both stand-in models, in the order they happened.
    events = []

    def __init__(self, Segmentation_Parameters_Str) -> None:
        self.params, self.model = Segmentation_Parameters_Str, None

    @property
    def Loaded(self) -> bool:
        return self.model is not None

    @property
    def Model_Key(self):
        return (self.params.Model_Path, self.params.Device)

    def Set_Parameters(self, Segmentation_Parameters_Str) -> None:
        self.params = Segmentation_Parameters_Str

    def Load(self, stage_cb=None) -> None:
        if self.model is None:
            if 'broken' in self.params.Model_Path:
                raise Vision_Segmenter_Error('The FastSAM weights at "%s" could not be loaded.'
                                             % self.params.Model_Path)
            self.events.append(('load segmenter', self.params.Model_Path))
            self.model = object()

    def Release(self) -> None:
        if self.model is not None:
            self.events.append(('release segmenter', self.params.Model_Path))
        self.model = None

    def Segment(self, image, stage_cb=None):
        # No FastSAM masks: the objects come from the background cue alone.
        return [], []


class _Fake_Describer_Cls(object):
    """A stand-in Gemma: records Load / Release, fails to load when its weights path says so."""
    Name = 'gemma'
    events = _Fake_Segmenter_Cls.events

    def __init__(self, Description_Parameters_Str) -> None:
        self.params, self.model = Description_Parameters_Str, None

    @property
    def Loaded(self) -> bool:
        return self.model is not None

    @property
    def Model_Key(self):
        return self.params.Model_Path

    def Set_Parameters(self, Description_Parameters_Str) -> None:
        self.params = Description_Parameters_Str

    def Load(self) -> None:
        if self.model is None:
            if 'broken' in self.params.Model_Path:
                raise Vision_Describer_Error('The model weights at "%s" could not be loaded.'
                                             % self.params.Model_Path)
            self.events.append(('load describer', self.params.Model_Path))
            self.model = object()

    def Release(self) -> None:
        if self.model is not None:
            self.events.append(('release describer', self.params.Model_Path))
        self.model = None

    def Describe(self, image, purpose) -> str:
        self.purposes = getattr(self, 'purposes', []) + [purpose]
        return 'A machined part on a plain surface.'


from Vision.Segmenter import Segmenter_Error_Cls as Vision_Segmenter_Error      # noqa: E402
from Vision.Describers import Describer_Error_Cls as Vision_Describer_Error      # noqa: E402


@pytest.fixture
def fake_models(monkeypatch):
    """The pipeline wired to the stand-in models, and the shipped configuration to start from."""
    import dataclasses
    _Fake_Segmenter_Cls.events.clear()
    monkeypatch.setattr(Vision_Core, 'Fast_Sam_Cls', _Fake_Segmenter_Cls)
    monkeypatch.setattr(Vision_Core, 'Gemma_Describer_Cls', _Fake_Describer_Cls)
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'gemma')
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)

    def _Variant(name, **description):
        return dataclasses.replace(config, Name=name,
                                   Description=dataclasses.replace(config.Description, **description))

    return _Fake_Segmenter_Cls.events, config, _Variant


def test_load_models_preloads_both_so_no_analysis_pays_for_them(fake_models) -> None:
    """
    Description:
        Load_Models loads the segmenter and the describer up front; Models_Loaded then says so, and
        a second call loads nothing again.
    """

    events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    assert not vision.Models_Loaded
    vision.Load_Models()
    vision.Load_Models()
    assert vision.Models_Loaded
    assert [event for event, _path in events] == ['load segmenter', 'load describer']
    assert vision.Model_Names == ('FastSAM-x.pt', 'gemma-4-e4b-it-4bit')


def test_configure_keeps_a_model_whose_identity_is_unchanged(fake_models) -> None:
    """
    Description:
        A mode that only changes prompts, thresholds or fusion settings reuses the loaded models —
        no reload, no ~9 s — and the new parameters are in force.
    """

    import dataclasses
    events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Load_Models()
    segmenter = getattr(vision, '_Vision_Pipeline_Cls__segmenter')
    describer = getattr(vision, '_Vision_Pipeline_Cls__describer')
    events.clear()
    variant = _Variant('Config_x_Mode_B.yaml', Prompt_Object='Name the part.')
    variant = dataclasses.replace(variant, Segmentation=dataclasses.replace(variant.Segmentation, Confidence=0.25))
    vision.Configure(variant)

    assert events == []                                              # nothing released, nothing loaded
    assert vision.Models_Loaded
    # The same two models are in use, and each now runs with the new configuration's parameters.
    assert getattr(vision, '_Vision_Pipeline_Cls__segmenter') is segmenter
    assert getattr(vision, '_Vision_Pipeline_Cls__describer') is describer
    assert segmenter.params.Confidence == 0.25
    assert describer.params.Prompt_Object == 'Name the part.'


def test_the_background_is_described_once_per_configuration(fake_models, reference_background,
                                                            make_synthetic_frame) -> None:
    """
    Description:
        The one background sentence comes from the reference, which does not change between frames:
        two analyses ask the describer for it once. A new configuration can change the reference,
        the prompt, the crop margin or the limits, so after Configure it is asked again.
    """

    import cv2
    import dataclasses
    _events, config, _Variant = fake_models
    frame = cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 560, 560)]), cv2.COLOR_BGR2RGB)
    vision = Vision_Pipeline_Cls(Configuration_Str=dataclasses.replace(config, Scale=None))
    background = Vision_Core.CONST_PURPOSE_BACKGROUND

    vision.Analyze(frame)
    vision.Analyze(frame)
    describer = getattr(vision, '_Vision_Pipeline_Cls__describer')
    assert describer.purposes.count(background) == 1

    vision.Configure(dataclasses.replace(_Variant('Config_x_Mode_B.yaml', Background_Crop_Margin=0.2), Scale=None))
    vision.Analyze(frame)
    assert getattr(vision, '_Vision_Pipeline_Cls__describer') is describer       # same model, kept
    assert describer.purposes.count(background) == 2


@pytest.mark.parametrize('describer', ['gemma', 'fallback'])
def test_the_task_a_reading_carries(fake_models, monkeypatch, reference_background, make_synthetic_frame,
                                    describer) -> None:
    """
    Description:
        The Task row and each capture set's 'task' record what produced the reading, through a real
        Analyze (stand-in models, the real stages around them): a model reading carries the
        configuration's Identity.Task ('part inspection' as shipped), the model-free fallback its
        own label.
    """

    import cv2
    import dataclasses
    _events, config, _Variant = fake_models
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', describer)
    frame = cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 560, 560)]), cv2.COLOR_BGR2RGB)

    result = Vision_Pipeline_Cls(Configuration_Str=dataclasses.replace(config, Scale=None)).Analyze(frame)

    assert len(result.Objects) == 1
    expected = {'gemma': 'part inspection', 'fallback': Vision_Core.CONST_FALLBACK_TASK_LABEL}[describer]
    assert config.Identity.Task == 'part inspection'
    assert result.Task == expected


def test_configure_releases_a_changed_model_before_loading_its_replacement(fake_models) -> None:
    """
    Description:
        A changed describer is RELEASED before the new one loads, so the two are never held at once.
    """

    events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Load_Models()
    events.clear()
    vision.Configure(_Variant('Config_x_Mode_B.yaml', Model_Path='/models/other-gemma'))
    assert events == [('release describer', config.Description.Model_Path),
                      ('load describer', '/models/other-gemma')]


def test_a_failed_load_leaves_the_previous_configuration_in_force_and_reloads_it(fake_models) -> None:
    """
    Description:
        When the new models cannot load, the previous configuration is put back in force. Its
        describer was released to make room, so it is loaded again — and the message says that,
        so the operator knows why the load took twice as long.
    """

    events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Load_Models()
    events.clear()
    with pytest.raises(Vision_Error_Cls) as error:
        vision.Configure(_Variant('Config_x_Mode_Broken.yaml', Model_Path='/models/broken'))
    message = str(error.value)
    assert 'could not be loaded' in message                            # the reason first
    assert '%s is still in force and was loaded again.' % config.Identity.Display_Name in message
    assert events == [('release describer', config.Description.Model_Path),
                      ('load describer', config.Description.Model_Path)]
    assert vision.Models_Loaded and vision.Model_Names[1] == 'gemma-4-e4b-it-4bit'


def test_a_failed_load_before_any_model_was_loaded_leaves_nothing_to_reload(fake_models) -> None:
    """
    Description:
        If the previous configuration's models were never loaded (the dialog used before the first
        CONNECT), a failed load reloads nothing: the previous configuration stays in force and its
        configuration is not loaded, as the message says.
    """

    events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    with pytest.raises(Vision_Error_Cls, match='still in force, not loaded'):
        vision.Configure(_Variant('Config_x_Mode_Broken.yaml', Model_Path='/models/broken'))
    # The segmenter is the same in both configurations, so the one loaded on the way is kept —
    # it is the previous configuration's too. The describer never loaded.
    assert [event for event, _path in events] == ['load segmenter']
    assert not vision.Models_Loaded
    assert vision.Model_Names[1] == 'gemma-4-e4b-it-4bit'                 # the previous one's
