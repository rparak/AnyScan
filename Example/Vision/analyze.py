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
# File Name: ../Example/Vision/analyze.py
## =========================================================================== ##

# System (Default)
import sys
import os
import argparse
# Provenance stamping: a content fingerprint of each source file and a run timestamp,
# so an artefact left over from an earlier or failed run is identifiable on sight.
import datetime
# Resolve the project folder from this file's own location (Example/Vision -> ..),
# so the script runs the same whether launched from Example/Vision/ or the repo root.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    '..', '..'))
_SRC = os.path.join(CONST_PROJECT_FOLDER, 'src')
if _SRC not in sys.path:
    sys.path.append(_SRC)
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan vision — the pipeline, its errors, and data-file discovery
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Florence_Vision_Cls, Vision_Error_Cls
#   ../Vision/Segmenter
import Vision.Segmenter as Vision_Segmenter
from Vision.Segmenter import Segmenter_Error_Cls
#   ../Vision/Utilities/Discovery
from Vision.Utilities.Discovery import Discover_Scenes, Select_Background, Discovery_Error_Cls
#   ../Vision/Utilities/Provenance
import Vision.Utilities.Provenance as Provenance
#   ../Vision/Utilities/Annotate
from Vision.Utilities.Annotate import Draw_Annotated, Draw_Label_Mask
#   ../Reporting/Core
from Reporting.Core import Screen_Understanding
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str

"""
Description:
    Initialization of constants.

    The validation harness for the ported vision pipeline. It runs EVERY committed
    Data/Camera/Image_[0-9]*.png frame through the application's own Vision.Core.Analyze
    (never a second copy of the pipeline) against the empty-surface reference, and for
    each frame writes the three artefacts of §1c to Data/Camera/Results/:

        <stem>_annotated.png     the frame with each object's fill, contour, box, index
        <stem>_mask.png          the label mask: black ground, each object its own colour
        <stem>_descriptions.txt  one line per object (the model's caption)

    Then it reports the per-frame object count, the raw FastSAM mask count and the
    per-cue attribution, so the detection can be judged against the known inventory.

    Note:
        The drawing here is deliberately throwaway (a fixed BGR palette, Hershey text)
        — the themed, resolution-scaled renderer that makes the annotated image look
        like the PyQt application is a later step. The single job of this phase is to
        make the DETECTION visible so it can be checked before any UI is built on it.
"""
# Committed inputs live here; the three per-frame artefacts are written here
# (git-ignored) by default.
#   Unit [string]
CONST_INPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Camera')
CONST_OUTPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Camera', 'Results')

# Throwaway per-object colours (BGR), one per index, cycled past the tenth object.
# The montage cell size (px) for the optional enhanced-crop debug view.
#   Unit [int]
CONST_MONTAGE_CELL = 260

# The provenance stamp constants live in the shared Vision.Utilities.Provenance module,
# re-exported here so this harness's own names keep working. EVERY artefact carries the
# run timestamp and the source frame's content fingerprint on a footer band, so a file
# left over from an earlier or failed run is identifiable by looking at it, instead of
# masquerading as current output — the failure mode that let a stale montage and .txt,
# written before the reference went missing, pass review as if they were fresh.
#   Unit [int]
CONST_STAMP_BAND_H = Provenance.CONST_STAMP_BAND_H
#   Unit [float]
CONST_STAMP_FONT_SCALE = Provenance.CONST_STAMP_FONT_SCALE
#   Unit [int]
CONST_FINGERPRINT_LEN = Provenance.CONST_FINGERPRINT_LEN


def _Fingerprint(path: str) -> str:
    """
    Description:
        The short content fingerprint of a file — delegated to the shared
        Provenance.Fingerprint, so the harness and the capture writer fingerprint the
        same way.

    Args:
        (1) path [string]: The file to fingerprint.

    Returns:
        (1) parameter [string]: The short hex fingerprint.
    """

    return Provenance.Fingerprint(path)


