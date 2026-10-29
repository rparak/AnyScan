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
# File Name: JIC_SF_UI/Charts.py
## =========================================================================== ##

# System (Default)
import math
# Typing (Support for type hints)
import typing as tp
# Dataclasses (Data structures)
from dataclasses import dataclass, field
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QFontMetrics, QPainterPath
from PyQt5.QtWidgets import QWidget, QLabel, QSizePolicy
# JIC_SF_UI: tokens, fonts and the card chrome
from . import Style
from .Style import Font
from .Widgets import Card_Cls, Card_Head_Cls

"""
Description:
    Initialization of constants.

    Hand-drawn charts in the JIC Smart Factory style, generalised from AnyScan's Trends view (src/UI/Views/Trends.py and
    the Qt-free maths of src/Reporting/Trends.py). One chart base draws the furniture (gridlines on nice ticks, the
    axis titles, the line-sample legend above the plot, the hover read-out); a chart only declares its series and
    guides. The rules (references/charts.md):
      - every series is a 2 px line with a 7 px SQUARE marker on the pixel grid at every point;
      - a derived series (a running mean) is dashed (6 px dash, 4 px gap) with HOLLOW squares (a 2 px ring, its own
        line clipped out of it), drawn on top;
      - a state series is exactly its state's colour (Theme.Verdict_Color()[0]); a total is CONST_INK_MUTE; neutral
        series are CONST_DETECTION_INK (dark) and CONST_CHART_LIGHT_INK (light), never a state's colour;
      - threshold guides are 1 px, dashed, the neutral grey, labelled above their right end with what they mean;
      - the charts' own text (axis titles, legend labels, guide labels, hover secondaries) is the neutral grey: beside
        data the purple would read as OK. Tick labels are CONST_INK_MUTE, gridlines CONST_LINE.
"""
# Plot margins inside the widget, and the room an x tick label needs.
#   Unit [int] (px)
CONST_MARGIN_LEFT = 60
CONST_MARGIN_BOTTOM = 52
CONST_MARGIN_TOP = 34
CONST_MARGIN_RIGHT = 18
CONST_X_LABEL_PX = 46
# One line width and one marker for every series and its legend sample.
#   Unit [float] (px) / [int] (px)
CONST_SERIES_LINE_W = 2.0
CONST_SERIES_MARKER_PX = 7
CONST_HOLLOW_MARKER_PX = 2
# A derived series' dash, in line widths (Qt): 3 x 2 px dash, 2 x 2 px gap.
#   Unit [Vector<float>]
CONST_DERIVED_DASH = [3.0, 2.0]
# Threshold guides' dashes in px (1 px lines): long for the milder threshold, short for the severe one.
#   Unit [Vector<float>]
CONST_GUIDE_DASH_LONG = [6.0, 4.0]
CONST_GUIDE_DASH_SHORT = [2.0, 3.0]
# Markers are drawn only while the columns are at least this far apart; the hover still reads each point.
#   Unit [float] (px)
CONST_MARKER_MIN_SPACING = 10.0
CONST_CHART_MIN_HEIGHT = 240


@dataclass
class Series_Str:
    """
    Description:
        One series: its legend label, colour token, y values (None breaks the line), and whether it is derived
        (dashed, hollow squares, drawn on top).
    """

    Label: str = ''
    Color: str = ''
    Values: tp.List[tp.Optional[float]] = field(default_factory=list)
    Derived: bool = False


@dataclass
class Guide_Str:
    """
    Description:
        A horizontal threshold guide: its value, the label saying what it means ('Warning below 80 %') and its dash.
    """

    Value: float = 0.0
    Label: str = ''
    Dash: tp.List[float] = field(default_factory=lambda: list(CONST_GUIDE_DASH_LONG))


def __Nice_Number(value: float, round_it: bool) -> float:
    """
    Description:
        A 1/2/5 x 10^n number near value: rounded to the nearest, or the next at or above it.

    Args:
        (1) value [float]: The number (> 0).
        (2) round_it [bool]: Round to nearest (True) or ceil (False).

    Returns:
        (1) parameter [float]: The nice number.
    """

    if value <= 0:
        return 1.0
    exponent = math.floor(math.log10(value))
    fraction = value / (10 ** exponent)
    if round_it:
        nice = 1.0 if fraction < 1.5 else 2.0 if fraction < 3.0 else 5.0 if fraction < 7.0 else 10.0
    else:
        nice = 1.0 if fraction <= 1.0 else 2.0 if fraction <= 2.0 else 5.0 if fraction <= 5.0 else 10.0
    return nice * (10 ** exponent)


