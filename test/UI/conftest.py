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
# File Name: ../test/UI/conftest.py
## =========================================================================== ##

# System (Default)
import os
# Qt must render headless; set the platform before any QApplication is constructed.
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
# Pytest (Testing framework) [pip3 install pytest]
import pytest
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtWidgets import QApplication
# Custom Lib.: AnyScan UI — the bundled fonts
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style

"""
Description:
    The UI tests' one QApplication, with the bundled fonts registered before any widget exists, in the order
    App/run.py starts the application. A module's own qt_app fixture then finds this instance.

    Why first: Qt caches the face it resolved for a font request. A request for 'Public Sans' made before the family
    is registered resolves to the platform's fallback, and the same request keeps resolving to it after
    Style.Load_Fonts registers the family (measured on macOS, Qt 5.15.14: 9 pt Bold asked before registration stays
    '.AppleSystemUIFont'; a size never asked before resolves to Public Sans). A module that built a widget before any
    module had loaded the fonts made a later font test fail only in the full run.
"""


@pytest.fixture(scope='session', autouse=True)
def ui_application() -> QApplication:
    """
    Description:
        The session's QApplication, its fonts loaded before any UI test runs.

    Returns:
        (1) parameter [QApplication(object)]: The application instance.
    """

    app = QApplication.instance() or QApplication([])
    Style.Load_Fonts()
    return app
