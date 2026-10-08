---
name: project-optimize
description: >-
  Makes the AnyScan application cleaner, faster, simpler and more reliable without changing what it
  does, outputs, or shows the user. Four kinds: cleanup (unused code, stale comments, duplication),
  speed (slow paths, timed before and after), complexity (functions radon rates D or worse, split
  only into named steps) and reliability (crashes, hangs, leaks, intermittent failures, each fixed
  with a test that fails on the old code). It reports first with nothing changed, plans small
  verifiable steps, and executes only what the user approves. Anything that would change
  functionality is handed to feature-manager. Use it for "clean up", "remove unused code",
  "optimise", "speed up", "simplify", "reduce complexity", "fix the hang", "why does it crash", or a
  review of what can go. Conventions come from project-style-rpx; commits follow feature-manager § 8.
---

# project-optimize

It makes the same application cleaner, faster, simpler and more reliable, never different.

**Conventions come from `project-style-rpx`**, and commits follow `feature-manager` § 8 (small, your
own hunks only, never pushed unasked). Neither is restated here.

## The rule: functionality never changes

What the application does, what it outputs, and what the user sees and operates stay exactly as they
are. This covers the window, every message and state, the close sequence, the records and exports,
and the configuration files the user edits. Every step proves it, by the proof its kind requires:

| Kind | What it covers | Proof |
|---|---|---|
| **Cleanup** | Unused code and files, stale or false comments and docs, duplicated logic, tests that cannot fail | Equivalence: pinning tests pass on the old code, and the output is byte-identical |
| **Speed** | Slow paths | Equivalence, plus timing before and after on the same frames |
| **Complexity** | Functions radon rates **D or worse** | Equivalence. Split only when the parts read as named steps, not to satisfy the score |
| **Reliability** | Crashes, hangs, leaks, intermittent failures | A test that fails on the old code and passes on the new, proven by breaking the fix |

**Anything that would touch functionality is not optimization.** List it in the report under **For
feature-manager**, and do not do it here. Cases:

- removing something the user sees or operates: a view, a record, a configuration field (even one
  that does nothing: the loader would then warn on it), or a harness in `Example/`;
- a reliability fix that adds a message, a state, or a different sequence.

## Never touched

