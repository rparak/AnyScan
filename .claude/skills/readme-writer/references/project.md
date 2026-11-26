# readme-writer: project reference for AnyScan

AnyScan's README decisions; they override **readme-writer** (`SKILL.md`, beside this folder) where they
differ. The checker's reasoned exceptions are in `check_readme.json`, beside this file.

## Readers

- **Main reader: the person setting up and running a station** - Setup, Run, Configuration, Captures
  on the rig, Platform.
- Others: integrators (Configuration, Swapping a component), maintainers (Tests, Detection logic,
  Repository layout), funders and partners (Authors, Funding).

## Sources of numbers

| What the README shows | Source | Pinned by |
|---|---|---|
| Platform: per-object times, memory peaks, GPU minimum, identical output across runs | DD entries of the measured runs (macOS; Linux 2026-09-29, commit `3cec51a`) | - (by hand) |
| Model download sizes (5.2 GB, 145 MB, 346 MB) and pins, Figure 5 | `install.sh`'s constants and file lists, summed by `Example/UI/readme_diagrams.py` | `test/UI/test_readme_diagrams.py` |
| The test set: 41 frames, `Image_055`-`095` | `Data/Images/Test/` | `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` |
| The EU disclaimer | `UI.Widgets.Funding_Row_Cls.DISCLAIMER` | `test/UI/test_funding_band.py` |

