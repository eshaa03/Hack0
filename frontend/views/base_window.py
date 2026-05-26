from __future__ import annotations

from pathlib import Path
from typing import Type

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import Qt


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
        self._next_window.setGeometry(self.geometry())
        if self.isMaximized():
            self._next_window.showMaximized()
        elif self.isFullScreen():
            self._next_window.showFullScreen()
        else:
            self._next_window.show()
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            from PyQt5.QtWidgets import QTextEdit, QPlainTextEdit
            focused = self.focusWidget()
            if isinstance(focused, (QTextEdit, QPlainTextEdit)):
                super().keyPressEvent(event)
            else:
                self.focusNextChild()
        else:
            super().keyPressEvent(event)
