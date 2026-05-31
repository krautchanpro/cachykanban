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
