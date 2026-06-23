"""UART command builders for the STM32 smart-fan firmware."""

from __future__ import annotations


MIN_RPM = 0
MAX_RPM = 190

COMMAND_HELP_LINES = [
    "s150   set target speed to 150 RPM",
    "p35    set Kp gain to 35",
    "i100   set Ki gain to 100",
    "d0.5   set Kd gain to 0.5",
    "x      stop fan by setting target speed to 0 RPM",
    "r      reset faults and PID integrator",
    "?      print firmware command help",
]

_PID_PREFIX = {
    "kp": "p",
    "p": "p",
    "ki": "i",
    "i": "i",
    "kd": "d",
    "d": "d",
}


def _format_number(value: float) -> str:
    numeric = float(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.4f}".rstrip("0").rstrip(".")


def build_set_speed_command(rpm: float) -> str:
    target = int(round(float(rpm)))
    target = max(MIN_RPM, min(MAX_RPM, target))
    return f"s{target}\n"


def build_pid_command(gain: str, value: float) -> str:
    prefix = _PID_PREFIX.get(gain.strip().lower())
    if prefix is None:
        raise ValueError(f"Unknown PID gain: {gain}")
    return f"{prefix}{_format_number(value)}\n"


def build_auto_mode_command() -> str:
    """Hand speed control to the firmware's temperature curve."""
    return "a\n"


def build_manual_mode_command() -> str:
    """Take manual control of target RPM / tuning."""
    return "m\n"


def build_stop_command() -> str:
    return "x\n"


def build_reset_faults_command() -> str:
    return "r\n"


def build_help_command() -> str:
    return "?\n"
