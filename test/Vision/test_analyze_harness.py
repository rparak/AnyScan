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
# File Name: ../test/Vision/test_analyze_harness.py
## =========================================================================== ##

# System (Default)
import os
import types
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: the validation harness itself (Example/Vision is on the import path)
#   ../Example/Vision/analyze
import analyze

"""
Description:
    Tests for the harness's anti-staleness guarantees (the fix that closes the
    silent-failure mode where a run that did not succeed still left output that looked
    finished):
      (1) a missing/unreadable reference fails non-zero BEFORE anything is written;
      (2) every artefact carries a provenance stamp — the run timestamp and the source
          frame's content fingerprint — so a stale file is identifiable on sight.
    They exercise the harness's own helpers and its main() failure path, with no camera
    and no model weights.
"""


def test_fingerprint_tracks_file_bytes(tmp_path) -> None:
    """
    Description:
        _Fingerprint is a content fingerprint: identical bytes fingerprint the same,
        different bytes fingerprint differently — so an artefact whose stamp no longer
        matches its source frame is stale.
    """

    a = tmp_path / 'a.bin'; a.write_bytes(b'the same bytes')
    b = tmp_path / 'b.bin'; b.write_bytes(b'the same bytes')
    c = tmp_path / 'c.bin'; c.write_bytes(b'different bytes')

    assert analyze._Fingerprint(str(a)) == analyze._Fingerprint(str(b))
    assert analyze._Fingerprint(str(a)) != analyze._Fingerprint(str(c))
    assert len(analyze._Fingerprint(str(a))) == analyze.CONST_FINGERPRINT_LEN


def test_stamp_line_carries_timestamp_and_frame_fingerprint(tmp_path) -> None:
    """
    Description:
        The provenance line names the run timestamp, the frame stem and its fingerprint,
        the reference fingerprint and the describer — everything needed to tell which
        run and which inputs produced an artefact.
    """

    scene = tmp_path / 'Image_001.png'; scene.write_bytes(b'scene-bytes')
    stamp = analyze._Stamp_Line('Image_001', str(scene), '2026-09-16T17:00:00', 'refhash0001', 'gemma')

    assert '2026-09-16T17:00:00' in stamp
    assert 'Image_001' in stamp
    assert analyze._Fingerprint(str(scene)) in stamp
    assert 'refhash0001' in stamp
    assert 'gemma' in stamp


def test_stamp_image_appends_a_visible_footer_band() -> None:
    """
    Description:
        _Stamp_Image appends the stamp on a footer band BELOW the content: the content
        rows are untouched (never occluded) and the image grows by the band height, with
        the drawn text making the band non-uniform.
    """

    image = np.full((40, 800, 3), 127, np.uint8)
    stamped = analyze._Stamp_Image(image, '2026-09-16T17:00:00 | frame Image_001 abcdef0123')

    assert stamped.shape == (40 + analyze.CONST_STAMP_BAND_H, 800, 3)
    assert np.array_equal(stamped[:40], image)            # content is preserved, not drawn over
    band = stamped[40:]
    assert band.std() > 0                                  # the stamp text marks the band


def test_scene_discovery_orders_naturally_and_tolerates_a_gap(tmp_path) -> None:
    """
    Description:
        The scene glob finds the Image_<n> frames in natural order, tolerates a missing Image_001,
        and excludes the empty-surface reference and any stray file — the glob-not-a-range
        contract. Image_010 is included and sorts after Image_008 (natural, not lexicographic),
        the guard against silently skipping a two-digit frame. The files are empty stand-ins:
        only their paths are resolved.
    """

    for name in ('Image_002.png', 'Image_010.png', 'Image_008.png', 'Image_003.png',
                 'Image_Background_001.png', 'notes.txt'):
        (tmp_path / name).write_bytes(b'')

    scenes = [os.path.basename(path) for path in analyze.Discover_Scenes(str(tmp_path))]

    assert scenes == ['Image_002.png', 'Image_003.png', 'Image_008.png', 'Image_010.png']


