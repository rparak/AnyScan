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
# File Name: ../Example/Camera/generate_checkerboard.py
## =========================================================================== ##

# System (Default)
import sys
# OS (Operating system interfaces)
import os
# Resolve src/ from this file's own location (Example/Camera -> ../../src), so the script runs the
# same whether launched from Example/Camera/ or the repository root.
_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))
if _SRC not in sys.path:
    sys.path.append(_SRC)
# Argparse (Command-line parsing)
import argparse
# Textwrap (Wrapping the instructions to the page)
import textwrap
# Typing (Support for type hints)
import typing as tp
# Custom Library:
#   ../Configuration/Core — the repository root, for the default output path
from Configuration.Core import CONST_PROJECT_ROOT

"""
Description:
    Initialization of constants.

    The printed chessboard read by Example/Camera/calibrate.py (Calibration.Core.Detect_Board:
    findChessboardCornersSBWithMeta with CALIB_CB_LARGER). The PDF is written by hand with the
    standard library: two pages of filled rectangles, lines and the built-in Helvetica font need no
    PDF library, and millimetres convert exactly to PDF points, so the geometry is exact vector
    geometry (a raster at 600 dpi would put 12 mm at 283.46 px and wobble every edge). The output
    carries no timestamp, so the same constants always produce the same bytes.
"""
# The board's squares (columns, rows): the value of calibrate.py --board-squares. 11 x 8 at 12 mm is
# 132 x 96 mm, which the detector finds whole: rendered through a camera at 122 px a square, flat
# and tilted 10-35 deg, Calibration.Core.Detect_Board returned the full 10 x 7 grid in 12 of 12
# frames. A board larger than the field does NOT work with that detector: from its minimum grid,
# CALIB_CB_LARGER stops growing beyond ~15 columns and where the board leaves the frame, so the same
# test on 20 x 13 returned grids from 3 x 5 to 17 x 3 (see design-decisions.md, ChArUco is the
# route to a larger board). The factor's uniformity is bought with views instead: 11 x 8 spreads
# 0.057 / 0.103 % (median / 90th percentile) at 24 views, over the 0.1 % limit, and 0.039 / 0.065 %
# at 40 (calibration_tilt_study.py's camera, 0.1 px noise, 40 seeds) — hence 40+ views.
#   Unit [Vector<int> 1x2]
CONST_BOARD_SQUARES = (11, 8)
# The nominal square size. Nominal only: calibrate.py --square-mm takes the CALIPERED size.
#   Unit [float] (mm)
CONST_SQUARE_MM = 12.0
# The white border around the board, kept free of every mark: the sector-based detector wants about
# one square of white around the whole board (OpenCV, findChessboardCornersSB). The board plus this
# border is 120 mm tall against a ~118 mm field, so a flat view cannot hold all of it; that was
# measured not to matter (the detection above, and test/Camera/test_generate_checkerboard.py). Do
# not shrink the border to make it fit.
#   Unit [float] (mm)
CONST_QUIET_ZONE_MM = CONST_SQUARE_MM
# A4 landscape, and the margin most printers cannot print into.
#   Unit [Vector<float> 1x2] (mm) / [float] (mm)
CONST_PAGE_MM = (297.0, 210.0)
CONST_PRINTER_MARGIN_MM = 5.0
# The scale rulers, one per axis, each this many squares long. Printers can scale the paper-feed
# direction and the head direction differently, and calibrate.py solves the x and y factors
# separately from ONE --square-mm, so an error in one direction goes straight into that axis's factor.
#   Unit [int]
CONST_RULER_SQUARES = 10
# How far the two calipered directions may differ over the ruler length: 0.1 mm over 120 mm is
# 0.083 %, under Calibration.Core.CONST_CALIB_FACTOR_UNIFORM_PCT (0.1 %).
#   Unit [float] (mm)
CONST_AXIS_TOLERANCE_MM = 0.1
# The PDF written by default: under Data/Calibration/, the calibration's committed input (the board
# printed for calibrate.py --capture), apart from the git-ignored capture sets in Data/Images/Calibration/.
#   Unit [string]
CONST_OUTPUT_FILE = os.path.join(CONST_PROJECT_ROOT, 'Data', 'Calibration', 'Checkerboard_%dx%d_%dmm_A4.pdf'
                                 % (CONST_BOARD_SQUARES + (int(CONST_SQUARE_MM),)))
