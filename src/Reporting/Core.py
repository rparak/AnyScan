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
from Parameters.Vision import (Detection_Str, Dimension_Check_Str, Hole_Count_Str, Catalogue_Result_Str,
                               CONST_WARNING_KINDS)
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
# into certainty (design-decisions.md, "The object label keeps the model's alternatives").
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
# removed rather than retuned (design-decisions.md). The background is stated once,
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
# such, and do not revert them to a scale-derived count (design-decisions.md).
#   Unit [int]
CONST_SIZE_DECIMALS = 2
# Counts in a reason are words up to ten, digits above (Count_Word).
#   Unit [Tuple<string>]
CONST_COUNT_WORDS = ('no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten')


# The describer guard (Guard_Description) reads, clause by clause, each mention of what a check decides — a hole
# of a kind, a stain — and what the words round it claim: there (with a count, 'two', 'both', or all of them,
# 'each'), not there ('no', 'without', 'free of' just before it; 'are absent' after it), missing or extra. A claim
# the check that ran does not bear out drops its sentence, and every drop is logged. Words, not judgement
# (KNOWN_ISSUES). Read per mention, not per sentence: 'features through-holes without countersinks' claims the
# through-holes there and the countersinks not; read as one negated sentence it let a back with no hole found
# keep its through-holes (capture 20261015-160433_s1, 2026-10-15).
# The hole kinds, each named as the catalogue's hole group it is held to: a stepped hole is its countersink; a
# kind no group of the side has (a counterbore on the plate, a countersink on its back) is one the check found
# none of; '' is a plain hole, held to the largest group (a hole is a position: the plate's groups are
# concentric). Matched in this order, so a stepped hole is not also read as a plain one.
#   Unit [Tuple<Tuple<string> 1x2>]
CONST_GUARD_HOLE_KINDS = (
    ('countersink', r'stepped[- ]holes?|counter-?sunk[- ]holes?|counter-?sinks?|counter-?sinking|counter-?sunk'),
    ('counterbore', r'counter-?bor(?:e|es|ed|ing)(?:[- ]holes?)?'),
    ('through-hole', r'through[- ]?holes?'),
    ('', r'holes?'),
)
# A stain mention ('stainless' is a material, not a stain); a side claimed clean outright; a defect denied
# outright ('no defects', 'free of flaws'), which claims the side free of the stains and the holes' faults alike
# (only a word before it denies it: 'they are not defects' is the catalogue's own 'not a defect').
#   Unit [string]
CONST_GUARD_STAIN = r'stain(?!less)\w*|fingerprint\w*|smudge\w*|smear\w*|discolou?r\w*'
CONST_GUARD_CLEAN = (r'\b(spotless|unblemished|pristine|flawless|stain-free)\b'
                     r'|\bclean (surface|finish|face|front|back|side|part|plate)\b'
                     r'|\b(surface|finish|face|front|back|side|part|plate) (is|looks|appears) clean\b')
CONST_GUARD_DEFECT = r'defects?|flaws?|blemish\w*|damage'
# A stain denied for part of the side only ('while the other face shows no such staining'), which a stain found
# elsewhere does not contradict: the check gives no region to hold it to. Measured: Gemma wrote it, true, on capture
# 20261015-131258_s1 frame 6, object 2 (both stains on one half).
#   Unit [string]
CONST_GUARD_PART_OF_SIDE = (r'\b(other|rest|remaining|elsewhere|left|right|upper|lower|top|bottom|half|halves|end|ends'
                            r'|corners?|edges?|sections?|portions?|areas?|regions?)\b')
# The words read back from a mention, at most CONST_GUARD_REACH of them, stopping at one that starts another
# phrase ('no scratches near the holes' denies no hole; 'the' stops too, except in 'free of the'): a negator denies
# the mention ('free of', 'clean of', 'devoid of' as pairs), 'missing' or 'extra' claims a fault, a count word claims
# that many ('both' and 'pair' two), and 'each', 'every', 'all' claim every hole of the group. A defect is denied by a
# strict negator only.
#   Unit [int] / [Tuple<string>]
CONST_GUARD_REACH = 4
CONST_GUARD_NEGATORS = ('no', 'not', 'without', 'none', 'nor', 'neither', 'never', 'lack', 'lacks', 'lacking')
CONST_GUARD_DEFECT_NEGATORS = ('no', 'without', 'none')
CONST_GUARD_DENY_PAIRS = (('free', 'of'), ('free', 'from'), ('clean', 'of'), ('devoid', 'of'))
CONST_GUARD_MISSING = ('missing', 'absent')
CONST_GUARD_EXTRA = ('extra', 'additional', 'surplus')
CONST_GUARD_ALL = ('each', 'every', 'all')
CONST_GUARD_STOPS = ('the', 'near', 'around', 'at', 'on', 'in', 'by', 'beside', 'between', 'along', 'across', 'above',
                     'below', 'under', 'over', 'to', 'toward', 'towards', 'with', 'into', 'where', 'which', 'that', 'is',
                     'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had', 'shows', 'show', 'features', 'feature',
                     'displays', 'exhibits', 'surrounding', 'than')
