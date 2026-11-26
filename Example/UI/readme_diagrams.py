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
# File Name: ../Example/UI/readme_diagrams.py
## =========================================================================== ##

# System (Default)
import sys
import os
import argparse
import re
import io
# Resolve the project folder from this file's own location (Example/UI -> ..), so the script
# runs the same whether launched from Example/UI/ or the repo root.
CONST_PROJECT_FOLDER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                    '..', '..'))
_SRC = os.path.join(CONST_PROJECT_FOLDER, 'src')
if _SRC not in sys.path:
    sys.path.append(_SRC)
# Typing (Support for type hints)
import typing as tp
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pillow (Drawing the images) [pip3 install Pillow]
from PIL import Image, ImageDraw, ImageFont
# Custom Lib.: AnyScan — the colour tokens, the ONLY source of the diagrams' colours
#   ../Parameters/Theme
import Parameters.Theme as Theme
# Custom Lib.: AnyScan UI — the pixel icons the application draws too (Qt-free)
#   ../../src/UI/Utilities/Pixel_Motif
from UI.Utilities.Pixel_Motif import Icon_Cells, CONST_ICON_GRID
# Custom Lib.: AnyScan — the one reader of a catalogue item file
#   ../Configuration/Core
from Configuration.Core import Load_Catalogue

"""
Description:
    Initialization of constants.

    The generator of the README's two light/dark figure pairs, shown through <picture>, and of its models table:
    images/anyscan-pipeline-{light,dark}.png, a frame's way to the record in the station's order (frame -> find ->
    measure -> judge -> describe -> record, the judge step a catalogue mode's only); images/anyscan-catalogue-item-
    {light,dark}.webp, the shipped catalogue item's card (its reference images and what it is checked on, read from
    Data/Catalogue/mounting_plate/ through Configuration.Core.Load_Catalogue); and the README's models table
    (Models_Table: each model's role, what it runs on, the revision install.sh pins and its download size, read from
    install.sh, never typed here).

    Light: the window's white card, purple words, grey-lilac rules. Dark: a transparent ground under white words and
    periwinkle rules, for GitHub's dark page. Every colour is a Parameters/Theme.py token, every icon one of the
    application's pixel icons, and the words are set in the bundled OFL fonts (App/assets/fonts), drawn into the
    image, so a reader without Public Sans sees the same picture. Each image is drawn at twice the README's width
    (~880 px), so its smallest words render at 13 px there.

    Regenerating is the way to change them; the images are never edited by hand. test/UI/test_readme_diagrams.py
    fails when a committed image is not this script's output (the WebP pair within CONST_LOSSY_TOLERANCE), or when
    the README's models table is not Models_Table().

        .venv/bin/python Example/UI/readme_diagrams.py              # rewrite the four images
        .venv/bin/python Example/UI/readme_diagrams.py --check      # exit 1 if one is stale
        .venv/bin/python Example/UI/readme_diagrams.py --out <dir>  # write them into another folder
"""
# The images folder, the fonts, and the installer the pins and sizes are read from.
#   Unit [string]
CONST_IMAGES_FOLDER = os.path.join(CONST_PROJECT_FOLDER, 'images')
CONST_FONT_FOLDER = os.path.join(CONST_PROJECT_FOLDER, 'App', 'assets', 'fonts')
CONST_INSTALLER = os.path.join(CONST_PROJECT_FOLDER, 'install.sh')
CONST_README = os.path.join(CONST_PROJECT_FOLDER, 'README.md')
# The files this script writes, each a light and a dark version.
#   Unit [List<string>]
CONST_FIGURES = ['anyscan-pipeline-%s.png', 'anyscan-catalogue-item-%s.webp']
# The item card holds photographs, so it is WebP at this quality (lossless would be about 1 MB a version). A lossy
# file is compared with this script's pixels block by block: no CONST_LOSSY_BLOCK px square may differ by more than
# CONST_LOSSY_TOLERANCE on average per channel. The encoder's own error peaks at about 10 there (2026-11-26); one
# changed character of the card moves its block by about 88.
#   Unit [int] / [int] (px) / [float] (0-255)
CONST_WEBP_QUALITY = 92
CONST_LOSSY_BLOCK = 16
CONST_LOSSY_TOLERANCE = 24.0
# The drawing width: twice the README's ~880 px, so 26 px words render at 13 px there.
#   Unit [px]
CONST_WIDTH = 1760
# The pixel icons' cell, so an icon is 12 cells of 3 px (36 px) as in the architecture diagram.
#   Unit [px]
CONST_ICON_CELL = 3
# The faces, per weight: Public Sans for words, JetBrains Mono for machine values (a revision, a size).
#   Unit [Dictionary<Tuple<string, int>, string>]
CONST_FACES = {('sans', 400): 'PublicSans-Regular.ttf', ('sans', 600): 'PublicSans-SemiBold.ttf',
               ('sans', 700): 'PublicSans-Bold.ttf', ('mono', 500): 'JetBrainsMono-Medium.ttf'}


