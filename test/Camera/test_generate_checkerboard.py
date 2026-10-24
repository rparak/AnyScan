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
# File Name: ../test/Camera/test_generate_checkerboard.py
## =========================================================================== ##

# System (Default)
import os
import re
import sys
import subprocess
import importlib.util
# Typing (Support for type hints)
import typing as tp
# OpenCV (Computer Vision) [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Custom Lib.: AnyScan
#   ../Calibration/Core — the detector the printed board is read with
from Calibration.Core import Detect_Board

"""
Description:
    Tests for Example/Camera/generate_checkerboard.py, on the PDF it writes.

    The generator runs in a fresh interpreter from an unrelated directory, as a person runs it. Its
    page 1 is rendered from the PDF's own content stream (filled rectangles, stroked lines, and each
    line of text as a solid box, so text too close to the board counts against it) at the camera's
    scale, and read with the calibration's real detector, Calibration.Core.Detect_Board. That check
    found that a 20 x 13 board is read as fragments (the detector's CALIB_CB_LARGER growth stops at
    ~15 columns and at the frame's edge), which a synthetic study assuming every corner is detected
    missed, and that even the 11 x 8 board was read whole in only 86 of 100 tilted views until the
    detector was told the board. A change to the board, its square size or its quiet zone shows up here as a detection
    failure, not as a bad calibration weeks later.
"""
# The project root, the generator, and the committed PDF it must reproduce.
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONST_GENERATOR = os.path.join(CONST_PROJECT_FOLDER, 'Example', 'Camera', 'generate_checkerboard.py')
CONST_COMMITTED_PDF = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Calibration', 'Checkerboard_11x8_12mm_A4.pdf')
# The camera's scale: 12 mm squares are ~122 px at 0.098 mm/px, and the sensor window it sees.
#   Unit [float] (px/mm) / [Vector<int> 1x2] (px)
CONST_PX_PER_MM = 1.0 / 0.098
CONST_WINDOW = (1920, 1200)
# PDF points per millimetre.
#   Unit [float]
CONST_PT_PER_MM = 72.0 / 25.4