# After a mention, in its clause: a denial ('are absent', 'is not visible'), a fault ('are missing'), every hole
# ('in each corner'), or a hypothesis that claims nothing ('where holes would be').
#   Unit [string]
CONST_GUARD_AFTER_DENIED = r'^\W*(?:\w+\W+){0,2}?(?:is|are|was|were|appears?|seems?|remains?)\s+(?:not|absent|nowhere)\b'
CONST_GUARD_AFTER_MISSING = r'^\W*(?:\w+\W+){0,2}?(?:is|are|was|were|appears?|seems?)\s+missing\b'
CONST_GUARD_AFTER_ALL = r'^[^,;:]*?\b(?:in|at|near|by)\s+(?:each|every|all|both)\s+(?:of\s+the\s+)?(?:corners?|ends?|halves|half)\b'
CONST_GUARD_AFTER_HYPOTHESIS = r'^\W*(?:would|should|could|might|ought|will)\b'
# The guard's reason for a sentence with a digit, which is dropped without asking the describer again (Vision.Core:
# a contradiction of a check is asked again once, with the findings restated).
#   Unit [string]
CONST_GUARD_NUMBER = 'it states a number'
# The describer is told the checks' findings as facts, and describes holes and stains only as features it sees: a
# sentence naming the checks, a verification, a confirmation or a detection ('the automatic check confirmed both
# countersinks') reads as the describer's own finding, and is treated as a contradiction (asked again once, then
# left out). The rule the describer is given, last in its prompt (Describer_Prompt), and the words that break it.
# Measured: told every hole group, Gemma recited the check on 5 of 11 judged parts (2026-10-15, design-decisions.md).
#   Unit [string]
CONST_DESCRIBER_CHECKS_RULE = ('Describe holes and stains only as features you see on the part, for example "two '
                               'stepped holes"; never mention the checks, a verification, a confirmation or a detection.')
CONST_GUARD_CHECKS = r'\b(?:automatic(?:ally)?|automated|checks?|checked|verif\w*|confirm\w*|detect\w*)\b'
CONST_GUARD_CHECKS_WHY = 'it refers to the checks'
# A part outside the inspection area has no check run on it (design-decisions.md, *A part outside the inspection
# area is not checked*): its prompt holds no hole or stain fact and asks for its material, shape and surface alone,
# and a sentence naming a hole, a countersink or a stain is left out, since nothing measured stands behind it.
#   Unit [string]
CONST_DESCRIBER_OUTSIDE_PROMPT = ('Describe this object briefly: only its material, its shape and its surface. Do not '
                                  'mention holes, countersinks, stains or marks, and give no numbers.')
CONST_GUARD_OUTSIDE_WHY = 'it names a hole or a stain, which are not checked outside the inspection area'


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


def Warning_Kind_Name(kind: str) -> str:
    """
    Description:
        A Warning kind's name as the operator reads it (Parameters.Vision.CONST_WARNING_KINDS: 'outside' is
        'Outside area', 'several_parts' 'Several parts', ...).

    Args:
        (1) kind [string]: The kind, as recorded ('warning_kind').

    Returns:
        (1) parameter [string]: The name; '' for no kind or one this version does not know.
    """

    return dict(CONST_WARNING_KINDS).get(kind, '')


def State_Word(det: Detection_Str) -> str:
    """
    Description:
        An object's state as Scene Understanding and the log name it: its verdict, a catalogue Warning with its kind
        ('Warning – Outside area').

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The state.
    """

    name = Warning_Kind_Name(det.Catalogue.Warning_Kind) if det.Catalogue is not None else ''
    return '%s – %s' % (det.Verdict, name) if det.Verdict == 'Warning' and name else det.Verdict


