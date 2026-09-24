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
  metadata. The metadata records the configuration, the background reference, and the camera, lens
  and lighting, so each frame can be re-measured under any later calibration.
- Do not move the camera, the lens or the light between CONNECT and the last frame of an item. If
  anything moves, note it and start the item again.
- `<set>` numbers restart at 1 on every CONNECT. With one CONNECT per item and no retakes, the number
  is the frame's position in the item's table. On a retake, write down the number that replaced it.

| # | Item | Frames | What it is for |
|---|---|---|---|
| 1 | Multi-view calibration set | 20+ | The camera's first multi-view calibration: the lens model, the principal point and the mm/px factor. Not checked against known sizes in this version |
| 2 | Empty-surface reference | 1 | The background reference, re-shot under the new calibration, with its provenance sidecar |
| 3 | Parts session: defects, low-contrast parts, harsh shadow | ~40 | Real frames for the open questions in KNOWN_ISSUES (low-contrast parts, harsh shadow) and data for a future defect rule |

**Before item 1: confirm the camera is pinned.** Power-cycle the camera (it then starts from its
factory default, the full 1936 × 1216 sensor), start the application, load the configuration and
CONNECT. The log must read *Camera set to 1920 × 1200 at offset (8, 8) of its 1936 × 1216 sensor …
(read back from the camera)*, and the status bar 1920 × 1200. Anything else: stop and report it —
every item below depends on the window. Capture the calibration set into a **new** directory: its
`capture.json` records the window, and the calibration written from it carries it.

**Order: 1, then 2, then 3.**

1. **Calibrate first.** Adopt the new calibration, then restart the application so it is in force.
2. **Then the empty-surface reference, under the new calibration.** The reference is an undistorted
   frame, so it belongs to one lens model: the one shot before recalibrating is out of date.
3. **Then the parts session.** Its frames are then undistorted under the new calibration and
   analysed against the new reference.

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
application so it is in force. Item 2 is shot under it. (The old calibration stays in git history; every
capture set keeps its frame before undistortion, so frames can be re-undistorted under either.)

---

## 2. Empty-surface reference (one frame)

**Why.** After the sensor-window change every other artefact is captured at a pinned, recorded window.
The reference in force (`Data/Camera/Image_Background_001.png`) is the right size, but the window it was
shot at is a guess — "probably (0, 0)" — and so are the calibration and lighting it was shot under. And
it is an undistorted frame, so item 1's new lens model puts its geometry out of date. Re-shooting it
removes the last unverified artefact. It is one frame of an empty table.

**Conditions.** Item 1's calibration adopted and in force (application restarted), shipped
configuration, shipped lighting, camera untouched since item 1, **the table empty** — nothing in view,
no shadows from the operator.

**Shoot it with the application, and make it with `make_reference.py`.** The reference must be the
frame the pipeline compares against — the application's capture set — and its provenance must come from
that set's own records, not from a person.

1. CONFIGURATION → Load, CONNECT, confirm the log's *Camera set to 1920 × 1200 at offset (8, 8)* line.
2. SCAN + ANALYZE on the empty table. **Spurious detections are expected here, and are not a
   failure.** The empty table is analysed against the *old* reference, which was shot at another
   window position, under another calibration, and perhaps in other light. The small differences
   between the two frames can show up as objects.
3. Make the reference from that set:

   ```bash
   cd Example/Camera
   python make_reference.py --from ../../logger/captures/<connection>/<set>_raw.png
   ```

   It writes `Data/Camera/Image_Background_002.png` (the next free number — `_001` is never
   overwritten: the characterization baseline was analysed against it) and its sidecar
   `Image_Background_002.json`: the window the camera read back, the lens model that undistorted the
   frame, the configuration, the camera, lens and lighting, and the time. It refuses a set that records
   no window and an existing file. If the analysis found objects, it refuses too, and lists each one:
   its size in pixels, its share of the frame, and where it lies. Read the list before overriding.
   A few small boxes scattered near the edges (for example *3 objects, all under 200 px*) are the noise
   described above: run it again with `--accept-objects`, and the sidecar records what was accepted.
   One large box, or one near the centre (for example *1 object, 40 000 px, centre*), means something
   is on the table: clear it and shoot again.
4. Set `Segmentation.Background.Reference: Data/Camera/Image_Background_002.png` and restart the
   application: the load now checks the reference against its sidecar, and the *no provenance sidecar*
   warning is gone.

---

## 3. Parts session — defects, low-contrast parts, harsh shadow

One session on the parts table, in three parts. The first two use the shipped lighting; the third
changes only the light.

### 3a. Defective parts, with clean controls

**Why.** Whether a defect is reported depends on the framing: `Image_002`'s rust is named at crop
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
configuration** whose `Camera.Lighting` names the side light — the reference's sidecar records the
lighting the configuration names, and the load refuses a reference shot under other lighting. **First
shoot an empty table under that light** with the copy loaded, make the reference from that set with
`make_reference.py` (as in item 2), and set it as the copy's `Segmentation.Background.Reference`. The
subtraction is only meaningful against a reference lit the same way.

| Frames | What |
|---|---|
| 1 | the empty table under the side light (the reference for this subsection) |
| 3–4 | two or three parts with long, dark shadows; include one dark part and one thin part |

**Record alongside:**

- [ ] the light's position and angle
- [ ] which configuration copy (and reference) the frames were analysed under
- [ ] per frame, whether any part's outline reached into its shadow
