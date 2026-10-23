# project-optimize: project reference for AnyScan

AnyScan's part of the personal skill **project-optimize**; it overrides that skill where they differ.
Conventions are project-style-rpx's, commits feature-manager § 8. This folder has no `SKILL.md` on
purpose: a personal skill wins over a project skill of the same name, so a copy here would be ignored
and drift.

## Outputs compared byte for byte

Every output below is produced into a scratch directory, never the repository, by
`Example/Vision/analyze.py` run unchanged through the frozen-clock wrapper (next section), with the
model-free fallback describer (`--no-describe`). Gemma's descriptions are **not** compared: Gemma is
not deterministic across platforms (MLX on macOS, the GPU on Linux), so a change on its path is
judged on the same crops (feature-manager `project.md` > *AI*), never by bytes.

| Output | Produced by (into a temporary directory) | Deterministic inputs | Identical on two runs (date) |
|---|---|---|---|
| Detect-only artefacts: 41 `*_annotated.png`, 41 `*_mask.png`, 150 `*_objNN_crop.png` | `"$PY" -I "$SCRATCH/frozen_analyze.py" "$REPO" --no-describe --output-dir "$SCRATCH/before"` | `Data/Images/Test/` (41 frames), the default mode file `Config_…_Mode_Seg_Anything.yaml`, `Data/Images/Background/Image_Background_001.png`, `models/FastSAM/FastSAM-x.pt`; no randomness once the clock is frozen | yes, 232 of 232 files, 2026-10-23 (Apple M2 Pro, FastSAM on its default device) |
| Catalogue artefacts, the same 232 files | the same, plus `--config "$REPO/Configuration/Mode/Config_a2A1920_51gcPRO_Computar_M1228_MPW3_Mode_Mounting_Plate.yaml"` | the above, plus `Data/Catalogue/mounting_plate/` and `models/dinov2-base/` | yes, 232 of 232 files, 2026-10-23 |
| `analyze.py`'s printed report (per-frame counts, cues, the TOTAL table) for both runs above | its stdout | as above | yes after the filter below, 2026-10-23 |
| `test/Vision/data/characterization.txt` | `test/Vision/test_characterize.py` regenerates and diffs it on every run | the test's own frames | pinned by its test |

Also compared when a step touches them: rendered pixels of a UI change (an offscreen grab before and
after), a capture set and a run-summary CSV row written through the application's path.

Run on Linux, these outputs have not been compared (FastSAM on CUDA); a step proven on macOS says so.

## The frozen clock

`analyze.py` draws the run timestamp into every artefact's provenance footer, so two runs differ in
those pixels (251 of them per file, measured 2026-10-23) and nowhere else. The wrapper freezes
`datetime.now()` and runs the script unchanged; it lives in `$SCRATCH`, not the repository:

```python
"""Run Example/Vision/analyze.py unchanged with datetime.now() frozen, so its run stamp is fixed.

Usage: <project python> frozen_analyze.py <repo> [analyze.py options ...]
"""
import datetime
import runpy
import sys


class _Frozen_Datetime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 1, 1, 0, 0, 0, tzinfo=tz)


datetime.datetime = _Frozen_Datetime
repo = sys.argv.pop(1)
sys.argv[0] = repo + '/Example/Vision/analyze.py'
runpy.run_path(sys.argv[0], run_name='__main__')
```

## Normalisation filter for printed output

What varies between runs and is replaced (nothing else): each frame's wall-clock time `(NNN ms)` and
the output directory on the last line.

```bash
sed -E -e 's/\([0-9]+ ms\)/(<ms>)/g' -e 's#written to: .*#written to: <out>#' "$SCRATCH/before.stdout" > "$SCRATCH/before.normalised"
```

Checked on two real runs of each mode: identical after the filter, 2026-10-23.

## Never touched

