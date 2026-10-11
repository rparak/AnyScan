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
# File Name: ../test/UI/test_timing_log.py
## =========================================================================== ##

# System (Default)
import os
import re
import json
import time
import dataclasses
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyYAML (YAML parser and emitter) [pip3 install pyyaml]
import yaml
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the window, the dialog module and the Log view whose sink is read
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../UI/Configuration_Dialog
import UI.Configuration_Dialog as Dialog
#   ../UI/Views/Log
from UI.Views.Log import Log_View_Cls
#   ../UI/Capture
from UI.Capture import Discover_Capture_Sets
# Custom Lib.: AnyScan domain — the camera base, the pipeline, the timing, the logger
#   ../Camera/Core
from Camera.Core import Camera_Backend_Cls
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls
#   ../Vision/Utilities/Timing
from Vision.Utilities.Timing import Build_Timing
#   ../Parameters/Vision
from Parameters.Vision import (Analysis_Str, CONST_TIMING_STAGES, CONST_STAGE_BACKGROUND, CONST_STAGE_SEGMENTATION,
                               CONST_STAGE_SEGMENTATION_POST, CONST_STAGE_FUSION, CONST_STAGE_CROPS,
                               CONST_STAGE_DESCRIPTIONS)
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
# Custom Lib.: AnyScan — the configuration layer
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Calibration_Path_For, Station_Path_For, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The analysis timing and the configuration-load timing, as the operator reads them: every
    assertion is on the text the Log view's sink received. The real pipeline, window, logger and
    Configuration dialog run; only the model runtimes are stand-ins (test/conftest.py fake_runtimes),
    with a delay knob per stage and device work that completes only when waited for.
"""
# The window's name-mangling prefix, and the shipped hardware.
#   Unit [string]
CONST_MANGLE = '_AnyScan_Window_Cls'
CONST_HARDWARE = 'a2A1920_51gcPRO_Computar_M1228_MPW3'
# The two rectangles painted onto the reference: two objects, found by the background cue.
#   Unit [Vector<Tuple<int> 1x4>]
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]
# The delay injected into one stage, and the most any OTHER stage may move when it is (half of it).
#   Unit [float] (s), [int] (ms)
CONST_DELAY_S = 0.3
CONST_DELAY_MS = int(CONST_DELAY_S * 1000)
CONST_TOLERANCE_MS = CONST_DELAY_MS // 2


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


class _Idle_Camera_Cls(Camera_Backend_Cls):
    """A camera that never needs hardware."""

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        pass

    def _Grab(self):
        return np.zeros((40, 60, 3), dtype=np.uint8)

    @property
    def Resolution(self):
        return (60, 40)


@pytest.fixture
def received(monkeypatch) -> tp.List[str]:
    """Every line the Log view's sink is handed, as handed (the view still renders it)."""
    lines = []
    original = Log_View_Cls.Sink

    def _Sink(self, record, line) -> None:
        lines.append(line)
        original(self, record, line)

    monkeypatch.setattr(Log_View_Cls, 'Sink', _Sink)
    return lines


def _Configuration(runtime):
    """The shipped configuration pointed at the stand-in weights, FastSAM on 'mps'."""
    config = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    return dataclasses.replace(
        config, Segmentation=dataclasses.replace(config.Segmentation, Model_Path=runtime.segmenter_path, Device='mps'),
        Description=dataclasses.replace(config.Description, Model_Path=runtime.describer_path))


def _Window(tmp_path, config, vision=None) -> AnyScan_Window_Cls:
    """A window with a real logger in tmp_path; `vision` replaces its backend when given."""
    logger = Session_Logger_Cls(config_path=None, log_dir=str(tmp_path / 'log'), install_handlers=False)
    window = AnyScan_Window_Cls(camera=_Idle_Camera_Cls(), logger=logger, Configuration_Str=config)
    if vision is not None:
        setattr(window, CONST_MANGLE + '__vision', vision)
    return window


def _Frame(reference_background, make_synthetic_frame) -> np.ndarray:
    """The reference with the two rectangles, as the RGB array a capture hands the pipeline."""
    return np.ascontiguousarray(make_synthetic_frame(reference_background, CONST_RECTS)[:, :, ::-1])


