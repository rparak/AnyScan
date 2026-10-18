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
# File Name: ../test/UI/test_grid_fit.py
## =========================================================================== ##

# System (Default)
import os
import re
# Custom Lib.: AnyScan UI — the 1x grid-fitting of a logo's mark (Qt-free)
#   ../UI/Utilities/Grid_Fit
from UI.Utilities.Grid_Fit import CONST_THIN_PX, Fit_Svg
import UI.Utilities.Style as Style

"""
Description:
    UI.Utilities.Grid_Fit moves a logo mark's straight edges onto whole device pixels at a scale, keeps equal strokes
    equal and shared edges shared, honours a group's translate, and leaves curves and everything right of the mark as
    delivered (docs/design-decisions.md, "The header logos are grid-fitted on a 1x display"). Checked on small SVGs whose
    answer is worked out by hand, and on the two header logos at their 1x heights.
"""
# A synthetic mark at a scale of 0.36 px per unit: three bars 7 units tall (2.52 px), placed so that rounding each edge on
# its own would make them 2, 3 and 3 px tall (y 10, 31 and 50); a stroked bracket, a translated group, a relative
# straight path, a curve and a shape right of the mark.
#   Unit [string]
CONST_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 100">'
             '<rect x="11" y="10" width="40" height="7"/><rect x="11" y="31" width="30" height="7"/>'
             '<rect x="11" y="50" width="20" height="7"/>'
             '<g fill="none" stroke="#000" stroke-width="8"><path d="M5,36 V5 H36"/></g>'
             '<g transform="translate(0,9)"><path d="M60,10 h5 v6 h-5 Z"/></g>'
             '<path d="M70,10 Q80,0 90,10 Z"/><rect x="300" y="10" width="50" height="7"/></svg>')
CONST_SCALE = 0.36


def _Numbers(element: str) -> list:
    """The numbers of an element's geometry attributes, in order."""
    geometry = ' '.join(re.findall(r'(?:x|y|width|height|d|points)="([^"]*)"', element))
    return [float(v) for v in re.findall(r'-?\d+\.?\d*', geometry)]


def test_equal_bars_stay_equal_and_land_on_whole_pixels() -> None:
    """
    Description:
        Three bars 7 units tall (2.52 px at the scale) are each 3 px tall after fitting, though rounding their edges one by
        one would make the first 2 px, and every edge is a whole pixel; the stroked bracket's stroke is a whole 3 px
        (2.88 rounded) with both edges on pixels.
    """

    fitted = Fit_Svg(CONST_SVG, CONST_SCALE, 200.0)
    rects = re.findall(r'<rect[^>]*>', fitted)[:3]
    for rect in rects:
        x, y, w, h = (v * CONST_SCALE for v in _Numbers(rect))
        assert all(abs(v - round(v)) < 1e-3 for v in (x, y, w, h)), rect
        assert round(h) == 3, rect
    group = re.search(r'<g fill="none"[^>]*>', fitted).group(0)
    width = float(re.search(r'stroke-width="([^"]*)"', group).group(1)) * CONST_SCALE
    assert abs(width - 3) < 1e-3
    centres = [v * CONST_SCALE for v in _Numbers(re.search(r'<path d="M[^"]*"/>', fitted).group(0))]
    assert all(abs((c - 1.5) - round(c - 1.5)) < 1e-3 for c in centres), centres


def test_a_translated_relative_path_lands_on_pixels_in_absolute_terms() -> None:
    """
    Description:
        A relative straight path inside translate(0,9) is written absolute, and its edges land on whole pixels once the
        translate is added back.
    """

    fitted = Fit_Svg(CONST_SVG, CONST_SCALE, 200.0)
    inner = re.search(r'<g transform="translate\(0,9\)"><path d="([^"]*)"', fitted).group(1)
    assert not re.search('[hvl]', inner)
    values = [float(v) for v in re.findall(r'-?\d+\.?\d*', inner)]
    for x, y in zip(values[0::2], values[1::2]):
        assert abs(x * CONST_SCALE - round(x * CONST_SCALE)) < 1e-3 and abs((y + 9) * CONST_SCALE - round((y + 9) * CONST_SCALE)) < 1e-3


