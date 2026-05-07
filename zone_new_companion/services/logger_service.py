"""Real-time logging service for zone-new-companion."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import TextIO

from PyQt6.QtCore import QObject, pyqtSignal


class LoggerService(QObject):
    """Real-time logging service with timestamp support."""
    
    # Signal for real-time log updates
    log_added = pyqtSignal(str, str, str)  # timestamp, level, message
    
    def __init__(self) -> None:
        super().__init__()
        self._logs: list[tuple[str, str, str]] = []  # timestamp, level, message
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Setup Python logging with custom handler."""
        # Create custom handler that emits signals
        class QtSignalHandler(logging.Handler):
            def __init__(self, logger_service: LoggerService) -> None:
                super().__init__()
                self.logger_service = logger_service
                
            def emit(self, record: logging.LogRecord) -> None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                level = record.levelname
                message = record.getMessage()
                self.logger_service._add_log(timestamp, level, message)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Add console handler with verbose output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Add Qt signal handler
        qt_handler = QtSignalHandler(self)
        qt_handler.setLevel(logging.DEBUG)
        qt_formatter = logging.Formatter("%(message)s")
        qt_handler.setFormatter(qt_formatter)
        root_logger.addHandler(qt_handler)
        
        # Log initialization
        self.info("Logger service initialized")
        
    def _add_log(self, timestamp: str, level: str, message: str) -> None:
        """Add log entry and emit signal."""
        self._logs.append((timestamp, level, message))
        self.log_added.emit(timestamp, level, message)
        
        # Keep only last 1000 logs in memory
        if len(self._logs) > 1000:
            self._logs = self._logs[-1000:]
    
    def debug(self, message: str) -> None:
        """Log debug message."""
        logging.debug(message)
        
    def info(self, message: str) -> None:
        """Log info message."""
        logging.info(message)
        
    def warning(self, message: str) -> None:
        """Log warning message."""
        logging.warning(message)
        
    def error(self, message: str) -> None:
        """Log error message."""
        logging.error(message)
        
    def critical(self, message: str) -> None:
        """Log critical message."""
        logging.critical(message)
        
    def get_logs(self) -> list[tuple[str, str, str]]:
        """Get all logs."""
        return self._logs.copy()
        
    def clear_logs(self) -> None:
        """Clear all logs."""
        self._logs.clear()
        self.info("Logs cleared")
        
    def save_logs_to_file(self, file_path: str | Path) -> None:
        """Save logs to file."""
        file_path = Path(file_path)
        with file_path.open("w", encoding="utf-8") as f:
            f.write("zone-new-companion Log File\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            for timestamp, level, message in self._logs:
                f.write(f"{timestamp} | {level:-8} | {message}\n")
                
        self.info(f"Logs saved to {file_path}")


# Global logger instance
logger_service = LoggerService()
