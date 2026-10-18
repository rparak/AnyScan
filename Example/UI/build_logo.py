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
# File Name: ../Example/UI/build_logo.py
## =========================================================================== ##

# System (Default)
import argparse
import os
import re
import shutil
import sys
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Derive the application's copies of the AnyScan logo from the delivered, outlined logo
    (images/anyscan-logo.svg, the JIC Smart Factory designer's file, committed unchanged):

        App/assets/anyscan-logo.svg           the logo, byte for byte
        App/assets/anyscan-logo-wordmark.svg  the logo without its tagline, in the logo's own viewBox: the
                                              top bar draws it and sets the tagline beside it as live text
                                              (docs/design-decisions.md, "The header draws the delivered logo
                                              and sets its tagline as live text")
        App/assets/anyscan-mark.svg           the mark alone (the empty viewport, and the source of the icon)
        App/assets/anyscan-mark.ico           the window and taskbar icon: the mark alone on a transparent ground,
                                              filling the square, grid-fitted at each of 16-256 px

    The derivation is string surgery on the delivered file, so every byte it does not remove is the
    designer's: the logo's text is three top-level outlined paths after the mark's groups, the wordmark
    above CONST_TAGLINE_TOP and the tagline below it. The mark derived this way is byte for byte the mark
    file delivered with the logo. No font and no Inkscape are involved.

        python Example/UI/build_logo.py                        # rewrite the four files in App/assets/
        python Example/UI/build_logo.py --output-dir /tmp/logo # write them elsewhere, e.g. to compare

    After a new logo, regenerate the diagram: python Example/UI/architecture_diagram.py.
"""
# The project folder, from this file's own location (Example/UI -> ..).
#   Unit [string]
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
CONST_LOGO_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-logo.svg')
CONST_ASSETS_FOLDER = os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets')
# The files written, by their names in App/assets/.
#   Unit [string]
CONST_LOGO_NAME = 'anyscan-logo.svg'
CONST_WORDMARK_NAME = 'anyscan-logo-wordmark.svg'
CONST_MARK_NAME = 'anyscan-mark.svg'
CONST_ICON_NAME = 'anyscan-mark.ico'
# Where the logo's parts are told apart, in logo units: a top-level path starting below y = 107.5 is the
# tagline (the wordmark's ink ends at 105.1, the tagline's starts at 109.9); the mark is the logo's first
# 140 x 140 units (its ink is 0-140, the wordmark's starts at x = 165.5).
#   Unit [logo units]
CONST_TAGLINE_TOP = 107.5
CONST_MARK_SIZE = '140'
# The notes the derived SVGs carry, and the mark's accessible name.
#   Unit [string]
CONST_WORDMARK_NOTE = ('<!-- Built by Example/UI/build_logo.py from images/anyscan-logo.svg: the logo without its tagline, '
                       'which the top bar sets as live text. Do not edit. -->')
CONST_MARK_LABEL = 'AnyScan mark'
# The icon's sizes. The mark fills each square, on a transparent ground (the owner's choice, 2026-10-18).
#   Unit [Vector<int>] (px)
CONST_ICON_SIZES = (16, 20, 24, 32, 48, 64, 128, 256)


def Split_Logo(logo: str) -> tp.Tuple[str, tp.List[str], str]:
    """
    Description:
        The logo split into its head (the root tag, the title and the mark's groups), its top-level text
        paths in order, and its closing tag. Stops when the logo is not in the shape the derivation reads.

    Args:
        (1) logo [string]: The logo SVG.

    Returns:
        (1) parameter [Tuple<string, Vector<string>, string>]: (head, text paths, tail).
    """

    end = logo.rfind('</g>') + len('</g>')
    paths = re.findall(r'<path [^>]*/>', logo[end:])
    tail = logo[end:]
    for path in paths:
        tail = tail.replace(path, '', 1)
    if end < len('</g>') or len(paths) != 3 or tail.strip() != '</svg>':
        sys.exit('[ERROR] %s is not the delivered logo\'s shape: the mark\'s groups, then exactly three outlined text '
                 'paths and </svg>.' % CONST_LOGO_FILE)
    return logo[:end], paths, tail


def First_Point(path: str) -> tp.Tuple[float, float]:
    """
    Description:
        The first point of an outlined path ('M x y').

    Args:
        (1) path [string]: The <path/> element.

    Returns:
        (1) parameter [Vector<float> 1x2]: (x, y) in logo units.
    """

    found = re.search(r' d="M\s*([-\d.]+)[\s,]+([-\d.]+)', path)
    return float(found.group(1)), float(found.group(2))


def Wordmark_Only(logo: str) -> str:
    """
    Description:
        The logo without its tagline: the top-level path below CONST_TAGLINE_TOP removed, a note added,
        the viewBox unchanged, so the tagline set at the logo's coordinates lands where the logo has it.

    Args:
        (1) logo [string]: The logo SVG.

    Returns:
        (1) parameter [string]: The SVG.
    """

    head, paths, tail = Split_Logo(logo)
    tagline = [path for path in paths if First_Point(path)[1] >= CONST_TAGLINE_TOP]
    if len(tagline) != 1:
        sys.exit('[ERROR] %d top-level paths start below y = %g; the tagline is exactly one.' % (len(tagline), CONST_TAGLINE_TOP))
    root_end = head.index('>') + 1
    return (head[:root_end].replace('aria-label="AnyScan – The camera sees, the model describes."', 'aria-label="AnyScan"')
            + CONST_WORDMARK_NOTE + head[root_end:] + ''.join(path for path in paths if path not in tagline) + tail)


def Mark_Only(logo: str) -> str:
    """
    Description:
        The logo's mark alone: the text paths removed and the viewBox cut to the mark's square, with the mark's
        accessible name.

    Args:
        (1) logo [string]: The logo SVG.

    Returns:
        (1) parameter [string]: The SVG.
    """

    head, _, tail = Split_Logo(logo)
    head = re.sub(r'viewBox="[^"]*" width="[^"]*" height="[^"]*"',
                  'viewBox="0 0 %s %s" width="%s" height="%s"' % ((CONST_MARK_SIZE,) * 4), head, count=1)
    head = re.sub(r'aria-label="[^"]*"', 'aria-label="%s"' % CONST_MARK_LABEL, head, count=1)
    head = head.replace('<title>AnyScan</title>', '<title>%s</title>' % CONST_MARK_LABEL, 1)
    return head + tail


def Write_Icon(mark_path: str, output: str) -> None:
    """
    Description:
        The window and taskbar icon: the mark, filling a transparent square, rendered at each of CONST_ICON_SIZES and
        written as one .ico. Each size is rendered, not scaled down from the largest, and grid-fitted for its size
        (UI.Utilities.Grid_Fit, every edge to its own nearest pixel), so a 16 px icon keeps the mark's shape and has no
        half-covered edge.

    Args:
        (1) mark_path [string]: The mark SVG.
        (2) output [string]: The .ico file.
    """

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    # PyQt5 (Render the SVG) [pip3 install PyQt5] and Pillow (Write the .ico) [pip3 install Pillow]
    from PyQt5.QtCore import QByteArray, QRectF, Qt
    from PyQt5.QtGui import QImage, QPainter
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtWidgets import QApplication
    from PIL import Image
    # Custom Lib.: Grid-fitting of a mark's straight edges (Qt-free)
    #   ../src/UI/Utilities/Grid_Fit.py
    sys.path.append(os.path.join(CONST_PROJECT_FOLDER, 'src'))
    from UI.Utilities.Grid_Fit import Fit_Svg

    app = QApplication.instance() or QApplication([])
    with open(mark_path, 'r', encoding='utf-8') as handle:
        mark = handle.read()
    side = float(CONST_MARK_SIZE)
    images = []
    for size in CONST_ICON_SIZES:
        renderer = QSvgRenderer(QByteArray(Fit_Svg(mark, size / side, side, thin_px=0.0).encode('utf-8')))
        image = QImage(size, size, QImage.Format_RGBA8888)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter, QRectF(0.0, 0.0, size, size))
        painter.end()
        pointer = image.constBits()
        pointer.setsize(image.byteCount())
        images.append(Image.frombuffer('RGBA', (size, size), bytes(pointer), 'raw', 'RGBA', image.bytesPerLine(), 1))
    images[-1].save(output, format='ICO', sizes=[(s, s) for s in CONST_ICON_SIZES], append_images=images[:-1])
    del app
    print('[INFO] Wrote %s: the mark at %s px.' % (output, ', '.join(str(s) for s in CONST_ICON_SIZES)))


def main() -> int:
    """
    Description:
        Read the delivered logo, write its copy, the wordmark and the mark, and render the icon from the mark.

    Returns:
        (1) parameter [int]: The exit code.
    """

    parser = argparse.ArgumentParser(description='Derive the application\'s logo files from images/anyscan-logo.svg.')
    parser.add_argument('--output-dir', default=CONST_ASSETS_FOLDER, help='Where to write them (default: App/assets/).')
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    with open(CONST_LOGO_FILE, 'r', encoding='utf-8') as handle:
        logo = handle.read()
    shutil.copyfile(CONST_LOGO_FILE, os.path.join(args.output_dir, CONST_LOGO_NAME))
    print('[INFO] Copied %s to %s.' % (CONST_LOGO_FILE, args.output_dir))
    for name, content in ((CONST_WORDMARK_NAME, Wordmark_Only(logo)), (CONST_MARK_NAME, Mark_Only(logo))):
        with open(os.path.join(args.output_dir, name), 'w', encoding='utf-8', newline='') as handle:
            handle.write(content)
        print('[INFO] Wrote %s.' % os.path.join(args.output_dir, name))
    Write_Icon(os.path.join(args.output_dir, CONST_MARK_NAME), os.path.join(args.output_dir, CONST_ICON_NAME))
    print('[INFO] Now run python Example/UI/architecture_diagram.py.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
