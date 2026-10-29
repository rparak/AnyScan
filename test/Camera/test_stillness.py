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
# Author   : JIC Smart Factory
# File Name: ../test/Camera/test_stillness.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Custom Lib.: AnyScan domain — the still-scene check a scan makes
#   ../Camera/Utilities/Stillness
import Camera.Utilities.Stillness as Stillness

"""
Description:
    Tests for the still-scene check (Camera.Utilities.Stillness) on real frames of the pinned test set. The sensor
    noise between two frames of a still table is SYNTHETIC here — Gaussian noise added to each RGB channel, its sigma
    chosen so the reduced, blurred difference peaks where the rig's did (4.55 grey levels over 222 still pairs,
    2026-10-16; this sigma gives 4.5 to 5.1) — since the set holds no two consecutive frames of one still scene.
"""
# The frames the check is exercised on: three of the pinned test set's, different scenes on the table.
#   Unit [Tuple<string>]
CONST_FRAMES = ('Image_055.png', 'Image_057.png', 'Image_061.png')
# The per-channel sigma of the synthetic sensor noise (see the module description).
#   Unit [grey level]
CONST_NOISE_SIGMA = 12.0


def _Frame(project_root: str, name: str) -> np.ndarray:
    """A pinned test frame as the camera delivers it (RGB)."""
    path = os.path.join(project_root, 'Data', 'Images', 'Test', name)
    if not os.path.isfile(path):
        pytest.fail('The pinned test frame %s is missing.' % path)
    return cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)


def _Noisy(frame: np.ndarray, seed: int) -> np.ndarray:
    """The frame with synthetic sensor noise (CONST_NOISE_SIGMA), as one exposure of a still scene."""
    noise = np.random.default_rng(seed).normal(0.0, CONST_NOISE_SIGMA, frame.shape)
    return np.clip(frame + noise, 0, 255).astype(np.uint8)


def _Shifted(frame: np.ndarray, dx: float) -> np.ndarray:
    """The frame moved dx pixels to the right, as if the whole scene slid."""
    return cv2.warpAffine(frame, np.float32([[1, 0, dx], [0, 1, 0]]), (frame.shape[1], frame.shape[0]),
                          borderMode=cv2.BORDER_REPLICATE)


@pytest.mark.parametrize('name', CONST_FRAMES)
def test_two_exposures_of_a_still_scene_read_still(project_root, name: str) -> None:
    """
    Description:
        Two exposures of one still scene, differing only by sensor noise at the rig's measured level, read still:
        no pixel of the reduced difference reaches the level, so a still table never refuses a scan.
    """

    frame = _Frame(project_root, name)
    for seed in range(3):
        first, second = _Noisy(frame, 2 * seed), _Noisy(frame, 2 * seed + 1)
        assert Stillness.Moving_Pixels(first, second) == 0
        assert Stillness.Is_Still(first, second)


@pytest.mark.parametrize('name', CONST_FRAMES)
def test_a_scene_that_slid_two_pixels_reads_moving(project_root, name: str) -> None:
    """
    Description:
        The same scene slid 2 px (0.2 mm on the table) between two noisy exposures reads moving: a part that
        moves that much between frames is still moving when the scan would take its frame.
    """

    frame = _Frame(project_root, name)
    assert not Stillness.Is_Still(_Noisy(frame, 0), _Noisy(_Shifted(frame, 2.0), 1))


def test_a_hand_over_the_table_reads_moving(project_root) -> None:
    """
    Description:
        A hand reaching into the view — a dark patch the size of a palm (80 x 80 mm) that is in one frame and not
        the next — reads moving.
    """

    frame = _Frame(project_root, CONST_FRAMES[0])
    hand = frame.copy()
    cv2.rectangle(hand, (900, 500), (1684, 1284), (60, 45, 40), thickness=-1)
    assert Stillness.Moving_Pixels(_Noisy(frame, 0), _Noisy(hand, 1)) > 1000
    assert not Stillness.Is_Still(_Noisy(frame, 0), _Noisy(hand, 1))


def test_a_speck_smaller_than_the_area_reads_still_and_a_larger_change_moving(project_root) -> None:
    """
    Description:
        The area threshold is what separates a stray speck from movement: a change of 2 x 2 reduced pixels reads
        still, a change of 8 x 8 reduced pixels moving. Both changes are far above the level.
    """

    frame = _Frame(project_root, CONST_FRAMES[1])
    scale = Stillness.CONST_STILL_SCALE

    def _Patched(cells: int) -> np.ndarray:
        patched = frame.copy()
        patched[400:400 + cells * scale, 600:600 + cells * scale] = 255 - patched[400:400 + cells * scale,
                                                                                 600:600 + cells * scale]
        return patched

    assert Stillness.Is_Still(frame, _Patched(2))
    assert not Stillness.Is_Still(frame, _Patched(8))


def test_frames_of_different_sizes_are_refused() -> None:
    """
    Description:
        Two frames of different sizes are not compared (a window change mid-scan would be a camera fault): the
        check raises instead of reading anything.
    """

    with pytest.raises(ValueError, match='differ in size'):
        Stillness.Is_Still(np.zeros((40, 60, 3), np.uint8), np.zeros((40, 64, 3), np.uint8))


def test_module_is_qt_free() -> None:
    """
    Description:
        The check belongs to the camera layer, which imports no Qt.
    """

    with open(Stillness.__file__, encoding='utf-8') as handle:
        source = handle.read()
    assert 'PyQt' not in source and 'QImage' not in source
