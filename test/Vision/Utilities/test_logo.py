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
# File Name: ../test/Vision/Utilities/test_logo.py
## =========================================================================== ##

# System (Default)
import os
import dataclasses
# Typing (Support for type hints)
import typing as tp
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Custom Lib.: AnyScan — the logo check, the rule that applies it, the item it reads and the structures
#   ../Vision/Utilities/Logo
from Vision.Utilities.Logo import Reference_Logo_Crop, Prepare_Reference, Check_Logo
#   ../Vision/Utilities/Classify
from Vision.Utilities.Classify import Apply_Logo
#   ../Configuration/Core
from Configuration.Core import Load_Catalogue
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Logo_Result_Str, Logo_Letter_Str
#   ../Parameters/Catalogue
from Parameters.Catalogue import Catalogue_Logo_Reference_Str

"""
Description:
    The catalogue's logo check: a part's crop is registered to each logo reference by SIFT features; none
    registering is no inscription; each letter is compared with that letter in every reference it registered to,
    and is there at both the similarity and the contrast threshold. On the shipped labyrinth item's references
    (no model needed), with SYNTHETIC defects — a letter inpainted away, a plate without the logo — since no
    frame of the test set shows one; the real backs are pinned in test_pipeline (slow) and below (slow: every
    letter of every complete real logo erased in turn).
"""

# The shipped labyrinth item, read once: its back's logo check and its first reference (filled letters).
CONST_ITEM = Load_Catalogue(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Data', 'Catalogue', 'labyrinth',
                                         'labyrinth.yaml'))
CONST_LOGO = CONST_ITEM.Logo['back']
CONST_REFERENCE = CONST_LOGO.References[0]


def _Crop() -> np.ndarray:
    """The filled-letter reference, cut out and turned as the check cuts it."""
    return Reference_Logo_Crop(cv2.imread(CONST_REFERENCE.Image_Path), CONST_REFERENCE, cv2, np)


def _Erase(crop: np.ndarray, index: int) -> np.ndarray:
    """SYNTHETIC: one letter's engraved strokes (the dark pixels in its box) inpainted from the plate around them."""
    _letter, x, y, w, h = CONST_REFERENCE.Letters[index]
    box = np.zeros(crop.shape[:2], np.uint8)
    box[y - 2:y + h + 2, x - 2:x + w + 2] = 255
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    strokes = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 8) > 0) & (box > 0)
    return cv2.inpaint(crop, cv2.dilate(strokes.astype(np.uint8) * 255, np.ones((5, 5), np.uint8)), 5, cv2.INPAINT_TELEA)


def _One(logo: tp.Any = CONST_LOGO, **changes: tp.Any) -> tp.Any:
    """The logo check with the filled-letter reference only, and any thresholds changed."""
    return dataclasses.replace(logo, References=[CONST_REFERENCE], **changes)


def test_the_reference_crop_is_turned_about_its_box_before_it_is_cut() -> None:
    """
    Description:
        Rotation_Deg turns the frame about the box's centre (counter-clockwise, OpenCV's sense) before the box
        is cut: 180 degrees gives the box crop upside down, 90 gives it turned a quarter counter-clockwise.
    """

    frame = np.zeros((100, 200, 3), np.uint8)
    frame[30:40, 60:70] = (0, 0, 255)                                   # a marker in the box's top-left corner
    reference = Catalogue_Logo_Reference_Str(Name='x', Box=(0.5, 0.5, 0.4, 0.8), Letters=[])

    def Marker(crop: np.ndarray) -> tp.Tuple[int, int]:
        rows, columns = np.nonzero(crop[:, :, 2] > 128)
        return int(rows.mean()), int(columns.mean())

    upright = Reference_Logo_Crop(frame, reference, cv2, np)
    assert upright.shape == (80, 80, 3) and Marker(upright) == (24, 4)
    assert Marker(Reference_Logo_Crop(frame, dataclasses.replace(reference, Rotation_Deg=180.0), cv2, np)) == (55, 75)
    assert Marker(Reference_Logo_Crop(frame, dataclasses.replace(reference, Rotation_Deg=90.0), cv2, np)) == (75, 24)


