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
# File Name: ../Example/Camera/calibrate.py
## =========================================================================== ##

# System (Default)
import sys
#   Add access if it is not in the system path.
if '../../' + 'src' not in sys.path:
    sys.path.append('../../' + 'src')
# OS (Operating system interfaces)
import os
# Argparse (Command-line parsing)
import argparse
# Typing (Support for type hints)
import typing as tp
# Datetime (Timestamps for the capture manifest)
from datetime import datetime
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Custom Library:
#   ../Camera/Utilities/Image_Processing
import Camera.Utilities.Image_Processing
#   ../Camera/Basler
from Camera.Basler import Basler_Cls
#   ../Camera/Core — the application's processing profile, so this harness cannot drift from it
from Camera.Core import CONST_BASLER_IMAGE_PROFILE
#   ../Configuration/Core — the one configuration layer (read the camera, write the calibration)
from Configuration.Core import (Load_Configuration, Write_Calibration, Hardware_And_Mode,
                                Calibration_Path_For, CONST_DEFAULT_CONFIG_FILE, CONST_PROJECT_ROOT)
#   ../Calibration/Core
import Calibration.Core

"""
Description:
    Initialization of constants.
"""
# The new calibration file a solved calibration is written to, beside the one in force:
# 'Calibration_<Hardware>_calib-<date>.yaml'. The hardware's calibration in force
# ('Calibration_<Hardware>.yaml', shared by every mode on it) is overwritten only with
# --write-calibration. Nothing else is ever written: no mode configuration is touched.
#   Unit [string]
CONST_OUTPUT_TEMPLATE = 'Calibration_{hardware}_calib-{stamp}.yaml'
# Where --capture without a DIR writes: a NEW timestamped directory each run (one calibration set,
# one window, one directory — a set is never extended across runs by accident). Git-ignored: a set
# is 20+ frames of ~4 MB, and the calibration records the directory it was solved from.
#   Unit [string]
CONST_CAPTURE_ROOT = os.path.join(CONST_PROJECT_ROOT, 'Data', 'Images', 'Calibration')


def Capture_Main(directory: str, config_path: str) -> int:
    """
    Description:
        Capture calibration frames interactively into a directory, one per key press, until 'q'.
        Each frame is the camera's image after the application's own processing step and BEFORE
        undistortion (a lens model can only be solved from distorted frames). Every frame taken
        is kept — also one where no board is found, which is reported but never deleted — and
        recorded in the directory's capture.json, which states that the frames are distorted.

        Note:
            This is the ONE harness that does not capture through the application's camera path
            (Camera.Core.Basler_Camera_Cls), and deliberately: that path undistorts every frame with
            the calibration in force, and a lens model can only be solved from frames that have NOT
            been undistorted — least of all with the model being replaced. So it drives Basler_Cls
            directly, and matches the application on everything else: the same sensor window (set and
            read back by Basler_Cls from Camera.Resolution / Camera.Offset) and the same processing
            step (Process_Image_Cls with the application's profile, Camera.Core.CONST_BASLER_IMAGE_PROFILE).
            scan.py, which has no such reason, goes through the application's path.

    Args:
        (1) directory [string]: The directory the frames are written to (created if missing).
        (2) config_path [string]: The configuration whose camera settings the capture uses.

    Returns:
        (1) parameter [int]: The process exit code.
    """

    os.makedirs(directory, exist_ok=True)
    configuration = Load_Configuration(config_path)
    Basler_Cfg_Str = configuration.Camera
    # One calibration set, one sensor window: frames from another window would be solved together
    # into a lens model that belongs to neither, so a set started at another window is not extended.
    recorded = Calibration.Core.Captured_Window(directory)
    configured = {'resolution': list(Basler_Cfg_Str.Resolution), 'offset': list(Basler_Cfg_Str.Offset)}
    if recorded is not None and recorded != configured:
        print('[ERROR] %s was captured at %d x %d, offset (%d, %d), but the configuration sets the camera to '
              '%d x %d, offset (%d, %d). Capture into a new directory.'
              % ((directory,) + tuple(recorded['resolution']) + tuple(recorded['offset'])
                 + tuple(configured['resolution']) + tuple(configured['offset'])))
        return 1
    Basler_Cam_Id_1 = Basler_Cls(config=Basler_Cfg_Str.Custom_Cfg, resolution=Basler_Cfg_Str.Resolution,
                                 offset=Basler_Cfg_Str.Offset)
    applied = Basler_Cam_Id_1.Applied_Settings
    Process_Image_Cls = Camera.Utilities.Image_Processing.Process_Image_Cls(CONST_BASLER_IMAGE_PROFILE)
    header = {'distorted': True,
              'note': ('These frames are NOT undistorted: they are the camera\'s images after the '
                       'application\'s processing step (the same blur and colour adjustment) and '
                       'before undistortion, for solving the lens model. They are not the '
                       'application\'s <set>_raw.png, which is undistorted.'),
              'processing': "Camera.Utilities.Image_Processing.Process_Image_Cls('%s')" % CONST_BASLER_IMAGE_PROFILE,
              'configuration': configuration.Name,
              'camera': Basler_Cfg_Str.Name, 'custom_cfg': Basler_Cfg_Str.Custom_Cfg,
              # The sensor window the frames were captured at, as the camera read it back. The
              # solve records it in the calibration: K and the factor are in this window's pixels.
              'window': {'resolution': list(applied['resolution']), 'offset': list(applied['offset'])},
              'kinds': {Calibration.Core.CONST_CALIB_FLAT_PREFIX: 'board flat on the table: lens '
                        'model and mm/px factor', Calibration.Core.CONST_CALIB_VIEW_PREFIX: 'board '
                        'tilted or raised: lens model only'},
              'created': datetime.now().isoformat(timespec='seconds')}

    print('[INFO] Capturing distorted calibration frames into: %s' % directory)
    print('[INFO] Keys: f = board FLAT on the table, t = board TILTED (vary the tilt: 20-45 degrees '
          'in several directions), q = quit. Every frame is kept.')
    while True:
        key = input('[f / t / q] > ').strip().lower()
        if key == 'q':
            break
        if key not in ('f', 't'):
            continue
        image_raw = Basler_Cam_Id_1.Capture()
        if image_raw is None:
            print('[WARNING] No image captured; nothing was written. Try again.')
            continue
        image = Process_Image_Cls.Apply(image_raw)
        name = Calibration.Core.Next_Capture_Name(directory, flat=(key == 'f'))
        cv2.imwrite(os.path.join(directory, name), image)
        detection = Calibration.Core.Detect_Board(image)
        Calibration.Core.Record_Capture(directory, header, {
            'file': name, 'kind': 'flat' if key == 'f' else 'view',
            'time': datetime.now().isoformat(timespec='milliseconds'),
            'board_found': detection.Found, 'grid': list(detection.Grid),
            'corners': int(detection.Corners.shape[0]), 'reason': detection.Reason})
        if detection.Found:
            print('[INFO] %s: board found, %d x %d inner corners visible.'
                  % (name, detection.Grid[0], detection.Grid[1]))
        else:
            print('[WARNING] %s: kept, but %s. Consider another pose.' % (name, detection.Reason))

    del Basler_Cam_Id_1, Process_Image_Cls
    return 0


