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
# File Name: ../Example/Camera/preview_check.py
## =========================================================================== ##


# System (Default)
import sys
# OS (Operating system interfaces)
import os
# Argparse (Command-line parsing)
import argparse
# Time (Time access and conversions)
import time
# Typing (Support for type hints)
import typing as tp
# Resolve src/ from this file's own location (Example/Camera -> ../../src), so the script runs the
# same whether launched from Example/Camera/ or the repository root.
_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
if _SRC not in sys.path:
    sys.path.append(_SRC)
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.:
#   ../Camera/Core — the application's own camera path (stream, processing, undistortion, scan)
from Camera.Core import Basler_Camera_Cls, Camera_Error_Cls
#   ../Camera/Utilities/Stillness — the comparison a scan makes
import Camera.Utilities.Stillness as Stillness
#   ../Configuration/Core — the one configuration layer
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Initialization of constants.
"""
# The camera nodes read back before the preview, during it and after each scan: every image setting the
# station file sets or pins, the window, and the transport and frame-rate settings Camera.Basler writes.
#   Unit [Tuple<string>]
CONST_SETTING_NODES = ('ExposureTime', 'ExposureAuto', 'Gain', 'GainAuto', 'BalanceWhiteAuto', 'Gamma', 'PixelFormat',
                       'Width', 'Height', 'OffsetX', 'OffsetY', 'AcquisitionFrameRateEnable', 'AcquisitionFrameRate',
                       'DeviceLinkThroughputLimitMode', 'DeviceLinkThroughputLimit', 'GevSCPSPacketSize', 'GevSCPD')
# The white-balance channels read back (BalanceRatioSelector).
#   Unit [Tuple<string>]
CONST_BALANCE_CHANNELS = ('Red', 'Green', 'Blue')
# The difference levels whose exceeding-pixel counts are reported for the still scene.
#   Unit [Tuple<float>]
CONST_REPORTED_LEVELS = (4.0, 5.0, 6.0, 8.0, 10.0, 12.0)


def Read_Settings(camera: Basler_Camera_Cls) -> tp.Dict[str, str]:
    """
    Description:
        Read every setting in CONST_SETTING_NODES and the three white-balance ratios back from the camera.

    Args:
        (1) camera [Basler_Camera_Cls(object)]: The connected camera.

    Returns:
        (1) parameter [Dict]: Node name -> the value it read, as text ('n/a' for a node the camera lacks).
    """

    device = camera.Device.camera
    settings = {}
    for node in CONST_SETTING_NODES:
        try:
            settings[node] = str(getattr(device, node).Value)
        except Exception:                                 # noqa: BLE001
            settings[node] = 'n/a'
    for channel in CONST_BALANCE_CHANNELS:
        device.BalanceRatioSelector.SetValue(channel)
        settings['BalanceRatio ' + channel] = str(device.BalanceRatio.Value)
    return settings


def Latch_Clock(camera: Basler_Camera_Cls) -> int:
    """
    Description:
        Latch the camera's clock and read it: the instant, in the camera's own time base, that a frame's
        TimeStamp is compared with.

    Args:
        (1) camera [Basler_Camera_Cls(object)]: The connected camera.

    Returns:
        (1) parameter [int]: The latched camera time [ns].
    """

    device = camera.Device.camera
    device.TimestampLatch.Execute()
    return int(device.TimestampLatchValue.Value)


def Measure_Preview(camera: Basler_Camera_Cls, seconds: float) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Run the live preview for the given time on a still scene, as the application's worker does
        (Start_Preview, Preview_Frame), and measure the frame rate, the process's CPU load, and the
        frame-to-frame difference a scan compares (Stillness.Motion_Image) for every consecutive pair.

    Args:
        (1) camera [Basler_Camera_Cls(object)]: The connected camera.
        (2) seconds [float]: How long to stream.

    Returns:
        (1) parameter [Dict]: frames, fps, cpu (percent of one core), incomplete, peaks (the largest difference
                              of each pair), counts (per pair, the pixels above each CONST_REPORTED_LEVELS) and
                              moving (the pairs Stillness.Is_Still would call moving).
    """

    peaks, counts, incomplete, frames, moving = [], [], 0, 0, 0
    previous = None
    camera.Start_Preview()
    cpu_start, wall_start = time.process_time(), time.perf_counter()
    try:
        while time.perf_counter() - wall_start < seconds:
            frame = camera.Preview_Frame()
            if frame is None:
                incomplete += 1
                continue
            frames += 1
            if previous is not None:
                motion = Stillness.Motion_Image(previous, frame)
                peaks.append(float(motion.max()))
                counts.append([int(np.count_nonzero(motion > level)) for level in CONST_REPORTED_LEVELS])
                moving += int(np.count_nonzero(motion > Stillness.CONST_STILL_LEVEL) > Stillness.CONST_STILL_AREA_PX)
            previous = frame
    finally:
        wall = time.perf_counter() - wall_start
        cpu = time.process_time() - cpu_start
        camera.Stop_Preview()
    return {'frames': frames, 'fps': frames / wall, 'cpu': 100.0 * cpu / wall, 'incomplete': incomplete,
            'peaks': np.array(peaks), 'counts': np.array(counts), 'moving': moving}