def test_scene_discovery_of_an_empty_directory_is_empty(tmp_path) -> None:
    """
    Description:
        A directory with no scene frames yields an empty list rather than raising — main() decides
        that "no scenes" is an error, and says so.
    """

    assert analyze.Discover_Scenes(str(tmp_path)) == []


def test_descriptions_file_opens_with_the_provenance_stamp(tmp_path) -> None:
    """
    Description:
        The descriptions file leads with the stamp as a comment line, so a stale .txt is
        identifiable on opening; the Screen-Understanding body follows it.
    """

    result = types.SimpleNamespace(Objects=[], Background='A plain green surface.')
    # __file__ is a readable file to fingerprint; the stamp's exact frame does not matter here.
    stamp = analyze._Stamp_Line('Image_001', __file__, '2026-09-16T17:00:00', 'refhash0001', 'gemma')
    path = tmp_path / 'Image_001_descriptions.txt'
    analyze._Write_Descriptions(str(path), result, stamp)

    lines = path.read_text().splitlines()
    assert lines[0].startswith('# ')
    assert '2026-09-16T17:00:00' in lines[0] and 'gemma' in lines[0]
    assert len(lines) > 1                                  # the reading follows the stamp


def _Configured(monkeypatch, **changes) -> None:
    """
    Description:
        Make analyze.py load the shipped configuration with some fields replaced — the reference,
        the test frames — so a failure path can be reached without editing the real file.

    Args:
        (1) monkeypatch [MonkeyPatch(object)]: pytest's monkeypatch.
        (2) changes [Dict]: 'reference' and/or 'frames' to set.
    """

    real = analyze.Load_Configuration

    def _Load(path: str):
        config = real(path)
        if 'reference' in changes:
            config.Segmentation.Background_Reference = changes['reference']
        if 'frames' in changes:
            config.Evaluation.Frames = changes['frames']
        return config

    monkeypatch.setattr(analyze, 'Load_Configuration', _Load)


def _Frame(path, size=(1920, 1200)) -> None:
    """Write a readable grey frame of (width, height) at path."""
    import cv2
    cv2.imwrite(str(path), np.full((size[1], size[0], 3), 90, np.uint8))


def test_missing_reference_fails_before_writing_anything(tmp_path, monkeypatch) -> None:
    """
    Description:
        The core anti-staleness guarantee: with a valid frame present but the configuration's
        reference unreadable, main() returns non-zero and writes NOTHING — no output directory of
        finished-looking artefacts from a run that did not succeed. This is the exact failure that
        let a stale montage and .txt pass review.
    """

    in_dir = tmp_path / 'in'; in_dir.mkdir()
    out_dir = tmp_path / 'out'
    _Frame(in_dir / 'Image_001.png')
    unreadable = tmp_path / 'Image_Background_001.png'
    unreadable.write_bytes(b'')                                # present, but imread returns None
    _Configured(monkeypatch, reference=str(unreadable))

    monkeypatch.setattr('sys.argv', ['analyze.py', '--input-dir', str(in_dir), '--output-dir', str(out_dir)])
    assert analyze.main() == 1
    assert (not out_dir.exists()) or (os.listdir(str(out_dir)) == [])


def test_frames_default_to_the_configuration_and_are_required(tmp_path, monkeypatch, capsys) -> None:
    """
    Description:
        The frames come from the configuration's Evaluation.Frames when --input-dir is not given;
        with neither, the run stops and says which field to set — there is no default path in the
        script.
    """

    _Configured(monkeypatch, frames='')
    monkeypatch.setattr('sys.argv', ['analyze.py', '--output-dir', str(tmp_path / 'out')])
    assert analyze.main() == 1
    assert 'Evaluation.Frames' in capsys.readouterr().out
    assert not (tmp_path / 'out').exists()


