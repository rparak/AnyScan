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
# File Name: ../Example/Vision/characterize.py
## =========================================================================== ##

# System (Default)
import sys
import os
# Resolve the project folder from this file's own location (Example/Vision -> ..)
# rather than the current working directory, so the harness produces the same
# baseline whether it is launched from Example/Vision/ or from the repo root.
# The sibling capture scripts use a cwd-relative '../../src'; this tool is meant
# to be re-run from anywhere during the migration, so it locates src/ and App/
# absolutely instead.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    '..', '..'))
for _path in (os.path.join(CONST_PROJECT_FOLDER, 'src'),
              os.path.join(CONST_PROJECT_FOLDER, 'App')):
    if _path not in sys.path:
        sys.path.append(_path)
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — logic under test
#   Functions are characterized BEFORE App/run.py is fully split into src/, so
#   whatever is not yet extracted is imported from `run`. As each module moves,
#   its import is repointed at the new src/ home and the .log must not change.
#   Status:
#     Detection / Analysis         -> ../Parameters/Vision.py   [EXTRACTED]
#     compose / summarise / scene_note / verdict / describe_object /
#     caption_sentence + label constants -> ../Reporting/Core.py [EXTRACTED]
#     _build_mask / _find_objects / _crop_with_pad -> ../Vision/Utilities/Segmentation.py [EXTRACTED]
#     _describe / _condense_label  -> ../Vision/Utilities/Caption.py       [EXTRACTED]
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
import Reporting.Core as Reporting
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Build_Mask, Find_Objects
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Condense_Label
#   ../../App/run.py
import run

"""
Description:
    Initialization of constants.
"""
# The committed reference background, at its Data/Camera/ path. The mixed pair
# below differences it against a synthetic frame derived from itself — same size,
# fully deterministic — so no second real image and no model weights are needed.
#   Unit [string]
CONST_BACKGROUND_A = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Camera', 'Image_Background_001.png')

# The two filled rectangles drawn onto the reference to synthesize a frame with
# a known foreground. They are well above SEG_MIN_AREA_FRAC and separated in x,
# so _find_objects must return them left-to-right. Given as (x1, y1, x2, y2).
#   Unit [Vector<Tuple<int> 1x4>]
CONST_SYNTHETIC_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]

# Where the deterministic baseline is written. This file is committed; the
# regression check after each extraction step is `git diff` on it.
#   Unit [string]
CONST_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'characterize_baseline.log')

# The frame size passed to the composer. Position is not part of any sentence, so
# the exact value only has to be fixed, not real.
#   Unit [Vector<int> 1x2]
CONST_FRAME_SIZE = (1920, 1200)

# Captions fed to the label distiller, chosen to exercise the lead-in stripping,
# the clause boundaries and the word cap.
#   Unit [Vector<string>]
CONST_CAPTION_SAMPLES = [
    'The image shows a close-up of a hex bolt on a green surface.',
    'In this image we can see a washer.',
    'a photograph of two brass fittings sitting on a table',
    'This is an M6 stainless steel screw with a hexagonal head.',
    '',
]


def _Format_Boxes(boxes: tp.List[tp.Tuple[int, int, int, int]]) -> tp.List[str]:
    """
    Description:
        Render a list of segmentation boxes as sorted, fixed-width text lines, so
        the baseline is stable regardless of how the list is iterated.

    Args:
        (1) boxes [Vector<Tuple<int> 1x4>]: Object boxes as (x1, y1, x2, y2).

    Returns:
        (1) parameter [Vector<string>]: One line per box, in row order.
    """

    return [f'    box[{i:02d}] = ({x1:>5}, {y1:>5}, {x2:>5}, {y2:>5})'
            for i, (x1, y1, x2, y2) in enumerate(boxes)]


def _Make_Synthetic_Frame(bg: np.ndarray) -> np.ndarray:
    """
    Description:
        Copy the reference and paint the CONST_SYNTHETIC_RECTS onto it in black,
        producing a same-size frame whose only difference from the reference is a
        known foreground. Differencing this against the reference isolates exactly
        the drawn regions, so the detected boxes are deterministic and independent
        of what the reference photograph actually shows.

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The background reference (BGR).

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The synthesized frame (BGR).
    """

    frame = bg.copy()
    for x1, y1, x2, y2 in CONST_SYNTHETIC_RECTS:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
    return frame


