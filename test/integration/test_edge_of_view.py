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
# File Name: ../test/integration/test_edge_of_view.py
## =========================================================================== ##

# System (Default)
import os
import json
import collections
import dataclasses
# Typing (Support for type hints)
import typing as tp
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan domain — the vision backend, the configuration, the verdict's reason
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Mode_Directory
#   ../Reporting/Core
from Reporting.Core import Reason_Sentence

"""
Description:
    The mounting plate by the edge of the view, on real frames (Data/Images/Edge), through the application's pipeline
    in the mounting-plate mode (FastSAM and DINOv2 on the CPU, the model-free describer). Four frames of capture
    20261015-170251_s1: the stained front 60-67 mm from the frame centre, turned about 30 degrees, where DINOv2 chose
    its back (which has neither the countersink nor the stain check): it read OK on frame 16 and NOK for a through-hole
    on frames 17 and 19, a bore seen at an angle; frame 1 the control (a clean front near the centre, the hole-less
    block, a real back 58 mm out). Three of capture 20261015-180933_s1: the stained front again (DINOv2's margin
    -0.076, the widest wrong one measured) and two clean fronts 60 mm out, where DINOv2 tells the front by less than
    its margin and the countersinks decide. Four of the rig's capture 20261016-111250_s1, the red block inside the area
    and cut by its top border, which must stay a foreign object (grey) there. Four of capture 20261016-070531_s1: the stained front cut by the right
    border and failing identification (frame 2, similarity 0.738, its outline cut to 61.56 mm), cut by it and still
    identified by its outline (frame 6), whole but over the top and right edges of the inspection area (frame 14, read
    Unspecified 71 mm out by the radius rule this replaced), and a clean front inside the area 56 mm out (frame 21).

    Since 2026-10-16 only a part wholly inside the station's inspection area is judged (Classify.Settle_Area): every
    plate by the right edge here lies over the area's edge, so it is a Warning, and the checks that pinned its side,
    holes and stains still run on it, as information named in its reason.

    Each frame is stored as crops around its objects (40 px margin) with a manifest: their offsets, the frame's size,
    the source capture frame and its SHA-256. The test pastes them onto the mode's empty-surface reference at their
    offsets, so every distance from the frame centre and the camera geometry are the frame's. Measured on all seven
    first frames (2026-10-15): the side, how it was decided, the holes found and passing, the stains and the verdict are
    the full frame's on every object; the measured values are not (outlines up to 0.79 mm, hole distances up to
    0.60 mm), since the background difference's Otsu threshold is taken over the whole frame and the rebuilt frame has
    no table noise outside the crops. So these pin decisions, never values. A set separate from the pinned
    Data/Images/Test.
"""

# The frames' folder, beside the pinned test set: one <frame>.json manifest per frame, its crops beside it.
#   Unit [string]
CONST_EDGE_FRAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Data', 'Images', 'Edge')
# Every frame's objects' states, in no particular order: frame 1's clean front (4.8 mm out) and back (58.4 mm) are OK
# and the block of the part's outline with no holes is NOK, all three inside the inspection area; every plate by the
# right edge lies over the area's edge, so it is a Warning, stained (59.9-66.6 mm out) or clean (59.8 and 60.2 mm), as
# are the cut and the whole stained fronts of 20261016-070531_s1; its clean front 56 mm out, inside, is OK. By eye,
# 2026-10-15 and 2026-10-16: both stepped holes are whole on every frame but frame 2's (cut by the border).
#   Unit [Dict<string, Tuple<string>>]
CONST_EDGE_VERDICTS = {
    '20261015-170254_1': ('OK', 'OK', 'NOK'),
    '20261015-170809_16': ('Warning',),
    '20261015-170816_17': ('Warning',),
    '20261015-170830_19': ('Warning',),
    '20261015-180936_1': ('Warning',),
    '20261015-180955_2': ('Warning',),
    '20261015-181017_6': ('Warning',),
    '20261016-070547_2': ('Warning',),
    '20261016-070619_6': ('Warning',),
    '20261016-070812_14': ('Warning',),
    '20261016-070930_21': ('OK',),
    '20261016-111254_1': ('NOK', 'Warning'),
    '20261016-111301_2': ('Warning', 'NOK'),
    '20261016-111333_4': ('Warning', 'NOK'),
    '20261016-111340_5': ('Warning', 'Warning'),
}
# The rig's frames of 20261016-111250_s1 with the red block (a foreign object with a countersunk hole): inside the area
# (frame 1), only a corner of it below the top border (frame 2, similarity 0.517), and cut by the top border (frames 4
# and 5, 0.645 and 0.635); with the stained front inside the area, NOK (frames 1, 2, 4), and outside it (frame 5).
#   Unit [Tuple<string>]
CONST_RED_BLOCK_FRAMES = ('20261016-111254_1', '20261016-111301_2', '20261016-111333_4', '20261016-111340_5')
# The frames whose plate is the stained front by the edge, identified, and those whose plate is a clean front by it.
#   Unit [Tuple<string>]
CONST_STAINED_EDGE_FRONTS = ('20261015-170809_16', '20261015-170816_17', '20261015-170830_19', '20261015-180936_1',
                             '20261016-070619_6', '20261016-070812_14')
