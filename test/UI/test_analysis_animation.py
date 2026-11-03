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
# File Name: ../test/UI/test_analysis_animation.py
## =========================================================================== ##

# System (Default)
import os
import sys
import struct
import subprocess
import importlib.util
from datetime import datetime
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# PyYAML (YAML parsing)
import yaml
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan — the camera, the configuration, the window
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Mode_Directory, CONST_DEFAULT_CONFIG_FILE
#   ../UI/Core
import UI.Core as UI_Core

"""
Description:
    Example/UI/analysis_animation.py, the README's animation: its recording runs the real window, dialog and
    workers on the stand-in runtimes (test/conftest.py fake_runtimes) and grabs on events in order, the clip it
    writes stays within 10 s, the clock is frozen, the script refuses a missing frame in a fresh interpreter, and
    the committed images/anyscan-analysis.webp is an animation within the README's limits. The clip itself is not
    compared byte for byte: it runs the real models (readme-writer references/project.md > Figures).
"""
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONST_SCRIPT = os.path.join(CONST_PROJECT_FOLDER, 'Example', 'UI', 'analysis_animation.py')
CONST_CLIP = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-analysis.webp')
CONST_HARDWARE = 'a2A1920_51gcPRO_Computar_M1228_MPW3'
CONST_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]
# The README's limits for the clip: its length, its file size and its width.
#   Unit [ms] / [byte] / [px]
CONST_MAX_LENGTH_MS = 10000
CONST_MAX_BYTES = 5 * 1024 * 1024
CONST_WIDTH = 960


