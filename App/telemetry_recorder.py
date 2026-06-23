"""CSV recording of the fan telemetry stream for offline analysis / PID tuning."""

from __future__ import annotations

import csv
from pathlib import Path
from time import strftime
from typing import Optional, TextIO

from telemetry import FanTelemetrySample


class TelemetryRecorder:
    """Append fan telemetry samples to a CSV file, one row per sample.

    Rows are flushed as they are written so a crash or unplug still leaves a
    usable file. The wall-clock column makes it easy to line samples up with
    notes taken during a bench session, alongside the firmware's own ``ms``.
    """

    FIELDNAMES = (
        "wall_clock",
        "timestamp_ms",
        "rps",
        "rpm",
        "target_rpm",
        "pwm",
        "temperature_c",
        "fault_code",
        "state",
    )

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._file: Optional[TextIO] = None
        self._writer: Optional[csv.DictWriter] = None
        self.rows_written = 0

    @property
    def is_recording(self) -> bool:
        return self._file is not None

    def start(self) -> None:
        self._file = open(self.path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.FIELDNAMES)
        self._writer.writeheader()
        self._file.flush()
        self.rows_written = 0

    def write_sample(self, sample: FanTelemetrySample) -> None:
        if self._writer is None or self._file is None:
            return
        self._writer.writerow(
            {
                "wall_clock": strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp_ms": sample.timestamp_ms,
                "rps": sample.rps,
                "rpm": sample.rpm,
                "target_rpm": sample.target_rpm,
                "pwm": sample.pwm,
                "temperature_c": sample.temperature_c,
                "fault_code": sample.fault_code,
                "state": sample.state,
            }
        )
        self._file.flush()
        self.rows_written += 1

    def stop(self) -> None:
        if self._file is not None:
            self._file.close()
        self._file = None
        self._writer = None
