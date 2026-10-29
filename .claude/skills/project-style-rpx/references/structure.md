# Structure

How the code is divided, what may depend on what, and what the repository root holds. ✅ =
enforced by a test; 📄 = documentation only. The project reference fills in the names: its domains,
its layer order, its scripts folder, its formats and their readers, its root entries.

## Layout 📄

```
src/<Domain>/Core.py             one folder per domain; Core.py is its primary module
src/<Domain>/<Topic>.py          a second concern of the domain, when it has one (below)
src/<Domain>/Const.py            only the constants that more than one module of the domain uses
<scripts>/<script>.py            runnable scripts (the project names the folder: scripts/, Example/, ...)
test/<Domain>/test_<module>.py   mirroring src/; test/<scripts>/test_<script>.py per script; installer
                                 and README tests in their own folders; test/conftest.py
<config folder>/<file>.yaml      the configuration, written by hand (references/yaml.md)
<data folders>                   inputs and generated outputs, as the SPEC lists them
Media/                           the README images, written by one script (readme-writer); the default name
<generated folder>/<Kind>/       generated output by kind (reports, images, ...), git-ignored (below)
<log folder>/                    run logs, git-ignored
.claude/project-docs/            SPEC.md, KNOWN_ISSUES.md, design-decisions.md (FEATURES.md if the project keeps one)
.claude/skills/<skill>/          the shipped skills: SKILL.md, references/, assets/, scripts/ (below)
install.sh, requirements.txt     the installer and the pinned requirements (references/shell.md)
README.md, LICENSE, CLAUDE.md
```

No `__init__.py`. `src/` reaches `sys.path` through `test/conftest.py` in tests and, in scripts,
through a path built from `__file__`.

## Modules: Core.py, a topic module per second concern, Const.py for shared constants 📄 (✅ by a layout test)

- `Core.py` is each domain's primary module. A domain with one concern has only `Core.py`.
- **A second concern gets its own topic module**, named for the concern (`Check.py`, `Report.py`,
  `Parser.py`), which imports `Core.py` and never the other way round. Split by what the code is
  about, never by kind: a `Core.py` / `Utilities.py` / `Helpers.py` split scatters what belongs
  together, because "helper" is not a property of the code.
- **A constant lives with its only reader.** A constant that more than one module of the domain
  uses lives in the domain's `Const.py`, which holds nothing else. Another domain imports a name from
  the module that defines it.
- **A `*_Str` structure lives in the module that defines its behaviour**: a topic module's own
  structures live with it, not in `Core.py`.
- Tests mirror the modules (`test/<Domain>/test_<module>.py`); a `Const.py` is tested through its
  readers.
- A layout test pins it: each domain's declared modules (a literal list in the test), each module's
  test file, each constant with its readers. The project reference names the test, or says 📄.

## Generated output: one ignored folder per kind 📄

A run's products go into one git-ignored folder, a subfolder per kind (reports, images, trajectories;
the project names them), created by the installer and by the scripts; `--out DIR` moves a file. Logs
go to their own git-ignored folder: they are not results. Nothing generated lands at the root or in
the working directory (a library that writes a log file into the working directory is routed by the
code that calls it). A generated file that becomes a delivered input is committed on purpose
(*Committed generated data*, below).

## The root holds only what is declared ✅

The root holds `README.md`, `LICENSE`, `CLAUDE.md`, the code and data folders, the README images folder (`Media/` by default), the
installer and its requirements, `.gitignore` and `.claude/` - nothing else, unless the project
reference lists the exception with its reason (a test runner's configuration file it cannot read
from elsewhere; `CITATION.cff`, which GitHub reads only at the root, when the project wants to be
cited - readme-writer tests it). Internal documents are not at the root: they live in
`.claude/project-docs/`.

A test pins it: it lists the entries git tracks at the root (`git ls-files`, first path component)
and compares them with a literal set written in the test, and checks that the three project docs
exist in `.claude/project-docs/`. The set is written out, never read from the README or the
filesystem it checks (references/python.md > Tests). A new root entry changes the test, the
project reference and the SPEC's layout section in the same commit.

- The test reads what git tracks, so it is run **after** the new entry is staged; run before, it
  passes on a tree that does not yet hold the entry and fails on the next commit.
- It also refuses two tracked paths that differ only in letter case: a case-insensitive file system
  (macOS by default) checks out only one of them. A case-only rename goes through a temporary name
  (`git mv data tmp_data && git mv tmp_data Data`).

## `.claude/project-docs/` 📄

