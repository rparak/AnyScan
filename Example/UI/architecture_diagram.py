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

"""
Description:
    Initialization of constants.

    The generator of images/anyscan-architecture.svg, the diagram the README opens with.
    Regenerating is the way to change it; the SVG is never edited by hand. Every colour comes
    from a Parameters/Theme.py token and every size from the console's type scale, so the
    figure moves with the theme instead of drifting from it. The logo is copied into the
    diagram byte for byte from images/anyscan-logo.svg: the README shows the diagram through
    <img>, and an SVG loaded that way never fetches another file.

    test/UI/test_brand_figures.py fails when the committed SVG is not this script's output, or
    draws a colour that is not a token.

        python Example/UI/architecture_diagram.py            # rewrite the SVG
        python Example/UI/architecture_diagram.py --check    # exit 1 if it is stale

    The layout is checked against FALLBACK font metrics (Helvetica/Arial and Courier), which
    is what most README readers get: an <img> SVG cannot load Inter or JetBrains Mono. A
    layout that only fits with Inter installed will overflow for them.
"""
# The source logo, and the diagram this script writes.
#   Unit [string]
CONST_LOGO_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-logo.svg')
CONST_DIAGRAM_FILE = os.path.join(CONST_PROJECT_FOLDER, 'images', 'anyscan-architecture.svg')
# The marker comments around the inline logo; the test reads the copy between them.
#   Unit [string]
CONST_LOGO_BEGIN = '<!-- logo:begin -->'
CONST_LOGO_END = '<!-- logo:end -->'
# The drawing size in user units. README width (~830 px) renders it at ~0.94.
#   Unit [px]
CONST_WIDTH = 880
CONST_HEIGHT = 1950
# The console's type scale (Style.CONST_TYPE_SCALE, in points) at 1.2x, so the smallest step
# still renders above 10 px at README width.
#   Unit [Vector<float>]
CONST_SCALE = [round(size * 1.2, 1) for size in Style.CONST_TYPE_SCALE]
# The font stacks: the console's own candidates in its order, then the generic family.
#   Unit [string]
CONST_UI_FONT = ','.join(["'%s'" % name for name in Style.CONST_FONT_UI_CANDIDATES] + ['sans-serif'])
CONST_MONO_FONT = ','.join(["'%s'" % name for name in Style.CONST_FONT_MONO_CANDIDATES] + ['monospace'])


