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
# File Name: ../Camera/Core.py
## =========================================================================== ##

# System (Default)
import os
import sys
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the camera block of a loaded configuration
#   ../Parameters/Camera
from Parameters.Camera import Camera_Configuration_Str

"""
Description:
    Initialization of constants.

    The camera layer: connect, capture, disconnect, behind one interface so the
    real Basler and the developer-only saved-frame backend are interchangeable in
    one place. Capture returns a captured frame as an RGB NumPy array — the
    application's exchange format — so this module is Qt-free.

    Note:
        The Basler SDK, OpenCV and the project libraries are imported lazily inside
        _Open, never at module level, so the console still starts on a machine
        with no pylon and this module imports with none of them present.
"""
# Absolute path to the project's src/ directory (this file lives in src/Camera/),
# holding Camera.Basler and Camera.Utilities.Image_Processing.
CONST_BASLER_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# getOptimalNewCameraMatrix's free-scaling parameter for undistortion: 1 keeps every source
# pixel (black corners, no crop). The new camera matrix it yields defines the pixel space every
# measurement happens in, so it is recorded with each distorted frame the capture set keeps.
#   Unit [int]
CONST_BASLER_UNDISTORT_ALPHA = 1


class Camera_Error_Cls(RuntimeError):
    """
    Description:
        Raised for anything the operator needs to see on screen. Its message is a
        full, actionable sentence.
    """


class Camera_In_Use_Error_Cls(Camera_Error_Cls):
    """
    Description:
        The camera is on the network but another program holds it - the AnyScan application connected
        to it, or a camera script still running. A Camera_Error_Cls, so every caller that reports one
        reports this; a script can tell it apart to say which program to stop.
    """


