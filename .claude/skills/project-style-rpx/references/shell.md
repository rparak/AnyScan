# Shell - the installer

`install.sh` at the root installs the project. A second shell script follows the same rules; a
disagreement between the two is a question, not a new rule. The project reference names the target platforms, the interpreter and any verification step.

✅ = enforced by the installer test; 📄 = documentation only. The style checker is Python-only;
`bash -n install.sh` is the syntax check.

## Targets 📄

- The project reference lists each target platform and whether it is **verified** (run on that
  platform for real) or **unverified** (written, tested only against stubs). Every message and
  document says which; nothing claims an unverified platform works.
- The OS and architecture are detected (`uname -s`, `uname -m`), never assumed. An unsupported OS
  fails with a sentence naming what was found and the supported platforms.
- The installer has **one block per platform the project reference lists** - its detection arm,
  its interpreter lookup and its install command - and nothing for a platform it does not list.
- No `.bat` unless Windows is a target.

## Prerequisites 📄

What the installer does not install itself (the interpreter from Homebrew or apt, a system
library) is a **prerequisite**: the README and the installer's failure message give its install
command, and it is verified by a **presence check** (`python3.11 --version`, `command -v <tool>`),
never by running the install command. The installer's own first steps are that presence check.

## Shape 📄

- `#!/usr/bin/env bash`, then the same `#`-comment licence header as the Python files, with
  `File Name: ../install.sh`.
- A `# Description:` comment block: what it does, the order of its steps and why, usage with every
  option (`--detect-only`), and the output format.
- Constants in a `# Description:\n#   Initialization of constants.` block, each `CONST_*`, preceded
  by a comment saying what and why, ending `#   Unit [type]` - as in Python.
- Functions, not one long sequence: `Pascal_Snake_Case` names (`Detect_Platform`, `Find_Python`,
  `Ensure_Venv`, `Install_Requirements`), each opening with a `# Description:` / `# Args:` /
  `# Returns:` comment in the Python docstring's numbered form. `Main` calls the steps in order.
- `Main` runs only when the file is executed, not sourced
  (`if [ "${BASH_SOURCE[0]}" = "$0" ]; then Main "$@"; fi`), so tests can source it and call one step.
- When macOS is a target: written for **bash 3.2**, the version macOS ships: no associative arrays, no `mapfile`, no
  `${var,,}`, no `|&`, no `declare -n`.

## Steps, cheapest check first 📄

1. Detect the OS and architecture.
2. Find the project's Python version, **called explicitly**: an absolute path where the platform
   has a known one (Homebrew on macOS), the versioned name (`python3.11`) on `PATH` otherwise. **A
   bare `python3` is never called**: it resolves to whatever is first on `PATH`. Missing → fail
   with the install command for that platform.
3. Create `.venv` with that interpreter if it is absent. A `.venv` that exists but is broken (wrong
   version, no `bin/python`) is reported with the command to remove it; the script **never deletes** it.
4. `pip install -r requirements.txt` into `.venv`. `requirements.txt` pins every **direct**
   dependency with `==` (the version installed and run), grouped under comments naming what needs
   each. A full `pip freeze` lock file only if the project reference asks for one.
5. Project-specific verification, if the project reference names one (hashes of vendored files, a
   recorded input hash). Nothing is downloaded that the repository could vendor.

`--detect-only` reports what was found and the plan (a `Plan:` line), then stops before step 3.

## A new dependency 📄

Before a package joins `requirements.txt`:

- **It installs from a wheel on every target platform** the project reference lists (check the
  package index's files for the platform tags; a package with no wheel and no buildable source for a
  target is not adopted, or the project writes the part it needs itself, with its tests).
- **Its licence is checked**, including any binary it bundles (an encoder, a solver): a bundled GPL
  program run as a separate process is not linked, but redistributing it is a different case. The
  result is a design-decisions entry and, for the public page, a third-party note (readme-writer).
- It is pinned `==` to the version installed and run, under a comment naming what needs it, with the
  owner's approval (feature-manager: a new dependency is a "large" change).

## Output ✅

Every line through one `Log` function, in the log format:

```
2026-01-12 11:05:07 [INFO   ] Detected macOS on Apple silicon (arm64).
2026-01-12 11:05:07 [WARNING] Ubuntu Linux is a target but is unverified.
2026-01-12 11:05:08 [ERROR  ] python3.11 was not found. Install it with: brew install python@3.11
```

`YYYY-MM-DD HH:MM:SS [LEVEL  ] message`: the level is padded to `CONST_LEVEL_WIDTH` (7, the width of
`WARNING`) and chosen by the call site. A third-party tool's own output is either suppressed and
summarised (pip: output kept, its tail logged as ERROR lines on failure) or shown only when attached
to a terminal.

## Failure 📄

- A failure is one or more ERROR lines, the last saying what to do, then a non-zero exit - through
  `Die`. Never a bare trace: an ERR trap (`On_Unexpected_Error`) names the line and command of
  anything unanticipated; INT/TERM (`On_Interrupt`) says re-running is safe.
- Check the cheapest thing first (the platform and Python before creating the environment before pip).
- Report what was found before acting on it (detection lines, then the `Plan:` line).

## Re-running 📄

- Every step checks what is in place and says so (`.venv already present`, `pip changed nothing`),
  so a second run changes nothing.
- The script never deletes the user's state and never edits a tracked file.

## Tests ✅

pytest in `test/Install/test_install.py`: `bash -n install.sh`; the script is **sourced** in a fresh
`/bin/bash` with a hermetic `PATH` - stubs for the commands that describe the machine (`uname`, the
versioned Python, a `python3` stub that fails the test if it is ever called) ahead of links to the
real coreutils - and each step is called on its own: OS detection for every target, Python
resolution, any verification step failing on a tampered copy, and every log line checked against the
format. The test never re-implements a step in Python (references/python.md > Tests). The test
file's docstring states which paths ran for real and which only against stubs.
