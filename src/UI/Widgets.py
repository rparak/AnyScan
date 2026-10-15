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
import math
import os
import re
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QTimer, QRect, QRectF, QPoint, QPointF, QByteArray, pyqtSignal
from PyQt5.QtGui import (QColor, QFont, QFontMetrics, QFontMetricsF, QImage, QPainter, QPainterPath, QPen,
                         QPixmap, QPaintEvent)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (QWidget, QFrame, QLabel, QPushButton, QButtonGroup,
                             QVBoxLayout, QHBoxLayout, QSizePolicy, QApplication)
# Custom Lib.: AnyScan UI — design tokens and style helpers
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font, Hairline
# Custom Lib.: AnyScan UI — a logo's mark grid-fitted for a 1x display (Qt-free)
#   ../UI/Utilities/Grid_Fit
from UI.Utilities.Grid_Fit import Fit_Svg
# Custom Lib.: AnyScan UI — the brand's pixel motif for the funding band (Qt-free)
#   ../UI/Utilities/Pixel_Motif
from UI.Utilities.Pixel_Motif import Motif_Cells
# Custom Lib.: AnyScan domain — the confidence thresholds the object list colours numbers by
#   ../Parameters/Vision
from Parameters.Vision import Confidence_Thresholds_Str, Heatmap_Str
# Custom Lib.: AnyScan domain — the shared Scene-Understanding formatter
#   ../Reporting/Core
from Reporting.Core import Object_Label, Object_Confidence, Object_Size, Verdict_Lines, CONST_LABEL_SEPARATOR

"""
Description:
    The console's widgets. Every widget is a behaviour class carrying the _Cls
    suffix and its Qt base. paintEvent is kept camelCase — Qt dispatches it by name.
    Attributes that other widgets or the window compose with (a card's `box`
    layout, a head's `badge`, the status strip's cells) stay public; everything
    else is name-mangled private state.
"""


