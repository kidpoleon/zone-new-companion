"""Generic QRunnable wrapper for background tasks."""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class TaskSignals(QObject):
    """Signals for async task lifecycle."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)
    finished = pyqtSignal()


class TaskWorker(QRunnable):
    """Run a callable in QThreadPool and emit status signals."""

    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self._task = task
        self.signals = TaskSignals()

    @pyqtSlot()
    def run(self) -> None:
        try:
            result = self._task()
            self.signals.succeeded.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(str(exc))
        finally:
            self.signals.finished.emit()
