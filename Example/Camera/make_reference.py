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
# File Name: ../Example/Camera/make_reference.py
## =========================================================================== ##

# System (Default)
import sys
# OS (Operating system interfaces)
import os
# Resolve src/ from this file's own location (Example/Camera -> ../../src), so the script runs the
# same whether launched from Example/Camera/ or the repository root.
_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
if _SRC not in sys.path:
    sys.path.append(_SRC)
# Re (Regular expressions: the next free reference index)
import re
# JSON (the sidecar)
import json
# Argparse (Command-line parsing)
import argparse
# Typing (Support for type hints)
import typing as tp
# Datetime (when the reference was shot)
from datetime import datetime
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.:
#   ../Camera/Core — the application's own camera path (window, processing, undistortion)
from Camera.Core import Basler_Camera_Cls, Camera_Error_Cls
#   ../Configuration/Core — the one configuration layer, the reference sidecar's one format, repository paths
from Configuration.Core import (Load_Configuration_For_Reference, Build_Reference_Sidecar, Reference_Sidecar_Path,
                                Reference_Line, Hardware_Record, File_Sha256, Display_Path, Configuration_Error_Cls,
                                CONST_DEFAULT_CONFIG_FILE, CONST_PROJECT_ROOT)
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str, Segmentation_Parameters_Str
#   ../Vision — stages 1 to 3 of the application's analysis: the background difference, FastSAM, the fusion
from Vision.Utilities.Segmentation import Background_Difference, Foreground_Mask
from Vision.Utilities.Fusion import Fuse_Objects
from Vision.Segmenter import Fast_Sam_Cls, Segmenter_Error_Cls

"""
Description:
    Initialization of constants.
"""
# Where references live, and their name: Image_Background_<NNN>.png and its sidecar .json, the next free index.
#   Unit [string]
CONST_REFERENCE_DIR = os.path.join(CONST_PROJECT_ROOT, 'Data', 'Images', 'Background')
CONST_REFERENCE_TEMPLATE = 'Image_Background_{index:03d}.png'
CONST_REFERENCE_PATTERN = re.compile(r'^Image_Background_(\d{3})\.(png|json)$')
# How many frames the reference is the mean of. Measured on the rig (2026-10-13, empty table, 16 frames through
# the application's camera path): the temporal noise is 5.9 grey levels per pixel; against held-out empty
# frames the difference's 99th percentile is 11 for one frame, 9 for 4 and 8 for 8 (the Otsu floor is 28). On
# the 41 test frames no reference changed a count or a verdict; between two references of 1 frame the sizes
# moved by 0.011 mm on average (0.20 mm at most), between two of 8 frames by 0.005 mm (0.16 mm). 16 frames
# added little over 8. 8 frames take about 2.6 s at the camera's 0.32 s per grab.
#   Unit [int]
CONST_REFERENCE_FRAMES = 8


class Reference_Error_Cls(ValueError):
    """
    Description:
        A reference that cannot be made; the message says why and what to do.
    """


def Next_Reference_Path(directory: str = CONST_REFERENCE_DIR) -> str:
    """
    Description:
        The next free reference name in a directory: one above the highest Image_Background_NNN, image or
        sidecar, so an existing reference (and the analyses made against it) is never overwritten.

    Args:
        (1) directory [string]: The reference directory.

    Returns:
        (1) parameter [string]: The path of the image.
    """

    indices = [int(match.group(1)) for match in map(CONST_REFERENCE_PATTERN.match, os.listdir(directory)) if match]
    return os.path.join(directory, CONST_REFERENCE_TEMPLATE.format(index=max(indices, default=0) + 1))


def Describe_Objects(objects: tp.List[tp.Any], size: tp.List[int]) -> tp.List[str]:
    """
    Description:
        What the check found, one line per object — its box in pixels, its share of the frame, and where it
        lies — so the operator can find it on the table.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The objects (Bbox as (x, y, w, h)).
        (2) size [Vector<int> 1x2]: The frame (width, height).

    Returns:
        (1) parameter [Vector<string>]: The lines, largest object first.
    """

    def _Region(x: float, y: float) -> str:
        """
        Description:
            The frame third a point falls in.

        Args:
            (1 - 2) x, y [float]: The point in frame pixels.

        Returns:
            (1) parameter [string]: 'top-left' ... 'centre' ... 'bottom-right'.
        """

        row = ('top', 'middle', 'bottom')[min(2, int(3 * y / size[1]))]
        column = ('left', 'centre', 'right')[min(2, int(3 * x / size[0]))]
        return 'centre' if (row, column) == ('middle', 'centre') else '%s-%s' % (row, column)

    boxes = sorted((tuple(int(v) for v in obj.Bbox) for obj in objects), key=lambda b: -b[2] * b[3])
    frame = float(size[0] * size[1])
    return ['%d × %d px (%.2f %% of the frame) at (%d, %d), %s'
            % (w, h, 100.0 * w * h / frame, x, y, _Region(x + w / 2.0, y + h / 2.0)) for x, y, w, h in boxes]