def _Load_Generator() -> tp.Any:
    """The generator as a module, for its constants."""
    spec = importlib.util.spec_from_file_location('generate_checkerboard', CONST_GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _Generate(directory: str) -> tp.Tuple[subprocess.CompletedProcess, bytes]:
    """Run the generator in a fresh interpreter with 'directory' as its working directory."""
    output = os.path.join(directory, 'board.pdf')
    result = subprocess.run([sys.executable, CONST_GENERATOR, '--output', output], cwd=directory,
                            capture_output=True, text=True, timeout=120)
    with open(output, 'rb') as handle:
        return result, handle.read()


def _Page_Streams(pdf: bytes) -> tp.List[str]:
    """The pages' content streams, in page order."""
    return re.findall(r'stream\n(.*?)endstream', pdf.decode('latin-1'), re.S)


def _Lines_Mm(stream: str, page_height_mm: float) -> tp.List[tp.Tuple[float, float, float, float]]:
    """Every stroked line (x0, y0, x1, y1) in mm from the page's top-left corner."""
    lines = []
    for match in re.finditer(r'([\d.]+) ([\d.]+) m ([\d.]+) ([\d.]+) l S', stream):
        x0, y0, x1, y1 = (float(v) / CONST_PT_PER_MM for v in match.groups())
        lines.append((x0, page_height_mm - y0, x1, page_height_mm - y1))
    return lines


def _Texts(stream: str) -> tp.List[str]:
    """Every line of text drawn, unescaped."""
    return [re.sub(r'\\(.)', r'\1', text) for text in re.findall(r'\((.*?)(?<!\\)\) Tj', stream)]


def _Render(stream: str, page_mm: tp.Tuple[float, float], px_per_mm: float) -> np.ndarray:
    """
    Description:
        Render a page's content stream to a grey image: rectangles filled, lines stroked, and each
        line of text as a solid box over its approximate extent (Helvetica averages ~0.55 em a glyph).
    """
    scale = px_per_mm / CONST_PT_PER_MM
    height_pt = page_mm[1] * CONST_PT_PER_MM
    image = np.full((int(round(page_mm[1] * px_per_mm)), int(round(page_mm[0] * px_per_mm))), 255, np.uint8)

    def Px(x_pt: float, y_pt: float) -> tp.Tuple[int, int]:
        return (int(round(x_pt * scale)), int(round((height_pt - y_pt) * scale)))

    for x, y, w, h in re.findall(r'([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) re f', stream):
        x, y, w, h = float(x), float(y), float(w), float(h)
        (c0, r1), (c1, r0) = Px(x, y), Px(x + w, y + h)
        image[r0:r1, c0:c1] = 0
    for x0, y0, x1, y1 in re.findall(r'([\d.]+) ([\d.]+) m ([\d.]+) ([\d.]+) l S', stream):
        cv2.line(image, Px(float(x0), float(y0)), Px(float(x1), float(y1)), 0, max(1, int(round(0.5 * scale))))
    text_pattern = r'/F\d ([\d.]+) Tf (-?\d) -?\d -?\d -?\d ([\d.]+) ([\d.]+) Tm \((.*?)(?<!\\)\) Tj'
    for size, a, x, y, text in re.findall(text_pattern, stream):
        size, x, y, length = float(size), float(x), float(y), 0.55 * float(size) * len(text)
        if a == '1':
            corners = (Px(x, y - 0.2 * size), Px(x + length, y + 0.75 * size))
        else:
            corners = (Px(x - 0.75 * size, y), Px(x + 0.2 * size, y + length))
        cv2.rectangle(image, corners[0], corners[1], 0, -1)
    return image


def _Camera_View(page: np.ndarray, tilt_deg: float, seed: int) -> np.ndarray:
    """
    Description:
        The page as the camera would see it: the 1920 x 1200 window centred on the board, tilted by
        a perspective warp about the vertical axis, blurred, with sensor noise.
    """
    rng = np.random.default_rng(seed)
    dark = np.argwhere(page[:int(page.shape[0] * 0.8), :int(page.shape[1] * 0.75)] == 0)
    centre = dark.mean(axis=0)[::-1]
    half = np.float32(CONST_WINDOW) / 2.0
    source = np.float32([centre + [-half[0], -half[1]], centre + [half[0], -half[1]],
                         centre + [half[0], half[1]], centre + [-half[0], half[1]]])
    squeeze = np.cos(np.radians(tilt_deg))
    near = 1.0 + 0.5 * np.sin(np.radians(tilt_deg)) * 0.25
    target = np.float32([[half[0] * (1 - squeeze), half[1] * (1 - 1 / near)],
                         [half[0] * (1 + squeeze), 0.0],
                         [half[0] * (1 + squeeze), 2 * half[1]],
                         [half[0] * (1 - squeeze), half[1] * (1 + 1 / near)]])
    view = cv2.warpPerspective(page, cv2.getPerspectiveTransform(source, target), CONST_WINDOW, borderValue=255)
    view = cv2.GaussianBlur(view, (5, 5), 1.2).astype(np.float64) + rng.normal(0.0, 3.0, view.shape)
    return np.clip(view, 0, 255).astype(np.uint8)


def test_the_generator_runs_from_an_unrelated_directory_and_reproduces_the_committed_pdf(tmp_path) -> None:
    """
    Description:
        Run as a person runs it, from a directory that is neither the repository root nor its own,
        the generator writes a two-page PDF byte-identical to docs/'s: the printed board and the
        generator never drift apart.
    """

    result, pdf = _Generate(str(tmp_path))
    assert result.returncode == 0, result.stderr[-2000:]
    assert '[INFO] Written:' in result.stdout
    assert pdf.startswith(b'%PDF-') and len(_Page_Streams(pdf)) == 2
    with open(CONST_COMMITTED_PDF, 'rb') as handle:
        assert pdf == handle.read(), 'docs/ holds a PDF the generator no longer writes: regenerate it'


def test_the_calibration_detector_reads_the_printed_board_whole(tmp_path) -> None:
    """
    Description:
        Page 1, rendered at the camera's scale and seen at tilts of 0-45 deg (three noise seeds each),
        is read by Calibration.Core.Detect_Board as the board's complete inner-corner grid in EVERY
        view: each of the 40+ calibration views contributes all 70 corners. Before the detector was
        told the board it grew from its minimum grid and read 86 of 100 such views whole, the rest as
        partial grids of ~30 corners. A 20 x 13 board fails this too. (The draft's thin grey outline
        in the quiet zone did not change the detection here; the quiet-zone test guards it, on
        OpenCV's stated requirement rather than a measured failure.)
    """

    generator = _Load_Generator()
    _, pdf = _Generate(str(tmp_path))
    page = _Render(_Page_Streams(pdf)[0], generator.CONST_PAGE_MM, CONST_PX_PER_MM)
    columns, rows = generator.CONST_BOARD_SQUARES
    partial = []
    for tilt_deg in range(0, 50, 5):
        for seed in range(3):
            detection = Detect_Board(_Camera_View(page, float(tilt_deg), seed=100 + seed), (columns, rows))
            if not (detection.Found and sorted(detection.Grid) == sorted((columns - 1, rows - 1))):
                partial.append((tilt_deg, seed, detection.Grid, detection.Reason))
    assert not partial, partial


def test_nothing_is_drawn_inside_the_quiet_zone(tmp_path) -> None:
    """
    Description:
        The white border the sector-based detector needs (one square around the board) holds no
        mark at all — no outline, ruler or text. The draft drew a grey outline 2 mm from the squares;
        it did not break detection on these renders, but OpenCV asks for the border and real prints
        under real light are less forgiving than a render.
    """

    generator = _Load_Generator()
    _, pdf = _Generate(str(tmp_path))
    px_per_mm = 10.0
    page = _Render(_Page_Streams(pdf)[0], generator.CONST_PAGE_MM, px_per_mm)
    # The board's top-left corner: the first dark pixel above the caption strip and left of the vertical
    # ruler (the top-left square is black). Then the board's extent and the border around it.
    dark = np.argwhere(page[:int(page.shape[0] * 0.8), :int(page.shape[1] * 0.75)] == 0)
    columns, rows = generator.CONST_BOARD_SQUARES
    top, left = dark.min(axis=0)
    width, height = (columns * generator.CONST_SQUARE_MM * px_per_mm, rows * generator.CONST_SQUARE_MM * px_per_mm)
    quiet = generator.CONST_QUIET_ZONE_MM * px_per_mm
    zone = page[int(top - quiet) + 1:int(top + height + quiet) - 1, int(left - quiet) + 1:int(left + width + quiet) - 1]
    inner = np.ones_like(zone, dtype=bool)
    inner[int(quiet) - 1:int(quiet + height), int(quiet) - 1:int(quiet + width)] = False
    assert zone[inner].min() == 255


def test_both_rulers_are_exactly_ten_squares_and_the_caption_demands_both(tmp_path) -> None:
    """
    Description:
        Page 1 carries a horizontal AND a vertical ruler, each exactly ten squares (120 mm) with a
        tick at every square — printers can scale the two axes differently, and the solver takes the x
        and y factors from one --square-mm. The caption asks for both measurements and says what to do
        when either is wrong: not use the board, fix the print.
    """

    generator = _Load_Generator()
    _, pdf = _Generate(str(tmp_path))
    stream = _Page_Streams(pdf)[0]
    lines = _Lines_Mm(stream, generator.CONST_PAGE_MM[1])
    square = generator.CONST_SQUARE_MM
    for axis in (0, 1):
        along, across = (0, 1) if axis == 0 else (1, 0)
        rulers = [l for l in lines if abs(l[across] - l[across + 2]) < 1e-6 and abs(l[along] - l[along + 2]) > 20]
        assert len(rulers) == 1, 'expected one %s ruler' % ('horizontal' if axis == 0 else 'vertical')
        ruler = rulers[0]
        assert abs(abs(ruler[along + 2] - ruler[along]) - 10 * square) < 1e-3
        start = min(ruler[along], ruler[along + 2])
        # The ticks: short lines across the ruler, centred on it.
        ticks = sorted(l[along] for l in lines if abs(l[along] - l[along + 2]) < 1e-6
                       and abs(l[across] - l[across + 2]) < 5
                       and abs((l[across] + l[across + 2]) / 2 - ruler[across]) < 1e-3)
        assert len(ticks) == 11
        assert np.allclose(np.array(ticks) - start, np.arange(11) * square, atol=1e-3)
    caption = ' '.join(_Texts(stream))
    assert 'BOTH' in caption and 'H (horizontal) AND V (vertical)' in caption and 'EACH measure 120.0 mm' in caption
    assert 'do NOT use this board' in caption and 'reprint' in caption


def test_the_command_asks_for_the_calipered_size_never_the_nominal(tmp_path) -> None:
    """
    Description:
        The calibrate.py command printed on both pages names the board's squares and leaves
        --square-mm as a placeholder for the calipered size: nothing a person could copy as 12.0.
    """

    _, pdf = _Generate(str(tmp_path))
    for stream in _Page_Streams(pdf):
        text = ' '.join(_Texts(stream))
        assert '--board-squares 11x8' in text
        assert '--square-mm <CALIPERED mm>' in text
        assert not re.search(r'--square-mm\s+\d', text)


def test_the_printed_text_names_no_repository_path_of_a_record(tmp_path) -> None:
    """
    Description:
        The paper outlives the repository's layout: the instructions name the capture checklist by name,
        never by a path such as docs/capture-checklist.md, which went stale when the records moved.
    """

    _, pdf = _Generate(str(tmp_path))
    text = ' '.join(' '.join(_Texts(stream)) for stream in _Page_Streams(pdf))
    assert 'capture checklist' in text
    assert not re.search(r'[\w./-]+\.md\b', text), re.findall(r'[\w./-]+\.md\b', text)
    assert 'docs/' not in text
