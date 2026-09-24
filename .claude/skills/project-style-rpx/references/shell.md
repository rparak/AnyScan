# Shell

`install.sh` is the only shell file, so this page describes what it does — the conventions of one
file, not a pattern observed across several. A second script follows it; a disagreement between the
two is a question, not a new rule. There is no `.bat`: Windows is not a target (README > Platform).

✅ = enforced by `test/Install/test_install.py`; 📄 = documentation only (the style checker is
Python-only; `bash -n install.sh` is the syntax check).

## Shape 📄

- `#!/usr/bin/env bash`, then the same `#`-comment MIT header as the Python files, with
  `File Name: ../install.sh`.
- A `# Description:` comment block: what it does, the order of its steps and why, usage with every
  option, and the output format.
- Constants in a `# Description:\n#   Initialization of constants.` block, each `CONST_*`, preceded
  by a comment saying what and why, ending `#   Unit [type]` — as in Python.
- Functions, not one long sequence: `Pascal_Snake_Case` names (`Detect_Platform`, `Ensure_Venv`,
  `Verify_File`), each opening with a `# Description:` / `# Args:` / `# Returns:` comment in the
  Python docstring's numbered form. `Main` calls the steps in order.
- `Main` runs only when the file is executed, not sourced
  (`if [ "${BASH_SOURCE[0]}" = "$0" ]; then Main "$@"; fi`), so tests can source it and call one step.
- Written for bash 3.2, the version macOS ships: no associative arrays, no `mapfile`, no `${var,,}`.

## Output ✅

Every line in the application's log format (`src/Logger/Core.py`), through one `Log` function:

```
2026-09-24 13:05:07 [INFO   ] Detected macOS 26.6.2 on Apple silicon (Apple M2 Pro).
2026-09-24 13:05:09 [WARNING] No NVIDIA driver found (nvidia-smi is not installed); installing ...
```

The level is padded to `CONST_LEVEL_WIDTH` (7, the logger's own constant) and chosen by the call
site. A third-party tool's own output is either suppressed and summarised (pip: output kept, its tail
logged as ERROR lines on failure) or shown only as a progress bar when attached to a terminal.

## Failure 📄

- A failure is one or more ERROR lines, the last saying what to do, then a non-zero exit — through
  `Die`. Never a bare trace: an ERR trap (`On_Unexpected_Error`) names the line and command of
  anything unanticipated; INT/TERM (`On_Interrupt`) says re-running is safe.
- Check the cheapest thing first (the Python version before the platform before a 5 GB download).
- Report what was found before acting on it (detection lines, then a `Plan:` line); `--detect-only`
  stops there.

## Re-running 📄

- Every step checks what is in place and says so (`already present and verified`, `pip changed
  nothing`), so a second run changes nothing.
- A download goes to a `.part` file, is verified, and only then replaces anything.
- The script never deletes the user's state: a broken `.venv` is reported with the command to remove it.

## Tests ✅

pytest in `test/Install/test_install.py`: the script is sourced in a fresh `/bin/bash` with a hermetic
`PATH` — stubs for the commands that describe the machine ahead of links to the real coreutils — and
every log line is checked against the format. The test file's docstring states which paths ran for
real and which only against stubs.