def Badges(objects: tp.List[Detection_Str], threshold: float = 0.35) -> tp.List[tp.Tuple[str, str]]:
    """
    Description:
        The verdict badges' wording and severity levels. The level drives each badge's colour, returned separately so
        the interface never parses the wording to decide how to paint it.

        In a catalogue mode (the objects carry catalogue evidence) one badge per state present that needs the operator,
        all at once, so a Warning is never hidden behind a NOK (the owner's ruling, 2026-10-16), in this order:
        'NOK · 2' (level 'fail'), 'Warning · 3' ('warn', the amber, every kind counted together); with neither,
        'All OK' ('ok'). The word carries the state as well as the colour. Outside a catalogue mode, one badge: low
        confidence, or what was found.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.
        (2) threshold [float]: The confidence below which the verdict is degraded.

    Returns:
        (1) parameter [Vector<Tuple<string> 1x2>]: The (wording, level) pairs, at least one; level is 'fail' | 'ok' |
                                                   'warn' | 'idle'.
    """

    if not objects:
        return [('Empty', 'idle')]
    if any(o.Catalogue is not None for o in objects):
        verdicts = [o.Verdict for o in objects]
        badges = [('%s · %d' % (state, verdicts.count(state)), level)
                  for state, level in (('NOK', 'fail'), ('Warning', 'warn')) if state in verdicts]
        return badges or [('All OK', 'ok')]
    scored = [o.Confidence for o in objects if o.Confidence is not None]
    if scored and min(scored) < threshold:
        return [('Low confidence', 'warn')]
    return [('%d found' % len(objects), 'ok')]


def Verdict(objects: tp.List[Detection_Str], threshold: float = 0.35) -> tp.Tuple[str, str]:
    """
    Description:
        The first verdict badge's wording and level (Badges): the one the session log and a single-badge reader take,
        NOK when there is one.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.
        (2) threshold [float]: The confidence below which the verdict is degraded.

    Returns:
        (1) parameter [Tuple<string> 1x2]: The (wording, level) pair.
    """

    return Badges(objects, threshold)[0]


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


def __Warning_Sentence(result: Catalogue_Result_Str) -> str:
    """
    Description:
        Why a Warning was not judged, and what the operator does, by its kind (Catalogue_Result_Str.Warning_Kind): a part
        outside the inspection area, to move inside; a foreign object, to remove; several parts found as one, to
        separate; a side that cannot be told, or that its holes and its look disagree on, to scan nearer the centre.

    Args:
        (1) result [Catalogue_Result_Str(object)]: The object's catalogue result, a Warning.

    Returns:
        (1) parameter [string]: The sentence.
    """

    looks = ', '.join('%s %.2f' % (side, similarity) for side, similarity in result.Side_Similarities.items())
    if result.Warning_Kind == 'outside':
        return 'It lies outside the inspection area, so it is not judged: move it fully inside the area and scan again.'
    if result.Warning_Kind == 'several_parts':
        return ("Its area is %.2f times the part's, probably several parts touching or lying close together, so it "
                'cannot be judged: separate the parts and scan again.' % result.Area_Ratio)
    if result.Warning_Kind == 'side_mismatch':
        return ('Its holes show one side up and its look the other (similarity %s), so it cannot be judged: check '
                'that it is the part and scan it again nearer the centre.' % looks)
    if result.Warning_Kind == 'side_unknown':
        return ('Which side is up cannot be told from its look (similarity %s) or its holes, and its verdict depends '
                'on it, so it cannot be judged: move it nearer the centre and scan again.' % looks)
    if result.Outside_Area:
        return 'It is not the part and lies outside the inspection area: remove it from the surface.'
    return 'It is not the part, so it should not be there: remove it from the surface.'


def Outside_Part(det: Detection_Str) -> bool:
    """
    Description:
        Whether an object is a catalogue part lying outside the inspection area: a Warning for where it lies that
        resembles the part (Catalogue_Result_Str.Resembles), drawn amber. No check runs on it, so it carries no hole
        or stain finding, and its description may name none.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [bool]: True for a part outside the area.
    """

    result = det.Catalogue
    return result is not None and det.Verdict == 'Warning' and result.Warning_Kind == 'outside'