class Camera_Backend_Cls(object):
    """
    Description:
        The camera interface: Connect, Capture, Disconnect. The base owns the
        connected flag and refuses Capture when disconnected, so a subclass never
        tracks that itself. The flag follows the device, not only the buttons: a grab
        that fails on a device the backend reports removed disconnects it, and so does
        Check_Connection, which the application polls while connected. _Grab returns an RGB NumPy array — the exchange format
        for the whole application, whatever the SDK hands you.

        _Open, _Close, _Grab and _Device_Removed are the per-device SPI a subclass implements; they
        keep a single leading underscore rather than the name-mangled __ private
        form precisely because they are overridden across classes.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class (a concrete subclass).
                Cls = Basler_Camera_Cls()

            Features:
                # Properties of the class.
                Cls.Connected; Cls.Resolution

                # Functions of the class.
                Cls.Connect(); Cls.Capture(); Cls.Check_Connection(); Cls.Disconnect()
    """

    Name = 'camera'

    def __init__(self) -> None:
        # << PRIVATE >> #
        self.__connected = False
        # An optional log sink the UI wires to the session logger. The Qt-free camera
        # layer must not reach up into the UI or hold the logger (the same inversion
        # Basler.py avoids by not importing Core), so it emits (level, message) events
        # through this injected callback instead — default None (nothing wired).
        self._log_cb = None
        # The last captured frame BEFORE undistortion (RGB) and the undistortion that turned it
        # into the delivered frame — None for a backend that does not undistort (a saved frame
        # is delivered as it is). Kept so a capture set can store the lens-distorted original,
        # the only form a future calibration can re-undistort.
        self._last_distorted = None
        self._last_undistortion = None
        # The camera block of the configuration in force (acquisition settings + calibration) and
        # the names of the files it came from. Set by the application before CONNECT; a camera
        # never reads a configuration file itself.
        self._camera_config = None
        self._configuration_name = ''
        self._calibration_name = ''

    def Set_Configuration(self, Camera_Configuration_Str: Camera_Configuration_Str,
                          configuration_name: str, calibration_name: str) -> None:
        """
        Description:
            Hand the camera the configuration it will connect with. Refused while connected: the
            acquisition settings and the calibration are fixed for a whole session.

        Args:
            (1) Camera_Configuration_Str [Camera_Configuration_Str(object)]: The camera block,
                with the hardware's calibration.
            (2) configuration_name [string]: The mode file's name (recorded with each frame).
            (3) calibration_name [string]: The calibration file's name (recorded with each frame).
        """

        if self.__connected:
            raise Camera_Error_Cls('The configuration cannot change while the camera is connected. '
                                   'Disconnect the camera first.')
        self._camera_config = Camera_Configuration_Str
        self._configuration_name, self._calibration_name = configuration_name, calibration_name

    def Set_Log_Callback(self, log_cb: tp.Optional[tp.Callable[[str, str], None]]) -> None:
        """
        Description:
            Wire (or clear) the log sink the camera emits events through. The callback
            takes a level ('INFO'/'WARNING'/'ERROR') and a message — never a formatted
            line, formatting is the logger's job.

        Args:
            (1) log_cb [function]: The (level, message) sink, or None to clear it.
        """

        self._log_cb = log_cb

    def _Log(self, level: str, message: str) -> None:
        """
        Description:
            Emit one event to the log sink if one is wired. Wrapped so a raising sink can
            never break capture or connection — logging must never be load-bearing.

        Args:
            (1) level [string]: The severity ('INFO' / 'WARNING' / 'ERROR').
            (2) message [string]: The event text.
        """

        if self._log_cb is None:
            return
        try:
            self._log_cb(level, message)
        except Exception:                                 # noqa: BLE001
            pass

    @property
    def Window(self) -> tp.Optional[tp.Dict[str, tp.List[int]]]:
        """
        Description:
            The sensor window the camera was set to, as it read it back on connect — recorded with
            every capture set, so what was captured at which window is a fact, not a guess. None for a
            backend that has no sensor window (a saved frame) or before it is connected.

        Returns:
            (1) parameter [Dict or None]: {'resolution': [w, h], 'offset': [x, y]}, or None.
        """

        return None

    @property
    def Last_Distorted_Frame(self) -> tp.Optional[tp.List[tp.List[int]]]:
        """
        Description:
            The most recent Capture's frame BEFORE undistortion — processed exactly as the
            delivered frame (the same blur and colour step) but with the lens distortion still
            in it — or None when this backend does not undistort.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3 or None]: The distorted frame (RGB), or None.
        """

        return self._last_distorted

    @property
    def Last_Undistortion(self) -> tp.Optional[tp.Dict[str, tp.Any]]:
        """
        Description:
            The undistortion that produced the most recent Capture's frame from
            Last_Distorted_Frame: the configuration it came from, the frame size, K, the
            distortion coefficients, getOptimalNewCameraMatrix's alpha and the new camera
            matrix it gave. None when this backend does not undistort.

        Returns:
            (1) parameter [Dict or None]: The JSON-ready undistortion record, or None.
        """

        return self._last_undistortion

    @property
    def Connected(self) -> bool:
        """
        Description:
            Whether the backend is currently connected.

        Returns:
            (1) parameter [bool]: True when connected.
        """

        return self.__connected

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        """
        Description:
            The current frame size as (width, height).

        Returns:
            (1) parameter [Tuple<int> 1x2]: (width, height).
        """

        raise NotImplementedError

    def _Open(self) -> None:
        """
        Description:
            Open the device / load the source. Implemented per backend.
        """

        raise NotImplementedError

    def _Close(self) -> None:
        """
        Description:
            Close the device / release the source. Implemented per backend.
        """

        raise NotImplementedError

    def _Grab(self) -> tp.List[tp.List[int]]:
        """
        Description:
            Grab one frame as a contiguous RGB array. Implemented per backend.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The frame (RGB).
        """

        raise NotImplementedError

    def _Device_Removed(self) -> bool:
        """
        Description:
            Whether the open device is gone (unplugged, powered off, its link down), as the device's
            SDK reports it. A backend that cannot lose its device (a saved frame) never is.

        Returns:
            (1) parameter [bool]: True when the device is reported removed.
        """

        return False

    def Check_Connection(self) -> bool:
        """
        Description:
            While connected, ask the device whether it is still there; when it is not, disconnect —
            so Connected says what the hardware is, not what the last button did.

        Returns:
            (1) parameter [bool]: True when the connection was found lost by this call (and is now
                                  closed); False when connected and present, or not connected.
        """

        if not self.__connected or not self._Device_Removed():
            return False
        self.Disconnect()
        return True

    def Connect(self) -> None:
        """
        Description:
            Connect the backend, once. A second call is a no-op.
        """

        if self.__connected:
            return
        self._Open()
        self.__connected = True

    def Disconnect(self) -> None:
        """
        Description:
            Disconnect the backend, once. A call while disconnected is a no-op.
        """

        if not self.__connected:
            return
        self._Close()
        self.__connected = False

    def Capture(self) -> tp.List[tp.List[int]]:
        """
        Description:
            Capture one frame as a contiguous RGB array. Refuses when disconnected. A grab that fails
            on a device reported removed disconnects the backend before the error goes on, so the
            caller sees a lost connection (Connected False), not a transient capture error.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The frame (RGB).
        """

        if not self.__connected:
            raise Camera_Error_Cls('Camera is not connected.')
        # A frame's distorted original never outlives it: cleared before every grab, so a
        # failed grab cannot leave the previous frame's original behind.
        self._last_distorted = None
        self._last_undistortion = None
        try:
            return self._Grab()
        except Camera_Error_Cls:
            if self._Device_Removed():
                self.Disconnect()
            raise


