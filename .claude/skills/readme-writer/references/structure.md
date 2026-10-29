# README structure

Adapt; never pad. A section that has nothing true and useful to say is left out. The order below
is the default; a project reference may record a different one.

## The top block (the first screen)

In this order:

1. **Title**: the project's name; a subtitle only if the name does not say what it is.
2. **One-sentence value statement**: what it does and for whom. No adjectives that cannot be
   measured.
3. **Badges, a few and real**: version or release, licence, CI. Each points at something that
   exists: a release, the `LICENSE` file, a workflow in `.github/workflows/`. A static badge
   (a language or library version) states a fact that is checked against its source (the
   installer, the pinned requirements). No badge for a CI that does not exist, a coverage that is
   not measured, or a download count.
4. **One key figure or demo**: the image that shows the result or the product. Captioned.
5. **One GitHub alert** for what users must not miss (safety, data loss, a breaking change):
   `> [!WARNING]` or `> [!CAUTION]` for risk, `> [!NOTE]` / `> [!IMPORTANT]` for a fact.
   The marker line stands alone; the text follows on `>` lines. At most two alerts in the README.

## The sections, each only if relevant

| Section | It answers | Notes |
|---|---|---|
| Contents | where things are | one line of links, visible sections only (GitHub also offers its own outline) |
| About | the problem, the approach, the context | 1 short paragraph + 3 bullets at most |
| Results / Features | what it achieves, measured | one table and one or two figures visible; the rest collapsed |
| Quick start | from clone to the first result | at most 5 copy-paste commands; platforms explicit; the expected output shown |
| How it works | the method, at a glance | one Mermaid diagram + 3-6 bullets; the full method collapsed |
| Inputs and outputs | what it reads and writes | a file table; formats collapsed |
| Usage | common tasks | one task per sub-heading, each with its command |
| Configuration | what can be set | the fields that matter; the full list collapsed or linked |
| Limitations (and safety) | what it does not do, and what can go wrong | concrete; the alert at the top repeats only the must-not-miss part |
| Troubleshooting / FAQ | real problems users hit | only problems that happened; no invented questions |
| Repository layout | where the code is | a `text` block, one line per top-level folder |
| Contributing / development | how to test and change it | test and style commands |
| Citation | how to cite | only if the project wants to be cited; `CITATION.cff` (CFF 1.2.0) then exists at the root (a root-layout exception, project-style-rpx), and a test checks it against the schema and the repository (title, licence, version and date of the release) |
| Licence | the licence | the name, the holder, a link to `LICENSE`; third-party licences named |
| Acknowledgements | who contributed or funded | only what the project states |

**A tool the reader runs and changes** (a simulation, a pipeline): the visible part follows the
user's path - the quick start (install -> the one command -> see the result), the result, how to
change the main input (numbered steps, then a table *When this fails | It means | Do*), and a table
of the files by who changes them (you edit / generated / re-captured / never edit by hand).
Everything else is collapsed.

**A block written by code** sits between named markers (`<!-- <name>:start -->` ...
`<!-- <name>:end -->`), has one writer and one command that regenerates it, and a test that compares
the block with what the writer gives. Nothing else of the README is written by code; the block is
regenerated, never edited by hand.

## Information hierarchy

- The **visible part** (everything outside `<details>`) answers what / why / how to start in about
  one to two screens: **about 150-250 lines**. `check_readme.py` reports the count.
- **Depth goes into `<details>`** directly under the section it belongs to, or into docs the project
  already has (linked). One `<details>` per topic, with a summary that says what is inside:
  `<summary><b>All metrics</b>: the full table and its notes</summary>`.
- A blank line follows `</summary>`, or GitHub renders the Markdown below it as plain text.
- Headings inside `<details>` work as anchors, but the Contents line lists visible sections only.
- Nothing essential is only in a collapsed block: the visible part names the safety facts, the
  install path and the main result.

## Anchors and headings

- One H1 (the title); sections are H2; no level is skipped.
- Heading text is stable: a link elsewhere points at its anchor (lower case, punctuation removed,
  spaces as hyphens; a repeated heading gets `-1`, `-2`). Renaming a heading means updating every
  link to it; `check_readme.py` finds the broken ones.
