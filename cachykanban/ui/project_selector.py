from __future__ import annotations

from PySide6.QtCore import Signal, Qt
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
    """Compact project switcher and management controls for the toolbar."""

    projectSelected = Signal(str)
    changed = Signal()
    _ADD_PROJECT = "__add_project__"

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setObjectName("ProjectSelector")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.project_box = QComboBox()
        self.project_box.setObjectName("ProjectSelectorBox")
        self.project_box.setMinimumWidth(190)
        self.project_box.currentIndexChanged.connect(self._on_project_changed)
        layout.addWidget(self.project_box)

        self.manage_button = QToolButton()
        self.manage_button.setText("⋮")
        self.manage_button.setToolTip("Manage current project")
        self.manage_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.manage_button.setMenu(QMenu(self.manage_button))
        self.manage_button.menu().aboutToShow.connect(self._populate_menu)
        layout.addWidget(self.manage_button)

        self._last_index = -1
        self.reload()

    def reload(self) -> None:
        """Refresh projects while keeping combo-box signals single-fire."""
        current_id = self.controller.board.id if self.controller.board else self.controller.active_project_id
        self.project_box.blockSignals(True)
        try:
            self.project_box.clear()
            selected = -1
            for summary in self.controller.summaries:
                index = self.project_box.count()
                self.project_box.addItem(summary["name"], summary["id"])
                self.project_box.setItemData(index, summary["color"], Qt.ItemDataRole.UserRole + 1)
                if summary["id"] == current_id:
                    selected = index
            self.project_box.addItem("＋ Add project…", self._ADD_PROJECT)
            if selected < 0 and self.project_box.count() > 1:
                selected = 0
            self.project_box.setCurrentIndex(selected)
            self._last_index = selected
        finally:
            self.project_box.blockSignals(False)

    def _on_project_changed(self, index: int) -> None:
        project_id = self.project_box.itemData(index)
        if project_id == self._ADD_PROJECT:
            self._add_project()
            return
        if not isinstance(project_id, str) or not project_id:
            return
        self._last_index = index
        self.projectSelected.emit(project_id)

    def _restore_last_index(self) -> None:
        self.project_box.blockSignals(True)
        try:
            self.project_box.setCurrentIndex(self._last_index)
        finally:
            self.project_box.blockSignals(False)

    def _add_project(self) -> None:
        name, ok = QInputDialog.getText(self, "New project", "Name:")
        if not ok or not name.strip():
            self._restore_last_index()
            return
        project = self.controller.add_project(name.strip())
        self.reload()
        self.projectSelected.emit(project.id)

    def _populate_menu(self) -> None:
        menu = self.manage_button.menu()
        menu.clear()
        add = QAction("Add project…", self)
        add.triggered.connect(self._add_project)
        menu.addAction(add)
        project = self.controller.board
        if project is None:
            return
        menu.addSeparator()
        rename = QAction("Rename project…", self)
        rename.triggered.connect(lambda: self._rename(project.id, project.name))
        recolor = QAction("Change color…", self)
        recolor.triggered.connect(lambda: self._recolor(project.id))
        delete = QAction("Delete project", self)
        delete.triggered.connect(lambda: self._delete(project.id))
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)

    def _rename(self, project_id: str, current: str) -> None:
        name, ok = QInputDialog.getText(self, "Rename project", "Name:", text=current)
        if ok and name.strip():
            self.controller.rename_board(project_id, name.strip())
            self.reload()
            self.changed.emit()

    def _recolor(self, project_id: str) -> None:
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            self.controller.recolor_board(project_id, color.name())
            self.reload()
            self.changed.emit()

    def _delete(self, project_id: str) -> None:
        self.controller.delete_board(project_id)
        self.reload()
        self.changed.emit()
