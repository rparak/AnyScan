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
# File Name: ../test/Camera/test_core.py
## =========================================================================== ##

# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Typing (Support for type hints)
import typing as tp
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


class _Fake_Device_Cls(object):
    """A stand-in pypylon device: every Capture returns the same BGR frame."""

    def __init__(self, frame) -> None:
        self.frame = frame

    def Capture(self):
        return self.frame.copy()


class _Identity_Processor_Cls(object):
    """A stand-in image pipeline that passes the frame through."""

    def Apply(self, image):
        return image


def _Basler_Grabbing(calibration) -> tp.Tuple[Basler_Camera_Cls, tp.Any]:
    """A Basler backend with its device and pipeline stood in, so _Grab runs without hardware."""
    import cv2
    import numpy as np
    frame = np.zeros((120, 160, 3), np.uint8)
    cv2.rectangle(frame, (20, 20), (140, 100), (0, 0, 255), 2)
    cam = Basler_Camera_Cls()
    for name, value in (('__cam', _Fake_Device_Cls(frame)), ('__processor', _Identity_Processor_Cls()),
                        ('__calib', calibration), ('__cv2', cv2), ('__np', np)):
        setattr(cam, '_Basler_Camera_Cls' + name, value)
    return cam, frame


def test_a_camera_without_calibration_delivers_frames_without_undistortion() -> None:
    """
    Description:
        A camera whose hardware has no calibration file yet (the state calibrate.py starts from)
        does not crash on the missing K: the processed frame is delivered as it is, and there is no
        separate distorted original or undistortion record, because nothing was undistorted.
    """

    import numpy as np
    cam, frame = _Basler_Grabbing(None)
    rgb = cam._Grab()
    assert rgb.shape == frame.shape and np.array_equal(rgb[..., ::-1], frame)
    assert cam.Last_Distorted_Frame is None and cam.Last_Undistortion is None
    assert cam.Resolution == (160, 120)


def test_a_calibrated_camera_still_undistorts_and_records_how() -> None:
    """
    Description:
        With a calibration the frame is undistorted and the original kept, with the record of the
        undistortion that was applied — the path the no-calibration branch must not have disturbed.
    """

    import numpy as np
    from Parameters.Camera import Camera_Calibration_Parameters_Str
    calibration = Camera_Calibration_Parameters_Str(
        K=np.array([[200.0, 0.0, 80.0], [0.0, 200.0, 60.0], [0.0, 0.0, 1.0]]),
        Coefficients={'k1': -0.3, 'k2': 0.1, 'p1': 0.0, 'p2': 0.0, 'k3': 0.0})
    cam, frame = _Basler_Grabbing(calibration)
    rgb = cam._Grab()
    assert not np.array_equal(rgb[..., ::-1], frame)                   # the lens model was applied
    assert np.array_equal(cam.Last_Distorted_Frame[..., ::-1], frame)
    assert cam.Last_Undistortion['coefficients']['k1'] == -0.3


def test_the_cached_undistortion_is_byte_identical_to_cv2_undistort(reference_background) -> None:
    """
    Description:
        The undistortion builds its maps once per frame size and remaps each frame; the result is
        byte-identical to cv2.undistort with the shipped calibration, on a committed real frame, on
        the first grab and on the cached second one. (Float maps would differ by up to 2 grey
        levels; the fixed-point maps cv2.undistort itself uses do not.)
    """

    import cv2
    import numpy as np
    from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE
    calibration = Load_Configuration(CONST_DEFAULT_CONFIG_FILE).Camera.Calibration
    cam = Basler_Camera_Cls()
    for name, value in (('__cam', _Fake_Device_Cls(reference_background)), ('__processor', _Identity_Processor_Cls()),
                        ('__calib', calibration), ('__cv2', cv2), ('__np', np)):
        setattr(cam, '_Basler_Camera_Cls' + name, value)
    h, w = reference_background.shape[:2]
    coefficients = np.array(list(calibration.Coefficients.values()), dtype=np.float64)
    new_K, _ = cv2.getOptimalNewCameraMatrix(calibration.K, coefficients, (w, h),
                                             Camera_Core.CONST_BASLER_UNDISTORT_ALPHA, (w, h))
    expected = cv2.cvtColor(cv2.undistort(reference_background, calibration.K, coefficients, None, new_K),
                            cv2.COLOR_BGR2RGB)

    assert np.array_equal(cam._Grab(), expected)
    assert np.array_equal(cam._Grab(), expected)                        # from the cached maps
    assert cam.Last_Undistortion['new_camera_matrix'] == [[float(v) for v in row] for row in new_K]


class _Unpluggable_Camera_Cls(Camera_Backend_Cls):
    """A backend whose device can be pulled (removed) and whose grab can fail, without hardware."""

    def __init__(self) -> None:
        super().__init__()
        self.removed, self.failing, self.closed = False, False, 0

    def _Open(self) -> None:
        pass

    def _Close(self) -> None:
        self.closed += 1

    def _Device_Removed(self) -> bool:
        return self.removed

    def _Grab(self):
        if self.failing:
            raise Camera_Error_Cls('The camera did not return a frame in time.')
        return [[0]]

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        return (1, 1)


def test_a_failed_grab_on_a_removed_device_disconnects_and_a_transient_one_does_not() -> None:
    """
    Description:
        Connected follows the device, not only the buttons: a grab that fails on a device the backend
        reports removed closes the connection before the error goes on (a lost connection), while the
        same failure on a device still present leaves it connected (a transient capture error).
    """

    cam = _Unpluggable_Camera_Cls()
    cam.Connect()
    cam.failing = True
    with pytest.raises(Camera_Error_Cls):
        cam.Capture()
    assert cam.Connected and cam.closed == 0                            # transient: still connected

    cam.removed = True
    with pytest.raises(Camera_Error_Cls, match='did not return a frame'):
        cam.Capture()
    assert not cam.Connected and cam.closed == 1                        # lost: closed by the backend


def test_the_connection_check_closes_a_connection_whose_device_is_gone() -> None:
    """
    Description:
        Check_Connection, polled while connected, finds a removed device without a Scan: it closes the
        connection and says so once; with the device present, or with nothing connected, it does nothing.
    """

    cam = _Unpluggable_Camera_Cls()
    assert not cam.Check_Connection()                                   # not connected
    cam.Connect()
    assert not cam.Check_Connection() and cam.Connected                 # present
    cam.removed = True
    assert cam.Check_Connection() and not cam.Connected and cam.closed == 1
    assert not cam.Check_Connection() and cam.closed == 1               # already closed


def test_the_basler_backend_asks_pylon_whether_the_device_was_removed() -> None:
    """
    Description:
        The Basler backend's removal check is pylon's IsCameraDeviceRemoved on the open device; an SDK
        call that itself fails is not taken as a removal, and with no device open nothing is removed.
        (Not yet verified on the hardware: docs/capture-checklist.md has the cable-pull check.)
    """

    class _Device_Cls(object):
        """A pylon device stand-in: removed, present, or (None) its SDK call fails."""

        removed = False

        def IsCameraDeviceRemoved(self) -> bool:
            if self.removed is None:
                raise RuntimeError('pylon call failed')
            return self.removed

    device = _Device_Cls()
    cam = Basler_Camera_Cls()
    assert not cam._Device_Removed()                                    # nothing open
    setattr(cam, '_Basler_Camera_Cls__cam', type('_Basler', (), {'camera': device})())
    assert not cam._Device_Removed()
    device.removed = True
    assert cam._Device_Removed()
    device.removed = None
    assert not cam._Device_Removed()
