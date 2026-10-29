---
name: feature-manager
description: >-
  Turns a change request written as notes - often short, incomplete or in another language - into a
  well-scoped change and carries it through: it restates the request as testable requirements,
  checks the premise on the real data, challenges whether the requested solution is the right one (a
  reviewer's checklist plus the project's domain checklist), reports before building and stops for
  approval, measures instead of judging, stops and reports instead of loosening a limit, breaks
  every new test once, commits small, and updates the SPEC, design-decisions, KNOWN_ISSUES and the
  tracker in the same change. Where the output drives a physical system, nothing claims more than
  the tests or simulation showed. Use it for any new feature, behaviour change or bug fix, even a
  one-line note, and to hand work over to a new session. Conventions come from project-style-rpx.
---

# feature-manager

The procedure for turning a note into a change and seeing the change through.

**Assumes** (deliberate): a **git** repository whose code follows `project-style-rpx` (Python,
pytest - the collected counts and mutations below are pytest's), with its specification and
records in `.claude/project-docs/`, and an owner who approves before building. The physical-system
rules apply only when the project reference declares one.

## 0. Read the project's part first

[references/project.md](references/project.md) holds the project's part: its domain checklist, the
formats and fields whose change is always "large", where its real data is, what must never be
committed, what a result may claim, and which docs apply (README triggers live in readme-writer's
project reference). **It overrides this skill** where they differ: a rule of this file that a
project decision replaces is written there, not here.

**Conventions come from `project-style-rpx`.** Load it alongside this skill. Every rule about code,
tests, configuration, the installer and Markdown lives there (with its own project reference). This
skill links to those rules and never restates them. A rule that belongs to style goes there.

**`.claude/project-docs/SPEC.md` is the source of truth** for structure, formats and decisions. A
change that contradicts it either updates it in the same change, with the owner's agreement, or does
not happen.

**Language.** Communicate in the language the project's `CLAUDE.md` names - reports, questions,
summaries, commit messages and every file. The owner's notes may be in another language; answer in
the named one anyway.

**Physical systems: passed ≠ safe.** When the project reference says the output drives a physical
system, every output not yet tested on the real system by the owner is a proposal, run there first
under the safe conditions the project reference names. No change, report or
commit message claims more than the tests or the simulation showed; the project reference gives the
exact sentence.

## 1. Restate the request

Before anything else:

1. **Quote the note** as given.
2. **Requirements**, numbered, concrete and testable: what changes, what the output looks like (the
   lines written, the printed report), what stays the same. One requirement per line.
3. **Left open**: everything the note does not say and the change needs. Typical gaps: which inputs,
   the unit and frame of a value, a configuration field versus a code constant, the limit that
   applies, what happens when the limit cannot be met.

**Ask before building** when any of these holds. The owner's answer decides scope, so do not pick a
default and build on it.

- The change is **large**: several modules, a new configuration field, a change to a file format or
  to a safety margin or limit (the project reference lists which formats and fields).
- The note is **ambiguous**: two readings would produce different code or different output.
- The plan **rests on an assumption** you have not checked: what the owner means by a term, which
  frame or unit a value is in, or what causes the behaviour they describe.

A small, unambiguous change (a typo, a message, one obvious fix) needs no question. Sections 2 and 3
then take a line each, and it goes straight to building.

## 2. Check the premise

A note says what someone saw, and often names a cause. Establish where the problem actually is
before proposing a fix.

- **Reproduce it first**, on the real data and the shipped configuration (the project reference
  says where they are). If it cannot be reproduced, say so and stop.
- **Walk the chain.** Look at each step's output, not just the final verdict: what was parsed, what
  each stage computed, what the check reported and why.
- **Name the step that is wrong**, with the evidence, before naming a fix.

Example (generic): "the report shows the wrong total" could be a parse that drops a row, a unit
converted twice, a filter applied in the wrong order, or a correct total of wrong input. Each needs a
different fix; rounding the output would hide all four.

When the premise is wrong, report what you found and ask whether the request still stands. Do not
quietly build a different fix.

## 3. Challenge the approach

Section 2 asks whether the problem is where the request says. This step asks whether the **requested
solution** is the right one. Act as a reviewer with the project's domain judgement and
software-engineering judgement, not as the person who will build it.

- **Is this the right lever?** If a better alternative exists, name it, give its trade-off, and say
  which you would choose. Typical cases: tightening the one component that is wrong instead of
  loosening a global limit; reporting a near case instead of excluding it; failing explicitly instead
  of returning a result outside the requirements.
- **Will the result mean what it seems to?** Flag where an output could look right and be wrong: a
  number shown more precisely than its error, a result checked against a model that differs from the
  real system, a test that passes because its input is missing.

Go through the checklist for the areas the change touches: the generic items below, then the
project's domain checklist in its project reference.

**Generic checklist**

- [ ] **One source of truth** per fact (a constant, a table, a file); a second copy is derived, never
      maintained beside it.
- [ ] **Configured vs derived**: a value the owner sets is configured with its source; a value
      computed from others is never stored.
- [ ] **Pin vs bound**: a regression pin holds a measured value in a narrow band; an acceptance
      bound comes from the rule. Neither is widened to let a change pass (style references/python.md
      > Tests).
- [ ] **Limits fail explicitly**: an input or result outside a limit is an error naming what, by how
      much and the limit - no silent pass, no silent clamp, no override without an explicit decision.
- [ ] **Units and frames** named for every value.
- [ ] Configuration fields that do nothing, or have a single legal value (style references/yaml.md,
      references/structure.md).
- [ ] One reader and writer per format (style references/structure.md).
- [ ] Heavy runtimes stay out of what the tests import.
- [ ] **What is not modelled** (by the tests, the simulation, the data): a change that relies on it
      says so.

**Then:**

- **The request stands:** say so in one line (*Approach: as requested - …*) and continue.
- **It does not:** stop and ask, with the alternative and its trade-off stated. Building waits for
  the answer.
- **Never silently build something you would advise against**, and never silently build the
  alternative instead.
- **A failing check is not a dial.** When a check fails on behaviour that was verified (a reference
  run, a physics-tested path), or a change would pass only with a wider limit, stop: report the
  measured value, the bound and its source, the candidate causes and the options. The owner decides;
  the decision goes into design-decisions with its numbers. A bound is never widened, nor a check
  skipped, to let a change through.

## 4. Report before implementing

Any non-trivial change starts with a report, and nothing is written until the owner has seen it.
A **large** change (section 1) reports in two parts:

- **Part A - the design.** What will be built and how, on a **measured basis**: the numbers the
  design rests on, measured now in a scratch run or a temporary directory (no code in the
  repository), and **numbered open questions**, each with a recommended answer. Stop for approval.
- **Part B - the implementation**, after the owner's answers, which are recorded with their date
  (in the tracker or the SPEC) before building. A design that has to change while building goes back
  to the owner as a short Part A addendum.

The report:

| | |
|---|---|
| **Requirements** | from section 1, with the owner's answers |
| **Diagnosis** | from section 2, when it is a fix |
| **Approach** | from section 3: as requested, or the alternative the owner chose, and why |
| **Modules** | each file to change, and what changes in it |
| **Configuration** | fields added, changed or removed, with unit, source and REQUIRED status |
| **Formats** | any change to a file format the project reads or writes |
| **Limits and margins** | what changes and why it is still covered (the project reference names its budgets) |
| **Tests** | tests added or changed, what each pins, and the expected collected count before and after |
| **Docs** | which SPEC section, which design-decisions entry, which KNOWN_ISSUES item |
| **Risks** | what could break, and what can only be checked on the real system |
| **Open questions** | what still needs the owner |

## 5. Measure, don't judge

- **Values come from sources or data.** A dimension comes from a manual page or a measurement; a
  margin from its budget; a threshold from measurements, with the method recorded next to it
  (style: a comment recording why a value was chosen stays). "Looks about right" is not a reason.
- **Before and after numbers** for any change to computation or checking: errors, distances,
  violation counts, sizes, runtimes - on the same inputs and seed.
- **Fixed seeds.** Every random sample and any search uses a recorded seed, so a number can be
  reproduced.
- **Say what was not measured.** Name every number that is an estimate, comes from another revision,
  or holds only on the inputs it was measured on.

## 6. Configuration

Apply `project-style-rpx` references/yaml.md to every field added or changed, and update the SPEC's
configuration table in the same change.

## 7. Tests

The rules are in `project-style-rpx` references/python.md > Tests. The order:

1. Record `pytest --collect-only -q` before the change.
2. Write or change the tests (pins first, on the old code, for a behaviour-preserving change).
3. Make the change.
4. **Break what each new test names once** and watch it fail (python.md > Tests: how to break and
   restore safely).
5. Compare the collected count with the expected one: before, minus removed, plus added.
6. **Visual changes: look.** For a change to anything rendered or shown, open it and look at what
   changed; a passing numeric test does not show a misplaced element.
7. Run the style checker on the changed files, then the project's per-commit checks (`CLAUDE.md`
   names them; without tiers, the suite). The slower tier runs before the owner accepts the feature
   and before a push (the tiers are designed in project-optimize). Report skips as skips, never as
   passes.