def _Finish(window, result: Analysis_Str, frame_rgb: np.ndarray, index: int) -> None:
    """Hand a finished analysis to the window, as the worker's signal does."""
    setattr(window, CONST_MANGLE + '__frame', frame_rgb)
    setattr(window, CONST_MANGLE + '__session_analyses', index)
    setattr(window, CONST_MANGLE + '__current_set_id', 'set%d' % index)
    setattr(window, CONST_MANGLE + '__session_id', 'session1')
    getattr(window, CONST_MANGLE + '__On_Analysis_Finished')(result)


def _Analyze(window, vision, frame_rgb: np.ndarray, received: tp.List[str], index: int) -> tp.Tuple[Analysis_Str,
                                                                                                    tp.List[str]]:
    """Run one real analysis and hand it to the window; return it and the lines it logged."""
    start = len(received)
    result = vision.Analyze(frame_rgb)
    _Finish(window, result, frame_rgb, index)
    return result, received[start:]


def _Message(line: str) -> str:
    """The message part of a logged line ('<date> <time> [LEVEL  ] message')."""
    return line.split('] ', 1)[1]


def _Timing(lines: tp.List[str]) -> tp.Dict[str, tp.Any]:
    """The one timing line among `lines`, read back into its numbers."""
    found = [_Message(line) for line in lines if re.match(r'Analysis \d+ timing( \(first after load\))?:', _Message(line))]
    assert len(found) == 1, lines
    match = re.fullmatch(r'Analysis \d+ timing( \(first after load\))?: (-?\d+) ms = (.*) \+ other (-?\d+)\. '
                         r'Measurement (\d+) ms \(not in the inference time\)\.', found[0])
    assert match, found[0]
    stages = {}
    for term in match.group(3).split(' + '):
        name, value = term.rsplit(' ', 1)
        stages[name] = int(value)
    return {'first': bool(match.group(1)), 'total': int(match.group(2)), 'stages': stages,
            'other': int(match.group(4)), 'measurement': int(match.group(5))}


def _Object_Times(lines: tp.List[str]) -> tp.List[tp.Dict[str, int]]:
    """The crop and describe times (and tokens) on each 'Object detected' line, in order."""
    times = []
    for line in lines:
        match = re.search(r'crop=(\d+) ms, describe=(\d+) ms(?:, input tokens=(\d+), output tokens=(\d+))?\.$',
                          _Message(line))
        if _Message(line).startswith('Object detected:'):
            assert match, line
            times.append({'crop': int(match.group(1)), 'describe': int(match.group(2)),
                          'tokens': (int(match.group(3)), int(match.group(4))) if match.group(3) else None})
    return times


def _Loaded_Pipeline(runtime) -> Vision_Pipeline_Cls:
    """The real pipeline on the stand-in runtimes, its configuration loaded (and warmed up)."""
    config = _Configuration(runtime)
    vision = Vision_Pipeline_Cls(Configuration_Str=config)
    vision.Configure(config)
    return vision


def _Slowed(function: tp.Callable, seconds: float) -> tp.Callable:
    """`function`, taking `seconds` longer."""
    def _Run(*args, **kwargs):
        time.sleep(seconds)
        return function(*args, **kwargs)
    return _Run


# Where each stage's delay is injected: a knob on the stand-in runtimes, or a pipeline function slowed.
#   Unit [Dict<string, Tuple>]
CONST_INJECTIONS = {CONST_STAGE_SEGMENTATION: ('knob', 'inference_s'),
                    CONST_STAGE_SEGMENTATION_POST: ('knob', 'post_s'),
                    CONST_STAGE_BACKGROUND: ('function', 'Background_Difference'),
                    CONST_STAGE_FUSION: ('function', 'Fuse_Objects'),
                    CONST_STAGE_CROPS: ('function', 'Enhance_Crop'),
                    CONST_STAGE_DESCRIPTIONS: ('knob', 'generate_s')}