def _Characterize_Segmentation(bg: np.ndarray, fg: np.ndarray, frame_label: str) -> tp.List[str]:
    """
    Description:
        Run the background-subtraction detector on one (background, frame) pair
        and return a deterministic textual summary: the foreground pixel count
        and every object box found.

        This is the ported segment_classify pipeline: _build_mask differences the
        frame against the reference, _find_objects turns the mask into ordered
        boxes. Both are pure numpy/OpenCV and need no model.

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The empty-surface background reference (BGR).
        (2) fg [Matrix<uint8> HxWx3]: The frame differenced against it (BGR).
        (3) frame_label [string]: A short description of the frame, for the log.

    Returns:
        (1) parameter [Vector<string>]: The summary lines for the baseline file.
    """

    lines = [f'  frame = {frame_label}']
    mask = Build_Mask(bg, fg, cv2, np)
    boxes = Find_Objects(mask, cv2, np)
    lines.append(f'  foreground pixels = {int(np.count_nonzero(mask))}')
    lines.append(f'  objects found     = {len(boxes)}')
    lines.extend(_Format_Boxes(boxes))
    return lines


def _Make_Detection(label: str, bbox: tp.Tuple[int, int, int, int], detail: str = '',
                    confidence: tp.Optional[float] = None, text: tp.Optional[str] = None) -> Detection_Str:
    """
    Description:
        Build one Detection_Str fixture. Wrapped in a helper so the construction
        is named in exactly one place.

    Args:
        (1) label [string]: The distilled noun-phrase label.
        (2) bbox [Vector<int> 1x4]: Box as (x, y, w, h) in frame pixels.
        (3) detail [string]: The model's full caption (rendered as a sentence).
        (4) confidence [float]: Detector score, or None when unscored.
        (5) text [string]: Any text read off the object, or None.

    Returns:
        (1) parameter [Detection_Str(object)]: The populated detection.
    """

    return Detection_Str(Label=label, Bbox=bbox, Detail=detail, Confidence=confidence, Text=text)


