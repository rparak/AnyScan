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
# Typing (Support for type hints)
import typing as tp
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
    Last_Inference_S = 0.0

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

    # The holes it draws on a catalogue part's crop, as (x, y, diameter) in mm from the crop's top-left
    # corner; none by default. A test sets them to stand in for FastSAM finding a part's holes.
    crop_holes = []

    def Segment(self, image, stage_cb=None):
        # No FastSAM masks on a frame: the objects come from the background cue alone. On a smaller image (a
        # catalogue part's upright crop) the class's crop_holes, as disc masks at the crop's scale (0.1009 mm/px,
        # the mounting plate's top face).
        self.segmented = getattr(self, 'segmented', []) + [image.shape]
        if image.shape[0] >= 1200 or not self.crop_holes:
            return [], []
        import numpy as np
        import cv2
        masks = []
        for x, y, diameter in self.crop_holes:
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.circle(mask, (int(round(x / 0.1009)), int(round(y / 0.1009))), int(round(diameter / 2 / 0.1009)), 1, -1)
            masks.append(mask.astype(bool))
        return masks, [0.9] * len(masks)


class _Fake_Describer_Cls(object):
    """A stand-in Gemma: records Load / Release, fails to load when its weights path says so."""
    Name = 'gemma'
    events = _Fake_Segmenter_Cls.events
    Last_Tokens = None

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

    # What Describe answers; a test sets it to exercise the background sentence's fallback.
    caption = 'A machined part on a plain surface.'

    def Describe(self, image, purpose) -> str:
        self.purposes = getattr(self, 'purposes', []) + [purpose]
        self.images = getattr(self, 'images', []) + [image]
        return self.caption


class _Fake_Identifier_Cls(object):
    """A stand-in DINOv2: records Load / Release, and embeds an image as one of two unit vectors by its size —
    a crop with a side of at least 200 px (the references, a plate-sized part) as one, anything smaller as
    the other — so a plate-sized part matches the references exactly and a small one not at all."""
    events = _Fake_Segmenter_Cls.events

    def __init__(self, model_path, device) -> None:
        self.key, self.model = (model_path, device), None

    @property
    def Loaded(self) -> bool:
        return self.model is not None

    @property
    def Model_Key(self):
        return self.key

    def Load(self, stage_cb=None) -> None:
        if self.model is None:
            if 'broken' in self.key[0]:
                raise Vision_Identifier_Error('The DINOv2 weights at "%s" could not be loaded.' % self.key[0])
            self.events.append(('load identifier', self.key[0]))
            self.model = object()

    def Embed(self, images, cv2, np):
        self.Load()
        return np.array([[1.0, 0.0] if max(image.shape[:2]) >= 200 else [0.0, 1.0] for image in images])

    def Release(self) -> None:
        if self.model is not None:
            self.events.append(('release identifier', self.key[0]))
        self.model = None


from Vision.Identifier import Identifier_Error_Cls as Vision_Identifier_Error    # noqa: E402
from Vision.Segmenter import Segmenter_Error_Cls as Vision_Segmenter_Error      # noqa: E402
from Vision.Describers import Describer_Error_Cls as Vision_Describer_Error      # noqa: E402


