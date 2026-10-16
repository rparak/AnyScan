# Capture checklist

The real captures only the rig can produce: a new calibration, the background reference that goes
with it, and a parts session whose frames the software cannot invent.

**None of them verifies the measurements.** This version does not check sizes against calipered
references, so the limitations in the README (*Limitations*) stand unverified whatever is captured
here: the sizes are repeatable, not absolute, and the describer is not a defect detector.

**For every item:**

- Capture **through the application** (CONFIGURATION → Load, then CONNECT, then SCAN → ANALYZE per
  frame). Each ANALYZE writes a capture set under `logger/captures/<connection>/`: the undistorted
  frame (`<set>_raw.png`), the frame before undistortion (`<set>_distorted.png` + `.json`), and the
  metadata. **`_raw.png` is the frame to keep**: "raw" means unannotated, not unprocessed. It is the
  frame the application analysed, and the only one that is comparable with the background reference;
  a test frame (`Data/Images/Test/`) or a reference is made from it, never from `_distorted.png`, which
  is kept only so a later calibration can undistort the frame again. The metadata records the configuration, the background reference, and the camera, lens
  and lighting, so each frame can be re-measured under any later calibration.
- Do not move the camera, the lens or the light between CONNECT and the last frame of an item. If
  anything moves, note it and start the item again.
- `<set>` numbers restart at 1 on every CONNECT. With one CONNECT per item and no retakes, the number
  is the frame's position in the item's table. On a retake, write down the number that replaced it.

| # | Item | Frames | What it is for | Status |
|---|---|---|---|---|
| 1 | Multi-view calibration set | 40+ | The lens model, the principal point and the mm/px factor. Not checked against known sizes in this version | **Done 2026-09-28** — in force |
| 2 | Empty-surface reference | 1 | The background reference, shot under the calibration in force, with its provenance sidecar | **Done 2026-09-28** — in force |
| 3 | Parts session: defects, low-contrast parts, harsh shadow, plates far from the centre | ~50 | Real frames for the open questions in KNOWN_ISSUES (low-contrast parts, harsh shadow), data for a future defect rule, and mounting plates far from the centre to widen the size checks' verified zone | To do |
| 4 | Cable pull: a lost connection is detected | 0 | Not a capture: the one check of lost-connection detection on the real camera, which no test can make (it is unverified on the hardware until this is done) | To do |

Items 1 and 2 are repeated, in that order, whenever the camera, the lens, its focus or the mount
changes. Their procedures stay below for that.

**Before item 1: confirm the camera is pinned.** **Confirmed on the real camera, 2026-10-13**, with `7d9ffe7`:
the log read *Camera set to 1920 × 1200 at offset (8, 8) of its 1936 × 1216 sensor, exposure 10000 µs, gain
10.00, BayerRG8, ExposureAuto Off, GainAuto Off, BalanceWhiteAuto Off, BalanceRatio Red 0.949951, Green 0.899902,
Blue 1.19995 (± 0.0078125, the camera reports no step), Gamma 1, LightSourcePreset not available (read back from
the camera; LightSourcePreset not pinned).* The three automatic modes are Off; Gamma 1 is pinned in the station
file (`Camera.Custom_Cfg.Gamma`); this model has no colour-preset node, so `Light_Source_Preset` is not pinned
("not available" is not an error while it is unpinned); and it reports no step for BalanceRatio, so the 1/128
fallback is the tolerance, each ratio reading back within about 0.00005 of the station file's (0.95, 0.90, 1.20).
The window itself was first confirmed on 2026-09-24. Repeat the check after any change to the camera's settings
or firmware: power-cycle the camera (it then starts from its factory default, the full 1936 × 1216 sensor), start
the application, load the configuration and CONNECT. The log must read the line above, and the status bar
1920 × 1200. A camera that keeps an automatic mode on, a ratio outside the tolerance or a gamma other than 1 is
refused at CONNECT, naming it. Anything else: stop and report it —
every item below depends on the window. Each calibration set goes in its own directory
(`calibrate.py --capture` makes a new one each run): its `capture.json` records the window, and the
calibration written from it carries it.

**Order: 1, then 2, then 3.**