def Font(size: int, weight: int = 400, mono: bool = False) -> ImageFont.FreeTypeFont:
    """
    Description:
        One of the bundled faces at a pixel size.

    Args:
        (1) size [int]: The size in px.
        (2) weight [int]: 400, 600 or 700 (500 for the mono face).
        (3) mono [bool]: JetBrains Mono instead of Public Sans.

    Returns:
        (1) parameter [ImageFont.FreeTypeFont]: The font.
    """

    return ImageFont.truetype(os.path.join(CONST_FONT_FOLDER, CONST_FACES[('mono' if mono else 'sans', weight)]), size)


def Wrap(text: str, font: ImageFont.FreeTypeFont, width: float) -> tp.List[str]:
    """
    Description:
        Words broken into lines no wider than a width (a single longer word keeps its own line).

    Args:
        (1) text [string]: The words.
        (2) font [ImageFont.FreeTypeFont]: The font they are set in.
        (3) width [float]: The width in px.

    Returns:
        (1) parameter [List<string>]: The lines.
    """

    lines, line = [], ''
    for word in text.split(' '):
        trial = (line + ' ' + word).strip()
        if font.getlength(trial) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def Rgba(hex_color: str, alpha: float = 1.0) -> tp.Tuple[int, int, int, int]:
    """
    Description:
        A Theme colour as an RGBA tuple at an opacity.

    Args:
        (1) hex_color [string]: A Theme token's '#RRGGBB'.
        (2) alpha [float]: The opacity, 0 to 1.

    Returns:
        (1) parameter [Tuple<int, int, int, int>]: The colour.
    """

    return Theme.Hex_To_Rgb(hex_color) + (round(255 * alpha),)


def Colors(dark: bool) -> tp.Dict[str, tp.Any]:
    """
    Description:
        The roles of one version, each a Theme token: the ground, the card's fill and edge, the words, the secondary
        words, the arrows, the catalogue tag and its group's dashed edge.

    Args:
        (1) dark [bool]: The dark version (transparent ground, white words, periwinkle rules).

    Returns:
        (1) parameter [Dictionary<string, Any>]: Each role's RGBA colour.
    """

    if not dark:
        return {'ground': Rgba(Theme.CONST_CARD), 'card': Rgba(Theme.CONST_CARD), 'edge': Rgba(Theme.CONST_CARD_BORDER),
                'ink': Rgba(Theme.CONST_INK), 'mute': Rgba(Theme.CONST_INK_MUTE), 'arrow': Rgba(Theme.CONST_INK),
                'tag': Rgba(Theme.CONST_BRAND), 'tag_ink': Rgba(Theme.CONST_ON_INK),
                'group': Rgba(Theme.CONST_SCROLLBAR_HANDLE)}
    return {'ground': (0, 0, 0, 0), 'card': (0, 0, 0, 0), 'edge': Rgba(Theme.CONST_SCROLLBAR_HANDLE),
            'ink': Rgba(Theme.CONST_ON_INK), 'mute': Rgba(Theme.CONST_BAND_TEXT, Theme.CONST_BAND_TEXT_ALPHA),
            'arrow': Rgba(Theme.CONST_SCROLLBAR_HANDLE), 'tag': Rgba(Theme.CONST_ON_INK),
            'tag_ink': Rgba(Theme.CONST_INK), 'group': Rgba(Theme.CONST_SCROLLBAR_HANDLE)}


