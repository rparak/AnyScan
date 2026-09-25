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
# File Name: ../Calibration/Core.py
## =========================================================================== ##

# System (Default)
import os
import re
import json
# OpenCV library for computer vision tasks
import cv2
# Numpy (Array computing)
import numpy as np
# Typing (Support for type hints)
import typing as tp
# Custom Lib.:
#   ../Parameters/Camera
from Parameters.Camera import (Camera_Calibration_Parameters_Str, Board_Detection_Str,
                               Calibration_View_Str, Calibration_Report_Str)
#   ../Camera/Core — the application's own undistortion setting (the pixel space of measurement)
from Camera.Core import CONST_BASLER_UNDISTORT_ALPHA

"""
Description:
    Initialization of constants.

    Calibration captures are the camera's frames BEFORE undistortion — the only form a lens model
    can be solved from — and every one taken is kept: a pose that is thrown away can never be
    re-examined. They are numbered in one sequence, their kind in the name: 'flat_NNN.png' is a
    board lying flat on the table (it feeds the lens model AND the mm/px factor), 'view_NNN.png' a
    tilted or raised board (it feeds the lens model only). A 'capture.json' manifest beside them
    states that they are distorted and how they were produced, so no reader mistakes them for the
    application's undistorted '<set>_raw.png'.

    The lens model is solved with cv2.calibrateCamera over ALL detected views together. The mm/px
    factor is derived afterwards from the FLAT views only, from their corners UNDISTORTED into the
    application's own pixel space (getOptimalNewCameraMatrix with CONST_BASLER_UNDISTORT_ALPHA) —
    the space every measurement happens in — never from raw, distorted corners.
"""
# The filename prefixes of the two kinds of calibration capture.
#   Unit [string]
CONST_CALIB_FLAT_PREFIX = 'flat_'
CONST_CALIB_VIEW_PREFIX = 'view_'
# The manifest (sidecar) written beside the captures.
#   Unit [string]
CONST_CALIB_MANIFEST = 'capture.json'
# The smallest inner-corner grid (columns, rows) accepted from a board partly outside the frame:
# enough rows and columns to fix a plane's perspective, small enough that a board overhanging a
# corner by a couple of squares still qualifies.
#   Unit [Vector<int> 1x2]
CONST_CALIB_MIN_GRID = (4, 3)
# The sector-based detector's flags. CALIB_CB_LARGER finds whatever part of the grid is visible
# (the classic findChessboardCorners needs the whole board and fails on an overhanging one), and
# CALIB_CB_ACCURACY is the sub-pixel refinement. Measured on six noisy, perspective-warped
# synthetic boards (mean corner error against the true positions): LARGER | ACCURACY 0.031 px,
# LARGER alone 0.041 px; cornerSubPix run AFTER either makes it worse (0.051 px with an 11 x 11
# window, 0.079 px with 5 x 5), so it is not used; CALIB_CB_NORMALIZE_IMAGE costs 0.22 px, so it
# is not used either.
#   Unit [int]
CONST_CALIB_DETECT_FLAGS = cv2.CALIB_CB_LARGER | cv2.CALIB_CB_ACCURACY
# The image files a calibration directory is read from.
#   Unit [Vector<string>]
CONST_CALIB_IMAGE_EXTENSIONS = ('.png', '.bmp', '.tif', '.tiff', '.jpg', '.jpeg')
# The tilt (degrees between the board's normal and the optical axis) a view needs to count as
# tilted, and how many such views a set needs before its principal point is trusted. From the
# synthetic study Example/Camera/calibration_tilt_study.py (12 views, 0.1 px corner noise;
# principal-point error median / 90th percentile over 40 seeds):
#   k views tilted 10 deg, the rest flat:  k=0 45 / 100 px (focal 18 % off) — at 0.2 px noise
#   94 / 614 px, the failure the single-view calibration showed at ~800 px;  k=1 22 / 49 px;
#   k=2 2.8 / 6.8 px;  k=3 2.3 / 4.4 px (focal 0.14 %);  k=6 1.4 / 2.5 px.
#   tilts uniform up to a maximum:  0 deg 45 px, 2 deg 4.8 px, 3 deg 3.1 px, 5 deg 2.1 px,
#   8 deg 1.5 px, 10 deg 1.5 px (focal 0.15 %), 15-45 deg 1.5-1.6 px — the plateau starts at
#   8-10 deg and recovery degrades sharply below 5 deg.
# Three views of at least 10 deg is the first point on the plateau in both sweeps. Tilt does not
# buy scale uniformity (that is corner noise and view count: 0.085 % at 12 views, 0.057 % at 24).
#   Unit [float] / [int]
CONST_CALIB_MIN_TILT_DEG = 10.0
CONST_CALIB_MIN_TILTED_VIEWS = 3
# A view whose own reprojection RMS exceeds this multiple of the set's median is named as a bad
# capture (blurred, moved, glared or misdetected) to retake or exclude.
#   Unit [float]
CONST_CALIB_OUTLIER_RATIO = 2.0
# The frame regions (columns, rows) the factor is mapped over to show position dependence.
#   Unit [Vector<int> 1x2]
CONST_CALIB_FACTOR_MAP_CELLS = (3, 3)
# The per-axis spread of the factor across the frame (max - min, % of the factor) above which it
# is reported as position-dependent rather than averaged away: one pixel in a thousand — a 100 mm
# part is ~1000 px at ~0.1 mm/px, so a larger variation changes its size at the display
# resolution. (The synthetic study puts pure corner noise, median / 90th percentile, at
# 0.057 / 0.103 % for 24 views and 0.039 / 0.065 % for 40, so a set of 40+ views stays under it
# unless the variation is real; at 24 one set in ten crosses it on noise alone.)
#   Unit [float] (%)
CONST_CALIB_FACTOR_UNIFORM_PCT = 0.1
# The points the distortion's reach is reported at: the frame's corners and edge midpoints, as
# fractions of (width - 1, height - 1).
#   Unit [Dict]
CONST_CALIB_EDGE_POINTS = {'top-left': (0.0, 0.0), 'top': (0.5, 0.0), 'top-right': (1.0, 0.0),
                           'right': (1.0, 0.5), 'bottom-right': (1.0, 1.0), 'bottom': (0.5, 1.0),
                           'bottom-left': (0.0, 1.0), 'left': (0.0, 0.5)}
