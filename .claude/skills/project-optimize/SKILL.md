---
name: project-optimize
description: >-
  Makes a project cleaner, faster, simpler and more reliable without changing what it does or
  outputs. Four kinds: cleanup (unused code, stale comments, duplication, outdated docs), speed
  (slow code, tests and checks, timed before and after), complexity (functions radon rates D or
  worse) and reliability (crashes, hangs, intermittent failures, each fixed with a test that fails
  on the old code). The outputs are compared byte for byte on the same deterministic inputs before
  and after. It reports first with nothing changed, plans small verifiable steps and executes only
  what the owner approves; a change of functionality goes to feature-manager. Use it for
  clean up, remove unused code, optimise, speed up the code or the test suite, simplify, reduce
  complexity, fix the hang, why does it crash, tidy the docs, or a review of what can go.
  Conventions come from project-style-rpx.
---

# project-optimize

It makes the same project cleaner, faster, simpler and more reliable, never different.

**Assumes** (deliberate): a **Python** project following `project-style-rpx`, tested with
**pytest**, in **git**; **radon** (complexity) run from a throwaway environment; outputs that are
deterministic given their inputs (and seed, if anything is random) - an output that is not is a
reliability finding first.

## 0. Read the project's part first

[references/project.md](references/project.md) names the project's outputs and the command that
produces each from deterministic inputs (a seed if anything is random), what is never touched, the
ways code is reached that a grep misses, the known slow paths and the interpreter. **It overrides
this skill** where they differ: a rule of this file that a project decision replaces is written
there, not here.

**Conventions come from `project-style-rpx`**, and commits follow `feature-manager` § 8 (small, your
own hunks only, never pushed unasked). Neither is restated here.

## The rule: behaviour does not change

What the project computes, writes and prints stays exactly as it is: the generated files, the
verdicts and every violation they list, every derived data set and its manifest, every
`[INFO]`/`[WARNING]`/`[ERROR]` line and operator sentence, the configuration the owner edits. Every
step proves it, by the proof its kind requires:

| Kind | What it covers | Proof |
|---|---|---|
| **Cleanup** | Unused code and files, stale or false comments and docs, duplicated logic, tests that cannot fail | Equivalence: pinning tests pass on the old code, and the output is byte-identical |
| **Speed** | Slow paths | Equivalence, plus timing before and after on the same inputs |
| **Complexity** | Functions radon rates **D or worse** | Equivalence. Split only when the parts read as named steps, not to satisfy the score |
| **Reliability** | Crashes, hangs, leaks, intermittent failures | A test that fails on the old code and passes on the new, proven by breaking the fix |

**The output is the contract.** Any step that touches code on the path from the inputs to a written
output is proven by producing every output the project reference names **from the same deterministic
inputs** (and seed, if anything is random) before and after and comparing the files **byte for byte**. Printed output is compared the same way after
the project's **normalisation filter** - a documented command in the project reference that
replaces only what legitimately varies between runs (an output path, a wall-clock time) with a
fixed token. Nothing else is filtered: a filter that hides a changed number hides a behaviour
change. **An output that cannot be byte-identical** (a video encoder whose rate control reacts to a
one-level pixel difference, for example) gets a tolerance only after a measurement shows why identity
is not reachable; the tolerance (frame count, size, a PSNR floor, ...) and its measured cause go into
the project reference, and every other output stays byte for byte. An output that is still valid but different is a behaviour change, not an optimization: a faster search that returns another valid answer is for
`feature-manager`.

**Anything that would touch functionality is not optimization.** List it in the report under **For
feature-manager**, and do not do it here. Cases:

- removing something the owner sees or runs: a script, a printed line, a configuration field (even
  one that does nothing: the loader would then warn on it);
- changing a margin, a tolerance, a sample spacing, an exclusion or a numeric format, even when every
  test still passes;
- a reliability fix that adds a message, an error or a different sequence.

## Never touched

- What the project reference lists: vendored files, source data, committed derived data (rebuilding
  it is a deliberate change with its own report), the original inputs whose bytes are pins.
