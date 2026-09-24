# FastSAM pipeline — branch summary

> Historical record of the FastSAM branch. The describer it mentions (Florence-2) was later
> replaced by Gemma 4 E4B — see `docs/design-decisions.md`. Its stage 3 (`Mask_Filter`, the
> change-coverage gate, `CONST_FILTER_CHANGE_COVERAGE`, `CONST_SEG_MASK_DILATE_KERNEL`) no longer
> exists either: fusion replaced it, and the detection parameters now live in the configuration.
> For what is open today, read `KNOWN_ISSUES.md` and `docs/capture-checklist.md`, not this file.

Review summary for `feat/fastsam-pipeline` (off `style/role-migration`). What
changed, what is tested, what is tuned only against synthetic data, and what needs
a real capture before this is trustworthy on the shop floor.

## Goal

Replace OpenCV region extraction — which merged touching objects and cropped
shadows and neighbours into the described region — with FastSAM instance
segmentation behind a swappable seam, keeping Florence-2 for description.
13 commits, +2231 / −257 across 22 files.

## What changed

- **Stage 1 — background subtraction** (`Vision/Utilities/Segmentation.py`,
  `Build_Mask`): now returns `(change mask, candidate regions)` and slightly dilates
  the mask. The change mask skips stage 2 and feeds stage 3's coverage gate directly.
- **Stage 2 — instance segmentation** (`Vision/Segmenter.py`, new):
  `Segmenter_Backend_Cls` → `Fast_Sam_Cls`, ultralytics loaded lazily. Default is
  **everything-mode** (box-prompt kept as a config alternative — it inherits stage-1
  merges, so it does not separate touching parts).
- **Stage 3 — mask filtering** (`Vision/Utilities/Mask_Filter.py`, new):
  change-coverage gate, area / border rejection, part/whole NMS (intersection-over-
  smaller, whole-over-part tiebreak), left-to-right ordering. Replaced and removed
  the old `Find_Objects`.
- **Stage 4 — description** (`Vision/Core.py`): `Analyze` reads as four named
  stages; masked crop fed to the describer by default; describer is Florence-2 or
  the new model-free `Describe_Fallback` (HSV colour classification).
  `Detection_Str` gained `Mask`, `Change_Coverage`, `Segmenter_Score`.
- **Example** (`Example/Vision/analyze.py`, new): runs the whole pipeline on a real
  (reference, scene) image pair with the full flag set, and writes `result.png`,
  `change_mask.png`, per-object crop/mask/description files and `summary.json`.
- **Removed:** the `<REGION_PROPOSAL>` no-background detector, `Crop_With_Pad`, and
  orphaned constants. Dependencies gained `ultralytics`; the numpy floor was raised
  to 2.2 so a fresh install is not dragged down to numpy 1.x / opencv 4.x.

## What is tested

`pytest` 64 passed / 4 skipped; `--runslow` 67 passed. Harness baseline green;
`check_style` adds no new categories.

- **Mask filter** (hermetic): shadow / static-scene rejection, whole-frame and
  border rejection, nested-mask NMS, whole-over-part tiebreak, left-to-right
  ordering, identical-frames → no objects.
- **Fallback describer** (hermetic): HSV colour including the dark-red-vs-brown case.
- **Real path** (slow, weight-gated, loud banner when absent): CPU FastSAM +
  Florence smoke; and the shadow-sliver **known-defect** test below.
- **Contracts:** the new modules import under a PyQt5 block (Qt-free separation);
  the characterization harness stays byte-identical.

## Tuned only against synthetic data

Every threshold below was set and checked against synthetic frames (solid shapes on
the flat green reference), never against hardware. See `KNOWN_ISSUES.md`.

- `CONST_FILTER_CHANGE_COVERAGE = 0.35` and `CONST_SEG_MASK_DILATE_KERNEL = 5` —
  validated on a degenerate distribution (objects ~1.0, shadow 0.0); real-object
  coverage is unknown.
- Everything-mode at the configured `Segmentation.Confidence`, the NMS overlap threshold,
  and the area / border limits.

## Needs a real capture before shop-floor trust

1. **Low-contrast parts.** FastSAM missed a mid-grey box and a near-black plate in
   synthetic scenes; grey / metallic / dark parts are exactly what this inspects.
   Saturated-colour scenes were used *because* of this, so a passing demo run shows
   the wiring works, not that all parts are found.
2. **Coverage gate + dilation.** Set them from real-object coverage numbers, not
   synthetic 1.0s. Watch for real objects sitting just above 0.35 (dilation too
   small).
3. **Shadow-edge slivers.** A cast shadow abutting a part makes everything-mode emit
   a boundary sliver that clears the gate and evades the NMS, so N objects can report
   as more than N (measured: two objects → four detections). This is a worse operator
   experience than the old path's merge, and the old path could not produce it.
   Pinned by `test_shadow_abutting_part_over_segments_known_defect`. Confirm on real
   shadowed parts and re-tune the thresholds from that.
4. **Everything-mode determinism and speed** on real frames.

## Trade-offs, accepted

Gained: touching parts separated; shadow / neighbour pixels removed from the
described crop; precise per-object masks with coverage and segmenter score.

Paid: analysis now **requires a reference background** (the no-background path was
removed); +144 MB FastSAM model, +torch, +matplotlib; everything-mode is ~2.5 s /
frame on CPU versus milliseconds for the blob path; and it is less reliable on
low-contrast shapes and can over-segment at shadow edges — failure modes the coarse
OpenCV path did not have. The verdict's confidence branch is left dormant by design.

## Old vs new, one input pair

Two objects 10 px apart with a shadow abutting their lower edges:

| | Old (OpenCV blob) | New (FastSAM + filter) |
| --- | --- | --- |
| objects | 1 (A and B merged) | 4 (A, B separated + 2 shadow slivers) |
| shadow in described crop | whole shadow in the one rectangular crop | removed from the object crops by the mask |

The new path wins on what it was built to fix (separation, shadow-free crops) and
is worse on cost, low-contrast robustness, and the shadow-edge over-segmentation.
