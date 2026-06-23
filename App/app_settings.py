"""Persisted dashboard preferences (last device, custom names, auto-reconnect).

A tiny best-effort JSON store under the user's home directory. Loading is
defensive — a missing or corrupt file yields defaults rather than an error —
and saving never raises, because preferences must never crash the app.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppSettings:
    last_port_key: str | None = None
    custom_names: dict[str, str] = field(default_factory=dict)
    auto_reconnect: bool = False


def default_settings_path() -> Path:
    return Path.home() / ".stm32_smart_fan" / "settings.json"


class SettingsStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> AppSettings:
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return AppSettings()
        if not isinstance(data, dict):
            return AppSettings()
        raw_names = data.get("custom_names")
        custom_names = (
            {str(key): str(value) for key, value in raw_names.items()}
            if isinstance(raw_names, dict)
            else {}
        )
        last_port_key = data.get("last_port_key")
        return AppSettings(
            last_port_key=str(last_port_key) if last_port_key else None,
            custom_names=custom_names,
            auto_reconnect=bool(data.get("auto_reconnect", False)),
        )

    def save(self, settings: AppSettings) -> None:
        payload = {
            "last_port_key": settings.last_port_key,
            "custom_names": settings.custom_names,
            "auto_reconnect": settings.auto_reconnect,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(payload, indent=2), "utf-8")
        except OSError:
            pass  # preferences are best-effort; never crash the app
