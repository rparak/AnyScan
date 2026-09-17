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
# File Name: ../Example/UI/screenshot.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
import argparse
import datetime
# Resolve the project folder from this file's own location (Example/UI -> ..), so the
# script runs the same whether launched from Example/UI/ or the repo root.
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
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI and vision
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
#   ../Vision/Utilities/Annotate
from Vision.Utilities.Annotate import Draw_Annotated, Draw_Label_Mask
#   ../Vision/Utilities/Provenance
import Vision.Utilities.Provenance as Provenance
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Analysis_Str

"""
Description:
    Initialization of constants.

    The review-render harness: it produces the Camera-View annotated image, the exported
    label mask and the whole-window grab for a set of NAMED demo scenes, and STAMPS each
    output with the scene name and the run timestamp on a footer band — the same reason
    the validation harness (Example/Vision/analyze.py) stamps its artefacts. A review
    grab is then never ambiguous about which scene produced it: two renders that look
    alike, or two status figures that differ, are told apart by reading the image, not by
    remembering which script made them.

    The scenes are synthetic (no camera, no weights), so the demo is deterministic and
    the stamp identifies the scene by NAME rather than by a frame hash — the analogue of
    the harness's frame fingerprint for a scene that has no source file.
"""
# Where the stamped review renders are written (git-ignored).
#   Unit [string]
CONST_OUTPUT_DIR = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Screenshots')


def _Stamp(image: tp.Any, text: str) -> tp.Any:
    """
    Description:
        Return the image with the scene/run stamp on a slim footer band appended below
        it — never drawn over the content, so it labels the render without occluding it.
        The same footer-band stamp the validation harness uses on its artefacts.

    Args:
        (1) image [Matrix<uint8> HxWx3]: The render (BGR).
        (2) text [string]: The stamp text (scene name and run timestamp).

    Returns:
        (1) parameter [Matrix<uint8> (H+band)xWx3]: The stamped render.
    """

    return Provenance.Stamp_Image(image, text, cv2, np)


def _Grab_Bgr(window: AnyScan_Window_Cls) -> tp.Any:
    """
    Description:
        The window grabbed as a BGR ndarray, so the same cv2 stamp can be appended to it
        as to the annotated image and the mask.

    Args:
        (1) window [AnyScan_Window_Cls(object)]: The window to grab.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The grab (BGR).
    """

    qimage = window.grab().toImage().convertToFormat(QImage.Format_RGB888)
    width, height = qimage.width(), qimage.height()
    pointer = qimage.constBits()
    pointer.setsize(height * qimage.bytesPerLine())
    rgb = np.frombuffer(pointer, np.uint8).reshape(height, qimage.bytesPerLine())
    rgb = rgb[:, :width * 3].reshape(height, width, 3)
    return np.ascontiguousarray(rgb[..., ::-1])   # RGB -> BGR


def _Detection(label: str, box: tp.Tuple[int, int, int, int], verdict: str = 'OK',
               score: tp.Optional[float] = None, sentence: str = '') -> Detection_Str:
    """
    Description:
        A synthetic detection with a filled rectangular mask, a verdict and an optional
        FastSAM score, for the demo scenes.

    Args:
        (1) label [string]: The object label.
        (2) box [Vector<int> 1x4]: The box as (x, y, w, h).
        (3) verdict [string]: 'OK' or 'NOK'.
        (4) score [float]: The FastSAM score, or None for a background-cue object.
        (5) sentence [string]: The composed sentence for the panel.

    Returns:
        (1) parameter [Detection_Str(object)]: The detection.
    """

    x, y, w, h = box
    mask = np.zeros((1200, 1920), dtype=bool)
    mask[y:y + h, x:x + w] = True
    return Detection_Str(Label=label, Bbox=box, Mask=mask, Cue='both', Verdict=verdict,
                         Segmenter_Score=score, Sentence=sentence)


def _Scene_Objects() -> tp.List[Detection_Str]:
    """
    Description:
        The demo scene's objects: a mix of verdicts and of scored / background-only
        objects, so the annotation colours and the confidence coverage are both
        exercised.

    Returns:
        (1) parameter [Vector<Detection_Str(object)>]: The objects.
    """

    return [
        _Detection('ring', (300, 200, 240, 240), 'OK', 0.91, 'A silver ring.'),
        _Detection('block', (780, 300, 300, 360), 'OK', 0.88, 'A pink block.'),
        _Detection('bracket', (360, 760, 760, 150), 'NOK', 0.83, 'A blue lattice bracket.'),
        _Detection('nut', (1250, 240, 150, 150), 'OK', 0.90, 'A hex nut.'),
        _Detection('screw', (560, 560, 120, 120), 'OK', None, 'A small screw.'),
    ]


def _Render(output_dir: str, stamp: str) -> None:
    """
    Description:
        Render and stamp the three review images — the annotated frame, the label mask
        and the whole window — for the demo scene, into the output directory.

    Args:
        (1) output_dir [string]: The directory to write into.
        (2) stamp [string]: The scene/run stamp appended to every image.
    """

    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()

    reference = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Camera', 'Image_Background_001.png')
    window = AnyScan_Window_Cls(camera=File_Camera_Cls(reference))
    window.resize(1500, 950)

    mangle = '_AnyScan_Window_Cls'
    getattr(window, mangle + '__camera').Connect()
    getattr(window, mangle + '__Sync_Controls')()
    getattr(window, mangle + '__On_Scan_Button_Clicked')()
    for _ in range(8):
        app.processEvents()

    frame = getattr(window, mangle + '__frame')
    objects = _Scene_Objects()
    scene_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    result = Analysis_Str(Objects=objects, Latency_Ms=1180, Verdict='5 found',
                          Verdict_Level='ok', Task='caption',
                          Background='A green background that is very bright.')
    getattr(window, mangle + '__On_Analysis_Finished')(result)
    for _ in range(12):
        app.processEvents()

    cv2.imwrite(os.path.join(output_dir, 'demo_annotated.png'),
                _Stamp(Draw_Annotated(scene_bgr, objects, cv2, np), stamp))
    cv2.imwrite(os.path.join(output_dir, 'demo_mask.png'),
                _Stamp(Draw_Label_Mask(objects, scene_bgr.shape, cv2, np), stamp))
    cv2.imwrite(os.path.join(output_dir, 'demo_window.png'), _Stamp(_Grab_Bgr(window), stamp))


def main() -> int:
    """
    Description:
        Render the stamped review images for the demo scene into the output directory.

    Returns:
        (1) parameter [int]: The process exit code (0 on success).
    """

    parser = argparse.ArgumentParser(description='Render the stamped Camera-View / mask / window review images.')
    parser.add_argument('--output-dir', default=CONST_OUTPUT_DIR, help='where to write the stamped renders')
    parser.add_argument('--scene', default='demo', help='the scene name recorded in the stamp')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    run_stamp = datetime.datetime.now().isoformat(timespec='seconds')
    stamp = 'scene %s | %s' % (args.scene, run_stamp)
    _Render(args.output_dir, stamp)
    print('[INFO] Stamped review renders written to: %s' % os.path.abspath(args.output_dir))
    print('[INFO] Stamp: %s' % stamp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
