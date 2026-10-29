"""
Copy the JIC Smart Factory UI package into a project.

    python scaffold.py <target_dir> [--no-example] [--no-tests]

Creates <target_dir>/JIC_SF_UI/ (the modules), <target_dir>/JIC_SF_UI/assets/ (fonts with their OFL licences and the
logo SVGs with USAGE.md), and unless told otherwise <target_dir>/example_app.py, <target_dir>/annotate_demo.py and
<target_dir>/tests/ (the style tests). Refuses to overwrite an existing JIC_SF_UI/ so a project's own edits are never lost.
"""
import argparse
import os
import shutil
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('target')
    parser.add_argument('--no-example', action='store_true')
    parser.add_argument('--no-tests', action='store_true')
    args = parser.parse_args()

    target = os.path.abspath(args.target)
    package = os.path.join(target, 'JIC_SF_UI')
    if os.path.exists(package):
        print('refused: %s exists; merge by hand' % package, file=sys.stderr)
        return 1
    os.makedirs(target, exist_ok=True)
    shutil.copytree(os.path.join(SKILL, 'templates', 'JIC_SF_UI'), package,
                    ignore=shutil.ignore_patterns('__pycache__'))
    assets = os.path.join(package, 'assets')
    shutil.copytree(os.path.join(SKILL, 'assets', 'fonts'), os.path.join(assets, 'fonts'))
    for name in os.listdir(os.path.join(SKILL, 'assets', 'logos')):
        shutil.copy2(os.path.join(SKILL, 'assets', 'logos', name), assets)
    copied = [package]
    if not args.no_example:
        for name in ('example_app.py', 'annotate_demo.py'):
            copied.append(shutil.copy2(os.path.join(SKILL, 'templates', name), target))
    if not args.no_tests:
        copied.append(shutil.copytree(os.path.join(SKILL, 'templates', 'tests'), os.path.join(target, 'tests'),
                                      dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__')))
    # List only what was copied (a venv inside the target would otherwise flood the output).
    for path in copied:
        if os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for name in sorted(files):
                    print(os.path.relpath(os.path.join(root, name), target))
        else:
            print(os.path.relpath(path, target))
    return 0


if __name__ == '__main__':
    sys.exit(main())
