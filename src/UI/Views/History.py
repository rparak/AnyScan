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
# File Name: ../UI/Views/History.py
## =========================================================================== ##

# System (Default)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QEvent, QRect, QRectF, QPoint, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QFrame, QPushButton, QVBoxLayout, QHBoxLayout,
                             QGridLayout, QScrollArea, QSizePolicy, QApplication)
# Custom Lib.: AnyScan UI — design tokens, style helpers and shared widgets
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font, Hairline
#   ../UI/Widgets
from UI.Widgets import Card_Cls, Card_Head_Cls, Segmented_Control_Cls, Object_List_Cls, Meta_Row
# Custom Lib.: AnyScan — the Qt-free capture-set reader (the view never re-reads or parses)
#   ../UI/Capture
from UI.Capture import Discover_Capture_Sets, CONST_CAPTURE_RETENTION_SETS
# Custom Lib.: AnyScan domain — the detection structure, the shared formatter, the palette
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str, Confidence_Thresholds_Str
#   ../Parameters/General — the one default for the classification flag
from Parameters.General import CONST_CLASSIFICATION_ENABLED_DEFAULT
#   ../Reporting/Core
from Reporting.Core import Screen_Header
#   ../Parameters/Theme
from Parameters.Theme import Verdict_Color, Detection_Color

"""
Description:
    The History view — a browser of the capture sets on disk. It reads them through the Qt-free
    Discover_Capture_Sets (the view never parses a file itself), as master and detail. The LEFT
    panel ('Captures') is a compact, scrollable thumbnail grid — newest-first, grouped by session,
    with the filter and the retention note; the thumbnails only have to be recognisable, so they
    are small and the panel is narrow, giving the width back to the detail.

    The DETAIL panel shows the two result images — Annotated and Mask — SIDE BY SIDE at equal
    size, so they can be compared (there is no Raw/Annotated/Mask toggle). Raw is not shown for a
    successful set (it is still written to disk); a PARTIAL set — a failed or stopped analysis with
    only a raw frame — instead renders that raw frame across the full width under a failure banner, because
    that frame is the thing worth looking at. The set identity (id, date, time) and the set-level
    record (session, objects, task, inference time, frame mean confidence) are always visible.

    The object text lives behind an INFO control, not inline: pressing Info slides a panel in from
    the right with the full Scene-Understanding text as it stood at analysis time — the background
    sentence, the object list with confidences, and the unscored-object note — built from the
    '_objects.json' through the SAME shared formatter as the Live panel and the '.txt' file. It
    narrows the images rather than covering them, dismisses with Escape or Info, and keeps object
    selection working: clicking a row highlights that object's box in the Annotated pane.
"""
# The thumbnail grid: columns per session group and the thumbnail's drawn size (px) — small, so
# more sets are visible at once and the panel stays narrow.
#   Unit [int]
CONST_THUMB_COLUMNS = 2
CONST_THUMB_W = 128
CONST_THUMB_H = 80

# The Info side panel's open width (px), and its slide duration (ms).
#   Unit [int]
CONST_INFO_PANEL_WIDTH = 330
CONST_INFO_SLIDE_MS = 160

# The retention note, stating the rolling-window bound so nobody assumes an archive.
#   Unit [string]
CONST_RETENTION_NOTE = ('Rolling window — the newest %d sets are kept; older sets are evicted.'
                        % CONST_CAPTURE_RETENTION_SETS)
# The note shown when the set being viewed is evicted out from under the reader.
#   Unit [string]
CONST_REMOVED_NOTE = ('This capture set fell outside the retention window and was removed. '
                      'Select another set from the list.')

# The filter segments, in order as (key, label).
#   Unit [Vector<Tuple<string> 1x2>]
CONST_FILTER_SEGMENTS = (('all', 'All'), ('ok', 'OK'), ('nok', 'NOK'))

# The empty-grid messages, per filter — the NOK one names why it is expected to be empty today.
#   Unit [Dict<string, string>]
CONST_EMPTY_MESSAGES = {
    'all': 'No captures in this run yet. Analyse an image to begin.',
    'ok': 'No OK results in the current history.',
    'nok': 'No NOK results — no classifier is running yet, so no object has been judged.'}


