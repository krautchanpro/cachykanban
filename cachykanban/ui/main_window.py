from __future__ import annotations

from PySide6.QtCore import QFileSystemWatcher, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLineEdit, QMainWindow, QPushButton,
    QVBoxLayout, QWidget,
)

from ..controller import Controller
from ..models import PRIORITIES, Project
from ..store import StoreError
from . import theme
from .board_view import BoardView
from .card_editor import CardEditor
from .label_manager import LabelManager
from .project_selector import ProjectSelector


class MainWindow(QMainWindow):
    def __init__(self, controller: Controller) -> None:
        super().__init__()
        self.controller = controller
        self.setWindowTitle("CachyKanban")
        self.resize(1180, 760)

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())

        self.board_view = BoardView(controller)
        self.board_view.cardClicked.connect(self._edit_card)
        root.addWidget(self.board_view, 1)

        self.setCentralWidget(central)
        self._install_shortcuts()
        self._install_external_change_monitor()

    # ---- toolbar / search -------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("Toolbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 6)

        self.project_selector = ProjectSelector(self.controller)
        # Convenience alias for integrations/tests that need the native combo.
        self.project_box = self.project_selector.project_box
        self.board_box = self.project_selector.board_box
        self.project_selector.projectSelected.connect(self._open_project)
        self.project_selector.boardSelected.connect(self._open_board)
        self.project_selector.changed.connect(self._refresh_board)
        layout.addWidget(self.project_selector)

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
    def _open_project(self, project_id: str) -> None:
        self.controller.open_project(project_id)
        self._refresh_board()

    def _open_board(self, board_id: str) -> None:
        self.controller.open_board(board_id)
        self._refresh_board()

    def _refresh_board(self) -> None:
        # Defer the board rebuild: this is often called from a card's own
        # event handler (e.g. after the modal card editor closes, while the
        # originating CardWidget's mouseReleaseEvent is still on the stack).
        # Destroying that widget synchronously is a use-after-free.
        self.board_view.schedule_rebuild()
        self.project_selector.reload()

    # ---- web/desktop synchronization ------------------------------------
    def _install_external_change_monitor(self) -> None:
        """Reload card changes written by the companion web service.

        Store writes use atomic replacement, so watching only individual JSON
        files is unreliable on Linux. Watch both containing directories and
        keep a low-frequency poll as a fallback for coalesced/missed events.
        """
        store = self.controller.store
        store.base.mkdir(parents=True, exist_ok=True)
        store.projects_dir.mkdir(parents=True, exist_ok=True)
        self._store_watcher = QFileSystemWatcher(
            [str(store.base), str(store.projects_dir)], self
        )
        self._store_watcher.directoryChanged.connect(self._schedule_external_reload)

        self._external_reload_timer = QTimer(self)
        self._external_reload_timer.setSingleShot(True)
        self._external_reload_timer.setInterval(250)
        self._external_reload_timer.timeout.connect(self._reload_external_changes)

        self._external_poll_timer = QTimer(self)
        self._external_poll_timer.setInterval(2000)
        self._external_poll_timer.timeout.connect(self._reload_external_changes)
        self._external_poll_timer.start()

    def _schedule_external_reload(self, _path: str = "") -> None:
        self._external_reload_timer.start()

    @staticmethod
    def _project_content(project: Project) -> dict[str, object]:
        """Return content relevant to an open desktop view.

        Active selections and timestamps are intentionally ignored: opening
        the web page updates those bookkeeping fields but should not make the
        desktop redraw. Card, column, board, or label edits still compare
        unequal and trigger a reload.
        """
        data = project.to_dict()
        data.pop("updated", None)
        data.pop("active_board_id", None)
        for board in data.get("boards", []):
            board.pop("updated", None)
        return data

    def _disk_content_changed(self) -> bool:
        store = self.controller.store
        disk_index = store.load_index()
        disk_projects = disk_index.get("projects", [])
        if disk_projects != self.controller.index.get("projects", []):
            return True
        if disk_index.get("theme", "dark") != self.controller.theme_name:
            return True
        project = self.controller.project
        if project is None:
            return bool(disk_projects)
        try:
            disk_project = store.load_project(project.id)
        except StoreError:
            return True
        return self._project_content(disk_project) != self._project_content(project)

    def _reload_external_changes(self) -> None:
        if QApplication.activeModalWidget() is not None:
            # Avoid replacing model objects underneath an open card/label
            # editor. Retry shortly after the modal dialog closes.
            self._external_reload_timer.start(1000)
            return
        if not self._disk_content_changed():
            return

        project_id = self.controller.project.id if self.controller.project else None
        board_id = self.controller.board.id if self.controller.board else None
        self.controller.load()
        available_projects = {item["id"] for item in self.controller.summaries}
        if project_id in available_projects:
            self.controller.open_project(project_id, board_id)

        self.theme_box.blockSignals(True)
        self.theme_box.setCurrentText(self.controller.theme_name)
        self.theme_box.blockSignals(False)
        QApplication.instance().setStyleSheet(theme.qss(self.controller.theme_name))
        self._refresh_board()

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