@pytest.fixture
def fake_models(monkeypatch):
    """The pipeline wired to the stand-in models, and the shipped configuration to start from."""
    import dataclasses
    _Fake_Segmenter_Cls.events.clear()
    _Fake_Segmenter_Cls.crop_holes = []
    monkeypatch.setattr(Vision_Core, 'Fast_Sam_Cls', _Fake_Segmenter_Cls)
    monkeypatch.setattr(Vision_Core, 'Gemma_Describer_Cls', _Fake_Describer_Cls)
    monkeypatch.setattr(Vision_Core, 'Dino_Identifier_Cls', _Fake_Identifier_Cls)
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
                                                            make_synthetic_frame, tmp_path) -> None:
    """
    Description:
        The one background sentence comes from the reference, which does not change between frames:
        two analyses ask the describer for it once. A new configuration can change the reference,
        the prompt, the crop margin or the limits, so Configure describes it again — at the load,
        from the NEW configuration's reference, and no analysis after it asks again.
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

    # Another reference, told apart by its colour: solid red, which no part of the committed (teal)
    # one is — so any crop of it, whatever the margin, is red, and any crop of the old one is not.
    other = str(tmp_path / 'other_reference.png')
    red = reference_background.copy()
    red[:] = (0, 0, 255)
    cv2.imwrite(other, red)
    variant = _Variant('Config_x_Mode_B.yaml', Background_Crop_Margin=0.2)
    variant = dataclasses.replace(variant, Scale=None, Segmentation=dataclasses.replace(
        variant.Segmentation, Background_Reference=other))
    vision.Configure(variant)
    assert getattr(vision, '_Vision_Pipeline_Cls__describer') is describer       # same model, kept
    assert describer.purposes.count(background) == 2                            # at the load
    # The new reference — not the one cached before Configure.
    assert describer.images[-1].size and (describer.images[-1] == (0, 0, 255)).all()

    vision.Configure(dataclasses.replace(_Variant('Config_x_Mode_C.yaml', Background_Crop_Margin=0.2), Scale=None))
    vision.Analyze(frame)
    vision.Analyze(frame)
    assert describer.purposes.count(background) == 3                            # none by an analysis


def test_a_configuration_load_warms_up_what_the_first_analysis_would_pay(fake_models) -> None:
    """
    Description:
        Configure, after loading, pays the first analysis's one-time costs under its own stage
        label: FastSAM's first pass (on the reference, the frame's size) and the background
        sentence (Gemma's first generation) — measured at +0.64 s and +1.08 s plus ~1 s of Gemma
        warm-up on the first analysis after a load.
    """

    import cv2
    _events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    stages = []
    vision.Configure(config, stages.append)

    assert stages == ['Loading model…', 'Warming up…']         # the stand-in segmenter reports none
    reference_shape = cv2.imread(config.Segmentation.Background_Reference).shape
    assert getattr(vision, '_Vision_Pipeline_Cls__segmenter').segmented == [reference_shape]
    assert getattr(vision, '_Vision_Pipeline_Cls__describer').purposes == [Vision_Core.CONST_PURPOSE_BACKGROUND]


def test_the_background_audit_reaches_the_first_analysis_after_a_load(fake_models, reference_background,
                                                                     make_synthetic_frame) -> None:
    """
    Description:
        The background sentence is described at the load, but its audit (a warning when the
        caption was unusable and the neutral sentence stood in) is logged with an analysis — so it
        is held and carried by the first analysis after the load, once.
    """

    import cv2
    import dataclasses
    _events, config, _Variant = fake_models
    config = dataclasses.replace(config, Scale=None)
    frame = cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 560, 560)]), cv2.COLOR_BGR2RGB)
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Load_Models()
    getattr(vision, '_Vision_Pipeline_Cls__describer').caption = ''             # unusable

    vision.Configure(config)
    first, second = vision.Analyze(frame), vision.Analyze(frame)

    assert first.Background == second.Background == Vision_Core.CONST_BACKGROUND_FALLBACK
    assert [level for level, _message in first.Audit] == ['warning']
    assert second.Audit == []


def test_a_failed_warm_up_is_not_a_failed_load(fake_models, reference_background, make_synthetic_frame,
                                              tmp_path) -> None:
    """
    Description:
        The warm-up runs once the configuration is in force, so its failure (here: an unreadable
        reference) does not fail the load; the first analysis meets the same failure and reports
        it in its own words.
    """

    import cv2
    import dataclasses
    _events, config, _Variant = fake_models
    missing = str(tmp_path / 'missing.png')
    broken = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation,
                                                                          Background_Reference=missing))
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Configure(broken)
    assert vision.Models_Loaded

    frame = cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 560, 560)]), cv2.COLOR_BGR2RGB)
    with pytest.raises(Vision_Error_Cls, match='could not be read'):
        vision.Analyze(frame)


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


def test_the_reload_after_a_failed_load_is_warmed_up_like_a_load(fake_models) -> None:
    """
    Description:
        When a failed load reloads the previous configuration, that reload is warmed up too — FastSAM
        runs on the reference and the reloaded, cold Gemma describes the background again — so the
        first analysis after a failed load is not slow on top of the failure.
    """

    _events, config, _Variant = fake_models
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Configure(config)
    segmenter = getattr(vision, '_Vision_Pipeline_Cls__segmenter')
    describer = getattr(vision, '_Vision_Pipeline_Cls__describer')
    stages = []
    with pytest.raises(Vision_Error_Cls, match='was loaded again'):
        vision.Configure(_Variant('Config_x_Mode_Broken.yaml', Model_Path='/models/broken'), stages.append)

    assert stages[-3:] == ['Reloading the previous configuration…', 'Loading model…', 'Warming up…']
    assert len(segmenter.segmented) == 2                                          # the load, the reload
    assert describer.purposes == [Vision_Core.CONST_PURPOSE_BACKGROUND] * 2


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


def test_the_heatmap_is_the_difference_the_mask_was_thresholded_from(fake_models, monkeypatch, reference_background,
                                                                     make_synthetic_frame) -> None:
    """
    Description:
        Analyze hands the Camera View the background difference it thresholded — that very array, not a
        recomputed one — on the fixed 0 .. 128 scale, with the threshold applied marked and named by what
        set it: Otsu on a frame with a part, the floor of 28 on an empty one (the reference itself).
    """

    import cv2
    import dataclasses
    _events, config, _Variant = fake_models
    thresholded = []
    real = Vision_Core.Foreground_Mask

    def _Recorded(gray, *args, **kwargs):
        mask, threshold, otsu = real(gray, *args, **kwargs)
        thresholded.append((gray, threshold))
        return mask, threshold, otsu

    monkeypatch.setattr(Vision_Core, 'Foreground_Mask', _Recorded)
    vision = Vision_Pipeline_Cls(Configuration_Str=dataclasses.replace(config, Scale=None))
    part = cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 560, 560)]), cv2.COLOR_BGR2RGB)
    with_part = vision.Analyze(part)
    empty = vision.Analyze(cv2.cvtColor(reference_background, cv2.COLOR_BGR2RGB))

    (part_difference, part_threshold), (_empty_difference, _empty_threshold) = thresholded
    assert with_part.Heatmap.Values is part_difference
    assert (with_part.Heatmap.Low, with_part.Heatmap.High) == (0.0, 128.0)
    assert part_threshold > 28 and with_part.Heatmap.Marks == [(part_threshold, 'Otsu %d' % part_threshold)]
    assert empty.Heatmap.Marks == [(28.0, 'floor 28')]


def test_a_catalogue_mode_checks_each_measured_object_and_segment_anything_does_not(fake_models, reference_background,
                                                                                   make_synthetic_frame) -> None:
    """
    Description:
        Through a real Analyze (stand-in models, the real stages around them): in the mounting-plate
        mode a 601 x 401 px part, measured at the plate's top face (~60.6 x 40.5 mm), carries the
        outline's length and width checks against 60 and 40 mm, both within; on the same frame Segment
        Anything measures it and checks nothing.
    """

    import cv2
    _events, config, _Variant = fake_models
    frame = cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 900, 700)]), cv2.COLOR_BGR2RGB)
    catalogue = Load_Configuration(os.path.join(os.path.dirname(CONST_DEFAULT_CONFIG_FILE),
                                                'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml'))

    (part,) = Vision_Pipeline_Cls(Configuration_Str=catalogue).Analyze(frame).Objects
    assert [(c.Name, c.Nominal_Mm, c.Tolerance_Mm, c.Within) for c in part.Dimension_Checks] == [
        ('length', 60.0, 1.5, True), ('width', 40.0, 1.5, True)]
    assert part.Dimension_Checks[0].Measured_Mm == part.Measurement.Width_Mm

    (plain,) = Vision_Pipeline_Cls(Configuration_Str=config).Analyze(frame).Objects
    assert plain.Measurement is not None and plain.Dimension_Checks == []


def _Catalogue_Mode(mode: str = 'Mounting_Plate') -> tp.Any:
    """A shipped catalogue mode, loaded."""
    return Load_Configuration(os.path.join(os.path.dirname(CONST_DEFAULT_CONFIG_FILE),
                                           'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_%s.yaml' % mode))


def test_a_catalogue_mode_loads_releases_and_keeps_its_identifier(fake_models) -> None:
    """
    Description:
        The identifier is a model like the others: a catalogue mode loads it with the segmenter and the
        describer (and Load_Timing names it); a second catalogue mode on the same weights keeps it; Segment
        Anything releases it, so it is never held where nothing uses it; and a mode whose identifier
        cannot load leaves the previous configuration in force, its identifier loaded again.
    """

    import dataclasses
    events, config, _Variant = fake_models
    pipeline = Vision_Pipeline_Cls(Configuration_Str=_Catalogue_Mode())
    pipeline.Load_Models()
    assert ('load identifier', _Catalogue_Mode().Identification.Model_Path) in events
    assert [model.Name for model in pipeline.Load_Timing.Models] == ['FastSAM-x.pt', 'dinov2-base', 'gemma-4-e4b-it-4bit']

    events.clear()
    pipeline.Configure(_Catalogue_Mode('Labyrinth'))
    assert not [event for event in events if 'identifier' in event[0]] and pipeline.Models_Loaded

    pipeline.Configure(config)
    assert [event for event in events if 'identifier' in event[0]] == [('release identifier',
                                                                       config.Identification.Model_Path or
                                                                       _Catalogue_Mode().Identification.Model_Path)]
    assert pipeline.Models_Loaded

    pipeline.Configure(_Catalogue_Mode())
    broken = _Catalogue_Mode('Labyrinth')
    broken = dataclasses.replace(broken, Identification=dataclasses.replace(broken.Identification,
                                                                             Model_Path='/x/broken-dinov2'))
    with pytest.raises(Vision_Core.Vision_Error_Cls, match='could not be loaded'):
        pipeline.Configure(broken)
    assert pipeline.Models_Loaded


def test_a_catalogue_mode_judges_every_object_by_the_rule(fake_models, reference_background,
                                                          make_synthetic_frame) -> None:
    """
    Description:
        Through a real Analyze (stand-in models, the real stages around them, the stand-in identifier
        matching by size, the stand-in segmenter drawing the plate's front holes on its crop): a part of the
        plate's size and look, its holes where the catalogue puts them, is OK, its side the reference it
        matched; a small part is a Warning and is not hole-checked; and the catalogue checks' time is carried
        beside the measurement's. The rule's every branch is pinned in test_classify and test_holes; this pins
        that Analyze applies them to every object.
    """

    import cv2
    _events, _config, _Variant = fake_models
    # The front's holes on a 60.6 x 40.4 mm crop: through-holes 15 mm from a long edge and 17.5 from each
    # short edge, a countersink around each.
    _Fake_Segmenter_Cls.crop_holes = [(15.0, 17.5, 6.0), (15.0, 43.1, 6.0), (15.0, 17.5, 12.0), (15.0, 43.1, 12.0)]
    frame_bgr = make_synthetic_frame(reference_background, [(300, 300, 900, 700), (1300, 300, 1400, 360)])
    config = _Catalogue_Mode()
    pipeline = Vision_Pipeline_Cls(Configuration_Str=config)
    result = pipeline.Analyze(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

    plate, small = result.Objects
    assert plate.Catalogue is not None and small.Catalogue is not None
    assert plate.Catalogue.Identify_Similarity == 0.75 and plate.Catalogue.Unspecified_Area_Ratio == 1.7
    assert plate.Catalogue.Side in ('front', 'back')
    assert small.Verdict == 'Warning'
    assert plate.Catalogue.Similarity == 1.0 and small.Catalogue.Similarity == 0.0
    assert plate.Verdict == 'OK' and [c.Within for c in plate.Dimension_Checks] == [True, True]
    assert [(c.Name, c.Found, c.Expected) for c in plate.Hole_Counts] == [('countersink', 2, 2), ('through-hole', 2, 2)]
    assert plate.Hole_Checks and all(c.Within for c in plate.Hole_Checks)
    assert small.Hole_Counts == [] and small.Hole_Checks == []
    # The judged part's description says which side is up — DINOv2's side, the catalogue's words; the
    # Warning's does not.
    assert plate.Sentence.endswith(' It lies with its %s up.' % plate.Catalogue.Side_Name)
    assert plate.Catalogue.Side_Name in ('machined front', 'unmachined back')
    assert 'It lies with its' not in small.Sentence
    # The badge states the worst verdict, recomposed after the verdicts: a Warning beside an OK part.
    assert (result.Verdict, result.Verdict_Level) == ('Foreign object · 1', 'warn')
    assert result.Timing.Identification_Ms is not None


def test_segment_anything_judges_nothing(fake_models, reference_background, make_synthetic_frame) -> None:
    """
    Description:
        Segment Anything has no identifier: nothing is loaded for it, no object carries catalogue
        evidence, every object keeps the default verdict, and no identification time is reported.
    """

    import cv2
    events, config, _Variant = fake_models
    pipeline = Vision_Pipeline_Cls(Configuration_Str=config)
    pipeline.Load_Models()
    result = pipeline.Analyze(cv2.cvtColor(make_synthetic_frame(reference_background, [(300, 300, 900, 700)]),
                                           cv2.COLOR_BGR2RGB))
    assert not [event for event in events if 'identifier' in event[0]]
    assert [(det.Catalogue, det.Verdict) for det in result.Objects] == [(None, 'OK')]
    assert result.Timing.Identification_Ms is None


def test_a_judged_part_without_its_holes_is_nok(fake_models, reference_background, make_synthetic_frame) -> None:
    """
    Description:
        Through a real Analyze, a part of the plate's size and look whose crop shows no holes (the stand-in
        segmenter finds none) is NOK, its holes counted missing; and FastSAM ran on its upright crop once, beside
        the frame's pass — a Warning's crop is never segmented.
    """

    import cv2
    _events, _config, _Variant = fake_models
    _Fake_Segmenter_Cls.crop_holes = []
    frame_bgr = make_synthetic_frame(reference_background, [(300, 300, 900, 700), (1300, 300, 1400, 360)])
    pipeline = Vision_Pipeline_Cls(Configuration_Str=_Catalogue_Mode())
    plate, small = pipeline.Analyze(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).Objects
    assert plate.Verdict == 'NOK' and small.Verdict == 'Warning'
    assert [(c.Name, c.Found, c.Expected) for c in plate.Hole_Counts] == [('countersink', 0, 2), ('through-hole', 0, 2)]
    segmenter = _Private_Segmenter(pipeline)
    crops = [shape for shape in segmenter.segmented if shape[0] < 1200]
    assert len(crops) == 1 and abs(crops[0][0] - 601) <= 3 and abs(crops[0][1] - 401) <= 3   # the plate, upright


def _Private_Segmenter(pipeline: Vision_Pipeline_Cls) -> tp.Any:
    """The pipeline's (stand-in) segmenter."""
    return getattr(pipeline, '_Vision_Pipeline_Cls__segmenter')
