---
name: feature-manager
description: >-
  Turns a change request written as notes — often Czech or Slovak, often short or incomplete —
  into a well-scoped change to the AnyScan application and carries it through. It restates the
  request as requirements, checks the premise before fixing, reports before building, measures
  instead of judging, and commits small. Use it for any new feature, behaviour change or bug fix
  in this repository, including a one-line note ("přidat export do CSV", "fúzia spája dve
  platne"). Every code, test, YAML and Markdown convention comes from project-style-rpx, which
  this skill does not restate.
---

# feature-manager

How work on this project has actually gone, as a procedure. It turns a note into a change and sees
the change through.

**Conventions come from `project-style-rpx`.** Load it alongside this skill. Every rule about code,
tests, YAML and Markdown lives there. This skill links to those rules and never restates them. A rule
that belongs to style goes into `project-style-rpx`, not here.

**Language.** Ask clarifying questions in the note's language (Czech or Slovak when the note is).
Restated requirements, reports, code, comments, commit messages and every file are in English.

## 1. Restate the request

Before anything else:

1. **Quote the note** as given.
2. **Requirements**, numbered, concrete and testable: what changes, where the user sees it, what
   stays the same. One requirement per line.
3. **Left open**: everything the note does not say and the change needs. Typical gaps include the
   UI location, the default value, a mode file versus a constant, the effect on existing records,
   and whether old files must still be read.

**Ask before building** when any of these holds. The user's answer decides scope, so do not pick a
default and build on it.

- The change is **large**: several modules, a new configuration field, a new record format, or a
  change to a data contract (the run-summary CSV, the station event file, `_objects.json`).
- The note is **ambiguous**: two readings would produce different code.
- The plan **rests on an assumption** you have not checked: what the user means by a term, or what
  causes the behaviour they describe.

A small, unambiguous change (a typo, a label, one obvious fix) goes straight to section 3.

## 2. Check the premise

A note says what someone saw, and often names a cause. Establish where the problem actually is
before proposing a fix. Several requests here rested on a wrong diagnosis.

- **Reproduce it first**, on a real frame from `Data/Images/Test/` or a capture set under
  `logger/captures/`. If it cannot be reproduced, say so and stop.
- **Walk the stages.** Look at each stage's output for that frame, not just the final result: the
  background mask, the FastSAM masks, the fused components before and after the closing, the crop
  the describer saw. The Camera View's Heatmap shows the background difference.
- **Name the stage that is wrong**, with the evidence, before naming a fix.

The case to remember: two touching plates came back as one object, and FastSAM was blamed. The masks
showed causes in the fusion and the background cue. The fusion's closing joined plates about 10 px
apart that were separate before it. In two of the three frames where touching plates merged, the
bridge between them came from the background cue, not from FastSAM. See design-decisions *The closing
never joins two components* and KNOWN_ISSUES *Touching parts merge before the closing*. A "better
segmenter" would have fixed one frame of three.

When the premise is wrong, report what you found and ask whether the request still stands. Do not
quietly build a different fix.

## 3. Report before implementing

Any non-trivial change starts with a report, and nothing is written until the user has seen it:

| | |
|---|---|
| **Requirements** | from section 1, with the user's answers |
| **Diagnosis** | from section 2, when it is a fix |
| **Modules** | each file to change, and what changes in it |
| **Configuration** | fields added, changed or removed, with default, unit and REQUIRED status, and which mode files |
| **Records** | any change to a capture set, the run-summary CSV, the station event file or the session log's markers |
| **Tests** | tests added or changed, what each pins, and the expected collected count before and after |
| **Docs** | which `docs/capabilities.md` rows, which `docs/design-decisions.md` entry, which KNOWN_ISSUES or README > Limitations entry |
| **Risks** | what could break, what cannot be tested without the rig (`docs/capture-checklist.md`) |
| **Open questions** | what still needs the user |

## 4. Measure, don't judge

- **Thresholds come from data.** Derive a value from measurements on real frames, and record the
  method next to it (style: a comment recording why a value was chosen stays). "Looks about right"
  is not a reason.
- **Before and after numbers** for any change to detection, description, measurement or timing:
  object counts, sizes, timings, on the same frames, from the same harness
  (`Example/Vision/analyze.py`, `evaluate_describer.py`).
- **Real frames from the test set.** `Data/Images/Test/All` is the pinned set. Changing it is a
  deliberate move that carries its inventory, xfails and doc citations with it. Synthetic frames are
  for cases the set cannot show, and are labelled as such.
- **Say what was not measured.** Name every number that comes from an earlier set, an estimate or
  another machine.

## 5. Configuration

All in `project-style-rpx`. Check each before adding or changing a field:

- A field must be read by something that can change behaviour, and may not have only one legal value
  (`references/yaml.md`, `references/structure.md`).
- REQUIRED or a documented default that equals the code's, validated at load, never silently
  defaulted when invalid (`references/yaml.md` > Loading).
- A value true on one machine only stays in that machine's local copy (`references/yaml.md` >
  *Machine-specific values stay out of the repository*).
