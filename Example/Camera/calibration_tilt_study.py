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
# File Name: ../Example/Camera/calibration_tilt_study.py
## =========================================================================== ##

# System (Default)
import sys
import math
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Initialization of constants.

    The synthetic study behind Calibration.Core.CONST_CALIB_MIN_TILT_DEG and
    CONST_CALIB_MIN_TILTED_VIEWS: how well a multi-view calibration recovers the principal point
    as the board tilts narrow, and how many tilted views a set needs. A camera close to the real
    one (1920 x 1200, f = 3500 px — a 12 mm lens on 3.45 um pixels — the principal point a little
    off the centre, barrel distortion) views an 11 x 8, 12 mm board ~360 mm away; corners are
    projected exactly, Gaussian noise is added (0.03 px is the detector's measured error on clean
    synthetic boards, 0.1-0.2 px a realistic range for real ones), corners outside the frame are
    dropped (partial boards), and cv2.calibrateCamera solves each set. Reported: the principal
    point's error (median and 90th percentile over seeds), the focal length's error, and the
    per-axis spread of the undistorted table-plane scale across the frame — the quantity
    measurement depends on.

    The board is the printed one (Data/Calibration/Checkerboard_11x8_12mm_A4.pdf, from generate_checkerboard.py),
    and the study assumes every visible corner is detected. For this board that is nearly true:
    Calibration.Core.Detect_Board reads it whole in most views (test/Camera/test_generate_checkerboard.py)
    and a partial grid only means fewer corners. It is NOT true for a board larger than the field,
    which the detector reads as fragments, so this study cannot be used to size a larger board
    (docs/design-decisions.md, the ChArUco entry). Swapping in a 20 x 13 board here lowers every
    error and keeps the curve's shape (collapse at one tilted view, plateau from 8-10 deg), so the
    thresholds do not depend on the board.
"""
CONST_SIZE = (1920, 1200)
CONST_K = np.array([[3500.0, 0.0, 975.0], [0.0, 3500.0, 590.0], [0.0, 0.0, 1.0]])
CONST_D = np.array([-0.15, 0.10, 0.0, 0.0, 0.0])
CONST_Z, CONST_SQUARE = 360.0, 12.0
CONST_SEEDS = 40
# The board's inner corners, centred on its middle.
CONST_OBJECT = np.array([[c * CONST_SQUARE, r * CONST_SQUARE, 0.0] for r in range(7)
                         for c in range(10)]) - np.array([4.5 * CONST_SQUARE, 3.0 * CONST_SQUARE, 0.0])
# A fronto-parallel table plane sampled every 10 mm, for the scale-uniformity metric.
CONST_PLANE = np.stack([g.ravel() for g in np.meshgrid(np.linspace(-90, 90, 19),
                                                       np.linspace(-55, 55, 12))] + [np.zeros(228)], 1)


def Solve(tilts: tp.List[float], seed: int, noise: float) -> tp.Tuple[float, float, float]:
    """
    Description:
        Solve one synthetic set: one view per entry of 'tilts' (degrees), each in a random
        direction and at a random place in the field.

    Args:
        (1) tilts [Vector<float>]: The views' tilts.
        (2) seed [int]: The random seed.
        (3) noise [float]: The corner noise (px, standard deviation).

    Returns:
        (1) parameter [Tuple<float>]: (principal-point error px, focal error %, scale spread %).
    """

    rng = np.random.default_rng(seed)
    objects, images = [], []
    for tilt in tilts:
        azimuth = rng.uniform(0.0, 2.0 * math.pi)
        rvec = np.array([math.cos(azimuth), math.sin(azimuth), 0.0]) * math.radians(tilt)
        tvec = np.array([rng.uniform(-40, 40), rng.uniform(-25, 25), CONST_Z])
        points = cv2.projectPoints(CONST_OBJECT, rvec, tvec, CONST_K, CONST_D)[0].reshape(-1, 2)
        points += rng.normal(0.0, noise, points.shape)
        inside = ((points[:, 0] > 0) & (points[:, 0] < CONST_SIZE[0]) & (points[:, 1] > 0)
                  & (points[:, 1] < CONST_SIZE[1]))
        objects.append(CONST_OBJECT[inside].astype(np.float32))
        images.append(points[inside].astype(np.float32))
    _, K, D, _, _ = cv2.calibrateCamera(objects, images, CONST_SIZE, None, None)
    new_K, _ = cv2.getOptimalNewCameraMatrix(K, D, CONST_SIZE, 1, CONST_SIZE)
    truth = cv2.projectPoints(CONST_PLANE, np.zeros(3), np.array([0.0, 0.0, CONST_Z]), CONST_K, CONST_D)[0]
    grid = cv2.undistortPoints(truth, K, D, P=new_K).reshape(12, 19, 2)
    spread = max(float(np.ptp(s) / s.mean()) for s in
                 (10.0 / np.linalg.norm(np.diff(grid, axis=a), axis=2) for a in (0, 1)))
    return (math.hypot(K[0, 2] - CONST_K[0, 2], K[1, 2] - CONST_K[1, 2]),
            100.0 * abs(K[0, 0] / CONST_K[0, 0] - 1.0), 100.0 * spread)


def main():
    """
    Description:
        Print the three sweeps: the tilt spread (12 views, tilts uniform up to a maximum), the
        number of tilted views (12 views, k of them tilted, the rest flat), and the view count.
    """

    for noise in (0.03, 0.1, 0.2):
        print('[INFO] 12 views, tilts uniform in [0, max], corner noise %.2f px' % noise)
        print('[INFO]   max tilt | principal point err median / 90th px | focal err median % '
              '| scale spread median / 90th %')
        for maximum in (0, 2, 3, 5, 8, 10, 15, 20, 30, 45):
            results = np.array([Solve(list(np.random.default_rng(1000 + s).uniform(0, maximum, 12)),
                                      s, noise) for s in range(CONST_SEEDS)])
            print('[INFO]   %8d | %8.1f %8.1f | %8.2f | %6.3f %6.3f'
                  % (maximum, np.median(results[:, 0]), np.percentile(results[:, 0], 90),
                     np.median(results[:, 1]), np.median(results[:, 2]), np.percentile(results[:, 2], 90)))
    print('[INFO] 12 views, k tilted by T, the rest flat, corner noise 0.10 px')
    for tilt in (10, 20):
        for k in (0, 1, 2, 3, 4, 6, 12):
            results = np.array([Solve([tilt] * k + [0.0] * (12 - k), s, 0.1) for s in range(CONST_SEEDS)])
            print('[INFO]   T %2d k %2d | principal point %6.1f / %6.1f px | focal %6.2f %%'
                  % (tilt, k, np.median(results[:, 0]), np.percentile(results[:, 0], 90),
                     np.median(results[:, 1])))
    print('[INFO] n views, tilts uniform in [0, 30], corner noise 0.10 px')
    for n in (6, 12, 24, 40):
        results = np.array([Solve(list(np.random.default_rng(2000 + s).uniform(0, 30, n)), s, 0.1)
                            for s in range(CONST_SEEDS)])
        print('[INFO]   n %2d | principal point %4.1f px | scale spread median %.3f %% / 90th %.3f %%'
              % (n, np.median(results[:, 0]), np.median(results[:, 2]), np.percentile(results[:, 2], 90)))

if __name__ == '__main__':
    sys.exit(main())