**A fix's test fails on the old code.** For a bug fix, run the new test on the unchanged code first
and show it fails there, then make the fix, then break it once (step 4). **A new check gets a forced
failure** that rebuilds the case it exists for (the old design, the old order, the old value) and
shows that the checks already there pass on it - the proof that the new check adds something.

**Long runs.** A run that takes minutes runs in the foreground with an explicit timeout above its
measured time, and prints its progress; it is not left in the background. After an interruption,
check the state first - `git status`, the outputs and logs that exist, what a previous run already
wrote - and continue from there; never start a second copy of a run that may still be going.

A test that fails intermittently is named with its cause before it is called a flake: loop it with a
per-run timeout. "Passed on re-run" is not a diagnosis.

## 8. Commits

- **Small and separate per concern.** A style rule, a feature, its doc correction and an unrelated
  fix found on the way are separate commits. A test change and the code it pins go together.
- **Stage by name, never `git add -A` or `git add .`** Check `git status` and `git diff` before
  staging. The owner's uncommitted hunks are never staged. When they sit in a file you changed, stage
  only your hunks, or ask.
- **Never push** unless asked. **Never restore a deleted file** without asking: a deletion in the
  working tree may be the owner's.
- What must never be committed, or only as its own deliberate change (regenerated vendored files,
  rebuilt derived data), is listed in the project reference.
