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
# File Name: ../UI/Views/Trends.py
## =========================================================================== ##

# System (Default)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFontMetrics
from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QSizePolicy
# Custom Lib.: AnyScan UI — design tokens, style helpers and shared widgets
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font
#   ../UI/Widgets
from UI.Widgets import Card_Cls, Card_Head_Cls
# Custom Lib.: AnyScan domain — the Qt-free trend model and the plotting maths
#   ../Reporting/Trends
from Reporting.Trends import Nice_Ticks, Value_To_Pixel, Nearest_Index, Thin_Label_Indices
#   ../Parameters/Theme
from Parameters.Theme import Verdict_Color, Detection_Color
#   ../Parameters/Vision
from Parameters.Vision import Confidence_Thresholds_Str

"""
Description:
    Initialization of constants.

    The Trends view: two hand-drawn charts of the current run, sharing ONE chart base
    (Chart_Base_Cls) that draws the frame, the nice-stepped ticks and gridlines, the axis titles
    with units, the legend and the hover read-out — the two charts differ only in the series they
    paint over it, not in the furniture around them. All colours come from Theme, all sizes from
    the type scale, and the plotting maths (tick values, value→pixel, hover hit-test, label
    thinning) live in the Qt-free Reporting.Trends so they are unit-tested without a widget. Both
    charts and the status bar read the one Trends accumulator, so the last run-mean point and
    the status figure are the same number.
"""

# The plot margins inside the widget (px): room for the y tick labels + title on the left, the x
# tick labels + title at the bottom, and a little breathing space top and right.
#   Unit [int]
CONST_MARGIN_LEFT = 60
CONST_MARGIN_BOTTOM = 52
CONST_MARGIN_TOP = 34
CONST_MARGIN_RIGHT = 18
# The approximate pixels one x tick label needs; the label thinning keeps them from overlapping.
#   Unit [int]
CONST_X_LABEL_PX = 46
# The scored-object dot radius, and the jitter spread as a fraction of the column spacing, so a
# frame's several dots fan out horizontally instead of stacking into one.
#   Unit [float]
CONST_DOT_RADIUS = 3.0
CONST_JITTER_FRACTION = 0.55
# The minimum column spacing (px) at which the object chart still draws a marker per image.
#   Unit [float]
CONST_MARKER_MIN_SPACING = 10.0
# The minimum widget height so a chart stays readable at a few hundred points.
#   Unit [int]
CONST_CHART_MIN_HEIGHT = 240


