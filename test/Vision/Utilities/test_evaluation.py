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
# File Name: ../test/Vision/Utilities/test_evaluation.py
## =========================================================================== ##

# System (Default)
import json
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan vision — the answer key's reader and the scoring rules
#   ../Vision/Utilities/Evaluation
from Vision.Utilities.Evaluation import (Load_Answer_Key, Score_Type, Score_Material, Score_Colour, Score_Object, Tally,
                                         Evaluation_Error_Cls, CONST_ANSWER_KEY_FILE)

"""
Description:
    The describer's answer key and its scoring rules (Vision.Utilities.Evaluation), without a model:
    the key records the owner's answers, and each rule scores the way the key's "rules" block states.
    The key is the previous test set's (Data/Images/Test/All/answer_key.json at 1061966, copied byte for
    byte): its frames are gone, but its rules, patterns and the owner's answers are the data the scoring
    is tested on. The current set (Data/Images/Test) has no key yet, so nothing checks a key against its
    inventory until one is written. The describer run itself (Example/Vision/evaluate_describer.py) needs
    the weights and is not part of the suite.
"""
# The previous test set's answer key, kept as the scoring rules' test data.
#   Unit [string]
CONST_KEY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'answer_key_1061966.json')


@pytest.fixture(scope='module')
def key() -> dict:
    """The previous test set's answer key, through its reader."""
    return Load_Answer_Key(CONST_KEY)


def test_the_key_records_the_owners_answers(key) -> None:
    """
    Description:
        The materials the owner gave from the physical parts (2026-09-29): the red block is anodised
        aluminium, the white washer and the bushing aluminium. Every object counts in the totals (the
        owner's choice); the clipped hex nuts 5.3 and 6.2 carry a note saying why their crop is special.
    """

    objects = {(entry['frame'], entry['index']): entry for entry in key['objects']}
    for place in (('Image_006', 3), ('Image_007', 2)):
        assert (objects[place]['material'], objects[place]['material_detail']) == ('metal', 'anodised aluminium')
    for place in (('Image_001', 5), ('Image_002', 4), ('Image_008', 5), ('Image_002', 2)):
        assert (objects[place]['material'], objects[place]['material_detail']) == ('metal', 'aluminium')
    assert not [entry for entry in key['objects'] if 'exclude_from_totals' in entry]
    assert sorted(place for place, entry in objects.items() if entry.get('note')) == [('Image_005', 3), ('Image_006', 2)]


def test_a_named_type_scores_and_a_feature_is_not_a_type(key) -> None:
    """
    Description:
        A plain "washer" is correct; "octagonal metal washer" for a hex nut is wrong; an "outer ring" is
        a feature, not the part called a ring; "ring-shaped" is; a plain "ring" for the bushing is not
        decidable; "component" states no type.
    """

    classes = key['type_classes']
    assert Score_Type('The object is a circular, metallic washer with a hole.', classes['washer'], key) == 'correct'
    assert Score_Type('The object is a small, roughly octagonal metal washer.', classes['hex_nut'], key) == 'wrong'
    assert Score_Type('The part is a hexagonal nut made of metal.', classes['hex_nut'], key) == 'correct'
    assert Score_Type('The part is a circular object with a brighter outer ring.', classes['washer'], key) == 'not stated'
    assert Score_Type('The part is a circular, ring-shaped object.', classes['washer'], key) == 'wrong'
    assert Score_Type('The part is a metal ring with a central bore.', classes['bushing'], key) == 'not decidable'
    assert Score_Type('The part is a circular, metallic component.', classes['hex_nut'], key) == 'not stated'


def test_a_feature_ring_is_no_type_claim_but_a_named_type_still_counts(key) -> None:
    """
    Description:
        A type counts as claimed only after a naming cue ("is a", "appears to be a" ...): "the outer white
        ring" or "the metal ring" names a feature, and "a concentric ring design" is a feature too, so
        neither is a type claim. A correct name counts wherever it stands. (The 8-bit E4B texts the
        whole-text rule scored wrong, 2026-09-29.)
    """

    washer = key['type_classes']['washer']
    later = ('The part is circular with a concentric, layered structure. It is enclosed by a bright, '
             'outer white ring. The surface of the metal ring appears clean.')
    assert Score_Type(later, washer, key) == 'not stated'
    assert Score_Type('The part is circular with a distinct concentric ring design. It is white.', washer, key) == 'not stated'
    assert Score_Type('The part is round and flat. It is a plain washer with a central hole.', washer, key) == 'correct'


