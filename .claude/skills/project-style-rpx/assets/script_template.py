## =========================================================================== ##
# MIT License
# Copyright (c) {{Year}} {{Holder}}
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
## =========================================================================== ##
# Author   : {{Author}}
# File Name: ../{{scripts}}/{{script}}.py
## =========================================================================== ##

# System (Default)
import sys
# OS (Operating system interfaces)
import os
# The repository root, built from this file's location, so the script runs from any working
# directory (project-style-rpx references/structure.md).
#   Unit [string]
CONST_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
#   Add access if it is not in the system path.
if os.path.join(CONST_REPO_ROOT, 'src') not in sys.path:
    sys.path.append(os.path.join(CONST_REPO_ROOT, 'src'))
# Argparse (Command-line parsing)
import argparse
# Custom Lib.:
#   ../Configuration/Core - the only reader of the configuration
from Configuration.Core import Load_Configuration, Configuration_Error_Cls

"""
Description:
    Initialization of constants.
"""
# The shipped configuration (project-style-rpx references/yaml.md; the file is named in the SPEC).
#   Unit [string]
CONST_CONFIG_FILE = os.path.join(CONST_REPO_ROOT, '{{config folder}}', '{{config file}}.yaml')


def main():
    """
    Description:
        {{What the script does, and - if it checks or shows what the project computes - that it goes
        through the project's own path (references/structure.md).}}

            .venv/bin/python {{scripts}}/{{script}}.py --config {{config folder}}/{{config file}}.yaml --out <dir>
    """

    parser = argparse.ArgumentParser(description='{{One line.}}')
    parser.add_argument('--config', default=CONST_CONFIG_FILE, help='the configuration (default: {{config folder}}/{{config file}}.yaml)')
    # A script that writes: --out DIR moves the configured file into DIR, keeping its name
    # ({{delete this comment and the --out lines below if the script writes nothing}}).
    parser.add_argument('--out', default=None, help='write into this directory instead (default: the configured path)')
    args = parser.parse_args()

    try:
        configuration = Load_Configuration(args.config)
    except Configuration_Error_Cls as error:
        print('[ERROR] %s' % error)
        return 1
    # The loader returns its WARNING notes (unknown keys); a script prints them.
    for level, message in configuration.Notes:
        print('[%s] %s' % (level, message))

    output_path = configuration.Output_Path   # {{the configured output path field}}
    if args.out is not None:
        output_path = os.path.join(args.out, os.path.basename(output_path))
    print('[INFO] {{What was done with %s.}}' % type(configuration).__name__)
    return 0


if __name__ == '__main__':
    sys.exit(main())
