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
#   Add access if it is not in the system path.
if '../../' + 'src' not in sys.path:
    sys.path.append('../../' + 'src')
# OS (Operating system interfaces)
import os
# Re (Regular expressions: the next free reference index)
import re
# JSON (the sidecar)
import json
# Shutil (copying the frame byte for byte)
import shutil
# Argparse (Command-line parsing)
import argparse
# Typing (Support for type hints)
import typing as tp
# Pillow (Image header reading: the frame's size) [pip3 install Pillow]
from PIL import Image
# Custom Lib.:
#   ../Configuration/Core — the reference sidecar's one format, and repository paths
from Configuration.Core import (Build_Reference_Sidecar, Reference_Sidecar_Path, Display_Path,
                                CONST_PROJECT_ROOT)
#   ../UI/Capture — the capture set's one reader, and its file names
from UI.Capture import Read_Capture_Set, CONST_CAPTURE_SUFFIXES

"""
Description:
    Initialization of constants.
"""
# Where references live, and their name: Image_Background_<NNN>.png, the next free index.
#   Unit [string]
CONST_REFERENCE_DIR = os.path.join(CONST_PROJECT_ROOT, 'Data', 'Images', 'Background')
CONST_REFERENCE_TEMPLATE = 'Image_Background_{index:03d}.png'
CONST_REFERENCE_PATTERN = re.compile(r'^Image_Background_(\d{3})\.png$')


class Reference_Error_Cls(ValueError):
    """
    Description:
        A capture set that cannot become a reference; the message says why and what to do.
    """


def Set_Prefix(path: str) -> str:
    """
    Description:
        The capture set a path names: any of its artefacts ('<dir>/<set>_raw.png', '_objects.json', ...)
        or the prefix itself, as '<dir>/<set>'.

    Args:
        (1) path [string]: A path to one of the set's files, or to the set's prefix.

    Returns:
        (1) parameter [string]: The set's prefix.
    """

    for suffix in CONST_CAPTURE_SUFFIXES:
        if path.endswith(suffix):
            return path[:-len(suffix)]
    return path


def Next_Reference_Path(directory: str = CONST_REFERENCE_DIR) -> str:
    """
    Description:
        The next free reference name in a directory: one above the highest Image_Background_NNN.png,
        so an existing reference (and the analyses made against it) is never overwritten.

    Args:
        (1) directory [string]: The reference directory.

    Returns:
        (1) parameter [string]: The path.
    """

    indices = [int(match.group(1)) for match in map(CONST_REFERENCE_PATTERN.match, os.listdir(directory)) if match]
    return os.path.join(directory, CONST_REFERENCE_TEMPLATE.format(index=max(indices, default=0) + 1))


