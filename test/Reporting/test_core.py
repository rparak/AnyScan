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

# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — data structures and report composer
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str
#   ../Reporting/Core
import Reporting.Core as Reporting

#   ../Parameters/Configuration — the background-sentence limits (their documented defaults)
from Parameters.Configuration import Description_Parameters_Str
"""
Description:
    Tests for the report composer. This is the panel's one voice, so the sentences
    are pinned exactly. The composer is Qt-free and depends only on the data
    structures, so nothing here needs a camera or the model.
"""



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


def test_verdict_levels() -> None:
    """
    Description:
        Empty is idle; unscored objects pass; a score under threshold degrades.
    """

    assert Reporting.Verdict([]) == ('Empty', 'idle')
    assert Reporting.Verdict([_Detection('a'), _Detection('b')]) == ('2 found', 'ok')
    assert Reporting.Verdict([_Detection('a', confidence=0.20)]) == ('Low confidence', 'warn')


def test_the_description_is_kept_as_written_and_only_tidied() -> None:
    """
    Description:
        No caption-template lead-in is peeled any more (they were Florence-2's phrasing; Gemma
        never writes them): the description is the model's own sentence, only tidied into the
        panel's capitalisation and terminal stop.
    """

    det = _Detection('ring', detail='  the object is a circular ring  ')
    assert Reporting.Object_Description(det) == 'The object is a circular ring.'
    assert not hasattr(Reporting, 'Caption_Sentence') and not hasattr(Reporting, 'CONST_LABEL_LEADINS')


def test_object_description_detail_reading_and_fallback() -> None:
    """
    Description:
        The full detail becomes the line; a reading is appended; an empty detail
        falls back to 'A <label>.'.
    """

    # Nothing is removed from the description (there is no background strip).
    verbose = _Detection('hex bolt', detail='The object is a hex bolt on a green surface.')
    assert Reporting.Object_Description(verbose) == 'The object is a hex bolt on a green surface.'

    reading = _Detection('screw', detail='The object is a screw.', text='M6')
    assert Reporting.Object_Description(reading) == 'The object is a screw, reading “M6”.'

    fallback = _Detection('nut', detail='')
    assert Reporting.Object_Description(fallback) == 'A nut.'


def test_compose_sets_sentence_and_never_reorders() -> None:
    """
    Description:
        Compose writes each object's Sentence and returns the objects in the same
        order (the index contract), plus the note.
    """

    objects = [_Detection('washer', detail='A metal washer.'),
               _Detection('nut', detail='')]
    returned, note = Reporting.Compose(objects)

    assert returned is objects
    assert objects[0].Sentence == 'A metal washer.'
    assert objects[1].Sentence == 'A nut.'
    assert note == ''


