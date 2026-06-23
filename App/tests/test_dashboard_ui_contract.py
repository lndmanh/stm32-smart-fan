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
            ("Refresh", "Connect", "Set speed", "Stop", "PID", "Reset", "Help"),
        )

    def test_footer_controls_are_grouped_by_workflow(self):
        self.assertTrue(hasattr(dashboard_app, "FOOTER_CONTROL_GROUPS"))

        self.assertEqual(
            dashboard_app.FOOTER_CONTROL_GROUPS,
            (
                ("connection", "Connection", ("refresh", "connect")),
                ("speed", "Speed control", ("set_speed", "stop")),
                ("tuning", "Tune & service", ("pid", "reset", "help")),
            ),
        )

    def test_footer_action_roles_are_consistent(self):
        self.assertTrue(hasattr(dashboard_app, "FOOTER_ACTION_ROLES"))

        self.assertEqual(dashboard_app.FOOTER_ACTION_ROLES["stop"], "danger")
        self.assertEqual(dashboard_app.FOOTER_ACTION_ROLES["connect"], "primary")
        self.assertEqual(dashboard_app.FOOTER_ACTION_ROLES["help"], "secondary")

    def test_footer_action_sequence_comes_from_group_model(self):
        self.assertTrue(hasattr(dashboard_app, "footer_action_sequence"))

        self.assertEqual(
            dashboard_app.footer_action_sequence(),
            ("refresh", "connect", "set_speed", "stop", "pid", "reset", "help"),
        )

    def test_footer_action_model_has_labels_and_roles_for_every_action(self):
        actions = dashboard_app.footer_action_sequence()

        self.assertEqual(len(actions), len(set(actions)))
        self.assertEqual(set(actions), set(dashboard_app.FOOTER_ACTION_LABEL_MAP))
        self.assertEqual(set(actions), set(dashboard_app.FOOTER_ACTION_ROLES))
        self.assertLessEqual(set(dashboard_app.FOOTER_ACTION_ROLES.values()), {"primary", "secondary", "danger"})

    def test_missing_fan_asset_is_not_available(self):
        missing_asset = Path(dashboard_app.__file__).resolve().parent / "assets" / "missing-fan-model.png"

        self.assertTrue(hasattr(dashboard_app, "fan_asset_is_available"))
        self.assertFalse(dashboard_app.fan_asset_is_available(missing_asset))

    def test_fan_modes_expose_auto_and_manual(self):
        self.assertEqual(dashboard_app.FAN_MODES, (("auto", "Auto"), ("manual", "Manual")))
        self.assertEqual(dashboard_app.DEFAULT_MODE, "auto")  # firmware powers up in temp control

    def test_mode_command_builders_match_firmware(self):
        builders = dashboard_app.MODE_COMMAND_BUILDERS

        self.assertEqual(set(builders), {mode_id for mode_id, _ in dashboard_app.FAN_MODES})
        self.assertEqual(builders["auto"](), "a\n")
        self.assertEqual(builders["manual"](), "m\n")

    def test_event_log_tab_is_not_a_mode(self):
        self.assertNotIn(dashboard_app.EVENT_LOG_TAB_LABEL, dashboard_app.MODE_TAB_LABELS)

    def test_fan_stage_chip_layout_places_overlays_consistently(self):
        self.assertTrue(hasattr(dashboard_app, "fan_stage_chip_layout"))

        positions = dashboard_app.fan_stage_chip_layout(1000, 700)

        self.assertEqual(positions["rpm"], (50.0, 42.0, "nw"))
        self.assertEqual(positions["fault"], (680.0, 532.0, "nw"))


if __name__ == "__main__":
    unittest.main()
