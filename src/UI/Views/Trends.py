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
from Parameters.Theme import Verdict_Color, Detection_Mask_Outline, CONST_DETECTION_INK
#   ../Parameters/Vision
from Parameters.Vision import Confidence_Thresholds_Str
#   ../Parameters/General — the one default for the classification flag
from Parameters.General import CONST_CLASSIFICATION_ENABLED_DEFAULT

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
# ONE line width and ONE marker size for every series of the Trends view (the owner's rule, 2026-10-18): Total, OK,
# NOK, Warning, the frame mean and the run mean, and the legend samples that stand for them. 3 px and a radius of 4 px
# (8 px across) are the values the light states were given on 2026-10-16 so the amber Warning (1.62:1 on the white
# card) reads by its line and its markers (docs/design-decisions.md, *Each state has one colour in every view*); every
# series now takes them. A marker is filled in its series' colour, no edge of another colour. The threshold lines are
# guides, not data: they stay 1 px (below).
#   Unit [float] (px)
CONST_SERIES_LINE_W = 3.0
CONST_SERIES_MARKER_RADIUS = 4.0
# The confidence chart's two series are told apart by pattern and colour only, at that one width: the frame mean solid
# with a marker at every analysed image, in the muted ink (Style.CONST_INK_MUTE #6F5783, 6.24:1 on white); the run mean
# dashed, no markers, in the lighter neutral grey (Theme.Detection_Mask_Outline #817A8A, 4.13:1; ΔE 21.8 and 1.51:1
# from the muted ink, the theme's farthest neutral pair). The run mean is drawn over the frame mean's line and under its
# markers, so where the two are equal the dashes alternate with the frame mean's colour and the markers still show.
# The dash pattern is in line widths (Qt), dash then gap: 9 px and 6 px.
#   Unit [Vector<float>] (line widths)
CONST_RUN_MEAN_DASH = [3.0, 2.0]
# The two confidence-threshold lines: 1 px, both in the neutral grey ink (Theme.CONST_DETECTION_INK #655E6D, 6.22:1 on
# white), no verdict's colour nor the log's error red (the owner's rule, 2026-10-18), told apart by their dash, long at
# the warning threshold and short at the error threshold, and by their labels. Patterns in px (1 px lines), dash then
# gap.
#   Unit [Vector<float>] (px)
CONST_WARN_LINE_DASH = [6.0, 4.0]
CONST_ERROR_LINE_DASH = [2.0, 3.0]
# The minimum column spacing (px) at which the object chart still draws a marker per image.
#   Unit [float]
CONST_MARKER_MIN_SPACING = 10.0
# The minimum widget height so a chart stays readable at a few hundred points.
#   Unit [int]
CONST_CHART_MIN_HEIGHT = 240


