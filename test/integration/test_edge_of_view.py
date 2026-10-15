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
    The mounting plate by the edge of the view, on real frames (Data/Images/Edge): four undistorted frames of the
    capture set 20261015-170251_s1, each the set's <name>_raw.png byte for byte, through the application's pipeline in
    the mounting-plate mode (FastSAM and DINOv2 on the CPU, the model-free describer). The stained front lies 60-67 mm
    from the frame centre turned about 30 degrees, where DINOv2 chose its back, which has neither the countersink nor
    the stain check: it read OK on frame 16 and NOK for a through-hole on frames 17 and 19, on a bore seen at an
    angle. Frame 1 is the control: a clean front near the centre, the hole-less block and a real back 58 mm out.
    A set separate from the pinned Data/Images/Test, so that set's inventory and its measurements stand.
"""

# The frames' folder, beside the pinned test set.
#   Unit [string]
CONST_EDGE_FRAMES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Data', 'Images', 'Edge')
# Every frame's objects' states, in no particular order: frame 1's clean front (4.8 mm out) and back (58.4 mm) are OK
# and the block of the part's outline with no holes is NOK; the stained front is NOK, for its two stains, on each of
# the others (59.9-66.6 mm out). By eye, 2026-10-15: both stepped holes are whole on every frame.
#   Unit [Dict<string, Tuple<string>>]
CONST_EDGE_VERDICTS = {
    '20261015-170254_1.png': ('OK', 'OK', 'NOK'),
    '20261015-170809_16.png': ('NOK',),
    '20261015-170816_17.png': ('NOK',),
    '20261015-170830_19.png': ('NOK',),
}
# The frames whose plate is the stained front by the edge.
#   Unit [Tuple<string>]
CONST_STAINED_EDGE_FRONTS = ('20261015-170809_16.png', '20261015-170816_17.png', '20261015-170830_19.png')
CONST_CATALOGUE_MODE_FILE = 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml'
# Each frame's objects, analysed once per session (the pipeline is deterministic on one frame).
#   Unit [Dict<string, Vector<Detection_Str(object)>>]
CONST_ANALYSED = {}


def _Objects(name: str, require_weights, monkeypatch) -> tp.List[tp.Any]:
    """A frame through the application's pipeline in the mounting-plate mode; a missing frame fails."""
    import cv2
    config = Load_Configuration(os.path.join(Mode_Directory(), CONST_CATALOGUE_MODE_FILE))
    config = dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))
    require_weights([config.Segmentation.Model_Path, config.Identification.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    if name not in CONST_ANALYSED:
        frame = cv2.imread(os.path.join(CONST_EDGE_FRAMES, name))
        if frame is None:
            pytest.fail('%s is missing from %s' % (name, os.path.abspath(CONST_EDGE_FRAMES)))
        CONST_ANALYSED[name] = Vision_Pipeline_Cls(Configuration_Str=config).Analyze(
            cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).Objects
    return CONST_ANALYSED[name]


def test_the_inventory_names_every_frame_of_the_edge_set() -> None:
    """
    Description:
        CONST_EDGE_VERDICTS names exactly the frames in Data/Images/Edge, so a frame removed cannot leave its pins
        passing on nothing and one added cannot go unlabelled.
    """

    frames = sorted(name for name in os.listdir(CONST_EDGE_FRAMES) if name.endswith('.png'))
    assert frames == sorted(CONST_EDGE_VERDICTS)


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
def test_a_stained_front_by_the_edge_is_checked_on_its_front(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        The stained front 60-67 mm out is checked on its front, shown by its countersinks (a hole only the front has)
        where DINOv2's margin chose the back: both countersinks and both through-holes found, every diameter, edge
        distance and pitch within tolerance (the through-hole measured at its countersink's centre, from the top
        face's edges), and its two stains found, which are the reason it is NOK. On frames 17 and 19 a through-hole
        read 19.04 and 19.37 mm from its short edge against 17.5 ± 1.5, its bore seen at an angle.
    """

    (det,) = _Objects(name, require_weights, monkeypatch)
    assert det.Catalogue.Side == 'front'
    assert [(c.Name, c.Found, c.Expected) for c in det.Hole_Counts] == [('countersink', 2, 2), ('through-hole', 2, 2)]
    assert [c.Name for c in det.Hole_Checks if not c.Within] == []
    assert len(det.Stains or []) == 2
    reason = Reason_Sentence(det)
    assert 'two stains on the machined front' in reason and 'hole' not in reason
    assert det.Catalogue.Side_Evidence == 'holes'


@pytest.mark.slow
def test_the_back_by_the_edge_stays_a_back(require_weights, monkeypatch) -> None:
    """
    Description:
        The control, as it was before the side took the holes' evidence: frame 1's real back, 58 mm out, has only
        through-holes, which both sides have, so no hole shows a side and DINOv2's margin (0.53) keeps it a back, OK,
        with both through-holes found and within tolerance (the side wall left out of its edges changes none).
    """

    objects = _Objects('20261015-170254_1.png', require_weights, monkeypatch)
    (back,) = [det for det in objects if det.Catalogue.Center_Distance_Mm > 50.0 and det.Verdict == 'OK']
    assert back.Catalogue.Side == 'back'
    assert [(c.Name, c.Found, c.Expected) for c in back.Hole_Counts] == [('through-hole', 2, 2)]
    assert all(c.Within for c in back.Hole_Checks)
