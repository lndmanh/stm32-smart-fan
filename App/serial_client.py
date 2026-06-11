"""Bluetooth/serial transport for the fan dashboard."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import serial
import serial.tools.list_ports


LineCallback = Callable[[str], None]
StatusCallback = Callable[[str], None]
ErrorCallback = Callable[[Exception], None]


class SerialClient:
    def __init__(
        self,
        baud_rate: int = 115200,
        on_line: Optional[LineCallback] = None,
        on_status: Optional[StatusCallback] = None,
        on_error: Optional[ErrorCallback] = None,
    ):
        self.baud_rate = baud_rate
        self.on_line = on_line
        self.on_status = on_status
        self.on_error = on_error
        self._serial: Optional[serial.Serial] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    @staticmethod
    def list_ports() -> list[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

    @property
    def is_connected(self) -> bool:
        return bool(self._serial and self._serial.is_open and self._running)

    def connect(self, port: str) -> None:
        self.disconnect()
        self._serial = serial.Serial(port, self.baud_rate, timeout=0.2)
        time.sleep(1.2)
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        self._emit_status(f"Connected to {port} @ {self.baud_rate}")

    def disconnect(self) -> None:
        self._running = False
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
            self._serial = None
        self._emit_status("Disconnected")

    def send(self, command: str) -> None:
        payload = command.encode("utf-8")
        with self._lock:
            if not self._serial or not self._serial.is_open:
                raise RuntimeError("Serial port is not connected")
            self._serial.write(payload)

    def _read_loop(self) -> None:
        while self._running:
            try:
                with self._lock:
                    serial_port = self._serial
                if not serial_port or not serial_port.is_open:
                    time.sleep(0.05)
                    continue

                raw = serial_port.readline()
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                if line and self.on_line:
                    self.on_line(line)
            except Exception as exc:  # keep the background reader alive
                self._emit_error(exc)
                time.sleep(0.1)

    def _emit_status(self, message: str) -> None:
        if self.on_status:
            self.on_status(message)

    def _emit_error(self, exc: Exception) -> None:
        if self.on_error:
            self.on_error(exc)