- **The repository root as a workspace.** Reviewers, mutations and reproductions run only in a
  scratch clone or a temporary directory outside the repository, with that directory as the working
  directory, and `git status` is checked when each one returns.

## Phase 1 - Report, change nothing

### Cleanup

| Look for | Evidence that makes it a finding |
|---|---|
| Unused code, files, exports | No reader after the checks in *A hit is a candidate* below |
| Duplicated logic | The copies side by side, and which one is the reader of record (style: one reader per format) |
| Stale or false comments and docs | The comment or doc next to the code, measurement or SPEC section it contradicts |
| Tests that cannot fail | The mutation that left it green: the line deleted, the branch swapped (style references/python.md > Tests) |

**Documentation.** Clean docs by truth, not by length. Classify each passage: **stale** (contradicts
the code, a measurement or the SPEC), **duplicate** (said in another file that owns it),
**superseded** (a decision replaced by a later one), **history** (how it got there - git holds it).
Then:

1. Move first whatever is still true and cited by code, configuration, tests or other docs, to the
   file that owns it (style references/markdown.md); correct citations in the same step.
2. List every removal: the passage, its class, where its truth now lives or the commit that holds it.
3. Check that nothing true is lost: every number, name and decision of the old text still occurs in
   the new docs or is on the removal list with its reason (a script that extracts the numbers of
   both versions makes this mechanical).
4. Section numbers that others cite stay (style references/markdown.md).

**Comments.** Only comments that are stale, false or restate the code are candidates (style
references/python.md). A why-comment stays - above all one citing a manual page, a measurement or a
SPEC section behind a value. **When unsure whether a comment explains why, keep it** and list it in
the report as *kept, unsure*, with the line, so the owner can decide.

**A review of what can go (user simplicity).** For a request to make the project simpler for its
user: not only unused code, but every script, tool, generator, folder and dependency the user does
not need. Report first, like every finding.

