from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog, QDialog, QHBoxLayout, QInputDialog, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from ..controller import Controller


class LabelManager(QDialog):
    """Manage the current board's label palette (add / recolor / delete)."""

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setWindowTitle("Labels")
        self.resize(320, 380)

        layout = QVBoxLayout(self)
        self.list = QListWidget()
        layout.addWidget(self.list)

        add_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("New label name")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        add_row.addWidget(self.name_edit)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        actions = QHBoxLayout()
        recolor = QPushButton("Recolor selected")
        recolor.clicked.connect(self._recolor)
        delete = QPushButton("Delete selected")
        delete.clicked.connect(self._delete)
        actions.addWidget(recolor)
        actions.addWidget(delete)
        layout.addLayout(actions)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close)

        self.reload()

    def reload(self) -> None:
        self.list.clear()
        for label in self.controller.board.labels:
            item = QListWidgetItem(label.name)
            item.setData(Qt.ItemDataRole.UserRole, label.id)
            item.setForeground(Qt.GlobalColor.black)
            item.setBackground(_qcolor(label.color))
            self.list.addItem(item)

    def _selected_id(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add(self) -> None:
        name = self.name_edit.text().strip()
        if name:
            self.controller.add_label(name, "#6ea8fe")
            self.name_edit.clear()
            self.reload()

    def _recolor(self) -> None:
        label_id = self._selected_id()
        if not label_id:
            return
        label = self.controller.board.find_label(label_id)
        color = QColorDialog.getColor()
        if color.isValid() and label is not None:
            self.controller.update_label(label_id, label.name, color.name())
            self.reload()

    def _delete(self) -> None:
        label_id = self._selected_id()
        if label_id:
            self.controller.delete_label(label_id)
            self.reload()


def _qcolor(hex_color: str):
    from PySide6.QtGui import QColor
    return QColor(hex_color)
