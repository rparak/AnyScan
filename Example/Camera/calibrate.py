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
#   ../Configuration/Core — the one configuration layer (read the camera, write the calibration)
from Configuration.Core import (Load_Configuration, Write_Calibration, Hardware_And_Mode,
                                Calibration_Path_For, CONST_DEFAULT_CONFIG_FILE)
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


def Capture_Main(directory: str, config_path: str) -> int:
    """
    Description:
        Capture calibration frames interactively into a directory, one per key press, until 'q'.
        Each frame is the camera's image after the application's own processing step and BEFORE
        undistortion (a lens model can only be solved from distorted frames). Every frame taken
        is kept — also one where no board is found, which is reported but never deleted — and
        recorded in the directory's capture.json, which states that the frames are distorted.

    Args:
        (1) directory [string]: The directory the frames are written to (created if missing).
        (2) config_path [string]: The configuration whose camera settings the capture uses.

    Returns:
        (1) parameter [int]: The process exit code.
    """

    os.makedirs(directory, exist_ok=True)
    configuration = Load_Configuration(config_path)
    Basler_Cfg_Str = configuration.Camera
    Basler_Cam_Id_1 = Basler_Cls(config=Basler_Cfg_Str.Custom_Cfg)
    Process_Image_Cls = Camera.Utilities.Image_Processing.Process_Image_Cls('real')
    header = {'distorted': True,
              'note': ('These frames are NOT undistorted: they are the camera\'s images after the '
                       'application\'s processing step (the same blur and colour adjustment) and '
                       'before undistortion, for solving the lens model. They are not the '
                       'application\'s <set>_raw.png, which is undistorted.'),
              'processing': "Camera.Utilities.Image_Processing.Process_Image_Cls('real')",
              'configuration': configuration.Name,
              'camera': Basler_Cfg_Str.Name, 'custom_cfg': Basler_Cfg_Str.Custom_Cfg,
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
    if not Write_Calibration(Calibration.Core.Calibration_Parameters(report), hardware=hardware,
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

            --capture DIR   capture distorted frames interactively ('f' flat, 't' tilted)
            --images DIR    solve from every image in DIR and write a NEW calibration file
                            (or overwrite the hardware's calibration in force with
                            --write-calibration)

        Setup:
            Camera Model: Basler a2A1920-51gcPRO GigE Camera
            Lighting: EFFI-FD-200-200-000 High-Power Flat Light
    """

    parser = argparse.ArgumentParser(description='Camera calibration from chessboard captures.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', metavar='DIR', help='capture distorted calibration frames into DIR')
    mode.add_argument('--images', metavar='DIR', help='calibrate from every image in DIR')
    parser.add_argument('--board-squares', type=Parse_Board, metavar='CxR',
                        help='the board\'s squares, columns x rows, e.g. 11x8 (--images)')
    parser.add_argument('--square-mm', type=float, metavar='MM',
                        help='the CALIPERED square size in mm (--images)')
    parser.add_argument('--board-height-mm', type=float, metavar='MM',
                        help='the flat boards\' surface height above the table in mm (--images)')
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
        return Capture_Main(args.capture, args.config)
    missing = [flag for flag, value in (('--board-squares', args.board_squares),
                                        ('--square-mm', args.square_mm),
                                        ('--board-height-mm', args.board_height_mm)) if value is None]
    if missing:
        parser.error('--images requires %s (no defaults: each changes the result)' % ', '.join(missing))
    return Images_Main(args.images, args.board_squares, args.square_mm, args.board_height_mm,
                       args.write_calibration, args.config)

if __name__ == '__main__':
    sys.exit(main())