**Open item** (the owner's ruling, 2026-10-23): no test holds the hand-kept numbers to their sources;
a later change adds one.

## Triggers

The one list of what makes a change update the README (feature-manager's `project.md` points here):

| A change to | Updates | Then run |
|---|---|---|
| the pipeline's stages, cues or their modules | Figure 1, Figure 13, *Detection logic*, the top paragraph | `.venv/bin/python Example/UI/architecture_diagram.py` and `readme_diagrams.py` |
| the theme, the type scale, the pixel icons, a logo | Figures 1, 5, 13 and 14 | `.venv/bin/python Example/UI/architecture_diagram.py` and `readme_diagrams.py` |
| the funding logos or `Funding_Row_Cls.DISCLAIMER` | *Funding* (Figure 14 and the disclaimer, word for word), the video's end card | `.venv/bin/python Example/UI/architecture_diagram.py` |
| `install.sh`, `requirements*.txt`, a model, its pin or its size | *Setup* (Figure 5), *Platform* | `.venv/bin/python Example/UI/readme_diagrams.py` |
| an option of `App/run.py` or an `Example/` script | *Workflow*, *Validation*, *Tests* | - |
| a step of the operator's sequence, a tool's output path or message (`install.sh`, `calibrate.py`, `make_reference.py`, the window), or a time it quotes | *Workflow* (and SPEC > *Run sequence*) | - |
| a run on the rig or at a station, or a capture still to do | *Validation* (and SPEC > *Verified on hardware, and not yet*) | - |
| the window, the analysis or the mounting-plate mode as the clips show them | Figures 3 and 7 (a new screen recording, cut as *Figures* says) | - |
| a configuration file name, kind or link | *Configuration* | - |
| a measured run on a platform | *Platform* (the table and its numbers) | - |
| a limitation found, measured or lifted | nothing in the README: SPEC > *Known limitations* holds them (and KNOWN_ISSUES, the DD) | - |
| a root entry, a folder, a committed asset | *Repository layout* (its `<details>`, with the packages under `src/`) | - |
| the test layers or their commands | *Tests* | - |
| an author or a contributor added or renamed (the owner's words only) | *Authors* (a cell: avatar, name, role) | - |

## Statuses

`.claude/project-docs/SPEC.md` > *Verified on hardware, and not yet* is the source of truth; the README uses its
words exactly (the owner's ruling, 2026-10-23): **Verified, measured** (macOS), **Verified on one
machine, 2026-09-29, and in real use on it as station SF4 on 2026-10-29** (Linux, SPEC's whole status, R4), **Never tried, not a target** (Windows); in the text, *verified* /
*not verified* / *unverified* with what was run. A status changed in one place changes in both.

## Figures

- Script: `Example/UI/architecture_diagram.py` writes `images/anyscan-architecture.svg` (Figure 1)
  and `images/anyscan-funding.svg` (Figure 14), from the theme's tokens, `Style.py`'s type scale and
  font fallbacks, and the pixel icon set; regenerated, never edited by hand. `Example/UI/build_logo.py`
  derives the logo copies in `App/assets/` from `images/anyscan-logo.svg`, never edited by hand either.
  After replacing the logo, run `build_logo.py` first, then `architecture_diagram.py` (the diagram embeds
  the logo); `test/UI/test_brand_figures.py` fails when they disagree. This is the one place the
  regeneration rule is written; project-style-rpx and jic-sf-ui-style point here.
- Script: `Example/UI/readme_diagrams.py` (Phase C, 2026-11-26) writes the two light/dark pairs,
  `images/anyscan-models-{light,dark}.png` (Figure 5, *Setup*: each model's role, what it runs on, its pin and its
  download size, read from `install.sh`) and `images/anyscan-pipeline-{light,dark}.png` (Figure 13, *Detection logic*:
  frame, find, describe and measure, judge, record), PNG at 1760 px with the bundled OFL fonts drawn in;
  regenerated, never edited. `test/UI/test_readme_diagrams.py` holds them to its output pixel for pixel.
- **The animations** (Phase C, the owner, 2026-11-26): Figure 3, `images/anyscan-scan-analyze.webp` (live preview,
  SCAN, the frame, the analysis grid, the result), is cut from the AnyScan-Media archive's screen recording of station
  SF4 (footage/Screen, 2026-11-19): only the Camera View card, never the recording's first seconds (an editor and a
  terminal) or a stretch with a hand under the camera. Animated WebP, at most 720 px wide, 12-15 fps, 3-6 s, under
  400 kB, each action shown to its end; a part played faster says so in the caption (the analysis at 2.5x). Not
  generated, so not reproduced byte for byte; the cut is kept outside the repository with the video's build.
  Figure 7, `images/anyscan-history-filter.webp`, is the same recording's History view: the Captures card's state
  filter from All through NOK, OK and Warning back to All, in real time (640 px, 12 fps, 5.3 s, 66 kB).
  `test/UI/test_analysis_animation.py` holds each README animation to these limits, and
  `Example/UI/analysis_animation.py` on the stand-in runtimes (its replay clip is no longer the README's).
- **The video poster** (Figure 4, `images/anyscan-video.jpg`): the video's opening frame with a marker block saying
  where it leads, 1920 px, JPEG, under 500 kB, no metadata, from the video's build outside the repository (the video
  itself is never committed). It links to the owner's YouTube channel until the video is published, then to the
  video's own URL (`.claude/project-docs/FEATURES.md` > *Open*).
- **Photographs and screenshots** (`images/anyscan-station.jpg`, `images/anyscan-live-*.jpg`): taken from the
  AnyScan-Media archive, not generated. They are exported as JPEG quality 85, 1600 px wide, with every metadata block
  dropped (the station photo carried GPS tags), the station photo cropped above the monitor so no window or office
  shows. Each passed the publication rule below when it was added (R4, 2026-11-03). They are single-version: each
  carries its own ground.
- **The gallery** (R5, 2026-11-03), at the end of *Workflow*: three screenshots cropped to their view's panel
  (`images/anyscan-trends-catalogue.jpg` and `-mask-catalogue.jpg`, from the archive's UI/ screenshots of
  2026-10-29 14-45-59 and 14-45-38; History is the animation, Figure 7, since 2026-11-26) and two crops of recorded frames
  (`images/anyscan-scan-nok-ok.jpg` from captures/20261029-143904_s1 set `20261029-144027_8`,
  `images/anyscan-scan-segment-anything.jpg` from captures/20261029-142803_s2 set `20261029-143609_13`, each its
  `_annotated.png`). The same export rule, at most 1600 px wide, cropped from the full resolution and never
  upscaled. Kept out: the Log views (unreadable at README width), Similarity (it reads like a defect map), and
  anything the Live screenshots, the station photo or the animation already show. Each passed the publication
  rule below. The gallery is an HTML table, three to a row, each image linked to itself, its `<br><b>Figure N:</b>`
  caption on the line after it (the checker reads that line).
- Folder: `images/` (the generic default is `Media/`; project-style-rpx `project.md` > *Root*).
- **Nothing private is published.** Before any image, screenshot or recording goes into `images/`, every frame of it
  is checked for people and faces, name badges, business cards, screens showing personal or confidential data, and
  parts that are not JIC Smart Factory's. One that shows any of them is not published. `capture-checklist.md` holds
  the same list for capturing.
- **No published file embeds a commercial font program** (a PDF's embedded GT fonts, for one). Outlined lettering
  and images made under JIC Smart Factory's GT licence are allowed (the logo, the screenshots, the animation, the
  photo), as are the OFL fonts in `App/assets/fonts/` (R6, 2026-11-03; design-decisions, *The poster is dropped
  and every version removed from history*).
- Light and dark (the owner, 2026-11-26): the diagrams drawn for the README since Phase C (Figures 5 and 13) are
  `<picture>` pairs, `<source media="(prefers-color-scheme: dark)">` the dark version and the `<img>` the light one
  with the alt text: light on white, dark on a transparent ground with white words and periwinkle rules. Figures 1
  and 14 carry their own opaque ground (a white card, the purple band), and the photographs, screenshots, animations
  and the poster their own picture, so they are single-version. Looked at in both appearances through the rendered
  README in a headless browser (2026-11-26); not yet on GitHub itself.
- There is no project poster. The owner dropped it, and every version was removed from history: its PDFs embedded
  the GT fonts, whose public distribution embedded in a PDF the EULA does not expressly grant (R6, 2026-11-03;
  design-decisions, *The poster is dropped and every version removed from history*).
- Numbering, in document order: Figure 1 the architecture, Figure 2 the station photo, Figure 3 the SCAN and
  ANALYZE animation and Figure 4 the video poster, all in the top block; Figure 5 the models diagram in *Setup*; at
  the end of *Workflow*, the gallery: Figures 6 to 8 visible (Trends, the History animation, the NOK plate beside the
  OK one), Figures 9 to 12 collapsed (the two Live screenshots, the Mask view, the Segment Anything frame); Figure 13
  the pipeline diagram at the top of *Detection logic*; Figure 14 the funding row. Captions `**Figure N:** …` directly below, in the gallery `<b>Figure N:</b>`.

## Rules

- **The top block**: Figure 1 and its caption, the paragraph that says two cues are fused and links
  *Detection logic*, the station photo (Figure 2, the README's first view of the system), the animation
  (Figure 3) and the video poster (Figure 4) with their captions, then the Contents line (R4, 2026-11-03). No alert: the owner removed it with
  *Limitations* on 2026-11-03 (`ea26ff0`).
- **Detection logic** states the stages briefly: the shared stages named in one sentence, then in one `text` block
  naming each stage's module and function, collapsed (R5), and the catalogue stages, one numbered item each with
  their thresholds, in a `<details>` block; `.claude/project-docs/SPEC.md` > *Pipeline stages* lists them one line each,
  and the two agree.
- **Headings cited from elsewhere stay as they are**: *Setup*, *Platform* and *Licence note* are named in
  operator messages and code comments ("README > Setup"), and SPEC links `#setup`, `#validation`, `#platform`
  and `#detection-logic` (checked by `test_capabilities_doc.py`).
- **Commands** use one spelling, the interpreter `./install.sh` creates: `.venv/bin/python …`, the tests as
  `.venv/bin/python -m pytest`, the Hugging Face CLI as `.venv/bin/hf`, never an activated environment (the owner,
  2026-11-03; `CLAUDE.md` spells them the same).
- **Authors** stands just before *Funding* (readme-writer has no Authors rule; its Acknowledgements, who
  contributed or funded, sit there). It is one HTML table row of four centred cells, in this order, each the
  GitHub avatar (`https://avatars.githubusercontent.com/<username>`, `width="120px;"`, alt "GitHub avatar of <name>, <role> of AnyScan, linking to the GitHub profile
  <username>", 12 words or more), the
  name in bold linked to the profile, and the role below: Roman Parak, Author (`rparak`); Lukas Moravansky,
  Contributor (`LukasMoravansky`); Vojtěch Marek, Contributor (`vojtechmarek13`); Filip Rusnak, Contributor
  (`piifl`). The names and roles are the owner's words, exactly (the owner's ruling, 2026-10-24); none is
  added or changed without the owner. `LICENSE`'s copyright holder (JIC Smart Factory) is separate and
  unchanged.
- **Checker exception, Authors only** (the owner's ruling, 2026-10-24): `check_readme.py` treats each
  avatar as a figure and would report a `caption` ERROR on each (no "Figure N:"). An avatar is an identifying
  portrait, not a figure, so it carries no caption: the four avatars are listed in `check_readme.json` as
  `uncaptioned_figures`, each with its reason (owner, 2026-10-29), which turns those ERRORs into INFO lines. Their
  alt text has 12 words or more since R4 (2026-11-03), so the baseline is **0 ERRORs** and 1 warning
  (`5.0.0.93 looks like an IP address`, the OpenCV pin); any ERROR is a defect. The avatars are external images
  (GitHub's avatar service), the README's only ones.
- **Funding** reads: "Developed within internal research at JIC Smart Factory as a demonstrator through which the EDIH-DIGIMAT project shows small and medium-sized enterprises (SMEs) how AI-based visual inspection can work on their own parts." (the owner's words,
  2026-10-24, the README's only sentence on where AnyScan was developed; Figure 1's description
  carries the same sentence, then "Funded by the European Union.", from its generator), Figure 14, its
  caption, then the EU disclaimer word for word as `Funding_Row_Cls.DISCLAIMER` holds it. The window's
  band does not carry the disclaimer; the README and Figure 14's source do.
- **No semicolons in prose** (readme-writer `style.md` > *Language*, the owner's rule of 2026-10-24;
  `check_readme.py` reports one as ERROR [semicolons]). The EU disclaimer has none, so it needs no
  exception. The semicolons left in the README are syntax, which the check skips: the FastSAM
  `python -c` one-liner, the folders' `text` block and the avatars' `width="120px;"`. Figure 14's alt
  text and the funding SVG's `aria-label` (written by `Example/UI/architecture_diagram.py`) list the
  three logos the same way, with commas.
- **No *Limitations* section** (the owner removed it and the top block's alert on 2026-11-03, `ea26ff0`): the three
  limitations are SPEC > *Known limitations*, worded as they were, and the README states none of them. *Validation*
  keeps its own sentence that nothing there measures accuracy.
- **No internal document is linked or named** (the owner's ruling, 2026-10-24): nothing in
  `.claude/project-docs/`, and never the Claude Code skills. A fact the README needs is stated where it
  is used; a reader who needs more reads the code and its comments.
- The root layout is project-style-rpx `project.md` > *Root*; this file does not repeat it.
- **Workflow** (R6, the owner, 2026-11-03), right after *Setup*: one numbered list from a fresh clone to the first
  analysis (install, calibrate, the empty-surface reference, the mode, start, CONNECT, PREVIEW, SCAN, ANALYZE, the
  results), each step with its command, what it writes, how to tell it worked and its common failure, and a time
  only where one was measured. Each fact is stated once: *Configuration*, *Detection logic* and *Platform* hold the
  details and are linked from the steps.
- **Length**: within the generic 250-line budget (250 visible lines, R6, 2026-11-03), with fourteen `<details>`
  blocks: setup by hand, back to an earlier release, `--frame` and `scan.py`, the gallery's
  second half, the configuration's file names, what each configuration file holds, the rig's validation, the golden
  file, the four shared stages, the catalogue stages, the models and the Linux measurement (with the determinism
  note), the repository's folders, swapping a component, and the third-party components (the owner's rulings of
  2026-10-24 and 2026-11-03, and R5's and R6's). The platforms, `./install.sh`, the models diagram, the Workflow, the top block's figures,
  the gallery's first row, the pipeline diagram, the lamp and station-copy rules and the station's validation stay
  visible.
- **Checker false positive**: `5.0.0.93` (line ~74, the opencv-python-headless version) is reported as
  an IP address; it is a version.

## README tests

| Test | Pins |
|---|---|
| `test/UI/test_brand_figures.py::test_the_readme_shows_the_diagram` | Figure 1 is in the README |
| `test/UI/test_brand_figures.py::test_the_diagram_is_the_generators_output` | Figure 1 is the script's output |
| `test/UI/test_brand_figures.py::test_the_readme_funding_row_is_the_generators_and_self_contained` | Figure 14 is the script's output |
| `test/UI/test_analysis_animation.py` | the replay script, and each README animation's width, length, frame rate and size |
| `test/UI/test_readme_diagrams.py` | Figures 5 and 13: each light and dark image is the generator's output, its ground, the pins, the `<picture>` blocks |
| `test/UI/test_funding_band.py::test_the_disclaimer_is_kept_word_for_word_in_the_readme_and_the_diagram` | the EU disclaimer, word for word |
| `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` | the test set the README counts |

Commands:

```bash
.venv/bin/python -m pytest -q test/UI/test_brand_figures.py test/UI/test_funding_band.py test/UI/test_readme_diagrams.py test/UI/test_analysis_animation.py
.venv/bin/python .claude/skills/readme-writer/scripts/check_readme.py README.md   # 0 errors, 1 warning (the version read as an IP, above)
<throwaway python with cmarkgfm> .claude/skills/readme-writer/scripts/render_readme.py README.md   # 0 leftovers, 2026-11-03
```

## Third-party components

The confirmed inventory the README's third-party table is built from (R1, 2026-10-29; the README's *Licence note*
since R4, 2026-11-03, a collapsed table of component, use, licence and link). Versions: the pin in
`requirements.txt` / `install.sh`, then what `.venv` held on the development Mac. Licences were read from each
package's installed metadata or licence file, from the model card at the pinned revision (Hugging Face API), or from
the file in the repository; each row names its source. **Unconfirmed** means not read at the source in R1. A row
changed here changes the README's table in the same commit.

| Component | Version | What AnyScan uses it for | Arrives | Licence | Source of the licence | Licence | Project |
|---|---|---|---|---|---|---|---|
| PyQt5 | `>=5.15` / 5.15.11 | the desktop window and its widgets | pip | **GPL-3.0** (or Riverbank's commercial licence) | metadata "GPL v3" | [GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html), [Riverbank FAQ](https://www.riverbankcomputing.com/commercial/license-faq) | [PyQt](https://www.riverbankcomputing.com/software/pyqt/) |
| Qt 5 libraries (PyQt5-Qt5) | with PyQt5 / 5.15.19 | the Qt runtime under PyQt5 | pip | LGPL-3.0 | dist-info `LICENSE` | [LGPL-3.0](https://www.gnu.org/licenses/lgpl-3.0.html) | [Qt licensing](https://www.qt.io/licensing/) |
| PyQt5_sip | with PyQt5 / 12.19.0 | PyQt5's binding layer | pip | BSD-2-Clause | metadata | in the package | [sip](https://github.com/Python-SIP/sip) |
| numpy | `>=2.2` / 2.2.6 | image and number arrays | pip | BSD-3-Clause | dist-info `LICENSE.txt` | [licence](https://numpy.org/doc/stable/license.html) | numpy.org |
| opencv-python-headless | `==5.0.0.93` | image processing, undistortion, drawing | pip | Apache-2.0 | metadata, `cv2/LICENSE.txt` | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [opencv-python](https://github.com/opencv/opencv-python) |
| Pillow | `>=10.0` / 12.3.0 | image files | pip | MIT-CMU | metadata | [LICENSE](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | python-pillow.org |
| PyYAML | `>=6.0` / 6.0.3 | reading the configuration files | pip | MIT | metadata | [LICENSE](https://github.com/yaml/pyyaml/blob/main/LICENSE) | pyyaml.org |
| pypylon | `>=3.0` / 26.8 | talking to the Basler camera | pip | BSD-3-Clause text for its own code; metadata classifier "Other/Proprietary License" | dist-info `LICENSE` (Copyright Basler AG) | [LICENSE](https://github.com/basler/pypylon/blob/master/LICENSE) | [pypylon](https://github.com/basler/pypylon) |
| Basler pylon runtime | inside the pypylon 26.8 wheel | the camera driver pypylon calls | pip, bundled | **Basler pylon End-User License Agreement (proprietary)** | `pypylon/pylon.framework/Versions/A/Resources/License.txt` | **unconfirmed**: Basler's download page refused scripted reads (403) | baslerweb.com |
| huggingface_hub | `>=1.30` / 1.33.0 | downloading Gemma and DINOv2 at install | pip | Apache-2.0 | metadata | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [huggingface_hub](https://github.com/huggingface/huggingface_hub) |
| torch | `>=2.3` / 2.14.0 | runs FastSAM and DINOv2 | pip | BSD-3-Clause, with Apache-2.0, BSL-1.0 and MIT parts | metadata `License-Expression` | [LICENSE](https://github.com/pytorch/pytorch/blob/main/LICENSE) | pytorch.org |
| transformers | `>=5.14.0` / 5.17.0 | loads DINOv2 (`src/Vision/Identifier.py`) | pip, declared (R3) | Apache-2.0 | metadata ("License: Apache 2.0 License"), dist-info `licenses/LICENSE` | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [transformers](https://github.com/huggingface/transformers) |
| ultralytics | `>=8.2` / 8.4.123 | runs the FastSAM segmenter | pip | **AGPL-3.0** | metadata, dist-info `LICENSE` | [ultralytics licence](https://www.ultralytics.com/license), [AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html) | [ultralytics](https://github.com/ultralytics/ultralytics) |
| mlx, mlx-metal | `==0.32.2` | runs Gemma on the GPU | pip | MIT | metadata | [LICENSE](https://github.com/ml-explore/mlx/blob/main/LICENSE) | [mlx](https://github.com/ml-explore/mlx) |
| mlx[cuda12 / cuda13 / cpu] (Linux) | no version in `requirements/`; bound by `mlx==0.32.2` (`install.sh`, one pip call) | the Linux backend | pip | MIT, as mlx | **unconfirmed** separately (not installed on the Mac) | as mlx | as mlx |
| mlx-vlm | `==0.7.2` | Gemma's vision-language interface | pip | MIT | metadata | in the package | [mlx-vlm](https://github.com/Blaizzy/mlx-vlm) |
| pytest | `>=7.0` / 9.1.1 | the test suite | pip | MIT | metadata | [LICENSE](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | pytest.org |
| fontTools | `>=4.22.0` / 4.65.0 | `Example/UI/build_fonts.py` (maintenance only) | pip, declared (R3) | MIT | metadata ("License: MIT"), dist-info `licenses/LICENSE` (Copyright (c) 2017 Just van Rossum); `LICENSE.external` covers the test fonts it bundles (OFL-1.1) | [LICENSE](https://github.com/fonttools/fonttools/blob/main/LICENSE) | [fonttools](https://github.com/fonttools/fonttools) |
| FastSAM-x weights | ultralytics assets `v8.4.0`, SHA-256 pinned in `install.sh` | finds the objects in the frame | `install.sh` download | **AGPL-3.0** | the ultralytics/assets repository's licence (GitHub API); the original CASIA-IVA-Lab/FastSAM `LICENSE` is AGPL-3.0 too | [ultralytics licence](https://www.ultralytics.com/license) | [release](https://github.com/ultralytics/assets/releases/tag/v8.4.0), [FastSAM](https://github.com/CASIA-IVA-Lab/FastSAM) |
| Gemma 4 E4B, 4-bit MLX | `mlx-community/gemma-4-e4b-it-4bit@475b908` | writes each object's description | `install.sh` download | Apache-2.0 | the owner's statement (design-decisions, *The owner's statements of 2026-10-29*); the base `google/gemma-4-E4B-it@fee6332` card says `apache-2.0` (Hugging Face API, 2026-10-29); the conversion's card says `license: gemma`, converter boilerplate | [Gemma 4 licence](https://ai.google.dev/gemma/docs/gemma_4_license) | [base model](https://huggingface.co/google/gemma-4-E4B-it), [conversion](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit) |
| DINOv2 base | `facebook/dinov2-base@f9e44c8` | recognises the catalogued part | `install.sh` download | Apache-2.0 | model card at that revision (Hugging Face API) | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [model](https://huggingface.co/facebook/dinov2-base) |
| Public Sans | the google/fonts commit pinned in `build_fonts.py` | the UI typeface | in the repository (`App/assets/fonts/`) | OFL-1.1 | `PublicSans-OFL.txt` beside the files | [OFL](https://openfontlicense.org) | [Public Sans](https://github.com/uswds/public-sans) |
| JetBrains Mono | the same commit | the UI's monospace face | in the repository | OFL-1.1 | `JetBrainsMono-OFL.txt` | [OFL](https://openfontlicense.org) | [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) |
| JIC Smart Factory logo | `App/assets/jic-smart-factory.svg` | the header's brand mark | in the repository | usage rules, not a licence | jic-sf-ui-style `assets/logos/USAGE.md`; the owner's source of the rules **unconfirmed** | - | jic.cz |
| EDIH-DIGIMAT, Ministry of Industry and Trade, EU emblem | traced SVGs in `App/assets/` | the funding band and Figure 14 (a funding obligation) | in the repository | the funders' usage and visibility rules | `USAGE.md`; the EU's [visibility rules](https://commission.europa.eu/funding-tenders/managing-your-project/communicating-and-raising-eu-visibility_en); the other two sources **unconfirmed** | - | edih-digimat.cz, mpo.gov.cz |
| `src/Transformation/` | inherited | nothing imports it | in the repository | MIT | file headers ("Copyright (c) 2023 JIC Smart Factory"); the style's origin credit, DD *File headers carry JIC Smart Factory* | `LICENSE` | [RoLE](https://github.com/rparak/RoLE) |

**Copyleft and non-open terms**, in plain words, not a legal conclusion:

- **PyQt5 (GPL-3.0)**: whoever distributes AnyScan together with PyQt5 distributes the combination under GPL-3.0's
  conditions. AnyScan's MIT code may be combined with it; a closed or commercial redistribution needs Riverbank's
  commercial licence.
- **ultralytics and the FastSAM-x weights (AGPL-3.0)**: using them is free, but whoever distributes a modified
  version, or offers it to users over a network, must provide its source under AGPL-3.0.
- **The Basler pylon runtime (proprietary EULA)**: it comes inside the pypylon wheel under Basler's own terms, which
  govern its use and redistribution.
- **Gemma 4**: Apache-2.0, the owner's statement (design-decisions, *The owner's statements of 2026-10-29*), per the
  base model's card; the conversion's `gemma` tag looks like converter boilerplate.

## Pointers

`CLAUDE.md` > *Skills*; feature-manager `project.md` > *Docs*.