CONST_CLEAN_EDGE_FRONTS = ('20261015-180955_2', '20261015-181017_6')
# What every object outside the inspection area's reason opens with.
#   Unit [string]
CONST_OUTSIDE = 'It lies outside the inspection area, so it is not judged: move it fully inside the area and scan again.'
CONST_CATALOGUE_MODE_FILE = 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml'
# Each frame's objects, analysed once per session (the pipeline is deterministic on one frame).
#   Unit [Dict<string, Vector<Detection_Str(object)>>]
CONST_ANALYSED = {}


def _Frame(name: str, reference_path: str) -> tp.Any:
    """A frame rebuilt from its manifest: its crops pasted onto the empty-surface reference; anything missing fails."""
    import cv2
    path = os.path.join(CONST_EDGE_FRAMES, name + '.json')
    if not os.path.isfile(path):
        pytest.fail('%s is missing from %s' % (name, os.path.abspath(CONST_EDGE_FRAMES)))
    manifest = json.load(open(path))
    frame = cv2.imread(reference_path)
    if frame is None or [frame.shape[1], frame.shape[0]] != manifest['frame_size']:
        pytest.fail('the reference %s does not match the frame size %s of %s' % (reference_path, manifest['frame_size'], name))
    for crop in manifest['crops']:
        pixels = cv2.imread(os.path.join(CONST_EDGE_FRAMES, crop['file']))
        if pixels is None:
            pytest.fail('%s is missing from %s' % (crop['file'], os.path.abspath(CONST_EDGE_FRAMES)))
        x, y = crop['offset']
        frame[y:y + pixels.shape[0], x:x + pixels.shape[1]] = pixels
    return frame


def _Objects(name: str, require_weights, monkeypatch) -> tp.List[tp.Any]:
    """A frame, rebuilt, through the application's pipeline in the mounting-plate mode."""
    import cv2
    config = Load_Configuration(os.path.join(Mode_Directory(), CONST_CATALOGUE_MODE_FILE))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path, config.Identification.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    if name not in CONST_ANALYSED:
        frame = _Frame(name, config.Segmentation.Background_Reference)
        CONST_ANALYSED[name] = Vision_Pipeline_Cls(Configuration_Str=config).Analyze(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).Objects
    return CONST_ANALYSED[name]


