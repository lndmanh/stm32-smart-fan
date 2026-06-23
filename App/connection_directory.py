"""Friendly serial / Bluetooth device directory for the connection picker.

pyserial hands the dashboard raw device paths like ``/dev/cu.HC-05-DevB`` with
loosely populated metadata. These pure helpers turn that into human-readable
labels, flag Bluetooth links, and give every device a *stable key* so the app
can remember the last-used device and per-device custom names across launches
(even though the OS may hand out a different path next time).
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PortInfo:
    """The subset of pyserial's ``ListPortInfo`` the dashboard cares about."""

    device: str
    description: str = ""
    manufacturer: str = ""
    hwid: str = ""
    serial_number: str | None = None
    vid: int | None = None
    pid: int | None = None


@dataclass(frozen=True)
class PortChoice:
    """A presentation-ready device entry for the picker."""

    device: str          # raw path to open, e.g. /dev/cu.HC-05
    key: str             # stable identity for persistence
    name: str            # friendly, possibly user-customised, unique label
    detail: str          # one-line subtitle (type · path · last-used)
    is_bluetooth: bool
    is_last_used: bool


# Substrings that mark a port as a wireless / Bluetooth serial link.
BLUETOOTH_HINTS = (
    "bluetooth", "rfcomm", "hc-05", "hc-06", "hc05", "hc06",
    "spp", "serial port profile", "wireless", "-devb",
)
_NOISE = ("", "n/a", "na", "none", "unknown")


def _has_hint(text: str) -> bool:
    low = text.lower()
    return any(hint in low for hint in BLUETOOTH_HINTS)


def is_bluetooth_port(info: PortInfo) -> bool:
    return any(_has_hint(field) for field in (info.device, info.description, info.hwid, info.manufacturer))


def port_key(info: PortInfo) -> str:
    """A stable id: prefer USB serial / vid:pid, else fall back to the path."""
    if info.serial_number:
        return f"sn:{info.serial_number}"
    if info.vid is not None and info.pid is not None:
        return f"usb:{info.vid:04x}:{info.pid:04x}"
    return f"dev:{info.device}"


def _basename(device: str) -> str:
    return device.replace("\\", "/").rstrip("/").split("/")[-1]


def _clean_basename(device: str) -> str:
    base = _basename(device)
    for prefix in ("cu.", "tty."):
        if base.lower().startswith(prefix):
            base = base[len(prefix):]
            break
    # Drop the macOS Bluetooth "-DevB"/"-SPPDev" suffixes; keep hyphens so module
    # names like "HC-05" survive. Underscores read better as spaces.
    for suffix in ("-DevB", "-SPPDev"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    base = base.replace("_", " ").strip()
    return base or device


def default_friendly_name(info: PortInfo) -> str:
    """A readable name from the description, else a cleaned-up device path."""
    description = info.description.strip()
    if description.lower() not in _NOISE and description != info.device:
        return description
    return _clean_basename(info.device)


def _detail(info: PortInfo, *, is_bluetooth: bool, is_last_used: bool) -> str:
    parts = ["Bluetooth" if is_bluetooth else "Serial", info.device]
    manufacturer = info.manufacturer.strip()
    if manufacturer.lower() not in _NOISE:
        parts.append(manufacturer)
    detail = " · ".join(parts)
    return f"{detail} · Last used" if is_last_used else detail


def _dedupe_names(choices: list[PortChoice]) -> list[PortChoice]:
    """Keep dropdown labels unique by suffixing collisions with the path."""
    counts: dict[str, int] = {}
    for choice in choices:
        counts[choice.name] = counts.get(choice.name, 0) + 1
    if all(count == 1 for count in counts.values()):
        return choices
    return [
        replace(choice, name=f"{choice.name} ({_basename(choice.device)})") if counts[choice.name] > 1 else choice
        for choice in choices
    ]


def build_port_choices(
    infos,
    *,
    last_key: str | None = None,
    custom_names: dict[str, str] | None = None,
) -> list[PortChoice]:
    """Turn raw :class:`PortInfo` rows into ordered, presentation-ready choices.

    Ordering: the remembered device first, then Bluetooth links, then the rest
    alphabetically — so the device you most likely want sits at the top.
    """
    custom_names = custom_names or {}
    choices: list[PortChoice] = []
    for info in infos:
        key = port_key(info)
        is_bluetooth = is_bluetooth_port(info)
        is_last_used = last_key is not None and key == last_key
        name = custom_names.get(key) or default_friendly_name(info)
        choices.append(
            PortChoice(
                device=info.device,
                key=key,
                name=name,
                detail=_detail(info, is_bluetooth=is_bluetooth, is_last_used=is_last_used),
                is_bluetooth=is_bluetooth,
                is_last_used=is_last_used,
            )
        )
    choices = _dedupe_names(choices)
    choices.sort(key=lambda choice: (not choice.is_last_used, not choice.is_bluetooth, choice.name.lower()))
    return choices
