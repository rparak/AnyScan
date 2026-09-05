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
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

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

# The project's own libraries (Basler.Core, Utilities.Image_Processing,
# Calibration.Parameters) and their heavy dependencies (pypylon, OpenCV) are
# NOT imported here. They are imported lazily inside BaslerCamera._open(), and
# torch/transformers/OpenCV likewise inside FlorenceVision, so the window still
# opens on a machine with neither the camera SDK nor the model runtime present
# and fails with a sentence the operator can act on. See the configuration
# blocks below.

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ============================================================================
# Basler camera configuration
#
# Everything the real backend needs lives here — exposure, gain, pixel format
# and the path to the project's src/ directory. Nothing in BaslerCamera is
# hard-coded; change a value here, never inside a method.
# ============================================================================

# Absolute path to the project's `src/` directory, which holds Basler.Core,
# Utilities.Image_Processing and Calibration.Parameters. Derived from this
# file's own location (App/ -> ../src) and made absolute, so it holds whatever
# the working directory is — a shortcut, a service, or a PyInstaller launch —
# rather than the old cwd-relative '../src'. Override with an absolute path if
# the source tree lives elsewhere.
BASLER_SRC = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

# Settings passed straight to Basler.Core.Camera_Cls. The keys are capitalized
# to match Camera_Cls.__Configure exactly; lower-case keys are read by nothing
# and then raise KeyError when the device is configured.
BASLER_CONFIG = {
    'Exposure_Time': 10000,                                # microseconds
    'Gain': 10,
    'Balance_Ratios': {'Red': 0.95, 'Green': 0.9, 'Blue': 1.2},
    'Pixel_Format': 'BayerRG8',
}

# Which Utilities.Image_Processing.Process_Image_Cls profile is applied to each
# raw frame. 'real' is the profile written for the physical camera.
BASLER_IMAGE_PROFILE = 'real'

# ============================================================================
# Vision configuration
#
# Everything the analysis pipeline needs — the model directory, the empty-scene
# background reference, the segmentation thresholds and the generation settings
# — lives here. analyze() reads these and holds no magic numbers of its own:
# every path and threshold in this block, nothing hard-coded in a method.
#
# The pipeline is a straight port of segment_classify.py: subtract a saved
# empty-surface photo from the captured frame to find the objects, crop each
# one from the ORIGINAL frame (Florence-2 labels natural images far better than
# objects floating on black), and run one caption pass per crop.
# ============================================================================

# The local Florence-2 weights. Presented to the operator as JIC-AnyScan-VLM-v1
# (see MODEL_NAME); the weights are Florence-2, MIT licensed — keep Microsoft's
# notice with the project. Loaded from this directory only, never a hub id, so
# there is no network call at runtime. Derived from this file's location
# (App/ -> ../models/...) and made absolute so it survives any working dir.
MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                 "models", "florence2-large-ft")
)

# The empty-surface reference photo. Segmentation is the difference between the
# captured frame and this image, so it must come from the SAME fixed camera and
# match the frame's pixel dimensions exactly. Re-shoot it whenever the camera or
# the lighting is moved.
BACKGROUND_REF = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                 "Data", "Camera", "Image_Background_001.png")
)

# The Florence-2 task token sent per crop. <CAPTION> is the default: on a single
# cropped object it returns a concise "A bolt on a green surface." that distils
# cleanly to a noun-phrase `label`, and it is faster. <DETAILED_CAPTION> and
# <MORE_DETAILED_CAPTION> also work — the distiller handles their verbose "In
# this image we can see a …" template — but they add no identification accuracy
# on a single crop and their extra words land in the line's second sentence only
# when they actually say more. The token passed to generate() and to
# post_process_generation() must be identical — they are, both read from here.
VISION_TASK = "<MORE_DETAILED_CAPTION>"

# The human-readable task name shown in the reading panel's meta row. Keep it in
# step with VISION_TASK ("caption", "detailed caption", "more detailed caption").
VISION_TASK_LABEL = "detailed caption"

# Torch device: "auto" picks cuda, then mps, then cpu. float32 is deliberate —
# fp16 on Apple's MPS backend is unreliable for this model and produces garbage
# captions.
VISION_DEVICE = "auto"

# Generation. do_sample stays False so the same frame reads the same twice; a
# console the operator cannot trust is worse than a slow one. One beam is the
# fast, deterministic default; raise VISION_NUM_BEAMS to 3 (the model's own
# default) for marginally better wording at roughly triple the latency.
VISION_NUM_BEAMS = 1
VISION_MAX_NEW_TOKENS = 256

# How object boxes are found, before any per-crop description:
#   "segment"  — background subtraction against BACKGROUND_REF. Pixel-tight on a
#                fixed rig and CLASS-AGNOSTIC: it boxes every foreground part
#                regardless of what it is, which is what "any object" needs. It
#                does need the empty-surface photo. The ported, proven method,
#                and the default for that reason.
#   "florence" — Florence-2's own detection on the full frame. No background
#                reference, robust to a moved camera — but the box set depends on
#                the detection task (below), and <OD> only proposes classes the
#                model was trained on, so it silently drops unfamiliar parts
#                (e.g. washers). Use <REGION_PROPOSAL> for class-agnostic boxes.
# Either way, each box is then cropped and described by one VISION_TASK pass.
DETECTOR = "segment"

