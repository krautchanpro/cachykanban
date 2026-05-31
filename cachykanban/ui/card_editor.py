from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget,
    QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from ..controller import Controller
from ..models import PRIORITIES, Card, ChecklistItem


class CardEditor(QDialog):
    """Modal editor for a single card. Applies changes via the controller."""

    def __init__(self, card_id: str, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.card_id = card_id
        found = controller.board.find_card(card_id)
        if found is None:
            raise KeyError(card_id)
        _, self.card = found
        self.setWindowTitle("Edit card")
        self.resize(460, 560)

        layout = QVBoxLayout(self)

        self.title_edit = QLineEdit(self.card.title)
        layout.addWidget(QLabel("Title"))
        layout.addWidget(self.title_edit)

        # notes with edit/preview tabs (Qt renders markdown natively)
        tabs = QTabWidget()
        self.notes_edit = QTextEdit(self.card.notes)
        preview = QTextBrowser()
        preview.setMarkdown(self.card.notes)
        self.notes_edit.textChanged.connect(lambda: preview.setMarkdown(self.notes_edit.toPlainText()))
        tabs.addTab(self.notes_edit, "Notes")
        tabs.addTab(preview, "Preview")
        layout.addWidget(QLabel("Notes (markdown)"))
        layout.addWidget(tabs)

        # priority
        prio_row = QHBoxLayout()
        prio_row.addWidget(QLabel("Priority"))
        self.priority_box = QComboBox()
        self.priority_box.addItems(PRIORITIES)
        self.priority_box.setCurrentText(self.card.priority)
        prio_row.addWidget(self.priority_box)
        prio_row.addStretch(1)
        layout.addLayout(prio_row)

        # labels as checkboxes
        layout.addWidget(QLabel("Labels"))
        self.label_boxes: list[tuple[str, QCheckBox]] = []
        labels_row = QHBoxLayout()
        for label in controller.board.labels:
            box = QCheckBox(label.name)
            box.setChecked(label.id in self.card.label_ids)
            self.label_boxes.append((label.id, box))
            labels_row.addWidget(box)
        labels_row.addStretch(1)
        layout.addLayout(labels_row)

        # checklist
        layout.addWidget(QLabel("Checklist"))
        self.checklist = QListWidget()
        for item in self.card.checklist:
            self._add_checklist_row(item.text, item.done)
        layout.addWidget(self.checklist)
        cl_row = QHBoxLayout()
        add_item = QPushButton("+ Add item")
        add_item.clicked.connect(self._add_checklist_item)
        rm_item = QPushButton("Remove selected")
        rm_item.clicked.connect(self._remove_checklist_item)
        cl_row.addWidget(add_item)
        cl_row.addWidget(rm_item)
        cl_row.addStretch(1)
        layout.addLayout(cl_row)

        # bottom: archive + ok/cancel
        bottom = QHBoxLayout()
        self.archive_btn = QPushButton("Unarchive" if self.card.archived else "Archive")
        self.archive_btn.clicked.connect(self._toggle_archive)
        bottom.addWidget(self.archive_btn)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)

    def _add_checklist_row(self, text: str, done: bool) -> None:
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked if done else Qt.CheckState.Unchecked)
        self.checklist.addItem(item)

    def _add_checklist_item(self) -> None:
        text, ok = QInputDialog.getText(self, "Checklist item", "Text:")
        if ok and text.strip():
            self._add_checklist_row(text.strip(), False)

    def _remove_checklist_item(self) -> None:
        row = self.checklist.currentRow()
        if row >= 0:
            self.checklist.takeItem(row)

    def _toggle_archive(self) -> None:
        self.card.archived = not self.card.archived
        self.archive_btn.setText("Unarchive" if self.card.archived else "Archive")

    def _save(self) -> None:
        checklist = []
        for i in range(self.checklist.count()):
            item = self.checklist.item(i)
            checklist.append(ChecklistItem(item.text(), item.checkState() == Qt.CheckState.Checked))
        label_ids = [lid for lid, box in self.label_boxes if box.isChecked()]
        self.controller.update_card(
            self.card_id,
            title=self.title_edit.text().strip() or "Untitled",
            notes=self.notes_edit.toPlainText(),
            priority=self.priority_box.currentText(),
            label_ids=label_ids,
            checklist=checklist,
            archived=self.card.archived,
        )
        self.accept()
