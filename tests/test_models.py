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


class BoardTests(unittest.TestCase):
    def _board(self):
        from cachykanban.models import Board, Column, Card, Label
        return Board(
            id="brd00001",
            name="SeedsOfAdventure",
            color="#6ea8fe",
            columns=[
                Column(id="col1", name="Backlog", color="#7c8596",
                       cards=[Card(id="c1", title="one")]),
                Column(id="col2", name="Done", color="#48bb78",
                       cards=[Card(id="c2", title="two")]),
            ],
            labels=[Label(id="l1", name="bug", color="#fc8181")],
        )

    def test_round_trip(self):
        from cachykanban.models import Board
        board = self._board()
        self.assertEqual(Board.from_dict(board.to_dict()), board)

    def test_find_column(self):
        board = self._board()
        self.assertEqual(board.find_column("col2").name, "Done")
        self.assertIsNone(board.find_column("nope"))

    def test_find_card_returns_column_and_card(self):
        board = self._board()
        col, card = board.find_card("c2")
        self.assertEqual(col.id, "col2")
        self.assertEqual(card.title, "two")

    def test_find_card_missing_returns_none(self):
        self.assertIsNone(self._board().find_card("ghost"))

    def test_summary(self):
        self.assertEqual(
            self._board().summary(),
            {"id": "brd00001", "name": "SeedsOfAdventure", "color": "#6ea8fe"},
        )


if __name__ == "__main__":
    unittest.main()