def test_a_complete_logo_reads_complete_turned_and_smaller() -> None:
    """
    Description:
        The reference's own part, turned a quarter and shrunk to 85 %, registers to it and reads complete: every
        letter there, each named with its word in reading order (JIC, SMART, FACTORY).
    """

    crop = cv2.resize(np.ascontiguousarray(np.rot90(_Crop())), None, fx=0.85, fy=0.85)
    result = Check_Logo(crop, _One(), [Prepare_Reference(_Crop(), cv2, np)], cv2, np)
    assert result.Reference == 'back' and result.Matches >= CONST_LOGO.Min_Matches
    assert ''.join(letter.Letter for letter in result.Letters) == 'JICSMARTFACTORY'
    assert [letter.Word for letter in result.Letters] == ['JIC'] * 3 + ['SMART'] * 5 + ['FACTORY'] * 7
    assert all(letter.Present for letter in result.Letters)


@pytest.mark.parametrize('index', [0, 5, 13], ids=['J of JIC', 'A of SMART', 'R of FACTORY'])
def test_an_erased_letter_is_missing_and_named_with_its_word(index: int) -> None:
    """
    Description:
        SYNTHETIC: one letter inpainted away from the part (turned a quarter) is missing, and only it, with its
        word; a letter that is in two words (A, R) is told apart by its place.
    """

    crop = np.ascontiguousarray(np.rot90(_Erase(_Crop(), index)))
    result = Check_Logo(crop, _One(), [Prepare_Reference(_Crop(), cv2, np)], cv2, np)
    assert [(i, letter.Letter, letter.Word) for i, letter in enumerate(result.Letters) if not letter.Present] == \
        [(index, CONST_REFERENCE.Letters[index][0], ('JIC', 'SMART', 'FACTORY')[(index >= 3) + (index >= 8)])]