# The Florence-2 detection task used when DETECTOR == "florence".
#   <REGION_PROPOSAL>       boxes only, CLASS-AGNOSTIC — the right choice for
#                           "any object"; the per-crop caption supplies the name.
#   <DENSE_REGION_CAPTION>  boxes + a short caption each, also class-agnostic.
#   <OD>                    boxes + a class label each, but ONLY for classes the
#                           model knows — it will miss industrial parts. Avoid
#                           for a general "any object" console.
# Boxes come back in full-frame pixels — the description crops the frame, so
# there is no crop-to-frame coordinate remap. Detection needs room for many
# boxes, so it gets its own (larger) token budget.
FLORENCE_DETECT_TASK = "<REGION_PROPOSAL>"
FLORENCE_DETECT_MAX_TOKENS = 1024
FLORENCE_MIN_AREA_FRAC = 0.0005   # drop stray specks Florence sometimes proposes

# Segmentation thresholds. Areas are fractions of the frame. The differencing
# group (colour/shadow/blur/morph/min-area) is read only when DETECTOR ==
# "segment"; the last four (max-area, max-objects, crop pad, min crop side) are
# shared — both detectors cap and crop the same way.
#
# Segmentation works in COLOUR distance, not brightness: on the green surface a
# grey screw is close to the green in luminance but far from it in colour, so a
# brightness threshold drops dark parts while a colour threshold keeps them.
# Distance is Euclidean over the three 0..255 channels, so it runs 0..441.
SEG_COLOR_DIST = 40           # min colour distance to count a pixel as foreground
SEG_STRONG_DIST = 90          # colour distance that is an object regardless of hue
SEG_SHADOW_TOLERANCE = 0.18   # min per-channel ratio spread; rejects hue-preserving shadow
SEG_BLUR = 5                  # Gaussian blur kernel before differencing
SEG_MORPH_KERNEL = 7          # ellipse kernel for open/close
SEG_OPEN_ITERS = 1
SEG_CLOSE_ITERS = 3
SEG_MIN_AREA_FRAC = 0.001     # ignore specks smaller than this
SEG_MAX_AREA_FRAC = 0.5       # ignore blobs larger than this (lighting drift)
SEG_MAX_OBJECTS = 12          # cap the number of crops per analysis (shared)
SEG_CROP_PAD_FRAC = 0.2       # crop margin as a fraction of object size (shared)
SEG_MIN_CROP_SIDE = 224       # upscale crops smaller than this before the model

# Turning a Florence caption into a two-to-three word noun phrase for `label`.
# These lead-ins are stripped from the front, the phrase is cut at the first of
# these clause boundaries, and at most LABEL_MAX_WORDS words are kept. The full
# caption is preserved as the object line's second sentence, so an imperfect
# distillation loses no information.
# Stripped from the front, repeatedly, until the noun phrase is exposed. Order
# is not important (the caller iterates to a fixed point), but every granular
# piece of Florence's templates must appear — "in this image we can see a bolt"
# peels as "in this image" + "we can see" + the article. Longest variants first
# only as a readability aid.
LABEL_LEADINS = (
    "in this image we can see", "in the image we can see",
    "in this picture we can see", "in this image, we can see",
    "in this image there are", "in this image there is",
    "in this image we see", "here we can see", "we can also see",
    "we can see", "we see", "you can see",
    "in this image", "in the image", "in this picture", "in the picture",
    "the image shows", "this image shows", "the photo shows",
    "this is a", "this is an", "there is a", "there is an",
    "there are", "here is a", "here is an",
    "a close-up of", "a close up of", "close-up of", "close up of",
    "an image of", "a image of", "image of", "a photo of", "a picture of",
    "a photograph of", "it is a", "it is an", "showing a", "showing an",
    "shows a", "shows an",
)
LABEL_BOUNDARIES = (
    ",", " is ", " are ", " was ", " with ", " that ", " which ", " has ",
    " have ", " sitting", " lying", " laying", " placed", " resting",
    " standing", " scattered", " showing", " appears", " against ", " next to",
    " on top", " on a ", " on an ", " on the ", " in the ", " in a ", " in an ",
    " across ", " and ",
)
LABEL_MAX_WORDS = 4

# The object line's wording:
#   True  — the model's full detailed description, cleaned into the panel's voice
#           ("A silver key on a green surface with a keyring attached to it.").
#   False — a short "A <label>." distilled from the caption.
SHOW_OBJECT_DETAIL = True

# What the panel says when the model finds nothing. It names both honest
# possibilities; the report composer's own scene note supplies the next action
# ("Check the lighting and the focus, then scan again."), so this is only the
# explanation and carries no trailing full stop of its own.
EMPTY_SCENE_EXPLANATION = (
    "Either nothing is on the surface, or the model did not recognise what is there"
)

# Busy-indicator animation, driven by a QTimer in the Viewport while the worker
# runs. Kept here so the whole console's tunable values live in one place.
BUSY_TICK_MS = 33             # ~30 fps repaint
BUSY_SPIN_DEG = 6             # arc rotation per tick

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
MODEL_NAME = "JIC-AnyScan-VLM-v1"


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
# ============================================================================

@dataclass
class Detection:
    """One object the pipeline located.

    Order is meaningful: the position in the list is the number the operator
    sees, both on the box drawn over the frame and at the start of the matching
    line of text. Never reorder after composing.
    """
    label: str
    bbox: tuple  # (x, y, w, h) in frame pixels
    confidence: Optional[float] = None
    text: Optional[str] = None
    detail: str = ""     # the model's full caption, rendered as a second sentence
    sentence: str = ""


