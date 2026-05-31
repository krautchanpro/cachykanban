import unittest

from cachykanban.ui.theme import qss, palette, THEMES


class ThemeTests(unittest.TestCase):
    def test_themes_known(self):
        self.assertIn("dark", THEMES)
        self.assertIn("light", THEMES)

    def test_qss_nonempty_and_themeable(self):
        self.assertIn("QWidget", qss("dark"))
        self.assertNotEqual(qss("dark"), qss("light"))

    def test_unknown_theme_falls_back_to_dark(self):
        self.assertEqual(qss("bogus"), qss("dark"))

    def test_palette_has_core_keys(self):
        for key in ("bg", "panel", "ink", "accent", "line"):
            self.assertIn(key, palette("dark"))


if __name__ == "__main__":
    unittest.main()
