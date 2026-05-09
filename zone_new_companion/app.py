"""Application bootstrap."""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Callable

# Set Windows AppUserModelID BEFORE any UI initialization (must be before QApplication)
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('kidpoleon.zone-new-companion.1.2.2')
    except Exception:
        pass

# Determine base directory for resources (PyInstaller or normal)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt
import qdarkstyle

from zone_new_companion.config import ConfigStore
from zone_new_companion.controllers.app_controller import AppController
from zone_new_companion.logging_config import configure_logging
from zone_new_companion.models import MediaItem, PlaylistCategory
from zone_new_companion.state import StateStore
from zone_new_companion.ui.main_window import MainWindow
from zone_new_companion import __version__


def run() -> None:
    """Start the GUI application."""
    app_data = Path.home() / ".zone-new-companion"
    configure_logging(app_data / "logs")

    config_store = ConfigStore(app_data / "config.json")
    state_store = StateStore()
    controller = AppController(state_store, config_store)

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("zone-new-companion")
    qt_app.setApplicationVersion(__version__)
    
    # Set application icon (shows in taskbar on Windows)
    icon_path = os.path.join(BASE_DIR, "zone_new_companion", "icon", "icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        qt_app.setWindowIcon(app_icon)
    
    if controller.config.ui.dark_theme:
        qt_app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))

    window = MainWindow()
    
    # Set window icon explicitly (inherited from app, but setting again ensures it)
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    
    window.resize(controller.config.ui.width, controller.config.ui.height)
    _refresh_history_menu(window, controller)
    window.set_help_info(lambda: _show_info(window))

    def on_error(message: str) -> None:
        QMessageBox.critical(window, "Error", message)

    state_store.state_changed.connect(window.apply_state)
    window.connect_requested.connect(
        lambda credentials: controller.connect(
            credentials,
            on_success=lambda message: _on_connect_success(window, controller, message),
            on_error=on_error,
        ),
    )
    window.category_selected.connect(
        lambda tab_name, category: _load_category(controller, tab_name, category, on_error, window.notify),
    )
    window.item_activated.connect(
        lambda tab_name, item: _activate_item(controller, tab_name, item, on_error, window.notify),
    )
    window.back_requested.connect(lambda tab_name: _go_back(controller, tab_name, window.notify, on_error))
    window.history_selected.connect(lambda index: _pick_history(window, controller, index))
    window.history_clear_requested.connect(lambda: _clear_history(window, controller))
    window.verify_item_requested.connect(
        lambda tab_name, item: controller.verify_single_item(tab_name, item, on_success=window.notify, on_error=on_error),
    )
    window.verify_all_channels_requested.connect(
        lambda tab_name: controller.verify_all_channels(tab_name, on_success=window.notify, on_error=on_error),
    )
    window.verify_tab_requested.connect(
        lambda tab_name: controller.verify_tab(tab_name, on_success=window.notify, on_error=on_error),
    )
    window.verify_cancel_requested.connect(
        lambda: controller.cancel_verification(on_success=window.notify, on_error=on_error),
    )
    window.now_playing_requested.connect(lambda tab_name, item: controller.request_now_playing(tab_name, item))
    window.reset_requested.connect(lambda: _reset(window, controller))

    if controller.config.last_input:
        window.populate_form(controller.config.last_input)

    qt_app.aboutToQuit.connect(lambda: controller.save_ui_state(window.width(), window.height()))
    
    # Show as normal window with controls (not fullscreen) - ensures minimize/maximize/close buttons
    window.show()
    
    sys.exit(qt_app.exec())


def _load_category(
    controller: AppController,
    tab_name: str,
    category: PlaylistCategory,
    on_error: Callable[[str], None],
    on_success: Callable[[str], None],
) -> None:
    controller.load_items(
        tab_name=tab_name,
        category=category,
        on_success=on_success,
        on_error=on_error,
    )


def _activate_item(
    controller: AppController,
    tab_name: str,
    item: MediaItem,
    on_error: Callable[[str], None],
    on_success: Callable[[str], None],
) -> None:
    controller.activate_item(tab_name, item, on_success=on_success, on_error=on_error)


def _go_back(
    controller: AppController,
    tab_name: str,
    on_success: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    if controller.go_back(tab_name):
        on_success("Returned to previous list")
    else:
        on_error("No previous list for this tab.")


def _pick_history(window: MainWindow, controller: AppController, index: int) -> None:
    history = controller.history_entries()
    if 0 <= index < len(history):
        window.populate_form(history[index])
        window.notify("Loaded credentials from history")


def _reset(window: MainWindow, controller: AppController) -> None:
    controller.reset_form()
    window.login_panel.clear()
    _refresh_history_menu(window, controller)
    window.notify("Form reset")


def _on_connect_success(window: MainWindow, controller: AppController, message: str) -> None:
    _refresh_history_menu(window, controller)
    window.notify(message)


def _refresh_history_menu(window: MainWindow, controller: AppController) -> None:
    groups: dict[str, list[tuple[int, str]]] = {}
    history = controller.history_entries()
    for idx, row in enumerate(history):
        day = (row.saved_at or "Unknown Date").split("T", 1)[0]
        label = f"{row.portal_type.value.upper()} | {row.base_url} | {row.username or row.mac_address or 'anonymous'}"
        groups.setdefault(day, []).append((idx, label))
    window.set_history_grouped(groups)


def _clear_history(window: MainWindow, controller: AppController) -> None:
    controller.clear_history()
    _refresh_history_menu(window, controller)
    window.notify("History cleared")


def _show_info(window: MainWindow) -> None:
    QMessageBox.information(
        window,
        "About zone-new-companion",
        "zone-new-companion\n"
        f"Version: {__version__}\n\n"
        "GitHub: https://github.com/kidpoleon/zone-new-companion\n"
        "Support: Open an issue on GitHub\n",
    )
