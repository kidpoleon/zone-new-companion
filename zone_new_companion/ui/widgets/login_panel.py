"""Login panel widget."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from zone_new_companion.models import Credentials, PortalType


class LoginPanel(QWidget):
    """Collect connection parameters for both portal types."""

    connect_clicked = pyqtSignal(object)
    reset_clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        self.form_group = QGroupBox("Connection")
        form = QFormLayout(self.form_group)

        self.portal_type_input = QComboBox()
        self.portal_type_input.addItems([PortalType.XTREAM.value, PortalType.STALKER.value])
        self.portal_type_input.setToolTip("Select backend protocol.")
        self.portal_type_input.currentTextChanged.connect(self._update_field_visibility)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("http://example.com")
        self.base_url_input.setToolTip("Server host without spaces.")

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mac_input = QLineEdit()
        self.mac_input.setPlaceholderText("00:11:22:33:44:55")

        form.addRow("Portal", self.portal_type_input)
        form.addRow("Base URL", self.base_url_input)
        form.addRow("Username", self.username_input)
        form.addRow("Password", self.password_input)
        form.addRow("MAC", self.mac_input)
        root.addWidget(self.form_group)
        root.addWidget(self._divider())

        self.info_group = QGroupBox("Credential Information")
        info_layout = QVBoxLayout(self.info_group)
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setToolTip("Shows details for the last successful connection.")
        self.info_box.setPlaceholderText(
            "Connect successfully to view expiry, connections, domain, ports, timezone, and account status.",
        )
        info_layout.addWidget(self.info_box)
        root.addWidget(self.info_group, 1)

        buttons = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.setToolTip("Validate and load playlist.")
        self.reset_button = QPushButton("Reset")
        self.reset_button.setToolTip("Clear form fields.")
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.reset_button)
        root.addLayout(buttons)

        self.connect_button.clicked.connect(self._emit_credentials)
        self.reset_button.clicked.connect(self.reset_clicked.emit)
        self._update_field_visibility(self.portal_type_input.currentText())

    def _emit_credentials(self) -> None:
        portal = PortalType(self.portal_type_input.currentText())
        payload = Credentials(
            name="Last Used",
            base_url=self.base_url_input.text().strip(),
            portal_type=portal,
            username=self.username_input.text().strip(),
            password=self.password_input.text().strip(),
            mac_address=self.mac_input.text().strip(),
        )
        self.connect_clicked.emit(payload)

    def clear(self) -> None:
        """Clear all editable fields."""
        for edit in (
            self.base_url_input,
            self.username_input,
            self.password_input,
            self.mac_input,
        ):
            edit.clear()
        self.info_box.clear()

    def set_connection_info(self, info_map: dict[str, str]) -> None:
        """Render key/value details in the info panel."""
        if not info_map:
            self.info_box.setPlainText("No connection details yet.")
            return
        lines = [f"{key}: {value}" for key, value in info_map.items()]
        self.info_box.setPlainText("\n".join(lines))

    @staticmethod
    def _divider() -> QFrame:
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        return divider

    def _update_field_visibility(self, portal_name: str) -> None:
        is_stalker = portal_name == PortalType.STALKER.value
        self.username_input.setEnabled(not is_stalker)
        self.password_input.setEnabled(not is_stalker)
        self.mac_input.setEnabled(is_stalker)
        self.username_input.setToolTip(
            "Required for Xtream connections." if not is_stalker else "Not required for Stalker mode.",
        )
        self.password_input.setToolTip(
            "Required for Xtream connections." if not is_stalker else "Not required for Stalker mode.",
        )
        self.mac_input.setToolTip(
            "Required for Stalker mode." if is_stalker else "Not required for Xtream mode.",
        )