# A printed board's warning, stated with every result: the square size scales every measurement.
#   Unit [string]
CONST_CALIB_SQUARE_WARNING = ('The square size scales every measurement. Caliper a printed board '
                              'across several squares: printer scaling of 0.5-1 % is the same '
                              'order as the errors this calibration is meant to remove.')


class Calibration_Error_Cls(RuntimeError):
    """
    Description:
        Raised when a calibration cannot produce a trustworthy result at all — no images, no
        detected board, no flat view for the factor, mixed image sizes. Its message is a full
        sentence saying what to capture.
    """


def Detect_Board(image: np.ndarray) -> Board_Detection_Str:
    """
    Description:
        Find the chessboard's visible inner-corner grid in one image with
        findChessboardCornersSBWithMeta and CALIB_CB_LARGER, so a board that overhangs the frame
        still yields its visible part. The corners come back row-major over the detected grid.

    Args:
        (1) image [Matrix<uint8> HxW or HxWx3]: The image (BGR or grey).

    Returns:
        (1) parameter [Board_Detection_Str(object)]: The detection, or Found False with a reason.
    """

    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    found, corners, meta = cv2.findChessboardCornersSBWithMeta(grey, CONST_CALIB_MIN_GRID,
                                                               CONST_CALIB_DETECT_FLAGS)
    if not found or corners is None or meta is None:
        return Board_Detection_Str(Reason='no chessboard of at least %d x %d inner corners was '
                                          'found (blurred, glared, or too little of the board '
                                          'in view)' % CONST_CALIB_MIN_GRID)
    rows, columns = meta.shape[:2]
    points = corners.reshape(-1, 2).astype(np.float64)
    if points.shape[0] != rows * columns:
        return Board_Detection_Str(Reason='the detector returned %d corners for a %d x %d grid'
                                          % (points.shape[0], columns, rows))
    return Board_Detection_Str(Found=True, Grid=(int(columns), int(rows)), Corners=points)


