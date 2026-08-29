import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cachykanban.controller import Controller
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

    def test_projects_have_isolated_cards_and_active_project_persists(self):
        controller = make_controller(self._tmp.name)
        first = controller.board
        second = controller.add_project("Second")
        controller.open_project(second.id)
        controller.add_card(second.columns[0].id, "second-only")

        controller.open_project(first.id)
        self.assertEqual(controller.board.id, first.id)
        self.assertEqual(controller.board.columns[0].cards, [])
        index = json.loads(Path(self._tmp.name, "index.json").read_text())
        self.assertEqual(index["active_project_id"], first.id)

        reloaded = make_controller(self._tmp.name)
        self.assertEqual(reloaded.board.id, first.id)
        reloaded.open_project(second.id)
        self.assertEqual(reloaded.board.columns[0].cards[0].title, "second-only")

    def test_old_index_and_stale_active_project_fall_back_to_first(self):
        controller = make_controller(self._tmp.name)
        second = controller.add_project("Second")
        index_path = Path(self._tmp.name, "index.json")
        index = json.loads(index_path.read_text())

        index.pop("active_project_id")
        index_path.write_text(json.dumps(index))
        old_index = make_controller(self._tmp.name)
        self.assertEqual(old_index.board.id, controller.summaries[0]["id"])

        index = json.loads(index_path.read_text())
        index["active_project_id"] = "missing-project"
        index_path.write_text(json.dumps(index))
        stale_index = make_controller(self._tmp.name)
        self.assertEqual(stale_index.board.id, controller.summaries[0]["id"])
        self.assertNotEqual(stale_index.board.id, second.id)


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

    def test_switching_combo_opens_selected_project(self):
        from cachykanban.ui.main_window import MainWindow

        second = self.controller.add_project("Second")
        window = MainWindow(self.controller)
        try:
            window.project_box.setCurrentIndex(1)
            self.assertEqual(self.controller.board.id, second.id)
            self.assertEqual(self.controller.active_project_id, second.id)
        finally:
            window.close()

    def test_add_project_uses_one_open_signal_and_selects_it(self):
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
            self.assertEqual(self.controller.board.name, "New project")
            self.assertEqual(window.project_box.currentText(), "New project")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
