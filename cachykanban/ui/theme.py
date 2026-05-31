from __future__ import annotations

THEMES = ("dark", "light", "system")

_PALETTES = {
    "dark": {
        "bg": "#1b1d23", "panel": "#23262e", "panel2": "#2a2e38",
        "ink": "#e6e8ee", "sub": "#9aa3b2", "line": "#343945", "accent": "#6ea8fe",
    },
    "light": {
        "bg": "#f4f5f7", "panel": "#ffffff", "panel2": "#eef0f3",
        "ink": "#1b1d23", "sub": "#5a6473", "line": "#d6dae1", "accent": "#3b82f6",
    },
}


def palette(theme: str) -> dict[str, str]:
    if theme == "system":
        theme = "dark"
    return _PALETTES.get(theme, _PALETTES["dark"])


def qss(theme: str) -> str:
    p = palette(theme)
    return f"""
    QWidget {{ background: {p['bg']}; color: {p['ink']};
        font-family: "Inter", "Cantarell", system-ui, sans-serif; font-size: 13px; }}
    QFrame#Panel {{ background: {p['panel']}; border: 1px solid {p['line']};
        border-radius: 10px; }}
    QFrame#Card {{ background: {p['panel2']}; border: 1px solid {p['line']};
        border-radius: 8px; }}
    QFrame#Card:hover {{ border: 1px solid {p['accent']}; }}
    QLabel#ColumnTitle {{ font-weight: 700; }}
    QLabel#Muted {{ color: {p['sub']}; }}
    QPushButton {{ background: {p['panel2']}; border: 1px solid {p['line']};
        border-radius: 6px; padding: 5px 10px; }}
    QPushButton:hover {{ border: 1px solid {p['accent']}; }}
    QPushButton#Accent {{ background: {p['accent']}; color: #0c0d10; font-weight: 700; }}
    QLineEdit, QTextEdit, QComboBox {{ background: {p['panel']};
        border: 1px solid {p['line']}; border-radius: 6px; padding: 4px 6px; }}
    QListWidget {{ background: {p['panel']}; border: 1px solid {p['line']};
        border-radius: 8px; }}
    """
