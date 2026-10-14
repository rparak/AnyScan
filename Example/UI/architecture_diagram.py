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
import re
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
    AnyScan is and how it works in its two modes, at the top level only — the camera, finding the
    objects, describing and measuring each one, the desktop application; what a catalogue mode adds
    (recognising its part, the checks its item defines, a verdict per object); the files that set
    the stages up (the mode, the station, the calibration, the catalogue item, the reference); and
    the records the application writes and reads back. No class, model or product names, no
    configuration fields, no check of one part; README > Detection logic has the detail. Each card
    carries a line icon from CONST_ICONS, drawn here, so the figure needs no icon set or its licence.

    Regenerating is the way to change it; the SVG is never edited by hand. Every colour comes
    from a Parameters/Theme.py token and every size from the console's type scale, so the
    figure moves with the theme instead of drifting from it. The SVG is self-contained, because
    the README shows it through <img>, and an SVG loaded that way never fetches another file:
    the AnyScan logo is copied in byte for byte from images/anyscan-logo.svg, the JIC Smart Factory
    logo from App/assets/, and the funding band's logos are embedded from App/assets/ as base64 PNG data. The band is the
    console's own (UI.Widgets.Funding_Row_Cls): the same logos, order and disclaimer.

    test/UI/test_brand_figures.py fails when the committed SVG is not this script's output, or
    draws a colour that is not a token.

        python Example/UI/architecture_diagram.py            # rewrite the SVG
        python Example/UI/architecture_diagram.py --check    # exit 1 if it is stale

    The layout is checked against FALLBACK font metrics (Helvetica Neue / Arial), which is
    what most README readers get: an <img> SVG cannot load Public Sans as a web font. A layout that
    only fits with Public Sans installed will overflow for them.
