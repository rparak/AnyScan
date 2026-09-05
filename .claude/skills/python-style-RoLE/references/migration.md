# Migrating an existing project to RoLE style

Converting a codebase that already works is not the same as writing new code.
Most RoLE conventions are cosmetic and safe; a few — the `Pascal_Snake_Case`
renaming and the `_Cls` / `_Str` suffixes — break every call site simultaneously.
Doing those first, across the whole repository, is how a migration turns into a
day of debugging import errors.

Work in the phase order below. Each phase is independently committable and
independently revertable.

## Step 0 — Safety net

```bash
git checkout -b style/role-migration
python .claude/skills/python-style-RoLE/scripts/check_style.py . > /tmp/gap.txt
tail -1 /tmp/gap.txt
```

Establish how you will know the code still works:

- If the project has tests, run them now and record the result. That is the
  baseline for every phase.
- If it has no tests, write a characterization script **before** touching
  anything: call the main entry points with fixed inputs, dump the outputs to a
  file, and diff against that file after each phase. Without this there is no way
  to distinguish a successful rename from a silent breakage.

Never run a migration on a dirty working tree.

## Phase 1 — Cosmetic, file-local, non-breaking

Nothing here changes a name any other file depends on. Safe to do in bulk.

1. MIT header docstring in every file, with the correct `File Name:` line.
2. Import comments — library name, purpose, `[pip3 install x]`, and the
   `# Custom Lib.:` group with `#   ../Path/Module` lines.
3. `import typing as tp`; rewrite `List[str]` / `list[str]` as `tp.List[str]`.
4. Add missing parameter and return annotations.
5. Convert docstrings to the RoLE format — `Description:`, numbered `Args:`,
   `Returns:` with the `parameter` entry, `[Vector<float> 1x3]` type notation.
6. Move module-level literals into a `CONST_*` block under the
   `"""Description:\n    Initialization of constants.\n"""` heading. **Keep the
   old name as an alias** if anything outside the module imports it.
7. Comment density — add the missing block comments explaining intent.

Verify: baseline tests still pass; `check_style.py` count drops sharply.
Commit as one change per file or one per category, not one giant commit.

## Phase 2 — Structural, still mostly local

1. Mutable default arguments → `None` sentinel. Behaviour-preserving unless
   something relied on the shared list, which is a bug either way.
2. Public attributes → `self.__private` plus a `@property`. Breaking for anyone
   who *assigned* to the attribute; find those first:
   ```bash
   grep -rn "\.attribute_name\s*=" --include='*.py' .
   ```
   If assignment sites exist, add an explicit `Set_*` method rather than a
   property setter.
3. Plain parameter-bag classes and dicts → `@dataclass` `*_Str` with
   `Pascal_Snake_Case` fields and `#   Unit [type]` comments.
4. `logging` calls → `print(f'[INFO] ...')`. Do this only if the project is not
   a library someone else configures logging for; note the tradeoff to the user.
5. Error handling → the assert-inside-try pattern. Read the caller side first:
   if callers currently catch a real exception, converting the callee to print
   and return `None` will produce a `TypeError` further downstream instead. In
   that case leave the exception in place and tell the user why.

Verify after each item.

## Phase 3 — Renaming (the breaking phase)

Do this in one atomic commit per module, never partially.

**Build the map first.** Do not rename in place as you read.

```bash
# Every definition that will change
grep -rnE '^\s*(class|def) ' --include='*.py' . > /tmp/defs.txt
```

Produce an explicit table before editing anything:

| Old | New |
| --- | --- |
| `class BoundingBox` | `class Bounding_Box_Cls` |
| `def get_center(self)` | `def Get_Center(self)` |
| `self.center` | `self.__center` + `@property Center` |

Show the table to the user and get agreement before applying it. A rename map is
cheap to argue about and expensive to undo.

**Then apply with word-boundary matching**, one name at a time:

```bash
grep -rlnw 'get_center' --include='*.py' . | xargs sed -i 's/\bget_center\b/Get_Center/g'
```

`\b` matters. A bare substitution of `center` also hits `centered`,
`center_of_mass`, and the word "center" inside every docstring.

**Names that must not be renamed:**

- Dunder methods — `__init__`, `__repr__`, `__enter__`, `__call__`.
- Anything a framework dispatches on by name: `pytest`'s `test_*` and
  `conftest.py`, Django's `save()` / `clean()`, `unittest`'s `setUp`,
  Flask/FastAPI route handlers referenced by decorator, Celery task names,
  Blender's `bpy` operator `execute` / `poll`, `argparse` dest names.
- Methods overriding a third-party base class — the parent defines the name.
- Anything in a published package's public API, unless the user accepts a major
  version bump. Offer a deprecation shim instead:
  ```python
  # Deprecated: kept for backward compatibility with the previous API.
  get_center = Get_Center
  ```
- Names referenced from outside Python: config files, JSON/YAML keys, templates,
  notebooks, documentation, `entry_points`.

**Find the dynamic references that grep for definitions will miss:**

```bash
grep -rnE "getattr|setattr|hasattr|globals\(\)|locals\(\)|__all__|importlib" --include='*.py' .
grep -rn "get_center" --include='*.md' --include='*.ipynb' --include='*.yaml' --include='*.toml' .
```

A name used as a string inside `getattr(obj, 'get_center')` will not move with
the rename and will fail only at runtime.

Verify: full test suite or characterization diff after **every** module.

## Phase 4 — Layout

Only worth doing on a project that will genuinely live as a RoLE-style project.

1. Move sources under `src/<Package>/<Domain>/Core.py`, helpers into
   `<Domain>/Utilities/<Theme>.py`, dataclasses into `Parameters/`.
2. Use `git mv` so history follows the file.
3. Convert runnables into `Example/<mirror>/` scripts with the `CONST_*`
   configuration block and `if __name__ == '__main__': sys.exit(main())`.
4. Removing `__init__.py` and switching to the `sys.path` idiom is the most
   disruptive change available and breaks `pip install -e .`. **Do not do this
   unless the user explicitly asks.** If the project is installed as a package,
   keep the packaging and skip this step — a RoLE-styled installable package is a
   perfectly reasonable end state.

## When to stop

Not every project should be fully converted. Push back and say so if:

- It is a library other people import — renaming is a breaking API change.
- It uses a framework whose conventions conflict (Django models, pytest suites,
  pydantic settings). Framework conventions win; apply RoLE style to the code
  around them.
- The team on the project did not ask for it. A repository consistent in its own
  style is better than one half-converted to another.

Partial adoption is a legitimate outcome. Phases 1 and 2 give most of the
readability benefit with almost none of the risk; Phase 3 is the one that needs a
real reason.

## Reporting

At the end, tell the user: the phases completed, the `check_style.py` count
before and after, every name that was deliberately not renamed and why, and any
place where RoLE style was overridden by a framework requirement.