@pytest.mark.parametrize('stage', list(CONST_INJECTIONS))
def test_a_delay_in_one_stage_shows_in_that_stage_only(qt_app, tmp_path, monkeypatch, received, fake_runtimes,
                                                        reference_background, make_synthetic_frame, stage) -> None:
    """
    Description:
        A delay injected into one stage shows in that stage: its logged time is at least the delay (a
        sleep inside the stage guarantees that much, whatever the machine's load). No other stage (nor
        'other') rises by more than half the delay against the same analysis without it. For the crops
        and descriptions the per-object times on the 'Object detected' lines are at least the delay too.
    """

    vision = _Loaded_Pipeline(fake_runtimes)
    window = _Window(tmp_path, _Configuration(fake_runtimes), vision)
    frame = _Frame(reference_background, make_synthetic_frame)
    _result, before = _Analyze(window, vision, frame, received, 1)

    kind, name = CONST_INJECTIONS[stage]
    if kind == 'knob':
        setattr(fake_runtimes, name, CONST_DELAY_S)
    else:
        monkeypatch.setattr(Vision_Core, name, _Slowed(getattr(Vision_Core, name), CONST_DELAY_S))
    _result, after = _Analyze(window, vision, frame, received, 2)

    base, slow = _Timing(before), _Timing(after)
    # The stage's own time, not its rise over the first analysis: the first run's real work in the stage
    # varies with load (13-17 ms under a parallel suite), so a difference could fall below the delay.
    assert slow['stages'][stage] >= CONST_DELAY_MS, (stage, slow['stages'])
    for other in CONST_TIMING_STAGES:
        if other != stage:
            assert slow['stages'][other] - base['stages'][other] < CONST_TOLERANCE_MS, other
    assert slow['other'] - base['other'] < CONST_TOLERANCE_MS
    if stage in (CONST_STAGE_CROPS, CONST_STAGE_DESCRIPTIONS):
        key = 'crop' if stage == CONST_STAGE_CROPS else 'describe'
        assert [times[key] >= CONST_DELAY_MS for times in _Object_Times(after)] == [True, True]


def test_device_work_is_charged_to_the_stage_that_queued_it(qt_app, tmp_path, received, fake_runtimes,
                                                            reference_background, make_synthetic_frame) -> None:
    """
    Description:
        FastSAM's and Gemma's calls return before their device work is done (the stand-in devices
        finish only when waited for). The segmenter's torch sync and the describer's mx.synchronize
        make each stage wait for its own work: FastSAM's lands in 'segmentation', not in the
        post-processing that reads the masks back; each object's lands in its own describe time, not
        in the next object's.
    """

    vision = _Loaded_Pipeline(fake_runtimes)
    window = _Window(tmp_path, _Configuration(fake_runtimes), vision)
    frame = _Frame(reference_background, make_synthetic_frame)
    _Analyze(window, vision, frame, received, 1)                  # nothing queued by the warm-up is left

    fake_runtimes.segment_device_s = fake_runtimes.describe_device_s = CONST_DELAY_S
    _result, lines = _Analyze(window, vision, frame, received, 2)

    timing = _Timing(lines)
    assert timing['stages'][CONST_STAGE_SEGMENTATION] >= CONST_DELAY_MS
    assert timing['stages'][CONST_STAGE_SEGMENTATION_POST] < CONST_TOLERANCE_MS
    first, second = _Object_Times(lines)
    assert first['describe'] >= CONST_DELAY_MS and second['describe'] >= CONST_DELAY_MS
    assert first['tokens'] == second['tokens'] == (408, 65)


def test_the_logged_numbers_add_up_to_the_logged_total(qt_app, tmp_path, received, fake_runtimes) -> None:
    """
    Description:
        Stage times whose rounded values do not sum to the rounded total (eight stages of 1.9 ms each
        in a 17 ms analysis) are logged so that the stage integers plus 'other' equal the total
        exactly — 'other' is derived from the logged stages, not measured on its own — and that
        total is the 'finished in' number.
    """

    window = _Window(tmp_path, _Configuration(fake_runtimes))
    timing = Build_Timing(17, {name: 0.0019 for name in CONST_TIMING_STAGES}, [], False)
    _Finish(window, Analysis_Str(Latency_Ms=17, Timing=timing, Verdict='Empty', Verdict_Level='idle'),
            np.zeros((40, 60, 3), np.uint8), 1)

    logged = _Timing(received)
    assert logged['stages'] == {name: 1 for name in CONST_TIMING_STAGES}
    assert sum(logged['stages'].values()) + logged['other'] == logged['total'] == 17
    assert any(_Message(line).startswith('Analysis 1 finished in 17 ms.') for line in received)