def test_scene_note_empty_scene_carries_caption_and_advice() -> None:
    """
    Description:
        With no objects the note is the empty-scene explanation followed by the
        next action.
    """

    note = Reporting.Scene_Note([], caption=Reporting.CONST_EMPTY_SCENE_EXPLANATION)
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
        object's description and is kept word for word. This is the case
        the strip got wrong — Gemma's description of the red block's holes, which it deleted
        because the sentence named the surface showing through them.
    """

    holes = ('It features two circular holes, one near the top and one near the bottom, each '
             'appearing to have a passage allowing a view of a bright green surface through them.')
    det = _Detection('part', detail='The object is a rectangular, flat part. ' + holes)
    assert Reporting.Object_Description(det).endswith(holes)
    assert not hasattr(Reporting, 'Strip_Background')


def test_the_models_words_are_not_rewritten() -> None:
    """
    Description:
        There is no substance substitution any more (it corrected Florence reading machined metal
        as wood; Gemma reads the machining marks correctly and it never fired): a description
        that names a material is kept as the model wrote it.
    """

    det = _Detection('block', detail='A wooden block with a cardboard edge.')
    assert Reporting.Object_Description(det) == 'A wooden block with a cardboard edge.'
    assert not hasattr(Reporting, 'Substitute_Substance')

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

    # The exact text, not a re-assembly of the same helpers: a drift in any shared piece shows here.
    assert Reporting.Screen_Understanding(objects, bg) == (
        'The background is a plain green table. There are 2 objects on it, described below.\n'
        '\n'
        'Object 1 · Confidence — - A washer.\n'
        'Object 2 · Confidence — - A bolt.')
    # And it IS the shared pieces: the header, a blank line, one Object_Line per object.
    assert Reporting.Screen_Understanding(objects, bg).split('\n') == (
        [Reporting.Screen_Header(objects, bg), ''] + [Reporting.Object_Line(i, det) for i, det in enumerate(objects)])
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
        warning — so a rambling model answer never becomes the first line of the output.
    """

    # A clean single sentence is kept as-is, no warning.
    kept, records = Reporting.Background_Sentence('a plain green surface', Description_Parameters_Str=Description_Parameters_Str())
    assert kept == 'A plain green surface.'
    assert records == []

    # A multi-sentence ramble falls back, with a warning.
    ramble = 'The image is a solid green color. The color is a shade of teal. It has no color.'
    kept, records = Reporting.Background_Sentence(ramble, Description_Parameters_Str=Description_Parameters_Str())
    assert kept == Reporting.CONST_BACKGROUND_FALLBACK
    assert any(level == 'warning' for level, message in records)

    # An over-long single sentence falls back too.
    long_one = 'a ' * 30 + 'surface'
    kept, records = Reporting.Background_Sentence(long_one, Description_Parameters_Str=Description_Parameters_Str())
    assert kept == Reporting.CONST_BACKGROUND_FALLBACK
    assert records and records[0][0] == 'warning'

    # An empty caption falls back.
    kept, records = Reporting.Background_Sentence('', Description_Parameters_Str=Description_Parameters_Str())
    assert kept == Reporting.CONST_BACKGROUND_FALLBACK
    assert records and records[0][0] == 'warning'


def test_the_frame_confidence_is_the_mean_of_the_scored_objects_only() -> None:
    """
    Description:
        The frame's confidence is the mean of the scored objects' own scores, rounded to a whole
        percent, over how many were scored: an unscored object (found by the background cue alone)
        is left out, not counted as 0%, and a frame with none scored has no mean at all.
    """

    def _Scored(score):
        return Detection_Str(Label='p', Bbox=(0, 0, 4, 4), Segmenter_Score=score)

    assert Reporting.Frame_Confidence([_Scored(0.91), _Scored(0.844), _Scored(None)]) == (88, 2)
    assert Reporting.Frame_Confidence([_Scored(None), _Scored(None)]) == (None, 0)
    assert Reporting.Frame_Confidence([]) == (None, 0)


def _Judged(verdict: str, similarity: float = 0.94, distance: float = 30.0,
            checks: tp.Optional[tp.List[tp.Any]] = None, area: float = 1.0) -> Detection_Str:
    """An object as a catalogue mode leaves it: a verdict, its evidence and its dimension checks."""
    from Parameters.Vision import Catalogue_Result_Str
    from Vision.Utilities.Dimensions import Check_Dimension
    return Detection_Str(Label='plate', Bbox=(0, 0, 1, 1), Verdict=verdict, Sentence='A plate.',
                         Dimension_Checks=checks if checks is not None else [Check_Dimension('length', 60.2, 60.0, 1.5),
                                                                             Check_Dimension('width', 40.1, 40.0, 1.5)],
                         Catalogue=Catalogue_Result_Str(Similarity=similarity, Side='front', Identify_Similarity=0.75,
                                                        Area_Ratio=area, Unspecified_Area_Ratio=1.7,
                                                        Center_Distance_Mm=distance, Verified_Radius_Mm=74.3))


def test_each_state_reads_as_the_owner_specified() -> None:
    """
    Description:
        Scene Understanding shows the state and, when it is not OK, why — never the similarity, which is in the
        log only: OK is 'State: OK.' alone; a Warning is 'State: Warning.' and 'Reason: The object should not be
        on the surface.'; an Unspecified object says why it could not be judged and what to do.
    """

    from Reporting.Core import Verdict_Lines
    assert Verdict_Lines(_Judged('OK')) == ['State: OK.']
    assert Verdict_Lines(_Judged('Warning', similarity=0.31)) == ['State: Warning.',
                                                                  'Reason: The object should not be on the surface.']
    assert Verdict_Lines(_Judged('Unspecified', area=2.04)) == [
        'State: Unspecified.',
        "Reason: Its area is 2.04 times the part's, probably several parts together, so it cannot be judged. "
        'Separate them and scan again.']
    for verdict in ('OK', 'NOK', 'Warning', 'Unspecified'):
        assert not [line for line in Verdict_Lines(_Judged(verdict)) if 'similarity' in line.lower()], verdict


