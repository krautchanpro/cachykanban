import unittest

from cachykanban.models import ChecklistItem, Label, new_id, PRIORITIES


class HelperTests(unittest.TestCase):
    def test_new_id_is_unique_hex(self):
        a, b = new_id(), new_id()
        self.assertNotEqual(a, b)
        self.assertEqual(len(a), 8)
        int(a, 16)  # raises if not hex

    def test_priorities_constant(self):
        self.assertEqual(PRIORITIES, ("none", "low", "med", "high"))


class ChecklistItemTests(unittest.TestCase):
    def test_round_trip(self):
        item = ChecklistItem(text="write tests", done=True)
        self.assertEqual(ChecklistItem.from_dict(item.to_dict()), item)

    def test_from_dict_defaults(self):
        item = ChecklistItem.from_dict({})
        self.assertEqual(item.text, "")
        self.assertFalse(item.done)


class LabelTests(unittest.TestCase):
    def test_round_trip(self):
        label = Label(id="lbl12345", name="bug", color="#fc8181")
        self.assertEqual(Label.from_dict(label.to_dict()), label)

    def test_from_dict_generates_id_when_missing(self):
        label = Label.from_dict({"name": "idea", "color": "#6ea8fe"})
        self.assertTrue(label.id)
        self.assertEqual(label.name, "idea")


class CardTests(unittest.TestCase):
    def _card(self):
        from cachykanban.models import Card
        return Card(
            id="card0001",
            title="NPC idle animation",
            notes="wire into AnimationTree",
            label_ids=["lbl1", "lbl2"],
            checklist=[ChecklistItem("a", True), ChecklistItem("b", False)],
            priority="high",
            created="2026-05-31T00:00:00",
            updated="2026-05-31T00:00:00",
        )

    def test_round_trip(self):
        card = self._card()
        from cachykanban.models import Card
        self.assertEqual(Card.from_dict(card.to_dict()), card)

    def test_progress_counts_done_over_total(self):
        self.assertEqual(self._card().progress(), (1, 2))

    def test_progress_empty_checklist(self):
        from cachykanban.models import Card
        self.assertEqual(Card(id="c", title="t").progress(), (0, 0))

    def test_from_dict_clamps_unknown_priority_to_none(self):
        from cachykanban.models import Card
        card = Card.from_dict({"id": "c", "title": "t", "priority": "bogus"})
        self.assertEqual(card.priority, "none")


if __name__ == "__main__":
    unittest.main()
