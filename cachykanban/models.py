from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

PRIORITIES: tuple[str, ...] = ("none", "low", "med", "high")


def new_id() -> str:
    """Short, unique identifier for boards/columns/cards/labels."""
    return uuid.uuid4().hex[:8]


@dataclass(slots=True)
class ChecklistItem:
    text: str
    done: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "done": self.done}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChecklistItem":
        return cls(text=str(data.get("text", "")), done=bool(data.get("done", False)))


@dataclass(slots=True)
class Label:
    id: str
    name: str
    color: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "color": self.color}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Label":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#888888")),
        )


@dataclass(slots=True)
class Card:
    id: str
    title: str
    notes: str = ""
    label_ids: list[str] = field(default_factory=list)
    checklist: list[ChecklistItem] = field(default_factory=list)
    priority: str = "none"
    archived: bool = False
    created: str = ""
    updated: str = ""

    def progress(self) -> tuple[int, int]:
        done = sum(1 for item in self.checklist if item.done)
        return done, len(self.checklist)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "notes": self.notes,
            "label_ids": list(self.label_ids),
            "checklist": [item.to_dict() for item in self.checklist],
            "priority": self.priority,
            "archived": self.archived,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Card":
        priority = str(data.get("priority", "none"))
        if priority not in PRIORITIES:
            priority = "none"
        return cls(
            id=str(data.get("id") or new_id()),
            title=str(data.get("title", "")),
            notes=str(data.get("notes", "")),
            label_ids=[str(x) for x in data.get("label_ids", [])],
            checklist=[ChecklistItem.from_dict(x) for x in data.get("checklist", [])],
            priority=priority,
            archived=bool(data.get("archived", False)),
            created=str(data.get("created", "")),
            updated=str(data.get("updated", "")),
        )


@dataclass(slots=True)
class Column:
    id: str
    name: str
    color: str = "#7c8596"
    cards: list[Card] = field(default_factory=list)

    def find_card(self, card_id: str) -> Card | None:
        for card in self.cards:
            if card.id == card_id:
                return card
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "cards": [card.to_dict() for card in self.cards],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Column":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#7c8596")),
            cards=[Card.from_dict(x) for x in data.get("cards", [])],
        )


@dataclass(slots=True)
class Board:
    id: str
    name: str
    color: str = "#6ea8fe"
    columns: list[Column] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    created: str = ""
    updated: str = ""

    def find_column(self, column_id: str) -> Column | None:
        for column in self.columns:
            if column.id == column_id:
                return column
        return None

    def find_card(self, card_id: str) -> tuple[Column, Card] | None:
        for column in self.columns:
            card = column.find_card(card_id)
            if card is not None:
                return column, card
        return None

    def find_label(self, label_id: str) -> Label | None:
        for label in self.labels:
            if label.id == label_id:
                return label
        return None

    def summary(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "color": self.color}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "columns": [column.to_dict() for column in self.columns],
            "labels": [label.to_dict() for label in self.labels],
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Board":
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#6ea8fe")),
            columns=[Column.from_dict(x) for x in data.get("columns", [])],
            labels=[Label.from_dict(x) for x in data.get("labels", [])],
            created=str(data.get("created", "")),
            updated=str(data.get("updated", "")),
        )


@dataclass(slots=True)
class Project:
    """A project and all of its boards.

    Projects are the persistence boundary.  A project file contains the
    complete board graph, so saving a project can never leave cards stranded
    in a separate board file.
    """

    id: str
    name: str
    color: str = "#6ea8fe"
    boards: list[Board] = field(default_factory=list)
    active_board_id: str | None = None
    created: str = ""
    updated: str = ""

    def find_board(self, board_id: str) -> Board | None:
        for board in self.boards:
            if board.id == board_id:
                return board
        return None

    @property
    def active_board(self) -> Board | None:
        if self.active_board_id:
            board = self.find_board(self.active_board_id)
            if board is not None:
                return board
        return self.boards[0] if self.boards else None

    # Transitional conveniences for integrations that used the old board
    # object returned by add_project(). New code should use ``active_board``.
    @property
    def columns(self) -> list[Column]:
        return self.active_board.columns if self.active_board else []

    @property
    def labels(self) -> list[Label]:
        return self.active_board.labels if self.active_board else []

    def summary(self) -> dict[str, str]:
        return {"id": self.id, "name": self.name, "color": self.color}

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 2,
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "boards": [board.to_dict() for board in self.boards],
            "active_board_id": self.active_board_id,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        raw_boards = data.get("boards", [])
        if not isinstance(raw_boards, list):
            raw_boards = []
        active = data.get("active_board_id")
        return cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name", "")),
            color=str(data.get("color", "#6ea8fe")),
            boards=[Board.from_dict(item) for item in raw_boards if isinstance(item, dict)],
            active_board_id=str(active) if active else None,
            created=str(data.get("created", "")),
            updated=str(data.get("updated", "")),
        )
