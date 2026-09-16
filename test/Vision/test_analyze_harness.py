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
    stamp = analyze._Stamp_Line('Image_001', str(scene), '2026-09-16T17:00:00', 'refhash0001', 'florence')

    assert '2026-09-16T17:00:00' in stamp
    assert 'Image_001' in stamp
    assert analyze._Fingerprint(str(scene)) in stamp
    assert 'refhash0001' in stamp
    assert 'florence' in stamp


def test_stamp_image_appends_a_visible_footer_band() -> None:
    """
    Description:
        _Stamp_Image appends the stamp on a footer band BELOW the content: the content
        rows are untouched (never occluded) and the image grows by the band height, with
        the drawn text making the band non-uniform.
    """

    image = np.full((40, 200, 3), 127, np.uint8)
    stamped = analyze._Stamp_Image(image, '2026-09-16T17:00:00 | frame Image_001 abcdef0123')

    assert stamped.shape == (40 + analyze.CONST_STAMP_BAND_H, 200, 3)
    assert np.array_equal(stamped[:40], image)            # content is preserved, not drawn over
    band = stamped[40:]
    assert band.std() > 0                                  # the stamp text marks the band


def test_descriptions_file_opens_with_the_provenance_stamp(tmp_path) -> None:
    """
    Description:
        The descriptions file leads with the stamp as a comment line, so a stale .txt is
        identifiable on opening; the Screen-Understanding body follows it.
    """

    result = types.SimpleNamespace(Objects=[], Background='A plain green surface.')
    # __file__ is a readable file to fingerprint; the stamp's exact frame does not matter here.
    stamp = analyze._Stamp_Line('Image_001', __file__, '2026-09-16T17:00:00', 'refhash0001', 'florence')
    path = tmp_path / 'Image_001_descriptions.txt'
    analyze._Write_Descriptions(str(path), result, stamp)

    lines = path.read_text().splitlines()
    assert lines[0].startswith('# ')
    assert '2026-09-16T17:00:00' in lines[0] and 'florence' in lines[0]
    assert len(lines) > 1                                  # the reading follows the stamp


def test_missing_reference_fails_before_writing_anything(tmp_path, monkeypatch) -> None:
    """
    Description:
        The core anti-staleness guarantee: with a scene present but the reference
        unreadable, main() returns non-zero and writes NOTHING — no output directory of
        finished-looking artefacts from a run that did not succeed. This is the exact
        failure that let a stale montage and .txt pass review.
    """

    in_dir = tmp_path / 'in'; in_dir.mkdir()
    out_dir = tmp_path / 'out'
    # A discoverable scene, and a reference that exists by name but cannot be read.
    (in_dir / 'Image_001.png').write_bytes(b'\x89PNG\r\n')     # discovered by glob, never read
    (in_dir / 'Image_Background_001.png').write_bytes(b'')     # present but unreadable -> imread None

    monkeypatch.setattr('sys.argv',
                        ['analyze.py', '--input-dir', str(in_dir), '--output-dir', str(out_dir)])
    code = analyze.main()

    assert code == 1
    # Nothing written: the output directory was never even created past the gate.
    assert (not out_dir.exists()) or (os.listdir(str(out_dir)) == [])
