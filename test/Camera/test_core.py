## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../test/Camera/test_core.py
## =========================================================================== ##

# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — camera backends
#   ../Camera/Core
import Camera.Core as Camera_Core
from Camera.Core import Camera_Backend_Cls, File_Camera_Cls, Basler_Camera_Cls, Camera_Error_Cls

"""
Description:
    Tests for the camera layer. The File_Camera_Cls backend is exercised on the
    committed reference PNG — real data, no hardware — and Capture returns the RGB
    ndarray exchange format. The Basler backend needs the camera, so it is not run
    here (only its type/interface is checked).
"""


def test_backends_share_the_interface() -> None:
    """
    Description:
        Both concrete backends are Camera_Backend_Cls; the base refuses Capture
        while disconnected.
    """

    assert issubclass(File_Camera_Cls, Camera_Backend_Cls)
    assert issubclass(Basler_Camera_Cls, Camera_Backend_Cls)
    with pytest.raises(Camera_Error_Cls):
        Camera_Backend_Cls().Capture()


def test_file_camera_lifecycle(reference_background_path, reference_shape) -> None:
    """
    Description:
        Connect loads the saved frame; Resolution is (width, height); Capture
        returns a contiguous RGB array at the reference size; Disconnect clears it.
    """

    cam = File_Camera_Cls(reference_background_path)
    assert not cam.Connected

    cam.Connect()
    assert cam.Connected
    height, width, _ = reference_shape
    assert cam.Resolution == (width, height)

    frame = cam.Capture()
    assert frame.shape == reference_shape
    assert str(frame.dtype) == 'uint8'

    cam.Disconnect()
    assert not cam.Connected


def test_resolution_before_open_is_zero(reference_background_path) -> None:
    """
    Description:
        Before Connect, the resolution is (0, 0).
    """

    assert File_Camera_Cls(reference_background_path).Resolution == (0, 0)


def test_capture_before_connect_raises(reference_background_path) -> None:
    """
    Description:
        Capturing before Connect is refused with a Camera_Error_Cls.
    """

    with pytest.raises(Camera_Error_Cls):
        File_Camera_Cls(reference_background_path).Capture()


def test_missing_file_raises_on_connect() -> None:
    """
    Description:
        Connecting to a path with no file raises an actionable Camera_Error_Cls.
    """

    with pytest.raises(Camera_Error_Cls):
        File_Camera_Cls('/no/such/frame.png').Connect()


def test_module_is_qt_free() -> None:
    """
    Description:
        The camera layer imports no Qt — Capture hands back an ndarray, and the UI
        owns the ndarray -> QImage conversion.
    """

    source = open(Camera_Core.__file__).read()
    assert 'PyQt' not in source
    assert 'QImage' not in source


class _Sink_Camera_Cls(Camera_Backend_Cls):
    """A minimal backend for exercising the log sink."""

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        pass

    def _Grab(self):
        return None

    @property
    def Resolution(self):
        return (0, 0)


def test_log_sink_delivers_level_and_message_and_never_raises() -> None:
    """
    Description:
        The Qt-free camera emits (level, message) events through the injected sink — a
        level plus a message, not a formatted line. The emit is wrapped so a sink that
        raises can never break capture or connection: logging is not load-bearing.
        Last_Capture_Retries defaults to 0 (the first grab succeeded).
    """

    camera = _Sink_Camera_Cls()
    assert camera.Last_Capture_Retries == 0

    received = []
    camera.Set_Log_Callback(lambda level, message: received.append((level, message)))
    camera._Log('WARNING', 'frame dropped')
    assert received == [('WARNING', 'frame dropped')]

    # A raising sink is swallowed — the camera keeps working.
    def _Raising(level, message):
        raise RuntimeError('sink is broken')

    camera.Set_Log_Callback(_Raising)
    camera._Log('ERROR', 'this must not propagate')     # no exception

    # Clearing the sink is a no-op emit.
    camera.Set_Log_Callback(None)
    camera._Log('INFO', 'nothing wired')


class _Undistorting_Camera_Cls(_Sink_Camera_Cls):
    """A backend that undistorts: its grab records an original, or fails after a success."""

    def __init__(self) -> None:
        super().__init__()
        self.fail = False

    def _Grab(self):
        import numpy as np
        if self.fail:
            raise Camera_Error_Cls('no frame')
        self._last_distorted = np.zeros((2, 2, 3), np.uint8)
        self._last_undistortion = {'alpha': 1}
        return np.ones((2, 2, 3), np.uint8)


def test_distorted_original_belongs_to_one_frame_only() -> None:
    """
    Description:
        A backend that undistorts exposes the frame before undistortion and the undistortion
        that was applied; a saved-frame backend exposes neither (its frame is delivered as it
        is). A failed grab clears them, so a capture set can never pair a new frame with the
        previous frame's original.
    """

    cam = _Undistorting_Camera_Cls()
    cam.Connect()
    cam.Capture()
    assert cam.Last_Distorted_Frame is not None and cam.Last_Undistortion == {'alpha': 1}
    cam.fail = True
    with pytest.raises(Camera_Error_Cls):
        cam.Capture()
    assert cam.Last_Distorted_Frame is None and cam.Last_Undistortion is None
    assert File_Camera_Cls('/no/such/frame.png').Last_Distorted_Frame is None
