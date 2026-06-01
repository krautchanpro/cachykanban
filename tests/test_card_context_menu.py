"""Tests for the card right-click context menu (delete a card).

Safety note: a context menu runs a nested event loop via menu.exec(), and
deleting a card destroys its CardWidget. As with the drag/modal fixes, the
rebuild that destroys the widget must be DEFERRED (schedule_rebuild) and
triggered from outside the nested loop, or it is a use-after-free. These tests
assert the deletion path removes the card without synchronously freeing the
emitting widget.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _GuiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"PySide6 unavailable: {exc}")
        from cachykanban.ui import theme
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(theme.qss("dark"))

    def _setup(self, n_cards=1):
        from cachykanban.controller import Controller
        from cachykanban.store import Store
        from cachykanban.ui import MainWindow

        tmp = tempfile.mkdtemp()
        controller = Controller(Store(base=Path(tmp)))
        controller.load()
        ids = [controller.add_card(controller.board.columns[0].id, f"card {i}").id
               for i in range(n_cards)]
        window = MainWindow(controller)
        return controller, window, ids

    def _find_card(self, root, card_id):
        from cachykanban.ui.card_widget import CardWidget
        for cw in root.findChildren(CardWidget):
            if cw.card.id == card_id:
                return cw
        return None


class CardContextMenuTests(_GuiCase):
    def test_card_widget_exposes_delete_signal(self):
        from cachykanban.ui.card_widget import CardWidget
        controller, window, ids = self._setup()
        cw = self._find_card(window, ids[0])
        self.assertIsNotNone(cw)
        self.assertTrue(hasattr(cw, "deleteRequested"))

    def test_context_menu_contains_delete_action(self):
        controller, window, ids = self._setup()
        cw = self._find_card(window, ids[0])
        menu, actions = cw.build_context_menu()
        labels = [a.text() for a in menu.actions() if a.text()]
        self.assertIn("Delete card", labels)
        self.assertIn("Delete card", actions)  # mapping exposes it by key

    def test_delete_request_removes_card_without_freeing_widget_synchronously(self):
        from PySide6.QtWidgets import QApplication
        controller, window, ids = self._setup(n_cards=2)
        target = ids[0]
        cw = self._find_card(window, target)
        self.assertIsNotNone(cw)

        # Simulate the user picking "Delete card" in the context menu.
        cw.deleteRequested.emit(target)

        # Model updated immediately...
        self.assertIsNone(controller.board.find_card(target))
        # ...but the widget must NOT be destroyed synchronously (rebuild deferred).
        try:
            cw.objectName()
        except RuntimeError:
            self.fail("CardWidget freed synchronously on delete (use-after-free)")

        # After the event loop ticks, the rebuild runs and the card is gone.
        QApplication.processEvents()
        self.assertIsNone(self._find_card(window, target))
        # The other card survives.
        self.assertIsNotNone(self._find_card(window, ids[1]))


if __name__ == "__main__":
    unittest.main()
