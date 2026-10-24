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
# File Name: ../test/UI/test_control_contrast.py
## =========================================================================== ##

# System (Default)
import os
import hashlib
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Numpy (Array computing) [pip3 install numpy]
import numpy as np
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt, QEvent, QPointF
from PyQt5.QtGui import QImage, QPainter, QMouseEvent
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget
# Custom Lib.: AnyScan UI — the window whose real controls are measured
#   ../UI/Core
from UI.Core import AnyScan_Window_Cls
#   ../Camera/Core
from Camera.Core import File_Camera_Cls
# Custom Lib.: AnyScan domain — the palette's contrast and ΔE maths
#   ../Parameters/Theme
import Parameters.Theme as Theme
# Dataclasses (the shipped configuration, unscaled, for the window)
import dataclasses
# Custom Lib.: AnyScan — the configuration layer the window is built from
#   ../Configuration/Core
from Configuration.Core import Load_Configuration, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Initialization of constants.

    Label-to-background contrast for EVERY interactive state of every control in the console,
    measured from rendered pixels — not read back from the stylesheet. Qt resolves stylesheet
    rules by how many pseudo-states a selector names, not by their order, so reading the rules
    tells you what the author meant, not what Qt paints; a hovered selected segment once rendered
    white on #f6f5fa (1.08:1) from a stylesheet that looked correct. Only the pixels are the truth.

    Each state is driven through Qt's real event path (a QPushButton only reports State_MouseOver
    after a MouseMove while WA_UnderMouse is set), rendered at 2x so the label strokes reach their
    full colour, and measured in the label area: the background is the dominant colour there, the
    label the pixel of highest contrast against it.
