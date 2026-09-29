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
import glob
import importlib.util
import json
import os
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan vision — the answer key's reader and the scoring rules
#   ../Vision/Utilities/Evaluation
from Vision.Utilities.Evaluation import (Load_Answer_Key, Naming_Sentence, Score_Type, Score_Material, Score_Colour, Score_Object, Tally,
                                         Evaluation_Error_Cls, CONST_ANSWER_KEY_FILE)

"""
Description:
    The describer's answer key and its scoring rules (Vision.Utilities.Evaluation), without a model:
    the shipped key covers the pinned test set as CONST_INVENTORY counts it and records the owner's
    answers, and each rule scores the way the key's "rules" block states. The describer run itself
    (Example/Vision/evaluate_describer.py) needs the weights and is not part of the suite.
"""
# The pinned test set, its answer key, and the inventory that counts its objects.
#   Unit [string]
CONST_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
CONST_FRAMES = os.path.join(CONST_ROOT, 'Data', 'Images', 'Test', 'All')
CONST_KEY = os.path.join(CONST_FRAMES, CONST_ANSWER_KEY_FILE)
CONST_PIPELINE_TESTS = os.path.join(CONST_ROOT, 'test', 'integration', 'test_pipeline.py')


@pytest.fixture(scope='module')
def key() -> dict:
    """The shipped answer key, through its reader."""
    return Load_Answer_Key(CONST_KEY)


