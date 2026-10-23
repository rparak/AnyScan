# project-style-rpx

The conventions of the anyscan-pyqt repository — Python, the shell installer, the YAML
configuration and calibration files, the design-decisions Markdown, and the structural rules —
written from what the code does. Claude Code loads it from `.claude/skills/` in this repository;
`SKILL.md` is the entry point.

It began as `python-style-RP`, a Python-only skill derived from rparak/RoLE. Where RoLE's practice
differs from this repository's (RoLE raises no exceptions, has no tests, and writes its header as a
docstring), the skill now describes this repository.

| Path | What |
|---|---|
| `SKILL.md` | The rules in brief, what enforces each, and the practices still unsettled |
| `references/python.md` | Python: header, names, imports, docstrings, types, errors, tests, scripts |
| `references/pyqt.md` | What Qt changes: overrides, signals and slots, threads |
| `references/ui-design.md` | AnyScan's bindings of the UI style (its views, vision overlays, catalogue wording, the tests); the style itself is the personal skill `jic-sf-ui-style` |
| `references/shell.md` | `install.sh` |
| `references/yaml.md` | The configuration and calibration files |
| `references/markdown.md` | design-decisions, README > Limitations, KNOWN_ISSUES |
| `references/structure.md` | Layers, one reader per format, injected runtimes, fields that must take effect |
| `assets/` | The file header and a module / script skeleton |
| `scripts/check_style.py` | The Python checker (stdlib only); `check_style.json` holds its reasoned exclusions |
| `scripts/test_check_style.py` | The checker's own tests (not in the app's `test/` suite) |

```bash
.venv/bin/python .claude/skills/project-style-rpx/scripts/check_style.py src App Example test
.venv/bin/python -m pytest .claude/skills/project-style-rpx/scripts/test_check_style.py
```