def test_conflicting_type_names_are_a_hedge(key) -> None:
    """
    Description:
        When a claim offers the right type and another part type as alternatives ("washer or cap",
        "washer or ring": E4B 4-bit's six large washers, 2026-09-29), or a claim names a wrong type while
        the right one appears elsewhere, the names conflict and the type is not stated, as a material
        hedge is. Synonyms of the right type are no conflict ("bolt or screw").
    """

    classes = key['type_classes']
    assert Score_Type('The object is a circular, metallic washer or cap. It is grey.', classes['washer'], key) == 'not stated'
    assert Score_Type('The object is a circular metal washer or ring, silver.', classes['washer'], key) == 'not stated'
    assert Score_Type('The object is a metallic bolt or screw. It is threaded.', classes['screw'], key) == 'correct'
    later = 'The object is a small, roughly octagonal metal washer. It could also be a hex nut.'
    assert Score_Type(later, classes['hex_nut'], key) == 'not stated'
    assert Score_Type('The object is a small metal washer or cap. It is dull.', classes['hex_nut'], key) == 'wrong'


def test_a_wrong_name_after_the_first_sentence_counts(key) -> None:
    """
    Description:
        A naming claim in a later sentence counts: E4B 4-bit's comb (1.3) is "a small, elongated ...
        plastic or composite part" and then "suggesting it is a component or mold insert", which names
        another part type, so the type is wrong. With the right name in the text, the same later claim
        makes the names conflict: not stated.
    """

    comb = key['type_classes']['comb']
    text = ('The object appears to be a small, elongated plastic part. It has text molded onto it, suggesting it is '
            'a component or mold insert.')
    assert Score_Type(text, comb, key) == 'wrong'
    assert Score_Type('The object is a grey plastic comb. It looks like a mold insert.', comb, key) == 'not stated'


def test_a_material_outside_metal_and_plastic_is_wrong_alone(key) -> None:
    """
    Description:
        A material the key has no class for counts: named alone it is wrong, as every part in the key is
        metal or plastic (E4B 8-bit's robot, 3.3: "a soft, possibly felt or fabric material").
    """

    assert Score_Material('made of a soft, possibly felt or fabric material', 'plastic', key) == 'wrong'


def test_the_right_material_beside_another_is_a_hedge(key) -> None:
    """
    Description:
        Material hedges score as type hedges do: the right material named beside any other material is
        not stated, whether the other is the key's other class or another material (E4B 4-bit's comb and
        robot, "plastic or composite"; the 12B's washer and robot, "metallic or ceramic", "plastic or
        ceramic", 2026-09-29). The right material alone stays correct.
    """

    assert Score_Material('made of plastic or composite', 'plastic', key) == 'not stated'
    assert Score_Material('possibly metallic or ceramic', 'metal', key) == 'not stated'
    assert Score_Material('a solid plastic or painted metal', 'plastic', key) == 'not stated'
    assert Score_Material('made of white plastic', 'plastic', key) == 'correct'


def test_a_plural_synonym_counts(key) -> None:
    """
    Description:
        A synonym counts in the plural: E4B 8-bit's comb label (8.3) "rectangular white plastic strips".
    """

    assert Score_Type('The part consists of four rectangular white plastic strips.', key['type_classes']['comb'], key) == 'correct'


def test_a_material_hedge_between_metal_and_plastic_is_not_stated(key) -> None:
    """
    Description:
        One material class named scores against the key; "plastic or painted metal" names both and is
        not stated; "metallic or composite" on a plastic part names only a wrong material: wrong.
    """

    assert Score_Material('made of steel', 'metal', key) == 'correct'
    assert Score_Material('a metallic grey component', 'plastic', key) == 'wrong'
    assert Score_Material('a solid plastic or painted metal', 'plastic', key) == 'not stated'
    assert Score_Material('a metallic or composite material', 'plastic', key) == 'wrong'
    assert Score_Material('a solid, opaque material', 'metal', key) == 'not stated'


def test_a_colour_is_correct_only_when_one_of_its_terms_is_named() -> None:
    """
    Description:
        A colour term names the colour (at a word start, so "blue-violet" counts); no term, not stated.
    """

    assert Score_Colour('a vibrant, mottled blue-violet colour', ['blue', 'violet']) == 'correct'
    assert Score_Colour('a smooth metallic surface', ['blue']) == 'not stated'


def test_every_object_counts_in_the_totals(key) -> None:
    """
    Description:
        Tally counts every scored object, the clipped hex nuts included (the owner, 2026-09-29).
    """

    scores = [(entry, Score_Object('a circular metal part', entry, key)) for entry in key['objects']]
    assert sum(Tally(scores)['type'].values()) == len(key['objects']) == 37


def test_an_unusable_key_is_refused_with_its_reason(tmp_path, key) -> None:
    """
    Description:
        A missing key, and a key with an object of an undefined type class, stop with a sentence naming
        the file and the fault.
    """

    with pytest.raises(Evaluation_Error_Cls, match='does not exist'):
        Load_Answer_Key(str(tmp_path / 'absent.json'))
    broken = dict(key, objects=[dict(key['objects'][0], type_class='sprocket')])
    path = tmp_path / CONST_ANSWER_KEY_FILE
    path.write_text(json.dumps(broken))
    with pytest.raises(Evaluation_Error_Cls, match='type class "sprocket"'):
        Load_Answer_Key(str(path))
