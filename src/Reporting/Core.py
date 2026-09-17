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
# File Name: ../Reporting/Core.py
## =========================================================================== ##

# System (Default)
import re
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — data structures
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Initialization of constants.

    The panel on the right is the product. Every sentence the operator reads is
    written in this module and nowhere else, so the console keeps one voice
    whichever backend produced the data. This module is Qt-free and depends only
    on the Parameters data structures; it never imports torch, OpenCV or a model.

    House style: plain declarative sentences, present tense, no hedging adverbs,
    no self-reference, numbers one to ten spelled out, and an empty result is a
    statement with a next action rather than an apology.
"""
# The whole-number words the summary spells out; anything past ten falls back to
# digits (see Count_Word).
CONST_NUMBER_WORDS = {0: 'no', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
                      6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten'}

# The object line's wording:
#   True  — the model's full detailed description, cleaned into the panel's voice
#           ('A silver key on a green surface with a keyring attached to it.').
#   False — a short 'A <label>.' distilled from the caption.
CONST_SHOW_OBJECT_DETAIL = True

# What the panel says when the model finds nothing. It names both honest
# possibilities; Scene_Note supplies the next action ('Check the lighting and the
# focus, then scan again.'), so this is only the explanation and carries no
# trailing full stop of its own.
CONST_EMPTY_SCENE_EXPLANATION = (
    'Either nothing is on the surface, or the model did not recognise what is there'
)

# The Florence caption template lead-ins, peeled from the front of a caption to
# expose the description (Caption_Sentence) and the noun phrase (the label
# distiller in ../Vision/Utilities/Caption, which imports this). Every granular
# piece must appear — 'in this image we can see a bolt' peels as 'in this image'
# + 'we can see' + the article. Longest variants first, only as a readability aid.
# The strings are kept verbatim; their exact content is behaviour.
CONST_LABEL_LEADINS = (
    "in this image we can see", "in the image we can see",
    "in this picture we can see", "in this image, we can see",
    "in this image there are", "in this image there is",
    "in this image we see", "here we can see", "we can also see",
    "we can see", "we see", "you can see",
    "in this image", "in the image", "in this picture", "in the picture",
    "the image shows", "this image shows", "the photo shows",
    "this is a", "this is an", "there is a", "there is an",
    "there are", "here is a", "here is an",
    "a close-up of", "a close up of", "close-up of", "close up of",
    "an image of", "a image of", "image of", "a photo of", "a picture of",
    "a photograph of", "it is a", "it is an", "showing a", "showing an",
    "shows a", "shows an",
)

# The clause boundaries the label distiller cuts a noun phrase at. Verbatim.
CONST_LABEL_BOUNDARIES = (
    ",", " is ", " are ", " was ", " with ", " that ", " which ", " has ",
    " have ", " sitting", " lying", " laying", " placed", " resting",
    " standing", " scattered", " showing", " appears", " against ", " next to",
    " on top", " on a ", " on an ", " on the ", " in the ", " in a ", " in an ",
    " across ", " and ",
)

# The most words the distilled label keeps.
CONST_LABEL_MAX_WORDS = 4

# ---- Background stripping (§ object lines never mention the background) --------- #
# STRONG background nouns — unambiguously the ground. A bare one (not bound to an
# object by 'of') makes a sentence about the background and drops it. A colour word is
# NEVER the trigger: Florence misreads the green table as 'red' as readily as 'green'
# (Image_006/007), so a colour match is worthless and the noun carries the load.
CONST_BG_NOUNS_STRONG = ('background', 'backdrop', 'table', 'tablecloth', 'cloth',
                         'felt', 'mat', 'desk', 'floor', 'sheet')

# 'surface' is a WEAK background noun: it is as often the OBJECT's surface ('the
# surface of the plate is machined', 'the surface is shiny and reflective') as the
# ground's. It counts as background ONLY when BOUND to the background — a colour word
# before it ('green surface') or a locative phrase ('on a surface', caught by the
# trailing trim) — never standing alone or bound to the object. This is what keeps
# object detail that merely says 'surface' while still dropping 'a green surface'.
CONST_BG_SURFACE_COLOURS = ('green', 'red', 'teal', 'turquoise', 'blue', 'cyan',
                            'grey', 'gray', 'brown', 'white', 'black', 'tan', 'olive')

# A trailing locative background phrase: an optional linking verb / gerund, a
# locative preposition, then a background noun (strong OR 'surface' — a trailing 'on
# a … surface' is always the ground) to the end of the sentence. This is what turns
# 'A metal washer on a green surface' into 'A metal washer'.
_BG_ALL = '(?:%s)' % '|'.join(CONST_BG_NOUNS_STRONG + ('surface',))
CONST_BG_TRAIL = re.compile(
    r'\s*(?:\b(?:is|are|was|were|it\s+is)\b\s*)?'
    r'(?:\b(?:sitting|lying|resting|laying|placed|standing|scattered|sits|lies|rests)\b\s*)?'
    r'\b(?:on|in|against|over|upon|atop|inside|beneath|under)\b\s+'
    r'[^.]*?\b(%s)\b[^.]*$' % _BG_ALL, re.IGNORECASE)

# A bare STRONG background noun — one NOT bound to an object by a following 'of'
# ('the surface of the table' still matches on 'table', which is not followed by 'of').
CONST_BG_BARE = re.compile(
    r'\b(%s)\b(?!\s+of\b)' % ('(?:%s)' % '|'.join(CONST_BG_NOUNS_STRONG)), re.IGNORECASE)

# A colour-bound 'surface' (the weak noun in a background binding): a colour word,
# optionally one word, then 'surface' — 'green surface', 'bright green surface'.
CONST_BG_SURFACE = re.compile(
    r'\b(?:%s)\b\s+(?:\w+\s+)?surface\b' % '|'.join(CONST_BG_SURFACE_COLOURS), re.IGNORECASE)

# A connective the trailing-phrase trim can leave dangling at the end ('The ring is
# shiny and' -> 'The ring is shiny'), peeled off after the trim.
CONST_BG_DANGLE = re.compile(
    r'[\s,]+(?:and|with|on|in|is|are|was|were|that|of|the|a|an|it|sitting)?\s*$', re.IGNORECASE)

# ---- Substance substitution (machined parts are never wood/paper) --------------- #
# Florence occasionally reads the concentric machining marks as wood or the plate as
# cardboard/paper; these parts are always machined metal/plastic, so the impossible
# substance guess is neutralised. Whole words only, so 'cardboard' is replaced but a
# word merely containing the letters is not. Every substitution is logged — rewriting
# what the model said is a domain assumption and must be auditable.
CONST_SUBSTANCE_WORDS = re.compile(r'\b(wood|woods|wooden|cardboard|paper)\b', re.IGNORECASE)
CONST_SUBSTANCE_REPLACEMENT = 'metal'

# ---- The global background sentence -------------------------------------------- #
# The background is captioned with Florence's concise <CAPTION> task (not the
# paragraph <MORE_DETAILED_CAPTION> the objects use): on a plain surface the detailed
# task has nothing to work with and confabulates. Even <CAPTION> can misfire, so a
# caption that is empty, runs to more than one sentence, or exceeds this many words is
# rejected for a fixed neutral string rather than written into the file as a ramble.
CONST_BACKGROUND_MAX_WORDS = 20
CONST_BACKGROUND_FALLBACK = 'The background is a plain surface.'


def Count_Word(n: int) -> str:
    """
    Description:
        The whole number n as a word for n in 0..10, otherwise as digits.

    Args:
        (1) n [int]: The count to spell.

    Returns:
        (1) parameter [string]: The count as a word ('no', 'one', ...) or digits.
    """

    return CONST_NUMBER_WORDS.get(n, str(n))


def Zone(bbox: tp.Tuple[int, int, int, int], size: tp.Tuple[int, int]) -> str:
    """
    Description:
        A coarse nine-cell position, the way a person would describe it.

        Note:
            Currently unused: object lines were changed to say what a part is, not
            where it is (the number on the coloured box carries position). Kept for
            the day a position phrase is wanted back — re-add it in Describe_Object.

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
        Tidy the model's caption into a standalone second sentence. The composer,
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


