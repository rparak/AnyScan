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


def Describe_Object(det: Detection_Str, size: tp.Tuple[int, int]) -> str:
    """
    Description:
        One line for one detection — what the object is, not where it is.

        With CONST_SHOW_OBJECT_DETAIL the line is the model's full description,
        cleaned into the console's voice; otherwise it is the short 'A <label>.'
        Position is deliberately not stated: the operator reads the number off the
        coloured box on the frame, so a coarse location in words earns nothing.
        (`size` is unused now that the zone is gone; kept so the call site is
        unchanged.) The index is not repeated here either; the list prints
        'Object N:' in the box's colour, and duplicating the number reads as a
        stutter.

    Args:
        (1) det [Detection_Str(object)]: The detection to describe.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).

    Returns:
        (1) parameter [string]: The object's line of text.
    """

    sentence = Caption_Sentence(det.Detail) if CONST_SHOW_OBJECT_DETAIL else ''
    if not sentence:
        article = 'An' if det.Label[:1].lower() in 'aeiou' else 'A'
        sentence = '%s %s.' % (article, det.Label)
    if det.Text:
        sentence = sentence.rstrip('.') + ', reading “%s”.' % det.Text
    return sentence


def Summarise(objects: tp.List[Detection_Str]) -> str:
    """
    Description:
        The lead sentence introducing the located objects.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects.

    Returns:
        (1) parameter [string]: The summary sentence.
    """

    n = len(objects)
    if n == 0:
        return 'No objects were located in this frame.'
    if n == 1:
        return 'The frame contains one object, described as follows:'
    return 'The frame contains %s objects, which are described as follows:' % Count_Word(n)


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


def Compose(objects: tp.List[Detection_Str], size: tp.Tuple[int, int],
            caption: str = '') -> tp.Tuple[tp.List[Detection_Str], str, str]:
    """
    Description:
        Write the line for every object (into det.Sentence) and return the objects
        alongside the summary and the note. The objects are never reordered here —
        their order is the operator-visible index contract.

    Args:
        (1) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (2) size [Vector<int> 1x2]: The frame size as (width, height).
        (3) caption [string]: An optional leading explanation for the note.

    Returns:
        (1) parameter [Tuple]: (objects, summary, note).
    """

    for det in objects:
        det.Sentence = Describe_Object(det, size)
    return objects, Summarise(objects), Scene_Note(objects, size, caption)
