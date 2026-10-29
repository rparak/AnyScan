# YAML - the project configuration

The rules for a hand-written configuration file and the loader that reads it. The project reference
names the file (or files), its loader, its sections and its test. ✅ = enforced by the loader and
its test; 📄 = documentation only.

## One reader 📄

One loader function parses the file and returns a `*_Str`; it is the only code that opens it. No
module or script reads the YAML for itself; every setting reaches its user through that structure.
Tests load it raw only to write a mutated copy for the loader. No tool writes the file: a script
that finds a value to change prints the line to change instead.

## Shape 📄

Start from `assets/config_template.yaml`.

- A short header block between `## ===…=== ##` rules, in `#   Description:`-style sections, with
  **no licence text** (the licence is in `LICENSE`): what the file is, who reads it (the loader's
  path), what REQUIRED means, the units used, the frames or reference systems its values are
  expressed in.
- Keys are `Pascal_Snake_Case`, nested by concern (`Input.*`, `Limits.*`, `Output.*`).
- Every top-level section is preceded by a comment saying what it covers.
- **Every field is preceded by a comment** saying:
  1. what it means (and, where it matters, why its value is what it is);
  2. its **unit in brackets**, as the SI symbol or the unit's usual symbol - `[m]`, `[deg]`,
     `[°C]`, `[s]`, `[path]`, `[-]` (dimensionless); the canonical units are declared in the
     project reference;
  3. `REQUIRED.` - by default a project has **no optional fields**, so there are no defaults to keep
     in step with the code; an optional field is a decision the project reference records. A value
     that may be absent is written explicitly (`null`, `[]`), the header and the field's comment say
     which fields allow it, and an omitted key is still an error;
  4. **the source of the value** when it has one: a manual page, a datasheet, a measurement, the
     owner's confirmation. Example (hypothetical):

```yaml
Limits:
  # Largest file the reader accepts; above it the conversion runs out of memory on the target
  # machine. Source: measured 2026-01-12 (design-decisions.md). [MB] REQUIRED.
  Max_Input_Size: 512
```

- Paths are repository-relative.
- A documented estimate says so in its comment and its source, and is listed in
  `.claude/project-docs/KNOWN_ISSUES.md`.

## Loading ✅

- **A strict reader.** PyYAML's defaults hide errors in a hand-written file: of two equal keys the
  last silently wins, and `ON`, `OFF`, `yes`, `no` become booleans. The project's one YAML reader
  uses a `yaml.SafeLoader` subclass whose mapping constructor refuses a duplicate key (naming it and
  both lines), whose resolver reads only `true` / `false` as booleans (everything else that looks
  boolean stays text), and which keeps each value's line so every message can name file, line and
  key path. The loader's test pins each of the three.
- **Every problem is collected first, then the load fails once**, listing all of them
  (`Configuration_Error_Cls`).
- A REQUIRED field that is missing fails the load, **naming the field** by its full key
  (`Limits.Max_Input_Size`).
- A present value that is invalid fails the load; it **never falls back** to a default. Invalid
  includes a wrong type or vector length, `Min ≥ Max`, a value outside its physical or documented
  range, a precondition another rule relies on.
- An **unknown key** is reported as a **WARNING**, naming it (likely misspelt); it does not fail the
  load. The loader returns its notes; a script prints them.
- Units are converted once, in the loader, to the canonical unit of each quantity (declared in the
  project reference; SI by default); code downstream sees canonical units only.
- The loader's test names each required field literally, mutates the shipped file into a temporary
  copy for each rule, and checks the message names the field.

## A small language inside the configuration 📄

When a field holds lines of a small language (a program of calls such as `Move(P_HOME, v=0.5)`, a
formula), the loader parses each line - with Python's `ast` for call syntax, or a grammar of its own -
into a typed structure, and never evaluates it (`eval`, `exec`, `compile` and calling into the result
are not used). Anything outside the grammar (an expression, an attribute chain, a call as an argument)
is a load error naming the file, the line and the text. Names used in the lines are declared
elsewhere in the configuration and checked for the kind each argument needs.

## A field must be read by something that can change behaviour 📄

A field that reads as configurable, is accepted, and cannot take effect is worse than a missing one:
someone concludes the setting is in force when it is not. So a field exists only if some code reads it
**and** a different value changes what that code does; otherwise it is removed with the code path.

**The loader cannot enforce this.** It catches unknown keys, not known keys that nothing uses. Check
it by hand for every new field: name the reader and what a different value changes.

**A value with a single legal value is not a field.** It is a code constant, with its reason in a
comment. The project reference lists the project's cases.

A derived value is not a field either: it is computed from its inputs where it is needed. Storing it
would create a second source that can disagree.

## Machine-specific values stay out of the shipped file 📄

The committed file holds values that are right on every machine that clones it: repository-relative
paths and the project's own data. A value true on one machine only - an absolute path, a user name,
a host name, a secret - never goes into the shipped file. How a machine keeps its own copy is
*Unsettled* until a project needs it; the project reference then records the override convention.
