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
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Item_Str
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
# Counts in a reason are words up to ten, digits above (Count_Word).
#   Unit [Tuple<string>]
CONST_COUNT_WORDS = ('no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten')


# The describer guard's claims (Guard_Description), per check: a pattern claiming its defect, and one claiming
# its absence outright; a sentence that also negates ('no', 'not', 'without', 'free of') claims the defect absent.
# Words, not judgement: a sentence is dropped only when it says what a check contradicts, and every drop is logged.
#   Unit [Dict<string, Tuple<string> 1x2>] / [string]
CONST_GUARD_CLAIMS = {
    'stain': (r'\b(stain\w*|fingerprint\w*|smudge\w*|smear\w*|discolou?r\w*)',
              r'\b(spotless|unblemished|pristine|flawless|stain-free)\b'
              r'|\bclean (surface|finish|face|front|back|side|part|plate)\b|\b(surface|finish|face|part|plate) (is|looks|appears) clean\b'),
    'hole': (r'\b(missing|extra|absent)\b[^.]*\bholes?\b|\bholes?\b[^.]*\b(missing|absent)\b',
             r'\b(one|two|three|four|five|six|seven|eight|nine|ten|both|pair|each|every|all)\b[^.]*\bholes?\b'
             r'|\bholes?\b[^.]*\b(each|every|both|all) (of the )?corners?\b'),
}
CONST_GUARD_NEGATION = r"\b(no|not|without|free of|free from|clean of|none)\b|n't\b"


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

        In a catalogue mode (the objects carry catalogue evidence) the badge states the worst verdict, so it
        is never green while anything on the surface is not OK: any NOK ('NOK · 2 of 5', level 'fail'), else
        any Unspecified ('Not judged · 1', 'warn'), else any Warning ('Foreign object · 3', 'warn'), else
        every object OK ('All OK · 2', 'ok'). The word carries the state as well as the colour.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.
        (2) threshold [float]: The confidence below which the verdict is degraded.

    Returns:
        (1) parameter [Tuple<string> 1x2]: The (wording, level) pair, where level
                                           is 'fail' | 'ok' | 'warn' | 'idle'.
    """

    if not objects:
        return 'Empty', 'idle'
    if any(o.Catalogue is not None for o in objects):
        count = {state: sum(o.Verdict == state for o in objects) for state in ('NOK', 'Unspecified', 'Warning')}
        if count['NOK']:
            return 'NOK · %d of %d' % (count['NOK'], len(objects)), 'fail'
        if count['Unspecified']:
            return 'Not judged · %d' % count['Unspecified'], 'warn'
        if count['Warning']:
            return 'Foreign object · %d' % count['Warning'], 'warn'
        return 'All OK · %d' % len(objects), 'ok'
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


def Count_Word(count: int) -> str:
    """
    Description:
        A count as the panel writes it: in words up to ten ('two'), in digits above (the owner's rule, 2026-10-11,
        for every count in a reason).

    Args:
        (1) count [int]: The count.

    Returns:
        (1) parameter [string]: The word or the digits.
    """

    return CONST_COUNT_WORDS[count] if 0 <= count < len(CONST_COUNT_WORDS) else str(count)


def __Plural(count: int, noun: str) -> str:
    """
    Description:
        A noun for a count: 'through-hole' for one, 'through-holes' for any other.

    Args:
        (1) count [int]: The count.
        (2) noun [string]: The noun, singular.

    Returns:
        (1) parameter [string]: The noun.
    """

    return noun if count == 1 else noun + 's'


def __Join(items: tp.List[str]) -> str:
    """
    Description:
        Items as a list in a sentence: 'a', 'a and b', 'a, b and c'.

    Args:
        (1) items [Vector<string>]: The items.

    Returns:
        (1) parameter [string]: The list.
    """

    return items[0] if len(items) == 1 else '%s and %s' % (', '.join(items[:-1]), items[-1])


def __Hole_Clauses(det: Detection_Str) -> tp.List[str]:
    """
    Description:
        Each hole group's finding as a clause: missing ('one of two through-holes is missing', 'all four … are
        missing', 'both … are missing' for a pair, 'the … is missing' for a group of one), over ('there is one through-hole too many'), out of
        tolerance ('one through-hole is out of tolerance': its diameter, edge distance or pitch), the first two
        joined with the third ('… are missing and one is out of tolerance').

    Args:
        (1) det [Detection_Str(object)]: The part, its holes checked.

    Returns:
        (1) parameter [Vector<string>]: The clauses, in group order.
    """

    clauses = []
    for count in det.Hole_Counts:
        out = sum(1 for feature in det.Features if feature.Kind == 'hole' and feature.Name == count.Name
                  and feature.Found and not all(check.Within for check in feature.Checks))
        parts = []
        missing = count.Expected - count.Found
        if missing > 0:
            if count.Found == 0:
                parts.append('the %s is missing' % count.Name if count.Expected == 1 else
                             'both %ss are missing' % count.Name if count.Expected == 2 else
                             'all %s %ss are missing' % (Count_Word(count.Expected), count.Name))
            else:
                parts.append('%s of %s %ss %s missing' % (Count_Word(missing), Count_Word(count.Expected), count.Name,
                                                         'is' if missing == 1 else 'are'))
        elif missing < 0:
            parts.append('there %s %s %s too many' % ('is' if missing == -1 else 'are', Count_Word(-missing),
                                                     __Plural(-missing, count.Name)))
        if out:
            parts.append(('%s %s out of tolerance' % (Count_Word(out), 'is' if out == 1 else 'are')) if parts else
                         '%s %s %s out of tolerance' % (Count_Word(out), __Plural(out, count.Name),
                                                        'is' if out == 1 else 'are'))
        if parts:
            clauses.append(' and '.join(parts))
    return clauses


def Reason_Sentence(det: Detection_Str) -> str:
    """
    Description:
        Why a judged object is not OK, as the one sentence Scene Understanding shows (the owner's rule,
        2026-10-11): each kind of finding a clause — the outline's size ('its length is out of tolerance'), its
        look, the holes (__Hole_Clauses) and the stains ('there are two stains on the machined front') — in that
        order, joined ('A, b and c.'). Counts in words up to ten. The
        measured and expected values are in the log (Part_Lines). A Warning should not be there; an Unspecified
        object could not be judged, and what to do. Empty for an OK part and outside a catalogue mode.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The sentence, or ''.
    """

    result = det.Catalogue
    if result is None or det.Verdict == 'OK':
        return ''
    if det.Verdict == 'Warning':
        return 'The object should not be on the surface.'
    if det.Verdict == 'Unspecified':
        return ("Its area is %.2f times the part's, probably several parts together, so it cannot be judged. "
                'Separate them and scan again.' % result.Area_Ratio)
    clauses = []
    failed = [check.Name for check in det.Dimension_Checks if not check.Within]
    if not det.Dimension_Checks:
        clauses.append('its outline could not be measured')
    elif failed:
        clauses.append('its %s %s out of tolerance' % (__Join(failed), 'is' if len(failed) == 1 else 'are'))
    if result.Similarity < result.Identify_Similarity:
        clauses.append("it has the part's outline but does not look like the part")
    clauses += __Hole_Clauses(det)
    if det.Stains:
        side = ' on the %s' % result.Side_Name if result.Side_Name else ''
        clauses.append('there is a stain%s' % side if len(det.Stains) == 1 else
                       'there are %s stains%s' % (Count_Word(len(det.Stains)), side))
    if not clauses:
        return ''
    sentence = clauses[0] if len(clauses) == 1 else '%s, and %s' % (', '.join(clauses[:-1]), clauses[-1])
    return sentence[0].upper() + sentence[1:] + '.'


def Part_Lines(index: int, det: Detection_Str) -> tp.List[str]:
    """
    Description:
        A judged part's evidence for the log, below its verdict line (the request's explainability: each part's
        measured value, expected value and tolerance): its outline's checks, each hole group's count, then one
        line per part ('Part 2.3 · through-hole: …'), numbered as the frame numbers its failing parts.

    Args:
        (1) index [int]: The object's 0-based position.
        (2) det [Detection_Str(object)]: The object, judged.

    Returns:
        (1) parameter [Vector<string>]: The lines; [] for an object not judged the part.
    """

    if det.Catalogue is None or det.Verdict not in ('OK', 'NOK'):
        return []
    label = Object_Label(index)
    lines = []
    if det.Dimension_Checks:
        lines.append('%s · outline: %s.' % (label, '; '.join(Dimension_Check_Text(check) for check in det.Dimension_Checks)))
    lines += ['%s · %ss: %d of %d found%s.' % (label, count.Name, count.Found, count.Expected,
                                               '' if count.Found <= count.Expected else ', too many')
              for count in det.Hole_Counts]
    for feature in det.Features:
        if not feature.Part:
            continue
        head = 'Part %s · %s: ' % (feature.Part, feature.Name)
        if feature.Kind == 'hole' and not feature.Found:
            lines.append(head + 'not found at its expected position.')
        elif feature.Kind == 'hole':
            score = '' if feature.Score is None else ' (mask score %.2f)' % feature.Score
            over = ('' if feature.Passed or not all(check.Within for check in feature.Checks)
                    else '; its group has more holes than the part')
            lines.append('Part %s · %s' % (feature.Part, '; '.join(Dimension_Check_Text(check) for check in feature.Checks))
                         + over + score + '.')
        elif feature.Kind == 'stain':
            lines.append(head + '%.*f mm².' % (CONST_SIZE_DECIMALS, feature.Area_Mm2))
    return lines


def Size_Note(det: Detection_Str) -> str:
    """
    Description:
        The note a part judged on its size carries when it lies beyond the radius the size checks were
        verified to: its distance and the radius. The verdict stands; the note explains it.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The note, or '' when it needs none.
    """

    result = det.Catalogue
    if (result is None or det.Verdict not in ('OK', 'NOK') or not det.Dimension_Checks
            or result.Center_Distance_Mm <= result.Verified_Radius_Mm):
        return ''
    return ('The size check is not verified here: %.0f mm from the frame centre, verified to %.0f mm.'
            % (result.Center_Distance_Mm, result.Verified_Radius_Mm))


def Verdict_Lines(det: Detection_Str) -> tp.List[str]:
    """
    Description:
        A catalogue mode's verdict on one object as Scene Understanding shows it: 'State: <state>.', then, when it
        is not OK, its one 'Reason:' sentence (Reason_Sentence), then the size note when it applies. No
        similarity and no side here: the similarity is in the log only (Verdict_Log_Line), and the side is in
        the description (Side_Sentence). Empty outside a catalogue mode.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [Vector<string>]: The lines, the state first; [] outside a catalogue mode.
    """

    if det.Catalogue is None:
        return []
    note, reason = Size_Note(det), Reason_Sentence(det)
    return (['State: %s.' % det.Verdict] + (['Reason: %s' % reason] if reason else [])
            + (['Note: %s' % note] if note else []))


def Side_Sentence(det: Detection_Str) -> str:
    """
    Description:
        The sentence a judged part's description gains: which side is up, in the catalogue's words for it
        ('It lies with its machined front up.'). Only for an object judged the part (OK, NOK): a Warning is
        not the part, and an Unspecified object is several. The side is DINOv2's (Catalogue_Result_Str.Side),
        never the describer's: the describer is told it (Describer_Prompt), not asked.

    Args:
        (1) det [Detection_Str(object)]: The object, judged.

    Returns:
        (1) parameter [string]: The sentence, or '' when it has none.
    """

    if det.Catalogue is None or det.Verdict not in ('OK', 'NOK') or not det.Catalogue.Side_Name:
        return ''
    return 'It lies with its %s up.' % det.Catalogue.Side_Name


def Findings(det: Detection_Str) -> str:
    """
    Description:
        What the checks found on a judged part, for the describer to locate and describe: facts in words and
        without a number (the describer is given none), one sentence per check that ran — the stains, the holes,
        the outline and the look. It does not say OK or NOK: the describer describes,
        the checks decide.

    Args:
        (1) det [Detection_Str(object)]: The part, judged.

    Returns:
        (1) parameter [string]: The sentences; '' outside a catalogue mode or for an object not judged the part.
    """

    if det.Catalogue is None or det.Verdict not in ('OK', 'NOK'):
        return ''
    side = det.Catalogue.Side_Name or 'side up'
    found = []
    if det.Stains is not None:
        found.append('An automatic check found yellow-brown stains on its %s; describe them and where they are.'
                     % side if det.Stains else 'An automatic check found no stain on its %s.' % side)
    for count in det.Hole_Counts:
        if count.Found < count.Expected:
            found.append('An automatic check found fewer %ss than the part has.' % count.Name)
        elif count.Found > count.Expected:
            found.append('An automatic check found more %ss than the part has.' % count.Name)
    if any(not check.Within for check in det.Hole_Checks):
        found.append('An automatic check found a hole out of tolerance.')
    if any(not check.Within for check in det.Dimension_Checks):
        found.append('An automatic check found its outline out of tolerance.')
    if det.Catalogue.Similarity < det.Catalogue.Identify_Similarity:
        found.append("An automatic check found that it has the part's outline but does not look like the part.")
    return ' '.join(found)


def Describer_Prompt(det: Detection_Str, Catalogue_Item_Str: Catalogue_Item_Str) -> str:
    """
    Description:
        The describer's prompt for a judged part: the item's Describer.Prompt filled with the side up (its
        Name, DINOv2's side), that side's description, that side's defects and what the checks found (Findings).
        Nothing filled in holds a number: the loader refuses one in the texts, and Findings writes none.

    Args:
        (1) det [Detection_Str(object)]: The part, judged.
        (2) Catalogue_Item_Str [Catalogue_Item_Str(object)]: The item.

    Returns:
        (1) parameter [string]: The prompt; '' for an object not judged the part, or an item without a prompt
                                (the mode's own object prompt is used then).
    """

    item = Catalogue_Item_Str
    if not item.Describer_Prompt or det.Catalogue is None or det.Verdict not in ('OK', 'NOK'):
        return ''
    side = next((entry for entry in item.Sides if entry.Side == det.Catalogue.Side), None)
    defects = ' '.join('%s: %s%s' % (defect.Name.capitalize(), defect.Looks_Like,
                                     ' Not a defect: %s' % defect.Not_A_Defect if defect.Not_A_Defect else '')
                       for defect in item.Defects if defect.Side == det.Catalogue.Side)
    return ' '.join(item.Describer_Prompt.format(
        side=side.Name if side is not None else det.Catalogue.Side_Name,
        side_description=side.Description if side is not None else '',
        defects=defects or 'None described.', findings=Findings(det)).split())


def Guard_Description(text: str, det: Detection_Str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        The describer's text on a judged part, with what it may not say taken out, sentence by sentence: a
        sentence with a number (a measurement or a count is the checks' to give; the describer was given
        none), and a sentence contradicting a check that ran — its defect claimed when the check found none, or
        claimed absent when it found one (CONST_GUARD_CLAIMS: stains, the holes; a sentence negating the defect,
        'no stains', claims it absent; a count of holes claims them all there). The describer confirms and
        describes; it never decides.

    Args:
        (1) text [string]: The describer's text.
        (2) det [Detection_Str(object)]: The part, judged, with its checks.

    Returns:
        (1) parameter [Tuple<string, Vector<Tuple<string> 1x2>>]: The text kept, and each sentence dropped with
                                                                    why.
    """

    checks = {'stain': (det.Stains is not None, bool(det.Stains)),
              'hole': (bool(det.Hole_Counts), any(count.Found != count.Expected for count in det.Hole_Counts))}
    kept, dropped = [], []
    for sentence in [part for part in re.split(r'(?<=[.!?])\s+', text.strip()) if part]:
        why = 'it states a number' if re.search(r'\d', sentence) else ''
        for check, (defect, absent) in CONST_GUARD_CLAIMS.items():
            ran, found = checks[check]
            if why or not ran:
                continue
            claims_defect = re.search(defect, sentence, re.IGNORECASE) is not None
            negated = re.search(CONST_GUARD_NEGATION, sentence, re.IGNORECASE) is not None
            if found and (re.search(absent, sentence, re.IGNORECASE) is not None or (claims_defect and negated)):
                why = 'it says there is no %s defect, which the %s check found' % (check, check)
            elif not found and claims_defect and not negated:
                why = 'it claims a %s defect, which the %s check did not find' % (check, check)
        if why:
            dropped.append((sentence, why))
        else:
            kept.append(sentence)
    return ' '.join(kept), dropped


def Verdict_Log_Line(index: int, det: Detection_Str) -> tp.Tuple[str, str]:
    """
    Description:
        An object's verdict as one log line, with what Scene Understanding leaves out: 'Object N: <state>,
        <side> up, similarity 0.91. Reason: … Note: …' — the side for a judged part, the similarity always —
        and the level it is logged at: WARNING for an object that should not be there or could not be judged
        (Warning, Unspecified), INFO otherwise — a NOK is a result the station reports, not a fault of the
        application.

    Args:
        (1) index [int]: The object's 0-based position in the list.
        (2) det [Detection_Str(object)]: The object, judged.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (level 'INFO' or 'WARNING', the line).
    """

    result = det.Catalogue
    level = 'WARNING' if det.Verdict in ('Warning', 'Unspecified') else 'INFO'
    evidence = [det.Verdict] + (['%s up' % result.Side] if det.Verdict in ('OK', 'NOK') else [])
    evidence.append('similarity %.2f' % result.Similarity)
    note = Size_Note(det)
    reason = Reason_Sentence(det)
    words = (['%s.' % ', '.join(evidence)] + (['Reason: %s' % reason] if reason else [])
             + (['Note: %s' % note] if note else []))
    return level, '%s: %s' % (Object_Label(index), ' '.join(words))


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