def Nice_Ticks(low: float, high: float, target: int = 5) -> tp.List[float]:
    """
    Description:
        Axis tick values on 1, 2 or 5 x 10^n steps, from the step multiple at or below low to the one at or above high.

    Args:
        (1) low [float]: The data minimum.
        (2) high [float]: The data maximum.
        (3) target [int]: The approximate number of intervals.

    Returns:
        (1) parameter [Vector<float>]: The ticks, ascending.
    """

    if high <= low:
        high = low + 1.0
    step = __Nice_Number(__Nice_Number(high - low, round_it=False) / max(1, target), round_it=True)
    value, end, ticks = math.floor(low / step) * step, math.ceil(high / step) * step, []
    while value <= end + step * 0.5 and len(ticks) < 1000:
        ticks.append(round(value, 10))
        value += step
    return ticks


def Thin_Label_Indices(count: int, max_labels: int) -> tp.List[int]:
    """
    Description:
        Which of count evenly spaced positions get an x label so labels never overlap and land on round numbers:
        multiples of a nice step, the first always, the last when it clears the previous by half a step.

    Args:
        (1) count [int]: The number of positions (position i is number i + 1).
        (2) max_labels [int]: The most labels that fit (>= 2).

    Returns:
        (1) parameter [Vector<int>]: The 0-based indices to label.
    """

    if count <= 0:
        return []
    if count <= max_labels or count <= 2:
        return list(range(count))
    step = max(1, int(round(__Nice_Number(count / float(max(1, max_labels - 1)), round_it=False))))
    numbers = [1] + [n for n in range(step, count + 1, step) if n > 1]
    if len(numbers) > 1 and numbers[1] - numbers[0] < step / 2.0:
        numbers.pop(1)
    if count - numbers[-1] >= step / 2.0:
        numbers.append(count)
    return [n - 1 for n in numbers]


def Marker_Rect(center: QPointF) -> QRectF:
    """
    Description:
        The square a marker fills, CONST_SERIES_MARKER_PX across, on whole pixels round the pixel its centre is in.

    Args:
        (1) center [QPointF(object)]: The data point.

    Returns:
        (1) parameter [QRectF(object)]: The square.
    """

    half = CONST_SERIES_MARKER_PX // 2
    return QRectF(int(center.x()) - half, int(center.y()) - half, CONST_SERIES_MARKER_PX, CONST_SERIES_MARKER_PX)


def Draw_Marker(painter: QPainter, center: QPointF, color: str, hollow: bool = False) -> None:
    """
    Description:
        A filled square in its colour to its edge (no darker edge), or a hollow one: a 2 px ring round a transparent
        inside. Unantialiased.

    Args:
        (1) painter [QPainter(object)]: The painter.
        (2) center [QPointF(object)]: The data point.
        (3) color [string]: The series' token.
        (4) hollow [bool]: The ring alone.
    """

    square = Marker_Rect(center)
    path = QPainterPath()
    path.addRect(square)
    if hollow:
        edge = CONST_HOLLOW_MARKER_PX
        path.addRect(square.adjusted(edge, edge, -edge, -edge))
        path.setFillRule(Qt.OddEvenFill)
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing, False)
    painter.fillPath(path, QBrush(Style.Token_Color(color)))
    painter.restore()


def Outside_Markers(bounds: QRectF, centers: tp.List[QPointF]) -> QPainterPath:
    """
    Description:
        A clip of everything in bounds but the markers' squares, so a derived line is not drawn inside its rings.

    Args:
        (1) bounds [QRectF(object)]: The area.
        (2) centers [Vector<QPointF(object)>]: The markers.

    Returns:
        (1) parameter [QPainterPath(object)]: The clip.
    """

    path = QPainterPath()
    path.addRect(bounds)
    for center in centers:
        path.addRect(Marker_Rect(center))
    path.setFillRule(Qt.OddEvenFill)
    return path


