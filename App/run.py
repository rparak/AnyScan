"""
AnyScan — Vision-Language Industrial Inspection Console
The camera sees, the model describes.

Single-file PyQt5 application reproducing the approved AnyScan web design.
Built at JIC within the EDIH-DIGIMAT project.

The console runs on real hardware only: a Basler camera for capture and the
local Florence-2 vision-language model (presented as JIC-AnyScan-VLM-v1) for
analysis. Both sit behind small interfaces — `Camera` and `VisionBackend` — so
either can be swapped in one place, but there are no synthetic backends: the
window opens without the camera or the model present and reports a usable
sentence when a real component is missing.

For coordinate checks without hardware, `--frame path/to/Image_NNN.png` loads a
real frame previously saved from this camera and runs the full pipeline on it
against the configured background reference. See FileCamera and main().

Layout targets a 1920x1080 or larger display and scales with the window.
"""

import argparse
import os
import sys
import time
from datetime import datetime

from PyQt5.QtCore import (
    QObject, QPoint, QRect, QRectF, QSize, Qt, QThread, QTimer, pyqtSignal,
)
from PyQt5.QtGui import (
    QColor, QFont, QFontDatabase, QIcon, QImage, QPainter, QPainterPath, QPen,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QApplication, QFrame, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

# The project's src/ directory holds the extracted, Qt-free domain modules
# (Parameters, Reporting, Vision, Camera). It is put on the path here so they
# import by domain name. The lightweight data structures below are imported at
# module load; the heavier domain code (Basler.Core, Utilities.Image_Processing,
# Calibration.Parameters, and torch/transformers/OpenCV) is still imported
# lazily inside BaslerCamera._open() and FlorenceVision, so the window still
# opens on a machine with neither the camera SDK nor the model runtime present.
_SRC = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# Custom Lib.: AnyScan domain — the scene-analysis result (Qt-free)
#   ../Parameters/Vision
from Parameters.Vision import Analysis_Str
# Custom Lib.: AnyScan domain — camera backends (Qt-free; Capture returns ndarray)
#   ../Camera/Core
from Camera.Core import Camera_Error_Cls, File_Camera_Cls, Basler_Camera_Cls
# Custom Lib.: AnyScan domain — vision backend (Qt-free; Analyze takes an ndarray).
# The composer, segmentation and captioning modules are now used through this
# backend, not directly by the UI.
#   ../Vision/Core
import Vision.Core as Vision_Core
from Vision.Core import Florence_Vision_Cls

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ============================================================================
# Vision configuration
#
# All of the analysis pipeline's configuration now lives with the code that reads
# it, under ../src/Vision/ and ../src/Reporting/ as CONST_*:
#   - model dir, background reference, device, detector, task label and the
#     Florence detection settings          -> Vision/Core.py
#   - segmentation thresholds              -> Vision/Utilities/Segmentation.py
#   - caption task / budget / crop upscale -> Vision/Utilities/Caption.py
#   - panel voice + caption vocabulary     -> Reporting/Core.py
# The --background flag reassigns Vision_Core.CONST_BACKGROUND_REF at startup.
# ============================================================================

# ============================================================================
# Design tokens
#
# These mirror the :root block of the web build one for one. Change a value
# here, never in a widget: a hard-coded colour further down is how a design
# system stops being one.
# ============================================================================

BG            = "#eceded"   # page background
CARD          = "#ffffff"   # card fill
CARD_BORDER   = "#e8e8ea"   # card outline
INK           = "#16181d"   # primary text, and the primary button
INK_SOFT      = "#3f434b"   # secondary text, object sentences
INK_MUTE      = "#8a8f98"   # labels, empty states, disclaimer
LINE          = "#edeef0"   # dividers

BRAND         = "#ff005c"   # EDIH-DIGIMAT magenta: object 1 and focus only
OK            = "#16a34a"   # connected, pass
OK_INK        = "#15803d"
OK_SOFT       = "#f2faf5"
OK_BORDER     = "#cfe9d8"
WARN          = "#d97706"   # degraded but working
WARN_INK      = "#b45309"
WARN_SOFT     = "#fdf8ef"
WARN_BORDER   = "#f3e2c3"

VIEWPORT      = "#1e1f21"   # the one dark surface in the console
VIEWPORT_TEXT = "#71767d"

RADIUS_CARD   = 18
RADIUS_BTN    = 11
GAP           = 16          # gap between cards, everywhere

# What an empty value slot shows. It is a placeholder, not prose: the em dash
# stays out of sentences and out of labels, and appears only where a number or
# a timestamp will later sit.
NO_VALUE      = "\u2014"

# One colour pair per detection index, shared by the frame overlay and the
# text. `box` is the stroke on the dark viewport; `ink` is a darkened twin of
# the same hue for type on white, because a saturated stroke colour set as
# 14.5px text falls below readable contrast. Same hue plus the same number is
# what keeps the mapping legible.
#
# Green, red and amber are deliberately absent: here they mean pass, fail and
# degraded. An object numbered 3 is not "the good one".
INDEX_COLORS = [
    ("#ff005c", "#b3003f"),
    ("#0ea5e9", "#0369a1"),
    ("#7c3aed", "#5b21b6"),
    ("#14b8a6", "#0f766e"),
    ("#6366f1", "#4338ca"),
    ("#d946ef", "#a21caf"),
]

FONT_UI = "Inter"       # resolved in load_fonts()
FONT_MONO = "Consolas"  # resolved in load_fonts()

TAGLINE = "The camera sees, the model describes."
# The presented model name now lives in ../src/Vision/Core.py as CONST_MODEL_NAME
# and is read off the backend as `self.vision.Name`.


def load_fonts() -> None:
    """Pick the closest available faces.

    Inter and JetBrains Mono are what the design is drawn in. Drop the .ttf
    files into assets/fonts/ and they will be used; otherwise the nearest
    system face is chosen, which shifts the metrics slightly but keeps the
    layout intact.
    """
    global FONT_UI, FONT_MONO

    font_dir = os.path.join(ASSETS, "fonts")
    if os.path.isdir(font_dir):
        for name in os.listdir(font_dir):
            if name.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(font_dir, name))

    families = set(QFontDatabase().families())
    for candidate in ("Inter", "Segoe UI Variable Display", "Segoe UI",
                      "Helvetica Neue", "Arial"):
        if candidate in families:
            FONT_UI = candidate
            break
    for candidate in ("JetBrains Mono", "Cascadia Mono", "Consolas",
                      "DejaVu Sans Mono", "Courier New"):
        if candidate in families:
            FONT_MONO = candidate
            break


