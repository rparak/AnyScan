---
name: readme-writer
description: >-
  Writes, restructures, reviews and maintains a GitHub repository's README so that its first
  screens say what the project does, for whom and how to start, every number has a source, every
  command has been run (or is a marked example), figures are generated, captioned and readable in light and dark mode, and
  statuses read the same everywhere. It updates only what a change affects, proposes a restructure
  before writing it, then verifies with scripts/check_readme.py and scripts/render_readme.py. Use it
  whenever a README is
  written, created, restructured, reviewed or updated, and whenever a change affects what a
  README states: results or measured numbers, figures or their inputs, commands or options,
  inputs and outputs, install steps, or the status of a deliverable (delivered, tested,
  proposal, deprecated) - even when the README is not mentioned.
---

# readme-writer

A README is the project's front page. Its reader decides in a minute whether the project is for
them and how to start. This skill keeps that page accurate, short at the top and verifiable.

**Assumes** (deliberate): a README in **GitHub-flavoured Markdown** rendered on **GitHub**
(alerts, `<picture>` light/dark images, Mermaid); its tools are Python scripts (stdlib, plus
`cmarkgfm` in a throwaway environment for rendering). Figures come from a script the project owns.

## 0. Read the project's part first

[references/project.md](references/project.md) holds this README's decisions: its readers, the
source of every number, the triggers, the statuses, the figures and their script, the layout rules
and the README tests; [references/check_readme.json](references/check_readme.json) holds the
checker's reasoned exceptions (uncaptioned figures, size budgets). **They override this skill**
wherever they differ: a rule of this file that a project decision replaces is written there, not
here. Where this skill's generic advice would change something the project reference records as
deliberate, list it as a judgement call for the user; never change it on your own.

Also follow the project's own conventions for code, commits and interpreters (for example a
project that forbids a bare `python3` - use its interpreter to run the scripts below). In a project
that follows `project-style-rpx`, the root layout is that skill's rule and its project reference
lists the root entries; this skill's project reference points there rather than repeating them.

## 1. Maintenance

1. Read `references/project.md`.
2. **Map the change** to what the README states, starting from the reference's *Triggers*: which
   sections, numbers, statuses, commands, figures and tests it touches. Write that list down before
   editing.
3. **Update only those.** Keep the structure, the visible/collapsed split and the wording of
   everything else. A number changed in one place is changed everywhere it appears (tables,
   captions, figure footnotes, prose); a status likewise.
4. **Regenerate** the figures whose input changed, with the project's figure script, and look at
   every regenerated image (light and dark).
5. **Run** the project's README tests and the checks in section 3.
6. A rule the change makes stale in `references/project.md` is corrected there in the same change.

A **restructure** (sections added, moved or removed, the visible/collapsed split changed) is proposed
first: the outline ([references/structure.md](references/structure.md)), what each section holds and
whether it is collapsed, the estimated visible line count and the tests it changes. **Stop for
approval**, then write it.

## 2. Rules that are never traded

Details: [references/style.md](references/style.md).

- **Every claim is backed by the repository**: a file, a test, a dated run. No invented authors,
  URLs, publications, benchmarks, users or roadmap promises. Future work is "possible", never
  promised.
- **Every number has its unit and its source**; estimates and simulation results say so; a
  meaningful difference is never rounded away.
- **Statuses are written the same everywhere** (README text, tables, figure labels, captions).
- **Every documented command has been run** as written, on the documented platform, with the
  output shown matching what it printed. A command that could not be run is said to be unverified.
  An **example** - marked with a reader placeholder such as `git clone <URL>` and an `# example:`
  comment - is not run as written; output that contains a path is shown normalised
  ([references/style.md](references/style.md) > Commands).
  Exception: a **system prerequisite**'s install command (`brew install ...`, `apt install ...`)
  is documented as a prerequisite and verified by a presence check (`python3.11 --version`), never
  by running the install.
- **Figures come from one deterministic script**, never edited by hand, and are looked at before
  they are committed.
- **No absolute local paths, hosts, IPs, secrets** or links to internal documents the public
  cannot open.
- **Safety and other must-not-miss facts** go into a GitHub alert near the top, not into prose.

## 3. Verify

1. `scripts/check_readme.py README.md` (stdlib only). ERROR findings are objective defects and are
   fixed; a figure the owner decided needs no caption (a header brand mark) is listed, with its reason, in the
   project's `references/check_readme.json` (`uncaptioned_figures`), which turns its finding into an INFO line;
   a size budget the owner decided (an animated preview) goes there too (`image_budgets`, `media_budget`,
   each with its reason; [references/figures.md](references/figures.md)), never as an accepted warning. WARN findings are judgement calls: fix them only when the project reference agrees,
   otherwise list them for the user. INFO lines are checked by hand (static badges against their
   source, Mermaid blocks).
2. **Rendering.** `scripts/render_readme.py` with cmarkgfm in a throwaway virtual environment
   outside the repository (see its docstring). GitHub's Markdown API (`--github-api`) uploads the
   text: offer it, and use it only with the user's consent. Mermaid: check with `mmdc` if it is
   installed; otherwise tell the user to look at the diagram on GitHub after the push.
3. **Project tests**: the README tests named in `references/project.md`.
4. **Images**: open every new or changed image, light and dark, at README width.
5. Walk [references/checklist.md](references/checklist.md) and report each item as done, not
   applicable, or not verified (with the reason).

The skill's own scripts are tested by `scripts/test_check_readme.py` and
`scripts/test_render_readme.py`, in the project's suite when the project lists this folder in its
pytest `testpaths` (the project reference says whether it does).

## 4. Report

- What changed in the README (sections, numbers, figures), with the sources.
- The checker summary (errors fixed, warnings left and why), the rendering result, the project
  tests run and their result, the images looked at.
- **Judgement calls for the user**, each with the alternative.
- **Not verified**: commands not run, Mermaid not rendered, platforms not tried.

## Reference map

| Read | When |
|---|---|
| [references/structure.md](references/structure.md) | choosing or reordering sections, the top block, what goes into `<details>` |
| [references/style.md](references/style.md) | writing or reviewing any text, table, command or link |
| [references/figures.md](references/figures.md) | adding, changing or reviewing a figure or the figure script |
| [references/checklist.md](references/checklist.md) | before finishing |
| [references/project.md](references/project.md), [references/check_readme.json](references/check_readme.json) | always, first |