def test_a_nok_gives_each_reason_with_measured_and_expected_values() -> None:
    """
    Description:
        Every reason a part is NOK has its own 'Reason:' line: a dimension out of tolerance with its measured
        value, nominal and tolerance; the part's outline without its look; an outline that could not be
        measured. A passing dimension is not listed.
    """

    from Reporting.Core import Verdict_Lines
    from Vision.Utilities.Dimensions import Check_Dimension
    long = [Check_Dimension('length', 62.04, 60.0, 1.5), Check_Dimension('width', 40.1, 40.0, 1.5)]
    assert Verdict_Lines(_Judged('NOK', checks=long)) == [
        'State: NOK.', 'Reason: The length is 62.04 mm, expected 60.00 ± 1.50 mm.']
    assert Verdict_Lines(_Judged('NOK', similarity=0.58)) == [
        'State: NOK.', "Reason: It has the part's outline but does not look like the part."]
    assert Verdict_Lines(_Judged('NOK', checks=[]))[1:] == ['Reason: Its outline could not be measured.']


@pytest.mark.parametrize('verdict', ['OK', 'NOK'])
def test_a_size_checked_outside_the_verified_zone_says_so(verdict: str) -> None:
    """
    Description:
        A part judged on its size beyond the radius the size checks were verified to carries a note giving its
        distance and the radius — the verdict stands (a NOK stays NOK), the note explains it. Inside the
        radius, and on an object not judged by size, there is no note.
    """

    from Reporting.Core import Verdict_Lines
    note = 'Note: The size check is not verified here: 82 mm from the frame centre, verified to 74 mm.'
    lines = Verdict_Lines(_Judged(verdict, distance=82.2))
    assert lines[0] == 'State: %s.' % verdict and lines[-1] == note
    unverified = 'Note: The size check is not verified here'
    assert not [line for line in Verdict_Lines(_Judged(verdict, distance=74.3)) if line.startswith(unverified)]
    assert not [line for line in Verdict_Lines(_Judged('Warning', distance=82.2)) if line.startswith(unverified)]


def test_the_verdict_reaches_the_file_and_the_log_keeps_the_similarity() -> None:
    """
    Description:
        The Screen Understanding file's object line carries the verdict lines, indented, under the object. The
        log carries the verdict on one line with what Scene Understanding leaves out — the side of a judged
        part and the similarity of every object — at WARNING for a Warning or an Unspecified object and at
        INFO for OK and NOK. Outside a catalogue mode the object line is exactly what it was.
    """

    from Reporting.Core import Object_Line, Verdict_Log_Line
    line = Object_Line(0, _Judged('NOK', similarity=0.58))
    assert line.split('\n')[1:] == ['    State: NOK.',
                                    "    Reason: It has the part's outline but does not look like the part."]
    plain = Detection_Str(Label='plate', Bbox=(0, 0, 1, 1), Sentence='A plate.')
    assert Object_Line(0, plain) == 'Object 1 · Confidence — - A plate.'
    assert Verdict_Log_Line(1, _Judged('Warning', similarity=0.31)) == (
        'WARNING', 'Object 2: Warning, similarity 0.31. Reason: The object should not be on the surface.')
    assert Verdict_Log_Line(0, _Judged('NOK', similarity=0.58, distance=82.2)) == (
        'INFO', "Object 1: NOK, front up, similarity 0.58. Reason: It has the part's outline but does not look like "
                'the part. Note: The size check is not verified here: 82 mm from the frame centre, verified to 74 mm.')
    assert Verdict_Log_Line(0, _Judged('OK')) == ('INFO', 'Object 1: OK, front up, similarity 0.94.')
    assert Verdict_Log_Line(0, _Judged('Unspecified', area=2.0))[0] == 'WARNING'