| File | Holds | Shape |
|---|---|---|
| `SPEC.md` | The current truth: goal, scope, measured facts, layout, formats, configuration, tests, risks | Numbered sections whose numbers never change: a section that goes away keeps its number with a one-line note; new sections are appended. Other files cite `SPEC §n`. History is in git, not in the text: no "previously", no changelog |
| `KNOWN_ISSUES.md` | Open limitations and accepted risks of the output | Only what is open. An item that is fixed is removed, and its resolution goes to design-decisions |
| `design-decisions.md` | Deliberate choices whose reason the code cannot show | **Decision / Why / Alternatives / Revisit if** and the pinning tests; a correction is made in place and says so |
| `FEATURES.md` (optional) | The feature tracker, if the project keeps one | Open items, and one row per done feature with its commits and acceptance date (references/markdown.md) |

The entry formats are in references/markdown.md. The README does not mention these files when the
project reference says so (readme-writer's project reference records it).

## Skills layout 📄

- The repository ships its skills in `.claude/skills/<skill>/`: `SKILL.md`, `references/`,
  `assets/`, `scripts/` - one self-contained skill each, the project's decisions in its
  `references/project.md` and any project-only reference or configuration (`check_style.json`, a
  file format's page). Each rule is written in one file.
- A personal skill of the same name would take precedence over the project's copy, so none is
  installed beside it; the project reference says how the personal copies are kept out.
- `CLAUDE.md` names the skills; a test pins their files.

## Layers 📄

The project reference declares the layer order of its domains:

```
<lowest domains>    import nothing of the project
<middle domain>     → the domains it names
<top domain>        → the domains it names
<scripts>/          → any of src/
```

- A lower layer never imports a higher one. A pure-computation domain knows nothing of files, the
  configuration file or heavy runtimes.
- A `src/` module never prints and never holds global state a caller cannot see: it reports through
  return values, exceptions (`*_Error_Cls` sentences) and injected callbacks.

## One reader and writer per file format 📄

Each on-disk format is parsed by exactly one module - the one that writes it, where anything writes
it - and everything else goes through that module, scripts and test helpers included (a test
compares against literal text). A second parser drifts from the writer silently. The project
reference keeps the table: format, read and written by, and who writes it by hand.

A file no code writes (the configuration) has one reader. A file written by a script only (a
results table, the README images) is written through one function of that script and read through
one.

**A writer is deterministic**: the same data gives the same bytes - a fixed key and column order, a
fixed number format (`%.9f`, or `float.hex` where exactness matters), no timestamp, no absolute
path. A run's provenance (the commit, the platform) goes into a named metadata field that a
comparison can leave out. **A binary or structured format carries a version**, and its reader
refuses another version, a missing field or a wrong shape with a sentence naming it.

## Committed generated data 📄

A file a tool generates is normally git-ignored and regenerated. When one is a delivered input
(a planned schedule, an optimized program, a fitted table) it is committed, and then:

- one script writes it, and nothing edits it by hand;
- it records the hash of every input it was made from, and the platform and versions;
- **a YAML or JSON input is hashed by its loaded content, not its bytes**: the document serialised
  as compact JSON with each mapping in the file's order (not sorted - an order can matter to a
  reader). A comment-only edit of a hand-written file then does not make the output stale; any other
  input (a recording, a binary model) is hashed by its bytes;
- its reader refuses it when an input's hash differs, naming the input and the command that makes it
  again;
- a test reproduces it byte for byte from its inputs (on the platform it records).

## Heavy runtimes only where needed 📄

A dependency that is slow to import or install and needed by one build tool only is imported inside
the function that needs it, never at module level of a module the tests import; the tests read the
committed product of that tool. The project reference names which runtimes are heavy.

## No parameter or field that cannot take effect 📄

A parameter with a single legal value, or a configuration field that is accepted but cannot change
what the code does, reads as a choice that is not there. Remove it together with the code path that
made it look configurable.

- **In code:** no flag that only one value is ever legal for; a test-only option that changes what
  the shipped code checks is the same fault.
- **In configuration:** a field must be read by something that can change behaviour, not merely
  parsed. A loader catches unknown keys but **not known keys that nothing reads**; that is checked
  by hand (references/yaml.md).
- A derived value is computed where it is needed, not stored as a parameter beside its inputs.

## A harness takes the project's path 📄

A script that checks, builds or shows what the project computes goes through the project's own code,
so its output cannot silently differ: a demo builds its model with the project's builder, a build
tool writes with the project's writer so the reader accepts exactly what it wrote. An exception is
stated where it is made and why.
