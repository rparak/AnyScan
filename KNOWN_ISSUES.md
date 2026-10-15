# Known issues

Open behaviours of the pipeline that show up in its text or its numbers, recorded so they are
recognised when they appear. Nobody decides anything on them. **The two limitations that do affect
decisions — sizes are repeatable, not absolute; the describer is not a defect detector — are in the
README, under [Limitations](README.md#limitations).**

Each entry states the behaviour, what it affects, and why it is not fixed. An entry is removed when
the behaviour is fixed, and the resolution is recorded in `docs/design-decisions.md`.

## `Basler_Cls` connection code raises and catches bare `Exception`

`Camera/Basler.py`'s connection code raises and catches bare `Exception` — e.g.
`raise Exception('[ERROR] No Basler cameras detected...')` and `except Exception`
in `__Connect`, `Capture`, `__Set_Optional`, `__Close`. This is the inherited
driver's style, not this codebase's (a `*_Error_Cls` whose message is an operator
sentence), and a bare `except Exception` can mask an unexpected error as a routine one.

- **Impact:** low in practice. The facade `Basler_Camera_Cls._Open`/`_Grab` catches
  whatever `Basler_Cls` raises and re-wraps it into a `Camera_Error_Cls` with an
  actionable sentence, so the operator never sees a bare traceback. The roughness
  is internal to the driver. One path is already narrowed: a setting the camera refuses or
  does not keep (the sensor window) raises `Basler_Settings_Error_Cls`, reported as it stands
  rather than as "no camera", and a failed configure closes the device before raising
  (docs/design-decisions.md, *The configuration sets the camera's sensor window*). So is a camera
  another program holds: it raises `Basler_In_Use_Error_Cls` at once, not retried, reported as in use
  (docs/design-decisions.md, *A new reference is the mean of 8 frames…*).
- **Not fixed here:** the style pass gave `Basler_Cls` types, docstrings and
  `CONST_*` naming but deliberately did not restructure the connection's control flow —
  rewriting it changes behaviour on a hardware path with little automated coverage. Narrow
  the remaining `except Exception` clauses in `__Connect`, `Capture`, `__Set_Optional` and
  `__Close` together with a real camera run.

## Basler's grab retries print to the console and never reach the session log

`Basler_Cls.Capture` (`Camera/Basler.py`) retries a failed or incomplete grab up to `max_attempts`
times (3) and prints each failed attempt to the console (`[WARNING] Attempt n/m ...`). Nothing passes
the count back to `Basler_Camera_Cls`, so a frame that needed retries and then arrived leaves no line
in the session log: a run's log cannot show how often grabs were dropped. A grab that fails on every
attempt is not affected: `Capture` returns None, `_Grab` raises a `Camera_Error_Cls` ("The camera
returned an empty frame..."), and the failed scan is logged.

A count and a warning, "N frame(s) dropped during capture (retried)", were meant to carry this
(`Camera_Cls.Last_Capture_Retries`). Nothing ever set the count, so the warning never fired; both
were removed in `c69b909`.

- **Impact:** low today. Only retried-then-successful grabs are invisible in the log. A cable or
  camera that starts dropping frames shows on the console alone, which an operator who starts the
  application from a launcher does not see, and the station event files never record it.
- **Not fixed here:** reporting it means `Basler_Cls.Capture` returning its attempt count and the
  camera emitting it through its log sink: a new line the operator reads, so a change of its own,
  checked with a real camera (the retry path has no automated coverage).

## The fusion's parameters are validated on one table under one light

This entry used to describe a coverage gate and a mask dilation (`CONST_FILTER_CHANGE_COVERAGE`,
`CONST_SEG_MASK_DILATE_KERNEL`) tuned on synthetic scenes. **Neither exists any more.** The gate
was replaced by fusion: an object survives on *either* cue, FastSAM or background subtraction, so no
coverage threshold decides whether a FastSAM mask counts (docs/design-decisions.md, *The fusion
needs both cues*).

What decides detection now is set in the configuration:

- `Segmentation.Background.*` — the background difference: the Otsu floor, and the opening and
  dilation kernels.
- `Segmentation.Fusion.*` — the closing kernel, the minimum component area, and the
  background-rejection fractions and border count.

Two constants in `Vision/Utilities/Fusion.py` also remain: the 0.10 cue-attribution overlap, which
only labels which cue found an object, and the row band / object cap, which order and limit the
objects.

Unlike the old gate, these have run on real captures, with every frame's count pinned against a
by-eye inventory (`test/integration/test_pipeline.py::test_counts_match_the_inventory`). The pinned
test set is now the 41 frames of the 2026-10-09 session (`Evaluation.Frames`, `Data/Images/Test`,
`Image_055`–`095`, the capture sets' `_raw.png` frames, counted by eye and confirmed by the owner
2026-10-11). Against the shipped reference (`Image_Background_001`, shot 2026-09-28) all 41 match. The
three 2×2 grids of plates set close together (`Image_093`–`095`) come back as four objects each. (The same
scenes' `_distorted.png` files were briefly the set, `Image_014`–`054`, recoverable from `1580e92`: on
nine of them the reference's undistortion border, which those frames lacked, added one object in the
bottom-right corner — see design-decisions, *A replaced image never keeps its name*, case 6.)

Before it, the set was eight frames (`Data/Images/Test/All`, shot under the calibration and reference
then in force; no longer in the repository, recoverable from `1061966`), and all eight matched. Five
more frames, two plates each, were in that set until `b5ca788` removed them (recoverable from
`b5ca788^`); three of those merged, in the entry below. The seven frames of the set before that
(removed in `eb00508`, recoverable from `eb00508^`, shot under the previous calibration) give the same
counts as before the closing changed, object masks unchanged pixel for pixel. 41 frames of one table,
under one light, is still a narrow base.

- **Seen since:** parts that touch or nearly touch, and a dark rusted plate the background cue barely
  sees (2 % of it), carried by FastSAM alone — both on frames no longer in the set (`All/Image_009`–`013`,
  recoverable from `b5ca788^`). And an extra object in the bottom-right corner on frames that skipped
  the undistortion the reference went through (the `_distorted.png` frames `Image_014`–`054`, no longer
  in the repository, recoverable from `1580e92`).
- **Not yet seen on real data:** parts close to the table's colour, and any other lighting.
- **The failure signatures to watch:**
  - a real part missing from the count (a cue failed and the other did not carry it)
  - one part split into two components — the closing fills gaps inside a component but no longer
    joins two separate ones, so a part the cues see in two pieces stays two (not seen on any of the
    twenty frames it was measured on — the thirteen of `b5ca788^` and the previous seven: every count
    there was the same with no closing at all)
  - two neighbours merged into one (they touch; see *Touching parts merge before the closing*)
  - a part's outline running into its shadow (see the harsh-shadow entry below)
- **Until more real frames are analysed,** the parameters are trusted on these frames only.
  When a failure signature appears, look at which stage causes it before changing a parameter: the
  touching-plate merge looked like a closing-kernel problem and three of five were not.

## Touching parts merge before the closing

*Evidence from frames no longer in the test set* — `All/Image_009`–`013`, the five two-plate frames,
were removed in `b5ca788` and are recoverable from `b5ca788^`. Every number in this entry was measured
on them (and, where stated, on the previous set's seven frames, `eb00508^`). The eight frames that
followed in `All/` (no longer in the repository, recoverable from `1061966`) held no touching parts;
route 2 below was re-measured where those eight could answer it. The current set (`Data/Images/Test`)
has plates set close together in its 2×2 grids (`Image_093`–`095`), but none touching by eye, and all
three come back as four objects, so it does not re-measure this entry either. The reasoning stands;
the frames are gone.

Of the five two-plate frames, three came back as ONE object: `All/Image_009`, `011` and `012`. Five routes to separating them have been measured, and all five fail. They fail for the
same reason, and that reason is why this entry exists:

**FastSAM's output contains the division, and nothing structural identifies which level holds it.**
FastSAM returns a hierarchy. In 009, 011 and 012 it is three levels deep: a mask covering both plates,
then each plate, then the hole rings. The division is at the middle level, and with the both-plates mask
removed, FastSAM alone returns the two plates apart in 009 and 011. But for a single machined plate that
same middle level is the plate's two halves, and the two cases measure the same: two touching plates in
011 and one plate's halves in 010 both cover 0.99 of their parent, overlap 0.000 and lie 1.9 px apart.
Any rule that reads the division off the masks' shape either fails to fire on the plates or splits
single objects.

**Two causes merge these frames, and they are independent.** One is FastSAM's (the both-plates mask and
the level problem above). The other is a bridge that remains in each frame when the both-plates mask is
gone. **In 009 and 011 that bridge is the background cue's; in 012 it is FastSAM's own.** So even a
segmenter that got the level right would fix only 012. 009 and 011 would still merge until the
background bridge is dealt with separately. A model swap alone does not close this entry.

| Measured per row (2026-09-28) | 009 | 011 | 012 |
|---|---|---|---|
| Dark seam between the plates | 1 px, absent in 207 of 543 rows | 10 px, every row | 6 px, every row |
| Seam brightness / plates' | 0.58 | 0.38 | 0.47 |
| FastSAM's both-plates mask against each plate | 0.81 against 0.97 / 0.97 | 0.94 against 0.91 / 0.87 | 0.94 against 0.94 / 0.82 |
| FastSAM's two plate masks | 23 px apart, never touching | 2 px apart, never touching | 4 px apart; touching in 35 of 361 rows (y 615–658) |
| The background cue joins them | rows 621–867 | rows 316–320 only (the seam's top end, where it opens into a V) | nowhere |
| Count with the both-plates mask removed: FastSAM alone / fused | 2 / **1** | 2 / **1** | 1 / 1 |

- **The background cue joins 009 and 011 only at those rows; everywhere else it holds them apart.**
  Counterintuitive, so stated plainly: background subtraction asks whether a pixel differs from the
  *green table*, not from the plate. A dark seam is far closer to the dark-green table than a bright
  plate is: its difference from the table (~40–44) sits at those frames' Otsu threshold (42–43), and
  after the blur it falls below — so the cue reads the seam as table in every row of 012 and all but
  five rows of 011. The more visible the seam, the more the cue separates. 009 is the exception: dark
  plates and a faint seam, the threshold drops to its floor (28), and plates and gap all clear it.
- **012's second bridge is FastSAM's own:** its plate edges each bleed ~3 px into a 6 px seam and meet
  mid-seam over 35 rows. At the 1024 px inference size the seam is ~3 px wide.

`010` and `013` (plates 10.8 and 9.8 px apart) used to merge in the closing; once the closing stopped
joining components that were separate before it, they counted two (design-decisions, *The closing
never joins two components*).

- **Impact:** two touching parts read as one object: the count is one low and the size is the pair's.
- **Not fixed here:** left open deliberately. Two plates butted against each other is not a realistic
  inspection case, and every route below either fails to fire on it or splits single objects.
- **What would work** (well-defined, out of scope), in two parts, and both are needed for all three frames:
  1. **Something that picks out the middle level.** Either a segmenter that returns flat instances
     (one mask per part) instead of a hierarchy, or a cue this pipeline does not have (depth, a second
     view). Alone, this fixes 012.
  2. **A separate answer for the background bridge in 009 and 011**, which a new segmenter does not touch.

### The five routes, measured 2026-09-28

All five were measured on the thirteen frames `All/` held at `b5ca788^` (FastSAM at 1024 px on the
CPU). Routes 3–5 were also measured on the seven old frames (`eb00508^`, with the reference of that
commit).

- **1. Lowering FastSAM's NMS `IoU` (`Segmentation.IoU`, shipped 0.9).** Measured at 0.9 / 0.7 / 0.5 /
  0.3: 009, 011 and 012 count one at every value, and the other ten frames stay on the inventory. The
  both-plates mask overlaps each plate by about half, so only 0.3 removes anything, and then:
  - **009 and 012:** the both-plates mask goes. 009 stays joined by the background bridge; 012 stays
    joined by its touching plate masks.
  - **011:** both plate masks go and the both-plates mask stays, because it outscores them. At 0.5 the
    weaker plate (0.87) is already gone.

  NMS can only choose between levels by score, and the score favours the wrong level as often as the
  right one.
- **2. A larger inference size (`Segmentation.Image_Size`).** At 1024 the 6–10 px seam is ~3 px wide,
  so running closer to the frame's 1920 px looked like a configuration fix. Measured at 1024 / 1280 /
  1536 / 1920, first on the thirteen frames (`b5ca788` recorded it as measured on all thirteen, in the
  same commit that removed five of them), then again on the eight that remain:
  - **It fixes the cause and creates a worse one** (the two-plate frames only, so not re-measurable). The
    both-plates mask weakens as the size grows — 011 0.94 → 0.96 → 0.79 → **0.48**, 012 0.94 → 0.91 →
    0.81 → **0.43** — but the plates' own masks grow into the seam (they take in the dark edge and the
    side wall, which is the seam) and touch: at 1920 in all five two-plate frames, 86–3,132 px of contact,
    011 included (923 px), which does not touch at 1024. 009, 011 and 012 stay merged at every size.
  - **It costs frames that count correctly — re-measured on the eight, the same frames fail.** Off the
    inventory on the eight: 1024 — none; 1280 and 1536 — 003, 004; 1920 — 003, 004, 005. (On the
    thirteen the five two-plate frames were off as well: 009, 011, 012 at every size, 010 and 013 from
    1280 as their plate masks began to touch, 010 recovering at 1920.) At 1920 in `All/Image_003` one
    FastSAM mask covers **0.495** of the frame — the right half of the table — just under the 0.50
    `Background_Area_Fraction` that would reject it as the table plane, so it stays in the union and joins
    the robot and the dark plate; re-measured on the eight, the same 0.495. That threshold sits at the
    edge of where it matters; this is the number beside it.
  - **Time is not the reason.** FastSAM per frame on the eight (median / max, MPS): 167 / 206 ms at 1024,
    237 / 299 at 1280, 310 / 343 at 1536, 443 / 483 at 1920 (the thirteen gave 171 / 237 to 435 / 495) —
    at most a quarter of a second more, against Gemma's seconds per object. The counts are the reason:
    `Image_Size` stays 1024.
- **3. Splitting a merged component by its FastSAM masks with a seam test.** "Both plates = two
  plates" has the same shape in mask space as "one plate = two halves", so this route looked for
  evidence that a boundary is a physical gap. It measured the darkness of the seam between two masks
  (its 10th percentile over the parts' median) on every candidate pair in all twenty frames:
  - touching plates 0.36–0.46
  - one plate's halves 0.73–0.88
  - **the robot's body against its arms, legs and head 0.44–0.61**

  The robot is separately printed pieces pinned together, so its joints are real seams, and the darkest
  (0.44) is darker than the lightest plate seam (0.46). Any threshold that splits the plates splits the
  robot. Do not retry this test without a new kind of evidence: at the seam, two parts touching and one
  assembled part look the same.
- **4. Dropping a parent mask that covers two non-overlapping children, before the union.** A census
  of every parent–child pair in all twenty frames:
  - **Containment is bimodal.** Of 397 pairs, 392 have the child ≥ 0.9 inside its parent and 5 have it
    ≤ 0.85 (none between 0.2 and 0.8), so "contains" is ≥ 0.9 without a choice.
  - **Stated as it is, the rule fires on 55 parents.** Among them: every plate (its two hole rings are
    disjoint children), the whole robot, the terminal strip, the grey comb, the screw with its nut.
  - **Adding coverage cuts it to 15.** Coverage is the fraction of the parent the two children cover
    together; it has an empty gap from 0.60 to 0.96. The 15 parents above the gap look alike, and three
    of them are the two-plate cases:

  | Parent, by eye | Parent | Coverage | Child overlap | Gap between children | Parent score vs children |
  |---|---|---|---|---|---|
  | **Two touching plates** | 009 P6 | 0.991 | 0.000 | 6.7 px | 0.81 vs 0.97 / 0.97 |
  | | 011 P5 | 0.989 | 0.000 | 1.9 px | 0.94 vs 0.91 / 0.87 |
  | | 012 P5 | 0.992 | 0.000 | 1.0 px | 0.94 vs 0.94 / 0.82 |
  | **One plate's machined halves** | 010 P2 | 0.993 | 0.000 | 1.9 px | 0.96 vs 0.69 / 0.61 |
  | | 012 P12 | 0.990 | 0.006 | 0 | 0.82 vs 0.79 / 0.46 |
  | | old 004 P0 | 0.989 | 0.008 | 0 | 0.98 vs 0.61 / 0.59 |
  | **Blue double triangle (one part)** | 001 P1, old 001 P1 | 0.98–0.99 | ≤ 0.005 | 0 | 0.97–0.98 vs 0.59–0.83 |
  | **Robot: arm + hand, leg + foot, head + handle** | 002 P8/P19/P24, 004 P15/P18, 005 P15, 003 P19 | 0.96–0.995 | ≤ 0.050 | 0 | 0.47–0.92 vs 0.50–0.94 |

  - **Scores do not separate them either.** The plates' weaker child scores 0.82–0.97, the halves' and
    the triangle's 0.46–0.74. But the robot's arm (002 P24) has children at 0.92 / 0.91 under a 0.47
    parent, which is the plates' pattern.
  - **Applied anyway, it splits a single plate:** 010 with FastSAM alone becomes three objects (the
    plate's halves). The background cue hides that in the fused count.
  - **It fixes 012 by accident:** it also drops 012's left plate mask as a "parent of two halves",
    which removes FastSAM's plate-to-plate contact.
  - **009 and 011 stay one object** because of the background bridge.
- **5. Splitting a fused component along the FastSAM leaf masks inside it** (leaf: a mask that
  contains no other mask). The leaf set is well-defined: it comes from the same bimodal containment.
  But it is the wrong level. The leaves are hole rings, smudges, limbs and edges, not plates. Every fused
  component in all twenty frames, by eye:

  | Component, by eye | Leaves | Worst overlap between leaves | Share of component the leaves cover |
  |---|---|---|---|
  | **009, two plates** | 4 hole rings | 0.000 | **0.031** |
  | **011, two plates** | 4 rings + 1 smudge | 0.000 | **0.080** |
  | **012, two plates** | 4 rings + 1 smudge | 0.000 | **0.080** |
  | Blue double triangle (001, old 001) | 2 | ≤ 0.005 | 0.98–0.99 |
  | Grey comb (001, 008) | 4 bars | 0.000 | 0.83–0.84 |
  | Robot (002–005) | 11–12 | 0.027–0.079 | 0.48–0.55 |
  | Screw with nut (001, 008) | head, nut | 0.000 | 0.52–0.53 |
  | Terminal strip (007, old 001) | 5–6 | ≤ 0.021 | 0.34–0.57 |
  | Lattice bracket (007) | 11 windows | 0.000 | 0.40 |
  | Red block (006, 007) | side face, holes | 0.000 | 0.25–0.29 |
  | Single plates (003, 004, 010, 013, old 002–005) | 2–4 | 0.000 | 0.030–0.196 |
  | Milled square plate (008), old 006, old 007 | 4–6 | 0.000 | 0.009–0.019 |

  - **The two-plate components are near the bottom.** Only single plates and the milled square plate cover less.
    A coverage cut low enough to include 009 fires on every multi-part object in the set. One high
    enough to mean "most" fires only on single objects.
  - **The leaf-overlap test does not protect the robot.** Leaves are the finest pieces, so they barely
    overlap (≤ 0.079). It is the robot's larger masks that overlap.

- **Pinned by:** nothing any more. The strict xfails on 009, 011 and 012 went with the frames in
  `b5ca788`; restoring the frames from `b5ca788^` together with their inventory entries brings the pin
  back.

## The label mask reveals near-but-distinct objects, not merged touching ones

The exported label mask (`Vision.Utilities.Annotate.Draw_Label_Mask`) fills each
object with a light tint of its box colour and outlines it in that box colour from
that object's **own** component mask. Two parts that
sit close together but do not touch are separate components, so they render as
two tinted shapes with two outlines and black ground between them — the mask reads
as two objects. Two parts that **touch**, however, are already a single component
by the time they reach the renderer: `Vision.Utilities.Fusion.Fuse_Objects`
unions and connected-components the fused cues *before* anything is drawn, so a
merge collapses into one blob upstream (see *Touching parts merge before the closing*). The mask draws one shape with one
contour and cannot reveal that it was two parts — the merge is not a rendering
question.

- **Impact:** a genuine merge (two touching parts read as one object) is invisible
  in the default mask; the per-object contour only distinguishes objects that were
  already separate components.
- **Detection route:** the object **count** against expectation is now the only route
  (a merge lowers the count by one; the status bar's OBJECTS DETECTED and the Trends
  chart both show it). The per-object diagnostic mask fill that used to reveal a merge
  in the mask itself (`CONST_ANNOTATE_MASK_FILL = 'index'`, filling each object in its
  own colour) was removed — its only consumer was that diagnostic, and it carried a
  whole coordinated-stroke palette with it, so the count against expectation stands
  alone.
- **Pinned by:** `test/Vision/Utilities/test_annotate.py::test_mask_separates_near_but_distinct_objects`.

## Open question: FastSAM's reliability on low-contrast shapes

FastSAM dropped low-contrast objects **twice** during development, in independent
synthetic scenes:

- In a synthetic comparison, it returned **no mask for a flat mid-grey box** (BGR ~105)
  on the green reference.
- While building the `analyze.py` synthetic scene, `'everything'` mode **dropped a
  near-black plate** (BGR ~25) it had segmented cleanly in a different layout — the
  stage-1 change mask found all four regions, but FastSAM returned a mask for only
  three.

So this is not a one-off grey quirk but a **low-contrast reliability question in
general**: objects whose colour sits close to the surface, or which are dark and
featureless, are the ones FastSAM everything-mode is least dependable on, and its
output is not fully deterministic across scenes. It is recorded as an **open
question, not a confirmed limitation** — a flat synthetic fill is a plausible
worst case (no internal texture or edges to latch onto), and real metal parts
carry specular highlights and surface texture FastSAM may segment well.

- **Why it matters here:** grey / metallic and dark parts are exactly what this
  application inspects, so the answer cannot be assumed either way.
- **What would answer it:** real low-contrast parts (grey/metallic and dark) on the
  reference background, analysed with `Example/Vision/analyze.py`, checking that each
  comes back as an object. Fusion carries a part FastSAM misses if the background
  difference sees it, so the risk is highest for parts close to the table's colour. If
  real parts are missed, lower the segmenter confidence (`Segmentation.Confidence`) or
  revisit the segmenter choice.

## A very harsh cast shadow can be absorbed into a part's component

The over-segmentation this entry used to describe — a cast shadow's boundary
surviving stage 3 as an extra sliver, so N parts reported as more than N — was a
property of the old coverage-gate + mask-NMS filter. The fusion pipeline replaced
that filter (see git history: the FastSAM-∪-background-subtraction port), and on
**real captures the defect is gone**: the soft cast shadow of the previous test set's
`Image_004` (a single two-hole plate; the set was removed in `eb00508`, recoverable from
`eb00508^`) is stripped by the background-subtraction opening
(`Segmentation.Background.Open_Kernel` in the configuration) and the plate comes back as a
single, tight silhouette (rectangularity ~0.88, no shadow tail). No frame of the current set
over-counts either: the three wrong counts are all merges (*Touching parts merge before the
closing*).

What remains is the **opposite, narrower** failure, and only off real data: when a
shadow is far darker and larger than any real capture — a 40%-darkening ellipse too
big for the opening to erase — its absdiff clears the Otsu floor (`Segmentation.Background.Otsu_Floor`), and the
fusion **absorbs** it into the object's component rather than rejecting it, so the
mask extends past the part into the shadow band. This does not over-count (it stays
one object), but the silhouette is no longer tight, and the enhanced crop fed to the
describer would then contain a strip of table.

- **Fixed case, pinned by:** `test/integration/test_pipeline.py::test_plates_come_back_as_compact_silhouettes_on_a_real_capture`
  (slow; `Image_072` → six objects, the machined plate's and the red block's rectangularity ≥ 0.80,
  measured 0.968 and 0.949 on 2026-10-11; it was `All/Image_003`, no longer in the repository,
  recoverable from `1061966`) and, for every frame's count, `::test_counts_match_the_inventory`. The
  single shadowed plate of the set before (`Image_004`, `eb00508^`) is not pinned as such.
- **Open case, pinned by:** `test/integration/test_pipeline.py::test_synthetic_harsh_shadow_not_absorbed_xfail`
  (slow; `xfail(strict=True)`. It asserts the desired behaviour — no object reaches into
  the shadow band — which currently fails. When the pipeline stops absorbing the harsh
  shadow the test XPASSes and the suite fails: the signal to promote it to a plain pass
  and delete this entry.)
- **Not fixed here:** rejecting a shadow this harsh is a threshold problem, and the
  background-subtraction thresholds are set against real captures, not a synthetic
  scene darker than any real one. Tuning them against this scene would just move the
  failure. Only a real harsh shadow, analysed against a reference shot under the same light,
  would say whether it happens on real data.

## The confidence status metric is partial — only the FastSAM cue is scored

The status strip's `Confidence (run mean)` averages `Detection_Str.Segmenter_Score`,
which only the FastSAM cue supplies. An object found by background subtraction
alone (`Cue == 'background'`) carries `Segmenter_Score is None` and no confidence
of its own. The run mean is therefore over **exactly** the scored objects, never
averaging over the partial set silently, and reads `—` when no object has a score; the
frame's own confidence shows the coverage (e.g. `87% over 5 of 9`).

The limitation stands; its example is stale. When it was written, four of the previous
test set's `Image_001`'s nine objects were background-only; re-measured 2026-09-25, none of
that set's objects were. On the set that followed (`All/`, the eight frames left after `b5ca788`,
re-measured 2026-09-28; no longer in the repository, recoverable from `1061966`; not re-measured on the
current set) none were either: 37 objects, 35 `both` and 2 `fastsam` (the blue double
triangle in `Image_001`, the lattice bracket in `Image_007`), every object scored 0.82–0.98. The
thirteen-frame set had a third `fastsam` object, the dark plate the background cue sees 2 % of, in
`Image_013` (`b5ca788^`). So the test frames score fully and
do not exercise this path; a rig frame with a part FastSAM misses would.

- **Why not route every object through FastSAM:** the fusion exists because neither
  cue is sufficient, and a single run proved it in both directions (the run this entry
  was written from; see design-decisions, *The fusion needs both cues*) — objects the
  background cue missed were carried by FastSAM (`cov=0.00`), and the `Cue ==
  'background'` objects had no FastSAM mask at all. Forcing them through means
  either lowering thresholds until FastSAM sees them (which admits false
  detections) or a second region-prompted pass (which roughly doubles time on the
  slowest stage). Either changes *detection* behaviour to populate a *status*
  field — not worth it.
- **Honest fix later (do not build now):** give the background-subtraction cue its
  own confidence — a normalised change magnitude or a mask-edge sharpness — so every
  object carries a score from whichever cue found it, and the mean covers the whole
  set. Until then the coverage fraction is the honest disclosure that it does not.
- **Pinned by:** `test/UI/test_status_metrics.py::test_status_confidence_is_the_session_mean_over_scored_objects`,
  `::test_status_confidence_denominator_is_the_scored_count_not_the_total`,
  `::test_status_confidence_is_no_value_when_no_object_has_a_score` and
  `::test_frame_confidence_shows_coverage_when_partial_and_dash_when_none`.

## Gemma reads some through-holes as "a central green element"

Seen on the previous test set (removed in `eb00508`, recoverable from `eb00508^`; the describer
has not been re-run on the current set). On its `Image_002` plate, whose two through-holes have dark rims, Gemma describes "two circular
cutouts each containing a central green element" — the green is the table showing through the
hole. The object prompt says "A hole may show the green surface through it; that green is not part
of the part", which fixed the same misreading on `Image_001`'s red block ("a passage allowing a view
of a bright green surface through them") but not on this plate. A sharper wording ("Any green you
see inside a hole … is the surface below showing through it") made it worse — the holes became
"indentations" — so the prompt was not tuned further.

- **Impact:** a false detail in one object's text on dark-rimmed through-holes; the object, its
  holes and its condition are otherwise described correctly (the rust on the same plate is found).
- **Not fixed by tuning:** a prompt adjusted until one frame reads right is the thing the
  comparison must not do. Revisit with a different input (e.g. a crop whose table is masked to a
  neutral colour) rather than more wording.

## The description and the measurement can disagree in the same panel — and the numbers are right

The describer guesses shape from the pixels of one small crop; the measurement computes it from the
mask. Where they disagree, the measurement is right, and the panel shows both side by side (seen on
the previous test set, `eb00508^`; the describer has not been re-run on the current set, and the sizes
below were shown to one decimal then):

- **Hex nuts** (`Image_001` objects 7 and 8): Gemma calls them "a small, roughly octagonal metal
  washer or flange" and "a circular metal washer or ring" (Florence-2 called them rings too). The
  measurement identifies them correctly: the across-flats detection finds the silhouette's 60°
  periodicity and reports `A/F 11.7 mm` / `A/F 11.5 mm`, not `Ø`. The geometry knows it is a hex
  nut; the text says washer.
- **The square plate in `Image_007`**: Gemma calls it "a rectangular, flat plate"; the measurement
  is 48.1 × 46.9 mm, i.e. square. (It calls the other square plate, `Image_006`'s milled square plate,
  47.8 × 47.0 mm, "square".)

Both models miss the nuts, so this is a limitation of describing a small crop, not something prompt
wording will fix.

- **Impact:** the object's text can misname its shape or kind while its size line is correct.
  Trust the numbers.
- **The likely fix, not built:** give the describer what the measurement already knows — e.g. the
  measured shape class and dimensions in the prompt ("this part measures A/F 11.7 mm, hexagonal") —
  rather than letting the model guess shape from pixels.

## A killed run never gets its run-summary CSV row

The run-summary CSV (`log_<Hardware>.csv`) gets its row from `Session_Logger_Cls.Close`, so a run that
never closes (killed with SIGKILL, a power loss, a hard crash) has a complete `.txt` log but no row, and
nothing adds one later. The daily station event file had the same gap and closes it with an export ledger
(docs/design-decisions.md, *The daily station event file is exported from the session log at close*):
every log the ledger does not name is exported at the next start.

- **Impact:** the CSV under-counts runs and their time after an abnormal exit. The `.txt` log of that run
  still records every event, so the time can be reconstructed by hand.
- **Not fixed here:** out of scope for the station event change. The same ledger mechanism could cover
  it: a run-summary row computed from a finished log, written at the next start for a log without one.

## One full test run died with a fatal error, and nothing named it

On 2026-10-08 one run of the whole suite (`pytest -q`) ended without its summary: the last line of its
output was a fatal-error dump's list of loaded native modules, *Extension modules: numpy._core...,
pypylon._genicam, pypylon._pylon, PyQt5.QtCore, PyQt5.QtGui, PyQt5.QtWidgets, PyQt5.QtSvg, PyQt5.QtTest,
..., fontTools.misc.bezierTools, fontTools.varLib.iup (total: 22)*. Only that line was kept, so the
test that was running, the thread and the kind of error (an abort such as PyQt5's qFatal on an exception
escaping a slot, or a segfault) are unknown. pytest's faulthandler prints that dump to stderr only between
its configure and unconfigure, so it happened during the session, not at interpreter exit. The tree was
`99c7e70` with the Trends change of `4f3a78b` uncommitted in it, pure-Python arithmetic in
`Reporting/Trends.py`. The same tree then passed 13 full runs in a row (745 passed, 14 skipped each, no
dump), as had about 20 full runs and a 30-run stress loop of `test/UI` earlier that day.

- **Impact:** one run in 14 or fewer on that tree, cause unknown. Not called a flake: it is unnamed.
- **What would answer it:** the next one. `test/conftest.py` now keeps a crash record,
  `test/crash_records/crash_record.txt` (git-ignored): each test's node id as it starts, and
  faulthandler's dump of every thread on a fatal error, during the session or at exit. A run that did not
  exit cleanly has its record kept by the next run as `crash_record_<time>.txt` (the newest ten), so
  running the suite again never deletes one (`test/integration/test_crash_record.py`). A crash in the
  interpreter's own finalisation, after the record's last line is written, is not kept.

## A hole drilled where the catalogue puts none is not reported

The hole check counts a positioned group's holes only near the positions the catalogue gives (within √2 ×
tolerance + 0.5 mm, mirrored to all four corners), which keeps a round mark of a hole's size elsewhere on the part
out of the count. A hole of the right size anywhere else on the part is not counted, and nothing says it is there.
Accepted by the owner, 2026-10-11, for phase C.

- **Impact:** a part with its catalogue holes right and one more in an unexpected place reads OK.
- **Not fixed here:** reporting candidates outside every position needs round marks told apart from holes by
  something other than position; no part with a misplaced hole is in the test set to measure it on.
- **Pinned by:** `test/Vision/Utilities/test_holes.py::test_a_hole_at_every_corner_is_counted_and_a_round_mark_beside_one_is_not`
  (a mark 5 mm along an edge is not counted).

## The stain check's colour band is this light's

The band (hue 5–30, saturation from 50, value from 40) was measured on the test set's fronts under the rig's
light and the station file's fixed exposure, gain and white balance (the ratios read back and checked on every
connect, since 2026-10-13). A warmer light, another white balance or a surface reflecting the table's green
differently moves the plate's colours; nothing checks that the band still fits.

- **Impact:** under another light a clean part could show band pixels (a false NOK) or a stain could fall
  outside the band (a stain passed: the error that matters).
- **Not fixed here:** a check of the band needs frames under another light (capture checklist); the camera's
  settings are fixed and read back since `7dbab51`.
- **Pinned by:** `test/Vision/Utilities/test_stain.py` (the band as shipped), the pipeline's verdicts on the
  test set (slow).

## The describer guard reads words, so a paraphrase can pass and a right sentence can go

`Reporting.Guard_Description` drops a describer's sentence that holds a number or contradicts a check by matching
patterns (a stain word with or without a negation, a hole count, "each corner"). It caught every contradiction
Gemma wrote on the 24 judged parts measured on 2026-10-11 (five, all "holes in each corner" on parts missing
holes) and dropped no right sentence in the final run; the first run dropped one
("clean of any staining", fixed).

- **Impact:** a contradiction worded unlike those measured can reach the panel; a right sentence using a
  pattern's words can be dropped. Every drop is in the log with the describer's full text. The verdict, State
  and Reasons never come from the describer.
- **Not fixed here:** the describer is not asked to decide, so a model judging its text would be one more
  model to trust; the patterns grow with what is measured.
- **Pinned by:** `test/Reporting/test_core.py::test_the_guard_drops_numbers_and_what_contradicts_a_check`
  (Gemma's own sentences).

## A missing hole is not marked when the part shows nothing to place it by

A hole expected and not found is marked dashed where a hole found puts it: at the pitch from a through-hole, under a
countersink, around a through-hole. The mounting plate's through-holes sit by one long edge, so with no hole of the
side found, which end of the part they belong at cannot be told from the outline, and none is marked. Seen on
capture `20261015-143622_s1`, object 3: a back with no holes, NOK, no hole mark.

- **Impact:** a plate missing all its holes shows no hole marks; its reason ("Both through-holes are missing.") and
  its log lines still say so, and its note says why the marks are absent.
- **Not fixed here:** DINOv2's best turn against the side's reference picked the wrong end on 3 of 21 plates (the test
  set and this capture's front) with every hole in view (margins up to 0.020, overlapping the right ones), and on object 3 its margin is 0.0022; a
  mark at a guessed end may be wrong (docs/design-decisions.md, *A missing hole is placed only by a hole found*).
  A confidence gate on that margin (0.025) was measured on these 21 plates, where it would place 6, all correctly,
  and was not built (owner's ruling, 2026-10-15): one table, one light, and 0.003 between the worst wrong margin and
  the next right one. It can be revisited once more rig captures give the margins on more plates.
- **Pinned by:** `test/Vision/Utilities/test_holes.py::test_a_side_with_no_hole_found_places_none_since_its_end_cannot_be_told`,
  `test/Reporting/test_core.py::test_missing_holes_not_marked_are_named_in_the_note`.