@dataclass
class Analysis:
    summary: str = ""
    objects: list = field(default_factory=list)
    note: str = ""
    latency_ms: int = 0
    verdict: str = "Idle"
    verdict_level: str = "idle"   # ok | warn | idle
    task: str = "detailed caption"


# ============================================================================
# Report composer
#
# The panel on the right is the product. Every sentence the operator reads is
# written here and nowhere else, so the console keeps one voice whichever
# backend produced the data.
#
# House style: plain declarative sentences, present tense, no hedging adverbs,
# no self-reference, numbers one to ten spelled out, and an empty result is a
# statement with a next action rather than an apology.
# ============================================================================

_NUMBER_WORDS = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def _count_word(n: int) -> str:
    return _NUMBER_WORDS.get(n, str(n))


def zone(bbox, size) -> str:
    """Coarse nine-cell position, the way a person would describe it.

    Currently unused: object lines were changed to say what a part is, not where
    it is (the number on the coloured box carries position). Kept for the day a
    position phrase is wanted back — re-add it in describe_object.
    """
    width, height = size
    cx = (bbox[0] + bbox[2] / 2) / max(width, 1)
    cy = (bbox[1] + bbox[3] / 2) / max(height, 1)
    row = "upper" if cy < 0.34 else ("lower" if cy > 0.66 else "middle")
    col = "left" if cx < 0.34 else ("right" if cx > 0.66 else "centre")
    if row == "middle" and col == "centre":
        return "the centre of the frame"
    if col == "centre":
        return "the %s centre of the frame" % row
    return "the %s %s of the frame" % (row, col)


def _clean_detail(text: str) -> str:
    """Tidy the model's caption into a standalone second sentence.

    The composer, not the model, owns punctuation and capitalisation, so the
    raw string is normalised here rather than printed as-is: surrounding
    whitespace gone, first letter capitalised, exactly one terminal full stop.
    """
    text = " ".join(text.split()).strip()
    if not text:
        return ""
    # capitalise the first letter of every sentence, not only the first
    out, at_start = [], True
    for ch in text:
        if at_start and ch.isalpha():
            ch = ch.upper()
            at_start = False
        out.append(ch)
        if ch in ".!?":
            at_start = True
    text = "".join(out)
    return text if text[-1] in ".!?" else text + "."


def _caption_sentence(caption: str) -> str:
    """The model's full caption as a clean, standalone description.

    Florence prefixes a fixed template ("In this image we can see a …"); those
    lead-ins are peeled from the front so the description reads naturally, then
    _clean_detail imposes the console's capitalisation and terminal stop. This
    is where the panel's one voice is put on the model's raw words.
    """
    text = " ".join(caption.split()).strip()
    stripped = True
    while stripped:
        stripped = False
        low = text.lower()
        for lead in LABEL_LEADINS:
            if low.startswith(lead):
                text = text[len(lead):].lstrip(" ,")
                stripped = True
                break
    return _clean_detail(text)


def describe_object(det: Detection, size) -> str:
    """One line for one detection — what the object is, not where it is.

    With SHOW_OBJECT_DETAIL the line is the model's full description, cleaned
    into the console's voice; otherwise it is the short "A <label>." Position is
    deliberately not stated: the operator reads the number off the coloured box
    on the frame, so a coarse location in words earns nothing. (`size` is unused
    now that the zone is gone; kept so the composer's call site is unchanged.)
    The index is not repeated here either; the list prints `Object N:` in the
    box's colour, and duplicating the number reads as a stutter.
    """
    sentence = _caption_sentence(det.detail) if SHOW_OBJECT_DETAIL else ""
    if not sentence:
        article = "An" if det.label[:1].lower() in "aeiou" else "A"
        sentence = "%s %s." % (article, det.label)
    if det.text:
        sentence = sentence.rstrip(".") + ", reading \u201c%s\u201d." % det.text
    return sentence


def summarise(objects) -> str:
    n = len(objects)
    if n == 0:
        return "No objects were located in this frame."
    if n == 1:
        return "The frame contains one object, described as follows:"
    return "The frame contains %s objects, which are described as follows:" % _count_word(n)


def scene_note(objects, size, caption="") -> str:
    # No framing advice: the note carries the empty-scene explanation and its
    # next action, and otherwise stays silent so the panel is just the objects.
    parts = []
    if caption:
        parts.append(caption.strip().rstrip(".") + ".")
    if not objects:
        parts.append("Check the lighting and the focus, then scan again.")
    return " ".join(parts)


def verdict(objects, threshold=0.35):
    """Badge wording and its severity level.

    The level drives the badge colour, returned separately so the interface
    never parses the wording to decide how to paint it.
    """
    if not objects:
        return "Empty", "idle"
    scored = [o.confidence for o in objects if o.confidence is not None]
    if scored and min(scored) < threshold:
        return "Low confidence", "warn"
    return "%d found" % len(objects), "ok"


def compose(objects, size, caption=""):
    for det in objects:
        det.sentence = describe_object(det, size)
    return objects, summarise(objects), scene_note(objects, size, caption)


# ============================================================================
# Camera layer
# ============================================================================

class CameraError(RuntimeError):
    """Raised for anything the operator needs to see on screen."""


