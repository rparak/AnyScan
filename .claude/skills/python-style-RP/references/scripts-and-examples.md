# Example scripts — RP

Runnable programs live in `Example/`, mirroring the `src/` tree. They are
demonstrations and benchmarks, not automated tests, even when named `test_*.py`.

## Fixed shape

1. MIT header docstring, with `File Name:` pointing at the script.
2. `import sys` and the `sys.path` guard.
3. Annotated imports — stdlib, third-party, then the `# Custom Lib.:` group.
4. `CONST_*` configuration block — this is the script's user interface.
5. `def main():` with a `Description:` docstring.
6. Body, divided by bare `"""Description: ..."""` section headings.
7. `if __name__ == '__main__': sys.exit(main())`.

## The sys.path guard

```python
import sys
if '../../../../' + 'src' not in sys.path:
    sys.path.append('../../../../' + 'src')
```

The `'../../../../' + 'src'` concatenation is the literal form used throughout —
keep it rather than writing `'../../../../src'`. Count the `../` segments from
the script's directory up to the repository root. A script at
`Example/Kinematics/FK/test_fk.py` is three levels deep, so it needs
`'../../../'`; one at `Example/Kinematics/IK/Results/x.py` needs
`'../../../../'`. Verify by running the script, since a wrong count fails only
at import time.

## Configuration block

```python
"""
Description:
    Initialization of constants.
"""
# Set the structure of the main parameters of the robot.
CONST_ROBOT_TYPE = Parameters.Universal_Robots_UR3_Str
# Number of randomly generated samples.
CONST_SIZE = 1000
# Save the data to a file.
CONST_SAVE_DATA = False
```

Scripts are configured by editing these lines. `argparse` is not used anywhere in
the project — do not introduce it unless asked.

## Section headings inside main()

Sections are separated by bare triple-quoted string expressions, which Python
evaluates and discards:

```python
    """
    Description:
        Generation of random joint orientations in radians.
    """
    theta_rand_aux = [0.0] * len(Robot_Str.Theta.Limit)
```

This is unusual but it is the house pattern for marking a phase of a script.
Ordinary `#` comments are used for individual steps within a section.

## Progress reporting

```python
    print('[INFO] The calculation is in progress.')

    # 1) Forward Kinematics (Standard)
    t_0 = time.time()
    for _, th in enumerate(theta_rand):
        RoLE.Kinematics.Core.Forward_Kinematics(th, 'Standard', Robot_Str)
    t = time.time() - t_0
    print(f'[INFO]  1) Forward Kinematics (Standard)')
    print(f'[INFO]      Time: {t:0.05f} in seconds.')

    ...

    if (np.array_equal(T_Standard, T_Modified)) == False:
        # Warning: Something wrong!
        print('[WARNING] The resulting homogeneous transformation matrices are different!')

    print('[INFO] The calculation process is complete.')
```

- Levels are `[INFO]`, `[WARNING]`, `[ERROR]`. The `logging` module is not used
  anywhere in the project (317 `print` calls, 0 loggers).
- Indentation of sub-items is done with spaces inside the string after the tag.
- Timings are formatted `{t:0.05f}`.
- Scripts open with a "in progress" line and close with a "complete" line.
- **Source deviation:** the repository writes these as `1\ ` with a backslash,
  which raises `SyntaxWarning: invalid escape sequence` on Python 3.12 in 19
  files. Write `1)` in strings and docstrings. The `# 1\ ` form is fine in
  ordinary comments.
- **Source deviation:** `== False` appears in comparisons; write `not ...`.

## Timing and data collection

`time.time()` deltas around a loop, not `timeit`. Collected results are written
under `Data/<Purpose>/<Robot_Name>/` as `.txt` or `.pkl`, with the output path
built from `CONST_PROJECT_FOLDER` and `CONST_FILE_NAME_OUT`.

## Entry point

```python
if __name__ == '__main__':
    sys.exit(main())
```

Always `sys.exit(main())`, never a bare `main()`. `main()` itself returns `None`
in the existing scripts.
