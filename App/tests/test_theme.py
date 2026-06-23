import unittest

from theme import (
    TEMP_GRADIENT_STOPS,
    darken,
    lighten,
    mix_color,
    temperature_to_color,
)


class ColorHelperTests(unittest.TestCase):
    def test_mix_color_interpolates_each_channel(self):
        self.assertEqual(mix_color("#000000", "#FFFFFF", 0.0), "#000000")
        self.assertEqual(mix_color("#000000", "#FFFFFF", 1.0), "#FFFFFF")
        self.assertEqual(mix_color("#000000", "#FFFFFF", 0.5), "#808080")

    def test_lighten_and_darken_move_toward_white_and_black(self):
        self.assertEqual(lighten("#808080", 1.0), "#FFFFFF")
        self.assertEqual(darken("#808080", 1.0), "#000000")
        self.assertEqual(lighten("#3366CC", 0.0), "#3366CC")


class TemperatureColorTests(unittest.TestCase):
    def test_clamps_below_and_above_the_stop_range(self):
        coldest_temp, coldest_color = TEMP_GRADIENT_STOPS[0]
        hottest_temp, hottest_color = TEMP_GRADIENT_STOPS[-1]
        self.assertEqual(temperature_to_color(coldest_temp - 50), coldest_color)
        self.assertEqual(temperature_to_color(hottest_temp + 50), hottest_color)

    def test_exact_stops_return_their_palette_color(self):
        for temp, color in TEMP_GRADIENT_STOPS:
            self.assertEqual(temperature_to_color(temp), color)

    def test_between_stops_blends_toward_the_warmer_color(self):
        (t0, c0), (t1, c1) = TEMP_GRADIENT_STOPS[0], TEMP_GRADIENT_STOPS[1]
        midpoint = temperature_to_color((t0 + t1) / 2)
        self.assertNotIn(midpoint, (c0, c1))
        self.assertEqual(midpoint, mix_color(c0, c1, 0.5))


if __name__ == "__main__":
    unittest.main()