def Describe_Objects(objects: tp.List[tp.Any], size: tp.List[int]) -> tp.List[str]:
    """
    Description:
        What the analysis of a would-be reference found, one line per object — its box in pixels, its
        share of the frame, and where it lies — so a decision to accept it is informed: a few small
        boxes scattered at the edges are the expected noise of analysing the empty table against the
        old reference; one large box in the middle is something left on the table.

    Args:
        (1) objects [Vector<Capture_Object_Str(object)>]: The set's objects (Bbox as (x, y, w, h)).
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


def Make_Reference(set_path: str, output: str, accept_objects: bool = False) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Make a background reference from a capture set: copy its '_raw.png' — the application's own
        frame, processed and undistorted exactly as the pipeline sees it — byte for byte, and write the
        sidecar from the set's own records: the window the camera read back, the lens model that
        undistorted it (the set's undistortion record), the configuration, the camera, lens and
        lighting, and when it was shot. Nothing in the sidecar is typed by a person.

        Refused, with nothing written: a set that records no window (older, or a saved frame), a
        frame whose size is not that window's, a set in which the analysis found objects unless
        accepted, and an output that already exists. Found objects are listed (size, share of the
        frame, position) in the refusal, so the override is a reading of the list, not a reflex; an
        accepted set records them in the sidecar ('accepted_objects').

    Args:
        (1) set_path [string]: The capture set (any of its files, or its prefix).
        (2) output [string]: The reference image to write (its sidecar goes beside it).
        (3) accept_objects [bool]: Make it even though the analysis found objects.

    Returns:
        (1) parameter [Dict]: The sidecar written.

    Raises:
        Reference_Error_Cls: The set cannot become a reference; the message says why.
    """

    # The set, through its one reader: a set whose ANALYZE failed (partial) has no record to vouch for it.
    prefix = Set_Prefix(set_path)
    capture = Read_Capture_Set(os.path.dirname(prefix), os.path.basename(os.path.dirname(prefix)),
                               os.path.basename(prefix))
    if capture.Partial or capture.Raw_Path is None:
        raise Reference_Error_Cls('%s is not a complete capture set: it needs its _raw.png and _objects.json '
                                  '(a set whose ANALYZE succeeded).' % prefix)

    # 1\ The window: recorded by the camera, or this set cannot say where on the sensor it was shot.
    window = capture.Window
    if window is None:
        raise Reference_Error_Cls('%s records no sensor window: it was captured before sets recorded one, or from '
                                  'a saved frame rather than the camera. Shoot the reference with the camera '
                                  '(docs/capture-checklist.md, item 2).' % os.path.basename(prefix))
    with Image.open(capture.Raw_Path) as image:
        size = [int(image.size[0]), int(image.size[1])]
    if size != list(window['resolution']):
        raise Reference_Error_Cls('%s is %d × %d but the set records a %d × %d window.'
                                  % (os.path.basename(capture.Raw_Path), size[0], size[1], window['resolution'][0],
                                     window['resolution'][1]))

    # 2\ An empty table: the analysis must have found nothing.
    objects = capture.Objects
    found = Describe_Objects(objects, size)
    if objects and not accept_objects:
        raise Reference_Error_Cls('the analysis of this set found %d object(s):\n%s\nSmall boxes scattered at the '
                                  'edges are the expected noise of analysing the empty table against the old '
                                  'reference; pass --accept-objects for those. A large box means something is on '
                                  'the table: clear it and shoot again.'
                                  % (len(objects), '\n'.join('  - ' + line for line in found)))

    # 3\ The lens model that undistorted the frame: the set's undistortion record (None when the camera
    #    had no calibration, and so the frame was not undistorted).
    undistortion = capture.Undistortion

    # 4\ Write: never over an existing reference or sidecar.
    sidecar_path = Reference_Sidecar_Path(output)
    for path in (output, sidecar_path):
        if os.path.exists(path):
            raise Reference_Error_Cls('%s already exists; references are never overwritten (analyses were made '
                                      'against it). Choose another --output.' % Display_Path(path))
    shutil.copyfile(capture.Raw_Path, output)
    sidecar = Build_Reference_Sidecar(output, source=Display_Path(capture.Raw_Path), shot=capture.Timestamp,
                                      configuration=capture.Configuration, window=window,
                                      undistortion=undistortion, hardware=capture.Hardware)
    if objects:
        # The override is part of the provenance: what the analysis found, and that it was accepted.
        sidecar['accepted_objects'] = found
    with open(sidecar_path, 'w', encoding='utf-8') as handle:
        json.dump(sidecar, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    return sidecar


def main():
    """
    Description:
        Make the empty-surface reference from a capture set of the empty table:

            python make_reference.py --from logger/captures/<connection>/<set>_raw.png

        writes Data/Images/Background/Image_Background_<next>.png and its provenance sidecar (.json). The
        configuration is not edited: set Segmentation.Background.Reference to the new file and
        restart, as a deliberate step.
    """

    parser = argparse.ArgumentParser(description='Make a background reference from a capture set of the empty table.')
    parser.add_argument('--from', dest='source', required=True, metavar='SET',
                        help='the capture set: any of its files, e.g. logger/captures/<connection>/<set>_raw.png')
    parser.add_argument('--output', metavar='PNG', help='the reference to write (default: the next free '
                                                        'Data/Images/Background/Image_Background_NNN.png)')
    parser.add_argument('--accept-objects', action='store_true',
                        help='make it even though the analysis found objects (only if they are spurious)')
    args = parser.parse_args()

    output = os.path.abspath(args.output) if args.output else Next_Reference_Path()
    try:
        sidecar = Make_Reference(os.path.abspath(args.source), output, args.accept_objects)
    except (Reference_Error_Cls, OSError, ValueError, KeyError) as error:
        for line in str(error).splitlines():
            print('[ERROR] %s' % line)
        print('[ERROR] No reference was written.')
        return 1
    for line in sidecar.get('accepted_objects', []):
        print('[WARNING] Accepted, recorded in the sidecar: %s' % line)
    window = sidecar['window']
    print('[INFO] Reference written: %s (and its sidecar %s)'
          % (Display_Path(output), os.path.basename(Reference_Sidecar_Path(output))))
    print('[INFO] Shot %s at %d x %d, offset (%d, %d), %s, lighting: %s.'
          % (sidecar['shot'], window['resolution'][0], window['resolution'][1], window['offset'][0],
             window['offset'][1], 'uncalibrated' if sidecar['calibration'] is None
             else 'undistorted with %s' % sidecar['calibration']['file'], sidecar['hardware'].get('lighting') or 'not named'))
    print('[INFO] To use it: set Segmentation.Background.Reference to %s and restart the application.'
          % Display_Path(output))
    return 0


if __name__ == '__main__':
    sys.exit(main())
