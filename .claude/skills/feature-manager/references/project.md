# feature-manager: project reference for AnyScan

AnyScan's part of the procedure in **feature-manager** (`SKILL.md`, beside this folder); it overrides
that skill where they differ. The language rule (notes in Czech or Slovak, everything written in
English) and the work rules (a branch per revision, pushing, attribution) are in `CLAUDE.md`.

## Records

In `.claude/project-docs/`, as the generic skill says, with one more (project-style-rpx `project.md` >
*Records*):

- **`SPEC.md`** - what the application does, its configuration tables, views, records and hardware;
  held to the code by `test/integration/test_capabilities_doc.py`. Its sections are named, not numbered.
- **`design-decisions.md`** (DD) - why; **`KNOWN_ISSUES.md`** - what is open;
  **`capture-checklist.md`** - what only the rig can show.
- **`FEATURES.md`** - the tracker: a line per revision (R1, R2, …), the owner's answers with their dates, and its
  acceptance with the date.

## What the output is

A verdict per object (OK, NOK, Warning with its kind) and a description, shown to the operator at the
station, recorded in the capture set, the run-summary CSV and the daily station event file.

## Physical system and safety

None. AnyScan drives no hardware beyond the camera it reads; a person acts on its verdicts. What a
verdict may claim is bounded by README > Limitations (sizes are repeatable, not absolute; the
describer is not a defect detector; a catalogue mode checks only what its item lists). The sentence a
result carries is the README's own warning (README.md, the `[!IMPORTANT]` alert under Figure 1): a
verdict is advice to the operator, verified only as SPEC > *Verified on hardware, and not yet* states.

## Always "large" (ask before building)

- Records and contracts: the run-summary CSV, the station event file, `_objects.json` /
  `_distorted.json` (a capture set), the session log's event markers.
- Configuration: a new field or section in a mode, station or calibration file, or a catalogue item.
- The pinned test set `Data/Images/Test/` (it carries its inventory, xfails and doc citations).

## Real data for reproducing a premise

- **Frames**: `Data/Images/Test/` (the pinned set) or a capture set under `logger/captures/`. If it
  cannot be reproduced on one of them, say so and stop.
- **Walk the stages** for that frame, not just the final result: the background mask, the FastSAM
  masks, the fused components before and after the closing, the crop the describer saw. The Camera
  View's Heatmap shows the background difference.
- **Harnesses** for before and after numbers: `Example/Vision/analyze.py`,
  `Example/Vision/evaluate_describer.py`. Synthetic frames only for cases the set cannot show, and
  labelled as such.

## Premise example

Two touching plates came back as one object, and FastSAM was blamed. The masks showed causes in the
fusion and the background cue: the fusion's closing joined plates about 10 px apart that were
separate before it, and in two of the three frames where touching plates merged, the bridge came
from the background cue, not from FastSAM. See DD *The closing never joins two components* and
KNOWN_ISSUES *Touching parts merge before the closing*. A "better segmenter" would have fixed one
frame of three.

## Typical better levers

