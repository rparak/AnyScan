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
_SRC = os.path.join(CONST_PROJECT_FOLDER, 'src')
if _SRC not in sys.path:
    sys.path.append(_SRC)
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — logic under test
#   The migration is complete: every characterized function now lives in its src/
#   module, so this harness imports only from src/ and needs no Qt. It stays the
#   end-to-end regression baseline; a change in the .log is a behaviour change.
#     Detection_Str / Analysis_Str -> ../Parameters/Vision.py
#     the report composer          -> ../Reporting/Core.py
#     background subtraction        -> ../Vision/Utilities/Segmentation.py
#     the label distiller           -> ../Vision/Utilities/Caption.py
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
import Reporting.Core as Reporting
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Background_Foreground
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Condense_Label

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

# The fixtures below are REAL describer output — verbatim Gemma 4 E4B text from the seven-frame
# run of 2026-09-24 (Apple silicon, temperature 0), so the baseline pins what the pipeline
# produces now, not phrasing no model writes. Frame and object are named at each one.
#
# The background sentence Gemma wrote for the Data/Camera reference; it opens the
# Screen-Understanding header (the panel's first line) in the baseline.
#   Unit [string]
CONST_BASELINE_BACKGROUND = 'A deep teal surface presents a uniform, matte finish.'

