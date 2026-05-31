import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"PySide6 unavailable: {exc}")
        cls.app = QApplication.instance() or QApplication([])

    def test_mainwindow_builds_against_temp_store(self):
        from cachykanban.controller import Controller
        from cachykanban.store import Store
        from cachykanban.ui import MainWindow

        with tempfile.TemporaryDirectory() as tmp:
            controller = Controller(Store(base=Path(tmp)))
            controller.load()
            controller.add_card(controller.board.columns[0].id, "smoke card")
            window = MainWindow(controller)
            window.show()
            # board view rebuilt without error and a default board is present
            self.assertEqual(window.windowTitle(), "CachyKanban")
            self.assertGreaterEqual(len(controller.board.columns), 1)
            window.close()


if __name__ == "__main__":
    unittest.main()