def __Finding_Clauses(det: Detection_Str, side_name: str) -> tp.List[str]:
    """
    Description:
        A judged part's findings as clauses, in order: the outline's size ('its length is out of tolerance'), its
        look, its holes (__Hole_Clauses) and its stains ('there are two stains on the machined front').

    Args:
        (1) det [Detection_Str(object)]: The part, or one side's reading of it.
        (2) side_name [string]: The side its holes and stains were checked on, as the catalogue names it.

    Returns:
        (1) parameter [Vector<string>]: The clauses.
    """

    result = det.Catalogue
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
        side = ' on the %s' % side_name if side_name else ''
        clauses.append('there is a stain%s' % side if len(det.Stains) == 1 else
                       'there are %s stains%s' % (Count_Word(len(det.Stains)), side))
    return clauses


def __Clause_Sentence(clauses: tp.List[str]) -> str:
    """
    Description:
        Clauses joined as one phrase ('A, b, and c'), uncapitalised and without its full stop.

    Args:
        (1) clauses [Vector<string>]: The clauses, at least one.

    Returns:
        (1) parameter [string]: The phrase.
    """

    return clauses[0] if len(clauses) == 1 else '%s, and %s' % (', '.join(clauses[:-1]), clauses[-1])


def Reason_Sentence(det: Detection_Str) -> str:
    """
    Description:
        Why a judged object is not OK, as the one sentence Scene Understanding shows (the owner's rule,
        2026-10-11): each kind of finding a clause — the outline's size ('its length is out of tolerance'), its
        look, the holes (__Hole_Clauses) and the stains ('there are two stains on the machined front') — in that
        order, joined ('A, b, and c.'). Counts in words up to ten. The
        measured and expected values are in the log (Part_Lines). A part whose side could not be told, NOK on every
        side, gives what its readings share; with nothing shared, each reading's clauses with its side named
        ('Read with its machined front up, …; read with its unmachined back up, ….'). A Warning says why it was not
        judged and what the operator does, by its kind (__Warning_Sentence), nothing else, as no check ran on it or
        its checks could not be trusted. Empty for an OK part and outside a catalogue mode.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The sentence, or ''.
    """

    result = det.Catalogue
    if result is None or det.Verdict == 'OK':
        return ''
    if det.Verdict == 'Warning':
        return __Warning_Sentence(result)
    clauses = __Finding_Clauses(det, result.Side_Name)
    readings = {name: __Finding_Clauses(reading, name) for name, reading in result.Side_Readings.items()}
    if result.Side_Evidence == 'undecided' and len(readings) > 1:
        shared = [clause for clause in next(iter(readings.values()))
                  if all(clause in other for other in readings.values())]
        if not shared and all(readings.values()):
            sentence = '; '.join('read with its %s up, %s' % (name, __Clause_Sentence(found))
                                 for name, found in readings.items())
            return sentence[0].upper() + sentence[1:] + '.'
        clauses = shared or clauses
    if not clauses:
        return ''
    sentence = __Clause_Sentence(clauses)
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
        The note a part judged on its size carries in the log (Verdict_Log_Line) when it lies beyond the radius the
        size checks were verified to: its distance and the radius. Not in Scene Understanding (Verdict_Lines): a size
        right for the part read there as one in doubt, the operator cannot act on it, and the verdict does not
        depend on it (KNOWN_ISSUES, *Sizes beyond 46.4 mm from the frame centre are unverified*). The log keeps it
        for the rig captures that widen the radius (capture-checklist.md).

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


def Unplaced_Hole_Note(det: Detection_Str) -> str:
    """
    Description:
        The note a part carries when holes it is missing are not marked on the frame: the holes found anchor where the
        missing ones go, and with none found the outline cannot tell which end of the part they belong at (their
        layout is not centred), so none is drawn (Vision.Utilities.Holes). The verdict stands; the note explains the
        missing marks.

    Args:
        (1) det [Detection_Str(object)]: The part, its holes checked and marked.

    Returns:
        (1) parameter [string]: The note, or '' when every missing hole is marked.
    """

    unplaced, total = [], 0
    for count in det.Hole_Counts:
        drawn = sum(1 for feature in det.Features if feature.Kind == 'hole' and feature.Name == count.Name
                    and not feature.Found)
        left = count.Expected - count.Found - drawn
        if left > 0:
            unplaced.append(__Plural(left, count.Name))
            total += left
    if not total:
        return ''
    return ('The missing %s %s not marked on the frame: with no hole found, which end of the part %s at cannot be '
            'told.' % (__Join(unplaced), 'is' if total == 1 else 'are', 'it belongs' if total == 1 else 'they belong'))