def Parse_Board(text: str) -> tp.Tuple[int, int]:
    """
    Description:
        Parse '--board-squares' ('11x8': squares across x down) into (columns, rows).

    Args:
        (1) text [string]: The argument.

    Returns:
        (1) parameter [Vector<int> 1x2]: (columns, rows).
    """

    try:
        columns, rows = (int(part) for part in text.lower().split('x'))
        assert columns >= 3 and rows >= 3
    except (ValueError, AssertionError):
        raise argparse.ArgumentTypeError('expected COLUMNSxROWS of squares, e.g. 11x8')
    return (columns, rows)


def Images_Main(directory: str, board_squares: tp.Tuple[int, int], square_mm: float,
                board_height_mm: float, write_calibration: bool, config_path: str) -> int:
    """
    Description:
        Calibrate from every image in a directory and print the report. The result is written to
        a NEW calibration file beside the hardware's calibration in force (which stays untouched),
        unless --write-calibration asks to overwrite it. Only a calibration file is ever written.

    Args:
        (1) directory [string]: The calibration capture directory.
        (2) board_squares [Vector<int> 1x2]: The board's squares (columns, rows).
        (3) square_mm [float]: The calipered square size (mm).
        (4) board_height_mm [float]: The flat boards' surface height above the table (mm).
        (5) write_calibration [bool]: Overwrite the calibration in force instead of writing a new one.
        (6) config_path [string]: A configuration on the hardware being calibrated (its name
                                  names the hardware, and so the calibration file).

    Returns:
        (1) parameter [int]: The process exit code (1 when nothing trustworthy could be solved).
    """

    try:
        report = Calibration.Core.Calibrate(Calibration.Core.Load_Views(directory), square_mm,
                                            board_height_mm, board_squares)
    except Calibration.Core.Calibration_Error_Cls as error:
        print('[ERROR] %s' % error)
        return 1
    for line in Calibration.Core.Report_Lines(report):
        print(line)
    # The window the images were captured at: its size is the images' own, its offset on the sensor
    # comes from the capture manifest. A set from before the manifest recorded it is accepted only
    # when its size is the configuration's, with the configuration's offset assumed - and said.
    window = Calibration.Core.Captured_Window(directory)
    configuration = Load_Configuration(config_path).Camera
    if window is not None:
        if tuple(window['resolution']) != tuple(report.Image_Size):
            print('[ERROR] The images are %d x %d but capture.json records %d x %d; nothing was written.'
                  % (tuple(report.Image_Size) + tuple(window['resolution'])))
            return 1
        offset = tuple(window['offset'])
    elif tuple(report.Image_Size) == tuple(configuration.Resolution):
        offset = tuple(configuration.Offset)
        print('[WARNING] capture.json does not record the sensor window; assuming the configuration\'s offset '
              '(%d, %d). Only true if the camera was set to it when these frames were taken.' % offset)
    else:
        print('[ERROR] The images are %d x %d, the configuration sets the camera to %d x %d, and capture.json '
              'does not record the window they were taken at; nothing was written. Recapture with --capture.'
              % (tuple(report.Image_Size) + tuple(configuration.Resolution)))
        return 1

    views = [view for view in report.Views if view.Detection.Found]
    flat = sum(view.Flat for view in views)
    record = {'date': datetime.now().isoformat(timespec='seconds'),
              'images': os.path.abspath(directory),
              'views': {'total': len(views), 'flat': flat, 'tilted': len(views) - flat},
              'rms_px': report.Rms_Px, 'square_mm': square_mm, 'board_height_mm': board_height_mm}
    hardware, _mode = Hardware_And_Mode(config_path)
    if not hardware:
        print('[ERROR] "%s" does not name its hardware (Config_<Hardware>_Mode_<Mode>.yaml).' % config_path)
        return 1
    in_force = Calibration_Path_For(config_path, hardware)
    # A camera calibrated for the first time has no calibration in force: there is nothing to keep,
    # so the result becomes it directly and the application measures from its next start.
    first = not os.path.exists(in_force)
    output = (in_force if write_calibration or first else
              os.path.join(os.path.dirname(in_force),
                           CONST_OUTPUT_TEMPLATE.format(hardware=hardware,
                                                        stamp=datetime.now().strftime('%Y%m%d-%H%M%S'))))
    if not Write_Calibration(Calibration.Core.Calibration_Parameters(report, offset), hardware=hardware,
                             header_source=in_force, output_path=output, record=record):
        return 1
    print('[INFO] Calibration written to: %s' % output)
    if first:
        print('[INFO] %s had no calibration, so this one is now in force for every mode on it.' % hardware)
    elif not write_calibration:
        print('[INFO] The calibration in force (%s) is UNCHANGED. Every mode on %s reads it, so '
              'adopting this one — renaming it over that file — is a separate, deliberate step.'
              % (os.path.basename(in_force), hardware))
    return 0