class Camera:
    """Connect, capture, disconnect. Nothing else.

    The base class owns the connected flag and refuses capture() when
    disconnected, so a subclass never tracks that itself. `_grab()` returns a
    QImage in RGB — that is the exchange format for the whole application,
    whatever the SDK hands you.
    """

    name = "camera"

    def __init__(self):
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def resolution(self):
        raise NotImplementedError

    def _open(self):
        raise NotImplementedError

    def _close(self):
        raise NotImplementedError

    def _grab(self) -> QImage:
        raise NotImplementedError

    def connect(self):
        if self._connected:
            return
        self._open()
        self._connected = True

    def disconnect(self):
        if not self._connected:
            return
        self._close()
        self._connected = False

    def capture(self) -> QImage:
        if not self._connected:
            raise CameraError("Camera is not connected.")
        return self._grab()


class FileCamera(Camera):
    """A real frame from disk, standing in for the camera — developer only.

    Not a mock: it delivers an actual PNG previously saved from this camera
    (see Example/Camera/scan.py), so the whole pipeline runs on real data with
    no pylon and no hardware present, repeatably. It is the fastest way to check
    that boxes land where the text says they do. Reached only through the
    `--frame` command-line argument in main() and never surfaced in the UI.
    """

    name = "Saved frame (developer)"

    def __init__(self, path):
        super().__init__()
        self._path = path
        self._image = None

    @property
    def resolution(self):
        if self._image is None:
            return (0, 0)
        return (self._image.width(), self._image.height())

    def _open(self):
        if not os.path.isfile(self._path):
            raise CameraError(
                "No saved frame at \"%s\". Pass --frame with the path to a PNG "
                "captured from this camera." % self._path
            )
        img = QImage(self._path)
        if img.isNull():
            raise CameraError(
                "The saved frame at \"%s\" could not be read as an image." % self._path
            )
        # RGB888 is the application's exchange format, matching BaslerCamera._grab.
        self._image = img.convertToFormat(QImage.Format_RGB888)

    def _close(self):
        self._image = None

    def _grab(self) -> QImage:
        if self._image is None:
            raise CameraError("The saved frame is not loaded.")
        return QImage(self._image)  # a shallow copy; the frame is immutable here


class BaslerCamera(Camera):
    """The real camera, wired to src/Basler/Core.Camera_Cls.

    Backed by pypylon through the project's Camera_Cls wrapper and the capture
    sequence in Example/Camera/scan.py and record.py. This is the console's
    camera; all its settings live in the Basler configuration block near the
    top. (For a hardware-free run, --frame swaps in a FileCamera instead.)

    The four things this class exists to get right:

      * The SDK is imported inside _open(), never at module level, so the
        console still starts (as the mock backend) on a machine with no pylon.
      * A pylon device is closed explicitly in _close() via the public camera
        handle — dropping the Python reference and waiting for __del__ is not
        deterministic, and a device left open makes the next CONNECT fail with
        "device busy".
      * Camera_Cls.Capture() returns BGR (its converter emits BGR8packed); this
        application exchanges RGB, so the frame is converted once, at the end.
      * getOptimalNewCameraMatrix depends only on the calibration and the frame
        size, so it is computed once per size and cached, never per frame.

    Camera_Cls.Capture() already uses an explicit 5000 ms retrieve timeout that
    raises on hang; _grab turns that (and any other grab failure) into a
    CameraError instead of freezing the GUI thread on a traceback.
    """

    name = "Basler"

    def __init__(self):
        super().__init__()
        self._cam = None
        # A placeholder until the device is open; overwritten with the real
        # device size in _open() and again with the delivered size in _grab().
        self._resolution = (1920, 1200)
        self._processor = None
        self._calib = None
        self._cv2 = None
        self._np = None
        # (width, height) -> (K, distortion coeffs, optimal new camera matrix)
        self._undistort_cache = {}

    @property
    def resolution(self):
        return self._resolution

    def _open(self):
        # Imported here, not at module level, so a machine without the camera
        # SDK can still run the mock backend and the UI.
        try:
            if BASLER_SRC not in sys.path:
                sys.path.insert(0, BASLER_SRC)
            import cv2
            import numpy as np
            from Basler.Core import Camera_Cls
            import Utilities.Image_Processing as Image_Processing
            from Calibration.Parameters import Basler_Calib_Param_Str
        except ImportError as exc:
            raise CameraError(
                "The Basler libraries could not be loaded from \"%s\". Check that "
                "pypylon and OpenCV are installed and that BASLER_SRC points at the "
                "project's src directory." % BASLER_SRC
            ) from exc

        # Camera_Cls connects inside its constructor and raises if no device is
        # found, so a failure here is a connection failure.
        try:
            self._cam = Camera_Cls(config=BASLER_CONFIG)
        except Exception as exc:                          # noqa: BLE001
            self._cam = None
            raise CameraError(
                "No Basler camera was detected. Check that the camera is powered "
                "and the GigE link is up."
            ) from exc

        if getattr(self._cam, "camera", None) is None:
            self._cam = None
            raise CameraError(
                "No Basler camera was detected. Check that the camera is powered "
                "and the GigE link is up."
            )

        # Cache what _grab needs so it never re-imports or re-reads config.
        self._cv2 = cv2
        self._np = np
        self._processor = Image_Processing.Process_Image_Cls(BASLER_IMAGE_PROFILE)
        self._calib = Basler_Calib_Param_Str
        self._undistort_cache = {}

        # Report the device's actual sensor size straight away, so the status
        # strip is right at CONNECT and not only after the first SCAN.
        try:
            self._resolution = (int(self._cam.camera.Width.Value),
                                int(self._cam.camera.Height.Value))
        except Exception:                                 # noqa: BLE001
            pass  # the delivered frame in _grab is the authoritative size

    def _close(self):
        # Stop grabbing and close the device explicitly through the public pylon
        # handle. Dropping the reference alone is not enough — see the class
        # docstring — and a close failure must never block DISCONNECT.
        cam = getattr(self._cam, "camera", None)
        if cam is not None:
            try:
                if cam.IsGrabbing():
                    cam.StopGrabbing()
                if cam.IsOpen():
                    cam.Close()
            except Exception:                             # noqa: BLE001
                pass
        self._cam = None
        self._processor = None
        self._undistort_cache = {}

    def _grab(self) -> QImage:
        cv2, np = self._cv2, self._np

        # One frame. Capture() auto-starts grabbing (LatestImageOnly) and uses a
        # 5000 ms retrieve timeout that raises on hang; translate any failure
        # into a message the operator can act on rather than freezing the window.
        try:
            raw = self._cam.Capture()
        except Exception as exc:                          # noqa: BLE001
            raise CameraError(
                "The camera did not return a frame in time. Check that it is still "
                "powered and that the GigE link is up, then scan again."
            ) from exc
        if raw is None:
            raise CameraError(
                "The camera returned an empty frame. Check the exposure time and "
                "the scene lighting, then scan again."
            )

        # Project image pipeline (BGR in, BGR out), then undistort with the
        # cached optimal camera matrix.
        processed = self._processor.Apply(raw)
        undistorted = self._undistort(processed)

        # The pipeline works in BGR; the application exchanges RGB.
        rgb = np.ascontiguousarray(cv2.cvtColor(undistorted, cv2.COLOR_BGR2RGB))
        h, w = rgb.shape[:2]
        self._resolution = (w, h)

        # QImage does not own the numpy buffer: it is a view over rgb.data with
        # a 3*w stride. .copy() detaches it so the frame survives rgb being
        # garbage-collected, which otherwise tears the viewport or segfaults.
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
        return image.copy()

    def _undistort(self, image):
        """Undistort a BGR frame, caching the per-size optimal camera matrix."""
        cv2, np = self._cv2, self._np
        h, w = image.shape[:2]
        cached = self._undistort_cache.get((w, h))
        if cached is None:
            K = self._calib.K
            coeffs = np.array(list(self._calib.Coefficients.values()),
                              dtype=np.float64)
            new_K, _ = cv2.getOptimalNewCameraMatrix(K, coeffs, (w, h), 1, (w, h))
            cached = (K, coeffs, new_K)
            self._undistort_cache[(w, h)] = cached
        K, coeffs, new_K = cached
        return cv2.undistort(image, K, coeffs, None, new_K)


