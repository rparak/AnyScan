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
# Custom Lib.: AnyScan UI — the band's pixel motif and the pixel icons the application draws too (Qt-free)
#   ../../src/UI/Utilities/Pixel_Motif
from UI.Utilities.Pixel_Motif import Motif_Cells, Icon_Cells, CONST_ICON_GRID

"""
Description:
    Initialization of constants.

    The generator of images/anyscan-architecture.svg, the diagram the README opens with: what
    AnyScan is and how it works in its two modes, at the top level only — the camera (a live preview,
    then a fresh frame once nothing moves), finding the objects, describing and measuring each one, the
    desktop application; what a catalogue mode adds (recognising its part, the inspection area that
    decides which parts are judged and tells a part outside it from a foreign object, the kinds of check
    an item can define on the side that is up, a state per object, and a description held to the
    checks); the files that set the stages up (the mode names the station, the station the calibration,
    and the catalogue item and the reference); and the records the application writes and reads back. No
    class, model or product names, no configuration fields, no number; README > Detection logic and
    SPEC.md have the detail. Each card
    carries a pixel icon from the application's own set (UI.Utilities.Pixel_Motif.CONST_PIXEL_ICONS), so the figure
    and the console never draw two versions of one icon, and the figure needs no icon set or its licence.

    Regenerating is the way to change it; the SVG is never edited by hand. Every colour comes
    from a Parameters/Theme.py token and every size from the console's type scale, so the
    figure moves with the theme instead of drifting from it. The SVG is self-contained, because
    the README shows it through <img>, and an SVG loaded that way never fetches another file:
    the AnyScan logo is copied in byte for byte from images/anyscan-logo.svg, the JIC Smart Factory
    logo from App/assets/, and the funding band's traced logos are inlined from App/assets/. The band is the
    console's own (UI.Widgets.Funding_Row_Cls): the same logos, heights (scaled), order, opacities and disclaimer.

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
# The README's funding logo row: the console's funding band, drawn as an SVG.
CONST_FUNDING_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-funding.svg')
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
CONST_HEIGHT = 1425
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
CONST_SET_TOP = 938
# The icon's drawn size (12 cells of 3 px: at the earlier 28 px line icons' size a cell would be 2.33 px and the grid
# would smear) and its inset from a card's right edge; it is centred on the title's capitals.
#   Unit [px]
CONST_ICON_SIZE = 36
CONST_ICON_INSET = 16
# The funding band: its top edge, the console's per-logo heights scaled by this factor (the
# heights are tuned per logo there, so they are scaled, never replaced), and the gap between logos.
#   Unit [px] / [-]
CONST_BAND_TOP = 1242
CONST_BAND_SCALE = 1.35
CONST_BAND_GAP = 36
# The band's inner space: above the logos, and from the logos to the rule under them.
#   Unit [px]
CONST_BAND_PAD = 20
# What each band logo is, for screen readers.
#   Unit [Dictionary<string, string>]
CONST_BAND_LABELS = {'edih-digimat-white.svg': 'EDIH-DIGIMAT',
                     'partner-ministry-white.svg': 'Ministry of Industry and Trade of the Czech Republic',
                     'funder-eu-white.svg': 'Funded by the European Union'}
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
             anchor: tp.Optional[str] = None, spacing: tp.Optional[str] = None, opacity: float = 1.0) -> None:
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
            (9) opacity [float]: The fill's opacity, 0..1.
        """

        attributes = ''.join([' font-weight="%s"' % weight if weight else '',
                              ' text-anchor="%s"' % anchor if anchor else '',
                              ' letter-spacing="%s"' % spacing if spacing else '',
                              ' fill-opacity="%g"' % opacity if opacity != 1.0 else ''])
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
            A pixel icon of the shared set (Pixel_Motif.Icon_Cells), CONST_ICON_SIZE square, in a Theme colour: one
            filled path of the grid's squares, drawn with crisp edges so neighbouring squares meet without a seam.

        Args:
            (1 - 2) x, y [float]: The top-left corner.
            (3) name [string]: The key in Pixel_Motif.CONST_PIXEL_ICONS.
            (4) color [string]: A Theme colour token.
        """

        cell = CONST_ICON_SIZE / CONST_ICON_GRID
        squares = ['M%g %g h%g v%g h-%g Z' % (round(x + column * cell, 2), round(y + row * cell, 2), cell, cell, cell)
                   for column, row in Icon_Cells(name)]
        self.Add('<path d="%s" fill="%s" shape-rendering="crispEdges"/>' % (' '.join(squares), color))

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

    def Svg_Logo(self, x: float, y: float, h: float, path: str, label: str) -> None:
        """
        Description:
            An SVG logo inlined as a nested <svg>, drawn at a height with its viewBox's aspect ratio.

        Args:
            (1) x, y [float]: The top-left corner.
            (3) h [float]: The drawn height.
            (4) path [string]: The SVG file.
            (5) label [string]: What the logo is, for screen readers.
        """

        w, h_box = Svg_Size(path)
        self.Raw(Svg_Body(path).replace('<svg ', '<svg x="%g" y="%g" width="%g" height="%g" role="img" aria-label="%s" '
                                        % (x, y, round(h * w / h_box, 1), h, escape(label)), 1))

    def Card(self, x: float, y: float, w: float, h: float, title: str, lines: tp.List[str],
             icon: tp.Optional[str] = None) -> None:
        """
        Description:
            A block: a card with a bold title and up to three lines under it, centred vertically.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) title [string]: The block's name.
            (6) lines [List<string>]: What it does, one short line each.
            (7) icon [string]: The key in Pixel_Motif.CONST_PIXEL_ICONS drawn in the top-right corner, or None.
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