def main():
    """
    Description:
        Camera calibration for the Basler a2A1920-51gcPRO with the Computar M1228-MPW3 lens, from
        several chessboard views solved together. Two modes:

            --capture [DIR] capture distorted frames interactively ('f' flat, 't' tilted) into DIR,
                            or into a new Data/Images/Calibration/<timestamp>/ when DIR is omitted
            --images DIR    solve from every image in DIR and write a NEW calibration file
                            (or overwrite the hardware's calibration in force with
                            --write-calibration)

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """

    parser = argparse.ArgumentParser(description='Camera calibration from chessboard captures.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', metavar='DIR', nargs='?', const='',
                      help='capture distorted calibration frames into DIR (default: a new '
                           'Data/Images/Calibration/<timestamp>/)')
    mode.add_argument('--images', metavar='DIR', help='calibrate from every image in DIR')
    parser.add_argument('--board-squares', type=Parse_Board, metavar='CxR',
                        help='the board\'s squares, columns x rows, e.g. 11x8 (--images)')
    parser.add_argument('--square-mm', type=float, metavar='MM',
                        help='the CALIPERED square size in mm (--images)')
    parser.add_argument('--board-height-mm', type=float, metavar='MM',
                        help='the flat boards\' surface height above the table in mm (--images); written into '
                             'the calibration as Board_Height_Mm, the reference plane its mm/px factor is '
                             'measured on. Recorded, not applied: it does not change the solve')
    parser.add_argument('--config', default=CONST_DEFAULT_CONFIG_FILE,
                        help='a configuration on the hardware being calibrated (default: %(default)s)')
    parser.add_argument('--write-calibration', action='store_true',
                        help='overwrite the hardware\'s calibration in force instead of writing a new file')
    # The pre-split flag, kept only to say what replaced it: it would be in someone's shell history.
    parser.add_argument('--write-config', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.write_config:
        parser.error('--write-config was renamed --write-calibration: the calibration now lives in its '
                     'own file (Calibration_<Hardware>.yaml), and that is all this harness writes.')
    if args.capture is not None:
        directory = args.capture or os.path.join(CONST_CAPTURE_ROOT, datetime.now().strftime('%Y%m%d-%H%M%S'))
        return Capture_Main(directory, args.config)
    missing = [flag for flag, value in (('--board-squares', args.board_squares),
                                        ('--square-mm', args.square_mm),
                                        ('--board-height-mm', args.board_height_mm)) if value is None]
    if missing:
        parser.error('--images requires %s (no defaults: the board and its square size decide the result, and the '
                     'board height is written into the calibration as the reference plane the mm/px factor is '
                     'measured on, so a calibration never lacks one)' % ', '.join(missing))
    return Images_Main(args.images, args.board_squares, args.square_mm, args.board_height_mm,
                       args.write_calibration, args.config)

if __name__ == '__main__':
    sys.exit(main())
