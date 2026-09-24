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
# File Name: ../test/Reporting/test_core.py
## =========================================================================== ##

# System (Default)
import os
# Custom Lib.: AnyScan domain — data structures and report composer
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str
#   ../Reporting/Core
import Reporting.Core as Reporting

"""
Description:
    Tests for the report composer. This is the panel's one voice, so the sentences
    are pinned exactly. The composer is Qt-free and depends only on the data
    structures, so nothing here needs a camera or the model.
"""

# The frame size passed to the composer. Position is not part of any sentence, so
# only its being fixed matters.
CONST_SIZE = (1920, 1200)


def _Detection(label: str, detail: str = '', confidence=None, text=None) -> Detection_Str:
    """
    Description:
        Build a Detection_Str fixture with a fixed box.

    Args:
        (1) label [string]: The distilled label.
        (2) detail [string]: The raw caption.
        (3) confidence [float]: The score, or None.
        (4) text [string]: Any reading, or None.

    Returns:
        (1) parameter [Detection_Str(object)]: The fixture.
    """

    return Detection_Str(Label=label, Bbox=(0, 0, 10, 10), Detail=detail,
                         Confidence=confidence, Text=text)


def test_count_word() -> None:
    """
    Description:
        Numbers zero to ten are words; anything past ten falls back to digits.
    """

    assert Reporting.Count_Word(0) == 'no'
    assert Reporting.Count_Word(1) == 'one'
    assert Reporting.Count_Word(10) == 'ten'
    assert Reporting.Count_Word(11) == '11'


def test_verdict_levels() -> None:
    """
    Description:
        Empty is idle; unscored objects pass; a score under threshold degrades.
    """

    assert Reporting.Verdict([]) == ('Empty', 'idle')
    assert Reporting.Verdict([_Detection('a'), _Detection('b')]) == ('2 found', 'ok')
    assert Reporting.Verdict([_Detection('a', confidence=0.20)]) == ('Low confidence', 'warn')


def test_caption_sentence_strips_florence_leadins() -> None:
    """
    Description:
        The fixed Florence template prefix is peeled off and the sentence is
        cleaned into the panel's capitalisation and terminal stop.
    """

    assert Reporting.Caption_Sentence('In this image we can see a washer.') == 'A washer.'
    assert Reporting.Caption_Sentence('the image shows a close-up of a hex bolt') == \
        'A hex bolt.'


def test_describe_object_detail_reading_and_fallback() -> None:
    """
    Description:
        The full detail becomes the line; a reading is appended; an empty detail
        falls back to 'A <label>.'.
    """

    # The lead-in is peeled; nothing else is removed (there is no background strip).
    verbose = _Detection('hex bolt', detail='In this image we can see a hex bolt on a green surface.')
    assert Reporting.Describe_Object(verbose, CONST_SIZE) == 'A hex bolt on a green surface.'

    reading = _Detection('screw', detail='A close-up of a screw.', text='M6')
    assert Reporting.Describe_Object(reading, CONST_SIZE) == 'A screw, reading “M6”.'

    fallback = _Detection('nut', detail='')
    assert Reporting.Describe_Object(fallback, CONST_SIZE) == 'A nut.'


def test_compose_sets_sentence_and_never_reorders() -> None:
    """
    Description:
        Compose writes each object's Sentence and returns the objects in the same
        order (the index contract), plus the note and the audit.
    """

    objects = [_Detection('washer', detail='A metal washer.'),
               _Detection('nut', detail='')]
    returned, note, audit = Reporting.Compose(objects, CONST_SIZE)

    assert returned is objects
    assert objects[0].Sentence == 'A metal washer.'
    assert objects[1].Sentence == 'A nut.'
    assert note == ''
    assert audit == []                      # nothing substituted here


def test_scene_note_empty_scene_carries_caption_and_advice() -> None:
    """
    Description:
        With no objects the note is the empty-scene explanation followed by the
        next action.
    """

    note = Reporting.Scene_Note([], CONST_SIZE, caption=Reporting.CONST_EMPTY_SCENE_EXPLANATION)
    assert note == (Reporting.CONST_EMPTY_SCENE_EXPLANATION.rstrip('.') + '.'
                    + ' Check the lighting and the focus, then scan again.')


def test_module_is_qt_free() -> None:
    """
    Description:
        The composer imports no Qt — it is a reusable domain module.
    """

    source = open(Reporting.__file__).read()
    assert 'PyQt' not in source
    assert 'import cv2' not in source
    assert 'import torch' not in source


