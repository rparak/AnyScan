"""Shared fixtures for the JIC Smart Factory style tests: the package on the path and one offscreen QApplication."""
import os
import sys

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)

import pytest                                                            # noqa: E402
from PyQt5.QtCore import Qt                                              # noqa: E402
from PyQt5.QtWidgets import QApplication                                 # noqa: E402


@pytest.fixture(scope='session')
def qt_app() -> QApplication:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication.instance() or QApplication([])
    from JIC_SF_UI import Style
    Style.Load_Fonts()
    return app