class Svg_Canvas_Cls(object):
    """
    Description:
        A list of SVG elements with the few drawing primitives the diagram is made of: text,
        boxes, arrows and the labelled chips that say what moves between stages. Every colour
        a caller passes is a Theme token.

    Initialization of the Class:
        Example:
            Initialization:
                # Initialization of the class.
                Cls = Svg_Canvas_Cls()

            Features:
                # Functions of the class.
                Cls.Add(element); Cls.Text(x, y, text, size, fill); Cls.Box(...)
                Cls.Markup()
    """

    def __init__(self) -> None:
        # << PRIVATE >> #
        self.__elements = []

    def Add(self, element: str) -> None:
        """
        Description:
            Append raw SVG markup.

        Args:
            (1) element [string]: The markup.
        """

        self.__elements.append(element)

    def Markup(self) -> str:
        """
        Description:
            The document so far, one element per line.

        Returns:
            (1) parameter [string]: The SVG text, with a trailing newline.
        """

        return '\n'.join(self.__elements) + '\n'

    def Text(self, x: float, y: float, text: str, size: float, fill: str, mono: bool = False,
             weight: tp.Optional[str] = None, anchor: tp.Optional[str] = None,
             spacing: tp.Optional[str] = None) -> None:
        """
        Description:
            One line of text in the UI or the mono face.

        Args:
            (1 - 2) x, y [float]: The baseline position.
            (3) text [string]: The text (escaped here).
            (4) size [float]: The font size, a step of CONST_SCALE.
            (5) fill [string]: A Theme colour token.
            (6) mono [bool]: The mono face (code names) instead of the UI face.
            (7) weight [string]: The font weight, or None for regular.
            (8) anchor [string]: 'middle' or 'end', or None for start.
            (9) spacing [string]: The letter spacing, or None.
        """

        attributes = ''.join([' font-weight="%s"' % weight if weight else '',
                              ' text-anchor="%s"' % anchor if anchor else '',
                              ' letter-spacing="%s"' % spacing if spacing else ''])
        self.Add('<text x="%s" y="%s" class="%s" font-size="%s" fill="%s"%s>%s</text>'
                 % (x, y, 'm' if mono else 'u', size, fill, attributes, escape(text)))

    def Rect(self, x: float, y: float, w: float, h: float, fill: str, stroke: tp.Optional[str] = None,
             rx: float = 12, stroke_width: float = 1, dash: tp.Optional[str] = None) -> None:
        """
        Description:
            A rounded rectangle.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) fill [string]: A Theme colour token, or 'none'.
            (6) stroke [string]: A Theme colour token for the outline, or None for none.
            (7) rx [float]: The corner radius.
            (8) stroke_width [float]: The outline width.
            (9) dash [string]: The outline's dash pattern, or None for solid.
        """

        attributes = ' stroke="%s" stroke-width="%s"' % (stroke, stroke_width) if stroke else ''
        attributes += ' stroke-dasharray="%s"' % dash if dash else ''
        self.Add('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"%s/>'
                 % (x, y, w, h, rx, fill, attributes))

    def Line(self, x1: float, y1: float, x2: float, y2: float, stroke: str, width: float = 1,
             dash: tp.Optional[str] = None) -> None:
        """
        Description:
            A plain line: a divider or the Qt-free boundary.

        Args:
            (1 - 4) x1, y1, x2, y2 [float]: The end points.
            (5) stroke [string]: A Theme colour token.
            (6) width [float]: The line width.
            (7) dash [string]: The dash pattern, or None for solid.
        """

        attributes = ' stroke-dasharray="%s"' % dash if dash else ''
        self.Add('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s"%s/>'
                 % (x1, y1, x2, y2, stroke, width, attributes))

    def Arrow(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """
        Description:
            A straight arrow: data or an import, in the direction it flows.

        Args:
            (1 - 4) x1, y1, x2, y2 [float]: The tail and the head.
        """

        self.Add('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.8" '
                 'stroke-linecap="round" marker-end="url(#arch-tip)"/>' % (x1, y1, x2, y2, Theme.CONST_INK_SOFT))

    def Path(self, d: str, stroke: str = Theme.CONST_INK_SOFT, arrow: bool = True,
             dash: tp.Optional[str] = None, width: float = 1.8) -> None:
        """
        Description:
            A routed path: a branching arrow, or a dashed configuration connector.

        Args:
            (1) d [string]: The path data.
            (2) stroke [string]: A Theme colour token.
            (3) arrow [bool]: Whether the path ends in an arrowhead.
            (4) dash [string]: The dash pattern, or None for solid.
            (5) width [float]: The stroke width.
        """

        attributes = ' stroke-dasharray="%s"' % dash if dash else ''
        attributes += ' marker-end="url(#arch-tip)"' if arrow else ''
        self.Add('<path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
                 'stroke-linejoin="round"%s/>' % (d, stroke, width, attributes))

    def Badge(self, cx: float, cy: float, number: str, dark: bool = False) -> None:
        """
        Description:
            A stage number in a disc, the numbering Vision/Core.py uses (stages 1-4).

        Args:
            (1 - 2) cx, cy [float]: The disc's centre.
            (3) number [string]: The stage number.
            (4) dark [bool]: Drawn on a dark (model) box.
        """

        self.Add('<circle cx="%s" cy="%s" r="12" fill="%s"/>'
                 % (cx, cy, Theme.CONST_ON_INK if dark else Theme.CONST_INK))
        self.Text(cx, cy + 5, number, CONST_SCALE[3], Theme.CONST_VIEWPORT if dark else Theme.CONST_ON_INK,
                  weight='700', anchor='middle')

    def Chip(self, cx: float, cy: float, lines: tp.List[str]) -> None:
        """
        Description:
            What moves between two stages, as a label on the arrow joining them.

        Args:
            (1 - 2) cx, cy [float]: The chip's centre.
            (3) lines [Vector<string>]: One or two lines of mono text.
        """

        w = max(len(line) for line in lines) * CONST_SCALE[1] * 0.62 + 24
        h = 16 * len(lines) + 12
        self.Rect(cx - w / 2, cy - h / 2, w, h, Theme.CONST_CARD, Theme.CONST_CONTROL_BORDER,
                  rx=h / 2 if len(lines) == 1 else 10)
        for i, line in enumerate(lines):
            self.Text(cx, cy - h / 2 + 19 + 16 * i, line, CONST_SCALE[1], Theme.CONST_INK_SOFT,
                      mono=True, anchor='middle')

    def Box(self, x: float, y: float, w: float, h: float, title: str, module: str, lines: tp.List[str],
            number: tp.Optional[str] = None, dark: bool = False, stroke: tp.Optional[str] = None,
            stroke_width: float = 1, title_size: tp.Optional[float] = None) -> None:
        """
        Description:
            A stage or an input: its title, the code that implements it, and what it does. A model
            (FastSAM, Gemma) is drawn dark, on the console's one dark surface colour.

        Args:
            (1 - 4) x, y, w, h [float]: The position and size.
            (5) title [string]: The title.
            (6) module [string]: The module and names that implement it.
            (7) lines [Vector<string>]: What it does, one entry per line.
            (8) number [string]: The stage number, or None.
            (9) dark [bool]: A model box.
            (10) stroke [string]: An outline token other than the card border, or None.
            (11) stroke_width [float]: The outline width.
            (12) title_size [float]: The title size, or None for the default step.
        """

        self.Rect(x, y, w, h, Theme.CONST_VIEWPORT if dark else Theme.CONST_CARD,
                  None if dark else (stroke or Theme.CONST_CARD_BORDER), stroke_width=stroke_width)
        title_x = x + 16
        if number:
            self.Badge(x + 28, y + 26, number, dark)
            title_x = x + 50
        self.Text(title_x, y + 31, title, title_size or CONST_SCALE[4],
                  Theme.CONST_ON_INK if dark else Theme.CONST_INK, weight='700')
        self.Text(x + 16, y + 52, module, CONST_SCALE[1],
                  Theme.CONST_VIEWPORT_TEXT if dark else Theme.CONST_INK_SOFT, mono=True)
        for i, line in enumerate(lines):
            self.Text(x + 16, y + 74 + 18 * i, line, CONST_SCALE[3],
                      Theme.CONST_BAND_TEXT if dark else Theme.CONST_INK_SOFT)

    def Pill(self, y: float, h: float, lines: tp.List[str], to_y: tp.Optional[float] = None) -> None:
        """
        Description:
            A configuration section in the left column, level with the stage it feeds, with a
            dashed connector to that stage when there is one to point at.

        Args:
            (1) y [float]: The top.
            (2) h [float]: The height.
            (3) lines [Vector<string>]: The section (first, bold), then what it sets.
            (4) to_y [float]: The connector's height, or None for no connector.
        """

        self.Rect(32, y, 176, h, Theme.CONST_CARD, Theme.CONST_CONTROL_BORDER, rx=10)
        for i, line in enumerate(lines):
            self.Text(42, y + 20 + 16 * i, line, CONST_SCALE[0] + 0.4,
                      Theme.CONST_INK if i == 0 else Theme.CONST_INK_SOFT, mono=True,
                      weight='700' if i == 0 else None)
        if to_y is not None:
            self.Path('M208 %s H222' % to_y, Theme.CONST_INK_MUTE, arrow=False, dash='3 3', width=1.4)

    def Section(self, y: float, label: str, sub: tp.Optional[str] = None, x: float = 32) -> None:
        """
        Description:
            A section heading, with an optional mono qualifier after it.

        Args:
            (1) y [float]: The baseline.
            (2) label [string]: The heading, in capitals.
            (3) sub [string]: The qualifier, or None.
            (4) x [float]: The start.
        """

        self.Text(x, y, label, CONST_SCALE[1], Theme.CONST_INK_SOFT, weight='700', spacing='1.4')
        if sub:
            self.Text(x + len(label) * CONST_SCALE[1] * 0.78 + 10, y, sub, CONST_SCALE[1],
                      Theme.CONST_INK_SOFT, mono=True)


def Draw_Architecture(logo_svg: str) -> str:
    """
    Description:
        The whole diagram, top to bottom: the header with the logo, the configuration column
        beside the pipeline (the two cues side by side into the fusion, then description,
        compose and measure, with what each stage hands on), the shared outputs, and the import
        layers with the Qt-free boundary. Everything drawn is in the code; nothing is planned.

    Args:
        (1) logo_svg [string]: The content of images/anyscan-logo.svg, inlined unchanged.

    Returns:
        (1) parameter [string]: The SVG document.
    """

    S = CONST_SCALE; T = Theme
    c = Svg_Canvas_Cls()
    c.Add('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
          'aria-label="AnyScan architecture">' % (CONST_WIDTH, CONST_HEIGHT, CONST_WIDTH, CONST_HEIGHT))
    c.Add('<!-- Generated by Example/UI/architecture_diagram.py; regenerate, do not edit by hand. -->')
    c.Add('<title>AnyScan architecture</title>')
    c.Add('<desc>How AnyScan turns a camera frame into a reading. Background subtraction and FastSAM are two '
          'independent cues fused so an object survives if either finds it; each object records its cue. Each '
          'object is cropped, enhanced and described by Gemma 4; Reporting composes the reading and the objects '
          'are measured through the calibration scale. One configuration file, read by Configuration.Core, sets '
          'the camera, the models, the prompts, the fusion and the thresholds. One formatter renders both the '
          'panel and the text file. The layers import downward only, with Parameters at the base; everything '
          'below the UI is Qt-free.</desc>')
    c.Add('<defs><style>.u{font-family:%s;} .m{font-family:%s;} .logo-slot svg{overflow:visible;}</style>'
          '<marker id="arch-tip" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
          'orient="auto"><path d="M1 1 L9 5 L1 9" fill="none" stroke="%s" stroke-width="1.8" '
          'stroke-linecap="round" stroke-linejoin="round"/></marker></defs>'
          % (CONST_UI_FONT, CONST_MONO_FONT, T.CONST_INK_SOFT))
    # The card: opaque, so the figure reads the same on a light or a dark README, like a screenshot.
    c.Rect(0.5, 0.5, CONST_WIDTH - 1, CONST_HEIGHT - 1, T.CONST_BG, T.CONST_CARD_BORDER, rx=18)

    """
    Description:
        The header: the logo (its own palette, which predates the theme) and the title.
    """
    c.Add('<g class="logo-slot" transform="translate(32,30) scale(0.28)">')
    c.Add(CONST_LOGO_BEGIN)
    c.Add(logo_svg.strip())
    c.Add(CONST_LOGO_END)
    c.Add('</g>')
    c.Text(848, 54, 'Architecture', S[7], T.CONST_INK, weight='700', anchor='end')
    c.Text(848, 76, 'what the code does today, and what imports what', S[3], T.CONST_INK_SOFT, anchor='end')
    c.Line(32, 102, 848, 102, T.CONST_CARD_BORDER)
    c.Section(134, 'CONFIGURATION')
    c.Section(134, 'PIPELINE', 'Vision_Pipeline_Cls.Analyze', x=224)

    """
    Description:
        The configuration column's head, and the two inputs: the reference feeds stage 1, the
        camera's frame feeds both cues.
    """
    c.Rect(32, 150, 176, 104, T.CONST_CARD, T.CONST_CONTROL_BORDER, rx=10)
    c.Text(42, 172, 'One file, one reader', S[3], T.CONST_INK, weight='700')
    for i, line in enumerate(['Config_*_Mode_*.yaml', '+ Calibration_*.yaml', 'Load_Configuration →']):
        c.Text(42, 192 + 16 * i, line, S[0] + 0.4, T.CONST_INK_SOFT, mono=True)
    c.Text(42, 244, 'Configuration_Str', S[1], T.CONST_INK, mono=True, weight='700')
    c.Box(224, 150, 300, 104, 'Empty-surface reference', 'Segmentation.Background.Reference',
          ['one shot from this camera; its sidecar', 'is checked against the sensor window'])
    c.Box(548, 150, 300, 104, 'Camera', 'Camera.Basler_Camera_Cls',
          ['sensor window pinned from Camera.*;', 'frame undistorted by the calibration'])
    c.Arrow(374, 254, 374, 306)
    c.Text(382, 284, 'reference', S[2], T.CONST_INK_SOFT, mono=True)
    c.Arrow(698, 254, 698, 306)
    c.Path('M698 272 H470 V306')
    c.Text(706, 284, 'RGB frame', S[2], T.CONST_INK_SOFT, mono=True)

    """
    Description:
        Stages 1 and 2 side by side: independent cues, neither gating the other.
    """
    c.Pill(318, 82, ['Segmentation.*', 'Background.* → 1', 'Model · Confidence', 'IoU · Image_Size → 2'], 358)
    c.Box(224, 308, 300, 100, 'Background subtraction', 'Segmentation.Background_Foreground',
          ['frame vs reference: absdiff → blur', '→ floored Otsu → open → dilate'], number='1')
    c.Box(548, 308, 300, 100, 'FastSAM', 'Segmenter.Fast_Sam_Cls',
          ['everything-mode instance masks', 'on the whole frame'], number='2', dark=True)
    c.Arrow(374, 408, 374, 472)
    c.Arrow(698, 408, 698, 472)
    c.Chip(374, 440, ['foreground mask'])
    c.Chip(698, 440, ['masks + scores'])
    c.Text(536, 436, 'two independent', S[1], T.CONST_INK, weight='700', anchor='middle')
    c.Text(536, 452, 'cues', S[1], T.CONST_INK, weight='700', anchor='middle')

    """
    Description:
        Stage 3, the fusion, and the cue attribution it hands on.
    """
    c.Pill(486, 82, ['Segmentation', '.Fusion.*', 'Close_Kernel · area', 'background fractions'], 526)
    c.Box(224, 474, 624, 120, 'Fusion — an object survives if either cue finds it',
          'Vision.Utilities.Fusion.Fuse_Objects',
          ['FastSAM union (background-like masks dropped) OR the foreground mask',
           '→ close → connected components → area filter → left to right;',
           'each object records the cue(s) that located it'], number='3', stroke=T.CONST_BRAND, stroke_width=2)
    c.Arrow(536, 594, 536, 674)
    c.Chip(536, 634, ['per object: Mask · Bbox · Cue = both | fastsam | background',
                      'Change_Coverage · Segmenter_Score (a FastSAM cue only)'])

    """
    Description:
        Stage 4: crop enhancement, then Gemma.
    """
    c.Pill(708, 98, ['Description.*', 'Model · Prompts', 'Object_Crop_Padding', 'Background', '_Crop_Margin'], 758)
    c.Rect(224, 676, 624, 306, 'none', T.CONST_CARD_BORDER, rx=14, dash='5 4')
    c.Badge(252, 702, '4')
    c.Text(274, 707, 'Description — each object, in order', S[4], T.CONST_INK, weight='700')
    c.Box(240, 722, 592, 102, 'Crop enhancement', 'Vision.Utilities.Enhancement: Isolate_Crop · Enhance_Crop',
          ['padded crop; every other object filled from the reference;',
           'contrast-stretched from the object’s own pixels'], title_size=S[3] + 1.2)
    c.Arrow(536, 824, 536, 870)
    c.Chip(536, 847, ['Enhanced_Crop'])
    c.Box(240, 872, 592, 102, 'Gemma 4 E4B', 'Vision.Describers.Gemma_Describer_Cls',
          ['object prompt on each Enhanced_Crop → Detail → Condense_Label → Label',
           'background prompt on the reference, once (cached) → background sentence'],
          dark=True, title_size=S[3] + 1.2)
    c.Add('<g transform="translate(0,16)">')
    c.Arrow(536, 966, 536, 1022)
    c.Chip(536, 994, ['Label · Detail per object + one background sentence'])

    """
    Description:
        Compose, then the measurement, then the result to the UI.
    """
    c.Box(224, 1024, 624, 84, 'Compose', 'Reporting.Core: Compose · Verdict',
          ['each object’s Sentence, the scene note and the verdict — objects are never reordered'])
    c.Arrow(536, 1108, 536, 1142)
    c.Pill(1144, 66, ['Scale', 'from the calibration', 'mm per px'], 1186)
    c.Box(224, 1144, 624, 84, 'Measure', 'Vision.Utilities.Measure.Measure_Objects',
          ['each mask through the scale: A × B, Ø, or A/F for hex parts; none without one'])
    c.Arrow(536, 1228, 536, 1270)
    c.Chip(536, 1249, ['Analysis_Str → the UI, via a worker off the GUI thread'])

    """
    Description:
        The outputs: one formatter for the panel and the .txt, one renderer for the viewport
        and the saved images.
    """
    c.Section(1300, 'OUTPUT', 'one source per rendering', x=224)
    c.Pill(1316, 100, ['To the UI', 'Confidence.* bands', 'General', '.Classification', 'Identity.* pill'])
    c.Box(224, 1316, 300, 100, 'One formatter', 'Reporting.Core',
          ['Object_Label · Object_Confidence ·', 'Object_Size → Screen_Understanding'])
    c.Box(548, 1316, 300, 100, 'One renderer', 'Vision.Utilities.Annotate',
          ['Draw_Annotated · Draw_Label_Mask,', 'colours from Parameters.Theme'])
    for cx in (374, 698):
        c.Path('M%s 1416 V1432 H%s V1446' % (cx, cx - 75))
        c.Path('M%s 1432 H%s V1446' % (cx, cx + 75))
    for cx, name, where in ((299, 'Live panel', 'UI.Widgets'), (449, '.txt files', 'capture · analyze.py'),
                            (623, 'Viewport', 'UI.Core'), (773, 'Images', 'capture · analyze.py')):
        c.Rect(cx - 73, 1448, 146, 50, T.CONST_CARD, T.CONST_CONTROL_BORDER, rx=10)
        c.Text(cx, 1469, name, S[3], T.CONST_INK, weight='700', anchor='middle')
        c.Text(cx, 1488, where, S[0], T.CONST_INK_SOFT, mono=True, anchor='middle')

    """
    Description:
        The layers, as the imports between src/ packages are: every edge points down, and
        nothing below the UI imports Qt.
    """
    c.Line(32, 1526, 848, 1526, T.CONST_CARD_BORDER)
    c.Section(1556, 'LAYERS', 'every import points down')
    c.Rect(32, 1572, 816, 66, T.CONST_CARD, T.CONST_CARD_BORDER)
    c.Text(48, 1600, 'UI', S[4], T.CONST_INK, weight='700')
    c.Text(76, 1600, 'PyQt5 — Live · Trends · History · Log, Configuration dialog, Workers', S[3], T.CONST_INK_SOFT)
    c.Text(48, 1624, 'imports Vision · Logger · Camera · Configuration · Reporting · Parameters   '
           '(App/run.py → UI + domain)', S[1] - 0.8, T.CONST_INK_SOFT, mono=True)
    c.Line(32, 1658, 848, 1658, T.CONST_INK, width=1.5, dash='6 4')
    c.Rect(31, 1647, 190, 22, T.CONST_BG, None, rx=0)
    c.Text(42, 1663, 'Qt-free below this line', S[2] + 1.2, T.CONST_INK, weight='700')
    c.Rect(482, 1647, 366, 22, T.CONST_BG, None, rx=0)
    c.Text(848, 1663, 'tested: test_contracts.py, test_module_is_qt_free', S[1] - 0.8, T.CONST_INK_SOFT,
           mono=True, anchor='end')
    for x, y, w, name, what in ((32, 1682, 260, 'Vision', 'the pipeline above'),
                                (322, 1682, 250, 'Calibration', 'used by calibrate.py only'),
                                (602, 1682, 246, 'Logger', 'session log · run CSV'),
                                (32, 1770, 210, 'Reporting', 'formatter · Trends'),
                                (292, 1770, 250, 'Camera', 'Basler · file · undistort'),
                                (602, 1770, 246, 'Configuration', 'the one YAML reader')):
        c.Rect(x, y, w, 56, T.CONST_CARD, T.CONST_CARD_BORDER, rx=10)
        c.Text(x + 14, y + 24, name, S[3] + 1.2, T.CONST_INK, weight='700')
        c.Text(x + 14, y + 44, what, S[1] - 0.8, T.CONST_INK_SOFT, mono=True)
    # Vision -> Reporting, Camera; Calibration -> Camera; Logger -> Configuration.
    c.Arrow(137, 1738, 137, 1768)
    c.Path('M280 1738 L312 1768')
    c.Arrow(447, 1738, 447, 1768)
    c.Arrow(725, 1738, 725, 1768)
    # Vision and Calibration also import Parameters directly (through the gaps in the row).
    c.Arrow(267, 1738, 267, 1846)
    c.Arrow(560, 1738, 560, 1846)
    for x in (137, 417, 725):
        c.Arrow(x, 1826, x, 1846)
    c.Rect(32, 1848, 816, 44, T.CONST_INK, None, rx=10)
    c.Text(48, 1876, 'Parameters', S[3] + 1.2, T.CONST_ON_INK, weight='700')
    c.Text(152, 1876, '*_Str dataclasses and Theme tokens — imports nothing of the project', S[1] - 0.8,
           T.CONST_BAND_TEXT, mono=True)
    c.Text(32, 1916, 'Not drawn: src/Transformation (inherited; the app never imports it) and the model-free '
           'fallback describer (analyze.py --no-describe only).', S[0] - 0.4, T.CONST_INK_SOFT)
    c.Add('</g>')
    c.Add('</svg>')
    return c.Markup()


def main():
    """
    Description:
        Write images/anyscan-architecture.svg from the theme and the logo, or with --check report
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
