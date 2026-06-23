import csv
import tempfile
import unittest
from pathlib import Path

from telemetry import FanTelemetrySample
from telemetry_recorder import TelemetryRecorder


def _sample(**overrides) -> FanTelemetrySample:
    base = dict(
        timestamp_ms=1200,
        rps=2.5,
        rpm=150.0,
        target_rpm=180.0,
        pwm=512,
        temperature_c=36.7,
        fault_code=0,
        state="RUN",
    )
    base.update(overrides)
    return FanTelemetrySample(**base)


class TelemetryRecorderTests(unittest.TestCase):
    def test_records_header_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "telemetry.csv"
            recorder = TelemetryRecorder(path)
            recorder.start()
            recorder.write_sample(_sample())
            recorder.write_sample(_sample(timestamp_ms=1300, rpm=160.0, fault_code=1, state="FAULT"))
            recorder.stop()

            with open(path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(recorder.rows_written, 2)
            self.assertEqual(rows[0]["rpm"], "150.0")
            self.assertEqual(rows[0]["state"], "RUN")
            self.assertEqual(rows[1]["fault_code"], "1")
            self.assertEqual(rows[1]["state"], "FAULT")

    def test_write_without_start_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = TelemetryRecorder(Path(tmp) / "unused.csv")
            recorder.write_sample(_sample())  # must not raise

            self.assertFalse(recorder.is_recording)
            self.assertEqual(recorder.rows_written, 0)

    def test_is_recording_tracks_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = TelemetryRecorder(Path(tmp) / "telemetry.csv")
            self.assertFalse(recorder.is_recording)
            recorder.start()
            self.assertTrue(recorder.is_recording)
            recorder.stop()
            self.assertFalse(recorder.is_recording)


if __name__ == "__main__":
    unittest.main()