def test_the_key_numbers_every_object_the_inventory_counts(key) -> None:
    """
    Description:
        The key names exactly the frames of the pinned set, and per frame exactly the objects
        CONST_INVENTORY counts, numbered 1..n, so a moved or added frame fails here without the weights.
    """

    spec = importlib.util.spec_from_file_location('pipeline_tests', CONST_PIPELINE_TESTS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frames = sorted(os.path.splitext(os.path.basename(path))[0] for path in glob.glob(os.path.join(CONST_FRAMES, 'Image_[0-9]*.png')))
    counted = {os.path.splitext(name)[0]: count for name, count in module.CONST_INVENTORY.items()}
    for frame in frames:
        indices = sorted(entry['index'] for entry in key['objects'] if entry['frame'] == frame)
        assert indices == list(range(1, counted[frame] + 1)), frame
    assert sorted({entry['frame'] for entry in key['objects']}) == frames


def test_the_key_records_the_owners_answers(key) -> None:
    """
    Description:
        The materials the owner gave from the physical parts (2026-09-29): the red block is anodised
        aluminium, the white washer and the bushing aluminium; the clipped hex nuts 5.3 and 6.2 are the
        only objects left out of the totals, each with its reason.
    """

    objects = {(entry['frame'], entry['index']): entry for entry in key['objects']}
    for place in (('Image_006', 3), ('Image_007', 2)):
        assert (objects[place]['material'], objects[place]['material_detail']) == ('metal', 'anodised aluminium')
    for place in (('Image_001', 5), ('Image_002', 4), ('Image_008', 5), ('Image_002', 2)):
        assert (objects[place]['material'], objects[place]['material_detail']) == ('metal', 'aluminium')
    excluded = sorted(place for place, entry in objects.items() if entry.get('exclude_from_totals'))
    assert excluded == [('Image_005', 3), ('Image_006', 2)]


def test_a_named_type_wins_over_a_wrong_one_and_a_feature_is_not_a_type(key) -> None:
    """
    Description:
        A plain "washer" is correct; "octagonal metal washer" for a hex nut is wrong; an "outer ring" is
        a feature, not the part called a ring; "ring-shaped" is; a plain "ring" for the bushing is not
        decidable; "component" states no type.
    """

    classes = key['type_classes']
    assert Score_Type('a circular, metallic washer with a hole', classes['washer'], key['type_nouns']) == 'correct'
    assert Score_Type('a small, roughly octagonal metal washer', classes['hex_nut']) == 'wrong'
    assert Score_Type('a hexagonal nut made of a metallic material', classes['hex_nut']) == 'correct'
    assert Score_Type('a circular object with a brighter outer ring', classes['washer']) == 'not stated'
    assert Score_Type('a ring-shaped object with a white outer surface', classes['washer']) == 'wrong'
    assert Score_Type('a metal ring with a central bore', classes['bushing']) == 'not decidable'
    assert Score_Type('a circular, metallic component', classes['hex_nut']) == 'not stated'


def test_a_feature_ring_is_no_type_claim_but_a_named_type_still_counts(key) -> None:
    """
    Description:
        A wrong type counts only where the text names the part, its first sentence: "the outer white
        ring" or "the metal ring" later on names a feature, and "a concentric ring design" in the naming
        sentence is a feature too, so neither is a type claim. A correct name still counts wherever it
        stands, and a wrong naming in the first sentence stays wrong. (The 8-bit E4B texts that the
        whole-text rule scored wrong, 2026-09-29.)
    """

    washer, nut = key['type_classes']['washer'], key['type_classes']['hex_nut']
    later = ('The part is circular with a concentric, layered structure. It is enclosed by a bright, '
             'outer white ring. The surface of the metal ring appears clean.')
    assert Naming_Sentence(later) == 'The part is circular with a concentric, layered structure.'
    assert Score_Type(later, washer) == 'not stated'
    assert Score_Type('The part is circular with a distinct concentric ring design. It is white.', washer) == 'not stated'
    assert Score_Type('The object is a circular, metallic washer. The rim is dull.', washer, key['type_nouns']) == 'correct'
    assert Score_Type('The part is round and flat. It is a plain washer with a central hole.', washer) == 'correct'
    assert Score_Type('The object is a small, roughly octagonal metal washer. The rim is dull.', nut) == 'wrong'


def test_conflicting_type_names_are_a_hedge(key) -> None:
    """
    Description:
        When the naming sentence offers the right type and another part type as alternatives ("washer or
        cap", "washer or ring": E4B 4-bit's six large washers, 2026-09-29), or names a wrong type while the
        right one appears only later ("washer" first, "nut" later), the names conflict and the type is not
        stated, as a material hedge is. Synonyms of the right type are no conflict ("bolt or screw").
    """

    nouns, classes = key['type_nouns'], key['type_classes']
    assert Score_Type('The object is a circular, metallic washer or cap. It is grey.', classes['washer'], nouns) == 'not stated'
    assert Score_Type('The object is a circular metal washer or ring, silver.', classes['washer'], nouns) == 'not stated'
    assert Score_Type('The object is a metallic bolt or screw. It is threaded.', classes['screw'], nouns) == 'correct'
    later = 'The object is a small, roughly octagonal metal washer. It could also be a hex nut.'
    assert Score_Type(later, classes['hex_nut'], nouns) == 'not stated'
    assert Score_Type('The object is a small metal washer or cap. It is dull.', classes['hex_nut'], nouns) == 'wrong'


def test_a_material_hedge_between_metal_and_plastic_is_not_stated(key) -> None:
    """
    Description:
        One material class named scores against the key; "plastic or painted metal" names both and is
        not stated; "plastic or ceramic" and "metallic or composite" count as the class they name.
    """

    materials = key['materials']
    assert Score_Material('made of steel', 'metal', materials) == 'correct'
    assert Score_Material('a metallic grey component', 'plastic', materials) == 'wrong'
    assert Score_Material('a solid plastic or painted metal', 'plastic', materials) == 'not stated'
    assert Score_Material('possibly plastic or ceramic', 'plastic', materials) == 'correct'
    assert Score_Material('a metallic or composite material', 'plastic', materials) == 'wrong'
    assert Score_Material('a solid, opaque material', 'metal', materials) == 'not stated'


def test_a_colour_is_correct_only_when_one_of_its_terms_is_named() -> None:
    """
    Description:
        A colour term names the colour (at a word start, so "blue-violet" counts); no term, not stated.
    """

    assert Score_Colour('a vibrant, mottled blue-violet colour', ['blue', 'violet']) == 'correct'
    assert Score_Colour('a smooth metallic surface', ['blue']) == 'not stated'


def test_objects_the_key_excludes_count_only_when_asked(key) -> None:
    """
    Description:
        Tally leaves out the objects the key marks exclude_from_totals, and counts them when asked.
    """

    entries = [entry for entry in key['objects'] if entry['frame'] == 'Image_006']
    scores = [(entry, Score_Object('a circular metal part', entry, key)) for entry in entries]
    assert sum(Tally(scores)['type'].values()) == len(entries) - 1
    assert sum(Tally(scores, include_excluded=True)['type'].values()) == len(entries)


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