1. **Calibrate first.** Adopt the new calibration, then restart the application so it is in force.
2. **Then the empty-surface reference, under the new calibration.** The reference is an undistorted
   frame, so it belongs to one lens model: the one shot before recalibrating is out of date.
3. **Then the parts session.** Its frames are then undistorted under the new calibration and
   analysed against the new reference.
4. **The cable pull last**, any time after item 3 — it disturbs nothing the other items depend on.
5. **The moving hand under SCAN** any time after CONNECT — it records nothing the other items depend on.

---

## 1. Multi-view calibration set

**Done 2026-09-28.** The set is `Data/Images/Calibration/20260928-103531`: 63 views (22 flat, 41
tilted), reprojection RMS 0.45 px, flat-board height 4.22 mm, principal point about 25 px from the
frame centre, factor 0.102 mm/px. Its record is `Calibration.Solved` in the calibration file
(commit `eb00508`).

**Why.** The calibration it replaced was solved from a single view, and its principal point sat
~800 px off centre: one near-frontal view cannot separate the principal point from the board's
position. A multi-view solve needs flat boards (for the lens model and the mm/px factor) and tilted
boards (the lens model only). The tilts are what pin the principal point: the synthetic study behind
`Calibration.Core` shows recovery degrades sharply below 5° of tilt, and plateaus from three views of
at least 10°.

**Needed.** The 12 mm calibration chessboard (11 × 8 squares), printed from
[`Checkerboard_11x8_12mm_A4.pdf`](Checkerboard_11x8_12mm_A4.pdf) and mounted on glass or ≥ 3 mm
aluminium (page 2 of the PDF says how, and why flatness matters), a caliper, and something to hold
it tilted. Before anything else, measure **both** scale rulers on page 1: each must be 120.0 mm. If
either is not, do not use the board; fix the printer scaling and reprint.

**Conditions.** Shipped lighting, camera untouched. Capture with the calibration harness, not the app:

```bash
cd Example/Camera
python calibrate.py --capture --board-squares 11x8
```

It captures into a new `Data/Images/Calibration/<timestamp>/` (git-ignored; pass a directory to
choose another). At each prompt, press `f` for a board **flat** on the table or `t` for a board
**tilted**. Every frame is kept, and the directory's `capture.json` records that the frames are
distorted, the sensor window they were taken at, and the board. Each frame says whether *the whole
board* was found or only *part of the board*; a partial view is usable but carries fewer corners, so
retake it unless the board overhangs the frame on purpose.

| Kind | How many | Conditions |
|---|---|---|
| flat (`f`) | at least 12 | centre and each corner region. Only the flat views feed the mm/px factor and its 3 × 3 map (tilted corner spacing does not describe the table plane), so the factor's spread rests on these alone: 12 is the floor for the one number every measurement depends on |
| tilted (`t`) | at least 28 | tilts of 20–45° **in several directions**; at least 3 must be ≥ 10° or the harness warns. They feed the lens model only; the principal point plateaus from 3 tilted views, so 28 is far past that — they are here for the total |
| total | 40+ | not excessive: the factor's spread from corner noise alone, median / 90th percentile, is 0.057 / **0.103 %** at 24 views, over the 0.1 % uniformity threshold in one set of ten, and 0.039 / 0.065 % at 40 |

**Record alongside:**

- [ ] the square size, **calipered across 10 squares, horizontally and vertically** (printer scaling of
      0.5–1 % is the same order as the error this removes); if the two differ by more than 0.1 mm, reprint —
      one `--square-mm` cannot carry two scales
- [ ] the flat boards' surface height above the table (mm) — the plane the factor is exact in
- [ ] the **tilt spread** the report prints (minimum, maximum, and how many views are ≥ 10°)
- [ ] the reprojection RMS, and any views the report names as outliers (retake them)
- [ ] whether the factor is reported as uniform, or which regions differ

**Then.** Solve, which writes a new `Configuration/Calibration/Calibration_<Hardware>_<YYYYMMDD-HHMMSS>.yaml`
and leaves the one in force and the station file untouched:

```bash
python calibrate.py --images ../../Data/Images/Calibration/<timestamp> --board-squares 11x8 --square-mm <calipered> --board-height-mm <h>
```