def Series_Pen(color: str, derived: bool) -> QPen:
    """
    Description:
        A series' pen: 2 px, solid or the derived dash, flat caps.

    Args:
        (1) color [string]: The token.
        (2) derived [bool]: Dashed.

    Returns:
        (1) parameter [QPen(object)]: The pen.
    """

    pen = QPen(Style.Token_Color(color), CONST_SERIES_LINE_W, Qt.CustomDashLine if derived else Qt.SolidLine,
               Qt.FlatCap)
    if derived:
        pen.setDashPattern(CONST_DERIVED_DASH)
    return pen


class Line_Chart_Cls(QWidget):
    """
    Description:
        A line chart over evenly spaced x positions 1..n (an image, a cycle, a sample), with its series, guides,
        legend and hover read-out. Set_Data replaces everything and repaints.
    """

    def __init__(self, x_title: str, y_title: str, empty_text: str = 'No data yet.',
                 parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__x_title, self.__y_title, self.__empty_text = x_title, y_title, empty_text
        self.__series, self.__guides = [], []
        self.__count, self.__y_ticks, self.__y_max, self.__y_min = 0, [0.0, 1.0], 1.0, 0.0
        self.__hover = None

        self.setMinimumHeight(CONST_CHART_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    def Set_Data(self, series: tp.List[Series_Str], guides: tp.Sequence[Guide_Str] = (),
                 y_range: tp.Optional[tp.Tuple[float, float]] = None) -> None:
        """
        Description:
            Take the series (derived ones are drawn last, on top), the guides and an optional fixed y range (a
            percentage's 0-100); otherwise the axis runs from 0 to the nice tick at or above the highest value.

        Args:
            (1) series [Vector<Series_Str(object)>]: The series, in legend order.
            (2) guides [Vector<Guide_Str(object)>]: The threshold guides.
            (3) y_range [Tuple<float> 1x2 or None]: A fixed (low, high).
        """

        self.__series, self.__guides = list(series), list(guides)
        self.__count = max((len(s.Values) for s in series), default=0)
        values = [v for s in series for v in s.Values if v is not None]
        low, high = y_range if y_range else (0.0, max(values, default=1.0) or 1.0)
        self.__y_ticks = Nice_Ticks(low, high, 5)
        self.__y_min, self.__y_max = (low, high) if y_range else (self.__y_ticks[0], self.__y_ticks[-1])
        if self.__hover is not None and self.__hover >= self.__count:
            self.__hover = None
        self.update()

    def __Plot_Rect(self) -> QRectF:
        return QRectF(CONST_MARGIN_LEFT, CONST_MARGIN_TOP, max(1.0, self.width() - CONST_MARGIN_LEFT - CONST_MARGIN_RIGHT),
                      max(1.0, self.height() - CONST_MARGIN_TOP - CONST_MARGIN_BOTTOM))

    def __Px_X(self, index: int, rect: QRectF) -> float:
        span = (self.__count + 0.5) - 0.5
        return rect.left() + ((index + 1) - 0.5) / span * rect.width() if span else rect.center().x()

    def __Px_Y(self, value: float, rect: QRectF) -> float:
        span = self.__y_max - self.__y_min
        return rect.bottom() - (value - self.__y_min) / span * rect.height() if span else rect.center().y()

    # << QT OVERRIDE >> #
    def paintEvent(self, _event: tp.Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.__Plot_Rect()
        if not self.__count:
            painter.setPen(Style.Token_Color(Style.CONST_INK_MUTE))
            painter.setFont(Font(Style.CONST_TYPE_SCALE[2]))
            painter.drawText(self.rect(), Qt.AlignCenter, self.__empty_text)
            painter.end()
            return
        self.__Draw_Grid(painter, rect)
        self.__Draw_Titles(painter, rect)
        self.__Draw_Guides(painter, rect)
        for series in sorted(self.__series, key=lambda s: s.Derived):
            self.__Draw_Series(painter, rect, series)
        self.__Draw_Legend(painter, rect)
        if self.__hover is not None:
            self.__Draw_Hover(painter, rect)
        painter.end()

    def __Draw_Grid(self, painter: QPainter, rect: QRectF) -> None:
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        for value in self.__y_ticks:
            if value < self.__y_min - 1e-9 or value > self.__y_max + 1e-9:
                continue
            y = self.__Px_Y(value, rect)
            painter.setPen(QPen(Style.Token_Color(Style.CONST_LINE), 1))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(Style.Token_Color(Style.CONST_INK_MUTE))
            label = '%d' % round(value) if abs(value - round(value)) < 1e-9 else '%.1f' % value
            painter.drawText(QRectF(0, y - 8, CONST_MARGIN_LEFT - 8, 16), Qt.AlignRight | Qt.AlignVCenter, label)
        painter.setPen(QPen(Style.Token_Color(Style.CONST_CARD_BORDER), 1))
        painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
        labelled = set(Thin_Label_Indices(self.__count, max(2, int(self.width() / CONST_X_LABEL_PX) or 2)))
        for index in sorted(labelled):
            x = self.__Px_X(index, rect)
            painter.setPen(QPen(Style.Token_Color(Style.CONST_CARD_BORDER), 1))
            painter.drawLine(QPointF(x, rect.bottom()), QPointF(x, rect.bottom() + 4))
            painter.setPen(Style.Token_Color(Style.CONST_INK_MUTE))
            painter.drawText(QRectF(x - CONST_X_LABEL_PX / 2.0, rect.bottom() + 6, CONST_X_LABEL_PX, 14),
                             Qt.AlignHCenter | Qt.AlignTop, str(index + 1))

    def __Draw_Titles(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(Style.Token_Color(Style.CONST_DETECTION_INK))
        painter.setFont(Font(Style.CONST_TYPE_SCALE[1]))
        painter.drawText(QRectF(rect.left(), self.height() - 18, rect.width(), 16), Qt.AlignHCenter | Qt.AlignVCenter,
                         self.__x_title)
        painter.save()
        painter.translate(14, rect.center().y())
        painter.rotate(-90)
        painter.drawText(QRectF(-rect.height() / 2.0, -8, rect.height(), 16), Qt.AlignHCenter | Qt.AlignVCenter,
                         self.__y_title)
        painter.restore()

    def __Draw_Guides(self, painter: QPainter, rect: QRectF) -> None:
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        for guide in self.__guides:
            y = self.__Px_Y(guide.Value, rect)
            pen = QPen(Style.Token_Color(Style.CONST_DETECTION_INK), 1, Qt.CustomDashLine, Qt.FlatCap)
            pen.setDashPattern(guide.Dash)
            painter.setPen(pen)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(Style.Token_Color(Style.CONST_DETECTION_INK))
            width = metrics.horizontalAdvance(guide.Label)
            painter.drawText(QRectF(rect.right() - width - 6, y - 16, width + 4, 14), Qt.AlignRight | Qt.AlignVCenter,
                             guide.Label)

    def __Points(self, rect: QRectF, series: Series_Str) -> tp.List[tp.Optional[QPointF]]:
        return [QPointF(self.__Px_X(i, rect), self.__Px_Y(v, rect)) if v is not None else None
                for i, v in enumerate(series.Values)]

    def __Draw_Series(self, painter: QPainter, rect: QRectF, series: Series_Str) -> None:
        points = self.__Points(rect, series)
        marked = rect.width() / max(1, self.__count) >= CONST_MARKER_MIN_SPACING
        centers = [pt for pt in points if pt is not None] if marked else []
        painter.save()
        if series.Derived and centers:
            painter.setClipPath(Outside_Markers(QRectF(self.rect()), centers))
        # A solid series line keeps Qt's default square cap, as AnyScan draws it; a dashed one is flat-capped.
        painter.setPen(Series_Pen(series.Color, True) if series.Derived
                       else QPen(Style.Token_Color(series.Color), CONST_SERIES_LINE_W))
        for a, b in zip(points, points[1:]):
            if a is not None and b is not None:
                painter.drawLine(a, b)
        painter.restore()
        for center in centers:
            Draw_Marker(painter, center, series.Color, hollow=series.Derived)

    def __Draw_Legend(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            One row of line samples and labels top-right ABOVE the plot, never on the data: each sample is its
            series' own line, 26 px long (three dashes and two gaps of the derived dash), with its square marker.
        """

        if not self.__series:
            return
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        gap = 14
        sample = (3 * CONST_DERIVED_DASH[0] + 2 * CONST_DERIVED_DASH[1]) * CONST_SERIES_LINE_W
        widths = [sample + 5 + metrics.horizontalAdvance(s.Label) for s in self.__series]
        x = rect.right() - (sum(widths) + gap * (len(widths) - 1))
        y = rect.top() - 24
        for series, width in zip(self.__series, widths):
            mid = int(y + 6) + 0.5
            center = QPointF(x + sample / 2.0, mid)
            painter.save()
            if series.Derived:
                painter.setClipPath(Outside_Markers(QRectF(self.rect()), [center]))
            painter.setPen(Series_Pen(series.Color, series.Derived))
            painter.drawLine(QPointF(x, mid), QPointF(x + sample, mid))
            painter.restore()
            Draw_Marker(painter, center, series.Color, hollow=series.Derived)
            painter.setPen(Style.Token_Color(Style.CONST_DETECTION_INK))
            painter.drawText(QRectF(x + sample + 5, y - 1, width, 14), Qt.AlignLeft | Qt.AlignVCenter, series.Label)
            x += width + gap

    def __Draw_Hover(self, painter: QPainter, rect: QRectF) -> None:
        x = self.__Px_X(self.__hover, rect)
        painter.setPen(QPen(Style.Token_Color(Style.CONST_CARD_BORDER), 1, Qt.DashLine))
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        lines = [('#%d' % (self.__hover + 1), Style.CONST_INK)]
        for series in self.__series:
            value = series.Values[self.__hover] if self.__hover < len(series.Values) else None
            lines.append(('%s: %s' % (series.Label, Style.CONST_NO_VALUE if value is None else '%g' % value),
                          Style.CONST_DETECTION_INK))
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        pad, line_h = 7, 15
        width = max(metrics.horizontalAdvance(text) for text, _ in lines) + 2 * pad
        height = line_h * len(lines) + 2 * pad
        bx = max(min(x + 10, rect.right() - width), rect.left())
        by = rect.top() + 6
        painter.setBrush(QBrush(Style.Token_Color(Style.CONST_CARD)))
        painter.setPen(QPen(Style.Token_Color(Style.CONST_CARD_BORDER), 1))
        painter.drawRect(QRectF(bx, by, width, height))
        ty = by + pad
        for text, color in lines:
            painter.setPen(Style.Token_Color(color))
            painter.drawText(QRectF(bx + pad, ty, width - 2 * pad, line_h), Qt.AlignLeft | Qt.AlignVCenter, text)
            ty += line_h

    # << QT OVERRIDE >> #
    def mouseMoveEvent(self, event: tp.Any) -> None:
        if not self.__count:
            return
        rect = self.__Plot_Rect()
        xs = [self.__Px_X(i, rect) for i in range(self.__count)]
        index = min(range(len(xs)), key=lambda i: abs(xs[i] - event.x()))
        if index != self.__hover:
            self.__hover = index
            self.update()

    # << QT OVERRIDE >> #
    def leaveEvent(self, _event: tp.Any) -> None:
        if self.__hover is not None:
            self.__hover = None
            self.update()


def Chart_Card(icon: str, title: str, subtitle: str, chart: QWidget) -> Card_Cls:
    """
    Description:
        A chart in its card: the head (pixel icon and title), a one-line subtitle in the muted ink (10.5 pt), the chart.

    Args:
        (1) icon [string]: The head's pixel icon.
        (2) title [string]: The title.
        (3) subtitle [string]: What the chart shows, one sentence.
        (4) chart [QWidget(object)]: The chart.

    Returns:
        (1) parameter [Card_Cls(object)]: The card.
    """

    card = Card_Cls()
    card.box.addWidget(Card_Head_Cls(icon, title))
    note = QLabel(subtitle)
    note.setFont(Font(Style.CONST_TYPE_SCALE[1]))
    note.setStyleSheet('color: %s; padding: 0 2px 8px 2px;' % Style.CONST_INK_MUTE)
    card.box.addWidget(note)
    card.box.addWidget(chart)
    return card
