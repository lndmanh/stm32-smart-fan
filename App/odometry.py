"""Differential-drive telemetry parsing and odometry integration.

The Arduino emits lines in this format:

    ODOM,<millis>,<left_pwm>,<right_pwm>,<direction>,<sensor_bits>

The GUI keeps this module separate so the math can be tested without Tkinter,
Matplotlib, Bluetooth hardware, or the robot.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


MIDDLE_SENSOR_MASK = 0b00111100  # S2..S5, because S0 is stored in bit 7.
LEFT_TURN_SENSOR_MASK = 0b11000000  # S0..S1.
RIGHT_TURN_SENSOR_MASK = 0b00000011  # S6..S7.


@dataclass(frozen=True)
class TelemetrySample:
    timestamp_ms: int
    left_pwm: int
    right_pwm: int
    direction: str
    sensor_bits: int


@dataclass(frozen=True)
class Pose:
    x_m: float
    y_m: float
    theta_rad: float


def classify_line_event(direction: str, sensor_bits: int) -> Optional[str]:
    # Ép server CHỈ tin vào string được gửi từ hàm sendTelemetry của Arduino
    if direction == "turn_left":
        return "turn_left"
    if direction == "turn_right":
        return "turn_right"
    if direction == "straight":
        return "straight"
    
    # Trả về straight cho tất cả các trường hợp nhiễu rác còn lại
    return "straight"


class LineMapTracker:
    """Build a crisp 90-degree map from line sensors and explicit turn events."""

    def __init__(self, step_m: float = 0.02):
        self.step_m = step_m
        self.pose = Pose(0.0, 0.0, 0.0)
        self.path = [self.pose]
        self._last_event: Optional[str] = None

    @property
    def path_x(self) -> list[float]:
        return [p.x_m for p in self.path]

    @property
    def path_y(self) -> list[float]:
        return [p.y_m for p in self.path]

    @property
    def theta_rad(self) -> float:
        return self.pose.theta_rad

    def reset(self) -> None:
        self.pose = Pose(0.0, 0.0, 0.0)
        self.path = [self.pose]
        self._last_event = None

    def update(self, direction: str, sensor_bits: int) -> Pose:
        event = classify_line_event(direction, sensor_bits)
        if event is None:
            self._last_event = None
            return self.pose

        if event == "straight":
            self._advance_straight()
        elif event in {"turn_left", "turn_right"} and event != self._last_event:
            self._turn_90(event)

        self._last_event = event
        return self.pose

    def _advance_straight(self) -> None:
        x = self.pose.x_m + self.step_m * math.cos(self.pose.theta_rad)
        y = self.pose.y_m + self.step_m * math.sin(self.pose.theta_rad)
        self.pose = Pose(round(x, 12), round(y, 12), self.pose.theta_rad)
        self.path.append(self.pose)

    def _turn_90(self, event: str) -> None:
        delta = math.pi / 2 if event == "turn_left" else -math.pi / 2
        theta = self.pose.theta_rad + delta
        theta = math.atan2(math.sin(theta), math.cos(theta))
        self.pose = Pose(self.pose.x_m, self.pose.y_m, theta)


def parse_telemetry_line(raw: str) -> Optional[TelemetrySample]:
    """Parse one Bluetooth line, ignoring status/debug messages.

    Returning None for non-telemetry lines lets the GUI continue to log normal
    Arduino messages such as "System Ready!" without treating them as errors.
    """
    parts = raw.strip().split(",")
    if len(parts) != 6 or parts[0] != "ODOM":
        return None

    try:
        return TelemetrySample(
            timestamp_ms=int(parts[1]),
            left_pwm=int(parts[2]),
            right_pwm=int(parts[3]),
            direction=parts[4],
            sensor_bits=int(parts[5]),
        )
    except ValueError:
        return None


class DifferentialDriveOdometry:
    """Estimate robot pose from timestamped left/right PWM commands.

    This is command-based dead reckoning, not true encoder odometry. It is still
    much better than the previous fixed-DT parser because it uses structured
    telemetry, real sample timestamps, and arc integration during turns.
    """

    def __init__(
        self,
        wheel_base_m: float,
        pwm_to_mps: float,
        max_dt_s: float = 0.5,
    ):
        self.wheel_base_m = wheel_base_m
        self.pwm_to_mps = pwm_to_mps
        self.max_dt_s = max_dt_s
        self.pose = Pose(0.0, 0.0, 0.0)
        self.path = [self.pose]
        self._last_timestamp_ms: Optional[int] = None

    def reset(self) -> None:
        self.pose = Pose(0.0, 0.0, 0.0)
        self.path = [self.pose]
        self._last_timestamp_ms = None

    def update_from_sample(self, sample: TelemetrySample) -> Pose:
        return self.update_from_pwm(sample.timestamp_ms, sample.left_pwm, sample.right_pwm)

    def update_from_pwm(self, timestamp_ms: int, left_pwm: int, right_pwm: int) -> Pose:
        if self._last_timestamp_ms is None:
            self._last_timestamp_ms = timestamp_ms
            return self.pose

        dt_s = (timestamp_ms - self._last_timestamp_ms) / 1000.0
        self._last_timestamp_ms = timestamp_ms

        if dt_s <= 0.0 or dt_s > self.max_dt_s:
            return self.pose

        left_distance_m = left_pwm * self.pwm_to_mps * dt_s
        right_distance_m = right_pwm * self.pwm_to_mps * dt_s
        return self.update_from_wheel_distances(left_distance_m, right_distance_m)

    def update_from_wheel_distances(self, left_distance_m: float, right_distance_m: float) -> Pose:
        x, y, theta = self.pose.x_m, self.pose.y_m, self.pose.theta_rad
        delta_theta = (right_distance_m - left_distance_m) / self.wheel_base_m
        delta_s = (right_distance_m + left_distance_m) / 2.0

        if abs(delta_theta) < 1e-9:
            x += delta_s * math.cos(theta)
            y += delta_s * math.sin(theta)
        else:
            radius = delta_s / delta_theta
            next_theta = theta + delta_theta
            x += radius * (math.sin(next_theta) - math.sin(theta))
            y -= radius * (math.cos(next_theta) - math.cos(theta))
            theta = next_theta

        theta = math.atan2(math.sin(theta), math.cos(theta))
        self.pose = Pose(x, y, theta)
        self.path.append(self.pose)
        return self.pose