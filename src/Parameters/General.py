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

# Whether a configuration performs OK/NOK classification, or only detects objects. This is the
# SINGLE default: the configuration reader falls back to it when the 'General.Classification'
# block is absent, and the UI defaults to it when no flag is passed. It is False because nothing
# classifies today — no code assigns NOK — so a configuration that does not say otherwise shows
# detected objects only, with no verdict state anywhere in the UI. Enabling it exposes the
# verdict UI; it does NOT create classification (see docs/design-decisions.md).
#   Unit [bool]
CONST_CLASSIFICATION_ENABLED_DEFAULT = False