def main() -> None:
    """
    Description:
        Offline characterization harness for the AnyScan vision logic. It exercises
        the parts of App/run.py that carry no Qt, no camera and no model — the
        report composer, the label distiller, the dataclasses and the background
        subtraction — on the two committed Data/Camera/ background frames, and
        writes a deterministic baseline to characterize_baseline.log.

        The baseline is the migration's safety net: after each module is extracted
        into src/, re-run this and confirm `git diff` on the .log is empty. Only
        numpy and OpenCV are required (pre-migration it also imports App/run.py,
        which pulls in PyQt5; after extraction it imports the Qt-free src/ modules).

        Reproduce (from the repo root, in the project venv — see README Setup):
            .venv/bin/python Example/Vision/characterize.py
    """

    print('[INFO] Characterizing the AnyScan vision logic (no camera, no weights).')
    lines = []

    """
    Description:
        Environment. Segmentation output depends on the OpenCV and NumPy builds,
        so their versions are recorded — a version change that shifts the boxes
        then shows up next to the numbers that moved.
    """
    lines.append('== AnyScan vision characterization baseline ==')
    lines.append(f'python = {sys.version.split()[0]}')
    lines.append(f'numpy  = {np.__version__}')
    lines.append(f'opencv = {cv2.__version__}')
    lines.append(f'detail-sentences (SHOW_OBJECT_DETAIL) = {Reporting.CONST_SHOW_OBJECT_DETAIL}')
    lines.append('')

    """
    Description:
        Domain dataclasses. Pin the field defaults and order.
    """
    lines.append('-- dataclasses --')
    det = _Make_Detection('hex bolt', (10, 20, 30, 40), detail='a hex bolt on a green surface')
    # Print field values under fixed labels, not the dataclass repr: the baseline
    # must pin behaviour, not the class/field names, so an RP rename of the
    # structure (Detection -> Detection_Str, label -> Label) leaves the .log
    # byte-identical and the post-extraction diff stays empty.
    lines.append('Detection: '
                 f'label={det.Label!r} bbox={det.Bbox} confidence={det.Confidence} '
                 f'text={det.Text} detail={det.Detail!r} sentence={det.Sentence!r}')
    analysis = Analysis_Str()
    lines.append('Analysis defaults: '
                 f'summary={analysis.Summary!r} objects={analysis.Objects} note={analysis.Note!r} '
                 f'latency_ms={analysis.Latency_Ms} verdict={analysis.Verdict!r} '
                 f'verdict_level={analysis.Verdict_Level!r} task={analysis.Task!r}')
    lines.append('')

    """
    Description:
        Report composer. Three scenes — empty, a single object with a verbose
        Florence caption, and several objects with a reading and a low score —
        pin every sentence the panel would show, plus the verdict wording/level.
    """
    lines.append('-- report composer --')

    # 1) Empty scene: the analyze() empty path passes EMPTY_SCENE_EXPLANATION.
    empty_objs, empty_summary, empty_note = Reporting.Compose([], CONST_FRAME_SIZE,
                                                        caption=Reporting.CONST_EMPTY_SCENE_EXPLANATION)
    e_badge, e_level = Reporting.Verdict(empty_objs)
    lines.append('[scene: empty]')
    lines.append(f'  summary = {empty_summary}')
    lines.append(f'  note    = {empty_note}')
    lines.append(f'  verdict = {e_badge} ({e_level})')

    # 2) One object, verbose caption exercising the lead-in stripping.
    one = [_Make_Detection('hex bolt', (100, 120, 80, 80),
                           detail='In this image we can see a hex bolt on a green surface.')]
    one_objs, one_summary, one_note = Reporting.Compose(one, CONST_FRAME_SIZE, caption='')
    o_badge, o_level = Reporting.Verdict(one_objs)
    lines.append('[scene: one object]')
    lines.append(f'  summary = {one_summary}')
    lines.append(f'  object1 = {one_objs[0].Sentence}')
    lines.append(f'  note    = {one_note!r}')
    lines.append(f'  verdict = {o_badge} ({o_level})')

    # 3) Several objects: a plain one, one with a reading and a low score, one
    #    with an empty caption that falls back to "A <label>.".
    many = [
        _Make_Detection('washer', (10, 10, 50, 50), detail='A metal washer.'),
        _Make_Detection('screw', (200, 50, 40, 90), detail='A close-up of a screw.',
                        confidence=0.20, text='M6'),
        _Make_Detection('nut', (300, 300, 60, 60), detail=''),
    ]
    many_objs, many_summary, many_note = Reporting.Compose(many, CONST_FRAME_SIZE, caption='')
    m_badge, m_level = Reporting.Verdict(many_objs)
    lines.append('[scene: several objects]')
    lines.append(f'  summary = {many_summary}')
    for i, obj in enumerate(many_objs, start=1):
        lines.append(f'  object{i} = {obj.Sentence}')
    lines.append(f'  note    = {many_note!r}')
    lines.append(f'  verdict = {m_badge} ({m_level})')
    lines.append('')

    """
    Description:
        Label distiller. The full caption survives in Detection_Str.Detail, so an
        imperfect distillation loses nothing — but the short label must stay
        stable, so it is pinned here directly.
    """
    lines.append('-- label distiller (_condense_label) --')
    for caption in CONST_CAPTION_SAMPLES:
        lines.append(f'  {caption!r:>62} -> {Condense_Label(caption)!r}')
    lines.append('')

    """
    Description:
        Segmentation, on the committed Data/Camera/ reference (001). The identical
        pair (001 vs 001) must yield no foreground; the synthetic pair differences
        001 against a copy of itself carrying two drawn rectangles, so exactly two
        ordered boxes must come back. Everything is read from the committed 001
        reference; no second real image is used.
    """
    lines.append('-- segmentation --')
    bg_a = cv2.imread(CONST_BACKGROUND_A)
    lines.append(f'reference 001 shape = {None if bg_a is None else bg_a.shape}')
    lines.append('[pair: 001 vs 001 (identical -> expect no objects)]')
    lines.extend(_Characterize_Segmentation(bg_a, bg_a, '001 (identical to reference)'))
    lines.append('[pair: 001 vs synthetic(001 + two rectangles)]')
    lines.extend(_Characterize_Segmentation(bg_a, _Make_Synthetic_Frame(bg_a),
                                            '001 with CONST_SYNTHETIC_RECTS drawn'))
    lines.append('')

    """
    Description:
        Write the baseline. One trailing newline, no timestamps, no absolute
        paths — the file must be byte-stable across runs on the same environment.
    """
    with open(CONST_OUTPUT_PATH, 'w') as handle:
        handle.write('\n'.join(lines) + '\n')

    rel_out = os.path.relpath(CONST_OUTPUT_PATH, CONST_PROJECT_FOLDER)
    print(f'[INFO] Baseline written to: {rel_out}')
    print(f'[INFO] {len(lines)} lines. Re-run after each extraction and diff this file.')


if __name__ == '__main__':
    sys.exit(main())
