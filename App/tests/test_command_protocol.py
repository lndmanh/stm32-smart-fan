import unittest

from command_protocol import (
    COMMAND_HELP_LINES,
    build_help_command,
    build_pid_command,
    build_reset_faults_command,
    build_set_speed_command,
    build_stop_command,
)


class CommandProtocolTests(unittest.TestCase):
    def test_build_set_speed_command_rounds_to_integer_rpm(self):
        self.assertEqual(build_set_speed_command(150.4), "s150\n")

    def test_build_set_speed_command_clamps_to_safe_range(self):
        self.assertEqual(build_set_speed_command(-20), "s0\n")
        self.assertEqual(build_set_speed_command(500), "s190\n")

    def test_build_pid_command_uses_legacy_single_letter_protocol(self):
        self.assertEqual(build_pid_command("kp", 8.5), "p8.5\n")
        self.assertEqual(build_pid_command("ki", 30), "i30\n")
        self.assertEqual(build_pid_command("kd", 0.5), "d0.5\n")

    def test_build_pid_command_rejects_unknown_gain(self):
        with self.assertRaises(ValueError):
            build_pid_command("kg", 1.0)

    def test_quick_action_commands(self):
        self.assertEqual(build_stop_command(), "x\n")
        self.assertEqual(build_reset_faults_command(), "r\n")
        self.assertEqual(build_help_command(), "?\n")

    def test_help_documents_fix_commands(self):
        joined = "\n".join(COMMAND_HELP_LINES)
        self.assertIn("s150", joined)
        self.assertIn("p35", joined)
        self.assertIn("d0.5", joined)
        self.assertIn("reset", joined.lower())


if __name__ == "__main__":
    unittest.main()