# Descriptions fed to the label distiller (Gemma's, verbatim), chosen to cover the range of
# the head-noun rule — including one it handles poorly and one where the text itself is wrong.
# Printed in the baseline by frame and object, with the label they distil to; '' is the
# empty-description default.
#   Unit [Vector<Tuple<string, string>>]
CONST_CAPTION_SAMPLES = [
    ('Image_007 obj 1',
     'The object is a rectangular, flat plate of a bright, silvery-grey metal, likely '
     'steel or aluminum. It features four small, drilled holes near the corners, and the '
     'main surface exhibits numerous fine scratches and minor scuffs consistent with '
     'handling or machining. Overall, the surface appears relatively clean, though it '
     'bears the marks of use.'),
    ('Image_001 obj 5',
     'The object is a small, white, rectangular plastic or ceramic component with a '
     'series of evenly spaced vertical slots on its base. Through these slots, several '
     'circular holes are visible, each containing a small, metallic, screw-like element, '
     'and the overall surface appears clean with no visible signs of dirt or '
     'discoloration.'),
    ('Image_001 obj 1',
     'The object is a circular ring, appearing to be made of a dull, metallic material '
     'with a silvery-grey tone. It features a central through-hole, and the outer rim '
     'exhibits several faint, parallel linear markings across its surface. The part '
     'appears generally clean, though there is some slight unevenness in the finish.'),
    ('Image_001 obj 6',
     'The object is a metallic bolt or screw, appearing silver in color and likely made '
     'of steel or a similar alloy. It features a cylindrical head and a threaded shaft '
     'extending from it. The surface appears relatively clean, though there are some '
     'minor streaks or slight variations in tone across the body.'),
    ('Image_001 obj 2',
     'The object is a dark blue, somewhat amorphous plastic or rubber-like part with a '
     'shape resembling a stylized arrow or a wide, uneven bracket. Its surface appears '
     'mostly uniform in color, though there is a slight variation in tone across its '
     'expanse, and it seems to be in generally clean condition with no immediately '
     'visible scratches or significant stains.'),
    ('Image_001 obj 7',
     'The object is a small, roughly octagonal metal washer or flange with a central '
     'circular depression. The piece appears to be made of a dull, silvery-grey metal, '
     'and its surface shows some minor signs of tarnish or slight discoloration, '
     'particularly around the edges.'),
    ('empty', ''),
]
# What each sample exercises (in order): the comma-separated adjective run and ' of '
# (handled well); 'or' joining modifiers before the noun; an '-ing' clause after the noun and a
# part name ending in '-ing'; 'or' between alternative nouns; handled poorly (vague, with a
# degree adverb kept); faithful to a wrong text (a hex nut Gemma calls a washer); the default.


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

        Background_Foreground differences the frame against the reference and returns
        the background-subtracted foreground mask — the deterministic stage-1 output
        that is one of the two cues the fusion stage combines. The FastSAM/fusion
        stages need weights and are not part of this hermetic harness, so this
        characterizes the mask alone: its foreground pixel count and the connected
        components it splits into. Pure numpy/OpenCV, no model.

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The empty-surface background reference (BGR).
        (2) fg [Matrix<uint8> HxWx3]: The frame differenced against it (BGR).
        (3) frame_label [string]: A short description of the frame, for the log.

    Returns:
        (1) parameter [Vector<string>]: The summary lines for the baseline file.
    """

    lines = [f'  frame = {frame_label}']
    mask = Background_Foreground(bg, fg, cv2, np)
    lines.append(f'  foreground pixels = {int(np.count_nonzero(mask))}')

    # The connected components of the foreground mask, above a small speck area, as
    # deterministic boxes — the objects the difference alone can already separate.
    count, _, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8) * 255,
                                                          connectivity=8)
    boxes = [(int(stats[i, cv2.CC_STAT_LEFT]), int(stats[i, cv2.CC_STAT_TOP]),
              int(stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH]),
              int(stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT]))
             for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 50]
    boxes.sort()
    lines.append(f'  foreground components = {len(boxes)}')
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
                 f'objects={analysis.Objects} note={analysis.Note!r} '
                 f'latency_ms={analysis.Latency_Ms} verdict={analysis.Verdict!r} '
                 f'verdict_level={analysis.Verdict_Level!r} task={analysis.Task!r}')
    lines.append('')

    """
    Description:
        Report composer. Three scenes — empty, a single object with a real Gemma
        description, and several objects with a reading and a low score —
        pin every sentence the panel would show, plus the verdict wording/level.
    """
    lines.append('-- report composer --')

    # 1) Empty scene: the analyze() empty path passes EMPTY_SCENE_EXPLANATION.
    empty_objs, empty_note = Reporting.Compose([], CONST_FRAME_SIZE,
                                                        caption=Reporting.CONST_EMPTY_SCENE_EXPLANATION)
    e_badge, e_level = Reporting.Verdict(empty_objs)
    lines.append('[scene: empty]')
    lines.append(f'  header  = {Reporting.Screen_Header(empty_objs, CONST_BASELINE_BACKGROUND)}')
    lines.append(f'  note    = {empty_note}')
    lines.append(f'  verdict = {e_badge} ({e_level})')

    # 2) One object: Gemma's description of the rust-stained plate (Image_002 obj 1).
    one = [_Make_Detection('rectangular metallic plate', (100, 120, 80, 80),
                           detail='The object is a rectangular metallic plate, appearing to be silver or a similar '
                              'bright metal, featuring two circular cutouts each containing a central green '
                              'element. The surface exhibits numerous fine, concentric scratches across the '
                              'entire body, and there are noticeable brown, earthy-toned stains or deposits '
                              'clustered in the upper section of the plate.')]
    one_objs, one_note = Reporting.Compose(one, CONST_FRAME_SIZE, caption='')
    o_badge, o_level = Reporting.Verdict(one_objs)
    lines.append('[scene: one object]')
    lines.append(f'  header  = {Reporting.Screen_Header(one_objs, CONST_BASELINE_BACKGROUND)}')
    lines.append(f'  object1 = {one_objs[0].Sentence}')
    lines.append(f'  note    = {one_note!r}')
    lines.append(f'  verdict = {o_badge} ({o_level})')

    # 3) Several objects: a plain one, one with a reading and a low score, one
    #    with an empty caption that falls back to "A <label>.".
    #    The two descriptions are Gemma's (Image_001 obj 3 and obj 6).
    many = [
        _Make_Detection('circular metallic washer', (10, 10, 50, 50),
                        detail='The object is a circular metallic washer or ring, appearing silver or bright in '
                               'color, with a central through-hole. The outer edge is clearly defined, and the '
                               'inner hole allows a view into the green surface beneath. The surface of the part '
                               'appears generally clean with no visible scratches, stains, or tarnish.'),
        _Make_Detection('metallic bolt', (200, 50, 40, 90),
                        detail='The object is a metallic bolt or screw, appearing silver in color and likely made '
                               'of steel or a similar alloy. It features a cylindrical head and a threaded shaft '
                               'extending from it. The surface appears relatively clean, though there are some '
                               'minor streaks or slight variations in tone across the body.',
                        confidence=0.20, text='M6'),
        _Make_Detection('nut', (300, 300, 60, 60), detail=''),
    ]
    many_objs, many_note = Reporting.Compose(many, CONST_FRAME_SIZE, caption='')
    m_badge, m_level = Reporting.Verdict(many_objs)
    lines.append('[scene: several objects]')
    lines.append(f'  header  = {Reporting.Screen_Header(many_objs, CONST_BASELINE_BACKGROUND)}')
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
    for source, caption in CONST_CAPTION_SAMPLES:
        lines.append(f'  {source:<16} -> {Condense_Label(caption)!r}')
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
