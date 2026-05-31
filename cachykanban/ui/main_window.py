from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLineEdit, QMainWindow, QPushButton,
    QVBoxLayout, QWidget,
)

from ..controller import Controller
from ..models import PRIORITIES
from . import theme
from .board_view import BoardView
from .card_editor import CardEditor
from .label_manager import LabelManager
from .sidebar import Sidebar


class MainWindow(QMainWindow):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("CachyKanban")
        self.resize(1180, 760)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(controller)
        self.sidebar.boardSelected.connect(self._open_board)
        self.sidebar.changed.connect(self._refresh_board)
        root.addWidget(self.sidebar)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self._build_toolbar())

        self.board_view = BoardView(controller)
        self.board_view.cardClicked.connect(self._edit_card)
        right_layout.addWidget(self.board_view)
        root.addWidget(right, 1)

        self.setCentralWidget(central)
        self._install_shortcuts()

    # ---- toolbar / search -------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 6)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search cards…  (Ctrl+K)")
        self.search_edit.textChanged.connect(self._apply_query)
        layout.addWidget(self.search_edit, 1)

        self.priority_filter = QComboBox()
        self.priority_filter.addItem("Any priority", None)
        for p in PRIORITIES[1:]:
            self.priority_filter.addItem(p, p)
        self.priority_filter.currentIndexChanged.connect(self._apply_query)
        layout.addWidget(self.priority_filter)

        labels_btn = QPushButton("Labels…")
        labels_btn.clicked.connect(self._manage_labels)
        layout.addWidget(labels_btn)

        self.theme_box = QComboBox()
        self.theme_box.addItems(list(theme.THEMES))
        self.theme_box.setCurrentText(self.controller.theme_name)
        self.theme_box.currentTextChanged.connect(self._change_theme)
        layout.addWidget(self.theme_box)
        return bar

    def _apply_query(self) -> None:
        self.board_view.set_query({
            "text": self.search_edit.text().strip(),
            "label_id": None,
            "priority": self.priority_filter.currentData(),
        })

    # ---- actions ----------------------------------------------------------
    def _open_board(self, board_id: str) -> None:
        self.controller.open_board(board_id)
        self._refresh_board()

    def _refresh_board(self) -> None:
        # Defer the board rebuild: this is often called from a card's own
        # event handler (e.g. after the modal card editor closes, while the
        # originating CardWidget's mouseReleaseEvent is still on the stack).
        # Destroying that widget synchronously is a use-after-free.
        self.board_view.schedule_rebuild()
        self.sidebar.reload()

    def _edit_card(self, card_id: str) -> None:
        dialog = CardEditor(card_id, self.controller, self)
        if dialog.exec():
            self._refresh_board()

    def _manage_labels(self) -> None:
        LabelManager(self.controller, self).exec()
        self._refresh_board()

    def _change_theme(self, name: str) -> None:
        self.controller.set_theme(name)
        QApplication.instance().setStyleSheet(theme.qss(name))

    # ---- shortcuts --------------------------------------------------------
    def _install_shortcuts(self) -> None:
        focus_search = QAction(self)
        focus_search.setShortcut(QKeySequence("Ctrl+K"))
        focus_search.triggered.connect(lambda: self.search_edit.setFocus())
        self.addAction(focus_search)

        add_column = QAction(self)
        add_column.setShortcut(QKeySequence("Ctrl+Shift+N"))
        add_column.triggered.connect(self.board_view._add_column)
        self.addAction(add_column)