def test_a_sentence_naming_the_surface_is_kept_whole() -> None:
    """
    Description:
        There is no background strip: a sentence that mentions the green surface is part of the
        object's description and is kept word for word, with no audit record. This is the case
        the strip got wrong — Gemma's description of the red block's holes, which it deleted
        because the sentence named the surface showing through them.
    """

    holes = ('It features two circular holes, one near the top and one near the bottom, each '
             'appearing to have a passage allowing a view of a bright green surface through them.')
    det = _Detection('part', detail='The object is a rectangular, flat part. ' + holes)
    sentence, audit = Reporting.Object_Description(det)
    assert sentence.endswith(holes) and audit == []
    assert not hasattr(Reporting, 'Strip_Background')


def test_substitute_substance_word_boundaries() -> None:
    """
    Description:
        The impossible-substance guess is replaced with 'metal' at word boundaries
        only, and every substitution is recorded. A word merely containing the letters
        (plywood) is left alone.
    """

    out, records = Reporting.Substitute_Substance('A wooden block with a cardboard edge.')
    assert out == 'A metal block with a metal edge.'
    assert len(records) == 2 and all(level == 'info' for level, message in records)

    # No substring damage: 'plywood' contains 'wood' but is not the word 'wood'.
    out, records = Reporting.Substitute_Substance('The plywood sheet is thick.')
    assert out == 'The plywood sheet is thick.'
    assert records == []


def _Line(sentence: str, label: str = 'object') -> Detection_Str:
    """
    Description:
        A detection whose composed Sentence is preset, for the assembly tests.

    Args:
        (1) sentence [string]: The object's already-composed line.
        (2) label [string]: The label (unused by the assembler).

    Returns:
        (1) parameter [Detection_Str(object)]: The fixture.
    """

    det = _Detection(label)
    det.Sentence = sentence
    return det


def test_screen_understanding_assembly() -> None:
    """
    Description:
        The Screen-Understanding text states the background once on the first line
        with the object count, then one numbered line per object. Singular and plural
        read correctly, the count is len(objects) (never recomputed), the lines are
        numbered from 1, and the zero case reads 'no objects were detected on it'.
    """

    bg = 'The background is a plain green table.'

    # Zero objects: the count sentence, no object lines.
    assert Reporting.Screen_Understanding([], bg) == \
        'The background is a plain green table. No objects were detected on it.'

    # One object: singular verb and noun, one numbered line. The unscored fixture's label
    # carries the 'Confidence —' suffix, since every label keeps the same shape.
    one = Reporting.Screen_Understanding([_Line('A washer.')], bg)
    assert one == ('The background is a plain green table. There is 1 object on it, '
                   'described below.\n\nObject 1 · Confidence — - A washer.')

    # Several objects: plural, numbered from 1, in list order.
    several = Reporting.Screen_Understanding(
        [_Line('A washer.'), _Line('A bolt.'), _Line('A nut.')], bg)
    header, _, body = several.partition('\n\n')
    assert header.endswith('There are 3 objects on it, described below.')
    assert body == ('Object 1 · Confidence — - A washer.\nObject 2 · Confidence — - A bolt.'
                    '\nObject 3 · Confidence — - A nut.')

    # An empty background sentence falls back to the neutral string — never a headless
    # count line ('There is 1 object on it' with no background named).
    assert Reporting.Screen_Understanding([_Line('A washer.')], '') == \
        (Reporting.CONST_BACKGROUND_FALLBACK
         + ' There is 1 object on it, described below.\n\nObject 1 · Confidence — - A washer.')


def test_screen_understanding_is_built_from_the_shared_pieces() -> None:
    """
    Description:
        The file and the application panel share ONE source for the first line and the
        per-object lines: Screen_Understanding is exactly Screen_Header followed by the
        Object_Line of each object. The panel renders from the same two functions, so it
        cannot number or word an object differently from the file.
    """

    bg = 'The background is a plain green table.'
    objects = [_Line('A washer.'), _Line('A bolt.')]

    assert Reporting.Screen_Understanding(objects, bg) == (
        Reporting.Screen_Header(objects, bg) + '\n\n'
        + '\n'.join(Reporting.Object_Line(i, det) for i, det in enumerate(objects)))
    # The zero case is the header alone (no lines), and it names no object count as '0'.
    assert Reporting.Screen_Understanding([], bg) == Reporting.Screen_Header([], bg)
    assert Reporting.Object_Line(0, _Line('A washer.')) == 'Object 1 · Confidence — - A washer.'