def Caption_Sentence(caption: str) -> str:
    """
    Description:
        The model's full caption as a clean, standalone description. Florence
        prefixes a fixed template ('In this image we can see a ...'); those
        lead-ins are peeled from the front so the description reads naturally, then
        Clean_Detail imposes the console's capitalisation and terminal stop. This
        is where the panel's one voice is put on the model's raw words.

    Args:
        (1) caption [string]: The model's raw caption.

    Returns:
        (1) parameter [string]: The cleaned, standalone description sentence.
    """

    text = ' '.join(caption.split()).strip()
    stripped = True
    while stripped:
        stripped = False
        low = text.lower()
        for lead in CONST_LABEL_LEADINS:
            if low.startswith(lead):
                text = text[len(lead):].lstrip(' ,')
                stripped = True
                break
    return Clean_Detail(text)


def Substitute_Substance(text: str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        Replace an impossible substance guess (wood / cardboard / paper) with 'metal'
        at word boundaries only, and return every substitution made. These parts are
        always machined metal/plastic, so the guess is neutralised — but rewriting
        what the model said is a domain assumption, so each substitution is returned
        for the audit log rather than done silently.

    Args:
        (1) text [string]: The caption text.

    Returns:
        (1) parameter [Tuple]: (the substituted text, a Vector of (level, message)
                               audit records, one 'info' per substitution).
    """

    records = []

    def _Replace(match: tp.Any) -> str:
        """
        Description:
            Record one substitution and return the replacement word.

        Args:
            (1) match [re.Match]: The matched substance word.

        Returns:
            (1) parameter [string]: CONST_SUBSTANCE_REPLACEMENT.
        """

        records.append(('info', "substituted '%s' -> '%s'"
                        % (match.group(0), CONST_SUBSTANCE_REPLACEMENT)))
        return CONST_SUBSTANCE_REPLACEMENT

    return CONST_SUBSTANCE_WORDS.sub(_Replace, text), records


def __Background_Trigger(text: str) -> tp.Optional[str]:
    """
    Description:
        The background noun that makes a sentence about the background, or None. A bare
        STRONG background noun triggers it; the weak 'surface' triggers it only when
        colour-bound ('green surface'), never standing alone — so 'the surface is
        shiny' and 'the surface of the plate is machined' are kept while 'a green
        surface' and 'the surface of the table' (the latter on its bare 'table') go.

    Args:
        (1) text [string]: The sentence (or its object-side remainder) to test.

    Returns:
        (1) parameter [string]: The matched background noun, or None.
    """

    strong = CONST_BG_BARE.search(text)
    if strong:
        return strong.group(1)
    if CONST_BG_SURFACE.search(text):
        return 'surface'
    return None


def __Strip_Sentence(core: str) -> tp.Tuple[tp.Optional[str], tp.Optional[str]]:
    """
    Description:
        Decide one sentence's fate under the background rule. `core` is the sentence
        without terminal punctuation. A trailing locative background phrase is trimmed
        ('A washer on a green surface' -> 'A washer'); if what remains is still about
        the background (see __Background_Trigger), the whole sentence is dropped. A
        sentence with no background trigger is kept untouched.

    Args:
        (1) core [string]: One sentence, without its terminal punctuation.

    Returns:
        (1) parameter [Tuple]: (the kept text or None to drop, the matched background
                               noun or None).
    """

    trail = CONST_BG_TRAIL.search(core)
    if trail:
        trimmed = core[:trail.start()].strip()
        previous = None
        while trimmed != previous:
            previous = trimmed
            trimmed = CONST_BG_DANGLE.sub('', trimmed).strip()
        if (not trimmed) or __Background_Trigger(trimmed):
            return None, trail.group(1)
        return trimmed, trail.group(1)
    trigger = __Background_Trigger(core)
    if trigger:
        return None, trigger
    return core, None


def Strip_Background(text: str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        Remove the background from an object caption so the object is described on its
        own — the background is stated once, globally (Screen_Understanding), never per
        object. A sentence is dropped only when it is ABOUT the background (a bare
        background noun), and a trailing locative background phrase is trimmed from an
        otherwise-object sentence. If stripping would empty the caption, the original is
        returned and a WARNING is recorded rather than leaving the object with no
        description.

        Every dropped sentence and trimmed phrase is returned with the background noun
        that matched, so over-stripping surfaces in the audit log instead of silently.

    Args:
        (1) text [string]: The object caption (lead-ins already peeled).

    Returns:
        (1) parameter [Tuple]: (the cleaned caption, a Vector of (level, message)
                               audit records).
    """

    kept, records = [], []
    for sentence in re.split(r'(?<=[.!?])\s+', text.strip()):
        core = sentence.strip()
        if not core:
            continue
        core_np = core.rstrip('.!?').rstrip()
        out, noun = __Strip_Sentence(core_np)
        if out is None:
            records.append(('info', "stripped background sentence (%s): '%s'" % (noun, core)))
            continue
        cleaned = out if out.endswith(('.', '!', '?')) else out + '.'
        if out != core_np:
            records.append(('info', "trimmed background phrase (%s): '%s' -> '%s'"
                            % (noun, core, cleaned)))
        kept.append(cleaned)

    result = ' '.join(kept).strip()
    if not result:
        records.append(('warning', "kept the original caption unchanged; stripping the "
                        "background would have left it empty: '%s'" % text.strip()))
        return text.strip(), records
    return result, records


def Object_Description(det: Detection_Str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        The object's line and its audit trail. The model caption is peeled of the
        Florence template (Caption_Sentence), its impossible substance guesses are
        neutralised (Substitute_Substance), and the background is stripped
        (Strip_Background) so the line describes the object alone. When no usable
        caption remains, the short 'A <label>.' stands in; a reading, if any, is
        appended.

    Args:
        (1) det [Detection_Str(object)]: The detection to describe.

    Returns:
        (1) parameter [Tuple]: (the object's line, a Vector of (level, message)
                               audit records for this object).
    """

    audit = []
    sentence = Caption_Sentence(det.Detail) if CONST_SHOW_OBJECT_DETAIL else ''
    if sentence:
        sentence, subs = Substitute_Substance(sentence)
        sentence, strips = Strip_Background(sentence)
        audit = subs + strips
    if not sentence:
        article = 'An' if det.Label[:1].lower() in 'aeiou' else 'A'
        sentence = '%s %s.' % (article, det.Label)
    if det.Text:
        sentence = sentence.rstrip('.') + ', reading “%s”.' % det.Text
    return sentence, audit


def Background_Sentence(caption: str) -> tp.Tuple[str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        The one global background sentence, from the reference caption. Florence's
        concise <CAPTION> is expected to return a single short sentence; a caption that
        is empty, multi-sentence, or longer than CONST_BACKGROUND_MAX_WORDS is rejected
        for the fixed neutral CONST_BACKGROUND_FALLBACK and a warning is recorded,
        rather than writing a paragraph of confabulation as the first line.

    Args:
        (1) caption [string]: The reference frame's raw caption.

    Returns:
        (1) parameter [Tuple]: (the background sentence, a Vector of (level, message)
                               audit records — a single warning when the fallback is used).
    """

    sentence = Caption_Sentence(caption)
    words = len(sentence.split())
    count = len([part for part in re.split(r'[.!?]+', sentence) if part.strip()])
    if (not sentence) or count > 1 or words > CONST_BACKGROUND_MAX_WORDS:
        return CONST_BACKGROUND_FALLBACK, [('warning',
                "background caption unusable (%d words, %d sentence(s)); used the neutral "
                "fallback instead of: '%s'" % (words, count, ' '.join(caption.split())))]
    return sentence, []


def Describe_Object(det: Detection_Str, size: tp.Tuple[int, int]) -> str:
    """
    Description:
        One line for one detection — what the object is, not where it is (the operator
        reads the number off the coloured box, so a location in words earns nothing).
        Delegates to Object_Description and drops the audit; use Object_Description
        directly when the audit is wanted. (`size` is unused now that the zone is gone;
        kept so the call site is unchanged.)

    Args:
        (1) det [Detection_Str(object)]: The detection to describe.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).

    Returns:
        (1) parameter [string]: The object's line of text.
    """

    return Object_Description(det)[0]


def Scene_Note(objects: tp.List[Detection_Str], size: tp.Tuple[int, int], caption: str = '') -> str:
    """
    Description:
        The closing note. It carries the empty-scene explanation and its next
        action, and otherwise stays silent so the panel is just the objects.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).
        (3) caption [string]: An optional leading explanation (e.g. the empty-scene text).

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
        count; every line below describes an object alone (each det.Sentence was
        already stripped of the background by Compose).

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
    # falls back to the neutral string here too.
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


def Object_Line(index: int, det: Detection_Str) -> str:
    """
    Description:
        One numbered object line ('Obj. N - <sentence>'), the single source of the
        per-object line for BOTH the file and the panel, so the numbering and wording
        live in one place and cannot be copied out of step. The number is 1-based and
        the sentence is det.Sentence (already stripped of the background by Compose).

    Args:
        (1) index [int]: The object's 0-based position in the list.
        (2) det [Detection_Str(object)]: The object.

    Returns:
        (1) parameter [string]: The numbered line.
    """

    return 'Obj. %d - %s' % (index + 1, det.Sentence)


def Compose(objects: tp.List[Detection_Str], size: tp.Tuple[int, int],
            caption: str = '') -> tp.Tuple[tp.List[Detection_Str], str, tp.List[tp.Tuple[str, str]]]:
    """
    Description:
        Write the line for every object (into det.Sentence) and return the objects
        alongside the note and the post-processing audit. Each line is stripped of the
        background and has its impossible substance guesses neutralised; the audit
        records every strip and substitution, tagged with the object index, so nothing
        the composer rewrote is silent. The objects are never reordered here — their
        order is the operator-visible index contract.

        The lead line is NOT built here: the view and the descriptions file both render
        it from the shared Screen_Header, so there is one source for it and no second
        copy to drift.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).
        (3) caption [string]: An optional leading explanation for the note.

    Returns:
        (1) parameter [Tuple]: (objects, note, audit), where audit is a Vector of
                               (level, message) records.
    """

    audit = []
    for i, det in enumerate(objects):
        det.Sentence, records = Object_Description(det)
        audit.extend(('%s' % level, 'Obj. %d: %s' % (i + 1, message)) for level, message in records)
    return objects, Scene_Note(objects, size, caption), audit
