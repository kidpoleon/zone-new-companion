"""Login panel widget."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from zone_new_companion.models import Credentials, PortalType


class LoginPanel(QWidget):
    """Collect connection parameters for XTREAM, M3U, and STALKER APIs."""

    connect_clicked = pyqtSignal(object)
    reset_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # Create tab widget for different connection types
        self.tab_widget = QTabWidget()
        
        # XTREAM API Tab
        self.xtream_group = QGroupBox("XTREAM API")
        xtream_form = QFormLayout()
        self.xtream_group.setLayout(xtream_form)

        self.xtream_base_url = QLineEdit()
        self.xtream_base_url.setPlaceholderText("http://example.com:8080")
        self.xtream_base_url.setToolTip("XTREAM server URL without trailing slash")

        self.xtream_username = QLineEdit()
        self.xtream_password = QLineEdit()
        self.xtream_password.setEchoMode(QLineEdit.EchoMode.Password)

        xtream_form.addRow("Server URL", self.xtream_base_url)
        xtream_form.addRow("Username", self.xtream_username)
        xtream_form.addRow("Password", self.xtream_password)

        # M3U Tab
        self.m3u_group = QGroupBox("M3U Playlist")
        m3u_form = QFormLayout()
        self.m3u_group.setLayout(m3u_form)

        self.m3u_url = QLineEdit()
        self.m3u_url.setPlaceholderText("http://example.com/playlist.m3u8 or get.php?...")
        self.m3u_url.setToolTip("M3U playlist URL or XTREAM get.php URL")

        m3u_form.addRow("Playlist URL", self.m3u_url)

        # STALKER API Tab
        self.stalker_group = QGroupBox("STALKER API")
        stalker_form = QFormLayout()
        self.stalker_group.setLayout(stalker_form)

        self.stalker_base_url = QLineEdit()
        self.stalker_base_url.setPlaceholderText("http://example.com/stalker")
        self.stalker_base_url.setToolTip("STALKER portal URL")

        self.stalker_mac = QLineEdit()
        self.stalker_mac.setPlaceholderText("00:11:22:33:44:55")
        self.stalker_mac.setToolTip("MAC address for STALKER authentication")

        stalker_form.addRow("Portal URL", self.stalker_base_url)
        stalker_form.addRow("MAC Address", self.stalker_mac)

        # Add tabs
        self.tab_widget.addTab(self.xtream_group, "XTREAM API")
        self.tab_widget.addTab(self.m3u_group, "M3U")
        self.tab_widget.addTab(self.stalker_group, "STALKER API")

        # Buttons
        buttons_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.setToolTip("Connect using selected configuration")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Clear all form fields")
        buttons_layout.addWidget(self.connect_button)
        buttons_layout.addWidget(self.reset_button)

        # Info panel
        self.info_group = QGroupBox("Connection Information")
        info_layout = QVBoxLayout()
        self.info_group.setLayout(info_layout)
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setToolTip("Shows details for the last successful connection")
        self.info_box.setPlaceholderText(
            "Connect successfully to view connection details and account information."
        )
        self.info_box.setMaximumHeight(120)
        info_layout.addWidget(self.info_box)

        # Add everything to main layout
        root.addWidget(self.tab_widget)
        root.addLayout(buttons_layout)
        root.addWidget(self.info_group)

        # Connect signals
        self.connect_button.clicked.connect(self._emit_credentials)
        self.reset_button.clicked.connect(self.reset_clicked.emit)


    def _emit_credentials(self) -> None:
        """Emit credentials based on current tab."""
        current_tab = self.tab_widget.currentIndex()
        
        if current_tab == 0:  # XTREAM API
            portal = PortalType.XTREAM
            base_url = self.xtream_base_url.text().strip()
            username = self.xtream_username.text().strip()
            password = self.xtream_password.text().strip()
            mac_address = ""
        elif current_tab == 1:  # M3U
            portal = PortalType.M3U
            base_url = self.m3u_url.text().strip()
            username = ""
            password = ""
            mac_address = ""
        else:  # STALKER API
            portal = PortalType.STALKER
            base_url = self.stalker_base_url.text().strip()
            username = ""
            password = ""
            mac_address = self.stalker_mac.text().strip()

        payload = Credentials(
            name="Last Used",
            base_url=base_url,
            portal_type=portal,
            username=username,
            password=password,
            mac_address=mac_address,
        )
        self.connect_clicked.emit(payload)

    def clear(self) -> None:
        """Clear all editable fields."""
        self.xtream_base_url.clear()
        self.xtream_username.clear()
        self.xtream_password.clear()
        self.m3u_url.clear()
        self.stalker_base_url.clear()
        self.stalker_mac.clear()
        self.info_box.clear()

    def set_connection_info(self, info_map: dict[str, str]) -> None:
        """Render key/value details in the info panel."""
        if not info_map:
            self.info_box.setPlainText("No connection details yet.")
            return
        lines = [f"{key}: {value}" for key, value in info_map.items()]
        self.info_box.setPlainText("\n".join(lines))

    def populate_form(self, credentials: Credentials) -> None:
        """Load credentials into appropriate form fields."""
        if credentials.portal_type == PortalType.XTREAM:
            self.tab_widget.setCurrentIndex(0)
            self.xtream_base_url.setText(credentials.base_url)
            self.xtream_username.setText(credentials.username)
            self.xtream_password.setText(credentials.password)
        elif credentials.portal_type == PortalType.M3U:
            self.tab_widget.setCurrentIndex(1)
            self.m3u_url.setText(credentials.base_url)
        elif credentials.portal_type == PortalType.STALKER:
            self.tab_widget.setCurrentIndex(2)
            self.stalker_base_url.setText(credentials.base_url)
            self.stalker_mac.setText(credentials.mac_address)
