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
# File Name: ../Camera/Basler.py
## =========================================================================== ##

# pypylon library for interfacing with Basler cameras
from pypylon import pylon
# Time (Time access and conversions)
import time
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — the camera configuration (single source of truth)
#   ../Camera/Core
from Camera.Core import CONST_BASLER_CONFIG


## =========================================================================== ##
# GigE transport tuning
#
# These values govern how image data travels from the camera to the host. They
# depend on the network hardware, not on the scene being captured, so they are
# module constants rather than per-capture configuration.
#
# A 1936x1216 BayerRG8 frame is ~2.2 MB. An unthrottled a2A1920-51gcPRO at
# 51 fps produces ~117 MB/s, which saturates a 1 GbE link and causes the
# "buffer was incompletely grabbed" error.
#
# On macOS pylon reaches GigE cameras through a GenTL producer, which exposes
# no stream grabber node map. MaxSocketBufferSize and the Statistic_* nodes are
# unavailable, and GevSCBWR / GevSCBWRA are read-only. CONST_THROUGHPUT_LIMIT is
# therefore the decisive setting: it is enforced inside the camera, so it
# throttles the sender instead of relying on the host to keep up.
## =========================================================================== ##

# Number of buffers allocated for grabbing. The pylon default is 10; a higher
# value protects against buffer underruns.
CONST_MAX_NUM_BUFFER = 20

# Stream packet size in bytes. Use 1400 for a standard 1500 B MTU, or 8192 when
# the adapter and switch support jumbo frames end to end.
CONST_PACKET_SIZE = 1400

# Inter-packet delay in ticks (1 tick = 8 ns). Higher values reduce the
# instantaneous data rate. Lower it until incomplete grabs reappear.
CONST_INTER_PACKET_DELAY = 5000

# Device link throughput limit in bytes/s. Measured ceiling on a USB-C Ethernet
# adapter at full resolution: 10 MB/s. Raise it once jumbo frames or a better
# adapter are in place. Set to None to leave the camera default in effect.
CONST_THROUGHPUT_LIMIT = 10_000_000

# Bandwidth reserve for packet resends, in percent of the stream bandwidth.
# Read-only under a GenTL producer, so it is skipped silently on macOS.
CONST_BANDWIDTH_RESERVE = 25

# Acquisition frame rate limit in fps. Set to None to leave the camera
# unthrottled, which is not advisable on a 1 GbE link.
CONST_FRAME_RATE = 5.0

# Print informational messages about nodes that were skipped because they are
# absent or read-only on this platform. Turn on when tuning a new setup.
CONST_VERBOSE = False


