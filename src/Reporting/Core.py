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
# File Name: ../Reporting/Core.py
## =========================================================================== ##

# System (Default)
import re
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — data structures
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Dimension_Check_Str
#   ../Parameters/Configuration
from Parameters.Configuration import Description_Parameters_Str

"""
Description:
    Initialization of constants.

    The panel on the right is the product. Every sentence the operator reads is
    written in this module and nowhere else, so the console keeps one voice
    whichever backend produced the data. This module is Qt-free and depends only
    on the Parameters data structures; it never imports torch, OpenCV or a model.

    House style: plain declarative sentences, present tense, no hedging adverbs,
    no self-reference, and an empty result is a statement with a next action rather
    than an apology.
"""

# The middot that joins an object's name and its confidence in the label ('Object 1 ·
# Confidence 91%'). One definition, so the panel (which renders the two parts in different
# weights) and the descriptions file (which writes the label as one string) put the SAME
# separator between them and cannot drift.
CONST_LABEL_SEPARATOR = ' · '

# What the confidence suffix shows when an object carries no score — the background cue
# found it, so FastSAM emitted none. The field is kept rather than omitted so every
# object's label reads the same shape and a missing score stays visible. It is the panel's
# em dash, defined here (not imported from the Qt style) so this module stays Qt-free.
CONST_NO_CONFIDENCE = '—'

# What the panel says when the model finds nothing. It names both honest
# possibilities; Scene_Note supplies the next action ('Check the lighting and the
# focus, then scan again.'), so this is only the explanation and carries no
# trailing full stop of its own.
CONST_EMPTY_SCENE_EXPLANATION = (
    'Either nothing is on the surface, or the model did not recognise what is there'
)

# The describer's own sentence openers, peeled for the LABEL only: Gemma begins every
# description "The object is a …" (all 15 objects of the previous test set, eb00508^); unpeeled,
# the distiller cut at ' is ' and every label read 'object'. (Florence-2's caption template
# lead-ins — "In this image we can see …" — were peeled here too until Florence was removed;
# Gemma never writes them.)
# They are not peeled from the object LINE, which keeps the model's full sentence. The article
# is left in place for the distiller's own article strip; longest first.
#   Unit [Tuple<string>]
CONST_LABEL_OPENERS = (
    "the object appears to be", "the part appears to be", "the item appears to be",
    "the object is shaped like", "the part is shaped like", "the object consists of", "the part consists of",
    "the object is", "this object is", "the part is", "this part is",
    "the item is", "this item is", "the component is", "this component is", "this is", "it is",
)

# The label is the noun phrase UP TO ITS HEAD NOUN, which in English comes last in the phrase:
# 'a rectangular, flat plate of bright metal' -> 'rectangular flat plate'. So a comma does NOT end
# the phrase by itself — it usually separates adjectives in front of the noun. It ends the phrase
# only when the next word opens a new clause: an '-ing' participle ('ring, appearing …') or one of
# these hedging adverbs ('plate, likely steel'). (Florence rarely listed adjectives with commas,
# so cutting at every comma used to work; on Gemma's phrasing it left 8 of 15 labels a lone
# adjective.)
#   Unit [Tuple<string>]
CONST_LABEL_HEDGES = ('likely', 'possibly', 'probably', 'perhaps', 'apparently', 'presumably')

# The clause boundaries the label distiller cuts the joined phrase at. ' of ' ends it ('plate of
# bright metal'), and so does a bare ' in ' or a participle that follows the noun ('piece rendered in
# vibrant blues', 'arrow pointing to the right'); commas are handled by the rule above. ' or ' is
# kept: 'washer or cap' stays 'washer or cap', the model's own hedge, which the label must not turn
# into certainty (docs/design-decisions.md, "The object label keeps the model's alternatives").
#   Unit [Tuple<string>]
CONST_LABEL_BOUNDARIES = (
    " is ", " are ", " was ", " with ", " that ", " which ", " has ",
    " have ", " sitting", " lying", " laying", " placed", " resting",
    " standing", " scattered", " showing", " appears", " against ", " next to",
    " on top", " on a ", " on an ", " on the ", " in the ", " in a ", " in an ",
    " across ", " and ", " of ", " in ", " rendered", " pointing", " appearing", " featuring",
)