def test_stages_that_overlap_are_reported_not_clamped(qt_app, tmp_path, received, fake_runtimes) -> None:
    """
    Description:
        When the stages sum to more than the total (a stage counted twice), 'other' is logged
        negative, the numbers still add up, and a WARNING line says the timing does not add up.
    """

    window = _Window(tmp_path, _Configuration(fake_runtimes))
    timing = Build_Timing(15, {CONST_STAGE_BACKGROUND: 0.010, CONST_STAGE_SEGMENTATION: 0.010}, [], False)
    _Finish(window, Analysis_Str(Latency_Ms=15, Timing=timing, Verdict='Empty', Verdict_Level='idle'),
            np.zeros((40, 60, 3), np.uint8), 1)

    assert _Timing(received)['other'] == -5
    warnings = [line for line in received if '[WARNING] ' in line]
    assert [_Message(line) for line in warnings] == [
        'Analysis 1 timing does not add up: its stages sum to 20 ms, 5 ms more than the total, '
        'so a stage was counted twice.']


def _Mode_File(directory: str, mode: str, runtime) -> str:
    """A mode file for the shipped hardware whose models are the stand-in weights, and its calibration."""
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    data['Segmentation']['Model'], data['Segmentation']['Device'] = runtime.segmenter_path, 'mps'
    data['Description']['Model'] = runtime.describer_path
    path = os.path.join(directory, 'Config_%s_Mode_%s.yaml' % (CONST_HARDWARE, mode))
    with open(path, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    station = Station_Path_For(path, CONST_HARDWARE)
    if not os.path.exists(station):
        with open(Station_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r', encoding='utf-8') as f:
            station_text = f.read().replace(CONST_HARDWARE, CONST_HARDWARE)
        with open(station, 'w', encoding='utf-8') as f:
            f.write(station_text)
    calibration = Calibration_Path_For(path, CONST_HARDWARE)
    if not os.path.exists(calibration):
        with open(Calibration_Path_For(CONST_DEFAULT_CONFIG_FILE, CONST_HARDWARE), 'r', encoding='utf-8') as handle:
            content = handle.read()
        with open(calibration, 'w', encoding='utf-8') as handle:
            handle.write(content)
    return path


def _Load_Through_Dialog(window, path: str) -> None:
    """Choose a file in the window's Configuration dialog, Load it, and wait for the worker."""
    dialog = getattr(window, CONST_MANGLE + '__Make_Configuration_Dialog')()
    dialog.Select(path)
    dialog.Load()
    deadline = time.time() + 20
    while dialog.Loading and time.time() < deadline:
        QApplication.instance().processEvents()
        time.sleep(0.005)
    QApplication.instance().processEvents()
    assert not dialog.Loading


def test_a_configuration_load_logs_each_model_and_the_warm_up(qt_app, tmp_path, monkeypatch, received,
                                                             fake_runtimes) -> None:
    """
    Description:
        Loading a configuration through the dialog logs, right after its 'Models loaded' line and
        before any analysis, each model's own load time and the warm-up's parts. Loading another
        configuration with the same models logs each as kept, not reloaded — never as a 0 s load.
    """

    directory = tmp_path / 'Configuration'
    directory.mkdir()
    monkeypatch.setattr(Dialog, 'CONST_CONFIG_DIR', str(directory))
    first = _Mode_File(str(directory), 'Seg_Anything', fake_runtimes)
    second = _Mode_File(str(directory), 'Inspect', fake_runtimes)
    fake_runtimes.segmenter_load_s, fake_runtimes.describer_load_s = 0.3, 0.5
    window = _Window(tmp_path, Load_Configuration(first))

    _Load_Through_Dialog(window, first)
    messages = [_Message(line) for line in received]
    loaded = next(i for i, text in enumerate(messages) if text.startswith("Models loaded for 'Config_"))
    following = messages[loaded + 1:loaded + 4]
    expected = ['Model FastSAM-x.pt loaded in ', 'Model gemma-4-e4b-it-4bit loaded in ', 'Warm-up took ']
    assert [text[:len(start)] for start, text in zip(expected, following)] == expected, (
        'The configuration load did not log its load lines %s right after "Models loaded"; the lines '
        'that followed were %r' % (expected, following))
    segmenter, describer, warm_up = following
    assert re.fullmatch(r'Model FastSAM-x\.pt loaded in (\d+\.\d\d) s\.', segmenter)
    assert float(segmenter.split(' in ')[1][:-3]) >= 0.3
    assert re.fullmatch(r'Model gemma-4-e4b-it-4bit loaded in (\d+\.\d\d) s\.', describer)
    assert float(describer.split(' in ')[1][:-3]) >= 0.5
    assert re.fullmatch(r'Warm-up took \d+\.\d\d s: reference \d+\.\d\d s, first FastSAM pass \d+\.\d\d s, '
                        r'background sentence \d+\.\d\d s\.', warm_up)
    assert not any('finished in' in text for text in messages)

    start = len(received)
    _Load_Through_Dialog(window, second)
    messages = [_Message(line) for line in received[start:]]
    loaded = next(i for i, text in enumerate(messages) if text.startswith("Models loaded for 'Config_"))
    assert messages[loaded + 1:loaded + 3] == ['Model FastSAM-x.pt kept, not reloaded.',
                                               'Model gemma-4-e4b-it-4bit kept, not reloaded.']


def test_a_warm_up_that_stops_early_is_a_warning(qt_app, tmp_path, monkeypatch, received, fake_runtimes) -> None:
    """
    Description:
        When the warm-up fails (here FastSAM's first pass, on the reference), the configuration still
        loads, and the warm-up line becomes a WARNING that gives the parts that ran, why it stopped and
        that the first analysis pays the rest — the failure is not swallowed silently.
    """

    directory = tmp_path / 'Configuration'
    directory.mkdir()
    monkeypatch.setattr(Dialog, 'CONST_CONFIG_DIR', str(directory))
    path = _Mode_File(str(directory), 'Seg_Anything', fake_runtimes)
    fake_runtimes.segment_raises = True
    window = _Window(tmp_path, Load_Configuration(path))

    _Load_Through_Dialog(window, path)
    warm_up = [line for line in received if 'Warm-up took ' in line]
    assert len(warm_up) == 1 and '[WARNING] ' in warm_up[0], warm_up
    assert re.fullmatch(r'Warm-up took \d+\.\d\d s: reference \d+\.\d\d s; it stopped early \(The segmenter failed '
                        r'to process the frame\. Check the device setting and the scene, then scan again\), so the '
                        r'first analysis pays the rest\.', _Message(warm_up[0])), warm_up[0]
    assert getattr(window, CONST_MANGLE + '__vision').Models_Loaded


def test_the_first_analysis_after_each_load_is_marked(qt_app, tmp_path, received, fake_runtimes,
                                                     reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The timing line says '(first after load)' for exactly the first analysis to finish after a
        configuration load — including a reload of a configuration whose models are kept — and for no
        other.
    """

    config = _Configuration(fake_runtimes)
    vision = _Loaded_Pipeline(fake_runtimes)
    window = _Window(tmp_path, config, vision)
    frame = _Frame(reference_background, make_synthetic_frame)

    marks = [_Timing(_Analyze(window, vision, frame, received, 1)[1])['first'],
             _Timing(_Analyze(window, vision, frame, received, 2)[1])['first']]
    vision.Configure(dataclasses.replace(config, Name='Config_x_Mode_Other.yaml'))      # the models are kept
    assert [model.Seconds for model in vision.Load_Timing.Models] == [None, None]
    marks += [_Timing(_Analyze(window, vision, frame, received, 3)[1])['first'],
              _Timing(_Analyze(window, vision, frame, received, 4)[1])['first']]
    assert marks == [True, False, True, False]


def test_the_inference_time_readers_see_what_they_saw_before(qt_app, tmp_path, monkeypatch, received, fake_runtimes,
                                                            reference_background, make_synthetic_frame) -> None:
    """
    Description:
        Latency_Ms keeps its interval: it starts before the models are checked (a pipeline never
        preloaded pays the describer's load inside it, in 'other', and is marked first after load) and
        stops before the measurement (a slow measurement does not move it; the timing line names it as
        outside). Its readers are unchanged: the 'finished in' line has its old text (plus, since
        2026-10-07, the '#analysis-end' event marker that ends the scan's cycle), the timing total
        is the same number, and the capture set's '_objects.json' — and the History record read back
        from it — carry it as inference_ms.
    """

    config = _Configuration(fake_runtimes)
    fake_runtimes.describer_load_s = CONST_DELAY_S
    vision = Vision_Pipeline_Cls(Configuration_Str=config)                   # never preloaded
    window = _Window(tmp_path, config, vision)
    frame = _Frame(reference_background, make_synthetic_frame)

    cold, lines = _Analyze(window, vision, frame, received, 1)
    timing = _Timing(lines)
    assert cold.Latency_Ms >= CONST_DELAY_MS and timing['other'] >= CONST_DELAY_MS and timing['first']

    warm, _lines = _Analyze(window, vision, frame, received, 2)
    monkeypatch.setattr(Vision_Core, 'Measure_Objects', _Slowed(Vision_Core.Measure_Objects, CONST_DELAY_S))
    result, lines = _Analyze(window, vision, frame, received, 3)
    timing = _Timing(lines)
    assert result.Latency_Ms - warm.Latency_Ms < CONST_TOLERANCE_MS
    assert timing['measurement'] >= CONST_DELAY_MS and timing['total'] == result.Latency_Ms

    finished = [_Message(line) for line in lines if ' finished in ' in line]
    assert finished == ['Analysis 3 finished in %d ms. 2 objects detected, none scored for confidence. '
                        'Capture set set3. #analysis-end' % result.Latency_Ms]
    root = str(tmp_path / 'log' / 'captures')
    with open(os.path.join(root, 'session1', 'set3_objects.json'), 'r', encoding='utf-8') as handle:
        assert json.load(handle)['inference_ms'] == result.Latency_Ms
    assert {cap.Set_Id: cap.Inference_Ms for cap in Discover_Capture_Sets(root)}['set3'] == result.Latency_Ms


def test_a_catalogue_analysis_logs_each_verdict_and_its_identification_time(qt_app, tmp_path, received,
                                                                            reference_background,
                                                                            make_synthetic_frame) -> None:
    """
    Description:
        In a catalogue mode the window logs each object's verdict on the line after its detection, as
        Reporting writes it — a Warning and an Unspecified object at WARNING, OK and NOK at INFO, the size
        note included — and the timing line says how long identification took, outside the inference time.
        Segment Anything's timing line is unchanged (test_the_logged_numbers_add_up_to_the_logged_total).
    """

    from Configuration.Core import CONST_CONFIG_DIR
    from Parameters.Vision import Detection_Str, Catalogue_Result_Str, Timing_Str, Object_Timing_Str
    from Vision.Utilities.Dimensions import Check_Dimension
    import os
    config = Load_Configuration(os.path.join(CONST_CONFIG_DIR, 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_'
                                                               'Mounting_Plate.yaml'))
    window = _Window(tmp_path, config)

    def _Judged(verdict: str, similarity: float, distance: float) -> Detection_Str:
        return Detection_Str(Label='plate', Bbox=(10, 10, 20, 20), Verdict=verdict, Sentence='A plate.',
                             Dimension_Checks=[Check_Dimension('length', 62.0, 60.0, 1.5),
                                               Check_Dimension('width', 40.0, 40.0, 1.5)],
                             Catalogue=Catalogue_Result_Str(Similarity=similarity, Side='front', Identify_Similarity=0.75,
                                                            Area_Ratio=1.0, Unspecified_Area_Ratio=1.7,
                                                            Center_Distance_Mm=distance, Verified_Radius_Mm=74.3))

    objects = [_Judged('NOK', 0.9, 80.0), _Judged('Warning', 0.3, 10.0)]
    timing = Timing_Str(Total_Ms=100, Stages=[('segmentation', 100)], Other_Ms=0, Measurement_Ms=3,
                        Identification_Ms=41, Objects=[Object_Timing_Str(), Object_Timing_Str()])
    result = Analysis_Str(Objects=objects, Latency_Ms=100, Verdict='2 found', Verdict_Level='ok', Task='part inspection',
                          Background='A surface.', Timing=timing)
    start = len(received)
    _Finish(window, result, _Frame(reference_background, make_synthetic_frame), 1)
    lines = received[start:]

    verdicts = [line for line in lines if re.match(r'Object \d+: ', _Message(line))]
    assert [line.split('] ', 1)[0].split('[')[-1].strip() for line in verdicts] == ['INFO', 'WARNING']
    assert _Message(verdicts[0]) == ('Object 1: NOK, front up, similarity 0.90. Reason: The length is 62.00 mm, '
                                     'expected 60.00 ± 1.50 mm. Note: The size check is not verified here: 80 mm from '
                                     'the frame centre, verified to 74 mm.')
    detected = [i for i, line in enumerate(lines) if _Message(line).startswith('Object detected:')]
    assert [lines.index(line) for line in verdicts] == [i + 1 for i in detected]
    timing_line = [_Message(line) for line in lines if re.match(r'Analysis \d+ timing', _Message(line))][0]
    assert timing_line.endswith('Measurement 3 ms (not in the inference time). Identification 41 ms (not in the '
                                'inference time).')
