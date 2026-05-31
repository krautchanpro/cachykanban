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


if __name__ == "__main__":
    unittest.main()
