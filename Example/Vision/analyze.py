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
import json
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
# Custom Lib.: AnyScan vision — the pipeline, its errors, and stage 1 for the debug view
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Florence_Vision_Cls, Vision_Error_Cls
#   ../Vision/Segmenter
import Vision.Segmenter as Vision_Segmenter
from Vision.Segmenter import Segmenter_Error_Cls
#   ../Vision/Utilities/Segmentation
from Vision.Utilities.Segmentation import Background_Foreground
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str

"""
Description:
    Initialization of constants.

    End-to-end demonstration of the four-stage FastSAM pipeline: read a background
    and a scene, run background subtraction -> FastSAM segmentation -> mask filtering
    -> description, and write an annotated result, a change-mask debug view, per-object
    crops / masks / descriptions and a summary.json. A real (reference, scene) image
    pair is required (see --input-dir / --background); the script fails with a clear
    message if none is found.

    CONST_* below are the defaults; the flags override them (see main).
"""
# Committed inputs live here; outputs are written here (git-ignored) by default.
#   Unit [string]
CONST_INPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Camera')
CONST_OUTPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Camera', 'Results')

# A filename containing one of these marks the reference (empty-surface) image; the
# other image in the directory is the scene.
#   Unit [Vector<string>]
CONST_REFERENCE_MARKERS = ('background', 'reference', 'empty', 'bg')
CONST_IMAGE_EXTS = ('.png', '.jpg', '.jpeg')

# Box / label colours for the annotated result, one per object index (BGR).
#   Unit [Vector<tuple>]
CONST_RESULT_COLORS = ((230, 70, 200), (70, 200, 230), (120, 220, 120),
                       (80, 130, 240), (210, 160, 70), (170, 120, 230))


def _Discover_Images(input_dir: str, background_override: tp.Optional[str]) -> tp.Optional[tp.Tuple[str, str]]:
    """
    Description:
        Find the reference and scene image paths in a directory. The reference is the
        file whose name carries a CONST_REFERENCE_MARKERS mark (or the explicit
        override); the scene is the first other image. Returns None when the directory
        has no usable pair, so the caller fails with a clear message.

    Args:
        (1) input_dir [string]: The directory to search.
        (2) background_override [string]: An explicit reference path, or None.

    Returns:
        (1) parameter [Tuple<string> 1x2 or None]: (reference path, scene path), or None.
    """

    if not os.path.isdir(input_dir):
        return None
    images = [os.path.join(input_dir, name) for name in sorted(os.listdir(input_dir))
              if os.path.splitext(name)[1].lower() in CONST_IMAGE_EXTS]
    if background_override:
        scenes = [p for p in images if os.path.abspath(p) != os.path.abspath(background_override)]
        return (background_override, scenes[0]) if scenes else None

    reference = next((p for p in images
                      if any(mark in os.path.basename(p).lower() for mark in CONST_REFERENCE_MARKERS)), None)
    scenes = [p for p in images if p != reference]
    if reference is None or not scenes:
        return None
    return reference, scenes[0]


