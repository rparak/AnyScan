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
# File Name: ../Vision/Utilities/Caption.py
## =========================================================================== ##

# Custom Lib.: AnyScan domain — report composer (the label vocabulary lives there)
#   ../Reporting/Core
from Reporting.Core import (CONST_LABEL_OPENERS, CONST_LABEL_BOUNDARIES, CONST_LABEL_HEDGES,
                            CONST_LABEL_MAX_WORDS, CONST_LABEL_ALTERNATIVE_WORDS)

"""
Description:
    Initialization of constants.

    The label distiller: a short noun-phrase label from a description (Condense_Label). Pure
    text — no model and no heavy runtime — so this module imports cheaply. (The Florence-2
    caption pass that also lived here was removed with the Florence describer.)
"""


def Condense_Label(caption: str) -> str:
    """
    Description:
        A short noun phrase for the label, distilled from a caption: at most
        CONST_LABEL_MAX_WORDS words, plus CONST_LABEL_ALTERNATIVE_WORDS to keep an
        alternative after 'or'.

        The label is the log's 'Object detected: type=...', and Object_Description's
        'A <label>.' when no description remains, so a paragraph there produces a line
        that is not a sentence. The front matter and any trailing clause are stripped and
        the phrase is capped; the full caption survives untouched in Detection_Str.Detail,
        which is the object's line, so an imperfect distillation loses nothing.

    Args:
        (1) caption [string]: The model's raw caption.

    Returns:
        (1) parameter [string]: The distilled label, or 'object' if nothing remains.
    """

    text = ' '.join(caption.split()).strip().rstrip('.')
    # Gemma opens 'The object is a …' or 'This is a …': peel the opener so the front is the noun
    # phrase itself. Longest first, so 'the part is shaped like' wins over 'the part is'.
    low = text.lower()
    for opener in sorted(CONST_LABEL_OPENERS, key=len, reverse=True):
        if low.startswith(opener):
            text = text[len(opener):].lstrip(' ,')
            break

    # Join the comma-separated adjective run; stop at a comma that opens a new clause: an '-ing'
    # participle, but not a hyphenated adjective ('metallic-looking object' is one phrase).
    segments = [segment.strip() for segment in text.split(',')]
    phrase = segments[0]
    for segment in segments[1:]:
        first = segment.split()[0].lower() if segment.split() else ''
        if not first or (first.endswith('ing') and '-' not in first) or first in CONST_LABEL_HEDGES:
            break
        phrase += ' ' + segment
    text = phrase

    low = text.lower()
    cut = len(text)
    for boundary in CONST_LABEL_BOUNDARIES:
        idx = low.find(boundary)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut].strip(' ,')

    # Coordination: 'or' is kept, with its alternative ('washer or cap', 'plastic or ceramic
    # component'): it is the model's hedge, and the label must not state more than the text does.
    # The cap below keeps CONST_LABEL_ALTERNATIVE_WORDS more words for it.
    alternative = ' or ' in text

    for article in ('a ', 'an ', 'the '):
        if text.lower().startswith(article):
            text = text[len(article):]
            break

    # A trailing past participle is not the head noun ('part rendered in …' -> 'part'). Only
    # '-ed' words of five letters or more: '-ing' is never dropped here because many part names
    # end in it (ring, bearing, bushing, housing, fitting, spring), and a short '-ed' word may be
    # a noun or colour ('red').
    words = text.split()
    while (len(words) > 1 and '-' not in words[-1] and len(words[-1]) >= 5
           and words[-1].lower().endswith('ed')):
        words.pop()
    keep = CONST_LABEL_MAX_WORDS + (CONST_LABEL_ALTERNATIVE_WORDS if alternative else 0)
    text = ' '.join(words[-keep:]).strip(' ,.')
    return text.lower() if text else 'object'
