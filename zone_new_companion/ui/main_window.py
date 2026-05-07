"""Main UI shell."""

from __future__ import annotations

import sys
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from zone_new_companion.models import Credentials
from zone_new_companion.state import AppState
from zone_new_companion.ui.widgets.login_panel import LoginPanel
from zone_new_companion.ui.widgets.toast import ToastLabel
from zone_new_companion import __version__


class MainWindow(QMainWindow):
    """Main application window."""

    connect_requested = pyqtSignal(object)
    category_selected = pyqtSignal(str, object)
    item_activated = pyqtSignal(str, object)
    verify_item_requested = pyqtSignal(str, object)
    verify_all_channels_requested = pyqtSignal(str)
    verify_tab_requested = pyqtSignal(str)
    verify_cancel_requested = pyqtSignal()
    logs_clear_requested = pyqtSignal()
    # logs_show_requested signal removed for performance
    logs_save_requested = pyqtSignal()
    now_playing_requested = pyqtSignal(str, object)
    back_requested = pyqtSignal(str)
    reset_requested = pyqtSignal()
    history_selected = pyqtSignal(int)
    history_clear_requested = pyqtSignal()
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"zone-new-companion v{__version__}")
        self.setMinimumSize(1000, 650)
        
        # Set window flags based on OS
        if sys.platform == "win32":
            # Windows: Add minimize/maximize buttons, keep frame
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowMaximizeButtonHint |
                Qt.WindowType.WindowCloseButtonHint
            )
        elif sys.platform == "darwin":
            # macOS: Native window controls
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowMaximizeButtonHint |
                Qt.WindowType.WindowCloseButtonHint
            )
        else:
            # Linux: Standard window controls
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowMaximizeButtonHint |
                Qt.WindowType.WindowCloseButtonHint
            )
        self._help_menu = QMenu("Help", self)
        self._history_menu = QMenu("History", self)
        self._logs_menu = QMenu("Logs", self)
        self._verify_menu = QMenu("Verify", self)
        self.menuBar().addMenu(self._help_menu)
        self.menuBar().addMenu(self._verify_menu)
        self.menuBar().addMenu(self._history_menu)
        self.menuBar().addMenu(self._logs_menu)

        self._help_info_action = self._help_menu.addAction("Info")
        self._help_exit_action = self._help_menu.addAction("Exit")
        self._help_exit_action.triggered.connect(self.close)

        # Verify menu actions
        self._verify_cancel_action = self._verify_menu.addAction("Cancel Verification")
        self._verify_cancel_action.triggered.connect(self._emit_cancel_verification)
        
        self._verify_menu.addSeparator()
        
        self._verify_live_action = self._verify_menu.addAction("Verify Live")
        self._verify_live_action.triggered.connect(lambda: self._emit_verify_tab("Live"))
        
        self._verify_movies_action = self._verify_menu.addAction("Verify Movies")
        self._verify_movies_action.triggered.connect(lambda: self._emit_verify_tab("Movies"))
        
        self._verify_series_action = self._verify_menu.addAction("Verify Series")
        self._verify_series_action.triggered.connect(lambda: self._emit_verify_tab("Series"))

        # Logs menu actions
        self._logs_clear_action = self._logs_menu.addAction("Clear Logs")
        self._logs_clear_action.triggered.connect(self._emit_clear_logs)
        
        self._logs_menu.addSeparator()
        
        # Log viewer removed for performance
        
        self._logs_save_action = self._logs_menu.addAction("Save Logs to File")
        self._logs_save_action.triggered.connect(self._emit_save_logs)

        self._toast = ToastLabel(self)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.login_panel = LoginPanel()
        self.login_panel.connect_clicked.connect(self.connect_requested.emit)
        self.login_panel.reset_clicked.connect(self._confirm_reset)
        layout.addWidget(self.login_panel, 0)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        
        # Create tab widget (verify button moved to titlebar menu)
        self.tab_widget = QTabWidget()
        
        self.category_lists: dict[str, QListWidget] = {}
        self.item_tables: dict[str, QTableWidget] = {}
        for tab_name in ("Live", "Movies", "Series"):
            tab = QWidget()
            tab_layout = QHBoxLayout(tab)
            categories = QListWidget()
            categories.setToolTip("Category list")
            table = QTableWidget()
            table.setToolTip("Playlist items")
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Name", "Now Playing", "Status", "Verify", "Play"])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
            table.cellClicked.connect(lambda row, _col, name=tab_name: self._emit_now_playing(name, row))
            table.cellDoubleClicked.connect(lambda row, _col, name=tab_name: self._emit_play_from_row(name, row))
            tab_layout.addWidget(categories, 1)
            tab_layout.addWidget(table, 3)
            self.tab_widget.addTab(tab, tab_name)
            self.category_lists[tab_name] = categories
            self.item_tables[tab_name] = table

            categories.itemClicked.connect(
                lambda item, name=tab_name: self.category_selected.emit(name, item.data(Qt.ItemDataRole.UserRole)),
            )
            table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            table.customContextMenuRequested.connect(lambda _pos, name=tab_name: self.back_requested.emit(name))
        right_layout.addWidget(self.tab_widget)
        layout.addWidget(right, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setMinimumHeight(25)  # Increase height for better visibility
        self.progress.setMinimumWidth(300)  # Increase width for better visibility
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                font-weight: bold;
                background-color: #2a2a2a;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        self.progress.hide()
        self.status_label = QLabel("Ready")
        status = QStatusBar()
        status.addPermanentWidget(self.status_label, 1)
        status.addPermanentWidget(self.progress)
        self.setStatusBar(status)

    def _confirm_reset(self) -> None:
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Warning)
        message.setWindowTitle("Confirm reset")
        message.setText("Reset all form fields?")
        message.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if message.exec() == QMessageBox.StandardButton.Yes:
            self.reset_requested.emit()

    def apply_state(self, state: AppState) -> None:
        """Render state changes."""
        self.status_label.setText(state.status_text)
        
        # Handle progress bar visibility and text
        if state.busy:
            self.progress.show()
            # Show verification progress if available
            if "Verifying" in state.status_text:
                self.progress.setRange(0, 0)  # Indeterminate progress
                self.progress.setFormat("Verifying...")
            elif "Priority verifying" in state.status_text:
                self.progress.setRange(0, 0)  # Indeterminate progress
                self.progress.setFormat("Priority Verification...")
            else:
                self.progress.setRange(0, 0)  # Indeterminate progress
                self.progress.setFormat("Loading...")
        else:
            self.progress.hide()
            self.progress.setFormat("")
        self.login_panel.set_connection_info(state.credential_info)
        for tab_name, categories in state.categories.items():
            list_widget = self.category_lists[tab_name]
            list_widget.clear()
            for category in categories:
                item = QListWidgetItem(category.name)
                item.setData(Qt.ItemDataRole.UserRole, category)
                list_widget.addItem(item)
        for tab_name, items in state.current_items.items():
            table = self.item_tables[tab_name]
            table.setRowCount(0)
            for media in items:
                row = table.rowCount()
                table.insertRow(row)
                name_item = QTableWidgetItem(media.name)
                name_item.setData(Qt.ItemDataRole.UserRole, media)
                now_text = state.now_playing.get(tab_name, {}).get(media.id, "")
                now_item = QTableWidgetItem(now_text)
                # Use persistent verification results first, fallback to current tab results
                status = state.persistent_verification_results.get(media.id, "")
                if not status:
                    status = state.verification_results.get(tab_name, {}).get(media.id, "")
                status_item = QTableWidgetItem(status)
                table.setItem(row, 0, name_item)
                table.setItem(row, 1, now_item)
                table.setItem(row, 2, status_item)

                verify_button = QPushButton("🔍")
                verify_button.setToolTip("Verify stream")
                verify_button.clicked.connect(lambda checked=False, name=tab_name, m=media: self.verify_item_requested.emit(name, m))
                verify_button.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
                        padding: 4px;
                        border-radius: 3px;
                        background-color: #3a3a3a;
                        color: white;
                        min-width: 30px;
                        max-width: 30px;
                    }
                    QPushButton:hover {
                        background-color: #4a4a4a;
                    }
                    QPushButton:pressed {
                        background-color: #2a2a2a;
                    }
                """)
                
                play_button = QPushButton("▶")
                play_button.setToolTip("Play stream")
                play_button.clicked.connect(lambda checked=False, name=tab_name, m=media: self.item_activated.emit(name, m))
                play_button.setStyleSheet("""
                    QPushButton {
                        font-size: 14px;
                        padding: 4px;
                        border-radius: 3px;
                        background-color: #3a3a3a;
                        color: white;
                        min-width: 30px;
                        max-width: 30px;
                    }
                    QPushButton:hover {
                        background-color: #4a4a4a;
                    }
                    QPushButton:pressed {
                        background-color: #2a2a2a;
                    }
                """)
                table.setCellWidget(row, 3, verify_button)
                table.setCellWidget(row, 4, play_button)

                self._apply_row_color(table, row, status)

    def notify(self, text: str) -> None:
        """Show toast notification."""
        self._toast.show_message(text)

    def populate_form(self, credentials: Credentials) -> None:
        """Load credentials into form."""
        self.login_panel.populate_form(credentials)

    def set_history_actions(self, labels: list[str]) -> None:
        """Populate top menu history actions."""
        self._history_menu.clear()
        if not labels:
            action = self._history_menu.addAction("No successful connections yet")
            action.setEnabled(False)
            return
        for index, label in enumerate(labels):
            action = self._history_menu.addAction(label)
            action.triggered.connect(lambda checked=False, idx=index: self.history_selected.emit(idx))

    def set_history_grouped(self, groups: dict[str, list[tuple[int, str]]]) -> None:
        """Populate history menu grouped by day."""
        self._history_menu.clear()
        clear_action = self._history_menu.addAction("Clear History")
        clear_action.triggered.connect(self.history_clear_requested.emit)
        saved_menu = self._history_menu.addMenu("Saved Credentials")
        if not groups:
            action = saved_menu.addAction("No successful connections yet")
            action.setEnabled(False)
            return
        for day, entries in groups.items():
            sub = saved_menu.addMenu(day)
            for index, label in entries:
                action = sub.addAction(label)
                action.triggered.connect(lambda checked=False, idx=index: self.history_selected.emit(idx))

    def set_help_info(self, callback) -> None:
        self._help_info_action.triggered.connect(callback)

    @staticmethod
    def _apply_row_color(table: QTableWidget, row: int, status: str) -> None:
        if status.startswith("OK"):
            color = QColor(46, 125, 50, 80)
        elif status.startswith("OFF"):
            color = QColor(198, 40, 40, 80)
        else:
            return
        for col in range(0, 3):
            item = table.item(row, col)
            if item is not None:
                item.setBackground(color)

    def _emit_play_from_row(self, tab_name: str, row: int) -> None:
        table = self.item_tables[tab_name]
        cell = table.item(row, 0)
        if cell is None:
            return
        media = cell.data(Qt.ItemDataRole.UserRole)
        self.item_activated.emit(tab_name, media)

    def _emit_now_playing(self, tab_name: str, row: int) -> None:
        table = self.item_tables[tab_name]
        cell = table.item(row, 0)
        if cell is None:
            return
        media = cell.data(Qt.ItemDataRole.UserRole)
        self.now_playing_requested.emit(tab_name, media)

    def _emit_verify_all_channels(self) -> None:
        """Emit verify all channels for current tab."""
        current_index = self.tab_widget.currentIndex()
        current_tab = self.tab_widget.tabText(current_index)
        if current_tab in ("Live", "Movies", "Series"):
            self.verify_all_channels_requested.emit(current_tab)

    def _emit_verify_tab(self, tab_name: str) -> None:
        """Emit verify request for specific tab."""
        if tab_name in ("Live", "Movies", "Series"):
            self.verify_tab_requested.emit(tab_name)

    def _emit_cancel_verification(self) -> None:
        """Emit cancel verification request."""
        self.verify_cancel_requested.emit()

    def _emit_clear_logs(self) -> None:
        """Emit clear logs request."""
        self.logs_clear_requested.emit()

    # Show logs method removed for performance

    def _emit_save_logs(self) -> None:
        """Emit save logs request."""
        self.logs_save_requested.emit()