# PDF points per millimetre (72 points per inch, 25.4 mm per inch).
#   Unit [float]
CONST_PT_PER_MM = 72.0 / 25.4


def To_Pt(value_mm: float) -> float:
    """
    Description:
        Convert millimetres to PDF points.

    Args:
        (1) value_mm [float]: The length (mm).

    Returns:
        (1) parameter [float]: The length (pt).
    """

    return value_mm * CONST_PT_PER_MM


def Rectangle(x_mm: float, y_mm: float, width_mm: float, height_mm: float) -> str:
    """
    Description:
        A filled rectangle, placed from the page's top-left corner (the PDF's origin is bottom-left).

    Args:
        (1) x_mm [float]: The left edge (mm from the page's left).
        (2) y_mm [float]: The top edge (mm from the page's top).
        (3) width_mm [float]: The width (mm).
        (4) height_mm [float]: The height (mm).

    Returns:
        (1) parameter [string]: The content-stream operators.
    """

    return '%.4f %.4f %.4f %.4f re f\n' % (To_Pt(x_mm), To_Pt(CONST_PAGE_MM[1] - y_mm - height_mm),
                                           To_Pt(width_mm), To_Pt(height_mm))


def Line(x0_mm: float, y0_mm: float, x1_mm: float, y1_mm: float) -> str:
    """
    Description:
        A stroked line, placed from the page's top-left corner.

    Args:
        (1) x0_mm, y0_mm [float]: The start (mm from the page's left and top).
        (2) x1_mm, y1_mm [float]: The end (mm from the page's left and top).

    Returns:
        (1) parameter [string]: The content-stream operators.
    """

    return '%.4f %.4f m %.4f %.4f l S\n' % (To_Pt(x0_mm), To_Pt(CONST_PAGE_MM[1] - y0_mm),
                                            To_Pt(x1_mm), To_Pt(CONST_PAGE_MM[1] - y1_mm))


def Text(x_mm: float, y_mm: float, text: str, size_pt: float, bold: bool = False, vertical: bool = False) -> str:
    """
    Description:
        A line of text (ASCII, Helvetica) with its baseline starting at a point placed from the
        page's top-left corner.

    Args:
        (1) x_mm, y_mm [float]: The baseline's start (mm from the page's left and top).
        (2) text [string]: The text.
        (3) size_pt [float]: The font size (pt).
        (4) bold [bool]: Helvetica-Bold instead of Helvetica.
        (5) vertical [bool]: Read bottom to top (rotated 90 deg anticlockwise).

    Returns:
        (1) parameter [string]: The content-stream operators.
    """

    escaped = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    matrix = '0 1 -1 0' if vertical else '1 0 0 1'
    return 'BT /%s %.1f Tf %s %.4f %.4f Tm (%s) Tj ET\n' % ('F2' if bold else 'F1', size_pt, matrix, To_Pt(x_mm),
                                                           To_Pt(CONST_PAGE_MM[1] - y_mm), escaped)