@pytest.fixture(scope='module')
def qt_app() -> QApplication:
    """A single offscreen QApplication for the module."""
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope='module')
def script() -> tp.Any:
    """Example/UI/analysis_animation.py, loaded as a module."""
    spec = importlib.util.spec_from_file_location('analysis_animation', CONST_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _Webp_Frames(path: str) -> tp.Tuple[int, tp.List[int]]:
    """The animated WebP's canvas width and each frame's duration [ms], read from its VP8X and ANMF chunks."""
    with open(path, 'rb') as handle:
        data = handle.read()
    assert data[:4] == b'RIFF' and data[8:12] == b'WEBP', '%s is not a WebP file' % path
    width, durations, index = 0, [], 12
    while index < len(data):
        tag, size = data[index:index + 4], struct.unpack('<I', data[index + 4:index + 8])[0]
        payload = data[index + 8:index + 8 + size]
        if tag == b'VP8X':
            width = 1 + int.from_bytes(payload[4:7], 'little')
        elif tag == b'ANMF':
            durations.append(int.from_bytes(payload[12:15], 'little'))
        index += 8 + size + (size & 1)
    return width, durations


def _Mode_File(runtime: tp.Any) -> str:
    """A Segment Anything mode file in the test's Configuration/, its models the stand-in weights."""
    with open(CONST_DEFAULT_CONFIG_FILE, 'r', encoding='utf-8') as handle:
        data = yaml.safe_load(handle)
    data['Segmentation']['Model'], data['Segmentation']['Device'] = runtime.segmenter_path, 'mps'
    data['Description']['Model'] = runtime.describer_path
    path = os.path.join(Mode_Directory(), 'Config_%s_Mode_Seg_Anything.yaml' % CONST_HARDWARE)
    with open(path, 'w', encoding='utf-8') as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return path


def test_the_recording_grabs_each_event_in_order_and_the_clip_stays_within_10_s(
        qt_app, script, tmp_path, monkeypatch, session_logger, configuration_root, fake_runtimes,
        reference_background, make_synthetic_frame) -> None:
    """
    Description:
        On a saved frame with two objects, the recording loads the mode through the dialog, then grabs the
        connected window, SCAN pressed, the frame taken, at least one analysing badge and the result, in that
        order, and the clip it writes is CONST_WIDTH wide and at most CONST_MAX_LENGTH_MS long, its analysis
        frames sharing CONST_ANALYSIS_MS.
    """

    frame_path = str(tmp_path / 'frame.png')
    cv2.imwrite(frame_path, make_synthetic_frame(reference_background, CONST_RECTS))
    mode_file = _Mode_File(fake_runtimes)
    monkeypatch.setattr(UI_Core, 'datetime', datetime)          # restored after the test
    script.Freeze_Window_Clock(UI_Core)
    logger = session_logger(config_path=mode_file, log_dir=str(tmp_path / 'log'), install_handlers=False)
    window = UI_Core.AnyScan_Window_Cls(camera=File_Camera_Cls(frame_path), logger=logger,
                                        Configuration_Str=Load_Configuration(mode_file))
    window.resize(*script.CONST_WINDOW_SIZE)
    window.show()
    try:
        recording = script.Record_Analysis(qt_app, window, mode_file, CONST_WIDTH)
    finally:
        window.close()

    kinds = [kind for kind, _image in recording['frames']]
    assert kinds[:3] == ['idle', 'scanning', 'scanned'] and kinds[-1] == 'result', kinds
    assert set(kinds[3:-1]) == {'analysing'}, kinds
    assert all(image.width == CONST_WIDTH for _kind, image in recording['frames'])
    output = str(tmp_path / 'clip.webp')
    length = script.Write_Webp(recording['frames'], output)
    width, durations = _Webp_Frames(output)
    assert (width, sum(durations)) == (CONST_WIDTH, length)
    assert length <= CONST_MAX_LENGTH_MS
    assert sum(script.Frame_Durations(kinds)[3:-1]) <= script.CONST_ANALYSIS_MS


@pytest.mark.parametrize('analysing', [1, 7, 40])
def test_any_number_of_analysis_frames_plays_in_the_same_time(script, analysing: int) -> None:
    """
    Description:
        However many badge changes an analysis has, its frames share CONST_ANALYSIS_MS and the clip stays within
        CONST_MAX_LENGTH_MS.
    """

    kinds = ['idle', 'scanning', 'scanned'] + ['analysing'] * analysing + ['result']
    durations = script.Frame_Durations(kinds)
    assert sum(durations[3:-1]) <= script.CONST_ANALYSIS_MS
    assert sum(durations) <= CONST_MAX_LENGTH_MS


def test_the_window_clock_is_frozen(script, monkeypatch) -> None:
    """
    Description:
        After Freeze_Window_Clock, the time the window reads is CONST_CLOCK, so the clip shows no time of the run.
    """

    monkeypatch.setattr(UI_Core, 'datetime', datetime)          # restored after the test
    script.Freeze_Window_Clock(UI_Core)
    assert UI_Core.datetime.now() == script.CONST_CLOCK


def test_the_script_refuses_a_missing_frame_in_a_fresh_interpreter(tmp_path) -> None:
    """
    Description:
        Run from an unrelated working directory, the script names a frame that does not exist and exits 1,
        writing nothing.
    """

    output = str(tmp_path / 'clip.webp')
    run = subprocess.run([sys.executable, CONST_SCRIPT, '--frame', str(tmp_path / 'missing.png'), '--output', output],
                         cwd=str(tmp_path), capture_output=True, text=True, timeout=120)
    assert run.returncode == 1, run.stdout + run.stderr
    assert '[ERROR] The frame %s does not exist.' % (tmp_path / 'missing.png') in run.stdout
    assert not os.path.exists(output)


def test_the_committed_clip_is_an_animation_within_the_readmes_limits() -> None:
    """
    Description:
        images/anyscan-analysis.webp is an animated WebP, CONST_WIDTH wide, at most CONST_MAX_LENGTH_MS long and
        CONST_MAX_BYTES large, with more than the three frames before the analysis.
    """

    width, durations = _Webp_Frames(CONST_CLIP)
    assert width == CONST_WIDTH
    assert len(durations) > 3
    assert sum(durations) <= CONST_MAX_LENGTH_MS
    assert os.path.getsize(CONST_CLIP) <= CONST_MAX_BYTES