def app_icon() -> QIcon:
    """The window, taskbar and Alt-Tab icon.

    Several explicit sizes are registered rather than one large pixmap: Qt
    picks the nearest and scales, and a 256px render squeezed into a 16px
    title-bar slot loses the shape entirely. Small sizes come out as a dark
    disc with a magenta ring, which is as much as 16 pixels can carry.
    """
    icon = QIcon()
    for name in ("icon.png", "anyscan-mark.png"):
        source = QPixmap(os.path.join(ASSETS, name))
        if not source.isNull():
            break
    else:
        return icon
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(source.scaled(size, size, Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation))
    return icon


def load_logo(name: str, height: int) -> QPixmap:
    """Load a logo and scale it for the display it will actually be drawn on.

    QPixmap.scaledToHeight() works in logical pixels. On a 125% or 150%
    display Qt then stretches that result up to physical pixels, which is what
    makes every logo look soft even though the source file has resolution to
    spare. Scaling to height * devicePixelRatio and tagging the pixmap with
    that ratio hands Qt the pixels it needs and it draws them one to one.
    """
    pix = QPixmap(os.path.join(ASSETS, name))
    if pix.isNull():
        return pix
    app = QApplication.instance()
    dpr = app.devicePixelRatio() if app else 1.0
    dpr = max(1.0, float(dpr))
    scaled = pix.scaledToHeight(int(round(height * dpr)),
                                Qt.SmoothTransformation)
    scaled.setDevicePixelRatio(dpr)
    return scaled


def font(size: float, weight: int = QFont.Normal, mono: bool = False,
         tracking: float = 0.0) -> QFont:
    """Build a font. `tracking` is percentage letter spacing, as in the CSS."""
    f = QFont(FONT_MONO if mono else FONT_UI)
    f.setPointSizeF(size)
    f.setWeight(weight)
    if tracking:
        f.setLetterSpacing(QFont.PercentageSpacing, 100 + tracking)
    return f


# ============================================================================
# Domain objects
#
# Detection_Str and Analysis_Str now live in ../src/Parameters/Vision.py and are
# imported at the top of this file. They are plain data carriers with no Qt.
# ============================================================================

# ============================================================================
# UI/domain boundary (ndarray <-> QImage)
#
# The camera (../src/Camera/Core.py) and the vision backend (../src/Vision/Core.py)
# are both Qt-free: a frame is a contiguous RGB ndarray, the application's exchange
# format. The one place a QImage is needed is the viewport, which paints one — so
# the ndarray -> QImage conversion lives here, on the UI side, and nowhere else.
# ============================================================================

def _rgb_to_qimage(rgb) -> QImage:
    """An RGB ndarray (H, W, 3) as a QImage for the viewport to paint.

    QImage does not own the numpy buffer: it is a view over rgb.data with a 3*w
    stride. .copy() detaches it so the frame survives rgb being garbage-collected,
    which otherwise tears the viewport or segfaults.
    """
    h, w = rgb.shape[:2]
    image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
    return image.copy()


# ============================================================================
# Widgets
# ============================================================================

def hairline(vertical=True, length=None, color=LINE):
    """A one-pixel rule.

    QFrame.VLine draws from the widget palette and ignores a stylesheet
    `color`, which is why hand-set frame lines come out the wrong shade or
    invisible. A plain filled QWidget is predictable.
    """
    line = QWidget()
    line.setObjectName("hairline")
    line.setStyleSheet("#hairline { background: %s; }" % color)
    if vertical:
        line.setFixedWidth(1)
        if length:
            line.setFixedHeight(length)
    else:
        line.setFixedHeight(1)
    return line