class Canvas_Cls(object):
    """
    Description:
        One image being drawn, with the few marks the two diagrams share: a card with its pixel icon and title, a
        state badge, an arrow and a dashed group.

    Initialization of the Class:
        Args:
            (1) height [int]: The image's height in px.
            (2) dark [bool]: The dark version.
    """

    def __init__(self, height: int, dark: bool) -> None:
        self.c = Colors(dark)
        self.image = Image.new('RGBA', (CONST_WIDTH, height), self.c['ground'])
        self.draw = ImageDraw.Draw(self.image)

    def Text(self, x: float, y: float, text: str, font: ImageFont.FreeTypeFont, role: str,
             anchor: str = 'ls') -> None:
        """
        Description:
            Words on a baseline in a role's colour.

        Args:
            (1 - 2) x, y [float]: The anchor point.
            (3) text [string]: The words.
            (4) font [ImageFont.FreeTypeFont]: The font.
            (5) role [string]: A key of Colors().
            (6) anchor [string]: Pillow's text anchor.
        """

        self.draw.text((x, y), text, font=font, fill=self.c[role], anchor=anchor)

    def Icon(self, x: float, y: float, name: str) -> None:
        """
        Description:
            A pixel icon of the application's set (Pixel_Motif.Icon_Cells) in whole cells, in the words' colour.

        Args:
            (1 - 2) x, y [float]: The top-left corner.
            (3) name [string]: The key in Pixel_Motif.CONST_PIXEL_ICONS.
        """

        for column, row in Icon_Cells(name):
            self.draw.rectangle([x + column * CONST_ICON_CELL, y + row * CONST_ICON_CELL,
                                 x + (column + 1) * CONST_ICON_CELL - 1, y + (row + 1) * CONST_ICON_CELL - 1],
                                fill=self.c['ink'])

    def Card(self, x: float, y: float, w: float, h: float, icon: str, title: str, title_font: ImageFont.FreeTypeFont,
             title_gap: float) -> float:
        """
        Description:
            A square card: its 2 px edge, its pixel icon at the top right and its title, wrapped clear of the icon.

        Args:
            (1 - 4) x, y, w, h [float]: The card's box.
            (5) icon [string]: The pixel icon.
            (6) title [string]: The title.
            (7) title_font [ImageFont.FreeTypeFont]: The title's font.
            (8) title_gap [float]: The distance between two title lines.

        Returns:
            (1) parameter [float]: The baseline under the title, where the card's words start.
        """

        self.draw.rectangle([x, y, x + w, y + h], fill=self.c['card'], outline=self.c['edge'], width=2)
        self.Icon(x + w - 24 - CONST_ICON_GRID * CONST_ICON_CELL, y + 22, icon)
        baseline = y + 54
        for line in Wrap(title, title_font, w - 48 - 56):
            self.Text(x + 24, baseline, line, title_font, 'ink')
            baseline += title_gap
        return baseline + 2

    def Badge(self, x: float, y: float, state: str, size: int, h: int) -> float:
        """
        Description:
            A state badge: the purple word on the state's ground (Theme.Label_Ground), square, as the console's.

        Args:
            (1 - 2) x, y [float]: The top-left corner.
            (3) state [string]: OK, NOK or Warning.
            (4) size [int]: The word's size in px.
            (5) h [int]: The badge's height.

        Returns:
            (1) parameter [float]: The badge's width.
        """

        font = Font(size, 700)
        w = font.getlength(state) + 0.9 * h
        self.draw.rectangle([x, y, x + w, y + h], fill=Theme.Hex_To_Rgb(Theme.Label_Ground(state)) + (255,))
        self.draw.text((x + w / 2, y + h / 2), state, font=font, fill=Theme.Hex_To_Rgb(Theme.CONST_INK) + (255,),
                       anchor='mm')
        return w

    def Arrow(self, x1: float, x2: float, y: float) -> None:
        """
        Description:
            A horizontal arrow from one card to the next.

        Args:
            (1 - 2) x1, x2 [float]: Its tail and its tip.
            (3) y [float]: Its height.
        """

        self.draw.line([(x1, y), (x2 - 12, y)], fill=self.c['arrow'], width=3)
        self.draw.polygon([(x2, y), (x2 - 16, y - 9), (x2 - 16, y + 9)], fill=self.c['arrow'])

    def Dashed_Rect(self, box: tp.Tuple[float, float, float, float]) -> None:
        """
        Description:
            A dashed group edge (12 px dashes, 10 px gaps), as the architecture diagram marks a catalogue mode's steps.

        Args:
            (1) box [Tuple<float, float, float, float>]: Its left, top, right and bottom.
        """

        x0, y0, x1, y1 = box
        for ax, ay, bx, by in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
            length = abs(bx - ax) + abs(by - ay)
            sx, sy = (bx - ax) / length, (by - ay) / length
            p = 0.0
            while p < length:
                q = min(p + 12, length)
                self.draw.line([(ax + sx * p, ay + sy * p), (ax + sx * q, ay + sy * q)], fill=self.c['group'], width=3)
                p = q + 10