def _Stamp_Line(stem: str, scene_path: str, run_stamp: str, reference_hash: str,
                describer: str) -> str:
    """
    Description:
        The one-line provenance stamp shared by every artefact of a frame: the run
        timestamp, the frame's stem and content fingerprint, the reference's
        fingerprint, and the describer that wrote the captions. It is written into the
        descriptions header and drawn onto each image, so a stale file names the run and
        the exact inputs that produced it.

    Args:
        (1) stem [string]: The frame stem (e.g. 'Image_001').
        (2) scene_path [string]: The source frame path (fingerprinted here).
        (3) run_stamp [string]: The run timestamp, ISO-8601 to the second.
        (4) reference_hash [string]: The empty-surface reference's fingerprint.
        (5) describer [string]: The describer that wrote the captions.

    Returns:
        (1) parameter [string]: The provenance line.
    """

    return ('%s | frame %s %s | ref %s | describer %s'
            % (run_stamp, stem, _Fingerprint(scene_path), reference_hash, describer))


def _Stamp_Image(image: tp.Any, text: str) -> tp.Any:
    """
    Description:
        Return the image with the provenance stamp on a slim footer band below it —
        delegated to the shared Provenance.Stamp_Image so every writer stamps alike.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The artefact image (BGR).
        (2) text [string]: The provenance line (see _Stamp_Line).

    Returns:
        (1) parameter [Matrix<uint8> (H+band)xWx3]: The stamped image.
    """

    return Provenance.Stamp_Image(image, text, cv2, np)


def _Write_Descriptions(path: str, result: Analysis_Str, stamp: str) -> None:
    """
    Description:
        Write the Screen-Understanding text — the background stated once on the first
        line with the object count, then one background-stripped line per object — via
        the SAME Reporting.Screen_Understanding the application panel renders from, so
        the file and the view can never drift apart. The provenance stamp is written as
        a leading comment line, so a stale descriptions file is identifiable on opening.

    Args:
        (1) path [string]: The descriptions file path.
        (2) result [Analysis_Str(object)]: The finished analysis.
        (3) stamp [string]: The provenance line (see _Stamp_Line).
    """

    with open(path, 'w') as handle:
        handle.write('# ' + stamp + '\n')
        handle.write(Screen_Understanding(result.Objects, result.Background) + '\n')


def _Montage(enhanced_crops: tp.List[tp.Any], cols: int = 3) -> tp.Optional[tp.Any]:
    """
    Description:
        Tile the already-enhanced object crops into a single inspection image. This is
        PURE rendering: it tiles the crops the pipeline produced (Detection_Str.Enhanced_Crop)
        and does not re-enhance them, so the montage shows exactly what Florence-2
        received. It is a debug view, off by default, and is not one of the three
        standard per-frame artefacts.

    Args:
        (1) enhanced_crops [Vector<Matrix<uint8> hxwx3>]: The enhanced crops, in order.
        (2) cols [int]: The number of columns in the tiling.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3 or None]: The montage, or None when empty.
    """

    crops = [crop for crop in enhanced_crops if crop is not None]
    if not crops:
        return None
    cell = CONST_MONTAGE_CELL
    tiles = []
    for crop in crops:
        ch, cw = crop.shape[:2]
        scale = min(cell / cw, cell / ch)
        resized = cv2.resize(crop, (max(1, int(cw * scale)), max(1, int(ch * scale))))
        canvas = np.full((cell, cell, 3), 40, np.uint8)
        rh, rw = resized.shape[:2]
        y0, x0 = (cell - rh) // 2, (cell - rw) // 2
        canvas[y0:y0 + rh, x0:x0 + rw] = resized
        tiles.append(canvas)
    rows = []
    for i in range(0, len(tiles), cols):
        row = tiles[i:i + cols]
        while len(row) < cols:
            row.append(np.full((cell, cell, 3), 40, np.uint8))
        rows.append(np.hstack(row))
    return np.vstack(rows)


def _Banner(title: str, lines: tp.List[str]) -> None:
    """
    Description:
        Print an impossible-to-miss banner for a first-run failure (e.g. weights
        absent) — a full-width rule, the title, and the actionable sentence — so it is
        never a quiet failure or a bare traceback.

    Args:
        (1) title [string]: The banner title.
        (2) lines [Vector<string>]: The message lines under it.
    """

    rule = '=' * 78
    print('\n' + rule)
    print('  ' + title)
    print(rule)
    for line in lines:
        print('  ' + line)
    print(rule + '\n')


