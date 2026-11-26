# readme-writer: project reference for AnyScan

AnyScan's README decisions; they override **readme-writer** (`SKILL.md`, beside this folder) where they
differ. The checker's reasoned exceptions are in `check_readme.json`, beside this file.

## Readers

- **A new visitor**: what AnyScan is, how it works and how to run it, from the top block, *What AnyScan does*,
  *Architecture* and *Catalogue mode*.
- **The person setting up and running a station**: *The station*, *Quick start* (its steps in detail collapsed),
  *Requirements and platforms*, *Configuration*, *Records*.
- Others: integrators (*Configuration*, *Development* > swapping a component), maintainers (*Development*, the
  collapsed stages in *Architecture* and *Catalogue mode*), funders and partners (*Authors*, *Funding*).

## Sources of numbers

| What the README shows | Source | Pinned by |
|---|---|---|
| Requirements and platforms: per-object times, memory peaks, GPU minimum, identical output across runs; Quick start's times | DD entries of the measured runs (macOS; Linux 2026-09-29, commit `3cec51a`) | - (by hand) |
| The models table: download sizes (5.2 GB, 145 MB, 346 MB) and pins | `install.sh`'s constants and file lists, written by `Example/UI/readme_diagrams.py` (`Models_Table`) | `test/UI/test_readme_diagrams.py::test_the_readme_models_table_is_the_installers` |
| The catalogue item card's checks (Figure 7) | `Data/Catalogue/mounting_plate/mounting_plate.yaml` through `Load_Catalogue` | `test/UI/test_readme_diagrams.py::test_the_item_card_states_what_the_item_file_holds` |
| The station's hardware and scale | the station file's `Camera` block; SPEC > *Calibration* (the calibration in force) | - (by hand) |
| Figure captions' sizes and capture sets | each capture set's `_objects.json` and `_understanding.txt` in the AnyScan-Media archive | - (by hand) |
| The test set: 41 frames, `Image_055`-`095` | `Data/Images/Test/` | `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` |
| The BibTeX entry | `CITATION.cff` | `test/integration/test_citation.py::test_the_readme_bibtex_is_the_citation_files` |
| The EU disclaimer | `UI.Widgets.Funding_Row_Cls.DISCLAIMER` | `test/UI/test_funding_band.py` |

