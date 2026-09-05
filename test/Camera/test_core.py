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
