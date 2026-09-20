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
# File Name: ../UI/Core.py
## =========================================================================== ##

# System (Default)
import typing as tp
import os
import statistics
from datetime import datetime
# OpenCV library for computer vision tasks [pip3 install opencv-python]
import cv2
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtGui import QFont, QKeyEvent, QCloseEvent
from PyQt5.QtWidgets import (QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                             QGridLayout, QScrollArea, QFrame, QStackedWidget)
# Custom Lib.: AnyScan UI — style, widgets and workers
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import (Font, Load_Svg, Load_Logo, Rgb_To_Qimage, Bgr_To_Qimage,
                                Hairline)
#   ../UI/Widgets
from UI.Widgets import (Card_Cls, Card_Head_Cls, Icon_Cls, Viewport_Cls, Tool_Button_Cls,
                        View_Toggle_Cls, Segmented_Control_Cls, Object_List_Cls,
                        Status_Strip_Cls, Funding_Row_Cls)
#   ../UI/Views/History
from UI.Views.History import History_View_Cls
#   ../UI/Views/Log
from UI.Views.Log import Log_View_Cls
#   ../UI/Workers
from UI.Workers import Analysis_Worker_Cls, Connect_Worker_Cls
# Custom Lib.: AnyScan domain — backends, renderers and the result structure
#   ../Camera/Core
from Camera.Core import Basler_Camera_Cls, Camera_Error_Cls
#   ../Vision/Core
from Vision.Core import Florence_Vision_Cls
#   ../Vision/Utilities/Annotate
import Vision.Utilities.Annotate as Annotate
from Vision.Utilities.Annotate import Draw_Annotated, Draw_Label_Mask, Seg_Lines
#   ../Reporting/Core
from Reporting.Core import Screen_Header, Screen_Understanding, Yolo_Lines
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str, Detection_Str
# Custom Lib.: AnyScan — the session logger and the per-analysis capture writer
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls
#   ../UI/Capture
from UI.Capture import Capture_Writer_Cls, Build_Set_Metadata