def test_curves_and_shapes_right_of_the_mark_are_left_as_delivered() -> None:
    """
    Description:
        A curved path and a rect right of mark_right come out byte for byte as they went in.
    """

    fitted = Fit_Svg(CONST_SVG, CONST_SCALE, 200.0)
    assert '<path d="M70,10 Q80,0 90,10 Z"/>' in fitted
    assert '<rect x="300" y="10" width="50" height="7"/>' in fitted


def test_with_no_thin_gap_every_edge_goes_to_its_own_nearest_pixel() -> None:
    """
    Description:
        With thin_px 0 (the window icon's small sizes) no edge keeps a rounded width from the one before it: the three
        bars' edges each go to their own nearest pixel, so the first bar is 2 px tall where the default makes it 3.
    """

    fitted = Fit_Svg(CONST_SVG, CONST_SCALE, 200.0, thin_px=0.0)
    edges = []
    for rect in re.findall(r'<rect[^>]*>', fitted)[:3]:
        _, y, _, h = _Numbers(rect)
        edges += [y, y + h]
    original = [10, 17, 31, 38, 50, 57]
    assert [round(v * CONST_SCALE, 3) for v in edges] == [float(round(v * CONST_SCALE)) for v in original]
    assert round(edges[1] * CONST_SCALE - edges[0] * CONST_SCALE) == 2


def test_the_header_logos_marks_land_on_whole_pixels_at_1x() -> None:
    """
    Description:
        At the 1x heights the header draws them at (96 and 100 dpi), every straight edge of the AnyScan mark and of the
        J-I-C bars lands on a whole pixel after fitting: each filled shape's coordinates (its rects, polygons and
        straight paths: the AnyScan mark's square frame is one), and each stroke's edges; the shapes right of the mark
        (the lettering) are unchanged. The AnyScan mark, fitted edge by edge (Style.CONST_LOGO_MARK_THIN_PX), stays
        square, height x height px, with no edge moved more than half a pixel.
    """

    logos = (('anyscan-logo-wordmark.svg', 140.0, Style.CONST_LOGO_MARK_RIGHT, (69, 72), Style.CONST_LOGO_MARK_THIN_PX),
             ('jic-smart-factory.svg', 134.76, 452.0, (33, 35), CONST_THIN_PX))
    for name, units, mark_right, heights, thin_px in logos:
        with open(os.path.join(Style.CONST_ASSETS, name), 'r', encoding='utf-8') as handle:
            svg = handle.read()
        for height in heights:
            scale = height / units
            fitted = Fit_Svg(svg, scale, mark_right, thin_px)
            straight = [element for element in re.findall(r'<path[^>]*>', fitted) if not re.search(r'[QqCcSsAa]', element)]
            for element in re.findall(r'<(?:rect|polygon)[^>]*>', fitted) + straight:
                if 'stroke=' in element:
                    continue
                values = _Numbers(element)
                if 'points=' in element or element.startswith('<path'):
                    pairs = list(zip(values[0::2], values[1::2]))
                else:
                    pairs = [(values[0], values[1]), (values[0] + values[2], values[1] + values[3])]
                for x, y in pairs:
                    if x > mark_right:
                        break
                    on_x = abs(x * scale - round(x * scale)) < 1e-3
                    on_y = abs(y * scale - round(y * scale)) < 1e-3
                    assert on_x and on_y, (name, height, element[:60])
            lettering = [element for element in re.findall(r'<path[^>]*>', svg) if re.search(r'[QqCc]', element)]
            assert all(element in fitted for element in lettering)
            if name.startswith('anyscan'):
                delivered, placed = re.findall(r'<rect[^>]*>', svg), re.findall(r'<rect[^>]*>', fitted)
                corners = [(_Numbers(d), _Numbers(f)) for d, f in zip(delivered, placed)]
                moved = max(abs(a - b) * scale for d, f in corners
                            for a, b in zip(d[:2] + [d[0] + d[2], d[1] + d[3]], f[:2] + [f[0] + f[2], f[1] + f[3]]))
                assert moved <= 0.5 + 1e-3, (height, moved)
                assert round(max(f[0] + f[2] for _, f in corners) * scale) == height, 'the mark is not as wide as it is tall'
                assert round(max(f[1] + f[3] for _, f in corners) * scale) == height
