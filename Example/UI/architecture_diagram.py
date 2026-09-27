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
# File Name: ../Example/UI/architecture_diagram.py
## =========================================================================== ##

# System (Default)
import sys
import os
import argparse
import base64
# Resolve the project folder from this file's own location (Example/UI -> ..), so the script
# runs the same whether launched from Example/UI/ or the repo root.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    '..', '..'))
_SRC = os.path.join(CONST_PROJECT_FOLDER, 'src')
if _SRC not in sys.path:
    sys.path.append(_SRC)
# XML (Escaping text content)
from xml.sax.saxutils import escape
# Typing (Support for type hints)
import typing as tp
# Custom Lib.: AnyScan — the colour tokens, the ONLY source of the diagram's colours
#   ../Parameters/Theme
import Parameters.Theme as Theme
# Custom Lib.: AnyScan UI — the type scale and the font fallbacks the console uses
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
# Custom Lib.: AnyScan UI — the console's funding band, whose logos and disclaimer the diagram repeats
#   ../UI/Widgets
from UI.Widgets import Funding_Row_Cls

"""
Description:
    Initialization of constants.

    The generator of images/anyscan-architecture.svg, the diagram the README opens with: what
    AnyScan is and how it works, at the top level only — the camera, finding the objects,
    describing and measuring each one, the desktop application, and the configuration behind
    them. No class names, no configuration fields; README > Detection logic has the detail.

    Regenerating is the way to change it; the SVG is never edited by hand. Every colour comes
    from a Parameters/Theme.py token and every size from the console's type scale, so the
    figure moves with the theme instead of drifting from it. The SVG is self-contained, because
    the README shows it through <img>, and an SVG loaded that way never fetches another file:
    the AnyScan logo is copied in byte for byte from images/anyscan-logo.svg, and the JIC mark and
    the funding band's logos are embedded from App/assets/ as base64 PNG data. The band is the
    console's own (UI.Widgets.Funding_Row_Cls): the same logos, order and disclaimer.

    test/UI/test_brand_figures.py fails when the committed SVG is not this script's output, or
    draws a colour that is not a token.

        python Example/UI/architecture_diagram.py            # rewrite the SVG
        python Example/UI/architecture_diagram.py --check    # exit 1 if it is stale

    The layout is checked against FALLBACK font metrics (Helvetica Neue / Arial), which is
    what most README readers get: an <img> SVG cannot load Inter as a web font. A layout that
    only fits with Inter installed will overflow for them.
"""
# The source logo, the folder of the PNG marks, the JIC mark, and the diagram this script writes.
#   Unit [string]
CONST_LOGO_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-logo.svg')
CONST_ASSETS_FOLDER = os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets')
CONST_JIC_FILE = os.path.join(CONST_ASSETS_FOLDER, 'brand-jic-mute.png')
CONST_DIAGRAM_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-architecture.svg')
# The marker comments around the inline logo; the test reads the copy between them.
#   Unit [string]
CONST_LOGO_BEGIN = '<!-- logo:begin -->'
CONST_LOGO_END = '<!-- logo:end -->'
# The drawing size in user units: wide, so it stays legible at README width (~900 px renders
# it at 0.75).
#   Unit [px]
CONST_WIDTH = 1200
CONST_HEIGHT = 790
# The funding band: its top edge, the console's per-logo heights scaled by this factor (the
# heights are tuned per logo there, so they are scaled, never replaced), and the gap between logos.
#   Unit [px] / [-]
CONST_BAND_TOP = 636
CONST_BAND_SCALE = 1.35
CONST_BAND_GAP = 36
# What each band logo is, for screen readers.
#   Unit [Dictionary<string, string>]
CONST_BAND_LABELS = {'edih-digimat-white.png': 'EDIH-DIGIMAT',
                     'partner-ministry-white.png': 'Ministry of Industry and Trade of the Czech Republic',
                     'funder-eu-white.png': 'Funded by the European Union'}
# The console's type scale (Style.CONST_TYPE_SCALE, in points) at 1.4x, so the smallest step
# used still renders at about 12 px at README width.
#   Unit [Vector<float>]
CONST_SCALE = [round(size * 1.4, 1) for size in Style.CONST_TYPE_SCALE]
# The font stack: the console's own candidates in its order, then the generic family.
#   Unit [string]
CONST_UI_FONT = ','.join(["'%s'" % name for name in Style.CONST_FONT_UI_CANDIDATES] + ['sans-serif'])
# The indentation of one nesting level in the written SVG.
#   Unit [string]
CONST_INDENT = '  '


