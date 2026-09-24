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

# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan domain — report composer (the label vocabulary lives there)
#   ../Reporting/Core
from Reporting.Core import (CONST_LABEL_LEADINS, CONST_LABEL_OPENERS, CONST_LABEL_BOUNDARIES,
                            CONST_LABEL_HEDGES, CONST_LABEL_MAX_WORDS)

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
        A two-to-three word noun phrase for the label, distilled from a caption.

        Describe_Object renders the label as 'A <label>.', so a paragraph there
        produces a line that is not a sentence. The front matter and any trailing
        clause are stripped and the phrase is capped; the full caption survives
        untouched in Detection_Str.Detail as the line's second sentence, so an
        imperfect distillation loses nothing.

    Args:
        (1) caption [string]: The model's raw caption.

    Returns:
        (1) parameter [string]: The distilled label, or 'object' if nothing remains.
    """

    text = ' '.join(caption.split()).strip().rstrip('.')
    # Florence stacks lead-ins ('The image shows a close-up of a hex bolt'), and Gemma opens
    # 'The object is a …', so strip both repeatedly until the front is the noun phrase itself.
    stripped = True
    while stripped:
        stripped = False
        low = text.lower()
        for lead in CONST_LABEL_OPENERS + CONST_LABEL_LEADINS:
            if low.startswith(lead):
                text = text[len(lead):].lstrip(' ,')
                stripped = True
                break

    # Join the comma-separated adjective run; stop at a comma that opens a new clause.
    segments = [segment.strip() for segment in text.split(',')]
    phrase = segments[0]
    for segment in segments[1:]:
        first = segment.split()[0].lower() if segment.split() else ''
        if not first or first.endswith('ing') or first in CONST_LABEL_HEDGES:
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

    # Coordination: one word after 'or' is an alternative noun (dropped with 'or'); more words
    # mean 'or' joined modifiers in front of the noun (only 'or <modifier>' is dropped).
    before, joined, after = text.partition(' or ')
    if joined:
        rest = after.split()
        text = before if len(rest) <= 1 else ' '.join([before] + rest[1:])

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
    text = ' '.join(words[-CONST_LABEL_MAX_WORDS:]).strip(' ,.')
    return text.lower() if text else 'object'
