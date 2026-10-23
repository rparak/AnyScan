# PyQt (src/UI/)

The Python rules (references/python.md) apply in full; this page covers what Qt changes. ✅ =
enforced by `scripts/check_style.py`, 📄 = documentation only.

## Qt-dispatched names ✅

Qt calls some methods by name. Renaming one to Pascal_Snake_Case raises no error — Qt simply stops
calling it. So a Qt override keeps Qt's camelCase and carries the marker on the line above:

```python
    # << QT OVERRIDE >> #
    def closeEvent(self, event: QCloseEvent) -> None:
```

All 16 overrides in `src/UI/` carry it (`paintEvent`, `closeEvent`, `eventFilter`, `keyPressEvent`,
`mousePressEvent`, `resizeEvent`, `showEvent`, `leaveEvent`, `reject` …). The checker exempts a
method from the naming rule **only when it is marked**, so an unmarked camelCase method is still
reported: the marker is what makes the exemption. Whether an override's docstring documents its
`event` argument is unsettled (SKILL.md).

## Classes ✅ (names) 📄 (shape)

- Widgets are `_Cls` with their Qt base, directly or through a project widget:
  `Status_Strip_Cls(Card_Cls)`, `Card_Cls(QFrame)`. Their docstrings do not need
  `Initialization of the Class:` — the UI builds them (✅ the checker follows the class chain).
- Widgets are private attributes named by their type: `self.__button_*` (47), `self.__label_*` (46).
- The widget tree is built in private `__Build_*` methods (`__Build_Topbar`, `__Build_Reading_Card`);
  the constructor declares state and calls them.

## Signals and slots 📄

- Custom signals are `Pascal_Snake_Case` class attributes: `Stage_Changed = pyqtSignal(str)`,
  `Analysis_Finished = pyqtSignal(object)` (19 in `src/UI/`).
- Slots are private and named by their trigger: `__On_Analysis_Finished`, `__On_Connect_Failed` (24).
- Every connection is explicit (`signal.connect(slot)`); nothing uses `connectSlotsByName` or
  `on_<object>_<signal>` auto-connection. Whether connections sit in one `__Connect_Signals` method
  (2 classes) or where the widget is built (the rest) is unsettled.

## Threads 📄

Long work never runs on the GUI thread. A `<Task>_Worker_Cls(QObject)` (`Analysis_Worker_Cls`,
`Connect_Worker_Cls`, `Model_Load_Worker_Cls` in `UI/Workers.py`) is moved to a `QThread` and reports
only through its signals — progress, a result, or an operator sentence on failure. The thread is torn
down when the worker finishes, whichever way.

## The UI holds no domain logic 📄

A UI class reads input, calls into the Qt-free domain modules (`Camera`, `Vision`, `Configuration`,
`Reporting`, `Logger`) and renders the result. The domain modules never import Qt and never hold the
UI or the logger — they emit through injected callbacks (references/structure.md).

## Colours and fonts ✅

How the interface looks is the personal skill **jic-sf-ui-style**; AnyScan's bindings of it (its views, vision
overlays, catalogue wording and the tests) are **references/ui-design.md**. In code: colours and fonts come from `UI/Utilities/Style.py`
(tokens defined in the Qt-free `Parameters/Theme.py`); stylesheets are built inline where they are
applied, from those tokens (`'color: %s;' % Style.CONST_INK`); a token at an opacity is
`Style.Token_Color(token, alpha)` (✅ `test/UI/test_colour_tokens.py`).
