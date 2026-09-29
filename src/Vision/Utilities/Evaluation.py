## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# File Name: ../Vision/Utilities/Evaluation.py
## =========================================================================== ##

# System (Default)
import json
import os
import re
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    Describer quality against a confirmed answer key: the key's reader (Load_Answer_Key, the one
    reader of answer_key.json) and the scoring of one description on part type, material and colour
    (Score_Object), then the totals (Tally). The rules are the key's own, stated in its "rules" block;
    the patterns they apply are data in the key, not code here, and so is which objects are left out
    of the totals. Pure text matching, no model, so the rules are tested on their own
    (test/Vision/Utilities/test_evaluation.py). Example/Vision/evaluate_describer.py runs the describer
    and scores it.
"""
# The answer key's file name, beside the frames it describes (Evaluation.Frames).
#   Unit [string]
CONST_ANSWER_KEY_FILE = 'answer_key.json'
# The scored attributes, and the outcomes a score takes.
#   Unit [Tuple<string>]
CONST_ATTRIBUTES = ('type', 'material', 'colour')
CONST_CORRECT, CONST_WRONG, CONST_NOT_STATED, CONST_NOT_DECIDABLE = 'correct', 'wrong', 'not stated', 'not decidable'
CONST_OUTCOMES = (CONST_CORRECT, CONST_WRONG, CONST_NOT_STATED, CONST_NOT_DECIDABLE)
# The fields every object in the key carries.
#   Unit [Tuple<string>]
CONST_OBJECT_FIELDS = ('frame', 'index', 'type', 'type_class', 'material', 'colour', 'colour_terms', 'source', 'status')
# Where one sentence ends and the next begins: a full stop, question or exclamation mark, then space.
#   Unit [string] (regular expression)
CONST_SENTENCE_END = r'(?<=[.!?])\s+'


class Evaluation_Error_Cls(RuntimeError):
    """
    Description:
        Raised when the answer key cannot be used: missing, unreadable, or incomplete. Its message is
        a full sentence naming the file and what to fix.
    """


def Load_Answer_Key(path: str) -> tp.Dict[str, tp.Any]:
    """
    Description:
        Read and check the answer key: every object has the key's fields, a type class the key
        defines and a material the key's material classes name, and no frame and index is listed twice.

    Args:
        (1) path [string]: The answer_key.json file.

    Returns:
        (1) parameter [Dict<string, Any>]: The key, as the file holds it.
    """

    if not os.path.isfile(path):
        raise Evaluation_Error_Cls('The answer key "%s" does not exist. It sits beside the frames it describes '
                                   '(the configuration\'s Evaluation.Frames).' % path)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            key = json.load(handle)
    except (OSError, ValueError) as error:
        raise Evaluation_Error_Cls('The answer key "%s" could not be read (%s). Fix the file and run again.'
                                   % (path, error)) from error
    for field in ('rules', 'materials', 'type_classes', 'objects'):
        if field not in key:
            raise Evaluation_Error_Cls('The answer key "%s" has no "%s" block.' % (path, field))
    seen = set()
    for entry in key['objects']:
        missing = [field for field in CONST_OBJECT_FIELDS if field not in entry]
        name = '%s object %s' % (entry.get('frame'), entry.get('index'))
        if missing:
            raise Evaluation_Error_Cls('In the answer key "%s", %s has no %s.' % (path, name, ', '.join(missing)))
        if entry['type_class'] not in key['type_classes']:
            raise Evaluation_Error_Cls('In the answer key "%s", %s names the type class "%s", which the key does not '
                                       'define.' % (path, name, entry['type_class']))
        if entry['material'] not in key['materials']:
            raise Evaluation_Error_Cls('In the answer key "%s", %s has the material "%s"; the key\'s materials are %s.'
                                       % (path, name, entry['material'], ', '.join(sorted(key['materials']))))
        if (entry['frame'], entry['index']) in seen:
            raise Evaluation_Error_Cls('The answer key "%s" lists %s twice.' % (path, name))
        seen.add((entry['frame'], entry['index']))
    return key


def _Matches(text: str, patterns: tp.List[str]) -> bool:
    """
    Description:
        Whether any pattern occurs in the text, ignoring case.

    Args:
        (1) text [string]: The description.
        (2) patterns [Vector<string>]: Regular expressions.

    Returns:
        (1) parameter [bool]: True when one matches.
    """

    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def Naming_Sentence(text: str) -> str:
    """
    Description:
        The sentence in which a description names the part: its first ("The object is a ...", "This is
        a ..."). The sentences after it describe features, surface and condition.

    Args:
        (1) text [string]: The description.

    Returns:
        (1) parameter [string]: The first sentence, or the whole text when it has only one.
    """

    return re.split(CONST_SENTENCE_END, text.strip(), maxsplit=1)[0]


def _Alternatives(sentence: str) -> tp.List[tp.Tuple[str, str]]:
    """
    Description:
        The word pairs a sentence offers as alternatives: "X or Y" (an article after "or" skipped).

    Args:
        (1) sentence [string]: The sentence.

    Returns:
        (1) parameter [Vector<Tuple<string> 1x2>]: The (X, Y) pairs, in order.
    """

    return re.findall(r'([\w-]+) or (?:an? |the )?([\w-]+)', sentence, re.IGNORECASE)


def Score_Type(text: str, type_class: tp.Dict[str, tp.List[str]], type_nouns: tp.Sequence[str] = ()) -> str:
    """
    Description:
        The part type's outcome. Correct when a "correct" pattern occurs anywhere in the text, unless the
        names conflict: the naming sentence offers the right type and another part type (a type_nouns
        word that is not a synonym) as alternatives, "washer or cap", or names a wrong type while the
        right one appears only later. Conflicting names are a hedge, not stated, as "plastic or painted
        metal" is for material. Without a correct name: wrong when a "wrong" pattern occurs in the
        naming sentence, not decidable for an "undecidable" one there, otherwise not stated. A wrong or
        undecidable term after the naming sentence names a feature ("the outer white ring"), not the
        part. (Condense_Label's short label was tried as the naming and rejected: it drops names the
        text gives, e.g. "This is a small robot figure" condenses to "this".)

    Args:
        (1) text [string]: The description.
        (2) type_class [Dict<string, Vector<string>>]: The class's "correct", "wrong" and optional
                                                        "undecidable" patterns.
        (3) type_nouns [Vector<string>]: Patterns for every part type, to recognise an alternative that
                                         names another type (the key's "type_nouns").

    Returns:
        (1) parameter [string]: One of CONST_OUTCOMES.
    """

    naming = Naming_Sentence(text)
    named_wrong = _Matches(naming, type_class.get('wrong', []))
    if _Matches(text, type_class['correct']):
        offered = any(_Matches(one, type_class['correct']) and _Matches(other, list(type_nouns))
                      and not _Matches(other, type_class['correct'])
                      for pair in _Alternatives(naming) for one, other in (pair, pair[::-1]))
        right_in_naming = _Matches(naming, type_class['correct'])
        return CONST_NOT_STATED if offered or (named_wrong and not right_in_naming) else CONST_CORRECT
    if named_wrong:
        return CONST_WRONG
    if _Matches(naming, type_class.get('undecidable', [])):
        return CONST_NOT_DECIDABLE
    return CONST_NOT_STATED


def Score_Material(text: str, material: str, materials: tp.Dict[str, tp.List[str]]) -> str:
    """
    Description:
        The material's outcome: the material classes the text names; one class, correct when it is
        the key's material and wrong otherwise; both (a hedge) or none, not stated.

    Args:
        (1) text [string]: The description.
        (2) material [string]: The key's material class for the object.
        (3) materials [Dict<string, Vector<string>>]: Each material class's patterns.

    Returns:
        (1) parameter [string]: One of CONST_OUTCOMES.
    """

    named = [name for name, patterns in materials.items() if _Matches(text, patterns)]
    if len(named) != 1:
        return CONST_NOT_STATED
    return CONST_CORRECT if named[0] == material else CONST_WRONG


def Score_Colour(text: str, colour_terms: tp.List[str]) -> str:
    """
    Description:
        The colour's outcome: correct when the text names one of the object's colour terms, otherwise
        not stated (a wrong colour is not scored; see the key's rules).

    Args:
        (1) text [string]: The description.
        (2) colour_terms [Vector<string>]: The words that name the object's colour in its crop.

    Returns:
        (1) parameter [string]: CONST_CORRECT or CONST_NOT_STATED.
    """

    return CONST_CORRECT if _Matches(text, [r'\b%s' % re.escape(term) for term in colour_terms]) else CONST_NOT_STATED


def Score_Object(text: str, entry: tp.Dict[str, tp.Any], key: tp.Dict[str, tp.Any]) -> tp.Dict[str, str]:
    """
    Description:
        One description's outcome on each scored attribute.

    Args:
        (1) text [string]: The description.
        (2) entry [Dict<string, Any>]: The object's entry in the key.
        (3) key [Dict<string, Any>]: The whole key (its type and material classes).

    Returns:
        (1) parameter [Dict<string, string>]: Attribute -> outcome.
    """

    return {'type': Score_Type(text, key['type_classes'][entry['type_class']], key.get('type_nouns', ())),
            'material': Score_Material(text, entry['material'], key['materials']),
            'colour': Score_Colour(text, entry['colour_terms'])}


def Tally(scores: tp.List[tp.Tuple[tp.Dict[str, tp.Any], tp.Dict[str, str]]],
          include_excluded: bool = False) -> tp.Dict[str, tp.Dict[str, int]]:
    """
    Description:
        The totals: per attribute, how many objects had each outcome. Objects the key marks
        "exclude_from_totals" count only when include_excluded is True.

    Args:
        (1) scores [Vector<Tuple<Dict, Dict>>]: Each object's key entry and its outcomes.
        (2) include_excluded [bool]: Count the objects the key leaves out of the totals.

    Returns:
        (1) parameter [Dict<string, Dict<string, int>>]: Attribute -> outcome -> count.
    """

    totals = {attribute: {outcome: 0 for outcome in CONST_OUTCOMES} for attribute in CONST_ATTRIBUTES}
    for entry, outcome in scores:
        if entry.get('exclude_from_totals') and not include_excluded:
            continue
        for attribute in CONST_ATTRIBUTES:
            totals[attribute][outcome[attribute]] += 1
    return totals
