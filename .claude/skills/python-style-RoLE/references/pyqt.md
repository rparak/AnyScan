# PyQt applications — RoLE

Qt introduces one genuine conflict with the RoLE style: some method names are
**dispatched by the framework by name**, and renaming them to `Pascal_Snake_Case`
silently breaks the application — the event never fires, no error is raised. The
rule below is therefore not "rename everything"; it is "rename everything you
call yourself, and leave the names Qt calls for you exactly as Qt spells them."

Everything the RoLE style already says still applies: MIT header, annotated
imports, `tp.*` hints, `CONST_*` constants, `*_Str` dataclasses, the RoLE
docstring format, `print(f'[INFO] ...')`, single quotes. This file only covers
what is specific to a Qt UI.

## Naming, and the Qt exception

**Widget and window classes take `_Cls` and keep their Qt base** (hard
requirement). The suffix marks it as a behaviour class; the base stays explicit,
the same way RoLE classes write `(object)`:

```python
class Main_Window_Cls(QMainWindow):
class Scan_View_Cls(QWidget):
```

**Methods you write and call yourself are `Pascal_Snake_Case`** (hard
requirement) — `Initialize_Ui`, `Connect_Signals`, `Update_Preview`,
`Get_Selected_Path`. These are ordinary RoLE methods; Qt never looks them up by
name, so the convention applies unchanged.

**Qt-dispatched names keep their camelCase and are never renamed** (hard
requirement). Qt finds these by their exact name — an event method, a virtual it
overrides, or a model interface method. Renaming any of them means Qt no longer
calls it. Mark each one with a `# << QT OVERRIDE >> #` comment on the line above
the definition, so the exception is visible and nobody "fixes" it later:

```python
    # << QT OVERRIDE >> #
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Description:
            Render the current scan frame onto the widget surface.

        Args:
            (1) event [QPaintEvent(object)]: The Qt paint event.
        """

        ...
```

The names that must stay camelCase include the event handlers `paintEvent`,
`closeEvent`, `resizeEvent`, `mousePressEvent`, `keyPressEvent`, the virtuals
`eventFilter` and `sizeHint`, and the `QAbstractItemModel` overrides `rowCount`,
`columnCount`, `data`, `headerData`, `setData` and `flags`. This is not the full
Qt surface — the test is always "does Qt call this by name?" If yes, keep the Qt
spelling and mark it; if you call it yourself, it is `Pascal_Snake_Case`.

**Do not use `connectSlotsByName` or `on_<objectName>_<signal>` auto-connection**
(hard requirement). That mechanism forces slot names into a Qt-defined shape and
would drag the whole UI back into camelCase. Connect every signal explicitly in a
`Connect_Signals` method instead, which frees slot names to follow the project
convention:

```python
    def __Connect_Signals(self) -> None:
        """
        Description:
            Wire every widget signal to its slot. All connections live here;
            no auto-connection is used anywhere in the application.
        """

        self.__button_scan.clicked.connect(self.__On_Scan_Button_Clicked)
        self.__combo_model.currentIndexChanged.connect(self.__On_Model_Changed)
```

**Custom signals are class attributes in `Pascal_Snake_Case`** (hard
requirement). Declare them at class level, above `__init__`:

```python
class Scan_Worker_Cls(QObject):
    # << SIGNALS >> #
    Scan_Finished = pyqtSignal(object)
    Progress_Changed = pyqtSignal(int)
    Error_Raised = pyqtSignal(str)
```

**Slots are private and prefixed with the trigger** (hard requirement) —
`__On_<Widget>_<Event>`. The prefix makes it read as "reaction to an event",
distinct from the methods you call directly:

```python
    def __On_Scan_Button_Clicked(self) -> None:
    def __On_Model_Changed(self, index: int) -> None:
    def __On_Scan_Finished(self, result: object) -> None:
```

Do **not** decorate slots with `@pyqtSlot` unless a specific overload or a
cross-thread queued connection requires it — a plain method connected explicitly
is the house pattern, and `@pyqtSlot` is not needed for ordinary connections.

## State and structure

**Widgets are private, name-mangled attributes** (hard requirement), declared
under the `# << PRIVATE >> #` marker in `__init__`, exactly as RoLE declares
private state. Prefix each by widget type so the type is readable at the call
site — `button_`, `label_`, `combo_`, `line_`, `table_`, `layout_`:

```python
        # << PRIVATE >> #
        self.__button_scan = None
        self.__label_status = None
        self.__combo_model = None
        self.__layout_main = None
```

**`__init__` stays short** (hard requirement): call `super().__init__()`, declare
state, then hand off to `self.__Initialize_Ui()` and `self.__Connect_Signals()`.
No widget is constructed inline in `__init__` — construction lives in
`Initialize_Ui`:

```python
    def __init__(self, Window_Parameters_Str: Window_Parameters_Str = None) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__Window_Parameters_Str = Window_Parameters_Str if Window_Parameters_Str is not None \
                                       else CONST_WINDOW_PARAMETERS
        self.__button_scan = None
        self.__label_status = None

        self.__Initialize_Ui()
        self.__Connect_Signals()
```