1. **Inventory.** One row per tracked script or tool, module folder, data folder and dependency:
   *item | purpose | used by | verdict*. *Used by* is the user's workflow (the documented commands),
   the checks (the project's tiers), the tests, or nobody; the verdict is KEEP, REMOVE or MERGE
   (into what). Each REMOVE or MERGE names its evidence (*A hit is a candidate until its reader is
   found*).
2. **Who carries it out.** Removing or merging what the user runs or sees is a change of
   functionality (*Anything that would touch functionality*, above): it goes under **For
   feature-manager**, which carries it out with steps 3-8. Code left without a reader is cleanup,
   here.
3. **Dead code after the removals.** Every function, constant, class, fixture and test helper whose
   only readers were the removed items, searched by name and as a string, goes in the same step as
   its last reader, with its tests (the collected count drops by exactly those).
4. **Dependencies.** A dependency goes in the same commit as its last reader, never before it;
   removing a pin is the owner's decision, like adding one (*Speed*, a new dependency). Measured
   before and after in a throwaway environment: install time (three runs, warm cache, with the
   spread), environment size, package count.
5. **Restore point first.** Before the first removal, the commit before it is recorded by its full
   hash in the change's design-decisions entry, with how to bring a file back
   (`git show <hash>:<path>`, `git checkout <hash> -- <path>`).
6. **Nothing points to what went.** After each removal, `git grep` for every removed file, module,
   function, option and dependency, in its exact spelling (a case-insensitive hit is checked by
   hand): no hit outside the history the project keeps and the committed artefacts that cannot be
   edited, both listed by path, with the reason, in the report.
7. **What stays is unchanged.** Every output of what stays is compared with a frozen run of the
   commit before the change, on the same inputs. The deterministic outputs are compared byte for
   byte, printed output after the normalisation filter (*The output is the contract*); an output
   the project compares with tolerances instead stays within its regression tolerances and envelopes. The project
   reference says which output is which and where each tolerance lives. A difference is allowed
   only in lines the owner approved one by one (each listed, old and new); a pin those lines move is
   re-captured in its own commit (feature-manager §8).
8. **A fresh clone last.** The installer, the user's main command, both tiers of checks and the
   checkers run in a fresh clone with `HOME` and `TMPDIR` set to empty directories (*Prove it
   outside the working tree*, below): the proof that nothing removed was still needed by a path the
   developer's tree hid.

### Speed

**Measure every check first.** Before speeding anything up, time each check the project runs: every
script in the checks, the fast suite and the full suite (serially and, if the project has it, in
parallel), the heaviest single runs, and the slowest tests (`pytest --durations=15`); three runs each,
with the spread, the machine and the date, into the project reference. The list says where the time
goes; a guess usually picks the wrong target.

**Two tiers of checks.** From those timings, propose a **per-commit tier** (minutes: the fast tests,
the exact pins, the style checker) and a **per-accepted-feature tier** (the slow runs, the full suite);
the owner approves, and `CLAUDE.md` records both with commands and times (feature-manager §7 runs
them).

**Common speed steps**, each proven like any other:

- **Independent heavy runs in parallel**: a process pool, results collected in input order, and the
  outputs proven byte-identical to the sequential run before the pool is adopted.
- **Build once per session**: an expensive object several tests build (a model, a compiled program)
  becomes a session fixture (once per worker with a parallel runner). A disk cache only when its key
  holds the hash of every input and of the code that builds it (style references/structure.md >
  *Committed generated data* for hashing inputs); otherwise it serves stale results.
- **A new dependency** (a parallel test runner) is the owner's decision: pinned `==`, recorded in
  the SPEC, and the suite must still pass without it (serially).

A slow path is a finding only with a timing: what was timed, on which inputs and seed, on which
machine, over how many runs, with the spread. Without a measurement it is a guess. The step's proof is
equivalence plus the same timing after: same inputs (and seed), same machine, several runs, both
numbers and their spread reported.

### Complexity

Find candidates with radon. It only reads source, so run it from a throwaway environment rather than
adding it to the project's, with the project's explicit interpreter (`SCRATCH` is a temporary
directory outside the repository; the project reference names the interpreter and the folders):

```bash
<explicit python> -m venv "$SCRATCH/radon" && "$SCRATCH/radon/bin/pip" install -q radon
"$SCRATCH/radon/bin/radon" cc -s -n D <code folders>
```

**A module with two concerns** is split by topic, not by kind (style references/structure.md >
*Modules*): the blocks move verbatim (count them: moved = total), the tests are mirrored and stay
otherwise identical (compare their ASTs), and every output is byte-identical.

**A score alone is not a reason.** A function that is a table of rules, or one flat sequence of
checks (a configuration loader validating field after field), can score high and read fine. Splitting
it scatters what belongs together. A function is a finding when it does several things that already
read as steps (numbered comments, blocks with their own purpose), and the split gives each step a
name.

Equivalence for a split means the old and new code run side by side on many inputs, including the
failing ones, and give the same output, errors included. Example: a loader split into named steps is
run, old and new, on the shipped file and on many mutated copies of it; the same files load, the same
are refused, with the same error text in the same order.

### Reliability

**Allowed only where the intended behaviour is already defined and the code fails to deliver it.**
Removing a crash or a hang takes nothing away from the owner. If the fix would change what the owner
sees or gets (a new message, a new error, a different result), it is not optimization: stop and hand
it to `feature-manager`.

What to look for:

- **A resource left open** (a viewer, a file, a process, a simulation) when a script exits on an error.
- **A failure surfaced as the wrong error**: a malformed file reported as a missing one.
- **Non-determinism**: an unseeded random source, iteration over an unordered container feeding the
  output, a numerical result that depends on thread count. It shows as an output that differs
  between two runs on the same inputs (and seed).
- **An intermittent failure called a flake before it is named.**

**Prove it outside the working tree.** A test or script that passes only in the developer's tree
(an ignored folder that exists there, a file left by an earlier run, a path under the home folder) is
a reliability finding. Run the suite and the main scripts in a fresh clone (generated and ignored
folders absent, own `TMPDIR`), and the project's code with `HOME` set to an empty directory, so
nothing depends on personal configuration such as `~/.claude/`. A failure there gets a test that runs
in a fresh tree.

**Evidence for an intermittent problem is a stress run, not one green run.** Loop the suspect test
file or node with a per-run timeout above its own run time, for example on macOS (no `timeout`
command by default):

```bash
perl -e 'alarm shift; exec @ARGV' 300 <project python> -m pytest test/<file>::<test> -q -p no:cacheprovider
```

Report the failure rate before the fix and the run count after it, and keep the full output of every
run that does not print the expected pass count. N clean runs at the old failure rate is evidence,
not proof, and is reported as such. Do not edit the source while a loop runs.

### A hit is a candidate until its reader is found

vulture, pyflakes, coverage, radon and grep say where to look (style: *a static-analysis hit is a
candidate, not a finding*). Before calling anything unused, check every way code is reached that a
grep for its name misses:

- **Entry points**: every script, the installer (which names requirement and manifest files), and
  scripts that import other scripts as modules.
- **Tests**: `conftest.py` puts `src/` on the path; pytest finds fixtures and hooks (`pytest_*`) by
  name; script tests run scripts in a subprocess.
- **Configuration keys**: a field is used if the loader maps it and a reader changes behaviour on it.
- **Names by string**: anything looked up by a string (a registry, a model's element names, a
  column name) - search for the name as a string literal and in the configuration.
- **Files by path string**: data folders, fixtures, skill configuration files.
- **Docs**: a file or name cited in the SPEC, design-decisions, KNOWN_ISSUES or the README is a
  reader of that name. Removing the thing means correcting the citation in the same step.

The project reference adds its own (and names the concrete folders and names).

### Finding format

One table per kind (Cleanup, Speed, Complexity, Reliability), then **For feature-manager**, then
*kept, unsure* comments:

| # | Kind | Location | Evidence | Why it matters | Risk | Proof planned | Certainty |
|---|---|---|---|---|---|---|---|
| 1 | Speed | `path:line` | the timing, or the reader found or not found | the cost of leaving it | what could break | equivalence (outputs byte-identical, same inputs) + timing | **confirmed** / **likely** / **unknown** |

- **confirmed**: every check was run, and the reader search, timing, score or failing test is shown.
- **likely**: the static evidence is clear, but a check could not be run. Name the missing check.
- **unknown**: worth a look, not worth acting on yet.

End the report with what was **not** examined.

## Phase 2 - Plan, then wait for approval

A prioritised list of steps, highest value and lowest risk first. Each step:

- is **one concern** of **one kind**, small enough to review alone, and becomes one commit;
- states **its proof** from the table above, the tests that pin it, and the collected count expected
  after it;
- can be **reverted on its own** without touching the others.

Execute only the steps the owner approves, in order, reporting after each. If a step turns out not to
be what the report said (a reader appears, the output differs, the fix would show the owner something
new), stop and report. Do not adapt the step.

## Rules for executing

- **Equivalence** as style references/python.md > Tests defines it. The outputs compared are those
  the project reference names; printed output after its normalisation filter. A difference stops
  the step.
- **A reliability fix's test fails on the old code.** Run it there first and show the failure, then
  break the fix once on the new code (python.md > Tests). For an intermittent fault, the stress run
  before and after is part of the proof.
- **Removing a test** is itself a finding with evidence (it cannot fail, or it duplicates another).
  The collected count drops by exactly that many.
- **Docs**: a stale statement is corrected, not deleted, when the fact it records still matters.
  Corrections to a design-decisions entry are made in place and say so (style references/markdown.md).
- After each step: the style checker on changed files, the suite, the collected count, and
  `git status` clean apart from the step.
- **A restructure in several steps** keeps the old entry point working through thin shims (the old
  names re-exported from the new modules) until the last step removes them; each step proves its
  outputs identical against a frozen run of the old code.
- **A rewrite that git no longer sees as a rename** (a file changed beyond git's 50 % similarity)
  records in `CLAUDE.md` how to follow history across it: `git log --follow -M20% <file>`.
