# AnyScan

AnyScan is a PyQt5 station application that captures a part on the table, finds and identifies the
objects in the frame, and gives the operator a verdict (OK, NOK, Warning) with a description. The
public page is `README.md`.

The owner's notes may be in Czech or Slovak. Everything written - reports, questions, summaries,
commit messages, code, comments and every file - is in English.

## Internal docs

`.claude/project-docs/`: `SPEC.md` (what the application does, held to the code by
`test/integration/test_capabilities_doc.py`), `design-decisions.md`, `KNOWN_ISSUES.md`,
`capture-checklist.md` (what only the rig can show) and `FEATURES.md` (the tracker).

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
.venv/bin/python App/run.py                                                     # the application
```

Two tiers of checks (times measured on the Apple M2 Pro, 2026-10-29):

```bash
# Per commit: the default suite (the skills' checker tests included) and the style checker.
.venv/bin/python -m pytest -q                                                   # 1529 collected, 198 s
.venv/bin/python .claude/skills/project-style-rpx/scripts/check_style.py src App Example test   # 11 known issues, 2 s
# Before the owner's acceptance and any push: the real models too.
.venv/bin/python -m pytest -q --runslow                                         # 535 s (R0, before the skills' tests joined)
```

## Work rules

- **A branch per revision** (R1 is `skills-in-repo`): the work is committed there in small commits,
  staged by name. After the owner's acceptance the owner fast-forwards it into `main` and pushes; a
  session never pushes.
- **No force-push**, except a tag moved with the owner's approval.
- **No attribution trailers** in commits or pull requests, as `.claude/settings.json` sets.
- The tracker is `.claude/project-docs/FEATURES.md`: each revision's line, and its acceptance with the
  date.
