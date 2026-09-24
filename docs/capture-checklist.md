# Capture checklist

The real captures only the rig can produce. Each one closes a question the software cannot answer
from the frames it already has. This is the **real-capture list** that KNOWN_ISSUES refers to: when an
entry there says "on the capture list", it means an item below.

Read this before trying to verify anything about this project's measurements or its descriptions.
Every number the application reports about size, and every claim about what the describer notices,
is unverified until the relevant item here has been captured and checked.

**For every item:**

- Capture **through the application** (CONFIGURATION → Load, then CONNECT, then SCAN → ANALYZE per
  frame). Each ANALYZE writes a capture set under `logger/captures/<connection>/`: the undistorted
  frame (`<set>_raw.png`), the frame before undistortion (`<set>_distorted.png` + `.json`), and the
  metadata. The metadata records the configuration, the background reference, and the camera, lens
  and lighting, so each frame can be re-measured under any later calibration.
- Do not move the camera, the lens or the light between CONNECT and the last frame of an item. If
  anything moves, note it and start the item again.
- `<set>` numbers restart at 1 on every CONNECT. With one CONNECT per item and no retakes, the number
  is the frame's position in the item's table. On a retake, write down the number that replaced it.

| # | Item | Frames | Closes |
|---|---|---|---|
| 1 | Multi-view calibration set | 20+ | The camera's first multi-view calibration: the lens model, the principal point and the mm/px factor that item 2 then checks |
| 2 | Reference frames: scale and parallax | 9 | *Measured sizes may carry a systematic error*; *A part's measured size depends on where it lies in the frame* |
| 3 | Parts session: defects, low-contrast parts, harsh shadow | ~40 | *The describer is not a defect detector*; *Open question: FastSAM's reliability on low-contrast shapes*; *A very harsh cast shadow can be absorbed* |

**Before item 1: confirm the camera is pinned.** Power-cycle the camera (it then starts from its
factory default, the full 1936 × 1216 sensor), start the application, load the configuration and
CONNECT. The log must read *Camera set to 1920 × 1200 at offset (8, 8) of its 1936 × 1216 sensor …
(read back from the camera)*, and the status bar 1920 × 1200. Anything else: stop and report it —
every item below depends on the window. Capture the calibration set into a **new** directory: its
`capture.json` records the window, and the calibration written from it carries it.

**Order: 1, then 2, then 3.**

1. **Calibrate first.** Adopt the new calibration, then restart the application so it is in force.
2. **Then shoot the reference frames, under the new calibration.** Frames shot before recalibrating
   would measure a factor that is about to be replaced.
3. **Then the parts session.** Its frames are then undistorted and measured under the calibration
   that item 2 has checked.

---

## 1. Multi-view calibration set

**Why.** The calibration in force was solved from a single view; its principal point sits ~800 px off
centre. A multi-view solve needs flat boards (for the lens model and the mm/px factor) and tilted
boards (the lens model only). The tilts are what pin the principal point: the synthetic study behind
`Calibration.Core` shows recovery degrades sharply below 5° of tilt, and plateaus from three views of
at least 10°.

**Needed.** The 12 mm calibration chessboard (11 × 8 squares), a caliper, and something to hold it
tilted.

**Conditions.** Shipped lighting, camera untouched. Capture with the calibration harness, not the app:

```bash
cd Example/Camera
python calibrate.py --capture DIR
```

At each prompt, press `f` for a board **flat** on the table or `t` for a board **tilted**. Every
frame is kept, and `DIR/capture.json` records that the frames are distorted.

| Kind | How many | Conditions |
|---|---|---|
| flat (`f`) | at least 5 | centre and each corner region; the flat views produce the factor and its map over the frame (3 × 3 regions) |
| tilted (`t`) | at least 15 | tilts of 20–45° **in several directions**; at least 3 must be ≥ 10° or the harness warns |
| total | 20+ | the factor's spread from corner noise alone is ~0.06 % at 24 views, under the 0.1 % uniformity threshold |

**Record alongside:**

- [ ] the square size, **calipered across several squares** (printer scaling of 0.5–1 % is the same
      order as the error this removes)