class History_Image_Cls(QWidget):
    """
    Description:
        One image pane. It draws the image at its own aspect ratio with a hairline border — no
        wide dark letterbox bands — and, when an object is selected, highlights that object's box
        mapped through the same fit. Two panes of equal size therefore scale identically. With no
        image it shows a centred message.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__pixmap = None
        self.__message = ''
        self.__highlight = None                          # (x, y, w, h) in frame pixels, or None

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(160)

    def Set_Image(self, pixmap: tp.Optional[QPixmap], message: str = '') -> None:
        """
        Description:
            Show a pixmap (fitted to aspect) or, when it is None, a centred message.

        Args:
            (1) pixmap [QPixmap(object) or None]: The image, or None to show the message.
            (2) message [string]: The message shown when there is no image.
        """

        self.__pixmap = pixmap
        self.__message = message
        self.update()

    def Set_Highlight(self, bbox: tp.Optional[tp.Tuple[int, int, int, int]]) -> None:
        """
        Description:
            Highlight one object's box (frame pixels), or clear it with None.

        Args:
            (1) bbox [Vector<int> 1x4 or None]: The object's box (x, y, w, h), or None.
        """

        self.__highlight = bbox
        self.update()

    def __Fitted_Rect(self) -> QRect:
        """
        Description:
            Where the pixmap sits, fitted to aspect and centred — the drawn image rectangle.

        Returns:
            (1) parameter [QRect(object)]: The image's rectangle (empty when no pixmap).
        """

        if self.__pixmap is None or self.__pixmap.isNull():
            return QRect()
        scale = min(self.width() / self.__pixmap.width(),
                    self.height() / self.__pixmap.height())
        w = int(self.__pixmap.width() * scale)
        h = int(self.__pixmap.height() * scale)
        return QRect((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    # << QT OVERRIDE >> #
    def paintEvent(self, event: tp.Any) -> None:
        """
        Description:
            Paint the fitted image with a hairline border (or a centred message), then the object
            highlight mapped into the fitted rectangle.
        """

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self.__pixmap is None or self.__pixmap.isNull():
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), 8, 8)
            painter.fillPath(path, QColor(Style.CONST_BG))
            painter.setPen(QColor(Style.CONST_INK_MUTE))
            painter.setFont(Font(9.5, mono=True))
            painter.drawText(self.rect(), Qt.AlignCenter, self.__message)
            painter.end()
            return

        rect = self.__Fitted_Rect()
        painter.drawPixmap(rect, self.__pixmap)
        painter.setPen(QPen(QColor(Style.CONST_CARD_BORDER), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        if self.__highlight is not None:
            sx = rect.width() / float(self.__pixmap.width())
            sy = rect.height() / float(self.__pixmap.height())
            x, y, w, h = self.__highlight
            box = QRect(rect.left() + int(x * sx), rect.top() + int(y * sy),
                        int(w * sx), int(h * sy))
            painter.setPen(QPen(Style.Token_Color(Style.CONST_THUMB_HIGHLIGHT), 3))
            painter.setBrush(Style.Token_Color(Style.CONST_THUMB_HIGHLIGHT, Style.CONST_THUMB_HIGHLIGHT_FILL_ALPHA))
            painter.drawRect(box)
        painter.end()


class Thumb_Card_Cls(QFrame):
    """
    Description:
        One capture set in the grid: a small thumbnail (recognisable, not readable), its time, and
        its object count — or, for a partial set, a failure marker in the log's ERROR colour. The
        thumbnail loads lazily as the card scrolls into view. Clicking emits Clicked; the selected
        card is outlined in the set's verdict colour.
    """

    # << SIGNAL >> #
    Clicked = pyqtSignal(object)

    def __init__(self, cap: tp.Any, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__cap = cap
        self.__loaded = False

        self.setObjectName('thumbCard')
        self.setCursor(Qt.PointingHandCursor)
        self.Set_Selected(False)

        column = QVBoxLayout(self)
        column.setContentsMargins(5, 5, 5, 5)
        column.setSpacing(3)

        self.__thumb = QLabel()
        self.__thumb.setFixedSize(CONST_THUMB_W, CONST_THUMB_H)
        self.__thumb.setAlignment(Qt.AlignCenter)
        self.__thumb.setWordWrap(True)
        self.__thumb.setStyleSheet('background: %s; border-radius: 5px; color: %s;'
                                   % (Style.CONST_VIEWPORT, Style.CONST_VIEWPORT_TEXT))
        self.__thumb.setText('…')
        column.addWidget(self.__thumb)

        time_label = QLabel(self.__Time_Text())
        time_label.setFont(Font(7.5, mono=True))
        time_label.setStyleSheet('color: %s;' % Style.CONST_INK)
        column.addWidget(time_label)

        count_label = QLabel(self.__Count_Text())
        count_label.setFont(Font(7.5, QFont.DemiBold if cap.Partial else QFont.Normal))
        count_label.setStyleSheet('color: %s;'
                                  % (Style.CONST_LOG_ERROR if cap.Partial else Style.CONST_INK_MUTE))
        column.addWidget(count_label)

    def Cap(self) -> tp.Any:
        """
        Description:
            The capture set this card represents.

        Returns:
            (1) parameter [Capture_Set_Str(object)]: The set.
        """

        return self.__cap

    def Loaded(self) -> bool:
        """
        Description:
            Whether the thumbnail has already been loaded.

        Returns:
            (1) parameter [bool]: True once loaded.
        """

        return self.__loaded

    def Load(self) -> None:
        """
        Description:
            Load the thumbnail pixmap from disk, once. A partial set (or a missing thumbnail)
            shows a failure placeholder in the ERROR colour, not a muted 'no preview'.
        """

        if self.__loaded:
            return
        self.__loaded = True
        path = self.__cap.Thumb_Path
        if path:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                self.__thumb.setPixmap(pixmap.scaled(CONST_THUMB_W, CONST_THUMB_H,
                                                     Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        # No thumbnail — a partial set (a failed analysis, or one stopped at close). Marked as an
        # error, not a bland placeholder.
        self.__thumb.setStyleSheet('background: %s; border-radius: 5px; color: %s;'
                                   % (Style.CONST_VIEWPORT, Style.CONST_ERROR_ON_DARK))
        self.__thumb.setText('ANALYSIS\nFAILED')
        self.__thumb.setFont(Font(7.5, QFont.DemiBold, tracking=1))

    def Set_Selected(self, selected: bool, color: tp.Optional[str] = None) -> None:
        """
        Description:
            Outline the card when selected, in the set's verdict colour (passed by the view); a
            plain hairline border otherwise.

        Args:
            (1) selected [bool]: Whether this card is the selected one.
            (2) color [string]: The verdict colour to outline with when selected.
        """

        border = (color or Style.CONST_INK) if selected else Style.CONST_CARD_BORDER
        width = 2 if selected else 1
        self.setStyleSheet('#thumbCard { background: %s; border: %dpx solid %s;'
                           ' border-radius: 9px; }' % (Style.CONST_CARD, width, border))

    def __Time_Text(self) -> str:
        """
        Description:
            The set's time, from its timestamp when present, else its set id.

        Returns:
            (1) parameter [string]: The time label text.
        """

        stamp = self.__cap.Timestamp
        if stamp and 'T' in stamp:
            return stamp.split('T', 1)[1]
        return self.__cap.Set_Id

    def __Count_Text(self) -> str:
        """
        Description:
            The object count, or a failed marker for a partial set.

        Returns:
            (1) parameter [string]: The count label text.
        """

        if self.__cap.Partial:
            return 'Analysis failed'
        count = len(self.__cap.Objects)
        return '%d object%s' % (count, '' if count == 1 else 's')

    # << QT OVERRIDE >> #
    def mousePressEvent(self, event: tp.Any) -> None:
        """
        Description:
            Emit Clicked with this set on a left click.
        """

        if event.button() == Qt.LeftButton:
            self.Clicked.emit(self.__cap)
        super().mousePressEvent(event)


class History_View_Cls(QWidget):
    """
    Description:
        The History view: the compact 'Captures' grid on the left, the selected set on the right.
        It is given the captures root and reads it on Refresh (the window calls Refresh when
        History is shown, and when a set is written or evicted while History is on screen). Everything it renders comes from the
        Qt-free reader.
    """

    def __init__(self, captures_root: tp.Optional[str] = None, run_id: str = '',
                 classification_enabled: bool = CONST_CLASSIFICATION_ENABLED_DEFAULT,
                 parent: tp.Optional[QWidget] = None, *,
                 Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__root = captures_root
        # The current application run: History lists ONLY the sets written in it (matched by
        # run id), so earlier runs stay on disk but are not shown.
        self.__run_id = run_id
        # Whether the configuration in force classifies: the OK/NOK filter shows iff it does. It can
        # change only before the run's first CONNECT (Set_Configuration) — before any set of the run
        # exists — so every set listed shares it; each set also names its configuration.
        self.__classification_enabled = classification_enabled
        # The confidence thresholds numbers are coloured by — the ones in force NOW, applied to
        # every set shown, whatever was in force when it was captured (a viewing preference).
        self.__thresholds = Confidence_Thresholds_Str
        self.__sets = []
        self.__cards = []
        self.__selected_id = None
        self.__detail_cap = None
        self.__info_open = False
        self.__info_anim = None

        grid = QGridLayout(self)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__Build_List_Panel(), 0, 0)
        grid.addWidget(self.__Build_Detail_Panel(), 0, 1)
        grid.setColumnStretch(0, 25)          # narrow browser
        grid.setColumnStretch(1, 75)          # the reclaimed width goes to the images
        grid.setRowStretch(0, 1)

    # ------------------------------------------------------------------ construction

    def __Build_List_Panel(self) -> Card_Cls:
        """
        Description:
            The left 'Captures' card: the head with the OK/NOK filter, the retention note, and the
            scrollable, session-grouped thumbnail grid.

        Returns:
            (1) parameter [Card_Cls(object)]: The list card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('reading', 'Captures')
        self.__filter = Segmented_Control_Cls(CONST_FILTER_SEGMENTS)
        self.__filter.Segment_Selected.connect(lambda _key: self.__Rebuild_List())
        head.box.addWidget(self.__filter)
        card.box.addWidget(head)

        note = QLabel(CONST_RETENTION_NOTE)
        note.setFont(Font(8.5))
        note.setWordWrap(True)
        note.setStyleSheet('color: %s; padding-bottom: 10px;' % Style.CONST_INK_MUTE)
        card.box.addWidget(note)

        self.__list_body = QWidget()
        self.__list_body.setStyleSheet('background: transparent;')
        self.__list_box = QVBoxLayout(self.__list_body)
        self.__list_box.setContentsMargins(2, 2, 2, 2)
        self.__list_box.setSpacing(10)
        self.__list_box.setAlignment(Qt.AlignTop)

        self.__list_scroll = QScrollArea()
        self.__list_scroll.setWidget(self.__list_body)
        self.__list_scroll.setWidgetResizable(True)
        self.__list_scroll.setFrameShape(QFrame.NoFrame)
        self.__list_scroll.setStyleSheet(Style.Scroll_Style(framed=False))
        self.__list_scroll.verticalScrollBar().valueChanged.connect(lambda _v: self.__Load_Visible())
        card.box.addWidget(self.__list_scroll, 1)
        return card

    def __Build_Detail_Panel(self) -> Card_Cls:
        """
        Description:
            The right card: the head (title + Info toggle), the set identity, the failure banner,
            the two image panes beside the Info side panel, and the always-visible set-level table.

        Returns:
            (1) parameter [Card_Cls(object)]: The detail card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('camera', 'Capture set')
        self.__info_button = QPushButton('ⓘ  Info')
        self.__info_button.setCheckable(True)
        self.__info_button.setCursor(Qt.PointingHandCursor)
        self.__info_button.setFont(Font(9, QFont.DemiBold, tracking=2))
        self.__info_button.setFixedHeight(30)
        self.__info_button.setStyleSheet(
            'QPushButton { background: %s; border: 1px solid %s; color: %s;'
            ' padding: 0 14px; border-radius: %dpx; }'
            'QPushButton:hover:enabled { background: %s; }'
            'QPushButton:checked { background: %s; border-color: %s; color: %s; }'
            'QPushButton:disabled { color: %s; border-color: %s; }'
            % (Style.CONST_CARD, Style.CONST_CONTROL_BORDER, Style.CONST_INK, Style.CONST_RADIUS_BTN,
               Style.CONST_CONTROL_HOVER, Style.CONST_INK, Style.CONST_INK, Style.CONST_ON_INK,
               Style.CONST_CONTROL_DISABLED_TEXT, Style.CONST_CONTROL_DISABLED_BORDER))
        self.__info_button.clicked.connect(self.__Toggle_Info)
        head.box.addWidget(self.__info_button)
        card.box.addWidget(head)

        # The set identity, prominently: the id (which links to the log) and the timestamp.
        identity = QWidget()
        identity_row = QHBoxLayout(identity)
        identity_row.setContentsMargins(2, 0, 2, 8)
        identity_row.setSpacing(8)
        self.__identity_id = QLabel()
        self.__identity_id.setFont(Font(11, QFont.DemiBold))
        self.__identity_id.setStyleSheet('color: %s;' % Style.CONST_INK)
        identity_row.addWidget(self.__identity_id)
        self.__identity_time = QLabel()
        self.__identity_time.setFont(Font(9.5, mono=True))
        self.__identity_time.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        identity_row.addWidget(self.__identity_time)
        identity_row.addStretch(1)
        card.box.addWidget(identity)

        self.__banner = QLabel()
        self.__banner.setFont(Font(10))
        self.__banner.setWordWrap(True)
        self.__banner.setStyleSheet('color: %s; padding: 0 2px 10px 2px;' % Style.CONST_LOG_ERROR)
        self.__banner.hide()
        card.box.addWidget(self.__banner)

        # The images and the Info side panel share one row: opening Info narrows the images.
        content = QWidget()
        content_row = QHBoxLayout(content)
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(Style.CONST_GAP)
        content_row.addWidget(self.__Build_Images(), 1)
        content_row.addWidget(self.__Build_Info_Panel())
        card.box.addWidget(content, 1)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 8, 0, 0)
        meta.setSpacing(0)
        self.__meta_session = Meta_Row(meta, 'Connection', compact=True, mono=True, first=True)
        self.__meta_objects = Meta_Row(meta, 'Objects', compact=True)
        self.__meta_task = Meta_Row(meta, 'Task', compact=True)
        self.__meta_configuration = Meta_Row(meta, 'Configuration', compact=True)
        self.__meta_latency = Meta_Row(meta, 'Inference time', compact=True, mono=True)
        self.__meta_confidence = Meta_Row(meta, 'Confidence (mean)', compact=True, mono=True)
        card.box.addLayout(meta)
        return card

    def __Build_Images(self) -> QWidget:
        """
        Description:
            The two image panes side by side, equal size (equal stretch) so they scale together.
            Each is a captioned History_Image_Cls; the captions and images are reassigned per set
            (Annotated/Mask for a full set, Raw full-width for a partial one).

        Returns:
            (1) parameter [QWidget(object)]: The images row widget.
        """

        self.__images_row = QWidget()
        row = QHBoxLayout(self.__images_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(Style.CONST_GAP)

        self.__pane_a, self.__caption_a, self.__image_a = self.__Build_Pane()
        self.__pane_b, self.__caption_b, self.__image_b = self.__Build_Pane()
        row.addWidget(self.__pane_a, 1)
        row.addWidget(self.__pane_b, 1)
        return self.__images_row

    def __Build_Pane(self) -> tp.Tuple[QWidget, QLabel, History_Image_Cls]:
        """
        Description:
            One captioned image pane: a small caption above the image.

        Returns:
            (1) parameter [Tuple]: (the pane widget, its caption label, its image widget).
        """

        pane = QWidget()
        column = QVBoxLayout(pane)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(6)
        caption = QLabel('')
        caption.setFont(Font(8.5, QFont.Bold, tracking=6))
        caption.setAlignment(Qt.AlignHCenter)
        caption.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        column.addWidget(caption)
        image = History_Image_Cls()
        column.addWidget(image, 1)
        return pane, caption, image

    def __Build_Info_Panel(self) -> QWidget:
        """
        Description:
            The Info side panel: a fixed-width content column inside a clip widget whose width the
            slide animates (0 ↔ CONST_INFO_PANEL_WIDTH). It holds the full Scene-Understanding
            text — the background lead, the selectable object list, and the unscored-object note —
            built from the shared formatter, so it matches the Live panel and the '.txt'.

        Returns:
            (1) parameter [QWidget(object)]: The clip widget (starts collapsed and hidden).
        """

        clip = QWidget()
        clip.setMaximumWidth(0)                          # collapsed; the slide animates this
        clip.setMinimumWidth(0)
        clip_row = QHBoxLayout(clip)
        clip_row.setContentsMargins(0, 0, 0, 0)

        inner = QWidget()
        inner.setFixedWidth(CONST_INFO_PANEL_WIDTH)
        inner.setObjectName('infoPanel')
        inner.setStyleSheet('#infoPanel { border-left: 1px solid %s; }' % Style.CONST_LINE)
        column = QVBoxLayout(inner)
        column.setContentsMargins(14, 0, 2, 0)
        column.setSpacing(10)

        self.__info_title = QLabel('Scene understanding')
        self.__info_title.setFont(Font(Style.CONST_TYPE_INFO_HEADING, QFont.DemiBold, tracking=-1))
        self.__info_title.setStyleSheet('color: %s;' % Style.CONST_INK)
        column.addWidget(self.__info_title)

        body = QWidget()
        body.setStyleSheet('background: transparent;')
        body_col = QVBoxLayout(body)
        body_col.setContentsMargins(0, 0, 0, 0)
        body_col.setSpacing(12)
        # The background paragraph is body text — the same size as the object descriptions, and
        # below the object labels and the heading (read up close, so the Info tokens, not the
        # larger Live ones).
        self.__info_lead = QLabel()
        self.__info_lead.setFont(Font(Style.CONST_TYPE_INFO_BODY))
        self.__info_lead.setWordWrap(True)
        self.__info_lead.setStyleSheet('color: %s;' % Style.CONST_INK)
        body_col.addWidget(self.__info_lead)
        self.__object_list = Object_List_Cls(selectable=True,
                                             label_size=Style.CONST_TYPE_INFO_LABEL,
                                             body_size=Style.CONST_TYPE_INFO_BODY,
                                             confidence_size=Style.CONST_TYPE_INFO_META,
                                             Confidence_Thresholds_Str=self.__thresholds)
        self.__object_list.Object_Selected.connect(self.__On_Object_Selected)
        body_col.addWidget(self.__object_list)
        self.__score_note = QLabel()
        self.__score_note.setFont(Font(Style.CONST_TYPE_INFO_META))
        self.__score_note.setWordWrap(True)
        self.__score_note.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        self.__score_note.hide()
        body_col.addWidget(self.__score_note)
        body_col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(Style.Scroll_Style(framed=False))
        column.addWidget(scroll, 1)

        clip_row.addWidget(inner)
        self.__info_panel = clip
        self.__info_panel.hide()
        return clip

    # -------------------------------------------------------------------- public API

    def Set_Configuration(self, classification_enabled: bool,
                          Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        """
        Description:
            Adopt a newly loaded configuration's classification flag and confidence thresholds,
            and redraw: the filter follows the flag, every number the thresholds.

        Args:
            (1) classification_enabled [bool]: Whether the configuration classifies.
            (2) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: Its thresholds.
        """

        self.__classification_enabled = classification_enabled
        self.__thresholds = Confidence_Thresholds_Str
        self.__object_list.Set_Thresholds(Confidence_Thresholds_Str)
        self.__selected_id = None
        self.Refresh()

    def Refresh(self) -> None:
        """
        Description:
            Rediscover the sets on disk and rebuild the grid. Called when History is shown, and
            when a set is written or evicted while it is on screen. If the set being viewed is gone (evicted), the
            detail is cleared with a note; otherwise the current selection is kept, or the first
            set is selected.
        """

        prior = self.__selected_id
        discovered = Discover_Capture_Sets(self.__root) if self.__root else []
        # Only THIS run's sets: match the run id written into each set's metadata. Earlier runs'
        # sets stay on disk (retention manages them) but are not listed.
        self.__sets = [cap for cap in discovered if cap.Run_Id == self.__run_id]
        removed = prior is not None and prior not in {cap.Set_Id for cap in self.__sets}
        self.__Rebuild_List(removed_prior=removed)

    def Selected_Set_Id(self) -> tp.Optional[str]:
        """
        Description:
            The set id currently shown in the detail panel, or None — so the window can tell
            whether an eviction removed the set on display and log it.

        Returns:
            (1) parameter [string or None]: The selected set id.
        """

        return self.__selected_id

    def Is_Info_Open(self) -> bool:
        """
        Description:
            Whether the Info side panel is open.

        Returns:
            (1) parameter [bool]: True while the Info panel is open.
        """

        return self.__info_open

    # --------------------------------------------------------------------- the grid

    def __Rebuild_List(self, removed_prior: bool = False) -> None:
        """
        Description:
            Rebuild the thumbnail grid for the active filter (session groups, newest-first). When
            the filter matches nothing, the filter-aware empty message is shown. Selection: if the
            viewed set was just evicted, clear the detail with the removed note; otherwise keep the
            current selection when it is still shown, else select the first set.

        Args:
            (1) removed_prior [bool]: True when the previously selected set was evicted.
        """

        # The OK/NOK filter is shown only when the configuration in force classifies — its images
        # carry verdict colours, so the filter must exist to explain and narrow them. When it only
        # detects there is no verdict state to filter, so the filter is removed (hidden) and forced
        # to 'All', not merely disabled: nothing on screen then implies a feature it does not have.
        # History lists only this run's sets, and a run has one configuration.
        self.__filter.setVisible(self.__classification_enabled)
        if not self.__classification_enabled:
            self.__filter.Set_Selection('all')

        while self.__list_box.count():
            item = self.__list_box.takeAt(0)
            widget = item.widget()
            if widget:
                # Unparent now, not just deleteLater — a deferred delete leaves the old cards
                # painted behind the new grid on a rapid rebuild.
                widget.setParent(None)
                widget.deleteLater()
        self.__cards = []

        matching = [cap for cap in self.__sets if self.__Filter_Matches(cap)]
        if not matching:
            self.__list_box.addWidget(self.__Empty_Message())
            self.__Select(None)
            return

        for session_id, caps in self.__Group_By_Session(matching):
            self.__list_box.addWidget(self.__Session_Header(session_id, len(caps)))
            self.__list_box.addWidget(self.__Session_Grid(caps))

        if removed_prior:
            self.__Show_Removed()
        else:
            target = next((cap for cap in matching if cap.Set_Id == self.__selected_id),
                          matching[0])
            self.__Select(target)
        QTimer.singleShot(0, self.__Load_Visible)

    def __Empty_Message(self) -> QLabel:
        """
        Description:
            The filter-aware empty-grid message (the NOK case names why it is empty today).

        Returns:
            (1) parameter [QLabel(object)]: The message label.
        """

        message = QLabel(CONST_EMPTY_MESSAGES.get(self.__filter.Selection() or 'all', ''))
        message.setFont(Font(9.5))
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        message.setStyleSheet('color: %s; padding: 24px 8px;' % Style.CONST_INK_MUTE)
        return message

    def __Group_By_Session(self, caps: tp.List) -> tp.List[tp.Tuple[str, tp.List]]:
        """
        Description:
            Group sets by session, preserving the newest-first order (the session of the newest
            set comes first). The list is labelled by session — the id matches the log lines.

        Args:
            (1) caps [Vector<Capture_Set_Str>]: The filtered sets, newest first.

        Returns:
            (1) parameter [Vector<Tuple[string, Vector<Capture_Set_Str>]>]: The groups, in order.
        """

        groups = []
        index = {}
        for cap in caps:
            if cap.Session_Id not in index:
                index[cap.Session_Id] = len(groups)
                groups.append((cap.Session_Id, []))
            groups[index[cap.Session_Id]][1].append(cap)
        return groups

    def __Session_Header(self, session_id: str, count: int) -> QWidget:
        """
        Description:
            A session group header: the session id (matching the log) and the set count.

        Args:
            (1) session_id [string]: The session id.
            (2) count [int]: The number of sets in the group.

        Returns:
            (1) parameter [QWidget(object)]: The header widget.
        """

        header = QWidget()
        row = QHBoxLayout(header)
        row.setContentsMargins(2, 4, 2, 0)
        row.setSpacing(8)
        label = QLabel('Connection %s' % session_id)
        label.setFont(Font(8.5, tracking=1))
        label.setStyleSheet('color: %s;' % Style.CONST_INK_SOFT)
        row.addWidget(label)
        row.addWidget(Hairline(vertical=False), 1)
        count_label = QLabel('%d' % count)
        count_label.setFont(Font(8.5, mono=True))
        count_label.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        row.addWidget(count_label)
        return header

    def __Session_Grid(self, caps: tp.List) -> QWidget:
        """
        Description:
            A grid of thumbnail cards for one session, CONST_THUMB_COLUMNS wide. Each card is
            registered for lazy thumbnail loading and wired to select its set on click.

        Args:
            (1) caps [Vector<Capture_Set_Str>]: The session's sets, newest first.

        Returns:
            (1) parameter [QWidget(object)]: The grid widget.
        """

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)
        for position, cap in enumerate(caps):
            card = Thumb_Card_Cls(cap)
            card.Clicked.connect(self.__Select)
            grid.addWidget(card, position // CONST_THUMB_COLUMNS,
                           position % CONST_THUMB_COLUMNS)
            self.__cards.append(card)
        for column in range(CONST_THUMB_COLUMNS):
            grid.setColumnStretch(column, 1)
        return grid_widget

    def __Filter_Matches(self, cap: tp.Any) -> bool:
        """
        Description:
            Whether a set passes the active filter. 'all' matches everything. 'ok' and 'nok' mean
            a JUDGEMENT — 'classified and passed' / 'classified and failed' — so they match only a
            set written WITH classification: a detect-only set was never judged and is neither OK
            nor NOK, so it appears only under All. Filtering it under OK would assert a judgement
            nobody made. (A partial set was never classified either, so it too is All-only.)

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [bool]: True when the set is shown.
        """

        key = self.__filter.Selection() or 'all'
        if key == 'all':
            return True
        if not cap.Classification:
            return False                                 # never judged -> only under All
        return cap.Is_Nok() if key == 'nok' else not cap.Is_Nok()

    def __Load_Visible(self) -> None:
        """
        Description:
            Load the thumbnails of the cards currently in the viewport, once each — lazy loading
            as the operator scrolls.

            Note:
                The pending layout requests are applied first. Right after a rebuild (and on the
                first show) the new cards have not been laid out yet: every one still sits at
                (0, 0), so every one would count as visible and the whole grid would load. The
                zero-delay timer that calls this after a rebuild fires before Qt gets to those
                requests, so waiting for it is not enough.
        """

        QApplication.sendPostedEvents(None, QEvent.LayoutRequest)
        viewport = self.__list_scroll.viewport()
        view_rect = viewport.rect()
        for card in self.__cards:
            if card.Loaded():
                continue
            top_left = card.mapTo(viewport, QPoint(0, 0))
            if view_rect.intersects(QRect(top_left, card.size())):
                card.Load()

    # ---------------------------------------------------------------- the detail

    def __Select(self, cap: tp.Optional[tp.Any]) -> None:
        """
        Description:
            Render the detail panel for a set (or clear it when None): identity, the two image
            panes (or a partial set's raw frame full-width), the set-level record, and the Info
            panel's Scene-Understanding text. Object selection and the Info panel are reset.

        Args:
            (1) cap [Capture_Set_Str(object) or None]: The set to show, or None.
        """

        self.__detail_cap = cap
        self.__selected_id = cap.Set_Id if cap is not None else None
        self.__image_a.Set_Highlight(None)
        self.__object_list.Set_Selected(None)
        self.__Mark_Selected()

        if cap is None:
            self.__Clear_Detail('Select a capture set.')
            return

        self.__identity_id.setText(cap.Set_Id)
        self.__identity_time.setText(self.__Timestamp_Text(cap))
        self.__meta_session.setText(cap.Session_Id or Style.CONST_NO_VALUE)

        if cap.Partial:
            self.__Show_Partial(cap)
        else:
            self.__Show_Full(cap)

    def __Show_Full(self, cap: tp.Any) -> None:
        """
        Description:
            A successful set: the Annotated and Mask panes side by side, the set-level record, and
            the Info panel's text. The Info control is enabled.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.
        """

        self.__banner.hide()
        self.__info_button.setEnabled(True)

        self.__pane_b.show()
        self.__caption_a.setText('Annotated')
        self.__caption_b.setText('Mask')
        self.__image_a.Set_Image(self.__Pixmap(cap.Annotated_Path),
                                 'No annotated image for this set.')
        self.__image_b.Set_Image(self.__Pixmap(cap.Mask_Path), 'No mask for this set.')

        detections = self.__Detections(cap)
        self.__info_lead.setText(Screen_Header(detections, cap.Background))
        self.__object_list.Set_Objects(detections)
        self.__Update_Score_Note(cap)

        self.__meta_objects.setText('%d' % len(cap.Objects))
        self.__meta_task.setText(cap.Task or Style.CONST_NO_VALUE)
        self.__meta_configuration.setText(cap.Configuration or Style.CONST_NO_VALUE)
        self.__meta_latency.setText('%d ms' % cap.Inference_Ms)
        # The frame-mean number carries its severity colour and weight, like the Live panel.
        if cap.Frame_Mean_Confidence is not None:
            percent = int(cap.Frame_Mean_Confidence)
            self.__meta_confidence.setText(Style.Confidence_Number_Html('%d%%' % percent, percent,
                                                                        self.__thresholds))
        else:
            self.__meta_confidence.setText(Style.CONST_NO_VALUE)

    def __Show_Partial(self, cap: tp.Any) -> None:
        """
        Description:
            A failed set: there is no annotated image and no mask, so the raw frame is shown across
            the full width (the mask pane is hidden) under the failure banner. There is no
            Scene-Understanding text, so the Info control is closed and disabled.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.
        """

        self.__Close_Info()
        self.__info_button.setEnabled(False)

        self.__banner.setText('Analysis failed for set %s — only the raw frame was captured. '
                              '%s (Find set %s in the session log.)'
                              % (cap.Set_Id, cap.Note, cap.Set_Id))
        self.__banner.show()

        self.__pane_b.hide()                             # one pane -> the raw frame fills the width
        self.__caption_a.setText('Raw')
        self.__image_a.Set_Image(self.__Pixmap(cap.Raw_Path), 'No raw frame for this set.')

        self.__object_list.Set_Objects([])
        self.__info_lead.setText('')
        self.__score_note.hide()
        self.__meta_objects.setText(Style.CONST_NO_VALUE)
        self.__meta_task.setText(Style.CONST_NO_VALUE)
        self.__meta_configuration.setText(Style.CONST_NO_VALUE)
        self.__meta_latency.setText(Style.CONST_NO_VALUE)
        self.__meta_confidence.setText(Style.CONST_NO_VALUE)

    def __Clear_Detail(self, image_message: str) -> None:
        """
        Description:
            Empty the detail panel — used for no selection.

        Args:
            (1) image_message [string]: The message shown in the image area.
        """

        self.__Close_Info()
        self.__info_button.setEnabled(False)
        self.__identity_id.setText('')
        self.__identity_time.setText('')
        self.__banner.hide()
        self.__pane_b.hide()
        self.__caption_a.setText('')
        self.__image_a.Set_Image(None, image_message)
        self.__object_list.Set_Objects([])
        self.__info_lead.setText('')
        self.__score_note.hide()
        for value in (self.__meta_session, self.__meta_objects, self.__meta_task,
                      self.__meta_configuration, self.__meta_latency, self.__meta_confidence):
            value.setText(Style.CONST_NO_VALUE)

    def __Show_Removed(self) -> None:
        """
        Description:
            Clear the detail with the retention note when the viewed set was evicted, and drop the
            selection (no card is highlighted).
        """

        self.__selected_id = None
        self.__detail_cap = None
        self.__Mark_Selected()
        self.__Clear_Detail('This set is no longer available.')
        self.__banner.setText(CONST_REMOVED_NOTE)
        self.__banner.show()

    def __Pixmap(self, path: tp.Optional[str]) -> tp.Optional[QPixmap]:
        """
        Description:
            Load a set image by path (each selection reads the files afresh, so an evicted or
            rewritten set is never shown from memory), or None when the path is absent/unreadable.

        Args:
            (1) path [string or None]: The image path.

        Returns:
            (1) parameter [QPixmap(object) or None]: The pixmap, or None.
        """

        if not path:
            return None
        pixmap = QPixmap(path)
        return pixmap if not pixmap.isNull() else None

    def __Timestamp_Text(self, cap: tp.Any) -> str:
        """
        Description:
            The set's capture timestamp for the identity line (a middot for the 'T'), or empty.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [string]: The timestamp text.
        """

        return cap.Timestamp.replace('T', '  ·  ') if cap.Timestamp else ''

    def __Detections(self, cap: tp.Any) -> tp.List[Detection_Str]:
        """
        Description:
            Rebuild Detection_Str objects from the set's metadata so the object list and the lead
            render through the SHARED formatter, identical to Scene Understanding.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [Vector<Detection_Str(object)>]: The reconstructed objects.
        """

        detections = []
        for obj in cap.Objects:
            score = obj.Confidence / 100.0 if obj.Confidence is not None else None
            detections.append(Detection_Str(Label='', Bbox=tuple(obj.Bbox), Segmenter_Score=score,
                                            Sentence=obj.Description, Verdict=obj.Verdict,
                                            Cue=obj.Cue, Measurement=obj.Measurement))
        return detections

    def __Update_Score_Note(self, cap: tp.Any) -> None:
        """
        Description:
            Explain any object showing 'Confidence —' with a single foot note.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.
        """

        unscored = sum(1 for obj in cap.Objects if obj.Confidence is None)
        if unscored:
            self.__score_note.setText('%d object%s found by background subtraction carr%s no '
                                      'FastSAM confidence score (shown as “Confidence —”).'
                                      % (unscored, '' if unscored == 1 else 's',
                                         'ies' if unscored == 1 else 'y'))
            self.__score_note.show()
        else:
            self.__score_note.hide()

    def __On_Object_Selected(self, index: int) -> None:
        """
        Description:
            Highlight the clicked object's box in the Annotated pane and mark its row — both stay
            visible, since the Info panel narrows the images rather than covering them.

        Args:
            (1) index [int]: The object index.
        """

        if self.__detail_cap is None or index >= len(self.__detail_cap.Objects):
            return
        self.__object_list.Set_Selected(index)
        self.__image_a.Set_Highlight(tuple(self.__detail_cap.Objects[index].Bbox))

    # ------------------------------------------------------------------ the info panel

    def __Toggle_Info(self) -> None:
        """
        Description:
            Open or close the Info side panel.
        """

        if self.__info_open:
            self.__Close_Info()
        else:
            self.__Open_Info()

    def __Open_Info(self) -> None:
        """
        Description:
            Slide the Info panel in from the right (narrowing the images), unless the set is
            partial or nothing is selected.
        """

        if self.__detail_cap is None or self.__detail_cap.Partial:
            return
        self.__info_open = True
        self.__info_button.setChecked(True)
        self.__info_panel.setVisible(True)
        self.__Animate_Info(CONST_INFO_PANEL_WIDTH)

    def __Close_Info(self) -> None:
        """
        Description:
            Slide the Info panel closed, giving the width back to the images.
        """

        if not self.__info_open and self.__info_panel.maximumWidth() == 0:
            return
        self.__info_open = False
        self.__info_button.setChecked(False)
        self.__Animate_Info(0)

    def __Animate_Info(self, target: int) -> None:
        """
        Description:
            Animate the Info clip width to a target (the slide). On collapse the panel is hidden
            when the animation finishes, so it never steals a click at width zero.

        Args:
            (1) target [int]: The target maximum width in px.
        """

        anim = QPropertyAnimation(self.__info_panel, b'maximumWidth', self)
        anim.setDuration(CONST_INFO_SLIDE_MS)
        anim.setStartValue(self.__info_panel.maximumWidth())
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        if target == 0:
            anim.finished.connect(lambda: self.__info_panel.setVisible(False))
        anim.start()
        self.__info_anim = anim                          # keep a reference so it is not collected

    # -------------------------------------------------------------------- selection paint

    def __Mark_Selected(self) -> None:
        """
        Description:
            Outline the selected card in the set's verdict colour (mute for a partial set), and
            clear the outline on every other card.
        """

        for card in self.__cards:
            cap = card.Cap()
            selected = cap.Set_Id == self.__selected_id
            card.Set_Selected(selected, self.__Set_Color(cap) if selected else None)

    def __Set_Color(self, cap: tp.Any) -> str:
        """
        Description:
            The selection-outline colour for a set, decided by how the set was WRITTEN (not the
            current config): the muted tone for a partial set; the verdict colour (NOK when any
            object is NOK, else OK) for a set written WITH classification; and the neutral
            detection colour for a set written WITHOUT — so a verdict-coloured set and a
            detect-only set read differently, matching their baked-in image colours.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [string]: The outline colour.
        """

        if cap.Partial:
            return Style.CONST_INK_MUTE
        if cap.Classification:
            return Verdict_Color('NOK' if cap.Is_Nok() else 'OK')[0]
        return Detection_Color()[0]

    # << QT OVERRIDE >> #
    def keyPressEvent(self, event: tp.Any) -> None:
        """
        Description:
            Escape closes the Info panel when it is open.
        """

        if event.key() == Qt.Key_Escape and self.__info_open:
            self.__Close_Info()
            return
        super().keyPressEvent(event)

    # << QT OVERRIDE >> #
    def resizeEvent(self, event: tp.Any) -> None:
        """
        Description:
            Load any thumbnails brought into view by a resize.
        """

        super().resizeEvent(event)
        self.__Load_Visible()

    # << QT OVERRIDE >> #
    def showEvent(self, event: tp.Any) -> None:
        """
        Description:
            Load visible thumbnails when the view is first shown (their geometry is only known
            once the view is on screen).
        """

        super().showEvent(event)
        self.__Load_Visible()
