# python-style-RP

A Claude Code skill that reproduces the Python house style of
[rparak/RoLE](https://github.com/rparak/RoLE) (Robotics Library for Everyone).

Generated from commit `ee0e67a` (2026-08-16) — 68 files, 17 278 lines.

## Install

```bash
cp -r python-style-RP /path/to/target-repo/.claude/skills/
```

Or for all your projects:

```bash
cp -r python-style-RP ~/.claude/skills/
```

Restart Claude Code, then check with `/skills`.

## Use

The skill triggers on ordinary requests once installed:

> Add a `Sphere_Cls` primitive to `src/RoLE/Primitives/Core.py` with a radius
> property and an overlap test against `AABB_Cls`.

To force it: *"use the python-style-RP skill"*.

## Convert an existing project

> Use the python-style-RP skill. Read references/migration.md, then run
> Phase 1 on src/ only. Do not rename anything yet.

Work through the phases in order — see `references/migration.md`.

## Check existing code

```bash
python .claude/skills/python-style-RP/scripts/check_style.py src/
```

Rules covered: MIT header presence and `File Name:` accuracy, `_Cls`/`_Str`
class suffixes, `Pascal_Snake_Case` functions, docstring `Description:` /
numbered `Args:` / `Returns:` sections, `Initialization of the Class:` on `_Cls`,
full type-hint coverage, `tp.*` hint style, mutable default arguments, relative
imports, `logging` use, `== False`, invalid escape sequences, over-long lines,
and `CONST_*` / `*_Str` module-level naming.

Running it against the source repository reports 525 issues — most are the known
deviations documented in the "Observed anti-patterns" section of `SKILL.md`
(52 `== False`, 13 invalid escapes, 5 mutable defaults, 298 long lines).

## Files

| Path | Purpose |
| --- | --- |
| `SKILL.md` | The always-loaded rules — read this first |
| `references/layout.md` | Directory structure, `sys.path` idiom, no `__init__.py` |
| `references/naming.md` | Full naming tables, verb prefixes, symbol conventions |
| `references/typing-and-data.md` | `tp.*` hints, `_Cls` vs `_Str`, constants |
| `references/docstrings-comments.md` | The RP docstring format, comment style |
| `references/scripts-and-examples.md` | `Example/` script shape |
| `references/pyqt.md` | Building PyQt UIs in RP style, and the Qt-dispatch exception |
| `references/migration.md` | Phased workflow for converting an existing project |
| `assets/header.txt` | The MIT header block to copy into new files |
| `assets/module_template.py` | A blank library module in house style |
| `assets/script_template.py` | A blank evaluation script |
| `scripts/check_style.py` | Automated compliance checker |
