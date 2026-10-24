# AnyScan

AnyScan is a PyQt5 station application that captures a part on the table, finds and identifies the
objects in the frame, and gives the operator a verdict (OK, NOK, Warning) with a description. The
public page is `README.md`.

The owner's notes may be in Czech or Slovak. Everything written - reports, questions, summaries,
commit messages, code, comments and every file - is in English.

## Internal docs

`.claude/project-docs/`: `SPEC.md` (what the application does, held to the code by
`test/integration/test_capabilities_doc.py`), `design-decisions.md`, `KNOWN_ISSUES.md` and
`capture-checklist.md` (what only the rig can show).

## Skills

Personal, in `~/.claude/skills/` (private repository `rparak/rp-claude-skills`). This repository holds
only each skill's project layer, `.claude/skills/<skill>/references/project.md` (and the checker's
`check_style.json`), never a `SKILL.md`: `project-style-rpx`, `jic-sf-ui-style`, `feature-manager`,
`project-optimize`, `readme-writer`.

## Commands

Use `.venv/bin/python`, the environment `install.sh` creates; never a bare `python3`.

```bash
./install.sh                                                                    # creates .venv and fetches the models
.venv/bin/python -m pytest -q                                                   # everyday: skips the slow tests, about 3.5 min
.venv/bin/python -m pytest -q --runslow                                         # before a commit: the real models too, about 10 min
.venv/bin/python ~/.claude/skills/project-style-rpx/scripts/check_style.py src App Example test   # 11 known issues
.venv/bin/python App/run.py                                                     # the application
```
