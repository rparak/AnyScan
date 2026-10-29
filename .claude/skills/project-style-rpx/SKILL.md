---
name: project-style-rpx
description: >-
  The RP code and repository conventions for a Python project, plus each project's own rules from
  its project reference: Python in the RP style (_Cls/_Str/_Error_Cls/CONST_* names,
  Pascal_Snake_Case functions, import typing as tp, numbered Description/Args/Returns docstrings, a
  #-comment licence header), pytest layout and test discipline, the structure rules (a Core.py per
  src domain with topic modules, mirrored tests, a layer order, one reader and writer per file
  format, no field without effect, a pinned root layout), the YAML configuration and installer
  rules, the Markdown records (SPEC, decisions, known issues), data figures, and brand-independent
  PyQt UI engineering. Use it for any change in a repository that follows these conventions - Python, a
  script, a configuration field, the installer, a record, a figure, a review, any UI work - even
  when style is not mentioned. It runs scripts/check_style.py.
---

# project-style-rpx

The conventions of a project in the RP style. This skill holds the generic rules; the project's own
decisions (its domains and layer order, its file formats, its configuration file, its platforms,
its header holder) are in its **project reference**. Every rule says whether something **enforces**
it (✅ the checker, a test, the configuration loader) or whether it is **documentation only** (📄).
A practice followed by too little code to call a rule is marked *Unsettled*.

**Assumes** (deliberate; a project that differs records it in its project reference, or does not
use this skill): a **Python 3** project with **pytest**; the **RP coding style** below (names,
docstrings, header) rather than PEP 8 naming or Google/NumPy docstrings; a **bash** installer
`install.sh` with a `.venv` and `requirements.txt`; **git**; YAML for configuration; the internal
records in `.claude/project-docs/`; for a desktop UI, **PyQt5** (Qt 5.15), rendered offscreen in
tests (`QT_QPA_PLATFORM=offscreen`). Folder names (`src/`, `test/`, the scripts folder, `Media/`)
are defaults the project reference may rename.

**Visual style lives in three layers**, each rule in one place: brand-independent UI engineering
here ([references/ui.md](references/ui.md)); a brand's look in its own skill (palette, fonts,
logos, icons, chart and annotation style), which the project reference names; and the project's
bindings in its project reference. Data figures (matplotlib for reports and READMEs) follow
[references/figures.md](references/figures.md), with a brand's look where one applies.

The naming and docstring style descends from rparak/RoLE (the "RP" style). Where RoLE differs (it
raises no exceptions, has no tests, writes its header as a docstring) these conventions do not
follow it.

## 0. Read the project reference first

`.claude/skills/project-style-rpx/references/`, beside this file:

- `project.md` - the project's decisions: holder, domains and layer order, scripts folder, formats
  and their readers, configuration file, installer targets, root-layout exceptions, project-only
  rules. It may name further project-only references in the same folder (a file format, a vendored
  model); read the ones the change touches.
- `check_style.json` - the checker's configuration (holder, licence, class, test and check roots,
  reasoned exclusions).

**The project reference overrides this skill** where they differ. A difference that looks like a
mistake is raised with the owner, never changed on your own. A rule a change makes stale in
`project.md` is corrected there in the same change.

Also follow the project's instructions file (`CLAUDE.md`) for its interpreter: run every command
below with the interpreter it names (for example `.venv/bin/python`), never a bare `python3`.

## 1. Run the checker before every commit

```bash
<project python> .claude/skills/project-style-rpx/scripts/check_style.py            # the project's check_roots
<project python> .claude/skills/project-style-rpx/scripts/check_style.py <paths>    # or named files and folders
```

The checker finds the project root from the working directory upwards (or `--root DIR`) and refuses to
run without the project's `check_style.json` (exit 2, never "clean"). It must report 0 issues for
the files you changed. The commit that adds a folder the checker should read also adds it to
`check_roots`. The `exclude` list holds reasoned exclusions; an entry without a reason is
refused and the summary line names every exclusion that applied. A path that does not exist, a
non-`.py` file or an unreadable file is refused (exit 2, named in the output); a directory walk
skips hidden directories.

Its own tests, `scripts/test_check_style.py`, run in the project's suite when the project lists this
folder in its pytest `testpaths` (the project reference says whether it does). The checker and its
tests are a stdlib tool in plain PEP 8 style and are not held to the rules they check.

## 2. What is enforced, and by what