class Basler_Cls:
    """
    Description:
        Initialize and configure a Basler camera from a configuration dictionary.

        Only the image parameters are passed in through 'config'. The GigE
        transport tuning lives in the module constants at the top of this file,
        because it is a property of the network hardware rather than of the
        capture.

    Initialization of the Class:
        Args:
            (1) config [dict]: Image parameters (exposure time, gain, balance ratios).
            (2) max_retries [int]: Maximum number of connection attempts.
            (3) retry_delay [int]: Delay in seconds between attempts.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Basler_Cls(config={'Exposure_Time': 10000, 'Gain': 10})

            Features:
                # Functions of the class.
                Cls.Capture(); Cls.Is_Grabbing(); Cls.Print_Statistics()
    """

    def __init__(self, config: tp.Optional[tp.Dict[str, tp.Any]] = None, max_retries: int = 10,
                 retry_delay: int = 1) -> None:
        self.camera = None; self.tl_factory = None
        self.devices = None

        # Image configuration. CONST_BASLER_CONFIG (../Camera/Core.py) is the single
        # source of truth; a caller may override individual keys. Transport tuning
        # lives in the module constants above (a property of the network hardware,
        # not of the scene being captured).
        self.config = dict(CONST_BASLER_CONFIG)
        if config:
            self.config.update(config)

        # Attempt to connect to the camera.
        self.__Connect(max_retries, retry_delay)

        self.__Configure()

        # Setup converter for Bayer to BGR conversion.
        self.converter = pylon.ImageFormatConverter()
        self.converter.OutputPixelFormat = pylon.PixelType_BGR8packed
        self.converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        # Initialize the image as None
        self.image = None

    def __Connect(self, max_retries: int, retry_delay: int) -> None:
        """
        Description:
            A function that attempts to connect to the camera. If it fails, it retries a specified
            number of times.

        Args:
            (1) max_retries [int]: Maximum number of connection attempts.
            (2) retry_delay [int]: Delay in seconds between attempts.
        """

        attempt = 0
        while attempt < max_retries:
            try:
                # Attempt to initialize camera components
                self.tl_factory = pylon.TlFactory.GetInstance()
                self.devices = self.tl_factory.EnumerateDevices()

                if not self.devices:
                    raise Exception('[ERROR] No Basler cameras detected. Check the connection!')

                # List available devices
                for device in self.devices:
                    print(f'[INFO] Model: {device.GetModelName()}, IP: {device.GetIpAddress()}, Serial: {device.GetSerialNumber()}')

                self.camera = pylon.InstantCamera(self.tl_factory.CreateFirstDevice())

                # Attempt to open the camera connection
                self.camera.Open()
                print(f'[INFO] Connected to: {self.camera.GetDeviceInfo().GetModelName()} '
                      f'({self.camera.GetDeviceInfo().GetIpAddress()})')

                # Exit the loop if connection is successful
                break
            except Exception as e:
                print(f'[WARNING] Connection attempt {attempt + 1} failed: {e}')

                # Release the control channel before retrying. Without this a
                # half-opened camera can keep the channel locked, making every
                # subsequent attempt fail.
                if self.camera is not None:
                    try:
                        if self.camera.IsOpen():
                            self.camera.Close()
                    except Exception:
                        pass

                self.camera = None; self.tl_factory = None
                self.devices = None
                attempt += 1

                # Pause before attempting to connect again
                time.sleep(retry_delay)
        else:
            # If max_retries is reached without success, raise an error
            raise Exception(f'[ERROR] Failed to connect after {max_retries} attempts.')

    def __Set_Optional(self, node_name: str, value: tp.Any, unit: str = '') -> bool:
        """
        Description:
            Set a camera node only if the device exposes it and the node is
            writable.

            Two distinct cases have to be tolerated. Some nodes do not exist at
            all (GigE transport nodes are absent on USB3 and CoaXPress models).
            Others exist but are read-only: on macOS the GenTL producer manages
            the stream bandwidth itself and locks GevSCBWR and GevSCBWRA. Both
            cases are expected on some platforms, so neither is reported as a
            warning.

        Args:
            (1) node_name [string]: Name of the GenICam node.
            (2) value [int/float/bool/string]: Value to be written to the node.
            (3) unit [string]: Optional unit appended to the log message.

        Returns:
            (1) parameter [bool]: True if the value was written.
        """

        try:
            node = getattr(self.camera, node_name)
        except Exception:
            self.__Log(f'[INFO] Node {node_name} is not available on this device. Skipped.')
            return False

        # Check writability before attempting the write, so a read-only node
        # produces a quiet info message rather than an AccessException.
        if not self.__Is_Writable(node):
            self.__Log(f'[INFO] Node {node_name} is read-only on this platform. Skipped.')
            return False

        try:
            node.Value = value
            self.__Log(f'[INFO] {node_name} set to: {value}{unit}')
            return True
        except Exception as e:
            print(f'[WARNING] Could not set {node_name} to {value}: {e}')
            return False

    @staticmethod
    def __Is_Writable(node: tp.Any) -> bool:
        """
        Description:
            Determine whether a GenICam node accepts a write.

            pypylon versions differ in what they expose, so three access paths
            are tried in order of preference. If none of them work the node is
            assumed writable, which lets the caller's exception handler decide.

        Args:
            (1) node [IValue]: GenICam node object.

        Returns:
            (1) parameter [bool]: True if the node appears writable.
        """

        # Preferred: the method pypylon puts on the parameter object itself.
        try:
            return bool(node.IsWritable())
        except Exception:
            pass

        # Fallback: the free function from the genicam module.
        try:
            from pypylon import genicam
            return bool(genicam.IsWritable(node.GetNode()))
        except Exception:
            pass

        # Last resort: inspect the access mode directly.
        try:
            from pypylon import genicam
            return node.GetAccessMode() in (genicam.RW, genicam.WO)
        except Exception:
            pass

        return True

    def __Log(self, message: str) -> None:
        """
        Description:
            Print an informational message unless the configuration asks for
            quiet operation. Skipped-node messages are normal on some
            platforms and only clutter the output once the setup is known.

        Args:
            (1) message [string]: Message to be printed.
        """

        if CONST_VERBOSE:
            print(message)

    def __Configure(self) -> None:
        """
        Description:
            Apply the image settings from the configuration dictionary, then the
            transport settings from the module constants.
        """

        self.camera.Gain.SetValue(self.config['Gain'])
        # Disable Auto White Balance.
        self.camera.BalanceWhiteAuto.SetValue('Off')

        # Set manual white balance ratios.
        for color, value in self.config['Balance_Ratios'].items():
            self.camera.BalanceRatioSelector.SetValue(color)
            self.camera.BalanceRatio.SetValue(value)

        # Set Pixel Format.
        self.camera.PixelFormat.SetValue(self.config['Pixel_Format'])

        # Disable Auto Exposure.
        self.camera.ExposureAuto.SetValue('Off')

        # Set the exposure time in microseconds.
        self.camera.ExposureTime.SetValue(self.config['Exposure_Time'])
        print(f'[INFO] Exposure Time set to: {self.config["Exposure_Time"]} µs')

        self.__Configure_Transport()

    def __Configure_Transport(self) -> None:
        """
        Description:
            Apply the GigE transport settings from the module constants.

            Kept separate from the image configuration because these values are
            a property of the network hardware, not of the capture. Nodes that
            are absent or read-only on the current platform are skipped
            silently; see __Set_Optional.
        """

        # The parameter MaxNumBuffer can be used to control the count of buffers
        # allocated for grabbing. The default value of this parameter is 10.
        self.camera.MaxNumBuffer.Value = CONST_MAX_NUM_BUFFER
        self.__Log(f'[INFO] MaxNumBuffer set to: {CONST_MAX_NUM_BUFFER}')

        # Stream packet size. Smaller packets are more robust on USB-C Ethernet
        # adapters; larger ones require jumbo frames end to end.
        self.__Set_Optional('GevSCPSPacketSize', CONST_PACKET_SIZE, ' B')

        # Inter-packet delay. A coarse lever against incomplete grabs.
        self.__Set_Optional('GevSCPD', CONST_INTER_PACKET_DELAY, ' ticks')

        # Device link throughput limit. Enforced inside the camera, so it
        # throttles the sender rather than relying on the host keeping up.
        if CONST_THROUGHPUT_LIMIT is not None:
            if self.__Set_Optional('DeviceLinkThroughputLimitMode', 'On'):
                self.__Set_Optional('DeviceLinkThroughputLimit', CONST_THROUGHPUT_LIMIT, ' B/s')

        # Bandwidth reserve for resends. Read-only under a GenTL producer, as on
        # macOS, because the producer manages the stream bandwidth itself.
        if CONST_BANDWIDTH_RESERVE is not None:
            self.__Set_Optional('GevSCBWR', CONST_BANDWIDTH_RESERVE, ' %')
            self.__Set_Optional('GevSCBWRA', 5)

        # Limit the acquisition frame rate. Without this the camera floods the
        # link and buffers arrive incomplete.
        if CONST_FRAME_RATE is not None:
            if self.__Set_Optional('AcquisitionFrameRateEnable', True):
                self.__Set_Optional('AcquisitionFrameRate', float(CONST_FRAME_RATE), ' fps')
        else:
            self.__Set_Optional('AcquisitionFrameRateEnable', False)

        # Report what the camera will actually deliver after all limits apply.
        try:
            print(f'[INFO] Resulting frame rate: {self.camera.ResultingFrameRate.Value:.2f} fps')
        except Exception:
            pass

    def Is_Grabbing(self) -> bool:
        """
        Description:
            Function to check whether the camera is currently in the process of acquiring images.

        Returns:
            (1) parameter [bool]: True while the camera is grabbing.
        """

        return self.camera.IsGrabbing()

    def Capture(self, max_attempts: int = 3, timeout: int = 5000) -> tp.Optional[tp.List[tp.List[int]]]:
        """
        Description:
            Capture a single image and store it in the 'image' class parameter.

            The camera is started for exactly one frame and stopped afterwards.
            This avoids the continuous stream that GrabStrategy_LatestImageOnly
            produces, which is the usual cause of incompletely grabbed buffers
            when only one frame is needed.

        Args:
            (1) max_attempts [int]: Number of retries if the buffer is grabbed incompletely.
            (2) timeout [int]: Retrieval timeout in milliseconds.

        Returns:
            (1) parameter [Vector<uint8> 3xArray] / [None]: Captured BGR image, or None on failure.
        """

        for attempt in range(max_attempts):
            try:
                self.camera.StartGrabbingMax(1, pylon.GrabStrategy_OneByOne)
                result = self.camera.RetrieveResult(timeout, pylon.TimeoutHandling_ThrowException)
            except Exception as e:
                print(f'[WARNING] Attempt {attempt + 1}/{max_attempts}: retrieval failed: {e}')
                self.__Stop_Grabbing()
                time.sleep(0.2)
                continue

            if result.GrabSucceeded():
                self.image = self.converter.Convert(result).GetArray()
                print(f'[INFO] Captured image with shape: {self.image.shape} and dtype: {self.image.dtype}')
                result.Release()
                self.__Stop_Grabbing()

                return self.image

            print(f'[WARNING] Attempt {attempt + 1}/{max_attempts} failed. '
                  f'Code: {result.ErrorCode}, Description: {result.ErrorDescription}')
            result.Release()
            self.__Stop_Grabbing()
            time.sleep(0.2)

        print(f'[ERROR] Failed to capture a complete image after {max_attempts} attempts.')
        #self.Print_Statistics()

        return None

    def Print_Statistics(self) -> None:
        """
        Description:
            Print stream grabber statistics. A non-zero failed packet count after
            tuning points at the hardware chain (cable, adapter, switch) rather
            than at the configuration.
        """

        try:
            p = self.camera.GetStreamGrabberParams()
        except Exception as e:
            print(f'[WARNING] Stream grabber statistics are not available: {e}')
            return

        for label, node_name in (('Failed buffers', 'Statistic_Failed_Buffer_Count'),
                                 ('Buffer underruns', 'Statistic_Buffer_Underrun_Count'),
                                 ('Resend requests', 'Statistic_Resend_Request_Count'),
                                 ('Total packets', 'Statistic_Total_Packet_Count'),
                                 ('Failed packets', 'Statistic_Failed_Packet_Count')):
            try:
                print(f'[STAT] {label}: {getattr(p, node_name).Value}')
            except Exception:
                print(f'[STAT] {label}: n/a')

    def __Stop_Grabbing(self) -> None:
        """
        Description:
            Stop the acquisition if it is currently running.
        """

        try:
            if self.camera is not None and self.camera.IsGrabbing():
                self.camera.StopGrabbing()
        except Exception as e:
            print(f'[WARNING] Could not stop grabbing: {e}')

    def __Close(self) -> None:
        """
        Description:
            Release the camera resources.
        """

        if self.camera is not None:
            self.__Stop_Grabbing()
            try:
                if self.camera.IsOpen():
                    self.camera.Close()
            except Exception as e:
                print(f'[WARNING] Could not close the camera: {e}')
            print('[INFO] Camera resources released.')

    def __del__(self) -> None:
        """
        Description:
            Ensure resources are released when the object is destroyed.
        """

        self.__Close()