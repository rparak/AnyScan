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
# File Name: ../UI/Utilities/Grid_Fit.py
## =========================================================================== ##

# System (Default)
import re
# Typing (Support for type hints)
import typing as tp

"""
Description:
    Grid-fitting of a logo's mark for a 1x display (docs/design-decisions.md, "The header logos are grid-fitted on a 1x
    display"). An SVG drawn at a scale puts its edges between pixels, where they are drawn half-covered and read soft,
    and no single scale puts an irregular set of edges on whole pixels. Fit_Svg moves each straight edge of the mark to a
    whole device pixel: rectangles, polygons and paths of straight segments only (M, L, H, V, Z, absolute or relative),
    filled or stroked. Curves (the lettering) are left exactly as delivered, as is every shape that reaches right of the
    mark.

    - A filled shape's edges share one map per axis across the whole mark, so an edge two shapes share stays shared (the
      I's foot and the J's and C's). Along an axis the lowest edge goes to its nearest pixel; an edge across a gap
      narrower than CONST_THIN_PX on screen keeps the gap's rounded width from the previous one, so equal strokes stay
      equal (each J-I-C bar, the mark's three bars); an edge across a wider gap goes to its own nearest pixel, so no
      error carries far. With thin_px 0 (the window icon's small sizes) every edge goes to its own nearest pixel.
    - A stroked shape's stroke becomes a whole number of pixels (at least one), and each of its centre lines is placed so
      both of the stroke's edges land on pixels.

    Pure text in, text out, with no Qt: the caller renders the fitted SVG at exactly the scale it was fitted for, with the
    viewBox's origin (0 0) on a whole device pixel.
"""
# A gap between two edges narrower than this on screen is a stroke: its far edge keeps the gap's rounded width.
#   Unit [px]
CONST_THIN_PX = 10.0
# The elements read, and a number in SVG text.
#   Unit [Pattern] / [string]
CONST_ELEMENT = re.compile(r'<(/?)(g|path|rect|polygon)\b([^>]*?)(/?)>')
CONST_NUMBER = r'-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def __Number(value: float) -> str:
    """
    Description:
        A coordinate as short SVG text.

    Args:
        (1) value [float]: The value.

    Returns:
        (1) parameter [string]: The value with at most four decimals.
    """

    text = ('%.4f' % value).rstrip('0').rstrip('.')
    return '0' if text in ('', '-0') else text


def __Attribute(attributes: str, name: str) -> tp.Optional[str]:
    """
    Description:
        An attribute's value in an element's attribute text.

    Args:
        (1) attributes [string]: The element's attributes.
        (2) name [string]: The attribute.

    Returns:
        (1) parameter [string or None]: Its value, or None when absent.
    """

    found = re.search(r'(?:^|\s)%s="([^"]*)"' % re.escape(name), attributes)
    return found.group(1) if found else None


def __Set(attributes: str, name: str, value: str) -> str:
    """
    Description:
        An element's attribute text with one attribute's value replaced, or added when it is absent.

    Args:
        (1) attributes [string]: The element's attributes.
        (2) name [string]: The attribute.
        (3) value [string]: Its new value.

    Returns:
        (1) parameter [string]: The attribute text.
    """

    if __Attribute(attributes, name) is None:
        return '%s %s="%s"' % (attributes.rstrip(), name, value)
    return re.sub(r'((?:^|\s)%s=")[^"]*(")' % re.escape(name), lambda m: m.group(1) + value + m.group(2), attributes, count=1)


def __Absolute_Path(data: str) -> tp.Optional[tp.List[tp.Tuple[str, float, float]]]:
    """
    Description:
        A straight-only path as absolute points: every M, L, H and V (absolute or relative) as an M or L to a point,
        and Z. None for a path with anything else (a curve).

    Args:
        (1) data [string]: The path's d.

    Returns:
        (1) parameter [Vector<Tuple<string, float, float>> or None]: (command, x, y) per point, 'Z' with the start.
    """

    if re.sub(r'[MmLlHhVvZz\s,]|%s' % CONST_NUMBER, '', data):     # anything else is a curve (or unknown)
        return None
    tokens = re.findall(r'[MmLlHhVvZz]|%s' % CONST_NUMBER, data)
    points, x, y, start, command, index = [], 0.0, 0.0, (0.0, 0.0), None, 0
    while index < len(tokens):
        token = tokens[index]
        if re.fullmatch('[MmLlHhVvZz]', token):
            command, index = token, index + 1
            if command in 'Zz':
                points.append(('Z', start[0], start[1]))
                x, y = start
            continue
        if command is None:
            return None
        relative = command.islower()
        if command in 'MmLl':
            vx, vy = float(tokens[index]), float(tokens[index + 1])
            index += 2
            x, y = (x + vx, y + vy) if relative else (vx, vy)
            points.append(('M' if command in 'Mm' else 'L', x, y))
            if command in 'Mm':
                start = (x, y)
                command = 'l' if relative else 'L'      # a moveto's further pairs are linetos
        elif command in 'Hh':
            value, index = float(tokens[index]), index + 1
            x = x + value if relative else value
            points.append(('L', x, y))
        else:
            value, index = float(tokens[index]), index + 1
            y = y + value if relative else value
            points.append(('L', x, y))
    return points


