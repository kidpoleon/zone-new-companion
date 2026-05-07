"""Log viewer window for real-time log display."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from zone_new_companion.services.logger_service import logger_service


class LogViewerDialog(QDialog):
    """Dialog for viewing real-time logs."""
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Real-time Logs")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        self._setup_ui()
        self._connect_signals()
        self._load_existing_logs()
        
        # Auto-scroll timer
        self._auto_scroll_timer = QTimer()
        self._auto_scroll_timer.timeout.connect(self._auto_scroll)
        self._auto_scroll_timer.start(100)  # Check every 100ms
        
    def _setup_ui(self) -> None:
        """Setup the UI components."""
        layout = QVBoxLayout(self)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self._clear_logs)
        
        self.save_button = QPushButton("Save to File")
        self.save_button.clicked.connect(self._save_logs)
        
        self.pause_button = QPushButton("Pause")
        self.pause_button.setCheckable(True)
        self.pause_button.clicked.connect(self._toggle_pause)
        
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Log display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(self.font())
        
        # Set monospace font for better readability
        font = self.log_display.font()
        font.setFamily("Consolas" if font.family() == "Segoe UI" else "monospace")
        font.setPointSize(9)
        self.log_display.setFont(font)
        
        layout.addWidget(self.log_display)
        
        # Status bar
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self._is_paused = False
        
    def _connect_signals(self) -> None:
        """Connect signals."""
        logger_service.log_added.connect(self._on_log_added)
        
    def _load_existing_logs(self) -> None:
        """Load existing logs."""
        self.log_display.clear()
        for timestamp, level, message in logger_service.get_logs():
            self._add_log_to_display(timestamp, level, message)
        self._scroll_to_bottom()
        
    def _on_log_added(self, timestamp: str, level: str, message: str) -> None:
        """Handle new log entry."""
        if not self._is_paused:
            self._add_log_to_display(timestamp, level, message)
            self._scroll_to_bottom()
            
        # Update status
        total_logs = len(logger_service.get_logs())
        self.status_label.setText(f"Total logs: {total_logs} | Last: {timestamp}")
        
    def _add_log_to_display(self, timestamp: str, level: str, message: str) -> None:
        """Add log entry to display."""
        # Color coding for different levels
        color = {
            "DEBUG": "#888888",
            "INFO": "#000000",
            "WARNING": "#FF8C00",
            "ERROR": "#FF0000",
            "CRITICAL": "#8B0000",
        }.get(level, "#000000")
        
        formatted_line = f'<span style="color: {color}">{timestamp} | {level:<8} | {message}</span>'
        self.log_display.append(formatted_line)
        
    def _scroll_to_bottom(self) -> None:
        """Scroll to bottom of log display."""
        scrollbar = self.log_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _auto_scroll(self) -> None:
        """Auto-scroll if not paused."""
        if not self._is_paused:
            self._scroll_to_bottom()
            
    def _clear_logs(self) -> None:
        """Clear all logs."""
        logger_service.clear_logs()
        self.log_display.clear()
        
    def _save_logs(self) -> None:
        """Save logs to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path.home() / f"zone_new_companion_logs_{timestamp}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Logs",
            str(default_path),
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                logger_service.save_logs_to_file(file_path)
                self.status_label.setText(f"Logs saved to: {file_path}")
            except Exception as e:
                self.status_label.setText(f"Error saving logs: {e}")
                
    def _toggle_pause(self) -> None:
        """Toggle pause state."""
        self._is_paused = self.pause_button.isChecked()
        self.pause_button.setText("Resume" if self._is_paused else "Pause")
        
    def closeEvent(self, event) -> None:
        """Handle close event."""
        self._auto_scroll_timer.stop()
        super().closeEvent(event)
