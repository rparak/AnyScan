## =========================================================================== ##
# MIT License
# Copyright (c) 2025 JIC Smart Factory
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
# File Name: ../Parameters/General.py
## =========================================================================== ##

# Description:
#   Initialization of constants.
#
#   General (non-camera, non-vision) project settings read from the 'General' block of the
#   configuration file. Qt-free and dependency-free, so both the configuration layer and the UI
#   read these from ONE place — no literal default duplicated across modules.

# Whether the verdict UI is shown when a view is built without being told: no. A configuration
# classifies exactly when it is a catalogue mode (Configuration_Str.Classifies); the window passes
# that to each view, and this is only the views' default before it does. The configuration switch
# that once set it, General.Classification.Enabled, is removed (design-decisions.md).
#   Unit [bool]
CONST_CLASSIFICATION_ENABLED_DEFAULT = False
