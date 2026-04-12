from __future__ import annotations

from pathlib import Path
from typing import Type

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget


ROOT_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT_DIR / "frontend"
UI_DIR = FRONTEND_DIR / "ui"
STYLE_PATH = FRONTEND_DIR / "styles" / "theme_ironman.qss"

def apply_global_theme(app: QApplication) -> None:
    if STYLE_PATH.exists():
        app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))
    else:
        fallback = FRONTEND_DIR / "styles" / "theme.qss"
        if fallback.exists():
            app.setStyleSheet(fallback.read_text(encoding="utf-8"))


class BaseWindow(QMainWindow):
    def __init__(self, ui_filename: str):
        super().__init__()
        uic.loadUi(str(UI_DIR / ui_filename), self)
        self._next_window: QWidget | None = None

    def navigate_to(self, window_cls: Type[QWidget]) -> None:
        self._next_window = window_cls()
        self._next_window.show()
        self.close()