- **`models/`**: weights, and the installer tests' fixture; the suite fails if it changes
  ([*models/ is out of reach of the installer tests…*](../../../../docs/design-decisions.md#models-is-out-of-reach-of-the-installer-tests-and-the-suite-fails-if-it-changes)).
- **Captures and data**: `Data/` (the pinned test set, references and their sidecars, answer key),
  `logger/` contents, calibration capture sets.
- **`src/Transformation/`**: inherited, excluded in `check_style.json` with its reason. Findings in it
  are reported under their own heading, never acted on.
- **The repository root as a workspace.** Reviewers, mutations and reproductions run in a scratch
  clone (`cp -c -R`, an APFS clone) or a temporary directory outside the repository, with that directory
  as the working directory. A script's `tempfile.mkdtemp(dir='.')` run from the root once left six
  session-log folders and a truncated copy of the calibration there. Every reviewer's prompt says
  this, and `git status` is checked when each returns.

## Reached without a grep hit

- **Qt dispatch**: methods marked `# << QT OVERRIDE >> #`, slots passed to `.connect(...)`, and paint
  paths that read a value a grep does not obviously link (the status cell's `dot_color`).
- **Attribute lookups by string**: `getattr(obj, 'Name', …)` in `src/UI/Core.py`,
  `src/UI/Views/Trends.py` and `src/Camera/Core.py`; search for the name as a string literal too.
- **Configuration keys**: a `*_Str` field is read through `Configuration/Core.py`'s `CONST_FIELDS`
  table and the YAML; a key is used if `Load_Configuration` maps it and a reader changes behaviour on it.
- **Entry points**: `App/run.py`, every script in `Example/`, and `install.sh` (which names
  `requirements/*.txt` and model paths).
- **Harnesses and tests**: `test/conftest.py` puts `src/`, `App/` and `Example/Vision` on the path, so
  tests import harness code; pytest finds fixtures and hooks by name; the characterization golden
  file is read by its test.
- **Files by path string**: `App/assets/` (logo, fonts, icons), `images/` linked from the README,
  `.gitkeep` files that keep a required directory in a fresh clone (`logger/Station_Events/.gitkeep`:
  the shipped configuration does not load without it), and
  `.claude/skills/project-style-rpx/references/check_style.json`.
- **Docs**: a file or name cited in `docs/`, `KNOWN_ISSUES.md` or the README is a reader of that name;
  removing the thing corrects the citation in the same step.

## Proof patterns from this project

- **Complexity**: commit `4f7f201` split `Load_Configuration` (F 52 → C 14), `Calibrate` (E 36 → C 11)
  and `analyze.main` (D 21 → B 7) along their own steps. `Load_Configuration` was compared with the
  committed loader on 1,052 mutated mode files (175 loaded, 877 refused, identically, down to the
  error text and its order); `Calibrate` on four synthetic view sets with OpenCV pinned to one thread
  ([*Two calibrations of the same images agree only to the last digits…*](../../../../docs/design-decisions.md#two-calibrations-of-the-same-images-agree-only-to-the-last-digits--read-a-small-difference-as-noise));
  `analyze.main` on a real run, timings and stamps masked.
- **Reliability**, from where it happened here:
  - a worker's thread released while still running - the UI suite hung or crashed in about 4 runs of
    53 ([*A worker's thread is joined before the slot that takes its result lets the worker go*](../../../../docs/design-decisions.md#a-workers-thread-is-joined-before-the-slot-that-takes-its-result-lets-the-worker-go));
  - a close that destroys a running thread, `QThread: Destroyed while thread is still running`
    ([*Closing waits for a running worker…*](../../../../docs/design-decisions.md#closing-waits-for-a-running-worker-stops-an-analysis-before-its-next-object-and-has-an-escape);
    its fix added a visible stopping state, so it was a feature);
  - a loss the hardware never reports ([*A lost connection is detected by the camera, not only by DISCONNECT*](../../../../docs/design-decisions.md#a-lost-connection-is-detected-by-the-camera-not-only-by-disconnect));
  - a failure surfaced as the wrong error ([*The configuration sets the camera's sensor window*](../../../../docs/design-decisions.md#the-configuration-sets-the-cameras-sensor-window),
    and [*`Basler_Cls` connection code raises and catches bare `Exception`*](../../../../KNOWN_ISSUES.md#basler_cls-connection-code-raises-and-catches-bare-exception)).
- **Stress run** for an intermittent fault: 30 runs of `test/UI` under a 300 s alarm, `faulthandler`
  on and a native `sample <pid>` of any hung run (pytest's capture swallows `faulthandler_timeout`
  dumps): `perl -e 'alarm shift; exec @ARGV' 300 .venv/bin/python -m pytest test/UI -q -p no:cacheprovider`.
- **Functionality the user sees** (a view, a record, a configuration field even if it does nothing, a
  harness in `Example/`, a new message, state or close sequence) is for feature-manager.
- Every step that changes `src/`, `App/`, `Configuration/` or `Example/` reviews `docs/capabilities.md`
  (feature-manager `project.md` > *Docs*): normally the *Last reviewed* line moves, with
  *Capabilities: no change (optimization: <kind>)* in the message.

## Slow paths and timings

| Path | Time | Machine, date |
|---|---|---|
| `analyze.py --no-describe`, detect-only, 41 frames | 26 s wall (two runs: 26.3, 25.9) | Apple M2 Pro, 2026-10-23 |
| `analyze.py --no-describe`, catalogue, 41 frames | 42 s wall (42.6, 41.8) | Apple M2 Pro, 2026-10-23 |
| the default suite, `pytest -q` (1231 passed, 186 skipped) | 199 s | Apple M2 Pro, 2026-10-23 |

## Interpreter and tools

- Project python: `.venv/bin/python` (`CLAUDE.md`); `-I` for anything run against scratch copies.
- Explicit python for throwaway environments (radon, cmarkgfm): `/opt/homebrew/bin/python3`.
- Code folders for radon: `src App Example`.
