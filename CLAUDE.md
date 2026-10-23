# AnyScan

AnyScan is a PyQt5 station application that captures a part on the table, finds and identifies the
objects in the frame, and gives the operator a verdict (OK, NOK, Warning) with a description. It is an
established repository: its records are in `docs/` - `docs/capabilities.md` (what the application
does, held to the code by tests), `docs/design-decisions.md` (why) and `docs/capture-checklist.md` -
with `KNOWN_ISSUES.md` at the root, not in `.claude/project-docs/`, and there is no SPEC. So the
`project-bootstrap` skill does not apply here. The public page is `README.md`.

The owner's notes may be in Czech or Slovak. Everything written - reports, questions, summaries,
commit messages, code, comments and every file - is in English.

## Skills

The skills are personal (`~/.claude/skills/`, private repository `rparak/rp-claude-skills`). This
repository holds only each skill's project layer, `.claude/skills/<skill>/references/` - never a
`SKILL.md`:

- `project-style-rpx` - code, structure, configuration, installer, Markdown and brand-independent UI
  rules; `references/project.md` and the checker's `references/check_style.json`.
- `jic-sf-ui-style` - the JIC Smart Factory look; `references/project.md` holds AnyScan's bindings.
- `feature-manager` - how a feature, behaviour change or fix is made; `references/project.md`.
- `project-optimize` - behaviour-preserving work; `references/project.md`.
- `readme-writer` - the README; `references/project.md`.

## Commands

Use `.venv/bin/python`, the environment `install.sh` creates; never a bare `python3`.

```bash
./install.sh                                                                    # creates .venv and fetches the models
.venv/bin/python -m pytest -q                                                   # everyday: skips the slow tests, about 3.5 min
.venv/bin/python -m pytest -q --runslow                                         # before a commit: the real models too
.venv/bin/python ~/.claude/skills/project-style-rpx/scripts/check_style.py src App Example test   # 11 known issues
.venv/bin/python App/run.py                                                     # the application
```
