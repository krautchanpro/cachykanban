"""Tests for application icon wiring.

The app previously never set a window icon or the Wayland desktop-file name, so
the running window showed a generic placeholder in the taskbar/alt-tab even
though an icon file was installed. These tests pin the resolution helper and the
QApplication wiring.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DESKTOP_ID = "io.github.tubbyhubby.CachyKanban"


class IconResolveTests(unittest.TestCase):
    def test_bundled_icon_path_exists(self):
        # The packaged SVG ships next to the source tree under data/.
        from cachykanban.app import _bundled_icon_path
        p = _bundled_icon_path()
        self.assertIsNotNone(p)
        self.assertTrue(p.exists(), f"expected bundled icon at {p}")
        self.assertEqual(p.suffix, ".svg")

    def test_load_icon_returns_nonnull(self):
        from PySide6.QtWidgets import QApplication
        from cachykanban.app import load_app_icon
        _ = QApplication.instance() or QApplication([])
        icon = load_app_icon()
        self.assertFalse(icon.isNull(), "app icon should resolve to a real image")


class IconWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_apply_app_identity_sets_icon_and_desktop_name(self):
        from PySide6.QtWidgets import QApplication
        from cachykanban.app import apply_app_identity

        apply_app_identity(self.app)
        self.assertEqual(QApplication.desktopFileName(), DESKTOP_ID)
        self.assertFalse(self.app.windowIcon().isNull())

    def test_mainwindow_has_window_icon(self):
        from PySide6.QtWidgets import QApplication
        from cachykanban.app import apply_app_identity
        from cachykanban.controller import Controller
        from cachykanban.store import Store
        from cachykanban.ui import MainWindow

        apply_app_identity(self.app)
        with tempfile.TemporaryDirectory() as tmp:
            controller = Controller(Store(base=Path(tmp)))
            controller.load()
            window = MainWindow(controller)
            # Window inherits the application icon; it must not be null.
            self.assertFalse(window.windowIcon().isNull()
                             or self.app.windowIcon().isNull())
            window.close()


if __name__ == "__main__":
    unittest.main()