def Next_Capture_Name(directory: str, flat: bool) -> str:
    """
    Description:
        The filename for the next calibration capture in a directory: one running number across
        both kinds (so the capture order survives), never reusing a number already on disk — an
        existing frame is never overwritten.

    Args:
        (1) directory [string]: The capture directory.
        (2) flat [bool]: True for a board lying flat on the table, False for a tilted view.

    Returns:
        (1) parameter [string]: 'flat_NNN.png' or 'view_NNN.png'.
    """

    pattern = re.compile(r'^(?:%s|%s)(\d+)\.png$' % (CONST_CALIB_FLAT_PREFIX, CONST_CALIB_VIEW_PREFIX))
    taken = [int(m.group(1)) for m in map(pattern.match, os.listdir(directory)) if m]
    prefix = CONST_CALIB_FLAT_PREFIX if flat else CONST_CALIB_VIEW_PREFIX
    return '%s%03d.png' % (prefix, max(taken, default=0) + 1)


def Record_Capture(directory: str, header: tp.Dict[str, tp.Any],
                   entry: tp.Dict[str, tp.Any]) -> str:
    """
    Description:
        Add one capture to the directory's manifest, creating it from the header the first time.
        The manifest is rewritten whole through a temporary file and an atomic replace, so an
        interrupted session leaves the previous, consistent manifest rather than a torn one.

    Args:
        (1) directory [string]: The capture directory.
        (2) header [Dict]: The manifest's fixed part (used only when the manifest is new).
        (3) entry [Dict]: The capture's record (file, kind, time, detection).

    Returns:
        (1) parameter [string]: The manifest path.
    """

    path = os.path.join(directory, CONST_CALIB_MANIFEST)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as handle:
            manifest = json.load(handle)
    else:
        manifest = dict(header, frames=[])
    manifest['frames'].append(entry)
    temporary = path + '.writing'
    with open(temporary, 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
    os.replace(temporary, path)
    return path

def Captured_Window(directory: str) -> tp.Optional[tp.Dict[str, tp.List[int]]]:
    """
    Description:
        The sensor window a calibration set was captured at, from its manifest — read here, beside
        Record_Capture that writes it, so the manifest has one reader.

    Args:
        (1) directory [string]: The capture directory.

    Returns:
        (1) parameter [Dict or None]: {'resolution': [w, h], 'offset': [x, y]}, or None when the
                                      directory has no manifest or the manifest does not record it
                                      (sets captured before the window was recorded).
    """

    path = os.path.join(directory, CONST_CALIB_MANIFEST)
    if not os.path.isfile(path):
        return None
    with open(path, 'r', encoding='utf-8') as handle:
        window = json.load(handle).get('window')
    return window if isinstance(window, dict) else None


def Natural_Key(name: str) -> tp.List[tp.Any]:
    """
    Description:
        A natural sort key: digit runs compare as numbers, so 'view_10' follows 'view_9'.

    Args:
        (1) name [string]: The filename.

    Returns:
        (1) parameter [Vector]: The key.
    """

    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', name)]


def Load_Views(directory: str) -> tp.List[tp.Tuple[str, np.ndarray]]:
    """
    Description:
        Every image in a calibration directory, in natural filename order. An image that cannot
        be read is still returned (as None) so the solve reports it by name instead of it
        silently vanishing.

    Args:
        (1) directory [string]: The capture directory.

    Returns:
        (1) parameter [Vector<Tuple<string, Matrix or None>>]: (filename, image) pairs.
    """

    if not os.path.isdir(directory):
        raise Calibration_Error_Cls('There is no calibration directory at "%s".' % directory)
    names = sorted((name for name in os.listdir(directory)
                    if name.lower().endswith(CONST_CALIB_IMAGE_EXTENSIONS)), key=Natural_Key)
    return [(name, cv2.imread(os.path.join(directory, name))) for name in names]


def __Grid_Object_Points(detection: Board_Detection_Str, square_mm: float) -> np.ndarray:
    """
    Description:
        The board-plane coordinates (mm, z = 0) of a detection's corners, row-major over its grid.
        A partial grid is labelled from its own first corner: each view has its own pose, so only
        the relative geometry has to be right.

    Args:
        (1) detection [Board_Detection_Str(object)]: The detection.
        (2) square_mm [float]: The square size in mm.

    Returns:
        (1) parameter [Matrix<float32> Nx3]: The object points.
    """

    columns, rows = detection.Grid
    ys, xs = np.mgrid[0:rows, 0:columns]
    return np.stack([xs.ravel() * square_mm, ys.ravel() * square_mm,
                     np.zeros(rows * columns)], axis=1).astype(np.float32)


def __Solve_Scale(pairs_px: np.ndarray, square_mm: float) -> tp.Optional[tp.Tuple[float, float]]:
    """
    Description:
        The per-axis mm/px (sx, sy) that best explains a set of adjacent-corner pairs, each one
        square apart: square_mm^2 = (dx sx)^2 + (dy sy)^2 is linear in (sx^2, sy^2), so a board
        at any rotation on the table contributes to both axes. None when the pairs cannot fix
        both axes (e.g. every pair points the same way).

    Args:
        (1) pairs_px [Matrix<float> Nx2]: The (dx, dy) of each pair, in undistorted pixels.
        (2) square_mm [float]: The square size in mm.

    Returns:
        (1) parameter [Vector<float> 1x2 or None]: (mm/px x, mm/px y), or None.
    """

    if pairs_px.shape[0] < 2:
        return None
    design = pairs_px ** 2
    if np.linalg.matrix_rank(design, tol=1e-6 * float(design.max())) < 2:
        return None
    solution, *_ = np.linalg.lstsq(design, np.full(pairs_px.shape[0], square_mm ** 2), rcond=None)
    if (solution <= 0.0).any():
        return None
    return (float(np.sqrt(solution[0])), float(np.sqrt(solution[1])))


def __Undistorted_Pairs(detection: Board_Detection_Str, K: np.ndarray, coeffs: np.ndarray,
                        new_K: np.ndarray) -> tp.Tuple[np.ndarray, np.ndarray]:
    """
    Description:
        A flat view's adjacent-corner pairs (along both grid directions) after undistorting its
        corners into the application's pixel space, with each pair's midpoint.

    Args:
        (1) detection [Board_Detection_Str(object)]: The flat view's detection.
        (2) K [Matrix<float> 3x3]: The solved camera matrix.
        (3) coeffs [Vector<float>]: The solved distortion coefficients.
        (4) new_K [Matrix<float> 3x3]: The application's undistortion camera matrix.

    Returns:
        (1) parameter [Tuple<Matrix Nx2, Matrix Nx2>]: (pair vectors, pair midpoints) in px.
    """

    columns, rows = detection.Grid
    undistorted = cv2.undistortPoints(detection.Corners.reshape(-1, 1, 2), K, coeffs,
                                      P=new_K).reshape(rows, columns, 2)
    vectors, midpoints = [], []
    for axis in (0, 1):
        a = undistorted[:-1, :] if axis == 0 else undistorted[:, :-1]
        b = undistorted[1:, :] if axis == 0 else undistorted[:, 1:]
        vectors.append((b - a).reshape(-1, 2))
        midpoints.append(((a + b) / 2.0).reshape(-1, 2))
    return np.concatenate(vectors), np.concatenate(midpoints)


def __Spread_Pct(values: tp.List[tp.Tuple[float, float]]) -> tp.Tuple[float, float]:
    """
    Description:
        The per-axis spread (max - min) of a set of (x, y) factors, as % of their mean.

    Args:
        (1) values [Vector<Tuple<float>>]: The factors.

    Returns:
        (1) parameter [Vector<float> 1x2]: (x %, y %), 0 for fewer than two values.
    """

    if len(values) < 2:
        return (0.0, 0.0)
    array = np.array(values)
    return tuple(float(100.0 * (array[:, k].max() - array[:, k].min()) / array[:, k].mean())
                 for k in (0, 1))


def Calibrate(views: tp.List[tp.Tuple[str, tp.Optional[np.ndarray]]], square_mm: float,
              board_height_mm: float, board_squares: tp.Tuple[int, int]) -> Calibration_Report_Str:
    """
    Description:
        Solve the camera over a set of chessboard images and report everything needed to judge
        the result. Each image is detected on its own; one that fails (unreadable, blurred,
        glared, no board, a grid larger than the board) is named with the reason and skipped,
        never fatal. cv2.calibrateCamera then runs over all detected views together. The mm/px
        factor comes from the FLAT views only ('flat_' prefix), from their corners undistorted
        into the application's pixel space; with no flat view detected this raises rather than
        derive a factor from tilted boards.

    Args:
        (1) views [Vector<Tuple<string, Matrix or None>>]: (filename, image) pairs, e.g. from
                                                           Load_Views.
        (2) square_mm [float]: The board's square size in mm (as calipered).
        (3) board_height_mm [float]: The flat boards' surface height above the table (mm) — the
                                     reference plane the factor belongs to; recorded, not applied.
        (4) board_squares [Vector<int> 1x2]: The board's squares (columns, rows), e.g. (11, 8);
                                             its inner-corner grid is one fewer each way.

    Returns:
        (1) parameter [Calibration_Report_Str(object)]: The solved calibration and its diagnostics.
    """

    if not views:
        raise Calibration_Error_Cls('The calibration directory holds no images.')
    report = Calibration_Report_Str(Square_Mm=float(square_mm), Board_Height_Mm=float(board_height_mm))

    # 1\ Detect each view on its own; a failure is recorded with its reason and skipped.
    size = __Detect_Views(views, board_squares, report)
    detected = [view for view in report.Views if view.Detection.Found]
    if not detected:
        raise Calibration_Error_Cls('No chessboard was found in any image; nothing can be solved.')
    flats = [view for view in detected if view.Flat]
    if not flats:
        raise Calibration_Error_Cls('No flat view (a "%s*" image with the board found) is present: '
                                    'the mm/px factor comes only from boards lying flat on the table, '
                                    'and is never derived from tilted ones. Capture the board flat '
                                    'at the centre and in the corners.' % CONST_CALIB_FLAT_PREFIX)
    report.Image_Size = size

    # 2\ One calibration over every detected view.
    object_points = [__Grid_Object_Points(view.Detection, square_mm) for view in detected]
    image_points = [view.Detection.Corners.reshape(-1, 1, 2).astype(np.float32) for view in detected]
    rms, K, coeffs, rvecs, tvecs = cv2.calibrateCamera(object_points, image_points, size, None, None)
    coeffs = coeffs.ravel()[:5]
    report.K, report.Rms_Px = K, float(rms)
    report.Coefficients = dict(zip(('k1', 'k2', 'p1', 'p2', 'k3'), (float(c) for c in coeffs)))

    # 3\ Per view: reprojection error and the board's tilt from facing the camera.
    __View_Diagnostics(report, detected, object_points, image_points, rvecs, tvecs, K, coeffs)

    # 4\ The principal point against the image centre, and the distortion at the frame edge.
    __Lens_Diagnostics(report, K, coeffs, size)

    # 5\ The factor from the flat views' undistorted corners, in the application's pixel space.
    __Solve_Factor(report, flats, K, coeffs, size, square_mm)
    return report


def __Detect_Views(views: tp.List[tp.Tuple[str, tp.Optional[np.ndarray]]], board_squares: tp.Tuple[int, int],
                   report: Calibration_Report_Str) -> tp.Optional[tp.Tuple[int, int]]:
    """
    Description:
        Detect the board in each view on its own, recording every view in the report. A view that
        cannot be read, shows no board or shows a grid larger than the board's is recorded with the
        reason and skipped; images of more than one size stop the calibration.

    Args:
        (1) views [Vector<Tuple<string, Matrix or None>>]: (filename, image) pairs.
        (2) board_squares [Vector<int> 1x2]: The board's squares (columns, rows).
        (3) report [Calibration_Report_Str(object)]: The report its views are appended to.

    Returns:
        (1) parameter [Vector<int> 1x2 or None]: The image size (width, height), or None when no
                                                 view could be read.
    """

    inner = sorted((board_squares[0] - 1, board_squares[1] - 1))
    size = None
    for name, image in views:
        view = Calibration_View_Str(Name=name, Flat=name.startswith(CONST_CALIB_FLAT_PREFIX))
        report.Views.append(view)
        if image is None:
            view.Detection = Board_Detection_Str(Reason='the file could not be read as an image')
            continue
        image_size = (int(image.shape[1]), int(image.shape[0]))
        if size is None:
            size = image_size
        elif image_size != size:
            raise Calibration_Error_Cls('"%s" is %d x %d but the first image is %d x %d; a '
                                        'calibration needs one image size.' % (name, *image_size, *size))
        view.Detection = Detect_Board(image)
        grid = sorted(view.Detection.Grid)
        if view.Detection.Found and (grid[0] > inner[0] or grid[1] > inner[1]):
            view.Detection = Board_Detection_Str(Reason='a %d x %d grid was found, larger than the '
                                                        'board\'s %d x %d inner corners'
                                                        % (*view.Detection.Grid, *inner))
    return size


def __View_Diagnostics(report: Calibration_Report_Str, detected: tp.List[Calibration_View_Str],
                       object_points: tp.List[np.ndarray], image_points: tp.List[np.ndarray],
                       rvecs: tp.Sequence[np.ndarray], tvecs: tp.Sequence[np.ndarray], K: np.ndarray,
                       coeffs: np.ndarray) -> None:
    """
    Description:
        Per view: its reprojection error, whether it is an outlier against the median, and the
        board's tilt from facing the camera; then the tilt range and a warning when too few views
        are tilted to separate the principal point from the board's position.

    Args:
        (1) report [Calibration_Report_Str(object)]: The report being filled.
        (2) detected [Vector<Calibration_View_Str(object)>]: The views the board was found in.
        (3 - 4) object_points, image_points [Vector<Matrix>]: Their board and image points.
        (5 - 6) rvecs, tvecs [Vector<Matrix>]: Their solved poses.
        (7) K [Matrix<float> 3x3]: The solved camera matrix.
        (8) coeffs [Vector<float>]: The solved distortion coefficients.
    """

    for view, obj, img, rvec, tvec in zip(detected, object_points, image_points, rvecs, tvecs):
        projected, _ = cv2.projectPoints(obj, rvec, tvec, K, coeffs)
        view.Rms_Px = float(np.sqrt(np.mean(np.sum((projected - img) ** 2, axis=2))))
        normal = cv2.Rodrigues(rvec)[0][:, 2]
        view.Tilt_Deg = float(np.degrees(np.arccos(min(1.0, abs(float(normal[2]))))))
    median_rms = float(np.median([view.Rms_Px for view in detected]))
    for view in detected:
        view.Outlier = view.Rms_Px > CONST_CALIB_OUTLIER_RATIO * median_rms
    tilts = [view.Tilt_Deg for view in detected]
    report.Tilt_Range_Deg = (min(tilts), max(tilts))
    report.Tilted_Views = sum(tilt >= CONST_CALIB_MIN_TILT_DEG for tilt in tilts)
    if report.Tilted_Views < CONST_CALIB_MIN_TILTED_VIEWS:
        report.Tilt_Warning = ('Only %d view(s) are tilted by %.0f deg or more (%d needed): '
                               'near-frontal views cannot separate the principal point from the '
                               'board\'s position, so this result may be as unreliable as the '
                               'single-view calibration it replaces. Add views tilted %.0f-30 deg '
                               'in several directions.' % (report.Tilted_Views, CONST_CALIB_MIN_TILT_DEG,
                                                           CONST_CALIB_MIN_TILTED_VIEWS,
                                                           CONST_CALIB_MIN_TILT_DEG))


def __Lens_Diagnostics(report: Calibration_Report_Str, K: np.ndarray, coeffs: np.ndarray,
                       size: tp.Tuple[int, int]) -> None:
    """
    Description:
        The principal point against the image centre (in pixels, as a distance and as a fraction of
        the frame), and how far the lens model moves a point at each CONST_CALIB_EDGE_POINTS position.

    Args:
        (1) report [Calibration_Report_Str(object)]: The report being filled.
        (2) K [Matrix<float> 3x3]: The solved camera matrix.
        (3) coeffs [Vector<float>]: The solved distortion coefficients.
        (4) size [Vector<int> 1x2]: The image size (width, height).
    """

    width, height = size
    centre = ((width - 1) / 2.0, (height - 1) / 2.0)
    dx, dy = float(K[0, 2] - centre[0]), float(K[1, 2] - centre[1])
    report.Principal_Offset_Px = (dx, dy)
    report.Principal_Distance_Px = float(np.hypot(dx, dy))
    report.Principal_Offset_Fraction = (dx / width, dy / height)
    edge = np.array([[fx * (width - 1), fy * (height - 1)]
                     for fx, fy in CONST_CALIB_EDGE_POINTS.values()]).reshape(-1, 1, 2)
    moved = cv2.undistortPoints(edge, K, coeffs, P=K).reshape(-1, 2) - edge.reshape(-1, 2)
    report.Edge_Distortion_Px = {key: float(np.hypot(*d)) for key, d in
                                 zip(CONST_CALIB_EDGE_POINTS, moved)}


def __Solve_Factor(report: Calibration_Report_Str, flats: tp.List[Calibration_View_Str], K: np.ndarray,
                   coeffs: np.ndarray, size: tp.Tuple[int, int], square_mm: float) -> None:
    """
    Description:
        The mm/px factor from the FLAT views' corners, undistorted into the application's pixel
        space (the camera matrix getOptimalNewCameraMatrix gives at CONST_BASLER_UNDISTORT_ALPHA):
        per view, overall, the spread between views, and a map across the frame with its spread —
        warning when the factor varies across the frame by more than CONST_CALIB_FACTOR_UNIFORM_PCT.

    Args:
        (1) report [Calibration_Report_Str(object)]: The report being filled.
        (2) flats [Vector<Calibration_View_Str(object)>]: The flat views the board was found in.
        (3) K [Matrix<float> 3x3]: The solved camera matrix.
        (4) coeffs [Vector<float>]: The solved distortion coefficients.
        (5) size [Vector<int> 1x2]: The image size (width, height).
        (6) square_mm [float]: The board's square size in mm.
    """

    width, height = size
    new_K, _ = cv2.getOptimalNewCameraMatrix(K, coeffs, size, CONST_BASLER_UNDISTORT_ALPHA, size)
    report.Undistortion_Rescale = (float(new_K[0, 0] / K[0, 0]), float(new_K[1, 1] / K[1, 1]))
    all_vectors, all_midpoints = [], []
    for view in flats:
        vectors, midpoints = __Undistorted_Pairs(view.Detection, K, coeffs, new_K)
        view.Factor = __Solve_Scale(vectors, square_mm)
        all_vectors.append(vectors)
        all_midpoints.append(midpoints)
    vectors, midpoints = np.concatenate(all_vectors), np.concatenate(all_midpoints)
    factor = __Solve_Scale(vectors, square_mm)
    if factor is None:
        raise Calibration_Error_Cls('The flat views do not determine the factor on both axes.')
    report.Factor = factor
    report.Factor_View_Spread_Pct = __Spread_Pct([view.Factor for view in flats
                                                 if view.Factor is not None])
    cells_x, cells_y = CONST_CALIB_FACTOR_MAP_CELLS
    column = np.clip((midpoints[:, 0] / width * cells_x).astype(int), 0, cells_x - 1)
    row = np.clip((midpoints[:, 1] / height * cells_y).astype(int), 0, cells_y - 1)
    report.Factor_Map = [[__Solve_Scale(vectors[(row == r) & (column == c)], square_mm)
                          for c in range(cells_x)] for r in range(cells_y)]
    report.Factor_Frame_Spread_Pct = __Spread_Pct([cell for cells in report.Factor_Map
                                                  for cell in cells if cell is not None])
    if max(report.Factor_Frame_Spread_Pct) > CONST_CALIB_FACTOR_UNIFORM_PCT:
        report.Factor_Warning = ('The factor varies across the frame by %.3f %% (x) / %.3f %% (y), '
                                 'more than %.1f %%: sizes depend on where a part lies. See the '
                                 'map; a gradient across it suggests the table is not parallel to '
                                 'the sensor.' % (*report.Factor_Frame_Spread_Pct,
                                                  CONST_CALIB_FACTOR_UNIFORM_PCT))


def Report_Lines(report: Calibration_Report_Str) -> tp.List[str]:
    """
    Description:
        The calibration report as printable lines — per image (kind, detection, corners,
        reprojection, tilt), then the principal point (prominently: its misplacement is what
        exposed the single-view calibration), the tilt spread, the distortion at the frame edge,
        and the factor with its spread across images and across the frame. Warnings are lines
        starting '[WARNING]'.

    Args:
        (1) report [Calibration_Report_Str(object)]: The report.

    Returns:
        (1) parameter [Vector<string>]: The lines.
    """

    lines = []
    flats = [v for v in report.Views if v.Flat and v.Detection.Found]
    tilted = [v for v in report.Views if not v.Flat and v.Detection.Found]
    failed = [v for v in report.Views if not v.Detection.Found]
    lines.append('[INFO] Images: %d  |  used: %d flat (lens model + factor), %d tilted (lens model '
                 'only)  |  skipped: %d' % (len(report.Views), len(flats), len(tilted), len(failed)))
    for view in report.Views:
        kind = 'flat' if view.Flat else 'view'
        if not view.Detection.Found:
            lines.append('[WARNING]   %-22s %s  SKIPPED: %s' % (view.Name, kind, view.Detection.Reason))
            continue
        lines.append('[INFO]      %-22s %s  %2d x %-2d = %3d corners  reprojection %.3f px  tilt %5.1f deg%s'
                     % (view.Name, kind, *view.Detection.Grid, view.Detection.Corners.shape[0],
                        view.Rms_Px, view.Tilt_Deg,
                        ('  factor %.6f x %.6f mm/px' % view.Factor) if view.Factor else ''))
    for view in report.Views:
        if view.Outlier:
            lines.append('[WARNING] %s reprojects at %.3f px, over %.0fx the set\'s median: a bad '
                         'capture (blur, movement, glare) - retake or exclude it.'
                         % (view.Name, view.Rms_Px, CONST_CALIB_OUTLIER_RATIO))
    lines.append('[INFO] Overall reprojection RMS: %.3f px' % report.Rms_Px)
    width, height = report.Image_Size
    lines.append('[INFO] PRINCIPAL POINT: (%.1f, %.1f) px  -  %.1f px from the image centre '
                 '(dx %+.1f, dy %+.1f; %+.1f %% of the width, %+.1f %% of the height)'
                 % (report.K[0, 2], report.K[1, 2], report.Principal_Distance_Px,
                    *report.Principal_Offset_Px, 100.0 * report.Principal_Offset_Fraction[0],
                    100.0 * report.Principal_Offset_Fraction[1]))
    lines.append('[INFO] Focal length: %.1f x %.1f px' % (report.K[0, 0], report.K[1, 1]))
    lines.append('[INFO] Board tilt across the set: %.1f - %.1f deg; %d view(s) tilted %.0f deg or more'
                 % (*report.Tilt_Range_Deg, report.Tilted_Views, CONST_CALIB_MIN_TILT_DEG))
    if report.Tilt_Warning:
        lines.append('[WARNING] ' + report.Tilt_Warning)
    lines.append('[INFO] Distortion (k1, k2, p1, p2, k3): ' + ', '.join(
        '%s %.5f' % item for item in report.Coefficients.items()))
    lines.append('[INFO] Distortion moves the frame edge by: ' + ', '.join(
        '%s %.1f px' % item for item in report.Edge_Distortion_Px.items()))
    lines.append('[INFO] Undistortion (alpha %d) rescales the focal length to %.4f (x) / %.4f (y) of K'
                 % (CONST_BASLER_UNDISTORT_ALPHA, *report.Undistortion_Rescale))
    lines.append('[INFO] FACTOR (flat views, undistorted corners, application pixel space): '
                 '%.6f x %.6f mm/px' % report.Factor)
    lines.append('[INFO] Factor spread across the %d flat view(s): %.3f %% (x) / %.3f %% (y)'
                 % (len(flats), *report.Factor_View_Spread_Pct))
    lines.append('[INFO] Factor across the frame (%d x %d regions, mm/px x / y), spread %.3f %% (x) '
                 '/ %.3f %% (y):' % (*CONST_CALIB_FACTOR_MAP_CELLS, *report.Factor_Frame_Spread_Pct))
    for cells in report.Factor_Map:
        lines.append('[INFO]     ' + '   '.join('%.6f / %.6f' % cell if cell else '      (no data)      '
                                                for cell in cells))
    if report.Factor_Warning:
        lines.append('[WARNING] ' + report.Factor_Warning)
    lines.append('[INFO] Square size %.3f mm; reference plane (flat boards\' surface) %.1f mm above '
                 'the table.' % (report.Square_Mm, report.Board_Height_Mm))
    lines.append('[WARNING] ' + CONST_CALIB_SQUARE_WARNING)
    return lines


def Calibration_Parameters(report: Calibration_Report_Str, offset: tp.Tuple[int, int]) -> Camera_Calibration_Parameters_Str:
    """
    Description:
        The report's result as the configuration's calibration structure (K, coefficients, the
        mm/px factor and the sensor window it was solved at), for writing. The window's size is the
        images' own; its offset on the sensor is not in the images and comes from the capture.

    Args:
        (1) report [Calibration_Report_Str(object)]: The report.
        (2) offset [Vector<int> 1x2]: The sensor window's offset (x, y) the images were captured at.

    Returns:
        (1) parameter [Camera_Calibration_Parameters_Str(object)]: The calibration parameters.
    """

    return Camera_Calibration_Parameters_Str(K=report.K, Coefficients=dict(report.Coefficients),
                                             Conversion_Factor={'x': report.Factor[0],
                                                                'y': report.Factor[1]},
                                             Resolution=(int(report.Image_Size[0]), int(report.Image_Size[1])),
                                             Offset=(int(offset[0]), int(offset[1])))