class Card(QFrame):
    """The white card every panel sits in."""

    def __init__(self, padding=16, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(
            "#card { background: %s; border: 1px solid %s; border-radius: %dpx; }"
            % (CARD, CARD_BORDER, RADIUS_CARD)
        )
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(padding, padding, padding, padding)
        self.box.setSpacing(0)


class Icon(QWidget):
    """The three stroked icons the card heads use.

    Hand-painted rather than shipped as files: three shapes do not justify an
    asset pipeline, and painting them keeps the stroke weight tied to the size.
    """

    def __init__(self, kind, size=22, color=INK, parent=None):
        super().__init__(parent)
        self.kind, self.color = kind, color
        self.setFixedSize(size, size)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = self.width() / 24.0
        pen = QPen(QColor(self.color), 1.7 * s)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        def r(x, y, w, h):
            return QRectF(x * s, y * s, w * s, h * s)

        if self.kind == "camera":
            p.drawRoundedRect(r(2, 6, 20, 14), 2 * s, 2 * s)
            p.drawLine(QPoint(int(9.5 * s), int(6 * s)), QPoint(int(11 * s), int(4 * s)))
            p.drawLine(QPoint(int(14.5 * s), int(6 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawLine(QPoint(int(11 * s), int(4 * s)), QPoint(int(13 * s), int(4 * s)))
            p.drawEllipse(r(8.4, 9.4, 7.2, 7.2))
        elif self.kind == "reading":
            p.drawRoundedRect(r(4, 4, 16, 16), 1.5 * s, 1.5 * s)
            p.drawLine(QPoint(int(12 * s), int(4 * s)), QPoint(int(12 * s), int(20 * s)))
            for y in (9, 12.5):
                p.drawLine(QPoint(int(7 * s), int(y * s)), QPoint(int(9.5 * s), int(y * s)))
                p.drawLine(QPoint(int(14.5 * s), int(y * s)), QPoint(int(17 * s), int(y * s)))
        elif self.kind == "cube":
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


class Badge(QLabel):
    """The verdict badge.

    Coloured by meaning, never by brand: green when objects were found, amber
    when confidence is under threshold, neutral when there is nothing to say.
    It used to be magenta, which on a light card reads as an alarm — exactly
    the wrong signal for a successful result.
    """

    def __init__(self, text="Idle", parent=None):
        super().__init__(text, parent)
        self.setFont(font(8, mono=True))
        self.setFixedHeight(24)
        self.set_level("idle")

    def set_level(self, level):
        if level == "ok":
            border, bg, fg = OK_BORDER, OK_SOFT, OK_INK
        elif level == "warn":
            border, bg, fg = WARN_BORDER, WARN_SOFT, WARN_INK
        else:
            border, bg, fg = CARD_BORDER, CARD, INK_MUTE
        self.setStyleSheet(
            "border: 1px solid %s; background: %s; color: %s;"
            "border-radius: 7px; padding: 0 9px;" % (border, bg, fg)
        )

    def set_state(self, text, level):
        self.setText(text)
        self.set_level(level)


class CardHead(QWidget):
    """Icon, title, spacer, and at most one badge."""

    def __init__(self, icon_kind, title, badge_text=None, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 2, 2, 14)
        row.setSpacing(10)
        row.addWidget(Icon(icon_kind))
        label = QLabel(title)
        label.setFont(font(15.5, QFont.Bold, tracking=-2))
        label.setStyleSheet("color: %s;" % INK)
        row.addWidget(label)
        row.addStretch(1)
        self.badge = None
        if badge_text is not None:
            self.badge = Badge(badge_text)
            row.addWidget(self.badge)


class Viewport(QWidget):
    """The camera image and the boxes drawn over it.

    The image is letterboxed inside a 16:10 area, so the overlay has to
    recompute the draw rectangle on every paint. That maths lives here and
    nowhere else — it is the single most common source of boxes that land in
    the wrong place.
    """

    MIN_ASPECT = 16 / 10.0   # never shorter than this; taller is fine

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.detections = []
        # Busy overlay. `_busy` shows the scrim and step text; `_animated` adds
        # the turning arc and is driven by `_timer`, which runs ONLY while the
        # analysis worker is busy and is stopped the moment it is not — a timer
        # left running repaints a static screen forever.
        self._busy = False
        self._busy_text = ""
        self._animated = False
        self._spin = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(BUSY_TICK_MS)
        self._timer.timeout.connect(self._tick)
        # An empty state is an instruction, so it has to describe the step the
        # operator can actually take right now. Telling a connected operator to
        # connect a camera is worse than saying nothing.
        self.empty_text = "Connect a camera, then press Scan to capture a frame."
        self.mark = QPixmap(os.path.join(ASSETS, "anyscan-mark.png"))
        # The viewport takes every pixel the card can spare and letterboxes the
        # frame inside it. An aspect-locked height would leave a white gap under
        # the image on a tall window, which reads as a layout bug rather than as
        # a camera view.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(320)

    def show_frame(self, image: QImage):
        self.image = image
        self.detections = []
        self.update()

    def show_detections(self, detections):
        self.detections = detections
        self.update()

    def clear(self):
        self.image = None
        self.detections = []
        self.update()

    def set_empty_text(self, text):
        if text != self.empty_text:
            self.empty_text = text
            self.update()

    def set_busy(self, text):
        """A static overlay for the short, GUI-thread steps (connect, scan).

        No animation is possible here: the GUI thread is about to block on the
        call, so a spinner would freeze mid-turn. processEvents forces the
        static text to paint before that block.
        """
        self._busy = bool(text)
        self._busy_text = text
        self._animated = False
        self._timer.stop()
        self.update()
        QApplication.processEvents()

    def start_busy(self, text):
        """The animated overlay for the threaded analysis.

        The worker runs off the GUI thread, so the timer's repaints are free to
        turn the arc while inference proceeds.
        """
        self._busy = True
        self._busy_text = text
        self._animated = True
        self._spin = 0.0
        if not self._timer.isActive():
            self._timer.start()
        self.update()

    def set_busy_text(self, text):
        """Update the step line without disturbing the animation."""
        self._busy_text = text
        self.update()

    def stop_busy(self):
        self._busy = False
        self._busy_text = ""
        self._animated = False
        self._timer.stop()
        self.update()

    def _tick(self):
        self._spin = (self._spin + BUSY_SPIN_DEG) % 360.0
        self.update()

    def _draw_rect(self):
        """Where the letterboxed image actually sits inside this widget."""
        if self.image is None:
            return QRect()
        scale = min(self.width() / self.image.width(),
                    self.height() / self.image.height())
        w = self.image.width() * scale
        h = self.image.height() * scale
        return QRect(int((self.width() - w) / 2), int((self.height() - h) / 2),
                     int(w), int(h))

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 8, 8)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor(VIEWPORT))

        if self.image is None:
            self._paint_empty(p)
        else:
            target = self._draw_rect()
            p.drawImage(target, self.image)
            self._paint_boxes(p, target)

        if self._busy:
            self._paint_busy(p)
        p.end()

    def _paint_busy(self, p):
        """Dim the viewport, turn an arc, and print the step underneath.

        The arc is drawn only while `_animated`; the synchronous connect/scan
        steps show the same scrim and text without it, because an arc that
        cannot turn is worse than none.
        """
        p.fillRect(self.rect(), QColor(24, 25, 27, 158))
        cx, cy = self.width() / 2.0, self.height() / 2.0

        if self._animated:
            radius = 22
            arc = QRectF(cx - radius, cy - radius - 16, radius * 2, radius * 2)
            track = QPen(QColor(255, 255, 255, 40), 3)
            track.setCapStyle(Qt.RoundCap)
            p.setPen(track)
            p.setBrush(Qt.NoBrush)
            p.drawArc(arc, 0, 360 * 16)
            head = QPen(QColor("#f2f2f3"), 3)
            head.setCapStyle(Qt.RoundCap)
            p.setPen(head)
            # Qt angles are 1/16 degree, counter-clockwise; negate to turn the
            # usual clockwise direction. A 90-degree sweep reads as a spinner.
            p.drawArc(arc, int(-self._spin * 16), 90 * 16)

        p.setPen(QColor("#f2f2f3"))
        p.setFont(font(9.5, mono=True))
        text_rect = QRect(0, int(cy + 14), self.width(), 40)
        p.drawText(text_rect, Qt.AlignHCenter | Qt.AlignTop, self._busy_text)

    def _paint_empty(self, p):
        """The project mark holds the empty state.

        The render is glossy, glowing and three-dimensional: everything this
        design is not. It is legitimate here because the viewport is the only
        dark surface in the console and the surface it was drawn for, and
        because it disappears the instant a frame arrives.
        """
        cy = self.height() // 2
        if not self.mark.isNull():
            size = min(210, int(self.width() * 0.44))
            dpr = max(1.0, float(self.devicePixelRatioF()))
            scaled = self.mark.scaled(int(size * dpr), int(size * dpr),
                                      Qt.KeepAspectRatio, Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(dpr)
            draw_w = int(scaled.width() / dpr)
            draw_h = int(scaled.height() / dpr)
            p.setOpacity(0.92)
            p.drawPixmap((self.width() - draw_w) // 2, cy - draw_h // 2 - 20, scaled)
            p.setOpacity(1.0)
            text_top = cy + draw_h // 2 - 8
        else:
            text_top = cy
        p.setPen(QColor(VIEWPORT_TEXT))
        p.setFont(font(9.5, mono=True))
        p.drawText(QRect(0, text_top, self.width(), 60), Qt.AlignHCenter | Qt.AlignTop,
                   self.empty_text)

    def _paint_boxes(self, p, target):
        if not self.detections or self.image is None:
            return
        scale = target.width() / float(self.image.width())
        p.setFont(font(9.5, QFont.DemiBold))
        metrics = p.fontMetrics()
        for i, det in enumerate(self.detections):
            box_color = QColor(INDEX_COLORS[i % len(INDEX_COLORS)][0])
            x, y, w, h = det.Bbox
            bx = target.x() + x * scale
            by = target.y() + y * scale
            p.setPen(QPen(box_color, 2.5))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(bx, by, w * scale, h * scale))

            label = "Object %d" % (i + 1)
            tw = metrics.horizontalAdvance(label) + 12
            top = max(0, by - 19)
            p.setPen(Qt.NoPen)
            p.setBrush(box_color)
            p.drawRect(QRectF(bx, top, tw, 19))
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(bx + 6, top, tw, 19), Qt.AlignVCenter, label)


class ToolButton(QPushButton):
    """48px tall, uppercase, tracked. Exactly one is primary.

    The primary is black rather than magenta: the strongest control on screen
    should read as structural, the way the black EDIH-DIGIMAT wordmark does,
    and that leaves magenta free to mean one thing only — a detected object.
    """

    def __init__(self, text, primary=False, parent=None):
        super().__init__(text, parent)
        self.setFont(font(9.5, QFont.DemiBold, tracking=6))
        self.setFixedHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if primary:
            self.setStyleSheet("""
                QPushButton { background: %s; border: 1px solid %s; color: #fff;
                              border-radius: %dpx; }
                QPushButton:hover:enabled { background: #2c3038; border-color: #2c3038; }
                QPushButton:pressed:enabled { background: #000; border-color: #000; }
                QPushButton:disabled { background: #c9cacd; border-color: #c9cacd;
                                       color: #f2f2f3; }
            """ % (INK, INK, RADIUS_BTN))
        else:
            self.setStyleSheet("""
                QPushButton { background: #fff; border: 1px solid #e4e5e7; color: %s;
                              border-radius: %dpx; }
                QPushButton:hover:enabled { background: #f7f7f8; border-color: #d8d9dc; }
                QPushButton:disabled { color: #b9bbbf; border-color: #eceded; }
            """ % (INK, RADIUS_BTN))


class ObjectList(QWidget):
    """The numbered lines, each keyed by colour to its box on the frame."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(0, 0, 0, 0)
        self.box.setSpacing(13)

    def set_objects(self, objects):
        while self.box.count():
            item = self.box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, det in enumerate(objects):
            ink = INDEX_COLORS[i % len(INDEX_COLORS)][1]
            line = QLabel(
                '<span style="color:%s"><b>Object %d:</b></span> '
                '<span style="color:%s">%s</span>' % (ink, i + 1, INK_SOFT, det.Sentence)
            )
            line.setFont(font(15))
            line.setWordWrap(True)
            line.setTextFormat(Qt.RichText)
            line.setStyleSheet(
                "border-left: 2px solid %s; padding-left: 13px;" % ink
            )
            self.box.addWidget(line)


class StatCell(QWidget):
    """One cell of the status strip.

    The two counts are larger than the four states, because in a demo the
    counts are read from the back of the room and the states by the person at
    the keyboard.
    """

    def __init__(self, label, value="", big=False, dot=False, mono=False, parent=None):
        super().__init__(parent)
        self.dot = dot
        col = QVBoxLayout(self)
        col.setContentsMargins(20, 13, 20, 13)
        col.setSpacing(5)

        self.label = QLabel(label.upper())
        self.label.setFont(font(8, QFont.Bold, tracking=7))
        self.label.setStyleSheet("color: %s;" % INK_MUTE)
        col.addWidget(self.label)

        self.value = QLabel(value)
        if big:
            # still the loudest thing in the strip, just no longer shouting
            self.value.setFont(font(18, QFont.Bold, tracking=-4))
        elif mono:
            self.value.setFont(font(12, QFont.Medium, mono=True))
        else:
            self.value.setFont(font(13.5, QFont.DemiBold, tracking=-2))
        self.value.setStyleSheet("color: %s;" % INK)
        col.addWidget(self.value)
        col.addStretch(1)
        self._color = INK

    def set_value(self, text, color=None, dot_color=None):
        self._dot_color = dot_color
        self.value.setStyleSheet("color: %s;" % (color or INK))
        self.value.setText(("\u25cf  " if dot_color else "") + text)
        if dot_color:
            self.value.setText(
                '<span style="color:%s">\u25cf</span>&nbsp;&nbsp;'
                '<span style="color:%s">%s</span>' % (dot_color, color or INK, text)
            )
            self.value.setTextFormat(Qt.RichText)


class StatusStrip(Card):
    """Six hairline-divided cells across the full width."""

    def __init__(self, parent=None):
        super().__init__(padding=0, parent=parent)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        self.camera = StatCell("Camera", "Disconnected", dot=True)
        self.resolution = StatCell("Resolution", NO_VALUE, mono=True)
        self.system = StatCell("System", "Ready", dot=True)
        self.updated = StatCell("Last update", NO_VALUE, mono=True)
        self.images = StatCell("Images analysed", "0", big=True)
        self.objects = StatCell("Objects detected", "0", big=True)

        for i, cell in enumerate([self.camera, self.resolution, self.system,
                                  self.updated, self.images, self.objects]):
            if i:
                row.addWidget(hairline(vertical=True))
            row.addWidget(cell, 1)

        self.box.addLayout(row)
        self.camera.set_value("Disconnected", INK_MUTE, INK_MUTE)
        self.system.set_value("Ready", OK, OK)


class FundingRow(Card):
    """The project and funding obligation, as part of the product.

    Logo heights are set per logo, never globally: a wordmark and a three-line
    institutional block cannot share one height and stay optically equal.
    Before adding a logo, check its content box — several of these files ship
    with most of the canvas empty and render far smaller than the height
    suggests.
    """

    LOGOS = [
        ("edih-digimat-dark.png", 21),
        (None, 0),                       # hairline divider
        ("partner-ministry.png", 34),
        ("funder-eu.png", 31),
    ]

    DISCLAIMER = (
        "Funded by the European Union. Views and opinions expressed are however those "
        "of the author(s) only and do not necessarily reflect those of the European "
        "Union or European Commission. Neither the European Union nor the granting "
        "authority can be held responsible for them."
    )

    def __init__(self, parent=None):
        super().__init__(padding=16, parent=parent)
        row = QHBoxLayout()
        row.setSpacing(32)
        row.addStretch(1)
        for name, height in self.LOGOS:
            if name is None:
                row.addWidget(hairline(vertical=True, length=30))
                continue
            pix = load_logo(name, height)
            label = QLabel()
            if not pix.isNull():
                label.setPixmap(pix)
            else:
                label.setText(name)  # missing asset should be visible, not silent
                label.setStyleSheet("color: %s;" % INK_MUTE)
            row.addWidget(label)
        row.addStretch(1)
        self.box.addLayout(row)

        self.box.addSpacing(13)
        self.box.addWidget(hairline(vertical=False))

        # The disclaimer runs the full width rather than wrapping into a
        # four-line block: the same words, a third of the height, and the
        # space goes back to the two panels that matter.
        note = QLabel(self.DISCLAIMER)
        note.setFont(font(8))
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color: %s; padding-top: 10px;" % INK_MUTE)
        self.box.addWidget(note)


# ============================================================================
# Main window
# ============================================================================

class AnalysisWorker(QObject):
    """Runs one analysis off the GUI thread.

    The Florence-2 pipeline takes seconds; on the GUI thread it would freeze the
    window and the busy animation with it. This object is moved onto a QThread,
    reports progress per crop, and hands back the finished Analysis — or a
    failure sentence — through queued signals.
    """

    stage = pyqtSignal(str)         # phase text: "Loading model…", "Segmenting…"
    progress = pyqtSignal(int, int)  # (objects done, total)
    finished = pyqtSignal(object)    # the Analysis
    failed = pyqtSignal(str)         # an actionable sentence for the panel

    def __init__(self, vision, image):
        super().__init__()
        self._vision = vision
        self._image = image

    def run(self):
        try:
            # self._image is already the RGB ndarray the camera captured (the
            # exchange format); the Qt-free backend takes it directly.
            result = self._vision.Analyze(
                self._image,
                progress_cb=lambda done, total: self.progress.emit(done, total),
                stage_cb=lambda text: self.stage.emit(text),
            )
        except Exception as exc:                          # noqa: BLE001
            # Every failure is a sentence the operator can act on; the panel
            # prints it verbatim.
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)


class ConnectWorker(QObject):
    """Opens the camera off the GUI thread.

    A Basler CONNECT enumerates the device, configures it and reads the sensor
    size — seconds of blocking work that would freeze the window and its loading
    animation. Moved onto a QThread, it reports only done-or-failed; the sensor
    size is read back on the GUI thread once it succeeds.
    """

    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, camera):
        super().__init__()
        self._camera = camera

    def run(self):
        try:
            self._camera.Connect()
        except Exception as exc:                          # noqa: BLE001
            self.failed.emit(str(exc))
        else:
            self.finished.emit()


class AnyScanWindow(QMainWindow):

    # The reading panel says what to do next, which depends on how far the
    # operator has got. One fixed sentence is wrong in two of the three states.
    READING_DISCONNECTED = ("Connect a camera and scan a frame, then press Analyze. "
                            "The model\u2019s reading of the scene appears here as "
                            "plain English text.")
    READING_NO_FRAME = ("Press Scan to capture a frame, then Analyze. The model\u2019s "
                        "reading of the scene appears here as plain English text.")
    READING_HAS_FRAME = ("Frame captured. Press Analyze to read the scene. The result "
                         "appears here as plain English text.")

    def __init__(self, camera=None):
        super().__init__()
        self.setWindowTitle("AnyScan  \u00b7  %s" % TAGLINE)

        # One real implementation each. `camera` is injected so the developer
        # --frame path can supply a FileCamera; production is the Basler.
        self.camera = camera if camera is not None else Basler_Camera_Cls()
        self.vision = Florence_Vision_Cls()

        self.frame = None
        self.analyses = 0
        self.objects_found = 0
        # while an error is on screen, the prompts must not overwrite it
        self._showing_error = False
        # analysis worker plumbing; None when idle
        self._thread = None
        self._worker = None
        self._worker_running = False
        # camera-connect worker plumbing; None when idle
        self._conn_thread = None
        self._conn_worker = None

        self._build_ui()
        self._sync_controls()

    # ---------------------------------------------------------------- layout

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        # An id selector, never a bare `background:` — a bare declaration here
        # cascades into every child widget and paints grey blocks behind the
        # card titles and the disclaimer.
        root.setStyleSheet("#root { background: %s; }" % BG)
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 0, 18, 18)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())

        grid = QGridLayout()
        grid.setSpacing(GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self._build_camera_card(), 0, 0)
        grid.addWidget(self._build_reading_card(), 0, 1)
        grid.setColumnStretch(0, 55)   # the frame is always the widest element
        grid.setColumnStretch(1, 45)
        grid.setRowStretch(0, 1)       # spare height goes to the reading panel

        self.status = StatusStrip()
        grid.addWidget(self.status, 1, 0, 1, 2)
        grid.addWidget(FundingRow(), 2, 0, 1, 2)

        # The console runs on a monitor at the station, so it fills the window.
        # Only the reading column is capped, further down: sentences set 1700px
        # wide are technically visible and practically unreadable.
        outer.addLayout(grid, 1)

    def _build_topbar(self):
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(4, 20, 4, 18)
        row.setSpacing(16)

        logo = QLabel()
        logo.setPixmap(load_logo("brand-jic.png", 26))
        row.addWidget(logo)
        row.addWidget(self._rule(26))

        name = QLabel("AnyScan")
        name.setFont(font(15.5, QFont.Bold, tracking=-3.5))
        name.setStyleSheet("color: %s;" % INK)
        row.addWidget(name)

        row.addWidget(self._rule(24))

        # The sentence is large enough to read across a room and light enough
        # not to compete with the name: weight and colour do the separating,
        # not size alone.
        tag = QLabel(TAGLINE)
        tag.setFont(font(12.5))
        tag.setStyleSheet("color: %s;" % INK_SOFT)
        row.addWidget(tag)

        row.addStretch(1)

        self.pill_camera = self._pill("Camera offline", dot=True)
        row.addWidget(self.pill_camera)

        model_pill = QWidget()
        model_pill.setObjectName("modelPill")
        model_pill.setFixedHeight(31)
        model_pill.setStyleSheet(
            "#modelPill { border: 1px solid %s; border-radius: 15px; }" % CARD_BORDER)
        pill_row = QHBoxLayout(model_pill)
        pill_row.setContentsMargins(12, 0, 12, 0)
        pill_row.setSpacing(7)
        pill_row.addWidget(Icon("cube", 15, INK_MUTE))
        model_label = QLabel(self.vision.Name)
        model_label.setFont(font(9, QFont.DemiBold))
        model_label.setStyleSheet("color: %s;" % INK_MUTE)
        pill_row.addWidget(model_label)
        row.addWidget(model_pill)
        return bar

    def _rule(self, height):
        return hairline(vertical=True, length=height, color="#d9dadd")

    def _pill(self, text, dot=False):
        pill = QLabel(("\u25cf  " if dot else "") + text)
        pill.setFont(font(9, QFont.DemiBold))
        pill.setFixedHeight(31)
        pill.setStyleSheet(
            "border: 1px solid %s; background: %s; color: %s;"
            "border-radius: 15px; padding: 0 12px;" % (CARD_BORDER, CARD, INK_MUTE)
        )
        return pill

    def _build_camera_card(self):
        card = Card()
        head = CardHead("camera", "Camera View", "No frame")
        self.frame_badge = head.badge
        card.box.addWidget(head)

        self.viewport = Viewport()
        card.box.addWidget(self.viewport, 1)

        bar = QHBoxLayout()
        bar.setSpacing(12)
        bar.setContentsMargins(0, 16, 0, 0)
        self.btn_connect = ToolButton("CONNECT")
        self.btn_disconnect = ToolButton("DISCONNECT")
        self.btn_scan = ToolButton("SCAN")
        self.btn_analyze = ToolButton("ANALYZE", primary=True)
        self.btn_clear = ToolButton("CLEAR")
        for b in (self.btn_connect, self.btn_disconnect, self.btn_scan,
                  self.btn_analyze, self.btn_clear):
            bar.addWidget(b)
        card.box.addLayout(bar)

        self.btn_connect.clicked.connect(self.on_connect)
        self.btn_disconnect.clicked.connect(self.on_disconnect)
        self.btn_scan.clicked.connect(self.on_scan)
        self.btn_analyze.clicked.connect(self.on_analyze)
        self.btn_clear.clicked.connect(self.on_clear)
        return card

    def _build_reading_card(self):
        card = Card()
        head = CardHead("reading", "Scene Understanding", "Idle")
        self.stage_badge = head.badge
        card.box.addWidget(head)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        col = QVBoxLayout(body)
        col.setContentsMargins(18, 18, 18, 16)
        col.setSpacing(0)

        self.reading_empty = QLabel(self.READING_DISCONNECTED)
        self.reading_empty.setFont(font(11.5))
        self.reading_empty.setWordWrap(True)
        self.reading_empty.setAlignment(Qt.AlignTop)
        self.reading_empty.setStyleSheet("color: %s;" % INK_MUTE)
        col.addWidget(self.reading_empty)

        self.reading_lead = QLabel()
        self.reading_lead.setFont(font(16.5, QFont.DemiBold, tracking=-1.5))
        self.reading_lead.setWordWrap(True)
        self.reading_lead.setStyleSheet("color: %s; padding-bottom: 14px;" % INK)
        self.reading_lead.hide()
        col.addWidget(self.reading_lead)

        self.object_list = ObjectList()
        col.addWidget(self.object_list)

        self.reading_note = QLabel()
        self.reading_note.setFont(font(11.5))
        self.reading_note.setWordWrap(True)
        self.reading_note.setStyleSheet(
            "color: %s; border-top: 1px solid %s; padding-top: 15px;"
            "margin-top: 18px;" % (INK_MUTE, LINE)
        )
        self.reading_note.hide()
        col.addWidget(self.reading_note)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(body)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMinimumHeight(320)
        scroll.setStyleSheet("""
            QScrollArea { border: 1px solid #ececee; border-radius: 10px;
                          background: %s; }
            QScrollBar:vertical { background: transparent; width: 9px; margin: 6px 3px; }
            QScrollBar::handle:vertical { background: #c9cacd; border-radius: 4px;
                                          min-height: 30px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent; }
        """ % CARD)
        card.box.addWidget(scroll, 1)

        meta = QVBoxLayout()
        meta.setContentsMargins(0, 10, 0, 0)
        meta.setSpacing(0)
        self.meta_task = self._meta_row(meta, "Task", first=True)
        self.meta_objects = self._meta_row(meta, "Objects found")
        self.meta_latency = self._meta_row(meta, "Inference time", mono=True)
        card.box.addLayout(meta)
        return card

    def _meta_row(self, parent_layout, key, mono=False, first=False):
        row = QWidget()
        if not first:
            row.setStyleSheet("border-top: 1px solid %s;" % LINE)
        line = QHBoxLayout(row)
        line.setContentsMargins(2, 9, 2, 9)
        label = QLabel(key)
        label.setFont(font(10))
        label.setStyleSheet("color: %s; border: none;" % INK_SOFT)
        line.addWidget(label)
        line.addStretch(1)
        value = QLabel(NO_VALUE)
        value.setFont(font(9 if mono else 10, QFont.Medium, mono=mono))
        value.setStyleSheet("color: %s; border: none;" % INK)
        line.addWidget(value)
        parent_layout.addWidget(row)
        return value

    # --------------------------------------------------------------- actions

    def _prompt_text(self):
        if self.frame is not None:
            return self.READING_HAS_FRAME
        return self.READING_NO_FRAME if self.camera.Connected else self.READING_DISCONNECTED

    def _sync_prompts(self):
        """Point both empty states at the step that is actually available."""
        self.viewport.set_empty_text(
            "Press Scan to capture a frame." if self.camera.Connected
            else "Connect a camera, then press Scan to capture a frame."
        )
        if not self._showing_error and not self.reading_empty.isHidden():
            self.reading_empty.setText(self._prompt_text())

    def _sync_controls(self):
        connected = self.camera.Connected
        # While the worker runs, every control is disabled: a second ANALYZE
        # must not start on top of the first, and connect/scan/clear would pull
        # the frame out from under it.
        running = self._worker_running
        self.btn_connect.setEnabled(not connected and not running)
        self.btn_disconnect.setEnabled(connected and not running)
        self.btn_scan.setEnabled(connected and not running)
        self.btn_analyze.setEnabled(self.frame is not None and not running)
        self.btn_clear.setEnabled(not running)

        if connected:
            self.pill_camera.setText("\u25cf  Camera live")
            self.pill_camera.setStyleSheet(
                "border: 1px solid %s; background: %s; color: %s;"
                "border-radius: 15px; padding: 0 12px;" % (OK_BORDER, CARD, OK))
        else:
            self.pill_camera.setText("\u25cf  Camera offline")
            self.pill_camera.setStyleSheet(
                "border: 1px solid %s; background: %s; color: %s;"
                "border-radius: 15px; padding: 0 12px;" % (CARD_BORDER, CARD, INK_MUTE))
        self._sync_prompts()

    def _fail(self, message):
        """A failure has to be visible where the operator is already looking."""
        self._showing_error = True
        self.stage_badge.set_state("Error", "warn")
        self.reading_empty.setText(message)
        self.reading_empty.show()
        self.reading_lead.hide()
        self.reading_note.hide()
        self.object_list.set_objects([])
        print("[ERROR] %s" % message)

    def on_connect(self):
        if self._worker_running or self.camera.Connected:
            return

        # Open the camera on its own thread so the loading indicator turns and
        # the window stays responsive through the (seconds-long) Basler handshake.
        self._worker_running = True
        self._showing_error = False
        self.status.camera.set_value("Connecting\u2026", WARN, WARN)
        self.viewport.start_busy("Connecting to camera\u2026")
        self._sync_controls()

        self._conn_thread = QThread(self)
        self._conn_worker = ConnectWorker(self.camera)
        self._conn_worker.moveToThread(self._conn_thread)

        self._conn_thread.started.connect(self._conn_worker.run)
        self._conn_worker.finished.connect(self._on_connect_ok)
        self._conn_worker.failed.connect(self._on_connect_fail)

        self._conn_worker.finished.connect(self._conn_thread.quit)
        self._conn_worker.failed.connect(self._conn_thread.quit)
        self._conn_thread.finished.connect(self._conn_worker.deleteLater)
        self._conn_thread.finished.connect(self._conn_thread.deleteLater)

        self._conn_thread.start()

    def _on_connect_ok(self):
        self._worker_running = False
        self._conn_thread = None
        self._conn_worker = None
        self.viewport.stop_busy()
        w, h = self.camera.Resolution
        self.status.camera.set_value("Connected", OK, OK)
        self.status.resolution.set_value("%d \u00d7 %d" % (w, h))
        self._sync_controls()

    def _on_connect_fail(self, message):
        self._worker_running = False
        self._conn_thread = None
        self._conn_worker = None
        self.viewport.stop_busy()
        self.status.camera.set_value("Disconnected", INK_MUTE, INK_MUTE)
        self._fail(message)
        self._sync_controls()

    def on_disconnect(self):
        self.camera.Disconnect()
        self.frame = None
        self.viewport.clear()
        self.frame_badge.setText("No frame")
        self.status.camera.set_value("Disconnected", INK_MUTE, INK_MUTE)
        self.status.resolution.set_value(NO_VALUE)
        self._sync_controls()

    def on_scan(self):
        try:
            self.viewport.set_busy("Capturing frame\u2026")
            self.frame = self.camera.Capture()
        except Camera_Error_Cls as exc:
            self._fail(str(exc))
        else:
            self.viewport.show_frame(_rgb_to_qimage(self.frame))
            self.frame_badge.setText("%d \u00d7 %d \u00b7 RGB"
                                     % (self.frame.shape[1], self.frame.shape[0]))
            self.status.updated.set_value(datetime.now().strftime("%H:%M:%S"))
            self._clear_reading()
        finally:
            self.viewport.set_busy("")
            self._sync_controls()

    def on_analyze(self):
        if self.frame is None or self._worker_running:
            return

        # Hand the analysis to a worker on its own thread and drive the animated
        # indicator from here. Nothing blocks the GUI thread, so the arc turns
        # for the whole duration.
        self._worker_running = True
        self._showing_error = False
        self.viewport.start_busy("Preparing\u2026")
        self._sync_controls()

        self._thread = QThread(self)
        self._worker = AnalysisWorker(self.vision, self.frame)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.stage.connect(self.viewport.set_busy_text)
        self._worker.progress.connect(self._on_analysis_progress)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.failed.connect(self._on_analysis_failed)

        # Tear the thread down once the worker is done, whichever way it ended.
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_analysis_progress(self, done, total):
        # `done` is the number completed; the one being read is done + 1.
        current = min(done + 1, total)
        self.viewport.set_busy_text("Analysing object %d of %d\u2026" % (current, total))

    def _on_analysis_finished(self, result):
        self._worker_running = False
        self._thread = None
        self._worker = None
        self.viewport.stop_busy()
        self._show_analysis(result)
        self._sync_controls()

    def _on_analysis_failed(self, message):
        self._worker_running = False
        self._thread = None
        self._worker = None
        self.viewport.stop_busy()
        self._fail(message)
        self._sync_controls()

    def _show_analysis(self, result: Analysis_Str):
        self._showing_error = False
        self.reading_empty.hide()
        self.reading_lead.setText(result.Summary)
        self.reading_lead.show()
        self.object_list.set_objects(result.Objects)
        self.reading_note.setText(result.Note)
        self.reading_note.setVisible(bool(result.Note))

        self.viewport.show_detections(result.Objects)
        self.stage_badge.set_state(result.Verdict, result.Verdict_Level)

        self.meta_task.setText(result.Task)
        self.meta_objects.setText(str(len(result.Objects)))
        self.meta_latency.setText("%d ms" % result.Latency_Ms)

        self.analyses += 1
        self.objects_found += len(result.Objects)
        self.status.images.set_value(str(self.analyses))
        self.status.objects.set_value(str(self.objects_found))
        self.status.updated.set_value(datetime.now().strftime("%H:%M:%S"))

    def _clear_reading(self):
        self._showing_error = False
        self.reading_empty.setText(self._prompt_text())
        self.reading_empty.show()
        self.reading_lead.hide()
        self.reading_note.hide()
        self.object_list.set_objects([])
        self.stage_badge.set_state("Idle", "idle")
        self.meta_task.setText(NO_VALUE)
        self.meta_objects.setText(NO_VALUE)
        self.meta_latency.setText(NO_VALUE)

    def on_clear(self):
        self.frame = None
        self.analyses = 0
        self.objects_found = 0
        self.viewport.clear()
        self.frame_badge.setText("No frame")
        self.status.images.set_value("0")
        self.status.objects.set_value("0")
        self.status.updated.set_value(NO_VALUE)
        self._clear_reading()
        self._sync_controls()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_F11:
            self.showNormal() if self.isFullScreen() else self.showFullScreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        # If a worker thread (analysis or connect) is still running, stop it
        # before the window is torn down, or Qt warns "QThread: Destroyed while
        # thread is still running" and may crash on exit.
        for thread in (self._thread, self._conn_thread):
            if thread is not None:
                thread.quit()
                thread.wait(5000)
        super().closeEvent(event)


# ============================================================================
# Entry point
# ============================================================================

def _parse_args(argv):
    """Developer-only command line. Absent all flags, this is the console."""
    ap = argparse.ArgumentParser(
        description="AnyScan console. With no arguments it runs the Basler "
                    "camera and the Florence-2 model.")
    ap.add_argument(
        "--frame", metavar="PNG", default=None,
        help="Developer path: run the pipeline on a real frame previously saved "
             "from this camera instead of connecting it. Segmentation differences "
             "the frame against the reference background, so the frame must match "
             "that background's resolution (1920x1200). Real data, no hardware.")
    ap.add_argument(
        "--background", metavar="PNG", default=None,
        help="Override the empty-surface reference (default: the reference "
             "in the configuration block).")
    # parse_known_args so Qt's own flags (-style, -platform, …) pass through.
    args, _ = ap.parse_known_args(argv[1:])
    return args


def main():
    args = _parse_args(sys.argv)
    if args.background:
        Vision_Core.CONST_BACKGROUND_REF = os.path.abspath(args.background)

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    load_fonts()

    icon = app_icon()
    app.setWindowIcon(icon)

    # On Windows the taskbar groups by AppUserModelID, and a plain Python
    # process inherits python.exe's identity. Without this the title bar shows
    # the AnyScan icon while the taskbar still shows the Python one.
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "cz.jic.anyscan.console"
            )
        except Exception:  # noqa: BLE001 - cosmetic only, never worth a crash
            pass

    camera = File_Camera_Cls(os.path.abspath(args.frame)) if args.frame else Basler_Camera_Cls()
    window = AnyScanWindow(camera=camera)
    window.setWindowIcon(icon)
    window.resize(1720, 1020)
    window.showMaximized()   # F11 toggles fullscreen, Esc closes
    QTimer.singleShot(0, lambda: window.viewport.update())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