class File_Camera_Cls(Camera_Backend_Cls):
    """
    Description:
        A real frame from disk, standing in for the camera — developer only.

        Not a mock: it delivers an actual PNG previously saved from this camera
        (see Example/Camera/scan.py), so the whole pipeline runs on real data with
        no pylon and no hardware present, repeatably. Reached only through the
        --frame command-line argument and never surfaced in the UI.

    Initialization of the Class:
        Args:
            (1) path [string]: Path to the saved PNG frame.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = File_Camera_Cls('Data/Images/Background/Image_Background_001.png')
    """

    Name = 'Saved frame (developer)'

    def __init__(self, path: str) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__path = path
        # The loaded frame as an RGB array, or None until opened.
        self.__image = None

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        """
        Description:
            The loaded frame's (width, height), or (0, 0) before it is opened.

        Returns:
            (1) parameter [Tuple<int> 1x2]: (width, height).
        """

        if self.__image is None:
            return (0, 0)
        return (self.__image.shape[1], self.__image.shape[0])

    def _Open(self) -> None:
        """
        Description:
            Load the saved PNG into an RGB array, raising if it is missing/unreadable.
        """

        if not os.path.isfile(self.__path):
            raise Camera_Error_Cls(
                'No saved frame at "%s". Pass --frame with the path to a PNG '
                'captured from this camera.' % self.__path
            )
        # OpenCV library for computer vision tasks [pip3 install opencv-python]
        import cv2
        # Numpy (Array computing) [pip3 install numpy]
        import numpy as np
        bgr = cv2.imread(self.__path)
        if bgr is None:
            raise Camera_Error_Cls(
                'The saved frame at "%s" could not be read as an image.' % self.__path
            )
        # RGB is the application's exchange format, matching Basler_Camera_Cls._Grab.
        self.__image = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))

    def _Close(self) -> None:
        """
        Description:
            Drop the loaded frame.
        """

        self.__image = None

    def _Grab(self) -> tp.List[tp.List[int]]:
        """
        Description:
            Return a copy of the loaded frame (RGB); the source is immutable here.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The frame (RGB).
        """

        if self.__image is None:
            raise Camera_Error_Cls('The saved frame is not loaded.')
        return self.__image.copy()  # a copy; the frame is immutable here