def test_a_plate_without_the_logo_has_no_inscription() -> None:
    """
    Description:
        SYNTHETIC: a plate of the logo's size with a brushed-metal texture and no engraving registers to no
        reference, so it has no inscription and no letters; and a logo short of Min_Matches is not registered.
    """

    rng = np.random.default_rng(7)
    plate = cv2.GaussianBlur(rng.normal(200, 12, (490, 490)).astype(np.float32), (0, 0), 1.5)
    plate = cv2.cvtColor(np.clip(plate, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    prepared = [Prepare_Reference(_Crop(), cv2, np)]
    assert Check_Logo(plate, _One(), prepared, cv2, np).Letters == []
    assert Check_Logo(plate, _One(), prepared, cv2, np).Reference == ''
    unreachable = Check_Logo(_Crop(), _One(Min_Matches=10 ** 6), prepared, cv2, np)
    assert (unreachable.Reference, unreachable.Letters) == ('', []) and unreachable.Matches > 0


def test_a_letter_is_there_only_at_both_thresholds() -> None:
    """
    Description:
        A letter is there at Letter_Min_Similarity AND Letter_Min_Contrast: the same complete logo reads every
        letter missing when either threshold is out of reach, so neither shape alone (correlation is blind to how
        faint the edges are) nor contrast alone decides. Both are reported per letter.
    """

    prepared = [Prepare_Reference(_Crop(), cv2, np)]
    for changes in ({'Letter_Min_Contrast': 10 ** 6}, {'Letter_Min_Similarity': 1.0 + 1e-9}):
        result = Check_Logo(_Crop(), _One(**changes), prepared, cv2, np)
        assert result.Reference == 'back' and not any(letter.Present for letter in result.Letters)
    result = Check_Logo(_Crop(), _One(), prepared, cv2, np)
    assert all(letter.Similarity >= 0.99 and letter.Contrast > CONST_LOGO.Letter_Min_Contrast for letter in result.Letters)


def test_each_letter_takes_its_best_reference_not_only_the_best_registered() -> None:
    """
    Description:
        Two references of one variant: A, the part's best match (most features), with its S erased (SYNTHETIC: a
        reference lit so that a letter is faint), and B, the same blurred. The part's S is there through B; with
        A alone it is missing. So one reference's dim letter does not fail a part another reference shows.
    """

    a = dataclasses.replace(CONST_REFERENCE, Name='A')
    b = dataclasses.replace(CONST_REFERENCE, Name='B')
    prepared_a = Prepare_Reference(_Erase(_Crop(), 3), cv2, np)
    prepared_b = Prepare_Reference(cv2.GaussianBlur(_Crop(), (0, 0), 1.2), cv2, np)
    both = Check_Logo(_Crop(), dataclasses.replace(CONST_LOGO, References=[a, b]), [prepared_a, prepared_b], cv2, np)
    assert both.Reference == 'A' and all(letter.Present for letter in both.Letters)
    alone = Check_Logo(_Crop(), dataclasses.replace(CONST_LOGO, References=[a]), [prepared_a], cv2, np)
    assert [letter.Letter for letter in alone.Letters if not letter.Present] == ['S']


@pytest.mark.parametrize('logo, before, after', [
    (Logo_Result_Str(Reference='back', Matches=99, Letters=[Logo_Letter_Str('JIC', 'J', 0.9, 5.0, True)]), 'OK', 'OK'),
    (Logo_Result_Str(Reference='back', Matches=99, Letters=[Logo_Letter_Str('JIC', 'J', 0.2, 5.0, False)]), 'OK', 'NOK'),
    (Logo_Result_Str(Reference='', Matches=3), 'OK', 'NOK'),
    (Logo_Result_Str(Reference='back', Matches=99, Letters=[Logo_Letter_Str('JIC', 'J', 0.9, 5.0, True)]), 'NOK', 'NOK'),
], ids=['complete', 'a letter missing', 'no inscription', 'already nok'])
def test_a_judged_parts_logo_decides_ok_or_nok(logo: Logo_Result_Str, before: str, after: str) -> None:
    """
    Description:
        A part judged OK stays OK only with its inscription found and every letter there; no inscription or a
        missing letter makes it NOK; a part already NOK stays NOK. The result is kept on the object for the report.
    """

    det = Detection_Str(Label='plate', Bbox=(0, 0, 1, 1), Verdict=before)
    Apply_Logo(det, logo)
    assert det.Verdict == after and det.Logo is logo


# The complete logos of the test set's labyrinth backs, by frame: their places among the frame's backs from the
# left (labelled by eye, 2026-10-11): the filled letters, and the outline letters on 069, 092's left and 095's left.
# Image_092's right plate (back_dark) is complete too and erased from as well: it is a reference, so it shows that
# an erasure is caught against the plate's own letters, not that the dark appearance is verified (KNOWN_ISSUES).
#   Unit [Dict<string, Tuple<int>>]
CONST_COMPLETE_BACKS = {'Image_058.png': (0,), 'Image_061.png': (0,), 'Image_067.png': (0,), 'Image_069.png': (0,),
                        'Image_084.png': (0,), 'Image_086.png': (1,), 'Image_090.png': (0,), 'Image_092.png': (0, 1),
                        'Image_094.png': (1,), 'Image_095.png': (0, 1)}


def _Aligned(crop: np.ndarray, reference_crop: np.ndarray) -> np.ndarray:
    """The test's own registration of a part's crop onto a reference (to place the synthetic erasure there)."""
    sift = cv2.SIFT_create()
    image = cv2.resize(crop, (reference_crop.shape[1], reference_crop.shape[0]), interpolation=cv2.INTER_AREA)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(reference_crop, cv2.COLOR_BGR2GRAY), None)
    good = [a for a, b in (p for p in cv2.BFMatcher().knnMatch(d1, d2, k=2) if len(p) == 2) if a.distance < 0.75 * b.distance]
    warp, _inliers = cv2.estimateAffinePartial2D(np.float32([k1[m.queryIdx].pt for m in good]),
                                                 np.float32([k2[m.trainIdx].pt for m in good]), method=cv2.RANSAC)
    return cv2.warpAffine(image, warp, (reference_crop.shape[1], reference_crop.shape[0]))


def _Labyrinth_Mode() -> tp.Any:
    """The shipped labyrinth mode with FastSAM and DINOv2 on the CPU (portable)."""
    from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE
    config = Load_Configuration(os.path.join(os.path.dirname(CONST_DEFAULT_CONFIG_FILE),
                                             'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Labyrinth.yaml'))
    return dataclasses.replace(config, Segmentation=dataclasses.replace(config.Segmentation, Device='cpu'))


@pytest.mark.slow
@pytest.mark.parametrize('name', sorted(CONST_COMPLETE_BACKS))
def test_every_letter_erased_from_a_real_logo_is_caught(name: str, require_weights, monkeypatch) -> None:
    """
    Description:
        Each complete logo of the test set's backs (cut out by the application's pipeline in the labyrinth mode)
        reads complete; then each of its 15 letters is erased in turn (SYNTHETIC: its strokes inpainted, on the
        part registered onto its best reference) and that letter is missing. 180 erasures over the 12 logos,
        at most 0.34. (An eraser of the dark strokes only left the dark plate's lighter letters in place, and on
        two J left a seam of the letter's shape, 0.58-0.59 at contrast 0.18-0.19, which the contrast condition
        catches.) Slow because it runs FastSAM and DINOv2; missing weights fail it under
        --runslow.
    """

    import Vision.Core as Vision_Core
    from Vision.Utilities.Classify import Object_Crop
    config = _Labyrinth_Mode()
    require_weights([config.Segmentation.Model_Path, config.Identification.Model_Path])
    monkeypatch.setattr(Vision_Core, 'CONST_DESCRIBER', 'fallback')
    frame = cv2.imread(os.path.join(config.Evaluation.Frames, name))
    if frame is None:
        pytest.fail('%s is missing from the pinned test set' % name)
    objects = Vision_Core.Vision_Pipeline_Cls(Configuration_Str=config).Analyze(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).Objects
    backs = sorted((det for det in objects if det.Catalogue is not None and det.Catalogue.Side == 'back'
                    and det.Verdict in ('OK', 'NOK')), key=lambda det: det.Bbox[0])
    logo = config.Catalogue.Logo['back']
    crops = {r.Name: Reference_Logo_Crop(cv2.imread(r.Image_Path), r, cv2, np) for r in logo.References}
    prepared = [Prepare_Reference(crops[r.Name], cv2, np) for r in logo.References]
    for place in CONST_COMPLETE_BACKS[name]:
        crop = Object_Crop(frame, backs[place], cv2, np)
        complete = Check_Logo(crop, logo, prepared, cv2, np)
        assert complete.Reference and all(letter.Present for letter in complete.Letters), (place, complete)
        reference = next(r for r in logo.References if r.Name == complete.Reference)
        aligned = _Aligned(crop, crops[reference.Name])
        for index, (_letter, x, y, w, h) in enumerate(reference.Letters):
            box = np.zeros(aligned.shape[:2], np.uint8)
            box[max(0, y - 2):y + h + 2, max(0, x - 2):x + w + 2] = 255
            # The strokes are the pixels off their surroundings either way: the dark plate's engraving is lighter
            # than the plate, and a dark-only eraser left its letters in place.
            gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY).astype(int)
            strokes = (np.abs(gray - cv2.blur(gray.astype(np.uint8), (31, 31)).astype(int)) > 8) & (box > 0)
            erased = cv2.inpaint(aligned, cv2.dilate(strokes.astype(np.uint8) * 255, np.ones((5, 5), np.uint8)), 5,
                                 cv2.INPAINT_TELEA)
            result = Check_Logo(erased, logo, prepared, cv2, np)
            assert result.Letters and not result.Letters[index].Present, (place, index, result.Letters[index])