def Ruler(x_mm: float, y_mm: float, vertical: bool) -> str:
    """
    Description:
        A scale ruler CONST_RULER_SQUARES squares long with a tick at every square, starting at a
        point and running right (horizontal) or down (vertical).

    Args:
        (1) x_mm, y_mm [float]: The start (mm from the page's left and top).
        (2) vertical [bool]: Run down instead of right.

    Returns:
        (1) parameter [string]: The content-stream operators.
    """

    length = CONST_RULER_SQUARES * CONST_SQUARE_MM
    tick = 1.5
    if vertical:
        stream = Line(x_mm, y_mm, x_mm, y_mm + length)
        for i in range(CONST_RULER_SQUARES + 1):
            stream += Line(x_mm - tick, y_mm + i * CONST_SQUARE_MM, x_mm + tick, y_mm + i * CONST_SQUARE_MM)
    else:
        stream = Line(x_mm, y_mm, x_mm + length, y_mm)
        for i in range(CONST_RULER_SQUARES + 1):
            stream += Line(x_mm + i * CONST_SQUARE_MM, y_mm - tick, x_mm + i * CONST_SQUARE_MM, y_mm + tick)
    return stream


def Command_Line() -> str:
    """
    Description:
        The calibrate.py command this board is solved with, placeholders where a measured value goes.

    Returns:
        (1) parameter [string]: The command.
    """

    return ('python Example/Camera/calibrate.py --images <DIR> --board-squares %dx%d '
            '--square-mm <CALIPERED mm> --board-height-mm <PLATE + PAPER mm>' % CONST_BOARD_SQUARES)


def Board_Page() -> str:
    """
    Description:
        Page 1: the board centred horizontally inside its quiet zone, a vertical ruler in the right
        margin, and below the quiet zone a horizontal ruler, the scale check and the board's command.
        Nothing is drawn inside the quiet zone.

    Returns:
        (1) parameter [string]: The page's content stream.
    """

    columns, rows = CONST_BOARD_SQUARES
    width, height = columns * CONST_SQUARE_MM, rows * CONST_SQUARE_MM
    ruler = CONST_RULER_SQUARES * CONST_SQUARE_MM
    h_y = CONST_PAGE_MM[1] - 21.0
    x0 = (CONST_PAGE_MM[0] - width) / 2.0
    y0 = (CONST_PRINTER_MARGIN_MM + h_y - 4.0 - height) / 2.0
    assert x0 - CONST_QUIET_ZONE_MM >= CONST_PRINTER_MARGIN_MM + 8.0, 'no room for the vertical ruler'
    assert y0 - CONST_QUIET_ZONE_MM >= CONST_PRINTER_MARGIN_MM, 'the quiet zone runs off the page'

    # The board: the top-left square black.
    stream = '0 g\n'
    for row in range(rows):
        for column in range(columns):
            if (row + column) % 2 == 0:
                stream += Rectangle(x0 + column * CONST_SQUARE_MM, y0 + row * CONST_SQUARE_MM,
                                    CONST_SQUARE_MM, CONST_SQUARE_MM)

    # The rulers, outside the quiet zone: vertical beside it on the right, horizontal below it.
    v_x = x0 + width + CONST_QUIET_ZONE_MM + 6.0
    v_y = y0 + (height - ruler) / 2.0
    h_x = (CONST_PAGE_MM[0] - ruler) / 2.0
    assert h_y - 2.0 >= y0 + height + CONST_QUIET_ZONE_MM, 'the horizontal ruler is inside the quiet zone'
    assert v_y >= CONST_PRINTER_MARGIN_MM, 'the vertical ruler runs off the page'
    stream += '0 G 0.5 w\n' + Ruler(v_x, v_y, vertical=True) + Ruler(h_x, h_y, vertical=False)
    stream += Text(v_x - 3.0, v_y + ruler, 'V: must be %.1f mm' % ruler, 7.0, bold=True, vertical=True)
    stream += Text(h_x - 30.0, h_y + 1.0, 'H: must be %.1f mm' % ruler, 7.0, bold=True)

    # The scale check and the board's identity, in the strip below.
    margin = CONST_PRINTER_MARGIN_MM + 5.0
    stream += Text(margin, h_y + 6.5, 'SCALE CHECK - measure BOTH rulers before use: H (horizontal) AND V (vertical) '
                   'must EACH measure %.1f mm (%d squares).' % (ruler, CONST_RULER_SQUARES), 8.0, bold=True)
    stream += Text(margin, h_y + 10.5, 'If either does not, do NOT use this board: fix the printer scaling (100 %, '
                   'no fit-to-page) and reprint. Why both: page 2.', 8.0)
    stream += Text(margin, h_y + 14.3, '%d x %d squares, %.0f mm nominal, %d x %d inner corners. Solve: %s'
                   % (columns, rows, CONST_SQUARE_MM, columns - 1, rows - 1, Command_Line()), 6.0)
    return stream


