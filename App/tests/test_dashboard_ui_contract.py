import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch


serial_module = types.ModuleType("serial")
serial_module.Serial = object
serial_tools_module = types.ModuleType("serial.tools")
serial_list_ports_module = types.ModuleType("serial.tools.list_ports")
serial_list_ports_module.comports = lambda: []
serial_tools_module.list_ports = serial_list_ports_module
serial_module.tools = serial_tools_module
with patch.dict(
    sys.modules,
    {
        "serial": serial_module,
        "serial.tools": serial_tools_module,
        "serial.tools.list_ports": serial_list_ports_module,
    },
):
    import dashboard_app


class DashboardUIContractTests(unittest.TestCase):
    def test_fan_asset_path_points_at_expected_asset(self):
        expected = Path(dashboard_app.__file__).resolve().parent / "assets" / "fan_model.png"

        self.assertEqual(dashboard_app.FAN_ASSET_PATH, expected)

    def test_metric_keys_are_stable(self):
        self.assertEqual(
            dashboard_app.DASHBOARD_METRIC_KEYS,
            ("rpm", "rps", "target", "pwm", "temperature", "fault", "state"),
        )

    def test_footer_action_labels_are_stable(self):
        self.assertEqual(
            dashboard_app.FOOTER_ACTION_LABELS,
            ("Refresh", "Connect", "Set speed", "Stop", "Reset", "PID", "Help"),
        )

    def test_missing_fan_asset_is_not_available(self):
        missing_asset = Path(dashboard_app.__file__).resolve().parent / "assets" / "missing-fan-model.png"

        self.assertTrue(hasattr(dashboard_app, "fan_asset_is_available"))
        self.assertFalse(dashboard_app.fan_asset_is_available(missing_asset))

    def test_fan_stage_chip_layout_places_overlays_consistently(self):
        self.assertTrue(hasattr(dashboard_app, "fan_stage_chip_layout"))

        positions = dashboard_app.fan_stage_chip_layout(1000, 700)

        self.assertEqual(positions["rpm"], (50.0, 42.0, "nw"))
        self.assertEqual(positions["fault"], (680.0, 532.0, "nw"))


if __name__ == "__main__":
    unittest.main()
