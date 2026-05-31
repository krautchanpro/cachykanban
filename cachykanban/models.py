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