def Svg_Body(path: str) -> str:
    """
    Description:
        An SVG file's <svg> element without its XML declaration, comments, or its own width and height, for inlining.

    Args:
        (1) path [string]: The SVG file.

    Returns:
        (1) parameter [string]: The markup.
    """

    with open(path, 'r', encoding='utf-8') as handle:
        svg = handle.read()
    svg = re.sub(r'<\?xml[^>]*>\s*|<!--.*?-->\s*', '', svg, flags=re.S)
    return re.sub(r'(<svg [^>]*?) width="[^"]*" height="[^"]*"', r'\1', svg, count=1).strip()


def Svg_Size(path: str) -> tp.Tuple[float, float]:
    """
    Description:
        An SVG file's viewBox size.

    Args:
        (1) path [string]: The SVG file.

    Returns:
        (1) parameter [Tuple<float> 1x2]: (width, height) in viewBox units.
    """

    _, _, w, h = (float(v) for v in re.search(r'viewBox="([^"]+)"', Svg_Body(path)).group(1).split())
    return w, h


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
        desktop application; under it what a catalogue mode adds for each object — recognise, the
        inspection area, check, the state; the mode, station, calibration (a chain, each naming the next),
        catalogue item and reference that set the stages up, and the records under the application that
        writes them; and the console's
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
          'also judges it. In every mode the camera shows a live preview while parts are placed, then takes a fresh '
          'frame once nothing moves, undistorted. Two cues, fused, find the objects: what differs from the empty '
          'surface, and a segmentation model. Each object is described in words by a local vision-language model '
          'and measured in mm through the calibration, and the desktop application shows the result in its Live, '
          'Trends, History and Log views. A catalogue mode adds four steps for each object found. It recognises the '
          'catalogued part by its reference images. Only a part wholly inside the inspection area is judged, and '
          'one outside is told apart as a part or a foreign object by similarity, size and colour. A judged part is '
          'checked on the side that is up, told by its references or else by its countersinks: its size, its '
          'holes, each bore centred in its countersink with the view angle corrected, and its stains. Each object '
          'then gets a state: OK, NOK or Warning, a Warning with its kind: outside the area, a foreign object, several '
          'parts, or a side unclear or mismatched. In a catalogue mode each object '
          'is described after its state, told what the checks found, and a sentence that contradicts them is '
          'dropped. The stages are set up by the mode (models and prompts), which names its station (camera, '
          'light, table and inspection area). The station names its calibration (undistortion and mm per pixel) '
          'and the empty-surface reference, and a catalogue mode also names its catalogue item (the part, its '
          'checks and its reference images). Every analysis is recorded with its images and results, alongside '
          'the session log, a run summary and the daily station events. Developed within internal research at '
          'JIC Smart Factory. Funded by the European Union.</desc>')
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
    c.Open('<g id="capture">', '1. Capture: a live preview, then a fresh frame once nothing moves')
    c.Card(40, y, 180, h, 'Capture', ['a live preview', 'while parts are', 'placed, then a', 'fresh frame once',
                                      'nothing moves,', 'undistorted'], icon='camera')
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

    # What a catalogue mode adds, for each object, in a group marked like 'each object': recognise, then the
    # inspection area under it (stacked as Describe and Measure are), then the check and the state.
    y_cat, h_cat = 546, 276
    mid_cat = y_cat + h_cat / 2
    h_recognise, gap = 96, 34
    y_area, h_area = y_cat + h_recognise + gap, h_cat - h_recognise - gap
    c.Open('<g id="catalogue">', '4. A catalogue mode also recognises its part, judges only inside the inspection area, '
           'checks the side that is up and gives each object a state')
    # Every object found goes on to these steps: down from Find objects, over, and into Recognise.
    c.Elbow([(389, y + h + 6), (389, y + h + 33), (191, y + h + 33), (191, y_cat - 6)])
    c.Rect(40, y_cat - 20, 808, h_cat + 90, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    c.Rect(214, y_cat - 34, 320, 28, T.CONST_BRAND)
    c.Text(374, y_cat - 14, 'catalogue mode adds, for each object', S[2], T.CONST_ON_INK, weight='700', anchor='middle')
    c.Card(56, y_cat, 270, h_recognise, 'Recognise', ['the catalogued part, by', 'its reference images'], icon='focus')
    c.Elbow([(191, y_cat + h_recognise + 6), (191, y_area - 6)])
    c.Card(56, y_area, 270, h_area, 'Inspection area', ['only a part wholly inside', 'is judged. Outside: a part',
                                                        'or a foreign object, by', 'similarity, size, colour'],
           icon='area')
    c.Arrow(332, y_area + h_area / 2, 360)
    c.Card(366, y_cat, 240, h_cat, 'Check', ['on the side that is up,', 'by its references, else',
                                            'by its countersinks:', 'size, holes, each bore',
                                            'centred in its countersink', '(view angle corrected)', 'and stains'],
           icon='checklist')
    c.Arrow(612, mid_cat, 640)
    # The three states, each a label in the purple on its state's ground, as the console's badges and History's filter,
    # and under Warning the kinds Scene Understanding names (Parameters.Vision.CONST_WARNING_KINDS).
    kinds = ['a kind: outside area,', 'foreign object,', 'several parts,', 'side unclear or', 'side mismatch']
    h_states = 42 + 2 * 40 + 22 * len(kinds) - 6
    top_states = y_cat + (h_cat - h_states) / 2
    c.Rect(646, y_cat, 186, h_cat, T.CONST_CARD, T.CONST_CARD_BORDER)
    c.Text(670, top_states + 22, 'State', S[6], T.CONST_INK, weight='700')
    c.Icon(832 - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top_states + 22), 'badge', T.CONST_INK_SOFT)
    for state, x_chip, row, w_chip in [('OK', 670, 0, 64), ('NOK', 742, 0, 72), ('Warning', 670, 1, 98)]:
        y_chip = top_states + 42 + 40 * row
        c.Rect(x_chip, y_chip, w_chip, 30, T.Label_Ground(state))
        c.Text(x_chip + w_chip / 2, y_chip + 21, state, S[2], T.CONST_INK, weight='700', anchor='middle')
    for i, line in enumerate(kinds):
        c.Text(670, top_states + 42 + 2 * 40 + 14 + 22 * i, line, S[2], T.CONST_INK_SOFT)
    c.Arrow(854, mid_cat, 886)
    # In a catalogue mode the description comes last: it is written with what the checks found, and held to it.
    for i, line in enumerate(['In this mode each object is described after its state, told what the checks found,',
                              'and a sentence that contradicts them is dropped.']):
        c.Text(832, y_cat + h_cat + 32 + 22 * i, line, S[2], T.CONST_INK_MUTE, anchor='end')
    c.Close('g')
    c.Blank()

    c.Open('<g id="application">', '5. The desktop application and its four views')
    h_app = y_cat + h_cat + 70 - y
    c.Rect(892, y, 268, h_app, T.CONST_VIEWPORT)
    top = y + (h_app - 250) / 2 + 22
    c.Text(916, top, 'Desktop app', S[6], T.CONST_VIEWPORT_TEXT, weight='700')
    c.Icon(1160 - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top), 'window', T.CONST_VIEWPORT_TEXT)
    for i, line in enumerate(['shows each object, its', 'description and size,', 'and, in a catalogue', 'mode, its state']):
        c.Text(916, top + 30 + 24 * i, line, S[3], T.CONST_VIEWPORT_TEXT)
    for i, view in enumerate(['Live', 'Trends', 'History', 'Log']):
        x_view, y_view = 916 + 114 * (i % 2), top + 140 + 44 * (i // 2)
        c.Rect(x_view, y_view, 106, 34, T.CONST_CARD, T.CONST_INK)
        c.Text(x_view + 53, y_view + 23, view, S[2], T.CONST_INK, weight='600', anchor='middle')
    c.Close('g')
    c.Blank()

    # What sets the stages up, as cards in a group marked like 'each object': the mode names its station and
    # the station its calibration, a chain drawn with arrows; the mode also names any catalogue item, the station
    # the empty-surface reference.
    y_set, h_set = CONST_SET_TOP, 264
    c.Open('<g id="set-up">', 'What sets the stages up: the mode, which names the station, which names the calibration, '
           'the catalogue item, the reference')
    c.Rect(40, y_set, 808, h_set, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    c.Rect(60, y_set - 14, 104, 28, T.CONST_BRAND)
    c.Text(112, y_set + 6, 'set up by', S[2], T.CONST_ON_INK, weight='700', anchor='middle')
    for i, (title, lines, icon) in enumerate([('Mode', ['models and prompts,', 'and its station'], 'gear'),
                                              ('Station', ['camera, light, table,', 'inspection area, and',
                                                           'its calibration'], 'station'),
                                              ('Calibration', ['undistortion and', 'mm per pixel'], 'target')]):
        c.Card(56 + 272 * i, y_set + 22, 232, 120, title, lines, icon=icon)
        if i:
            c.Arrow(56 + 272 * i - 34, y_set + 82, 56 + 272 * i - 6)
    for i, (title, lines, icon) in enumerate([('Catalogue item', ['named by a catalogue mode: the',
                                                                  'part, its checks, reference images'], 'catalogue'),
                                              ('Reference', ['named by the station: the empty',
                                                             'surface each frame is compared with'], 'image')]):
        c.Card(56 + 393 * i, y_set + 152, 383, 96, title, lines, icon=icon)
    c.Close('g')
    c.Blank()

    c.Open('<g id="records">', 'What the application writes and reads back')
    c.Connector(1026, y_set, y + h_app + 4)
    c.Card(892, y_set, 268, h_set, 'Records', ['images and results', 'of every analysis,', 'the session log,',
                                                   'a run summary and', 'daily station events'], icon='folder')
    c.Close('g')
    c.Blank()

    c.Open('<g id="funding-band">', 'The funding band, as in the console: the logos in its order, faint rules, '
           'the EU disclaimer')
    c.Add('<rect x="0.75" y="%g" width="1198.5" height="%g" fill="%s"/>' % (CONST_BAND_TOP, CONST_HEIGHT - 0.75 - CONST_BAND_TOP, T.CONST_BAND))
    # The row is centred like the console's (stretch on both sides); None is its hairline divider. The console sets
    # the disclaimer beside the logos; the diagram's 1200 px leave no room for it there, so it keeps the poster's
    # place, under a rule.
    tallest = max(height for _, height in Funding_Row_Cls.LOGOS) * CONST_BAND_SCALE
    row = []
    for name, height in Funding_Row_Cls.LOGOS:
        if name is None:
            row.append((None, 0.0, Funding_Row_Cls.DIVIDER_SHARE * tallest))
            continue
        w, h_box = Svg_Size(os.path.join(CONST_ASSETS_FOLDER, name))
        row.append((name, height * CONST_BAND_SCALE * w / h_box, height * CONST_BAND_SCALE))
    x = (CONST_WIDTH - sum(w for _, w, _ in row) - CONST_BAND_GAP * (len(row) - 1)) / 2
    y_row = CONST_BAND_TOP + CONST_BAND_PAD + tallest / 2
    for name, w, h in row:
        if name is None:
            c.Add('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-opacity="%g" stroke-width="1.5"/>'
                  % (x, round(y_row - h / 2, 1), x, round(y_row + h / 2, 1), T.CONST_BAND_LINE, T.CONST_BAND_LINE_ALPHA))
        else:
            c.Svg_Logo(round(x, 1), round(y_row - h / 2, 1), round(h, 1), os.path.join(CONST_ASSETS_FOLDER, name),
                       CONST_BAND_LABELS[name])
        x += w + CONST_BAND_GAP
    y_rule = round(y_row + tallest / 2 + CONST_BAND_PAD, 1)
    c.Add('<line x1="40" y1="%g" x2="1160" y2="%g" stroke="%s" stroke-opacity="%g" stroke-width="1"/>'
          % (y_rule, y_rule, T.CONST_BAND_LINE, T.CONST_BAND_LINE_ALPHA))
    for i, line in enumerate(Split_In_Two(Funding_Row_Cls.DISCLAIMER)):
        c.Text(CONST_WIDTH / 2, round(y_rule + 26 + 21 * i, 1), line, S[1], T.CONST_BAND_TEXT, anchor='middle',
               opacity=T.CONST_BAND_TEXT_ALPHA)
    c.Close('g')
    c.Close('svg')
    return c.Markup()


# The README's funding band: its width (the logos, the console's sizes, centred with room for the motif at both
# ends; GitHub shows it at the README column's width).
#   Unit [px]
CONST_FUNDING_WIDTH = 1000


def Draw_Funding_Band() -> str:
    """
    Description:
        The README's funding logo row: the console's funding band (UI.Widgets.Funding_Row_Cls) as an SVG, its own
        purple ground, so it reads the same on GitHub's light and dark themes. The same logos, heights, order, rule,
        clear space and pixel motif as the window's band, at CONST_FUNDING_WIDTH; the logos inlined, so the file is
        self-contained.

    Returns:
        (1) parameter [string]: The SVG document.
    """

    B, T = Funding_Row_Cls, Theme
    width, height = CONST_FUNDING_WIDTH, B.MOTIF_ROWS * B.MOTIF_CELL
    tallest = max(h for _, h in B.LOGOS)
    row = []
    for name, h in B.LOGOS:
        if name is None:
            row.append((None, 1.0, B.DIVIDER_SHARE * tallest))
            continue
        w, h_box = Svg_Size(os.path.join(CONST_ASSETS_FOLDER, name))
        row.append((name, h * w / h_box, h))
    x = (width - sum(w for _, w, _ in row) - Style.CONST_MARK_GAP * (len(row) - 1)) / 2
    logos, keep_out = [], []
    for name, w, h in row:
        y = round((height - h) / 2, 1)
        if name is None:
            logos.append('<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-opacity="%g" stroke-width="1"/>'
                         % (round(x + 0.5, 1), y, round(x + 0.5, 1), round(y + h, 1), T.CONST_BAND_LINE,
                            T.CONST_BAND_LINE_ALPHA))
        else:
            logos.append(Svg_Body(os.path.join(CONST_ASSETS_FOLDER, name)).replace(
                '<svg ', '<svg x="%g" y="%g" width="%g" height="%g" role="img" aria-label="%s" '
                % (round(x, 1), y, round(w, 1), h, escape(CONST_BAND_LABELS[name])), 1))
            keep_out.append((x - B.CLEAR_SPACE, x + w + B.CLEAR_SPACE))
        x += w + Style.CONST_MARK_GAP
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
             'aria-label="EDIH-DIGIMAT; Ministry of Industry and Trade of the Czech Republic; Funded by the European '
             'Union">' % (width, height, width, height),
             '<!-- Generated by Example/UI/architecture_diagram.py from the console\'s funding band; do not edit. -->',
             '<rect width="%d" height="%d" fill="%s"/>' % (width, height, T.CONST_BAND)]
    for cx, cy, strong in Motif_Cells(width, height, B.MOTIF_CELL, B.MOTIF_FILL, B.MOTIF_REACH, B.MOTIF_STRONG,
                                      keep_out):
        lines.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s" fill-opacity="%g"/>'
                     % (cx, cy, B.MOTIF_CELL, B.MOTIF_CELL, T.CONST_BAND_LINE, B.MOTIF_ALPHA[1 if strong else 0]))
    return '\n'.join(lines + logos + ['</svg>']) + '\n'


def main():
    """
    Description:
        Write images/anyscan-architecture.svg and the README's funding logo row, images/anyscan-funding.svg, from the
        theme and the logos, or with --check report whether either committed file is stale.

            python Example/UI/architecture_diagram.py [--check]
    """

    parser = argparse.ArgumentParser(description='Generate the README architecture diagram.')
    parser.add_argument('--check', action='store_true',
                        help='do not write; exit 1 if the committed diagram differs from the output')
    args = parser.parse_args()

    with open(CONST_LOGO_FILE, 'r', encoding='utf-8') as handle:
        figures = [(CONST_DIAGRAM_FILE, Draw_Architecture(handle.read())), (CONST_FUNDING_FILE, Draw_Funding_Band())]
    stale = 0
    for path, markup in figures:
        if args.check:
            current = ''
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as handle:
                    current = handle.read()
            if current != markup:
                print('[ERROR] %s is stale or was edited by hand; regenerate it with this script.' % path)
                stale = 1
            else:
                print('[INFO] %s is up to date.' % path)
            continue
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(markup)
        print('[INFO] Wrote %s.' % path)
    return stale


if __name__ == '__main__':
    sys.exit(main())
