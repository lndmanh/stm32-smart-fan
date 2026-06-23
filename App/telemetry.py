"""Fan telemetry parsing for the STM32 smart-fan dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


PWM_LIMIT = 1599

# DS18B20-style sensors report sentinels such as -127 °C (disconnected) or 85 °C
# (power-on default). Anything outside a sane physical band is treated as "no
# reading" so a single bad sample cannot wreck the auto-scaled temperature chart.
TEMP_VALID_MIN_C = -55.0
TEMP_VALID_MAX_C = 150.0


def temperature_is_valid(temp_c: float) -> bool:
    """Return True when a temperature reading is within a plausible physical band."""
    return TEMP_VALID_MIN_C <= temp_c <= TEMP_VALID_MAX_C


@dataclass(frozen=True)
class FanTelemetrySample:
    timestamp_ms: int
    rps: float
    rpm: float
    target_rpm: float
    pwm: int
    temperature_c: float
    fault_code: int
    state: str


def parse_fan_telemetry_line(raw: str) -> Optional[FanTelemetrySample]:
    """Parse one structured `FAN,...` telemetry line.

    Expected format:
        FAN,<ms>,<rps>,<rpm>,<target_rpm>,<pwm>,<temp_c>,<fault_code>,<state>

    Returns None for debug/status lines and malformed telemetry so the UI can
    log those lines without crashing the serial reader.
    """
    parts = raw.strip().split(",")
    if len(parts) != 9 or parts[0] != "FAN":
        return None

    try:
        pwm = int(float(parts[5]))
        pwm = max(-PWM_LIMIT, min(PWM_LIMIT, pwm))
        state = parts[8].strip() or "UNKNOWN"
        return FanTelemetrySample(
            timestamp_ms=int(parts[1]),
            rps=float(parts[2]),
            rpm=float(parts[3]),
            target_rpm=float(parts[4]),
            pwm=pwm,
            temperature_c=float(parts[6]),
            fault_code=int(parts[7]),
            state=state,
        )
    except ValueError:
        return None


def is_legacy_odometry_line(raw: str) -> bool:
    """Return True when a line uses the previous robot tracker format."""
    return raw.strip().startswith("ODOM,")