**Window and widget configuration lives in `CONST_*` constants and a
`*_Parameters_Str` dataclass** (hard requirement) — window title, geometry,
margins, icon paths, colours. No magic numbers in layout code:

```python
@dataclass
class Window_Parameters_Str(object):
    """
    Description:
        The structure of the main window configuration parameters.
    """

    # The title shown in the window bar.
    #   Unit [string]
    Title: str = 'AnyScan'
    # Initial window geometry as (x, y, width, height).
    #   Unit [Vector<int> 1x4]
    Geometry: tp.List[int] = field(default_factory=lambda: [100, 100, 1280, 720])
    # Layout margins (left, top, right, bottom).
    #   Unit [Vector<int> 1x4]
    Margins: tp.List[int] = field(default_factory=lambda: [8, 8, 8, 8])
```

**Stylesheets are `CONST_*` string constants** (hard requirement), not inline
`setStyleSheet` calls scattered through the code. One place to change a colour:

```python
"""
Description:
    Initialization of constants.
"""
# Stylesheet for the primary action button.
CONST_STYLE_BUTTON_PRIMARY = 'QPushButton { background-color: #2D7DD2; color: #FFFFFF; }'
```

## Separation and threading — the part that makes it professional

**UI classes contain no application logic** (hard requirement). A UI class reads
input, calls into the domain modules under `src/`, and renders the result.
Anything computational — image processing, model inference, file and model I/O,
formatting of results — belongs in a domain module and **must be callable without
Qt imported**. The test: if `import PyQt` were removed, the domain module still
runs. Keep the domain code out of `src/UI/` — `src/UI/` is for the widgets, and
the logic they drive lives in its own `Core.py` / `Utilities/<Theme>.py`
elsewhere under `src/`.

**Long-running work never runs on the UI thread** (hard requirement). A scan, an
inference pass or a large file read blocks the event loop and freezes the window.
Move the work into a `<Task>_Worker_Cls(QObject)`, push it onto a `QThread`, and
report back through `Pascal_Snake_Case` `pyqtSignal`s for progress, result and
error. Document the ownership and cleanup in the class docstring — who owns the
thread, and when it is quit and waited on:

```python
class Scan_Worker_Cls(QObject):
    """
    Description:
        Worker that runs the scan pipeline off the UI thread.

        Note:
            The worker is moved onto a QThread owned by the window. The window
            starts the thread, and on Scan_Finished / Error_Raised it calls
            quit() then wait() on the thread before the worker is deleted. The
            worker never touches a widget directly — it only emits signals.

    Initialization of the Class:
        Args:
            (1) Scan_Parameters_Str [Scan_Parameters_Str(object)]: The scan configuration.

        Example:
            Initialization:
                # Assignment of the variables.
                thread = QThread()

                # Initialization of the class.
                Cls = Scan_Worker_Cls(CONST_SCAN_PARAMETERS)
                Cls.moveToThread(thread)
                thread.started.connect(Cls.Run)

            Features:
                # Signals of the class.
                Cls.Scan_Finished; Cls.Progress_Changed; Cls.Error_Raised

                # Functions of the class.
                Cls.Run()
    """

    # << SIGNALS >> #
    Scan_Finished = pyqtSignal(object)
    Progress_Changed = pyqtSignal(int)
    Error_Raised = pyqtSignal(str)

    def __init__(self, Scan_Parameters_Str: Scan_Parameters_Str = None) -> None:
        super().__init__()

        # << PRIVATE >> #
        self.__Scan_Parameters_Str = Scan_Parameters_Str

    def Run(self) -> None:
        """
        Description:
            Execute the scan pipeline and emit the result. Runs on the worker
            thread; reports progress and errors through signals only.
        """

        try:
            assert self.__Scan_Parameters_Str is not None

            # 1) Call into the domain module (no Qt here).
            result = Core.Run_Scan(self.__Scan_Parameters_Str)

            self.Scan_Finished.emit(result)

        except AssertionError as error:
            print(f'[ERROR] Information: {error}')
            self.Error_Raised.emit('The scan parameters are not initialized.')
```

**Every class gets the RoLE docstring format** (hard requirement), including the
`Initialization of the Class:` block with `Args:` and an `Example:` section — the
same as any other `_Cls`. `__init__` itself carries no docstring; the
initialization block documents it. For a worker, the `Example:` shows the
`moveToThread` wiring and lists the signals under `Features:`, so a reader sees
how it is meant to be driven.

## Do not touch

- **Any `Ui_*.py` generated by `pyuic`.** It is machine-generated and regenerated
  from the `.ui` file; edits are overwritten. Style it by styling the `.ui`
  source, not the output.
- **Any widget attribute name that came from a `.ui` file.** Those names live in
  the XML and are bound by `loadUi` / the generated `setupUi` at runtime.
  Renaming the Python side without the XML breaks the binding. If a name must
  change, change it in the `.ui` file and regenerate.
