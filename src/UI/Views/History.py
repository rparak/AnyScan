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
# File Name: ../UI/Views/History.py
## =========================================================================== ##

# System (Default)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QRect, QRectF, QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import (QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QScrollArea, QSizePolicy)
# Custom Lib.: AnyScan UI — design tokens, style helpers and shared widgets
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font, Hairline
#   ../UI/Widgets
from UI.Widgets import Card_Cls, Card_Head_Cls, Segmented_Control_Cls, Object_List_Cls
# Custom Lib.: AnyScan — the Qt-free capture-set reader (the view never re-reads or parses)
#   ../UI/Capture
from UI.Capture import Discover_Capture_Sets, CONST_CAPTURE_RETENTION_SETS
# Custom Lib.: AnyScan domain — the detection structure and the verdict palette
#   ../Parameters/Vision
from Parameters.Vision import Detection_Str
#   ../Parameters/Theme
from Parameters.Theme import Verdict_Color

"""
Description:
    The History view — a browser of the capture sets on disk. It reads them through the Qt-free
    Discover_Capture_Sets (the view never parses a file itself), and lays them out as master and
    detail: a scrollable thumbnail grid on the left, newest-first and grouped by session, and the
    selected set on the right. The detail is built around what someone REVIEWING a past analysis
    wants — the set's identity (id, session, timestamp — the id links to the log), the image with
    a Raw/Annotated/Mask control, and a SELECTABLE object list (click an object to highlight it in
    the image) with the set-level record beneath it — rather than mirroring Live, where the
    operator only glances.

    History is a ROLLING WINDOW, not an archive: retention keeps the newest sets and evicts the
    oldest on every write, so the view states its bound, refreshes when a set is written, and — if
    the set being viewed is evicted — clears the detail with a note rather than pointing at files
    that no longer exist. A filter (All/OK/NOK) narrows the grid; nothing assigns NOK yet, so NOK
    is always empty and says so explicitly. A partial set (a failed analysis, raw frame only) is
    shown, not hidden, marked as a failure. A missing or malformed file degrades to a partial set;
    it never crashes the view.
"""
# The thumbnail grid: columns per session group and the thumbnail's drawn size (px).
#   Unit [int]
CONST_THUMB_COLUMNS = 2
CONST_THUMB_W = 190
CONST_THUMB_H = 120

# The retention note, stating the rolling-window bound so nobody assumes an archive.
#   Unit [string]
CONST_RETENTION_NOTE = ('Rolling window — the newest %d sets are kept; older sets are evicted.'
                        % CONST_CAPTURE_RETENTION_SETS)
# The note shown when the set being viewed is evicted out from under the reader.
#   Unit [string]
CONST_REMOVED_NOTE = ('This capture set fell outside the retention window and was removed. '
                      'Select another set from the list.')

# The filter segments and the image-mode segments, in order as (key, label).
#   Unit [Vector<Tuple<string> 1x2>]
CONST_FILTER_SEGMENTS = (('all', 'All'), ('ok', 'OK'), ('nok', 'NOK'))
CONST_IMAGE_SEGMENTS = (('raw', 'Raw'), ('annotated', 'Annotated'), ('mask', 'Mask'))

# The empty-grid messages, per filter — the NOK one names why it is expected to be empty today.
#   Unit [Dict<string, string>]
CONST_EMPTY_MESSAGES = {
    'all': 'No capture sets yet. Analyse a frame in Live and it will appear here.',
    'ok': 'No OK results in the current history.',
    'nok': 'No NOK results. Classification is not yet enabled, so every object is OK.'}


