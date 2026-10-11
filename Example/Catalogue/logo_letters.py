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
# File Name: ../Example/Catalogue/logo_letters.py
## =========================================================================== ##

# System (Default)
import sys
import os
import argparse
# Resolve the project folder from this file's own location (Example/Catalogue -> ..), so the script runs from anywhere.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
if os.path.join(CONST_PROJECT_FOLDER, 'src') not in sys.path:
    sys.path.append(os.path.join(CONST_PROJECT_FOLDER, 'src'))
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the reference's box reader and the crop the logo check compares in
#   ../Configuration/Core
from Configuration.Core import Read_Yolo_Box
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Logo_Reference_Str
#   ../Vision/Utilities/Logo
from Vision.Utilities.Logo import Reference_Logo_Crop

"""
Description:
    Initialization of constants.

    Writes a logo reference's letter boxes for its item file (Checks.Logo.<side>.References[].Letters). It cuts the
    reference the way the logo check does (Vision.Utilities.Logo.Reference_Logo_Crop: the frame turned Rotation_Deg
    about the YOLO box's centre, then cut by the box), finds the engraved strokes (adaptive threshold, a small
    closing), takes each component large enough as a letter, groups them into the given lines (top to bottom, each
    left to right, touching letters split and broken ones joined to the line's letter count), and names them. It
    prints the Letters lines and writes the crop with each box and letter drawn, to be looked at before the lines go
    into the item file; a count that does not match the lines is an error, and the boxes are then set by hand.

    Usage (from anywhere):
        python Example/Catalogue/logo_letters.py --item labyrinth --image back --lines JIC SMART FACTORY
"""

# The adaptive threshold's window and offset, the closing that joins a letter's broken strokes, the smallest
# letter, and the margin of the crop left out (the plate's edge and the table beyond it).
#   Unit [px] / [grey level] / [px] / [px^2] / [fraction of the crop]
CONST_BLOCK_PX = 31
CONST_OFFSET = 8
CONST_CLOSE_PX = 5
CONST_MIN_AREA_PX2 = 150
CONST_MARGIN = 0.06


def __Split(dark: tp.Any, box: tp.Tuple[int, int, int, int]) -> tp.List[tp.Tuple[int, int, int, int]]:
    """
    Description:
        A box holding two touching letters split in two at the column with the least stroke, away from its ends.

    Args:
        (1) dark [Matrix<uint8> hxw]: The strokes.
        (2) box [Tuple<int> 1x4]: (x, y, width, height).

    Returns:
        (1) parameter [Vector<Tuple<int> 1x4>]: The two boxes.
    """

    x, y, w, h = box
    columns = (dark[y:y + h, x:x + w] > 0).sum(axis=0).astype(float)
    inner = int(0.2 * w)
    cut = inner + int(np.argmin(columns[inner:w - inner]))
    return [(x, y, cut, h), (x + cut, y, w - cut, h)]


