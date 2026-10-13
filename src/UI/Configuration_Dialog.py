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
# File Name: ../UI/Configuration_Dialog.py
## =========================================================================== ##

# System (Default)
import os
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QThread, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QCloseEvent, QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (QDialog, QWidget, QLabel, QListWidget, QListWidgetItem, QProgressBar,
                             QVBoxLayout, QHBoxLayout, QLayout)
# Custom Lib.: AnyScan UI — style and the shared buttons, and the model-load worker
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font
#   ../UI/Widgets
from UI.Widgets import Tool_Button_Cls
#   ../UI/Workers
from UI.Workers import Model_Load_Worker_Cls, Join_Worker_Thread
# Custom Lib.: AnyScan — the configuration layer (the one reader of a configuration file)
#   ../Configuration/Core
from Configuration.Core import (Load_Configuration, Discover_Configurations, Configuration_Error_Cls,
                                Describe_Configuration, Display_Path, Mode_Directory)
#   ../Parameters/Configuration
from Parameters.Configuration import Configuration_Str

"""
Description:
    Initialization of constants.
"""
# The dialog's width and inner margin; the wrapped message is sized to the width between them.
#   Unit [int] (px)
CONST_DIALOG_WIDTH = 520
CONST_DIALOG_MARGIN = 24
# The list marker's size: a filled dot marks the configuration in force. The list shows up to
# CONST_LIST_ROWS rows before it scrolls.
#   Unit [int] (px) / [int]
CONST_MARK_PX = 10
CONST_LIST_ROWS = 6


def _Mark(filled: bool) -> QIcon:
    """
    Description:
        The list marker: a filled dot for the configuration in force, an empty (transparent) one of
        the same size for the rest, so every name starts at the same x.

    Args:
        (1) filled [bool]: The in-force marker, or the blank one.

    Returns:
        (1) parameter [QIcon(object)]: The marker.
    """

    pixmap = QPixmap(CONST_MARK_PX, CONST_MARK_PX)
    pixmap.fill(Qt.transparent)
    if filled:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(Style.CONST_OK))
        painter.drawEllipse(1, 1, CONST_MARK_PX - 2, CONST_MARK_PX - 2)
        painter.end()
    return QIcon(pixmap)


