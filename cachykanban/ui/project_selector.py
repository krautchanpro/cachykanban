from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QToolButton,
    QWidget,
)

from ..controller import Controller


class ProjectSelector(QWidget):
    """Compact project and board switchers for the top-left toolbar."""

    projectSelected = Signal(str)
    boardSelected = Signal(str)
    changed = Signal()
    _ADD_PROJECT = "__add_project__"
    _ADD_BOARD = "__add_board__"

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setObjectName("ProjectSelector")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.project_box = QComboBox()
        self.project_box.setObjectName("ProjectSelectorBox")
        self.project_box.setMinimumWidth(170)
        self.project_box.currentIndexChanged.connect(self._on_project_changed)
        layout.addWidget(self.project_box)

        self.project_manage_button = self._menu_button("Manage project")
        self.project_manage_button.menu().aboutToShow.connect(self._populate_project_menu)
        layout.addWidget(self.project_manage_button)

        self.board_box = QComboBox()
        self.board_box.setObjectName("BoardSelectorBox")
        self.board_box.setMinimumWidth(150)
        self.board_box.currentIndexChanged.connect(self._on_board_changed)
        layout.addWidget(self.board_box)

        self.board_manage_button = self._menu_button("Manage board")
        self.board_manage_button.menu().aboutToShow.connect(self._populate_board_menu)
        layout.addWidget(self.board_manage_button)

        # Compatibility alias for code that used one management control.
        self.manage_button = self.project_manage_button
        self._project_last_index = -1
        self._board_last_index = -1
        self.reload()

    @staticmethod
    def _menu_button(tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setText("⋮")
        button.setToolTip(tooltip)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(QMenu(button))
        return button

    def reload(self) -> None:
        """Refresh both selectors without generating switch events."""
        project_id = self.controller.project.id if self.controller.project else self.controller.active_project_id
        board_id = self.controller.board.id if self.controller.board else self.controller.active_board_id

        self.project_box.blockSignals(True)
        self.board_box.blockSignals(True)
        try:
            self.project_box.clear()
            selected_project = -1
            for summary in self.controller.summaries:
                index = self.project_box.count()
                self.project_box.addItem(summary["name"], summary["id"])
                self.project_box.setItemData(index, summary["color"], Qt.ItemDataRole.UserRole + 1)
                if summary["id"] == project_id:
                    selected_project = index
            self.project_box.addItem("＋ Add project…", self._ADD_PROJECT)
            if selected_project < 0 and self.project_box.count() > 1:
                selected_project = 0
            self.project_box.setCurrentIndex(selected_project)
            self._project_last_index = selected_project

            self.board_box.clear()
            selected_board = -1
            for summary in self.controller.board_summaries:
                index = self.board_box.count()
                self.board_box.addItem(summary["name"], summary["id"])
                self.board_box.setItemData(index, summary["color"], Qt.ItemDataRole.UserRole + 1)
                if summary["id"] == board_id:
                    selected_board = index
            self.board_box.addItem("＋ Add board…", self._ADD_BOARD)
            if selected_board < 0 and self.board_box.count() > 1:
                selected_board = 0
            self.board_box.setCurrentIndex(selected_board)
            self._board_last_index = selected_board
        finally:
            self.board_box.blockSignals(False)
            self.project_box.blockSignals(False)

    def _on_project_changed(self, index: int) -> None:
        project_id = self.project_box.itemData(index)
        if project_id == self._ADD_PROJECT:
            self._add_project()
            return
        if isinstance(project_id, str) and project_id:
            self._project_last_index = index
            self.projectSelected.emit(project_id)

    def _on_board_changed(self, index: int) -> None:
        board_id = self.board_box.itemData(index)
        if board_id == self._ADD_BOARD:
            self._add_board()
            return
        if isinstance(board_id, str) and board_id:
            self._board_last_index = index
            self.boardSelected.emit(board_id)

    def _restore_project(self) -> None:
        self.project_box.blockSignals(True)
        try:
            self.project_box.setCurrentIndex(self._project_last_index)
        finally:
            self.project_box.blockSignals(False)

    def _restore_board(self) -> None:
        self.board_box.blockSignals(True)
        try:
            self.board_box.setCurrentIndex(self._board_last_index)
        finally:
            self.board_box.blockSignals(False)

    def _add_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Name:")
        if not ok or not name.strip():
            self._restore_project()
            return
        project = self.controller.add_project(name.strip())
        self.reload()
        # MainWindow performs the one corresponding open operation.
        self.projectSelected.emit(project.id)

    def _add_board(self) -> None:
        name, ok = QInputDialog.getText(self, "New board", "Name:")
        if not ok or not name.strip():
            self._restore_board()
            return
        board = self.controller.add_board(name.strip())
        self.reload()
        self.boardSelected.emit(board.id)

    def _populate_project_menu(self) -> None:
        menu = self.project_manage_button.menu()
        menu.clear()
        add = QAction("Add project…", self)
        add.triggered.connect(self._add_project)
        menu.addAction(add)
        project = self.controller.project
        if project is None:
            return
        menu.addSeparator()
        rename = QAction("Rename project…", self)
        rename.triggered.connect(lambda: self._rename_project(project.id, project.name))
        recolor = QAction("Change color…", self)
        recolor.triggered.connect(lambda: self._recolor_project(project.id))
        delete = QAction("Delete project", self)
        delete.triggered.connect(lambda: self._delete_project(project.id))
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)

    def _populate_board_menu(self) -> None:
        menu = self.board_manage_button.menu()
        menu.clear()
        add = QAction("Add board…", self)
        add.triggered.connect(self._add_board)
        menu.addAction(add)
        board = self.controller.board
        if board is None:
            return
        menu.addSeparator()
        rename = QAction("Rename board…", self)
        rename.triggered.connect(lambda: self._rename_board(board.id, board.name))
        recolor = QAction("Change color…", self)
        recolor.triggered.connect(lambda: self._recolor_board(board.id))
        delete = QAction("Delete board", self)
        delete.triggered.connect(lambda: self._delete_board(board.id))
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)

    def _rename_project(self, project_id: str, current: str) -> None:
        name, ok = QInputDialog.getText(self, "Rename project", "Name:", text=current)
        if ok and name.strip():
            self.controller.rename_project(project_id, name.strip())
            self.reload()
            self.changed.emit()

    def _recolor_project(self, project_id: str) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.controller.recolor_project(project_id, color.name())
            self.reload()
            self.changed.emit()

    def _delete_project(self, project_id: str) -> None:
        self.controller.delete_project(project_id)
        self.reload()
        self.changed.emit()

    def _rename_board(self, board_id: str, current: str) -> None:
        name, ok = QInputDialog.getText(self, "Rename board", "Name:", text=current)
        if ok and name.strip():
            self.controller.rename_board(board_id, name.strip())
            self.reload()
            self.changed.emit()

    def _recolor_board(self, board_id: str) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.controller.recolor_board(board_id, color.name())
            self.reload()
            self.changed.emit()

    def _delete_board(self, board_id: str) -> None:
        self.controller.delete_board(board_id)
        self.reload()
        self.changed.emit()

    # Old private names are kept as small compatibility shims for callers
    # that customized the original project-only selector.
    _rename = _rename_project
    _recolor = _recolor_project
    _delete = _delete_project
