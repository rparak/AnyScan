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
                             QGridLayout, QScrollArea, QFrame)
# Custom Lib.: AnyScan UI — style, widgets and workers
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import (Font, Load_Svg, Load_Logo, Rgb_To_Qimage, Bgr_To_Qimage,
                                Hairline)
#   ../UI/Widgets
from UI.Widgets import (Card_Cls, Card_Head_Cls, Icon_Cls, Viewport_Cls, Tool_Button_Cls,
                        View_Toggle_Cls, Object_List_Cls, Status_Strip_Cls, Funding_Row_Cls)
#   ../UI/Workers
from UI.Workers import Analysis_Worker_Cls, Connect_Worker_Cls
# Custom Lib.: AnyScan domain — backends, renderers and the result structure
#   ../Camera/Core
from Camera.Core import Basler_Camera_Cls, Camera_Error_Cls
#   ../Vision/Core
from Vision.Core import Florence_Vision_Cls
#   ../Vision/Utilities/Annotate
from Vision.Utilities.Annotate import Draw_Annotated, Draw_Label_Mask
#   ../Reporting/Core
from Reporting.Core import Screen_Header
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
# Custom Lib.: AnyScan — the session logger
#   ../Logger/Core
from Logger.Core import Session_Logger_Cls


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
        self.__meta_objects = None
        self.__meta_latency = None
        self.__button_connect = None
        self.__button_disconnect = None
        self.__button_scan = None
        self.__button_analyze = None
        self.__button_clear = None

        self.__Build_Ui()
        self.__Connect_Signals()
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

        grid = QGridLayout()
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__Build_Camera_Card(), 0, 0)
        grid.addWidget(self.__Build_Reading_Card(), 0, 1)
        grid.setColumnStretch(0, 55)   # the frame is always the widest element
        grid.setColumnStretch(1, 45)
        grid.setRowStretch(0, 1)       # spare height goes to the reading panel

        self.__status = Status_Strip_Cls()
        grid.addWidget(self.__status, 1, 0, 1, 2)
        grid.addWidget(Funding_Row_Cls(), 2, 0, 1, 2)

        outer.addLayout(grid, 1)

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
            meta rows (task, objects, inference time).

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
        self.__meta_task = self.__Meta_Row(meta, 'Task', first=True)
        self.__meta_objects = self.__Meta_Row(meta, 'Objects found')
        self.__meta_latency = self.__Meta_Row(meta, 'Inference time', mono=True)
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
        w, h = self.__camera.Resolution
        self.__status.camera.Set_Value('Connected', Style.CONST_OK, Style.CONST_OK)
        self.__status.resolution.Set_Value('%d × %d' % (w, h))
        if self.__logger is not None:
            # A successful connection resolves a pending connect error, then opens a session.
            if self.__camera_error_id is not None:
                self.__logger.Log_Error_Resolved(self.__camera_error_id)
                self.__camera_error_id = None
            self.__logger.Log_Camera_Connected('%d × %d' % (w, h))
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
                self.__scan_error_id = self.__logger.Log_Error(str(exc))
            self.__Fail(str(exc))
        else:
            self.__viewport.Show_Frame(Rgb_To_Qimage(self.__frame))
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

        if self.__frame is None or self.__worker_running:
            return

        if self.__logger is not None:
            self.__logger.Log_Analysis_Started()

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
        self.__Show_Analysis(result)
        if self.__logger is not None:
            # A successful analysis resolves a pending analysis error, then reports the
            # analyzed image, every located object, and the inference time.
            if self.__analysis_error_id is not None:
                self.__logger.Log_Error_Resolved(self.__analysis_error_id)
                self.__analysis_error_id = None
            self.__logger.Log_Image_Analyzed(self.__analyses, len(result.Objects))
            for det in result.Objects:
                self.__logger.Log_Object_Detected(det.Label, det.Confidence, det.Bbox, det.Sentence)
            # The post-processing audit: every background sentence the composer stripped
            # and every substance substitution it made, each already tagged with the
            # object index. Rewriting what the model said is a domain assumption, so it is
            # recorded — a warning when stripping had to fall back, otherwise info — never
            # silent (§3). The view switch, by contrast, is not worth a log line.
            for level, message in result.Audit:
                if level == 'warning':
                    self.__logger.Log_Warning(message)
                else:
                    self.__logger.Log_Info(message)
            self.__logger.Log_Analysis_Ended(result.Latency_Ms)
        self.__Sync_Controls()

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
        if self.__logger is not None:
            self.__analysis_error_id = self.__logger.Log_Error(message)
        self.__Fail(message)
        self.__Sync_Controls()

    def __Show_Analysis(self, result: Analysis_Str) -> None:
        """
        Description:
            Render the reading: the summary lead, the object lines, the note, the
            box overlay, the verdict badge, the meta rows and the counters.

        Args:
            (1) result [Analysis_Str(object)]: The scene reading.
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

        # Produce both Camera View renders from the completed result via the SAME shared
        # renderers the harness exports, so the on-screen annotated view is exactly the
        # exported image. Both are held for the instant annotated/mask swap (§2b); the
        # remembered view choice is restored so a mask-view session stays in mask view.
        annotated, mask = self.__Render_Views(result)
        self.__viewport.Show_Views(annotated, mask, self.__view_choice)
        self.__view_toggle.Set_View(self.__view_choice)
        self.__stage_badge.Set_State(result.Verdict, result.Verdict_Level)

        self.__meta_task.setText(result.Task)
        self.__meta_objects.setText(str(len(result.Objects)))
        self.__meta_latency.setText('%d ms' % result.Latency_Ms)

        self.__analyses += 1
        self.__objects_found += len(result.Objects)
        self.__status.images.Set_Value(str(self.__analyses))
        self.__status.objects.Set_Value(str(self.__objects_found))
        self.__status.updated.Set_Value(datetime.now().strftime('%H:%M:%S'))
        self.__Update_Performance_Stats(result)

    def __Update_Performance_Stats(self, result: Analysis_Str) -> None:
        """
        Description:
            Update the two performance cells from a completed analysis: the rolling
            MEDIAN inference latency across the session's analyses (not per object, and a
            median so one slow frame does not swing it), and the MEAN detector confidence
            over the objects that carry a score. Only FastSAM supplies scores; objects the
            background cue alone found (Segmenter_Score None) have none, so the mean is
            shown WITH its coverage — '87% (5/9)' — never averaged silently over a partial
            set, and '—' when no object has a score.

        Args:
            (1) result [Analysis_Str(object)]: The scene reading.
        """

        self.__latencies.append(result.Latency_Ms)
        self.__status.inference.Set_Value('%d ms' % int(statistics.median(self.__latencies)))

        scores = [det.Segmenter_Score for det in result.Objects if det.Segmenter_Score is not None]
        if scores:
            mean_pct = int(round(100.0 * sum(scores) / len(scores)))
            self.__status.confidence.Set_Value('%d%% (%d/%d)'
                                               % (mean_pct, len(scores), len(result.Objects)))
        else:
            self.__status.confidence.Set_Value(Style.CONST_NO_VALUE)

    def __Render_Views(self, result: Analysis_Str) -> tp.Tuple[tp.Any, tp.Any]:
        """
        Description:
            Render the annotated image and the label mask for the current frame from the
            completed result, as QImages ready for the viewport. Both go through the
            shared Vision renderers (Draw_Annotated, Draw_Label_Mask) — the same code the
            validation harness exports — so the view and the file cannot drift, and both
            are the frame's resolution so the toggle swaps them in place.

        Args:
            (1) result [Analysis_Str(object)]: The scene reading.

        Returns:
            (1) parameter [Tuple<QImage>]: (annotated, mask).
        """

        frame_bgr = cv2.cvtColor(self.__frame, cv2.COLOR_RGB2BGR)
        annotated = Draw_Annotated(frame_bgr, result.Objects, cv2, np)
        mask = Draw_Label_Mask(result.Objects, frame_bgr.shape, cv2, np)
        return Bgr_To_Qimage(annotated), Bgr_To_Qimage(mask)

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
        self.__meta_objects.setText(Style.CONST_NO_VALUE)
        self.__meta_latency.setText(Style.CONST_NO_VALUE)

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
