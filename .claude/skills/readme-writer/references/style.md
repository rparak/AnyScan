# README writing

## Language

- Plain, precise English; active voice; present tense; short sentences.
- One idea per paragraph; the paragraph leads with its point.
- One name per thing, used everywhere: a variant, a file, a component keeps the same name in the
  text, the tables, the figures and the code. A domain term is defined at first use, or in a short
  glossary when there are several.
- Acronyms spelled out at first use: "Denavit-Hartenberg (DH) parameters".
- No marketing language and no filler: not "simply", "just", "easy", "powerful", "seamless",
  "blazing", "state-of-the-art". No emoji decoration. No exclamation marks.
- Say what the reader does and what happens: "Run X. It writes Y." not "X can be used to...".
- **No semicolons in prose.** Split the sentence in two, or use a comma, a colon or a dash, whichever
  reads best, without changing a fact. Code blocks, inline code, commands, URLs, HTML attributes and
  entities are exempt: a semicolon there is syntax. Text quoted word for word from a fixed source (a
  legal disclaimer, a licence notice) stays as it is, and a semicolon in it is reported, not changed.
  `check_readme.py` reports a semicolon in prose as an ERROR.

## Numbers

- Every number has its unit: `12.05 s`, `20 mm`, `1.818 m`. In a table, the unit is in the header:
  `Time [s]`.
- Every number has a source the reader or a test can find: a file in the repository, a dated run,
  a measurement with its method. The project reference lists the sources.
- Estimates, simulation results and measurements are labelled as what they are, where the number
  appears (the caption, the table note, the sentence).
- Keep the precision that carries a meaningful difference; do not round two different values to
  the same one. Use the precision of the source, not more.
- A relative change states its base: "−48.4 % against the taught program".

## Claims and statuses

- A claim is backed by something in the repository: code, a test, a result file, a dated note.
  No invented authors, URLs, DOIs, publications, benchmarks, users or adoption figures.
- Future work is written as possible ("could be extended to..."), never as promised, and only if
  the project wants it mentioned.
- **Status words are fixed** and written identically everywhere they appear (text, table, figure
  label, caption), with the evidence: for example *delivered — tested on the real system (who,
  date)*, *tested in simulation only*, *proposal, not verified*, *deprecated, superseded by X*.
  The project reference records the exact words.

## Commands

- In fenced blocks with a language tag: `bash` for commands, `console` for a transcript with
  prompts, `text` for output or plain listings, `yaml`, `python`, `mermaid`.
- Copy-pasteable: no `$ ` prompts in a `bash` block. Output is shown in its own `text` block, or
  as a trailing comment that the shell ignores.
- Platform differences explicit (a comment per line, or one block per platform), and the verified
  platform named: "macOS (verified), Ubuntu (not verified)".
- **Every command is run before it is documented**, as written, and the shown output is what it
  printed. A command that writes into the repository is run into a temporary directory, or with
  the project's own output option.
- **Commands run, and examples.** A command is either run as written (and documented as such) or
  an **example**: it contains a reader placeholder in angle brackets (`git clone <URL>`,
  `--out <dir>`) and is marked with a trailing `# example: replace <URL>` comment. An example is
  not run as written and is not reported as verified; the same command with the placeholder filled
  is run where it can be (a clone from the local path before a remote exists).
- **Output that contains a path** (an absolute output directory, a temporary path) is shown
  normalised: the path replaced by a marked placeholder (`<out>`), and the block or the line before
  it says so. Never paste a machine's path; `check_readme.py` flags `/Users/`, `/home/`,
  `/private/` and `/var/folders/` paths as errors and a bare `/tmp/` path as a warning.
- **System prerequisites** (the interpreter, a system package) are listed as prerequisites with
  their install command per platform. That command is not run to verify the README: the
  prerequisite is verified by a presence check (`python3.11 --version`, `command -v <tool>`), and
  the check's output is what was verified.
- Runtimes are given with the machine they were measured on.

## Links

- Relative links for repository files: `[LICENSE](LICENSE)`, `[script](scripts/run.py)`.
- No absolute local paths (`/Users/...`, `/home/...`, `C:\Users\...`), no `file://`.
- No links to internal or private documents, no hosts, no IP addresses, no secrets or tokens.
- Link to a heading by its GitHub anchor; keep headings stable.
- External links only to stable targets (a release, a DOI, the upstream project), never to a
  search result or a moving branch file when a tag exists.

## Tables

- At most about 6 columns in the visible part; wider tables go into `<details>` or a linked file.
- Numbers right-aligned (`---:`), units in the header, the same precision down a column.
- A dash `—` for "not applicable", never an empty cell that could mean zero.
- One row per thing; the reference row (baseline) first or marked.

## Accessibility

- Alt text describes what the image shows (at least 12 words), not the file name.
- Meaning never by colour alone: a label, a pattern or a marker carries it too.
- Headings in order, link text that says where it goes ("the comparison table", not "here").