@pytest.mark.parametrize('verdicts, badge', [
    (['OK', 'OK'], ('All OK · 2', 'ok')),
    (['OK', 'Warning', 'Warning'], ('Foreign object · 2', 'warn')),
    (['OK', 'Warning', 'Unspecified'], ('Not judged · 1', 'warn')),
    (['OK', 'NOK', 'Unspecified', 'Warning', 'NOK'], ('NOK · 2 of 5', 'fail')),
], ids=['all ok', 'warning', 'unspecified over warning', 'nok over all'])
def test_the_badge_states_the_worst_verdict(verdicts: tp.List[str], badge: tp.Tuple[str, str]) -> None:
    """
    Description:
        In a catalogue mode the badge is never green while anything on the surface is not OK: any NOK (the
        'fail' level), else any Unspecified, else any Warning (both 'warn'), else all OK ('ok') — each in words
        as well as colour. Outside a catalogue mode it still counts what was found.
    """

    from Reporting.Core import Verdict
    assert Verdict([_Judged(verdict) for verdict in verdicts]) == badge
    assert Verdict([Detection_Str(Label='plate', Bbox=(0, 0, 1, 1))] * 3) == ('3 found', 'ok')


def test_a_judged_part_says_which_side_is_up_in_the_catalogues_words() -> None:
    """
    Description:
        An OK or NOK part's description gains one sentence naming the side DINOv2 matched, in the catalogue's
        words for it; a Warning (not the part) and an Unspecified object (several) gain none, and neither does
        an object outside a catalogue mode.
    """

    from Reporting.Core import Side_Sentence
    for verdict in ('OK', 'NOK'):
        det = _Judged(verdict)
        det.Catalogue.Side_Name = 'machined front'
        assert Side_Sentence(det) == 'It lies with its machined front up.'
    for verdict in ('Warning', 'Unspecified'):
        det = _Judged(verdict)
        det.Catalogue.Side_Name = 'machined front'
        assert Side_Sentence(det) == ''
    assert Side_Sentence(Detection_Str(Label='plate', Bbox=(0, 0, 1, 1))) == ''


def test_a_nok_names_its_missing_extra_and_wrong_holes() -> None:
    """
    Description:
        A part NOK for its holes says so, one 'Reason:' per finding: each group short of its count ('3 of 4
        corner holes found.') or over it ('3 through-holes found, expected 2.'), and each hole out of tolerance
        with its measured and expected values; the log line carries the same reasons.
    """

    from Reporting.Core import Verdict_Lines, Verdict_Log_Line
    from Parameters.Vision import Hole_Count_Str
    from Vision.Utilities.Dimensions import Check_Dimension
    det = _Judged('NOK')
    det.Hole_Counts = [Hole_Count_Str(Name='corner hole', Found=3, Expected=4),
                       Hole_Count_Str(Name='through-hole', Found=3, Expected=2),
                       Hole_Count_Str(Name='countersink', Found=2, Expected=2)]
    det.Hole_Checks = [Check_Dimension('corner hole Ø', 4.1, 2.459, 1.0), Check_Dimension('corner hole Ø', 2.8, 2.459, 1.0)]
    assert Verdict_Lines(det) == ['State: NOK.', 'Reason: 3 of 4 corner holes found.',
                                  'Reason: 3 through-holes found, expected 2.',
                                  'Reason: The corner hole Ø is 4.10 mm, expected 2.46 ± 1.00 mm.']
    assert Verdict_Log_Line(0, det)[1].endswith('Reason: 3 of 4 corner holes found. Reason: 3 through-holes found, '
                                                'expected 2. Reason: The corner hole Ø is 4.10 mm, expected 2.46 ± 1.00 mm.')


def _Logo(missing: tp.Tuple[int, ...] = (), registered: bool = True) -> tp.Any:
    """A logo result on the labyrinth's back: the letters at the given places missing, or no inscription."""
    from Parameters.Vision import Logo_Result_Str, Logo_Letter_Str
    if not registered:
        return Logo_Result_Str(Reference='', Matches=4)
    words = ['JIC'] * 3 + ['SMART'] * 5 + ['FACTORY'] * 7
    return Logo_Result_Str(Reference='back', Matches=150, Letters=[
        Logo_Letter_Str(Word=word, Letter=letter, Similarity=0.2 if i in missing else 0.9, Contrast=5.0,
                        Present=i not in missing) for i, (word, letter) in enumerate(zip(words, 'JICSMARTFACTORY'))])


