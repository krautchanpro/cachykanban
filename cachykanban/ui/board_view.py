from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ..controller import Controller
from .column_widget import COLUMN_MIME, ColumnWidget


class BoardView(QScrollArea):
    """Horizontal area of columns for the current board. Rebuilds from model."""

    cardClicked = Signal(str)  # card_id

    def __init__(self, controller: Controller, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.query: dict = {"text": "", "label_id": None, "priority": None}
        self.setWidgetResizable(True)
        self.setAcceptDrops(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.rebuild()

    def set_query(self, query: dict) -> None:
        self.query = query
        self.rebuild()

    def rebuild(self) -> None:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        board = self.controller.board
        if board is not None:
            for column in board.columns:
                col_widget = ColumnWidget(column, self.controller, self.query)
                col_widget.cardClicked.connect(self.cardClicked)
                col_widget.changed.connect(self.rebuild)
                row.addWidget(col_widget)

        add_col = QPushButton("+ Add column")
        add_col.setFixedWidth(140)
        add_col.clicked.connect(self._add_column)
        holder = QVBoxLayout()
        holder.addWidget(add_col)
        holder.addStretch(1)
        wrap = QWidget()
        wrap.setLayout(holder)
        row.addWidget(wrap)

        self.setWidget(container)

    def _add_column(self) -> None:
        name, ok = QInputDialog.getText(self, "Add column", "Name:")
        if ok and name.strip():
            self.controller.add_column(name.strip())
            self.rebuild()

    # ---- column reorder drop ---------------------------------------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(COLUMN_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        if not event.mimeData().hasFormat(COLUMN_MIME):
            return
        board = self.controller.board
        if board is None:
            return
        moved_id = bytes(event.mimeData().data(COLUMN_MIME)).decode("utf-8")
        drop_x = event.position().toPoint().x() + self.horizontalScrollBar().value()
        order = [c.id for c in board.columns if c.id != moved_id]
        insert_at = self._column_index_at(drop_x, exclude=moved_id)
        order.insert(insert_at, moved_id)
        self.controller.reorder_columns(order)
        event.acceptProposedAction()
        self.rebuild()

    def _column_index_at(self, drop_x: int, exclude: str) -> int:
        board = self.controller.board
        index = 0
        x = 16
        for column in board.columns:
            if column.id == exclude:
                continue
            col_width = 258 + 12
            if drop_x > x + col_width / 2:
                index += 1
            x += col_width
        return index
