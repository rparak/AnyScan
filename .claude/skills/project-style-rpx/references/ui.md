# UI - desktop interfaces (PyQt5)

The brand-independent rules for a desktop UI: how the Qt code is written, how its look is held by
tokens and measurements, and how it is tested. ✅ = enforced by `scripts/check_style.py` or a test
the project has, 📄 = documentation only. The Python rules (references/python.md) apply in full; this
page covers what a UI adds.

What the interface looks like - palette values, fonts, components, icons, charts, wording - is a
brand's, not this page's: it is the brand skill the project reference names (for a PyQt6 brand
these rules hold too, with the Qt 6 differences that skill names). The project's own bindings (its views, its tokens' names, the tests that hold them) are in its project
reference.

## Qt-dispatched names ✅

Qt calls some methods by name. Renaming one to Pascal_Snake_Case raises no error - Qt simply stops
calling it. So a Qt override keeps Qt's camelCase and carries the marker on the line above (above its
decorators, if any):

```python
    # << QT OVERRIDE >> #
    def closeEvent(self, event: QCloseEvent) -> None:
```

The checker exempts a method from the naming rule **only when it is marked**, so an unmarked
camelCase method is still reported: the marker is what makes the exemption.

## Classes ✅ (exemption) 📄 (shape)

- Widgets are `_Cls` with their Qt base, directly or through a project widget:
  `Status_Strip_Cls(Card_Cls)`, `Card_Cls(QFrame)`. Their docstrings do not need
  `Initialization of the Class:` - the UI builds them (✅ the checker follows the class chain through
  the same file and the class roots).
- Widgets are private attributes named by their type: `self.__button_connect`, `self.__label_state`.
- The widget tree is built in private `__Build_*` methods (`__Build_Topbar`); the constructor declares
  state and calls them.

## Signals and slots 📄

- Custom signals are `Pascal_Snake_Case` class attributes: `Stage_Changed = pyqtSignal(str)`.
- Slots are private and named by their trigger: `__On_Analysis_Finished`.
- Every connection is explicit (`signal.connect(slot)`); nothing uses `connectSlotsByName` or
  `on_<object>_<signal>` auto-connection.

## Threads 📄

Long work never runs on the GUI thread. A `<Task>_Worker_Cls(QObject)` is moved to a `QThread` and
reports only through its signals - progress, a result, or an operator sentence on failure. The thread
is torn down when the worker finishes, whichever way.

## The UI holds no domain logic 📄

A UI class reads input, calls into the Qt-free domain modules and renders the result. The domain
modules never import Qt and never hold the UI or a logger - they emit through injected callbacks
(references/structure.md). A test that imports each domain module in a fresh interpreter and finds no
Qt loaded makes it ✅; the project reference names the modules it covers.

## Colour comes from the theme ✅ (the project's token test)

- **Every colour is a token in the theme.** UI code reads tokens through the style module and never
  names a colour by value: not a hex string in a stylesheet or anywhere else, and not a
  `QColor(r, g, b)` built from numbers. A token at an opacity goes through one helper
  (`Style.Token_Color(token, alpha)`), and the alpha is itself a named theme constant. Instance: a busy
  overlay filled with `QColor(43, 36, 85, 158)`, a hand copy of a token at another opacity, which
  nothing kept in step with the token.