- *Filtering after identification instead of changing segmentation*: decide what to keep once the
  objects are found and identified, rather than retuning the stage that finds them. See
  [*A catalogue mode identifies by similarity, and an object of the part's shape that does not look like it is NOK*](../../../project-docs/design-decisions.md#a-catalogue-mode-identifies-by-similarity-and-an-object-of-the-parts-shape-that-does-not-look-like-it-is-nok):
  FastSAM and the fusion keep finding every object; DINOv2 and the rule decide which is the part.
- *Measuring a threshold before moving it*: see
  [*The colour-name saturation cutoff is 120…*](../../../project-docs/design-decisions.md#the-colour-name-saturation-cutoff-is-120-and-was-not-tuned-for-the-red-block),
  [*The object crop padding stays at 0.20 for Gemma*](../../../project-docs/design-decisions.md#the-object-crop-padding-stays-at-020-for-gemma),
  and route 2 in [*Touching parts merge before the closing*](../../../project-docs/KNOWN_ISSUES.md#touching-parts-merge-before-the-closing):
  a larger `Image_Size` looked like the fix and cost frames that counted correctly.
- *A larger model that wasn't better*: see
  [*Gemma 4 12B was measured against E4B and is not better…*](../../../project-docs/design-decisions.md#gemma-4-12b-was-measured-against-e4b-and-is-not-better-e4b-stays-the-describer).

## Domain checklist

Each item links to where it happened here. Read the record; it is not retold.

**Vision**

- [ ] Lighting and the reference match:
      [*The background reference carries its provenance…*](../../../project-docs/design-decisions.md#the-background-reference-carries-its-provenance-harnesses-capture-through-the-apps-path).
- [ ] Calibration and the frame window match:
      [*The configuration sets the camera's sensor window*](../../../project-docs/design-decisions.md#the-configuration-sets-the-cameras-sensor-window).
- [ ] Precision shown versus precision measured:
      [*Sizes keep full precision…*](../../../project-docs/design-decisions.md#sizes-keep-full-precision-only-the-display-rounds-to-a-fixed-two-decimals)
      and [README > Limitations](../../../../README.md#measurements-are-repeatable-not-absolute).
- [ ] Results from one table's frames generalising:
      [*The fusion's parameters are validated on one table under one light*](../../../project-docs/KNOWN_ISSUES.md#the-fusions-parameters-are-validated-on-one-table-under-one-light).
- [ ] Parts touching:
      [*Touching parts merge before the closing*](../../../project-docs/KNOWN_ISSUES.md#touching-parts-merge-before-the-closing)
      and [*The closing never joins two components*](../../../project-docs/design-decisions.md#the-closing-never-joins-two-components).

**AI**

- [ ] Prompts that prime the answer (expected values, checklists recited back): the checklist echo in
      [*Gemma 4 12B was measured against E4B…*](../../../project-docs/design-decisions.md#gemma-4-12b-was-measured-against-e4b-and-is-not-better-e4b-stays-the-describer),
      and [*Gemma reads some through-holes as "a central green element"*](../../../project-docs/KNOWN_ISSUES.md#gemma-reads-some-through-holes-as-a-central-green-element),
      where wording tuned to one frame made another worse.
- [ ] A describer is not a detector:
      [README > Limitations](../../../../README.md#the-describer-is-not-a-defect-detector).
- [ ] Model comparisons on the same crops and settings:
      [*E4B stays the describer on both machines…*](../../../project-docs/design-decisions.md#e4b-stays-the-describer-on-both-machines-the-owners-choice-one-wrong-statement-ahead-of-the-12b).
- [ ] Provenance of weights: the pinned revision and the licence check in
      [README > Platform](../../../../README.md#platform) and [Licence note](../../../../README.md#licence-note).
- [ ] Gemma is not deterministic (MLX on macOS, the GPU on Linux): a before/after comparison of its
      text is a judgement on the same crops, never a byte comparison.

**Evaluation**

- [ ] The metric that matters: in quality control, false acceptance (a bad part passed), not overall
      accuracy. See *Why step 3 has no lower bound* in the DD entry linked under *Typical better levers*: a same-sized foreign
      object reads NOK, not Warning, because that is the safer error.
- [ ] A test set changed without its inventory:
      [*A replaced image never keeps its name*](../../../project-docs/design-decisions.md#a-replaced-image-never-keeps-its-name).

**Software**

- [ ] Worker threads and close paths:
      [*A worker's thread is joined before the slot that takes its result lets the worker go*](../../../project-docs/design-decisions.md#a-workers-thread-is-joined-before-the-slot-that-takes-its-result-lets-the-worker-go)
      and [*Closing waits for a running worker…*](../../../project-docs/design-decisions.md#closing-waits-for-a-running-worker-stops-an-analysis-before-its-next-object-and-has-an-escape).
- [ ] Configuration fields that do nothing:
      [project-style-rpx project.md > *A field must be read…*](../../project-style-rpx/references/project.md#a-field-must-be-read-by-something-that-can-change-behaviour-).
- [ ] Machine-specific values committed:
      [project-style-rpx project.md > *Machine-specific values…*](../../project-style-rpx/references/project.md#machine-specific-values-stay-out-of-the-repository-).

## Report rows

Beyond the generic report: **Records** - any change to a capture set, the run-summary CSV, the station
event file or the session log's markers; **Docs** - which `.claude/project-docs/SPEC.md` rows, which DD entry,
which KNOWN_ISSUES or README > Limitations entry; **Risks** - what cannot be tested without the rig
(`.claude/project-docs/capture-checklist.md`).

## Configuration

A new section in a mode, station or calibration file needs a row in `.claude/project-docs/SPEC.md`; its test
fails until the row exists.

## Tests

- The pinned test set is `Data/Images/Test/`; changing it is a deliberate move that carries its
  inventory, xfails and doc citations with it.
- A UI change is rendered offscreen and looked at (truncated text, clipping, contrast); a passing
  region-diff test does not show that.
- Skips (weights absent) are reported as skips. The two tiers and their commands are in `CLAUDE.md` > Commands.

## Commits

- What is never committed, and what is committed only as its own deliberate change: project-style-rpx
  `project.md` > *Root*, the one list.
- **The owner's configuration edits stay the owner's.** The owner's own edits to files under `Configuration/` (mode,
  station and calibration files) are never staged or committed by a session unless the owner names them. This is
  `SKILL.md` > *Commits* (the owner's uncommitted hunks are never staged) applied to the files a station tunes by
  hand.

## Docs - in the same commit as the behaviour

- **`.claude/project-docs/SPEC.md` is reviewed for every commit that changes `src/`, `App/`,
  `Configuration/` or `Example/`.** Required, never skipped. Read the sections the change touches,
  prose and hardware table included, then either:
  - **It affects a capability.** Update the document. A behaviour that changed under the same name
    counts: the drift tests cannot see it, so the review must.
  - **It affects none.** Move the *Last reviewed against the code at commit* line to the commit the
    change is based on (`git rev-parse --short HEAD` before committing), and put *Capabilities: no
    change* and the reason in the commit message.

  Either way the document is in the commit.
  `test_every_code_change_since_the_last_review_updated_the_document` fails on any code commit that
  left it untouched; the other tests in that file catch named things (sections, views, packages,
  records) going out of step.
- **DD**: a new entry for every deliberate choice whose reason the code cannot show, in the generic
  shape (project-style-rpx `project.md` > *Records*). An entry the change contradicts is corrected in
  place.
- **KNOWN_ISSUES**: an open behaviour found is recorded; one the change fixes is removed, and the
  resolution goes to the DD.
- **README**: the triggers are in `.claude/skills/readme-writer/references/project.md` > Triggers.
- **`SUPPORT_CHAT.md`**: when an accepted change alters what the brief states (the state, numbers, commands, rules,
  roles, modules or open items), refresh it with the support-brief skill.
