"""Tests for the LabelManager dialog rendering and recolor.

Regression context: the theme's QSS added QListWidget::item rules, and once a
list item is styled by a stylesheet Qt ignores per-item setBackground()/
setForeground(). That made the default labels render as unreadable text on the
panel color, and made "Recolor selected" appear to do nothing in the menu.

The dialog now renders each label as a colored chip widget (setItemWidget), so
the swatch color is QSS-proof and updates on reload.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _contrast_ink(hex_color: str) -> str:
    """Return near-black or near-white for best contrast on hex_color."""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    # perceived luminance (sRGB-ish)
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#0c0d10" if lum > 0.6 else "#f2f4f8"


class ContrastTests(unittest.TestCase):
    def test_dark_text_on_light_swatch(self):
        self.assertEqual(_contrast_ink("#68d391"), "#0c0d10")  # bright green

    def test_light_text_on_dark_swatch(self):
        self.assertEqual(_contrast_ink("#1b1d23"), "#f2f4f8")  # near-black


class LabelManagerRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"PySide6 unavailable: {exc}")
        from cachykanban.ui import theme
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(theme.qss("dark"))  # the QSS that broke item roles

    def _make(self):
        from cachykanban.controller import Controller
        from cachykanban.store import Store
        tmp = tempfile.mkdtemp()
        controller = Controller(Store(base=Path(tmp)))
        controller.load()
        return controller

    def _swatch_color_in_row(self, dlg, row):
        """Dominant non-(panel/black) color across the row's chip widget."""
        from PySide6.QtCore import QPoint
        lst = dlg.list
        item = lst.item(row)
        rect = lst.visualItemRect(item)
        img = dlg.grab().toImage()
        top = lst.mapTo(dlg, rect.topLeft())
        y = top.y() + rect.height() // 2
        counts: dict = {}
        for x in range(top.x() + 2, top.x() + rect.width() - 2):
            p = img.pixelColor(x, y)
            counts[(p.red(), p.green(), p.blue())] = counts.get((p.red(), p.green(), p.blue()), 0) + 1
        return sorted(counts.items(), key=lambda kv: -kv[1])

    def test_label_swatch_uses_label_color_under_theme_qss(self):
        from cachykanban.ui.label_manager import LabelManager
        c = self._make()  # default labels: bug=#fc8181 (red), feature=#68d391, idea=#6ea8fe
        dlg = LabelManager(c)
        dlg.resize(320, 380)
        dlg.show()
        self.app.processEvents()

        # row 0 "bug" is red -> red pixels must be present despite the QSS
        dom = self._swatch_color_in_row(dlg, 0)
        red_pixels = sum(n for (r, g, b), n in dom if r > 180 and g < 170 and b < 170)
        self.assertGreater(red_pixels, 20, f"label color not rendered; saw {dom[:3]}")
        dlg.close()

    def test_recolor_updates_swatch_in_menu(self):
        from cachykanban.ui.label_manager import LabelManager
        c = self._make()
        dlg = LabelManager(c)
        dlg.resize(320, 380)
        dlg.show()
        self.app.processEvents()

        # recolor the first label to bright yellow through the controller + reload
        first_id = c.board.labels[0].id
        c.update_label(first_id, c.board.labels[0].name, "#ffff00")
        dlg.reload()
        self.app.processEvents()

        dom = self._swatch_color_in_row(dlg, 0)
        yellow = sum(n for (r, g, b), n in dom if r > 180 and g > 180 and b < 120)
        self.assertGreater(yellow, 20, f"recolor not reflected in menu; saw {dom[:3]}")
        dlg.close()


if __name__ == "__main__":
    unittest.main()
