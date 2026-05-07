"""Simple non-intrusive toast widget."""

from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QWidget


class ToastLabel(QLabel):
    """Top-right timed toast."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background:#253046;color:white;padding:8px 12px;border-radius:6px;",
        )
        self.hide()

    def show_message(self, text: str, timeout_ms: int = 2200) -> None:
        """Show toast and auto-hide."""
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            self.move(parent.width() - self.width() - 18, 18)
        self.show()
        QTimer.singleShot(timeout_ms, self.hide)