def test_each_word_is_boxed_on_the_part_where_its_letters_are() -> None:
    """
    Description:
        The frame marks the logo word by word: each expected word's box on the checked crop is the box around
        its letters in the matched reference, taken back through the registration — on the reference's own part
        turned a quarter clockwise, JIC's box turns with it.
    """

    letters = CONST_REFERENCE.Letters
    prepared = [Prepare_Reference(_Crop(), cv2, np)]
    upright = Check_Logo(_Crop(), _One(), prepared, cv2, np)
    assert [word for word, _corners in upright.Words] == ['JIC', 'SMART', 'FACTORY']
    xs, ys = [x for x, _ in upright.Words[0][1]], [y for _, y in upright.Words[0][1]]
    assert abs(min(xs) - letters[0][1]) < 2 and abs(max(xs) - (letters[2][1] + letters[2][3])) < 2
    assert abs(min(ys) - min(l[2] for l in letters[:3])) < 2
    height = _Crop().shape[0]
    turned = Check_Logo(np.ascontiguousarray(np.rot90(_Crop(), -1)), _One(), prepared, cv2, np)
    txs = [x for x, _ in turned.Words[0][1]]
    # A clockwise quarter turn sends y to x' = height - y: JIC's top edge becomes its right edge.
    assert abs(max(txs) - (height - min(ys))) < 3