def Average_Frames(frames: tp.List[tp.List[tp.List[int]]]) -> tp.List[tp.List[int]]:
    """
    Description:
        The per-pixel mean of the frames, rounded to the nearest grey level: summed in float, so it never
        wraps at 255.

    Args:
        (1) frames [Vector<Matrix<uint8> HxWx3>]: The frames, all of one size.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The mean.
    """

    total = np.zeros(frames[0].shape, np.float64)
    for frame in frames:
        total += frame
    return np.clip(np.rint(total / len(frames)), 0, 255).astype(np.uint8)


def Find_Objects(frame_bgr: tp.List[tp.List[int]], reference_bgr: tp.Optional[tp.List[tp.List[int]]],
                 segmenter: tp.Any, Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> tp.List[tp.Any]:
    """
    Description:
        The objects the application would find on a frame: stages 1 to 3 of its analysis — the background
        difference against the reference, FastSAM, and the fusion with the mode's parameters (the same
        functions Vision.Core calls, so the same Min_Area_Fraction decides what is part-sized). Without a
        reference the background cue is empty and FastSAM alone finds the objects.

        Note:
            FastSAM is not optional. On the 41 test frames the background difference alone does not see 38 of
            the 150 objects (one of them a 60 × 40 mm plate in Image_062); FastSAM sees all 150, and returns
            no mask on an empty table (rig, 2026-10-13: 16 frames).

    Args:
        (1) frame_bgr [Matrix<uint8> HxWx3]: The frame (BGR).
        (2) reference_bgr [Matrix<uint8> HxWx3 or None]: The reference in force (BGR), or None.
        (3) segmenter [Fast_Sam_Cls(object)]: The loaded segmenter.
        (4) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: The mode's parameters.

    Returns:
        (1) parameter [Vector<Detection_Str(object)>]: The objects found.
    """

    if reference_bgr is None:
        background_fg = np.zeros(frame_bgr.shape[:2], np.uint8)
    else:
        background_fg, _threshold, _otsu = Foreground_Mask(Background_Difference(reference_bgr, frame_bgr, cv2, np),
                                                           cv2, np,
                                                           Segmentation_Parameters_Str=Segmentation_Parameters_Str)
    masks, scores = segmenter.Segment(frame_bgr)
    return Fuse_Objects(masks, scores, background_fg, cv2, np, Segmentation_Parameters_Str=Segmentation_Parameters_Str)


def Check_Empty(frames: tp.List[tp.List[tp.List[int]]], mean: tp.List[tp.List[int]],
                reference_bgr: tp.Optional[tp.List[tp.List[int]]], segmenter: tp.Any,
                Segmentation_Parameters_Str: Segmentation_Parameters_Str) -> None:
    """
    Description:
        Refuse a reference with anything part-sized on it: the mean, and each frame it is the mean of (a hand
        or a shadow in one frame is faint in the mean), must show no object to the application.

    Args:
        (1) frames [Vector<Matrix<uint8> HxWx3>]: The frames (BGR).
        (2) mean [Matrix<uint8> HxWx3]: Their mean (BGR): the reference to be written.
        (3) reference_bgr [Matrix<uint8> HxWx3 or None]: The reference in force (BGR), or None when it no
                                                         longer matches the camera.
        (4) segmenter [Fast_Sam_Cls(object)]: The loaded segmenter.
        (5) Segmentation_Parameters_Str [Segmentation_Parameters_Str(object)]: The mode's parameters.

    Raises:
        Reference_Error_Cls: Something was found; the message lists it.
    """

    size = [int(mean.shape[1]), int(mean.shape[0])]
    for name, image in [('the mean of the %d frames' % len(frames), mean)] \
            + [('frame %d of %d' % (i, len(frames)), frame) for i, frame in enumerate(frames, 1)]:
        objects = Find_Objects(image, reference_bgr, segmenter, Segmentation_Parameters_Str)
        if objects:
            raise Reference_Error_Cls(
                'The table is not empty: %s shows %d object(s) %s:\n%s\nClear the table (nothing in view, no shadow '
                'from the operator) and run it again.'
                % (name, len(objects), 'that differ from the reference in force' if reference_bgr is not None
                   else 'to FastSAM', '\n'.join('  - ' + line for line in Describe_Objects(objects, size))))


def Write_Reference(image: tp.List[tp.List[int]], output: str, sidecar_fields: tp.Dict[str, tp.Any]) -> tp.Dict:
    """
    Description:
        Write the reference and its sidecar, each created exclusively: an existing file is never written over,
        not even one that appeared since its name was chosen.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The reference (BGR).
        (2) output [string]: The image path; the sidecar goes beside it.
        (3) sidecar_fields [Dict]: Build_Reference_Sidecar's keyword arguments.

    Returns:
        (1) parameter [Dict]: The sidecar written.

    Raises:
        Reference_Error_Cls: The image or its sidecar already exists; nothing is left behind.
    """

    sidecar_path = Reference_Sidecar_Path(output)
    for path in (output, sidecar_path):
        if os.path.exists(path):
            raise Reference_Error_Cls('%s already exists; references are never overwritten (analyses were made '
                                      'against it).' % Display_Path(path))
    ok, encoded = cv2.imencode('.png', image)
    if not ok:
        raise Reference_Error_Cls('The reference could not be encoded as PNG.')
    try:
        with open(output, 'xb') as handle:
            handle.write(encoded.tobytes())
    except FileExistsError as error:
        raise Reference_Error_Cls('%s appeared while the reference was being written; nothing was written.'
                                  % Display_Path(output)) from error
    # The image is written: a sidecar that cannot be written takes it away again, so no reference is left
    # without its provenance (the configuration refuses one).
    try:
        sidecar = Build_Reference_Sidecar(output, **sidecar_fields)
        with open(sidecar_path, 'x', encoding='utf-8') as handle:
            json.dump(sidecar, handle, indent=2, ensure_ascii=False)
            handle.write('\n')
    except FileExistsError as error:
        os.remove(output)
        raise Reference_Error_Cls('%s appeared while the reference was being written; nothing was written.'
                                  % Display_Path(sidecar_path)) from error
    except Exception:
        os.remove(output)
        raise
    return sidecar


def Make_Reference(camera: tp.Any, Configuration_Str: Configuration_Str, reference_problems: tp.List[str],
                   segmenter: tp.Any, directory: str = CONST_REFERENCE_DIR) -> tp.Tuple[str, tp.Dict]:
    """
    Description:
        Shoot a background reference of the empty table and write it: CONST_REFERENCE_FRAMES frames through
        the application's camera path (the station's camera settings and window, the processing step, the
        undistortion with the station's calibration), their mean checked for anything part-sized, and the
        next free Image_Background_NNN.png with its sidecar. The station file is never edited.

        The check compares with the reference in force. When that reference no longer matches the camera
        (reference_problems: after a new calibration or window it fails the load), the comparison would mean
        nothing, so FastSAM alone looks for objects, and the sidecar records why nothing was compared.

    Args:
        (1) camera [Camera_Backend_Cls(object)]: The camera, configured, not connected.
        (2) Configuration_Str [Configuration_Str(object)]: The mode loaded by Load_Configuration_For_Reference.
        (3) reference_problems [Vector<string>]: What is wrong with the reference in force (empty: none).
        (4) segmenter [Fast_Sam_Cls(object)]: The loaded segmenter, built from the mode's parameters.
        (5) directory [string]: Where references are written.

    Returns:
        (1) parameter [Tuple]: (the image written, its sidecar).

    Raises:
        Camera_Error_Cls: The camera could not be connected or did not deliver (Camera.Core's
                          Camera_In_Use_Error_Cls: another program holds it, and the message says which to stop).
        Reference_Error_Cls: The table is not empty, or the name was taken; nothing is written.
    """

    # 1\ The frames, through the application's path, holding the camera no longer than the grabs.
    shot = datetime.now().isoformat(timespec='seconds')
    camera.Connect()
    try:
        frames = [cv2.cvtColor(camera.Capture(), cv2.COLOR_RGB2BGR) for _ in range(CONST_REFERENCE_FRAMES)]
        window, undistortion = camera.Window, camera.Last_Undistortion
    finally:
        camera.Disconnect()
    mean = Average_Frames(frames)

    # 2\ Nothing part-sized on the table: against the reference in force, or FastSAM alone without one.
    in_force = Configuration_Str.Segmentation.Background_Reference
    reference_bgr = None if reference_problems else cv2.imread(in_force)
    Check_Empty(frames, mean, reference_bgr, segmenter, Configuration_Str.Segmentation)

    # 3\ Write, never over an existing reference.
    output = Next_Reference_Path(directory)
    compared_with = None if reference_problems else {'reference': Display_Path(in_force),
                                                     'image_sha256': File_Sha256(in_force)}
    sidecar = Write_Reference(mean, output, dict(
        source='camera', frames=len(frames), shot=shot, configuration=Configuration_Str.Name,
        station=os.path.basename(Configuration_Str.Station_Path), window=window, undistortion=undistortion,
        hardware=Hardware_Record(Configuration_Str), compared_with=compared_with,
        not_compared='; '.join(reference_problems)))
    return output, sidecar


def Adoption_Lines(station_path: str, written: str) -> tp.List[str]:
    """
    Description:
        What to change to put a new reference in force: the station file's Background.Reference line, by its
        line number. The tool never edits the station file: it is written by hand, with comments, and adopting
        a reference is a deliberate step.

    Args:
        (1) station_path [string]: The station file.
        (2) written [string]: The new reference's path.

    Returns:
        (1) parameter [Vector<string>]: The lines to print.
    """

    station = Display_Path(station_path)
    line = Reference_Line(station_path, 'Background.Reference')
    where = 'line %d of %s' % (line, station) if line else "Background.Reference in %s" % station
    return ['[INFO] The station file was NOT edited: the reference in force is unchanged.',
            '[INFO] To use the new reference, change %s to:' % where,
            '        Reference: %s' % Display_Path(written).replace(os.sep, '/'),
            '[INFO] Then restart the application. Every mode naming this station uses it; the older references '
            'stay in %s to switch back to.' % (Display_Path(os.path.dirname(written)) + os.sep)]


def main():
    """
    Description:
        Shoot a new empty-surface reference with the camera. Clear the table first, then, with the AnyScan
        application disconnected from the camera:

            python Example/Camera/make_reference.py [--config <mode file>]

        writes Data/Images/Background/Image_Background_<next>.png, the mean of CONST_REFERENCE_FRAMES frames,
        and its provenance sidecar (.json), and prints the line of the station file to change to use it. The
        station file is not edited.
    """

    parser = argparse.ArgumentParser(description='Shoot a background reference of the empty table with the camera.')
    parser.add_argument('--config', default=CONST_DEFAULT_CONFIG_FILE,
                        help='a mode file naming the station: its camera settings, calibration and reference in '
                             'force, and the segmentation parameters the check uses (default: %(default)s)')
    # The removed flags, kept only to say what replaced them: they would be in someone's shell history.
    parser.add_argument('--from', dest='source', help=argparse.SUPPRESS)
    parser.add_argument('--accept-objects', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--output', help=argparse.SUPPRESS)
    args = parser.parse_args()
    for flag, given in (('--from', args.source is not None), ('--accept-objects', args.accept_objects),
                        ('--output', args.output is not None)):
        if given:
            parser.error('%s was removed: make_reference.py now shoots the reference itself, through the camera, '
                         'and refuses it if anything is on the table. Clear the table and run it without arguments '
                         '(or with --config); it writes the next free Data/Images/Background/Image_Background_NNN.png.'
                         % flag)

    try:
        configuration, reference_problems = Load_Configuration_For_Reference(args.config)
    except Configuration_Error_Cls as error:
        print('[ERROR] %s' % error)
        return 1
    for level, message in configuration.Notes:
        print('[%s] %s' % (level, message))
    if reference_problems:
        print('[WARNING] The reference in force no longer matches the camera, so the new one is not compared with '
              'it: FastSAM alone checks that the table is empty, and the sidecar records why. %s.'
              % '; '.join(reference_problems))

    print('[INFO] Loading FastSAM for the empty-table check...')
    segmenter = Fast_Sam_Cls(configuration.Segmentation)
    camera = Basler_Camera_Cls()
    camera.Set_Configuration(configuration.Camera, configuration.Name, os.path.basename(configuration.Calibration_Path))
    camera.Set_Log_Callback(lambda level, message: print('[%s] %s' % (level, message)))
    try:
        segmenter.Load()
        print('[INFO] Shooting %d frames of the table...' % CONST_REFERENCE_FRAMES)
        output, sidecar = Make_Reference(camera, configuration, reference_problems, segmenter, CONST_REFERENCE_DIR)
    except (Camera_Error_Cls, Segmenter_Error_Cls, Reference_Error_Cls, OSError) as error:
        for line in str(error).splitlines():
            print('[ERROR] %s' % line)
        print('[ERROR] No reference was written.')
        return 1
    finally:
        segmenter.Release()

    window = sidecar['window']
    print('[INFO] Reference written: %s (and its sidecar %s)'
          % (Display_Path(output), os.path.basename(Reference_Sidecar_Path(output))))
    print('[INFO] The mean of %d frames, shot %s at %d x %d, offset (%d, %d), undistorted with %s, lighting: %s.'
          % (sidecar['frames'], sidecar['shot'], window['resolution'][0], window['resolution'][1], window['offset'][0],
             window['offset'][1], sidecar['calibration']['file'], sidecar['hardware'].get('lighting') or 'not named'))
    if sidecar['compared_with'] is not None:
        print('[INFO] Compared with the reference in force (%s): nothing part-sized differs.'
              % sidecar['compared_with']['reference'])
    for line in Adoption_Lines(configuration.Station_Path, output):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