def Verdict_Notes(det: Detection_Str) -> str:
    """
    Description:
        A verdict's notes as the log gives them (Verdict_Log_Line): the size note (Size_Note) and the unplaced-hole
        note (Unplaced_Hole_Note), each when it applies. Scene Understanding gives the unplaced-hole note only.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The notes, or '' when none applies.
    """

    return ' '.join(note for note in (Size_Note(det), Unplaced_Hole_Note(det)) if note)


def Verdict_Lines(det: Detection_Str) -> tp.List[str]:
    """
    Description:
        A catalogue mode's verdict on one object as Scene Understanding shows it: 'State: OK.', 'State: NOK.' or
        'State: Warning – <kind>.' (State_Word), then, when it is not OK, its one 'Reason:'
        sentence with the operator's action for a Warning (Reason_Sentence), then the unplaced-hole note when it applies
        (Unplaced_Hole_Note). No similarity, no side and no size note here: the similarity and the size note are in
        the log only (Verdict_Log_Line), and the side is in the description (Side_Sentence). Empty outside a
        catalogue mode.

    Args:
        (1) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [Vector<string>]: The lines, the state first; [] outside a catalogue mode.
    """

    if det.Catalogue is None:
        return []
    note, reason = Unplaced_Hole_Note(det), Reason_Sentence(det)
    return (['State: %s.' % State_Word(det)] + (['Reason: %s' % reason] if reason else [])
            + (['Note: %s' % note] if note else []))


def Side_Sentence(det: Detection_Str) -> str:
    """
    Description:
        The sentence a judged part's description gains: which side is up, in the catalogue's words for it
        ('It lies with its machined front up.'). Only for an object judged the part (OK, NOK): a Warning was
        not judged. The side is the one the checks used
        (Catalogue_Result_Str.Side: DINOv2's by its margin, else its holes'), never the describer's: the describer
        is told it (Describer_Prompt), not asked.

    Args:
        (1) det [Detection_Str(object)]: The object, judged.

    Returns:
        (1) parameter [string]: The sentence, or '' when it has none.
    """

    if det.Catalogue is None or det.Verdict not in ('OK', 'NOK') or not det.Catalogue.Side_Name:
        return ''
    return 'It lies with its %s up.' % det.Catalogue.Side_Name


def __Hole_Fact(count: Hole_Count_Str) -> str:
    """
    Description:
        What the hole check found of one group, as the describer is told it: in words, no digit, never the number
        the part should have ('no through-holes', 'both countersinks', 'all the through-holes', 'only one
        through-hole', 'more through-holes than the part has').

    Args:
        (1) count [Hole_Count_Str(object)]: The group's count.

    Returns:
        (1) parameter [string]: The phrase.
    """

    name, found, expected = count.Name, count.Found, count.Expected
    if found > expected:
        return 'more %ss than the part has' % name
    if found == 0:
        return 'no %ss' % name
    if found == expected:
        return 'the %s' % name if expected == 1 else 'both %ss' % name if expected == 2 else 'all the %ss' % name
    return 'only %s' % (__Plural(found, CONST_COUNT_WORDS[found] + ' ' + name) if found < len(CONST_COUNT_WORDS)
                        else 'some %ss' % name)