# The most words the distilled label keeps — the LAST ones, where the head noun is — and the
# extra words it keeps for an alternative ('or <noun>'), so the hedge survives the cap.
CONST_LABEL_MAX_WORDS = 4
CONST_LABEL_ALTERNATIVE_WORDS = 2

# ---- No background strip -------------------------------------------------------- #
# Object descriptions are NOT stripped of the background any more. The strip existed because
# Florence-2 wrote sentences about the table into object captions; the Gemma describer is told
# to describe only the part and writes none. On Gemma's text the strip's only effect was harmful:
# it deleted "…a passage allowing a view of a bright green surface through them" — the red
# block's description of its own holes — because the sentence named the green surface. It was
# removed rather than retuned (docs/design-decisions.md). The background is stated once,
# globally, by the describer's background prompt (Screen_Header).

# ---- The global background sentence -------------------------------------------- #
# The background is described once, from the reference, by the describer's background
# prompt (one short sentence naming the surface). A model can still misfire, so a
# sentence that is empty or runs past the configured limits (Description.Background_Max_Words,
# Description.Background_Max_Sentences) is rejected for this fixed neutral string rather than
# written into the file as a ramble.
CONST_BACKGROUND_FALLBACK = 'The background is a plain surface.'

# ---- Displayed size precision ---------------------------------------------------- #
# The decimal places a size is SHOWN to ('24.31 × 18.70 mm') — a display choice, applied here and
# only here (Object_Size); the measurement, the stored record and every comparison keep the full
# float. It is fixed, not derived from the scale: the old derivation (one pixel's size,
# floor(-log10(mm/px))) silently dropped from 0.1 mm to whole millimetres when the recalibration
# moved the factor from 0.098 to 0.102 mm/px. The second digit is BELOW one pixel (~0.1 mm) at the
# current factor, and a size already carries a position-dependent error of up to ~1.5 mm near the
# frame edge (README > Limitations): two decimals are not improved resolution — do not read them as
# such, and do not revert them to a scale-derived count (docs/design-decisions.md).
#   Unit [int]
CONST_SIZE_DECIMALS = 2


def Zone(bbox: tp.Tuple[int, int, int, int], size: tp.Tuple[int, int]) -> str:
    """
    Description:
        A coarse nine-cell position, the way a person would describe it.

        Note:
            Currently unused: object lines were changed to say what a part is, not
            where it is (the number on the coloured box carries position). Kept for
            the day a position phrase is wanted back — re-add it in Object_Description.

    Args:
        (1) bbox [Vector<int> 1x4]: The box as (x, y, w, h) in frame pixels.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).

    Returns:
        (1) parameter [string]: A phrase naming the region of the frame.
    """

    width, height = size
    cx = (bbox[0] + bbox[2] / 2) / max(width, 1)
    cy = (bbox[1] + bbox[3] / 2) / max(height, 1)
    row = 'upper' if cy < 0.34 else ('lower' if cy > 0.66 else 'middle')
    col = 'left' if cx < 0.34 else ('right' if cx > 0.66 else 'centre')
    if row == 'middle' and col == 'centre':
        return 'the centre of the frame'
    if col == 'centre':
        return 'the %s centre of the frame' % row
    return 'the %s %s of the frame' % (row, col)


def Clean_Detail(text: str) -> str:
    """
    Description:
        Tidy the model's caption into the object's line. The composer,
        not the model, owns punctuation and capitalisation, so the raw string is
        normalised here: surrounding whitespace gone, first letter of every
        sentence capitalised, exactly one terminal full stop.

    Args:
        (1) text [string]: The raw caption text.

    Returns:
        (1) parameter [string]: The cleaned sentence, or an empty string.
    """

    text = ' '.join(text.split()).strip()
    if not text:
        return ''
    # Capitalise the first letter of every sentence, not only the first.
    out, at_start = [], True
    for ch in text:
        if at_start and ch.isalpha():
            ch = ch.upper()
            at_start = False
        out.append(ch)
        if ch in '.!?':
            at_start = True
    text = ''.join(out)
    return text if text[-1] in '.!?' else text + '.'


