import tempfile
import unittest
from pathlib import Path

from cachykanban.controller import Controller, DEFAULT_COLUMNS
from cachykanban.store import Store


def make_controller(tmp):
    store = Store(base=Path(tmp))
    controller = Controller(store)
    controller.now = lambda: "2026-05-31T12:00:00"  # deterministic timestamps
    controller.load()
    return controller


class LoadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_first_load_creates_one_default_board(self):
        c = make_controller(self._tmp.name)
        self.assertEqual(len(c.summaries), 1)
        self.assertIsNotNone(c.board)
        self.assertEqual([col.name for col in c.board.columns], list(DEFAULT_COLUMNS))

    def test_reload_reopens_persisted_board(self):
        c = make_controller(self._tmp.name)
        first_id = c.board.id
        c.add_card(c.board.columns[0].id, "remember me")
        c2 = make_controller(self._tmp.name)
        self.assertEqual(c2.board.id, first_id)
        titles = [card.title for card in c2.board.columns[0].cards]
        self.assertIn("remember me", titles)


class MutationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.c = make_controller(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_board_appends_and_persists_summary(self):
        board = self.c.add_board("Second", "#48bb78")
        self.assertIn(board.id, [s["id"] for s in self.c.summaries])
        self.assertTrue(self.c.store.board_exists(board.id))

    def test_rename_and_recolor_board(self):
        bid = self.c.board.id
        self.c.rename_board(bid, "Renamed")
        self.c.recolor_board(bid, "#000000")
        summary = next(s for s in self.c.summaries if s["id"] == bid)
        self.assertEqual(summary["name"], "Renamed")
        self.assertEqual(summary["color"], "#000000")

    def test_delete_board_removes_file_and_summary(self):
        extra = self.c.add_board("Temp", "#fff")
        self.c.delete_board(extra.id)
        self.assertNotIn(extra.id, [s["id"] for s in self.c.summaries])
        self.assertFalse(self.c.store.board_exists(extra.id))

    def test_add_rename_delete_column(self):
        col = self.c.add_column("Review", "#b794f6")
        self.assertIn(col.id, [x.id for x in self.c.board.columns])
        self.c.rename_column(col.id, "QA")
        self.assertEqual(self.c.board.find_column(col.id).name, "QA")
        self.c.delete_column(col.id)
        self.assertIsNone(self.c.board.find_column(col.id))

    def test_add_card_sets_timestamps(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "new task")
        self.assertEqual(card.created, "2026-05-31T12:00:00")
        self.assertEqual(card.updated, "2026-05-31T12:00:00")

    def test_update_card_changes_fields_and_updated(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        self.c.update_card(card.id, title="edited", priority="high")
        _, fresh = self.c.board.find_card(card.id)
        self.assertEqual(fresh.title, "edited")
        self.assertEqual(fresh.priority, "high")

    def test_archive_card(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        self.c.set_card_archived(card.id, True)
        _, fresh = self.c.board.find_card(card.id)
        self.assertTrue(fresh.archived)

    def test_delete_card(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        self.c.delete_card(card.id)
        self.assertIsNone(self.c.board.find_card(card.id))

    def test_add_label_and_delete_removes_from_cards(self):
        col_id = self.c.board.columns[0].id
        card = self.c.add_card(col_id, "task")
        label = self.c.add_label("bug", "#fc8181")
        self.c.update_card(card.id, label_ids=[label.id])
        self.c.delete_label(label.id)
        self.assertNotIn(label, self.c.board.labels)
        _, fresh = self.c.board.find_card(card.id)
        self.assertEqual(fresh.label_ids, [])


class MoveCardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.c = make_controller(self._tmp.name)
        self.col_a = self.c.board.columns[0].id
        self.col_b = self.c.board.columns[1].id
        self.k1 = self.c.add_card(self.col_a, "one").id
        self.k2 = self.c.add_card(self.col_a, "two").id
        self.k3 = self.c.add_card(self.col_a, "three").id

    def tearDown(self):
        self._tmp.cleanup()

    def _titles(self, col_id):
        return [card.title for card in self.c.board.find_column(col_id).cards]

    def test_reorder_within_column(self):
        self.c.move_card(self.k3, self.col_a, 0)
        self.assertEqual(self._titles(self.col_a), ["three", "one", "two"])

    def test_move_across_columns_at_index(self):
        self.c.move_card(self.k1, self.col_b, 0)
        self.assertEqual(self._titles(self.col_a), ["two", "three"])
        self.assertEqual(self._titles(self.col_b), ["one"])

    def test_index_is_clamped(self):
        self.c.move_card(self.k1, self.col_b, 999)
        self.assertEqual(self._titles(self.col_b), ["one"])


if __name__ == "__main__":
    unittest.main()