def Findings(det: Detection_Str) -> str:
    """
    Description:
        What the checks found on a judged part, for the describer to locate and describe: facts in words and
        without a digit or a measurement (the describer is given none), one sentence per check that ran — the
        stains, the holes (every group, found or not: 'found no through-holes on its unmachined back', 'found both
        countersinks and both through-holes on its machined front'), the outline and the look. It does not say OK
        or NOK: the describer describes, the checks decide.

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
    if det.Hole_Counts:
        found.append('An automatic check found %s on its %s.' % (__Join([__Hole_Fact(count) for count in det.Hole_Counts]),
                                                                side))
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
        Name, the side the identification decided), that side's description, that side's defects and what the checks found (Findings).
        Nothing filled in holds a number: the loader refuses one in the texts, and Findings writes none. The rule
        that holes and stains are described as features seen, never as the checks' (CONST_DESCRIBER_CHECKS_RULE),
        comes last.

    Args:
        (1) det [Detection_Str(object)]: The part, judged.
        (2) Catalogue_Item_Str [Catalogue_Item_Str(object)]: The item.

    Returns:
        (1) parameter [string]: The prompt; for a part outside the inspection area (Outside_Part), one with no hole
                                or stain fact asking for its material, shape and surface alone
                                (CONST_DESCRIBER_OUTSIDE_PROMPT); '' for an object not judged the part, or an item
                                without a prompt (the mode's own object prompt is used then).
    """

    item = Catalogue_Item_Str
    if Outside_Part(det):
        return CONST_DESCRIBER_OUTSIDE_PROMPT
    if not item.Describer_Prompt or det.Catalogue is None or det.Verdict not in ('OK', 'NOK'):
        return ''
    side = next((entry for entry in item.Sides if entry.Side == det.Catalogue.Side), None)
    defects = ' '.join('%s: %s%s' % (defect.Name.capitalize(), defect.Looks_Like,
                                     ' Not a defect: %s' % defect.Not_A_Defect if defect.Not_A_Defect else '')
                       for defect in item.Defects if defect.Side == det.Catalogue.Side)
    return ' '.join((item.Describer_Prompt.format(
        side=side.Name if side is not None else det.Catalogue.Side_Name,
        side_description=side.Description if side is not None else '',
        defects=defects or 'None described.', findings=Findings(det)) + ' ' + CONST_DESCRIBER_CHECKS_RULE).split())


def Restated_Prompt(prompt: str, det: Detection_Str) -> str:
    """
    Description:
        The prompt the describer is asked once more with when its text contradicted a check (Vision.Core): the first
        prompt, then the checks' findings restated as the facts its description must not contradict. No number,
        as in the first.

    Args:
        (1) prompt [string]: The first prompt (Describer_Prompt).
        (2) det [Detection_Str(object)]: The part, judged.

    Returns:
        (1) parameter [string]: The prompt.
    """

    return ' '.join(('%s Your last description contradicted the automatic checks, and the checks are right. What they '
                     'found: %s Write the description once more, in place of the last one: one short flowing paragraph that says '
                     'nothing these findings contradict.'
                     % (prompt, Findings(det))).split())


def __Guard_Words(text: str) -> tp.List[str]:
    """
    Description:
        A text's words, lower case, hyphens and apostrophes kept inside a word ('yellow-brown', "isn't").

    Args:
        (1) text [string]: The text.

    Returns:
        (1) parameter [Vector<string>]: The words.
    """

    return re.findall(r"[a-z]+(?:[-'][a-z]+)*", text.lower())


def __Guard_Before(words: tp.List[str], negators: tp.Tuple[str, ...]) -> tp.Tuple[str, tp.Optional[int]]:
    """
    Description:
        What the words just before a mention claim of it, read back at most CONST_GUARD_REACH words and stopping at a
        word that starts another phrase: 'denied' (a negator, or a pair like 'free of'), 'missing', 'extra' or
        'there'; and the count claimed, the nearest count word ('two'; 'both', 'pair' two; 'each', 'every', 'all'
        -1, every one of the group).

    Args:
        (1) words [Vector<string>]: The clause's words before the mention.
        (2) negators [Tuple<string>]: The words that deny it.

    Returns:
        (1) parameter [Tuple<string, int or None>]: The claim, and the count or None.
    """

    count = None
    for back in range(1, min(CONST_GUARD_REACH, len(words)) + 1):
        word, before = words[-back], words[-back - 1] if back < len(words) else ''
        if word in negators or ('not' in negators and word.endswith("n't")) or (before, word) in CONST_GUARD_DENY_PAIRS:
            return 'denied', count
        if word in CONST_GUARD_MISSING:
            return 'missing', count
        if word in CONST_GUARD_EXTRA:
            return 'extra', count
        if count is None and word in CONST_COUNT_WORDS[1:]:
            count = CONST_COUNT_WORDS.index(word)
        elif count is None and word in ('both', 'pair'):
            count = 2
        elif count is None and word in CONST_GUARD_ALL:
            count = -1
        if word in CONST_GUARD_STOPS and not (word == 'the' and before in ('of', 'from')):
            break
    return 'there', count