- A test tokenizes every UI module (except the style module) with the Python tokenizer and flags a
  hex colour in a string literal or a `QColor(` followed by a number; docstrings and comments are
  ignored. (jic-sf-ui-style's `scripts/check_tokens.py` does the same from the command line.)
- **The theme is Qt-free.** It sits outside the UI layer, so an OpenCV renderer, a figure generator or
  an exported image reads the same palette without importing Qt.
- **Figures follow the theme too.** In a project with a UI, a diagram or a README figure takes every
  colour from the theme, and its type sizes and font fallbacks from the style module, through a
  generator script (the figure rules themselves: references/figures.md); it is regenerated, never
  edited by hand, and a test holds the committed file to the generator's output.
  Derived logo files (a tagline-less wordmark, a window icon) are built by a script from the
  delivered logo and never hand-edited either.
- **Adding a colour.** First ask whether an existing token already plays the role. A new colour is a
  new token, commented with its role and its measured ratios: measure it against every ground it
  sits on and against its neighbours by ΔE76 (12 is the distinctness floor), then add its pair to
  the pair test (below). How a brand derives a new colour is the brand skill's.

## Contrast floors, measured ✅ (the project's contrast tests)

- **Text clears 4.5:1 on its ground, and a graphic clears 3:1.** This is a property of the colour
  pair, so it holds at every density; there is no density-dependent palette. An exception is the
  owner's recorded choice, listed in the brand skill or the project reference, never a silent one.
- Every (foreground, ground) pair is a parametrised test case with its floor (4.5 for text, 3.0 for a
  graphic); a new token adds its pair.
- **Disabled controls are exempt** from the floor but differ from their enabled state by ΔE76 ≥ 12 in
  label or fill; a disabled-hover state looks like disabled.
- **Severity never rides on colour alone.** A level has a word, a weight and a colour.
- **A relationship between two colours is held by code or a test, never by a comment**: by
  derivation that fails loudly when no valid value exists, or by a test on the floors (a mask fill
  against its box ΔE ≥ 25, against white ≥ 21, 4.5:1 on black, its hue within 5°).

## One density check 📄 (✅ by the type-floor test)

- One function decides density (`Style.Is_Low_Density`: device pixel ratio < 1.5); everything that
  differs by density (the type floor, a logo's height) asks it.
- **The type floor**: on a low-density display every font built through the style module's `Font`
  is raised to at least 9 pt. At DPR 1, 7.5-8.5 pt text has only 0.02-0.05 of its ink at full
  contrast, against 0.12-0.19 at 9 pt. A 2x display keeps the written size.
- The ratio is read when a widget is built, which for the window is before it is shown, when Qt 5
  reports the highest ratio of all screens; nothing re-reads it on a screen change.

## Qt quirks 📄

- **Qt's stylesheet engine never matches `:hover` on a disabled widget**, so no stylesheet can break
  the disabled-hover state; a paint path keyed on `underMouse()` needs its own test.
- **Selectors rank by how many pseudo-states they name, not by their order.** So every state rule
  names its fill, its border **and** its label; a fill-only rule can pair with another state's label
  colour. Instance: a hovered selected segment rendered white on near-white (1.08:1) from a stylesheet
  that read correctly.
- **A bare `background:` cascades into every child** and paints blocks behind titles: style a
  container with an id selector (`#root`, `setObjectName`).
- **A `QFrame.VLine` ignores the stylesheet colour**: draw a hairline as a filled 1 px widget.
- **Qt 5.15 exposes only a variable font's default instance** and synthesises every other weight (a
  button label's full-contrast share fell from 0.42 to 0.20): ship static files, one per weight
  requested, and request no weight without its face.
- **Fonts are registered right after the `QApplication` is built and before any widget exists**;
  `Qt.AA_EnableHighDpiScaling` and `Qt.AA_UseHighDpiPixmaps` are set *before* it is built.
- **The device pixel ratio is read when a widget is built**, so it cannot be changed within a process
  (a DPR 2 run is a fresh interpreter, below).

## Tests of a UI

- **Measure pixels, not stylesheets.** Only rendered pixels are the truth (*Selectors rank…* above).
  Render the widget into a `QImage` at **2x** (`image.setDevicePixelRatio(2); widget.render(image)`),
  so label strokes are several device pixels wide and their core reaches the label's true colour. In
  the label area the fill is the dominant colour and the label the pixel of highest contrast against
  it; assert ≥ 4.5:1 for every enabled state (rest, hover, pressed, focus, selected).
- **Drive states through Qt's real event path**: hover needs `WA_UnderMouse` and a `MouseMove`,
  pressed `setDown(True)`, checked `setChecked(True)`. Add a self-check that hover really rendered
  differently from rest, or a test can pass on states it never drew.
- **Text**: walk every visible label in the built window, grab the ground under it (which must be a
  theme token) and measure; painted text is measured the same way.
- **Run the module again at DPR 2.** A test spawns `python -m pytest <this file>` in a fresh
  interpreter with `QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2` and asserts it passes. Tests that
  only make sense at one density `pytest.skip` themselves on the other.
- **The type floor is measured**: at DPR 1 no text resolves below the floor; at DPR 2 the window is
  pixel-identical to the window without it.
- **A UI test asserts what is rendered, not the value handed to the widget.** Grab the widget
  (`widget.grab()`) and compare pixels, or render a rich-text label through `QTextDocument`, and
  measure on a **shown, laid-out** widget. Unshown labels report Qt's default geometry (a label 640 px
  wide), and rich text drops a leading space, so the source string is not what the screen shows.
- **An exception in a Qt callback fails the test that raised it.** PyQt5 calls `sys.excepthook` for
  an exception in a `paintEvent`, an event filter or a slot; at Python's default it calls qFatal and
  the whole run aborts. `test/conftest.py` replaces the hook for each test phase and fails that phase
  with the traceback. A test that asserts a paint path must still grab it: the guard sees only what
  raises.
- **A static-analysis hit in UI code is checked against the paint paths.** The reader of an
  attribute is often a `paintEvent` or a rich-text render that a grep does not obviously connect
  (references/python.md > Tests, *A static-analysis hit is a candidate*).

## Look at the render 📄

A region-average or pixel-count test misses truncated text, a clipped badge, a soft logo or a
misaligned icon. After any visible change, grab the window offscreen at DPR 1 and DPR 2, **open both
images and look** (spacing, crispness at 1x, nothing clipped or elided, icons square), and compare with
a reference screenshot of the same view; a pixel diff of a fixed region (a header, a chart card)
makes unintended drift obvious. Report what was checked and how; if a check was skipped or a test was
not run at DPR 2, say so.
