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
# File Name: ../Example/Vision/analyze.py
## =========================================================================== ##

# System (Default)
import sys
import os
import glob
import hashlib
import argparse
# Provenance stamping: a content fingerprint of each source file and a run timestamp,
# so an artefact left over from an earlier or failed run is identifiable on sight.
import datetime
# Dataclasses (a configuration copy with the CLI overrides applied)
import dataclasses
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
# Custom Lib.: AnyScan vision — the pipeline and its errors
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Vision_Pipeline_Cls, Vision_Error_Cls
#   ../Vision/Segmenter
from Vision.Segmenter import Segmenter_Error_Cls
#   ../Vision/Utilities/Annotate
from Vision.Utilities.Annotate import Render_Views
#   ../Reporting/Core
from Reporting.Core import Screen_Understanding, Object_Size, Dimension_Check_Text, Verdict_Log_Line, Part_Lines
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str, CONST_VERDICTS
# Custom Lib.: AnyScan — the ONE configuration layer the application loads its configuration
# through, so the harness runs exactly the stages, mode and scale the app runs
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, Configuration_Error_Cls, CONST_DEFAULT_CONFIG_FILE
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str
#   ../Calibration/Core — the natural sort key ('Image_2' before 'Image_10')
from Calibration.Core import Natural_Key

"""
Description:
    Initialization of constants.

    The validation harness for the ported vision pipeline. It runs EVERY Image_[0-9]*.png frame
    in the configuration's Evaluation.Frames directory (Data/Images/Test) through the
    application's own Vision.Core.Analyze (never a second copy of the pipeline) against the
    configuration's empty-surface reference, and for each frame writes these artefacts to
    Data/Results/:

        <stem>_annotated.png     the frame with each object's fill, contour, box, index
        <stem>_mask.png          the label mask: black ground, each object its own colour
        <stem>_descriptions.txt  one line per object (the model's caption)
        <stem>_objNN_crop.png    each object's enhanced crop: what the describer was given

    Then it reports the per-frame object count, the raw FastSAM mask count and the
    per-cue attribution, so the detection can be judged against the known inventory.

    Note:
        The annotated image and the mask are drawn by the application's own renderers
        (Vision.Utilities.Annotate, through Render_Views), so what the harness writes is what the
        application shows and stores; test/UI/test_harness_parity.py holds the two together.
"""
# Where the per-frame artefacts are written (git-ignored). The input frames are not a
# default here: they come from the configuration's Evaluation.Frames, or --input-dir.
#   Unit [string]
CONST_OUTPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Results')

# Each object's enhanced crop — exactly the image the describer receives — is written as
# <stem>_objNN_crop.png, NN its 1-based index in the object list (the number drawn on the annotated
# image and the 'Object N' line), zero-padded so the files sort in object order.
#   Unit [string]
CONST_CROP_NAME = '%s_obj%02d_crop.png'

# The montage cell size (px) for the optional enhanced-crop debug view.
#   Unit [int]
CONST_MONTAGE_CELL = 260

# The scene-frame glob. Image_<n>.png (any number of digits) are the scene captures, so Image_010
# and beyond are found rather than silently skipped. The empty-surface reference is excluded:
# the digit class requires a digit straight after 'Image_', which 'Image_Background_*' never has.
#   Unit [string]
CONST_SCENE_GLOB = 'Image_[0-9]*.png'

# EVERY artefact carries the run timestamp and the source frame's content fingerprint on a footer
# band, so a file left over from an earlier or failed run is identifiable by looking at it instead
# of masquerading as current output — the failure mode that let a stale montage and .txt, written
# before the reference went missing, pass review as if they were fresh. The band's height (px) and
# text scale, and the number of leading hex digits of a file's MD5 digest taken as its fingerprint.
#   Unit [int]
CONST_STAMP_BAND_H = 26
#   Unit [float]
CONST_STAMP_FONT_SCALE = 0.5
#   Unit [int]
CONST_FINGERPRINT_LEN = 10


