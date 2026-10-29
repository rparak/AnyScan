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
# File Name: example_app.py
## =========================================================================== ##

# System (Default)
import argparse
import os
import sys
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QStackedWidget, QScrollArea, QFrame)
# JIC_SF_UI: the style package (copied next to this file by scripts/scaffold.py)
from JIC_SF_UI import Style, Qss, Theme
from JIC_SF_UI.Style import Font
from JIC_SF_UI.Widgets import (Card_Cls, Card_Head_Cls, State_Marker_Cls, Viewport_Cls, Tool_Button_Cls,
                               Label_Pill_Cls, Status_Pill_Cls, Status_Strip_Cls, Logo_Lockup_Cls, Header_Cls, Funding_Row_Cls,
                               Meta_Row)
from JIC_SF_UI.Charts import Line_Chart_Cls, Series_Str, Guide_Str, Chart_Card, CONST_GUIDE_DASH_LONG, \
    CONST_GUIDE_DASH_SHORT

"""
Description:
    Initialization of constants.

    A minimal window in the JIC Smart Factory style, to start a new PyQt5 project from: the header (product lockup,
    rule, JIC Smart Factory logo, view tabs, status pills), a Live page with two cards (an image card with its state
    marker, empty view and action row; a reading card with a badge row, state lines and meta rows), a Trends page with
    one chart card, the status strip and the funding band. Replace the product constants below; keep the rest.

    Run:  python example_app.py                       (a window)
          python example_app.py --view trends --screenshot out.png   (offscreen grab, then exit)
          QT_SCALE_FACTOR=2 python example_app.py --screenshot out@2x.png   (the same at DPR 2)
          python example_app.py --demo-frame --state analysis   (the analysis grid over a synthetic frame)
"""
# THE PRODUCT. EXAMPLE ONLY: AnyScan's logo stands in to show how a lockup is built (the tagline-less outlined logo plus
# the tagline as live text at the logo's own position and size). A new product replaces all six with its own logo's
# values and never ships AnyScan's logo (assets/logos/USAGE.md).
#   Unit [string] / [string] / [Vector<float> 1x2] / [float] / [float] / [float]
CONST_PRODUCT_LOGO = 'anyscan-logo-wordmark.svg'
CONST_PRODUCT_MARK = 'anyscan-mark.svg'
CONST_TAGLINE = 'The camera sees, the model describes.'
CONST_TAGLINE_ORIGIN = (166.69, 128.0)
CONST_TAGLINE_SIZE = 24.55
CONST_LOGO_VIEWBOX_HEIGHT = 140.0
CONST_LOGO_MARK_RIGHT = 152.0
CONST_LOGO_MARK_THIN_PX = 0.0
CONST_PRODUCT_NAME = 'AnyScan'

# The header's view tabs, and the stack page each one shows.
#   Unit [Vector<Tuple<string> 1x2>]
CONST_VIEWS = (('live', 'Live'), ('trends', 'Trends'))