| Rule | Enforced by |
|---|---|
| Licence header naming the project's holder (`Copyright (c) <year> <holder>`) with a `File Name:` line matching the file (a template field `{{...}}` or `<...>` is not compared) | ✅ checker |
| Class name Pascal_Snake_Case ending in `_Cls`, dataclass in `_Str`, an exception (directly or through a project class) in `_Error_Cls`; functions Pascal_Snake_Case, parameters snake_case or math symbols, module-level names `CONST_*` or a `*_Str` preset | ✅ checker (naming in pytest modules too, pytest's own names excepted) |
| Every parameter and return annotated | ✅ checker - not in pytest modules (`test_*.py`, `conftest.py`, anything under a test root), helpers included |
| A function named `main` (a script's entry point, `def main():` in assets/script_template.py) is exempt from the naming, docstring and typing checks | ✅ checker (the exemption) |
| Docstring with `Description:`, numbered `Args:` when there are arguments, `Returns:` when a value is returned | ✅ checker - not in pytest modules |
| `Initialization of the Class:` in a `_Cls` docstring | ✅ checker - except exception classes and Qt classes, directly or through a class of the same file or of the class roots |
| A Qt-dispatched camelCase method is exempt from naming **only when marked** `# << QT OVERRIDE >> #` on the line above | ✅ checker (references/ui.md) |
| Lines ≤ 150, ≤ 2 statements per `;` line, no mutable defaults, no `== True/False`, no invalid escapes, no `logging`, no relative imports, `import typing as tp`, no `from __future__ import annotations`, no dead `__name` override | ✅ checker |
| A comment above every import; `# Custom Lib.:` group with `#   ../path` lines | 📄 |
| `# << PRIVATE >> #` marker, private state as `self.__name` | 📄 |
| `*_Error_Cls` messages are full operator sentences | 📄 |
| Required configuration fields present, values valid, all problems listed at once, unknown key → WARNING; duplicate keys refused, only `true` / `false` booleans | ✅ the project's loader and its test (references/yaml.md) |
| A configuration mini-language is parsed, never evaluated | ✅ the loader's test (references/yaml.md) |
| A configuration field is read by something that can change behaviour | 📄 - a loader cannot see it |
| The root holds only the declared entries; no case-only duplicate paths | ✅ the project's root-layout test (references/structure.md) |
| Core.py + a topic module per second concern + Const.py for shared constants | ✅ the project's layout test, or 📄 (references/structure.md) |
| Committed generated data records its inputs' hashes (YAML by content) and is refused stale | ✅ the project's test (references/structure.md) |
| A known library warning is filtered by its exact message only | ✅ the project's test (references/python.md) |
| Figures: one style module, two themes, measured contrasts, PNG + SVG, generated | ✅ the project's figure tests (references/figures.md) |
| Layer order; one reader and writer per file format | 📄 unless the project reference names a test |
| Installer: OS detection, explicit interpreter, log format | ✅ the project's installer test (references/shell.md) |
| A comment is removed only when stale, false or restating the code | 📄 (references/python.md > Docstrings) |
| Test discipline: a test calls the code it names, never takes its expectation from it, is broken once, a rewrite matches its collected count, a behaviour-preserving change is proven equivalent | 📄 (references/python.md > Tests) |
| A script test runs the script in a fresh interpreter from an unrelated working directory | ✅ the project's script tests |
| No parameter or field with a single legal value | 📄 |
| design-decisions entries carry **Why**, **Alternatives** and **Revisit if** | 📄 (references/markdown.md) |

The project reference adds its own rows (a file format's round trip, a vendored file's hashes).

## 3. Python - the essentials

Full rules: [references/python.md](references/python.md).

1. Every `.py` file opens with the `#`-comment licence header. Copy [assets/header.txt](assets/header.txt),
   put in the year, the project's holder and the author, and set `File Name:` to the real path (`../<Domain>/Core.py`
   for `src/<Domain>/Core.py`, `../<scripts>/<script>.py` for a script). The checker also accepts a
   `"""` docstring header; a project chooses one form.
2. Names: `Pascal_Snake_Case_Cls`, `Pascal_Snake_Case_Str` dataclasses, `Pascal_Snake_Case`
   functions and methods (verb-first), `snake_case` parameters and locals (or math symbols such as
   `x`, `n`, `A_b`), `CONST_*` module constants. A parameter carrying a `*_Str` is named after it.
3. `import typing as tp` and annotate everything; dataclass fields carry a comment ending in a
   `#   Unit [type]` line.
4. Docstrings: `Description:`, numbered `Args:` `(1) name [type]: ...`, `Returns:`
   `(1) parameter [type]: ...` - the RP format, not Google/NumPy/Sphinx. Units in brackets.
5. Errors: a module that can fail in a way the operator must see defines a `*_Error_Cls` and
   raises it with a full, actionable sentence.
6. Reporting: no `logging` module. Scripts print `[INFO]` / `[WARNING]` / `[ERROR]` lines. `src/`
   modules report through return values, exceptions and injected callbacks; they never print.
7. Tests: pytest, `test/<Domain>/test_<module>.py` mirroring `src/<Domain>/<Module>.py`, one test
   file per script, a `Description:` docstring per test saying what behaviour it pins.
8. No `__init__.py`. `src/` reaches `sys.path` through `test/conftest.py` in tests and, in scripts,
   through a path built from `__file__` - never a working-directory-relative path.
9. Line length: aim ≤ 120, the checker errors above 150.

## 4. Reference map

| Read | When |
|---|---|
| [references/python.md](references/python.md) | any Python: header, names, imports, constants, docstrings, types, errors, tests, scripts |
| [references/structure.md](references/structure.md) | a new module, folder, file format, dependency or root entry; `.claude/project-docs/`; the skills layout |
| [references/yaml.md](references/yaml.md) | a configuration file or field |
| [references/shell.md](references/shell.md) | the installer |
| [references/markdown.md](references/markdown.md) | SPEC, design-decisions, KNOWN_ISSUES |
| [references/figures.md](references/figures.md) | a data figure: style module, themes, palette, saving, the default look |
| [references/ui.md](references/ui.md) | a desktop UI: Qt code, theme tokens, contrast, density, UI tests, Qt quirks (a brand's look: its own skill, named in the project reference) |
| [assets/module_template.py](assets/module_template.py), [assets/script_template.py](assets/script_template.py), [assets/config_template.yaml](assets/config_template.yaml) | a new module, script or configuration file |
| the project's `references/project.md` | always, first |

## Unsettled - not rules yet

Ask before writing new code either way, unless the project reference settles it.

- **Import group order** among standard library, third-party and `typing`. Only the comment per
  import and the trailing `# Custom Lib.:` group are rules.
- **A shared structures package.** A `*_Str` lives with the module that defines its behaviour
  (references/structure.md); whether a shared `Parameters` package is ever needed is open.
- **Module-level private helpers.** The naming table covers private methods (`__X`) and test
  helpers (`_X`); a module-level helper's name is the project's choice.

A new project asks these before any code is written; the answers are recorded in the project
reference.