def Discover_Scenes(data_dir: str) -> tp.List[str]:
    """
    Description:
        The scene frames in a directory, naturally sorted (Image_2 before Image_10): a glob of
        CONST_SCENE_GLOB, never a hard-coded range, so a gap in the numbering is tolerated and the
        empty-surface reference is not among them. The reference itself is never discovered: it is
        the station's Background.Reference (Station_<Hardware>.yaml).

    Args:
        (1) data_dir [string]: The directory to search for scene frames.

    Returns:
        (1) parameter [Vector<string>]: The scene-frame paths, naturally sorted.
    """

    return sorted(glob.glob(os.path.join(data_dir, CONST_SCENE_GLOB)),
                  key=lambda path: Natural_Key(os.path.basename(path)))


def _Fingerprint(path: str) -> str:
    """
    Description:
        The short content fingerprint of a file: the first CONST_FINGERPRINT_LEN hex digits of its
        MD5 digest. Two runs over the same bytes fingerprint the same, so an artefact whose
        fingerprint no longer matches its source is stale on sight. Provenance, not security.

    Args:
        (1) path [string]: The file to fingerprint.

    Returns:
        (1) parameter [string]: The short hex fingerprint.
    """

    with open(path, 'rb') as handle:
        return hashlib.md5(handle.read()).hexdigest()[:CONST_FINGERPRINT_LEN]


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
        Return the image with the provenance stamp on a slim footer band appended BELOW it — never
        drawn over the content, so it labels the artefact without occluding anything under review.
        On an image narrower than the line (an object crop) the stamp wraps at its ' | ' separators,
        one band per line, so it is never clipped and the image is never widened.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The artefact image (BGR).
        (2) text [string]: The provenance line (see _Stamp_Line).

    Returns:
        (1) parameter [Matrix<uint8> (H+bands)xWx3]: The stamped image.
    """

    width = image.shape[1]
    lines = []
    for part in text.split(' | '):
        joined = part if not lines else lines[-1] + ' | ' + part
        fits = cv2.getTextSize(joined, cv2.FONT_HERSHEY_SIMPLEX, CONST_STAMP_FONT_SCALE, 1)[0][0] <= width - 16
        if lines and fits:
            lines[-1] = joined
        else:
            lines.append(part)
    bands = []
    for line in lines:
        band = np.full((CONST_STAMP_BAND_H, width, 3), 24, np.uint8)
        cv2.putText(band, line, (8, CONST_STAMP_BAND_H - 9), cv2.FONT_HERSHEY_SIMPLEX,
                    CONST_STAMP_FONT_SCALE, (210, 210, 210), 1, cv2.LINE_AA)
        bands.append(band)
    return np.vstack([image] + bands)


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


def _Write_Crops(output_dir: str, stem: str, result: Analysis_Str, stamp: str) -> None:
    """
    Description:
        Write each object's enhanced crop — the padded, neighbour-isolated, stretched image the
        describer actually received (Detection_Str.Enhanced_Crop), not a re-render — as
        CONST_CROP_NAME, stamped like every artefact. This frame's crops from an earlier run are
        removed first, so a frame that now has fewer objects cannot keep a stale obj07 that looks
        current. A merged pair is one object, so it is one crop holding both parts.

    Args:
        (1) output_dir [string]: The directory the artefacts are written to.
        (2) stem [string]: The frame stem (e.g. 'Image_012').
        (3) result [Analysis_Str(object)]: The finished analysis.
        (4) stamp [string]: The provenance line (see _Stamp_Line).
    """

    for old in glob.glob(os.path.join(output_dir, glob.escape(stem) + '_obj[0-9]*_crop.png')):
        os.remove(old)
    for index, det in enumerate(result.Objects, 1):
        if det.Enhanced_Crop is not None:
            cv2.imwrite(os.path.join(output_dir, CONST_CROP_NAME % (stem, index)),
                        _Stamp_Image(det.Enhanced_Crop, stamp))


def _Montage(enhanced_crops: tp.List[tp.Any], cols: int = 3) -> tp.Optional[tp.Any]:
    """
    Description:
        Tile the already-enhanced object crops into a single inspection image. This is
        PURE rendering: it tiles the crops the pipeline produced (Detection_Str.Enhanced_Crop)
        and does not re-enhance them, so the montage shows exactly what the describer
        received, side by side. It is a debug view, off by default; the same crops are always
        written one per object (_Write_Crops), which is the view to inspect a single object in.

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


