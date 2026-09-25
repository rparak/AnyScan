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
# File Name: ../UI/Widgets.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QTimer, QRect, QRectF, QPoint, pyqtSignal
from PyQt5.QtGui import (QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap,
                         QPaintEvent)
from PyQt5.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QButtonGroup,
                             QVBoxLayout, QHBoxLayout, QSizePolicy, QApplication)
# Custom Lib.: AnyScan UI — design tokens and style helpers
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font, Hairline, Load_Logo
# Custom Lib.: AnyScan domain — the confidence thresholds the object list colours numbers by
#   ../Parameters/Vision
from Parameters.Vision import Confidence_Thresholds_Str
# Custom Lib.: AnyScan domain — the shared Scene-Understanding formatter
#   ../Reporting/Core
from Reporting.Core import Object_Label, Object_Confidence, Object_Size, CONST_LABEL_SEPARATOR

"""
Description:
    The console's widgets. Every widget is a behaviour class carrying the _Cls
    suffix and its Qt base. paintEvent is kept camelCase — Qt dispatches it by name.
    Attributes that other widgets or the window compose with (a card's `box`
    layout, a head's `badge`, the status strip's cells) stay public; everything
    else is name-mangled private state.
"""


def Meta_Row(parent_layout: QVBoxLayout, key: str, *, compact: bool, mono: bool = False,
             first: bool = False) -> QLabel:
    """
    Description:
        One key/value record row under a hairline divider — the Live reading card's meta rows and,
        compact, the History record (which carries several). The value starts as the no-value dash;
        the caller keeps the returned label and updates it.

    Args:
        (1) parent_layout [QVBoxLayout(object)]: The layout to add the row to.
        (2) key [string]: The row label.
        (3) compact [bool]: REQUIRED, keyword-only: the tighter History rhythm (less padding, a
            size smaller, a regular-weight value) instead of the Live card's.
        (4) mono [bool]: Render the value monospace.
        (5) first [bool]: Omit the top divider on the first row.

    Returns:
        (1) parameter [QLabel(object)]: The value label to update later.
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
        The white card every panel sits in. Exposes `box`, the vertical layout the
        window and the Card subclasses add their content to.
    """

    def __init__(self, padding: int = 16, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('card')
        self.setStyleSheet(
            '#card { background: %s; border: 1px solid %s; border-radius: %dpx; }'
            % (Style.CONST_CARD, Style.CONST_CARD_BORDER, Style.CONST_RADIUS_CARD)
        )
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(padding, padding, padding, padding)
        self.box.setSpacing(0)


class Icon_Cls(QWidget):
    """
    Description:
        The three stroked icons the card heads use, hand-painted rather than
        shipped as files — three shapes do not justify an asset pipeline, and
        painting them keeps the stroke weight tied to the size.
    """

    def __init__(self, kind: str, size: int = 22, color: str = Style.CONST_INK,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__kind = kind
        self.__color = color

        self.setFixedSize(size, size)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Paint the stroked icon selected by kind at the widget's size.
        """

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width() / 24.0
        pen = QPen(QColor(self.__color), 1.7 * s)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        def _Rect(x: float, y: float, w: float, h: float) -> QRectF:
            """
            Description:
                A rectangle in the 24-unit icon grid, scaled to the widget.

            Args:
                (1 - 4) x, y, w, h [float]: The rectangle in icon units.

            Returns:
                (1) parameter [QRectF(object)]: The rectangle in widget pixels.
            """

            return QRectF(x * s, y * s, w * s, h * s)

        if self.__kind == 'camera':
            p.drawRoundedRect(_Rect(2, 6, 20, 14), 2 * s, 2 * s)
            p.drawLine(QPoint(int(9.5 * s), int(6 * s)), QPoint(int(11 * s), int(4 * s)))
            p.drawLine(QPoint(int(14.5 * s), int(6 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawLine(QPoint(int(11 * s), int(4 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawEllipse(_Rect(8.4, 9.4, 7.2, 7.2))
        elif self.__kind == 'reading':
            p.drawRoundedRect(_Rect(4, 4, 16, 16), 1.5 * s, 1.5 * s)
            p.drawLine(QPoint(int(12 * s), int(4 * s)), QPoint(int(12 * s), int(20 * s)))
            for y in (9, 12.5):
                p.drawLine(QPoint(int(7 * s), int(y * s)), QPoint(int(9.5 * s), int(y * s)))
                p.drawLine(QPoint(int(14.5 * s), int(y * s)), QPoint(int(17 * s), int(y * s)))
        elif self.__kind == 'cube':
            path = QPainterPath()
            path.moveTo(12 * s, 3 * s)
            path.lineTo(20 * s, 7 * s)
            path.lineTo(20 * s, 17 * s)
            path.lineTo(12 * s, 21 * s)
            path.lineTo(4 * s, 17 * s)
            path.lineTo(4 * s, 7 * s)
            path.closeSubpath()
            p.drawPath(path)
            p.drawLine(QPoint(int(4 * s), int(7 * s)), QPoint(int(12 * s), int(11 * s)))
            p.drawLine(QPoint(int(20 * s), int(7 * s)), QPoint(int(12 * s), int(11 * s)))
            p.drawLine(QPoint(int(12 * s), int(11 * s)), QPoint(int(12 * s), int(21 * s)))
        p.end()


class Badge_Cls(QLabel):
    """
    Description:
        The verdict badge, coloured by meaning never by brand: green when objects
        were found, amber when confidence is under threshold, neutral otherwise.
    """

    def __init__(self, text: str = 'Idle', parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setFont(Font(8, mono=True))
        self.setFixedHeight(24)
        self.Set_Level('idle')

    def Set_Level(self, level: str) -> None:
        """
        Description:
            Repaint the badge for a severity level ('ok' | 'warn' | anything else).

        Args:
            (1) level [string]: The severity level.
        """

        if level == 'ok':
            border, bg, fg = Style.CONST_OK_BORDER, Style.CONST_OK_SOFT, Style.CONST_OK_INK
        elif level == 'warn':
            border, bg, fg = Style.CONST_WARN_BORDER, Style.CONST_WARN_SOFT, Style.CONST_WARN_INK
        else:
            border, bg, fg = Style.CONST_CARD_BORDER, Style.CONST_CARD, Style.CONST_INK_MUTE
        self.setStyleSheet(
            'border: 1px solid %s; background: %s; color: %s;'
            'border-radius: 7px; padding: 0 9px;' % (border, bg, fg)
        )

    def Set_State(self, text: str, level: str) -> None:
        """
        Description:
            Set the badge wording and its level together.

        Args:
            (1) text [string]: The badge wording.
            (2) level [string]: The severity level.
        """

        self.setText(text)
        self.Set_Level(level)


class Card_Head_Cls(QWidget):
    """
    Description:
        A card head: icon, title, spacer, and at most one badge. Exposes `badge`
        (the Badge_Cls, or None) so the window can drive it.
    """

    def __init__(self, icon_kind: str, title: str, badge_text: tp.Optional[str] = None,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        # `box` is exposed so the window can add a right-aligned control (e.g. the
        # Camera View's annotated/mask toggle) into the head after the badge.
        self.box = QHBoxLayout(self)
        self.box.setContentsMargins(2, 2, 2, 14)
        self.box.setSpacing(10)
        self.box.addWidget(Icon_Cls(icon_kind))
        label = QLabel(title)
        label.setFont(Font(15.5, QFont.Bold, tracking=-2))
        label.setStyleSheet('color: %s;' % Style.CONST_INK)
        self.box.addWidget(label)
        self.box.addStretch(1)
        self.badge = None
        if badge_text is not None:
            self.badge = Badge_Cls(badge_text)
            self.box.addWidget(self.badge)


class Viewport_Cls(QWidget):
    """
    Description:
        The camera image and the boxes drawn over it. The image is letterboxed
        inside the widget, so the overlay recomputes the draw rectangle on every
        paint — that maths lives here and nowhere else, the single most common
        source of boxes that land in the wrong place.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__image = None
        # The two analysis renders (§2b): the annotated image and the label mask, both
        # produced from the completed result and held here so the toggle swaps them in
        # place — never re-analysing and never re-reading from disk. __view selects which
        # one paints. They are the SAME resolution as the frame, so the letterbox rect is
        # identical across the switch and the operator compares the same region.
        self.__annotated = None
        self.__mask = None
        self.__view = 'annotated'
        # Busy overlay. __busy shows the scrim and step text; __animated adds the
        # turning arc, driven by __timer, which runs ONLY while the analysis worker
        # is busy — a timer left running repaints a static screen forever.
        self.__busy = False
        self.__busy_text = ''
        self.__animated = False
        self.__spin = 0.0
        self.__timer = QTimer(self)
        self.__timer.setInterval(Style.CONST_BUSY_TICK_MS)
        self.__timer.timeout.connect(self.__Tick)
        # An empty state is an instruction — it names the step available right now.
        self.__empty_text = 'Connect a camera, then press Scan to capture a frame.'
        self.__mark = QPixmap(os.path.join(Style.CONST_ASSETS, 'anyscan-mark.png'))

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)

    def Show_Frame(self, image: QImage) -> None:
        """
        Description:
            Show a captured frame and drop any analysis renders. A new frame makes the
            previous frame's annotations stale — showing them over a different scene is
            the one genuinely misleading failure — so they are cleared here, and the
            window disables the view toggle to match.

        Args:
            (1) image [QImage(object)]: The frame to paint.
        """

        self.__image = image
        self.__annotated = None
        self.__mask = None
        self.update()

    def Show_Views(self, annotated: QImage, mask: QImage, view: str) -> None:
        """
        Description:
            Hold both analysis renders from the completed result and paint the selected
            one. The two images are swapped in place by Set_View with no re-analysis and
            no disk read.

        Args:
            (1) annotated [QImage(object)]: The annotated image.
            (2) mask [QImage(object)]: The label mask image.
            (3) view [string]: The view to show now ('annotated' or 'mask').
        """

        self.__annotated = annotated
        self.__mask = mask
        self.__view = view
        self.update()

    def Set_View(self, view: str) -> None:
        """
        Description:
            Swap the displayed analysis render. Instant: it only selects which held
            image paints, so the letterbox rect (and thus the on-screen region) is
            unchanged.

        Args:
            (1) view [string]: 'annotated' or 'mask'.
        """

        if view != self.__view:
            self.__view = view
            self.update()

    def Has_Views(self) -> bool:
        """
        Description:
            Whether an analysis render is currently held — the toggle is meaningful only
            then.

        Returns:
            (1) parameter [bool]: True once both renders are held.
        """

        return self.__annotated is not None

    def __Displayed(self) -> tp.Optional[QImage]:
        """
        Description:
            The image to paint: the selected analysis render when one is held, otherwise
            the bare frame.

        Returns:
            (1) parameter [QImage(object) or None]: The image, or None for the empty state.
        """

        if self.__annotated is not None:
            return self.__mask if self.__view == 'mask' else self.__annotated
        return self.__image

    def Clear_Views(self) -> None:
        """
        Description:
            Drop the analysis renders but keep the frame. A new run supersedes the old,
            so its renders are cleared the moment it starts — the toggle cannot show, and
            two runs in quick succession cannot leave a mixed annotated/mask pair.
        """

        self.__annotated = None
        self.__mask = None
        self.update()

    def Clear(self) -> None:
        """
        Description:
            Drop the frame and both analysis renders, returning to the empty state.
        """

        self.__image = None
        self.__annotated = None
        self.__mask = None
        self.update()

    def Set_Empty_Text(self, text: str) -> None:
        """
        Description:
            Change the empty-state instruction, repainting only if it differs.

        Args:
            (1) text [string]: The instruction to show.
        """

        if text != self.__empty_text:
            self.__empty_text = text
            self.update()

    def Set_Busy(self, text: str) -> None:
        """
        Description:
            A static overlay for the short, GUI-thread steps (connect, scan). No
            animation is possible: the GUI thread is about to block, so a spinner
            would freeze mid-turn. processEvents forces the text to paint first.

        Args:
            (1) text [string]: The step text (empty clears the overlay).
        """

        self.__busy = bool(text)
        self.__busy_text = text
        self.__animated = False
        self.__timer.stop()
        self.update()
        QApplication.processEvents()

    def Start_Busy(self, text: str) -> None:
        """
        Description:
            The animated overlay for the threaded analysis; the worker runs off the
            GUI thread, so the timer's repaints are free to turn the arc.

        Args:
            (1) text [string]: The initial step text.
        """

        self.__busy = True
        self.__busy_text = text
        self.__animated = True
        self.__spin = 0.0
        if not self.__timer.isActive():
            self.__timer.start()
        self.update()

    def Set_Busy_Text(self, text: str) -> None:
        """
        Description:
            Update the step line without disturbing the animation.

        Args:
            (1) text [string]: The new step text.
        """

        self.__busy_text = text
        self.update()

    def Stop_Busy(self) -> None:
        """
        Description:
            Clear the busy overlay and stop the animation timer.
        """

        self.__busy = False
        self.__busy_text = ''
        self.__animated = False
        self.__timer.stop()
        self.update()

    def __Tick(self) -> None:
        """
        Description:
            Advance the spinner arc one step and repaint. Driven by the timer.
        """

        self.__spin = (self.__spin + Style.CONST_BUSY_SPIN_DEG) % 360.0
        self.update()

    def __Draw_Rect(self) -> QRect:
        """
        Description:
            Where the letterboxed image actually sits inside this widget.

        Returns:
            (1) parameter [QRect(object)]: The image's draw rectangle.
        """

        displayed = self.__Displayed()
        if displayed is None:
            return QRect()
        scale = min(self.width() / displayed.width(),
                    self.height() / displayed.height())
        w = displayed.width() * scale
        h = displayed.height() * scale
        return QRect(int((self.width() - w) / 2), int((self.height() - h) / 2),
                     int(w), int(h))

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Paint the dark surface, the letterboxed frame, its boxes, and any busy
            overlay on top.
        """

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(Style.CONST_VIEWPORT))

        displayed = self.__Displayed()
        if displayed is None:
            self.__Paint_Empty(p)
        else:
            p.drawImage(self.__Draw_Rect(), displayed)

        if self.__busy:
            self.__Paint_Busy(p)
        p.end()

    def __Paint_Busy(self, p: QPainter) -> None:
        """
        Description:
            Dim the viewport, turn an arc (only while animated), and print the step
            underneath.

        Args:
            (1) p [QPainter(object)]: The active painter.
        """

        p.fillRect(self.rect(), Style.Token_Color(Style.CONST_BUSY_SCRIM, Style.CONST_BUSY_SCRIM_ALPHA))
        cx, cy = self.width() / 2.0, self.height() / 2.0

        if self.__animated:
            radius = 22
            arc = QRectF(cx - radius, cy - radius - 16, radius * 2, radius * 2)
            track = QPen(Style.Token_Color(Style.CONST_BUSY_TRACK, Style.CONST_BUSY_TRACK_ALPHA), 3)
            track.setCapStyle(Qt.RoundCap)
            p.setPen(track)
            p.setBrush(Qt.NoBrush)
            p.drawArc(arc, 0, 360 * 16)
            head = QPen(Style.Token_Color(Style.CONST_BUSY_INK), 3)
            head.setCapStyle(Qt.RoundCap)
            p.setPen(head)
            # Qt angles are 1/16 degree, counter-clockwise; negate to turn the usual
            # clockwise direction. A 90-degree sweep reads as a spinner.
            p.drawArc(arc, int(-self.__spin * 16), 90 * 16)

        p.setPen(Style.Token_Color(Style.CONST_BUSY_INK))
        p.setFont(Font(9.5, mono=True))
        text_rect = QRect(0, int(cy + 14), self.width(), 40)
        p.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self.__busy_text)

    def __Paint_Empty(self, p: QPainter) -> None:
        """
        Description:
            The project mark holds the empty state; it disappears the instant a
            frame arrives.

        Args:
            (1) p [QPainter(object)]: The active painter.
        """

        cy = self.height() // 2
        if not self.__mark.isNull():
            size = min(210, int(self.width() * 0.44))
            dpr = max(1.0, float(self.devicePixelRatioF()))
            scaled = self.__mark.scaled(int(size * dpr), int(size * dpr),
                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(dpr)
            draw_w = int(scaled.width() / dpr)
            draw_h = int(scaled.height() / dpr)
            p.setOpacity(0.92)
            p.drawPixmap((self.width() - draw_w) // 2, cy - draw_h // 2 - 20, scaled)
            text_top = cy + draw_h // 2 - 8
        else:
            text_top = cy
        p.setPen(QColor(Style.CONST_VIEWPORT_TEXT))
        p.setFont(Font(9.5, mono=True))
        p.drawText(QRect(0, text_top, self.width(), 60), Qt.AlignHCenter | Qt.AlignTop,
                   self.__empty_text)


class Tool_Button_Cls(QPushButton):
    """
    Description:
        48px tall, uppercase, tracked. Exactly one is primary. The primary is the
        deep-indigo brand ink rather than magenta: the strongest control reads as
        structural, leaving magenta to mean one thing only — a detected object.
    """

    def __init__(self, text: str, primary: bool = False,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setFont(Font(9.5, QFont.DemiBold, tracking=6))
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Every state rule names its fill AND its label, as in Segmented_Control_Cls: Qt picks a
        # rule by pseudo-state count, not order, so a fill-only rule can pair with a label chosen
        # for another state. Nothing competes here today, but the pairing keeps it that way.
        if primary:
            self.setStyleSheet("""
                QPushButton { background: %(ink)s; border: 1px solid %(ink)s; color: %(on_ink)s;
                              border-radius: %(radius)dpx; }
                QPushButton:hover:enabled { background: %(hover)s; border-color: %(hover)s;
                                            color: %(on_ink)s; }
                QPushButton:pressed:enabled { background: %(pressed)s; border-color: %(pressed)s;
                                              color: %(on_ink)s; }
                QPushButton:disabled { background: %(off_fill)s; border-color: %(off_fill)s;
                                       color: %(off_text)s; }
            """ % {'ink': Style.CONST_INK, 'on_ink': Style.CONST_ON_INK, 'hover': Style.CONST_INK_HOVER,
                   'pressed': Style.CONST_INK_PRESSED, 'off_fill': Style.CONST_PRIMARY_DISABLED_FILL,
                   'off_text': Style.CONST_PRIMARY_DISABLED_TEXT, 'radius': Style.CONST_RADIUS_BTN})
        else:
            self.setStyleSheet("""
                QPushButton { background: %(card)s; border: 1px solid %(border)s; color: %(ink)s;
                              border-radius: %(radius)dpx; }
                QPushButton:hover:enabled { background: %(hover)s; border-color: %(hover_border)s;
                                            color: %(ink)s; }
                QPushButton:disabled { background: %(card)s; border-color: %(off_border)s;
                                       color: %(off_text)s; }
            """ % {'card': Style.CONST_CARD, 'border': Style.CONST_CONTROL_BORDER, 'ink': Style.CONST_INK,
                   'hover': Style.CONST_CONTROL_HOVER, 'hover_border': Style.CONST_CONTROL_HOVER_BORDER,
                   'off_border': Style.CONST_CONTROL_DISABLED_BORDER,
                   'off_text': Style.CONST_CONTROL_DISABLED_TEXT, 'radius': Style.CONST_RADIUS_BTN})


class Segmented_Control_Cls(QWidget):
    """
    Description:
        The console's ONE segmented control: a row of mutually-exclusive, checkable segments
        styled as a single pill, so every selector (the Camera View's annotated/mask toggle,
        the header's Live/History/Log switch) shares one visual language. It emits
        Segment_Selected with the chosen key only on a USER click; Set_Selection reflects a
        choice programmatically without re-emitting, so restoring a remembered choice never
        loops. The first segment is selected at construction.
    """

    # << SIGNAL >> #
    Segment_Selected = pyqtSignal(str)

    def __init__(self, segments: tp.Sequence[tp.Tuple[str, str]], height: int = 30,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.__group = QButtonGroup(self)
        self.__group.setExclusive(True)
        # << PRIVATE >> #
        self.__buttons = {}
        for index, (key, label) in enumerate(segments):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFont(Font(9, QFont.DemiBold, tracking=2))
            button.setFixedHeight(height)
            button.setStyleSheet(self.__Segment_Style(index, len(segments)))
            button.clicked.connect(lambda _checked, k=key: self.Segment_Selected.emit(k))
            self.__group.addButton(button)
            self.__buttons[key] = button
            row.addWidget(button)
        if self.__buttons:
            next(iter(self.__buttons.values())).setChecked(True)

    def __Segment_Style(self, index: int, total: int) -> str:
        """
        Description:
            The stylesheet for one segment: only the outer corners are rounded, so the
            buttons read as a single segmented control, and the checked segment carries the
            brand ink.

            Note:
                Qt ranks a selector by its pseudo-state count, not its order, so a bare
                ':hover:enabled' (two states) beats ':checked' (one) and repaints a SELECTED
                segment's fill with the unselected hover tint while ':checked' still supplies
                the white label — white on near-white. Each hover rule is therefore scoped to
                checked or unchecked and sets the background AND the label together, so no
                state can inherit a label colour chosen for a different fill.

        Args:
            (1) index [int]: The segment's position.
            (2) total [int]: The number of segments.

        Returns:
            (1) parameter [string]: The Qt stylesheet.
        """

        radius = Style.CONST_RADIUS_BTN
        left = radius if index == 0 else 0
        right = radius if index == total - 1 else 0
        return ("""
            QPushButton { background: %(card)s; border: 1px solid %(border)s; color: %(ink)s;
                          padding: 0 16px;
                          border-top-left-radius: %(left)dpx; border-bottom-left-radius: %(left)dpx;
                          border-top-right-radius: %(right)dpx; border-bottom-right-radius: %(right)dpx; }
            QPushButton:!checked:hover:enabled { background: %(hover)s; color: %(ink)s; }
            QPushButton:checked { background: %(ink)s; border-color: %(ink)s; color: %(on_ink)s; }
            QPushButton:checked:hover:enabled { background: %(ink_hover)s; border-color: %(ink_hover)s;
                                                color: %(on_ink)s; }
            QPushButton:!checked:disabled { background: %(card)s; border-color: %(off_border)s;
                                            color: %(off_text)s; }
            QPushButton:checked:disabled { background: %(ink)s; border-color: %(ink)s;
                                           color: %(off_text)s; }
        """ % {'card': Style.CONST_CARD, 'border': Style.CONST_CONTROL_BORDER, 'ink': Style.CONST_INK,
               'hover': Style.CONST_CONTROL_HOVER, 'ink_hover': Style.CONST_INK_HOVER,
               'on_ink': Style.CONST_ON_INK, 'off_border': Style.CONST_CONTROL_DISABLED_BORDER,
               'off_text': Style.CONST_CONTROL_DISABLED_TEXT, 'left': left, 'right': right})

    def Set_Selection(self, key: str) -> None:
        """
        Description:
            Reflect a selection on the control WITHOUT emitting Segment_Selected — used to
            restore a remembered choice. A programmatic setChecked does not raise `clicked`,
            so the signal stays reserved for genuine user clicks.

        Args:
            (1) key [string]: The segment key to select.
        """

        button = self.__buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)

    def Selection(self) -> tp.Optional[str]:
        """
        Description:
            The key of the currently selected segment, or None when the control is empty.

        Returns:
            (1) parameter [string or None]: The selected key.
        """

        for key, button in self.__buttons.items():
            if button.isChecked():
                return key
        return None


class View_Toggle_Cls(Segmented_Control_Cls):
    """
    Description:
        The Camera View's annotated/mask selector (§2b) — a Segmented_Control_Cls fixed to
        two segments, so it shares the console's one segmented-control look. It re-exposes
        the control under its domain names: View_Changed (a user click) and Set_View
        (restore a remembered choice without re-emitting). The window hides it until an
        analysis has completed — there is nothing to toggle before then.
    """

    # << SIGNAL >> #
    View_Changed = pyqtSignal(str)

    # The segments, in order, as (key, label).
    CONST_SEGMENTS = (('annotated', 'Annotated'), ('mask', 'Mask'))

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(self.CONST_SEGMENTS, parent=parent)
        # Relay the generic selection under this control's domain name.
        self.Segment_Selected.connect(self.View_Changed)

    def Set_View(self, view: str) -> None:
        """
        Description:
            Reflect a view choice WITHOUT emitting View_Changed — restore the operator's
            remembered annotated/mask choice when a new analysis completes.

        Args:
            (1) view [string]: 'annotated' or 'mask'.
        """

        self.Set_Selection(view)


class Object_Block_Cls(QWidget):
    """
    Description:
        One object's two-level block inside Object_List_Cls. It carries its object index and,
        when the list is selectable (History), emits Clicked on a left click and paints a
        selection tint. In the non-selectable list (Live) it is an inert container.
    """

    # << SIGNAL >> #
    Clicked = pyqtSignal(int)

    def __init__(self, index: int, selectable: bool, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__index = index
        self.__selectable = selectable

        self.setObjectName('objBlock')
        if selectable:
            self.setCursor(Qt.PointingHandCursor)
        self.Set_Selected(False)

    def Set_Selected(self, selected: bool) -> None:
        """
        Description:
            Paint (or clear) the selection tint. Only a selectable block ever shows it.

        Args:
            (1) selected [bool]: Whether this block is the selected one.
        """

        tint = Style.CONST_LINE if (selected and self.__selectable) else 'transparent'
        self.setStyleSheet('#objBlock { background: %s; border-radius: 7px; }' % tint)

    # << QT OVERRIDE >> #
    def mousePressEvent(self, event: tp.Any) -> None:
        """
        Description:
            Emit Clicked with this block's index on a left click, when selectable.
        """

        if self.__selectable and event.button() == Qt.LeftButton:
            self.Clicked.emit(self.__index)
        super().mousePressEvent(event)


class Object_List_Cls(QWidget):
    """
    Description:
        The numbered objects, each a two-level block: the label line ('Object N · Confidence
        91%') on its own line, larger and bold, and the description beneath it, smaller and
        regular, with vertical space between objects. The label line is the object name
        (Reporting.Object_Label) leading and heavier and its own confidence
        (Reporting.Object_Confidence) trailing and lighter, joined by the shared
        CONST_LABEL_SEPARATOR — the same words the Screen-Understanding file writes as one
        string (Object_Label_Full via Object_Line), so the panel and the file cannot number,
        word or score an object differently. Everything is one colour (Style.CONST_INK): the
        object's colour lives on the frame, not here, and the hierarchy is size and weight,
        not colour. The type sizes come from the theme.

        A `selectable` list (History) makes each block clickable — it emits Object_Selected
        with the object index and paints the chosen block — so a reviewer can investigate one
        object. The default (Live) is inert, where the operator only glances.

        The three type sizes (label, description, confidence) are taken from the theme and
        default to the LIVE Scene-Understanding tokens; a caller reading up close (the History
        Info panel) passes the smaller Info tokens instead, so the same widget serves both
        distances without either set of sizes moving the other.

        Each confidence number is coloured by the configuration's thresholds, passed in (and
        replaced by Set_Thresholds when another configuration is loaded) — never a default here.
    """

    # << SIGNAL >> #
    Object_Selected = pyqtSignal(int)

    def __init__(self, selectable: bool = False, label_size: tp.Optional[float] = None,
                 body_size: tp.Optional[float] = None, confidence_size: tp.Optional[float] = None,
                 parent: tp.Optional[QWidget] = None, *,
                 Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__selectable = selectable
        self.__thresholds = Confidence_Thresholds_Str
        # The type sizes, from the theme (defaults are the Live tokens); a caller may pass the
        # smaller Info-panel tokens.
        self.__label_size = label_size if label_size is not None else Style.CONST_TYPE_OBJECT_LABEL
        self.__body_size = body_size if body_size is not None else Style.CONST_TYPE_OBJECT_BODY
        self.__confidence_size = (confidence_size if confidence_size is not None
                                  else Style.CONST_TYPE_OBJECT_CONFIDENCE)
        self.__blocks = []

        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(16)                          # vertical space between objects

    def Set_Thresholds(self, Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        """
        Description:
            Colour confidence numbers by another configuration's thresholds from the next
            Set_Objects on.

        Args:
            (1) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: The thresholds.
        """

        self.__thresholds = Confidence_Thresholds_Str

    def Set_Objects(self, objects: tp.List) -> None:
        """
        Description:
            Rebuild the two-level object blocks from the located objects, clearing any
            selection.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The located objects.
        """

        while self.box.count():
            item = self.box.takeAt(0)
            widget = item.widget()
            if widget:
                # Unparent NOW (not just deleteLater): takeAt removes the layout item but leaves
                # the widget a child, still painted at its old spot until the deferred delete
                # runs — a rapid rebuild then shows the previous rows behind the new ones.
                widget.setParent(None)
                widget.deleteLater()
        self.__blocks = []

        for i, det in enumerate(objects):
            block = self.__Object_Block(i, det)
            self.__blocks.append(block)
            self.box.addWidget(block)

    def Set_Selected(self, index: tp.Optional[int]) -> None:
        """
        Description:
            Paint the block at `index` as selected and clear the rest (None clears all).

        Args:
            (1) index [int or None]: The selected object index, or None.
        """

        for i, block in enumerate(self.__blocks):
            block.Set_Selected(i == index)

    def __Object_Block(self, index: int, det: tp.Any) -> QWidget:
        """
        Description:
            One object's two-level block: the label line above (the name leading and heavier,
            its confidence trailing and lighter), its description below, all Style.CONST_INK,
            differentiated only by the theme's type sizes and weight. A selectable block relays
            its click as Object_Selected(index).

        Args:
            (1) index [int]: The object's 0-based position.
            (2) det [Detection_Str(object)]: The object.

        Returns:
            (1) parameter [QWidget(object)]: The block widget.
        """

        block = Object_Block_Cls(index, self.__selectable)
        # Never let a layout shrink a block below its content: a 'Minimum' vertical policy makes
        # the block's sizeHint its floor, so in a tight scroll the list scrolls rather than
        # compressing the rows on top of each other.
        block.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        if self.__selectable:
            block.Clicked.connect(self.Object_Selected)
        column = QVBoxLayout(block)
        pad = 8 if self.__selectable else 0              # room for the selection tint
        column.setContentsMargins(pad, pad // 2, pad, pad // 2)
        column.setSpacing(3)                             # tight label -> description

        column.addWidget(self.__Label_Line(index, det))

        description = QLabel(det.Sentence)
        description.setFont(Font(self.__body_size))
        description.setWordWrap(True)
        description.setStyleSheet('color: %s; background: transparent;' % Style.CONST_INK)
        column.addWidget(description)
        return block

    def __Label_Line(self, index: int, det: tp.Any) -> QWidget:
        """
        Description:
            One object's label line: the shared name (Object_Label) leading — the label size
            and heavier — then its own confidence (Object_Confidence) trailing as secondary
            metadata: one step down in the theme's type scale AND a lighter weight, so the
            two do not read as one continuous run of text. Both come from the theme, never
            colour, and the two rendered together spell exactly the file's Object_Label_Full,
            one source in two renderings.

        Args:
            (1) index [int]: The object's 0-based position.
            (2) det [Detection_Str(object)]: The object.

        Returns:
            (1) parameter [QWidget(object)]: The label-line widget.
        """

        line = QWidget()
        row = QHBoxLayout(line)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        name = QLabel(Object_Label(index))
        name.setFont(Font(self.__label_size, QFont.DemiBold))
        name.setStyleSheet('color: %s;' % Style.CONST_INK)
        row.addWidget(name)

        # The same separator the file's Object_Label_Full uses, so the two spellings match.
        # The number carries its severity colour and weight (Style.Confidence_Number_Html); the
        # surrounding words stay the default ink. An unscored '—' is left plain — not a low read.
        suffix = Object_Confidence(det)
        if det.Segmenter_Score is not None:
            number = '%d%%' % int(round(100.0 * det.Segmenter_Score))
            suffix = suffix.replace(number, Style.Confidence_Number_Html(number, int(number[:-1]),
                                                                            self.__thresholds))
        # Rich text collapses the separator's leading space (HTML whitespace rules), which ran the
        # name and the '·' together; non-breaking spaces keep the file's spelling on screen.
        confidence = QLabel(CONST_LABEL_SEPARATOR.replace(' ', '&nbsp;') + suffix)
        confidence.setTextFormat(Qt.RichText)
        # Smaller than the name and a lighter weight — secondary metadata, not a continuation
        # of the heading.
        confidence.setFont(Font(self.__confidence_size))
        confidence.setStyleSheet('color: %s;' % Style.CONST_INK)
        row.addWidget(confidence)

        # The size, when the object was measured — the same words and separator as the file's
        # Object_Label_Full, in the confidence's secondary style so the name still leads. Plain
        # text: a measurement carries no severity. Absent entirely when there is no measurement.
        size = Object_Size(det)
        if size:
            size_label = QLabel(CONST_LABEL_SEPARATOR + size)
            size_label.setTextFormat(Qt.PlainText)
            size_label.setFont(Font(self.__confidence_size))
            size_label.setStyleSheet('color: %s;' % Style.CONST_INK)
            row.addWidget(size_label)

        row.addStretch(1)
        return line


class Stat_Cell_Cls(QWidget):
    """
    Description:
        One cell of the status strip. The two counts are larger than the four
        states, because in a demo the counts are read from the back of the room and
        the states by the person at the keyboard.
    """

    def __init__(self, label: str, value: str = '', big: bool = False,
                 mono: bool = False, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        col = QVBoxLayout(self)
        col.setContentsMargins(20, 13, 20, 13)
        col.setSpacing(5)

        self.__label = QLabel(label.upper())
        self.__label.setFont(Font(8, QFont.Bold, tracking=7))
        self.__label.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        col.addWidget(self.__label)

        self.__value = QLabel(value)
        if big:
            # still the loudest thing in the strip, just no longer shouting
            self.__value.setFont(Font(18, QFont.Bold, tracking=-4))
        elif mono:
            self.__value.setFont(Font(12, QFont.Medium, mono=True))
        else:
            self.__value.setFont(Font(13.5, QFont.DemiBold, tracking=-2))
        self.__value.setStyleSheet('color: %s;' % Style.CONST_INK)
        col.addWidget(self.__value)
        col.addStretch(1)

    def Value(self) -> str:
        """
        Description:
            The cell's current value text (without any status-dot markup).

        Returns:
            (1) parameter [string]: The value text.
        """

        return self.__value.text()

    def Set_Value(self, text: str, color: tp.Optional[str] = None,
                  dot_color: tp.Optional[str] = None, weight: tp.Optional[int] = None) -> None:
        """
        Description:
            Set the cell's value, optionally with a colour, a leading status dot, and a font
            weight. `weight` overrides only the weight, keeping the cell's own size and family,
            so the confidence run-mean can carry the severity weight ramp without the cell
            reinventing its type.

        Args:
            (1) text [string]: The value text.
            (2) color [string]: Optional text colour.
            (3) dot_color [string]: Optional leading-dot colour (rich text).
            (4) weight [int]: Optional QFont weight; None keeps the cell's own weight.
        """

        if weight is not None:
            font = self.__value.font()
            font.setWeight(weight)
            self.__value.setFont(font)
        self.__value.setStyleSheet('color: %s;' % (color or Style.CONST_INK))
        self.__value.setText(('●  ' if dot_color else '') + text)
        if dot_color:
            self.__value.setText(
                '<span style="color:%s">●</span>&nbsp;&nbsp;'
                '<span style="color:%s">%s</span>' % (dot_color, color or Style.CONST_INK, text)
            )
            self.__value.setTextFormat(Qt.RichText)


class Status_Strip_Cls(Card_Cls):
    """
    Description:
        Hairline-divided cells across the full width. The cells (camera, resolution, system,
        updated, images, objects, inference, confidence) are public so the window can drive
        them. The order runs device state first (what the console is connected to), then the
        run counts, then the two derived aggregates last, since those cover every frame
        checked since the application started or the last Clear (not one camera connection):
        inference is the run MEDIAN analysis latency (a median so one slow frame does not swing
        it) and confidence the run MEAN detector score. Both aggregate labels name their scope and their statistic — the two differ deliberately,
        so flattening them to one word would misname them.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(padding=0, parent=parent)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.camera = Stat_Cell_Cls('Camera', 'Disconnected')
        self.resolution = Stat_Cell_Cls('Resolution', Style.CONST_NO_VALUE, mono=True)
        self.system = Stat_Cell_Cls('System', 'Ready')
        self.updated = Stat_Cell_Cls('Last update', Style.CONST_NO_VALUE, mono=True)
        self.images = Stat_Cell_Cls('Images analysed', '0', big=True)
        self.objects = Stat_Cell_Cls('Objects detected', '0', big=True)
        self.inference = Stat_Cell_Cls('Inference (run median)', Style.CONST_NO_VALUE, mono=True)
        self.confidence = Stat_Cell_Cls('Confidence (run mean)', Style.CONST_NO_VALUE, mono=True)

        for i, cell in enumerate([self.camera, self.resolution, self.system, self.updated,
                                  self.images, self.objects, self.inference, self.confidence]):
            if i:
                row.addWidget(Hairline(vertical=True))
            row.addWidget(cell, 1)

        self.box.addLayout(row)
        self.camera.Set_Value('Disconnected', Style.CONST_INK_MUTE, Style.CONST_INK_MUTE)
        self.system.Set_Value('Ready', Style.CONST_OK, Style.CONST_OK)


class Funding_Row_Cls(Card_Cls):
    """
    Description:
        The project and funding obligation, as part of the product — and the console's
        strongest EDIH-DIGIMAT statement: a deep-indigo brand band carrying the white
        institutional logos. Logo heights are set per logo, never globally: a wordmark
        and a two-line institutional block cannot share one height and stay optically
        equal, and the white lockups are proportioned differently from the old dark
        ones, so the heights are re-tuned for the band.
    """

    LOGOS = [
        ('edih-digimat-white.png', 20),
        (None, 0),                       # hairline divider
        ('partner-ministry-white.png', 36),
        ('funder-eu-white.png', 30),
    ]

    DISCLAIMER = (
        'Funded by the European Union. Views and opinions expressed are however those '
        'of the author(s) only and do not necessarily reflect those of the European '
        'Union or European Commission. Neither the European Union nor the granting '
        'authority can be held responsible for them.'
    )

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(padding=16, parent=parent)
        # Repaint the card as the deep-indigo band. The border is the band colour
        # itself, so the block reads as one solid indigo surface on the light page
        # rather than the light violet outline the white cards carry.
        self.setStyleSheet(
            '#card { background: %s; border: 1px solid %s; border-radius: %dpx; }'
            % (Style.CONST_BAND, Style.CONST_BAND, Style.CONST_RADIUS_CARD)
        )
        row = QHBoxLayout()
        row.setSpacing(32)
        row.addStretch(1)
        for name, height in self.LOGOS:
            if name is None:
                row.addWidget(Hairline(vertical=True, length=30, color=Style.CONST_BAND_LINE))
                continue
            pix = Load_Logo(name, height)
            label = QLabel()
            if not pix.isNull():
                label.setPixmap(pix)
            else:
                label.setText(name)  # a missing asset should be visible, not silent
                label.setStyleSheet('color: %s;' % Style.CONST_BAND_TEXT)
            row.addWidget(label)
        row.addStretch(1)
        self.box.addLayout(row)

        self.box.addSpacing(13)
        self.box.addWidget(Hairline(vertical=False, color=Style.CONST_BAND_LINE))

        # The disclaimer runs the full width rather than wrapping into a four-line
        # block: the same words, a third of the height. Lavender on the indigo band.
        note = QLabel(self.DISCLAIMER)
        note.setFont(Font(8))
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet('color: %s; padding-top: 10px;' % Style.CONST_BAND_TEXT)
        self.box.addWidget(note)
