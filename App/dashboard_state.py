"""In-memory state model for the fan monitoring dashboard."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from time import strftime
from typing import Deque, Optional

from telemetry import FanTelemetrySample, temperature_is_valid


@dataclass(frozen=True)
class LogEntry:
    message: str
    level: str = "info"
    timestamp: str = field(default_factory=lambda: strftime("%H:%M:%S"))


class DashboardState:
    def __init__(self, max_history: int = 240, max_logs: int = 250):
        self.latest: Optional[FanTelemetrySample] = None
        self._speed_points: Deque[tuple[int, float, float]] = deque(maxlen=max_history)
        self._temperature_points: Deque[tuple[int, float]] = deque(maxlen=max_history)
        self._logs: Deque[LogEntry] = deque(maxlen=max_logs)
        self._last_fault_code = 0
        self._log_count = 0

    @property
    def speed_points(self) -> list[tuple[int, float, float]]:
        return list(self._speed_points)

    @property
    def temperature_points(self) -> list[tuple[int, float]]:
        return list(self._temperature_points)

    @property
    def logs(self) -> list[LogEntry]:
        return list(self._logs)

    @property
    def log_count(self) -> int:
        """Total log entries ever recorded, so the UI can append incrementally."""
        return self._log_count

    @property
    def connection_label(self) -> str:
        return "Telemetry live" if self.latest else "Waiting for telemetry"

    def apply_sample(self, sample: FanTelemetrySample) -> None:
        self.latest = sample
        self._speed_points.append((sample.timestamp_ms, sample.rpm, sample.target_rpm))
        if temperature_is_valid(sample.temperature_c):
            self._temperature_points.append((sample.timestamp_ms, sample.temperature_c))

        if sample.fault_code != self._last_fault_code:
            level = "error" if sample.fault_code else "success"
            self.add_log(f"Fault code changed: {self._last_fault_code} → {sample.fault_code}", level)
            self._last_fault_code = sample.fault_code

    def add_log(self, message: str, level: str = "info") -> None:
        self._logs.append(LogEntry(message=message, level=level))
        self._log_count += 1

    def metric_snapshot(self) -> dict[str, str]:
        if self.latest is None:
            return {
                "rpm": "--",
                "rps": "--",
                "target": "--",
                "pwm": "--",
                "temperature": "N/A",
                "fault": "0",
                "state": "Waiting",
            }

        sample = self.latest
        return {
            "rpm": f"{sample.rpm:.1f}",
            "rps": f"{sample.rps:.2f}",
            "target": f"{sample.target_rpm:.0f}",
            "pwm": f"{sample.pwm:d}",
            "temperature": (
                f"{sample.temperature_c:.1f} °C"
                if temperature_is_valid(sample.temperature_c)
                else "N/A"
            ),
            "fault": str(sample.fault_code),
            "state": sample.state,
        }
