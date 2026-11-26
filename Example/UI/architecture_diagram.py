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
import io
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
# fontTools (Subsetting the bundled Public Sans for the embedded @font-face)
from fontTools import subset as Font_Subset
# Pillow (Measuring words in the bundled Public Sans, to wrap them into their cards) [pip3 install Pillow]
from PIL import ImageFont
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

    The generator of images/anyscan-architecture.svg, the README's architecture figure: what AnyScan is and
    how it works in its two modes, at the top level only, in the station's order - the camera (a live preview,
    then a fresh frame once nothing moves), finding the objects, measuring each one, what a catalogue mode adds
    for each object (recognising its part, the inspection area that decides which parts are judged and tells a
    part outside it from a foreign object, the checks an item can define on the side that is up, and a verdict
    per object), then describing each object, told in a catalogue mode what the checks found; the desktop
    application; the files that set the stages up (the mode names the station, the station the calibration, and
    the catalogue item and the reference); and the records the application writes and reads back. No class,
    model or product names, no configuration fields, no number; README > Architecture and SPEC.md have the
    detail. Each card carries a pixel icon from the application's own set
    (UI.Utilities.Pixel_Motif.CONST_PIXEL_ICONS), so the figure and the console never draw two versions of one
    icon. The funding band is not part of it: the README's Funding section shows it (images/anyscan-funding.svg,
    written here too) with the EU disclaimer as text.

    Regenerating is the way to change it; the SVG is never edited by hand. Every colour comes
    from a Parameters/Theme.py token and every size from the console's type scale, so the
    figure moves with the theme instead of drifting from it. The SVG is self-contained, because
    the README shows it through <img>, and an SVG loaded that way never fetches another file:
    the AnyScan logo is copied in byte for byte from images/anyscan-logo.svg, the JIC Smart Factory
    logo from App/assets/, and the words are set in Public Sans, embedded as a subset of the bundled
    App/assets/fonts files (SIL Open Font License 1.1, which declares no Reserved Font Name, so a subset keeps
    the name) holding only the characters the figure uses, as data: URIs, so every reader sees the same type.

    test/UI/test_brand_figures.py fails when the committed SVG is not this script's output (the embedded font
    bytes aside, which depend on the fontTools version: Without_Font_Data), or draws a colour that is not a
    token, or when an embedded font misses a character the figure uses.

        python Example/UI/architecture_diagram.py            # rewrite the SVG
        python Example/UI/architecture_diagram.py --check    # exit 1 if it is stale
