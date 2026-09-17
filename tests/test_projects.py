import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cachykanban.controller import Controller
from cachykanban.models import Board, Card, Column, Label
from cachykanban.store import Store


def make_controller(tmp: str) -> Controller:
    controller = Controller(Store(base=Path(tmp)))
    controller.now = lambda: "2026-05-31T12:00:00"
    controller.load()
    return controller


class ProjectPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self._tmp.cleanup()

    def test_project_file_contains_multiple_boards_and_cards(self):
        controller = make_controller(self._tmp.name)
        project = controller.project
        first_board = controller.board
        controller.add_card(first_board.columns[0].id, "first-only")
        second_board = controller.add_board("Second board")
        controller.add_card(second_board.columns[0].id, "second-only")

        path = Path(self._tmp.name, "projects", f"{project.id}.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["id"], project.id)
        self.assertEqual({board["name"] for board in payload["boards"]}, {"My Board", "Second board"})
        titles = {
            card["title"]
            for board in payload["boards"]
            for column in board["columns"]
            for card in column["cards"]
        }
        self.assertEqual(titles, {"first-only", "second-only"})
        self.assertEqual(payload["active_board_id"], second_board.id)

    def test_projects_isolate_cards_and_boards(self):
        controller = make_controller(self._tmp.name)
        first_project = controller.project
        first_board = controller.board
        controller.add_card(first_board.columns[0].id, "first-only")

        second_project = controller.add_project("Second project")
        self.assertEqual(controller.board.name, "My Board")
        controller.add_card(controller.board.columns[0].id, "second-only")
        self.assertEqual(second_project.id, controller.project.id)
        self.assertNotIn(first_board.id, [board.id for board in second_project.boards])

        controller.open_project(first_project.id)
        self.assertEqual(controller.board.columns[0].cards[0].title, "first-only")
        self.assertNotIn("second-only", [card.title for card in controller.board.columns[0].cards])

    def test_active_project_and_board_restore_after_reload(self):
        controller = make_controller(self._tmp.name)
        project = controller.project
        second = controller.add_board("Second board")
        controller.open_board(second.id)
        reloaded = make_controller(self._tmp.name)
        self.assertEqual(reloaded.project.id, project.id)
        self.assertEqual(reloaded.board.id, second.id)
        self.assertEqual(reloaded.project.active_board_id, second.id)

    def test_project_crud_and_last_entity_safety(self):
        controller = make_controller(self._tmp.name)
        project_id = controller.project.id
        board_id = controller.board.id
        controller.rename_project(project_id, "Renamed project")
        controller.recolor_project(project_id, "#123456")
        controller.rename_board(board_id, "Renamed board")
        controller.recolor_board(board_id, "#654321")
        self.assertEqual(controller.project.name, "Renamed project")
        self.assertEqual(controller.board.name, "Renamed board")
        controller.delete_board(board_id)  # the only board cannot be removed
        self.assertEqual(len(controller.project.boards), 1)
        controller.delete_project(project_id)
        self.assertEqual(len(controller.summaries), 1)
        self.assertIsNotNone(controller.project)
        self.assertIsNotNone(controller.board)


class LegacyMigrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Store(base=Path(self._tmp.name))

    def tearDown(self):
        self._tmp.cleanup()

    def _legacy_board(self, board_id: str, title: str) -> Board:
        return Board(
            id=board_id,
            name=f"Legacy {board_id}",
            color="#abcdef",
            columns=[
                Column(
                    id=f"col-{board_id}", name="Todo",
                    cards=[Card(id=f"card-{board_id}", title=title, label_ids=[f"label-{board_id}"])],
                )
            ],
            labels=[Label(id=f"label-{board_id}", name="bug", color="#ff0000")],
            created="created", updated="updated",
        )

    def _write_legacy(self, boards: list[Board], active: str) -> dict:
        for board in boards:
            self.store.save_board(board)
        legacy = {
            "version": 1,
            "theme": "light",
            "boards": [board.summary() for board in boards],
            "active_project_id": active,
        }
        self.store.save_index(legacy)
        return legacy

    def test_v1_migration_preserves_ids_cards_labels_and_source_files(self):
        first = self._legacy_board("legacy1", "keep this card")
        second = self._legacy_board("legacy2", "keep this too")
        legacy_sources = {}
        for board in (first, second):
            self.store.save_board(board)
            legacy_sources[board.id] = (self.store.boards_dir / f"{board.id}.json").read_bytes()
        self.store.save_index({
            "version": 1, "theme": "light",
            "boards": [first.summary(), second.summary()],
            "active_project_id": second.id,
        })

        controller = Controller(self.store)
        controller.load()
        self.assertEqual(controller.project.id, second.id)
        for board in (first, second):
            project = self.store.load_project(board.id)
            migrated = project.boards[0]
            self.assertEqual(migrated.id, board.id)
            self.assertEqual(migrated.columns[0].cards[0].id, board.columns[0].cards[0].id)
            self.assertEqual(migrated.columns[0].cards[0].title, board.columns[0].cards[0].title)
            self.assertEqual(migrated.labels[0].id, board.labels[0].id)
            self.assertEqual((self.store.boards_dir / f"{board.id}.json").read_bytes(), legacy_sources[board.id])
        index = self.store.load_index()
        self.assertEqual(index["version"], 2)
        self.assertEqual({item["id"] for item in index["projects"]}, {"legacy1", "legacy2"})
        self.assertNotIn("boards", index)

    def test_migration_is_idempotent_and_stale_entries_fall_back(self):
        valid = self._legacy_board("valid", "safe")
        self.store.save_board(valid)
        source = (self.store.boards_dir / "valid.json").read_bytes()
        self.store.save_index({
            "version": 1, "theme": "dark",
            "boards": [valid.summary(), {"id": "missing", "name": "Missing", "color": "#fff"}],
            "active_project_id": "missing",
        })
        controller = Controller(self.store)
        controller.load()
        first_index = self.store.index_path.read_bytes()
        controller2 = Controller(self.store)
        controller2.load()
        self.assertEqual(controller2.project.id, "valid")
        self.assertEqual(self.store.index_path.read_bytes(), first_index)
        self.assertEqual((self.store.boards_dir / "valid.json").read_bytes(), source)
        self.assertFalse(self.store.project_exists("missing"))

    def test_corrupt_legacy_entry_does_not_block_readable_board(self):
        valid = self._legacy_board("valid", "safe")
        self.store.save_board(valid)
        corrupt_path = self.store.boards_dir / "broken.json"
        corrupt_path.parent.mkdir(parents=True, exist_ok=True)
        corrupt_path.write_text("{broken", encoding="utf-8")
        self.store.save_index({
            "version": 1, "theme": "dark",
            "boards": [valid.summary(), {"id": "broken", "name": "Broken", "color": "#fff"}],
        })
        controller = Controller(self.store)
        controller.load()
        self.assertEqual(controller.project.id, "valid")
        self.assertTrue(self.store.project_exists("valid"))
        self.assertFalse(self.store.project_exists("broken"))
        self.assertTrue(corrupt_path.exists())


class ProjectSelectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"PySide6 unavailable: {exc}")
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.controller = make_controller(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_project_and_board_combos_are_distinct_and_switch(self):
        from cachykanban.ui.main_window import MainWindow

        second_board = self.controller.add_board("Second board")
        second_project = self.controller.add_project("Second project")
        window = MainWindow(self.controller)
        try:
            self.assertIsNot(window.project_box, window.board_box)
            window.project_box.setCurrentIndex(0)
            window.board_box.setCurrentIndex(1)
            self.assertEqual(self.controller.board.id, second_board.id)
            window.project_box.setCurrentIndex(1)
            self.assertEqual(self.controller.project.id, second_project.id)
            self.assertEqual(self.controller.board.id, second_project.active_board_id)
        finally:
            window.close()

    def test_add_project_opens_once_and_selects_project(self):
        from cachykanban.ui.main_window import MainWindow

        window = MainWindow(self.controller)
        open_calls = []
        original_open = self.controller.open_board

        def tracked_open(board_id):
            open_calls.append(board_id)
            return original_open(board_id)

        self.controller.open_board = tracked_open
        try:
            with patch(
                "cachykanban.ui.project_selector.QInputDialog.getText",
                return_value=("New project", True),
            ):
                window.project_selector._add_project()
            self.assertEqual(len(open_calls), 1)
            self.assertEqual(self.controller.project.name, "New project")
            self.assertEqual(window.project_box.currentText(), "New project")
        finally:
            window.close()

    def test_add_board_opens_once_and_selects_board(self):
        from cachykanban.ui.main_window import MainWindow

        window = MainWindow(self.controller)
        open_calls = []
        original_open = self.controller.open_board

        def tracked_open(board_id):
            open_calls.append(board_id)
            return original_open(board_id)

        self.controller.open_board = tracked_open
        try:
            with patch(
                "cachykanban.ui.project_selector.QInputDialog.getText",
                return_value=("New board", True),
            ):
                window.project_selector._add_board()
            self.assertEqual(len(open_calls), 1)
            self.assertEqual(self.controller.board.name, "New board")
            self.assertEqual(window.board_box.currentText(), "New board")
        finally:
            window.close()

    def test_external_card_change_reloads_open_desktop_board(self):
        from cachykanban.controller import Controller
        from cachykanban.ui.main_window import MainWindow

        window = MainWindow(self.controller)
        try:
            project_id = self.controller.project.id
            board_id = self.controller.board.id
            column_id = self.controller.board.columns[0].id

            external = Controller(self.controller.store)
            external.load()
            external.open_project(project_id, board_id)
            added = external.add_card(column_id, "Added remotely")

            self.assertIsNone(self.controller.board.find_card(added.id))
            self.assertTrue(window._disk_content_changed())
            window._reload_external_changes()

            self.assertEqual(self.controller.project.id, project_id)
            self.assertEqual(self.controller.board.id, board_id)
            self.assertIsNotNone(self.controller.board.find_card(added.id))
            self.assertFalse(window._disk_content_changed())
        finally:
            window.close()

    def test_web_selection_bookkeeping_does_not_force_desktop_reload(self):
        from cachykanban.controller import Controller
        from cachykanban.ui.main_window import MainWindow

        second_board = self.controller.add_board("Second board")
        first_board_id = self.controller.project.boards[0].id
        self.controller.open_board(first_board_id)
        window = MainWindow(self.controller)
        try:
            external = Controller(self.controller.store)
            external.load()
            external.open_project(self.controller.project.id, second_board.id)

            self.assertFalse(window._disk_content_changed())
            self.assertEqual(self.controller.board.id, first_board_id)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