def __Shape(tag: str, attributes: str) -> tp.Optional[tp.List[tp.Tuple[str, float, float]]]:
    """
    Description:
        A fittable element's outline as points in its own coordinates: a rect's two corners, a polygon's points, a
        straight path's points. None for anything else.

    Args:
        (1) tag [string]: 'rect', 'polygon' or 'path'.
        (2) attributes [string]: Its attribute text.

    Returns:
        (1) parameter [Vector<Tuple<string, float, float>> or None]: (command, x, y) per point.
    """

    if tag == 'rect':
        x, y = float(__Attribute(attributes, 'x') or 0), float(__Attribute(attributes, 'y') or 0)
        return [('M', x, y), ('L', x + float(__Attribute(attributes, 'width')), y + float(__Attribute(attributes, 'height')))]
    if tag == 'polygon':
        values = [float(v) for v in re.findall(CONST_NUMBER, __Attribute(attributes, 'points') or '')]
        return [('L', px, py) for px, py in zip(values[0::2], values[1::2])]
    data = __Attribute(attributes, 'd')
    return None if data is None else __Absolute_Path(data)


def __Elements(svg: str) -> tp.List[tp.Tuple[tp.Any, str, str, float, float, tp.Optional[float]]]:
    """
    Description:
        Every rect, polygon and path in the SVG with the translate of the groups it is in and the stroke width it is
        drawn with (its own, else its group's), or None when it is filled.

    Args:
        (1) svg [string]: The SVG.

    Returns:
        (1) parameter [Vector<Tuple>]: (match, tag, attributes, dx, dy, stroke width or None).
    """

    stack, found = [(0.0, 0.0, None)], []
    for match in CONST_ELEMENT.finditer(svg):
        closing, tag, attributes, self_closing = match.groups()
        dx, dy, inherited = stack[-1]
        if tag == 'g':
            if closing:
                stack.pop()
            elif not self_closing:
                moved = re.search(r'translate\(\s*(%s)[\s,]+(%s)\s*\)' % (CONST_NUMBER, CONST_NUMBER), __Attribute(attributes, 'transform') or '')
                width = __Attribute(attributes, 'stroke-width')
                stroked = __Attribute(attributes, 'stroke') not in (None, 'none')
                stack.append((dx + (float(moved.group(1)) if moved else 0.0), dy + (float(moved.group(2)) if moved else 0.0),
                              float(width) if (stroked and width) else inherited))
            continue
        stroke, own = __Attribute(attributes, 'stroke'), __Attribute(attributes, 'stroke-width')
        if stroke == 'none':
            width = None
        elif stroke is not None:
            width = float(own) if own else 1.0
        else:
            width = inherited
        found.append((match, tag, attributes, dx, dy, width))
    return found


def __Axis_Map(values: tp.List[float], scale: float, thin_px: float) -> tp.Dict[float, float]:
    """
    Description:
        Where each of the mark's filled edge coordinates on one axis goes, in device pixels (see the module's
        description): the lowest to its nearest pixel, then across a thin gap the gap's rounded width from the previous
        edge, across a wide one the edge's own nearest pixel.

    Args:
        (1) values [Vector<float>]: The absolute coordinates, in viewBox units.
        (2) scale [float]: Device pixels per viewBox unit.
        (3) thin_px [float]: A gap narrower than this on screen is a stroke, in px; 0 sends every edge to its own
                             nearest pixel.

    Returns:
        (1) parameter [Dict<float, float>]: Each coordinate (rounded to 1e-6) and its pixel.
    """

    fitted, previous, placed = {}, None, 0.0
    for value in sorted(set(round(v, 6) for v in values)):
        if previous is not None and (value - previous) * scale < thin_px:
            placed = placed + round((value - previous) * scale)
        else:
            placed = float(round(value * scale))
        fitted[value] = placed
        previous = value
    return fitted