"""
# The window's configuration: the shipped one, loaded through the configuration layer, without a
# scale (nothing measured) — what these tests built the window with before configurations existed.
#   Unit [Configuration_Str(object)]
CONST_CONFIGURATION = dataclasses.replace(Load_Configuration(CONST_DEFAULT_CONFIG_FILE), Scale=None)
# The window's name-mangling prefix, for reaching its private widgets.
#   Unit [string]
CONST_MANGLE = '_AnyScan_Window_Cls'

# The WCAG AA floor for text. Every ENABLED state of every control is held to it.
#   Unit [float] (contrast ratio)
CONST_MIN_CONTRAST = 4.5

# THE DISABLED EXEMPTION — a decision on record, not a gap.
#
# A disabled control is EXEMPT from CONST_MIN_CONTRAST (as WCAG 1.4.3 exempts inactive UI). Its low
# contrast is doing a job: it tells the operator the control is unavailable. Holding it to 4.5:1
# would make a disabled button look active, which is worse than the faint label it replaces.
#
# The exemption is conditional. A disabled state must still be told apart from its enabled self at
# a glance, so it must differ from the enabled rest appearance by at least the project's
# perceptual distinctness floor, ΔE76 >= 12 (the same floor the object colours are held to, see
# Parameters/Theme.py), in its label or its fill. Its label-to-background contrast is still
# measured and reported, only not floored.
#   Unit [Tuple<string>] (the exempt states)
CONST_EXEMPT_STATES = ('disabled', 'disabled_hover')
#   Unit [float] (ΔE76)
CONST_MIN_DISABLED_DELTA_E = 12.0

# The states driven on every control. 'disabled_hover' is a control disabled WHILE the cursor is on
# it — the ordinary case of pressing CONNECT, which disables it under the pointer.
#   Unit [Tuple<string>]
CONST_STATES = ('rest', 'hover', 'pressed', 'focus', 'disabled', 'disabled_hover')

# The segmented controls, as (name, how to reach the control from the window).
#   Unit [Tuple<Tuple<string, string, string>>] (name, owner attribute, control attribute)
CONST_SEGMENTED = (('View switch', None, '__view_switch'),
                   ('Log filter', '__log_view', '_Log_View_Cls__filter'),
                   ('Annotated/Mask', None, '__view_toggle'),
                   ('Captures filter', '__history_view', '_History_View_Cls__filter'))

# The tool buttons, as (name, window attribute).
#   Unit [Tuple<Tuple<string, string>>]
CONST_TOOL_BUTTONS = (('CONNECT', '__button_connect'), ('DISCONNECT', '__button_disconnect'),
                      ('PREVIEW', '__button_preview'), ('SCAN', '__button_scan'), ('ANALYZE', '__button_analyze'),
                      ('CLEAR', '__button_clear'))

# The committed reference background, resolved from this file (test/UI -> ../..). The conftest
# fixture is function-scoped; the matrix is measured once per module, so the path is built here.
#   Unit [string]
CONST_REFERENCE_BACKGROUND = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                          'Data', 'Images', 'Background', 'Image_Background_001.png')

# Render scale: at 2x the label strokes are several device pixels wide, so their core reaches the
# label's true colour instead of an antialiased blend.
#   Unit [float]
CONST_RENDER_DPR = 2.0


def _Render(widget: QWidget) -> np.ndarray:
    """
    Description:
        Render a widget (with its inherited stylesheet cascade) to an RGB array at CONST_RENDER_DPR.

    Args:
        (1) widget [QWidget(object)]: The widget to render.

    Returns:
        (1) parameter [Matrix<uint8> HxWx3]: The rendered pixels (RGB).
    """

    image = QImage(int(widget.width() * CONST_RENDER_DPR), int(widget.height() * CONST_RENDER_DPR),
                   QImage.Format_RGB32)
    image.setDevicePixelRatio(CONST_RENDER_DPR)
    image.fill(Qt.white)
    painter = QPainter(image); widget.render(painter)
    painter.end()
    bits = image.constBits(); bits.setsize(image.byteCount())
    return np.frombuffer(bits, np.uint8).reshape(image.height(), image.width(), 4)[..., [2, 1, 0]].copy()


def _Measure(widget: QWidget) -> tp.Tuple[str, str, float, str]:
    """
    Description:
        The label and background colours of a rendered button and their contrast. Only the label
        area is sampled — the middle half vertically, inset past the 16px segment padding — so
        the border and rounded corners never stand in for the label. A digest of the WHOLE render
        is returned too, so the self-check can prove a forced state changed the pixels at all.

    Args:
        (1) widget [QWidget(object)]: The button to measure.

    Returns:
        (1) parameter [Tuple<string, string, float, string>]: (background hex, label hex, contrast
                                                               ratio, digest of the full render).
    """

    rgb = _Render(widget)
    h, w = rgb.shape[:2]
    inset = int(16 * CONST_RENDER_DPR)
    pixels = rgb[h // 4:h - h // 4, inset:w - inset].reshape(-1, 3)
    colors, counts = np.unique(pixels, axis=0, return_counts=True)
    background = '#%02x%02x%02x' % tuple(int(c) for c in colors[counts.argmax()])
    ratios = [Theme.Contrast_Ratio(background, '#%02x%02x%02x' % tuple(int(c) for c in color))
              for color in colors]
    label = '#%02x%02x%02x' % tuple(int(c) for c in colors[int(np.argmax(ratios))])
    return background, label, max(ratios), hashlib.sha1(rgb.tobytes()).hexdigest()


def _Set_Hover(button: QPushButton, hovered: bool) -> None:
    """
    Description:
        Put the cursor on (or off) a button the way Qt does: WA_UnderMouse plus a MouseMove, which
        is what sets QPushButton's private hover flag in Qt 5.15.

        Note:
            BOTH steps are required, and the failure mode of dropping one is silent. Qt 5.15's
            QPushButton::initStyleOption reports State_MouseOver only from a private 'hovering'
            flag, and that flag is set only by a MouseMove event arriving while WA_UnderMouse is
            set. The attribute alone (or a HoverEnter/HoverMove event) renders the button
            UNHOVERED — every hover row then measures the resting colours and passes while testing
            nothing. test_self_check_hover_is_really_rendered is the guard; if it fails, fix this
            function before believing any other result in this file.

    Args:
        (1) button [QPushButton(object)]: The button.
        (2) hovered [bool]: Whether the cursor is over it.
    """

    # WARNING: do not 'simplify' to setAttribute alone — see the Note above.
    button.setAttribute(Qt.WA_UnderMouse, hovered)
    QApplication.sendEvent(button, QMouseEvent(QEvent.MouseMove, QPointF(button.rect().center()),
                                               Qt.NoButton, Qt.NoButton, Qt.NoModifier))


def _Apply_State(button: QPushButton, holder: QWidget, state: str) -> None:
    """
    Description:
        Drive a button into one state from a clean rest. `holder` is what the app disables — the
        whole segmented control for a segment, the button itself for a tool button.

    Args:
        (1) button [QPushButton(object)]: The button measured.
        (2) holder [QWidget(object)]: The widget the application enables/disables.
        (3) state [string]: One of CONST_STATES.
    """

    holder.setEnabled(True); button.setDown(False)
    button.clearFocus(); _Set_Hover(button, False)
    if state in ('hover', 'pressed', 'disabled_hover'):
        _Set_Hover(button, True)
    if state == 'pressed':
        button.setDown(True)
    if state == 'focus':
        button.setFocus(Qt.TabFocusReason)
    if state in ('disabled', 'disabled_hover'):
        holder.setEnabled(False)
    QApplication.processEvents()


def _Private(owner: tp.Any, name: str) -> tp.Any:
    """
    Description:
        A name-mangled private attribute: window-level names start '__', others are pre-mangled.

    Args:
        (1) owner [object]: The window or view.
        (2) name [string]: The attribute name.

    Returns:
        (1) parameter [object]: The attribute.
    """

    return getattr(owner, CONST_MANGLE + name if name.startswith('__') else name)


def Measure_All(window: AnyScan_Window_Cls) -> tp.List[tp.Dict[str, tp.Any]]:
    """
    Description:
        Measure every state of every control. Segmented controls are measured on their first
        segment selected and their second unselected; tool buttons have no selection.

    Args:
        (1) window [AnyScan_Window_Cls(object)]: A shown, active window.

    Returns:
        (1) parameter [Vector<Dict>]: One record per (control, selection, state) with background,
                                      label, contrast, and — for exempt states — the ΔE of the
                                      label and fill against the enabled rest appearance.
    """

    targets = []
    for name, owner, attribute in CONST_SEGMENTED:
        control = _Private(_Private(window, owner) if owner else window, attribute)
        # A control the app keeps hidden (the view toggle until an analysis, the Captures filter
        # without classification) is shown for the measurement: its first render while hidden
        # can be stale, and what is measured is how it looks when the operator can see it.
        control.show()
        buttons = list(_Private(control, '_Segmented_Control_Cls__buttons').items())
        control.Set_Selection(buttons[0][0])
        targets.append((name, 'selected', buttons[0][1], control))
        targets.append((name, 'unselected', buttons[1][1], control))
    for name, attribute in CONST_TOOL_BUTTONS:
        button = _Private(window, attribute)
        targets.append((name, '', button, button))

    records = []
    for name, selection, button, holder in targets:
        # A hidden control (the view toggle before an analysis) is still styled and rendered.
        button.resize(button.sizeHint().expandedTo(button.size()))
        rest = None
        for state in CONST_STATES:
            _Apply_State(button, holder, state)
            background, label, contrast, digest = _Measure(button)
            record = {'control': name, 'selection': selection, 'state': state,
                      'background': background, 'label': label, 'contrast': contrast,
                      'digest': digest, 'focused': button.hasFocus()}
            if state == 'rest':
                rest = record
            else:
                record['delta_e_label'] = Theme.Delta_E(label, rest['label'])
                record['delta_e_fill'] = Theme.Delta_E(background, rest['background'])
            records.append(record)
        _Apply_State(button, holder, 'rest')
    return records


@pytest.fixture(scope='module')
def records() -> tp.List[tp.Dict[str, tp.Any]]:
    """Every control state measured once, from one shown and active window."""
    app = QApplication.instance() or QApplication([])
    window = AnyScan_Window_Cls(Configuration_Str=CONST_CONFIGURATION, camera=File_Camera_Cls(CONST_REFERENCE_BACKGROUND))
    window.show()
    QApplication.setActiveWindow(window)
    # Keyboard focus is what draws a focus indicator; set it as a Tab would.
    window.setAttribute(Qt.WA_KeyboardFocusChange, True)
    app.processEvents()
    measured = Measure_All(window)
    window.close()
    return measured


def test_every_state_of_every_control_was_measured(records) -> None:
    """
    Description:
        The matrix is complete (4 segmented controls x 2 selections + 5 tool buttons, each in every
        state), and the forced states really took: 'focus' holds focus. A state that silently
        failed to apply would measure as rest and pass for the wrong reason.
    """

    assert len(records) == (len(CONST_SEGMENTED) * 2 + len(CONST_TOOL_BUTTONS)) * len(CONST_STATES)
    assert all(r['focused'] for r in records if r['state'] == 'focus')


def test_self_check_hover_is_really_rendered(records) -> None:
    """
    Description:
        HARNESS SELF-CHECK — the hover rows mean nothing unless hover was actually rendered. If a
        Qt version changes how QPushButton decides it is hovered, _Set_Hover silently stops
        working, every 'hover' render equals its 'rest' render, and the floor test passes against
        identical pixels. So: if NO control's hovered render differs from its resting one, the
        harness is broken and this fails loudly. And every control's hover is expected to change
        its pixels today — one that stops doing so either lost its hover style or its forcing —
        but a selected segment's: clicking it does nothing, and in the one purple its hover keeps
        the selected look (design-decisions.md, "The palette is the JIC Smart Factory brand's").
    """

    by_key = {(r['control'], r['selection'], r['state']): r for r in records}
    unchanged = ['%s %s' % (control, selection) for (control, selection, state), r in by_key.items()
                 if state == 'hover' and selection != 'selected'
                 and r['digest'] == by_key[(control, selection, 'rest')]['digest']]
    hovered = sum(1 for key in by_key if key[2] == 'hover')
    assert len(unchanged) < hovered, (
        'HARNESS BROKEN: no hovered render differs from its resting render, so hover was never '
        'rendered and every hover/pressed result in this file is meaningless. Fix _Set_Hover (the '
        'MouseMove + WA_UnderMouse forcing) for this Qt version before trusting anything here.')
    assert not unchanged, 'hover changes nothing on:\n  %s' % '\n  '.join(unchanged)


def test_no_enabled_state_falls_below_the_text_contrast_floor(records) -> None:
    """
    Description:
        Every enabled state — rest, hover, pressed, focus, on selected and unselected segments and
        on every tool button — keeps its label >= 4.5:1 against its own background. Hover must
        never reduce contrast below the floor; this is the check that catches it next time.
    """

    failing = ['%s %s %s: %s on %s = %.2f:1' % (r['control'], r['selection'], r['state'], r['label'],
                                                  r['background'], r['contrast'])
               for r in records if r['state'] not in CONST_EXEMPT_STATES
               and r['contrast'] < CONST_MIN_CONTRAST]
    assert not failing, 'below %.1f:1:\n  %s' % (CONST_MIN_CONTRAST, '\n  '.join(failing))


def test_disabled_states_are_exempt_but_distinguishable_from_enabled(records) -> None:
    """
    Description:
        THE NAMED EXEMPTION (see CONST_EXEMPT_STATES): a disabled state is not held to 4.5:1, but
        it must read as different from the same control enabled — its label or its fill at least
        ΔE 12 from the enabled rest appearance. A disabled state that merely looked enabled would
        fail here; so would one styled identically to enabled by a specificity accident.
    """

    exempt = [r for r in records if r['state'] in CONST_EXEMPT_STATES]
    assert exempt, 'the exemption covers no measured state'
    failing = ['%s %s %s: ΔE label %.1f, fill %.1f' % (r['control'], r['selection'], r['state'],
                                                       r['delta_e_label'], r['delta_e_fill'])
               for r in exempt
               if max(r['delta_e_label'], r['delta_e_fill']) < CONST_MIN_DISABLED_DELTA_E]
    assert not failing, 'disabled not distinguishable from enabled:\n  %s' % '\n  '.join(failing)
