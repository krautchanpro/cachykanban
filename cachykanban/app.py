from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import __version__
from .controller import Controller
from .store import Store
from .ui import MainWindow
from .ui import theme


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("CachyKanban")
    app.setApplicationDisplayName("CachyKanban")
    app.setApplicationVersion(__version__)

    controller = Controller(Store())
    controller.load()
    app.setStyleSheet(theme.qss(controller.theme_name))

    window = MainWindow(controller)
    window.show()
    return app.exec()