class Svg_Writer_Cls(object):
    """
    Description:
        An SVG document written line by line, indented by nesting, with the few primitives the
        diagram is made of: text, cards, arrows and the partner marks. Every colour a caller
        passes is a Theme token.

    Initialization of the Class:
        Example:
            Initialization:
                # Initialization of the class.
                Cls = Svg_Writer_Cls()

            Features:
                # Functions of the class.
                Cls.Open('<g id="x">', 'a comment'); Cls.Text(...); Cls.Close('g')
                Cls.Markup()
    """

    def __init__(self) -> None:
        # << PRIVATE >> #
        self.__lines = []
        self.__depth = 0

    def Add(self, element: str) -> None:
        """
        Description:
            Append one line of markup at the current depth.

        Args:
            (1) element [string]: The markup.
        """

        self.__lines.append(CONST_INDENT * self.__depth + element)

    def Raw(self, markup: str) -> None:
        """
        Description:
            Append markup exactly as given, unindented (the inline logo must stay byte for byte).

        Args:
            (1) markup [string]: The markup.
        """

        self.__lines.append(markup)

    def Blank(self) -> None:
        """
        Description:
            An empty line between blocks.
        """

        self.__lines.append('')

    def Open(self, tag: str, comment: tp.Optional[str] = None) -> None:
        """
        Description:
            Open an element that holds others, with an optional comment above it.

        Args:
            (1) tag [string]: The opening tag.
            (2) comment [string]: The comment, or None.
        """

        if comment is not None:
            self.Add('<!-- %s -->' % comment)
        self.Add(tag)
        self.__depth += 1

    def Close(self, name: str) -> None:
        """
        Description:
            Close the innermost open element.

        Args:
            (1) name [string]: The element's name.
        """

        self.__depth -= 1
        self.Add('</%s>' % name)

    def Markup(self) -> str:
        """
        Description:
            The document so far.

        Returns:
            (1) parameter [string]: The SVG text, with a trailing newline.
        """

        return '\n'.join(self.__lines) + '\n'

    def Text(self, x: float, y: float, text: str, size: float, fill: str, weight: tp.Optional[str] = None,
             anchor: tp.Optional[str] = None, spacing: tp.Optional[str] = None) -> None:
        """
        Description:
            One line of text in the UI face.

        Args:
            (1 - 2) x, y [float]: The baseline position.
            (3) text [string]: The text (escaped here).
            (4) size [float]: The font size, a step of CONST_SCALE.
            (5) fill [string]: A Theme colour token.
            (6) weight [string]: The font weight, or None for regular.
            (7) anchor [string]: 'middle' or 'end', or None for start.
            (8) spacing [string]: The letter spacing, or None.
        """

        attributes = ''.join([' font-weight="%s"' % weight if weight else '',
                              ' text-anchor="%s"' % anchor if anchor else '',
                              ' letter-spacing="%s"' % spacing if spacing else ''])
        self.Add('<text x="%g" y="%g" font-size="%g" fill="%s"%s>%s</text>'
                 % (x, y, size, fill, attributes, escape(text)))

    def Rect(self, x: float, y: float, w: float, h: float, fill: str, stroke: tp.Optional[str] = None,
             rx: float = 14, dash: tp.Optional[str] = None) -> None:
        """
        Description:
            A rounded rectangle.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) fill [string]: A Theme colour token, or 'none'.
            (6) stroke [string]: A Theme colour token for the outline, or None for none.
            (7) rx [float]: The corner radius.
            (8) dash [string]: The outline's dash pattern, or None for solid.
        """

        attributes = ' stroke="%s" stroke-width="1.5"' % stroke if stroke else ''
        attributes += ' stroke-dasharray="%s"' % dash if dash else ''
        self.Add('<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="%s"%s/>'
                 % (x, y, w, h, rx, fill, attributes))

    def Arrow(self, x1: float, y: float, x2: float) -> None:
        """
        Description:
            A horizontal arrow, in the direction the frame flows.

        Args:
            (1) x1 [float]: The tail.
            (2) y [float]: The height.
            (3) x2 [float]: The head.
        """

        self.Add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="2.5" stroke-linecap="round" '
                 'marker-end="url(#arch-tip)"/>' % (x1, y, x2, y, Theme.CONST_INK_SOFT))

    def Connector(self, x: float, y1: float, y2: float) -> None:
        """
        Description:
            A dashed vertical line from the configuration up to what it sets.

        Args:
            (1) x [float]: The position.
            (2 - 3) y1, y2 [float]: The ends.
        """

        self.Add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.5" stroke-dasharray="4 5"/>'
                 % (x, y1, x, y2, Theme.CONST_INK_MUTE))

    def Image(self, x: float, y: float, h: float, path: str, label: str) -> None:
        """
        Description:
            A PNG mark embedded as base64 data, drawn at a height with its own aspect ratio.

        Args:
            (1 - 2) x, y [float]: The top-left corner.
            (3) h [float]: The drawn height.
            (4) path [string]: The PNG file.
            (5) label [string]: What the mark is, for screen readers.
        """

        w, h_px = Png_Size(path)
        with open(path, 'rb') as handle:
            data = base64.b64encode(handle.read()).decode('ascii')
        self.Add('<image x="%g" y="%g" width="%g" height="%g" aria-label="%s" href="data:image/png;base64,%s"/>'
                 % (x, y, round(h * w / h_px, 1), h, escape(label), data))

    def Card(self, x: float, y: float, w: float, h: float, title: str, lines: tp.List[str],
             dark: bool = False) -> None:
        """
        Description:
            A block: a card with a bold title and up to three lines under it, centred vertically.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) title [string]: The block's name.
            (6) lines [List<string>]: What it does, one short line each.
            (7) dark [bool]: The indigo viewport surface instead of a white card.
        """

        S = CONST_SCALE
        if dark:
            self.Rect(x, y, w, h, Theme.CONST_VIEWPORT)
        else:
            self.Rect(x, y, w, h, Theme.CONST_CARD, Theme.CONST_CARD_BORDER)
        # The text block runs from the title's cap height (~22 above its baseline) to the last
        # line's descender (~6 below its baseline).
        top = y + (h - (22 + 30 + 24 * (len(lines) - 1) + 6)) / 2 + 22
        self.Text(x + 24, top, title, S[6], Theme.CONST_ON_INK if dark else Theme.CONST_INK, weight='700')
        for i, line in enumerate(lines):
            self.Text(x + 24, top + 30 + 24 * i, line, S[3],
                      Theme.CONST_VIEWPORT_TEXT if dark else Theme.CONST_INK_SOFT)