def Fit_Svg(svg: str, scale: float, mark_right: float, thin_px: float = CONST_THIN_PX) -> str:
    """
    Description:
        The SVG with its mark's straight edges on whole device pixels at a scale: every rect, polygon and straight-only
        path lying wholly left of mark_right (in viewBox units) is fitted, filled ones through one map per axis, stroked
        ones with their stroke a whole number of pixels. Curves and shapes reaching right of mark_right are left as
        delivered.

    Args:
        (1) svg [string]: The SVG, its viewBox starting at 0 0.
        (2) scale [float]: Device pixels per viewBox unit, as it will be rendered.
        (3) mark_right [float]: The right edge of the mark, in viewBox units.
        (4) thin_px [float]: A gap between filled edges narrower than this on screen keeps its rounded width, in px.
                             The header's logos use CONST_THIN_PX; the window icon 0 (Example/UI/build_logo.py), since at
                             16-32 px nearly every gap is under 10 px and chaining the rounded widths runs past the
                             icon's square.

    Returns:
        (1) parameter [string]: The fitted SVG.
    """

    fittable = []
    for match, tag, attributes, dx, dy, width in __Elements(svg):
        shape = __Shape(tag, attributes)
        if shape and max(px for _, px, _ in shape) + dx <= mark_right:
            fittable.append((match, tag, attributes, dx, dy, width, shape))
    filled = [(dx, dy, shape) for _, _, _, dx, dy, width, shape in fittable if width is None]
    x_map = __Axis_Map([px + dx for dx, _, shape in filled for _, px, _ in shape], scale, thin_px)
    y_map = __Axis_Map([py + dy for _, dy, shape in filled for _, _, py in shape], scale, thin_px)

    def Place(value: float, offset: float, width: tp.Optional[float], axis_map: tp.Dict[float, float]) -> float:
        """
        Description:
            A coordinate's fitted value: a filled shape's from the axis map, a stroke's centre line placed so the
            stroke's two edges land on whole pixels.

        Args:
            (1) value [float]: The coordinate, in the element's own units.
            (2) offset [float]: The groups' translate on this axis.
            (3) width [float]: The stroke width in viewBox units, or None for a filled shape.
            (4) axis_map [Dict<float, float>]: The axis's map from __Axis_Map.

        Returns:
            (1) parameter [float]: The fitted coordinate, in the element's own units.
        """

        if width is None:
            return axis_map[round(value + offset, 6)] / scale - offset
        width_px = max(1, int(round(width * scale)))
        return (round((value + offset) * scale - width_px / 2.0) + width_px / 2.0) / scale - offset

    pieces, last = [], 0
    for match, tag, attributes, dx, dy, width, shape in fittable:
        points = [(command, Place(px, dx, width, x_map), Place(py, dy, width, y_map)) for command, px, py in shape]
        if tag == 'rect':
            (_, x0, y0), (_, x1, y1) = points
            for name, value in (('x', x0), ('y', y0), ('width', x1 - x0), ('height', y1 - y0)):
                attributes = __Set(attributes, name, __Number(value))
        elif tag == 'polygon':
            attributes = __Set(attributes, 'points', ' '.join('%s %s' % (__Number(px), __Number(py)) for _, px, py in points))
        else:
            attributes = __Set(attributes, 'd', ' '.join('Z' if command == 'Z' else '%s%s,%s' % (command, __Number(px), __Number(py))
                                                         for command, px, py in points))
        if width is not None and __Attribute(attributes, 'stroke-width') is not None:
            attributes = __Set(attributes, 'stroke-width', __Number(max(1, int(round(width * scale))) / scale))
        pieces.append(svg[last:match.start()])
        pieces.append('<%s%s%s>' % (tag, attributes, match.group(4)))
        last = match.end()
    pieces.append(svg[last:])

    # A stroked group's width becomes the whole pixels its fitted children were centred for.
    def Group(found: tp.Any) -> str:
        """
        Description:
            A group's start tag with its stroke width set to the whole pixels its children were centred for.

        Args:
            (1) found [re.Match(object)]: The group's start tag.

        Returns:
            (1) parameter [string]: The tag.
        """

        attributes = found.group(1)
        width = __Attribute(attributes, 'stroke-width')
        if width and __Attribute(attributes, 'stroke') not in (None, 'none'):
            attributes = __Set(attributes, 'stroke-width', __Number(max(1, int(round(float(width) * scale))) / scale))
        return '<g%s>' % attributes
    return re.sub(r'<g\b([^>]*)>', Group, ''.join(pieces))