def Digit_Variants(text: str) -> tp.List[str]:
    """
    Description:
        A text with every digit replaced by each of 0-9 in turn ('12:05' -> '00:00', '11:11', ...,
        '99:99'). The widest of them is as wide as any text of that shape can be, whatever its digits.

    Args:
        (1) text [string]: The text.

    Returns:
        (1) parameter [Vector<string>]: The ten variants (the text alone when it has no digit).
    """

    if not re.search(r'\d', text):
        return [text]
    return [re.sub(r'\d', digit, text) for digit in '0123456789']


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
            '#card { background: %s; border: 1px solid %s; }' % (Style.CONST_CARD, Style.CONST_CARD_BORDER)
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
            p.drawRect(_Rect(2, 6, 20, 14))
            p.drawLine(QPoint(int(9.5 * s), int(6 * s)), QPoint(int(11 * s), int(4 * s)))
            p.drawLine(QPoint(int(14.5 * s), int(6 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawLine(QPoint(int(11 * s), int(4 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawEllipse(_Rect(8.4, 9.4, 7.2, 7.2))
        elif self.__kind == 'reading':
            p.drawRect(_Rect(4, 4, 16, 16))
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
        The verdict badge, coloured by meaning, as the poster's tags are: the purple words on the OK verdict's
        ground (the periwinkle), on the NOK verdict's (the orange-red's tint) or on Warning's amber, and muted
        on the card otherwise (Style.Label_Ground: the words clear 4.5:1 on every ground).
    """

    def __init__(self, text: str = 'Idle', parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(text, parent)
        self.setFont(Font(8, QFont.Bold))
        self.setFixedHeight(24)
        self.Set_Level('idle')

    def Set_Level(self, level: str) -> None:
        """
        Description:
            Repaint the badge for a severity level ('ok' | 'warn' | 'fail' | anything else): the ground of the OK,
            Warning or NOK verdict ('fail' is a catalogue mode's NOK), the idle card otherwise.

        Args:
            (1) level [string]: The severity level.
        """

        verdict = {'ok': 'OK', 'warn': 'Warning', 'fail': 'NOK'}.get(level)
        if verdict is not None:
            bg = Style.Label_Ground(verdict)
            border, fg = bg, Style.CONST_INK
        else:
            border, bg, fg = Style.CONST_CARD_BORDER, Style.CONST_CARD, Style.CONST_INK_MUTE
        self.setStyleSheet(
            'border: 1px solid %s; background: %s; color: %s; padding: 0 9px;' % (border, bg, fg)
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
        # Camera View's view toggle) into the head after the badge.
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
        The camera image, with the analysis renders (boxes already drawn in by Render_Views),
        the heatmap legend and the busy overlay. The image is letterboxed inside the widget,
        so the draw rectangle is recomputed on every paint — that maths lives here and
        nowhere else, the single most common source of an image that lands in the wrong place.
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
        # The third view, the heatmap (Vision.Utilities.Heatmap), and its Heatmap_Str for the legend
        # painted over it; both None when the analysis brought none. Likewise the fourth, a catalogue mode's
        # similarity overlay (Vision.Utilities.Heatmap.Render_Overlay) and its legend.
        self.__heatmap = None
        self.__legend = None
        self.__similarity = None
        self.__similarity_legend = None
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
        self.__mark = QSvgRenderer(os.path.join(Style.CONST_ASSETS, 'anyscan-mark.svg'))

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)

    def Show_Frame(self, image: QImage) -> None:
        """
        Description:
            Show a captured frame and drop any analysis renders. A new frame makes the
            previous frame's annotations stale — showing them over a different scene is
            the one genuinely misleading failure — so they are cleared here, and the
            window hides the view toggle to match.

        Args:
            (1) image [QImage(object)]: The frame to paint.
        """

        self.__image = image
        self.__annotated = None
        self.__mask = None
        self.__heatmap = None
        self.__legend = None
        self.__similarity = None
        self.__similarity_legend = None
        self.update()

    def Show_Views(self, annotated: QImage, mask: QImage, view: str, *, heatmap: tp.Optional[QImage],
                   legend: tp.Optional[Heatmap_Str], similarity: tp.Optional[QImage] = None,
                   similarity_legend: tp.Optional[Heatmap_Str] = None) -> None:
        """
        Description:
            Hold the analysis renders from the completed result and paint the selected
            one. The images are swapped in place by Set_View with no re-analysis and
            no disk read.

        Args:
            (1) annotated [QImage(object)]: The annotated image.
            (2) mask [QImage(object)]: The label mask image.
            (3) view [string]: The view to show now ('annotated', 'mask', 'heatmap' or 'similarity').
            (4) heatmap [QImage(object) or None]: REQUIRED, keyword-only: the heatmap image, or None
                when the analysis brought none.
            (5) legend [Heatmap_Str(object) or None]: REQUIRED, keyword-only: the heatmap's scale, title
                and marks, painted as its legend; None with no heatmap.
            (6) similarity [QImage(object) or None]: The similarity overlay (a catalogue mode's), or None.
            (7) similarity_legend [Heatmap_Str(object) or None]: Its scale and title; None with no overlay.
        """

        self.__annotated = annotated
        self.__mask = mask
        self.__heatmap = heatmap
        self.__legend = legend
        self.__similarity = similarity
        self.__similarity_legend = similarity_legend
        self.__view = view
        self.update()

    def Set_View(self, view: str) -> None:
        """
        Description:
            Swap the displayed analysis render. Instant: it only selects which held
            image paints, so the letterbox rect (and thus the on-screen region) is
            unchanged.

        Args:
            (1) view [string]: 'annotated', 'mask', 'heatmap' or 'similarity'.
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
            if self.__view == 'heatmap' and self.__heatmap is not None:
                return self.__heatmap
            if self.__view == 'similarity' and self.__similarity is not None:
                return self.__similarity
            return self.__mask if self.__view == 'mask' else self.__annotated
        return self.__image

    def Clear_Views(self) -> None:
        """
        Description:
            Drop the analysis renders but keep the frame. A new run supersedes the old,
            so its renders are cleared the moment it starts — the toggle cannot show, and
            two runs in quick succession cannot leave a mixed set of renders.
        """

        self.__annotated = None
        self.__mask = None
        self.__heatmap = None
        self.__legend = None
        self.__similarity = None
        self.__similarity_legend = None
        self.update()

    def Clear(self) -> None:
        """
        Description:
            Drop the frame and the analysis renders, returning to the empty state.
        """

        self.__image = None
        self.__annotated = None
        self.__mask = None
        self.__heatmap = None
        self.__legend = None
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
            A static overlay for the short, GUI-thread step (the scan). No
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
            Paint the dark surface, the letterboxed frame (the boxes are in its render), the
            heatmap's legend when it shows, and any busy overlay on top.
        """

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(Style.CONST_VIEWPORT))

        displayed = self.__Displayed()
        if displayed is None:
            self.__Paint_Empty(p)
        else:
            p.drawImage(self.__Draw_Rect(), displayed)
            if displayed is self.__heatmap and self.__legend is not None:
                self.__Paint_Legend(p, self.__legend)
            elif displayed is self.__similarity and self.__similarity_legend is not None:
                self.__Paint_Legend(p, self.__similarity_legend)

        if self.__busy:
            self.__Paint_Busy(p)
        p.end()

    def __Paint_Legend(self, p: QPainter, legend: Heatmap_Str) -> None:
        """
        Description:
            The heatmap's legend, in the viewport's bottom-left corner on a solid viewport-ink panel: the
            title and unit, the colour bar from the scale's low end to its high end (the high end marked
            '≥', since values above it take its colour), and each mark — the threshold applied — as a
            tick through the bar with its label under it. Painted from the Heatmap_Str alone, so a
            heatmap from another source brings its own legend.

        Args:
            (1) p [QPainter(object)]: The active painter.
            (2) legend [Heatmap_Str(object)]: The heatmap's scale, title and marks.
        """

        pad, bar_h, margin = 10, 10, 12
        font = Font(9)
        metrics = QFontMetrics(font)
        line = metrics.height()
        title = '%s (%s)' % (legend.Title, legend.Unit) if legend.Unit else legend.Title
        # The bar is as wide as the title (at least 192 px), so the title and its unit are never cut.
        bar_w = max(192, metrics.horizontalAdvance(title))
        panel = QRect(margin, self.height() - margin - (pad * 2 + line * 2 + bar_h + 8), bar_w + pad * 2,
                      pad * 2 + line * 2 + bar_h + 8)
        p.save()
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(panel, Style.Token_Color(Style.CONST_VIEWPORT))
        p.setFont(font)
        p.setPen(Style.Token_Color(Style.CONST_VIEWPORT_TEXT))
        x0, y = panel.left() + pad, panel.top() + pad
        p.drawText(QRect(x0, y, bar_w, line), Qt.AlignLeft | Qt.AlignVCenter, title)
        bar = QRect(x0, y + line + 4, bar_w, bar_h)
        colors = Style.Heatmap_Colors()
        for column in range(bar_w):
            p.fillRect(QRect(bar.left() + column, bar.top(), 1, bar_h),
                       Style.Token_Color(colors[round(column * (len(colors) - 1) / (bar_w - 1))]))
        labels_y = bar.bottom() + 4
        p.drawText(QRect(x0, labels_y, bar_w, line), Qt.AlignLeft | Qt.AlignVCenter, '%g' % legend.Low)
        p.drawText(QRect(x0, labels_y, bar_w, line), Qt.AlignRight | Qt.AlignVCenter, '≥ %g' % legend.High)
        span = float(legend.High - legend.Low)
        for value, label in legend.Marks:
            x = bar.left() + round(min(max((value - legend.Low) / span, 0.0), 1.0) * (bar_w - 1))
            p.fillRect(QRect(x - 1, bar.top() - 3, 2, bar_h + 6), Style.Token_Color(Style.CONST_BUSY_INK))
            width = metrics.horizontalAdvance(label)
            left = min(max(x - width // 2, x0), x0 + bar_w - width)
            p.setPen(Style.Token_Color(Style.CONST_BUSY_INK))
            p.drawText(QRect(left, labels_y, width, line), Qt.AlignCenter, label)
            p.setPen(Style.Token_Color(Style.CONST_VIEWPORT_TEXT))
        p.restore()

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
        p.setFont(Font(9.5))
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
        if self.__mark.isValid():
            # The mark is rendered as vectors at its drawn size, never scaled from a raster (which blurred it).
            size = min(210, int(self.width() * 0.44))
            p.setOpacity(0.92)
            self.__mark.render(p, QRectF((self.width() - size) // 2, cy - size // 2 - 20, size, size))
            text_top = cy + size // 2 - 8
        else:
            text_top = cy
        p.setPen(QColor(Style.CONST_VIEWPORT_TEXT))
        p.setFont(Font(9.5))
        p.drawText(QRect(0, text_top, self.width(), 60), Qt.AlignHCenter | Qt.AlignTop,
                   self.__empty_text)


class Tool_Button_Cls(QPushButton):
    """
    Description:
        48px tall, uppercase, tracked, outlined in the purple as the brand's buttons are. Exactly one is
        primary: a 2 px rule where the others have 1 px, filled purple under a white label when hovered or
        pressed. A plain button fills grey-lilac when hovered and periwinkle when pressed.
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
                QPushButton { background: %(card)s; border: 2px solid %(ink)s; color: %(ink)s; }
                QPushButton:hover:enabled { background: %(hover)s; border-color: %(hover)s;
                                            color: %(on_ink)s; }
                QPushButton:pressed:enabled { background: %(pressed)s; border-color: %(pressed)s;
                                              color: %(on_ink)s; }
                QPushButton:disabled { background: %(off_fill)s; border-color: %(off_border)s;
                                       color: %(off_text)s; }
            """ % {'card': Style.CONST_CARD, 'off_border': Style.CONST_CONTROL_DISABLED_BORDER, 'ink': Style.CONST_INK,
                   'on_ink': Style.CONST_ON_INK, 'hover': Style.CONST_INK_HOVER,
                   'pressed': Style.CONST_INK_PRESSED, 'off_fill': Style.CONST_PRIMARY_DISABLED_FILL,
                   'off_text': Style.CONST_PRIMARY_DISABLED_TEXT})
        else:
            self.setStyleSheet("""
                QPushButton { background: %(card)s; border: 1px solid %(border)s; color: %(ink)s; }
                QPushButton:hover:enabled { background: %(hover)s; border-color: %(hover_border)s;
                                            color: %(ink)s; }
                QPushButton:pressed:enabled { background: %(pressed)s; border-color: %(hover_border)s;
                                              color: %(ink)s; }
                QPushButton:disabled { background: %(card)s; border-color: %(off_border)s;
                                       color: %(off_text)s; }
            """ % {'card': Style.CONST_CARD, 'border': Style.CONST_CONTROL_BORDER, 'ink': Style.CONST_INK,
                   'hover': Style.CONST_CONTROL_HOVER, 'hover_border': Style.CONST_CONTROL_HOVER_BORDER,
                   'pressed': Style.CONST_CONTROL_PRESSED, 'off_border': Style.CONST_CONTROL_DISABLED_BORDER,
                   'off_text': Style.CONST_CONTROL_DISABLED_TEXT})


class Segmented_Control_Cls(QWidget):
    """
    Description:
        The console's ONE segmented control: a row of mutually-exclusive, checkable segments
        styled as a single pill, so every selector (the Camera View's annotated/mask/heatmap/similarity
        toggle, the header's Live/Trends/History/Log switch, History's verdict filter) shares one visual language. It emits
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
            button.setStyleSheet(self.__Segment_Style(index))
            button.clicked.connect(lambda _checked, k=key: self.Segment_Selected.emit(k))
            self.__group.addButton(button)
            self.__buttons[key] = button
            row.addWidget(button)
        if self.__buttons:
            next(iter(self.__buttons.values())).setChecked(True)

    def __Segment_Style(self, index: int) -> str:
        """
        Description:
            The stylesheet for one segment: outlined in the purple, each segment after the first
            without its left rule, so neighbours share one 1 px rule and the buttons read as a
            single segmented control; the checked segment is filled purple under a white label.

            Note:
                Qt ranks a selector by its pseudo-state count, not its order, so a bare
                ':hover:enabled' (two states) beats ':checked' (one) and repaints a SELECTED
                segment's fill with the unselected hover tint while ':checked' still supplies
                the white label — white on near-white. Each hover rule is therefore scoped to
                checked or unchecked and sets the background AND the label together, so no
                state can inherit a label colour chosen for a different fill.

        Args:
            (1) index [int]: The segment's position.

        Returns:
            (1) parameter [string]: The Qt stylesheet.
        """

        return ("""
            QPushButton { background: %(card)s; border: 1px solid %(border)s; color: %(ink)s;
                          padding: 0 16px; border-left-width: %(left_border)dpx; }
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
               'off_text': Style.CONST_CONTROL_DISABLED_TEXT, 'left_border': 1 if index == 0 else 0})

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

    def Set_Segment_Enabled(self, key: str, enabled: bool) -> None:
        """
        Description:
            Enable or disable one segment — a choice that is not available now stays visible, greyed.

        Args:
            (1) key [string]: The segment key.
            (2) enabled [bool]: Whether it can be chosen.
        """

        self.__buttons[key].setEnabled(enabled)

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
        The Camera View's annotated/mask/heatmap/similarity selector (§2b) — a Segmented_Control_Cls
        fixed to four segments, so it shares the console's one segmented-control look. The heatmap
        segment is disabled while the held analysis brought no heatmap, and the similarity segment
        outside a catalogue mode (a diagnostic overlay, not a defect map). It re-exposes
        the control under its domain names: View_Changed (a user click) and Set_View
        (restore a remembered choice without re-emitting). The window hides it until an
        analysis has completed — there is nothing to toggle before then.
    """

    # << SIGNAL >> #
    View_Changed = pyqtSignal(str)

    # The segments, in order, as (key, label).
    CONST_SEGMENTS = (('annotated', 'Annotated'), ('mask', 'Mask'), ('heatmap', 'Heatmap'), ('similarity', 'Similarity'))

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(self.CONST_SEGMENTS, parent=parent)
        # Relay the generic selection under this control's domain name.
        self.Segment_Selected.connect(self.View_Changed)

    def Set_View(self, view: str) -> None:
        """
        Description:
            Reflect a view choice WITHOUT emitting View_Changed — restore the operator's
            remembered view choice when a new analysis completes.

        Args:
            (1) view [string]: 'annotated', 'mask', 'heatmap' or 'similarity'.
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
        self.setStyleSheet('#objBlock { background: %s; }' % tint)

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

        # A catalogue mode's verdict, between the label and the description: the state word leads its
        # line, so the verdict reads in words, not only in the frame's colours (Reporting.Verdict_Lines).
        lines = Verdict_Lines(det)
        if lines:
            verdict = QLabel('\n'.join(lines))
            verdict.setTextFormat(Qt.PlainText)
            verdict.setFont(Font(self.__body_size, QFont.DemiBold))
            verdict.setWordWrap(True)
            verdict.setStyleSheet('color: %s; background: transparent;' % Style.CONST_INK)
            column.addWidget(verdict)

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

    def Reserve_Width(self, texts: tp.Sequence[str], dot: bool = False,
                      weights: tp.Optional[tp.Sequence[int]] = None) -> None:
        """
        Description:
            Hold the value at the width of the widest text it can show, so a change of value never
            resizes the cell and shifts the columns beside it. A digit in a text stands for any digit:
            each text is measured with every digit place filled by each of 0-9 (Digit_Variants), so a
            proportional face's widest digit is reserved too. Measured in the cell's own value font at
            each weight it can take.

        Args:
            (1) texts [Vector<string>]: The widest value of each kind the cell can show.
            (2) dot [bool]: The cell draws a status dot before its value.
            (3) weights [Vector<int>]: Every QFont weight the value can take; None keeps the cell's own.
        """

        font = QFont(self.__value.font())
        widths = []
        for weight in (weights or [font.weight()]):
            font.setWeight(weight)
            metrics = QFontMetrics(font)
            widths += [metrics.horizontalAdvance(('●  ' if dot else '') + variant)
                       for text in texts for variant in Digit_Variants(text)]
        self.__value.setMinimumWidth(max(widths) + 2)

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
            (2) color [string]: Optional status colour; the words are drawn in its Style.Status_Text_Color.
            (3) dot_color [string]: Optional leading-dot colour (rich text).
            (4) weight [int]: Optional QFont weight; None keeps the cell's own weight.
        """

        if weight is not None:
            font = self.__value.font()
            font.setWeight(weight)
            self.__value.setFont(font)
        # The words take the status colour's text twin (Status_Text_Color); the dot keeps the colour.
        ink = Style.Status_Text_Color(color or Style.CONST_INK)
        self.__value.setStyleSheet('color: %s;' % ink)
        self.__value.setText(('●  ' if dot_color else '') + text)
        if dot_color:
            self.__value.setText(
                '<span style="color:%s">●</span>&nbsp;&nbsp;'
                '<span style="color:%s">%s</span>' % (dot_color, ink, text)
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
        self.system = Stat_Cell_Cls('System', Style.CONST_NO_VALUE)
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
        # The window sets the System cell from its real state as soon as it is built (never a
        # standing 'Ready'); until then it shows no value.
        self.system.Set_Value(Style.CONST_NO_VALUE, Style.CONST_INK_MUTE, Style.CONST_INK_MUTE)


def Paint_To_Pixmap(widget: QWidget, paint: tp.Callable[[QPainter], None]) -> QPixmap:
    """
    Description:
        What a widget paints, on a transparent pixmap of its size at its device pixel ratio (the application's before
        its window is shown): for measuring a mark's ink (Style.Ink_Insets), never for drawing it.

    Args:
        (1) widget [QWidget(object)]: The widget.
        (2) paint [function]: Paints the widget's content with a given painter.

    Returns:
        (1) parameter [QPixmap(object)]: The render, tagged with its devicePixelRatio.
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
                     fitted: tp.Dict[float, QSvgRenderer]) -> QSvgRenderer:
    """
    Description:
        The renderer to draw a logo with on a painter: on a device of pixel ratio 1 its mark grid-fitted to whole pixels at
        the drawn height (UI.Utilities.Grid_Fit, built once per height and kept in `fitted`), on any other the SVG as
        delivered (docs/design-decisions.md, "The header logos are grid-fitted on a 1x display").

    Args:
        (1) painter [QPainter(object)]: The painter it will be drawn with.
        (2) path [string]: The SVG file.
        (3) delivered [QSvgRenderer(object)]: The SVG's renderer as delivered.
        (4) height [float]: The drawn height, in logical pixels.
        (5) mark_right [float]: The mark's right edge, in viewBox units.
        (6) fitted [Dict<float, QSvgRenderer(object)>]: The fitted renderers built so far, by height (filled in).

    Returns:
        (1) parameter [QSvgRenderer(object)]: The renderer.
    """

    if painter.device().devicePixelRatioF() != 1.0:
        return delivered
    if height not in fitted:
        with open(path, 'r', encoding='utf-8') as handle:
            svg = handle.read()
        fitted[height] = QSvgRenderer(QByteArray(Fit_Svg(svg, height / delivered.viewBoxF().height(), mark_right).encode('utf-8')))
    return fitted[height]


class Svg_Image_Cls(QWidget):
    """
    Description:
        An SVG logo at a height, its width the viewBox's aspect, rendered as vectors by a QSvgRenderer whenever the
        widget paints: it lands on the device pixels it is drawn on at any device pixel ratio, and is never a raster
        scaled to fit (docs/design-decisions.md, "Logos are rendered as vectors at paint time"). On a 1x display its
        mark, every shape left of mark_right, is grid-fitted to whole pixels (Svg_Renderer_For).
    """

    def __init__(self, name: str, height: int, mark_right: float, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName('svgImage')

        # << PRIVATE >> #
        self.__path = os.path.join(Style.CONST_ASSETS, name)
        self.__mark_right = mark_right
        self.__fitted = {}
        self.__renderer = QSvgRenderer(self.__path)
        box = self.__renderer.viewBoxF()
        self.__rect = QRectF(0.0, 0.0, height * box.width() / box.height() if box.height() else 0.0, float(height))
        self.setFixedSize(int(math.ceil(self.__rect.width())), height)

    def __Paint(self, painter: QPainter) -> None:
        """
        Description:
            Render the SVG into the widget's rectangle, grid-fitted when the painter's device is 1x.

        Args:
            (1) painter [QPainter(object)]: A painter on the widget or on a pixmap of its size.
        """

        Svg_Renderer_For(painter, self.__path, self.__renderer, self.__rect.height(), self.__mark_right,
                         self.__fitted).render(painter, self.__rect)

    def Render(self) -> QPixmap:
        """
        Description:
            The image on a transparent pixmap, for measuring its ink (Style.Ink_Insets); never drawn.

        Returns:
            (1) parameter [QPixmap(object)]: The render, tagged with its devicePixelRatio.
        """

        return Paint_To_Pixmap(self, self.__Paint)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Paint the SVG.

        Args:
            (1) event [QPaintEvent(object)]: The paint event (unused; the whole image is painted).
        """

        painter = QPainter(self)
        self.__Paint(painter)
        painter.end()


class Logo_Lockup_Cls(QWidget):
    """
    Description:
        The top bar's AnyScan lockup: the delivered logo without its tagline (Style.CONST_LOGO_WORDMARK_FILE, in the
        logo's own viewBox), rendered as vectors by a QSvgRenderer whenever the widget paints, so it lands on the
        device pixels it is drawn on at any device pixel ratio and is never a scaled raster (on a 1x display its mark
        grid-fitted to whole pixels, Svg_Renderer_For), and the tagline as live text in the UI font,
        Public Sans 400, where the logo outlines it and at its size (Style.CONST_LOGO_TAGLINE_ORIGIN,
        Style.CONST_LOGO_TAGLINE_SIZE, scaled to the lockup's height), in the logo's colour. Outlined, the tagline is a
        picture whose stems fall between pixels at DPR 1, where nothing can hint them; live text goes through the
        platform's rasteriser, which hints it at 9 pt and above, the size Style.Logo_Height gives it on a
        low-density display (docs/design-decisions.md, "The header draws the delivered logo and sets its tagline as
        live text").

        The size is logo geometry, converted to points through the widget's own logical DPI so the pixel size
        is the logo's on any screen, and built with Style.Font like every UI font.
    """

    def __init__(self, height: int, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__wordmark_path = os.path.join(Style.CONST_ASSETS, Style.CONST_LOGO_WORDMARK_FILE)
        self.__wordmark = QSvgRenderer(self.__wordmark_path)
        self.__fitted = {}
        box = self.__wordmark.viewBoxF()
        scale = height / box.height()
        self.__wordmark_rect = QRectF(0.0, 0.0, box.width() * scale, float(height))
        self.__font = Font(Style.CONST_LOGO_TAGLINE_SIZE * scale * 72.0 / self.logicalDpiY())
        x, y = Style.CONST_LOGO_TAGLINE_ORIGIN
        self.__origin = QPointF((x - box.x()) * scale, (y - box.y()) * scale)
        right = self.__origin.x() + QFontMetricsF(self.__font).tightBoundingRect(Style.CONST_TAGLINE).right() \
            + Style.CONST_LOGO_MARGIN * scale
        right = max(right, self.__wordmark_rect.width())

        self.setAccessibleName('AnyScan. %s' % Style.CONST_TAGLINE)
        self.setFixedSize(int(math.ceil(right)), height)

    def __Paint(self, painter: QPainter) -> None:
        """
        Description:
            Draw the wordmark and the tagline.

        Args:
            (1) painter [QPainter(object)]: A painter on the widget or on a pixmap of its size.
        """

        Svg_Renderer_For(painter, self.__wordmark_path, self.__wordmark, self.__wordmark_rect.height(), Style.CONST_LOGO_MARK_RIGHT,
                         self.__fitted).render(painter, self.__wordmark_rect)
        painter.setFont(self.__font)
        painter.setPen(QColor(Style.CONST_LOGO_INK))
        painter.drawText(self.__origin, Style.CONST_TAGLINE)

    def Render(self) -> QPixmap:
        """
        Description:
            The lockup on a transparent pixmap at the widget's device pixel ratio, for measuring its ink
            (Style.Ink_Insets) before the window is shown. It is never drawn: the widget paints the vectors itself.

        Returns:
            (1) parameter [QPixmap(object)]: The render, tagged with its devicePixelRatio.
        """

        return Paint_To_Pixmap(self, self.__Paint)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Paint the lockup.

        Args:
            (1) event [QPaintEvent(object)]: The paint event (unused; the whole lockup is painted).
        """

        painter = QPainter(self)
        self.__Paint(painter)
        painter.end()


class Funding_Row_Cls(Card_Cls):
    """
    Description:
        The project and funding obligation, as part of the product: a solid purple band with its logos centred as one
        group, the EDIH-DIGIMAT wordmark, a faint vertical rule, and the Ministry of Industry and Trade's logo with the
        EU emblem and "Funded by the European Union". The logos are solid white SVGs traced
        from the white PNGs (no official vector files exist; docs/design-decisions.md, "The band's logos are traced
        SVGs"), rendered as vectors at paint time; the Ministry's lion is white without its field, as Czech ministries
        show their logo on dark grounds. The EU emblem is as tall as the Ministry's logo, so it is at least the size of
        the biggest other logo, as the EU's visibility rules ask. The rest of the band carries the brand's pixel motif
        (UI.Utilities.Pixel_Motif), white squares at a low opacity, decorative only, clustered at the band's two ends;
        no square comes within the EU emblem's protection area of any logo (CLEAR_SPACE). The EU disclaimer is not in
        the window's band: the README and the architecture diagram's band carry it (DISCLAIMER).
    """

    LOGOS = [
        ('edih-digimat-white.svg', 24),
        (None, 0),                       # hairline divider
        ('partner-ministry-white.svg', 56),
        ('funder-eu-white.svg', 56),
    ]

    # The EU disclaimer, word for word, as the architecture diagram's band and the README carry it.
    #   Unit [string]
    DISCLAIMER = (
        'Funded by the European Union. Views and opinions expressed are however those '
        'of the author(s) only and do not necessarily reflect those of the European '
        'Union or European Commission. Neither the European Union nor the granting '
        'authority can be held responsible for them.'
    )

    # The vertical rule's length, as a share of the tallest logo.
    #   Unit [ratio]
    DIVIDER_SHARE = 0.75
    # The clear space kept free of squares around every logo: the EU emblem's protection area, half the flag's height
    # ("The use of the EU emblem in the context of EU programmes 2021-2027", Protection area), the flag being as tall as
    # the EU logo.
    #   Unit [px]
    CLEAR_SPACE = 28
    # The motif: the cell's side (the band's 90 px are six cells), the chance a cell at the band's end is filled, how
    # many cells in it thins to nothing, the share of squares in the stronger tint, and the two tints' opacities.
    #   Unit [px], [0..1], [cells], [0..1], [0..1]
    MOTIF_CELL = 15
    MOTIF_FILL = 0.30
    MOTIF_REACH = 16
    MOTIF_STRONG = 0.4
    MOTIF_ALPHA = (0.07, 0.12)

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(padding=16, parent=parent)
        # Repaint the card as the purple band. The border is the band colour itself, so the block reads as one
        # solid surface on the white page.
        self.setStyleSheet(
            '#card { background: %s; border: 1px solid %s; }' % (Style.CONST_BAND, Style.CONST_BAND)
        )
        line = Style.Token_Css(Style.CONST_BAND_LINE, Style.CONST_BAND_LINE_ALPHA)
        rule = int(round(self.DIVIDER_SHARE * max(height for _, height in self.LOGOS)))
        # The whole group centred (stretch on both sides); the rule falls where it falls in it, slightly left of the
        # band's middle, as the Ministry's and the EU's logos together are wider than the EDIH-DIGIMAT wordmark.
        row = QHBoxLayout()
        row.setSpacing(Style.CONST_MARK_GAP)
        row.addStretch(1)
        for name, height in self.LOGOS:
            if name is None:
                row.addWidget(Hairline(vertical=True, length=rule, color=line))
                continue
            # The traced outlines are curves: nothing in them is grid-fitted (mark_right 0).
            row.addWidget(Svg_Image_Cls(name, height, 0.0))
        row.addStretch(1)
        self.box.addLayout(row)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Paint the purple band, then the pixel motif on it, clear of every logo by CLEAR_SPACE.

        Args:
            (1) event [QPaintEvent(object)]: The paint event.
        """

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
