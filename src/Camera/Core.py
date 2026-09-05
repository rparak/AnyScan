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
# File Name: ../Camera/Core.py
## =========================================================================== ##

# System (Default)
import os
import sys
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The camera layer: connect, capture, disconnect, behind one interface so the
    real Basler and the developer-only saved-frame backend are interchangeable in
    one place. Capture returns a captured frame as an RGB NumPy array — the
    application's exchange format — so this module is Qt-free.

    Note:
        The Basler SDK, OpenCV and the project libraries are imported lazily inside
        _Open/_Grab, never at module level, so the console still starts on a machine
        with no pylon and this module imports with none of them present.
"""
# Absolute path to the project's src/ directory (this file lives in src/Camera/),
# holding Basler.Core, Utilities.Image_Processing and Calibration.Parameters.
CONST_BASLER_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Settings passed straight to Basler.Core.Camera_Cls. The keys are capitalized to
# match Camera_Cls.__Configure exactly; lower-case keys are read by nothing and
# then raise KeyError when the device is configured.
CONST_BASLER_CONFIG = {
    'Exposure_Time': 10000,                                # microseconds
    'Gain': 10,
    'Balance_Ratios': {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2},
    'Pixel_Format': 'BayerRG8',
}

# Which Utilities.Image_Processing.Process_Image_Cls profile is applied to each
# raw frame. 'real' is the profile written for the physical camera.
CONST_BASLER_IMAGE_PROFILE = 'real'


class Camera_Error_Cls(RuntimeError):
    """
    Description:
        Raised for anything the operator needs to see on screen. Its message is a
        full, actionable sentence.
    """


class Camera_Backend_Cls(object):
    """
    Description:
        The camera interface: Connect, Capture, Disconnect. The base owns the
        connected flag and refuses Capture when disconnected, so a subclass never
        tracks that itself. _Grab returns an RGB NumPy array — the exchange format
        for the whole application, whatever the SDK hands you.

        _Open, _Close and _Grab are the per-device SPI a subclass implements; they
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
                Cls.Connect(); Cls.Capture(); Cls.Disconnect()
    """

    Name = 'camera'

    def __init__(self) -> None:
        # << PRIVATE >> #
        self.__connected = False

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
            Capture one frame as a contiguous RGB array. Refuses when disconnected.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The frame (RGB).
        """

        if not self.__connected:
            raise Camera_Error_Cls('Camera is not connected.')
        return self._Grab()


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
                Cls = File_Camera_Cls('Data/Camera/Image_Background_001.png')
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
        The real camera, wired to src/Basler/Core.Camera_Cls. Backed by pypylon
        through the project's Camera_Cls wrapper and the capture sequence in
        Example/Camera/scan.py and record.py. (For a hardware-free run, --frame
        swaps in a File_Camera_Cls instead.)

        Note:
            The four things this class exists to get right:
              (1) The SDK is imported inside _Open, never at module level, so the
                  console still starts on a machine with no pylon.
              (2) A pylon device is closed explicitly in _Close via the public
                  camera handle — dropping the Python reference is not
                  deterministic, and a device left open makes the next CONNECT fail
                  with 'device busy'.
              (3) Camera_Cls.Capture() returns BGR; this application exchanges RGB,
                  so the frame is converted once, at the end of _Grab.
              (4) getOptimalNewCameraMatrix depends only on the calibration and the
                  frame size, so it is computed once per size and cached.

            Camera_Cls.Capture() already uses an explicit 5000 ms retrieve timeout
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
        # A placeholder until the device is open; overwritten with the real device
        # size in _Open and again with the delivered size in _Grab.
        self.__resolution = (1920, 1200)
        self.__processor = None
        self.__calib = None
        self.__cv2 = None
        self.__np = None
        # (width, height) -> (K, distortion coeffs, optimal new camera matrix)
        self.__undistort_cache = {}

    @property
    def Resolution(self) -> tp.Tuple[int, int]:
        """
        Description:
            The device / last-delivered frame size as (width, height).

        Returns:
            (1) parameter [Tuple<int> 1x2]: (width, height).
        """

        return self.__resolution

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
            from Basler.Core import Camera_Cls
            import Utilities.Image_Processing as Image_Processing
            from Calibration.Parameters import Basler_Calib_Param_Str
        except ImportError as exc:
            raise Camera_Error_Cls(
                'The Basler libraries could not be loaded from "%s". Check that '
                'pypylon and OpenCV are installed and that CONST_BASLER_SRC points at '
                "the project's src directory." % CONST_BASLER_SRC
            ) from exc

        # Camera_Cls connects inside its constructor and raises if no device is
        # found, so a failure here is a connection failure.
        try:
            self.__cam = Camera_Cls(config=CONST_BASLER_CONFIG)
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
        self.__processor = Image_Processing.Process_Image_Cls(CONST_BASLER_IMAGE_PROFILE)
        self.__calib = Basler_Calib_Param_Str
        self.__undistort_cache = {}

        # Report the device's actual sensor size straight away, so the status strip
        # is right at CONNECT and not only after the first SCAN.
        try:
            self.__resolution = (int(self.__cam.camera.Width.Value),
                                 int(self.__cam.camera.Height.Value))
        except Exception:                                 # noqa: BLE001
            pass  # the delivered frame in _Grab is the authoritative size

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

    def _Grab(self) -> tp.List[tp.List[int]]:
        """
        Description:
            Capture, process and undistort one frame, returning it as RGB.

        Returns:
            (1) parameter [Matrix<uint8> HxWx3]: The captured frame (RGB).
        """

        cv2, np = self.__cv2, self.__np

        # One frame. Capture() auto-starts grabbing (LatestImageOnly) and uses a
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

        # Project image pipeline (BGR in, BGR out), then undistort with the cached
        # optimal camera matrix.
        processed = self.__processor.Apply(raw)
        undistorted = self.__Undistort(processed)

        # The pipeline works in BGR; the application exchanges RGB.
        rgb = np.ascontiguousarray(cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB))
        h, w = rgb.shape[:2]
        self.__resolution = (w, h)
        return rgb

    def __Undistort(self, image: tp.List[tp.List[int]]) -> tp.List[tp.List[int]]:
        """
        Description:
            Undistort a BGR frame, caching the per-size optimal camera matrix.

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
            new_K, _ = cv2.getOptimalNewCameraMatrix(K, coeffs, (w, h), 1, (w, h))
            cached = (K, coeffs, new_K)
            self.__undistort_cache[(w, h)] = cached
        K, coeffs, new_K = cached
        return cv2.undistort(image, K, coeffs, None, new_K)
