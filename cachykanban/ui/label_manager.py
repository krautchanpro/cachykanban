from __future__ import annotations

from PySide6.QtWidgets import (
    QColorDialog, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from ..controller import Controller


def _contrast_ink(hex_color: str) -> str:
    """Near-black or near-white text, whichever reads better on hex_color."""
    color = QColor(hex_color)
    lum = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
    return "#0c0d10" if lum > 0.6 else "#f2f4f8"


def _chip(name: str, hex_color: str) -> QWidget:
    """A pill showing the label name on its own color, with readable text.

    Rendered as a real widget (placed via setItemWidget) rather than relying on
    QListWidgetItem background/foreground roles, because the app's QSS styles
    QListWidget::item and that makes Qt ignore those per-item roles.
    """
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(6, 3, 6, 3)
    chip = QLabel(name)
    chip.setStyleSheet(
        f"background:{hex_color}; color:{_contrast_ink(hex_color)};"
        "border-radius:9px; padding:2px 12px; font-weight:600;"
    )
    row.addWidget(chip)
    row.addStretch(1)
    return holder


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
        self.name_edit.returnPressed.connect(self._add)
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
        selected = self._selected_id()
        self.list.clear()
        for label in self.controller.board.labels:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, label.id)
            self.list.addItem(item)
            widget = _chip(label.name, label.color)
            item.setSizeHint(widget.sizeHint())
            self.list.setItemWidget(item, widget)
            if label.id == selected:
                self.list.setCurrentItem(item)

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
        if label is None:
            return
        color = QColorDialog.getColor(QColor(label.color), self, "Recolor label")
        if color.isValid():
            self.controller.update_label(label_id, label.name, color.name())
            self.reload()

    def _delete(self) -> None:
        label_id = self._selected_id()
        if label_id:
            self.controller.delete_label(label_id)
            self.reload()
