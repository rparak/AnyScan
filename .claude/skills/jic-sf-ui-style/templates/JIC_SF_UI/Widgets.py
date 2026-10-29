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
# File Name: JIC_SF_UI/Widgets.py
## =========================================================================== ##

# System (Default)
import math
import re
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QTimer, QRect, QRectF, QPoint, QPointF, QByteArray, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QFontMetrics, QFontMetricsF, QIcon, QImage, QPainter, QPen, QPixmap, QPaintEvent, QRegion
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QButtonGroup, QLayout, QVBoxLayout, QHBoxLayout,
                             QSizePolicy)
# JIC_SF_UI: tokens and style helpers, the stylesheet builder, grid-fitting and the pixel set
from . import Style
from . import Qss
from .Style import Font, Hairline
from .Grid_Fit import CONST_THIN_PX, Fit_Svg
from .Pixel_Motif import (Motif_Cells, Corner_Cells, Busy_Cells, Icon_Cells, Grid_Shape, Wave_Diagonals,
                          CONST_ICON_GRID)

"""
Description:
    The reusable JIC Smart Factory widgets, generalised from AnyScan's src/UI/Widgets.py and the header in
    src/UI/Core.py (its vision, catalogue and camera logic removed). Every widget is a behaviour class with the _Cls
    suffix; paintEvent stays camelCase because Qt dispatches it by name. Sizes are AnyScan's: change one only with a
    reason recorded where the project keeps its design decisions.
"""
# A state swatch's side (a filter segment's icon, a legend square).
#   Unit [px]
CONST_SWATCH_PX = 10
# The inspection area's line width on screen, drawn unantialiased on whole pixels.
#   Unit [px]
CONST_INSPECTION_AREA_W = 1


def Digit_Variants(text: str) -> tp.List[str]:
    """
    Description:
        A text with every digit replaced by each of 0-9 in turn: the widest is as wide as any text of its shape.

    Args:
        (1) text [string]: The text.

    Returns:
        (1) parameter [Vector<string>]: The variants (the text alone when it has no digit).
    """

    if not re.search(r'\d', text):
        return [text]
    return [re.sub(r'\d', digit, text) for digit in '0123456789']


