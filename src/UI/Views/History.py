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
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPixmap
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
    Discover_Capture_Sets (the view never parses a file itself), and lays them out in the
    console's existing visual language: a scrollable thumbnail grid on the left, newest-first
    and grouped by session, and the selected set on the right laid out like Live — a dark image
    area with a Raw / Annotated / Mask segmented control (the same control the Camera View uses),
    the object list rendered from the shared formatter, and the set-level figures in the same
    small table.

    History is a ROLLING WINDOW, not an archive: retention keeps the newest sets and evicts the
    oldest, so the view states its bound rather than letting an operator assume everything is
    kept. A filter (All / OK / NOK) narrows the grid; nothing assigns NOK yet, so the NOK filter
    is always empty today and says so explicitly rather than showing a blank that reads as
    broken. A partial set (a failed analysis, raw frame only) is shown, not hidden — it is the
    one an operator most wants to see — with its failure note and set id. A missing or malformed
    file degrades to a partial set; it never crashes the view.
"""
# The thumbnail grid: columns per session group and the thumbnail's drawn size (px). The
# thumbnail is written at ~320px long edge, so it scales down cleanly into this cell.
#   Unit [int]
CONST_THUMB_COLUMNS = 2
CONST_THUMB_W = 190
CONST_THUMB_H = 120

# The retention note, stating the rolling-window bound so nobody assumes an archive.
#   Unit [string]
CONST_RETENTION_NOTE = ('Rolling window — the newest %d sets are kept; older sets are evicted.'
                        % CONST_CAPTURE_RETENTION_SETS)

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
        The detail image area: one letterboxed image on the console's dark viewport surface, or
        a centred message when the selected mode has no image (a partial set's missing annotated
        or mask). Deliberately simpler than the live Viewport — no busy or empty-state logic —
        because History only ever shows a still image that already exists.
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__pixmap = None
        self.__message = ''

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(240)

    def Set_Image(self, pixmap: tp.Optional[QPixmap], message: str = '') -> None:
        """
        Description:
            Show a pixmap (letterboxed) or, when it is None, a centred message.

        Args:
            (1) pixmap [QPixmap(object) or None]: The image, or None to show the message.
            (2) message [string]: The message shown when there is no image.
        """

        self.__pixmap = pixmap
        self.__message = message
        self.update()

    # << QT OVERRIDE >> #
    def paintEvent(self, event: tp.Any) -> None:
        """
        Description:
            Paint the dark rounded surface and the letterboxed image or the message.
        """

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), QColor(Style.CONST_VIEWPORT))

        if self.__pixmap is not None and not self.__pixmap.isNull():
            scaled = self.__pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.setPen(QColor(Style.CONST_VIEWPORT_TEXT))
            painter.setFont(Font(9.5, mono=True))
            painter.drawText(self.rect(), Qt.AlignCenter, self.__message)
        painter.end()


class Thumb_Card_Cls(QFrame):
    """
    Description:
        One capture set in the grid: its thumbnail, its time, and its object count (or a failed
        marker for a partial set). It loads its thumbnail lazily — only when Load is called, as
        the card scrolls into view — so a full grid never decodes fifty images at once. Clicking
        it emits Clicked with the set. The selected card is outlined in the set's verdict colour.
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
        self.__thumb.setStyleSheet('background: %s; border-radius: 6px; color: %s;'
                                   % (Style.CONST_VIEWPORT, Style.CONST_VIEWPORT_TEXT))
        self.__thumb.setText('…')
        column.addWidget(self.__thumb)

        time_text = self.__Time_Text()
        time_label = QLabel(time_text)
        time_label.setFont(Font(8.5, mono=True))
        time_label.setStyleSheet('color: %s;' % Style.CONST_INK)
        column.addWidget(time_label)

        count_label = QLabel(self.__Count_Text())
        count_label.setFont(Font(8.5))
        count_label.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
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
            shows a small 'no preview' note instead of a broken image.
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
        self.__thumb.setText('no preview')

    def Set_Selected(self, selected: bool, color: tp.Optional[str] = None) -> None:
        """
        Description:
            Outline the card when selected, in the set's verdict colour (passed by the view);
            a plain hairline border otherwise.

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
            The set's time, from its timestamp when present, else its set id (which begins with
            a timestamp). Just the time part is shown; the session header carries the date.

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
            return 'analysis failed'
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
        given the captures root and reads it on Refresh (the window calls Refresh whenever
        History is shown, so the rolling window is current). Everything it renders comes from the
        Qt-free reader; the view holds no file-format knowledge of its own.
    """

    def __init__(self, captures_root: tp.Optional[str] = None,
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__root = captures_root
        self.__sets = []
        self.__cards = []
        self.__selected_id = None
        self.__detail_pixmaps = {}
        self.__detail_cap = None

        grid = QGridLayout(self)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__Build_List_Panel(), 0, 0)
        grid.addWidget(self.__Build_Detail_Panel(), 0, 1)
        grid.setColumnStretch(0, 36)
        grid.setColumnStretch(1, 64)
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
            The right card: the head with the Raw / Annotated / Mask control, the image area, a
            partial-set banner, the object list, and the set-level meta table — laid out like the
            Live reading card so the two feel like one application.

        Returns:
            (1) parameter [Card_Cls(object)]: The detail card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('camera', 'Capture set')
        self.__image_toggle = Segmented_Control_Cls(CONST_IMAGE_SEGMENTS)
        self.__image_toggle.Segment_Selected.connect(self.__On_Image_Mode)
        head.box.addWidget(self.__image_toggle)
        card.box.addWidget(head)

        # The failure banner sits ABOVE the image, so a partial set reads 'why it failed' first
        # and it never overlaps the image below.
        self.__banner = QLabel()
        self.__banner.setFont(Font(10))
        self.__banner.setWordWrap(True)
        self.__banner.setStyleSheet('color: %s; padding: 0 2px 10px 2px;' % Style.CONST_LOG_ERROR)
        self.__banner.hide()
        card.box.addWidget(self.__banner)

        self.__image = History_Image_Cls()
        card.box.addWidget(self.__image, 3)

        body = QWidget()
        body.setStyleSheet('background: transparent;')
        body_col = QVBoxLayout(body)
        body_col.setContentsMargins(2, 12, 2, 2)
        body_col.setSpacing(0)
        self.__object_list = Object_List_Cls()
        body_col.addWidget(self.__object_list)
        body_col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(170)
        scroll.setStyleSheet(self.__Scroll_Style())
        card.box.addWidget(scroll, 2)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 10, 0, 0)
        meta.setSpacing(0)
        self.__meta_task = self.__Meta_Row(meta, 'Task', first=True)
        self.__meta_latency = self.__Meta_Row(meta, 'Inference time', mono=True)
        self.__meta_confidence = self.__Meta_Row(meta, 'Confidence (mean)', mono=True)
        card.box.addLayout(meta)
        return card

    def __Meta_Row(self, parent_layout: QVBoxLayout, key: str, mono: bool = False,
                   first: bool = False) -> QLabel:
        """
        Description:
            One key/value meta row, in the same style as the Live reading card's table.

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
        line.setContentsMargins(2, 9, 2, 9)
        label = QLabel(key)
        label.setFont(Font(10))
        label.setStyleSheet('color: %s; border: none;' % Style.CONST_INK_SOFT)
        line.addWidget(label)
        line.addStretch(1)
        value = QLabel(Style.CONST_NO_VALUE)
        value.setFont(Font(9 if mono else 10, mono=mono))
        value.setStyleSheet('color: %s; border: none;' % Style.CONST_INK)
        line.addWidget(value)
        parent_layout.addWidget(row)
        return value

    def __Scroll_Style(self) -> str:
        """
        Description:
            The console's scroll-area stylesheet (rounded border, thin handle), shared by both
            panels so History matches the Live reading card.

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
            Rediscover the sets on disk and rebuild the grid. Called whenever History is shown,
            so a set written or evicted since last time is reflected. The current selection is
            kept when the set still exists, otherwise the first set is selected.
        """

        self.__sets = Discover_Capture_Sets(self.__root) if self.__root else []
        self.__Rebuild_List()

    # --------------------------------------------------------------------- the grid

    def __Rebuild_List(self) -> None:
        """
        Description:
            Rebuild the thumbnail grid for the active filter: session groups (newest-first),
            each a header and a grid of cards. When the filter matches nothing, the filter-aware
            empty message is shown instead — so the always-empty NOK case reads as 'none
            occurred', not a broken panel. The selection is restored or defaulted, and the first
            screen of thumbnails is loaded.
        """

        while self.__list_box.count():
            item = self.__list_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.__cards = []

        matching = [cap for cap in self.__sets if self.__Filter_Matches(cap)]
        if not matching:
            message = QLabel(CONST_EMPTY_MESSAGES.get(self.__filter.Selection() or 'all', ''))
            message.setFont(Font(10))
            message.setWordWrap(True)
            message.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
            message.setStyleSheet('color: %s; padding: 24px 10px;' % Style.CONST_INK_MUTE)
            self.__list_box.addWidget(message)
            self.__Select(None)
            return

        for session_id, caps in self.__Group_By_Session(matching):
            self.__list_box.addWidget(self.__Session_Header(session_id, len(caps)))
            self.__list_box.addWidget(self.__Session_Grid(caps))

        target = next((cap for cap in matching if cap.Set_Id == self.__selected_id), matching[0])
        self.__Select(target)
        QTimer.singleShot(0, self.__Load_Visible)

    def __Group_By_Session(self, caps: tp.List) -> tp.List[tp.Tuple[str, tp.List]]:
        """
        Description:
            Group sets by session, preserving the newest-first order (the session of the newest
            set comes first). Sets span sessions, so the list is labelled by session — the id
            matches the log lines.

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
            Render the detail panel for a set (or clear it when None). The right panel is built
            from the reader's structure: the images, the object list from the shared formatter,
            and the set-level meta table; a partial set shows its failure note and set id and no
            object list.

        Args:
            (1) cap [Capture_Set_Str(object) or None]: The set to show, or None.
        """

        self.__detail_cap = cap
        self.__detail_pixmaps = {}
        self.__selected_id = cap.Set_Id if cap is not None else None
        self.__Mark_Selected()

        if cap is None:
            self.__image.Set_Image(None, 'Select a capture set.')
            self.__object_list.Set_Objects([])
            self.__banner.hide()
            self.__meta_task.setText(Style.CONST_NO_VALUE)
            self.__meta_latency.setText(Style.CONST_NO_VALUE)
            self.__meta_confidence.setText(Style.CONST_NO_VALUE)
            return

        if cap.Partial:
            self.__banner.setText('Analysis failed for set %s — only the raw frame was '
                                  'captured. %s (find set %s in the session log.)'
                                  % (cap.Set_Id, cap.Note, cap.Set_Id))
            self.__banner.show()
            self.__object_list.Set_Objects([])
            self.__meta_task.setText(Style.CONST_NO_VALUE)
            self.__meta_latency.setText(Style.CONST_NO_VALUE)
            self.__meta_confidence.setText(Style.CONST_NO_VALUE)
        else:
            self.__banner.hide()
            self.__object_list.Set_Objects(self.__Detections(cap))
            self.__meta_task.setText(cap.Task or Style.CONST_NO_VALUE)
            self.__meta_latency.setText('%d ms' % cap.Inference_Ms)
            self.__meta_confidence.setText('%d%%' % cap.Frame_Mean_Confidence
                                           if cap.Frame_Mean_Confidence is not None
                                           else Style.CONST_NO_VALUE)

        # Default to the annotated image when it exists, else raw; reflect it on the control.
        default = 'annotated' if cap.Annotated_Path else 'raw'
        self.__image_toggle.Set_Selection(default)
        self.__Show_Image(default)

    def __Detections(self, cap: tp.Any) -> tp.List[Detection_Str]:
        """
        Description:
            Rebuild Detection_Str objects from the set's metadata so the object list renders
            through the SHARED formatter, identical to Scene Understanding — the confidence
            percentage becomes a segmenter score (Object_Confidence rounds it straight back),
            and the description is the object's own sentence.

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
            Show the selected image mode for the current set, loading its pixmap once and
            caching it. When that mode's file does not exist (a partial set has only the raw
            frame), a message says so rather than showing a broken image.

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
            The set's verdict colour for its selection outline: the NOK colour when any object
            is NOK, the OK colour otherwise, and the muted tone for a partial set (which has no
            verdict — it failed).

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