Check the report (principal point near the image centre, tilt spread above the 10° floor, the factor's
map), then adopt the new calibration: change the station file's `Calibration` line, which the tool names by
number, to the new file name, and restart the application so it is in force. Commit the new calibration file
with the station file. Item 2 is shot under it. (The old calibration stays in `Configuration/Calibration/`,
one line away; every capture set keeps its frame before undistortion, so frames can be re-undistorted under
either.)

---

## 2. Empty-surface reference (the mean of 8 frames)

**Done 2026-09-28; re-shot 2026-10-12.** `Data/Images/Background/Image_Background_001.png` was first made by
the old `make_reference.py --from` from the capture set `20260928-111434_s1`, with four edge slivers accepted
with `--accept-objects`. *Corrected 2026-10-13:* the file in force is not that one. It was re-shot on
2026-10-12 (commit `b131244`) from the capture set `20261012-170521_s1`, with no objects accepted, and written
over the same name. Its sidecar records the window (1920 × 1200 at (8, 8)), the fingerprint of the calibration
in force and the lighting. It named that calibration by the file name it had then
(`Calibration_a2A1920_51gcPRO_Computar_M1228_MPW3.yaml`); the file has since been renamed
(`…_20260928-110755.yaml`, the same K and coefficients, so the fingerprint matches), and the sidecar's `file`
was corrected to the current name. The next reference is `_002`.

**Why.** The reference is an undistorted frame, so it belongs to one lens model and one sensor window:
a new calibration puts its geometry out of date. Shot through the application's camera path, with its
provenance from what the camera reported, it is a verified artefact rather than a guess. It is the mean of
8 frames: sizes then depend half as much on which frame was grabbed (docs/design-decisions.md, *A new
reference is the mean of 8 frames…*).

**Conditions.** The calibration in force (adopted, application restarted), shipped configuration, shipped
lighting, camera untouched since item 1, **the table empty** — nothing in view, no shadows from the operator.

**Shoot it with `make_reference.py`.**

1. In AnyScan, press **DISCONNECT** (or close it): the tool needs the camera, and says so if the
   application still holds it.
2. Clear the table and step out of the light.
3. From the repository root:

   ```bash
   .venv/bin/python Example/Camera/make_reference.py
   ```

   (`--config <mode file>` for another mode; the default is the shipped one.) It loads FastSAM, grabs
   8 frames through the application's camera path (about 3 s), and checks the mean and each frame with the
   application's own background difference, FastSAM and fusion against the reference in force. If anything is
   found it refuses, lists each object (its size in pixels, its share of the frame, where it lies) and writes
   nothing: clear the table and run it again. When the reference in force no longer matches the camera (after
   a new calibration or window), it says so and checks with FastSAM alone.
4. It writes `Data/Images/Background/Image_Background_NNN.png` (the next free number — an existing reference
   is never overwritten: capture sets and the characterization baseline cite it by name) and its sidecar
   `Image_Background_NNN.json`, and prints the line of the station file to change. Change that line
   (`Background.Reference` in `Configuration/Station/`, the station the mode names) and restart the
   application: the load checks the reference against its sidecar.

---

## 3. Parts session — defects, low-contrast parts, harsh shadow, plates far from the centre

One session on the parts table, in four parts. The first, second and fourth use the shipped lighting;
the third changes only the light.

### 3a. Defective parts, with clean controls

**Why.** Whether a defect is reported depends on the framing: the previous test set's `Image_002` (`eb00508^`) rust is named at crop
paddings 0.20 and 0.36 and missed at others (README > Limitations, *The describer is not a defect detector*).
That is one stain on one frame. These frames measure detection across defects and framings, and they
are the data an anomaly-detection rule — the route for defects, feeding the Classification verdict —
would be built and tested on.

**Needed.** Parts with **different** surface defects — rust, a stain, a scratch, dirt, corrosion,
aiming for at least two parts per kind — plus a clean part of each kind as a control.

| Frames per part | Conditions |
|---|---|
| 6 | centre, top-left and bottom-right, each at 0° and 90° rotation |

That is about 30 frames for five defective parts, plus the controls.

**Record alongside each frame:**