def test_a_frame_of_another_size_fails_before_writing_anything(tmp_path, monkeypatch, capsys) -> None:
    """
    Description:
        Every test frame must be the camera's window size, as the reference is; one that is not
        (here the full 1936 x 1216 sensor) stops the run before anything is written, naming it.
    """

    in_dir = tmp_path / 'frames'; in_dir.mkdir()
    _Frame(in_dir / 'Image_001.png')
    _Frame(in_dir / 'Image_002.png', size=(1936, 1216))
    _Configured(monkeypatch, frames=str(in_dir))
    monkeypatch.setattr('sys.argv', ['analyze.py', '--output-dir', str(tmp_path / 'out')])
    assert analyze.main() == 1
    out = capsys.readouterr().out
    assert 'Image_002.png: 1936 × 1216' in out and 'Image_001.png' not in out.split('not:')[-1]
    assert not (tmp_path / 'out').exists()


def test_stamp_wraps_at_its_separators_on_an_image_narrower_than_the_line() -> None:
    """
    Description:
        An object crop can be narrower than the provenance line: the stamp then wraps at its ' | '
        separators, one band per line, so no part of it is clipped — and the crop keeps its width
        and its pixels.
    """

    crop = np.full((60, 150, 3), 90, np.uint8)
    line = '2026-09-28T10:00:00 | frame Image_012 abcdef0123 | ref 0123456789 | describer gemma'
    stamped = analyze._Stamp_Image(crop, line)

    assert stamped.shape[1] == 150 and np.array_equal(stamped[:60], crop)
    bands = (stamped.shape[0] - 60) // analyze.CONST_STAMP_BAND_H
    assert bands == len(line.split(' | '))                 # each part on its own line at 150 px
    for k in range(bands):
        band = stamped[60 + k * analyze.CONST_STAMP_BAND_H:60 + (k + 1) * analyze.CONST_STAMP_BAND_H]
        assert band.std() > 0                              # every line carries text


def test_each_objects_crop_is_written_by_its_index_and_stale_crops_are_removed(tmp_path) -> None:
    """
    Description:
        Each object's enhanced crop — the image the describer received — is written as
        <frame>_objNN_crop.png, NN the object's 1-based index, its pixels exactly the crop's above the
        stamp. This frame's crops from an earlier run (a stale obj07 when there are now two objects)
        are removed; another frame's are left alone.
    """

    stale = tmp_path / 'Image_012_obj07_crop.png'
    other = tmp_path / 'Image_001_obj01_crop.png'
    stale.write_bytes(b'old'); other.write_bytes(b'other frame')
    crops = [np.full((50, 70, 3), 40, np.uint8), np.full((30, 90, 3), 200, np.uint8)]
    result = types.SimpleNamespace(Objects=[types.SimpleNamespace(Enhanced_Crop=crop) for crop in crops])

    analyze._Write_Crops(str(tmp_path), 'Image_012', result, 'stamp | line')

    import cv2
    assert not stale.exists() and other.read_bytes() == b'other frame'
    for index, crop in enumerate(crops, 1):
        written = cv2.imread(str(tmp_path / ('Image_012_obj%02d_crop.png' % index)))
        assert written is not None
        assert np.array_equal(written[:crop.shape[0]], crop)


def test_a_catalogue_run_finds_the_items_reference_frames_by_content() -> None:
    """
    Description:
        Judging an item on the frames it was defined from is circular, so a catalogue run reports them
        apart. They are found by content, not name: the test set's frames that are byte for byte the
        item's reference images — Image_055 and 056 for the mounting plate — and none outside a catalogue mode.
    """

    from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE
    folder = os.path.dirname(CONST_DEFAULT_CONFIG_FILE)
    for mode, expected in (('Mounting_Plate', ['Image_055.png', 'Image_056.png']),
                           ('Seg_Anything', [])):
        config = Load_Configuration(os.path.join(folder, 'Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_%s.yaml' % mode))
        scenes = analyze.Discover_Scenes(config.Evaluation.Frames)
        assert len(scenes) == 41
        assert sorted(os.path.basename(path) for path in analyze.Reference_Frames(config, scenes)) == expected