def test_a_nok_names_its_stains_and_its_missing_letters() -> None:
    """
    Description:
        A part NOK for a stain says how big, on which side: one stain by its area, several by their count, the
        largest and the total. A part NOK for its inscription names each missing letter with its word, or says
        no inscription was found on the side.
    """

    from Reporting.Core import Verdict_Reasons
    from Parameters.Vision import Stain_Str
    det = _Judged('NOK')
    det.Catalogue.Side_Name = 'machined front'
    det.Stains = [Stain_Str(Area_Mm2=152.224)]
    assert Verdict_Reasons(det) == ['A stain of 152.22 mm² on the machined front.']
    det.Stains = [Stain_Str(Area_Mm2=152.224), Stain_Str(Area_Mm2=30.0), Stain_Str(Area_Mm2=1.3)]
    assert Verdict_Reasons(det) == ['3 stains on the machined front, the largest 152.22 mm², 183.52 mm² in all.']
    det = _Judged('NOK')
    det.Catalogue.Side_Name = 'logo side'
    det.Logo = _Logo(missing=(1, 13))
    assert Verdict_Reasons(det) == ['The letter I of JIC is missing.', 'The letter R of FACTORY is missing.']
    det.Logo = _Logo(registered=False)
    assert Verdict_Reasons(det) == ['No inscription found on the logo side.']
    det.Logo = _Logo()
    assert Verdict_Reasons(det) == []


def test_the_findings_say_what_the_checks_found_in_words_without_numbers() -> None:
    """
    Description:
        What the describer is told of a judged part: one sentence per check that ran, in words and without a digit
        — stains found or none, the inscription complete, incomplete with its missing letters, or absent, a hole
        group short or over, an outline out of tolerance — and nothing for a Warning or an Unspecified object.
    """

    from Reporting.Core import Findings
    from Parameters.Vision import Stain_Str, Hole_Count_Str
    from Vision.Utilities.Dimensions import Check_Dimension
    det = _Judged('NOK', checks=[Check_Dimension('length', 63.2, 60.0, 1.5)])
    det.Catalogue.Side_Name = 'machined front'
    det.Stains = [Stain_Str(Area_Mm2=152.2)]
    det.Hole_Counts = [Hole_Count_Str(Name='countersink', Found=1, Expected=2),
                       Hole_Count_Str(Name='through-hole', Found=3, Expected=2)]
    assert Findings(det) == ('An automatic check found yellow-brown stains on its machined front; describe them and '
                             'where they are. An automatic check found fewer countersinks than the part has. An '
                             'automatic check found more through-holes than the part has. An automatic check found '
                             'its outline out of tolerance.')
    det = _Judged('OK')
    det.Catalogue.Side_Name = 'logo side'
    det.Stains, det.Logo = [], _Logo()
    assert Findings(det) == ('An automatic check found no stain on its logo side. An automatic check found the '
                             'inscription complete.')
    det.Logo = _Logo(missing=(4,))
    assert Findings(det).endswith('found the inscription incomplete: the letter M of SMART is missing; describe the '
                                  'inscription as you see it.')
    det.Logo = _Logo(registered=False)
    assert Findings(det).endswith('An automatic check found no inscription on its logo side.')
    assert not any(character.isdigit() for character in Findings(det))
    for verdict in ('Warning', 'Unspecified'):
        assert Findings(_Judged(verdict)) == ''


def test_the_describer_prompt_is_the_items_filled_for_the_part() -> None:
    """
    Description:
        A judged part's prompt is the item's Describer.Prompt with its side's name and description, that side's
        defects only (what they look like and what is not one) and the findings; no placeholder is left and no
        digit is in it. A Warning, an Unspecified object or an item without a prompt gets '' (the mode's prompt).
    """

    import dataclasses
    from Reporting.Core import Describer_Prompt
    from Parameters.Catalogue import Catalogue_Item_Str, Catalogue_Side_Str, Catalogue_Defect_Str
    item = Catalogue_Item_Str(
        Sides=[Catalogue_Side_Str(Side='front', Name='machined front', Description='Shiny milled metal.'),
               Catalogue_Side_Str(Side='back', Name='unmachined back', Description='Dark matte metal.')],
        Defects=[Catalogue_Defect_Str(Name='fingerprint', Side='front', Looks_Like='Yellow-brown stains.',
                                      Not_A_Defect='Small dark dots.'),
                 Catalogue_Defect_Str(Name='dent', Side='back', Looks_Like='A dent.')],
        Describer_Prompt='Its {side} is up: {side_description} Defects: {defects} {findings} Describe it.')
    det = _Judged('NOK')
    det.Catalogue.Side_Name = 'machined front'
    det.Stains = []
    assert Describer_Prompt(det, item) == ('Its machined front is up: Shiny milled metal. Defects: Fingerprint: '
                                           'Yellow-brown stains. Not a defect: Small dark dots. An automatic check '
                                           'found no stain on its machined front. Describe it.')
    for verdict in ('Warning', 'Unspecified'):
        assert Describer_Prompt(_Judged(verdict), item) == ''
    assert Describer_Prompt(det, dataclasses.replace(item, Describer_Prompt='')) == ''