# ============================================================================
# Vision layer
#
# The pipeline (DETECTOR selects how the boxes are found):
#
#   frame  --detect-->  N boxes in FULL-FRAME pixels
#     "segment":  frame + background reference -> _build_mask -> _find_objects
#     "florence": Florence-2 <OD> on the full frame -> _detect_florence
#          -> _crop_with_pad   crop each box from the ORIGINAL frame
#               -> _describe    one Florence-2 caption per crop (the "what")
#                    -> Detection(label, bbox, detail)
#                         -> compose()  the numbered lines the panel renders
#
# Boxes are in full-frame pixels either way, so there is no crop-to-frame
# coordinate remap to get wrong: only the crop (for the caption) is a sub-image.
# Florence-2 emits no confidence, so confidence stays None and the verdict
# handles unscored objects. The line says what the object is, not where.
# ============================================================================

class VisionError(RuntimeError):
    """Raised for anything the operator needs to see on screen.

    Its message must be a full, actionable sentence: it is printed straight
    into the Scene Understanding panel.
    """


def _qimage_to_bgr(image: QImage, np, cv2):
    """A QImage frame as a contiguous BGR array, matching cv2.imread's order."""
    img = image.convertToFormat(QImage.Format_RGB888)
    w, h = img.width(), img.height()
    bpl = img.bytesPerLine()                       # may be padded past 3*w
    ptr = img.constBits()
    ptr.setsize(h * bpl)
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, bpl))
    rgb = arr[:, : w * 3].reshape((h, w, 3))       # drop any row padding
    return cv2.cvtColor(np.ascontiguousarray(rgb), cv2.COLOR_RGB2BGR)


def _build_mask(bg, fg, cv2, np):
    """Foreground mask from the frame and the empty-surface reference.

    Colour distance, not brightness, is the primary test. On the green surface a
    grey or black screw sits close to the green in luminance — a brightness
    threshold silently drops it — yet far from the green in COLOUR, because the
    green channel alone falls sharply. A bright washer is far in every channel.
    Both therefore clear a colour-distance threshold.

    A large distance is an object outright. A moderate distance is an object only
    if the hue also changed (the per-channel ratio spread), which rejects the
    soft shadow a part casts on the surface: a shadow darkens the green but keeps
    its hue, so its channel ratios stay roughly constant.
    """
    blur = (SEG_BLUR, SEG_BLUR)
    bg_b = cv2.GaussianBlur(bg, blur, 0).astype(np.float32) + 1.0
    fg_b = cv2.GaussianBlur(fg, blur, 0).astype(np.float32) + 1.0

    diff = fg_b - bg_b
    dist = np.sqrt((diff * diff).sum(axis=2))       # Euclidean colour distance

    ratio = fg_b / bg_b
    spread = ratio.max(axis=2) - ratio.min(axis=2)  # hue change; ~0 under shadow

    strong = dist > SEG_STRONG_DIST                 # unmistakable object, any hue
    subtle = (dist > SEG_COLOR_DIST) & (spread > SEG_SHADOW_TOLERANCE)
    mask = ((strong | subtle).astype(np.uint8)) * 255

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                  (SEG_MORPH_KERNEL, SEG_MORPH_KERNEL))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=SEG_OPEN_ITERS)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=SEG_CLOSE_ITERS)

    # fill interior holes: washers and nuts are rings whose centre shows
    # background and would otherwise split into two components
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, contours, -1, 255, thickness=cv2.FILLED)
    return filled


