# readme-writer: project reference for AnyScan

AnyScan's README decisions; they override the personal skill **readme-writer** where they differ.
This folder has no `SKILL.md` on purpose: a personal skill wins over a project skill of the same
name, so a copy here would be ignored and drift.

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
| the theme, the type scale, the pixel icons, a logo | Figure 1 and Figure 2 | `.venv/bin/python Example/UI/architecture_diagram.py` |
| the funding logos or `Funding_Row_Cls.DISCLAIMER` | *Funding* (Figure 2 and the disclaimer, word for word) | `.venv/bin/python Example/UI/architecture_diagram.py` |
| `install.sh`, `requirements*.txt`, a model or its size | *Setup*, *Platform* | - |
| an option of `App/run.py` or an `Example/` script | *Run*, *Captures on the rig*, *Tests* | - |
| a configuration file name, kind or link | *Configuration* | - |
| a measured run on a platform | *Platform* (the table and its numbers) | - |
| a limitation found, measured or lifted | *Limitations* (and KNOWN_ISSUES, the DD) | - |
| a root entry, a folder, a committed asset | *Repository layout* (its `<details>`, with the packages under `src/`) | - |
| the test layers or their commands | *Tests* | - |
| an author or a contributor added (the owner's word only) | *Authors* | - |

## Statuses

`.claude/project-docs/SPEC.md` > *Verified on hardware, and not yet* is the source of truth; the README uses its
words exactly (the owner's ruling, 2026-10-23): **Verified, measured** (macOS), **Verified on one
machine, 2026-09-29** (Linux), **Never tried, not a target** (Windows); in the text, *verified* /
*not verified* / *unverified* with what was run. A status changed in one place changes in both.

## Figures

- Script: `Example/UI/architecture_diagram.py` writes `images/anyscan-architecture.svg` (Figure 1)
  and `images/anyscan-funding.svg` (Figure 2), from the theme's tokens, `Style.py`'s type scale and
  font fallbacks, and the pixel icon set; regenerated, never edited by hand. `Example/UI/build_logo.py`
  derives the logo copies from `images/anyscan-logo.svg`.
- Folder: `images/` (the generic default is `Media/`; project-style-rpx `project.md` > *Root*).
- Light and dark: each figure carries its own opaque ground (a white card, the purple band), so no
  `<picture>` variants. **Unchecked** on GitHub's dark theme until the owner looks at both figures
  there after the push (2026-10-23).
- The project poster, `images/anyscan-poster.pdf`, is linked from the top paragraph; it is the
  delivered file, not generated.
- Numbering: Figure 1 the architecture at the top, Figure 2 the funding row; captions
  `**Figure N:** …` directly below.

## Rules

- **The top block**: Figure 1 and its caption, the paragraph that says two cues are fused and links
  *Detection logic* and the poster, one `[!IMPORTANT]` alert repeating only the must-not-miss part of
  *Limitations*, then the Contents line.
- **Detection logic** states the stages briefly: the shared stages in one `text` block naming each
  stage's module and function, and the catalogue stages, one numbered item each with their thresholds,
  in a `<details>` block; `.claude/project-docs/SPEC.md` > *Pipeline stages* lists them one line each,
  and the two agree.
- **Headings cited from elsewhere stay as they are**: *Setup*, *Platform*, *Limitations* and *Licence
  note* are named in operator messages and code comments ("README > Setup"), and SPEC links `#setup`,
  `#limitations`, `#platform` and `#detection-logic` (checked by `test_capabilities_doc.py`).
- **Commands** are written for the environment `./install.sh` creates, activated with
  `source .venv/bin/activate` right after it (`python ...`, `pytest`).
- **Authors** stands just before *Funding* (readme-writer has no Authors rule; its Acknowledgements, who
  contributed or funded, sit there): Roman Parák, the author, linked to https://github.com/rparak, then the
  contributors LukasMoravansky, vojtechmarek13 and piifl, each shown by their GitHub username linked to their
  profile, no full name invented (the owner's ruling, 2026-10-24). `LICENSE`'s copyright holder (JIC Smart
  Factory) is separate and unchanged.
- **Funding** reads: "AnyScan was developed at JIC within the EDIH-DIGIMAT project.", Figure 2, its
  caption, then the EU disclaimer word for word as `Funding_Row_Cls.DISCLAIMER` holds it. The window's
  band does not carry the disclaimer; the README and Figure 2's source do.
- **Limitations** follow project-style-rpx `project.md` > *Records*: three limitations, each the
  consequence first, then the evidence, then whether it is verified.
- **No internal document is linked or named** (the owner's ruling, 2026-10-24): nothing in
  `.claude/project-docs/`, and never the Claude Code skills. A fact the README needs is stated where it
  is used; a reader who needs more reads the code and its comments.
- The root layout is project-style-rpx `project.md` > *Root*; this file does not repeat it.
- **Length**: within the generic 250-line budget (250 visible lines, 2026-10-24), with four `<details>`
  blocks: the setup by hand, the catalogue stages, the Linux measurement and the repository's folders
  (the owner's ruling of 2026-10-24, lifting the 2026-10-23 departure). Platforms, `./install.sh`,
  the alert and the limitations stay visible.
- **Checker false positive**: `5.0.0.93` (line ~62, the opencv-python-headless version) is reported as
  an IP address; it is a version.

## README tests

| Test | Pins |
|---|---|
| `test/UI/test_brand_figures.py::test_the_readme_shows_the_diagram` | Figure 1 is in the README |
| `test/UI/test_brand_figures.py::test_the_diagram_is_the_generators_output` | Figure 1 is the script's output |
| `test/UI/test_brand_figures.py::test_the_readme_funding_row_is_the_generators_and_self_contained` | Figure 2 is the script's output |
| `test/UI/test_funding_band.py::test_the_disclaimer_is_kept_word_for_word_in_the_readme_and_the_diagram` | the EU disclaimer, word for word |
| `test/integration/test_pipeline.py::test_the_inventory_names_every_frame_of_the_test_set` | the test set the README counts |

Commands:

```bash
.venv/bin/python -m pytest -q test/UI/test_brand_figures.py test/UI/test_funding_band.py
.venv/bin/python ~/.claude/skills/readme-writer/scripts/check_readme.py README.md   # 0 errors, 1 warning (above)
<throwaway python with cmarkgfm> ~/.claude/skills/readme-writer/scripts/render_readme.py README.md   # 0 leftovers, 2026-10-24
```

## Pointers

`CLAUDE.md` > *Skills*; feature-manager `project.md` > *Docs*.
