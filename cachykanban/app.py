from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import __version__
from .controller import Controller
from .store import Store
from .ui import MainWindow
from .ui import theme

#: Reverse-DNS desktop id; must match the installed .desktop file's basename so
#: Wayland compositors map the running window to the installed icon.
DESKTOP_FILE_NAME = "io.github.tubbyhubby.CachyKanban"
ICON_NAME = "cachykanban"


def _bundled_icon_path() -> Path | None:
    """Path to the SVG that ships in the source tree (data/cachykanban.svg)."""
    candidate = Path(__file__).resolve().parent.parent / "data" / f"{ICON_NAME}.svg"
    return candidate if candidate.exists() else None


def load_app_icon() -> QIcon:
    """Resolve the app icon, preferring the installed themed icon.

    Order: the system icon theme (when installed under hicolor) -> the bundled
    SVG in the source tree -> an empty icon as a last resort. Never raises.
    """
    themed = QIcon.fromTheme(ICON_NAME)
    if not themed.isNull():
        return themed
    bundled = _bundled_icon_path()
    if bundled is not None:
        return QIcon(str(bundled))
    return QIcon()


def apply_app_identity(app: QApplication) -> None:
    """Set the window icon and the Wayland/X11 desktop-file association.

    setDesktopFileName is what lets KDE/Wayland link the toplevel window to the
    installed .desktop entry (and therefore its icon); without it the taskbar
    and alt-tab show a generic placeholder regardless of the icon file.
    """
    QApplication.setDesktopFileName(DESKTOP_FILE_NAME)
    app.setWindowIcon(load_app_icon())


def _log_unhandled(
    exc_type: type[BaseException],
    exc: BaseException,
    tb: TracebackType | None,
    *,
    log_path: Path,
    show: bool = True,
) -> None:
    """Record an unhandled exception instead of letting it abort the process.

    Defense-in-depth: PySide6 turns an exception that escapes a Qt slot into a
    process abort. With the app launched via a .desktop entry (Terminal=false)
    the traceback is invisible, so a stray bug reads as a "random crash". We log
    the full traceback to ``log_path`` and (optionally) show a non-fatal dialog,
    keeping the event loop alive.

    Note: this catches Python-level exceptions only. It cannot catch a C++ abort
    such as a use-after-free in Qt — those are fixed structurally elsewhere.
    """
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"\n===== {stamp} =====\n{text}")
    except OSError:
        # Never let the error handler raise — that would defeat its purpose.
        pass

    # Mirror to stderr too (visible when launched from a terminal).
    sys.stderr.write(text)

    if show:
        try:
            QMessageBox.critical(
                None,
                "CachyKanban — unexpected error",
                f"{exc_type.__name__}: {exc}\n\nThe error was logged to:\n{log_path}\n\n"
                "The app will keep running, but you may want to restart it.",
            )
        except Exception:
            pass


def install_exception_guard(store: Store, *, show: bool = True) -> Path:
    """Route unhandled exceptions to the log file under the store's data dir.

    Returns the log path so callers/tests can locate it.
    """
    log_path = store.base / "cachykanban.log"

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        _log_unhandled(exc_type, exc, tb, log_path=log_path, show=show)

    sys.excepthook = hook
    return log_path


def main(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("CachyKanban")
    app.setApplicationDisplayName("CachyKanban")
    app.setApplicationVersion(__version__)
    apply_app_identity(app)

    store = Store()
    install_exception_guard(store)

    controller = Controller(store)
    controller.load()
    app.setStyleSheet(theme.qss(controller.theme_name))

    window = MainWindow(controller)
    window.show()
    return app.exec()
