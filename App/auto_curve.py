"""Temperature → fan-duty curve, mirrored from the firmware's auto mode.

In automatic mode the firmware drives the H-bridge PWM straight from the live
temperature (see ``TemperatureControlTask`` in ``Core/Src/main.c``): the fan is
idle until ``AUTO_TEMP_START_C``, kicks to a ``AUTO_PWM_MIN`` floor so the blades
actually break loose, then ramps linearly to full power at ``AUTO_TEMP_FULL_C``.

These constants and :func:`temperature_to_duty_percent` reproduce that mapping so
the dashboard's Auto tab can plot the exact curve the board follows and drop a
live marker on it — the indicator never lies about what the firmware will do.
"""

from __future__ import annotations

# Mirror of the firmware constants. Keep in sync with Core/Src/main.c.
AUTO_TEMP_START_C = 20.0   # blades stay idle at or below this
AUTO_TEMP_FULL_C = 50.0    # full power at or above this
AUTO_PWM_MIN = 400.0       # kick floor once the curve engages
AUTO_PWM_MAX = 1599.0      # 100% duty

# Plotting domain for the indicator: a little slack on either side of the ramp.
AUTO_TEMP_AXIS_MIN_C = 10.0
AUTO_TEMP_AXIS_MAX_C = 60.0


def temperature_to_duty_percent(temp_c: float) -> float:
    """Return the firmware's commanded duty (0–100 %) for a temperature."""
    if temp_c <= AUTO_TEMP_START_C:
        return 0.0
    if temp_c >= AUTO_TEMP_FULL_C:
        return 100.0
    ratio = (temp_c - AUTO_TEMP_START_C) / (AUTO_TEMP_FULL_C - AUTO_TEMP_START_C)
    pwm = AUTO_PWM_MIN + ratio * (AUTO_PWM_MAX - AUTO_PWM_MIN)
    return pwm / AUTO_PWM_MAX * 100.0


def auto_curve_points(samples: int = 96) -> list[tuple[float, float]]:
    """Sample the curve across the indicator's temperature axis for plotting."""
    if samples < 2:
        raise ValueError("samples must be at least 2")
    span = AUTO_TEMP_AXIS_MAX_C - AUTO_TEMP_AXIS_MIN_C
    points = []
    for index in range(samples):
        temp = AUTO_TEMP_AXIS_MIN_C + span * index / (samples - 1)
        points.append((temp, temperature_to_duty_percent(temp)))
    return points
