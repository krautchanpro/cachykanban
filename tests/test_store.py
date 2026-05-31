import json
import os
import tempfile
import unittest
from pathlib import Path

from cachykanban.store import Store, StoreError, SCHEMA_VERSION
from cachykanban.models import Board, Column, Card


class PathTests(unittest.TestCase):
    def test_base_defaults_under_data_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["XDG_DATA_HOME"] = tmp
            store = Store()
            self.assertEqual(store.base, Path(tmp) / "cachykanban")
            del os.environ["XDG_DATA_HOME"]

    def test_explicit_base_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(base=Path(tmp) / "kb")
            self.assertEqual(store.base, Path(tmp) / "kb")
            self.assertEqual(store.boards_dir, Path(tmp) / "kb" / "boards")
            self.assertEqual(store.index_path, Path(tmp) / "kb" / "index.json")


class BoardIOTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(base=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _board(self):
        return Board(id="b1", name="B", color="#fff",
                     columns=[Column(id="c1", name="Todo", cards=[Card(id="k1", title="x")])])

    def test_save_then_load_round_trips(self):
        board = self._board()
        self.store.save_board(board)
        self.assertEqual(self.store.load_board("b1"), board)

    def test_save_writes_no_leftover_tmp_file(self):
        self.store.save_board(self._board())
        leftovers = list(self.store.boards_dir.glob("*.tmp"))
        self.assertEqual(leftovers, [])

    def test_save_mirrors_latest_content_to_bak(self):
        # the backup mirrors the most recent good save, never a stale one
        self.store.save_board(self._board())
        bak = self.store.boards_dir / "b1.json.bak"
        self.assertTrue(bak.exists())
        backed_up = Board.from_dict(json.loads(bak.read_text(encoding="utf-8")))
        self.assertEqual(backed_up, self._board())

    def test_corrupt_file_recovers_from_bak(self):
        self.store.save_board(self._board())          # creates b1.json
        self.store.save_board(self._board())          # creates b1.json.bak (good)
        path = self.store.boards_dir / "b1.json"
        path.write_text("{ this is not json", encoding="utf-8")
        recovered = self.store.load_board("b1")        # should fall back to .bak
        self.assertEqual(recovered.id, "b1")

    def test_corrupt_file_without_bak_raises_storeerror(self):
        self.store.save_board(self._board())
        (self.store.boards_dir / "b1.json.bak").unlink()  # simulate a missing backup
        (self.store.boards_dir / "b1.json").write_text("nonsense", encoding="utf-8")
        with self.assertRaises(StoreError):
            self.store.load_board("b1")

    def test_load_missing_board_raises_storeerror(self):
        with self.assertRaises(StoreError):
            self.store.load_board("ghost")


class IndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(base=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_index_creates_default_when_missing(self):
        index = self.store.load_index()
        self.assertEqual(index["version"], SCHEMA_VERSION)
        self.assertEqual(index["theme"], "dark")
        self.assertEqual(index["boards"], [])

    def test_save_then_load_index(self):
        index = {"version": SCHEMA_VERSION, "theme": "light",
                 "boards": [{"id": "b1", "name": "B", "color": "#fff"}]}
        self.store.save_index(index)
        self.assertEqual(self.store.load_index(), index)

    def test_corrupt_index_recovers_from_bak(self):
        self.store.save_index({"version": SCHEMA_VERSION, "theme": "dark", "boards": []})
        self.store.save_index({"version": SCHEMA_VERSION, "theme": "light", "boards": []})
        self.store.index_path.write_text("broken", encoding="utf-8")
        self.assertEqual(self.store.load_index()["theme"], "light")


if __name__ == "__main__":
    unittest.main()