def test_object_label_carries_the_confidence_suffix() -> None:
    """
    Description:
        The object label is the name and the object's OWN confidence, from one source:
        Object_Label is the bare name, Object_Confidence the score suffix (or '—' when the
        object carries no score), and Object_Label_Full joins them with the shared separator
        — the exact string Object_Line writes to the file and the panel renders in two
        weights. A scored object reads its rounded percentage; an unscored one keeps the
        field with an em dash so a missing score stays visible.
    """

    scored = _Detection('ring')
    scored.Segmenter_Score = 0.906
    unscored = _Detection('nut')                       # no Segmenter_Score

    assert Reporting.Object_Label(0) == 'Object 1'
    assert Reporting.Object_Confidence(scored) == 'Confidence 91%'   # rounded from 90.6%
    assert Reporting.Object_Confidence(unscored) == 'Confidence —'

    # The full label is the name and the suffix joined by the one shared separator.
    assert Reporting.Object_Label_Full(0, scored) == 'Object 1 · Confidence 91%'
    assert Reporting.Object_Label_Full(3, unscored) == 'Object 4 · Confidence —'

    # The file line is the full label (confidence included) joined to the sentence.
    scored.Sentence = 'A silver ring.'
    assert Reporting.Object_Line(0, scored) == 'Object 1 · Confidence 91% - A silver ring.'


def test_yolo_lines_are_normalised_and_indexed_from_the_object_list() -> None:
    """
    Description:
        Yolo_Lines emits one '<class_id> <xc> <yc> <w> <h>' line per object, geometry
        normalised 0..1 against the frame at six decimals, from the SAME ordered object
        list as the numbering — the class id is the object's 0-based index (object 1 in the
        text is id 0), a per-frame handle, not a class. It lists every object and nothing
        else.
    """

    # A 200x100 frame (width x height); a box at (x=20,y=10,w=40,h=20) has centre
    # (40,20) -> (0.2, 0.2) and size (0.2, 0.2).
    objects = [_Line('A ring.'), _Line('A nut.')]
    objects[0].Bbox = (20, 10, 40, 20)
    objects[1].Bbox = (100, 50, 20, 10)
    lines = Reporting.Yolo_Lines(objects, (200, 100))

    assert len(lines) == len(objects)
    assert lines[0] == '0 0.200000 0.200000 0.200000 0.200000'
    assert lines[1] == '1 0.550000 0.550000 0.100000 0.100000'
    # The ids run 0..n-1 in list order (object 1 -> id 0), matching the numbering.
    assert [line.split()[0] for line in lines] == ['0', '1']
    # Every value is normalised into 0..1.
    for line in lines:
        assert all(0.0 <= float(v) <= 1.0 for v in line.split()[1:])


def test_yolo_lines_empty_when_no_objects() -> None:
    """
    Description:
        No objects yields no lines — the file lists every detected object and nothing else.
    """

    assert Reporting.Yolo_Lines([], (200, 100)) == []


def test_background_sentence_validation() -> None:
    """
    Description:
        The global background sentence keeps a single short caption but rejects an
        empty, multi-sentence or over-long one for the fixed neutral fallback, with a
        warning — so a Florence ramble never becomes the first line of the output.
    """

    # A clean single sentence is kept as-is, no warning.
    kept, records = Reporting.Background_Sentence('a plain green surface')
    assert kept == 'A plain green surface.'
    assert records == []

    # A multi-sentence ramble falls back, with a warning.
    ramble = 'The image is a solid green color. The color is a shade of teal. It has no color.'
    kept, records = Reporting.Background_Sentence(ramble)
    assert kept == Reporting.CONST_BACKGROUND_FALLBACK
    assert any(level == 'warning' for level, message in records)

    # An over-long single sentence falls back too.
    long_one = 'a ' * 30 + 'surface'
    kept, records = Reporting.Background_Sentence(long_one)
    assert kept == Reporting.CONST_BACKGROUND_FALLBACK
    assert records and records[0][0] == 'warning'

    # An empty caption falls back.
    kept, records = Reporting.Background_Sentence('')
    assert kept == Reporting.CONST_BACKGROUND_FALLBACK
    assert records and records[0][0] == 'warning'