@pytest.mark.parametrize('sentence, stains, logo, holes, dropped', [
    # Gemma's own sentences (E4B, prompt C, the test set, 2026-10-11), and their cases.
    ('Two holes of 12 mm sit near one edge.', None, None, None, True),
    ('The surface appears clean of any staining or significant marks.', [], None, None, False),
    ('The surface appears clean of any staining or significant marks.', [1.0], None, None, True),
    ('A noticeable yellow-brown stain is present on the lower right section.', [1.0], None, None, False),
    ('A noticeable yellow-brown stain is present on the lower right section.', [], None, None, True),
    ('The surface appears clean, with no visible stains or defects on the machined front.', [1.0], None, None, True),
    ('The plate has four small blind holes in each corner.', None, None, (3, 4), True),
    ('Four small blind holes are present, one near each corner.', None, None, (0, 4), True),
    ('Four small blind holes are present, one near each corner.', None, None, (4, 4), False),
    ('There are four corner holes.', None, None, (3, 4), True),
    ('Small blind holes are present in each corner.', None, None, (0, 4), True),
    ('Small blind holes are present in each corner.', None, None, (4, 4), False),
    ('It features an engraved JIC Smart Factory logo on one side, though an automatic check found no inscription '
     'on this side.', None, 'none', None, True),
    ('The inscription is present and complete, with no missing letters or inscriptions.', None, 'complete', None, False),
    ('The inscription is present and complete, with no missing letters or inscriptions.', None, 'one missing', None, True),
    ('The inscription is present, though it appears to be missing several letters.', None, 'one missing', None, False),
    ('The inscription is present, though it appears to be missing several letters.', None, 'complete', None, True),
], ids=['a number', 'clean, none found', 'clean, a stain found', 'a stain, one found', 'a stain, none found',
        'no stains, one found', 'four holes, three found', 'four holes, none found', 'four holes, all found',
        'a count alone', 'each corner, none found', 'each corner, all found', 'a logo, none found', 'complete, complete',
        'complete, a letter missing', 'letters missing, so they are', 'letters missing, none are'])
def test_the_guard_drops_numbers_and_what_contradicts_a_check(sentence: str, stains: tp.Any, logo: tp.Any,
                                                              holes: tp.Any, dropped: bool) -> None:
    """
    Description:
        The describer only confirms and describes: a sentence with a number is dropped, and so is one
        contradicting a check that ran — a stain claimed on a clean side or a clean side claimed when a stain was
        found ('clean of', 'no' negate the stain), all the holes claimed by a count when the check found fewer, an
        inscription affirmed where none was found, complete letters claimed when one is missing or missing ones
        when all are there. A sentence agreeing with the checks is kept, word for word.
    """

    from Reporting.Core import Guard_Description
    from Parameters.Vision import Stain_Str, Hole_Count_Str
    det = _Judged('NOK')
    det.Stains = [Stain_Str(Area_Mm2=area) for area in stains] if stains is not None else None
    det.Logo = {'none': _Logo(registered=False), 'complete': _Logo(), 'one missing': _Logo(missing=(4,)),
                None: None}[logo]
    det.Hole_Counts = [Hole_Count_Str(Name='corner hole', Found=holes[0], Expected=holes[1])] if holes else []
    kept, drops = Guard_Description('The part is a square metal plate. ' + sentence, det)
    assert kept == 'The part is a square metal plate.' + ('' if dropped else ' ' + sentence)
    assert [text for text, _why in drops] == ([sentence] if dropped else [])
