from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QColorDialog, QInputDialog, QListWidget, QListWidgetItem, QMenu,
    QPushButton, QVBoxLayout, QWidget,
)

from ..controller import Controller


class Sidebar(QWidget):
    """Board list with add/rename/recolor/delete. Emits the selected board id."""

    boardSelected = Signal(str)
    changed = Signal()

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setFixedWidth(210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 6, 12)
        layout.setSpacing(8)

        self.list = QListWidget()
        self.list.itemClicked.connect(self._on_click)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list)

        add_btn = QPushButton("+ New board")
        add_btn.clicked.connect(self._add_board)
        layout.addWidget(add_btn)

        self.reload()

    def reload(self) -> None:
        self.list.clear()
        current_id = self.controller.board.id if self.controller.board else None
        for summary in self.controller.summaries:
            item = QListWidgetItem(summary["name"])
            item.setData(Qt.ItemDataRole.UserRole, summary["id"])
            self.list.addItem(item)
            if summary["id"] == current_id:
                self.list.setCurrentItem(item)

    def _on_click(self, item: QListWidgetItem) -> None:
        self.boardSelected.emit(item.data(Qt.ItemDataRole.UserRole))

    def _add_board(self) -> None:
        name, ok = QInputDialog.getText(self, "New board", "Name:")
        if ok and name.strip():
            board = self.controller.add_board(name.strip(), "#6ea8fe")
            self.reload()
            self.boardSelected.emit(board.id)

    def _on_context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        board_id = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename = QAction("Rename", self)
        rename.triggered.connect(lambda: self._rename(board_id, item.text()))
        recolor = QAction("Change color", self)
        recolor.triggered.connect(lambda: self._recolor(board_id))
        delete = QAction("Delete", self)
        delete.triggered.connect(lambda: self._delete(board_id))
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self.list.mapToGlobal(pos))

    def _rename(self, board_id: str, current: str) -> None:
        name, ok = QInputDialog.getText(self, "Rename board", "Name:", text=current)
        if ok and name.strip():
            self.controller.rename_board(board_id, name.strip())
            self.reload()
            self.changed.emit()

    def _recolor(self, board_id: str) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self.controller.recolor_board(board_id, color.name())
            self.changed.emit()

    def _delete(self, board_id: str) -> None:
        self.controller.delete_board(board_id)
        self.reload()
        if self.controller.board:
            self.boardSelected.emit(self.controller.board.id)
        self.changed.emit()