**Open item** (the owner's ruling, 2026-10-23): no test holds the other hand-kept numbers to their sources;
a later change adds one.

## Triggers

The one list of what makes a change update the README (feature-manager's `project.md` points here):

| A change to | Updates | Then run |
|---|---|---|
| the pipeline's stages, cues or their modules | Figures 5 and 6, *Architecture* (its steps and its collapsed stages), *Catalogue mode*'s collapsed stages, the top paragraph | `.venv/bin/python Example/UI/architecture_diagram.py` and `readme_diagrams.py` |
| the theme, the type scale, the pixel icons, a logo | the headline, Figures 5, 6, 7 and 11 | `.venv/bin/python Example/UI/architecture_diagram.py` and `readme_diagrams.py` |
| the funding logos or `Funding_Row_Cls.DISCLAIMER` | *Funding* (Figure 11 and the disclaimer, word for word), the video's end card | `.venv/bin/python Example/UI/architecture_diagram.py` |
| `install.sh`, `requirements*.txt`, a model, its pin or its size | the models table (*Architecture*), *Quick start*, *Requirements and platforms* | `.venv/bin/python Example/UI/readme_diagrams.py` (prints the table) |
| the shipped catalogue item, its checks or reference images | Figure 7, *Catalogue mode* | `.venv/bin/python Example/UI/readme_diagrams.py` |
| an option of `App/run.py` or an `Example/` script | *Quick start*, *Development*, *Documentation* | - |
| a step of the operator's sequence, a tool's output path or message (`install.sh`, `calibrate.py`, `make_reference.py`, the window), or a time it quotes | *Quick start* (its steps in detail; and SPEC > *Run sequence*) | - |
| a run on the rig or at a station, or a capture still to do | the statuses in *Requirements and platforms* (SPEC > *Verified on hardware, and not yet* holds the runs) | - |
| the window, the analysis or the mounting-plate mode as the figures show them | Figures 2, 4 and 8 (new stills, built as *Figures* says) | - |
| the station's camera, lens, light or calibration in force | *The station* | - |
| a configuration file name, kind or link | *Configuration* | - |
| a record, its path, columns or events | *Records* | - |
| a measured run on a platform | *Requirements and platforms* (the table and its numbers) | - |
| a limitation found, measured or lifted | nothing in the README: SPEC > *Known limitations* holds them (and KNOWN_ISSUES, the DD) | - |
| a root entry, a folder, a committed asset | *Development* (its *Repository layout* `<details>`, with the packages under `src/`) | - |
| the test layers or their commands | *Development* | - |
| an author or a contributor added or renamed (the owner's words only) | *Authors* (a cell: avatar, name, role), `CITATION.cff` and the BibTeX | - |
| `CITATION.cff` | *Citation* (the BibTeX) | - |

## Statuses

`.claude/project-docs/SPEC.md` > *Verified on hardware, and not yet* is the source of truth; the README uses its
words (the owner's ruling, 2026-10-23), the station's machine name left out of the public text (2026-11-26):
**Verified, measured** (macOS), **Verified on one machine, 2026-09-29, and in real use on it as a station at JIC Smart
Factory on 2026-10-29** (Linux), **Never tried, not a target** (Windows); in the text, *verified* / *not verified* /
*unverified* with what was run. A status changed in one place changes in both.

## Figures

The README v11 set (the owner, 2026-11-26): no animation anywhere (`test/UI/test_analysis_animation.py::
test_the_readme_shows_no_animation`), every figure explains something, nothing shown twice. Text drawn into a new
figure is 13 px or more at the README's 880 px (26 px on a 1760 px canvas), checked by rendering; a screenshot or a
recorded annotation keeps the application's own type (below). Numbering, in document order:

| Figure | File | Source |
|---|---|---|
| headline (no number, no caption) | `images/anyscan-headline-{light,dark}.svg` | `Example/UI/architecture_diagram.py` (`Draw_Headline`): `images/anyscan-logo.svg` and `App/assets/jic-smart-factory.svg` inlined unchanged, the top bar's spacing and rule; the dark version only makes their one fill white (`Theme.CONST_ON_INK`), the owner's single-colour light version. `<picture>`, `width="820"` (about 96 px high), the owner's alt text "AnyScan, developed at JIC Smart Factory" (`check_readme.json` lets this mark have 6 words) |
| 1 the video poster | `images/anyscan-video.webp` | the video's thumbnail 5 ("OK or NOK?", a bare hand holding a stained plate) with a square play mark, 2000 px, WebP 90; links to `https://www.youtube.com/@RomanParak/videos` until the video is published (`.claude/project-docs/FEATURES.md` > *Open*) |
| 2 Frame, Find, Judge | `images/anyscan-frame-find-judge.webp` | capture set `20261119-120833_1` (the video's): `_raw`, `_mask`, `_annotated`, each cropped to 250-1800 × 150-1060 and tagged, 2000 px |
| 3 detect-only | `images/anyscan-detect-only.webp` | capture set `20261029-143609_13`, `_annotated.png` whole (1920 px): ten different objects, the richest detect-only frame of the archive. Its chips are the recorded annotation's, about 9 px at 880 |
| 4 Scene Understanding | `images/anyscan-scene-understanding.webp` | the lossless screenshot `UI/Screenshot From 2026-10-29 14-45-27.png`, cropped to the reading (1446-2500 × 182-694): OK with the back up, a Warning outside the area and a NOK in one view; lossless WebP, its body text about 13.4 px at 880 |
| 5 architecture | `images/anyscan-architecture.svg` | `Example/UI/architecture_diagram.py` (below) |
| 6 pipeline | `images/anyscan-pipeline-{light,dark}.png` | `Example/UI/readme_diagrams.py`, 1760 px |
| 7 catalogue item | `images/anyscan-catalogue-item-{light,dark}.webp` | `Example/UI/readme_diagrams.py` from `Data/Catalogue/mounting_plate/`, 1760 px, WebP 92 |
| 8 NOK and OK, and the words | `images/anyscan-verdict-{light,dark}.webp` | plate 3 of `20261119-120833_1` (NOK) beside plate 3 of `20261119-120856_2` (OK, the clean plate in its place 23 s later), both cropped to 760-1300 × 300-1010 of `_annotated.png`, each verdict, size and side from `_objects.json` and `_understanding.txt`, and two sentences of the NOK plate's recorded description, 1760 px, WebP 92 |
| 9, 10 the station | `images/anyscan-station-photo.webp`, `images/anyscan-station.webp` | the photo `Photos/IMG_2658.jpeg` (2026-11-03), cropped where the earlier JPEG was (found by template matching, 0.989), 2000 px, WebP 90, its metadata dropped (it carried GPS tags); the still of the station footage IMG_2704 6.0-7.5 s, tone-mapped HLG to BT.709, 1600 px, side by side |
| 11 funding | `images/anyscan-funding.svg` | `Example/UI/architecture_diagram.py` (`Draw_Funding_Band`) |

- **The recorded figures** (1, 2, 3, 4, 8, 9, 10) are built outside the repository with the video's build
  (`AnyScan-Video/scripts/readme_v11.py`, reading the AnyScan-Media archive read-only), never edited here, so they are
  not reproduced byte for byte. Every raw file stays in the archive; only processed, cropped figures come in.
- **Figure 5** is `Example/UI/architecture_diagram.py`'s SVG, in the station's order (capture, find, measure, what a
  catalogue mode adds, then describe), without the funding band (Figure 11 and the disclaimer carry it), its words in
  Public Sans subsets embedded as WOFF data URIs (OFL 1.1 declares no Reserved Font Name, so a subset keeps the name,
  and each subset keeps the font's name table with its copyright and licence notice). Its smallest words (the group
  tags, the verdict kinds) render at 11.8 px at 880, its card words at 12.8 px; the owner kept the figure's layout
  (2026-11-26). `test/UI/test_brand_figures.py` holds it to the generator (the font bytes masked), its subsets to
  every character, and its order. `Example/UI/build_logo.py` derives the logo copies in `App/assets/` from
  `images/anyscan-logo.svg`, never edited by hand either. After replacing the logo, run `build_logo.py` first, then
  `architecture_diagram.py` (the diagram and the headline embed the logo); `test/UI/test_brand_figures.py` fails when
  they disagree. This is the one place the regeneration rule is written; project-style-rpx and jic-sf-ui-style point
  here.
- **Figures 6 and 7** are `Example/UI/readme_diagrams.py`'s, light and dark through `<picture>`: light on white, dark
  on a transparent ground with white words and periwinkle rules, every word in the bundled OFL fonts drawn in.
  `test/UI/test_readme_diagrams.py` holds the PNGs to its output pixel for pixel and the WebP card within the
  encoder's error per 16 px square. The same script writes the README's models table (`Models_Table`), which the
  README holds word for word.
- Figures 5 and 11 carry their own opaque ground, the photographs, screenshots and the poster their own picture, so
  they are single-version.
- Folder: `images/` (the generic default is `Media/`; project-style-rpx `project.md` > *Root*).
- **Nothing private is published.** Before any image, screenshot or recording goes into `images/`, every frame of it
  is checked for people beyond a bare hand, faces, name badges, business cards, screens showing personal or
  confidential data, paths, hosts, and parts that are not JIC Smart Factory's. One that shows any of them is not
  published. `capture-checklist.md` holds the same list for capturing.
- **No published file embeds a commercial font program** (a PDF's embedded GT fonts, for one). Outlined lettering
  and images made under JIC Smart Factory's GT licence are allowed (the logo, the screenshots, the poster, the
  photos), as are the OFL fonts in `App/assets/fonts/`, Figure 5's subsets included (R6, 2026-11-03; design-decisions,
  *The poster is dropped and every version removed from history*).
- There is no project poster. The owner dropped it, and every version was removed from history (R6, 2026-11-03).
- Captions `**Figure N:** …` directly below; in a side-by-side table `<b>Figure N:</b>` on the line after the image.
  Each recorded figure's caption names its capture set (or screenshot) and its date.

## Rules

- **The top block**, in this order: the headline, the title and the tagline as text, the video poster (Figure 1), one
  paragraph saying what AnyScan is, the Contents line. No alert there.
- **Sections**, in this order (README v11, the owner, 2026-11-26): *What AnyScan does*, *Architecture*, *Catalogue
  mode*, *The station*, *Quick start*, *Requirements and platforms*, *Configuration*, *Records*, *Development*,
  *Documentation*, *Authors*, *Licence*, *Citation*, *Funding*.
- **Headings cited from elsewhere**: operator messages and code comments name *Quick start* and *Requirements and
  platforms* ("README > Quick start"), SPEC links `#quick-start`, `#requirements-and-platforms`, `#architecture`,
  `#catalogue-mode` and `#configuration`, and feature-manager's reference `#licence`. A rename updates every one in the
  same commit (`test/integration/test_skills.py` checks the skills' layers).
- **The prose says "verdict"**; the window and its quoted words keep "State" (`State: NOK.`).
- **Architecture** states the six steps in plain words and the models table; the shared stages with their modules are
  one collapsed `text` block. **Catalogue mode** says what an item defines and how to add one; the catalogue stages,
  one numbered item each with their thresholds, are collapsed. SPEC > *Pipeline stages* lists them one line each, and
  the two agree.
- **Commands** use one spelling, the interpreter `./install.sh` creates: `.venv/bin/python …`, the tests as
  `.venv/bin/python -m pytest`, the Hugging Face CLI as `.venv/bin/hf`, never an activated environment (the owner,
  2026-11-03; `CLAUDE.md` spells them the same).
- **Authors** stands just before *Licence*. It is one HTML table row of four centred cells, in this order, each the
  GitHub avatar (`https://avatars.githubusercontent.com/<username>`, `width="120px;"`, alt "GitHub avatar of <name>,
  <role> of AnyScan, linking to the GitHub profile <username>", 12 words or more), the name in bold linked to the
  profile, and the role below: Roman Parak, Author (`rparak`); Lukas Moravansky, Contributor (`LukasMoravansky`);
  Vojtěch Marek, Contributor (`vojtechmarek13`); Filip Rusnak, Contributor (`piifl`). The names and roles are the
  owner's words, exactly (the owner's ruling, 2026-10-24); none is added or changed without the owner. `LICENSE`'s
  copyright holder (JIC Smart Factory) is separate and unchanged.
- **Checker exceptions** (`check_readme.json`): the four avatars and the headline need no caption (each listed with
  its reason), and the headline's alt text may have 6 words (`min_alt_words`, the owner's words, 2026-11-26). The
  baseline is **0 ERRORs** and 1 warning (`5.0.0.93 looks like an IP address`, the OpenCV pin); any ERROR is a defect.
  The avatars are the README's only external images.
- **Funding** reads: "Developed within internal research at JIC Smart Factory as a demonstrator through which the
  EDIH-DIGIMAT project shows small and medium-sized enterprises (SMEs) how AI-based visual inspection can work on
  their own parts." (the owner's words, 2026-10-24, the README's only sentence on where AnyScan was developed), Figure
  11, its caption, then the EU disclaimer word for word as `Funding_Row_Cls.DISCLAIMER` holds it. Neither the window's
  band nor Figure 5 carries the disclaimer; the README does.
- **No semicolons in prose** (readme-writer `style.md` > *Language*, the owner's rule of 2026-10-24;
  `check_readme.py` reports one as ERROR [semicolons]). The semicolons left in the README are syntax, which the check
  skips: the FastSAM `python -c` one-liner, the folders' `text` block and the avatars' `width="120px;"`.
- **No *Limitations* section** (the owner removed it on 2026-11-03, `ea26ff0`): the three limitations are SPEC >
  *Known limitations*, and the README states none of them. Nothing in the README measures accuracy.
- **No internal document is linked or named** (the owner's ruling, 2026-10-24): nothing in `.claude/project-docs/`,
  and never the Claude Code skills. *Documentation* links what is public: `LICENSE`, `CITATION.cff`, the files'
  comments and the scripts' `--help`. Phase D, which moves the records to `docs/`, adds their links there, the
  limitations included (the owner, 2026-11-26).
- The root layout is project-style-rpx `project.md` > *Root*; this file does not repeat it.
- **Quick start** (README v11): three short visible steps (install, set the station up once, run), then the steps in
  detail collapsed: from a fresh clone to the first analysis, each step with its command, what it writes, how to tell
  it worked and its common failure, and a time only where one was measured.
- **Length**: within the generic 250-line budget (250 visible lines), with these `<details>` blocks: the stages in
  the code, the catalogue stages, each step in detail, setup by hand, back to an earlier release, `--frame` and
  `scan.py`, the Linux measurement, how the configuration is checked, the weights and the golden file, the
  repository layout, swapping a component, the third-party components and the BibTeX. Visible: the headline, every
  figure, the modes, verdicts, models, station, platform, configuration and records tables, the configuration alert,
  the installer note.
- **Checker false positive**: `5.0.0.93` (the opencv-python-headless version, in *Setup by hand*) is reported as an
  IP address; it is a version.

## README tests

| Test | Pins |
|---|---|
| `test/UI/test_brand_figures.py::test_the_readme_shows_the_diagram` | Figure 5 is in the README |
| `test/UI/test_brand_figures.py::test_the_diagram_is_the_generators_output` | Figure 5 is the script's output (the font bytes masked) |
| `test/UI/test_brand_figures.py::test_the_diagram_embeds_public_sans_for_every_character_it_sets` | Figure 5's embedded subsets |
| `test/UI/test_brand_figures.py::test_the_diagram_follows_the_stations_order` | Figure 5's order |
| `test/UI/test_brand_figures.py::test_the_headline_is_the_generators_and_draws_the_two_logo_files_unchanged` | the headline |
| `test/UI/test_brand_figures.py::test_the_readme_opens_with_the_headline_light_and_dark` | the headline's place, `<picture>` and alt text |
| `test/UI/test_brand_figures.py::test_the_readme_funding_row_is_the_generators_and_self_contained` | Figure 11 is the script's output |
| `test/UI/test_readme_diagrams.py` | Figures 6 and 7: each light and dark image is the generator's output, its ground, the `<picture>` blocks; the models table; the item card's checks |
| `test/UI/test_analysis_animation.py::test_the_readme_shows_no_animation` | no animated image |
| `test/UI/test_funding_band.py::test_the_disclaimer_is_kept_word_for_word_in_the_readme` | the EU disclaimer, word for word |
| `test/integration/test_citation.py` | the authors' order, the BibTeX |
| `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` | the test set the README counts |

Commands:

```bash
.venv/bin/python -m pytest -q test/UI/test_brand_figures.py test/UI/test_funding_band.py test/UI/test_readme_diagrams.py test/UI/test_analysis_animation.py test/integration/test_citation.py
.venv/bin/python .claude/skills/readme-writer/scripts/check_readme.py README.md   # 0 errors, 1 warning (the version read as an IP, above)
<throwaway python with cmarkgfm> .claude/skills/readme-writer/scripts/render_readme.py README.md   # 0 leftovers, 2026-11-26
```

## Third-party components

The confirmed inventory the README's third-party table is built from (R1, 2026-10-29; the README's *Licence*
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
| fontTools | `>=4.22.0` / 4.68.0 | `Example/UI/build_fonts.py` and the architecture figure's embedded subsets (maintenance only) | pip, declared (R3) | MIT | metadata ("License: MIT"), dist-info `licenses/LICENSE` (Copyright (c) 2017 Just van Rossum); `LICENSE.external` covers the test fonts it bundles (OFL-1.1) | [LICENSE](https://github.com/fonttools/fonttools/blob/main/LICENSE) | [fonttools](https://github.com/fonttools/fonttools) |
| FastSAM-x weights | ultralytics assets `v8.4.0`, SHA-256 pinned in `install.sh` | finds the objects in the frame | `install.sh` download | **AGPL-3.0** | the ultralytics/assets repository's licence (GitHub API); the original CASIA-IVA-Lab/FastSAM `LICENSE` is AGPL-3.0 too | [ultralytics licence](https://www.ultralytics.com/license) | [release](https://github.com/ultralytics/assets/releases/tag/v8.4.0), [FastSAM](https://github.com/CASIA-IVA-Lab/FastSAM) |
| Gemma 4 E4B, 4-bit MLX | `mlx-community/gemma-4-e4b-it-4bit@475b908` | writes each object's description | `install.sh` download | Apache-2.0 | the owner's statement (design-decisions, *The owner's statements of 2026-10-29*); the base `google/gemma-4-E4B-it@fee6332` card says `apache-2.0` (Hugging Face API, 2026-10-29); the conversion's card says `license: gemma`, converter boilerplate | [Gemma 4 licence](https://ai.google.dev/gemma/docs/gemma_4_license) | [base model](https://huggingface.co/google/gemma-4-E4B-it), [conversion](https://huggingface.co/mlx-community/gemma-4-e4b-it-4bit) |
| DINOv2 base | `facebook/dinov2-base@f9e44c8` | recognises the catalogued part | `install.sh` download | Apache-2.0 | model card at that revision (Hugging Face API) | [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) | [model](https://huggingface.co/facebook/dinov2-base) |
| Public Sans | the google/fonts commit pinned in `build_fonts.py` | the UI typeface | in the repository (`App/assets/fonts/`) | OFL-1.1 | `PublicSans-OFL.txt` beside the files | [OFL](https://openfontlicense.org) | [Public Sans](https://github.com/uswds/public-sans) |
| JetBrains Mono | the same commit | the UI's monospace face | in the repository | OFL-1.1 | `JetBrainsMono-OFL.txt` | [OFL](https://openfontlicense.org) | [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) |
| JIC Smart Factory logo | `App/assets/jic-smart-factory.svg` | the header's brand mark | in the repository | usage rules, not a licence | jic-sf-ui-style `assets/logos/USAGE.md`; the owner's source of the rules **unconfirmed** | - | jic.cz |
| EDIH-DIGIMAT, Ministry of Industry and Trade, EU emblem | traced SVGs in `App/assets/` | the funding band and Figure 18 (a funding obligation) | in the repository | the funders' usage and visibility rules | `USAGE.md`; the EU's [visibility rules](https://commission.europa.eu/funding-tenders/managing-your-project/communicating-and-raising-eu-visibility_en); the other two sources **unconfirmed** | - | edih-digimat.cz, mpo.gov.cz |
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