# The pipeline diagram's steps, in the station's order for a catalogue mode (README > Architecture: a catalogue
# mode measures, recognises and checks each object before it is described, and tells the describer what the checks
# found): each step's pixel icon, its name and its words. The catalogue mode's own step is CONST_CATALOGUE_STEP.
#   Unit [List<Tuple<string, string, string>>]
CONST_PIPELINE_STEPS = [('camera', 'Frame', 'SCAN takes one frame once nothing moves'),
                        ('magnifier', 'Find', 'what changed against the empty table, OR FastSAM segmentation'),
                        ('ruler', 'Measure', 'the size in mm, through the calibration'),
                        ('badge', 'Judge', 'DINOv2 recognises the part, the checks give a verdict'),
                        ('text', 'Describe', 'a local vision-language model, told what the checks found'),
                        ('log', 'Record', 'capture set, session log, run summary')]
CONST_CATALOGUE_STEP = 'Judge'


def Draw_Pipeline(dark: bool) -> Image.Image:
    """
    Description:
        A frame's way to the record, left to right, in the station's order for a catalogue mode
        (CONST_PIPELINE_STEPS): Frame, Find, Measure, Judge (the catalogue mode's step, in a dashed group with its tag,
        its three states as badges), Describe and Record. A detect-only mode skips Judge.

    Args:
        (1) dark [bool]: The dark version.

    Returns:
        (1) parameter [Image.Image]: The image.
    """

    canvas = Canvas_Cls(560, dark)
    title, body = Font(32, 700), Font(26, 400)
    n = len(CONST_PIPELINE_STEPS)
    w, gap, y, h = 250, 44, 96, 370
    x0 = (CONST_WIDTH - n * w - (n - 1) * gap) / 2
    for i, (icon, name, words) in enumerate(CONST_PIPELINE_STEPS):
        x = x0 + i * (w + gap)
        baseline = canvas.Card(x, y, w, h, icon, name, title, 40)
        for line in Wrap(words, body, w - 48):
            canvas.Text(x + 24, baseline, line, body, 'ink')
            baseline += 36
        if name == CONST_CATALOGUE_STEP:
            for row, states in enumerate([['OK', 'NOK'], ['Warning']]):
                bx = x + 24
                for state in states:
                    bx += canvas.Badge(bx, baseline - 8 + row * 46, state, 20, 38) + 8
            canvas.Dashed_Rect((x - 10, y - 10, x + w + 10, y + h + 10))
            tag = Font(24, 700)
            tw = tag.getlength('catalogue mode') + 28
            canvas.draw.rectangle([x + w / 2 - tw / 2, y - 52, x + w / 2 + tw / 2, y - 16], fill=canvas.c['tag'])
            canvas.Text(x + w / 2, y - 34, 'catalogue mode', tag, 'tag_ink', anchor='mm')
        if i < n - 1:
            canvas.Arrow(x + w + 6, x + w + gap - 6, y + h / 2)
    canvas.Text(x0, 530, 'The order of a catalogue mode. A detect-only mode skips Judge.', body, 'mute')
    return canvas.image