def Png_Size(path: str) -> tp.Tuple[int, int]:
    """
    Description:
        A PNG's pixel size, read from its IHDR chunk (no imaging library needed).

    Args:
        (1) path [string]: The PNG file.

    Returns:
        (1) parameter [Tuple<int> 1x2]: (width, height) in pixels.
    """

    with open(path, 'rb') as handle:
        head = handle.read(24)
    return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')


def Split_In_Two(text: str) -> tp.List[str]:
    """
    Description:
        A sentence broken into two lines at the space nearest its middle.

    Args:
        (1) text [string]: The text.

    Returns:
        (1) parameter [List<string>]: The two lines.
    """

    spaces = [i for i, character in enumerate(text) if character == ' ']
    cut = min(spaces, key=lambda i: abs(i - len(text) / 2))
    return [text[:cut], text[cut + 1:]]


def Draw_Architecture(logo_svg: str) -> str:
    """
    Description:
        The whole diagram: the header (the AnyScan logo and the JIC mark) and the tagline; the
        flow left to right — capture, find the objects, describe and measure each one, the
        desktop application; the configuration under the stages it sets; and the console's
        funding band (the EDIH-DIGIMAT, Ministry and EU logos and the EU disclaimer). Everything drawn is in the code; nothing is planned.

    Args:
        (1) logo_svg [string]: The content of images/anyscan-logo.svg, inlined unchanged.

    Returns:
        (1) parameter [string]: The SVG document.
    """

    S = CONST_SCALE; T = Theme
    c = Svg_Writer_Cls()
    c.Open('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
           'aria-label="AnyScan architecture">' % (CONST_WIDTH, CONST_HEIGHT, CONST_WIDTH, CONST_HEIGHT))
    c.Add('<!-- Generated by Example/UI/architecture_diagram.py; regenerate, do not edit by hand. -->')
    c.Add('<title>AnyScan architecture</title>')
    c.Add('<desc>AnyScan finds the objects in a camera frame, describes each one in words, and measures it in '
          'mm. A Basler camera captures a frame; FastSAM and background subtraction find the objects and are '
          'fused, so an object is kept if either finds it; each object is described by a local '
          'vision-language model and, when the camera is calibrated, measured in millimetres; the PyQt5 '
          'desktop application shows the result in its Live, Trends, History and Log views. One YAML '
          'configuration per camera and mode sets the stages up. Built at JIC within the EDIH-DIGIMAT '
          'project, funded by the European Union.</desc>')
    c.Blank()
    c.Open('<defs>')
    c.Open('<style>')
    c.Add('text { font-family: %s; }' % CONST_UI_FONT)
    c.Add('.logo-slot svg { overflow: visible; }')
    c.Close('style')
    c.Open('<marker id="arch-tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
           'orient="auto">')
    c.Add('<path d="M1 1 L9 5 L1 9" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" '
          'stroke-linejoin="round"/>' % T.CONST_INK_SOFT)
    c.Close('marker')
    c.Close('defs')
    c.Blank()

    c.Add('<!-- The card: opaque, so the figure reads the same on a light or a dark README. -->')
    c.Rect(0.75, 0.75, CONST_WIDTH - 1.5, CONST_HEIGHT - 1.5, T.CONST_BG, T.CONST_CARD_BORDER, rx=20)
    c.Blank()

    # The header, as the console's top bar: the lockup, a divider, the JIC mark.
    c.Open('<g id="header">', 'Header: the AnyScan logo (its own palette, which predates the theme), '
           'a divider and the JIC mark, as in the top bar')
    c.Open('<g class="logo-slot" transform="translate(40,34) scale(0.4)">')
    c.Raw(CONST_LOGO_BEGIN)
    c.Raw(logo_svg.strip())
    c.Raw(CONST_LOGO_END)
    c.Close('g')
    c.Add('<line x1="500" y1="44" x2="500" y2="96" stroke="%s" stroke-width="1.5"/>' % T.CONST_TOPBAR_DIVIDER)
    c.Image(524, 53, 34, CONST_JIC_FILE, 'JIC')
    c.Text(1160, 76, 'ARCHITECTURE', S[2], T.CONST_INK_MUTE, weight='700', anchor='end', spacing='2')
    c.Close('g')
    c.Blank()

    c.Open('<g id="tagline">', 'Tagline')
    c.Add('<line x1="40" y1="126" x2="1160" y2="126" stroke="%s" stroke-width="1.5"/>' % T.CONST_CARD_BORDER)
    c.Text(40, 168, 'AnyScan finds the objects in a camera frame, describes each one in words, and measures it in mm.',
           S[5], T.CONST_INK, weight='500')
    c.Close('g')
    c.Blank()

    # The flow: four columns at one height; the arrows sit on the cards' middle line.
    y, h = 232, 224
    mid = y + h / 2
    c.Open('<g id="capture">', '1. Capture: the camera takes the frame')
    c.Card(40, y, 180, h, 'Capture', ['Basler camera', 'takes a frame'])
    c.Close('g')
    c.Arrow(226, mid, 258)
    c.Blank()

    c.Open('<g id="find">', '2. Find the objects: two cues, fused')
    c.Card(264, y, 250, h, 'Find objects', ['FastSAM + background', 'subtraction, fused:', 'kept if either finds it'])
    c.Close('g')
    c.Arrow(520, mid, 552)
    c.Blank()

    c.Open('<g id="each-object">', '3. Each object: described and measured, marked like an object on the frame')
    c.Rect(558, y - 20, 290, h + 40, 'none', T.CONST_SCROLLBAR_HANDLE, rx=18, dash='6 6')
    c.Rect(578, y - 34, 124, 28, T.CONST_BRAND, rx=6)
    c.Text(640, y - 14, 'each object', S[2], T.CONST_ON_INK, weight='700', anchor='middle')
    c.Card(574, y + 4, 258, 104, 'Describe', ['local vision-language', 'model (Gemma 4)'])
    c.Card(574, y + h - 108, 258, 104, 'Measure', ['size in mm, when', 'the camera is calibrated'])
    c.Close('g')
    c.Arrow(854, mid, 886)
    c.Blank()

    c.Open('<g id="application">', '4. The desktop application and its four views')
    c.Rect(892, y, 268, h, T.CONST_VIEWPORT)
    c.Text(916, y + 60, 'Desktop app', S[6], T.CONST_ON_INK, weight='700')
    c.Text(916, y + 88, 'PyQt5', S[3], T.CONST_VIEWPORT_TEXT)
    for i, view in enumerate(['Live', 'Trends', 'History', 'Log']):
        x_view, y_view = 916 + 114 * (i % 2), y + 114 + 44 * (i // 2)
        c.Rect(x_view, y_view, 106, 34, T.CONST_INK_HOVER, T.CONST_BAND_LINE, rx=8)
        c.Text(x_view + 53, y_view + 23, view, S[2], T.CONST_ON_INK, weight='600', anchor='middle')
    c.Close('g')
    c.Blank()

    c.Open('<g id="configuration">', 'The configuration, and the stages it sets up')
    for x in (130, 389, 703):
        c.Connector(x, 520, y + h + (20 if x == 703 else 0) + 4)
    c.Rect(40, 520, 808, 84, T.CONST_CARD, T.CONST_CARD_BORDER)
    c.Text(64, 554, 'Configuration', S[6], T.CONST_INK, weight='700')
    c.Text(64, 582, 'one YAML file per camera and mode sets up every stage', S[3], T.CONST_INK_SOFT)
    c.Close('g')
    c.Blank()

    c.Open('<g id="funding-band">', 'The funding band, as in the console: the logos in its order, a hairline, '
           'the EU disclaimer')
    c.Add('<path d="M0.75 %g H1199.25 V%g A20 20 0 0 1 1179.25 %g H20.75 A20 20 0 0 1 0.75 %g Z" fill="%s"/>'
          % (CONST_BAND_TOP, CONST_HEIGHT - 20.75, CONST_HEIGHT - 0.75, CONST_HEIGHT - 20.75, T.CONST_BAND))
    # The row is centred like the console's (stretch on both sides); None is its hairline divider.
    row = []
    for name, height in Funding_Row_Cls.LOGOS:
        if name is None:
            row.append((None, 0.0, 30 * CONST_BAND_SCALE))
            continue
        w, h_px = Png_Size(os.path.join(CONST_ASSETS_FOLDER, name))
        row.append((name, height * CONST_BAND_SCALE * w / h_px, height * CONST_BAND_SCALE))
    x = (CONST_WIDTH - sum(w for _, w, _ in row) - CONST_BAND_GAP * (len(row) - 1)) / 2
    y_row = CONST_BAND_TOP + 44
    for name, w, h in row:
        if name is None:
            c.Add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="1.5"/>'
                  % (x, y_row - h / 2, x, y_row + h / 2, T.CONST_BAND_LINE))
        else:
            c.Image(round(x, 1), round(y_row - h / 2, 1), round(h, 1), os.path.join(CONST_ASSETS_FOLDER, name),
                    CONST_BAND_LABELS[name])
        x += w + CONST_BAND_GAP
    c.Add('<line x1="40" y1="%g" x2="1160" y2="%g" stroke="%s" stroke-width="1"/>'
          % (CONST_BAND_TOP + 92, CONST_BAND_TOP + 92, T.CONST_BAND_LINE))
    for i, line in enumerate(Split_In_Two(Funding_Row_Cls.DISCLAIMER)):
        c.Text(CONST_WIDTH / 2, CONST_BAND_TOP + 118 + 21 * i, line, S[1], T.CONST_BAND_TEXT, anchor='middle')
    c.Close('g')
    c.Close('svg')
    return c.Markup()


def main():
    """
    Description:
        Write images/anyscan-architecture.svg from the theme and the logos, or with --check report
        whether the committed file is stale.

            python Example/UI/architecture_diagram.py [--check]
    """

    parser = argparse.ArgumentParser(description='Generate the README architecture diagram.')
    parser.add_argument('--check', action='store_true',
                        help='do not write; exit 1 if the committed diagram differs from the output')
    args = parser.parse_args()

    with open(CONST_LOGO_FILE, 'r', encoding='utf-8') as handle:
        markup = Draw_Architecture(handle.read())
    if args.check:
        with open(CONST_DIAGRAM_FILE, 'r', encoding='utf-8') as handle:
            current = handle.read()
        if current != markup:
            print('[ERROR] %s is stale or was edited by hand; regenerate it with this script.' % CONST_DIAGRAM_FILE)
            return 1
        print('[INFO] %s is up to date.' % CONST_DIAGRAM_FILE)
        return 0
    with open(CONST_DIAGRAM_FILE, 'w', encoding='utf-8') as handle:
        handle.write(markup)
    print('[INFO] Wrote %s.' % CONST_DIAGRAM_FILE)
    return 0


if __name__ == '__main__':
    sys.exit(main())