- A new section needs a row in `docs/capabilities.md`. Its test fails until the row exists.

## 6. Tests

The rules are in `project-style-rpx` `references/python.md` > Tests. The order on this project:

1. Record `pytest --collect-only -q` before the change.
2. Write or change the tests. For a behaviour-preserving change, write the pins first and pass them
   on the old code.
3. Make the change.
4. **Break what each new test names once** and watch it fail, then restore the file byte for byte
   (subprocess, `PYTHONDONTWRITEBYTECODE=1`, `git status` afterwards).
5. Compare the collected count with the expected one: before, minus removed, plus added.
6. **UI changes: render and look.** Grab the widget offscreen, open the image, and check for
   truncated text, clipping and contrast. A passing region-diff test does not show that.
7. Run the style checker on the changed files, then the suite. Report skips (weights absent) as
   skips, never as passes.

A test that fails intermittently is named with its cause before it is called a flake: loop it with a
per-run timeout and sample the hang. "Passed on re-run" is not a diagnosis.

## 7. Commits

- **Small and separate per concern.** A style rule, a feature, its doc correction and an unrelated
  fix found on the way are separate commits. A test change and the code it pins go together.
- **Stage by name, never `git add -A` or `git add .`** Check `git status` and `git diff` before
  staging. The user's uncommitted hunks are never staged. When they sit in a file you changed, stage
  only your hunks, or ask.
- **Never push** unless asked. **Never restore a deleted file** without asking: a deletion in the
  working tree may be the user's.
- The message says what changed and why, with the numbers (before/after, the collected count, the
  mutations that proved the tests). End it with the attribution line the session gives.

## 8. The same change updates the docs

In the same commit as the behaviour it describes:

- **`docs/capabilities.md` is reviewed for every commit that changes `src/`, `App/`,
  `Configuration/` or `Example/`.** This is required and is never skipped. Read the sections the
  change touches, prose and hardware table included, then do one of two things:
  - **It affects a capability.** Update the document. A behaviour that changed under the same name
    counts: the drift tests cannot see it, so the review must.
  - **It affects none.** Move the *Last reviewed against the code at commit* line to the commit your
    change is based on (`git rev-parse --short HEAD` before committing). Put *Capabilities: no change*
    and the reason in the commit message.

  Either way the document is in the commit.
  `test_every_code_change_since_the_last_review_updated_the_document` fails on any code commit that
  left it untouched, so a code change and its doc change can never be split across commits. The
  other tests in that file catch named things (sections, views, packages, records) going out of
  step.
- **`docs/design-decisions.md`**: a new entry for every deliberate choice whose reason is not
  visible in the code, with **Revisit if** and its pinning tests (style: `references/markdown.md`).
  An entry the change contradicts is corrected in place.
- **`KNOWN_ISSUES.md`**: an open behaviour found is recorded. One the change fixes is removed, and
  the resolution goes to design-decisions.
- **README**: only setup, run and tests. What the application does goes in `capabilities.md`.

## Done means

- [ ] Requirements restated, and open points answered or asked
- [ ] Premise checked on a real frame, and the stage named
- [ ] Report shown before a non-trivial change
- [ ] Numbers before and after, with what was not measured stated
- [ ] Every configuration field read, validated, documented, and none machine-specific
- [ ] Each new test broken once; collected count as expected; UI rendered and looked at
- [ ] `check_style.py` 0 issues on changed files; suite run, with skips reported
- [ ] **`docs/capabilities.md` reviewed (required).** Either updated, or its *Last reviewed* line
      moved and the commit message says *Capabilities: no change* with the reason. Never silently
      skipped: the review test fails on a code commit without it
- [ ] design-decisions and KNOWN_ISSUES updated in the same change
- [ ] Commits small, only your hunks staged, nothing pushed
