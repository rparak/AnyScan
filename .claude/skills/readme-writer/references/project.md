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
| Limitations: size errors, scale, the side-wall term, tolerances | the DD and KNOWN_ISSUES entries behind each limitation (not linked) | - (by hand) |
| Model and download sizes (5.2 GB, 145 MB, 346 MB) | `install.sh` constants and the Setup instructions | - (by hand) |
| The test set: 41 frames, `Image_055`-`095` | `Data/Images/Test/` | `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` |
| The EU disclaimer | `UI.Widgets.Funding_Row_Cls.DISCLAIMER` | `test/UI/test_funding_band.py` |

**Open item** (the owner's ruling, 2026-10-23): no test holds the hand-kept numbers to their sources;
a later change adds one.

## Triggers

The one list of what makes a change update the README (feature-manager's `project.md` points here):

| A change to | Updates | Then run |
|---|---|---|
| the pipeline's stages, cues or their modules | Figure 1, *Detection logic*, the top paragraph | `.venv/bin/python Example/UI/architecture_diagram.py` |
| the theme, the type scale, the pixel icons, a logo | Figure 1 and Figure 6 | `.venv/bin/python Example/UI/architecture_diagram.py` |
| the funding logos or `Funding_Row_Cls.DISCLAIMER` | *Funding* (Figure 6 and the disclaimer, word for word) | `.venv/bin/python Example/UI/architecture_diagram.py` |
| `install.sh`, `requirements*.txt`, a model or its size | *Setup*, *Platform* | - |
| an option of `App/run.py` or an `Example/` script | *Run*, *Validation*, *Tests* | - |
| a run on the rig or at a station, or a capture still to do | *Validation* (and SPEC > *Verified on hardware, and not yet*) | - |
| the window, the analysis or the mounting-plate mode as the clip shows them | Figure 3 | `.venv/bin/python Example/UI/analysis_animation.py --frame <set>_raw.png` |
| a configuration file name, kind or link | *Configuration* | - |
| a measured run on a platform | *Platform* (the table and its numbers) | - |
| a limitation found, measured or lifted | *Limitations* (and KNOWN_ISSUES, the DD) | - |
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
  and `images/anyscan-funding.svg` (Figure 6), from the theme's tokens, `Style.py`'s type scale and
  font fallbacks, and the pixel icon set; regenerated, never edited by hand. `Example/UI/build_logo.py`
  derives the logo copies in `App/assets/` from `images/anyscan-logo.svg`, never edited by hand either.
  After replacing the logo, run `build_logo.py` first, then `architecture_diagram.py` (the diagram embeds
  the logo); `test/UI/test_brand_figures.py` fails when they disagree. This is the one place the
  regeneration rule is written; project-style-rpx and jic-sf-ui-style point here.
- **The animation**, `images/anyscan-analysis.webp`: written by `Example/UI/analysis_animation.py --frame <set>_raw.png`
  (the README's replays set `20261029-144501_15` of the AnyScan-Media archive, captures/20261029-143904_s1),
  regenerated, never edited. **It is the one figure not reproduced byte for byte** (the owner's ruling, 2026-11-03): it
  runs the real models, so the panel's measured inference time differs between runs, and on another backend so may
  the descriptions' wording. Its grabs follow events and its clock is frozen, so nothing else of the run shows.
  `test/UI/test_analysis_animation.py` holds the script on the stand-in runtimes and the committed clip to the
  README's limits: 960 px wide, at most 10 s, at most 5 MB. Its caption gives the analysis time the script printed.
- **Photographs and screenshots** (`images/anyscan-station.jpg`, `images/anyscan-live-*.jpg`): taken from the
  AnyScan-Media archive, not generated. They are exported as JPEG quality 85, 1600 px wide, with every metadata block
  dropped (the station photo carried GPS tags), the station photo cropped above the monitor so no window or office
  shows. Each passed the publication rule below when it was added (R4, 2026-11-03). They are single-version: each
  carries its own ground.
- Folder: `images/` (the generic default is `Media/`; project-style-rpx `project.md` > *Root*).
- **Nothing private is published.** Before any image, screenshot or recording goes into `images/`, every frame of it
  is checked for people and faces, name badges, business cards, screens showing personal or confidential data, and
  parts that are not JIC Smart Factory's. One that shows any of them is not published. `capture-checklist.md` holds
  the same list for capturing.
- Light and dark: each figure carries its own opaque ground (a white card, the purple band), so no
  `<picture>` variants. **Unchecked** on GitHub's dark theme until the owner looks at both figures
  there after the push (2026-10-23).
- The project poster, `images/anyscan-poster.pdf`, is the owner's export (its source is outside the repository, its
  metadata stripped), not generated; every claim on it holds against SPEC (checked 2026-11-03, R5).
- Numbering, in document order: Figure 1 the architecture, Figure 2 the station photo and Figure 3 the animation,
  all three in the top block; Figures 4 and 5 the Live screenshots, collapsed under *Run*; Figure 6 the funding row.
  Captions `**Figure N:** …` directly below.

## Rules

- **The top block**: Figure 1 and its caption, the paragraph that says two cues are fused and links
  *Detection logic* and the project poster, the station photo (Figure 2, the README's first view of the system) and the animation
  (Figure 3) with their captions, one `[!IMPORTANT]` alert repeating only the must-not-miss part of *Limitations*,
  then the Contents line (R4, 2026-11-03).
- **Detection logic** states the stages briefly: the shared stages in one `text` block naming each
  stage's module and function, and the catalogue stages, one numbered item each with their thresholds,
  in a `<details>` block; `.claude/project-docs/SPEC.md` > *Pipeline stages* lists them one line each,
  and the two agree.
- **Headings cited from elsewhere stay as they are**: *Setup*, *Platform*, *Limitations* and *Licence
  note* are named in operator messages and code comments ("README > Setup"), and SPEC links `#setup`,
  `#limitations`, `#platform` and `#detection-logic` (checked by `test_capabilities_doc.py`).
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
  carries the same sentence, then "Funded by the European Union.", from its generator), Figure 6, its
  caption, then the EU disclaimer word for word as `Funding_Row_Cls.DISCLAIMER` holds it. The window's
  band does not carry the disclaimer; the README and Figure 6's source do.
- **No semicolons in prose** (readme-writer `style.md` > *Language*, the owner's rule of 2026-10-24;
  `check_readme.py` reports one as ERROR [semicolons]). The EU disclaimer has none, so it needs no
  exception. The semicolons left in the README are syntax, which the check skips: the FastSAM
  `python -c` one-liner, the folders' `text` block and the avatars' `width="120px;"`. Figure 6's alt
  text and the funding SVG's `aria-label` (written by `Example/UI/architecture_diagram.py`) list the
  three logos the same way, with commas.
- **Limitations** follow project-style-rpx `project.md` > *Records*: three limitations, each the
  consequence first, then the evidence, then whether it is verified.
- **No internal document is linked or named** (the owner's ruling, 2026-10-24): nothing in
  `.claude/project-docs/`, and never the Claude Code skills. A fact the README needs is stated where it
  is used; a reader who needs more reads the code and its comments.
- The root layout is project-style-rpx `project.md` > *Root*; this file does not repeat it.
- **Length**: within the generic 250-line budget (249 visible lines, 2026-11-03), with ten `<details>` blocks:
  the setup by hand, `--frame` and `scan.py`, the two Live screenshots, the configuration's file names, the golden
  file, the catalogue stages, the models and the Linux measurement, the repository's folders, swapping a component,
  and the third-party components (the owner's rulings of 2026-10-24 and 2026-11-03). The platforms, `./install.sh`,
  the top block's figures, the alert, the limitations and the validation stay visible.
- **Checker false positive**: `5.0.0.93` (line ~62, the opencv-python-headless version) is reported as
  an IP address; it is a version.

## README tests

| Test | Pins |
|---|---|
| `test/UI/test_brand_figures.py::test_the_readme_shows_the_diagram` | Figure 1 is in the README |
| `test/UI/test_brand_figures.py::test_the_diagram_is_the_generators_output` | Figure 1 is the script's output |
| `test/UI/test_brand_figures.py::test_the_readme_funding_row_is_the_generators_and_self_contained` | Figure 6 is the script's output |
| `test/UI/test_analysis_animation.py` | Figure 3's script, and the committed clip's width, length and size |
| `test/UI/test_funding_band.py::test_the_disclaimer_is_kept_word_for_word_in_the_readme_and_the_diagram` | the EU disclaimer, word for word |
| `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` | the test set the README counts |

Commands:

```bash
.venv/bin/python -m pytest -q test/UI/test_brand_figures.py test/UI/test_funding_band.py
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
| EDIH-DIGIMAT, Ministry of Industry and Trade, EU emblem | traced SVGs in `App/assets/` | the funding band and Figure 6 (a funding obligation) | in the repository | the funders' usage and visibility rules | `USAGE.md`; the EU's [visibility rules](https://commission.europa.eu/funding-tenders/managing-your-project/communicating-and-raising-eu-visibility_en); the other two sources **unconfirmed** | - | edih-digimat.cz, mpo.gov.cz |
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