- [ ] a part id (the same id across that part's frames)
- [ ] the defect type (or "clean"), and its location on the part ("upper-left quarter",
      "along the long edge") and approximate size in mm
- [ ] a close-up phone photo of the defect, filed by part id (ground truth a reviewer can check)

### 3b. Low-contrast parts

**Why.** FastSAM dropped low-contrast shapes twice in synthetic scenes (a mid-grey box, a near-black
plate), and grey, metallic and dark parts are exactly what this application inspects (KNOWN_ISSUES,
*Open question: FastSAM's reliability on low-contrast shapes*).

**Needed.** Grey / metallic parts and dark, featureless parts — the closer to the table's colour, the
better.

| Frames | Conditions |
|---|---|
| 1 per part | the part alone, at the centre |
| 2 | all of them together, not touching |

**Record alongside:** each part's id and colour or finish. After ANALYZE, whether each part came back
as an object (the Live view's count, and the capture set). A part that was missed closes the question
the other way.

### 3c. Harsh cast shadow

**Why.** On real captures the soft shadow is rejected, but a shadow far harsher than any real capture
is absorbed into the part's component (KNOWN_ISSUES, *A very harsh cast shadow can be absorbed*). That
case is pinned only on a synthetic scene, by the strict xfail
`test/integration/test_pipeline.py::test_synthetic_harsh_shadow_not_absorbed_xfail`. A real harsh
shadow replaces the synthetic evidence either way.

**Conditions.** Add one low-angle side light so the parts cast hard shadows. Work in a **copy of the
configuration** — a mode file with the station file and calibration beside it — whose station names the
side light in `Camera.Lighting` — the reference's sidecar records the
lighting the configuration names, and the load refuses a reference shot under other lighting. **First
shoot the empty table under that light** with `make_reference.py --config <the copy's mode file>` (as in
item 2; the reference in force names other lighting, so it checks with FastSAM alone and says so), and set
the new reference as the copy's station `Background.Reference`. The
subtraction is only meaningful against a reference lit the same way.

| Frames | What |
|---|---|
| 1 | the empty table under the side light (the reference for this subsection) |
| 3–4 | two or three parts with long, dark shadows; include one dark part and one thin part |

**Record alongside:**

- [ ] the light's position and angle
- [ ] which configuration copy (and reference) the frames were analysed under
- [ ] per frame, whether any part's outline reached into its shadow

### 3d. Mounting plates far from the centre

The size checks are verified only out to 46.4 mm from the frame centre: the farthest judged mounting
plate of the test set (`Vision.Utilities.Classify.CONST_VERIFIED_RADIUS_MM`). A plate farther out is
still judged, and the session log notes that its size check is not verified there. Mounting plates placed far
from the centre, for example in the corners of the view, would win the zone back: if they read within
tolerance there, the zone can be widened to them.

Since 2026-10-16 a catalogue mode judges only inside the station's inspection area, the frame inset by 10 mm at
the top and bottom and 13 mm at the left and right (`Inspection_Area` in the station file); the area is drawn in the
Camera View. The insets were measured on plates mostly by the right edge and the top: inside the area the closest
measured plates came within 0.1 mm of its top edge, 0.7 mm of its right and 2.4 mm of its left, but only one within
9 mm of its bottom, and none lay in its corners, where a whole plate's centre can lie up to about 67 mm out (the
farthest measured inside, 58.4 mm). The rows below fill those in, and add what the outside-area Warning needs: plates
and foreign objects cut by the frame's border. Run them through the pipeline as the 2026-10-16 measurement did (each
plate's outline, holes and stains against half of each tolerance), and check each plate against the line on screen
before shooting: wholly inside, just inside an edge, or over it.

Shipped lighting, the mounting-plate mode, each plate lying flat:

| Frames | What |
|---|---|
| 4 | one plate in each corner of the inspection area, just inside its line, machined front up, clean |
| 4 | the same, unmachined back up |
| 6 | a clean front just inside the area's left edge and its bottom edge (three turns each) |
| 6 | the same with the fingerprinted front, and 3 with a back |
| 2 | one plate midway along the area's top edge and one along its right edge, clean (controls) |
| 4 | a plate cut by the frame's border: on the left, the bottom, the right and in a corner, stained front up |
| 3 | a foreign object (the red block, a square plate, the terminal block) cut by the frame's border |
| 2 | a foreign object wholly inside the area, and one over its line but whole |

**Record alongside:**

- [ ] each plate's lines in the log: its verdict, its side ("by its holes" when they decided it), its outline's
      measured sides and, beyond 46.4 mm, its size note, which gives its distance from the frame centre
- [ ] for every plate and object, whether it lies wholly inside the line on screen, over it, or cut by the frame's
      border, and its verdict line in the log (an object outside the area is a Warning; an identified part there
      names what its checks saw)

---

## 4. Cable pull: a lost connection is detected

**Why.** A lost connection closes the camera session. A Scan on a removed device must report the loss,
because its failed capture ends that scan's cycle in the daily station event file. A frame must not
appear to come from a camera that still reads connected. The loss itself ends no cycle (since
2026-10-07). It is detected two ways: the application asks pylon once a second whether
the device was removed (`InstantCamera.IsCameraDeviceRemoved`), and a Scan whose grab fails on a
removed device reports the loss. Both are tested only with a stand-in device. **Whether pylon reports
the removal on this GigE camera, and how fast, is unverified** (docs/design-decisions.md, *A lost
connection is detected by the camera, not only by DISCONNECT*).

**Conditions.** Configuration loaded, CONNECT done, no Scan or Analyze running. Note the clock time to
the second at each step.

1. Pull the camera's GigE cable. Do not touch the application.
2. Within a few seconds the Camera cell must read *Disconnected*, the header pill *Camera offline*, and
   the reading panel *The camera is no longer reachable…*. The log must have an ERROR *The camera
   connection was lost (…)* followed by *Connection N ended after …*.
3. Plug the cable back in and CONNECT: it must connect normally.
4. Repeat 1–3, but press SCAN straight after pulling the cable, before the cell changes. The Scan must
   report a lost connection (the log's *The camera connection was lost* ERROR), not a *did not return
   a frame* capture error with the camera still Connected.
5. Close the application, then open the day's station event file
   (`General.Station_Events.Directory/<date>.csv`): every CYCLE_START must have its CYCLE_DONE. The
   first loss, with no Scan, writes no cycle. Step 4's Scan writes one CYCLE_START at the Scan and its
   CYCLE_DONE at the failed capture.

**Record alongside:**

- [ ] the seconds from pulling the cable to the Camera cell reading *Disconnected* (step 2)
- [ ] whether step 4's Scan reported a lost connection or a capture error
- [ ] any loss not detected at all — stop and report it: then the camera reads connected after the
      cable is gone, and a Scan reports a capture error instead of the loss

6. Repeat 1–3 with the live preview running (PREVIEW pressed, the view showing *LIVE PREVIEW*). The preview must
   stop, the Camera cell read *Disconnected* and the reading panel *The live preview stopped. The camera is no
   longer reachable…*, with the same ERROR in the log; CONNECT must then work, and PREVIEW must start again.

- [ ] the seconds from pulling the cable to the preview stopping (step 6), and whether it reported a lost
      connection or *The live preview stopped: …* with the camera still Connected

## 5. Live preview and SCAN: a moving hand is refused

**Why.** SCAN takes its frame only once two consecutive frames show no movement, and refuses after about a
second (docs/design-decisions.md, *A scan waits for a still scene…*). The thresholds come from the still table's
noise on this camera; the refusal itself is tested only on scripted and synthetic frames.

**Conditions.** Configuration loaded, CONNECT done, a part on the table.

1. Press PREVIEW, then wave a hand over the table and press SCAN while it moves. The reading must say *Something is
   moving in the view…* with a *Moving* badge, the log a WARNING with the same sentence, and the preview must come
   back. The System cell must not count an error.
2. Hold the hand still in view and press SCAN: the scan must take the frame (a hand held still is still).
3. Take the hand away, wait a second, press SCAN: the frame must show the table without the hand.
4. Repeat 1 with a part slid slowly across the table instead of a hand.

**Record alongside:**

- [ ] whether each step behaved as written, and the scan's time in step 3 (the log's scan lines)
- [ ] any still table that was refused, or any movement that was scanned — stop and report it
