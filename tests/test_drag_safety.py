"""Regression tests for the use-after-free crashes ("random crashing").

Root cause: BoardView rebuilt (destroying every CardWidget/ColumnWidget) from
code that was still on the live call stack -- a widget's own event handler, or a
nested event loop it had started (QDrag.exec, modal QDialog.exec, QMenu.exec).
When that code unwound, Qt touched the freed C++ object and the process aborted
(SIGSEGV). A coredump confirmed the drag path:
    QDrag::exec -> QEventLoop::exec -> ... -> QObject::deleteLater -> SEGV

A zero-delay timer (QTimer.singleShot(0)) is NOT enough on its own: an
experiment showed it fires *inside* a running nested loop. So the fix triggers
every rebuild from OUTSIDE any nested loop and defers it one more tick.
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


class DragRebuildSafetyTests(_GuiCase):
    def test_card_drag_source_signals_rebuild_without_self_destruction(self):
        """A finished card drag must request the rebuild from the SOURCE widget
        (after QDrag.exec returns) and must not delete that widget synchronously."""
        from PySide6.QtWidgets import QApplication

        controller, window, card_id = self._setup()
        card_widget = self._find_card(window, card_id)
        self.assertIsNotNone(card_widget)
        # The CardWidget must expose the post-drag hook used to trigger rebuild.
        self.assertTrue(hasattr(card_widget, "dropHandled"))

        # Emulate: target column applied the move (model mutated) during the drop,
        # then QDrag.exec returned in the source and the source announces it.
        controller.move_card(card_id, controller.board.columns[1].id, 0)
        card_widget.dropHandled.emit()

        # Source must still be alive here (rebuild only scheduled, not run).
        try:
            card_widget.objectName()
        except RuntimeError:
            self.fail("CardWidget deleted synchronously when announcing drop (use-after-free)")

        QApplication.processEvents()  # deferred rebuild runs on the next tick
        self.assertIsNotNone(self._find_card(window, card_id))

    def test_column_drop_handler_does_not_rebuild_synchronously(self):
        """ColumnWidget.dropEvent must not delete card widgets while it runs
        (it executes inside the drag's nested loop)."""
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QMimeData, QPoint
        from PySide6.QtGui import QDropEvent
        from cachykanban.ui.card_widget import CARD_MIME
        from cachykanban.ui.column_widget import ColumnWidget

        controller, window, card_id = self._setup()
        col_id = controller.board.columns[0].id
        column = next(c for c in window.findChildren(ColumnWidget) if c.column.id == col_id)
        card_widget = self._find_card(window, card_id)

        mime = QMimeData()
        mime.setData(CARD_MIME, card_id.encode("utf-8"))
        drop = QDropEvent(QPoint(10, 10), __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.DropAction.MoveAction,
                          mime, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MouseButton.LeftButton,
                          __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.KeyboardModifier.NoModifier)
        column.dropEvent(drop)

        # dropEvent runs inside QDrag.exec's loop; the source card must survive it.
        try:
            card_widget.objectName()
        except RuntimeError:
            self.fail("dropEvent rebuilt synchronously and freed a live CardWidget")

        QApplication.processEvents()
        self.assertIsNotNone(self._find_card(window, card_id))

    def test_schedule_rebuild_defers_widget_destruction(self):
        from PySide6.QtWidgets import QApplication
        from cachykanban.ui.column_widget import ColumnWidget

        controller, window, _ = self._setup()
        column_widget = window.findChildren(ColumnWidget)[0]
        window.board_view.schedule_rebuild()
        try:
            column_widget.objectName()
        except RuntimeError:
            self.fail("ColumnWidget deleted synchronously by schedule_rebuild")
        QApplication.processEvents()
        self.assertGreaterEqual(len(window.findChildren(ColumnWidget)), 1)


class ModalRefreshSafetyTests(_GuiCase):
    def test_card_widget_survives_refresh_board(self):
        """Closing the card editor triggers _refresh_board while the originating
        CardWidget's mouseReleaseEvent is still on the stack. The widget must not
        be destroyed synchronously."""
        from PySide6.QtWidgets import QApplication

        controller, window, card_id = self._setup()
        card_widget = self._find_card(window, card_id)
        self.assertIsNotNone(card_widget)

        window._refresh_board()  # exactly what runs when the editor dialog closes
        try:
            card_widget.objectName()
        except RuntimeError:
            self.fail("CardWidget deleted synchronously by _refresh_board (use-after-free)")

        QApplication.processEvents()
        self.assertIsNotNone(self._find_card(window, card_id))


if __name__ == "__main__":
    unittest.main()