def Instructions_Page() -> str:
    """
    Description:
        Page 2: how to print, check, mount and use the board. Each section is paragraphs wrapped to
        the page; a paragraph starting with spaces is a command, printed as it is.

    Returns:
        (1) parameter [string]: The page's content stream.
    """

    columns, rows = CONST_BOARD_SQUARES
    ruler = CONST_RULER_SQUARES * CONST_SQUARE_MM
    sections = [
        ('1. Print', [
            'Print page 1 at 100 % (actual size): no "fit to page", no "shrink to printable area", landscape, on '
            'matte paper. Glossy paper glares under the flat light and hides corners.']),
        ('2. Check the scale - both axes, before anything else', [
            'With a steel rule, measure the H and V rulers on page 1. EACH must be %.1f mm (%d squares). If either '
            'is not, do NOT use the board: fix the printer scaling and reprint.' % (ruler, CONST_RULER_SQUARES),
            'Both, not one: a printer can scale the paper-feed direction differently from the head direction, and '
            'calibrate.py solves the x and y mm/px factors separately from ONE square size. An error in one '
            'direction goes straight into that axis\'s factor, and nothing in the calibration report will show it.',
            'Then caliper the board across %d squares horizontally AND vertically; --square-mm is that length / %d. '
            'If the two directions differ by more than %.1f mm (%.3f %%, under the calibration\'s 0.1 %% uniformity '
            'limit), reprint: one --square-mm cannot carry two scales.'
            % (CONST_RULER_SQUARES, CONST_RULER_SQUARES, CONST_AXIS_TOLERANCE_MM,
               100.0 * CONST_AXIS_TOLERANCE_MM / ruler)]),
        ('3. Mount - the flatness requirement grows with the board', [
            'Mount the %.0f x %.0f mm board on a rigid plate: glass, or aluminium at least 3 mm thick. Card and foam '
            'board bow, and a larger print needs a stiffer plate still. A warped board produces a calibration that '
            'looks fine and is WRONG: the solver assumes a plane, the bow can be absorbed into the lens model at a '
            'small reprojection error, and every measurement inherits it.'
            % (columns * CONST_SQUARE_MM, rows * CONST_SQUARE_MM),
            'Glue the whole sheet down without bubbles. Keep the white border around the board intact and unmarked: '
            'the detector needs about one square of white on every side. Do not trim it, write on it or tape '
            'over it.']),
        ('4. Calibrate', [
            'Capture at least 40 views, flat (f) and tilted (t); docs/capture-checklist.md, item 1, says how many of '
            'each and why 40:',
            '    python Example/Camera/calibrate.py --capture --board-squares %dx%d' % CONST_BOARD_SQUARES,
            'Solve:',
            '    ' + Command_Line(),
            '<CALIPERED mm> is the square size from step 2 - never the nominal %.0f mm printed here. <PLATE + PAPER '
            'mm> is the board surface\'s height above the table: the plate and paper thickness, measured.'
            % CONST_SQUARE_MM]),
        ('The board', [
            '%d x %d squares (--board-squares %dx%d), %d x %d inner corners, %.0f mm nominal squares, pattern '
            '%.0f x %.0f mm. Generated by Example/Camera/generate_checkerboard.py.'
            % (columns, rows, columns, rows, columns - 1, rows - 1, CONST_SQUARE_MM, columns * CONST_SQUARE_MM,
               rows * CONST_SQUARE_MM)])]
    stream = '0 g\n' + Text(20.0, 22.0, 'Checkerboard calibration target - %d x %d squares, %.0f mm'
                            % (columns, rows, CONST_SQUARE_MM), 14.0, bold=True)
    y = 34.0
    for heading, paragraphs in sections:
        stream += Text(20.0, y, heading, 10.0, bold=True)
        y += 5.5
        for paragraph in paragraphs:
            for line in ([paragraph] if paragraph.startswith(' ') else textwrap.wrap(paragraph, 125)):
                stream += Text(20.0, y, line, 8.5)
                y += 4.3
            y += 1.2
        y += 2.3
    assert y <= CONST_PAGE_MM[1] - CONST_PRINTER_MARGIN_MM, 'the instructions overflow page 2'
    return stream