class History_Image_Cls(QWidget):
    """
    Description:
        The detail image area. It draws the image at its own aspect ratio with only a hairline
        border — no wide dark letterbox bands, which were the most wasted space on screen — and,
        when an object is selected in the list, highlights that object's box mapped through the
        same fit. With no image (a partial set's missing annotated/mask) it shows a centred
        message.
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
            Show a pixmap (fitted to aspect) or, when it is None, a centred message. The object
            highlight is preserved across a mode switch (Set_Highlight owns it).

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
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.setBrush(QColor(255, 255, 255, 45))
            painter.drawRect(box)
        painter.end()


class Thumb_Card_Cls(QFrame):
    """
    Description:
        One capture set in the grid: its thumbnail, its time, and its object count — or, for a
        partial set, a clear failure marker in the log's ERROR colour (it is the set most worth
        opening, so it must not read as a muted 'no preview'). The thumbnail loads lazily, only
        when Load is called as the card scrolls into view. Clicking emits Clicked; the selected
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
        column.setContentsMargins(6, 6, 6, 6)
        column.setSpacing(5)

        self.__thumb = QLabel()
        self.__thumb.setFixedSize(CONST_THUMB_W, CONST_THUMB_H)
        self.__thumb.setAlignment(Qt.AlignCenter)
        self.__thumb.setWordWrap(True)
        self.__thumb.setStyleSheet('background: %s; border-radius: 6px; color: %s;'
                                   % (Style.CONST_VIEWPORT, Style.CONST_VIEWPORT_TEXT))
        self.__thumb.setText('…')
        column.addWidget(self.__thumb)

        time_label = QLabel(self.__Time_Text())
        time_label.setFont(Font(8.5, mono=True))
        time_label.setStyleSheet('color: %s;' % Style.CONST_INK)
        column.addWidget(time_label)

        count_label = QLabel(self.__Count_Text())
        count_label.setFont(Font(8.5, QFont.DemiBold if cap.Partial else QFont.Normal))
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
        # No thumbnail — a failed analysis. Mark it as an error, not a bland placeholder.
        self.__thumb.setStyleSheet('background: %s; border-radius: 6px; color: %s;'
                                   % (Style.CONST_VIEWPORT, Style.CONST_LOG_ERROR))
        self.__thumb.setText('ANALYSIS\nFAILED')
        self.__thumb.setFont(Font(9, QFont.DemiBold, tracking=2))

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
                           ' border-radius: 10px; }' % (Style.CONST_CARD, width, border))

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
        The History view: the thumbnail grid on the left, the selected set on the right. It is
        given the captures root and reads it on Refresh (the window calls Refresh when History is
        shown and whenever a set is written). Everything it renders comes from the Qt-free reader.
    """

    def __init__(self, captures_root: tp.Optional[str] = None,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__root = captures_root
        self.__sets = []
        self.__cards = []
        self.__selected_id = None
        self.__detail_cap = None
        self.__detail_pixmaps = {}

        grid = QGridLayout(self)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__Build_List_Panel(), 0, 0)
        grid.addWidget(self.__Build_Detail_Panel(), 0, 1)
        grid.setColumnStretch(0, 34)
        grid.setColumnStretch(1, 66)
        grid.setRowStretch(0, 1)

    # ------------------------------------------------------------------ construction

    def __Build_List_Panel(self) -> Card_Cls:
        """
        Description:
            The left card: the head with the OK/NOK filter, the retention note, and the
            scrollable, session-grouped thumbnail grid.

        Returns:
            (1) parameter [Card_Cls(object)]: The list card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('reading', 'History')
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
        self.__list_scroll.setStyleSheet(self.__Scroll_Style())
        self.__list_scroll.verticalScrollBar().valueChanged.connect(lambda _v: self.__Load_Visible())
        card.box.addWidget(self.__list_scroll, 1)
        return card

    def __Build_Detail_Panel(self) -> Card_Cls:
        """
        Description:
            The right card: the head with the Raw/Annotated/Mask control, the set identity, the
            failure banner, the image, the SELECTABLE object list with a missing-score note, and
            the set-level record table. The list is guaranteed room for a few objects and scrolls
            beyond; the image takes the rest and keeps its aspect.

        Returns:
            (1) parameter [Card_Cls(object)]: The detail card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('camera', 'Capture set')
        self.__image_toggle = Segmented_Control_Cls(CONST_IMAGE_SEGMENTS)
        self.__image_toggle.Segment_Selected.connect(self.__On_Image_Mode)
        head.box.addWidget(self.__image_toggle)
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

        self.__image = History_Image_Cls()
        card.box.addWidget(self.__image, 3)

        # The selectable object list — click an object to highlight it in the image — with a
        # foot note explaining any object that carries no score.
        self.__detail_body = QWidget()
        self.__detail_body.setStyleSheet('background: transparent;')
        body_col = QVBoxLayout(self.__detail_body)
        body_col.setContentsMargins(2, 10, 2, 2)
        body_col.setSpacing(10)
        self.__object_list = Object_List_Cls(selectable=True)
        self.__object_list.Object_Selected.connect(self.__On_Object_Selected)
        body_col.addWidget(self.__object_list)
        self.__score_note = QLabel()
        self.__score_note.setFont(Font(9))
        self.__score_note.setWordWrap(True)
        self.__score_note.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        self.__score_note.hide()
        body_col.addWidget(self.__score_note)
        body_col.addStretch(1)

        self.__detail_scroll = QScrollArea()
        self.__detail_scroll.setWidget(self.__detail_body)
        self.__detail_scroll.setWidgetResizable(True)
        self.__detail_scroll.setFrameShape(QFrame.NoFrame)
        self.__detail_scroll.setMinimumHeight(180)
        self.__detail_scroll.setStyleSheet(self.__Scroll_Style())
        card.box.addWidget(self.__detail_scroll, 2)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 8, 0, 0)
        meta.setSpacing(0)
        self.__meta_session = self.__Meta_Row(meta, 'Session', mono=True, first=True)
        self.__meta_objects = self.__Meta_Row(meta, 'Objects')
        self.__meta_task = self.__Meta_Row(meta, 'Task')
        self.__meta_latency = self.__Meta_Row(meta, 'Inference time', mono=True)
        self.__meta_confidence = self.__Meta_Row(meta, 'Confidence (mean)', mono=True)
        card.box.addLayout(meta)
        return card

    def __Meta_Row(self, parent_layout: QVBoxLayout, key: str, mono: bool = False,
                   first: bool = False) -> QLabel:
        """
        Description:
            One key/value record row, in the same style as the Live reading card's table but
            compact (History carries more rows).

        Args:
            (1) parent_layout [QVBoxLayout(object)]: The layout to add the row to.
            (2) key [string]: The row label.
            (3) mono [bool]: Render the value monospace.
            (4) first [bool]: Omit the top divider on the first row.

        Returns:
            (1) parameter [QLabel(object)]: The value label to update later.
        """

        row = QWidget()
        if not first:
            row.setStyleSheet('border-top: 1px solid %s;' % Style.CONST_LINE)
        line = QHBoxLayout(row)
        line.setContentsMargins(2, 6, 2, 6)
        label = QLabel(key)
        label.setFont(Font(9.5))
        label.setStyleSheet('color: %s; border: none;' % Style.CONST_INK_SOFT)
        line.addWidget(label)
        line.addStretch(1)
        value = QLabel(Style.CONST_NO_VALUE)
        value.setFont(Font(9 if mono else 9.5, mono=mono))
        value.setStyleSheet('color: %s; border: none;' % Style.CONST_INK)
        line.addWidget(value)
        parent_layout.addWidget(row)
        return value

    def __Scroll_Style(self) -> str:
        """
        Description:
            The console's scroll-area stylesheet, shared by both panels so History matches Live.

        Returns:
            (1) parameter [string]: The Qt stylesheet.
        """

        return ("""
            QScrollArea { border: 1px solid %s; border-radius: 10px; background: %s; }
            QScrollBar:vertical { background: transparent; width: 9px; margin: 6px 3px; }
            QScrollBar::handle:vertical { background: #c7c3d9; border-radius: 4px;
                                          min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent; }
        """ % (Style.CONST_LINE, Style.CONST_CARD))

    # -------------------------------------------------------------------- public API

    def Refresh(self) -> None:
        """
        Description:
            Rediscover the sets on disk and rebuild the grid. Called when History is shown and
            whenever a set is written or evicted. If the set that was being viewed is gone
            (evicted), the detail is cleared with a note rather than pointing at deleted files;
            otherwise the current selection is kept, or the first set is selected.
        """

        prior = self.__selected_id
        self.__sets = Discover_Capture_Sets(self.__root) if self.__root else []
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

        while self.__list_box.count():
            item = self.__list_box.takeAt(0)
            widget = item.widget()
            if widget:
                # Unparent now, not just deleteLater — a deferred delete leaves the old cards
                # painted behind the new grid on a rapid rebuild (e.g. a set written while
                # History is open).
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
        message.setFont(Font(10))
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        message.setStyleSheet('color: %s; padding: 24px 10px;' % Style.CONST_INK_MUTE)
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
        label = QLabel('Session %s' % session_id)
        label.setFont(Font(9, tracking=1))
        label.setStyleSheet('color: %s;' % Style.CONST_INK_SOFT)
        row.addWidget(label)
        row.addWidget(Hairline(vertical=False), 1)
        count_label = QLabel('%d' % count)
        count_label.setFont(Font(9, mono=True))
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
            Whether a set passes the active filter: 'all' matches everything; 'ok' matches a set
            with no NOK object (a partial set counts as OK — it failed, it did not fail an
            inspection); 'nok' matches a set with any NOK object.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [bool]: True when the set is shown.
        """

        key = self.__filter.Selection() or 'all'
        if key == 'all':
            return True
        if key == 'nok':
            return cap.Is_Nok()
        return not cap.Is_Nok()

    def __Load_Visible(self) -> None:
        """
        Description:
            Load the thumbnails of the cards currently in the viewport, once each — lazy loading
            as the operator scrolls, so a full grid never decodes every image at once.
        """

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
            Render the detail panel for a set (or clear it when None). Built from the reader's
            structure: identity, image, the selectable object list from the shared formatter, the
            missing-score note, and the set-level record. A partial set shows its failure banner
            and raw frame; a full set shows its objects.

        Args:
            (1) cap [Capture_Set_Str(object) or None]: The set to show, or None.
        """

        self.__detail_cap = cap
        self.__detail_pixmaps = {}
        self.__selected_id = cap.Set_Id if cap is not None else None
        self.__image.Set_Highlight(None)
        self.__object_list.Set_Selected(None)
        self.__Mark_Selected()

        if cap is None:
            self.__Clear_Detail('Select a capture set.')
            return

        self.__identity_id.setText(cap.Set_Id)
        self.__identity_time.setText(self.__Timestamp_Text(cap))
        self.__meta_session.setText(cap.Session_Id or Style.CONST_NO_VALUE)

        if cap.Partial:
            self.__banner.setText('Analysis failed for set %s — only the raw frame was captured. '
                                  '%s (Find set %s in the session log.)'
                                  % (cap.Set_Id, cap.Note, cap.Set_Id))
            self.__banner.show()
            self.__object_list.Set_Objects([])
            self.__score_note.hide()
            self.__meta_objects.setText(Style.CONST_NO_VALUE)
            self.__meta_task.setText(Style.CONST_NO_VALUE)
            self.__meta_latency.setText(Style.CONST_NO_VALUE)
            self.__meta_confidence.setText(Style.CONST_NO_VALUE)
        else:
            self.__banner.hide()
            self.__object_list.Set_Objects(self.__Detections(cap))
            self.__Update_Score_Note(cap)
            self.__meta_objects.setText('%d' % len(cap.Objects))
            self.__meta_task.setText(cap.Task or Style.CONST_NO_VALUE)
            self.__meta_latency.setText('%d ms' % cap.Inference_Ms)
            self.__meta_confidence.setText('%d%%' % cap.Frame_Mean_Confidence
                                           if cap.Frame_Mean_Confidence is not None
                                           else Style.CONST_NO_VALUE)

        default = 'annotated' if cap.Annotated_Path else 'raw'
        self.__image_toggle.Set_Selection(default)
        self.__Show_Image(default)

    def __Clear_Detail(self, image_message: str) -> None:
        """
        Description:
            Empty the detail panel — used for no selection and for a set removed by eviction.

        Args:
            (1) image_message [string]: The message shown in the image area.
        """

        self.__identity_id.setText('')
        self.__identity_time.setText('')
        self.__banner.hide()
        self.__object_list.Set_Objects([])
        self.__score_note.hide()
        self.__image.Set_Image(None, image_message)
        for value in (self.__meta_session, self.__meta_objects, self.__meta_task,
                      self.__meta_latency, self.__meta_confidence):
            value.setText(Style.CONST_NO_VALUE)

    def __Show_Removed(self) -> None:
        """
        Description:
            Clear the detail with the retention note when the viewed set was evicted, and drop
            the selection (no card is highlighted).
        """

        self.__selected_id = None
        self.__detail_cap = None
        self.__Mark_Selected()
        self.__banner.setText(CONST_REMOVED_NOTE)
        self.__banner.show()
        self.__identity_id.setText('')
        self.__identity_time.setText('')
        self.__object_list.Set_Objects([])
        self.__score_note.hide()
        self.__image.Set_Image(None, 'This set is no longer available.')
        for value in (self.__meta_session, self.__meta_objects, self.__meta_task,
                      self.__meta_latency, self.__meta_confidence):
            value.setText(Style.CONST_NO_VALUE)

    def __Timestamp_Text(self, cap: tp.Any) -> str:
        """
        Description:
            The set's capture timestamp, formatted for the identity line (a space for the 'T'),
            or an empty string when absent.

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [string]: The timestamp text.
        """

        return cap.Timestamp.replace('T', '  ·  ') if cap.Timestamp else ''

    def __Detections(self, cap: tp.Any) -> tp.List[Detection_Str]:
        """
        Description:
            Rebuild Detection_Str objects from the set's metadata so the object list renders
            through the SHARED formatter, identical to Scene Understanding — the confidence
            percentage becomes a segmenter score (Object_Confidence rounds it straight back), and
            the description is the object's own sentence.

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
                                            Cue=obj.Cue))
        return detections

    def __Update_Score_Note(self, cap: tp.Any) -> None:
        """
        Description:
            Explain any object showing 'Confidence —' with a single foot note (not per row): it
            was found by background subtraction and carries no FastSAM score.

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
            Highlight the clicked object in the image and mark its row.

        Args:
            (1) index [int]: The object index.
        """

        if self.__detail_cap is None or index >= len(self.__detail_cap.Objects):
            return
        self.__object_list.Set_Selected(index)
        self.__image.Set_Highlight(tuple(self.__detail_cap.Objects[index].Bbox))

    def __On_Image_Mode(self, key: str) -> None:
        """
        Description:
            Switch the detail image between raw, annotated and mask.

        Args:
            (1) key [string]: 'raw', 'annotated' or 'mask'.
        """

        self.__Show_Image(key)

    def __Show_Image(self, mode: str) -> None:
        """
        Description:
            Show the selected image mode for the current set, loading its pixmap once and caching
            it. When that mode's file does not exist, a message says so rather than a broken image.

        Args:
            (1) mode [string]: 'raw', 'annotated' or 'mask'.
        """

        if self.__detail_cap is None:
            return
        path = {'raw': self.__detail_cap.Raw_Path, 'annotated': self.__detail_cap.Annotated_Path,
                'mask': self.__detail_cap.Mask_Path}.get(mode)
        if not path:
            self.__image.Set_Image(None, 'No %s image for this set.' % mode)
            return
        if mode not in self.__detail_pixmaps:
            self.__detail_pixmaps[mode] = QPixmap(path)
        pixmap = self.__detail_pixmaps[mode]
        if pixmap.isNull():
            self.__image.Set_Image(None, 'The %s image could not be read.' % mode)
        else:
            self.__image.Set_Image(pixmap)

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
            The set's verdict colour for its selection outline: the NOK colour when any object is
            NOK, the OK colour otherwise, and the muted tone for a partial set (which failed, so
            has no verdict).

        Args:
            (1) cap [Capture_Set_Str(object)]: The set.

        Returns:
            (1) parameter [string]: The outline colour.
        """

        if cap.Partial:
            return Style.CONST_INK_MUTE
        return Verdict_Color('NOK' if cap.Is_Nok() else 'OK')[0]

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