"""
# The source logo, the folder of the marks, the JIC Smart Factory logo, and the diagram this script writes.
#   Unit [string]
CONST_LOGO_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-logo.svg')
CONST_ASSETS_FOLDER = os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets')
CONST_JIC_FILE = os.path.join(CONST_ASSETS_FOLDER, 'jic-smart-factory.svg')
CONST_DIAGRAM_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-architecture.svg')
# The marker comments around the inline logo; the test reads the copy between them.
#   Unit [string]
CONST_LOGO_BEGIN = '<!-- logo:begin -->'
CONST_LOGO_END = '<!-- logo:end -->'
# The marker comments around the inline JIC Smart Factory logo, brand artwork in its own colour like the AnyScan logo.
#   Unit [string]
CONST_JIC_BEGIN = '<!-- jic:begin -->'
CONST_JIC_END = '<!-- jic:end -->'
# The drawing size in user units: wide, so it stays legible at README width (~900 px renders
# it at 0.75).
#   Unit [px]
CONST_WIDTH = 1200
CONST_HEIGHT = 1226
# The header's logo: its top-left corner and its scale (logo units -> diagram units). The divider and
# the JIC mark follow the top bar's rule (UI/Core.py): Style.CONST_MARK_GAP from ink to divider and
# from divider to ink, scaled from the bar's Style.CONST_LOGO_HEIGHT px lockup to this logo's height.
#   Unit [px] / [-]
CONST_LOGO_X = 40
CONST_LOGO_Y = 34
CONST_LOGO_SCALE = 0.5
# Where the delivered logo's ink ends inside its viewBox: 603.9 of 609.8 units (measured on a render), so the
# divider is spaced from the ink, as in the top bar.
#   Unit [logo units]
CONST_LOGO_RIGHT_MARGIN = 5.9
# The JIC Smart Factory logo's drawn height and top edge: the top bar's ratio to the AnyScan logo
# (UI/Core.py, CONST_JIC_LOGO_HEIGHT over Style.CONST_LOGO_HEIGHT), centred on the logo.
#   Unit [px]
CONST_JIC_HEIGHT = 33.7
CONST_JIC_Y = 52.2
# The header divider's stroke width.
#   Unit [px]
CONST_DIVIDER_WIDTH = 1.5
# The top edge of the group of what sets the stages up.
#   Unit [px]
CONST_SET_TOP = 792
# The card icons: drawn here, on a 24-unit grid, as line shapes in one stroke (no icon font, no
# third-party set, so no licence to carry). Each is a list of SVG shapes, stroked, never filled.
#   Unit [Dictionary<string, List<string>>]
CONST_ICONS = {
    'camera': ['<path d="M3 8 a2 2 0 0 1 2 -2 h2.5 l1.5 -2 h6 l1.5 2 h2.5 a2 2 0 0 1 2 2 v10 a2 2 0 0 1 -2 2 h-14 '
               'a2 2 0 0 1 -2 -2 Z"/>', '<circle cx="12" cy="13" r="3.5"/>'],
    'magnifier': ['<circle cx="10.5" cy="10.5" r="6.5"/>', '<path d="M15.5 15.5 L21 21"/>'],
    'text': ['<path d="M4 6 H20 M4 11 H20 M4 16 H14"/>', '<path d="M4 20 H10"/>'],
    'ruler': ['<rect x="2" y="8" width="20" height="8" rx="1.5"/>',
              '<path d="M6 8 V11 M10 8 V12.5 M14 8 V11 M18 8 V12.5"/>'],
    'window': ['<rect x="3" y="4" width="18" height="16" rx="2"/>', '<path d="M3 9 H21"/>',
               '<path d="M6.5 6.5 H6.6 M9 6.5 H9.1"/>'],
    'focus': ['<path d="M3 8 V5 a2 2 0 0 1 2 -2 H8 M16 3 H19 a2 2 0 0 1 2 2 V8 M21 16 V19 a2 2 0 0 1 -2 2 H16 '
              'M8 21 H5 a2 2 0 0 1 -2 -2 V16"/>', '<rect x="8" y="8" width="8" height="8" rx="1"/>'],
    'checklist': ['<path d="M3 6.5 L5 8.5 L8.5 5 M3 15.5 L5 17.5 L8.5 14"/>', '<path d="M12 7 H21 M12 16 H21"/>'],
    'badge': ['<path d="M12 3 L19 6 V11 c0 4.5 -3 8 -7 10 c-4 -2 -7 -5.5 -7 -10 V6 Z"/>',
              '<path d="M9 12 L11 14 L15 10"/>'],
    'gear': ['<circle cx="12" cy="12" r="3"/>',
             '<path d="M18.7 10 L21.4 10.5 L21.4 13.5 L18.7 14 L18.2 15.3 L19.7 17.6 L17.6 19.7'
             ' L15.3 18.2 L14 18.7 L13.5 21.4 L10.5 21.4 L10 18.7 L8.7 18.2 L6.4 19.7 L4.3 17.6'
             ' L5.8 15.3 L5.3 14 L2.6 13.5 L2.6 10.5 L5.3 10 L5.8 8.7 L4.3 6.4 L6.4 4.3 L8.7 5.8'
             ' L10 5.3 L10.5 2.6 L13.5 2.6 L14 5.3 L15.3 5.8 L17.6 4.3 L19.7 6.4 L18.2 8.7 Z"/>'],
    'station': ['<path d="M2 21 H22 M6 21 V3 H15 V6"/>', '<rect x="11.5" y="6" width="7" height="5" rx="1"/>',
                '<path d="M13.5 11 L13 13.5 H17 L16.5 11"/>'],
    'target': ['<circle cx="12" cy="12" r="8"/>', '<circle cx="12" cy="12" r="3.5"/>',
               '<path d="M12 1.5 V5 M12 19 V22.5 M1.5 12 H5 M19 12 H22.5"/>'],
    'catalogue': ['<path d="M12 6.5 C10 5 7 4.5 3 5 V19 C7 18.5 10 19 12 20.5 C14 19 17 18.5 21 19 V5 '
                  'C17 4.5 14 5 12 6.5 Z"/>', '<path d="M12 6.5 V20.5"/>'],
    'image': ['<rect x="3" y="4" width="18" height="16" rx="2"/>', '<circle cx="8.5" cy="9.5" r="1.5"/>',
              '<path d="M21 16 L16 11 L6 20"/>'],
    'folder': ['<path d="M3 7 a2 2 0 0 1 2 -2 h4 l2 2.5 h8 a2 2 0 0 1 2 2 V18 a2 2 0 0 1 -2 2 H5 a2 2 0 0 1 -2 -2 Z"/>'],
}
# The icon's drawn size, its stroke on the 24-unit grid (2 px drawn), and its inset from a card's
# right edge; it is centred on the title's capitals.
#   Unit [px]
CONST_ICON_SIZE = 28
CONST_ICON_STROKE = 1.75
CONST_ICON_INSET = 18
# The funding band: its top edge, the console's per-logo heights scaled by this factor (the
# heights are tuned per logo there, so they are scaled, never replaced), and the gap between logos.
#   Unit [px] / [-]
CONST_BAND_TOP = 1072
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
             dash: tp.Optional[str] = None) -> None:
        """
        Description:
            A rectangle, square-cornered as the console's cards and controls are.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) fill [string]: A Theme colour token, or 'none'.
            (6) stroke [string]: A Theme colour token for the outline, or None for none.
            (7) dash [string]: The outline's dash pattern, or None for solid.
        """

        attributes = ' stroke="%s" stroke-width="1.5"' % stroke if stroke else ''
        attributes += ' stroke-dasharray="%s"' % dash if dash else ''
        self.Add('<rect x="%g" y="%g" width="%g" height="%g" fill="%s"%s/>' % (x, y, w, h, fill, attributes))

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

    def Elbow(self, points: tp.List[tp.Tuple[float, float]]) -> None:
        """
        Description:
            An arrow along straight segments at right angles, drawn like Arrow.

        Args:
            (1) points [List<Tuple<float> 1x2>]: The tail, the corners and the head.
        """

        d = ' '.join(('M%g %g' if i == 0 else 'L%g %g') % point for i, point in enumerate(points))
        self.Add('<path d="%s" fill="none" stroke="%s" stroke-width="2.5" stroke-linecap="round" '
                 'stroke-linejoin="round" marker-end="url(#arch-tip)"/>' % (d, Theme.CONST_INK_SOFT))

    def Icon(self, x: float, y: float, name: str, color: str) -> None:
        """
        Description:
            One of CONST_ICONS, CONST_ICON_SIZE square, stroked in a Theme colour.

        Args:
            (1 - 2) x, y [float]: The top-left corner.
            (3) name [string]: The key in CONST_ICONS.
            (4) color [string]: A Theme colour token.
        """

        self.Open('<g transform="translate(%g,%g) scale(%g)" fill="none" stroke="%s" stroke-width="%g" '
                  'stroke-linecap="round" stroke-linejoin="round">'
                  % (x, y, CONST_ICON_SIZE / 24, color, CONST_ICON_STROKE))
        for shape in CONST_ICONS[name]:
            self.Add(shape)
        self.Close('g')

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
             icon: tp.Optional[str] = None) -> None:
        """
        Description:
            A block: a card with a bold title and up to three lines under it, centred vertically.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) title [string]: The block's name.
            (6) lines [List<string>]: What it does, one short line each.
            (7) icon [string]: The key in CONST_ICONS drawn in the top-right corner, or None.
        """

        S = CONST_SCALE
        self.Rect(x, y, w, h, Theme.CONST_CARD, Theme.CONST_CARD_BORDER)
        # The text block runs from the title's cap height (~22 above its baseline) to the last
        # line's descender (~6 below its baseline).
        top = y + (h - (22 + 30 + 24 * (len(lines) - 1) + 6)) / 2 + 22
        if icon is not None:
            self.Icon(x + w - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top), icon,
                      Theme.CONST_INK_SOFT)
        self.Text(x + 24, top, title, S[6], Theme.CONST_INK, weight='700')
        for i, line in enumerate(lines):
            self.Text(x + 24, top + 30 + 24 * i, line, S[3], Theme.CONST_INK_SOFT)


def Icon_Top(baseline: float) -> float:
    """
    Description:
        The top of a card's icon, centred on its title's capitals (~8 above the baseline, in S[6]).

    Args:
        (1) baseline [float]: The title's baseline.

    Returns:
        (1) parameter [float]: The icon's top edge.
    """

    return baseline - 8 - CONST_ICON_SIZE / 2


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


def Header_Positions(logo_svg: str) -> tp.Tuple[float, float]:
    """
    Description:
        Where the header's divider and JIC mark go, by the top bar's rule: Style.CONST_MARK_GAP from
        the logo's rightmost ink to the divider's edge, and from its other edge to the JIC mark (whose
        PNG has no transparent margin), scaled from the bar's lockup height to this logo's. The ink
        ends CONST_LOGO_MARGIN inside the logo's viewBox, which build_logo.py fits to the ink.

    Args:
        (1) logo_svg [string]: The content of images/anyscan-logo.svg.

    Returns:
        (1) parameter [Vector<float> 1x2]: The divider's x (its centre line) and the JIC mark's x.
    """

    _, _, view_w, view_h = (float(v) for v in re.search(r'viewBox="([^"]+)"', logo_svg).group(1).split())
    ink_right = CONST_LOGO_X + CONST_LOGO_SCALE * (view_w - CONST_LOGO_RIGHT_MARGIN)
    gap = Style.CONST_MARK_GAP * CONST_LOGO_SCALE * view_h / Style.CONST_LOGO_HEIGHT
    divider = ink_right + gap + CONST_DIVIDER_WIDTH / 2
    return round(divider, 2), round(divider + CONST_DIVIDER_WIDTH / 2 + gap, 2)


def Draw_Architecture(logo_svg: str) -> str:
    """
    Description:
        The whole diagram: the header (the AnyScan logo and the JIC mark) and the tagline; the
        flow left to right — capture, find the objects, describe and measure each one, the
        desktop application; under it what a catalogue mode adds for each object — recognise,
        check, the verdict; the mode, station, calibration, catalogue item and reference that set
        the stages up, and the records under the application that writes them; and the console's
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
    c.Add('<!-- Generated by Example/UI/architecture_diagram.py. Regenerate it, do not edit it by hand. -->')
    c.Add('<title>AnyScan architecture</title>')
    c.Add('<desc>AnyScan finds every object on a work surface, describes it and measures it. A catalogue mode '
          'also judges it. In every mode the camera takes a frame and undistorts it. Two cues, fused, find the '
          'objects: what differs from the empty surface, and a segmentation model. Each object is described in '
          'words by a local vision-language model and measured in mm through the calibration, and the desktop '
          'application shows the result in its Live, Trends, History and Log views. A catalogue mode adds three '
          'steps for each object found: recognising the catalogued part and the side that is up by its reference '
          'images, the checks its catalogue item defines, which differ from item to item, and a verdict: OK, NOK, '
          'Warning or Unspecified. In a catalogue mode each object is described after its verdict. The stages are '
          'set up by the mode (models and prompts), which names its station (camera, light and table). The '
          'station names its calibration (undistortion and mm per pixel) and the empty-surface reference, and a '
          'catalogue mode also names its catalogue item (the part, its checks and its reference images). Every '
          'analysis is recorded with its images and results, alongside the session log, a run summary and the '
          'daily station events. Built at JIC within the EDIH-DIGIMAT project, funded by the European Union.</desc>')
    c.Blank()
    c.Open('<defs>')
    c.Open('<style>')
    c.Add('text { font-family: %s; }' % CONST_UI_FONT)
    c.Close('style')
    c.Open('<marker id="arch-tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" '
           'orient="auto">')
    c.Add('<path d="M1 1 L9 5 L1 9" fill="none" stroke="%s" stroke-width="2" stroke-linecap="round" '
          'stroke-linejoin="round"/>' % T.CONST_INK_SOFT)
    c.Close('marker')
    c.Close('defs')
    c.Blank()

    c.Add('<!-- The card: opaque, so the figure reads the same on a light or a dark README. -->')
    c.Rect(0.75, 0.75, CONST_WIDTH - 1.5, CONST_HEIGHT - 1.5, T.CONST_BG, T.CONST_CARD_BORDER)
    c.Blank()

    # The header, as the console's top bar: the lockup, a divider, the JIC mark.
    c.Open('<g id="header">', 'Header: the AnyScan logo (its own palette, which predates the theme), '
           'a divider and the JIC mark, as in the top bar')
    c.Open('<g class="logo-slot" transform="translate(%g,%g) scale(%g)">' % (CONST_LOGO_X, CONST_LOGO_Y, CONST_LOGO_SCALE))
    c.Raw(CONST_LOGO_BEGIN)
    c.Raw(logo_svg.strip())
    c.Raw(CONST_LOGO_END)
    c.Close('g')
    divider_x, jic_x = Header_Positions(logo_svg)
    c.Add('<line x1="%g" y1="44" x2="%g" y2="96" stroke="%s" stroke-width="%g"/>'
          % (divider_x, divider_x, T.CONST_TOPBAR_DIVIDER, CONST_DIVIDER_WIDTH))
    with open(CONST_JIC_FILE, 'r', encoding='utf-8') as handle:
        jic = re.sub(r'<\?xml[^>]*>\s*', '', handle.read()).strip()
    _, _, jic_w, jic_h = (float(v) for v in re.search(r'viewBox="([^"]+)"', jic).group(1).split())
    c.Raw(CONST_JIC_BEGIN)
    c.Raw(jic.replace('<svg ', '<svg x="%g" y="%g" width="%g" height="%g" ' % (jic_x, CONST_JIC_Y, round(CONST_JIC_HEIGHT * jic_w / jic_h, 1),
                                                                               CONST_JIC_HEIGHT), 1))
    c.Raw(CONST_JIC_END)
    c.Text(1160, 76, 'ARCHITECTURE', S[2], T.CONST_INK_MUTE, weight='700', anchor='end', spacing='2')
    c.Close('g')
    c.Blank()

    c.Open('<g id="tagline">', 'Tagline')
    c.Add('<line x1="40" y1="126" x2="1160" y2="126" stroke="%s" stroke-width="1.5"/>' % T.CONST_CARD_BORDER)
    c.Text(40, 168, 'AnyScan finds every object on a work surface, describes it and measures it. A catalogue mode also judges it.',
           S[5], T.CONST_INK, weight='500')
    c.Close('g')
    c.Blank()

    # Every mode: four columns at one height; the arrows sit on the cards' middle line.
    y, h = 232, 224
    mid = y + h / 2
    c.Open('<g id="capture">', '1. Capture: the camera takes the frame')
    c.Card(40, y, 180, h, 'Capture', ['the camera', 'takes a frame and', 'undistorts it'], icon='camera')
    c.Close('g')
    c.Arrow(226, mid, 258)
    c.Blank()

    c.Open('<g id="find">', '2. Find the objects: two cues, fused')
    c.Card(264, y, 250, h, 'Find objects', ['two cues, fused: what', 'differs from the empty', 'surface, and a', 'segmentation model'],
           icon='magnifier')
    c.Close('g')
    c.Arrow(520, mid, 552)
    c.Blank()

    c.Open('<g id="each-object">', '3. Each object: described and measured')
    c.Rect(558, y - 20, 290, h + 40, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    c.Rect(578, y - 34, 124, 28, T.CONST_BRAND)
    c.Text(640, y - 14, 'each object', S[2], T.CONST_ON_INK, weight='700', anchor='middle')
    c.Card(574, y + 4, 258, 104, 'Describe', ['in words, by a local', 'vision-language model'], icon='text')
    c.Card(574, y + h - 108, 258, 104, 'Measure', ['size in mm, through', 'the calibration'], icon='ruler')
    c.Close('g')
    c.Arrow(854, mid, 886)
    c.Blank()

    # What a catalogue mode adds, for each object, in a group marked like 'each object'.
    y_cat, h_cat = 546, 150
    mid_cat = y_cat + h_cat / 2
    c.Open('<g id="catalogue">', '4. A catalogue mode also recognises its part, checks it and gives each object a verdict')
    # Every object found goes on to these steps: down from Find objects, over, and into Recognise.
    c.Elbow([(389, y + h + 6), (389, y + h + 33), (172, y + h + 33), (172, y_cat - 6)])
    c.Rect(40, y_cat - 20, 808, h_cat + 68, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    c.Rect(214, y_cat - 34, 320, 28, T.CONST_BRAND)
    c.Text(374, y_cat - 14, 'catalogue mode adds, for each object', S[2], T.CONST_ON_INK, weight='700', anchor='middle')
    c.Card(56, y_cat, 232, h_cat, 'Recognise', ['the catalogued part and', 'the side that is up, by', 'its reference images'],
           icon='focus')
    c.Arrow(294, mid_cat, 328)
    c.Card(334, y_cat, 208, h_cat, 'Check', ['the checks its item', 'defines, which differ', 'from item to item'],
           icon='checklist')
    c.Arrow(548, mid_cat, 582)
    # The four verdicts, each a label in the purple on its verdict's ground, as the console's badge, two to a row.
    c.Rect(588, y_cat, 244, h_cat, T.CONST_CARD, T.CONST_CARD_BORDER)
    c.Text(612, y_cat + 42, 'Verdict', S[6], T.CONST_INK, weight='700')
    c.Icon(832 - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(y_cat + 42), 'badge', T.CONST_INK_SOFT)
    for i, (verdict, x_chip, w_chip) in enumerate([('OK', 612, 64), ('NOK', 684, 72), ('Warning', 612, 82),
                                                   ('Unspecified', 702, 108)]):
        y_chip = y_cat + 62 + 40 * (i // 2)
        c.Rect(x_chip, y_chip, w_chip, 30, T.Label_Ground(verdict))
        c.Text(x_chip + w_chip / 2, y_chip + 21, verdict, S[2], T.CONST_INK, weight='700', anchor='middle')
    c.Arrow(854, mid_cat, 886)
    # In a catalogue mode the description comes last: it is written with what the checks found.
    c.Text(832, y_cat + h_cat + 32, 'In this mode each object is described after its verdict.', S[2],
           T.CONST_INK_MUTE, anchor='end')
    c.Close('g')
    c.Blank()

    c.Open('<g id="application">', '5. The desktop application and its four views')
    h_app = y_cat + h_cat + 48 - y
    c.Rect(892, y, 268, h_app, T.CONST_VIEWPORT)
    top = y + (h_app - 250) / 2 + 22
    c.Text(916, top, 'Desktop app', S[6], T.CONST_VIEWPORT_TEXT, weight='700')
    c.Icon(1160 - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top), 'window', T.CONST_VIEWPORT_TEXT)
    for i, line in enumerate(['shows each object, its', 'description and size,', 'and, in a catalogue', 'mode, its verdict']):
        c.Text(916, top + 30 + 24 * i, line, S[3], T.CONST_VIEWPORT_TEXT)
    for i, view in enumerate(['Live', 'Trends', 'History', 'Log']):
        x_view, y_view = 916 + 114 * (i % 2), top + 140 + 44 * (i // 2)
        c.Rect(x_view, y_view, 106, 34, T.CONST_CARD, T.CONST_INK)
        c.Text(x_view + 53, y_view + 23, view, S[2], T.CONST_INK, weight='600', anchor='middle')
    c.Close('g')
    c.Blank()

    # What sets the stages up, as cards in a group marked like 'each object': the mode names its
    # station and any catalogue item, the station its calibration and the empty-surface reference.
    y_set, h_set = CONST_SET_TOP, 240
    c.Open('<g id="set-up">', 'What sets the stages up: the mode, the station, the calibration, the catalogue item, '
           'the reference')
    c.Rect(40, y_set, 808, h_set, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    c.Rect(60, y_set - 14, 104, 28, T.CONST_BRAND)
    c.Text(112, y_set + 6, 'set up by', S[2], T.CONST_ON_INK, weight='700', anchor='middle')
    for i, (title, lines, icon) in enumerate([('Mode', ['models and prompts,', 'and its station'], 'gear'),
                                              ('Station', ['camera, light, table,', 'and its calibration'], 'station'),
                                              ('Calibration', ['undistortion and', 'mm per pixel'], 'target')]):
        c.Card(56 + 262 * i, y_set + 22, 252, 96, title, lines, icon=icon)
    for i, (title, lines, icon) in enumerate([('Catalogue item', ['named by a catalogue mode: the',
                                                                  'part, its checks, reference images'], 'catalogue'),
                                              ('Reference', ['named by the station: the empty',
                                                             'surface each frame is compared with'], 'image')]):
        c.Card(56 + 393 * i, y_set + 128, 383, 96, title, lines, icon=icon)
    c.Close('g')
    c.Blank()

    c.Open('<g id="records">', 'What the application writes and reads back')
    c.Connector(1026, y_set, y + h_app + 4)
    c.Card(892, y_set, 268, h_set, 'Records', ['images and results', 'of every analysis,', 'the session log,',
                                                   'a run summary and', 'daily station events'], icon='folder')
    c.Close('g')
    c.Blank()

    c.Open('<g id="funding-band">', 'The funding band, as in the console: the logos in its order, a hairline, '
           'the EU disclaimer')
    c.Add('<rect x="0.75" y="%g" width="1198.5" height="%g" fill="%s"/>' % (CONST_BAND_TOP, CONST_HEIGHT - 0.75 - CONST_BAND_TOP, T.CONST_BAND))
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