def Swatch_Icon(color: str) -> QIcon:
    """
    Description:
        A state's swatch as an icon: a CONST_SWATCH_PX square in the state's colour, edged in that same colour.

    Args:
        (1) color [string]: The state's token.

    Returns:
        (1) parameter [QIcon(object)]: The icon.
    """

    ratio = 2
    pixmap = QPixmap(CONST_SWATCH_PX * ratio, CONST_SWATCH_PX * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(Style.Token_Color(color))
    p.setPen(QPen(Style.Token_Color(color), 1.25))
    p.drawRect(QRectF(0.625, 0.625, CONST_SWATCH_PX - 1.25, CONST_SWATCH_PX - 1.25))
    p.end()
    return QIcon(pixmap)


def Paint_Inspection_Area(p: QPainter, draw_rect: QRectF, frame_size: tp.Tuple[int, int],
                          area_px: tp.Tuple[float, float, float, float],
                          color: str = Style.CONST_INSPECTION_AREA) -> None:
    """
    Description:
        A screen-only inspection area over an image drawn at draw_rect: 1 px, solid, square, unfilled, on whole
        pixels; the light amber over a camera image, CONST_INSPECTION_AREA_EMPTY (the purple) over the empty view.

    Args:
        (1) p [QPainter(object)]: The active painter (its state is restored).
        (2) draw_rect [QRectF(object)]: Where the image lies, letterboxed.
        (3) frame_size [Vector<int> 1x2]: The image's (width, height).
        (4) area_px [Tuple<float> 1x4]: The area on the image as (left, top, right, bottom).
        (5) color [string]: The line's token.
    """

    sx, sy = draw_rect.width() / frame_size[0], draw_rect.height() / frame_size[1]
    left, top, right, bottom = area_px
    rect = QRect(int(round(draw_rect.left() + left * sx)), int(round(draw_rect.top() + top * sy)), 0, 0)
    rect.setRight(int(round(draw_rect.left() + right * sx)))
    rect.setBottom(int(round(draw_rect.top() + bottom * sy)))
    p.save()
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setPen(QPen(Style.Token_Color(color), CONST_INSPECTION_AREA_W, Qt.SolidLine, Qt.SquareCap, Qt.MiterJoin))
    p.setBrush(Qt.NoBrush)
    p.drawRect(rect)
    p.restore()


def Meta_Row(parent_layout: QVBoxLayout, key: str, *, compact: bool = False, mono: bool = False,
             first: bool = False) -> QLabel:
    """
    Description:
        One key/value record row under a hairline (a card's foot): the key in the purple, the value right-aligned,
        starting as the no-value dash. Compact is the tighter rhythm of a panel read up close.

    Args:
        (1) parent_layout [QVBoxLayout(object)]: The layout to add the row to.
        (2) key [string]: The key.
        (3) compact [bool]: Less padding, a size smaller, a regular-weight value.
        (4) mono [bool]: A machine value (a time, a size, a percentage) in JetBrains Mono.
        (5) first [bool]: Omit the top hairline.

    Returns:
        (1) parameter [QLabel(object)]: The value label.
    """

    pad, size = (6, 9.5) if compact else (9, 10)
    row = QWidget()
    if not first:
        row.setStyleSheet('border-top: 1px solid %s;' % Style.CONST_LINE)
    line = QHBoxLayout(row)
    line.setContentsMargins(2, pad, 2, pad)
    label = QLabel(key)
    label.setFont(Font(size))
    label.setStyleSheet('color: %s; border: none;' % Style.CONST_INK_SOFT)
    line.addWidget(label)
    line.addStretch(1)
    value = QLabel(Style.CONST_NO_VALUE)
    value.setFont(Font(9 if mono else size, QFont.Normal if compact else QFont.Medium, mono=mono))
    value.setStyleSheet('color: %s; border: none;' % Style.CONST_INK)
    line.addWidget(value)
    parent_layout.addWidget(row)
    return value


class Card_Cls(QFrame):
    """
    Description:
        The white card every panel sits in: 1 px grey-lilac outline, square, 16 px padding. Exposes `box`, the
        vertical layout content is added to.
    """

    def __init__(self, padding: int = 16, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('card')
        self.setStyleSheet(Qss.Card('card'))
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(padding, padding, padding, padding)
        self.box.setSpacing(0)


class Icon_Cls(QWidget):
    """
    Description:
        A pixel icon of the one set (Pixel_Motif.CONST_PIXEL_ICONS): its cells as whole squares of `cell` logical px,
        never antialiased, so every cell is a crisp square at 1x and at DPR 2. The widget is the whole 12-cell square,
        so every icon aligns alike whatever its ink.
    """

    # A card head's cell: 12 cells of 2 px, a 24 px icon beside the 15.5 pt title; its 2 px top margin drops it 1 px
    # below centred, so its ink centres 1.5 px above the title's capitals.
    #   Unit [px]
    CONST_HEAD_CELL = 2
    CONST_HEAD_DROP = 2

    def __init__(self, name: str, cell: int = CONST_HEAD_CELL, color: str = Style.CONST_INK,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__name = name
        self.__cells = Icon_Cells(name)
        self.__cell = cell
        self.__color = color

        self.setFixedSize(CONST_ICON_GRID * cell, CONST_ICON_GRID * cell)

    def Name(self) -> str:
        """
        Description:
            The icon's key in CONST_PIXEL_ICONS.

        Returns:
            (1) parameter [string]: The key.
        """

        return self.__name

    @classmethod
    def Head_Layout(cls, name: str) -> QVBoxLayout:
        """
        Description:
            A head's icon in its layout cell, dropped CONST_HEAD_DROP: for a card head and a dialog's title.

        Args:
            (1) name [string]: The icon.

        Returns:
            (1) parameter [QVBoxLayout(object)]: The layout holding the icon.
        """

        box = QVBoxLayout()
        box.setContentsMargins(0, cls.CONST_HEAD_DROP, 0, 0)
        box.addWidget(cls(name))
        return box

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        color = Style.Token_Color(self.__color)
        for column, row in self.__cells:
            p.fillRect(column * self.__cell, row * self.__cell, self.__cell, self.__cell, color)
        p.end()


class Badge_Cls(QLabel):
    """
    Description:
        A state badge, 24 px, 8 pt Bold: the purple words on the state's ground (Qss.Badge), the word carrying the
        state as well as the colour ('All OK', 'NOK · 2', 'Warning · 1'); muted on the card when idle.
    """

    def __init__(self, text: str = 'Idle', parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setFont(Font(8, QFont.Bold))
        self.setFixedHeight(24)
        self.Set_Level('idle')

    def Set_Level(self, level: str) -> None:
        """
        Description:
            Repaint for a level: 'ok', 'warn', 'fail' or anything else (idle).

        Args:
            (1) level [string]: The level.
        """

        self.setStyleSheet(Qss.Badge(level))

    def Set_State(self, text: str, level: str) -> None:
        """
        Description:
            Set the wording and the level together.

        Args:
            (1) text [string]: The wording.
            (2) level [string]: The level.
        """

        self.setText(text)
        self.Set_Level(level)


class Flow_Layout_Cls(QLayout):
    """
    Description:
        Widgets in right-aligned rows that wrap when the row is too narrow, each row as tall as its tallest widget:
        a badge row never clips or hides a badge.
    """

    def __init__(self, spacing: int, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self.setSpacing(spacing)

        # << PRIVATE >> #
        self.__items = []

    # << QT OVERRIDE >> #
    def addItem(self, item: tp.Any) -> None:
        self.__items.append(item)

    # << QT OVERRIDE >> #
    def count(self) -> int:
        return len(self.__items)

    # << QT OVERRIDE >> #
    def itemAt(self, index: int) -> tp.Any:
        return self.__items[index] if 0 <= index < len(self.__items) else None

    # << QT OVERRIDE >> #
    def takeAt(self, index: int) -> tp.Any:
        return self.__items.pop(index) if 0 <= index < len(self.__items) else None

    # << QT OVERRIDE >> #
    def expandingDirections(self) -> tp.Any:
        return Qt.Orientations(0)

    # << QT OVERRIDE >> #
    def hasHeightForWidth(self) -> bool:
        return True

    # << QT OVERRIDE >> #
    def heightForWidth(self, width: int) -> int:
        return self.__Arrange(QRect(0, 0, width, 0), place=False)

    # << QT OVERRIDE >> #
    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self.__Arrange(rect, place=True)

    # << QT OVERRIDE >> #
    def sizeHint(self) -> QSize:
        shown = [item.sizeHint() for item in self.__items if not item.isEmpty()]
        if not shown:
            return QSize(0, 0)
        return QSize(sum(s.width() for s in shown) + self.spacing() * (len(shown) - 1), max(s.height() for s in shown))

    # << QT OVERRIDE >> #
    def minimumSize(self) -> QSize:
        shown = [item.minimumSize() for item in self.__items if not item.isEmpty()]
        return QSize(max((s.width() for s in shown), default=0), max((s.height() for s in shown), default=0))

    def __Arrange(self, rect: QRect, place: bool) -> int:
        """
        Description:
            Lay the visible widgets out in right-aligned rows within the width, placing them when asked.

        Args:
            (1) rect [QRect(object)]: The rectangle.
            (2) place [bool]: Set the geometry, or only measure.

        Returns:
            (1) parameter [int]: The height taken.
        """

        gap = self.spacing()
        rows, row, row_width = [], [], 0
        for item in [item for item in self.__items if not item.isEmpty()]:
            width = item.sizeHint().width()
            if row and row_width + gap + width > rect.width():
                rows.append((row, row_width))
                row, row_width = [], 0
            row_width += (gap if row else 0) + width
            row.append(item)
        if row:
            rows.append((row, row_width))
        y = rect.y()
        for items, width in rows:
            height = max(item.sizeHint().height() for item in items)
            x = rect.x() + max(0, rect.width() - width)
            for item in items:
                size = item.sizeHint()
                if place:
                    item.setGeometry(QRect(QPoint(x, y + (height - size.height()) // 2), size))
                x += size.width() + gap
            y += height + gap
        return max(0, y - rect.y() - gap) if rows else 0


class Badge_Row_Cls(QWidget):
    """
    Description:
        A card head's badges, one per state that needs the person (NOK first, then Warning; 'All OK' when neither),
        right-aligned, wrapping onto a second row rather than clipping.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.__layout = Flow_Layout_Cls(6, self)
        policy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

        # << PRIVATE >> #
        self.__badges = []
        self.Set_Badges([('Idle', 'idle')])

    def Set_Badges(self, badges: tp.List[tp.Tuple[str, str]]) -> None:
        """
        Description:
            Show these (wording, level) badges, in order, and hide any left from before.

        Args:
            (1) badges [Vector<Tuple<string> 1x2>]: The badges.
        """

        while len(self.__badges) < len(badges):
            badge = Badge_Cls('')
            self.__layout.addWidget(badge)
            self.__badges.append(badge)
        for index, badge in enumerate(self.__badges):
            if index < len(badges):
                badge.Set_State(*badges[index])
            badge.setVisible(index < len(badges))
        self.__layout.invalidate()
        self.updateGeometry()

    def Badges(self) -> tp.List[Badge_Cls]:
        """
        Description:
            The badges shown now.

        Returns:
            (1) parameter [Vector<Badge_Cls(object)>]: The badges.
        """

        return [badge for badge in self.__badges if not badge.isHidden()]

    # << QT OVERRIDE >> #
    def hasHeightForWidth(self) -> bool:
        return True

    # << QT OVERRIDE >> #
    def heightForWidth(self, width: int) -> int:
        return self.__layout.heightForWidth(width)


class State_Marker_Cls(QWidget):
    """
    Description:
        The state marker in an image card's head, after the title: what the view shows while it is not a still
        result. White on a solid purple block (9.15:1), 9.5 pt DemiBold tracked 6 %, one size for every state (the
        widest's), so it never moves; an animated pixel icon in 2 px cells for a working state. Nothing of it is ever
        drawn inside the image.
    """

    # Each state's words and its busy icon (a key of Pixel_Motif.CONST_BUSY_STEPS, or None). A new state joins here.
    #   Unit [Dict<string, Tuple<string, string or None>>]
    CONST_STATES = {'preview': ('●  LIVE PREVIEW', None),
                    'scan': ('SCANNING…', 'camera'),
                    'analysis': ('ANALYZING…', 'magnifier')}
    CONST_ICON_CELL = 2
    CONST_PAD_X = 12
    CONST_PAD_Y = 6
    CONST_ICON_GAP = 10

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__state = ''
        self.__tick = 0
        self.__timer = QTimer(self)
        self.__timer.setInterval(Style.CONST_BUSY_TICK_MS)
        self.__timer.timeout.connect(self.__Tick)
        self.__font = Font(9.5, QFont.DemiBold, tracking=6)

        self.setFixedSize(max(self.__Width(state) for state in self.CONST_STATES),
                          QFontMetrics(self.__font).height() + 2 * self.CONST_PAD_Y)
        # Hidden, it keeps its size in the head, so naming a state never moves the view under it (where the marker is
        # taller than the title's line, as on macOS, showing it would grow the head and shrink the view).
        policy = self.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self.setSizePolicy(policy)
        self.setVisible(False)

    def Set_State(self, state: str) -> None:
        """
        Description:
            Mark a state (a key of CONST_STATES) or none (''); the icon's timer runs only while an icon shows.

        Args:
            (1) state [string]: The state, or ''.
        """

        if state == self.__state:
            return
        self.__state, self.__tick = state, 0
        if state and self.CONST_STATES[state][1] is not None:
            self.__timer.start()
        else:
            self.__timer.stop()
        self.setVisible(bool(state))
        self.update()

    def State(self) -> str:
        """
        Description:
            The state marked now, or ''.

        Returns:
            (1) parameter [string]: The state.
        """

        return self.__state

    def __Cells(self, state: str) -> tp.List[tp.Tuple[int, int, float]]:
        icon = self.CONST_STATES[state][1] if state else None
        return Busy_Cells(icon, self.__tick, Style.CONST_BUSY_DIM_ALPHA) if icon is not None else []

    def __Icon_Width(self, state: str) -> int:
        cells = self.__Cells(state)
        return (max(c for c, _, _ in cells) + 1) * self.CONST_ICON_CELL + self.CONST_ICON_GAP if cells else 0

    def __Width(self, state: str) -> int:
        words = QFontMetrics(self.__font).horizontalAdvance(self.CONST_STATES[state][0])
        return self.__Icon_Width(state) + words + 2 * self.CONST_PAD_X

    def __Tick(self) -> None:
        self.__tick += 1
        self.update()

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        if not self.__state:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        rect = self.rect()
        p.fillRect(rect, Style.Token_Color(Style.CONST_INK))
        cells, cell = self.__Cells(self.__state), self.CONST_ICON_CELL
        p.setFont(self.__font)
        p.setPen(Style.Token_Color(Style.CONST_ON_INK))
        spare = (rect.width() - self.__Width(self.__state)) // 2
        if cells:
            rows = max(r for _, r, _ in cells) + 1
            left, top = spare + self.CONST_PAD_X, (rect.height() - rows * cell) // 2
            for column, row, alpha in cells:
                p.fillRect(left + column * cell, top + row * cell, cell, cell, Style.Token_Color(Style.CONST_ON_INK, alpha))
        p.drawText(rect.adjusted(spare + self.__Icon_Width(self.__state), 0, -spare, 0), Qt.AlignCenter,
                   self.CONST_STATES[self.__state][0])
        p.end()


class Card_Head_Cls(QWidget):
    """
    Description:
        A card head: the pixel icon, the title (15.5 pt Bold, tracked -2 %, the purple), a stretch and at most one
        badge; or, with badge_row, a Badge_Row_Cls taking the width the title leaves. Exposes `box` (to insert a
        state marker after the title or a control at the right), `badge` and `badges`.
    """

    def __init__(self, icon: str, title: str, badge_text: tp.Optional[str] = None,
                 parent: tp.Optional[QWidget] = None, badge_row: bool = False) -> None:
        super().__init__(parent)
        self.box = QHBoxLayout(self)
        self.box.setContentsMargins(2, 2, 2, 14)
        self.box.setSpacing(10)
        self.box.addLayout(Icon_Cls.Head_Layout(icon))
        label = QLabel(title)
        label.setFont(Font(15.5, QFont.Bold, tracking=-2))
        label.setStyleSheet('color: %s;' % Style.CONST_INK)
        self.box.addWidget(label)
        self.badge, self.badges = None, None
        if badge_row:
            self.badges = Badge_Row_Cls()
            self.box.addWidget(self.badges, 1)
            return
        self.box.addStretch(1)
        if badge_text is not None:
            self.badge = Badge_Cls(badge_text)
            self.box.addWidget(self.badge)


class Tool_Button_Cls(QPushButton):
    """
    Description:
        An action button: 48 px tall, UPPERCASE, 9.5 pt DemiBold tracked 6 %, outlined in the purple, never narrower
        than its label plus 10 px each side. Exactly one per row is primary (Qss.Tool_Button).
    """

    CONST_LABEL_PAD = 10

    def __init__(self, text: str, primary: bool = False, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(text.upper(), parent)
        self.setFont(Font(9.5, QFont.DemiBold, tracking=6))
        self.setFixedHeight(48)
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(self.text()) + 2 * self.CONST_LABEL_PAD)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(Qss.Tool_Button(primary))


class Segmented_Control_Cls(QWidget):
    """
    Description:
        The ONE segmented control (the header's view tabs, a view toggle, a filter): checkable segments styled as one
        square pill, 30 px, 9 pt DemiBold tracked 2 %. Segment_Selected fires on a user click only; Set_Selection
        reflects a choice without emitting. The first segment starts selected.
    """

    # << SIGNAL >> #
    Segment_Selected = pyqtSignal(str)

    def __init__(self, segments: tp.Sequence[tp.Tuple[str, str]], height: int = 30,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        # << PRIVATE >> #
        self.__group = QButtonGroup(self)
        self.__group.setExclusive(True)
        self.__buttons = {}

        for index, (key, label) in enumerate(segments):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFont(Font(9, QFont.DemiBold, tracking=2))
            button.setFixedHeight(height)
            button.setStyleSheet(Qss.Segment(index))
            button.clicked.connect(lambda _checked, k=key: self.Segment_Selected.emit(k))
            self.__group.addButton(button)
            self.__buttons[key] = button
            row.addWidget(button)
        if self.__buttons:
            next(iter(self.__buttons.values())).setChecked(True)

    def Set_Selection(self, key: str) -> None:
        """
        Description:
            Select a segment without emitting Segment_Selected.

        Args:
            (1) key [string]: The segment.
        """

        button = self.__buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def Set_Segment_Icon(self, key: str, icon: QIcon) -> None:
        """
        Description:
            Put an icon before a segment's label (a state filter's Swatch_Icon).

        Args:
            (1) key [string]: The segment.
            (2) icon [QIcon(object)]: The icon.
        """

        self.__buttons[key].setIcon(icon)
        self.__buttons[key].setIconSize(QSize(CONST_SWATCH_PX, CONST_SWATCH_PX))

    def Set_Segment_Enabled(self, key: str, enabled: bool) -> None:
        """
        Description:
            Enable or disable a segment; an unavailable choice stays visible, greyed.

        Args:
            (1) key [string]: The segment.
            (2) enabled [bool]: Whether it can be chosen.
        """

        self.__buttons[key].setEnabled(enabled)

    def Selection(self) -> tp.Optional[str]:
        """
        Description:
            The selected segment's key.

        Returns:
            (1) parameter [string or None]: The key.
        """

        return next((key for key, button in self.__buttons.items() if button.isChecked()), None)


class Label_Pill_Cls(QLabel):
    """
    Description:
        A text-only header status pill, 31 px, 9 pt DemiBold, padded by its stylesheet (Qss.Pill), as AnyScan's camera
        pill: '●  Camera offline' (grey-lilac border, muted words) or '●  Camera connected' (green border, green words).
    """

    def __init__(self, text: str, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setFont(Font(9, QFont.DemiBold))
        self.setFixedHeight(31)
        self.Set_State(text, Style.CONST_CARD_BORDER, Style.CONST_INK_MUTE)

    def Set_State(self, text: str, border: str, ink: str, line: str = 'solid') -> None:
        """
        Description:
            Show a state: its words with their dot glyph, border token and status colour.

        Args:
            (1) text [string]: The words.
            (2) border [string]: The border token.
            (3) ink [string]: The status colour; the words take its text twin.
            (4) line [string]: 'solid' or 'dashed'.
        """

        self.setText(text)
        self.setStyleSheet(Qss.Pill(border, ink, line))


class Status_Pill_Cls(QWidget):
    """
    Description:
        A header status pill, 31 px: an optional pixel icon (1 px cells), an optional name and the status words with
        a leading dot glyph. Its three looks: idle (grey-lilac border, muted words, '●'), working (amber border, the
        amber's text twin, '◐'), ready (the JIC green border, the green's text twin, '●'); 'not loaded' is a dashed
        purple border with a hollow '○'. The state differs on dot, colour and outline at once.
    """

    def __init__(self, text: str, icon: tp.Optional[str] = None, name: tp.Optional[str] = None,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('pill')
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(31)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(7)

        # << PRIVATE >> #
        self.__icon = Icon_Cls(icon, 1, Style.CONST_INK_MUTE) if icon else None
        self.__name = QLabel(name) if name is not None else None
        self.__words = QLabel(text)

        if self.__icon is not None:
            row.addWidget(self.__icon)
        if self.__name is not None:
            self.__name.setFont(Font(9, QFont.DemiBold))
            self.__name.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
            row.addWidget(self.__name)
        self.__words.setFont(Font(9, QFont.DemiBold if self.__name is None else QFont.Normal))
        row.addWidget(self.__words)
        self.Set_State(text, Style.CONST_CARD_BORDER, Style.CONST_INK_MUTE)

    def Set_State(self, text: str, border: str, ink: str, line: str = 'solid',
                  name: tp.Optional[str] = None) -> None:
        """
        Description:
            Show a state: its words (with their dot glyph), border token, status colour and outline style.

        Args:
            (1) text [string]: The words, e.g. '●  Camera connected'.
            (2) border [string]: The border token.
            (3) ink [string]: The status colour; the words take its text twin.
            (4) line [string]: 'solid' or 'dashed'.
            (5) name [string or None]: The name to show (None keeps it).
        """

        self.__words.setText(text)
        self.__words.setStyleSheet('color: %s; border: none;' % Style.Status_Text_Color(ink))
        if name is not None and self.__name is not None:
            self.__name.setText(name)
        self.setStyleSheet('#pill { border: 1px %s %s; background: %s; }' % (line, border, Style.CONST_CARD))


class Stat_Cell_Cls(QWidget):
    """
    Description:
        One status-strip cell: an UPPERCASE label (8 pt Bold, tracked 7 %, muted) over its value: a count 18 pt Bold
        (read from across the room), a state 13.5 pt DemiBold, or a machine value 12 pt Medium in JetBrains Mono.
    """

    def __init__(self, label: str, value: str = '', big: bool = False, mono: bool = False,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(20, 13, 20, 13)
        col.setSpacing(5)
        caption = QLabel(label.upper())
        caption.setFont(Font(8, QFont.Bold, tracking=7))
        caption.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        col.addWidget(caption)

        # << PRIVATE >> #
        self.__value = QLabel(value)

        if big:
            self.__value.setFont(Font(18, QFont.Bold, tracking=-4))
        elif mono:
            self.__value.setFont(Font(12, QFont.Medium, mono=True))
        else:
            self.__value.setFont(Font(13.5, QFont.DemiBold, tracking=-2))
        self.__value.setStyleSheet('color: %s;' % Style.CONST_INK)
        col.addWidget(self.__value)
        col.addStretch(1)

    def Reserve_Width(self, texts: tp.Sequence[str], dot: bool = False,
                      weights: tp.Optional[tp.Sequence[int]] = None) -> None:
        """
        Description:
            Hold the value at the width of the widest text it can show (every digit standing for any digit), at every
            weight it can take, so a change of value never moves the columns beside it.

        Args:
            (1) texts [Vector<string>]: The widest value of each kind.
            (2) dot [bool]: The cell draws a status dot before its value.
            (3) weights [Vector<int> or None]: Every QFont weight the value can take (a severity ramp); None: its own.
        """

        font, widths = QFont(self.__value.font()), []
        for weight in (weights or [font.weight()]):
            font.setWeight(weight)
            metrics = QFontMetrics(font)
            widths += [metrics.horizontalAdvance(('●  ' if dot else '') + v) for t in texts for v in Digit_Variants(t)]
        self.__value.setMinimumWidth(max(widths) + 2)

    def Set_Value(self, text: str, color: tp.Optional[str] = None, dot_color: tp.Optional[str] = None) -> None:
        """
        Description:
            Set the value, optionally in a status colour (its words take the text twin) after a dot in the colour.

        Args:
            (1) text [string]: The value.
            (2) color [string or None]: The status colour.
            (3) dot_color [string or None]: The dot's colour.
        """

        ink = Style.Status_Text_Color(color or Style.CONST_INK)
        self.__value.setStyleSheet('color: %s;' % ink)
        if dot_color:
            self.__value.setTextFormat(Qt.RichText)
            self.__value.setText('<span style="color:%s">●</span>&nbsp;&nbsp;<span style="color:%s">%s</span>'
                                 % (dot_color, ink, text))
        else:
            self.__value.setText(text)


class Status_Strip_Cls(Card_Cls):
    """
    Description:
        Hairline-divided cells across the full width, under the central view: device state first, then counts, then
        derived aggregates (each label naming its scope and statistic, e.g. 'Inference (run median)').
    """

    def __init__(self, cells: tp.Sequence[tp.Tuple[str, str, str]], parent: tp.Optional[QWidget] = None) -> None:
        """
        Args:
            (1) cells [Vector<Tuple<string> 1x3>]: (key, label, kind) per cell; kind 'state', 'count' or 'mono'.
        """

        super().__init__(padding=0, parent=parent)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.cells = {}
        for index, (key, label, kind) in enumerate(cells):
            if index:
                row.addWidget(Hairline(vertical=True))
            cell = Stat_Cell_Cls(label, '0' if kind == 'count' else Style.CONST_NO_VALUE, big=kind == 'count',
                                 mono=kind == 'mono')
            self.cells[key] = cell
            row.addWidget(cell, 1)
        self.box.addLayout(row)


def Paint_To_Pixmap(widget: QWidget, paint: tp.Callable[[QPainter], None]) -> QPixmap:
    """
    Description:
        What a widget paints, on a transparent pixmap at its DPR: for measuring ink (Style.Ink_Insets), never drawn.

    Args:
        (1) widget [QWidget(object)]: The widget.
        (2) paint [function]: Paints its content with a painter.

    Returns:
        (1) parameter [QPixmap(object)]: The render.
    """

    ratio = max(1.0, float(widget.devicePixelRatioF()))
    pixmap = QPixmap(int(round(widget.width() * ratio)), int(round(widget.height() * ratio)))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    paint(painter)
    painter.end()
    return pixmap


def Svg_Renderer_For(painter: QPainter, path: str, delivered: QSvgRenderer, height: float, mark_right: float,
                     fitted: tp.Dict[float, QSvgRenderer], thin_px: float = CONST_THIN_PX) -> QSvgRenderer:
    """
    Description:
        The renderer to draw a logo with: on a DPR 1 device its mark (every straight shape left of mark_right)
        grid-fitted at the drawn height (built once per height), on any other the SVG as delivered.

    Args:
        (1) painter [QPainter(object)]: The painter it will be drawn with.
        (2) path [string]: The SVG file.
        (3) delivered [QSvgRenderer(object)]: Its renderer as delivered.
        (4) height [float]: The drawn height (logical px).
        (5) mark_right [float]: The mark's right edge in viewBox units (0: fit nothing).
        (6) fitted [Dict<float, QSvgRenderer(object)>]: The fitted renderers so far, by height (filled in).
        (7) thin_px [float]: Grid_Fit's thin-gap threshold.

    Returns:
        (1) parameter [QSvgRenderer(object)]: The renderer.
    """

    if painter.device().devicePixelRatioF() != 1.0 or mark_right <= 0.0:
        return delivered
    if height not in fitted:
        with open(path, 'r', encoding='utf-8') as handle:
            svg = handle.read()
        scale = height / delivered.viewBoxF().height()
        fitted[height] = QSvgRenderer(QByteArray(Fit_Svg(svg, scale, mark_right, thin_px).encode('utf-8')))
    return fitted[height]


class Svg_Image_Cls(QWidget):
    """
    Description:
        An SVG logo at a height, its width the viewBox's aspect, rendered as vectors at paint time (never a scaled
        pixmap), its mark grid-fitted at DPR 1.
    """

    def __init__(self, name: str, height: int, mark_right: float = 0.0, thin_px: float = CONST_THIN_PX,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__path = Style.Asset(name)
        self.__mark_right = mark_right
        self.__thin_px = thin_px
        self.__fitted = {}
        self.__renderer = QSvgRenderer(self.__path)
        box = self.__renderer.viewBoxF()
        self.__rect = QRectF(0.0, 0.0, height * box.width() / box.height() if box.height() else 0.0, float(height))

        self.setFixedSize(int(math.ceil(self.__rect.width())), height)

    def __Paint(self, painter: QPainter) -> None:
        Svg_Renderer_For(painter, self.__path, self.__renderer, self.__rect.height(), self.__mark_right,
                         self.__fitted, self.__thin_px).render(painter, self.__rect)

    def Render(self) -> QPixmap:
        """
        Description:
            The image on a transparent pixmap, for measuring its ink; never drawn.

        Returns:
            (1) parameter [QPixmap(object)]: The render.
        """

        return Paint_To_Pixmap(self, self.__Paint)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.__Paint(painter)
        painter.end()


class Logo_Lockup_Cls(QWidget):
    """
    Description:
        A product lockup: the delivered, outlined logo WITHOUT its tagline (an SVG rendered as vectors, its mark
        grid-fitted at DPR 1), and the tagline set as live Public Sans Regular text where the logo outlines it, in
        the logo's colour. Outlined small text is soft at DPR 1; live text is hinted at 9 pt and up.

    Initialization of the Class:
        Args:
            (1) file [string]: The tagline-less logo SVG (an asset name).
            (2) height [int]: The lockup's height (Style.Logo_Height).
            (3) tagline [string]: The tagline, or '' for none.
            (4) origin [Vector<float> 1x2]: The tagline's pen origin (x, baseline y) in logo units.
            (5) size [float]: The tagline's size in logo units (its cap height / Public Sans' 0.723).
            (6) mark_right [float]: The mark's right edge in logo units, for grid-fitting.
            (7) thin_px [float]: Grid_Fit's threshold for this mark.
    """

    # The empty space kept right of the tagline's ink, in logo units, so no antialiased edge is clipped.
    CONST_MARGIN = 5.0

    def __init__(self, file: str, height: int, tagline: str = '', origin: tp.Tuple[float, float] = (0.0, 0.0),
                 size: float = 0.0, mark_right: float = 0.0, thin_px: float = 0.0,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__path = Style.Asset(file)
        self.__renderer = QSvgRenderer(self.__path)
        self.__fitted = {}
        self.__mark_right = mark_right
        self.__thin_px = thin_px
        self.__tagline = tagline
        box = self.__renderer.viewBoxF()
        scale = height / box.height()
        self.__rect = QRectF(0.0, 0.0, box.width() * scale, float(height))
        self.__font = Font(size * scale * 72.0 / self.logicalDpiY()) if tagline else None
        self.__origin = QPointF((origin[0] - box.x()) * scale, (origin[1] - box.y()) * scale)

        right = self.__rect.width()
        if tagline:
            right = max(right, self.__origin.x() + QFontMetricsF(self.__font).tightBoundingRect(tagline).right()
                        + self.CONST_MARGIN * scale)
        self.setAccessibleName(tagline)
        self.setFixedSize(int(math.ceil(right)), height)

    def __Paint(self, painter: QPainter) -> None:
        Svg_Renderer_For(painter, self.__path, self.__renderer, self.__rect.height(), self.__mark_right,
                         self.__fitted, self.__thin_px).render(painter, self.__rect)
        if self.__tagline:
            painter.setFont(self.__font)
            painter.setPen(Style.Token_Color(Style.CONST_LOGO_INK))
            painter.drawText(self.__origin, self.__tagline)

    def Render(self) -> QPixmap:
        """
        Description:
            The lockup on a transparent pixmap, for measuring its ink; never drawn.

        Returns:
            (1) parameter [QPixmap(object)]: The render.
        """

        return Paint_To_Pixmap(self, self.__Paint)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        self.__Paint(painter)
        painter.end()


class Header_Cls(QWidget):
    """
    Description:
        The top bar: the product lockup, a 34 px grey-lilac rule and the JIC Smart Factory logo (spaced 32 px ink to
        rule to ink), the view tabs centred, and the status pills at the right. Margins 4/20/4/18, spacing 16.
        Exposes `tabs` (a Segmented_Control_Cls) and `pills` (a list).
    """

    # The JIC Smart Factory logo: the purple horizontal lockup at 26 px beside a 54 px product lockup (scaled with
    # it), its J-I-C bars grid-fitted at DPR 1 (they end at 449.44 units; the lettering starts at 516).
    #   Unit [string] / [px] / [float] (viewBox units)
    CONST_JIC_FILE = 'jic-smart-factory.svg'
    CONST_JIC_HEIGHT = 26
    CONST_JIC_MARK_RIGHT = 452.0

    def __init__(self, lockup: QWidget, segments: tp.Sequence[tp.Tuple[str, str]],
                 pills: tp.Sequence[QWidget] = (), parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 20, 4, 18)
        row.setSpacing(16)

        brand = QHBoxLayout()
        brand.setSpacing(0)
        brand.addWidget(lockup)
        render = lockup.Render() if hasattr(lockup, 'Render') else QPixmap()
        brand.addSpacing(max(0, Style.CONST_MARK_GAP - Style.Ink_Insets(render)[1]))
        brand.addWidget(Hairline(vertical=True, length=34, color=Style.CONST_TOPBAR_DIVIDER))
        jic = Svg_Image_Cls(self.CONST_JIC_FILE, int(round(self.CONST_JIC_HEIGHT * lockup.height()
                                                             / Style.CONST_LOGO_HEIGHT)), self.CONST_JIC_MARK_RIGHT)
        brand.addSpacing(max(0, Style.CONST_MARK_GAP - Style.Ink_Insets(jic.Render())[0]))
        brand.addWidget(jic)
        row.addLayout(brand)
        row.addStretch(1)

        self.tabs = Segmented_Control_Cls(segments)
        row.addWidget(self.tabs)
        row.addStretch(1)

        self.pills = list(pills)
        for pill in self.pills:
            row.addWidget(pill)


class Funding_Row_Cls(Card_Cls):
    """
    Description:
        The funding band at the window's foot: solid purple, 90 px (six 15 px motif cells), one centred group of white
        logos (EDIH-DIGIMAT 24 px, a white rule at 20 % 75 % of the tallest logo, the Ministry of Industry and Trade
        46 px, the EU emblem with 'Funded by the European Union' 46 px, 32 px apart) and the brand's pixel motif at the
        band's two ends, no square within CLEAR_SPACE of a logo. The disclaimer is NOT in the window's band: README
        and printed or generated figures carry it (DISCLAIMER). references/layout-components.md has the rules.
    """

    LOGOS = [('edih-digimat-white.svg', 24), (None, 0), ('partner-ministry-white.svg', 46), ('funder-eu-white.svg', 46)]
    # The EU disclaimer, word for word. Kept once, here.
    #   Unit [string]
    DISCLAIMER = ('Funded by the European Union. Views and opinions expressed are however those of the author(s) only '
                  'and do not necessarily reflect those of the European Union or European Commission. Neither the '
                  'European Union nor the granting authority can be held responsible for them.')
    DIVIDER_SHARE = 0.75
    # At least the EU emblem's protection area (half the flag's height, 23 px at 46 px); 28 px kept.
    CLEAR_SPACE = 28
    MOTIF_CELL = 15
    MOTIF_ROWS = 6
    MOTIF_FILL = 0.30
    MOTIF_REACH = 16
    MOTIF_STRONG = 0.4
    MOTIF_ALPHA = (0.07, 0.12)

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(padding=16, parent=parent)
        self.setStyleSheet(Qss.Band('card'))
        self.setFixedHeight(self.MOTIF_ROWS * self.MOTIF_CELL)
        self.box.setContentsMargins(16, 0, 16, 0)
        rule = int(round(self.DIVIDER_SHARE * max(height for _, height in self.LOGOS)))
        row = QHBoxLayout()
        row.setSpacing(Style.CONST_MARK_GAP)
        row.addStretch(1)
        for name, height in self.LOGOS:
            if name is None:
                row.addWidget(Hairline(vertical=True, length=rule,
                                       color=Style.Token_Css(Style.CONST_BAND_LINE, Style.CONST_BAND_LINE_ALPHA)))
            else:
                row.addWidget(Svg_Image_Cls(name, height))
        row.addStretch(1)
        self.box.addLayout(row)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        keep_out = []
        for logo in self.findChildren(Svg_Image_Cls):
            left = logo.mapTo(self, QPoint(0, 0)).x()
            keep_out.append((left - self.CLEAR_SPACE, left + logo.width() + self.CLEAR_SPACE))
        painter = QPainter(self)
        colors = [Style.Token_Color(Style.CONST_BAND_LINE, alpha) for alpha in self.MOTIF_ALPHA]
        for x, y, strong in Motif_Cells(self.width(), self.height(), self.MOTIF_CELL, self.MOTIF_FILL,
                                        self.MOTIF_REACH, self.MOTIF_STRONG, keep_out):
            painter.fillRect(x, y, self.MOTIF_CELL, self.MOTIF_CELL, colors[1 if strong else 0])
        painter.end()


class Viewport_Cls(QWidget):
    """
    Description:
        An image view: the grey-lilac ground, the image letterboxed in it, and its overlays, each the one place it is
        drawn: the empty state (a mark, the instruction naming the next step, the poster's pixel cluster in the
        top-right corner), the inspection area, the decorative analysis grid while work runs, and the busy overlay.
        Marker_Changed tells the card head's State_Marker_Cls what to name; nothing names a state inside the image.
    """

    CONST_CORNER_CELL = 16
    CONST_BUSY_CELL = 5

    # << SIGNAL >> #
    Marker_Changed = pyqtSignal(str)

    def __init__(self, mark: str = '', empty_text: str = '', parent: tp.Optional[QWidget] = None) -> None:
        """
        Args:
            (1) mark [string]: The product mark SVG drawn in the empty state (an asset name), or ''.
            (2) empty_text [string]: The empty state's instruction, naming the step available now.
        """

        super().__init__(parent)

        # << PRIVATE >> #
        self.__image = None
        self.__live = ''
        self.__area = None
        self.__empty_text = empty_text
        self.__mark = QSvgRenderer(Style.Asset(mark)) if mark else None
        self.__busy, self.__busy_text, self.__icon, self.__tick = False, '', 'magnifier', 0
        self.__timer = QTimer(self)
        self.__timer.setInterval(Style.CONST_BUSY_TICK_MS)
        self.__timer.timeout.connect(self.__Tick)
        self.__analysing, self.__grid_tick, self.__grid_layer, self.__grid_key = False, 0, None, None
        self.__grid_timer = QTimer(self)
        self.__grid_timer.setInterval(Style.CONST_GRID_TICK_MS)
        self.__grid_timer.timeout.connect(self.__Grid_Tick)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)

    def Show_Image(self, image: tp.Optional[QImage]) -> None:
        """
        Description:
            Show an image (None returns to the empty state).

        Args:
            (1) image [QImage(object) or None]: The image.
        """

        self.__image = image
        self.__grid_layer = None
        self.update()

    def Set_Empty_Text(self, text: str) -> None:
        """
        Description:
            Change the empty state's instruction.

        Args:
            (1) text [string]: The instruction.
        """

        self.__empty_text = text
        self.update()

    def Set_Inspection_Area(self, area: tp.Optional[tp.Tuple[tp.Tuple[int, int], tp.Tuple[float, float, float, float]]]
                            ) -> None:
        """
        Description:
            Show an inspection area: (the image's (width, height), (left, top, right, bottom)), or None.

        Args:
            (1) area [Tuple or None]: The area.
        """

        self.__area = area
        self.update()

    def Set_Live(self, kind: str) -> None:
        """
        Description:
            Mark the image as live frames ('preview' or 'scan') or not (''): the head's marker names it.

        Args:
            (1) kind [string]: The kind, or ''.
        """

        self.__live = kind
        self.Marker_Changed.emit(self.Marker_Kind())

    def Marker_Kind(self) -> str:
        """
        Description:
            What the head's marker names now: the live kind, 'analysis' while the grid sweeps, or ''.

        Returns:
            (1) parameter [string]: The kind.
        """

        return self.__live or ('analysis' if self.__analysing else '')

    def Start_Analysis(self) -> None:
        """
        Description:
            Sweep the decorative analysis grid over the image until Stop_Analysis (and mark ANALYZING… in the head).
        """

        self.__analysing, self.__grid_tick, self.__grid_layer = True, 0, None
        self.__grid_timer.start()
        self.update()
        self.Marker_Changed.emit(self.Marker_Kind())

    def Stop_Analysis(self) -> None:
        """
        Description:
            Stop the grid at once: the next paint is the image clean.
        """

        self.__analysing = False
        self.__grid_timer.stop()
        self.__grid_layer = None
        self.update()
        self.Marker_Changed.emit(self.Marker_Kind())

    def Start_Busy(self, text: str, icon: str) -> None:
        """
        Description:
            The busy overlay for a threaded step: the view's grey-lilac at 70 %, the task's pixel icon in 5 px cells
            and the step's words, both the purple.

        Args:
            (1) text [string]: The step, e.g. 'Connecting to the camera…'.
            (2) icon [string]: A key of Pixel_Motif.CONST_BUSY_STEPS ('camera', 'magnifier').
        """

        self.__busy, self.__busy_text, self.__icon, self.__tick = True, text, icon, 0
        self.__timer.start()
        self.update()

    def Stop_Busy(self) -> None:
        """
        Description:
            Clear the busy overlay and stop its timer (a timer left running repaints a still screen forever).
        """

        self.__busy = False
        self.__timer.stop()
        self.update()

    def __Tick(self) -> None:
        self.__tick += 1
        self.update()

    def __Grid_Tick(self) -> None:
        before = self.__Wave_Regions(self.__grid_tick)
        self.__grid_tick += 1
        after = self.__Wave_Regions(self.__grid_tick)
        if before is None or after is None:
            self.update()
            return
        dirty = QRegion()
        for region, _opacity in before + after:
            dirty += region
        if not dirty.isEmpty():
            self.update(dirty)

    def __Letterbox(self, width: int, height: int) -> QRect:
        scale = min(self.width() / width, self.height() / height)
        w, h = width * scale, height * scale
        return QRect(int((self.width() - w) / 2), int((self.height() - h) / 2), int(w), int(h))

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setClipRect(self.rect())
        p.fillRect(self.rect(), Style.Token_Color(Style.CONST_VIEWPORT))
        if self.__image is None:
            self.__Paint_Empty(p)
            if self.__area is not None:
                Paint_Inspection_Area(p, QRectF(self.__Letterbox(*self.__area[0])), *self.__area,
                                      Style.CONST_INSPECTION_AREA_EMPTY)
        else:
            rect = self.__Letterbox(self.__image.width(), self.__image.height())
            p.drawImage(rect, self.__image)
            if self.__area is not None:
                Paint_Inspection_Area(p, QRectF(rect), *self.__area)
            if self.__analysing:
                self.__Paint_Grid(p, rect)
        if self.__busy:
            self.__Paint_Busy(p)
        p.end()

    def __Grid_Layer(self, rect: QRect) -> tp.Tuple[QPixmap, tp.List[int], tp.List[int]]:
        """
        Description:
            The whole analysis grid for a draw rectangle, rendered once: 1 px periwinkle lines at 55 % on every cell
            edge (whole pixels), each cell filled inside them with #CC9EF1 at 30 %. Only the image's size enters it.
        """

        key = (rect.width(), rect.height(), self.__image.width(), self.__image.height(), self.devicePixelRatioF())
        if self.__grid_layer is not None and self.__grid_key == key:
            return self.__grid_layer
        columns, rows, cell = Grid_Shape(self.__image.width(), self.__image.height(), Style.CONST_GRID_COLUMNS)
        scale = rect.width() / float(self.__image.width())
        xs = [min(round(c * cell * scale), rect.width() - 1) for c in range(columns + 1)]
        ys = [min(round(r * cell * scale), rect.height() - 1) for r in range(rows + 1)]
        ratio = self.devicePixelRatioF()
        layer = QPixmap(round(rect.width() * ratio), round(rect.height() * ratio))
        layer.setDevicePixelRatio(ratio)
        layer.fill(Qt.transparent)
        q = QPainter(layer)
        q.setCompositionMode(QPainter.CompositionMode_Source)
        fill = Style.Token_Color(Style.CONST_GRID_FILL, Style.CONST_GRID_FILL_ALPHA)
        for r in range(rows):
            for c in range(columns):
                q.fillRect(xs[c] + 1, ys[r] + 1, xs[c + 1] - xs[c] - 1, ys[r + 1] - ys[r] - 1, fill)
        line = Style.Token_Color(Style.CONST_GRID_LINE, Style.CONST_GRID_LINE_ALPHA)
        for x in xs:
            q.fillRect(x, 0, 1, ys[-1] + 1, line)
        for y in ys:
            q.fillRect(0, y, xs[-1] + 1, 1, line)
        q.end()
        self.__grid_layer, self.__grid_key = (layer, xs, ys), key
        return self.__grid_layer

    def __Paint_Grid(self, p: QPainter, rect: QRect) -> None:
        if rect.width() < 2 or rect.height() < 2:
            return
        layer, _xs, _ys = self.__Grid_Layer(rect)
        p.save()
        for region, opacity in self.__Wave_Regions(self.__grid_tick):
            p.setClipRegion(region)
            p.setOpacity(opacity)
            p.drawPixmap(rect.topLeft(), layer)
        p.restore()

    def __Wave_Regions(self, tick: int) -> tp.Optional[tp.List[tp.Tuple[QRegion, float]]]:
        if self.__grid_layer is None or self.__image is None:
            return None
        rect = self.__Letterbox(self.__image.width(), self.__image.height())
        _layer, xs, ys = self.__grid_layer
        columns, rows = len(xs) - 1, len(ys) - 1
        drawn, regions = QRegion(), []
        for first, after, opacity in Wave_Diagonals(columns, rows, tick * Style.CONST_GRID_TICK_MS):
            region = QRegion()
            for row in range(rows):
                left, right = max(first - row, 0), min(after - row, columns)
                if left < right:
                    region += QRegion(rect.left() + xs[left], rect.top() + ys[row], xs[right] - xs[left] + 1,
                                      ys[row + 1] - ys[row] + 1)
            region -= drawn
            drawn += region
            regions.append((region, opacity))
        return regions

    def __Paint_Busy(self, p: QPainter) -> None:
        p.fillRect(self.rect(), Style.Token_Color(Style.CONST_BUSY_SCRIM, Style.CONST_BUSY_SCRIM_ALPHA))
        cx, cy = self.width() // 2, self.height() // 2
        cell = self.CONST_BUSY_CELL
        cells = Busy_Cells(self.__icon, self.__tick, Style.CONST_BUSY_DIM_ALPHA)
        columns = max(c for c, _, _ in cells) + 1
        rows = max(r for _, r, _ in cells) + 1
        left, top = cx - columns * cell // 2, cy - 6 - rows * cell
        p.save()
        p.setRenderHint(QPainter.Antialiasing, False)
        for column, row, alpha in cells:
            p.fillRect(left + column * cell, top + row * cell, cell, cell, Style.Token_Color(Style.CONST_BUSY_INK, alpha))
        p.restore()
        p.setPen(Style.Token_Color(Style.CONST_BUSY_INK))
        p.setFont(Font(9.5))
        p.drawText(QRect(0, int(cy + 14), self.width(), 40), Qt.AlignHCenter | Qt.AlignTop, self.__busy_text)

    def __Paint_Empty(self, p: QPainter) -> None:
        tints = [Style.Token_Color(Style.CONST_CORNER_MOTIF, alpha) for alpha in Style.CONST_CORNER_MOTIF_ALPHA]
        for x, y, strong in Corner_Cells(self.width(), 0, self.CONST_CORNER_CELL):
            p.fillRect(x, y, self.CONST_CORNER_CELL, self.CONST_CORNER_CELL, tints[1 if strong else 0])
        if self.__busy:
            return
        cy = self.height() // 2
        text_top = cy
        if self.__mark is not None and self.__mark.isValid():
            # The mark and the instruction under it at 92 %, as AnyScan draws them (its opacity carries to the text):
            # the purple at 92 % on the grey-lilac is still 6.1:1.
            size = min(210, int(self.width() * 0.44))
            p.setOpacity(0.92)
            self.__mark.render(p, QRectF((self.width() - size) // 2, cy - size // 2 - 20, size, size))
            text_top = cy + size // 2 - 8
        p.setPen(Style.Token_Color(Style.CONST_VIEWPORT_TEXT))
        p.setFont(Font(9.5))
        p.drawText(QRect(0, text_top, self.width(), 60), Qt.AlignHCenter | Qt.AlignTop, self.__empty_text)
