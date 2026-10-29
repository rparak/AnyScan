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
# File Name: JIC_SF_UI/Qss.py
## =========================================================================== ##

# JIC_SF_UI: the palette
from . import Theme as T

"""
Description:
    The stylesheet builder: one function per control kind, every rule from theme tokens. Three rules hold for every
    stylesheet here, and for any you add:

      1. Every state rule names its fill AND its label (and its border). Qt picks a rule by how many pseudo-states its
         selector names, not by order, so a fill-only ':hover:enabled' can pair with the label of ':checked' (white on
         a near-white hover, 1.08:1, seen in AnyScan). Scope hover rules to :checked / :!checked.
      2. Container backgrounds use an #objectName selector, never a bare 'background:', which cascades into every
         child and paints blocks behind titles.
      3. No corner radius anywhere: the brand draws every block, tag and button square. A radius is a regression
         (tests/test_style.py::test_no_corner_is_rounded scans for one).
"""


def Root(name: str = 'root') -> str:
    """
    Description:
        The window's central widget: the white page.

    Args:
        (1) name [string]: The widget's objectName.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    return '#%s { background: %s; }' % (name, T.CONST_BG)


def Card(name: str = 'card') -> str:
    """
    Description:
        A card: white fill, 1 px grey-lilac outline, square.

    Args:
        (1) name [string]: The card's objectName.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    return '#%s { background: %s; border: 1px solid %s; }' % (name, T.CONST_CARD, T.CONST_CARD_BORDER)


def Band(name: str = 'card') -> str:
    """
    Description:
        The funding band: a solid purple block, its border the purple itself.

    Args:
        (1) name [string]: The band's objectName.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    return '#%s { background: %s; border: 1px solid %s; }' % (name, T.CONST_BAND, T.CONST_BAND)


def Tool_Button(primary: bool = False) -> str:
    """
    Description:
        An action button (48 px, uppercase, tracked). Plain: 1 px purple rule on white; hover grey-lilac, pressed
        periwinkle, the label purple throughout. Primary (one per row): 2 px rule; hover and pressed fill purple under
        a white label. Disabled: the outline fades to the divider and the label to #B4A6BE, on white.

    Args:
        (1) primary [bool]: The row's one primary action.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    if primary:
        return """
            QPushButton { background: %(card)s; border: 2px solid %(ink)s; color: %(ink)s; }
            QPushButton:hover:enabled { background: %(hover)s; border-color: %(hover)s; color: %(on_ink)s; }
            QPushButton:pressed:enabled { background: %(pressed)s; border-color: %(pressed)s; color: %(on_ink)s; }
            QPushButton:disabled { background: %(off_fill)s; border-color: %(off_border)s; color: %(off_text)s; }
        """ % {'card': T.CONST_CARD, 'ink': T.CONST_INK, 'on_ink': T.CONST_ON_INK, 'hover': T.CONST_INK_HOVER,
               'pressed': T.CONST_INK_PRESSED, 'off_fill': T.CONST_PRIMARY_DISABLED_FILL,
               'off_border': T.CONST_CONTROL_DISABLED_BORDER, 'off_text': T.CONST_PRIMARY_DISABLED_TEXT}
    return """
        QPushButton { background: %(card)s; border: 1px solid %(border)s; color: %(ink)s; }
        QPushButton:hover:enabled { background: %(hover)s; border-color: %(hover_border)s; color: %(ink)s; }
        QPushButton:pressed:enabled { background: %(pressed)s; border-color: %(hover_border)s; color: %(ink)s; }
        QPushButton:disabled { background: %(card)s; border-color: %(off_border)s; color: %(off_text)s; }
    """ % {'card': T.CONST_CARD, 'border': T.CONST_CONTROL_BORDER, 'ink': T.CONST_INK, 'hover': T.CONST_CONTROL_HOVER,
           'hover_border': T.CONST_CONTROL_HOVER_BORDER, 'pressed': T.CONST_CONTROL_PRESSED,
           'off_border': T.CONST_CONTROL_DISABLED_BORDER, 'off_text': T.CONST_CONTROL_DISABLED_TEXT}


def Segment(index: int) -> str:
    """
    Description:
        One segment of a segmented control (tabs, a view toggle, a filter): outlined in the purple, neighbours sharing
        one 1 px rule (no left rule after the first), the checked segment purple under a white label.

    Args:
        (1) index [int]: The segment's position (0 draws its left rule).

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    return """
        QPushButton { background: %(card)s; border: 1px solid %(border)s; color: %(ink)s;
                      padding: 0 16px; border-left-width: %(left)dpx; }
        QPushButton:!checked:hover:enabled { background: %(hover)s; color: %(ink)s; }
        QPushButton:checked { background: %(ink)s; border-color: %(ink)s; color: %(on_ink)s; }
        QPushButton:checked:hover:enabled { background: %(ink_hover)s; border-color: %(ink_hover)s; color: %(on_ink)s; }
        QPushButton:!checked:disabled { background: %(card)s; border-color: %(off_border)s; color: %(off_text)s; }
        QPushButton:checked:disabled { background: %(ink)s; border-color: %(ink)s; color: %(off_text)s; }
    """ % {'card': T.CONST_CARD, 'border': T.CONST_CONTROL_BORDER, 'ink': T.CONST_INK, 'hover': T.CONST_CONTROL_HOVER,
           'ink_hover': T.CONST_INK_HOVER, 'on_ink': T.CONST_ON_INK, 'off_border': T.CONST_CONTROL_DISABLED_BORDER,
           'off_text': T.CONST_CONTROL_DISABLED_TEXT, 'left': 1 if index == 0 else 0}


def Badge(level: str) -> str:
    """
    Description:
        A badge (24 px, 8 pt Bold): the purple words on its state's ground ('ok' periwinkle, 'fail' #FFD9D0, 'warn'
        the amber), its border the ground; any other level is idle: muted words on the card in a grey-lilac rule.

    Args:
        (1) level [string]: 'ok', 'warn', 'fail' or anything else for idle.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    verdict = {'ok': 'OK', 'warn': 'Warning', 'fail': 'NOK'}.get(level)
    if verdict is not None:
        ground = T.Label_Ground(verdict)
        border, bg, fg = ground, ground, T.CONST_INK
    else:
        border, bg, fg = T.CONST_CARD_BORDER, T.CONST_CARD, T.CONST_INK_MUTE
    return 'border: 1px solid %s; background: %s; color: %s; padding: 0 9px;' % (border, bg, fg)


def Pill(border: str, ink: str, line: str = 'solid', name: str = '') -> str:
    """
    Description:
        A header status pill (31 px, 9 pt DemiBold): the card fill, a 1 px border and the status words in the
        colour's text twin. Idle: grey-lilac border, muted words. Ready: the JIC green border, green words. Not loaded:
        a dashed purple border.

    Args:
        (1) border [string]: The border token.
        (2) ink [string]: The status colour (its text twin is used for the words).
        (3) line [string]: 'solid' or 'dashed'.
        (4) name [string]: An objectName to scope the rule to (a pill that holds children), or '' for a QLabel.

    Returns:
        (1) parameter [string]: The stylesheet.
    """

    body = 'border: 1px %s %s; background: %s; color: %s; padding: 0 12px;' % (line, border, T.CONST_CARD,
                                                                            T.Status_Text_Color(ink))
    return '#%s { %s }' % (name, body) if name else body