def __Guard_Hole(kind: str, claim: str, count: tp.Optional[int], det: Detection_Str) -> str:
    """
    Description:
        Whether one hole mention contradicts the hole check: holes of the kind claimed there when it found none,
        a count other than it found, every one when it found fewer or more; claimed absent when it found some;
        claimed missing when it found them all; claimed extra when it found no more than the part has.

    Args:
        (1) kind [string]: The hole group the mention is held to ('' for a plain hole: the largest group).
        (2) claim [string]: 'there', 'denied', 'missing' or 'extra' (__Guard_Before).
        (3) count [int or None]: The count claimed, -1 for every one, None for none.
        (4) det [Detection_Str(object)]: The part, its holes checked.

    Returns:
        (1) parameter [string]: Why it contradicts the check, or '' when it does not.
    """

    groups = {group.Name: group for group in det.Hole_Counts}
    if kind:
        found, expected = (groups[kind].Found, groups[kind].Expected) if kind in groups else (0, 0)
    else:
        found, expected = max(group.Found for group in groups.values()), max(group.Expected for group in groups.values())
    noun = kind or 'hole'
    if claim == 'denied' and found:
        return 'it says there are no %ss, which the hole check found' % noun
    if claim == 'missing' and found >= expected:
        return 'it says %ss are missing, which the hole check did not find' % noun
    if claim == 'extra' and found <= expected:
        return 'it says there are extra %ss, which the hole check did not find' % noun
    if claim != 'there':
        return ''
    if not found:
        return 'it claims %ss, which the hole check did not find' % noun
    if count == -1 and found != expected:
        return 'it claims every %s, and the hole check found %d of %d' % (noun, found, expected)
    if count is not None and count > 0 and count != found:
        return 'it claims %s %s, and the hole check found %d' % (CONST_COUNT_WORDS[count], __Plural(count, noun), found)
    return ''


def __Guard_Clause(clause: str, det: Detection_Str) -> str:
    """
    Description:
        Whether one clause contradicts the hole or the stain check, mention by mention (CONST_GUARD_HOLE_KINDS,
        CONST_GUARD_STAIN, CONST_GUARD_DEFECT): each mention's claim read from the words before it and after it
        (__Guard_Before, CONST_GUARD_AFTER_*), a mention in a hypothesis ('where holes would be') claiming nothing.
        A check that did not run (no hole group on the side; no stain check) is not held against.

    Args:
        (1) clause [string]: The clause.
        (2) det [Detection_Str(object)]: The part, judged, with its checks.

    Returns:
        (1) parameter [string]: Why it contradicts a check, or '' when it does not.
    """

    flags = re.IGNORECASE
    holes_failed = any(group.Found != group.Expected for group in det.Hole_Counts)
    patterns = ['(?P<hole%d>%s)' % (index, pattern) for index, (_kind, pattern) in enumerate(CONST_GUARD_HOLE_KINDS)]
    mentions = r'\b(?:%s|(?P<stain>%s)|(?P<defect>%s))\b' % ('|'.join(patterns), CONST_GUARD_STAIN, CONST_GUARD_DEFECT)
    for match in re.finditer(mentions, clause, flags):
        words, after = __Guard_Words(clause[:match.start()]), clause[match.end():]
        if re.search(CONST_GUARD_AFTER_HYPOTHESIS, after, flags):
            continue
        if match.group('defect'):
            if __Guard_Before(words, CONST_GUARD_DEFECT_NEGATORS)[0] != 'denied':
                continue
            if det.Stains:
                return 'it says there is no defect, and the stain check found a stain'
            if holes_failed:
                return 'it says there is no defect, and the hole check found holes missing or extra'
            continue
        claim, count = __Guard_Before(words, CONST_GUARD_NEGATORS)
        if claim == 'there' and re.search(CONST_GUARD_AFTER_DENIED, after, flags):
            claim = 'denied'
        elif claim == 'there' and re.search(CONST_GUARD_AFTER_MISSING, after, flags):
            claim = 'missing'
        elif claim == 'there' and count is None and re.search(CONST_GUARD_AFTER_ALL, after, flags):
            count = -1
        if match.group('stain'):
            if det.Stains is None:
                continue
            if claim in ('denied', 'missing') and det.Stains and not re.search(CONST_GUARD_PART_OF_SIDE, clause, flags):
                return 'it says there is no stain, which the stain check found'
            if claim in ('there', 'extra') and not det.Stains:
                return 'it claims a stain, which the stain check did not find'
            continue
        if not det.Hole_Counts:
            continue
        kind = next(kind for index, (kind, _pattern) in enumerate(CONST_GUARD_HOLE_KINDS) if match.group('hole%d' % index))
        why = __Guard_Hole(kind, claim, count, det)
        if why:
            return why
    if det.Stains and re.search(CONST_GUARD_CLEAN, clause, flags):
        return 'it says the side is clean, and the stain check found a stain'
    return ''


