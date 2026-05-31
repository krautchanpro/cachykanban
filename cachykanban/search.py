from __future__ import annotations

from .models import Card, Column
from .models import PRIORITIES


def priority_rank(priority: str) -> int:
    try:
        return PRIORITIES.index(priority)
    except ValueError:
        return 0


def card_matches(
    card: Card,
    *,
    text: str = "",
    label_id: str | None = None,
    priority: str | None = None,
) -> bool:
    if text:
        needle = text.lower()
        if needle not in card.title.lower() and needle not in card.notes.lower():
            return False
    if label_id is not None and label_id not in card.label_ids:
        return False
    if priority is not None and card.priority != priority:
        return False
    return True


def visible_cards(
    column: Column,
    *,
    text: str = "",
    label_id: str | None = None,
    priority: str | None = None,
    include_archived: bool = False,
) -> list[Card]:
    result = []
    for card in column.cards:
        if card.archived and not include_archived:
            continue
        if card_matches(card, text=text, label_id=label_id, priority=priority):
            result.append(card)
    return result