- **`models/`**: weights, and the installer tests' fixture. The suite fails if it changes
  ([*models/ is out of reach of the installer tests…*](../../../docs/design-decisions.md#models-is-out-of-reach-of-the-installer-tests-and-the-suite-fails-if-it-changes)).
- **Captures and data**: `Data/` (the pinned test set, references and their sidecars, answer key),
  `logger/` contents, calibration capture sets.
- **`src/Transformation/`**: inherited code, excluded in `check_style.json` with its reason. Report
  findings in it under their own heading, and never rewrite it.

## Phase 1 — Report, change nothing

### Cleanup

| Look for | Evidence that makes it a finding |
|---|---|
| Unused code, files, exports | No reader after the checks in *A hit is a candidate* below |
| Duplicated logic | The copies side by side, and which one is the reader of record (style: one reader per format) |
| Stale or false comments and docs | The comment or doc next to the code or measurement it contradicts |
| Tests that cannot fail | The mutation that left it green: the line deleted, the branch swapped (style `references/python.md` > Tests) |

**Comments.** Only comments that are stale, false or restate the code are candidates (style
`references/python.md`). A why-comment stays. **When unsure whether a comment explains why, keep it**
and list it in the report as *kept, unsure*, with the line, so the user can decide.

### Speed

A slow path is a finding only with a timing: what was timed, on which frames, on which machine, over
how many runs, with the spread. Without a measurement it is a guess. The step's proof is equivalence
plus the same timing after: same frames, same machine, several runs, both numbers and their spread
reported.

### Complexity

Find candidates with radon. It only reads source, so run it from a throwaway environment rather than
adding it to the project's:

```bash
python3 -m venv "$SCRATCH/radon" && "$SCRATCH/radon/bin/pip" install -q radon
"$SCRATCH/radon/bin/radon" cc -s -n D src App Example
```

**A score alone is not a reason.** A function that is a lookup table of rules, or one flat sequence
of checks, can score high and read fine. Splitting it scatters what belongs together. A function is
a finding when it does several things that already read as steps (numbered comments, blocks with
their own purpose), and the split gives each step a name.

**The pattern is commit `4f7f201`**, which split `Load_Configuration` (F 52 → C 14), `Calibrate`
(E 36 → C 11) and `analyze.main` (D 21 → B 7) along their own steps:

- `Load_Configuration` was compared with the committed loader on 1,052 mutated mode files: 175
  loaded and 877 were refused, identically, down to the error text and its order.
- `Calibrate` was compared on four synthetic view sets, every report field identical, with OpenCV
  pinned to one thread. `calibrateCamera` is not bit-reproducible across threads; see
  [*Two calibrations of the same images agree only to the last digits…*](../../../docs/design-decisions.md#two-calibrations-of-the-same-images-agree-only-to-the-last-digits--read-a-small-difference-as-noise).
- `analyze.main` was compared on a real run: console output and every artefact identical, with only
  the timings and stamps masked.

Equivalence for a split means the old and new code run side by side on many inputs, including the
failing ones, and give the same output, errors included.

### Reliability

**Allowed only where the intended behaviour is already defined and the code fails to deliver it.**
Removing a hang or a crash takes nothing away from the user. If the fix would change what the user
sees or does (a new message, a new state, a different close sequence), it is not optimization: stop
and hand it to `feature-manager`.

The example is
[*Closing waits for a running worker…*](../../../docs/design-decisions.md#closing-waits-for-a-running-worker-stops-an-analysis-before-its-next-object-and-has-an-escape).
It fixed a crash, but it added a visible stopping state, so it was a feature.

What to look for, each from where it happened here:

- **A worker's thread released while still running**: the result slot dropped the worker before its
  thread was joined, and the UI suite hung or crashed in about 4 runs of 53.
  [*A worker's thread is joined before the slot that takes its result lets the worker go*](../../../docs/design-decisions.md#a-workers-thread-is-joined-before-the-slot-that-takes-its-result-lets-the-worker-go).
- **A close that destroys a running thread**: `QThread: Destroyed while thread is still running`.
  [*Closing waits for a running worker…*](../../../docs/design-decisions.md#closing-waits-for-a-running-worker-stops-an-analysis-before-its-next-object-and-has-an-escape)
  (its fix was a feature; finding the fault is in scope here).
- **A loss the hardware never reports**: the camera stayed "connected" after a failed grab, because
  only DISCONNECT changed the state.
  [*A lost connection is detected by the camera, not only by DISCONNECT*](../../../docs/design-decisions.md#a-lost-connection-is-detected-by-the-camera-not-only-by-disconnect).
- **A failure surfaced as the wrong error**: a setting the camera refuses must not read as "no camera".
  [*The configuration sets the camera's sensor window*](../../../docs/design-decisions.md#the-configuration-sets-the-cameras-sensor-window),
  and the remaining bare `except Exception` in
  [*`Basler_Cls` connection code raises and catches bare `Exception`*](../../../KNOWN_ISSUES.md#basler_cls-connection-code-raises-and-catches-bare-exception).
- **An intermittent failure called a flake before it is named**: the hang above was an application
  deadlock, which a "flaky test" label would have shipped.

**Evidence for an intermittent problem is a stress run, not one green run.** Loop the suite with a
per-run timeout. The project's run was 30 runs of `test/UI` under a 300 s alarm, with `faulthandler`
on and a native `sample <pid>` of any hung run, since pytest's capture swallows `faulthandler_timeout`
dumps. On macOS:

```bash
perl -e 'alarm shift; exec @ARGV' 300 .venv/bin/python -m pytest test/UI -q -p no:cacheprovider
```

Report the failure rate before the fix and the run count after it, and keep the full output of every
run that does not print the expected pass count. N clean runs at the old failure rate is evidence,
not proof, and is reported as such. Do not edit the source while a loop runs.

### A hit is a candidate until its reader is found

vulture, pyflakes, coverage, radon and grep say where to look (style: *a static-analysis hit is a
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

One table per kind (Cleanup, Speed, Complexity, Reliability), then **For feature-manager**, then
`src/Transformation/` on its own, then *kept, unsure* comments:

| # | Kind | Location | Evidence | Why it matters | Risk | Proof planned | Certainty |
|---|---|---|---|---|---|---|---|
| 1 | Speed | `path:line` | the timing, or the reader found or not found | the cost of leaving it | what could break | equivalence + timing | **confirmed** / **likely** / **unknown** |

- **confirmed**: every check was run, and the reader search, timing, score or failing test is shown.
- **likely**: the static evidence is clear, but a check could not be run (it needs the camera or the
  weights). Name the missing check.
- **unknown**: worth a look, not worth acting on yet.

End the report with what was **not** examined.

## Phase 2 — Plan, then wait for approval

A prioritised list of steps, highest value and lowest risk first. Each step:

- is **one concern** of **one kind**, small enough to review alone, and becomes one commit;
- states **its proof** from the table above, the tests that pin it, and the collected count expected
  after it;
- can be **reverted on its own** without touching the others.

Execute only the steps the user approves, in order, reporting after each. If a step turns out not to
be what the report said (a reader appears, the output differs, the fix would show the user something
new), stop and report. Do not adapt the step.

## Rules for executing

- **Equivalence** (style `references/python.md` > Tests): pinning tests are written and passed on
  the **old** code first. Then the output is byte-identical before and after: the characterization
  golden file, an analysed frame's capture set, a CSV row, rendered pixels. A difference stops the
  step.
- **A reliability fix's test fails on the old code.** Run it there first and show the failure. Then
  break the fix once on the new code and watch it fail again (subprocess, byte-exact restore,
  `PYTHONDONTWRITEBYTECODE=1`). For an intermittent fault, the stress run before and after is part of
  the proof.
- **Removing a test** is itself a finding with evidence (it cannot fail, or it duplicates another).
  The collected count drops by exactly that many.
- **`docs/capabilities.md`**: every step that changes `src/`, `App/`, `Configuration/` or `Example/`
  reviews it, per `feature-manager` § 9. An optimization changes no capability, so the review
  normally moves the *Last reviewed* line, with *Capabilities: no change (optimization: <kind>)* in
  the message. An internal removal the document names, such as a package in *Architecture* or a
  module in the data flow, is updated in the same commit. Removing anything it describes as seen or
  operated by the user is for feature-manager, not here.
- **Docs**: a stale statement is corrected, not deleted, when the fact it records still matters.
  Corrections to a design-decisions entry are made in place and say so (style
  `references/markdown.md`).
- After each step: `check_style.py` on changed files, the suite, the collected count, and `git status`
  clean apart from the step.
