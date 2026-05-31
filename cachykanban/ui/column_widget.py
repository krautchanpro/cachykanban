from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import (
    QAction, QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent,
)
from PySide6.QtWidgets import (
    QColorDialog, QFrame, QHBoxLayout, QInputDialog, QLabel, QMenu,
    QPushButton, QVBoxLayout, QWidget,
)

from ..controller import Controller
from ..models import Column
from .card_widget import CARD_MIME, CardWidget

COLUMN_MIME = "application/x-cachykanban-column"


class ColumnWidget(QFrame):
    """One column: header (name/color/count) + filtered card list + add-card."""

    cardClicked = Signal(str)       # card_id -> open editor
    changed = Signal()              # ask BoardView to rebuild

    def __init__(self, column: Column, controller: Controller, query: dict,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setAcceptDrops(True)
        self.column = column
        self.controller = controller
        self.query = query
        self.setFixedWidth(258)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        header = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{column.color};")
        title = QLabel(column.name)
        title.setObjectName("ColumnTitle")
        from ..search import visible_cards
        self._visible = visible_cards(
            column,
            text=query.get("text", ""),
            label_id=query.get("label_id"),
            priority=query.get("priority"),
        )
        count = QLabel(str(len(self._visible)))
        count.setObjectName("Muted")
        menu_btn = QPushButton("⋮")
        menu_btn.setFixedWidth(26)
        menu_btn.clicked.connect(self._open_menu)
        header.addWidget(dot)
        header.addWidget(title)
        header.addWidget(count)
        header.addStretch(1)
        header.addWidget(menu_btn)
        outer.addLayout(header)

        self._cards_box = QVBoxLayout()
        self._cards_box.setSpacing(8)
        self._cards_box.setContentsMargins(0, 0, 0, 0)
        for card in self._visible:
            widget = CardWidget(card, self.controller.board, column.id)
            widget.clicked.connect(self.cardClicked)
            self._cards_box.addWidget(widget)
        outer.addLayout(self._cards_box)

        add_btn = QPushButton("+ Add card")
        add_btn.clicked.connect(self._add_card)
        outer.addWidget(add_btn)
        outer.addStretch(1)

    # ---- header actions ---------------------------------------------------
    def _open_menu(self) -> None:
        menu = QMenu(self)
        rename = QAction("Rename column", self)
        rename.triggered.connect(self._rename)
        recolor = QAction("Change color", self)
        recolor.triggered.connect(self._recolor)
        delete = QAction("Delete column", self)
        delete.triggered.connect(self._delete)
        menu.addAction(rename)
        menu.addAction(recolor)
        menu.addSeparator()
        menu.addAction(delete)
        menu.exec(self.cursor().pos())

    def _rename(self) -> None:
        name, ok = QInputDialog.getText(self, "Rename column", "Name:", text=self.column.name)
        if ok and name.strip():
            self.controller.rename_column(self.column.id, name.strip())
            self.changed.emit()

    def _recolor(self) -> None:
        color = QColorDialog.getColor()
        if color.isValid():
            self.controller.recolor_column(self.column.id, color.name())
            self.changed.emit()

    def _delete(self) -> None:
        self.controller.delete_column(self.column.id)
        self.changed.emit()

    def _add_card(self) -> None:
        title, ok = QInputDialog.getText(self, "Add card", "Title:")
        if ok and title.strip():
            self.controller.add_card(self.column.id, title.strip())
            self.changed.emit()

    # ---- column drag source (from the header strip) -----------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._col_press = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        start = getattr(self, "_col_press", QPoint())
        if (event.position().toPoint() - start).manhattanLength() < 24:
            return
        # only start a column drag from the top header strip
        if event.position().toPoint().y() > 40:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(COLUMN_MIME, self.column.id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    # ---- drop target ------------------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(CARD_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not event.mimeData().hasFormat(CARD_MIME):
            return
        card_id = bytes(event.mimeData().data(CARD_MIME)).decode("utf-8")
        drop_y = event.position().toPoint().y()
        index = self._insertion_index(drop_y)
        self.controller.move_card(card_id, self.column.id, index)
        event.acceptProposedAction()
        self.changed.emit()

    def _insertion_index(self, drop_y: int) -> int:
        index = 0
        for i in range(self._cards_box.count()):
            item = self._cards_box.itemAt(i)
            widget = item.widget()
            if widget is None:
                continue
            center = widget.y() + widget.height() / 2
            if drop_y > center:
                index = i + 1
        return index