def _Configure(args: argparse.Namespace) -> None:
    """
    Description:
        Push the CLI options onto the pipeline's CONST_* configuration interface — the
        device for both models, the FastSAM weights, and the describer.

    Args:
        (1) args [argparse.Namespace(object)]: The parsed arguments.
    """

    if args.device:
        Vision_Core.CONST_VISION_DEVICE = args.device
        Vision_Segmenter.CONST_SEGMENTER_DEVICE = args.device
    if args.weights:
        Vision_Segmenter.CONST_SEGMENTER_WEIGHTS = os.path.abspath(args.weights)
    if args.no_describe:
        Vision_Core.CONST_DESCRIBER = 'fallback'


def _Analyze_Frame(backend: Florence_Vision_Cls, scene_path: str, output_dir: str,
                   write_descriptions: bool, write_montage: bool,
                   run_stamp: str, reference_hash: str) -> tp.Optional[Analysis_Str]:
    """
    Description:
        Run one scene through the application pipeline and write its artefacts — the
        annotated image and the label mask always; the descriptions file ONLY when the
        real describer ran (write_descriptions); the enhanced-crop montage when
        requested — into the output directory. Every artefact carries the provenance
        stamp (run timestamp, frame fingerprint, reference fingerprint, describer), so
        a file from an earlier or failed run is identifiable on sight. Returns the
        analysis, or None on a vision error (already reported through a banner).

        The descriptions file is skipped under the fallback describer: its placeholder
        captions are not the real reading, and silently overwriting a Florence
        *_descriptions.txt with them is how a stale artefact ends up looking finished.

    Args:
        (1) backend [Florence_Vision_Cls(object)]: The vision backend.
        (2) scene_path [string]: The scene image path.
        (3) output_dir [string]: The directory to write the artefacts into.
        (4) write_descriptions [bool]: Write the descriptions file (real describer only).
        (5) write_montage [bool]: Also write the enhanced-crop debug montage.
        (6) run_stamp [string]: The run timestamp shared by every artefact of this run.
        (7) reference_hash [string]: The empty-surface reference's fingerprint.

    Returns:
        (1) parameter [Analysis_Str(object) or None]: The analysis, or None on failure.
    """

    stem = os.path.splitext(os.path.basename(scene_path))[0]
    scene_bgr = cv2.imread(scene_path)
    if scene_bgr is None:
        _Banner('SCENE UNREADABLE', ['Could not read the scene image: %s' % scene_path])
        return None
    scene_rgb = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2RGB)
    try:
        result = backend.Analyze(scene_rgb)
    except Segmenter_Error_Cls as error:
        _Banner('FASTSAM WEIGHTS NOT VERIFIED - segmentation could not run', [str(error)])
        return None
    except Vision_Error_Cls as error:
        _Banner('VISION RUNTIME ERROR - the pipeline could not run', [str(error)])
        return None

    stamp = _Stamp_Line(stem, scene_path, run_stamp, reference_hash, Vision_Core.CONST_DESCRIBER)
    cv2.imwrite(os.path.join(output_dir, '%s_annotated.png' % stem),
                _Stamp_Image(Draw_Annotated(scene_bgr, result.Objects, cv2, np), stamp))
    cv2.imwrite(os.path.join(output_dir, '%s_mask.png' % stem),
                _Stamp_Image(Draw_Label_Mask(result.Objects, scene_bgr.shape, cv2, np), stamp))
    if write_descriptions:
        _Write_Descriptions(os.path.join(output_dir, '%s_descriptions.txt' % stem), result, stamp)
    if write_montage:
        montage = _Montage([det.Enhanced_Crop for det in result.Objects])
        if montage is not None:
            cv2.imwrite(os.path.join(output_dir, '%s_enhanced.png' % stem), _Stamp_Image(montage, stamp))
    return result