class Example_Window_Cls(QMainWindow):
    """
    Description:
        The example window. It holds no application logic: a real project drives the same widgets from its workers.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('%s  ·  %s' % (CONST_PRODUCT_NAME, CONST_TAGLINE))

        root = QWidget()
        root.setObjectName('root')
        root.setStyleSheet(Qss.Root('root'))
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(Style.CONST_PAGE_MARGIN, 0, Style.CONST_PAGE_MARGIN, Style.CONST_PAGE_MARGIN)
        outer.setSpacing(0)

        # The header: the lockup is taller on a 1x display so its live tagline reaches the 9 pt floor.
        height = Style.Logo_Height(root, CONST_TAGLINE_SIZE, CONST_LOGO_VIEWBOX_HEIGHT)
        lockup = Logo_Lockup_Cls(CONST_PRODUCT_LOGO, height, CONST_TAGLINE, CONST_TAGLINE_ORIGIN, CONST_TAGLINE_SIZE,
                                 CONST_LOGO_MARK_RIGHT, CONST_LOGO_MARK_THIN_PX)
        self.camera_pill = Label_Pill_Cls('●  Camera offline')
        self.model_pill = Status_Pill_Cls('○  Configuration not loaded.', icon='model', name=Style.CONST_NO_VALUE)
        self.model_pill.Set_State('○  Configuration not loaded.', Style.CONST_CONTROL_BORDER, Style.CONST_INK_MUTE,
                                  'dashed')
        self.header = Header_Cls(lockup, CONST_VIEWS, [self.camera_pill, self.model_pill])
        outer.addWidget(self.header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.__Build_Live())
        self.stack.addWidget(self.__Build_Trends())
        self.header.tabs.Segment_Selected.connect(self.Show_View)

        grid = QGridLayout()
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.stack, 0, 0)
        grid.setRowStretch(0, 1)
        self.status = Status_Strip_Cls([('camera', 'Camera', 'state'), ('resolution', 'Resolution', 'mono'),
                                        ('system', 'System', 'state'), ('updated', 'Last update', 'mono'),
                                        ('images', 'Images analysed', 'count'), ('objects', 'Objects detected', 'count'),
                                        ('inference', 'Inference (run median)', 'mono'),
                                        ('confidence', 'Confidence (run mean)', 'mono')])
        # Each cell as wide as the widest value it can show, so a change of value never moves a column.
        cells, dash = self.status.cells, Style.CONST_NO_VALUE
        cells['camera'].Reserve_Width(('Connecting…', 'Connected', 'Disconnected'), dot=True)
        cells['system'].Reserve_Width((dash, 'Analysis failed', 'Error logged', '9999 errors logged',
                                       'Models not loaded', 'Camera disconnected', 'Ready'), dot=True)
        cells['resolution'].Reserve_Width((dash, '9999 × 9999'))
        cells['updated'].Reserve_Width((dash, '23:59:59'))
        cells['images'].Reserve_Width(('9999',))
        cells['objects'].Reserve_Width(('9999',))
        cells['inference'].Reserve_Width((dash, '99999 ms'))
        cells['confidence'].Reserve_Width((dash, '100%'), weights=sorted(set(Style.CONST_LEVEL_WEIGHTS.values())))
        # Sample figures, consistent with the sample run the Trends page draws (8 images, 22 objects).
        self.status.cells['camera'].Set_Value('Disconnected', Style.CONST_INK_MUTE, Style.CONST_INK_MUTE)
        self.status.cells['system'].Set_Value('Models not loaded', Style.CONST_WARN, Style.CONST_WARN)
        self.status.cells['images'].Set_Value('8')
        self.status.cells['objects'].Set_Value('22')
        self.status.cells['inference'].Set_Value('712 ms')
        self.status.cells['confidence'].Set_Value('90%')
        grid.addWidget(self.status, 1, 0)
        grid.addWidget(Funding_Row_Cls(), 2, 0)
        outer.addLayout(grid, 1)

    def __Build_Live(self) -> QWidget:
        """
        Description:
            The Live page: the image card (55 %) and the reading card (45 %), side by side.

        Returns:
            (1) parameter [QWidget(object)]: The page.
        """

        page = QWidget()
        grid = QGridLayout(page)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)

        card = Card_Cls()
        head = Card_Head_Cls('camera', 'Camera View', 'No frame')
        self.frame_badge = head.badge
        self.marker = State_Marker_Cls()
        head.box.insertWidget(2, self.marker)
        head.box.insertSpacing(2, 6)
        card.box.addWidget(head)
        self.viewport = Viewport_Cls(CONST_PRODUCT_MARK, 'Connect a camera, then press Scan to capture a frame.')
        self.viewport.Marker_Changed.connect(self.marker.Set_State)
        card.box.addWidget(self.viewport, 1)
        bar = QHBoxLayout()
        bar.setSpacing(12)
        bar.setContentsMargins(0, 16, 0, 0)
        self.buttons = {}
        for key, primary, enabled in (('configuration', False, True), ('connect', False, False),
                                      ('scan', False, False), ('analyze', True, False), ('clear', False, True)):
            button = Tool_Button_Cls(key, primary=primary)
            button.setEnabled(enabled)
            self.buttons[key] = button
            bar.addWidget(button)
        card.box.addLayout(bar)
        grid.addWidget(card, 0, 0)

        reading = Card_Cls()
        head = Card_Head_Cls('text', 'Scene Understanding', badge_row=True)
        head.badges.Set_Badges([('NOK · 1', 'fail'), ('Warning · 1', 'warn')])
        reading.box.addWidget(head)
        body = QWidget()
        body.setStyleSheet('background: transparent;')
        col = QVBoxLayout(body)
        col.setContentsMargins(18, 18, 18, 16)
        col.setSpacing(16)
        lead = QLabel('Two objects lie on the table.')
        lead.setFont(Font(Style.CONST_TYPE_HEADING))
        lead.setWordWrap(True)
        lead.setStyleSheet('color: %s;' % Style.CONST_INK)
        col.addWidget(lead)
        for name, lines, description in (
                ('Object 1', ['State: NOK.', 'Reason: There are two stains on the machined front.'],
                 'A rectangular aluminium plate with four holes.'),
                ('Object 2', ['State: Warning – Outside area.',
                              'Reason: It lies outside the inspection area, so it is not judged: move it fully '
                              'inside the area and scan again.'], 'A plate near the table’s edge.')):
            block = QVBoxLayout()
            block.setSpacing(3)
            label = QLabel(name)
            label.setFont(Font(Style.CONST_TYPE_HEADING, QFont.DemiBold))
            label.setStyleSheet('color: %s;' % Style.CONST_INK)
            block.addWidget(label)
            state = QLabel('\n'.join(lines))
            state.setFont(Font(Style.CONST_TYPE_BODY, QFont.DemiBold))
            state.setWordWrap(True)
            state.setStyleSheet('color: %s;' % Style.CONST_INK)
            block.addWidget(state)
            text = QLabel(description)
            text.setFont(Font(Style.CONST_TYPE_BODY))
            text.setWordWrap(True)
            text.setStyleSheet('color: %s;' % Style.CONST_INK)
            block.addWidget(text)
            col.addLayout(block)
        col.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(Style.Scroll_Style(framed=True))
        reading.box.addWidget(scroll, 1)
        meta = QVBoxLayout()
        meta.setContentsMargins(0, 10, 0, 0)
        meta.setSpacing(0)
        Meta_Row(meta, 'Task', first=True).setText('Catalogue inspection – Mounting plate')
        Meta_Row(meta, 'Inference time', mono=True).setText('712 ms')
        Meta_Row(meta, 'Confidence (mean)', mono=True).setText('93%')
        reading.box.addLayout(meta)
        grid.addWidget(reading, 0, 1)
        grid.setColumnStretch(0, 55)
        grid.setColumnStretch(1, 45)
        return page

    def __Build_Trends(self) -> QWidget:
        """
        Description:
            The Trends page: a state chart (one colour per state, the total in the muted ink) and a confidence chart
            (two neutral means, the running one derived, with two labelled threshold guides).

        Returns:
            (1) parameter [QWidget(object)]: The page.
        """

        page = QWidget()
        grid = QGridLayout(page)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        counts = [(3, 2, 1, 0), (2, 2, 0, 0), (4, 2, 1, 1), (1, 1, 0, 0), (3, 1, 1, 1), (2, 2, 0, 0), (5, 3, 1, 1),
                  (2, 1, 0, 1)]
        cumulative = [[sum(c[k] for c in counts[:i + 1]) for i in range(len(counts))] for k in range(4)]
        objects = Line_Chart_Cls('Analysed image', 'Objects (cumulative)')
        objects.Set_Data([Series_Str('Total', Style.CONST_INK_MUTE, cumulative[0]),
                          Series_Str('OK', Theme.Verdict_Color('OK')[0], cumulative[1]),
                          Series_Str('NOK', Theme.Verdict_Color('NOK')[0], cumulative[2]),
                          Series_Str('Warning', Theme.Verdict_Color('Warning')[0], cumulative[3])])
        frame = [92, 95, 88, 97, 79, 94, 86, 90]
        weights = [c[0] for c in counts]
        running = [round(sum(f * w for f, w in zip(frame[:i + 1], weights[:i + 1])) / sum(weights[:i + 1]))
                   for i in range(len(frame))]
        confidence = Line_Chart_Cls('Analysed image', 'Confidence (%)')
        confidence.Set_Data([Series_Str('Frame mean', Style.CONST_DETECTION_INK, frame),
                             Series_Str('Run mean', Style.CONST_CHART_LIGHT_INK, running, Derived=True)],
                            [Guide_Str(80, 'Warning below 80 %', CONST_GUIDE_DASH_LONG),
                             Guide_Str(60, 'Error below 60 %', CONST_GUIDE_DASH_SHORT)], y_range=(0.0, 100.0))
        grid.addWidget(Chart_Card('magnifier', 'Detected objects', 'Cumulative objects found across the run’s images.',
                                  objects), 0, 0)
        grid.addWidget(Chart_Card('gauge', 'Confidence',
                                  'The mean confidence of each image and the running mean of the run.', confidence), 1, 0)
        return page

    def Show_Demo_Frame(self) -> None:
        """
        Description:
            Put a synthetic frame (a teal surface and two grey plates, demo pixels, not theme colours) in the image
            view with an inspection area, so the frame states (the analysis grid, LIVE PREVIEW) can be seen.
        """

        frame = np.zeros((1200, 1920, 3), np.uint8)
        frame[:] = (26, 102, 81)
        frame[380:760, 360:900] = (164, 159, 167)
        frame[300:620, 1180:1760] = (150, 146, 152)
        self.viewport.Show_Image(Style.Rgb_To_Qimage(frame))
        self.viewport.Set_Inspection_Area(((1920, 1200), (240.0, 150.0, 1680.0, 1050.0)))
        self.frame_badge.setText('1920 × 1200 · RGB')

    def Show_View(self, key: str) -> None:
        """
        Description:
            Show a page; only the central area changes, never the header, the strip or the band.

        Args:
            (1) key [string]: A key of CONST_VIEWS.
        """

        self.header.tabs.Set_Selection(key)
        self.stack.setCurrentIndex([k for k, _ in CONST_VIEWS].index(key))


def main() -> None:
    parser = argparse.ArgumentParser(description='The JIC Smart Factory style example window.')
    parser.add_argument('--view', choices=[k for k, _ in CONST_VIEWS], default='live')
    parser.add_argument('--state', choices=['', 'preview', 'scan', 'analysis'], default='',
                        help='mark a state in the image card head')
    parser.add_argument('--demo-frame', action='store_true',
                        help='show a synthetic frame (the analysis grid is drawn only over a frame)')
    parser.add_argument('--screenshot', default='', help='grab the window offscreen to this PNG and exit')
    parser.add_argument('--size', default='1600x1000',
                        help='requested size; the layout\'s minimum height wins (1600x1000 gives 1600x1029 at 1x)')
    args = parser.parse_args()
    if args.screenshot:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    Style.Load_Fonts()
    window = Example_Window_Cls()
    window.Show_View(args.view)
    if args.demo_frame:
        window.Show_Demo_Frame()
    if args.state:
        if args.state == 'analysis':
            window.viewport.Start_Analysis()
        else:
            window.viewport.Set_Live(args.state)
    width, height = (int(v) for v in args.size.split('x'))
    window.resize(width, height)
    window.show()
    if args.screenshot:
        app.processEvents()
        # Mid-sweep for the analysis grid (its wave crosses in 500 ms); at once otherwise.
        delay = 300 if args.state == 'analysis' else 50
        os.makedirs(os.path.dirname(os.path.abspath(args.screenshot)), exist_ok=True)
        saved = []
        QTimer.singleShot(delay, lambda: (saved.append(window.grab().save(args.screenshot)), app.quit()))
        app.exec_()
        if not (saved and saved[0]):
            sys.exit('could not write %s' % args.screenshot)
        sys.exit(0)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
