"""Main UI shell."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zone_new_companion.models import Credentials, EpgEntry
from zone_new_companion.state import AppState
from zone_new_companion.ui.widgets.login_panel import LoginPanel
from zone_new_companion.ui.widgets.toast import ToastLabel
from zone_new_companion import __version__


class MainWindow(QMainWindow):
    """Main application window."""

    connect_requested = pyqtSignal(object)
    category_selected = pyqtSignal(str, object)
    item_activated = pyqtSignal(str, object)
    live_epg_requested = pyqtSignal(object)
    back_requested = pyqtSignal(str)
    reset_requested = pyqtSignal()
    history_selected = pyqtSignal(int)
    verify_requested = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"zone-new-companion v{__version__}")
        self.setMinimumSize(1000, 650)
        self._history_menu = QMenu("History", self)
        self.menuBar().addMenu(self._history_menu)
        self._tools_menu = QMenu("Tools", self)
        self.menuBar().addMenu(self._tools_menu)
        self._verify_action = self._tools_menu.addAction("Verify Current Tab Streams")
        self._verify_action.triggered.connect(self._emit_verify_current_tab)

        self._toast = ToastLabel(self)
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        self.splitter = QSplitter()
        layout.addWidget(self.splitter)

        self.login_panel = LoginPanel()
        self.login_panel.connect_clicked.connect(self.connect_requested.emit)
        self.login_panel.reset_clicked.connect(self._confirm_reset)
        self.splitter.addWidget(self.login_panel)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.tab_widget = QTabWidget()
        self.category_lists: dict[str, QListWidget] = {}
        self.item_lists: dict[str, QListWidget] = {}
        for tab_name in ("Live", "Movies", "Series"):
            tab = QWidget()
            tab_layout = QHBoxLayout(tab)
            categories = QListWidget()
            categories.setToolTip("Category list")
            items = QListWidget()
            items.setToolTip("Items list")
            tab_layout.addWidget(categories, 1)
            tab_layout.addWidget(items, 2)
            if tab_name == "Live":
                epg_panel = self._build_epg_panel()
                tab_layout.addWidget(epg_panel, 2)
            self.tab_widget.addTab(tab, tab_name)
            self.category_lists[tab_name] = categories
            self.item_lists[tab_name] = items

            categories.itemClicked.connect(
                lambda item, name=tab_name: self.category_selected.emit(name, item.data(Qt.ItemDataRole.UserRole)),
            )
            if tab_name == "Live":
                items.itemClicked.connect(
                    lambda item: self.live_epg_requested.emit(item.data(Qt.ItemDataRole.UserRole)),
                )
            items.itemDoubleClicked.connect(
                lambda item, name=tab_name: self.item_activated.emit(name, item.data(Qt.ItemDataRole.UserRole)),
            )
            items.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            items.customContextMenuRequested.connect(lambda _pos, name=tab_name: self.back_requested.emit(name))
        right_layout.addWidget(self.tab_widget)
        self.splitter.addWidget(right)
        self.splitter.setSizes([320, 900])

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
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
        self.progress.setVisible(state.busy)
        self.login_panel.set_connection_info(state.credential_info)
        for tab_name, categories in state.categories.items():
            list_widget = self.category_lists[tab_name]
            list_widget.clear()
            for category in categories:
                item = QListWidgetItem(category.name)
                item.setData(Qt.ItemDataRole.UserRole, category)
                list_widget.addItem(item)
        for tab_name, items in state.current_items.items():
            list_widget = self.item_lists[tab_name]
            list_widget.clear()
            for media in items:
                status = state.verification_results.get(tab_name, {}).get(media.id, "")
                text = media.name if not status else f"[{status}] {media.name}"
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, media)
                item.setToolTip(status or media.name)
                list_widget.addItem(item)
        self._render_epg(state.live_epg)

    def notify(self, text: str) -> None:
        """Show toast notification."""
        self._toast.show_message(text)

    def populate_form(self, credentials: Credentials) -> None:
        """Load credentials into form."""
        self.login_panel.portal_type_input.setCurrentText(credentials.portal_type.value)
        self.login_panel.base_url_input.setText(credentials.base_url)
        self.login_panel.username_input.setText(credentials.username)
        self.login_panel.password_input.setText(credentials.password)
        self.login_panel.mac_input.setText(credentials.mac_address)

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

    def _build_epg_panel(self) -> QWidget:
        holder = QWidget()
        epg_layout = QVBoxLayout(holder)
        title = QLabel("EPG Guide (Local Time)")
        title.setToolTip("Shows previous and upcoming programs in machine timezone.")
        epg_layout.addWidget(title)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        epg_layout.addWidget(divider)
        self.live_epg_box = QTextEdit()
        self.live_epg_box.setReadOnly(True)
        self.live_epg_box.setPlaceholderText("Select a live channel to load EPG.")
        epg_layout.addWidget(self.live_epg_box)
        return holder

    def _render_epg(self, entries: list[EpgEntry]) -> None:
        if not hasattr(self, "live_epg_box"):
            return
        if not entries:
            self.live_epg_box.setPlainText("No EPG data for this channel.")
            return
        lines: list[str] = []
        now = datetime.now().astimezone()
        for row in entries:
            marker = "NOW" if row.start_at <= now <= row.end_at else "   "
            lines.append(
                f"[{marker}] {row.start_at.strftime('%Y-%m-%d %H:%M')} - "
                f"{row.end_at.strftime('%H:%M')} | {row.title}",
            )
        self.live_epg_box.setPlainText("\n".join(lines))

    def _emit_verify_current_tab(self) -> None:
        tab_name = self.tab_widget.tabText(self.tab_widget.currentIndex())
        self.verify_requested.emit(tab_name)
