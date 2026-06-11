# STM32F401RE PID Motor Control Project

## Overview
This project implements a digital PID speed controller for a DC motor using STM32F401RE.

Features:
- Closed-loop motor speed control
- Encoder feedback
- PWM motor driving
- Runtime PID tuning via UART
- Multiple protection mechanisms
- Interrupt-based control loop
- Register-level STM32 programming (without HAL)

---

# Hardware

## MCU
- STM32F401RE
- System clock: 16 MHz (HSI)

## Motor Driver
- L298N

## Motor
- DC motor
- 6V
- 150 RPM

## Encoder
- Quadrature encoder
- PPR = 2800

---

# Peripheral Usage

## TIM1
Used for PWM generation.

- PWM frequency: 10 kHz
- PWM output pin:
  - PA8 = TIM1_CH1

Motor direction pins:
- PA9  = DIR1
- PA10 = DIR2

---

## TIM2
Used in encoder interface mode.

Encoder pins:
- PA0 = Encoder Channel A
- PA1 = Encoder Channel B

Used for:
- Encoder counting
- Speed feedback

---

## TIM3
Used as periodic PID interrupt source.

Configuration:
- PID loop frequency: 100 Hz
- Sampling time: 10 ms

Responsibilities:
- Read encoder count
- Calculate motor speed
- Execute PID algorithm
- Update PWM output
- Run protection logic

---

## USART2
Used for UART communication.

Baudrate:
- 115200

Purpose:
- Runtime PID tuning
- Debug printing
- Setpoint control

Supported commands:
- s150 -> set speed to 150 RPM
- p35 -> set Kp
- i100 -> set Ki
- d0.5 -> set Kd
- x -> stop fan by setting target speed to 0 RPM
- r -> reset faults
- ? -> print firmware command help

Structured dashboard telemetry:

```text
FAN,<ms>,<rps>,<rpm>,<target_rpm>,<pwm>,<temp_c>,<fault_code>,<state>
```

Example:

```text
FAN,1200,2.50,150.0,180.0,512,36.7,0,RUN
```

`temp_c` is currently simulated in firmware so the monitoring dashboard can be used before a physical temperature sensor is added.

---

# PID Controller

## PID Equation
u = Kp*e + Ki*integral(e) + Kd*derivative(e)

Where:
- e = setpoint - current_speed

Default gains:
- Kp = 35
- Ki = 100
- Kd = 0.5

---

# Speed Calculation

Motor speed is calculated from encoder count difference.

Formula:
speed_rpm = (delta_count * 60) / (PPR * Ts)

Where:
- PPR = 2800
- Ts = 0.01 s

---

# Anti-Windup

Anti-windup is implemented.

When PWM output saturates:
- Integral accumulation is canceled
- Prevents excessive integral growth

---

# Protection Mechanisms

## Stall Detection
Triggered when:
- PWM duty > 800
- Speed < 5 RPM
- Condition persists for 20 PID cycles

---

## Over-Speed Protection
Triggered when:
- Speed exceeds ±190 RPM

---

# Software Architecture

Main loop responsibilities:
- UART command parsing
- Status printing

TIM3 interrupt responsibilities:
- Execute real-time PID control
- Read encoder
- Apply protection logic
- Update motor PWM

---

# Programming Style

This project uses:
- Register-level STM32 programming
- Interrupt-based real-time control
- No HAL drivers
- Deterministic timing using hardware timers

---

# Important Notes For AI Assistant

Only modify:
- application logic
- PID code
- USER CODE sections

Avoid modifying:
- clock configuration
- peripheral initialization unless requested
- generated startup code

The control loop must remain interrupt-based with fixed sampling time.

---

# Desktop Dashboard App

The Python app in `App/` is a Bluetooth/serial dashboard for live fan monitoring.

Install dependencies:

```bash
pip install pyserial matplotlib
```

Run the dashboard:

```bash
python3 App/do_line.py
```

Run Python checks:

```bash
PYTHONPATH=App python3 -m unittest discover App/tests -v
python3 -m py_compile App/*.py
```

Build firmware from STM32CubeIDE or with the generated Debug makefile after the local ARM GCC toolchain and linker script path are configured:

```bash
make -C Debug all
```