def Write_Pdf(pages: tp.List[str], path: str, title: str) -> None:
    """
    Description:
        Write a PDF of uncompressed content-stream pages at CONST_PAGE_MM, with the two built-in
        Helvetica fonts as /F1 (regular) and /F2 (bold).

    Args:
        (1) pages [Vector<string>]: The pages' content streams.
        (2) path [string]: The output file.
        (3) title [string]: The document title.
    """

    count = len(pages)
    page_ids = [6 + 2 * i for i in range(count)]
    objects = ['<< /Type /Catalog /Pages 2 0 R >>',
               '<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join('%d 0 R' % i for i in page_ids), count),
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
               '<< /Title (%s) /Creator (Example/Camera/generate_checkerboard.py) >>' % title]
    for i, stream in enumerate(pages):
        objects.append('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.4f %.4f] /Resources << /Font << /F1 3 0 R '
                       '/F2 4 0 R >> >> /Contents %d 0 R >>' % (To_Pt(CONST_PAGE_MM[0]), To_Pt(CONST_PAGE_MM[1]),
                                                                  page_ids[i] + 1))
        objects.append('<< /Length %d >>\nstream\n%sendstream' % (len(stream.encode('latin-1')), stream))

    output = b'%PDF-1.4\n'
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output += ('%d 0 obj\n%s\nendobj\n' % (number, body)).encode('latin-1')
    xref = len(output)
    output += ('xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)).encode('latin-1')
    output += ''.join('%010d 00000 n \n' % offset for offset in offsets).encode('latin-1')
    output += ('trailer\n<< /Size %d /Root 1 0 R /Info 5 0 R >>\nstartxref\n%d\n%%%%EOF\n'
               % (len(objects) + 1, xref)).encode('latin-1')
    with open(path, 'wb') as handle:
        handle.write(output)


def main():
    """
    Description:
        Generate the calibration chessboard as a two-page A4 PDF: page 1 the board with a scale
        ruler on each axis, page 2 how to print, check, mount and use it.
    """

    parser = argparse.ArgumentParser(description='Generate the printable calibration chessboard (PDF).')
    parser.add_argument('--output', default=CONST_OUTPUT_FILE, help='the PDF written (default: %(default)s)')
    args = parser.parse_args()

    columns, rows = CONST_BOARD_SQUARES
    Write_Pdf([Board_Page(), Instructions_Page()], args.output,
              'Checkerboard %d x %d squares, %.0f mm - camera calibration target' % (columns, rows, CONST_SQUARE_MM))
    print('[INFO] Written: %s' % args.output)
    print('[INFO] Board: %d x %d squares (%d x %d inner corners), %.1f x %.1f mm at %.1f mm nominal.'
          % (columns, rows, columns - 1, rows - 1, columns * CONST_SQUARE_MM, rows * CONST_SQUARE_MM, CONST_SQUARE_MM))
    print('[INFO] Before use: both rulers must measure %.1f mm, and --square-mm is the CALIPERED size, not the nominal.'
          % (CONST_RULER_SQUARES * CONST_SQUARE_MM))
    return 0

if __name__ == '__main__':
    sys.exit(main())
