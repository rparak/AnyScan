## =========================================================================== ##
# MIT License
# Copyright (c) 2025 Roman Parak
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
# Author   : Roman Parak
# Email    : Roman.Parak@outlook.com
# Github   : https://github.com/rparak
# File Name: ../UI/Views/History.py
## =========================================================================== ##

# Typing (Support for type hints)
import typing as tp
# PyQt5 (Qt bindings) [pip3 install PyQt5]
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout
# Custom Lib.: AnyScan UI — design tokens and the shared card
#   ../UI/Utilities/Style
import UI.Utilities.Style as Style
from UI.Utilities.Style import Font
#   ../UI/Widgets
from UI.Widgets import Card_Cls

"""
Description:
    The History view — one of the three central views the header switch selects. It is a
    placeholder for now: a single centred, muted line saying the view is under development,
    and nothing else. It is built as a REAL view in its own module (not an inline label in
    the window) so filling it in later — a browser of past captures — is a change to this
    file, not a restructuring of the view switch.
"""


class History_View_Cls(Card_Cls):
    """
    Description:
        The History view's card: a centred, muted 'under development' message on the same
        white card the other views sit in, so the switch swaps one card look for another.
        It carries no state and updates nothing; when the real history browser is built it
        replaces the message inside this same class.
    """

    # The placeholder message, in the console's own voice.
    CONST_MESSAGE = 'History view — under development.'

    def __init__(self, parent: tp.Optional[QWidget] = None) -> None:
        super().__init__(parent=parent)

        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.addStretch(1)

        message = QLabel(self.CONST_MESSAGE)
        message.setFont(Font(12.5))
        message.setAlignment(Qt.AlignCenter)
        # The muted tone — this is an empty state, not content.
        message.setStyleSheet('color: %s;' % Style.CONST_INK_MUTE)
        column.addWidget(message)

        column.addStretch(1)
        self.box.addLayout(column, 1)