def _Configure(args: argparse.Namespace, Configuration_Str: Configuration_Str) -> Configuration_Str:
    """
    Description:
        Apply the CLI overrides to a copy of the loaded configuration — the FastSAM device (Gemma
        runs on MLX's Metal GPU regardless) and the FastSAM weights — and select the model-free
        describer on --no-describe. The file itself is never edited.

    Args:
        (1) args [argparse.Namespace(object)]: The parsed arguments.
        (2) Configuration_Str [Configuration_Str(object)]: The loaded configuration.

    Returns:
        (1) parameter [Configuration_Str(object)]: The configuration with the overrides applied.
    """

    overrides = {}
    if args.device:
        overrides['Device'] = args.device
    if args.weights:
        overrides['Model_Path'] = os.path.abspath(args.weights)
    if args.no_describe:
        Vision_Core.CONST_DESCRIBER = 'fallback'
    if not overrides:
        return Configuration_Str
    return dataclasses.replace(Configuration_Str,
                               Segmentation=dataclasses.replace(Configuration_Str.Segmentation, **overrides))


def _Analyze_Frame(backend: Vision_Pipeline_Cls, scene_path: str, output_dir: str,
                   write_descriptions: bool, write_montage: bool,
                   run_stamp: str, reference_hash: str,
                   classification_enabled: bool) -> tp.Optional[Analysis_Str]:
    """
    Description:
        Run one scene through the application pipeline and write its artefacts — the
        annotated image, the label mask and each object's enhanced crop always; the
        descriptions file ONLY when the
        real describer ran (write_descriptions); the enhanced-crop montage when
        requested — into the output directory. Every artefact carries the provenance
        stamp (run timestamp, frame fingerprint, reference fingerprint, describer), so
        a file from an earlier or failed run is identifiable on sight. Returns the
        analysis, or None on a vision error (already reported through a banner).

        The descriptions file is skipped under the fallback describer: its placeholder
        captions are not the real reading, and silently overwriting a model-written
        *_descriptions.txt with them is how a stale artefact ends up looking finished.

    Args:
        (1) backend [Vision_Pipeline_Cls(object)]: The vision backend.
        (2) scene_path [string]: The scene image path.
        (3) output_dir [string]: The directory to write the artefacts into.
        (4) write_descriptions [bool]: Write the descriptions file (real describer only).
        (5) write_montage [bool]: Also write the enhanced-crop debug montage.
        (6) run_stamp [string]: The run timestamp shared by every artefact of this run.
        (7) reference_hash [string]: The empty-surface reference's fingerprint.
        (8) classification_enabled [bool]: The configuration's classification flag.

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
    annotated, mask = Render_Views(scene_bgr, result.Objects, cv2, np, verdict_colored=classification_enabled)
    cv2.imwrite(os.path.join(output_dir, '%s_annotated.png' % stem), _Stamp_Image(annotated, stamp))
    cv2.imwrite(os.path.join(output_dir, '%s_mask.png' % stem), _Stamp_Image(mask, stamp))
    if write_descriptions:
        _Write_Descriptions(os.path.join(output_dir, '%s_descriptions.txt' % stem), result, stamp)
    _Write_Crops(output_dir, stem, result, stamp)
    if write_montage:
        montage = _Montage([det.Enhanced_Crop for det in result.Objects])
        if montage is not None:
            cv2.imwrite(os.path.join(output_dir, '%s_enhanced.png' % stem), _Stamp_Image(montage, stamp))
    return result


def _Parse_Arguments() -> argparse.Namespace:
    """
    Description:
        The harness's command line.

    Returns:
        (1) parameter [argparse.Namespace(object)]: The parsed arguments.
    """

    parser = argparse.ArgumentParser(description='Run the AnyScan vision pipeline over every test frame.')
    parser.add_argument('--input-dir', default=None,
                        help="directory of Image_NNN.png frames (default: the configuration's Evaluation.Frames)")
    parser.add_argument('--output-dir', default=CONST_OUTPUT_DIR, help='where to write the per-frame artefacts')
    parser.add_argument('--weights', default=None, help='FastSAM weights path (overrides the default)')
    parser.add_argument('--device', default=None,
                        help="compute device for FastSAM: 'cpu', 'cuda', 'mps' or 'auto'")
    parser.add_argument('--no-describe', action='store_true',
                        help='use the model-free fallback describer (no VLM); does NOT write descriptions files')
    parser.add_argument('--montage', action='store_true', help='also write the enhanced-crop debug montage (off by default)')
    parser.add_argument('--config', default=CONST_DEFAULT_CONFIG_FILE,
                        help='the configuration to run (default: the one the application loads)')
    return parser.parse_args()


def _Resolve_Inputs(args: argparse.Namespace, configuration: Configuration_Str) -> tp.Optional[tp.List[str]]:
    """
    Description:
        The scenes to run, checked before a single artefact is written: found by the documented
        discovery rule in --input-dir or the configuration's Evaluation.Frames; the configuration's
        reference readable (every frame is differenced against it, so without it no caption is
        real — and a failed run must never leave output that looks finished); every frame the
        camera's window size, as the reference is. Each refusal is a banner naming what to fix.

    Args:
        (1) args [argparse.Namespace(object)]: The parsed arguments (input_dir is filled in).
        (2) configuration [Configuration_Str(object)]: The loaded configuration.

    Returns:
        (1) parameter [Vector<string> or None]: The scene paths, or None when the run is refused.
    """

    if args.input_dir is None:
        args.input_dir = configuration.Evaluation.Frames
    if not args.input_dir:
        _Banner('NO TEST FRAMES CONFIGURED',
                ["The configuration '%s' does not set Evaluation.Frames, and no --input-dir was given."
                 % configuration.Name, 'Set Evaluation.Frames (e.g. Data/Images/Test) or pass --input-dir.'])
        return None
    scenes = Discover_Scenes(args.input_dir)
    if not scenes:
        _Banner('NO SCENE FRAMES FOUND',
                ['No Image_[0-9]*.png scene frames were found in: %s' % os.path.abspath(args.input_dir)])
        return None
    reference_path = configuration.Segmentation.Background_Reference
    if cv2.imread(reference_path) is None:
        _Banner('BACKGROUND REFERENCE UNREADABLE',
                ['The empty-surface reference could not be read: %s' % reference_path,
                 'Every frame is differenced against it, so without it no caption is real.',
                 'Refusing to write artefacts that would look finished. Restore the reference.'])
        return None
    wrong = []
    for scene in scenes:
        frame = cv2.imread(scene, cv2.IMREAD_UNCHANGED)
        size = None if frame is None else (int(frame.shape[1]), int(frame.shape[0]))
        if size != tuple(configuration.Camera.Resolution):
            wrong.append('%s: %s' % (os.path.basename(scene), 'unreadable' if size is None else '%d × %d' % size))
    if wrong:
        _Banner('TEST FRAMES OF THE WRONG SIZE',
                ['Camera.Resolution is %d × %d; these frames are not:' % tuple(configuration.Camera.Resolution)]
                + wrong + ['Refusing to write artefacts. Use frames captured at this window.'])
        return None
    return scenes


def _Print_Run_Header(configuration: Configuration_Str, scenes: tp.List[str], input_dir: str,
                      reference_hash: str, run_stamp: str) -> None:
    """
    Description:
        What this run is: the reference and its fingerprint, the scenes, the describer, the
        configuration and its classification mode, the run stamp, and the measurement scale — or a
        warning that nothing will be measured, never a size from a default.

    Args:
        (1) configuration [Configuration_Str(object)]: The loaded configuration.
        (2) scenes [Vector<string>]: The scene paths.
        (3) input_dir [string]: Where they were found.
        (4) reference_hash [string]: The reference's fingerprint.
        (5) run_stamp [string]: The run timestamp.
    """

    print('[INFO] Reference: %s (%s)' % (configuration.Segmentation.Background_Reference, reference_hash))
    print('[INFO] Scenes   : %d frame(s) in %s' % (len(scenes), os.path.abspath(input_dir)))
    print('[INFO] Describer: %s' % Vision_Core.CONST_DESCRIBER)
    print('[INFO] Config   : %s' % configuration.Name)
    print('[INFO] Classify : %s' % ('enabled' if configuration.Classifies else 'disabled'))
    if configuration.Catalogue is not None:
        print('[INFO] Catalogue: %s (%s)' % (configuration.Catalogue.Name, configuration.Catalogue.Path))
    print('[INFO] Run stamp: %s\n' % run_stamp)
    scale = configuration.Scale
    if scale is None:
        print('[WARNING] %s has no calibration Conversion_Factor; objects will not be measured.'
              % configuration.Name)
    elif scale.Height_Mm is not None:
        print('[INFO] Scale    : %.5f x %.5f mm/px at %.2f mm above the table (the catalogue part\'s top face)'
              % (scale.Mm_Per_Px_X, scale.Mm_Per_Px_Y, scale.Height_Mm))
    else:
        print('[INFO] Scale    : %.5f x %.5f mm/px' % (scale.Mm_Per_Px_X, scale.Mm_Per_Px_Y))


def _Report_Frame(stem: str, result: Analysis_Str) -> tp.Tuple[str, int, int, tp.Dict[str, int], int]:
    """
    Description:
        Print one frame's result — the object count, the raw FastSAM mask count, the per-cue
        attribution, the background, each object with its cue and size, and the post-processing
        audit (so over-stripping surfaces instead of passing silently) — and return its summary row.

    Args:
        (1) stem [string]: The frame's stem (e.g. 'Image_001').
        (2) result [Analysis_Str(object)]: The frame's reading.

    Returns:
        (1) parameter [Tuple]: (stem, objects, raw FastSAM masks, cues, latency in ms).
    """

    cues = {}
    for det in result.Objects:
        cues[det.Cue] = cues.get(det.Cue, 0) + 1
    print('[INFO] %s: %d object(s)  raw FastSAM=%d  cues=%s  (%d ms)'
          % (stem, len(result.Objects), result.Raw_Mask_Count, cues, result.Latency_Ms))
    if result.Background:
        print('[INFO]     background = %s' % result.Background)
    for i, det in enumerate(result.Objects, 1):
        size = Object_Size(det)
        print('[INFO]     Obj. %d [%s]%s - %s' % (i, det.Cue, ' (%s)' % size if size else '', det.Sentence))
        for check in det.Dimension_Checks:
            print('[INFO]         %s' % Dimension_Check_Text(check))
        if det.Catalogue is not None:
            print('[INFO]         %s' % Verdict_Log_Line(i - 1, det)[1])
            for part_line in Part_Lines(i - 1, det):
                print('[INFO]           %s' % part_line)
    for level, message in result.Audit:
        print('[%s]     %s' % (level.upper(), message))
    return stem, len(result.Objects), result.Raw_Mask_Count, cues, result.Latency_Ms


def Reference_Frames(Configuration_Str: Configuration_Str, scenes: tp.List[str]) -> tp.Set[str]:
    """
    Description:
        The scenes that ARE the catalogue item's reference images (byte for byte, by content, not
        name): judging the item on the frames it was defined from is circular, so a catalogue run
        reports them apart. The reference images are the PNGs in the item's reference_image/ folder;
        none outside a catalogue mode.

    Args:
        (1) Configuration_Str [Configuration_Str(object)]: The loaded configuration.
        (2) scenes [Vector<string>]: The scene paths.

    Returns:
        (1) parameter [Set<string>]: The paths of the scenes that are reference images.
    """

    if Configuration_Str.Catalogue is None:
        return set()
    folder = os.path.join(os.path.dirname(Configuration_Str.Catalogue.Path), 'reference_image')
    references = {_Fingerprint(path) for path in glob.glob(os.path.join(folder, '*.png'))}
    return {path for path in scenes if _Fingerprint(path) in references}


def _Report_Verdicts(results: tp.List[tp.Tuple[str, Analysis_Str]], references: tp.Set[str]) -> None:
    """
    Description:
        A catalogue run's summary: how many objects took each state, and how many outlines were within the
        item's tolerance, on the test frames and, apart, on the item's reference frames (judging the item
        on the frames it was defined from is circular).

    Args:
        (1) results [Vector<Tuple<string, Analysis_Str(object)>>]: Each scene's path and analysis.
        (2) references [Set<string>]: The scenes that are the item's reference images.
    """

    for title, chosen in (('test frames', [r for r in results if r[0] not in references]),
                          ('reference frames', [r for r in results if r[0] in references])):
        objects = [det for _path, result in chosen for det in result.Objects]
        within = [det for det in objects
                  if det.Dimension_Checks and all(check.Within for check in det.Dimension_Checks)]
        states = ', '.join('%s %d' % (state, sum(det.Verdict == state for det in objects)) for state in CONST_VERDICTS)
        names = ', '.join(os.path.splitext(os.path.basename(path))[0] for path, _result in chosen)
        print('[INFO] On the %d %s: %s; outline within tolerance: %d object(s)%s'
              % (len(chosen), title, states, len(within),
                 ' (%s)' % names if title == 'reference frames' and names else ''))


def main() -> int:
    """
    Description:
        Discover every scene in the input directory (the reference is the configuration's
        station's Background.Reference, never discovered), run each scene through the
        application pipeline, write its artefacts, and report the per-frame object count,
        raw FastSAM mask count and per-cue attribution plus the total. The exit code is non-zero
        when the inputs cannot be resolved or the weights/runtime are missing, so the script gates
        a CI check.

    Returns:
        (1) parameter [int]: The process exit code (0 on success).
    """

    args = _Parse_Arguments()
    # The configuration, loaded ONCE through the application's configuration layer and validated
    # as a whole, so the harness runs the same stages, mode and scale the application runs.
    try:
        configuration = _Configure(args, Load_Configuration(args.config))
    except Configuration_Error_Cls as error:
        _Banner('CONFIGURATION REFUSED', [str(error)])
        return 1
    scenes = _Resolve_Inputs(args, configuration)
    if scenes is None:
        return 1

    # One timestamp stamps every artefact of this run; the reference's fingerprint is on each.
    reference_hash = _Fingerprint(configuration.Segmentation.Background_Reference)
    run_stamp = datetime.datetime.now().isoformat(timespec='seconds')
    os.makedirs(args.output_dir, exist_ok=True)
    _Print_Run_Header(configuration, scenes, args.input_dir, reference_hash, run_stamp)

    backend = Vision_Pipeline_Cls(Configuration_Str=configuration)
    rows, results = [], []
    for scene_path in scenes:
        result = _Analyze_Frame(backend, scene_path, args.output_dir, not args.no_describe, args.montage,
                                run_stamp, reference_hash, configuration.Classifies)
        if result is None:
            return 1
        rows.append(_Report_Frame(os.path.splitext(os.path.basename(scene_path))[0], result))
        results.append((scene_path, result))

    print('\n[INFO] %-14s %8s %12s   %s' % ('frame', 'objects', 'raw FastSAM', 'cues'))
    for stem, count, raw, cues, _latency in rows:
        print('[INFO] %-14s %8d %12d   %s' % (stem, count, raw, cues))
    print('[INFO] %-14s %8d' % ('TOTAL', sum(count for _stem, count, _raw, _cues, _latency in rows)))
    if configuration.Catalogue is not None:
        _Report_Verdicts(results, Reference_Frames(configuration, scenes))
    print('[INFO] Artefacts written to: %s' % os.path.abspath(args.output_dir))
    return 0


if __name__ == '__main__':
    sys.exit(main())