def test_the_inventory_names_every_frame_and_crop_of_the_edge_set() -> None:
    """
    Description:
        CONST_EDGE_VERDICTS names exactly the manifests in Data/Images/Edge, and the manifests name exactly its crops,
        each inside its frame, so a frame or a crop removed cannot leave its pins passing on nothing and one added
        cannot go unlabelled.
    """

    files = os.listdir(CONST_EDGE_FRAMES)
    assert sorted(name[:-5] for name in files if name.endswith('.json')) == sorted(CONST_EDGE_VERDICTS)
    named = []
    for name in CONST_EDGE_VERDICTS:
        manifest = json.load(open(os.path.join(CONST_EDGE_FRAMES, name + '.json')))
        width, height = manifest['frame_size']
        assert len(manifest['crops']) == len(CONST_EDGE_VERDICTS[name]), name
        for crop in manifest['crops']:
            x, y = crop['offset']
            assert 0 <= x < width and 0 <= y < height, crop
            named.append(crop['file'])
    assert sorted(named) == sorted(name for name in files if name.endswith('.png'))


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(CONST_EDGE_VERDICTS))
def test_each_edge_frame_gets_its_expected_verdicts(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Every object of every frame takes its labelled state, counted: the stained front by the edge is NOK (it read
        OK on frame 16 when DINOv2 chose its back), and frame 1's clean front, real back and hole-less block keep the
        states they had.
    """

    objects = _Objects(name, require_weights, monkeypatch)
    assert collections.Counter(det.Verdict for det in objects) == collections.Counter(CONST_EDGE_VERDICTS[name])


@pytest.mark.slow
@pytest.mark.parametrize('name', CONST_STAINED_EDGE_FRONTS)
def test_a_stained_front_by_the_edge_is_outside_the_area_with_its_checks_named(name: str, require_weights,
                                                                               monkeypatch) -> None:
    """
    Description:
        The stained front 60-71 mm out lies over the inspection area's edge, so it is a Warning, never judged; its
        checks still run, on its front, shown by its countersinks (a hole only the front has) where DINOv2's margin
        chose the back: both countersinks and both through-holes found, every diameter, edge distance and pitch within
        tolerance, and its two stains found, which its reason names as information. On frames 17 and 19 a through-hole
        once read 19.04 and 19.37 mm from its short edge against 17.5 ± 1.5, its bore seen at an angle; frame 6 is cut
        by the frame's border and still identified by its outline.
    """

    (det,) = _Objects(name, require_weights, monkeypatch)
    assert (det.Verdict, det.Catalogue.Outside_Area) == ('Warning', True)
    assert det.Catalogue.Side == 'front'
    assert [(c.Name, c.Found, c.Expected) for c in det.Hole_Counts] == [('countersink', 2, 2), ('through-hole', 2, 2)]
    assert [c.Name for c in det.Hole_Checks if not c.Within] == []
    assert len(det.Stains or []) == 2
    assert Reason_Sentence(det) == CONST_OUTSIDE + (' Seen there: both countersinks found, both through-holes found, '
                                                    'two stains found.')
    assert det.Catalogue.Side_Evidence == 'holes'
    assert sorted(feature.Kind for feature in det.Features) == ['hole'] * 4 + ['stain'] * 2


@pytest.mark.slow
def test_the_back_by_the_edge_stays_a_back(require_weights, monkeypatch) -> None:
    """
    Description:
        The control, as it was before the side took the holes' evidence: frame 1's real back, 58 mm out and inside the
        inspection area, has only through-holes, which both sides have, so no hole shows a side and DINOv2's margin
        (0.53) keeps it a back, OK, with both through-holes found and within tolerance (the side wall left out of its
        edges changes none).
    """

    objects = _Objects('20261015-170254_1', require_weights, monkeypatch)
    (back,) = [det for det in objects if det.Catalogue.Center_Distance_Mm > 50.0 and det.Verdict == 'OK']
    assert back.Catalogue.Side == 'back' and not back.Catalogue.Outside_Area
    assert [(c.Name, c.Found, c.Expected) for c in back.Hole_Counts] == [('through-hole', 2, 2)]
    assert all(c.Within for c in back.Hole_Checks)


@pytest.mark.slow
@pytest.mark.parametrize('name', CONST_CLEAN_EDGE_FRONTS)
def test_a_clean_front_by_the_edge_is_outside_the_area_with_its_checks_clean(name: str, require_weights,
                                                                             monkeypatch) -> None:
    """
    Description:
        A clean front 60 mm out (capture 20261015-180933_s1) lies over the inspection area's edge, so it is a Warning,
        not OK; its checks still run and find nothing: it looks like the part (similarity to the front 0.85-0.87, above
        0.75), its side is decided by its countersinks (DINOv2's margin +0.23 to +0.25, under the 0.265 that tells),
        every hole is found and within tolerance (the bores within 0.17 mm of their countersinks' axes once the
        camera's shift is out), and no stain is found, which its reason says.
    """

    (det,) = _Objects(name, require_weights, monkeypatch)
    assert (det.Verdict, det.Catalogue.Outside_Area) == ('Warning', True)
    assert Reason_Sentence(det) == CONST_OUTSIDE + (' Seen there: both countersinks found, both through-holes found, '
                                                    'no stain found.')
    assert det.Catalogue.Similarity >= det.Catalogue.Identify_Similarity
    assert det.Catalogue.Side == 'front'
    assert [(c.Name, c.Found, c.Expected) for c in det.Hole_Counts] == [('countersink', 2, 2), ('through-hole', 2, 2)]
    assert all(c.Within for c in det.Hole_Checks)
    assert len([c for c in det.Hole_Checks if c.Name == "through-hole's offset from its countersink"]) == 2
    assert not det.Stains
    assert det.Catalogue.Side_Evidence == 'holes'


@pytest.mark.slow
def test_a_cut_plate_that_fails_identification_is_outside_the_area_with_no_marks(require_weights, monkeypatch) -> None:
    """
    Description:
        The stained front cut by the frame's right border (20261016-070547_2, its outline cut to 61.56 mm, similarity
        0.738) is not identified as the part, so outside the area it is a Warning with the outside-area reason alone:
        no check runs on it and nothing is marked on it, as for a foreign object.
    """

    (det,) = _Objects('20261016-070547_2', require_weights, monkeypatch)
    assert (det.Verdict, det.Catalogue.Outside_Area) == ('Warning', True)
    assert det.Catalogue.Similarity < det.Catalogue.Identify_Similarity
    assert Reason_Sentence(det) == CONST_OUTSIDE
    assert (det.Features, det.Hole_Counts, det.Stains) == ([], [], None)


@pytest.mark.slow
def test_a_clean_front_inside_the_area_away_from_the_centre_is_ok(require_weights, monkeypatch) -> None:
    """
    Description:
        The control inside the area: the clean front 56 mm out on the left (20261016-070930_21), wholly inside it, is
        judged, OK, with every hole found and within tolerance and no stain.
    """

    (det,) = _Objects('20261016-070930_21', require_weights, monkeypatch)
    assert (det.Verdict, det.Catalogue.Outside_Area, Reason_Sentence(det)) == ('OK', False, '')
    assert [(c.Name, c.Found, c.Expected) for c in det.Hole_Counts] == [('countersink', 2, 2), ('through-hole', 2, 2)]
    assert all(c.Within for c in det.Hole_Checks) and not det.Stains


@pytest.mark.slow
def test_the_holeless_block_keeps_both_readings_and_gives_what_they_share(require_weights, monkeypatch) -> None:
    """
    Description:
        Frame 1's block of the part's outline with no holes is the one object whose side could not be told (DINOv2's
        margin 0.165, no hole to show a side): it is read on both sides, each NOK, and keeps both readings, the front's
        with its countersinks and through-holes missing, the back's with its through-holes missing. Its reason gives
        only what both share, never the front's missing countersinks.
    """

    objects = _Objects('20261015-170254_1', require_weights, monkeypatch)
    (block,) = [det for det in objects if det.Verdict == 'NOK']
    readings = block.Catalogue.Side_Readings
    assert block.Catalogue.Side_Evidence == 'undecided'
    assert sorted(readings) == ['machined front', 'unmachined back']
    assert [(c.Name, c.Found) for c in readings['machined front'].Hole_Counts] == [('countersink', 0), ('through-hole', 0)]
    assert [(c.Name, c.Found) for c in readings['unmachined back'].Hole_Counts] == [('through-hole', 0)]
    assert {reading.Verdict for reading in readings.values()} == {'NOK'}
    assert Reason_Sentence(block) == ("It has the part's outline but does not look like the part, and both "
                                      'through-holes are missing.')


@pytest.mark.slow
@pytest.mark.parametrize('name', CONST_RED_BLOCK_FRAMES)
def test_the_red_block_is_a_foreign_object_wherever_it_lies(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        The red block does not resemble the mounting plate, inside the inspection area or cut by the frame's top border:
        it is a Warning drawn as a foreign object (Annotate.Foreign, the grey), never as a part outside the area (the
        amber), with no marks. Inside the area it should not be on the surface; outside it, it is named as a foreign
        object to remove, not a part to move. Its colour rules it out (mean saturation above 100, every plate 40 at
        most) even where its similarity would not.
    """

    from Vision.Utilities.Annotate import Foreign
    (block,) = [det for det in _Objects(name, require_weights, monkeypatch) if det.Catalogue.Saturation > 100.0]
    assert (block.Verdict, block.Catalogue.Resembles, Foreign(block), block.Features) == ('Warning', False, True, [])
    assert Reason_Sentence(block) == ('It is not the part and lies outside the inspection area: remove it from the '
                                      'surface.' if block.Catalogue.Outside_Area else
                                      'The object should not be on the surface.')
    assert block.Catalogue.Outside_Area == (name != '20261016-111254_1')


@pytest.mark.slow
def test_a_stained_front_outside_the_area_beside_the_red_block_stays_amber(require_weights, monkeypatch) -> None:
    """
    Description:
        On the rig's frame 5 the stained front lies over the area's top edge beside the cut red block: it resembles the
        part (identified, similarity 0.750), so it is the amber part outside the area, its stains named, never grey.
    """

    from Vision.Utilities.Annotate import Foreign
    objects = _Objects('20261016-111340_5', require_weights, monkeypatch)
    (plate,) = [det for det in objects if det.Catalogue.Saturation <= 100.0]
    assert (plate.Verdict, plate.Catalogue.Outside_Area, plate.Catalogue.Resembles, Foreign(plate)) == \
        ('Warning', True, True, False)
    assert Reason_Sentence(plate) == CONST_OUTSIDE + (' Seen there: both countersinks found, both through-holes found, '
                                                      'two stains found.')