- **A pinned output moved on purpose** (golden data, a baseline, a fingerprint): commit the change
  with the pin failing in the expected ways and say so in the message; re-capture the pin in the
  next commit, alone, listing exactly what changed in it and why.
- **Restore points are commit hashes**, written in full where they are recorded (`CLAUDE.md`, a
  design-decisions entry). Tags are for releases only (`vMAJOR.MINOR`, annotated). Before a tag is
  deleted, what only it holds is exported, and the hash it named is checked to be an ancestor of the
  main branch (`git merge-base --is-ancestor`).
- **A failed experiment** is undone with `git revert`, never by rewriting pushed history. One that
  is not adopted but worth repeating is kept as data: its patch against its base commit, its script
  and a README (base commit, parameters, results, how to re-apply).
- **Acceptance**: the owner's acceptance of a feature is recorded with its date (the tracker, if
  the project keeps one). Push only when asked, or when the project reference says to push after
  each accepted feature.
- The message says what changed and why, with the numbers (before/after, the collected count, the
  mutations that proved the tests). Attribution lines follow the project's rule (`CLAUDE.md`).

## 9. The same change updates the docs

In the same commit as the behaviour it describes (formats: style references/markdown.md):

- **SPEC**: a change to structure, a format, a field, a limit or a decision updates the section
  that states it.
- **design-decisions**: a new entry for every deliberate choice whose reason is not visible in the
  code, with **Why**, **Alternatives**, **Revisit if** and its pinning tests. An entry the change
  contradicts is corrected in place.
- **KNOWN_ISSUES**: a limitation found is recorded. One the change removes is removed, and the
  resolution goes to design-decisions.
- **README**: a change that hits one of the README triggers updates the README with the
  `readme-writer` skill in maintenance mode. The triggers are listed in one place only,
  readme-writer's project reference (`.claude/skills/readme-writer/references/project.md` >
  Triggers); this skill does not repeat them.
- **A skill's `references/project.md`** made stale by the change is corrected in the same commit.
- **The tracker**, if the project keeps one (project-style-rpx references/markdown.md): the
  feature's line, and its acceptance with the date.
- **A rename or removal** ends with `git grep` for the old name: no hit in code, configuration,
  tests or docs, outside quotations of history.

## 10. Handing over to a new session

Before a session ends with work open, write a handover the next session reads first. The owner
pastes it into the new session; it is never stored in the repository. Start from
[assets/handover_template.md](assets/handover_template.md):

- **Read first**: `CLAUDE.md`, the SPEC sections, decisions and known issues the work touches, the
  tracker's open items.
- **State**: the last commit (hash and subject), whether it is pushed, uncommitted work (by file),
  the checks last run and their results, any run still going or interrupted.
- **Open**: the item in progress, its step, the owner's last answers (with dates), the questions
  still open.
- **Rules in force**: the ones the next session could break - what needs approval, what must not be
  changed, the language, the commit rules.
- **Next step**: one concrete action.

## Done means

- [ ] Requirements restated, and open points answered or asked
- [ ] Premise checked on the real data, and the wrong step named
- [ ] Approach challenged: the lever, what the result will mean, the generic and project checklists
      for the areas touched; the request stands (one line), or the owner chose after the alternative
      was stated
- [ ] Report shown before a non-trivial change
- [ ] Numbers before and after on a fixed seed, with what was not measured stated
- [ ] Every configuration field read, validated, documented with unit and source, none machine-specific
- [ ] Each new test broken once; collected count as expected; a visual change looked at
- [ ] Style checker 0 issues on changed files; suite run, with skips reported
- [ ] SPEC, design-decisions and KNOWN_ISSUES updated in the same change
- [ ] Nothing claims more than what was shown (physical systems: the project's sentence)
- [ ] Tracker updated; owner's acceptance dated
- [ ] Commits small, only your hunks staged, a moved pin re-captured in its own commit, nothing pushed
      unless asked or the project says so
