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
# File Name: ../test/Vision/test_characterize.py
## =========================================================================== ##

# System (Default)
import os
import difflib
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the logic the golden file pins
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str
#   ../Reporting/Core
import Reporting.Core as Reporting
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Background_Foreground
#   ../Vision/Utilities/Caption
from Vision.Utilities.Caption import Condense_Label
#   ../Configuration/Core — the stage parameters the application runs with
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    The characterization golden file: one text snapshot of the logic that carries no Qt, no camera
    and no model — the dataclass defaults, every sentence the report composer writes for three
    scenes, the label distiller on Gemma's own descriptions, and the background subtraction's
    object count on the committed reference — compared line for line against
    test/Vision/data/characterization.txt on every run.

    It replaces Example/Vision/characterize.py, a manual gate (run it, then `git diff` its log)
    that caught a missed baseline update once (0e67622) because someone happened to run it. The
    snapshot is deliberately free of toolchain detail: no Python / NumPy / OpenCV versions, no
    foreground pixel counts, no box coordinates — only what the application's behaviour decides,
    so a dependency bump does not fail it.

    An intended behaviour change: run `pytest test/Vision/test_characterize.py --update-golden`,
    then review the golden file's diff before committing it.
"""
# The committed golden file.
#   Unit [string]
CONST_GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'characterization.txt')
# Two rectangles drawn onto a copy of the reference: differencing that copy against the reference
# must find exactly these two objects.
#   Unit [Vector<Tuple<int> 1x4>] (x1, y1, x2, y2)
CONST_SYNTHETIC_RECTS = [(300, 300, 560, 560), (1200, 700, 1480, 980)]
# The frame size the composer is given, and the background sentence Gemma wrote for the reference
# (it opens the Scene-Understanding header).
#   Unit [Tuple<int> 1x2] / [string]
CONST_FRAME_SIZE = (1920, 1200)
CONST_BASELINE_BACKGROUND = 'A deep teal surface presents a uniform, matte finish.'
# Descriptions fed to the label distiller (Gemma's, verbatim), chosen to cover the range of the
# head-noun rule — including one it handles poorly and one where the text itself is wrong. In
# order: the comma-separated adjective run and ' of '; 'or' joining modifiers before the noun; an
# '-ing' clause after the noun and a part name ending in '-ing'; 'or' between alternative nouns;
# handled poorly (vague, with a degree adverb kept); faithful to a wrong text (a hex nut Gemma
# calls a washer); the empty default.
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


def _Detection(label: str, bbox: tp.Tuple[int, int, int, int], detail: str = '',
               confidence: tp.Optional[float] = None, text: tp.Optional[str] = None) -> Detection_Str:
    """
    Description:
        One Detection_Str fixture, built in one place.

    Args:
        (1) label [string]: The distilled label.
        (2) bbox [Vector<int> 1x4]: The box as (x, y, w, h).
        (3) detail [string]: The model's full description.
        (4) confidence [float]: A detector score, or None.
        (5) text [string]: Text read off the object, or None.

    Returns:
        (1) parameter [Detection_Str(object)]: The detection.
    """

    return Detection_Str(Label=label, Bbox=bbox, Detail=detail, Confidence=confidence, Text=text)


def _Component_Count(bg: np.ndarray, frame: np.ndarray) -> int:
    """
    Description:
        The objects background subtraction alone separates: connected components of the foreground
        mask of at least 50 px. The count is what the behaviour decides; the exact pixels depend
        on the OpenCV build and are not pinned.

    Args:
        (1) bg [Matrix<uint8> HxWx3]: The reference (BGR).
        (2) frame [Matrix<uint8> HxWx3]: The frame differenced against it (BGR).

    Returns:
        (1) parameter [int]: The component count.
    """

    mask = Background_Foreground(bg, frame, cv2, np,
                                 Segmentation_Parameters_Str=Load_Configuration(CONST_DEFAULT_CONFIG_FILE).Segmentation)
    count, _, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8) * 255, connectivity=8)
    return sum(1 for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 50)


def _Characterization(reference: np.ndarray) -> tp.List[str]:
    """
    Description:
        Build the snapshot's lines.

    Args:
        (1) reference [Matrix<uint8> HxWx3]: The committed reference background (BGR).

    Returns:
        (1) parameter [Vector<string>]: The lines, in the golden file's order.
    """

    lines = ['== AnyScan vision characterization ==',
             f'detail-sentences (SHOW_OBJECT_DETAIL) = {Reporting.CONST_SHOW_OBJECT_DETAIL}', '']

    # 1\ The dataclasses' field defaults, under fixed labels (not the repr), so a rename leaves it.
    det = _Detection('hex bolt', (10, 20, 30, 40), detail='a hex bolt on a green surface')
    analysis = Analysis_Str()
    lines += ['-- dataclasses --',
              f'Detection: label={det.Label!r} bbox={det.Bbox} confidence={det.Confidence} '
              f'text={det.Text} detail={det.Detail!r} sentence={det.Sentence!r}',
              f'Analysis defaults: objects={analysis.Objects} note={analysis.Note!r} '
              f'latency_ms={analysis.Latency_Ms} verdict={analysis.Verdict!r} '
              f'verdict_level={analysis.Verdict_Level!r} task={analysis.Task!r}', '']

    # 2\ The report composer: three scenes, every sentence the panel shows, and the verdict.
    lines.append('-- report composer --')
    empty_objs, empty_note = Reporting.Compose([], CONST_FRAME_SIZE, caption=Reporting.CONST_EMPTY_SCENE_EXPLANATION)
    badge, level = Reporting.Verdict(empty_objs)
    lines += ['[scene: empty]', f'  header  = {Reporting.Screen_Header(empty_objs, CONST_BASELINE_BACKGROUND)}',
              f'  note    = {empty_note}', f'  verdict = {badge} ({level})']
    # Gemma's description of the rust-stained plate (Image_002 obj 1).
    one = [_Detection('rectangular metallic plate', (100, 120, 80, 80),
                      detail='The object is a rectangular metallic plate, appearing to be silver or a similar '
                             'bright metal, featuring two circular cutouts each containing a central green '
                             'element. The surface exhibits numerous fine, concentric scratches across the '
                             'entire body, and there are noticeable brown, earthy-toned stains or deposits '
                             'clustered in the upper section of the plate.')]
    one_objs, one_note = Reporting.Compose(one, CONST_FRAME_SIZE, caption='')
    badge, level = Reporting.Verdict(one_objs)
    lines += ['[scene: one object]', f'  header  = {Reporting.Screen_Header(one_objs, CONST_BASELINE_BACKGROUND)}',
              f'  object1 = {one_objs[0].Sentence}', f'  note    = {one_note!r}', f'  verdict = {badge} ({level})']
    # A plain object, one with a reading and a low score, and one with no description (Gemma's
    # descriptions of Image_001 obj 3 and obj 6).
    many = [_Detection('circular metallic washer', (10, 10, 50, 50),
                       detail='The object is a circular metallic washer or ring, appearing silver or bright in '
                              'color, with a central through-hole. The outer edge is clearly defined, and the '
                              'inner hole allows a view into the green surface beneath. The surface of the part '
                              'appears generally clean with no visible scratches, stains, or tarnish.'),
            _Detection('metallic bolt', (200, 50, 40, 90),
                       detail='The object is a metallic bolt or screw, appearing silver in color and likely made '
                              'of steel or a similar alloy. It features a cylindrical head and a threaded shaft '
                              'extending from it. The surface appears relatively clean, though there are some '
                              'minor streaks or slight variations in tone across the body.',
                       confidence=0.20, text='M6'),
            _Detection('nut', (300, 300, 60, 60), detail='')]
    many_objs, many_note = Reporting.Compose(many, CONST_FRAME_SIZE, caption='')
    badge, level = Reporting.Verdict(many_objs)
    lines += ['[scene: several objects]', f'  header  = {Reporting.Screen_Header(many_objs, CONST_BASELINE_BACKGROUND)}']
    lines += [f'  object{i} = {obj.Sentence}' for i, obj in enumerate(many_objs, start=1)]
    lines += [f'  note    = {many_note!r}', f'  verdict = {badge} ({level})', '']

    # 3\ The label distiller, on Gemma's own descriptions.
    lines.append('-- label distiller (Condense_Label) --')
    lines += [f'  {source:<16} -> {Condense_Label(caption)!r}' for source, caption in CONST_CAPTION_SAMPLES]
    lines.append('')

    # 4\ Background subtraction on the committed reference: nothing against itself, exactly the two
    #    drawn rectangles against a copy carrying them.
    synthetic = reference.copy()
    for x1, y1, x2, y2 in CONST_SYNTHETIC_RECTS:
        cv2.rectangle(synthetic, (x1, y1), (x2, y2), (0, 0, 0), thickness=-1)
    lines += ['-- segmentation --', f'reference shape = {reference.shape}',
              f'reference vs itself: {_Component_Count(reference, reference)} objects',
              f'reference vs two drawn rectangles: {_Component_Count(reference, synthetic)} objects', '']
    return lines


def test_reference_background_file_exists(reference_background_path: str) -> None:
    """
    Description:
        The committed reference background is present at the path the configuration names.
    """

    assert os.path.isfile(reference_background_path)


def test_reference_background_loads_at_expected_shape(reference_background, reference_shape) -> None:
    """
    Description:
        The reference loads as a BGR array at 1200x1920x3 — the size a --frame input must match,
        since segmentation differences the two.
    """

    assert reference_background.shape == reference_shape


def test_make_synthetic_frame_preserves_shape(reference_background, make_synthetic_frame) -> None:
    """
    Description:
        The synthetic-frame factory returns a same-size frame — the invariant that lets it be
        differenced against the reference without a size mismatch.
    """

    frame = make_synthetic_frame(reference_background, [(300, 300, 560, 560)])
    assert frame.shape == reference_background.shape
    assert not (frame == reference_background).all()


def test_characterization_matches_the_golden_file(reference_background, request) -> None:
    """
    Description:
        The snapshot equals the committed golden file, line for line. A difference is a behaviour
        change: the failure shows the diff; if the change is intended, rerun with --update-golden
        and review the file's diff before committing it.
    """

    lines = _Characterization(reference_background)
    if request.config.getoption('--update-golden'):
        os.makedirs(os.path.dirname(CONST_GOLDEN), exist_ok=True)
        with open(CONST_GOLDEN, 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(lines) + '\n')
        pytest.skip('golden file rewritten: %s — review its diff before committing' % CONST_GOLDEN)
    with open(CONST_GOLDEN, 'r', encoding='utf-8') as handle:
        golden = handle.read().splitlines()
    diff = list(difflib.unified_diff(golden, lines, 'characterization.txt (committed)', 'current', lineterm=''))
    assert not diff, 'Behaviour changed:\n' + '\n'.join(diff)
