"""Persistent configuration management."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from zone_new_companion.models import Credentials, PortalType


@dataclass(slots=True)
class UiSettings:
    """UI settings persisted between restarts."""

    dark_theme: bool = True
    width: int = 1200
    height: int = 760


@dataclass(slots=True)
class AppConfig:
    """Whole application persisted config."""

    ui: UiSettings = field(default_factory=UiSettings)
    successful_history: list[Credentials] = field(default_factory=list)
    last_input: Credentials | None = None


class ConfigStore:
    """Manage config read/write as JSON."""

    def __init__(self, config_path: Path) -> None:
        self._path = config_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppConfig:
        """Load config from disk."""
        if not self._path.exists():
            return AppConfig()

        with self._path.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        ui_payload = payload.get("ui", {})
        history_payload = payload.get("successful_history", payload.get("profiles", []))
        history = [
            Credentials(
                name=str(row.get("name", "Last Used")),
                base_url=str(row.get("base_url", "")),
                portal_type=PortalType(str(row.get("portal_type", PortalType.XTREAM.value))),
                username=str(row.get("username", "")),
                password=str(row.get("password", "")),
                mac_address=str(row.get("mac_address", "")),
            )
            for row in history_payload
        ]
        last_input_payload = payload.get("last_input")
        last_input = None
        if isinstance(last_input_payload, dict):
            last_input = Credentials(
                name=str(last_input_payload.get("name", "Last Used")),
                base_url=str(last_input_payload.get("base_url", "")),
                portal_type=PortalType(
                    str(last_input_payload.get("portal_type", PortalType.XTREAM.value)),
                ),
                username=str(last_input_payload.get("username", "")),
                password=str(last_input_payload.get("password", "")),
                mac_address=str(last_input_payload.get("mac_address", "")),
            )
        ui = UiSettings(
            dark_theme=bool(ui_payload.get("dark_theme", True)),
            width=int(ui_payload.get("width", 1200)),
            height=int(ui_payload.get("height", 760)),
        )
        return AppConfig(ui=ui, successful_history=history, last_input=last_input)

    def save(self, config: AppConfig) -> None:
        """Safely write config to disk."""
        payload: dict[str, Any] = asdict(config)
        with self._path.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2)