def _find_objects(mask, cv2, np):
    """Object boxes as (x1, y1, x2, y2) in frame pixels, ordered left to right.

    The reference keeps the largest N by area; that selection is preserved, but
    the returned order is left-to-right — the order a person reads in and the
    contract the index draws on. compose() must see them already in this order
    and never reorder after.
    """
    h, w = mask.shape
    area_total = float(h * w)
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    boxes = []
    for i in range(1, n):  # 0 is background
        x, y, bw, bh, area = stats[i]
        frac = area / area_total
        if frac < SEG_MIN_AREA_FRAC or frac > SEG_MAX_AREA_FRAC:
            continue
        # cast off numpy int32, which is not JSON-serialisable and prints noisily
        boxes.append((int(x), int(y), int(x + bw), int(y + bh), int(area)))

    # keep the largest N, then present them left to right
    boxes.sort(key=lambda b: b[4], reverse=True)
    boxes = boxes[:SEG_MAX_OBJECTS]
    boxes.sort(key=lambda b: b[0])
    return [b[:4] for b in boxes]


def _crop_with_pad(img, box):
    """Crop from the ORIGINAL image with a margin, clamped to bounds.

    From the original, never the masked frame: Florence-2 is trained on natural
    images and an object floating on black is out of distribution.
    """
    h, w = img.shape[:2]
    x1, y1, x2, y2 = box
    pad = int(SEG_CROP_PAD_FRAC * max(x2 - x1, y2 - y1))
    cx1, cy1 = max(0, x1 - pad), max(0, y1 - pad)
    cx2, cy2 = min(w, x2 + pad), min(h, y2 + pad)
    return img[cy1:cy2, cx1:cx2]


def _describe(model, processor, device, dtype, crop_bgr, cv2, np, torch, PILImage):
    """One Florence-2 caption pass on a single crop; returns the raw caption."""
    pil = PILImage.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))

    # tiny crops upscale poorly through the processor's own resize; give it
    # something reasonable to work with
    if min(pil.size) < SEG_MIN_CROP_SIDE:
        scale = SEG_MIN_CROP_SIDE / min(pil.size)
        pil = pil.resize((int(pil.width * scale), int(pil.height * scale)),
                         PILImage.LANCZOS)

    inputs = processor(text=VISION_TASK, images=pil, return_tensors="pt")
    inputs = {k: (v.to(device, dtype) if v.is_floating_point() else v.to(device))
              for k, v in inputs.items()}

    with torch.inference_mode():
        ids = model.generate(**inputs, max_new_tokens=VISION_MAX_NEW_TOKENS,
                             num_beams=VISION_NUM_BEAMS, do_sample=False)
    # skip_special_tokens=False: post_process_generation needs the location and
    # task tokens that True would strip, or structured output silently vanishes.
    raw = processor.batch_decode(ids, skip_special_tokens=False)[0]
    parsed = processor.post_process_generation(
        raw, task=VISION_TASK, image_size=pil.size)[VISION_TASK]

    if isinstance(parsed, str):
        return parsed.strip()
    if isinstance(parsed, dict):                   # OD-style tasks return a dict
        labels = parsed.get("labels") or []
        return labels[0] if labels else ""
    return str(parsed)


def _condense_label(caption: str) -> str:
    """A two-to-three word noun phrase for `label`, distilled from a caption.

    describe_object() renders `label` as "A <label> in the upper left of the
    frame.", so a paragraph there produces a line that is not a sentence. The
    front matter and any trailing clause are stripped and the phrase is capped;
    the full caption survives untouched in Detection.detail as the line's second
    sentence, so an imperfect distillation loses nothing.
    """
    text = " ".join(caption.split()).strip().rstrip(".")
    # Florence stacks lead-ins ("The image shows a close-up of a hex bolt"), so
    # strip them repeatedly until the front is the noun phrase itself.
    stripped = True
    while stripped:
        stripped = False
        low = text.lower()
        for lead in LABEL_LEADINS:
            if low.startswith(lead):
                text = text[len(lead):].lstrip(" ,")
                stripped = True
                break

    low = text.lower()
    cut = len(text)
    for boundary in LABEL_BOUNDARIES:
        idx = low.find(boundary)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut].strip(" ,")

    for article in ("a ", "an ", "the "):
        if text.lower().startswith(article):
            text = text[len(article):]
            break

    words = text.split()[:LABEL_MAX_WORDS]
    text = " ".join(words).strip(" ,.")
    return text.lower() if text else "object"


class VisionBackend:
    """One method matters: analyze(image) -> Analysis.

    Everything the Scene Understanding panel shows comes out of that single
    call, so a backend swap never touches the interface. `progress_cb(done,
    total)` and `stage_cb(text)` are optional hooks the worker thread uses to
    drive the busy indicator; a backend may ignore them.
    """

    name = MODEL_NAME

    def analyze(self, image: QImage, progress_cb=None, stage_cb=None) -> Analysis:
        raise NotImplementedError