- [ ] the flat boards' surface height above the table (mm) — the plane the factor is exact in
- [ ] the **tilt spread** the report prints (minimum, maximum, and how many views are ≥ 10°)
- [ ] the reprojection RMS, and any views the report names as outliers (retake them)
- [ ] whether the factor is reported as uniform, or which regions differ

**Then.** Solve, which writes a new `Calibration_<Hardware>_calib-<date>.yaml` and leaves the one in
force untouched:

```bash
python calibrate.py --images DIR --board-squares 11x8 --square-mm <calipered> --board-height-mm <h>
```

Check the report (principal point near the image centre, tilt spread above the 10° floor, the factor's
map), then adopt the new calibration by renaming it over `Calibration_<Hardware>.yaml` and restart the
application so it is in force. Item 2 is shot under it. (The old calibration stays in git history; the
reference frames' distorted originals can be re-measured under it for a before/after comparison.)

---

## 2. Reference frames — scale and parallax

**Why.** The mm/px factor has never been checked against a known size on this rig. These frames
check the calibration from item 1 against calipered references: a uniform error means one correction
to the factor; an error that varies with position means the calibration itself needs another look.
Parts of known thickness at the centre and in the corners also give the parallax term directly.

**Needed.** The same chessboard as item 1, one flat plate, one washer, one hex nut, and a caliper.

**Conditions.** **Item 1's calibration adopted and in force** (the application restarted after the
rename). Shipped configuration loaded, one CONNECT, shipped lighting, camera untouched since item 1.
The board lies flat; the parts lie flat and do not touch each other.

| n | What | Where (as seen in the Live view) | Note |
|---|---|---|---|
| 1 | chessboard | centre | edges parallel to the image edges |
| 2 | chessboard | centre | **repeat of 1**: SCAN + ANALYZE again, touch nothing |
| 3 | chessboard | top-left | overhang the corner by ~1–2 squares each way; at least half the board in view |
| 4 | chessboard | top-right | as 3 |
| 5 | chessboard | bottom-left | as 3 |
| 6 | chessboard | bottom-right | as 3 |
| 7 | plate + washer + nut | centre | not touching |
| 8 | plate + washer + nut | top-left | ~10 mm clear of the frame edges |
| 9 | plate + washer + nut | bottom-right | as 8 |

**Record alongside** (the blank form is `Data/Reference/reference_check.yaml`):

- [ ] the connection folder name under `logger/captures/`, and each frame's final `<set>` number
- [ ] the calibration in force when the frames were shot
- [ ] chessboard, with the caliper: across 9 squares horizontally (nominal 108.0 mm), across 6
      vertically (nominal 72.0 mm), and its height above the table (print plus any backing)
- [ ] whether the board and its mounting are the same as at the calibration
- [ ] plate: length, width, thickness
- [ ] washer: outer diameter, thickness
- [ ] nut: across flats, across corners, thickness

**Check.** Frames 1 and 2 must agree to within 0.1 mm; if not, repeatability comes before any
correction. Then compare the error, in mm and %, per position.

---

## 3. Parts session — defects, low-contrast parts, harsh shadow

One session on the parts table, in three parts. The first two use the shipped lighting; the third
changes only the light.

### 3a. Defective parts, with clean controls

**Why.** Whether a defect is reported depends on the framing: `Image_002`'s rust is named at crop
paddings 0.20 and 0.36 and missed at others (KNOWN_ISSUES, *The describer is not a defect detector*).
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

**Conditions.** Add one low-angle side light so the parts cast hard shadows. **First shoot an empty
table under that same light** and set it as the configuration's `Segmentation.Background.Reference`
(in a copy of the configuration). The subtraction is only meaningful against a reference lit the same
way.

| Frames | What |
|---|---|
| 1 | the empty table under the side light (the reference for this subsection) |
| 3–4 | two or three parts with long, dark shadows; include one dark part and one thin part |

**Record alongside:**

- [ ] the light's position and angle
- [ ] which configuration copy (and reference) the frames were analysed under
- [ ] per frame, whether any part's outline reached into its shadow