def Installer_Value(text: str, name: str) -> str:
    """
    Description:
        A constant's value in install.sh (a quoted shell assignment at the start of a line, possibly several lines).

    Args:
        (1) text [string]: install.sh.
        (2) name [string]: The constant.

    Returns:
        (1) parameter [string]: Its value.
    """

    return re.search(r"^%s='([^']*)'" % name, text, re.M | re.S).group(1)


def Files_Size(text: str, name: str) -> int:
    """
    Description:
        The sum of the sizes in a file list of install.sh ('name size kind hash' per line).

    Args:
        (1) text [string]: install.sh.
        (2) name [string]: The list's constant.

    Returns:
        (1) parameter [int]: The bytes.
    """

    return sum(int(line.split()[1]) for line in Installer_Value(text, name).splitlines() if line.strip())


def Size_Text(total: int) -> str:
    """
    Description:
        A download's size as the README's models table writes it: GB to one decimal, else whole MB (10^6 bytes).

    Args:
        (1) total [int]: The bytes.

    Returns:
        (1) parameter [string]: The size.
    """

    return '%.1f GB' % (total / 1e9) if total >= 1e9 else '%d MB' % round(total / 1e6)


def Read_Installer() -> tp.Dict[str, str]:
    """
    Description:
        What the models table states about the models, read from install.sh: each pin shortened to 7 characters, and
        each download's size (the sum of its files) in MB or GB, rounded as the README's models table rounds it.

    Returns:
        (1) parameter [Dictionary<string, string>]: The pins and the sizes.
    """

    with open(CONST_INSTALLER, 'r', encoding='utf-8') as handle:
        text = handle.read()
    tag = re.search(r'releases/download/(v[\d.]+)/FastSAM-x\.pt', text).group(1)
    return {'fastsam_pin': '%s · sha256 %s' % (tag, Installer_Value(text, 'CONST_FASTSAM_SHA256')[:7]),
            'fastsam_size': Size_Text(int(Installer_Value(text, 'CONST_FASTSAM_SIZE'))),
            'gemma_pin': 'revision ' + Installer_Value(text, 'CONST_GEMMA_REVISION')[:7],
            'gemma_size': Size_Text(Files_Size(text, 'CONST_GEMMA_FILES')),
            'dino_pin': 'revision ' + Installer_Value(text, 'CONST_DINOV2_REVISION')[:7],
            'dino_size': Size_Text(Files_Size(text, 'CONST_DINOV2_FILES'))}


def Models_Table() -> str:
    """
    Description:
        The README's models table (README > Architecture), Markdown, its pins and download sizes read from install.sh
        (Read_Installer): each model, what it does, what it runs on, its pin and its download. The README holds it
        word for word; test/UI/test_readme_diagrams.py and --check fail when it does not.

    Returns:
        (1) parameter [string]: The table, one row per line.
    """

    pins = Read_Installer()
    rows = [('Model', 'What it does', 'Runs on', 'Pinned by the installer', 'Download'),
            ('---', '---', '---', '---', '---:'),
            ('FastSAM-x', "finds every object, and a part's holes", 'PyTorch (ultralytics)',
             '`%s`' % pins['fastsam_pin'], pins['fastsam_size']),
            ('Gemma 4 E4B, 4-bit', 'describes each object in words: the local vision-language model',
             'MLX: Metal on macOS, CUDA on Linux', '`%s`' % pins['gemma_pin'], pins['gemma_size']),
            ('DINOv2 base', 'recognises the catalogued part and its side (catalogue modes only)',
             'PyTorch (transformers)', '`%s`' % pins['dino_pin'], pins['dino_size'])]
    return '\n'.join('| %s |' % ' | '.join(row) for row in rows)


