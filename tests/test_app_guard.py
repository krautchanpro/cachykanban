"""Tests for the global exception guard (defense-in-depth).

The drag use-after-free was the known crash, but ANY unhandled exception in a
Qt slot aborts the process under PySide6. The guard turns such errors into a
logged, non-fatal message so the app keeps running instead of vanishing.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ExceptionGuardTests(unittest.TestCase):
    def test_logs_unhandled_exception_to_file(self):
        from cachykanban.app import _log_unhandled

        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "cachykanban.log"
            try:
                raise ValueError("boom-xyz")
            except ValueError:
                _log_unhandled(*sys.exc_info(), log_path=log, show=False)
            data = log.read_text(encoding="utf-8")
            self.assertIn("ValueError", data)
            self.assertIn("boom-xyz", data)

    def test_log_write_failure_is_swallowed(self):
        from cachykanban.app import _log_unhandled

        # An unwritable path must not raise from within the handler.
        bad = Path("/this/path/does/not/exist/cachykanban.log")
        try:
            raise RuntimeError("x")
        except RuntimeError:
            _log_unhandled(*sys.exc_info(), log_path=bad, show=False)  # must not raise

    def test_install_sets_excepthook(self):
        import cachykanban.app as appmod
        from cachykanban.store import Store

        old = sys.excepthook
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = appmod.install_exception_guard(Store(base=Path(tmp)))
                self.assertIsNot(sys.excepthook, old)
                self.assertEqual(path, Path(tmp) / "cachykanban.log")
        finally:
            sys.excepthook = old


if __name__ == "__main__":
    unittest.main()
