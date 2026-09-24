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
# Custom Lib.: AnyScan domain — vision backend and result structure
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Backend_Cls, Vision_Pipeline_Cls, Vision_Error_Cls
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
# Custom Lib.: AnyScan — the configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Tests for the vision backend. The interface, the constants and the Qt-freeness
    are checked without the model. The full Analyze path needs the FastSAM and Gemma
    weights, so it is marked `slow` and skipped by default (and skips anyway when
    the weights are not present).
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

    import Vision.Describers as Describers
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    assert Vision_Core.CONST_DESCRIBER == 'gemma'
    assert config.Description.Model_Path.endswith(os.path.join('models', 'gemma-4-e4b-it-4bit'))
    assert config.Segmentation.Model_Path.endswith(os.path.join('models', 'sam-1', 'FastSAM-x.pt'))
    assert set(Describers.CONST_DESCRIBERS) == {'gemma'}
    assert config.Segmentation.Background_Reference.endswith(
        os.path.join('Data', 'Camera', 'Image_Background_001.png'))
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


@pytest.mark.slow
def test_analyze_end_to_end(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The full pipeline on a synthetic frame (the reference with two rectangles
        drawn on it): Analyze takes an RGB array and returns a populated
        Analysis_Str. Needs the default describer's weights; skipped otherwise.
    """

    model_dir = Load_Configuration(CONST_DEFAULT_CONFIG_FILE).Description.Model_Path
    if not os.path.isdir(model_dir):
        pytest.skip(f'model weights not present at {model_dir}')

    import cv2

    rects = [(300, 300, 560, 560), (1200, 700, 1480, 980)]
    frame_bgr = make_synthetic_frame(reference_background, rects)
    image_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    result = Vision_Pipeline_Cls(Configuration_Str=Load_Configuration(CONST_DEFAULT_CONFIG_FILE)).Analyze(image_rgb)

    assert isinstance(result, Analysis_Str)
    assert len(result.Objects) == 2
    assert result.Latency_Ms >= 0


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


from Vision.Segmenter import Segmenter_Error_Cls as Vision_Segmenter_Error      # noqa: E402
from Vision.Describers import Describer_Error_Cls as Vision_Describer_Error      # noqa: E402


@pytest.fixture
def fake_models(monkeypatch):
    """The pipeline wired to the stand-in models, and the shipped configuration to start from."""
    import dataclasses
    _Fake_Segmenter_Cls.events.clear()
    monkeypatch.setattr(Vision_Core, 'Fast_Sam_Cls', _Fake_Segmenter_Cls)
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBERS', {'gemma': _Fake_Describer_Cls})
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

    events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Load_Models()
    events.clear()
    vision.Configure(_Variant('Config_x_Mode_B.yaml', Prompt_Object='Name the part.'))
    assert events == []
    assert vision.Models_Loaded


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