# The catalogue item the README's item card draws, and how much of each reference frame round the part it shows (the
# part's box from the reference's sidecar, widened by this share of its size on each side).
#   Unit [string] / [float]
CONST_CATALOGUE_ITEM = os.path.join(CONST_PROJECT_FOLDER, 'Data', 'Catalogue', 'mounting_plate', 'mounting_plate.yaml')
CONST_REFERENCE_MARGIN = 0.22


def Item_Rows(item: tp.Any) -> tp.List[tp.Tuple[str, tp.List[str]]]:
    """
    Description:
        What the item card lists, from the loaded item: its outline with the tolerance, each side's hole groups, the
        stain check by the side's name, and its known defects.

    Args:
        (1) item [Catalogue_Item_Str]: The item, as Configuration.Core.Load_Catalogue reads it.

    Returns:
        (1) parameter [List<Tuple<string, List<string>>>]: Each label and its lines.
    """

    names = {side.Side: side.Name for side in item.Sides}
    rows = [('OUTLINE', ['%g × %g mm, ± %g mm' % (item.Outline.Length_Mm, item.Outline.Width_Mm, item.Tolerance_Mm)])]
    for side, groups in item.Holes.items():
        lines = []
        for group in groups:
            line = '%d %ss, Ø %g mm' % (group.Count, group.Name, group.Diameter_Mm)
            lines.append(line + (', %g mm apart' % group.Pitch_Mm if group.Pitch_Mm else ''))
        rows.append(('HOLES, %s' % names.get(side, side).upper(), lines))
    for side, stain in item.Stain.items():
        rows.append(('STAINS', ['none of %g mm² or more on the %s' % (stain.Min_Area_Mm2, names.get(side, side))]))
    rows.append(('KNOWN DEFECTS', ['%s, on the %s' % (defect.Name, names.get(defect.Side, defect.Side))
                                   for defect in item.Defects]))
    return rows


def Draw_Catalogue_Item(dark: bool) -> Image.Image:
    """
    Description:
        The README's catalogue item card (README > Catalogue mode): the item's reference image of each side, cropped
        round the part by its sidecar's box and named by the side, beside the item's name and what it is checked on
        (Item_Rows), all read through Configuration.Core.Load_Catalogue from Data/Catalogue/mounting_plate/. Every word
        is 26 px or more, so 13 px or more at the README's width.

    Args:
        (1) dark [bool]: The dark version.

    Returns:
        (1) parameter [Image.Image]: The image.
    """

    item = Load_Catalogue(CONST_CATALOGUE_ITEM)
    names = {side.Side: side.Name for side in item.Sides}
    canvas = Canvas_Cls(720, dark)
    title, body, label = Font(36, 700), Font(28, 400), Font(26, 700)
    x, top, photo_h = 40, 40, 580
    for reference in item.References:
        with Image.open(reference.Image_Path) as frame:
            frame = frame.convert('RGB')
            cx, cy, w, h = reference.Box
            W, H = frame.size
            left, right = (cx - w / 2 - w * CONST_REFERENCE_MARGIN) * W, (cx + w / 2 + w * CONST_REFERENCE_MARGIN) * W
            upper, lower = (cy - h / 2 - h * CONST_REFERENCE_MARGIN / 2) * H, (cy + h / 2 + h * CONST_REFERENCE_MARGIN / 2) * H
            crop = frame.crop((round(left), round(upper), round(right), round(lower)))
        crop = crop.resize((round(crop.width * photo_h / crop.height), photo_h), Image.LANCZOS)
        canvas.image.paste(crop, (x, top))
        canvas.draw.rectangle([x, top, x + crop.width - 1, top + photo_h - 1], outline=canvas.c['edge'], width=2)
        canvas.Text(x, top + photo_h + 44, names.get(reference.Side, reference.Side), body, 'ink')
        x += crop.width + 32
    x += 40
    canvas.Text(x, top + 40, item.Display_Name, title, 'ink')
    baseline = top + 40
    for name, lines in Item_Rows(item):
        baseline += 62
        canvas.Text(x, baseline, name, label, 'mute')
        for line in lines:
            baseline += 40
            canvas.Text(x, baseline, line, body, 'ink')
    return canvas.image


