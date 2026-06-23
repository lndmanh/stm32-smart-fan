import unittest

from auto_curve import (
    AUTO_PWM_MAX,
    AUTO_PWM_MIN,
    AUTO_TEMP_AXIS_MAX_C,
    AUTO_TEMP_AXIS_MIN_C,
    AUTO_TEMP_FULL_C,
    AUTO_TEMP_START_C,
    auto_curve_points,
    temperature_to_duty_percent,
)


class AutoCurveTests(unittest.TestCase):
    def test_fan_idle_at_or_below_start_temperature(self):
        self.assertEqual(temperature_to_duty_percent(AUTO_TEMP_START_C), 0.0)
        self.assertEqual(temperature_to_duty_percent(0.0), 0.0)
        self.assertEqual(temperature_to_duty_percent(-1000.0), 0.0)  # sensor error sentinel

    def test_full_power_at_or_above_full_temperature(self):
        self.assertEqual(temperature_to_duty_percent(AUTO_TEMP_FULL_C), 100.0)
        self.assertEqual(temperature_to_duty_percent(120.0), 100.0)

    def test_curve_kicks_to_pwm_floor_just_above_start(self):
        # Just past the start temp the firmware jumps to its PWM floor, not 0%.
        duty = temperature_to_duty_percent(AUTO_TEMP_START_C + 0.001)
        self.assertAlmostEqual(duty, AUTO_PWM_MIN / AUTO_PWM_MAX * 100.0, places=2)

    def test_midpoint_matches_linear_pwm_interpolation(self):
        midpoint = (AUTO_TEMP_START_C + AUTO_TEMP_FULL_C) / 2
        expected_pwm = AUTO_PWM_MIN + 0.5 * (AUTO_PWM_MAX - AUTO_PWM_MIN)
        self.assertAlmostEqual(
            temperature_to_duty_percent(midpoint),
            expected_pwm / AUTO_PWM_MAX * 100.0,
            places=4,
        )

    def test_curve_points_span_the_axis_and_stay_bounded(self):
        points = auto_curve_points(samples=50)

        self.assertEqual(len(points), 50)
        self.assertEqual(points[0][0], AUTO_TEMP_AXIS_MIN_C)
        self.assertEqual(points[-1][0], AUTO_TEMP_AXIS_MAX_C)
        self.assertTrue(all(0.0 <= duty <= 100.0 for _temp, duty in points))

    def test_curve_points_rejects_degenerate_sample_count(self):
        with self.assertRaises(ValueError):
            auto_curve_points(samples=1)


if __name__ == "__main__":
    unittest.main()
