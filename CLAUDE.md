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

Six skills ship in `.claude/skills/<skill>/`: a generic `SKILL.md` with its references, assets and
scripts, and `references/project.md`, which holds every AnyScan decision for that skill. Their licence is
`.claude/skills/LICENSE` (MIT, Roman Parak). The personal copies of the same names are excluded from
`~/.claude/skills` by its sparse checkout, so these are the ones a session loads.

| Skill | Use it for |
|---|---|
| `project-style-rpx` | any change to code, a script, the configuration, the installer, a record or a figure |
| `feature-manager` | a new feature, a behaviour change or a bug fix, and a handover to a new session |
| `project-optimize` | cleanup, speed, complexity and reliability, with the outputs unchanged |
| `readme-writer` | anything the README states, and any change that touches one of its triggers |
| `jic-sf-ui-style` | the window's look: any widget, view, chart, icon, colour, logo, annotation or wording |
| `support-brief` | the support-chat brief, `.claude/project-docs/SUPPORT_CHAT.md` (only when asked) |

## Commands

Use `.venv/bin/python`, the environment `install.sh` creates; never a bare `python3`.

```bash
./install.sh                                                                    # creates .venv and fetches the models
.venv/bin/python -m pytest -q                                                   # everyday: skips the slow tests, about 3.5 min
.venv/bin/python -m pytest -q --runslow                                         # before a commit: the real models too, about 10 min
.venv/bin/python .claude/skills/project-style-rpx/scripts/check_style.py src App Example test   # 11 known issues
.venv/bin/python App/run.py                                                     # the application
```
