import unittest

from dashboard_state import DashboardState
from telemetry import FanTelemetrySample


class DashboardStateTests(unittest.TestCase):
    def test_apply_sample_updates_latest_and_rolling_history(self):
        state = DashboardState(max_history=2)

        state.apply_sample(FanTelemetrySample(1, 1.0, 60.0, 120.0, 300, 30.0, 0, "RUN"))
        state.apply_sample(FanTelemetrySample(2, 2.0, 120.0, 120.0, 350, 31.0, 0, "RUN"))
        state.apply_sample(FanTelemetrySample(3, 3.0, 180.0, 120.0, 400, 32.0, 1, "FAULT"))

        self.assertEqual(state.latest.fault_code, 1)
        self.assertEqual(state.speed_points, [(2, 120.0, 120.0), (3, 180.0, 120.0)])
        self.assertEqual(state.temperature_points, [(2, 31.0), (3, 32.0)])
        self.assertEqual(state.connection_label, "Telemetry live")

    def test_metric_snapshot_uses_empty_state_before_first_sample(self):
        snapshot = DashboardState(max_history=2).metric_snapshot()

        self.assertEqual(snapshot["rpm"], "--")
        self.assertEqual(snapshot["temperature"], "N/A")
        self.assertEqual(snapshot["state"], "Waiting")

    def test_metric_snapshot_formats_latest_values(self):
        state = DashboardState(max_history=2)
        state.apply_sample(FanTelemetrySample(42, 2.25, 135.2, 150.0, 456, 37.4, 0, "RUN"))

        snapshot = state.metric_snapshot()

        self.assertEqual(snapshot["rpm"], "135.2")
        self.assertEqual(snapshot["rps"], "2.25")
        self.assertEqual(snapshot["target"], "150")
        self.assertEqual(snapshot["pwm"], "456")
        self.assertEqual(snapshot["temperature"], "37.4 °C")
        self.assertEqual(snapshot["state"], "RUN")

    def test_log_history_is_bounded(self):
        state = DashboardState(max_logs=2)

        state.add_log("first")
        state.add_log("second")
        state.add_log("third")

        self.assertEqual([entry.message for entry in state.logs], ["second", "third"])


if __name__ == "__main__":
    unittest.main()
