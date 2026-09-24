## =========================================================================== ##
# MIT License
# Copyright (c) 2026 JIC Smart Factory
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
# Author   : JIC Smart Factory
# File Name: ../Example/<Domain>/<script>.py
## =========================================================================== ##

# System (Default)
import sys
#   Add access if it is not in the system path.
if '../../' + 'src' not in sys.path:
    sys.path.append('../../' + 'src')
# Argparse (Command-line parsing)
import argparse
# Custom Lib.:
#   ../Configuration/Core — the one configuration layer
from Configuration.Core import Load_Configuration, Configuration_Error_Cls, CONST_DEFAULT_CONFIG_FILE

"""
Description:
    Initialization of constants.
"""
# <What the constant means and why.>
#   Unit [int]
CONST_THING_COUNT = 1


def main():
    """
    Description:
        <What the script does, and — if it captures or renders what the application does — that it
        goes through the application's own path.>

            python <script>.py --config <mode file>
    """

    parser = argparse.ArgumentParser(description='<One line.>')
    parser.add_argument('--config', default=CONST_DEFAULT_CONFIG_FILE, help='the configuration (default: %(default)s)')
    args = parser.parse_args()

    try:
        configuration = Load_Configuration(args.config)
    except Configuration_Error_Cls as error:
        print('[ERROR] %s' % error)
        return 1
    for level, message in configuration.Notes:
        print('[%s] %s' % (level, message))

    print('[INFO] <What was done.>')
    return 0


if __name__ == '__main__':
    sys.exit(main())