class Chart_Base_Cls(QWidget):
    """
    Description:
        The shared chart canvas: it owns the plot frame, the nice-stepped ticks and gridlines, the
        axis titles, the legend and the hover read-out, and calls a subclass hook to paint the
        series over that furniture. A subclass configures the axes and columns through the
        protected setters, implements the series painting and the hover text, and never re-draws
        the frame itself.

    Initialization of the Class:
        Args:
            (1) x_title [string]: The x-axis title (with its unit).
            (2) y_title [string]: The y-axis title (with its unit).
    """

    def __init__(self, x_title: str, y_title: str, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__x_title = x_title
        self.__y_title = y_title
        # The data ranges and ticks, set by the subclass before each update.
        self._x_min, self._x_max = 0.0, 1.0
        self._y_min, self._y_max = 0.0, 1.0
        self._x_ticks, self._y_ticks = [], []
        self._x_tick_text = {}                 # tick value -> label (only the ones that get one)
        self._legend = []                      # [(label, color_hex)]
        self._columns = []                     # per-image x VALUES (1..n), for the hover hit-test
        self._hover = None                     # the hovered column index, or None
        self._empty_text = 'No analyses in this run yet.'

        self.setMinimumHeight(CONST_CHART_MIN_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

    # ------------------------------------------------------------------ subclass API

    def _Set_Axes(self, x_min: float, x_max: float, y_min: float, y_max: float,
                  x_ticks: tp.List[float], y_ticks: tp.List[float],
                  x_tick_text: tp.Dict[float, str]) -> None:
        """
        Description:
            Store the data ranges, the tick values and the (already thinned) x tick labels the
            shared frame is drawn from.

        Args:
            (1 - 4) x_min, x_max, y_min, y_max [float]: The data ranges of each axis.
            (5 - 6) x_ticks, y_ticks [Vector<float>]: The tick values on each axis.
            (7) x_tick_text [Dict<float, string>]: The label for each x tick that gets one.
        """

        self._x_min, self._x_max, self._y_min, self._y_max = x_min, x_max, y_min, y_max
        self._x_ticks, self._y_ticks, self._x_tick_text = x_ticks, y_ticks, x_tick_text

    def _Set_Legend(self, legend: tp.List[tp.Tuple[str, str]]) -> None:
        """
        Description:
            Store the legend items the base draws top-right.

        Args:
            (1) legend [Vector<Tuple<string> 1x2>]: The items as (label, colour hex).
        """

        self._legend = legend

    def _Set_Columns(self, x_values: tp.List[float]) -> None:
        """
        Description:
            Store the per-image x VALUES the hover hit-test snaps to, dropping a stale hover.

        Args:
            (1) x_values [Vector<float>]: The image x values (1..n), in order.
        """

        self._columns = x_values
        if self._hover is not None and self._hover >= len(x_values):
            self._hover = None

    def _Paint_Series(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Paint the data series over the shared frame — the subclass' responsibility.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle in widget pixels.
        """

        raise NotImplementedError

    def _Hover_Lines(self, index: int) -> tp.List[tp.Tuple[str, str]]:
        """
        Description:
            The hover read-out lines for one column — the subclass' responsibility.

        Args:
            (1) index [int]: The hovered column index.

        Returns:
            (1) parameter [Vector<Tuple<string> 1x2>]: The lines as (text, colour hex).
        """

        raise NotImplementedError

    # ------------------------------------------------------------------ geometry

    def _Plot_Rect(self) -> QRectF:
        """
        Description:
            The inner plotting rectangle (the widget less the axis margins).

        Returns:
            (1) parameter [QRectF]: The plot area in widget pixels.
        """

        return QRectF(CONST_MARGIN_LEFT, CONST_MARGIN_TOP,
                      max(1.0, self.width() - CONST_MARGIN_LEFT - CONST_MARGIN_RIGHT),
                      max(1.0, self.height() - CONST_MARGIN_TOP - CONST_MARGIN_BOTTOM))

    def _Px_X(self, value: float, rect: QRectF) -> float:
        """
        Description:
            The x pixel of a data x value within the plot rect.

        Args:
            (1) value [float]: The data x value.
            (2) rect [QRectF]: The plot rectangle.

        Returns:
            (1) parameter [float]: The x pixel.
        """

        return Value_To_Pixel(value, self._x_min, self._x_max, rect.left(), rect.right())

    def _Px_Y(self, value: float, rect: QRectF) -> float:
        """
        Description:
            The y pixel of a data y value (inverted: larger values sit higher on screen).

        Args:
            (1) value [float]: The data y value.
            (2) rect [QRectF]: The plot rectangle.

        Returns:
            (1) parameter [float]: The y pixel.
        """

        return Value_To_Pixel(value, self._y_min, self._y_max, rect.bottom(), rect.top())

    # ------------------------------------------------------------------ painting

    # << QT OVERRIDE >> #
    def paintEvent(self, _event: tp.Any) -> None:
        """
        Description:
            Draw the whole chart: the gridlines and ticks, the axis titles, the legend, the series
            (via the subclass) and, when a column is hovered, the guide line and the read-out. When
            there is no data an empty message is centred instead.
        """

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self._Plot_Rect()

        if not self._columns:
            painter.setPen(QColor(Style.CONST_INK_MUTE))
            painter.setFont(Font(Style.CONST_TYPE_SCALE[2]))
            painter.drawText(self.rect(), Qt.AlignCenter, self._empty_text)
            painter.end()
            return

        self.__Draw_Grid_And_Ticks(painter, rect)
        self.__Draw_Axis_Titles(painter, rect)
        self._Paint_Series(painter, rect)
        self.__Draw_Legend(painter, rect)
        if self._hover is not None and 0 <= self._hover < len(self._columns):
            self.__Draw_Hover(painter, rect)
        painter.end()

    def __Draw_Grid_And_Ticks(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw the horizontal gridlines and y labels at the y ticks, and the x axis line with its
            tick marks and thinned x labels.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        for value in self._y_ticks:
            if value < self._y_min - 1e-9 or value > self._y_max + 1e-9:
                continue
            y = self._Px_Y(value, rect)
            painter.setPen(QPen(QColor(Style.CONST_LINE), 1))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(QColor(Style.CONST_INK_MUTE))
            label = self.__Format_Tick(value)
            painter.drawText(QRectF(0, y - 8, CONST_MARGIN_LEFT - 8, 16),
                             Qt.AlignRight | Qt.AlignVCenter, label)
        # The x axis line.
        painter.setPen(QPen(QColor(Style.CONST_CARD_BORDER), 1))
        painter.drawLine(QPointF(rect.left(), rect.bottom()), QPointF(rect.right(), rect.bottom()))
        for value in self._x_ticks:
            text = self._x_tick_text.get(value)
            if text is None:
                continue
            x = self._Px_X(value, rect)
            painter.setPen(QPen(QColor(Style.CONST_CARD_BORDER), 1))
            painter.drawLine(QPointF(x, rect.bottom()), QPointF(x, rect.bottom() + 4))
            painter.setPen(QColor(Style.CONST_INK_MUTE))
            painter.drawText(QRectF(x - CONST_X_LABEL_PX / 2.0, rect.bottom() + 6,
                                    CONST_X_LABEL_PX, 14), Qt.AlignHCenter | Qt.AlignTop, text)

    def __Format_Tick(self, value: float) -> str:
        """
        Description:
            A y tick value as text: an integer where it is whole, else one decimal.

        Args:
            (1) value [float]: The tick value.

        Returns:
            (1) parameter [string]: The formatted label.
        """

        return '%d' % round(value) if abs(value - round(value)) < 1e-9 else '%.1f' % value

    def __Draw_Axis_Titles(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw the x title centred under the axis and the y title rotated at the far left.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        painter.setPen(QColor(Style.CONST_INK_SOFT))
        painter.setFont(Font(Style.CONST_TYPE_SCALE[1]))
        painter.drawText(QRectF(rect.left(), self.height() - 18, rect.width(), 16),
                         Qt.AlignHCenter | Qt.AlignVCenter, self.__x_title)
        painter.save()
        painter.translate(14, rect.center().y())
        painter.rotate(-90)
        painter.drawText(QRectF(-rect.height() / 2.0, -8, rect.height(), 16),
                         Qt.AlignHCenter | Qt.AlignVCenter, self.__y_title)
        painter.restore()

    def __Draw_Legend(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw a one-row legend of colour swatches and labels, top-right ABOVE the plot, so it
            never sits on the data.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        if not self._legend:
            return
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        gap, swatch = 14, 9
        widths = [swatch + 5 + metrics.horizontalAdvance(label) for label, _ in self._legend]
        total = sum(widths) + gap * (len(self._legend) - 1)
        x = rect.right() - total
        y = rect.top() - 24
        for (label, color), width in zip(self._legend, widths):
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(x, y + 2, swatch, swatch))
            painter.setPen(QColor(Style.CONST_INK_SOFT))
            painter.drawText(QRectF(x + swatch + 5, y - 1, width, 14),
                             Qt.AlignLeft | Qt.AlignVCenter, label)
            x += width + gap

    def __Draw_Hover(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw a vertical guide at the hovered column and a small read-out box near the top, from
            the subclass' hover lines.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        value = self._columns[self._hover]
        x = self._Px_X(value, rect)
        painter.setPen(QPen(QColor(Style.CONST_CARD_BORDER), 1, Qt.DashLine))
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

        lines = self._Hover_Lines(self._hover)
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        pad, line_h = 7, 15
        width = max(metrics.horizontalAdvance(text) for text, _ in lines) + 2 * pad
        height = line_h * len(lines) + 2 * pad
        bx = min(x + 10, rect.right() - width)
        bx = max(bx, rect.left())
        by = rect.top() + 6
        painter.setBrush(QBrush(QColor(Style.CONST_CARD)))
        painter.setPen(QPen(QColor(Style.CONST_CARD_BORDER), 1))
        painter.drawRoundedRect(QRectF(bx, by, width, height), 5, 5)
        ty = by + pad
        for text, color in lines:
            painter.setPen(QColor(color))
            painter.drawText(QRectF(bx + pad, ty, width - 2 * pad, line_h),
                             Qt.AlignLeft | Qt.AlignVCenter, text)
            ty += line_h

    # << QT OVERRIDE >> #
    def mouseMoveEvent(self, event: tp.Any) -> None:
        """
        Description:
            Track the cursor: pick the nearest image column and repaint the read-out. Off to the
            side of every column the read-out clears rather than snapping to the end.

        Args:
            (1) event [QMouseEvent(object)]: The move event.
        """

        rect = self._Plot_Rect()
        xs = [self._Px_X(value, rect) for value in self._columns]
        index = Nearest_Index(float(event.x()), xs, max_distance=max(20.0, rect.width()))
        if index != self._hover:
            self._hover = index
            self.update()

    # << QT OVERRIDE >> #
    def leaveEvent(self, _event: tp.Any) -> None:
        """
        Description:
            Clear the hover read-out when the cursor leaves the chart.
        """

        if self._hover is not None:
            self._hover = None
            self.update()


class Objects_Chart_Cls(Chart_Base_Cls):
    """
    Description:
        Chart 1 — the cumulative object count against the analysed-image index. One Total series,
        plus OK and NOK series when the run classifies. The final Total point equals the status
        bar's OBJECTS DETECTED and the last x equals IMAGES ANALYSED; a failed analysis never
        advances x, because the accumulator is only fed successful analyses.

    Initialization of the Class:
        Args:
            (none)
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__('Analysed image', 'Objects (cumulative)', parent)
        self.__rows = []
        self.__classified = False

    def Set_Data(self, rows: tp.List[tp.Any], classification_enabled: bool) -> None:
        """
        Description:
            Take the accumulator's per-image rows and the run's classification flag, recompute the
            axes and ticks, and repaint.

        Args:
            (1) rows [Vector<Trend_Image_Str(object)>]: The per-image trend rows.
            (2) classification_enabled [bool]: Whether to draw the OK/NOK split.
        """

        self.__rows, self.__classified = rows, classification_enabled
        n = len(rows)
        y_max = max((row.Cumulative_Total for row in rows), default=1) or 1
        x_ticks = [float(row.Index) for row in rows]
        labeled = set(Thin_Label_Indices(n, max(2, int(self.width() / CONST_X_LABEL_PX) or 2)))
        x_text = {float(rows[i].Index): str(rows[i].Index) for i in labeled} if rows else {}
        y_ticks = Nice_Ticks(0.0, y_max, 5)
        # The axis ends ON the top nice tick, so the highest point is never above the last gridline.
        self._Set_Axes(0.5, n + 0.5 if n else 1.5, 0.0, y_ticks[-1], x_ticks, y_ticks, x_text)
        legend = [('Total', Style.CONST_INK)]
        if classification_enabled:
            legend += [('OK', Verdict_Color('OK')[0]), ('NOK', Verdict_Color('NOK')[0])]
        self._Set_Legend(legend)
        self._Set_Columns([float(row.Index) for row in rows])
        self.update()

    def _Paint_Series(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw the cumulative-count line(s) — Total, and OK/NOK when the run classifies — with a
            small marker at each image.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        series = [('Cumulative_Total', Style.CONST_INK)]
        if self.__classified:
            series += [('Cumulative_Ok', Verdict_Color('OK')[0]),
                       ('Cumulative_Nok', Verdict_Color('NOK')[0])]
        for attr, color in series:
            painter.setPen(QPen(QColor(color), 2))
            previous = None
            for row in self.__rows:
                point = QPointF(self._Px_X(row.Index, rect), self._Px_Y(getattr(row, attr), rect))
                if previous is not None:
                    painter.drawLine(previous, point)
                previous = point
            # Point markers only while the columns are wide enough to read them; on a dense run
            # they would bead the line into a blur, and the hover still reads each image.
            if rect.width() / max(1, len(self.__rows)) < CONST_MARKER_MIN_SPACING:
                continue
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            for row in self.__rows:
                point = QPointF(self._Px_X(row.Index, rect), self._Px_Y(getattr(row, attr), rect))
                painter.drawEllipse(point, 2.5, 2.5)

    def _Hover_Lines(self, index: int) -> tp.List[tp.Tuple[str, str]]:
        """
        Description:
            The hover read-out for an image: its index, the objects THIS image added, and the
            running total (with the OK/NOK split when the run classifies).

        Args:
            (1) index [int]: The hovered image column index.

        Returns:
            (1) parameter [Vector<Tuple<string> 1x2>]: The read-out lines as (text, colour hex).
        """

        row = self.__rows[index]
        lines = [('Image %d' % row.Index, Style.CONST_INK),
                 ('This image: +%d' % row.Total, Style.CONST_INK_SOFT),
                 ('Total: %d' % row.Cumulative_Total, Style.CONST_INK)]
        if self.__classified:
            lines.append(('OK %d · NOK %d' % (row.Cumulative_Ok, row.Cumulative_Nok),
                          Style.CONST_INK_SOFT))
        return lines


class Confidence_Chart_Cls(Chart_Base_Cls):
    """
    Description:
        Chart 2 — confidence against the analysed-image index: one dot per SCORED object at its
        image (jittered horizontally so a frame's objects do not stack), the frame mean and the
        running run mean as two lines, and dashed reference lines at the §5 warn/error
        thresholds. Unscored objects are not plotted — that would draw a false 0% — and are shown
        in the hover count instead. Dots take their verdict colour when the run classifies.

    Initialization of the Class:
        Args:
            (none)
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__('Analysed image', 'Confidence (%)', parent)
        self.__rows = []
        self.__classified = False
        self.__thresholds = None

    def Set_Data(self, rows: tp.List[tp.Any], classification_enabled: bool,
                 Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        """
        Description:
            Take the accumulator's per-image rows, the run's classification flag and the
            thresholds in force, set the fixed 0..100% axis, thin the x labels, and repaint.

        Args:
            (1) rows [Vector<Trend_Image_Str(object)>]: The per-image trend rows.
            (2) classification_enabled [bool]: Whether the dots take their verdict colour.
            (3) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: Where the dashed
                warn / error reference lines are drawn.
        """

        self.__rows, self.__classified = rows, classification_enabled
        self.__thresholds = Confidence_Thresholds_Str
        n = len(rows)
        labeled = set(Thin_Label_Indices(n, max(2, int(self.width() / CONST_X_LABEL_PX) or 2)))
        x_text = {float(rows[i].Index): str(rows[i].Index) for i in labeled} if rows else {}
        self._Set_Axes(0.5, n + 0.5 if n else 1.5, 0.0, 100.0,
                       [float(row.Index) for row in rows], Nice_Ticks(0.0, 100.0, 5), x_text)
        self._Set_Legend([('Frame mean', Style.CONST_INK_MUTE), ('Run mean', Style.CONST_INK)])
        self._Set_Columns([float(row.Index) for row in rows])
        self.update()

    def _Paint_Series(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw the dashed warn/error reference lines, the jittered per-object scored dots, and
            the frame-mean and run-mean lines over them.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        # The dashed reference lines at the warn / error thresholds (§5), behind everything.
        thresholds = self.__thresholds
        references = (() if thresholds is None else
                      ((thresholds.Warn_Below, Style.CONST_LOG_WARNING),
                       (thresholds.Error_Below, Style.CONST_LOG_ERROR)))
        for value, color in references:
            y = self._Px_Y(value, rect)
            painter.setPen(QPen(QColor(color), 1, Qt.DashLine))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        # The scored-object dots, jittered horizontally within their column.
        spacing = rect.width() / max(1, len(self.__rows))
        # On the white card the neutral dot is the detection INK twin: the box value is tuned to be
        # drawn on the green frame and would all but vanish here.
        neutral = Detection_Color()[1]
        painter.setPen(Qt.NoPen)
        for row in self.__rows:
            count = len(row.Objects)
            for position, obj in enumerate(row.Objects):
                offset = 0.0 if count == 1 else ((position - (count - 1) / 2.0)
                                                 * (spacing * CONST_JITTER_FRACTION) / count)
                color = Verdict_Color(obj.Verdict)[0] if self.__classified else neutral
                dot = QColor(color)
                dot.setAlpha(200)
                painter.setBrush(QBrush(dot))
                painter.drawEllipse(QPointF(self._Px_X(row.Index, rect) + offset,
                                            self._Px_Y(obj.Confidence, rect)),
                                    CONST_DOT_RADIUS, CONST_DOT_RADIUS)
        # The two mean lines over the dots.
        self.__Draw_Mean_Line(painter, rect, 'Frame_Mean', Style.CONST_INK_MUTE)
        self.__Draw_Mean_Line(painter, rect, 'Run_Mean', Style.CONST_INK)

    def __Draw_Mean_Line(self, painter: QPainter, rect: QRectF, attr: str, color: str) -> None:
        """
        Description:
            Draw one mean line, breaking it across images that have no mean (nothing scored yet)
            rather than drawing a segment through a gap.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
            (3) attr [string]: The row attribute to plot ('Frame_Mean' or 'Run_Mean').
            (4) color [string]: The line colour hex.
        """

        painter.setPen(QPen(QColor(color), 2))
        previous = None
        for row in self.__rows:
            value = getattr(row, attr)
            if value is None:
                previous = None
                continue
            point = QPointF(self._Px_X(row.Index, rect), self._Px_Y(value, rect))
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point

    def _Hover_Lines(self, index: int) -> tp.List[tp.Tuple[str, str]]:
        """
        Description:
            The hover read-out for an image: its index, the frame and run means, the scored
            count, and the unscored count when any (the objects NOT plotted, so the dots reconcile).

        Args:
            (1) index [int]: The hovered image column index.

        Returns:
            (1) parameter [Vector<Tuple<string> 1x2>]: The read-out lines as (text, colour hex).
        """

        row = self.__rows[index]
        frame = '%d%%' % row.Frame_Mean if row.Frame_Mean is not None else '—'
        run = '%d%%' % row.Run_Mean if row.Run_Mean is not None else '—'
        lines = [('Image %d' % row.Index, Style.CONST_INK),
                 ('Frame mean: %s' % frame, Style.CONST_INK_MUTE),
                 ('Run mean: %s' % run, Style.CONST_INK),
                 ('Scored: %d' % len(row.Objects), Style.CONST_INK_SOFT)]
        if row.Unscored:
            lines.append(('Unscored: %d' % row.Unscored, Style.CONST_INK_SOFT))
        return lines


class Trends_View_Cls(QWidget):
    """
    Description:
        The Trends view: the two run charts stacked in cards. It holds no data of its own — the
        window hands it the accumulator's rows on Refresh, and it forwards them to the two charts.

    Initialization of the Class:
        Args:
            (1) classification_enabled [bool]: Whether the run classifies (drives the OK/NOK split
                                               and the verdict dot colours).
            (2) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: REQUIRED,
                keyword-only: where the confidence chart's reference lines are drawn.
    """

    def __init__(self, classification_enabled: bool = False,
                 parent: tp.Optional[QWidget] = None, *,
                 Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        super().__init__(parent)

        # << PRIVATE >> #
        self.__classification_enabled = classification_enabled
        self.__thresholds = Confidence_Thresholds_Str
        self.__accumulator = None

        grid = QGridLayout(self)
        grid.setSpacing(Style.CONST_GAP)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.__Chart_Card('Detected objects',
                                          'Cumulative objects found across the run’s images.',
                                          self.__Build_Objects_Chart()), 0, 0)
        grid.addWidget(self.__Chart_Card('Confidence',
                                         'Per-object scores, the frame mean and the running '
                                         'run mean.', self.__Build_Confidence_Chart()), 1, 0)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        # Hand the charts the flag and thresholds now, so the first paint already has them.
        self.Refresh()

    def __Build_Objects_Chart(self) -> Objects_Chart_Cls:
        """
        Description:
            Build and keep the object-count chart.

        Returns:
            (1) parameter [Objects_Chart_Cls(object)]: The chart.
        """

        self.__objects_chart = Objects_Chart_Cls()
        return self.__objects_chart

    def __Build_Confidence_Chart(self) -> Confidence_Chart_Cls:
        """
        Description:
            Build and keep the confidence chart.

        Returns:
            (1) parameter [Confidence_Chart_Cls(object)]: The chart.
        """

        self.__confidence_chart = Confidence_Chart_Cls()
        return self.__confidence_chart

    def __Chart_Card(self, title: str, subtitle: str, chart: QWidget) -> Card_Cls:
        """
        Description:
            One chart wrapped in the console's card chrome — a head with the title and a one-line
            subtitle above the chart canvas.

        Args:
            (1) title [string]: The card title.
            (2) subtitle [string]: The one-line description under the title.
            (3) chart [QWidget(object)]: The chart canvas.

        Returns:
            (1) parameter [Card_Cls(object)]: The chart card.
        """

        card = Card_Cls()
        card.box.addWidget(Card_Head_Cls('reading', title))
        note = QLabel(subtitle)
        note.setFont(Font(Style.CONST_TYPE_SCALE[1]))
        note.setStyleSheet('color: %s; padding: 0 2px 8px 2px;' % Style.CONST_INK_MUTE)
        card.box.addWidget(note)
        card.box.addWidget(chart)
        return card

    def Set_Accumulator(self, accumulator: tp.Any) -> None:
        """
        Description:
            Bind the run's Trends accumulator (the one the status bar also reads). Refresh draws
            from it, so the charts and the status figures share a single source.

        Args:
            (1) accumulator [Trends_Accumulator_Cls(object)]: The run accumulator.
        """

        self.__accumulator = accumulator

    def Refresh(self) -> None:
        """
        Description:
            Redraw both charts from the bound accumulator's current rows.
        """

        rows = self.__accumulator.Images() if self.__accumulator is not None else []
        self.__objects_chart.Set_Data(rows, self.__classification_enabled)
        self.__confidence_chart.Set_Data(rows, self.__classification_enabled, self.__thresholds)

    def Set_Configuration(self, classification_enabled: bool,
                          Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        """
        Description:
            Adopt a newly loaded configuration's classification flag and thresholds, and redraw.

        Args:
            (1) classification_enabled [bool]: Whether the configuration classifies.
            (2) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: Its thresholds.
        """

        self.__classification_enabled = classification_enabled
        self.__thresholds = Confidence_Thresholds_Str
        self.Refresh()