class FlorenceVision(VisionBackend):
    """The real vision-language model.

    Presented as JIC-AnyScan-VLM-v1; the weights are Florence-2, MIT licensed —
    keep Microsoft's notice with the project.

    Notes that cost hours if missed:

      * These are the native transformers `Florence2ForConditionalGeneration`
        weights (no bundled modelling code, no auto_map), so they load with
        local_files_only=True and NOT trust_remote_code. Nothing here touches
        the network at runtime.
      * torch, transformers and OpenCV are imported lazily on first analyze, so
        the window still opens on a machine without them.
      * The model loads once and is kept; the first analysis therefore pays a
        cold-load cost the busy indicator must cover ("Loading model…").
      * It emits no confidence scores. confidence stays None — the verdict
        handles unscored detections. Never invent a number.
      * Boxes are in full-frame pixels whichever detector is used (background
        subtraction or Florence's own <OD>); the per-crop pass only describes.
        There is no crop-to-frame remap, and `objects` is never reordered after
        compose().
    """

    def __init__(self):
        self._model = None
        self._processor = None
        self._device = None
        self._dtype = None
        self._torch = None
        self._cv2 = None
        self._np = None
        self._pil = None
        self._background = None   # cached BGR reference array

    def _pick_device(self, torch):
        if VISION_DEVICE != "auto":
            return torch.device(VISION_DEVICE)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _ensure_loaded(self, stage_cb):
        if self._model is not None:
            return
        if stage_cb:
            stage_cb("Loading model…")
        try:
            import cv2
            import numpy as np
            import torch
            from PIL import Image as PILImage
            from transformers import (AutoProcessor,
                                      Florence2ForConditionalGeneration)
        except ImportError as exc:
            raise VisionError(
                "The vision runtime is not installed. Install torch, transformers, "
                "OpenCV and Pillow into this environment, then scan again."
            ) from exc

        device = self._pick_device(torch)
        dtype = torch.float32  # fp16 on MPS is unreliable for this model
        try:
            model = Florence2ForConditionalGeneration.from_pretrained(
                MODEL_DIR, dtype=dtype, local_files_only=True)
            model.to(device)
            model.eval()
            processor = AutoProcessor.from_pretrained(
                MODEL_DIR, local_files_only=True)
        except Exception as exc:                          # noqa: BLE001
            raise VisionError(
                "The model weights at \"%s\" could not be loaded. Check that the "
                "directory is complete and readable." % MODEL_DIR
            ) from exc

        self._cv2, self._np, self._torch, self._pil = cv2, np, torch, PILImage
        self._model, self._processor = model, processor
        self._device, self._dtype = device, dtype

    def _load_background(self, cv2, frame_shape):
        if self._background is None:
            bg = cv2.imread(BACKGROUND_REF)
            if bg is None:
                raise VisionError(
                    "The background reference at \"%s\" could not be read. It is the "
                    "empty-surface photo the analysis subtracts from the frame; shoot "
                    "one from this camera and save it there." % BACKGROUND_REF
                )
            self._background = bg
        if self._background.shape != frame_shape:
            bh, bw = self._background.shape[:2]
            fh, fw = frame_shape[:2]
            raise VisionError(
                "The background reference is %d×%d but the frame is %d×%d. "
                "Re-shoot the empty-surface reference from this camera so the two "
                "match." % (bw, bh, fw, fh)
            )
        return self._background

    def _detect_florence(self, frame_bgr, stage_cb):
        """Florence-2's own detection on the full frame.

        Returns (boxes_xyxy, det_labels) in full-frame pixels, filtered by area,
        capped, and ordered left to right — the same contract _find_objects
        returns, plus the model's own per-box label for a fallback name.
        """
        cv2, torch, pil = self._cv2, self._torch, self._pil
        if stage_cb:
            stage_cb("Detecting objects…")

        frame_rgb = pil.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        inputs = self._processor(text=FLORENCE_DETECT_TASK, images=frame_rgb,
                                 return_tensors="pt")
        inputs = {k: (v.to(self._device, self._dtype) if v.is_floating_point()
                      else v.to(self._device)) for k, v in inputs.items()}
        with torch.inference_mode():
            ids = self._model.generate(
                **inputs, max_new_tokens=FLORENCE_DETECT_MAX_TOKENS,
                num_beams=VISION_NUM_BEAMS, do_sample=False)
        raw = self._processor.batch_decode(ids, skip_special_tokens=False)[0]
        parsed = self._processor.post_process_generation(
            raw, task=FLORENCE_DETECT_TASK, image_size=frame_rgb.size)

        block = parsed.get(FLORENCE_DETECT_TASK, {}) if isinstance(parsed, dict) else {}
        bboxes = block.get("bboxes", []) if isinstance(block, dict) else []
        labels = (block.get("labels") if isinstance(block, dict) else None) or []

        h, w = frame_bgr.shape[:2]
        area_total = float(h * w)
        items = []
        for i, box in enumerate(bboxes):
            x1, y1, x2, y2 = (int(round(v)) for v in box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 <= x1 or y2 <= y1:
                continue
            frac = ((x2 - x1) * (y2 - y1)) / area_total
            if frac < FLORENCE_MIN_AREA_FRAC or frac > SEG_MAX_AREA_FRAC:
                continue
            label = labels[i] if i < len(labels) else None
            items.append(((x1, y1, x2, y2), label, frac))

        # keep the largest N, then present them left to right (the index contract)
        items.sort(key=lambda it: it[2], reverse=True)
        items = items[:SEG_MAX_OBJECTS]
        items.sort(key=lambda it: it[0][0])
        return [it[0] for it in items], [it[1] for it in items]

    def _detect(self, frame_bgr, cv2, np, stage_cb):
        """Boxes (xyxy) and optional per-box labels, from the chosen detector."""
        if DETECTOR == "segment":
            if stage_cb:
                stage_cb("Segmenting…")
            bg_bgr = self._load_background(cv2, frame_bgr.shape)
            mask = _build_mask(bg_bgr, frame_bgr, cv2, np)
            boxes = _find_objects(mask, cv2, np)
            return boxes, [None] * len(boxes)
        return self._detect_florence(frame_bgr, stage_cb)

    def analyze(self, image: QImage, progress_cb=None, stage_cb=None) -> Analysis:
        t0 = time.perf_counter()
        self._ensure_loaded(stage_cb)
        cv2, np, torch, pil = self._cv2, self._np, self._torch, self._pil
        size = (image.width(), image.height())

        frame_bgr = _qimage_to_bgr(image, np, cv2)
        boxes, det_labels = self._detect(frame_bgr, cv2, np, stage_cb)

        objects = []
        total = len(boxes)
        for i, box in enumerate(boxes):
            if progress_cb:
                progress_cb(i, total)
            crop = _crop_with_pad(frame_bgr, box)
            caption = _describe(self._model, self._processor, self._device,
                                self._dtype, crop, cv2, np, torch, pil)
            label = _condense_label(caption)
            # If the caption gave nothing usable, fall back to the detector's own
            # class label (e.g. <OD>'s "screw") rather than the "object" default.
            if label == "object" and det_labels[i]:
                label = " ".join(det_labels[i].split()[:LABEL_MAX_WORDS]).lower()
            x1, y1, x2, y2 = box
            objects.append(Detection(
                label=label,
                bbox=(x1, y1, x2 - x1, y2 - y1),   # xyxy -> xywh, frame pixels
                confidence=None,                   # Florence-2 emits no score
                detail=caption,
            ))
        if progress_cb:
            progress_cb(total, total)

        caption = "" if objects else EMPTY_SCENE_EXPLANATION
        objects, summary, note = compose(objects, size, caption=caption)
        badge, level = verdict(objects)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return Analysis(summary=summary, objects=objects, note=note,
                        latency_ms=latency_ms, verdict=badge, verdict_level=level,
                        task=VISION_TASK_LABEL)


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
            x, y, w, h = det.bbox
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
                '<span style="color:%s">%s</span>' % (ink, i + 1, INK_SOFT, det.sentence)
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
            result = self._vision.analyze(
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
            self._camera.connect()
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
        self.camera = camera if camera is not None else BaslerCamera()
        self.vision = FlorenceVision()

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
        model_label = QLabel(self.vision.name)
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
        return self.READING_NO_FRAME if self.camera.connected else self.READING_DISCONNECTED

    def _sync_prompts(self):
        """Point both empty states at the step that is actually available."""
        self.viewport.set_empty_text(
            "Press Scan to capture a frame." if self.camera.connected
            else "Connect a camera, then press Scan to capture a frame."
        )
        if not self._showing_error and not self.reading_empty.isHidden():
            self.reading_empty.setText(self._prompt_text())

    def _sync_controls(self):
        connected = self.camera.connected
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
        if self._worker_running or self.camera.connected:
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
        w, h = self.camera.resolution
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
        self.camera.disconnect()
        self.frame = None
        self.viewport.clear()
        self.frame_badge.setText("No frame")
        self.status.camera.set_value("Disconnected", INK_MUTE, INK_MUTE)
        self.status.resolution.set_value(NO_VALUE)
        self._sync_controls()

    def on_scan(self):
        try:
            self.viewport.set_busy("Capturing frame\u2026")
            self.frame = self.camera.capture()
        except CameraError as exc:
            self._fail(str(exc))
        else:
            self.viewport.show_frame(self.frame)
            self.frame_badge.setText("%d \u00d7 %d \u00b7 RGB"
                                     % (self.frame.width(), self.frame.height()))
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

    def _show_analysis(self, result: Analysis):
        self._showing_error = False
        self.reading_empty.hide()
        self.reading_lead.setText(result.summary)
        self.reading_lead.show()
        self.object_list.set_objects(result.objects)
        self.reading_note.setText(result.note)
        self.reading_note.setVisible(bool(result.note))

        self.viewport.show_detections(result.objects)
        self.stage_badge.set_state(result.verdict, result.verdict_level)

        self.meta_task.setText(result.task)
        self.meta_objects.setText(str(len(result.objects)))
        self.meta_latency.setText("%d ms" % result.latency_ms)

        self.analyses += 1
        self.objects_found += len(result.objects)
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
        help="Override the empty-surface reference (default: the BACKGROUND_REF "
             "in the configuration block).")
    # parse_known_args so Qt's own flags (-style, -platform, …) pass through.
    args, _ = ap.parse_known_args(argv[1:])
    return args


def main():
    args = _parse_args(sys.argv)
    if args.background:
        global BACKGROUND_REF
        BACKGROUND_REF = os.path.abspath(args.background)

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

    camera = FileCamera(os.path.abspath(args.frame)) if args.frame else BaslerCamera()
    window = AnyScanWindow(camera=camera)
    window.setWindowIcon(icon)
    window.resize(1720, 1020)
    window.showMaximized()   # F11 toggles fullscreen, Esc closes
    QTimer.singleShot(0, lambda: window.viewport.update())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
