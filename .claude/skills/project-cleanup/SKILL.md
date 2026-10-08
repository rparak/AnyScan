---
name: project-cleanup
description: Finds what in the AnyScan repository is unused, duplicated, stale, slow or untestable, reports it with evidence, and removes or optimises it only after the user approves a plan. It works in two phases, always in this order: report first with nothing changed, then small, independently verifiable steps. Use it for "clean up", "remove unused code", "dead code", "optimise", "speed up", "tidy the docs", or a review of what can go. Every code, test, YAML and Markdown convention comes from project-style-rpx, and commits follow feature-manager § 7.
---

# project-cleanup

Two phases, always in this order. **Phase 1 changes nothing.** Phase 2 runs only the steps the user
has approved.

**Conventions come from `project-style-rpx`**, and commits follow `feature-manager` § 7 (small, your
own hunks only, never pushed unasked). Neither is restated here. A cleanup that changes behaviour is
not a cleanup: it goes through `feature-manager`.

## Never touched

- **`models/`**: weights, and the installer tests' fixture. The suite fails if it changes
  (design-decisions *models/ is out of reach of the installer tests…*).
- **Captures and data**: `Data/` (the pinned test set, references and their sidecars, answer key),
  `logger/` contents, calibration capture sets.
- **`src/Transformation/`**: inherited code, excluded in `check_style.json` with its reason. Report
  findings in it under their own heading, and never rewrite it.

## Phase 1 — Report, change nothing

### What to look for

| Kind | Evidence that makes it a finding |
|---|---|
| Unused code, files, exports | No reader after the checks below |
| Unused configuration fields | Read by nothing that can change behaviour (style `references/yaml.md`) |
| Duplicated logic | The copies side by side, and which one is the reader of record (style: one reader per format) |
| Stale or false comments and docs | The comment or doc next to the code or measurement it contradicts. Only comments that are stale, false or restate the code are candidates (style `references/python.md`). A why-comment never is. |
| Slow paths | A timing: what, on which frames, which machine, how many runs. Without a measurement it is a guess, not a finding. |
| Tests that can't fail | The mutation that left it green: the line deleted, the branch swapped (style `references/python.md` > Tests) |

### A hit is a candidate until its reader is found

vulture, pyflakes, coverage and grep say where to look (style: *a static-analysis hit is a
candidate, not a finding*). Before calling anything unused, check every way this repository reaches
code that a grep for its name misses:

- **Qt dispatch**: methods marked `# << QT OVERRIDE >> #` (`paintEvent`, `eventFilter`, …), slots
  passed to `.connect(...)`, and paint paths that read a value a grep does not obviously link (the
  status cell's `dot_color`).
- **Attribute lookups by string**: `getattr(obj, 'Name', …)` in `src/UI/Core.py`,
  `src/UI/Views/Trends.py` and `src/Camera/Core.py`. Search for the name as a string literal too.
- **Configuration keys**: a `*_Str` field is read through `Configuration/Core.py`'s `CONST_FIELDS` table
  and the YAML. A key is used if `Load_Configuration` maps it and a reader changes behaviour on it.
- **Entry points**: `App/run.py`, every script in `Example/`, and `install.sh` (which names
  `requirements/*.txt` and model paths).
- **Harnesses and tests**: `test/conftest.py` puts `src/`, `App/` and `Example/Vision` on the path, so
  tests import harness code. pytest finds fixtures and hooks (`pytest_*`) by name. The
  characterization golden file `test/Vision/data/characterization.txt` is read by its test.
- **Files by path string**: assets in `App/assets/` (logo, fonts, icons), `images/` linked from the
  README, `.gitkeep` files that keep a required directory in a fresh clone
  (`logger/Station_Events/.gitkeep`: the shipped configuration does not load without it), and
  `scripts/check_style.json`.
- **Docs**: a file or name cited in `docs/`, `KNOWN_ISSUES.md` or the README is a reader of that
  name. Removing the thing means correcting the citation in the same step.

### Finding format

One table per kind, plus `src/Transformation/` on its own:

| # | Location | Evidence | Why it matters | Risk of removing | Certainty |
|---|---|---|---|---|---|
| 1 | `path:line` | what was checked, and the reader found or not found | cost of keeping it | what could break | **confirmed** / **likely** / **unknown** |

- **confirmed**: every check above was run and found no reader, or the measurement or mutation is
  shown.
- **likely**: the static evidence is clear, but a check could not be run (it needs the camera or the
  weights). Name the missing check.
- **unknown**: worth a look, not worth acting on yet.

End the report with what was **not** examined.

## Phase 2 — Plan, then wait for approval

A prioritised list of steps, highest value and lowest risk first. Each step:

- is **one concern**, small enough to review alone, and becomes one commit;
- states **how it will be verified**: the tests that pin it, the byte comparison, the timing, and the
  collected count expected after it;
- can be **reverted on its own** without touching the others.

Execute only the steps the user approves, in order, reporting after each. If a step turns out not to
be what the report said (a reader appears, the output differs), stop and report. Do not adapt the
step.

## Rules for executing

- **Behaviour-preserving means proven equivalent** (style `references/python.md` > Tests). Pinning
  tests are written and passed on the **old** code first. Then the output is byte-identical
  before and after: the characterization golden file, an analysed frame's capture set, a CSV row,
  rendered pixels. A difference stops the step.
- **Removing a test** is itself a finding with evidence (it cannot fail, or it duplicates another).
  The collected count drops by exactly that many.
- **Removing a capability removes it from `docs/capabilities.md` in the same commit**: a
  configuration field (with its code path and documented default), a view, a record, a harness, a
  package, or a behaviour described in the prose. The drift tests fail on a named thing left behind.
  A described behaviour has no name for them to check, so read the document for it.
- **Every step that changes `src/`, `App/`, `Configuration/` or `Example/` reviews
  `docs/capabilities.md`**, per `feature-manager` § 8. A behaviour-preserving step affects no
  capability: move the *Last reviewed* line and say *Capabilities: no change (behaviour-preserving)*
  in the message. The review test fails on a step that skips it.
- **Performance**: measure before and after on the same frames, on the same machine, with several
  runs. Report both numbers and the spread, and say which machine.
- **Docs**: a stale statement is corrected, not deleted, when the fact it records still matters.
  Corrections to a design-decisions entry are made in place and say so (style
  `references/markdown.md`).
- After each step: `check_style.py` on changed files, the suite, the collected count, and `git status`
  clean apart from the step.