def main() -> int:
    """
    Description:
        Discover every scene and the reference in the input directory, run each scene
        through the application pipeline, write its three artefacts, and report the
        per-frame object count, raw FastSAM mask count and per-cue attribution plus the
        total. The exit code is non-zero when the inputs cannot be resolved or the
        weights/runtime are missing, so the script gates a CI check.

    Returns:
        (1) parameter [int]: The process exit code (0 on success).
    """

    parser = argparse.ArgumentParser(description='Run the AnyScan vision pipeline over every Data/Camera frame.')
    parser.add_argument('--input-dir', default=CONST_INPUT_DIR, help='directory holding the scene frames and the reference')
    parser.add_argument('--output-dir', default=CONST_OUTPUT_DIR, help='where to write the per-frame artefacts')
    parser.add_argument('--background', default=None, help='explicit reference filename (overrides the highest-index rule)')
    parser.add_argument('--weights', default=None, help='FastSAM weights path (overrides the default)')
    parser.add_argument('--device', default=None, help="compute device: 'cpu', 'cuda', 'mps' or 'auto'")
    parser.add_argument('--no-describe', action='store_true',
                        help='use the model-free fallback describer (no VLM); does NOT write descriptions files')
    parser.add_argument('--montage', action='store_true', help='also write the enhanced-crop debug montage (off by default)')
    args = parser.parse_args()

    _Configure(args)

    # Resolve the scenes and the reference by the documented discovery rules.
    try:
        scenes = Discover_Scenes(args.input_dir)
        reference_path = Select_Background(args.input_dir, args.background)
    except Discovery_Error_Cls as error:
        _Banner('INPUT DISCOVERY FAILED', [str(error)])
        return 1
    if not scenes:
        _Banner('NO SCENE FRAMES FOUND',
                ['No Image_[0-9]*.png scene frames were found in: %s' % os.path.abspath(args.input_dir)])
        return 1

    # Fail loudly and EARLY: every frame is differenced against the reference, so a
    # missing or unreadable reference means no caption is real. Verify it is readable
    # before a single artefact is written, so a failed run never leaves output that
    # looks finished (the reference had been cleaned out from under an earlier run).
    if cv2.imread(reference_path) is None:
        _Banner('BACKGROUND REFERENCE UNREADABLE',
                ['The empty-surface reference could not be read: %s' % reference_path,
                 'Every frame is differenced against it, so without it no caption is real.',
                 'Refusing to write artefacts that would look finished. Restore the reference.'])
        return 1
    reference_hash = _Fingerprint(reference_path)

    # Point the pipeline at this run's reference (the same mechanism the app's
    # --background flag uses), and describe once through the application backend. One
    # timestamp stamps every artefact of this run.
    Vision_Core.CONST_BACKGROUND_REF = reference_path
    run_stamp = datetime.datetime.now().isoformat(timespec='seconds')
    os.makedirs(args.output_dir, exist_ok=True)
    print('[INFO] Reference: %s (%s)' % (reference_path, reference_hash))
    print('[INFO] Scenes   : %d frame(s) in %s' % (len(scenes), os.path.abspath(args.input_dir)))
    print('[INFO] Describer: %s' % Vision_Core.CONST_DESCRIBER)
    print('[INFO] Run stamp: %s\n' % run_stamp)

    backend = Florence_Vision_Cls()
    total_objects = 0
    rows = []
    for scene_path in scenes:
        stem = os.path.splitext(os.path.basename(scene_path))[0]
        result = _Analyze_Frame(backend, scene_path, args.output_dir,
                                not args.no_describe, args.montage, run_stamp, reference_hash)
        if result is None:
            return 1
        cues = {}
        for det in result.Objects:
            cues[det.Cue] = cues.get(det.Cue, 0) + 1
        total_objects += len(result.Objects)
        rows.append((stem, len(result.Objects), result.Raw_Mask_Count, cues, result.Latency_Ms))
        print('[INFO] %s: %d object(s)  raw FastSAM=%d  cues=%s  (%d ms)'
              % (stem, len(result.Objects), result.Raw_Mask_Count, cues, result.Latency_Ms))
        if result.Background:
            print('[INFO]     background = %s' % result.Background)
        for i, det in enumerate(result.Objects, 1):
            print('[INFO]     Obj. %d [%s] - %s' % (i, det.Cue, det.Sentence))
        # The post-processing audit: every background strip and substance substitution,
        # so over-stripping surfaces here instead of passing silently.
        for level, message in result.Audit:
            print('[%s]     %s' % (level.upper(), message))

    print('\n[INFO] %-14s %8s %12s   %s' % ('frame', 'objects', 'raw FastSAM', 'cues'))
    for stem, count, raw, cues, _ in rows:
        print('[INFO] %-14s %8d %12d   %s' % (stem, count, raw, cues))
    print('[INFO] %-14s %8d' % ('TOTAL', total_objects))
    print('[INFO] Artefacts written to: %s' % os.path.abspath(args.output_dir))
    return 0


if __name__ == '__main__':
    sys.exit(main())