def Figures() -> tp.Dict[str, Image.Image]:
    """
    Description:
        Every image this script writes, by file name.

    Returns:
        (1) parameter [Dictionary<string, Image.Image>]: The images.
    """

    figures = {}
    for name, draw in zip(CONST_FIGURES, [Draw_Pipeline, Draw_Catalogue_Item]):
        for dark in (False, True):
            image = draw(dark)
            figures[name % ('dark' if dark else 'light')] = image if dark else image.convert('RGB')
    return figures


def Same_Pixels(path: str, image: Image.Image) -> bool:
    """
    Description:
        Whether a file holds these pixels (compared decoded, so the encoder's settings do not matter): a PNG exactly, a
        WebP within the lossy tolerance of every CONST_LOSSY_BLOCK square.

    Args:
        (1) path [string]: The committed image.
        (2) image [Image.Image]: This script's output.

    Returns:
        (1) parameter [bool]: True when the pixels match.
    """

    if not os.path.exists(path):
        return False
    with Image.open(path) as committed:
        if committed.mode != image.mode or committed.size != image.size:
            return False
        if path.endswith('.webp'):
            n = CONST_LOSSY_BLOCK
            difference = np.abs(np.asarray(committed, dtype=float) - np.asarray(image, dtype=float)).mean(axis=2)
            h, w = (difference.shape[0] // n) * n, (difference.shape[1] // n) * n
            blocks = difference[:h, :w].reshape(h // n, n, w // n, n).mean(axis=(1, 3))
            return float(blocks.max()) <= CONST_LOSSY_TOLERANCE
        return np.array_equal(np.asarray(committed), np.asarray(image))


def Save(image: Image.Image, path: str) -> None:
    """
    Description:
        Write an image with no metadata: a PNG optimised, a WebP at CONST_WEBP_QUALITY (its alpha exact).

    Args:
        (1) image [Image.Image]: The image.
        (2) path [string]: The file.
    """

    if path.endswith('.webp'):
        image.save(path, 'WEBP', quality=CONST_WEBP_QUALITY, method=6, exact=True)
    else:
        image.save(path, optimize=True)


def main():
    """
    Description:
        Write the four images into images/ (or --out), with no metadata, or with --check report whether a committed
        one is stale.

            .venv/bin/python Example/UI/readme_diagrams.py [--check | --out <dir>]
    """

    parser = argparse.ArgumentParser(description="Generate the README's pipeline diagram and catalogue item card, light "
                                                 "and dark, and check its models table.")
    parser.add_argument('--check', action='store_true',
                        help='do not write; exit 1 if a committed image differs from the output')
    parser.add_argument('--out', default=CONST_IMAGES_FOLDER, help='the folder to write into (default: images/)')
    args = parser.parse_args()

    stale = 0
    for name, image in Figures().items():
        if args.check:
            path = os.path.join(CONST_IMAGES_FOLDER, name)
            if Same_Pixels(path, image):
                print('[INFO] %s is up to date.' % path)
            else:
                print('[ERROR] %s is stale or was edited by hand; regenerate it with this script.' % path)
                stale = 1
            continue
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, name)
        Save(image, path)
        print('[INFO] Wrote %s.' % path)
    with open(CONST_README, 'r', encoding='utf-8') as handle:
        if Models_Table() not in handle.read():
            print('[%s] README.md does not hold the models table install.sh gives; paste this in:\n%s'
                  % ('ERROR' if args.check else 'WARNING', Models_Table()))
            stale = 1 if args.check else stale
    return stale


if __name__ == '__main__':
    sys.exit(main())
