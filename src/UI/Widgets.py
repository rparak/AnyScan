## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
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
# Custom Lib.: AnyScan domain — the shared Scene-Understanding formatter
#   ../Reporting/Core
from Reporting.Core import Object_Line

"""
Description:
    The console's widgets. Every widget is a behaviour class carrying the _Cls
    suffix and its Qt base. paintEvent is kept camelCase — Qt dispatches it by name.
    Attributes that other widgets or the window compose with (a card's `box`
    layout, a head's `badge`, the status strip's cells) stay public; everything
    else is name-mangled private state.
"""


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

        def r(x, y, w, h):
            return QRectF(x * s, y * s, w * s, h * s)

        if self.__kind == 'camera':
            p.drawRoundedRect(r(2, 6, 20, 14), 2 * s, 2 * s)
            p.drawLine(QPoint(int(9.5 * s), int(6 * s)), QPoint(int(11 * s), int(4 * s)))
            p.drawLine(QPoint(int(14.5 * s), int(6 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawLine(QPoint(int(11 * s), int(4 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawEllipse(r(8.4, 9.4, 7.2, 7.2))
        elif self.__kind == 'reading':
            p.drawRoundedRect(r(4, 4, 16, 16), 1.5 * s, 1.5 * s)
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

    def Current_View(self) -> str:
        """
        Description:
            The view currently selected ('annotated' or 'mask').

        Returns:
            (1) parameter [string]: The selected view.
        """

        return self.__view

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

        p.fillRect(self.rect(), QColor(43, 36, 85, 158))
        cx, cy = self.width() / 2.0, self.height() / 2.0

        if self.__animated:
            radius = 22
            arc = QRectF(cx - radius, cy - radius - 16, radius * 2, radius * 2)
            track = QPen(QColor(255, 255, 255, 40), 3)
            track.setCapStyle(Qt.RoundCap)
            p.setPen(track)
            p.setBrush(Qt.NoBrush)
            p.drawArc(arc, 0, 360 * 16)
            head = QPen(QColor('#f2f2f3'), 3)
            head.setCapStyle(Qt.RoundCap)
            p.setPen(head)
            # Qt angles are 1/16 degree, counter-clockwise; negate to turn the usual
            # clockwise direction. A 90-degree sweep reads as a spinner.
            p.drawArc(arc, int(-self.__spin * 16), 90 * 16)

        p.setPen(QColor('#f2f2f3'))
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
        if primary:
            self.setStyleSheet("""
                QPushButton { background: %s; border: 1px solid %s; color: #fff;
                              border-radius: %dpx; }
                QPushButton:hover:enabled { background: #3a3270; border-color: #3a3270; }
                QPushButton:pressed:enabled { background: #1f1a3f; border-color: #1f1a3f; }
                QPushButton:disabled { background: #cbc8db; border-color: #cbc8db;
                                       color: #f2f1f6; }
            """ % (Style.CONST_INK, Style.CONST_INK, Style.CONST_RADIUS_BTN))
        else:
            self.setStyleSheet("""
                QPushButton { background: #fff; border: 1px solid #e3e0ee; color: %s;
                              border-radius: %dpx; }
                QPushButton:hover:enabled { background: #f6f5fa; border-color: #d5d1e6; }
                QPushButton:disabled { color: #b6b2ca; border-color: #ecebf2; }
            """ % (Style.CONST_INK, Style.CONST_RADIUS_BTN))


class View_Toggle_Cls(QWidget):
    """
    Description:
        The Camera View's annotated/mask selector (§2b): two mutually-exclusive,
        checkable segments styled as one control. It emits View_Changed with the chosen
        key ('annotated' or 'mask') only on a user click, so restoring a remembered
        choice (Set_View) never re-emits and never loops. The window hides it until an
        analysis has completed — there is nothing to toggle before then.
    """

    # << SIGNAL >> #
    View_Changed = pyqtSignal(str)

    # The segments, in order, as (key, label).
    CONST_SEGMENTS = (('annotated', 'Annotated'), ('mask', 'Mask'))

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.__group = QButtonGroup(self)
        self.__group.setExclusive(True)
        # << PRIVATE >> #
        self.__buttons = {}
        for index, (key, label) in enumerate(self.CONST_SEGMENTS):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setFont(Font(9, QFont.DemiBold, tracking=2))
            button.setFixedHeight(30)
            button.setStyleSheet(self.__Segment_Style(index, len(self.CONST_SEGMENTS)))
            button.clicked.connect(lambda _checked, k=key: self.View_Changed.emit(k))
            self.__group.addButton(button)
            self.__buttons[key] = button
            row.addWidget(button)
        self.__buttons['annotated'].setChecked(True)

    def __Segment_Style(self, index: int, total: int) -> str:
        """
        Description:
            The stylesheet for one segment: only the outer corners are rounded, so the
            two buttons read as a single segmented control, and the checked segment
            carries the brand ink.

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
            QPushButton { background: #fff; border: 1px solid #e3e0ee; color: %s;
                          padding: 0 16px;
                          border-top-left-radius: %dpx; border-bottom-left-radius: %dpx;
                          border-top-right-radius: %dpx; border-bottom-right-radius: %dpx; }
            QPushButton:hover:enabled { background: #f6f5fa; }
            QPushButton:checked { background: %s; border-color: %s; color: #fff; }
            QPushButton:disabled { color: #b6b2ca; border-color: #ecebf2; }
        """ % (Style.CONST_INK, left, left, right, right, Style.CONST_INK, Style.CONST_INK))

    def Set_View(self, view: str) -> None:
        """
        Description:
            Reflect a view choice on the control WITHOUT emitting View_Changed — used to
            restore the operator's remembered choice when a new analysis completes.

        Args:
            (1) view [string]: 'annotated' or 'mask'.
        """

        button = self.__buttons.get(view)
        if button is not None and not button.isChecked():
            button.setChecked(True)


class Object_List_Cls(QWidget):
    """
    Description:
        The numbered object lines. Exposes `box`, the vertical layout the lines are
        rebuilt into. Every line's TEXT comes from the shared Reporting.Object_Line — the
        same source the Screen-Understanding file uses — so the panel and the file cannot
        number or word an object differently; this widget only styles it. The panel is a
        SINGLE colour (Style.CONST_INK): no per-object colours in the text — the object's
        colour lives on the frame, not here — with the 'Obj. N' label in bold and the
        description after it in regular weight, the only differentiation.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(13)

    def Set_Objects(self, objects: tp.List) -> None:
        """
        Description:
            Rebuild the numbered lines from the located objects.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: The located objects.
        """

        while self.box.count():
            item = self.box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, det in enumerate(objects):
            # The line text (number and wording) is the shared formatter's; the widget
            # only styles it — the 'Obj. N' label bold, the sentence regular weight, both
            # in the one panel colour — splitting on the formatter's ' - ' separator.
            prefix, _, sentence = Object_Line(i, det).partition(' - ')
            line = QLabel('<b>%s</b> %s' % (prefix, sentence))
            line.setFont(Font(15))
            line.setWordWrap(True)
            line.setTextFormat(Qt.RichText)
            line.setStyleSheet('color: %s;' % Style.CONST_INK)
            self.box.addWidget(line)


class Stat_Cell_Cls(QWidget):
    """
    Description:
        One cell of the status strip. The two counts are larger than the four
        states, because in a demo the counts are read from the back of the room and
        the states by the person at the keyboard.
    """

    def __init__(self, label: str, value: str = '', big: bool = False, dot: bool = False,
                 mono: bool = False, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__dot = dot
        self.__dot_color = None
        self.__color = Style.CONST_INK

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

    def Set_Value(self, text: str, color: tp.Optional[str] = None,
                  dot_color: tp.Optional[str] = None) -> None:
        """
        Description:
            Set the cell's value, optionally with a colour and a leading status dot.

        Args:
            (1) text [string]: The value text.
            (2) color [string]: Optional text colour.
            (3) dot_color [string]: Optional leading-dot colour (rich text).
        """

        self.__dot_color = dot_color
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
        Six hairline-divided cells across the full width. The cells (camera,
        resolution, system, updated, images, objects) are public so the window can
        drive them.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(padding=0, parent=parent)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.camera = Stat_Cell_Cls('Camera', 'Disconnected', dot=True)
        self.resolution = Stat_Cell_Cls('Resolution', Style.CONST_NO_VALUE, mono=True)
        self.system = Stat_Cell_Cls('System', 'Ready', dot=True)
        self.updated = Stat_Cell_Cls('Last update', Style.CONST_NO_VALUE, mono=True)
        self.images = Stat_Cell_Cls('Images analysed', '0', big=True)
        self.objects = Stat_Cell_Cls('Objects detected', '0', big=True)

        for i, cell in enumerate([self.camera, self.resolution, self.system,
                                  self.updated, self.images, self.objects]):
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