class Basler_Camera_Cls(Camera_Backend_Cls):
    """
    Description:
        The real camera, wired to Camera.Basler.Basler_Cls. Backed by pypylon
        through the project's Basler_Cls wrapper and the capture sequence in
        Example/Camera/scan.py. (For a hardware-free run, --frame
        swaps in a File_Camera_Cls instead.)

        Note:
            The four things this class exists to get right:
              (1) The SDK is imported inside _Open, never at module level, so the
                  console still starts on a machine with no pylon.
              (2) A pylon device is closed explicitly in _Close via the public
                  camera handle — dropping the Python reference is not
                  deterministic, and a device left open makes the next CONNECT fail
                  with 'device busy'.
              (3) Basler_Cls.Capture() returns BGR; this application exchanges RGB,
                  so the frame is converted once, at the end of _Grab.
              (4) getOptimalNewCameraMatrix depends only on the calibration and the
                  frame size, so it is computed once per size and cached.

            Basler_Cls.Capture() already uses an explicit 5000 ms retrieve timeout
            that raises on hang; _Grab turns that (and any other grab failure) into
            a Camera_Error_Cls instead of freezing the GUI thread on a traceback.

    Initialization of the Class:
        Args:
            None.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Basler_Camera_Cls()
    """

    Name = 'Basler'

    def __init__(self) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__cam = None
        # The window the device reported after it was configured (_Open), then the delivered frame's
        # size (_Grab). None until connected: before that Resolution is the configuration's window,
        # never a constant that merely happens to match it today.
        self.__resolution = None
        # The window the device read back on connect ({'resolution', 'offset'}), None until then.
        self.__window = None
        self.__processor = None
        self.__calib = None
        self.__cv2 = None
        self.__np = None
        # (width, height) -> (K, distortion coeffs, optimal new camera matrix, map_1, map_2)
        self.__undistort_cache = {}

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        """
        Description:
            The frame size as (width, height): the last delivered frame's once one is grabbed, the
            window the device reported after configuration once connected, and before that the
            configuration's Camera.Resolution — (0, 0) when no configuration has been handed over.

        Returns:
            (1) parameter [Tuple<int> 1x2]: (width, height).
        """

        if self.__resolution is not None:
            return self.__resolution
        if self._camera_config is not None:
            return tuple(self._camera_config.Resolution)
        return (0, 0)

    @property
    def Window(self) -> tp.Optional[tp.Dict[str, tp.List[int]]]:
        """
        Description:
            The sensor window as the device read it back on connect, or None before connecting.

        Returns:
            (1) parameter [Dict or None]: {'resolution': [w, h], 'offset': [x, y]}, or None.
        """

        return None if self.__window is None else {key: list(value) for key, value in self.__window.items()}

    def _Open(self) -> None:
        """
        Description:
            Enumerate and open the Basler device, cache the pipeline, and read the
            sensor size. Raises Camera_Error_Cls on any failure.
        """

        # Imported here, not at module level, so a machine without the camera SDK
        # can still run the UI.
        try:
            if CONST_BASLER_SRC not in sys.path:
                sys.path.insert(0, CONST_BASLER_SRC)
            import cv2
            import numpy as np
            from Camera.Basler import Basler_Cls, Basler_Settings_Error_Cls, Basler_In_Use_Error_Cls
            import Camera.Utilities.Image_Processing as Image_Processing
        except ImportError as exc:
            raise Camera_Error_Cls(
                'The Basler libraries could not be loaded from "%s". Check that '
                'pypylon and OpenCV are installed and that CONST_BASLER_SRC points at '
                "the project's src directory." % CONST_BASLER_SRC
            ) from exc

        # The acquisition settings and the calibration come from the configuration in force,
        # handed over by the application (Set_Configuration) — never read from a file here.
        # Checking first means a missing configuration fails before the device is touched.
        Basler_Cfg_Str = self._camera_config
        if Basler_Cfg_Str is None:
            raise Camera_Error_Cls('No configuration has been loaded, so the camera settings are '
                                   'unknown. Load a configuration, then connect.')

        # Basler_Cls connects inside its constructor and raises if no device is found, so a failure
        # here is a connection failure — except a settings error: the camera was reached but refused
        # (or did not keep) the configured window, and its message says which and how. The image
        # settings come from Custom_Cfg, the sensor window from Resolution and Offset.
        try:
            self.__cam = Basler_Cls(config=Basler_Cfg_Str.Custom_Cfg, resolution=Basler_Cfg_Str.Resolution,
                                    offset=Basler_Cfg_Str.Offset)
        except Basler_Settings_Error_Cls as exc:
            self.__cam = None
            raise Camera_Error_Cls(str(exc)) from exc
        except Basler_In_Use_Error_Cls as exc:
            self.__cam = None
            raise Camera_In_Use_Error_Cls(
                'The camera %s It is held by the AnyScan application connected to it, or by a camera script still '
                'running: press DISCONNECT in AnyScan (or close the other program), then try again.' % exc) from exc
        except Exception as exc:                          # noqa: BLE001
            self.__cam = None
            raise Camera_Error_Cls(
                'No Basler camera was detected. Check that the camera is powered '
                'and the GigE link is up.'
            ) from exc

        if getattr(self.__cam, 'camera', None) is None:
            self.__cam = None
            raise Camera_Error_Cls(
                'No Basler camera was detected. Check that the camera is powered '
                'and the GigE link is up.'
            )

        # Cache what _Grab needs so it never re-imports or re-reads config.
        self.__cv2 = cv2
        self.__np = np
        self.__processor = Image_Processing.Process_Image_Cls()
        self.__calib = Basler_Cfg_Str.Calibration
        if self.__calib is None:
            self._Log('WARNING', 'No calibration for this camera: frames are not undistorted and objects '
                                 'are not measured. Run Example/Camera/calibrate.py to create it.')
        self.__undistort_cache = {}

        # What the camera reports after configuration — read back, not what was asked for — goes into
        # the session log on every connect, so a camera that ever reverts again is visible in the log
        # before the next mismatch error, and the status strip is right at CONNECT.
        applied = self.__cam.Applied_Settings
        self.__resolution = tuple(applied['resolution'])
        self.__window = {'resolution': list(applied['resolution']), 'offset': list(applied['offset'])}
        # Gamma and the colour preset are read, never set: logged with whether the station file pins them.
        pinned = ', '.join('%s %s' % (node, ('%g' % value) if isinstance(value, float) else value)
                           for node, value in applied['pinned'].items())
        unpinned = applied['unpinned']
        # The white-balance ratios the stain check depends on, with the tolerance they were checked to.
        ratios = ', '.join('%s %g' % (color, value) for color, value in applied['balance_ratios'].items())
        tolerance, source = applied['balance_tolerance']
        self._Log('INFO', 'Camera set to %d × %d at offset (%d, %d) of its %d × %d sensor, exposure %g µs, gain '
                          '%.2f, %s, %s, BalanceRatio %s (± %g, %s), %s (read back from the camera%s).'
                  % (applied['resolution'] + applied['offset'] + applied['sensor']
                     + (applied['exposure_us'], applied['gain'], applied['pixel_format'],
                        ', '.join('%s %s' % (node, value) for node, value in applied['autos'].items()), ratios,
                        tolerance, source, pinned, '; %s not pinned' % ' and '.join(unpinned) if unpinned else '')))

    def _Close(self) -> None:
        """
        Description:
            Stop grabbing and close the device explicitly through the public pylon
            handle; a close failure must never block DISCONNECT.
        """

        # Stop grabbing and close the device explicitly through the public pylon
        # handle. A close failure must never block DISCONNECT.
        cam = getattr(self.__cam, 'camera', None)
        if cam is not None:
            try:
                if cam.IsGrabbing():
                    cam.StopGrabbing()
                if cam.IsOpen():
                    cam.Close()
            except Exception:                             # noqa: BLE001
                pass
        self.__cam = None
        self.__processor = None
        self.__undistort_cache = {}
        self._last_distorted = None
        self._last_undistortion = None

    def _Device_Removed(self) -> bool:
        """
        Description:
            pylon's own verdict on the open device (InstantCamera.IsCameraDeviceRemoved): for a GigE
            camera it turns true once the heartbeat times out after the cable is pulled or the power
            lost. An SDK call that itself fails is not taken as a removal. Not yet verified on the
            hardware: docs/capture-checklist.md has the cable-pull check.

        Returns:
            (1) parameter [bool]: True when pylon reports the device removed.
        """

        cam = getattr(self.__cam, 'camera', None)
        if cam is None:
            return False
        try:
            return bool(cam.IsCameraDeviceRemoved())
        except Exception:                                 # noqa: BLE001
            return False

    def _Grab(self) -> tp.List[tp.List[int]]:
        """
        Description:
            Capture, process and undistort one frame, returning it as RGB.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The captured frame (RGB).
        """

        cv2, np = self.__cv2, self.__np

        # One frame. Capture() grabs exactly one (StartGrabbingMax, GrabStrategy_OneByOne) with a
        # 5000 ms retrieve timeout that raises on hang; translate any failure into a
        # message the operator can act on rather than freezing the window.
        try:
            raw = self.__cam.Capture()
        except Exception as exc:                          # noqa: BLE001
            raise Camera_Error_Cls(
                'The camera did not return a frame in time. Check that it is still '
                'powered and that the GigE link is up, then scan again.'
            ) from exc
        if raw is None:
            raise Camera_Error_Cls(
                'The camera returned an empty frame. Check the exposure time and '
                'the scene lighting, then scan again.'
            )

        # A safety net behind the window set on connect: a frame of another size than the
        # configuration's is refused here, before it reaches undistortion or the pipeline.
        if self._camera_config is not None:
            expected = tuple(self._camera_config.Resolution)
            delivered = (int(raw.shape[1]), int(raw.shape[0]))
            if delivered != expected:
                raise Camera_Error_Cls(
                    'The camera delivered a %d × %d frame, but the configuration sets it to %d × %d. '
                    'Disconnect and connect again so the window is set; if it recurs, power-cycle '
                    'the camera.' % (delivered + expected))

        # Project image pipeline (BGR in, BGR out), then undistort with the cached
        # optimal camera matrix.
        processed = self.__processor.Apply(raw)

        # Without a calibration there is no lens model: the processed frame is delivered as it is,
        # and there is no separate 'distorted original' to keep — the delivered frame is it.
        if self.__calib is None:
            rgb = np.ascontiguousarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))
            self.__resolution = (rgb.shape[1], rgb.shape[0])
            self._last_distorted = self._last_undistortion = None
            return rgb
        undistorted = self.__Undistort(processed)

        # The pipeline works in BGR; the application exchanges RGB. The processed frame is also
        # kept as it was BEFORE undistortion, with the undistortion that was applied to it.
        rgb = np.ascontiguousarray(cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB))
        h, w = rgb.shape[:2]
        self.__resolution = (w, h)
        K, _coeffs, new_K, _map_1, _map_2 = self.__undistort_cache[(w, h)]
        self._last_distorted = np.ascontiguousarray(cv2.cvtColor(processed, cv2.COLOR_BGR2RGB))
        self._last_undistortion = {
            'configuration': self._configuration_name,
            'calibration': self._calibration_name,
            'frame_size': [int(w), int(h)],
            'K': [[float(v) for v in row] for row in K],
            'coefficients': {key: float(value) for key, value in self.__calib.Coefficients.items()},
            'alpha': CONST_BASLER_UNDISTORT_ALPHA,
            'new_camera_matrix': [[float(v) for v in row] for row in new_K]}
        return rgb

    def __Undistort(self, image: tp.List[tp.List[int]]) -> tp.List[tp.List[int]]:
        """
        Description:
            Undistort a BGR frame. The optimal camera matrix and the undistortion maps are built
            once per frame size and cached, so each frame is one cv2.remap instead of a
            cv2.undistort that rebuilds the maps every time (22.9 -> 2.3 ms on the committed
            1920 x 1200 frames). The maps are fixed-point (CV_16SC2) — the format cv2.undistort
            itself uses — which makes the result byte-identical to it; float maps differ by up to
            2 grey levels.

        Args:
            (1) image [Matrix<uint8> HxWx3]: The frame to undistort (BGR).

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The undistorted frame (BGR).
        """

        cv2, np = self.__cv2, self.__np
        h, w = image.shape[:2]
        cached = self.__undistort_cache.get((w, h))
        if cached is None:
            K = self.__calib.K
            coeffs = np.array(list(self.__calib.Coefficients.values()),
                              dtype=np.float64)
            new_K, _ = cv2.getOptimalNewCameraMatrix(K, coeffs, (w, h),
                                                     CONST_BASLER_UNDISTORT_ALPHA, (w, h))
            map_1, map_2 = cv2.initUndistortRectifyMap(K, coeffs, None, new_K, (w, h), cv2.CV_16SC2)
            cached = (K, coeffs, new_K, map_1, map_2)
            self.__undistort_cache[(w, h)] = cached
        _K, _coeffs, _new_K, map_1, map_2 = cached
        return cv2.remap(image, map_1, map_2, cv2.INTER_LINEAR)