"""
# The source logo, the folder of the marks, the JIC Smart Factory logo, and the diagram this script writes.
#   Unit [string]
CONST_LOGO_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-logo.svg')
CONST_ASSETS_FOLDER = os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets')
CONST_JIC_FILE = os.path.join(CONST_ASSETS_FOLDER, 'jic-smart-factory.svg')
CONST_DIAGRAM_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-architecture.svg')
# The README's funding logo row: the console's funding band, drawn as an SVG.
CONST_FUNDING_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-funding.svg')
# The README's headline, a light and a dark version: the AnyScan logo and the JIC Smart Factory logo as in the top bar.
#   Unit [string]
CONST_HEADLINE_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-headline-%s.svg')
# The marker comments around the inline logo; the test reads the copy between them.
#   Unit [string]
CONST_LOGO_BEGIN = '<!-- logo:begin -->'
CONST_LOGO_END = '<!-- logo:end -->'
# The marker comments around the inline JIC Smart Factory logo, brand artwork in its own colour like the AnyScan logo.
#   Unit [string]
CONST_JIC_BEGIN = '<!-- jic:begin -->'
CONST_JIC_END = '<!-- jic:end -->'
# The drawing width in user units (the README's ~880 px renders it at 0.73); its height follows from the cards'
# words (Draw_Architecture), written where CONST_HEIGHT_SLOT stands.
#   Unit [px] / [string]
CONST_WIDTH = 1200
CONST_HEIGHT_SLOT = '@HEIGHT@'
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
# The icon's drawn size (12 cells of 3 px: at the earlier 28 px line icons' size a cell would be 2.33 px and the grid
# would smear) and its inset from a card's right edge; it is centred on the title's capitals.
#   Unit [px]
CONST_ICON_SIZE = 36
CONST_ICON_INSET = 16
# The bundled Public Sans file of each weight the figure draws, embedded as a subset (App/assets/fonts).
#   Unit [Dictionary<string, string>]
CONST_FONT_FOLDER = os.path.join(CONST_ASSETS_FOLDER, 'fonts')
CONST_FONT_FILES = {'400': 'PublicSans-Regular.ttf', '500': 'PublicSans-Medium.ttf',
                    '600': 'PublicSans-SemiBold.ttf', '700': 'PublicSans-Bold.ttf'}
# The line the embedded @font-face rules replace once every word is written (the subsets hold only the characters
# the figure uses, so they are built last).
#   Unit [string]
CONST_FONT_SLOT = '/* font-face */'
# The embedded font data, as the generator writes it and as Without_Font_Data masks it.
#   Unit [re.Pattern]
CONST_FONT_DATA = re.compile(r'(data:font/woff;base64,)[A-Za-z0-9+/=]+')
# What each band logo is, for screen readers.
#   Unit [Dictionary<string, string>]
CONST_BAND_LABELS = {'edih-digimat-white.svg': 'EDIH-DIGIMAT',
                     'partner-ministry-white.svg': 'Ministry of Industry and Trade of the Czech Republic',
                     'funder-eu-white.svg': 'Funded by the European Union'}
# The console's type scale (Style.CONST_TYPE_SCALE, in points) at 1.55x, so the smallest step the diagram uses
# (S[2], 17.8 units: the group tags, the verdicts and their kinds, the view buttons, the notes) renders at 13 px
# or more at the README's 880 px (the owner, 2026-11-26), and a card's words (S[3], 19.4) at 14.2 px.
#   Unit [Vector<float>]
CONST_SCALE = [round(size * 1.55, 1) for size in Style.CONST_TYPE_SCALE]
# The smallest size the README may show [px] and the README's width [px], which test_brand_figures holds the
# diagram's every font size to.
#   Unit [float]
CONST_MIN_README_PX = 13.0
CONST_README_WIDTH = 880.0
# A card's inner space: its words' left inset and the room kept above and below its text block.
#   Unit [px]
CONST_CARD_PAD = 24
CONST_CARD_V_PAD = 22
# The text block's vertical metrics, in proportion to the font sizes (measured on the 1.4x layout and kept): a
# title's cap height and the gap from it to the first line, a line's pitch and its descender.
#   Unit [-]
CONST_CAP_RATIO = 22 / 23.1
CONST_TITLE_GAP_RATIO = 30 / 23.1
CONST_LINE_RATIO = 24 / 17.5
CONST_DESCENDER_RATIO = 6 / 17.5
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
        self.__characters = {}

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

    def Characters(self) -> tp.Dict[str, str]:
        """
        Description:
            The characters each font weight has set so far, for the embedded subsets.

        Returns:
            (1) parameter [Dictionary<string, string>]: Each weight ('400' ... '700') and its characters, sorted.
        """

        return {weight: ''.join(sorted(characters)) for weight, characters in sorted(self.__characters.items())}

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

        self.__characters.setdefault(weight or '400', set()).update(text)
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

    def Card(self, x: float, y: float, w: float, h: float, title: str, text: str,
             icon: tp.Optional[str] = None) -> None:
        """
        Description:
            A block: a card with a bold title and its words wrapped under it (Card_Lines), centred vertically.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size; h at least Card_Height(w, title, text).
            (5) title [string]: The block's name.
            (6) text [string]: What it does, wrapped to the card.
            (7) icon [string]: The key in Pixel_Motif.CONST_PIXEL_ICONS drawn in the top-right corner, or None.
        """

        S = CONST_SCALE
        lines = Card_Lines(w, title, text)
        self.Rect(x, y, w, h, Theme.CONST_CARD, Theme.CONST_CARD_BORDER)
        top = round(y + (h - Block_Height(len(lines), S[3])) / 2 + CONST_CAP_RATIO * S[6], 1)
        if icon is not None:
            self.Icon(x + w - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top), icon, Theme.CONST_INK_SOFT)
        self.Text(x + CONST_CARD_PAD, top, title, S[6], Theme.CONST_INK, weight='700')
        for i, line in enumerate(lines):
            self.Text(x + CONST_CARD_PAD, round(top + Title_Gap() + Line_Pitch(S[3]) * i, 1), line, S[3],
                      Theme.CONST_INK_SOFT)


def Icon_Top(baseline: float) -> float:
    """
    Description:
        The top of a card's icon, centred on its title's capitals (about 0.35 of the title size above the baseline).

    Args:
        (1) baseline [float]: The title's baseline.

    Returns:
        (1) parameter [float]: The icon's top edge.
    """

    return round(baseline - 8 / 23.1 * CONST_SCALE[6] - CONST_ICON_SIZE / 2, 1)


def Text_Width(text: str, size: float, weight: str = '400') -> float:
    """
    Description:
        How wide words are in the bundled Public Sans of a weight (CONST_FONT_FILES), the face the SVG embeds.

    Args:
        (1) text [string]: The words.
        (2) size [float]: The font size.
        (3) weight [string]: '400', '500', '600' or '700'.

    Returns:
        (1) parameter [float]: The width in user units.
    """

    return ImageFont.truetype(os.path.join(CONST_FONT_FOLDER, CONST_FONT_FILES[weight]), size).getlength(text)


def Wrap_Text(text: str, size: float, width: float, weight: str = '400') -> tp.List[str]:
    """
    Description:
        Words broken into lines no wider than a width, measured in the embedded face.

    Args:
        (1) text [string]: The words.
        (2) size [float]: The font size.
        (3) width [float]: The width the lines may take.
        (4) weight [string]: The weight.

    Returns:
        (1) parameter [List<string>]: The lines.

    Raises:
        ValueError: A single word is wider than the width, so the words cannot fit.
    """

    lines, line = [], ''
    for word in text.split(' '):
        if Text_Width(word, size, weight) > width:
            raise ValueError("'%s' is wider than %g at %g; widen its card." % (word, width, size))
        trial = (line + ' ' + word).strip()
        if Text_Width(trial, size, weight) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def Line_Pitch(size: float) -> float:
    """
    Description:
        The distance between two lines of words at a size.

    Args:
        (1) size [float]: The font size.

    Returns:
        (1) parameter [float]: The pitch.
    """

    return round(CONST_LINE_RATIO * size, 1)


def Title_Gap() -> float:
    """
    Description:
        The distance from a card title's baseline to its first line's.

    Returns:
        (1) parameter [float]: The gap.
    """

    return round(CONST_TITLE_GAP_RATIO * CONST_SCALE[6], 1)


def Block_Height(lines: int, size: float) -> float:
    """
    Description:
        A card's text block, from its title's cap height to its last line's descender.

    Args:
        (1) lines [int]: How many lines of words follow the title.
        (2) size [float]: Their font size.

    Returns:
        (1) parameter [float]: The height.
    """

    return CONST_CAP_RATIO * CONST_SCALE[6] + Title_Gap() + Line_Pitch(size) * (lines - 1) + CONST_DESCENDER_RATIO * size


def Card_Lines(w: float, title: str, text: str) -> tp.List[str]:
    """
    Description:
        A card's words wrapped to its width, after checking its title fits beside its icon.

    Args:
        (1) w [float]: The card's width.
        (2) title [string]: Its title.
        (3) text [string]: Its words.

    Returns:
        (1) parameter [List<string>]: The lines.

    Raises:
        ValueError: The title or a word does not fit the card.
    """

    room = w - CONST_CARD_PAD - CONST_ICON_INSET - CONST_ICON_SIZE - 12
    if Text_Width(title, CONST_SCALE[6], '700') > room:
        raise ValueError("The title '%s' is wider than its card leaves beside the icon; widen the card." % title)
    return Wrap_Text(text, CONST_SCALE[3], w - 2 * CONST_CARD_PAD)


def Card_Height(w: float, title: str, text: str) -> float:
    """
    Description:
        The height a card needs for its title and its wrapped words, with CONST_CARD_V_PAD above and below.

    Args:
        (1) w [float]: The card's width.
        (2) title [string]: Its title.
        (3) text [string]: Its words.

    Returns:
        (1) parameter [float]: The height.
    """

    return round(Block_Height(len(Card_Lines(w, title, text)), CONST_SCALE[3]) + 2 * CONST_CARD_V_PAD)


def Tag(c: tp.Any, x_mid: float, y_mid: float, text: str) -> None:
    """
    Description:
        A group's tag: its words in white on the brand purple, as wide as they are, centred on a point.

    Args:
        (1) c [Svg_Writer_Cls]: The document.
        (2 - 3) x_mid, y_mid [float]: The tag's centre.
        (4) text [string]: Its words.
    """

    S = CONST_SCALE
    w, h = round(Text_Width(text, S[2], '700') + 28), round(1.75 * S[2])
    c.Rect(round(x_mid - w / 2, 1), round(y_mid - h / 2, 1), w, h, Theme.CONST_BRAND)
    c.Text(x_mid, round(y_mid + 0.35 * S[2], 1), text, S[2], Theme.CONST_ON_INK, weight='700', anchor='middle')


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


def Font_Face_Css(characters: tp.Dict[str, str]) -> str:
    """
    Description:
        The @font-face rules that embed Public Sans: for each weight the figure sets, the bundled file
        (CONST_FONT_FILES) subset to the characters that weight draws, as WOFF in a data: URI. The subset keeps the
        font's whole name table, so its copyright and its SIL Open Font License 1.1 notice travel with it.

    Args:
        (1) characters [Dictionary<string, string>]: Each weight and the characters it draws (Svg_Writer_Cls.Characters).

    Returns:
        (1) parameter [string]: The rules, one per line.
    """

    rules = []
    for weight, text in characters.items():
        options = Font_Subset.Options()
        options.flavor = 'woff'
        options.name_IDs = ['*']
        options.name_languages = ['*']
        options.notdef_outline = True
        options.recalc_timestamp = False
        buffer = io.BytesIO()
        with Font_Subset.load_font(os.path.join(CONST_FONT_FOLDER, CONST_FONT_FILES[weight]), options) as font:
            subsetter = Font_Subset.Subsetter(options)
            subsetter.populate(text=text)
            subsetter.subset(font)
            Font_Subset.save_font(font, buffer, options)
        rules.append("@font-face { font-family: 'Public Sans'; font-weight: %s; src: url(data:font/woff;base64,%s) "
                     "format('woff'); }" % (weight, base64.b64encode(buffer.getvalue()).decode('ascii')))
    return '\n'.join(rules)


def Without_Font_Data(svg: str) -> str:
    """
    Description:
        An SVG with its embedded font bytes masked: the bytes depend on the fontTools version that subset them, the
        rest of the file on this script alone. What --check and the test compare.

    Args:
        (1) svg [string]: The SVG text.

    Returns:
        (1) parameter [string]: The text with each embedded font's data replaced by '...'.
    """

    return CONST_FONT_DATA.sub(r'\1...', svg)


def Draw_Architecture(logo_svg: str) -> str:
    """
    Description:
        The whole diagram, in the station's order: the header (the AnyScan logo and the JIC mark) and the tagline;
        capture, find the objects and measure each one, left to right; under them what a catalogue mode adds for
        each object - recognise, the inspection area, check, the verdict; then describe each object, after the
        verdict in a catalogue mode; the desktop application they feed; the mode, station, calibration (a chain,
        each naming the next), catalogue item and reference that set the stages up, and the records under the
        application that writes them. Everything drawn is in the code; nothing is planned.

    Args:
        (1) logo_svg [string]: The content of images/anyscan-logo.svg, inlined unchanged.

    Returns:
        (1) parameter [string]: The SVG document.
    """

    S = CONST_SCALE; T = Theme
    c = Svg_Writer_Cls()
    c.Open('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%s" viewBox="0 0 %d %s" role="img" '
           'aria-label="AnyScan architecture">' % (CONST_WIDTH, CONST_HEIGHT_SLOT, CONST_WIDTH, CONST_HEIGHT_SLOT))
    c.Add('<!-- Generated by Example/UI/architecture_diagram.py. Regenerate it, do not edit it by hand. -->')
    c.Add('<!-- The words are set in Public Sans (Copyright 2015 The Public Sans Project Authors), embedded as subsets '
          'under the SIL Open Font License 1.1: https://openfontlicense.org -->')
    c.Add('<title>AnyScan architecture</title>')
    c.Add('<desc>AnyScan finds every object on a work surface, measures it and describes it. A catalogue mode '
          'also judges it. In every mode the camera shows a live preview while parts are placed, then takes a fresh '
          'frame once nothing moves, undistorted. Two cues, fused, find the objects: what differs from the empty '
          'surface, and a segmentation model. Each object is measured in mm through the calibration. A catalogue '
          'mode then adds four steps for each object. It recognises the catalogued part by its reference images. '
          'Only a part wholly inside the inspection area is judged, and one outside is told apart as a part or a '
          'foreign object by similarity, size and colour. A judged part is checked on the side that is up, told by '
          'its references or else by its countersinks: its size, its holes, each bore centred in its countersink '
          'with the view angle corrected, and its stains. Each object then gets a verdict: OK, NOK or Warning, a '
          'Warning with its kind: outside the area, a foreign object, several parts, or a side unclear or '
          'mismatched. Then each object is described in words by a local vision-language model, in a catalogue '
          'mode told what the checks found, and a sentence that contradicts them is dropped. The desktop '
          'application shows the result in its Live, Trends, History and Log views. The stages are set up by the '
          'mode (models and prompts), which names its station (camera, light, table and inspection area). The '
          'station names its calibration (undistortion and mm per pixel) and the empty-surface reference, and a '
          'catalogue mode also names its catalogue item (the part, its checks and its reference images). Every '
          'analysis is recorded with its images and results, alongside the session log, a run summary and the '
          'daily station events.</desc>')
    c.Blank()
    c.Open('<defs>')
    c.Open('<style>')
    c.Add(CONST_FONT_SLOT)
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
    c.Add('<rect x="0.75" y="0.75" width="%g" height="%s" fill="%s" stroke="%s" stroke-width="1.5"/>'
          % (CONST_WIDTH - 1.5, CONST_HEIGHT_SLOT + '-1.5', T.CONST_BG, T.CONST_CARD_BORDER))
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
    # One sentence a line, each wrapped if it ever outgrows the width.
    tagline = [line for sentence in ['AnyScan finds every object on a work surface, measures it and describes it.',
                                     'A catalogue mode also judges it.']
               for line in Wrap_Text(sentence, S[5], CONST_WIDTH - 80, '500')]
    for i, line in enumerate(tagline):
        c.Text(40, round(168 + 1.3 * S[5] * i, 1), line, S[5], T.CONST_INK, weight='500')
    c.Close('g')
    c.Blank()

    # Every mode: three columns at one height, as tall as the fullest card; the arrows sit on their middle line.
    row = [(40, 232, 'Capture', 'a live preview while parts are placed, then a fresh frame once nothing moves, '
                                'undistorted', 'camera'),
           (316, 262, 'Find objects', 'two cues, fused: what differs from the empty surface, and a segmentation model',
            'magnifier'),
           (620, 212, 'Measure', 'size in mm, through the calibration', 'ruler')]
    y = round(168 + 1.3 * S[5] * (len(tagline) - 1) + 64)
    h = max([224] + [Card_Height(w, title, text) for _, w, title, text, _ in row])
    mid = y + h / 2
    for (x, w, title, text, icon), (group, comment) in zip(row, [('capture', '1. Capture: a live preview, then a fresh '
                                                                   'frame once nothing moves'),
                                                                  ('find', '2. Find the objects: two cues, fused'),
                                                                  ('measure', '3. Each object: measured')]):
        c.Open('<g id="%s">' % group, comment)
        if group == 'measure':
            c.Rect(604, y - 20, 244, h + 40, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
            Tag(c, 624 + (Text_Width('each object', S[2], '700') + 28) / 2, y - 20, 'each object')
        c.Card(x, y, w, h, title, text, icon=icon)
        c.Close('g')
        if group != 'measure':
            c.Arrow(x + w + 6, mid, x + w + 38)
        c.Blank()

    # What a catalogue mode adds, for each object measured, in a group marked like 'each object': recognise, then the
    # inspection area under it, then the check and the verdict.
    x_rec, w_rec, x_check, w_check, x_verdict, w_verdict = 56, 290, 380, 200, 614, 218
    recognise = 'the catalogued part, by its reference images'
    area = 'only a part wholly inside is judged. Outside: a part or a foreign object, by similarity, size, colour'
    check = ('on the side that is up, by its references, else by its countersinks: size, holes, each bore centred in its '
             'countersink (view angle corrected) and stains')
    kinds = Wrap_Text('a kind: outside area, foreign object, several parts, side unclear or side mismatch', S[2],
                      w_verdict - 2 * CONST_CARD_PAD)
    chip_h, chip_gap = round(1.9 * S[2]), 10
    h_states = round(CONST_CAP_RATIO * S[6] + 20 + 2 * chip_h + chip_gap + 18 + Line_Pitch(S[2]) * (len(kinds) - 1)
                     + CONST_DESCENDER_RATIO * S[2])
    h_recognise, gap = Card_Height(w_rec, 'Recognise', recognise), 34
    h_area = Card_Height(w_rec, 'Inspection area', area)
    y_cat = y + h + 90
    h_cat = max(h_recognise + gap + h_area, Card_Height(w_check, 'Check', check), h_states + 2 * CONST_CARD_V_PAD)
    mid_cat = y_cat + h_cat / 2
    y_area, h_area = y_cat + h_recognise + gap, h_cat - h_recognise - gap
    c.Open('<g id="catalogue">', '4. A catalogue mode then recognises its part, judges only inside the inspection area, '
           'checks the side that is up and gives each object a verdict')
    # Every object measured goes on to these steps: down from Measure, over, and into Recognise.
    x_down, x_into = 726, x_rec + w_rec / 2
    c.Elbow([(x_down, y + h + 26), (x_down, y + h + 45), (x_into, y + h + 45), (x_into, y_cat - 6)])
    c.Rect(40, y_cat - 20, 808, h_cat + 40, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    Tag(c, 440, y_cat - 20, 'catalogue mode adds, for each object')
    c.Card(x_rec, y_cat, w_rec, h_recognise, 'Recognise', recognise, icon='focus')
    c.Elbow([(x_into, y_cat + h_recognise + 6), (x_into, y_area - 6)])
    c.Card(x_rec, y_area, w_rec, h_area, 'Inspection area', area, icon='area')
    c.Arrow(x_rec + w_rec + 6, y_area + h_area / 2, x_check - 6)
    c.Card(x_check, y_cat, w_check, h_cat, 'Check', check, icon='checklist')
    c.Arrow(x_check + w_check + 6, mid_cat, x_verdict - 6)
    # The three verdicts, each a label in the purple on its state's ground, as the console's badges and History's
    # filter, and under them the Warning kinds Scene Understanding names (Parameters.Vision.CONST_WARNING_KINDS).
    top_states = round(y_cat + (h_cat - h_states) / 2 + CONST_CAP_RATIO * S[6], 1)
    c.Rect(x_verdict, y_cat, w_verdict, h_cat, T.CONST_CARD, T.CONST_CARD_BORDER)
    c.Text(x_verdict + CONST_CARD_PAD, top_states, 'Verdict', S[6], T.CONST_INK, weight='700')
    c.Icon(x_verdict + w_verdict - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top_states), 'badge', T.CONST_INK_SOFT)
    x_chip = x_verdict + CONST_CARD_PAD
    for state, row_index in [('OK', 0), ('NOK', 0), ('Warning', 1)]:
        if state == 'Warning':
            x_chip = x_verdict + CONST_CARD_PAD
        w_chip = round(Text_Width(state, S[2], '700') + 28)
        y_chip = round(top_states + 20 + (chip_h + chip_gap) * row_index, 1)
        c.Rect(x_chip, y_chip, w_chip, chip_h, T.Label_Ground(state))
        c.Text(x_chip + w_chip / 2, round(y_chip + chip_h / 2 + 0.35 * S[2], 1), state, S[2], T.CONST_INK, weight='700',
               anchor='middle')
        x_chip += w_chip + 8
    for i, line in enumerate(kinds):
        c.Text(x_verdict + CONST_CARD_PAD, round(top_states + 20 + 2 * chip_h + chip_gap + 18 + CONST_CAP_RATIO * S[2]
                                                 + Line_Pitch(S[2]) * i, 1), line, S[2], T.CONST_INK_SOFT)
    c.Close('g')
    c.Blank()

    # Then every mode describes each object: after the verdict in a catalogue mode, told what the checks found; in a
    # detect-only mode straight after Measure, as the note above the card says.
    describe = ('each object in words, by a local vision-language model. In a catalogue mode it is told what the checks '
                'found, and a sentence that contradicts them is dropped.')
    y_describe = y_cat + h_cat + 20 + 48
    h_describe = Card_Height(808, 'Describe', describe)
    c.Open('<g id="describe">', '5. Each object: described, in a catalogue mode after its verdict and held to the checks')
    x_verdict_mid = x_verdict + w_verdict / 2
    c.Elbow([(x_verdict_mid, y_cat + h_cat + 6), (x_verdict_mid, y_describe - 6)])
    c.Text(x_verdict_mid - 20, y_describe - 16, 'A detect-only mode goes from Measure straight to Describe.', S[2],
           T.CONST_INK_MUTE, anchor='end')
    c.Card(40, y_describe, 808, h_describe, 'Describe', describe, icon='text')
    c.Close('g')
    c.Arrow(854, y_describe + h_describe / 2, 886)
    c.Blank()

    c.Open('<g id="application">', '6. The desktop application and its four views')
    h_app = y_describe + h_describe - y
    app = Wrap_Text('shows each object, its size and description, and, in a catalogue mode, its verdict', S[3],
                    268 - 2 * CONST_CARD_PAD)
    button_h, button_gap = round(2 * S[2]), 10
    content = Block_Height(len(app), S[3]) + 30 + 2 * button_h + button_gap
    top = round(y + (h_app - content) / 2 + CONST_CAP_RATIO * S[6], 1)
    c.Rect(892, y, 268, h_app, T.CONST_VIEWPORT)
    c.Text(916, top, 'Desktop app', S[6], T.CONST_VIEWPORT_TEXT, weight='700')
    c.Icon(1160 - CONST_ICON_INSET - CONST_ICON_SIZE, Icon_Top(top), 'window', T.CONST_VIEWPORT_TEXT)
    for i, line in enumerate(app):
        c.Text(916, round(top + Title_Gap() + Line_Pitch(S[3]) * i, 1), line, S[3], T.CONST_VIEWPORT_TEXT)
    y_buttons = round(top + Title_Gap() + Line_Pitch(S[3]) * (len(app) - 1) + CONST_DESCENDER_RATIO * S[3] + 30, 1)
    for i, view in enumerate(['Live', 'Trends', 'History', 'Log']):
        x_view, y_view = 916 + 114 * (i % 2), round(y_buttons + (button_h + button_gap) * (i // 2), 1)
        c.Rect(x_view, y_view, 106, button_h, T.CONST_CARD, T.CONST_INK)
        c.Text(x_view + 53, round(y_view + button_h / 2 + 0.35 * S[2], 1), view, S[2], T.CONST_INK, weight='600',
               anchor='middle')
    c.Close('g')
    c.Blank()

    # What sets the stages up, as cards in a group marked like 'each object': the mode names its station and
    # the station its calibration, a chain drawn with arrows; the mode also names any catalogue item, the station
    # the empty-surface reference.
    chain = [('Mode', 'models and prompts, and its station', 'gear'),
             ('Station', 'camera, light, table, inspection area, and its calibration', 'station'),
             ('Calibration', 'undistortion and mm per pixel', 'target')]
    named = [('Catalogue item', 'named by a catalogue mode: the part, its checks, reference images', 'catalogue'),
             ('Reference', 'named by the station: the empty surface each frame is compared with', 'image')]
    records = 'images and results of every analysis, the session log, a run summary and daily station events'
    h_chain = max([120] + [Card_Height(232, title, text) for title, text, _ in chain])
    h_named = max([96] + [Card_Height(383, title, text) for title, text, _ in named])
    y_set = y_describe + h_describe + 48
    h_set = max(22 + h_chain + 10 + h_named + 16, Card_Height(268, 'Records', records))
    c.Open('<g id="set-up">', 'What sets the stages up: the mode, which names the station, which names the calibration, '
           'the catalogue item, the reference')
    c.Rect(40, y_set, 808, h_set, 'none', T.CONST_SCROLLBAR_HANDLE, dash='6 6')
    Tag(c, 60 + (Text_Width('set up by', S[2], '700') + 28) / 2, y_set, 'set up by')
    for i, (title, text, icon) in enumerate(chain):
        c.Card(56 + 272 * i, y_set + 22, 232, h_chain, title, text, icon=icon)
        if i:
            c.Arrow(56 + 272 * i - 34, y_set + 22 + h_chain / 2, 56 + 272 * i - 6)
    for i, (title, text, icon) in enumerate(named):
        c.Card(56 + 393 * i, y_set + 22 + h_chain + 10, 383, h_named, title, text, icon=icon)
    c.Close('g')
    c.Blank()

    c.Open('<g id="records">', 'What the application writes and reads back')
    c.Connector(1026, y_set, y + h_app + 4)
    c.Card(892, y_set, 268, h_set, 'Records', records, icon='folder')
    c.Close('g')
    height = round(y_set + h_set + 40)
    c.Close('svg')
    markup = c.Markup().replace(CONST_FONT_SLOT, Font_Face_Css(c.Characters()), 1)
    return markup.replace(CONST_HEIGHT_SLOT + '-1.5', '%g' % (height - 1.5)).replace(CONST_HEIGHT_SLOT, '%d' % height)


# The headline's logo height in its own units (the logo's viewBox height, drawn at scale 1), the JIC Smart Factory
# logo's height beside it (the top bar's ratio, UI/Core.py CONST_JIC_LOGO_HEIGHT over Style.CONST_LOGO_HEIGHT), and
# the brand purple both logo files fill with, which the dark version replaces with the white on the purple.
#   Unit [px] / [string]
CONST_HEADLINE_LOGO_HEIGHT = 140.0
CONST_HEADLINE_JIC_HEIGHT = round(140.0 * 26 / Style.CONST_LOGO_HEIGHT, 2)
CONST_LOGO_FILL = '#640aba'


def Draw_Headline(logo_svg: str, dark: bool) -> str:
    """
    Description:
        The README's headline: the AnyScan logo and the JIC Smart Factory logo side by side, a thin rule between them,
        spaced by the top bar's rule (Style.CONST_MARK_GAP from ink to rule and rule to ink, scaled), on a transparent
        ground. Both files are inlined unchanged; the dark version only replaces their one fill, the brand purple, with
        Theme.CONST_ON_INK (a single-colour light version of the same files), and draws the rule in the periwinkle.

    Args:
        (1) logo_svg [string]: The content of images/anyscan-logo.svg.
        (2) dark [bool]: The version for GitHub's dark theme.

    Returns:
        (1) parameter [string]: The SVG document.
    """

    T = Theme
    _, _, view_w, view_h = (float(v) for v in re.search(r'viewBox="([^"]+)"', logo_svg).group(1).split())
    scale = CONST_HEADLINE_LOGO_HEIGHT / view_h
    gap = Style.CONST_MARK_GAP * CONST_HEADLINE_LOGO_HEIGHT / Style.CONST_LOGO_HEIGHT
    ink_right = scale * (view_w - CONST_LOGO_RIGHT_MARGIN)
    rule_x = round(ink_right + gap + CONST_DIVIDER_WIDTH, 2)
    with open(CONST_JIC_FILE, 'r', encoding='utf-8') as handle:
        jic = re.sub(r'<\?xml[^>]*>\s*', '', handle.read()).strip()
    _, _, jic_w, jic_h = (float(v) for v in re.search(r'viewBox="([^"]+)"', jic).group(1).split())
    jic_x = round(rule_x + CONST_DIVIDER_WIDTH + gap, 2)
    jic_width = round(CONST_HEADLINE_JIC_HEIGHT * jic_w / jic_h, 2)
    width, height = round(jic_x + jic_width, 2), CONST_HEADLINE_LOGO_HEIGHT
    logo, rule = logo_svg.strip(), T.CONST_TOPBAR_DIVIDER
    if dark:
        logo = re.sub(CONST_LOGO_FILL, T.CONST_ON_INK, logo, flags=re.I)
        jic = re.sub(CONST_LOGO_FILL, T.CONST_ON_INK, jic, flags=re.I)
        rule = T.CONST_SCROLLBAR_HANDLE
    jic_y = round((height - CONST_HEADLINE_JIC_HEIGHT) / 2, 2)
    lines = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %g %g" width="%g" height="%g" role="img" '
             'aria-label="AnyScan, developed at JIC Smart Factory">' % (width, height, width, height),
             '<!-- Generated by Example/UI/architecture_diagram.py from images/anyscan-logo.svg and '
             'App/assets/jic-smart-factory.svg%s; do not edit. -->' % (', their fill made white' if dark else ''),
             '<g transform="scale(%g)">' % scale, logo, '</g>',
             '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g"/>'
             % (rule_x, round(height * 0.12, 2), rule_x, round(height * 0.88, 2), rule, CONST_DIVIDER_WIDTH * 2),
             jic.replace('<svg ', '<svg x="%g" y="%g" width="%g" height="%g" ' % (jic_x, jic_y, jic_width,
                                                                              CONST_HEADLINE_JIC_HEIGHT), 1),
             '</svg>']
    return '\n'.join(lines) + '\n'


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
             'aria-label="EDIH-DIGIMAT, Ministry of Industry and Trade of the Czech Republic, Funded by the European '
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
        Write images/anyscan-architecture.svg, the README's funding logo row (images/anyscan-funding.svg) and its
        headline (images/anyscan-headline-light.svg and -dark.svg) from the theme and the logos, or with --check
        report whether a committed file is stale.

            python Example/UI/architecture_diagram.py [--check]
    """

    parser = argparse.ArgumentParser(description='Generate the README architecture diagram.')
    parser.add_argument('--check', action='store_true',
                        help='do not write; exit 1 if the committed diagram differs from the output')
    args = parser.parse_args()

    with open(CONST_LOGO_FILE, 'r', encoding='utf-8') as handle:
        logo = handle.read()
    figures = [(CONST_DIAGRAM_FILE, Draw_Architecture(logo)), (CONST_FUNDING_FILE, Draw_Funding_Band()),
               (CONST_HEADLINE_FILE % 'light', Draw_Headline(logo, False)),
               (CONST_HEADLINE_FILE % 'dark', Draw_Headline(logo, True))]
    stale = 0
    for path, markup in figures:
        if args.check:
            current = ''
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as handle:
                    current = handle.read()
            if Without_Font_Data(current) != Without_Font_Data(markup):
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