def main() -> int:
    """
    Description:
        Check the live preview and the still-scene scan on the real camera, through the application's own
        camera path (Camera.Core.Basler_Camera_Cls):

          (1) the preview's frame rate and the CPU load it costs, and the still scene's frame-to-frame
              difference, from which Camera.Utilities.Stillness's thresholds were derived;
          (2) that a scan taken after the preview is fresh: the camera clock is latched after the preview
              stops and before the scan starts, and the scan frame's camera TimeStamp must be later;
          (3) that neither the preview nor a scan writes a camera setting: every node in
              CONST_SETTING_NODES and the white-balance ratios read back before, during and after match;
          (4) how long a scan takes on a still scene: today's single grab (Capture) against the scan
              with its stillness check (Capture_Still).

        The scene must be still for the whole run: nothing on or over the table moves.

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """

    parser = argparse.ArgumentParser(description='Check the live preview and the still-scene scan on the camera.')
    parser.add_argument('--seconds', type=float, default=60.0, help='How long to stream the still scene [s].')
    parser.add_argument('--scans', type=int, default=10, help='How many scans of each kind to time.')
    args = parser.parse_args()

    configuration = Load_Configuration(CONST_DEFAULT_CONFIG_FILE)
    camera = Basler_Camera_Cls()
    camera.Set_Configuration(configuration.Camera, configuration.Name,
                             os.path.basename(configuration.Calibration_Path) if configuration.Camera.Calibration else '')
    try:
        camera.Connect()
        before = Read_Settings(camera)

        # (1) The preview, with its settings read back while it runs.
        camera.Start_Preview()
        during = Read_Settings(camera)
        camera.Stop_Preview()
        result = Measure_Preview(camera, args.seconds)
        peaks, counts = result['peaks'], result['counts']
        print('[INFO] Preview: %d frames in %.0f s, %.2f fps, %d incomplete, CPU %.1f %% of one core.'
              % (result['frames'], args.seconds, result['fps'], result['incomplete'], result['cpu']))
        print('[INFO] Still scene, %d consecutive pairs: largest difference per pair median %.2f, 99th percentile '
              '%.2f, maximum %.2f grey levels.' % (len(peaks), np.median(peaks), np.percentile(peaks, 99), peaks.max()))
        for level, column in zip(CONST_REPORTED_LEVELS, counts.T):
            print('[INFO]   pixels above %4.1f: pairs with any %d of %d, most in one pair %d.'
                  % (level, int(np.count_nonzero(column)), len(column), int(column.max())))
        print('[INFO] In force: CONST_STILL_LEVEL %.1f, CONST_STILL_AREA_PX %d; pairs that read as moving: %d of %d.'
              % (Stillness.CONST_STILL_LEVEL, Stillness.CONST_STILL_AREA_PX, result['moving'], len(peaks)))

        # (2) and (4): scans after a preview, each latched between the preview's stop and the scan.
        fresh, still_times, single_times = [], [], []
        for _ in range(args.scans):
            camera.Start_Preview()
            camera.Preview_Frame()
            camera.Stop_Preview()
            latch = Latch_Clock(camera)
            start = time.perf_counter()
            camera.Capture_Still()
            still_times.append(time.perf_counter() - start)
            fresh.append((camera.Device.timestamp - latch) / 1e6)
        for _ in range(args.scans):
            start = time.perf_counter()
            camera.Capture()
            single_times.append(time.perf_counter() - start)
        after = Read_Settings(camera)
    except Camera_Error_Cls as error:
        print(f'[ERROR] {error}')
        return 1
    finally:
        camera.Disconnect()

    print('[INFO] Fresh: each scan frame was exposed after the latch by %.0f to %.0f ms (%s).'
          % (min(fresh), max(fresh), 'all after' if min(fresh) > 0 else 'NOT ALL AFTER'))
    print('[INFO] Scan time, median of %d: Capture %.3f s, Capture_Still %.3f s (+%.3f s); Capture_Still max %.3f s.'
          % (args.scans, np.median(single_times), np.median(still_times),
             np.median(still_times) - np.median(single_times), max(still_times)))
    changed = {node: (before[node], during[node], after[node]) for node in before
               if not before[node] == during[node] == after[node]}
    print('[INFO] Settings: %d values read back before, during and after: %s.'
          % (len(before), 'all identical' if not changed else 'CHANGED %s' % changed))
    return 0 if not changed and min(fresh) > 0 else 1

if __name__ == '__main__':
    sys.exit(main())