def Guard_Description(text: str, det: Detection_Str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        The describer's text on a judged part, with what it may not say taken out, sentence by sentence: a
        sentence with a digit (CONST_GUARD_NUMBER: a measurement or a count is the checks' to give), a sentence
        referring to the checks ('the automatic check confirmed…', CONST_GUARD_CHECKS: the describer describes what it
        sees, never the checks), and a sentence
        contradicting the hole or the stain check in either direction, read clause by clause and mention by mention
        (__Guard_Clause): holes of a kind claimed there that the check did not find, or a count it did not find;
        holes it found claimed absent; a stain claimed where it found none; the side claimed clean, or free of
        stains or defects, where it found one. For a part outside the inspection area (Outside_Part), on which no
        check ran, any sentence naming a hole, a countersink or a stain is left out instead
        (CONST_GUARD_OUTSIDE_WHY). The describer confirms and describes; it never decides, and the
        verdict is never changed here.

    Args:
        (1) text [string]: The describer's text.
        (2) det [Detection_Str(object)]: The part, judged, with its checks.

    Returns:
        (1) parameter [Tuple<string, Vector<Tuple<string> 1x2>>]: The text kept, and each sentence dropped with
                                                                    why.
    """

    kept, dropped = [], []
    outside = Outside_Part(det)
    for sentence in [part for part in re.split(r'(?<=[.!?])\s+', text.strip()) if part]:
        why = CONST_GUARD_NUMBER if re.search(r'\d', sentence) else ''
        why = why or (CONST_GUARD_CHECKS_WHY if re.search(CONST_GUARD_CHECKS, sentence, re.IGNORECASE) else '')
        if outside:
            named = any(re.search(r'\b(?:%s)\b' % pattern, sentence, re.IGNORECASE) for _kind, pattern in CONST_GUARD_HOLE_KINDS)
            why = why or (CONST_GUARD_OUTSIDE_WHY if named or re.search(CONST_GUARD_STAIN, sentence, re.IGNORECASE) else '')
        for clause in ([] if outside else re.split(r'[,;:()]|\s+(?:but|while|whereas)\s+', sentence)):
            why = why or __Guard_Clause(clause, det)
        if why:
            dropped.append((sentence, why))
        else:
            kept.append(sentence)
    return ' '.join(kept), dropped


def Verdict_Log_Line(index: int, det: Detection_Str) -> tp.Tuple[str, str]:
    """
    Description:
        An object's verdict as one log line, with what Scene Understanding leaves out: 'Object N: <state>,
        <side> up[ by its holes], similarity 0.91. Reason: … Note: …' — the side for a judged part ('by its
        holes' when a hole only that side has decided it, Vision.Utilities.Classify.Decide_Side), the
        similarity always —
        and the level it is logged at: WARNING for an object that should not be there or could not be judged
        (a Warning, with its kind), INFO otherwise — a NOK is a result the station reports, not a fault of the
        application.

    Args:
        (1) index [int]: The object's 0-based position in the list.
        (2) det [Detection_Str(object)]: The object, judged.

    Returns:
        (1) parameter [Tuple<string> 1x2]: (level 'INFO' or 'WARNING', the line).
    """

    result = det.Catalogue
    level = 'WARNING' if det.Verdict == 'Warning' else 'INFO'
    side = '%s up%s' % (result.Side, ' by its holes' if result.Side_Evidence == 'holes' else '')
    evidence = [State_Word(det)] + ([side] if det.Verdict in ('OK', 'NOK') else [])
    evidence.append('similarity %.2f' % result.Similarity)
    if det.Verdict == 'Warning' and result.Outside_Area:
        evidence.append('outside the inspection area, %s the part (saturation %.0f, extent %.1f mm)'
                        % ('resembles' if result.Resembles else 'does not resemble', result.Saturation, result.Extent_Mm))
    note = Verdict_Notes(det)
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
        these files must not be used for training as-is — see design-decisions.md.

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