def _Draw_Result(scene_bgr: tp.Any, objects: tp.List[Detection_Str]) -> tp.Any:
    """
    Description:
        The scene with each object's box and index drawn, colour-keyed by index. Only
        ASCII is passed to cv2.putText — Hershey fonts render non-ASCII as '?'.

    Args:
        (1) scene_bgr [Matrix<uint8> HxWx3]: The scene (BGR).
        (2) objects [Vector<Detection_Str(object)>]: The located objects, in order.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The annotated scene (BGR).
    """

    annotated = scene_bgr.copy()
    for i, det in enumerate(objects):
        color = CONST_RESULT_COLORS[i % len(CONST_RESULT_COLORS)]
        x, y, w, h = det.Bbox
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
        label = 'Object %d' % (i + 1)                # ASCII only
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        top = max(0, y - th - 8)
        cv2.rectangle(annotated, (x, top), (x + tw + 8, top + th + 8), color, thickness=-1)
        cv2.putText(annotated, label, (x + 4, top + th + 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return annotated


def _Draw_Change_Mask(change_mask: tp.Any, regions: tp.List[tp.Tuple[int, int, int, int]]) -> tp.Any:
    """
    Description:
        The change mask as a BGR image with the stage-1 candidate regions boxed — the
        debug view of what stage 1 handed the segmenter.

    Args:
        (1) change_mask [Matrix<uint8> HxW]: The stage-1 change mask (0 or 255).
        (2) regions [Vector<Tuple<int> 1x4>]: Candidate regions as (x1, y1, x2, y2).

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The debug view (BGR).
    """

    view = cv2.cvtColor(change_mask, cv2.COLOR_GRAY2BGR)
    for (x1, y1, x2, y2) in regions:
        cv2.rectangle(view, (x1, y1), (x2, y2), (60, 200, 60), 2)
    return view


def _Write_Outputs(output_dir: str, scene_bgr: tp.Any, objects: tp.List[Detection_Str],
                   change_mask: tp.Any, regions: tp.List, metadata: tp.Dict) -> None:
    """
    Description:
        Write the annotated result, the change-mask debug view, one crop / mask /
        description per object, and summary.json into the output directory.

    Args:
        (1) output_dir [string]: The directory to write into (created if absent).
        (2) scene_bgr [Matrix<uint8> HxWx3]: The scene (BGR).
        (3) objects [Vector<Detection_Str(object)>]: The located objects, in order.
        (4) change_mask [Matrix<uint8> HxW]: The stage-1 change mask.
        (5) regions [Vector<Tuple<int> 1x4>]: The stage-1 candidate regions.
        (6) metadata [dict]: The run metadata for summary.json.
    """

    os.makedirs(output_dir, exist_ok=True)
    # Clear the per-object files from any previous run, so a run that finds fewer
    # objects never leaves a stale object_NN_* behind to contradict summary.json.
    for name in os.listdir(output_dir):
        if name.startswith('object_'):
            os.remove(os.path.join(output_dir, name))
    cv2.imwrite(os.path.join(output_dir, 'result.png'), _Draw_Result(scene_bgr, objects))
    cv2.imwrite(os.path.join(output_dir, 'change_mask.png'), _Draw_Change_Mask(change_mask, regions))

    summary = dict(metadata)
    summary['object_count'] = len(objects)
    summary['objects'] = []
    for i, det in enumerate(objects):
        x, y, w, h = det.Bbox
        crop = scene_bgr[y:y + h, x:x + w]
        cv2.imwrite(os.path.join(output_dir, 'object_%02d_crop.png' % (i + 1)), crop)
        if det.Mask is not None:
            mask_u8 = (det.Mask[y:y + h, x:x + w].astype(np.uint8)) * 255
            cv2.imwrite(os.path.join(output_dir, 'object_%02d_mask.png' % (i + 1)), mask_u8)
        with open(os.path.join(output_dir, 'object_%02d_description.txt' % (i + 1)), 'w') as handle:
            handle.write(det.Sentence + '\n')
        summary['objects'].append({
            'index': i + 1, 'label': det.Label, 'bbox': [int(v) for v in det.Bbox],
            'change_coverage': round(float(det.Change_Coverage), 4),
            'segmenter_score': None if det.Segmenter_Score is None else round(float(det.Segmenter_Score), 4),
            'sentence': det.Sentence,
        })
    with open(os.path.join(output_dir, 'summary.json'), 'w') as handle:
        json.dump(summary, handle, indent=2)


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


def main() -> int:
    """
    Description:
        Parse the arguments, obtain the (reference, scene) pair from --input-dir (or
        --background), run the four-stage pipeline, write the outputs, and report. The
        exit code is non-zero when the pair is missing/unreadable, the weights are
        missing, or fewer than --expect-objects are found, so the script gates a CI check.

    Returns:
        (1) parameter [int]: The process exit code (0 on success).
    """

    parser = argparse.ArgumentParser(description='Run the AnyScan FastSAM vision pipeline on an image pair.')
    parser.add_argument('--input-dir', default=CONST_INPUT_DIR, help='directory holding the reference and scene images')
    parser.add_argument('--output-dir', default=CONST_OUTPUT_DIR, help='where to write result.png, crops and summary.json')
    parser.add_argument('--background', default=None, help='explicit reference-image path (overrides discovery)')
    parser.add_argument('--weights', default=None, help='FastSAM weights path (overrides the default)')
    parser.add_argument('--device', default=None, help="compute device: 'cpu', 'cuda', 'mps' or 'auto'")
    parser.add_argument('--no-describe', action='store_true', help='use the model-free fallback describer (no VLM)')
    parser.add_argument('--expect-objects', type=int, default=0, help='exit non-zero if fewer than N objects are found')
    parser.add_argument('--verbose', action='store_true', help='print per-object coverage and score')
    args = parser.parse_args()

    _Configure(args)

    # Obtain the (reference, scene) pair from the input directory. A real pair is
    # required; there is no synthetic fallback.
    discovered = _Discover_Images(args.input_dir, args.background)
    if discovered is None:
        _Banner('NO INPUT IMAGE PAIR FOUND',
                ['A real (reference, scene) image pair is required.',
                 'Searched: %s' % os.path.abspath(args.input_dir),
                 'Provide a reference image (name containing one of: %s)'
                 % ', '.join(CONST_REFERENCE_MARKERS),
                 'and a scene image in --input-dir, or pass --background explicitly.'])
        return 1
    reference_path, scene_path = discovered
    print('[INFO] Reference: %s' % reference_path)
    print('[INFO] Scene    : %s' % scene_path)
    reference_bgr = cv2.imread(reference_path)
    scene_bgr = cv2.imread(scene_path)
    if reference_bgr is None or scene_bgr is None:
        _Banner('INPUT IMAGE UNREADABLE',
                ['One of the input images could not be read as an image.',
                 'Reference: %s' % reference_path, 'Scene: %s' % scene_path])
        return 1

    # The pipeline differences the scene against CONST_BACKGROUND_REF, so point it at
    # this run's reference (the same mechanism the app's --background flag uses).
    Vision_Core.CONST_BACKGROUND_REF = os.path.abspath(reference_path)

    # Stage 1 again here, only to draw the background-foreground debug view; Analyze
    # runs its own copy internally. Cheap and deterministic, so the two agree. The
    # mask is 0/1; scale to 0/255 for the grayscale debug image. (The full harness
    # rework — glob discovery and the three §1c artefacts — lands in a later phase.)
    change_mask = Background_Foreground(reference_bgr, scene_bgr, cv2, np) * 255
    regions = []

    scene_rgb = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2RGB)
    print('[INFO] Running the pipeline (describer=%s, segmenter=%s)...'
          % (Vision_Core.CONST_DESCRIBER, Vision_Segmenter.CONST_SEGMENTER_PROMPT_MODE))
    try:
        result = Florence_Vision_Cls().Analyze(scene_rgb)
    except Segmenter_Error_Cls as error:
        _Banner('FASTSAM WEIGHTS NOT VERIFIED - segmentation could not run', [str(error)])
        return 1
    except Vision_Error_Cls as error:
        _Banner('VISION RUNTIME ERROR - the pipeline could not run', [str(error)])
        return 1

    objects = result.Objects
    metadata = {
        'reference': os.path.abspath(reference_path),
        'scene': os.path.abspath(scene_path),
        'device': Vision_Core.CONST_VISION_DEVICE,
        'segmenter_prompt_mode': Vision_Segmenter.CONST_SEGMENTER_PROMPT_MODE,
        'describer': Vision_Core.CONST_DESCRIBER,
        'fastsam_weights': Vision_Segmenter.CONST_SEGMENTER_WEIGHTS,
        'florence_weights': Vision_Core.CONST_MODEL_DIR,
        'verdict': result.Verdict,
        'latency_ms': result.Latency_Ms,
    }
    _Write_Outputs(args.output_dir, scene_bgr, objects, change_mask, regions, metadata)

    print('[INFO] Found %d object(s) in %d candidate region(s); verdict: %s (%d ms).'
          % (len(objects), len(regions), result.Verdict, result.Latency_Ms))
    for i, det in enumerate(objects):
        if args.verbose:
            print('[INFO]   Object %d: coverage=%.3f score=%s bbox=%s'
                  % (i + 1, det.Change_Coverage,
                     'n/a' if det.Segmenter_Score is None else '%.3f' % det.Segmenter_Score, det.Bbox))
        print('[INFO]   Object %d: %s' % (i + 1, det.Sentence))
    print('[INFO] Outputs written to: %s' % os.path.abspath(args.output_dir))

    if args.expect_objects and len(objects) < args.expect_objects:
        _Banner('OBJECT COUNT BELOW EXPECTED',
                ['Expected at least %d object(s); found %d.' % (args.expect_objects, len(objects))])
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