def Object_Description(det: Detection_Str) -> str:
    """
    Description:
        The object's line: the model's description, put into the panel's capitalisation
        and terminal stop (Clean_Detail). Nothing is
        rewritten or removed — the describer is asked to describe only the part. When no
        usable description remains, the short 'A <label>.' stands in; a reading, if any, is
        appended.

    Args:
        (1) det [Detection_Str(object)]: The detection to describe.

    Returns:
        (1) parameter [string]: The object's line.
    """

    sentence = Clean_Detail(det.Detail)
    if not sentence:
        article = 'An' if det.Label[:1].lower() in 'aeiou' else 'A'
        sentence = '%s %s.' % (article, det.Label)
    if det.Text:
        sentence = sentence.rstrip('.') + ', reading “%s”.' % det.Text
    return sentence


def Background_Sentence(caption: str, *,
                        Description_Parameters_Str: Description_Parameters_Str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        The one global background sentence, from the reference caption. The background
        prompt asks for a single short sentence; a caption that is empty, has more sentences
        than Background_Max_Sentences, or more words than Background_Max_Words is rejected
        for the fixed neutral CONST_BACKGROUND_FALLBACK and a warning is recorded,
        rather than writing a paragraph of confabulation as the first line.

    Args:
        (1) caption [string]: The reference frame's raw caption.
        (2) Description_Parameters_Str [Description_Parameters_Str(object)]: REQUIRED,
            keyword-only: the configured Background_Max_Words and Background_Max_Sentences.

    Returns:
        (1) parameter [Tuple]: (the background sentence, a Vector of (level, message)
                               audit records — a single warning when the fallback is used).
    """

    sentence = Clean_Detail(caption)
    words = len(sentence.split())
    count = len([part for part in re.split(r'[.!?]+', sentence) if part.strip()])
    if ((not sentence) or count > Description_Parameters_Str.Background_Max_Sentences
            or words > Description_Parameters_Str.Background_Max_Words):
        return CONST_BACKGROUND_FALLBACK, [('warning',
                "background caption unusable (%d words, %d sentence(s)); used the neutral "
                "fallback instead of: '%s'" % (words, count, ' '.join(caption.split())))]
    return sentence, []


def Scene_Note(objects: tp.List[Detection_Str], caption: str = '') -> str:
    """
    Description:
        The closing note. It carries the empty-scene explanation and its next
        action, and otherwise stays silent so the panel is just the objects.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.
        (2) caption [string]: An optional leading explanation (e.g. the empty-scene text).

    Returns:
        (1) parameter [string]: The note, or an empty string.
    """

    parts = []
    if caption:
        parts.append(caption.strip().rstrip('.') + '.')
    if not objects:
        parts.append('Check the lighting and the focus, then scan again.')
    return ' '.join(parts)


def Verdict(objects: tp.List[Detection_Str], threshold: float = 0.35) -> tp.Tuple[str, str]:
    """
    Description:
        The verdict-badge wording and its severity level. The level drives the
        badge colour, returned separately so the interface never parses the
        wording to decide how to paint it.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.
        (2) threshold [float]: The confidence below which the verdict is degraded.

    Returns:
        (1) parameter [Tuple<string> 1x2]: The (wording, level) pair, where level
                                           is 'ok' | 'warn' | 'idle'.
    """

    if not objects:
        return 'Empty', 'idle'
    scored = [o.Confidence for o in objects if o.Confidence is not None]
    if scored and min(scored) < threshold:
        return 'Low confidence', 'warn'
    return '%d found' % len(objects), 'ok'


def Screen_Understanding(objects: tp.List[Detection_Str], background_sentence: str) -> str:
    """
    Description:
        The Screen-Understanding text: the ONE rendering shared by the file the
        validation harness writes and the panel the application shows. The background
        is stated exactly once, on the first line, and that line carries the object
        count; every line below describes an object alone (the describer is asked to
        describe only the part; Compose writes each det.Sentence).

        The count is len(objects) — the same list used to number the lines, never
        recomputed — so the header and the lines cannot disagree. Singular and plural
        read correctly, and the zero case reads 'no objects were detected on it', not
        '0 objects'.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) background_sentence [string]: The one global background description
                                          (generated from the reference frame).

    Returns:
        (1) parameter [string]: The full Screen-Understanding text.
    """

    header = Screen_Header(objects, background_sentence)
    if not objects:
        return header
    lines = [Object_Line(i, det) for i, det in enumerate(objects)]
    return header + '\n\n' + '\n'.join(lines)


def Screen_Header(objects: tp.List[Detection_Str], background_sentence: str) -> str:
    """
    Description:
        The Screen-Understanding first line: the background stated once, then the object
        count. It is the single source of that sentence for BOTH the file (via
        Screen_Understanding) and the application's Scene-Understanding lead, so the two
        cannot disagree on the wording or the count.

        The count is len(objects) — the same list the lines are numbered from. Singular
        and plural read correctly, and the zero case reads 'no objects were detected on
        it', not '0 objects'.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) background_sentence [string]: The one global background description.

    Returns:
        (1) parameter [string]: The header line.
    """

    # The background is stated first, always: an empty sentence would leave the count
    # line headless ('There are 3 objects on it' with no 'it'), so a missing background
    # falls back to the neutral string here too. The two sentences are ONE string, and every
    # renderer shows it as one paragraph — there is deliberately no helper for either half, so
    # nothing downstream can split the pair and style the pieces differently.
    background = (background_sentence or '').strip() or CONST_BACKGROUND_FALLBACK
    if background[-1] not in '.!?':
        background += '.'
    lead = background + ' '

    count = len(objects)
    if count == 0:
        return lead + 'No objects were detected on it.'
    verb = 'is' if count == 1 else 'are'
    noun = 'object' if count == 1 else 'objects'
    return lead + 'There %s %d %s on it, described below.' % (verb, count, noun)


def Object_Label(index: int) -> str:
    """
    Description:
        The numbered NAME of an object ('Object N', 1-based) — the part of the label the
        object name occupies, without its confidence. The panel renders this leading and
        heavier so the name leads; the confidence follows from Object_Confidence. The full
        one-line label (name and confidence joined) is Object_Label_Full, the SINGLE source
        the descriptions file and the panel both build from, so the two cannot number an
        object differently.

    Args:
        (1) index [int]: The object's 0-based position in the list.

    Returns:
        (1) parameter [string]: The object name ('Object N').
    """

    return 'Object %d' % (index + 1)


def Object_Confidence(det: Detection_Str) -> str:
    """
    Description:
        The confidence suffix of an object's label ('Confidence 91%'), from the object's
        OWN score (det.Segmenter_Score) — the per-object figure, distinct from the frame
        mean in the panel table and the session mean in the status bar. An object the
        background cue alone found carries no score, and then the field reads 'Confidence
        —' rather than being omitted, so every label keeps the same shape and a missing
        score stays visible.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The confidence suffix ('Confidence N%' or 'Confidence —').
    """

    if det.Segmenter_Score is None:
        return 'Confidence %s' % CONST_NO_CONFIDENCE
    return 'Confidence %d%%' % int(round(100.0 * det.Segmenter_Score))


def Frame_Confidence(objects: tp.List[Detection_Str]) -> tp.Tuple[tp.Optional[int], int]:
    """
    Description:
        The frame's mean confidence and how many objects it is over: the mean of the SCORED
        objects' own scores as a whole percentage, and their count. Objects the background cue
        alone found carry no score and are not counted as 0% — a frame with none scored has no
        mean (None), not a zero. One computation for the panel table, the capture record and the
        finished-analysis log line, so the three can never disagree.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The frame's located objects.

    Returns:
        (1) parameter [int or None]: The mean percentage, or None when no object is scored.
        (2) parameter [int]: The number of scored objects.
    """

    scores = [det.Segmenter_Score for det in objects if det.Segmenter_Score is not None]
    if not scores:
        return None, 0
    return int(round(100.0 * sum(scores) / len(scores))), len(scores)


def Object_Size(det: Detection_Str) -> str:
    """
    Description:
        The size suffix of an object's label, from its measurement: 'A × B mm' (long side
        first) for an elongated or square-like object, 'Ø D mm' for a round symmetric one and
        'A/F D mm' for a hexagonal one (across flats — the label names the convention, since the
        two differ by up to 15 % on the same part), rounded to CONST_SIZE_DECIMALS — the one place
        a size is rounded; the number itself is never changed. An empty string when the object is
        not measured (no mask, or no scale configured): the label then simply has no size, never a
        placeholder number.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The size ('24.31 × 18.70 mm' / 'Ø 16.08 mm' / 'A/F 11.72 mm'), or
                                ''.
    """

    measurement = det.Measurement
    if measurement is None:
        return ''
    if measurement.Symmetric:
        return '%s %.*f mm' % ('A/F' if measurement.Across_Flats else 'Ø', CONST_SIZE_DECIMALS,
                               measurement.Diameter_Mm)
    return '%.*f × %.*f mm' % (CONST_SIZE_DECIMALS, measurement.Width_Mm, CONST_SIZE_DECIMALS,
                               measurement.Height_Mm)


def Dimension_Check_Text(Dimension_Check_Str: Dimension_Check_Str) -> str:
    """
    Description:
        One catalogue dimension check as text: the dimension, what was measured, what was expected
        with its tolerance, and the outcome — 'length 60.25 mm, expected 60.00 ± 1.50 mm: within' —
        so a failed check says all three. Rounded to CONST_SIZE_DECIMALS, like every size shown.

    Args:
        (1) Dimension_Check_Str [Dimension_Check_Str(object)]: The check.

    Returns:
        (1) parameter [string]: The text.
    """

    check = Dimension_Check_Str
    return '%s %.*f mm, expected %.*f ± %.*f mm: %s' % (
        check.Name, CONST_SIZE_DECIMALS, check.Measured_Mm, CONST_SIZE_DECIMALS, check.Nominal_Mm,
        CONST_SIZE_DECIMALS, check.Tolerance_Mm, 'within' if check.Within else 'OUT OF TOLERANCE')


def Verdict_Lines(det: Detection_Str) -> tp.List[str]:
    """
    Description:
        A catalogue mode's verdict on one object, as the sentences Screen Understanding and the Log show:
        the state first, with the evidence it rests on, then one line per reason it is not OK, and a note
        when its size was checked where the size checks are not verified. Every NOK says what was measured
        and what was expected; an Unspecified object says what to do. Empty outside a catalogue mode.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [Vector<string>]: The lines, the state first; [] outside a catalogue mode.
    """

    result = det.Catalogue
    if result is None:
        return []
    similarity = 'similarity %.2f' % result.Similarity
    if det.Verdict == 'Unspecified':
        return ['Unspecified — %.2f times the part\'s area: probably several parts together. Separate them and '
                'scan again.' % result.Area_Ratio]
    if det.Verdict == 'Warning':
        return ['Warning — not the part (%s): it should not be on the surface.' % similarity]
    lines = ['%s — the part, %s up (%s).' % (det.Verdict, result.Side, similarity)]
    if det.Verdict == 'NOK':
        if result.Similarity < result.Identify_Similarity:
            lines.append('It has the part\'s outline but does not look like the part (%s; the part is identified '
                         'from %.2f).' % (similarity, result.Identify_Similarity))
        if not det.Dimension_Checks:
            lines.append('Its outline could not be measured.')
        lines += [Dimension_Check_Text(check) for check in det.Dimension_Checks if not check.Within]
    if det.Dimension_Checks and result.Center_Distance_Mm > result.Verified_Radius_Mm:
        lines.append('The size check is not verified here: %.0f mm from the frame centre, verified to %.0f mm.'
                     % (result.Center_Distance_Mm, result.Verified_Radius_Mm))
    return lines


def Verdict_Log_Line(index: int, det: Detection_Str) -> tp.Tuple[str, str]:
    """
    Description:
        An object's verdict as one log line, 'Object N: <its verdict lines>', and the level it is logged at:
        WARNING for an object that should not be there or could not be judged (Warning, Unspecified), INFO
        otherwise — a NOK is a result the station reports, not a fault of the application.

    Args:
        (1) index [int]: The object's 0-based position in the list.
        (2) det [Detection_Str(object)]: The object, judged.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (level 'INFO' or 'WARNING', the line).
    """

    level = 'WARNING' if det.Verdict in ('Warning', 'Unspecified') else 'INFO'
    return level, '%s: %s' % (Object_Label(index), ' '.join(Verdict_Lines(det)))


def Object_Label_Full(index: int, det: Detection_Str) -> str:
    """
    Description:
        The whole one-line label of an object — the name, its confidence and, when measured, its
        size, joined by the one CONST_LABEL_SEPARATOR ('Object 1 · Confidence 91% · 24.31 × 18.70
        mm'). This is the SINGLE source of the label text for both the descriptions file (via
        Object_Line) and the panel, which renders the parts (Object_Label, Object_Confidence,
        Object_Size) in different weights so the name leads. Both renderings carry the same
        words and the same separator, so they cannot drift.

    Args:
        (1) index [int]: The object's 0-based position in the list.
        (2) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The full label ('Object N · Confidence …').
    """

    parts = [Object_Label(index), Object_Confidence(det)]
    size = Object_Size(det)
    if size:
        parts.append(size)
    return CONST_LABEL_SEPARATOR.join(parts)


def Object_Line(index: int, det: Detection_Str) -> str:
    """
    Description:
        One numbered object line ('Object N · Confidence … - <sentence>') for the
        descriptions file — the full label from Object_Label_Full joined to the
        description, so the file keeps its one-line form while the panel renders the same
        label and description on two levels. The sentence is det.Sentence (written by
        Compose). In a catalogue mode the object's verdict lines (Verdict_Lines) follow it,
        indented, so the file says what the panel says.

    Args:
        (1) index [int]: The object's 0-based position in the list.
        (2) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The numbered line.
    """

    return '\n'.join(['%s - %s' % (Object_Label_Full(index, det), det.Sentence)]
                     + ['    ' + line for line in Verdict_Lines(det)])


def Yolo_Lines(objects: tp.List[Detection_Str], size: tp.Tuple[int, int]) -> tp.List[str]:
    """
    Description:
        One YOLO-format region line per object — '<class_id> <x_center> <y_center>
        <width> <height>' — geometry normalised to 0..1 against the frame (width, height)
        at six decimals. The boxes come from the SAME ordered object list that drives the
        numbering, the mask and the Screen-Understanding text, so every artefact describes
        the same objects in the same order.

        The class id is the object's 0-BASED index in that list (object 1 in the text ->
        id 0), NOT a class: it is a per-frame handle for finding the object in the text
        and correcting it by hand. The same id means a different part in every frame, so
        these files must not be used for training as-is — see docs/design-decisions.md.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).

    Returns:
        (1) parameter [Vector<string>]: One YOLO line per object, in order.
    """

    width, height = float(size[0]), float(size[1])
    lines = []
    for index, det in enumerate(objects):
        x, y, w, h = det.Bbox
        x_center = (x + w / 2.0) / width
        y_center = (y + h / 2.0) / height
        lines.append('%d %.6f %.6f %.6f %.6f'
                     % (index, x_center, y_center, w / width, h / height))
    return lines


def Compose(objects: tp.List[Detection_Str], caption: str = '') -> tp.Tuple[tp.List[Detection_Str], str]:
    """
    Description:
        Write the line for every object (into det.Sentence) and return the objects
        alongside the note. Nothing the model wrote is rewritten, so there is no
        per-object audit. The objects are never reordered here — their order is the
        operator-visible index contract.

        The lead line is NOT built here: the view and the descriptions file both render
        it from the shared Screen_Header, so there is one source for it and no second
        copy to drift.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) caption [string]: An optional leading explanation for the note.

    Returns:
        (1) parameter [Tuple]: (objects, note).
    """

    for det in objects:
        det.Sentence = Object_Description(det)
    return objects, Scene_Note(objects, caption)
