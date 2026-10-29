"""
Find colours named by value outside the theme.

    python check_tokens.py <dir_or_file> [...] [--allow Theme.py]

Scans Python files with the tokenizer (so comments and docstrings are ignored) for a hex colour in a string
('#640ABA', '#fff') and for a QColor built from numbers (QColor(100, 10, 186)). The theme module (Theme.py by default)
is where every colour lives and is skipped, as are tests/ and test/ folders (they compare against literal values on
purpose). Exit status 1 when anything is found. AnyScan's
test/UI/test_colour_tokens.py does the same as a test.
"""
import argparse
import io
import os
import re
import sys
import tokenize

HEX = re.compile(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b')


def Scan(path: str):
    found = []
    with open(path, 'r', encoding='utf-8') as handle:
        source = handle.read()
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    for index, token in enumerate(tokens):
        if token.type == tokenize.STRING:
            text = token.string
            # A docstring is a statement of its own: a string token right after a NEWLINE/INDENT/DEDENT or at start.
            previous = tokens[index - 1].type if index else tokenize.NEWLINE
            if previous in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL) and \
                    tokens[index + 1].type in (tokenize.NEWLINE, tokenize.NL):
                continue
            for match in HEX.finditer(text):
                found.append((token.start[0], 'hex colour %s in a string' % match.group(0)))
        if token.type == tokenize.NAME and token.string == 'QColor' and index + 2 < len(tokens) \
                and tokens[index + 1].string == '(' and tokens[index + 2].type == tokenize.NUMBER:
            found.append((token.start[0], 'QColor built from numbers'))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--allow', action='append', default=['Theme.py'])
    args = parser.parse_args()
    files = []
    for path in args.paths:
        if os.path.isdir(path):
            for root, dirs, names in os.walk(path):
                # Tests compare against literal values on purpose; the theme's own module is allowed below.
                dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', '.venv', 'venv', 'tests', 'test')]
                files += [os.path.join(root, n) for n in names if n.endswith('.py')]
        else:
            files.append(path)
    problems = 0
    for path in sorted(files):
        if os.path.basename(path) in args.allow:
            continue
        for line, what in Scan(path):
            print('%s:%d: %s' % (path, line, what))
            problems += 1
    print('%d finding(s) in %d file(s)' % (problems, len(files)))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