class Configuration_Dialog_Cls(QDialog):
    """
    Description:
        The Configuration dialog: the usable configurations found in Configuration/Mode/, listed by
        their display name with the one in force marked, and Load. Loading validates the chosen
        file as a whole, then loads it on a worker thread (Model_Load_Worker_Cls: ~9 s) with the
        progress showing. On success it confirms what was loaded, in a sentence, and stays open
        until the operator closes it — the confirmation is there to be read; on failure it says
        what was wrong and the previous configuration stays in force. The words
        are the operator's — a configuration is loaded; its models are how — and model files, load
        times and the task go to the log. A file that cannot be loaded is not listed; it is logged
        at WARNING with the reason, so a corrupt file is told apart from a missing one.

        The dialog changes nothing itself: it emits Configuration_Loaded and the window applies it.

    Initialization of the Class:
        Args:
            (1) vision [Vision_Pipeline_Cls(object)]: The vision backend whose models load.
            (2) Configuration_Str [Configuration_Str(object)]: The configuration in force.
            (3) log_cb [function or None]: (level, message) sink for the files not listed.

        Example:
            Initialization:
                # Initialization of the class.
                Cls = Configuration_Dialog_Cls(vision, Configuration_Str, parent)

            Features:
                # Signals of the class.
                Cls.Load_Started; Cls.Configuration_Loaded; Cls.Load_Refused; Cls.Load_Failed

                # Functions of the class.
                Cls.Select(path); Cls.Load(); Cls.exec_()
    """

    # << SIGNALS >> #
    Load_Started = pyqtSignal()                        # a load has begun (the header shows it)
    Configuration_Loaded = pyqtSignal(object, float)   # (the Configuration_Str, load seconds)
    Load_Refused = pyqtSignal(str)                     # invalid file / other hardware: nothing changed
    Load_Failed = pyqtSignal(str)                      # the models failed: the previous one is in force

    def __init__(self, vision: tp.Any, Configuration_Str: Configuration_Str,
                 parent: tp.Optional[QWidget] = None,
                 log_cb: tp.Optional[tp.Callable[[str, str], None]] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__vision = vision
        self.__log_cb = log_cb
        self.__config = Configuration_Str
        self.__thread = None
        self.__worker = None
        self.__candidate = None
        # Widgets, populated by __Initialize_Ui.
        self.__list = None
        self.__label_empty = None
        self.__button_load = None
        self.__button_close = None
        self.__progress = None
        self.__label_stage = None
        self.__label_result = None

        self.__Initialize_Ui()
        self.__Connect_Signals()
        self.__Populate()

    @property
    def Loading(self) -> bool:
        """
        Description:
            Whether a model load is in progress (the dialog cannot be closed meanwhile).

        Returns:
            (1) parameter [bool]: True while the worker runs.
        """

        return self.__thread is not None

    def __Initialize_Ui(self) -> None:
        """
        Description:
            Build the dialog: the list, the progress, the message and the two buttons.
        """

        self.setWindowTitle('Configuration')
        self.setModal(True)
        self.setFixedWidth(CONST_DIALOG_WIDTH)
        self.setStyleSheet('QDialog { background: %s; }' % Style.CONST_CARD)

        box = QVBoxLayout(self)
        box.setContentsMargins(CONST_DIALOG_MARGIN, 22, CONST_DIALOG_MARGIN, 22)
        box.setSpacing(14)
        # The dialog follows its content's height as the message appears and wraps.
        box.setSizeConstraint(QLayout.SetMinAndMaxSize)

        title = QLabel('Configuration')
        title.setFont(Font(Style.CONST_TYPE_SCALE[4], QFont.DemiBold))
        title.setStyleSheet('color: %s;' % Style.CONST_INK)
        box.addWidget(title)

        self.__list = QListWidget()
        self.__list.setFont(Font(Style.CONST_TYPE_SCALE[2]))
        # The list fixes the dialog's width (the layout sizes the window to its content), never
        # scrolls sideways, and elides a name too long for it.
        self.__list.setFixedWidth(CONST_DIALOG_WIDTH - 2 * CONST_DIALOG_MARGIN)
        self.__list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.__list.setTextElideMode(Qt.ElideMiddle)
        self.__list.setIconSize(QSize(CONST_MARK_PX, CONST_MARK_PX))
        self.__list.setStyleSheet(
            'QListWidget { border: 1px solid %(border)s; border-radius: 8px; padding: 4px; outline: 0;'
            '              background: %(card)s; color: %(ink)s; }'
            'QListWidget::item { padding: 7px 6px; border-radius: 6px; color: %(ink)s; }'
            'QListWidget::item:selected { background: %(hover)s; color: %(ink)s; }'
            'QListWidget::item:disabled { color: %(mute)s; }'
            % {'border': Style.CONST_CONTROL_BORDER, 'card': Style.CONST_CARD, 'ink': Style.CONST_INK,
               'hover': Style.CONST_CONTROL_HOVER, 'mute': Style.CONST_INK_MUTE})
        box.addWidget(self.__list)
        # Where the list would be when there is nothing to list: it must be unmistakable, because
        # then no configuration can be loaded and CONNECT can never become available.
        self.__label_empty = QLabel()
        self.__label_empty.setFont(Font(Style.CONST_TYPE_SCALE[2]))
        self.__label_empty.setWordWrap(True)
        self.__label_empty.setStyleSheet('color: %s;' % Style.CONST_LOG_ERROR)
        self.__label_empty.hide()
        box.addWidget(self.__label_empty)

        self.__progress = QProgressBar()
        self.__progress.setRange(0, 0)                   # indeterminate: the load reports steps, not %
        self.__progress.setTextVisible(False)
        self.__progress.setFixedHeight(6)
        # From the palette like every other control: the divider tone for the track, the brand ink
        # for the moving bar — not the platform's default blue.
        self.__progress.setStyleSheet(
            'QProgressBar { border: none; border-radius: 3px; background: %s; }'
            'QProgressBar::chunk { border-radius: 3px; background: %s; }'
            % (Style.CONST_LINE, Style.CONST_INK))
        self.__progress.hide()
        box.addWidget(self.__progress)
        self.__label_stage = QLabel()
        self.__label_stage.setFont(Font(Style.CONST_TYPE_SCALE[1]))
        self.__label_stage.setStyleSheet('color: %s;' % Style.CONST_INK_SOFT)
        self.__label_stage.hide()
        box.addWidget(self.__label_stage)

        self.__label_result = QLabel()
        self.__label_result.setFont(Font(Style.CONST_TYPE_SCALE[1]))
        self.__label_result.setWordWrap(True)
        self.__label_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.__label_result.hide()
        box.addWidget(self.__label_result)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addStretch(1)
        self.__button_close = Tool_Button_Cls('CLOSE')
        self.__button_load = Tool_Button_Cls('LOAD', primary=True)
        for button in (self.__button_close, self.__button_load):
            button.setFixedWidth(140)
            buttons.addWidget(button)
        box.addLayout(buttons)

    def __Connect_Signals(self) -> None:
        """
        Description:
            Wire the dialog's buttons and list.
        """

        self.__button_load.clicked.connect(self.Load)
        self.__button_close.clicked.connect(self.reject)
        self.__list.itemDoubleClicked.connect(lambda _item: self.Load())
        self.__list.currentItemChanged.connect(lambda *_args: self.__On_Selection_Changed())

    def __Populate(self, log: bool = True) -> None:
        """
        Description:
            List the usable configurations in Configuration/Mode/ (and the one in force if it lives
            elsewhere) by display name, the one in force marked and selected. One for other hardware
            is shown greyed — it exists, and its tooltip says why it cannot be chosen. A file that
            cannot be loaded is NOT listed; it is logged at WARNING with the reason. With nothing
            usable, the list is replaced by a message naming the directory searched.

        Args:
            (1) log [bool]: Log the files not listed (once per opening, not again on a refresh).
        """

        entries = Discover_Configurations(Mode_Directory())
        if not any(os.path.abspath(path) == self.__config.Path for path, _c, _e in entries):
            try:
                entries.insert(0, (self.__config.Path, Load_Configuration(self.__config.Path), ''))
            except Configuration_Error_Cls as error:
                entries.insert(0, (self.__config.Path, None, str(error)))
        for path, config, error in entries:
            if config is None and log and self.__log_cb is not None:
                self.__log_cb('WARNING', 'Configuration file %s is not listed: %s' % (os.path.basename(path), error))
        usable = [(path, config) for path, config, _error in entries if config is not None]
        # This hardware's configurations first; other hardware's (shown, not choosable) after them.
        usable.sort(key=lambda entry: entry[1].Hardware != self.__config.Hardware)

        self.__list.clear()
        for path, config in usable:
            in_force = os.path.abspath(path) == self.__config.Path
            item = QListWidgetItem(_Mark(in_force), config.Identity.Display_Name)
            item.setData(Qt.UserRole, path)
            if in_force:
                font = item.font()
                font.setWeight(QFont.DemiBold)
                item.setFont(font)
            if config.Hardware != self.__config.Hardware:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
                item.setToolTip('Other hardware: start with --config to use it.')
            self.__list.addItem(item)
            if in_force:
                self.__list.setCurrentItem(item)

        choosable = any(config.Hardware == self.__config.Hardware for _path, config in usable)
        self.__list.setVisible(bool(usable))
        self.__label_empty.setVisible(not choosable)
        self.__Sync_Load()
        if not choosable:
            self.__label_empty.setText('No usable configuration for this camera in %s. Nothing can be '
                                       'loaded, so CONNECT stays unavailable. Add a valid configuration '
                                       'there (the log says why any file there was not listed).'
                                       % Display_Path(Mode_Directory()))
            self.__Fit(self.__label_empty)
        rows = max(1, min(self.__list.count(), CONST_LIST_ROWS))
        self.__list.setFixedHeight(rows * max(self.__list.sizeHintForRow(0), 1) + 2 * self.__list.frameWidth() + 10)

    def __On_Selection_Changed(self) -> None:
        """
        Description:
            A new selection clears the last result and re-decides whether LOAD has anything to do.
        """

        self.__label_result.hide()
        self.__Sync_Load()

    def __Sync_Load(self) -> None:
        """
        Description:
            LOAD is available when it would change something: a selected configuration other than
            the one in force, or the one in force while it is not loaded. Right after a successful
            load the one in force is selected and loaded, so there is nothing to do but close.
        """

        item = self.__list.currentItem()
        chosen = item is not None and bool(item.flags() & Qt.ItemIsEnabled) and not self.Loading
        in_force_loaded = (item is not None and os.path.abspath(item.data(Qt.UserRole)) == self.__config.Path
                           and self.__vision.Models_Loaded)
        self.__button_load.setEnabled(chosen and not in_force_loaded)

    def __Fit(self, label: QLabel) -> None:
        """
        Description:
            Give a word-wrapped label the height its text needs at the dialog's width. Qt does not
            ask a wrapped label for its height at the width it actually gets inside a top-level
            window, so without this a long message is cut after its first lines.

        Args:
            (1) label [QLabel(object)]: The label whose text just changed.
        """

        width = CONST_DIALOG_WIDTH - 2 * CONST_DIALOG_MARGIN
        label.setFixedWidth(width)
        label.setFixedHeight(label.heightForWidth(width))

    def __Show_Result(self, text: str, ok: bool) -> None:
        """
        Description:
            Show the outcome under the list.

        Args:
            (1) text [string]: The message.
            (2) ok [bool]: Success (the OK ink) or failure (the error colour).
        """

        # A file name is one long 'word'; a zero-width space after each underscore lets it wrap
        # there instead of running past the dialog's edge (display only — the log keeps the text).
        self.__label_result.setText(text.replace('_', '_\u200b'))
        self.__label_result.setStyleSheet('color: %s;' % (Style.CONST_OK_INK if ok else Style.CONST_LOG_ERROR))
        self.__Fit(self.__label_result)
        self.__label_result.show()

    def __Set_Busy(self, busy: bool) -> None:
        """
        Description:
            Show the progress and lock the dialog's controls while the models load.

        Args:
            (1) busy [bool]: Whether a load is running.
        """

        self.__progress.setVisible(busy)
        self.__label_stage.setVisible(busy)
        for widget in (self.__list, self.__button_close):
            widget.setEnabled(not busy)
        if busy:
            self.__button_load.setEnabled(False)
        else:
            self.__Sync_Load()

    def Select(self, path: str) -> None:
        """
        Description:
            Select a listed configuration by its file (what a click does).

        Args:
            (1) path [string]: The configuration file.
        """

        for row in range(self.__list.count()):
            item = self.__list.item(row)
            if os.path.abspath(item.data(Qt.UserRole)) == os.path.abspath(path):
                self.__list.setCurrentItem(item)
                return
        raise ValueError('%s is not listed' % path)

    def Load(self) -> None:
        """
        Description:
            Validate the selected configuration, then put it in force on a worker thread. A file
            that is invalid, or that names different hardware or a different station-event directory,
            is refused on the spot: nothing changes.
        """

        item = self.__list.currentItem()
        if self.Loading or item is None:
            return
        self.__label_result.hide()

        # 1\ The whole file first — nothing loads until all of it is valid (read again: it may have
        #    been edited since the list was built).
        try:
            candidate = Load_Configuration(item.data(Qt.UserRole))
        except Configuration_Error_Cls as error:
            message = 'Configuration was not loaded. %s' % error
            self.__Show_Result(message, ok=False)
            self.Load_Refused.emit(message)
            return

        # 2\ One hardware per run: the run summary is filed under the hardware chosen at startup.
        if candidate.Hardware != self.__config.Hardware:
            message = ("Configuration was not loaded. '%s' is for other hardware; start AnyScan with "
                       '--config %s to use it.' % (candidate.Identity.Display_Name, candidate.Path))
            self.__Show_Result(message, ok=False)
            self.Load_Refused.emit(message)
            return

        # 3\ One station-event directory per run: the launcher exports this run's log to the startup
        #    configuration's at close, so a mode naming another could not take effect.
        if candidate.Station_Events_Directory != self.__config.Station_Events_Directory:
            message = ("Configuration was not loaded. '%s' exports station events to %s, but this run exports "
                       'them to %s; start AnyScan with --config %s to use it.'
                       % (candidate.Identity.Display_Name, candidate.Station_Events_Directory,
                          self.__config.Station_Events_Directory, candidate.Path))
            self.__Show_Result(message, ok=False)
            self.Load_Refused.emit(message)
            return

        # 4\ The models, off the GUI thread.
        self.__candidate = candidate
        self.__label_stage.setText('Loading configuration…')
        self.__Set_Busy(True)
        self.Load_Started.emit()
        self.__thread = QThread(self)
        self.__worker = Model_Load_Worker_Cls(self.__vision, candidate)
        self.__worker.moveToThread(self.__thread)
        self.__thread.started.connect(self.__worker.Run)
        # The loader's own phases ('Loading segmenter…', 'Loading model…', 'Warming up…', and on a
        # failed load 'Reloading the previous configuration…') replace the opening line as they
        # happen, so a nine-second load visibly moves instead of looking hung.
        self.__worker.Stage_Changed.connect(self.__label_stage.setText)
        self.__worker.Load_Finished.connect(self.__On_Load_Finished)
        self.__worker.Load_Failed.connect(self.__On_Load_Failed)
        self.__worker.Load_Finished.connect(self.__thread.quit)
        self.__worker.Load_Failed.connect(self.__thread.quit)
        self.__thread.finished.connect(self.__worker.deleteLater)
        self.__thread.finished.connect(self.__thread.deleteLater)
        self.__thread.start()

    def __On_Load_Finished(self, seconds: float) -> None:
        """
        Description:
            The configuration is loaded: say what it is, in a sentence, and stay open — the
            operator closes the dialog when they have read it.

        Args:
            (1) seconds [float]: How long the load took (passed on for the log).
        """

        candidate, self.__candidate = self.__candidate, None
        Join_Worker_Thread(self.__thread)                   # before the references go: Join_Worker_Thread
        self.__thread = self.__worker = None
        self.__Set_Busy(False)
        self.__config = candidate
        self.Configuration_Loaded.emit(candidate, seconds)
        self.__Populate(log=False)                        # the marker moves; LOAD has nothing to do
        self.__Show_Result('Configuration loaded. %s' % Describe_Configuration(candidate), ok=True)

    def __On_Load_Failed(self, message: str) -> None:
        """
        Description:
            The models could not be loaded; the previous configuration is in force (the message,
            from Vision_Pipeline_Cls.Configure, names it and says whether its models were reloaded).

        Args:
            (1) message [string]: The failure sentence.
        """

        self.__candidate = None
        Join_Worker_Thread(self.__thread)                   # before the references go: Join_Worker_Thread
        self.__thread = self.__worker = None
        self.__Set_Busy(False)
        self.__Show_Result('Configuration was not loaded. %s' % message, ok=False)
        self.Load_Failed.emit(message)

    # << QT OVERRIDE >> #
    def reject(self) -> None:
        """
        Description:
            Close — but not while models load: the worker must finish and report first.
        """

        if not self.Loading:
            super().reject()

    # << QT OVERRIDE >> #
    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Description:
            Refuse the window-close button while models load, for the same reason as reject.

        Args:
            (1) event [QCloseEvent(object)]: The Qt close event.
        """

        if self.Loading:
            event.ignore()
        else:
            super().closeEvent(event)