def _Verdict_Series() -> tp.List[tp.Tuple[str, str, str]]:
    """
    Description:
        The objects chart's per-state series when the run classifies, as (label, Trend_Image_Str attribute,
        colour): OK, NOK and Warning (every kind), so the three add up to the total, each in exactly its frame mark's
        colour (Verdict_Color()[0], the owner's rule of 2026-10-16: one colour per state, learnt once). The light ones
        (the amber 1.62:1, the orange-red 2.92:1 on white) read
        on the white card by the view's one line width and marker size (CONST_SERIES_LINE_W, CONST_SERIES_MARKER_RADIUS)
        edged in that same colour. The total is the muted purple-grey, since the OK line is the purple.

    Returns:
        (1) parameter [Vector<Tuple<string> 1x3>]: The series, in legend order.
    """

    return [('OK', 'Cumulative_Ok', Verdict_Color('OK')[0]), ('NOK', 'Cumulative_Nok', Verdict_Color('NOK')[0]),
            ('Warning', 'Cumulative_Warning', Verdict_Color('Warning')[0])]


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
        self._legend_marks = {}                # label -> 'line_marker' | 'dashed'
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

    def _Set_Legend(self, legend: tp.List[tp.Tuple[str, str]], marks: tp.Optional[tp.Dict[str, str]] = None) -> None:
        """
        Description:
            Store the legend items the base draws top-right, each drawn as a sample of its series' own line, at the
            series' width and with its marker, so the legend matches what is drawn.

        Args:
            (1) legend [Vector<Tuple<string> 1x2>]: The items as (label, colour hex).
            (2) marks [Dict<string, string>]: Per label, 'dashed' (a dashed line, no marker); any other label is a
                                              solid line with its marker ('line_marker').
        """

        self._legend, self._legend_marks = legend, dict(marks or {})

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

        painter.setPen(QColor(CONST_DETECTION_INK))
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
            Draw a one-row legend of line samples and labels, top-right ABOVE the plot, so it
            never sits on the data.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        if not self._legend:
            return
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        # A line sample is as long as a dash, a gap and a dash of the dashed series, so every sample reads whole.
        gap = 14
        sample = (2 * CONST_RUN_MEAN_DASH[0] + CONST_RUN_MEAN_DASH[1]) * CONST_SERIES_LINE_W
        marks = [self._legend_marks.get(label, 'line_marker') for label, _ in self._legend]
        widths = [sample + 5 + metrics.horizontalAdvance(label) for label, _ in self._legend]
        total = sum(widths) + gap * (len(self._legend) - 1)
        x = rect.right() - total
        y = rect.top() - 24
        for (label, color), mark, width in zip(self._legend, marks, widths):
            mid = y + 6.5
            if mark == 'dashed':
                pen = QPen(QColor(color), CONST_SERIES_LINE_W, Qt.CustomDashLine, Qt.FlatCap)
                pen.setDashPattern(CONST_RUN_MEAN_DASH)
                painter.setPen(pen)
                painter.drawLine(QPointF(x, mid), QPointF(x + sample, mid))
            else:
                painter.setPen(QPen(QColor(color), CONST_SERIES_LINE_W, Qt.SolidLine, Qt.FlatCap))
                painter.drawLine(QPointF(x, mid), QPointF(x + sample, mid))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(color)))
                painter.drawEllipse(QPointF(x + sample / 2.0, mid), CONST_SERIES_MARKER_RADIUS, CONST_SERIES_MARKER_RADIUS)
            painter.setPen(QColor(CONST_DETECTION_INK))
            text_x = x + sample + 5
            painter.drawText(QRectF(text_x, y - 1, width, 14), Qt.AlignLeft | Qt.AlignVCenter, label)
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
        painter.drawRect(QRectF(bx, by, width, height))
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
            Track the cursor: pick the nearest image column and repaint the read-out. Anywhere on
            the chart it snaps to the nearest column; leaving the chart clears it (leaveEvent).

        Args:
            (1) event [QMouseEvent(object)]: The move event.
        """

        rect = self._Plot_Rect()
        xs = [self._Px_X(value, rect) for value in self._columns]
        index = Nearest_Index(float(event.x()), xs)
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
        plus one series per state (OK, NOK, Warning) when the run classifies. The
        final Total point equals the status bar's OBJECTS DETECTED and the last x equals IMAGES ANALYSED; a failed analysis never
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
            (2) classification_enabled [bool]: Whether to draw the per-verdict series.
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
        legend = [('Total', Style.CONST_INK_MUTE)]
        if classification_enabled:
            legend += [(label, color) for label, _attr, color in _Verdict_Series()]
        self._Set_Legend(legend)
        self._Set_Columns([float(row.Index) for row in rows])
        self.update()

    def _Paint_Series(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw the cumulative-count line(s) — Total, and per verdict when the run classifies — with a
            small marker at each image.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        series = [('Cumulative_Total', Style.CONST_INK_MUTE)]
        if self.__classified:
            series += [(attr, color) for _label, attr, color in _Verdict_Series()]
        for attr, color in series:
            painter.setPen(QPen(QColor(color), CONST_SERIES_LINE_W))
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
                painter.drawEllipse(point, CONST_SERIES_MARKER_RADIUS, CONST_SERIES_MARKER_RADIUS)

    def _Hover_Lines(self, index: int) -> tp.List[tp.Tuple[str, str]]:
        """
        Description:
            The hover read-out for an image: its index, the objects THIS image added, and the
            running total (with the split by verdict when the run classifies).

        Args:
            (1) index [int]: The hovered image column index.

        Returns:
            (1) parameter [Vector<Tuple<string> 1x2>]: The read-out lines as (text, colour hex).
        """

        row = self.__rows[index]
        lines = [('Image %d' % row.Index, Style.CONST_INK),
                 ('This image: +%d' % row.Total, CONST_DETECTION_INK),
                 ('Total: %d' % row.Cumulative_Total, Style.CONST_INK)]
        if self.__classified:
            lines.append((' · '.join('%s %d' % (label, getattr(row, attr)) for label, attr, _color in _Verdict_Series()),
                          CONST_DETECTION_INK))
        return lines


class Confidence_Chart_Cls(Chart_Base_Cls):
    """
    Description:
        Chart 2 — confidence against the analysed-image index: two series and nothing per object (the owner's
        rule, 2026-10-18), the frame mean (a thin solid line, a marker at every analysed image) and the running
        run mean (a thicker dashed line, no markers), in the theme's neutral inks, never a verdict colour, so they
        read apart even where they are equal; and the dashed reference lines at the configuration's warn and error
        thresholds, each labelled with what it means. Unscored objects are in neither mean — a false 0% — and are
        counted in the hover.

    Initialization of the Class:
        Args:
            (none)
    """

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__('Analysed image', 'Confidence (%)', parent)
        self.__rows = []
        self.__thresholds = None

    def Set_Data(self, rows: tp.List[tp.Any], Confidence_Thresholds_Str: Confidence_Thresholds_Str) -> None:
        """
        Description:
            Take the accumulator's per-image rows and the thresholds in force, set the fixed 0..100% axis, thin the
            x labels, and repaint. The same in every mode: the chart draws no verdict.

        Args:
            (1) rows [Vector<Trend_Image_Str(object)>]: The per-image trend rows.
            (2) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: Where the dashed
                warn / error reference lines are drawn.
        """

        self.__rows = rows
        self.__thresholds = Confidence_Thresholds_Str
        n = len(rows)
        labeled = set(Thin_Label_Indices(n, max(2, int(self.width() / CONST_X_LABEL_PX) or 2)))
        x_text = {float(rows[i].Index): str(rows[i].Index) for i in labeled} if rows else {}
        self._Set_Axes(0.5, n + 0.5 if n else 1.5, 0.0, 100.0,
                       [float(row.Index) for row in rows], Nice_Ticks(0.0, 100.0, 5), x_text)
        self._Set_Legend([('Frame mean', Style.CONST_INK_MUTE), ('Run mean', Detection_Mask_Outline())],
                         {'Frame mean': 'line_marker', 'Run mean': 'dashed'})
        self._Set_Columns([float(row.Index) for row in rows])
        self.update()

    def _Reference_Labels(self) -> tp.List[tp.Tuple[int, str, str]]:
        """
        Description:
            The dashed reference lines, each with the label it carries, its colour and its dash: the configuration's
            confidence thresholds, the same pair that colours every confidence number in the application
            (Confidence_Severity). Both are the neutral grey ink, never a verdict colour; the label carries the meaning
            and the dash tells them apart, long at the warning threshold, short at the error threshold.

        Returns:
            (1) parameter [Vector<Tuple 1x4>]: (threshold in percent, label, colour hex, dash pattern) per line; []
                                               with no thresholds set.
        """

        thresholds = self.__thresholds
        if thresholds is None:
            return []
        return [(thresholds.Warn_Below, 'Warning below %d %%' % thresholds.Warn_Below, CONST_DETECTION_INK,
                 CONST_WARN_LINE_DASH),
                (thresholds.Error_Below, 'Error below %d %%' % thresholds.Error_Below, CONST_DETECTION_INK,
                 CONST_ERROR_LINE_DASH)]

    def _Paint_Series(self, painter: QPainter, rect: QRectF) -> None:
        """
        Description:
            Draw the labelled reference lines, then the frame mean's solid line, the run mean's dashes over it, and
            the frame mean's markers on top (one marker at every analysed image), all at the view's one width and
            marker size.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
        """

        # The reference lines and their labels, behind the means: a label sits above its line's right end.
        painter.setFont(Font(Style.CONST_TYPE_SCALE[0]))
        metrics = QFontMetrics(painter.font())
        for value, label, color, dash in self._Reference_Labels():
            y = self._Px_Y(value, rect)
            line = QPen(QColor(color), 1, Qt.CustomDashLine, Qt.FlatCap)
            line.setDashPattern(dash)
            painter.setPen(line)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(QColor(color))
            painter.drawText(QRectF(rect.right() - metrics.horizontalAdvance(label) - 6, y - 16,
                                    metrics.horizontalAdvance(label) + 4, 14), Qt.AlignRight | Qt.AlignVCenter, label)
        run = QPen(QColor(Detection_Mask_Outline()), CONST_SERIES_LINE_W, Qt.CustomDashLine, Qt.FlatCap)
        run.setDashPattern(CONST_RUN_MEAN_DASH)
        self.__Draw_Mean_Line(painter, rect, 'Frame_Mean', QPen(QColor(Style.CONST_INK_MUTE), CONST_SERIES_LINE_W))
        self.__Draw_Mean_Line(painter, rect, 'Run_Mean', run)
        painter.setBrush(QBrush(QColor(Style.CONST_INK_MUTE)))
        painter.setPen(Qt.NoPen)
        for row in self.__rows:
            if row.Frame_Mean is not None:
                painter.drawEllipse(QPointF(self._Px_X(row.Index, rect), self._Px_Y(row.Frame_Mean, rect)),
                                    CONST_SERIES_MARKER_RADIUS, CONST_SERIES_MARKER_RADIUS)

    def __Draw_Mean_Line(self, painter: QPainter, rect: QRectF, attr: str, pen: QPen) -> None:
        """
        Description:
            Draw one mean line, breaking it across images that have no mean (nothing scored yet)
            rather than drawing a segment through a gap.

        Args:
            (1) painter [QPainter(object)]: The active painter.
            (2) rect [QRectF]: The plot rectangle.
            (3) attr [string]: The row attribute to plot ('Frame_Mean' or 'Run_Mean').
            (4) pen [QPen(object)]: The line's pen (its colour, width and dash).
        """

        painter.setPen(pen)
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
            count, and the unscored count when any (the objects in neither mean).

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
                 ('Run mean: %s' % run, Detection_Mask_Outline()),
                 ('Scored: %d' % len(row.Objects), CONST_DETECTION_INK)]
        if row.Unscored:
            lines.append(('Unscored: %d' % row.Unscored, CONST_DETECTION_INK))
        return lines


class Trends_View_Cls(QWidget):
    """
    Description:
        The Trends view: the two run charts stacked in cards. It holds no data of its own — it is
        bound to the window's accumulator and, on Refresh, forwards the accumulator's rows to the
        two charts.

    Initialization of the Class:
        Args:
            (1) classification_enabled [bool]: Whether the run classifies (drives the objects chart's
                                               per-verdict series).
            (2) Confidence_Thresholds_Str [Confidence_Thresholds_Str(object)]: REQUIRED,
                keyword-only: where the confidence chart's reference lines are drawn.
    """

    def __init__(self, classification_enabled: bool = CONST_CLASSIFICATION_ENABLED_DEFAULT,
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
                                         'The mean confidence of each image and the running mean of the run.',
                                         self.__Build_Confidence_Chart()), 1, 0)
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
        self.__confidence_chart.Set_Data(rows, self.__thresholds)

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
