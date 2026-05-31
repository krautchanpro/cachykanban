from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDrag, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..models import Board, Card

CARD_MIME = "application/x-cachykanban-card"

_PRIORITY_COLOR = {"low": "#9aa3b2", "med": "#f6ad55", "high": "#fc8181"}


class CardWidget(QFrame):
    """One card. Click to edit; drag to move. Carries its card id in mime data."""

    clicked = Signal(str)   # card_id -> open editor
    dropHandled = Signal()  # emitted after this card's drag.exec() returns

    def __init__(self, card: Card, board: Board, column_id: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.card = card
        self.column_id = column_id
        self._press_pos = QPoint()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 9)
        layout.setSpacing(6)

        if card.label_ids:
            chips = QHBoxLayout()
            chips.setSpacing(5)
            chips.setContentsMargins(0, 0, 0, 0)
            for label_id in card.label_ids:
                label = board.find_label(label_id)
                if label is None:
                    continue
                chip = QLabel(label.name)
                chip.setStyleSheet(
                    f"background:{label.color}; color:#0c0d10; border-radius:8px;"
                    "padding:1px 7px; font-size:11px; font-weight:600;"
                )
                chips.addWidget(chip)
            chips.addStretch(1)
            holder = QWidget()
            holder.setLayout(chips)
            layout.addWidget(holder)

        title = QLabel(card.title)
        title.setWordWrap(True)
        layout.addWidget(title)

        meta_bits = []
        done, total = card.progress()
        if total:
            meta_bits.append(f"☑ {done}/{total}")
        if card.priority != "none":
            color = _PRIORITY_COLOR.get(card.priority, "#9aa3b2")
            meta_bits.append(f"<span style='color:{color}'>⚑ {card.priority}</span>")
        if meta_bits:
            meta = QLabel("  ·  ".join(meta_bits))
            meta.setObjectName("Muted")
            meta.setTextFormat(Qt.TextFormat.RichText)
            meta.setStyleSheet("font-size:11px;")
            layout.addWidget(meta)

    # ---- interaction ------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            moved = (event.position().toPoint() - self._press_pos).manhattanLength()
            if moved < 6:
                self.clicked.emit(self.card.id)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self._press_pos).manhattanLength() < 12:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(CARD_MIME, self.card.id.encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.exec(Qt.DropAction.MoveAction)
        # drag.exec() ran a nested event loop; it has now returned, so we are
        # back in the main loop and this widget is still alive. Announce the
        # finished drag so the board rebuild is triggered from OUTSIDE the
        # nested loop (deleting this widget from inside it is a use-after-free).
        self.dropHandled.emit()