def Letter_Boxes(crop_bgr: tp.Any, lines: tp.List[str], margin: float) -> tp.List[tp.List[tp.Tuple[int, int, int, int]]]:
    """
    Description:
        The engraved letters' boxes in a turned reference crop, per line of text, each left to right. Components
        are grouped into lines by height, the lines taken from the top; a line with fewer components than letters
        has its widest split at its thinnest column, one with more has its two closest neighbours joined.

    Args:
        (1) crop_bgr [Matrix<uint8> hxwx3]: The turned crop.
        (2) lines [Vector<string>]: Each line's letters, from the top.
        (3) margin [float]: The fraction of the crop left out at each edge.

    Returns:
        (1) parameter [Vector<Vector<Tuple<int> 1x4>>]: (x, y, width, height) per letter, per line found.
    """

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    dark = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, CONST_BLOCK_PX, CONST_OFFSET)
    my, mx = int(margin * height), int(margin * width)
    dark[:my], dark[height - my:], dark[:, :mx], dark[:, width - mx:] = 0, 0, 0, 0
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, np.ones((CONST_CLOSE_PX, CONST_CLOSE_PX), np.uint8))
    count, _labels, stats, _centres = cv2.connectedComponentsWithStats(dark)
    boxes = [tuple(int(v) for v in stats[i, :4]) for i in range(1, count) if stats[i, 4] >= CONST_MIN_AREA_PX2]
    found = []
    for box in sorted(boxes, key=lambda b: b[1] + b[3] / 2.0):
        centre = box[1] + box[3] / 2.0
        line = next((line for line in found if line[0] <= centre <= line[1]), None)
        if line is None:
            found.append([box[1], box[1] + box[3], [box]])
        else:
            line[0], line[1] = min(line[0], box[1]), max(line[1], box[1] + box[3])
            line[2].append(box)
    result = []
    for text, (_top, _bottom, members) in zip(lines, sorted(found, key=lambda l: l[0])):
        members = sorted(members, key=lambda b: b[0])
        while len(members) < len(text):
            widest = max(range(len(members)), key=lambda i: members[i][2])
            members[widest:widest + 1] = __Split(dark, members[widest])
        while len(members) > len(text):
            i = min(range(len(members) - 1), key=lambda i: members[i + 1][0] - (members[i][0] + members[i][2]))
            (x0, y0, w0, h0), (x1, y1, w1, h1) = members[i], members[i + 1]
            x, y = min(x0, x1), min(y0, y1)
            members[i:i + 2] = [(x, y, max(x0 + w0, x1 + w1) - x, max(y0 + h0, y1 + h1) - y)]
        result.append(members)
    return result


def main() -> int:
    """
    Description:
        Cuts the reference, finds and names its letters, draws them and prints the item file's lines.

    Returns:
        (1) parameter [int]: 0 when every letter of the lines has a box, 1 otherwise.
    """

    parser = argparse.ArgumentParser(description='Write a logo reference\'s letter boxes.')
    parser.add_argument('--item', required=True, help='The catalogue item folder under Data/Catalogue.')
    parser.add_argument('--image', required=True, help='The reference image, reference_image/<image>.png.')
    parser.add_argument('--rotation', type=float, default=0.0, help='Degrees counter-clockwise to read upright.')
    parser.add_argument('--lines', nargs='+', required=True, help='The letters of each engraved line, from the top.')
    parser.add_argument('--margin', type=float, default=CONST_MARGIN, help='The fraction of the crop left out at each edge.')
    parser.add_argument('--out', default=None, help='Where to write the drawn crop (default: Data/Results/).')
    arguments = parser.parse_args()
    folder = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Catalogue', arguments.item, 'reference_image')
    image = os.path.join(folder, '%s.png' % arguments.image)
    box = Read_Yolo_Box(os.path.splitext(image)[0] + '.txt')
    frame = cv2.imread(image)
    if frame is None or box is None:
        print('[ERROR] %s and its one-line YOLO .txt are required.' % image)
        return 1
    crop = Reference_Logo_Crop(frame, Catalogue_Logo_Reference_Str(Name=arguments.image, Image_Path=image, Box=box,
                                                                    Rotation_Deg=arguments.rotation, Letters=[]), cv2, np)
    lines = [line.replace(' ', '').upper() for line in arguments.lines]
    letters = ''.join(lines)
    boxes = [box for line in Letter_Boxes(crop, lines, arguments.margin) for box in line]
    drawn = crop.copy()
    for letter, (x, y, w, h) in zip(letters, boxes):
        cv2.rectangle(drawn, (x, y), (x + w, y + h), (0, 0, 255), 1)
        cv2.putText(drawn, letter, (x, max(10, y - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
    out = arguments.out or os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Results', '%s_%s_letters.png' % (arguments.item,
                                                                                                      arguments.image))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cv2.imwrite(out, drawn)
    print('[INFO] The crop is %d x %d px; %d letter boxes found, %d letters expected; drawn to %s.'
          % (crop.shape[1], crop.shape[0], len(boxes), len(letters), out))
    if len(boxes) != len(letters):
        print('[ERROR] The boxes do not match the lines: look at the drawing and set the boxes by hand.')
        return 1
    print('        Letters:')
    for letter, (x, y, w, h) in zip(letters, boxes):
        print('          - [%s, %d, %d, %d, %d]' % (letter, x, y, w, h))
    return 0


if __name__ == '__main__':
    sys.exit(main())
