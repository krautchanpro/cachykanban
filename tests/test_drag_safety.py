"""Regression tests for the drag-and-drop use-after-free crash.

A drop handler used to call BoardView.rebuild() synchronously, which deletes
every CardWidget/ColumnWidget — including the widget whose drag.exec() was
still on the call stack. When the handler returned, Qt touched the freed C++
object and the process aborted ("random crash"). The fix defers the rebuild to
the next event-loop iteration so the handler unwinds before any widget dies.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class DragRebuildSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"PySide6 unavailable: {exc}")
        cls.app = QApplication.instance() or QApplication([])

    def _setup(self):
        from cachykanban.controller import Controller
        from cachykanban.store import Store
        from cachykanban.ui import MainWindow

        tmp = tempfile.mkdtemp()
        controller = Controller(Store(base=Path(tmp)))
        controller.load()
        card_id = controller.add_card(controller.board.columns[0].id, "drag me").id
        window = MainWindow(controller)
        return controller, window, card_id

    def _find_card(self, root, card_id):
        from cachykanban.ui.card_widget import CardWidget
        for cw in root.findChildren(CardWidget):
            if cw.card.id == card_id:
                return cw
        return None

    def test_card_widget_survives_its_own_drop_handler(self):
        """The dragged CardWidget must not be deleted synchronously on drop."""
        from PySide6.QtWidgets import QApplication
        from cachykanban.ui.column_widget import ColumnWidget

        controller, window, card_id = self._setup()
        col_id = controller.board.columns[0].id
        card_widget = self._find_card(window, card_id)
        self.assertIsNotNone(card_widget)

        column_widget = next(
            x for x in window.findChildren(ColumnWidget) if x.column.id == col_id
        )
        # Emulate ColumnWidget.dropEvent's tail: mutate model, then request a refresh.
        controller.move_card(card_id, col_id, 0)
        column_widget.changed.emit()

        # drag.exec() would now return into this very widget's mouseMoveEvent.
        # It must still be alive (rebuild deferred), or Qt aborts the process.
        try:
            card_widget.objectName()
        except RuntimeError:
            self.fail("CardWidget deleted synchronously during drop handler (use-after-free)")

        # The deferred rebuild runs on the next event-loop tick.
        QApplication.processEvents()
        self.assertIsNotNone(self._find_card(window, card_id))

    def test_schedule_rebuild_defers_widget_destruction(self):
        """schedule_rebuild() must not destroy live widgets synchronously."""
        from PySide6.QtWidgets import QApplication
        from cachykanban.ui.column_widget import ColumnWidget

        controller, window, _ = self._setup()
        column_widget = window.findChildren(ColumnWidget)[0]

        window.board_view.schedule_rebuild()
        try:
            column_widget.objectName()  # must survive synchronously
        except RuntimeError:
            self.fail("ColumnWidget deleted synchronously by schedule_rebuild")

        QApplication.processEvents()
        self.assertGreaterEqual(len(window.findChildren(ColumnWidget)), 1)


if __name__ == "__main__":
    unittest.main()
