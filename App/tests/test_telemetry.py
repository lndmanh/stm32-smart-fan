import unittest

from telemetry import FanTelemetrySample, is_legacy_odometry_line, parse_fan_telemetry_line


class FanTelemetryParsingTests(unittest.TestCase):
    def test_parse_fan_telemetry_line(self):
        sample = parse_fan_telemetry_line("FAN,1200,2.5,150.0,180.0,512,36.7,0,RUN")

        self.assertEqual(
            sample,
            FanTelemetrySample(
                timestamp_ms=1200,
                rps=2.5,
                rpm=150.0,
                target_rpm=180.0,
                pwm=512,
                temperature_c=36.7,
                fault_code=0,
                state="RUN",
            ),
        )

    def test_parse_rejects_debug_lines(self):
        self.assertIsNone(parse_fan_telemetry_line("System Ready"))

    def test_parse_rejects_malformed_fan_lines(self):
        self.assertIsNone(parse_fan_telemetry_line("FAN,1200,not-a-number,150,180,512,36.7,0,RUN"))

    def test_parse_clamps_pwm_to_signed_timer_range(self):
        sample = parse_fan_telemetry_line("FAN,1,0,0,0,-1600,30,2,FAULT")

        self.assertIsNotNone(sample)
        self.assertEqual(sample.pwm, -1599)

    def test_legacy_odometry_detection(self):
        self.assertTrue(is_legacy_odometry_line("ODOM,100,50,50,straight,255"))
        self.assertFalse(is_legacy_odometry_line("FAN,100,1,60,60,200,30,0,RUN"))


if __name__ == "__main__":
    unittest.main()