class AnyScan_Window_Cls(QMainWindow):
    """
    Description:
        The console's main window. It reads operator input, drives the camera and
        the vision backend through their Qt-free interfaces, and renders the result;
        it holds no application logic of its own. Long-running work (connect,
        analyze) runs on worker threads, never on the GUI thread.

    Initialization of the Class:
        Args:
            (1) camera [Camera_Backend_Cls(object)]: An injected camera backend, or
                None to use the real Basler_Camera_Cls (the --frame path injects a
                File_Camera_Cls).

        Example:
            Initialization:
                # Initialization of the class.
                Cls = AnyScan_Window_Cls(camera=File_Camera_Cls(path))
                Cls.showMaximized()

            Features:
                # Qt-dispatched overrides: keyPressEvent, closeEvent.
    """

    # The reading panel says what to do next, which depends on how far the operator
    # has got. One fixed sentence is wrong in two of the three states.
    CONST_READING_DISCONNECTED = ('Connect a camera and scan a frame, then press Analyze. '
                                  'The model’s reading of the scene appears here as '
                                  'plain English text.')
    CONST_READING_NO_FRAME = ('Press Scan to capture a frame, then Analyze. The model’s '
                              'reading of the scene appears here as plain English text.')
    # The central-view switch segments, in order, as (key, label) — the stack pages line up
    # with these by index (live=0, history=1, log=2). 'live' is first, so it is selected at
    # startup.
    CONST_VIEW_SEGMENTS = (('live', 'Live'), ('history', 'History'), ('log', 'Log'))
    # The switch keys mapped to their stack index.
    CONST_VIEW_INDEX = {'live': 0, 'history': 1, 'log': 2}

    CONST_READING_HAS_FRAME = ('Frame captured. Press Analyze to read the scene. The result '
                               'appears here as plain English text.')

    def __init__(self, camera: tp.Optional[tp.Any] = None,
                 logger: tp.Optional[Session_Logger_Cls] = None) -> None:
        super().__init__()
        self.setWindowTitle('AnyScan  ·  %s' % Style.CONST_TAGLINE)

        # << PRIVATE >> #
        # One real implementation each. `camera` is injected so the developer
        # --frame path can supply a File_Camera_Cls; production is the Basler.
        self.__camera = camera if camera is not None else Basler_Camera_Cls()
        self.__vision = Florence_Vision_Cls()
        # The session logger is injected by the launcher; None disables logging so the
        # window still builds under test and in the screenshot harness.
        self.__logger = logger
        # The per-analysis capture writer (four artefacts per analysis under
        # logger/captures/, retention-bounded). Only when a logger is present, since the
        # captures live beside its log; None disables capture entirely.
        self.__capture_writer = None
        # The captures root (per-session subdirectories live here) — also what the History
        # view reads from. None disables both capture and history.
        self.__captures_root = None
        log_path = getattr(logger, 'Path', None)
        if log_path is not None:
            self.__captures_root = os.path.join(os.path.dirname(log_path), 'captures')
            self.__capture_writer = Capture_Writer_Cls(self.__captures_root)
        # The camera emits its events (frame drops, config) through this sink; the Qt-free
        # camera never holds the logger.
        self.__camera.Set_Log_Callback(self.__Log_Event)
        # The per-session analysis index (for the capture-set id) and the current
        # analysis's set id, set when an analysis starts and reused when it finishes.
        self.__session_analyses = 0
        self.__current_set_id = None
        # The capture-session id — the logger's session (connect to disconnect) as its
        # start timestamp plus index, so a log line and a capture directory name the same
        # session, and ids stay distinguishable across runs.
        self.__session_id = None
        # The open camera/scan/analysis error ids, so the next matching success can
        # resolve them (e.g. a scan timeout resolved by the next successful scan).
        self.__camera_error_id = None
        self.__scan_error_id = None
        self.__analysis_error_id = None

        self.__frame = None
        self.__analyses = 0
        self.__objects_found = 0
        # The per-analysis latencies of this session, for the rolling MEDIAN inference
        # time in the status strip — a median so a single slow frame does not swing the
        # figure the operator reads. Reset with the counters on Clear.
        self.__latencies = []
        # Every scored object's confidence across the WHOLE session, for the session MEAN
        # in the status strip. Kept distinct from the per-frame mean the panel table shows:
        # the status figure is the mean over every object in every analysis since the
        # session began, the table figure the mean over one frame's objects. Reset on Clear.
        self.__session_scores = []
        # The Camera View's remembered annotated/mask choice (§2b): it persists across
        # analyses in a session, so an operator working in mask view is not thrown back
        # to annotated by the next Analyze.
        self.__view_choice = 'annotated'
        # While an error is on screen, the prompts must not overwrite it.
        self.__showing_error = False
        # Analysis worker plumbing; None when idle.
        self.__thread = None
        self.__worker = None
        self.__worker_running = False
        # Camera-connect worker plumbing; None when idle.
        self.__conn_thread = None
        self.__conn_worker = None
        # Widgets, populated by __Build_Ui.
        # The central view stack (Live / History / Log) and the header switch that drives it.
        # The header, status strip and funding row sit OUTSIDE the stack, so they stay fixed
        # and keep updating whichever view is shown.
        self.__stack = None
        self.__view_switch = None
        self.__history_view = None
        self.__log_view = None
        self.__viewport = None
        self.__view_toggle = None
        self.__status = None
        self.__frame_badge = None
        self.__stage_badge = None
        self.__pill_camera = None
        self.__reading_empty = None
        self.__reading_lead = None
        self.__reading_note = None
        self.__object_list = None
        self.__meta_task = None
        self.__meta_latency = None
        self.__meta_confidence = None
        self.__button_connect = None
        self.__button_disconnect = None
        self.__button_scan = None
        self.__button_analyze = None
        self.__button_clear = None

        self.__Build_Ui()
        self.__Connect_Signals()
        self.__Attach_Log_View()
        self.__Sync_Controls()
        # Nudge a first repaint once the event loop starts, so the viewport paints
        # its empty state immediately.
        QTimer.singleShot(0, lambda: self.__viewport.update() if self.__viewport else None)

    # ------------------------------------------------------------------ layout

    def __Build_Ui(self) -> None:
        """
        Description:
            Build the whole window: topbar, the two cards, the status strip and the
            funding row.
        """

        root = QWidget()
        root.setObjectName('root')
        # An id selector, never a bare `background:` — a bare declaration cascades
        # into every child widget and paints grey blocks behind the card titles.
        root.setStyleSheet('#root { background: %s; }' % Style.CONST_BG)
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 0, 18, 18)
        outer.setSpacing(0)

        outer.addWidget(self.__Build_Topbar())

        # Only the central area changes when the view switch is used: the topbar (above), the
        # status strip and the funding row (below) stay fixed and keep updating regardless of
        # which view is shown. The three views live in a stack; switching is a page change, so
        # each view keeps its state and an analysis still drives the status strip and the Live
        # cards while another view is on top.
        self.__stack = QStackedWidget()
        self.__stack.addWidget(self.__Build_Live_View())    # index 0 — Live
        self.__history_view = History_View_Cls(self.__captures_root)
        self.__stack.addWidget(self.__history_view)          # index 1 — History
        self.__log_view = Log_View_Cls()
        self.__stack.addWidget(self.__log_view)              # index 2 — Log

        grid = QGridLayout()
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__stack, 0, 0)
        grid.setRowStretch(0, 1)       # spare height goes to the central view

        self.__status = Status_Strip_Cls()
        grid.addWidget(self.__status, 1, 0)
        grid.addWidget(Funding_Row_Cls(), 2, 0)

        outer.addLayout(grid, 1)

    def __Build_Live_View(self) -> QWidget:
        """
        Description:
            The Live view — the two cards the console has always shown, Camera View and Scene
            Understanding, side by side. It is one page of the central stack; nothing about the
            cards changes, only that they now live inside a switchable view.

        Returns:
            (1) parameter [QWidget(object)]: The Live view widget.
        """

        view = QWidget()
        grid = QGridLayout(view)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__Build_Camera_Card(), 0, 0)
        grid.addWidget(self.__Build_Reading_Card(), 0, 1)
        grid.setColumnStretch(0, 55)   # the frame is always the widest element
        grid.setColumnStretch(1, 45)
        grid.setRowStretch(0, 1)       # spare height goes to the reading panel
        return view

    def __Build_Topbar(self) -> QWidget:
        """
        Description:
            The top bar: the AnyScan brand lockup, the JIC mark, the camera pill and
            the model pill. The lockup is the `anyscan-logo.svg` — the mark, the
            wordmark and the tagline. The "developed by JIC" attribution is no longer
            set as words in the logo; the JIC mark itself carries it, divided off to
            the right and tinted the muted-violet CONST_INK_MUTE so it reads as quiet
            attribution on the console's own palette.

        Returns:
            (1) parameter [QWidget(object)]: The top-bar widget.
        """

        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 20, 4, 18)
        row.setSpacing(16)

        logo = QLabel()
        logo.setPixmap(Load_Svg('anyscan-logo.svg', 54))
        row.addWidget(logo)

        row.addWidget(Hairline(vertical=True, length=34, color='#c9c5d8'))

        jic = QLabel()
        jic.setPixmap(Load_Logo('brand-jic-mute.png', 26))
        row.addWidget(jic)

        row.addStretch(1)

        # The central-view switch, in the same segmented-control language as the Camera View's
        # annotated/mask toggle, centred in the header. Live is selected at startup (the first
        # segment). It only changes which central view is shown — never the header, status strip
        # or footer.
        self.__view_switch = Segmented_Control_Cls(self.CONST_VIEW_SEGMENTS)
        row.addWidget(self.__view_switch)

        row.addStretch(1)

        self.__pill_camera = self.__Pill('Camera offline', dot=True)
        row.addWidget(self.__pill_camera)

        model_pill = QWidget()
        model_pill.setObjectName('modelPill')
        model_pill.setFixedHeight(31)
        model_pill.setStyleSheet(
            '#modelPill { border: 1px solid %s; border-radius: 15px; }' % Style.CONST_CARD_BORDER)
        pill_row = QHBoxLayout(model_pill)
        pill_row.setContentsMargins(12, 0, 12, 0)
        pill_row.setSpacing(7)
        pill_row.addWidget(Icon_Cls('cube', 15, Style.CONST_INK_MUTE))
        model_label = QLabel(self.__vision.Name)
        model_label.setFont(Font(9, QFont.DemiBold))
        model_label.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        pill_row.addWidget(model_label)
        row.addWidget(model_pill)
        return bar

    def __Pill(self, text: str, dot: bool = False) -> QLabel:
        """
        Description:
            A rounded status pill for the top bar.

        Args:
            (1) text [string]: The pill text.
            (2) dot [bool]: Prefix a status dot.

        Returns:
            (1) parameter [QLabel(object)]: The pill label.
        """

        pill = QLabel(('●  ' if dot else '') + text)
        pill.setFont(Font(9, QFont.DemiBold))
        pill.setFixedHeight(31)
        pill.setStyleSheet(
            'border: 1px solid %s; background: %s; color: %s;'
            'border-radius: 15px; padding: 0 12px;'
            % (Style.CONST_CARD_BORDER, Style.CONST_CARD, Style.CONST_INK_MUTE)
        )
        return pill

    def __Build_Camera_Card(self) -> Card_Cls:
        """
        Description:
            The camera card: head, viewport and the five action buttons.

        Returns:
            (1) parameter [Card_Cls(object)]: The camera card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('camera', 'Camera View', 'No frame')
        self.__frame_badge = head.badge
        # The annotated/mask selector lives in the head, right-aligned: it belongs to the
        # view, not the action row. Hidden until an analysis has produced both renders.
        self.__view_toggle = View_Toggle_Cls()
        self.__view_toggle.setVisible(False)
        head.box.addWidget(self.__view_toggle)
        card.box.addWidget(head)

        self.__viewport = Viewport_Cls()
        card.box.addWidget(self.__viewport, 1)

        bar = QHBoxLayout()
        bar.setSpacing(12)
        bar.setContentsMargins(0, 16, 0, 0)
        self.__button_connect = Tool_Button_Cls('CONNECT')
        self.__button_disconnect = Tool_Button_Cls('DISCONNECT')
        self.__button_scan = Tool_Button_Cls('SCAN')
        self.__button_analyze = Tool_Button_Cls('ANALYZE', primary=True)
        self.__button_clear = Tool_Button_Cls('CLEAR')
        for b in (self.__button_connect, self.__button_disconnect, self.__button_scan,
                  self.__button_analyze, self.__button_clear):
            bar.addWidget(b)
        card.box.addLayout(bar)
        return card

    def __Build_Reading_Card(self) -> Card_Cls:
        """
        Description:
            The Scene Understanding card: head, the scrolling reading body, and the
            meta rows (task, inference time, confidence mean) — every value for the
            current frame. The object count is NOT among them: the lead sentence above
            already states it, so a table row would only repeat it.

        Returns:
            (1) parameter [Card_Cls(object)]: The reading card.
        """

        card = Card_Cls()
        head = Card_Head_Cls('reading', 'Scene Understanding', 'Idle')
        self.__stage_badge = head.badge
        card.box.addWidget(head)

        body = QWidget()
        body.setStyleSheet('background: transparent;')
        col = QVBoxLayout(body)
        col.setContentsMargins(18, 18, 18, 16)
        col.setSpacing(0)

        self.__reading_empty = QLabel(self.CONST_READING_DISCONNECTED)
        self.__reading_empty.setFont(Font(11.5))
        self.__reading_empty.setWordWrap(True)
        self.__reading_empty.setAlignment(Qt.AlignTop)
        self.__reading_empty.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        col.addWidget(self.__reading_empty)

        self.__reading_lead = QLabel()
        self.__reading_lead.setFont(Font(16.5, QFont.DemiBold, tracking=-1.5))
        self.__reading_lead.setWordWrap(True)
        self.__reading_lead.setStyleSheet('color: %s; padding-bottom: 14px;' % Style.CONST_INK)
        self.__reading_lead.hide()
        col.addWidget(self.__reading_lead)

        self.__object_list = Object_List_Cls()
        col.addWidget(self.__object_list)

        self.__reading_note = QLabel()
        self.__reading_note.setFont(Font(11.5))
        self.__reading_note.setWordWrap(True)
        self.__reading_note.setStyleSheet(
            'color: %s; border-top: 1px solid %s; padding-top: 15px;'
            'margin-top: 18px;' % (Style.CONST_INK_MUTE, Style.CONST_LINE)
        )
        self.__reading_note.hide()
        col.addWidget(self.__reading_note)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(320)
        scroll.setStyleSheet("""
            QScrollArea { border: 1px solid %s; border-radius: 10px;
                          background: %s; }
            QScrollBar:vertical { background: transparent; width: 9px; margin: 6px 3px; }
            QScrollBar::handle:vertical { background: #c7c3d9; border-radius: 4px;
                                          min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent; }
        """ % (Style.CONST_LINE, Style.CONST_CARD))
        card.box.addWidget(scroll, 1)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 10, 0, 0)
        meta.setSpacing(0)
        # Every value here is for the CURRENT frame — the whole panel describes one frame,
        # so the labels carry no scope qualifier. 'Inference time' is this analysis's
        # latency and 'Confidence (mean)' the mean across this frame's objects, distinct
        # from the session median/mean in the status strip below.
        self.__meta_task = self.__Meta_Row(meta, 'Task', first=True)
        self.__meta_latency = self.__Meta_Row(meta, 'Inference time', mono=True)
        self.__meta_confidence = self.__Meta_Row(meta, 'Confidence (mean)', mono=True)
        card.box.addLayout(meta)
        return card

    def __Meta_Row(self, parent_layout: QVBoxLayout, key: str, mono: bool = False,
                   first: bool = False) -> QLabel:
        """
        Description:
            One key/value meta row for the reading card.

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
        value.setFont(Font(9 if mono else 10, QFont.Medium, mono=mono))
        value.setStyleSheet('color: %s; border: none;' % Style.CONST_INK)
        line.addWidget(value)
        parent_layout.addWidget(row)
        return value

    def __Connect_Signals(self) -> None:
        """
        Description:
            Wire the action buttons to their slots. All static connections live
            here; no auto-connection is used. The per-operation worker/thread
            wiring is set up in the handlers that start each operation.
        """

        self.__button_connect.clicked.connect(self.__On_Connect_Button_Clicked)
        self.__button_disconnect.clicked.connect(self.__On_Disconnect_Button_Clicked)
        self.__button_scan.clicked.connect(self.__On_Scan_Button_Clicked)
        self.__button_analyze.clicked.connect(self.__On_Analyze_Button_Clicked)
        self.__button_clear.clicked.connect(self.__On_Clear_Button_Clicked)
        self.__view_toggle.View_Changed.connect(self.__On_View_Toggle)
        self.__view_switch.Segment_Selected.connect(self.__On_View_Selected)

    def __Attach_Log_View(self) -> None:
        """
        Description:
            Wire the Log view to the session logger, when one is present: seed the view once
            from the log file (the lines written before this point, e.g. the application-start
            line), then follow live by registering the view's sink. Seeding before attaching
            the sink is race-free here — this runs during construction on the GUI thread, with
            no worker logging yet — so no line is missed or doubled. With no logger, or a
            minimal logger that exposes neither a file path nor the sink hook (a test spy),
            the view simply stays empty.
        """

        if self.__logger is None:
            return
        log_path = getattr(self.__logger, 'Path', None)
        if log_path is not None:
            self.__log_view.Seed_From_File(log_path)
        set_sink = getattr(self.__logger, 'Set_Line_Sink', None)
        if callable(set_sink):
            set_sink(self.__log_view.Sink)

    # ----------------------------------------------------------------- actions

    def __Prompt_Text(self) -> str:
        """
        Description:
            The reading-panel prompt for the current state.

        Returns:
            (1) parameter [string]: The prompt sentence.
        """

        if self.__frame is not None:
            return self.CONST_READING_HAS_FRAME
        return self.CONST_READING_NO_FRAME if self.__camera.Connected else self.CONST_READING_DISCONNECTED

    def __Sync_Prompts(self) -> None:
        """
        Description:
            Point both empty states at the step that is actually available.
        """

        self.__viewport.Set_Empty_Text(
            'Press Scan to capture a frame.' if self.__camera.Connected
            else 'Connect a camera, then press Scan to capture a frame.'
        )
        if not self.__showing_error and not self.__reading_empty.isHidden():
            self.__reading_empty.setText(self.__Prompt_Text())

    def __Sync_Controls(self) -> None:
        """
        Description:
            Enable/disable the controls and repaint the camera pill for the current
            connection and worker state. While a worker runs, every control is
            disabled.
        """

        connected = self.__camera.Connected
        running = self.__worker_running
        self.__button_connect.setEnabled(not connected and not running)
        self.__button_disconnect.setEnabled(connected and not running)
        self.__button_scan.setEnabled(connected and not running)
        self.__button_analyze.setEnabled(self.__frame is not None and not running)
        self.__button_clear.setEnabled(not running)

        # The annotated/mask toggle is meaningful only once an analysis has delivered
        # both renders, and never while a worker runs. Its visibility follows the held
        # renders, so a stale frame (which drops them) hides it in the same breath.
        has_views = self.__viewport.Has_Views()
        self.__view_toggle.setVisible(has_views)
        self.__view_toggle.setEnabled(has_views and not running)

        if connected:
            self.__pill_camera.setText('●  Camera live')
            self.__pill_camera.setStyleSheet(
                'border: 1px solid %s; background: %s; color: %s;'
                'border-radius: 15px; padding: 0 12px;'
                % (Style.CONST_OK_BORDER, Style.CONST_CARD, Style.CONST_OK))
        else:
            self.__pill_camera.setText('●  Camera offline')
            self.__pill_camera.setStyleSheet(
                'border: 1px solid %s; background: %s; color: %s;'
                'border-radius: 15px; padding: 0 12px;'
                % (Style.CONST_CARD_BORDER, Style.CONST_CARD, Style.CONST_INK_MUTE))
        self.__Sync_Prompts()

    def __Fail(self, message: str) -> None:
        """
        Description:
            Show a failure where the operator is already looking — the reading panel.

        Args:
            (1) message [string]: The actionable failure sentence.
        """

        self.__showing_error = True
        self.__stage_badge.Set_State('Error', 'warn')
        self.__reading_empty.setText(message)
        self.__reading_empty.show()
        self.__reading_lead.hide()
        self.__reading_note.hide()
        self.__object_list.Set_Objects([])
        print('[ERROR] %s' % message)

    def __On_Connect_Button_Clicked(self) -> None:
        """
        Description:
            Open the camera on its own thread so the loading indicator turns and the
            window stays responsive through the (seconds-long) Basler handshake.
        """

        if self.__worker_running or self.__camera.Connected:
            return

        if self.__logger is not None:
            self.__logger.Log_Camera_Connection_Attempt()

        self.__worker_running = True
        self.__showing_error = False
        self.__status.camera.Set_Value('Connecting…', Style.CONST_WARN, Style.CONST_WARN)
        self.__viewport.Start_Busy('Connecting to camera…')
        self.__Sync_Controls()

        self.__conn_thread = QThread(self)
        self.__conn_worker = Connect_Worker_Cls(self.__camera)
        self.__conn_worker.moveToThread(self.__conn_thread)

        self.__conn_thread.started.connect(self.__conn_worker.Run)
        self.__conn_worker.Connect_Finished.connect(self.__On_Connect_Finished)
        self.__conn_worker.Connect_Failed.connect(self.__On_Connect_Failed)

        self.__conn_worker.Connect_Finished.connect(self.__conn_thread.quit)
        self.__conn_worker.Connect_Failed.connect(self.__conn_thread.quit)
        self.__conn_thread.finished.connect(self.__conn_worker.deleteLater)
        self.__conn_thread.finished.connect(self.__conn_thread.deleteLater)

        self.__conn_thread.start()

    def __On_Connect_Finished(self) -> None:
        """
        Description:
            The camera opened. Read the sensor size back on the GUI thread and update
            the status strip.
        """

        self.__worker_running = False
        self.__conn_thread = None
        self.__conn_worker = None
        self.__viewport.Stop_Busy()
        # A new camera session: the per-session analysis index (capture-set <n>) restarts.
        self.__session_analyses = 0
        w, h = self.__camera.Resolution
        self.__status.camera.Set_Value('Connected', Style.CONST_OK, Style.CONST_OK)
        self.__status.resolution.Set_Value('%d × %d' % (w, h))
        if self.__logger is not None:
            # A successful connection resolves a pending connect error, then opens a session.
            if self.__camera_error_id is not None:
                self.__logger.Log_Error_Resolved(self.__camera_error_id)
                self.__camera_error_id = None
            session_index = self.__logger.Log_Camera_Connected('%d × %d' % (w, h))
            # The capture-session id matches the logger's session — its start timestamp
            # plus the index — so its directory and the log refer to the same session, and
            # reconnecting in the same run yields a distinct session (and directory).
            self.__session_id = '%s_s%d' % (datetime.now().strftime('%Y%m%d-%H%M%S'),
                                            session_index)
        self.__Sync_Controls()

    def __On_Connect_Failed(self, message: str) -> None:
        """
        Description:
            The camera failed to open. Report it in the panel.

        Args:
            (1) message [string]: The failure sentence.
        """

        self.__worker_running = False
        self.__conn_thread = None
        self.__conn_worker = None
        self.__viewport.Stop_Busy()
        self.__status.camera.Set_Value('Disconnected', Style.CONST_INK_MUTE, Style.CONST_INK_MUTE)
        if self.__logger is not None:
            self.__camera_error_id = self.__logger.Log_Error(message)
        self.__Fail(message)
        self.__Sync_Controls()

    def __On_Disconnect_Button_Clicked(self) -> None:
        """
        Description:
            Disconnect the camera and clear the frame and its status.
        """

        self.__camera.Disconnect()
        self.__frame = None
        self.__viewport.Clear()
        self.__frame_badge.setText('No frame')
        self.__status.camera.Set_Value('Disconnected', Style.CONST_INK_MUTE, Style.CONST_INK_MUTE)
        self.__status.resolution.Set_Value(Style.CONST_NO_VALUE)
        if self.__logger is not None:
            self.__logger.Log_Camera_Disconnected()
        self.__Sync_Controls()

    def __On_Scan_Button_Clicked(self) -> None:
        """
        Description:
            Capture one frame (a short GUI-thread step), show it in the viewport and
            reset the reading panel.
        """

        if self.__logger is not None:
            self.__logger.Log_Scan_Started()

        try:
            self.__viewport.Set_Busy('Capturing frame…')
            self.__frame = self.__camera.Capture()
        except Camera_Error_Cls as exc:
            if self.__logger is not None:
                # A capture that failed AND left the camera disconnected is a mid-session
                # connection LOST (ERROR, closes the session); a failure while still
                # connected is a transient capture error (tracked ERROR that a later scan
                # can resolve).
                if not self.__camera.Connected:
                    self.__logger.Log_Camera_Connection_Lost(str(exc))
                else:
                    self.__scan_error_id = self.__logger.Log_Error(str(exc))
            self.__Fail(str(exc))
        else:
            self.__viewport.Show_Frame(Rgb_To_Qimage(self.__frame))
            # A dropped-frame count from the driver's retries is reported as one line, not
            # one per retry (the count is attached to the capture, not streamed).
            if self.__logger is not None and self.__camera.Last_Capture_Retries > 0:
                self.__logger.Log_Warning('%d frame(s) dropped during capture (retried)'
                                          % self.__camera.Last_Capture_Retries)
            self.__frame_badge.setText('%d × %d · RGB'
                                       % (self.__frame.shape[1], self.__frame.shape[0]))
            self.__status.updated.Set_Value(datetime.now().strftime('%H:%M:%S'))
            if self.__logger is not None:
                # A successful scan resolves a pending scan error, then reports itself.
                if self.__scan_error_id is not None:
                    self.__logger.Log_Error_Resolved(self.__scan_error_id)
                    self.__scan_error_id = None
                self.__logger.Log_Scan_Ended()
            self.__Clear_Reading()
        finally:
            self.__viewport.Set_Busy('')
            self.__Sync_Controls()

    def __On_Analyze_Button_Clicked(self) -> None:
        """
        Description:
            Hand the analysis to a worker on its own thread and drive the animated
            indicator. Nothing blocks the GUI thread, so the arc turns throughout.
        """

        if self.__frame is None:
            return
        if self.__worker_running:
            # A re-analysis requested while one is still in flight is dropped, not queued;
            # record it so the ignored press is visible rather than silent.
            if self.__logger is not None:
                self.__logger.Log_Warning('Analyze was pressed while an analysis was already '
                                          'running. The request was ignored.')
            return

        # Form this analysis's capture-set id up front, so every log line for the analysis
        # (started, ended, per object, the audit, the capture) carries the same id and an
        # error points straight at the frame that produced it.
        self.__session_analyses += 1
        self.__current_set_id = '%s_%d' % (datetime.now().strftime('%Y%m%d-%H%M%S'),
                                           self.__session_analyses)
        if self.__logger is not None:
            self.__logger.Log_Analysis_Started(self.__session_analyses, self.__current_set_id)

        self.__worker_running = True
        self.__showing_error = False
        # Drop any previous run's renders before this one starts: the toggle hides for
        # the duration, and two Analyze presses in quick succession cannot leave the view
        # showing a mix of two runs.
        self.__viewport.Clear_Views()
        self.__viewport.Start_Busy('Preparing…')
        self.__Sync_Controls()

        self.__thread = QThread(self)
        self.__worker = Analysis_Worker_Cls(self.__vision, self.__frame)
        self.__worker.moveToThread(self.__thread)

        self.__thread.started.connect(self.__worker.Run)
        self.__worker.Stage_Changed.connect(self.__viewport.Set_Busy_Text)
        self.__worker.Progress_Changed.connect(self.__On_Analysis_Progress)
        self.__worker.Log_Event.connect(self.__Log_Event)
        self.__worker.Analysis_Finished.connect(self.__On_Analysis_Finished)
        self.__worker.Analysis_Failed.connect(self.__On_Analysis_Failed)

        # Tear the thread down once the worker is done, whichever way it ended.
        self.__worker.Analysis_Finished.connect(self.__thread.quit)
        self.__worker.Analysis_Failed.connect(self.__thread.quit)
        self.__thread.finished.connect(self.__worker.deleteLater)
        self.__thread.finished.connect(self.__thread.deleteLater)

        self.__thread.start()

    def __On_Analysis_Progress(self, done: int, total: int) -> None:
        """
        Description:
            Update the busy step line as each object is read.

        Args:
            (1) done [int]: The number completed.
            (2) total [int]: The total number of objects.
        """

        # `done` is the number completed; the one being read is done + 1.
        current = min(done + 1, total)
        self.__viewport.Set_Busy_Text('Analysing object %d of %d…' % (current, total))

    def __On_Analysis_Finished(self, result: Analysis_Str) -> None:
        """
        Description:
            Render a finished analysis and re-enable the controls.

        Args:
            (1) result [Analysis_Str(object)]: The scene reading.
        """

        self.__worker_running = False
        self.__thread = None
        self.__worker = None
        self.__viewport.Stop_Busy()

        # Render the two views once, in BGR, then share them: the viewport shows them and
        # the capture writer writes them, so the on-screen and on-disk images are identical.
        frame_bgr = cv2.cvtColor(self.__frame, cv2.COLOR_RGB2BGR)
        annotated_bgr = Draw_Annotated(frame_bgr, result.Objects, cv2, np)
        mask_bgr = Draw_Label_Mask(result.Objects, frame_bgr.shape, cv2, np)
        self.__Show_Analysis(result, annotated_bgr, mask_bgr)

        set_id = self.__current_set_id
        if self.__logger is not None:
            # A successful analysis resolves a pending analysis error, then reports each
            # located object and the finished-analysis summary (inference time and the mean
            # confidence with its coverage). The started and finished lines carry the set
            # id, so the object lines between them need not repeat it.
            if self.__analysis_error_id is not None:
                self.__logger.Log_Error_Resolved(self.__analysis_error_id)
                self.__analysis_error_id = None
            for det in result.Objects:
                confidence = (int(round(100.0 * det.Segmenter_Score))
                              if det.Segmenter_Score is not None else None)
                self.__logger.Log_Object_Detected(det.Label, confidence, det.Bbox)
            # The post-processing audit: every background sentence the composer stripped
            # and every substance substitution it made, each tagged with the object index.
            # Rewriting what the model said is a domain assumption, so it is recorded — a
            # warning when stripping had to fall back, otherwise info — never silent.
            for level, message in result.Audit:
                if level == 'warning':
                    self.__logger.Log_Warning(message)
                else:
                    self.__logger.Log_Info(message)
            # Which renderer produced the artefacts, so the log says so even when the
            # diagnostic index-fill mask mode is active.
            if Annotate.CONST_ANNOTATE_MASK_FILL != 'verdict':
                self.__logger.Log_Info("The label mask was rendered in the diagnostic '%s' mode."
                                       % Annotate.CONST_ANNOTATE_MASK_FILL)
            # The finished-analysis summary: object count, mean confidence and coverage.
            scores = [d.Segmenter_Score for d in result.Objects if d.Segmenter_Score is not None]
            mean = int(round(100.0 * sum(scores) / len(scores))) if scores else None
            self.__logger.Log_Analysis_Finished(self.__session_analyses, result.Latency_Ms,
                                                len(result.Objects), len(scores), mean, set_id)
            self.__Write_Capture(set_id, result, frame_bgr, annotated_bgr, mask_bgr)
        self.__Sync_Controls()

    def __Write_Capture(self, set_id: str, result: Analysis_Str, frame_bgr: tp.Any,
                        annotated_bgr: tp.Any, mask_bgr: tp.Any) -> None:
        """
        Description:
            Write this analysis's capture set into the current session's directory — the
            raw frame, the annotated image, the label mask, the Scene-Understanding text
            and the YOLO region records — refresh the classes file, and enforce the global
            retention bound, logging the session-directory creation, what was written and
            what was evicted. Writing must never break the analysis: a full disk or a
            permission failure is caught, logged as an ERROR, and the UI carries on.

        Args:
            (1) set_id [string]: The capture-set id (filename stem).
            (2) result [Analysis_Str(object)]: The scene reading.
            (3) frame_bgr [Matrix<uint8> HxWx3]: The raw frame (BGR).
            (4) annotated_bgr [Matrix<uint8> HxWx3]: The annotated image (BGR).
            (5) mask_bgr [Matrix<uint8> HxWx3]: The label mask (BGR).
        """

        if self.__capture_writer is None or self.__session_id is None:
            return
        # The '.txt' is exactly the panel's text — the shared formatter, not a second path.
        # The YOLO boxes and segmentation polygons come from the same object list (and the same
        # per-object masks), normalised against the frame, so every artefact and both images
        # describe identical objects in identical order.
        understanding = Screen_Understanding(result.Objects, result.Background)
        height, width = frame_bgr.shape[:2]
        size = (width, height)
        yolo = Yolo_Lines(result.Objects, size)
        seg = Seg_Lines(result.Objects, size, cv2, np)
        scores = [d.Segmenter_Score for d in result.Objects if d.Segmenter_Score is not None]
        frame_mean = int(round(100.0 * sum(scores) / len(scores))) if scores else None
        timestamp = datetime.now().isoformat(timespec='seconds')
        metadata = Build_Set_Metadata(self.__session_id, set_id, timestamp, result.Objects,
                                      size, result.Task, result.Latency_Ms, frame_mean)
        stamp = 'set %s | %s' % (set_id, timestamp)
        try:
            evicted, created = self.__capture_writer.Write(
                self.__session_id, set_id, frame_bgr, annotated_bgr, mask_bgr,
                understanding, yolo, seg, metadata, stamp, cv2, np)
        except Exception as exc:                          # noqa: BLE001
            self.__logger.Log_Error('failed to write capture set %s: %s' % (set_id, exc))
            return
        self.__Log_Capture_Side_Effects(created)
        self.__logger.Log_Info('Capture set %s written.' % set_id)
        self.__Log_Seg_Points(seg)
        self.__Log_Capture_Evictions(evicted)

    def __Log_Seg_Points(self, seg_lines: tp.List[str]) -> None:
        """
        Description:
            Report the typical polygon size — the median vertex count per object — so an
            unsimplified contour (thousands of points, a useless file) is visible in the log.

        Args:
            (1) seg_lines [Vector<string>]: The segmentation lines, one per object.
        """

        if not seg_lines:
            return
        counts = sorted((len(line.split()) - 1) // 2 for line in seg_lines)
        median = counts[len(counts) // 2]
        self.__logger.Log_Info('Segmentation polygons written for %d object%s; median %d '
                               'points per object.' % (len(counts), '' if len(counts) == 1
                                                       else 's', median))

    def __Log_Capture_Side_Effects(self, created_session: tp.Optional[str]) -> None:
        """
        Description:
            Log a session-directory creation (once per session, so a fresh directory on
            disk is never a surprise).

        Args:
            (1) created_session [string]: The session id whose directory was just created,
                                          or None when it already existed.
        """

        if created_session is not None:
            self.__logger.Log_Info('Created the capture directory for session %s.' % created_session)

    def __Log_Capture_Evictions(self, evicted: tp.List[str]) -> None:
        """
        Description:
            Log every eviction, so a set the operator was about to open is never deleted
            silently.

        Args:
            (1) evicted [Vector<string>]: The evicted set ids, oldest first.
        """

        for old in evicted:
            self.__logger.Log_Info('Evicted the oldest capture set %s to stay within the '
                                   'retention limit of %d across sessions.'
                                   % (old, self.__capture_writer.Retention))

    def __Log_Event(self, level: str, message: str) -> None:
        """
        Description:
            Route a (level, message) event from the Qt-free camera or vision layer to the
            session logger by level. The single sink both layers emit through, so their
            events reach the log without either holding the logger.

        Args:
            (1) level [string]: 'INFO', 'WARNING' or 'ERROR'.
            (2) message [string]: The event text.
        """

        if self.__logger is None:
            return
        if level == 'ERROR':
            self.__logger.Log_Error(message)
        elif level == 'WARNING':
            self.__logger.Log_Warning(message)
        else:
            self.__logger.Log_Info(message)

    def __On_Analysis_Failed(self, message: str) -> None:
        """
        Description:
            Report an analysis failure in the panel.

        Args:
            (1) message [string]: The failure sentence.
        """

        self.__worker_running = False
        self.__thread = None
        self.__worker = None
        self.__viewport.Stop_Busy()
        set_id = self.__current_set_id
        if self.__logger is not None:
            # The error belongs to THIS analysis, so it carries the set id — the raw frame
            # that caused the failure is in the capture directory under that id, and this
            # is the case where the link matters most.
            suffix = ' (set=%s)' % set_id if set_id else ''
            self.__analysis_error_id = self.__logger.Log_Error(message + suffix)
            # A failed analysis renders no annotated image or mask (rendering is on the
            # success path), but the raw frame exists — write a PARTIAL set (raw + a note)
            # so the crash leaves evidence rather than nothing.
            self.__Write_Partial_Capture(set_id, message)
        self.__Fail(message)

    def __Write_Partial_Capture(self, set_id: str, message: str) -> None:
        """
        Description:
            Write the partial capture for a failed analysis — the raw frame and a note —
            and log that it is partial. Like the full capture, a write failure here is
            caught and logged, never raised, so it cannot mask the analysis failure.

        Args:
            (1) set_id [string]: The capture-set id, or None when no analysis was in flight.
            (2) message [string]: The failure sentence, recorded in the note.
        """

        if self.__capture_writer is None or set_id is None or self.__frame is None \
                or self.__session_id is None:
            return
        frame_bgr = cv2.cvtColor(self.__frame, cv2.COLOR_RGB2BGR)
        note = ('Analysis FAILED — partial capture (raw frame only, no annotated image or '
                'mask). Failure: %s' % message)
        stamp = 'set %s (partial) | %s' % (set_id, datetime.now().isoformat(timespec='seconds'))
        try:
            evicted, created = self.__capture_writer.Write_Partial(
                self.__session_id, set_id, frame_bgr, note, stamp, cv2, np)
        except Exception as exc:                          # noqa: BLE001
            self.__logger.Log_Error('failed to write partial capture set %s: %s' % (set_id, exc))
            return
        self.__Log_Capture_Side_Effects(created)
        self.__logger.Log_Warning('Wrote a partial capture set %s for the failed analysis. It '
                                  'holds the raw frame only.' % set_id)
        self.__Log_Capture_Evictions(evicted)

    def __Show_Analysis(self, result: Analysis_Str, annotated_bgr: tp.Any, mask_bgr: tp.Any) -> None:
        """
        Description:
            Render the reading: the summary lead, the object lines, the note, the
            box overlay, the verdict badge, the meta rows and the counters. The two Camera
            View images are rendered by the caller (once, in BGR, shared with the capture
            writer), so the on-screen and on-disk images are identical.

        Args:
            (1) result [Analysis_Str(object)]: The scene reading.
            (2) annotated_bgr [Matrix<uint8> HxWx3]: The annotated image (BGR).
            (3) mask_bgr [Matrix<uint8> HxWx3]: The label mask (BGR).
        """

        self.__showing_error = False
        self.__reading_empty.hide()
        # The lead is the shared Screen-Understanding header — the background stated once
        # with the object count — the SAME first line the descriptions file carries, so
        # the view and the file cannot drift. The per-object lines below come from the
        # same shared formatter (via Object_List_Cls).
        self.__reading_lead.setText(Screen_Header(result.Objects, result.Background))
        self.__reading_lead.show()
        self.__object_list.Set_Objects(result.Objects)
        self.__reading_note.setText(result.Note)
        self.__reading_note.setVisible(bool(result.Note))

        # Both are held for the instant annotated/mask swap (§2b); the remembered view
        # choice is restored so a mask-view session stays in mask view.
        self.__viewport.Show_Views(Bgr_To_Qimage(annotated_bgr), Bgr_To_Qimage(mask_bgr),
                                   self.__view_choice)
        self.__view_toggle.Set_View(self.__view_choice)
        self.__stage_badge.Set_State(result.Verdict, result.Verdict_Level)

        self.__meta_task.setText(result.Task)
        self.__meta_latency.setText('%d ms' % result.Latency_Ms)
        self.__meta_confidence.setText(self.__Frame_Confidence_Text(result.Objects))

        self.__analyses += 1
        self.__objects_found += len(result.Objects)
        self.__status.images.Set_Value(str(self.__analyses))
        self.__status.objects.Set_Value(str(self.__objects_found))
        self.__status.updated.Set_Value(datetime.now().strftime('%H:%M:%S'))
        self.__Update_Performance_Stats(result)

    def __Update_Performance_Stats(self, result: Analysis_Str) -> None:
        """
        Description:
            Update the two status-strip aggregate cells from a completed analysis, both over
            the WHOLE session: the rolling MEDIAN inference latency across the session's
            analyses (not per object, and a median so one slow frame does not swing it), and
            the MEAN detector confidence over every scored object in every analysis since the
            session began. This session mean is deliberately distinct from the per-frame mean
            the panel table shows — they cover different scopes and will read different
            numbers at the same time. Only FastSAM supplies scores; objects the background cue
            alone found (Segmenter_Score None) have none, so the mean is over exactly the
            scored objects (never averaged silently over a partial set) and reads '—' until
            one object anywhere in the session is scored.

        Args:
            (1) result [Analysis_Str(object)]: The scene reading.
        """

        self.__latencies.append(result.Latency_Ms)
        self.__status.inference.Set_Value('%d ms' % int(statistics.median(self.__latencies)))

        self.__session_scores.extend(det.Segmenter_Score for det in result.Objects
                                     if det.Segmenter_Score is not None)
        if self.__session_scores:
            mean = sum(self.__session_scores) / len(self.__session_scores)
            self.__status.confidence.Set_Value('%d%%' % int(round(100.0 * mean)))
        else:
            self.__status.confidence.Set_Value(Style.CONST_NO_VALUE)

    def __Frame_Confidence_Text(self, objects: tp.List[Detection_Str]) -> str:
        """
        Description:
            The panel table's per-frame confidence: the MEAN detector score over exactly the
            objects in THIS frame that carry a score. When some objects were found by the
            background cue alone the coverage is shown alongside ('87% over 5 of 9'), since
            the object list directly below marks which objects lack a score and the two
            reconcile against each other; a fully scored frame needs no coverage and shows
            the percentage alone. With nothing scored it reads '—' rather than '0%', which
            would misstate an absent measurement as a zero confidence.

        Args:
            (1) objects [Vector<Detection_Str(object)>]: This frame's located objects.

        Returns:
            (1) parameter [string]: The frame confidence ('N%', 'N% over K of M' or '—').
        """

        scores = [det.Segmenter_Score for det in objects if det.Segmenter_Score is not None]
        if not scores:
            return Style.CONST_NO_VALUE
        mean = int(round(100.0 * sum(scores) / len(scores)))
        if len(scores) < len(objects):
            return '%d%% over %d of %d' % (mean, len(scores), len(objects))
        return '%d%%' % mean

    def __On_View_Toggle(self, view: str) -> None:
        """
        Description:
            Switch the Camera View between the annotated image and the mask. This only
            swaps the held render in place — it never re-runs analysis and never reads
            from disk — and remembers the choice for the next analysis.

        Args:
            (1) view [string]: 'annotated' or 'mask'.
        """

        self.__view_choice = view
        self.__viewport.Set_View(view)

    def __On_View_Selected(self, key: str) -> None:
        """
        Description:
            Switch the central area to the selected view (Live / History / Log). Only the stack
            page changes; the header, status strip and footer stay fixed, and every view keeps
            its state — so an analysis started on another view still shows its result when Live
            is selected again, and the status strip keeps updating throughout.

        Args:
            (1) key [string]: The view key ('live', 'history' or 'log').
        """

        index = self.CONST_VIEW_INDEX.get(key)
        if index is not None:
            self.__stack.setCurrentIndex(index)
        # History is a rolling window of what is on disk now — rediscover the sets each time it
        # is shown, so a set written (or evicted) since last time is reflected.
        if key == 'history':
            self.__history_view.Refresh()

    def __Clear_Reading(self) -> None:
        """
        Description:
            Reset the reading panel to its prompt/idle state.
        """

        self.__showing_error = False
        self.__reading_empty.setText(self.__Prompt_Text())
        self.__reading_empty.show()
        self.__reading_lead.hide()
        self.__reading_note.hide()
        self.__object_list.Set_Objects([])
        self.__stage_badge.Set_State('Idle', 'idle')
        self.__meta_task.setText(Style.CONST_NO_VALUE)
        self.__meta_latency.setText(Style.CONST_NO_VALUE)
        self.__meta_confidence.setText(Style.CONST_NO_VALUE)

    def __On_Clear_Button_Clicked(self) -> None:
        """
        Description:
            Clear the frame, the counters and the reading panel.
        """

        if self.__logger is not None:
            self.__logger.Log_Info('Cleared the frame, the counters and the reading panel')
        self.__frame = None
        self.__analyses = 0
        self.__objects_found = 0
        self.__latencies = []
        self.__session_scores = []
        self.__viewport.Clear()
        self.__frame_badge.setText('No frame')
        self.__status.images.Set_Value('0')
        self.__status.objects.Set_Value('0')
        self.__status.updated.Set_Value(Style.CONST_NO_VALUE)
        self.__status.inference.Set_Value(Style.CONST_NO_VALUE)
        self.__status.confidence.Set_Value(Style.CONST_NO_VALUE)
        self.__Clear_Reading()
        self.__Sync_Controls()

    # << QT OVERRIDE >> #
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Description:
            Esc closes the window; F11 toggles fullscreen.

        Args:
            (1) event [QKeyEvent(object)]: The Qt key event.
        """

        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        else:
            super().keyPressEvent(event)

    # << QT OVERRIDE >> #
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Description:
            Stop any running worker thread (analysis or connect) before the window is
            torn down, or Qt warns 'QThread: Destroyed while thread is still running'
            and may crash on exit.

        Args:
            (1) event [QCloseEvent(object)]: The Qt close event.
        """

        for thread in (self.__thread, self.__conn_thread):
            if thread is not None:
                thread.quit()
                thread.wait(5000)
        # Write the run summary and close the log file on a normal window close. Close
        # is idempotent, so the launcher's try/finally may safely run it again.
        if self.__logger is not None:
            self.__logger.Close()
        super().closeEvent(event)
