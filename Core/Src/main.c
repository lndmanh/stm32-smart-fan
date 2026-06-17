#include "main.h"
#include "hardware.h"
#include "pid_controller.h"
#include "system_config.h"
#include "sensor.h"
#include <stdint.h>
#include <stdlib.h>

#define TELEMETRY_PERIOD_MS 200U
#define TEMP_CONTROL_PERIOD_MS 1000U
#define CMD_BUFFER_SIZE 32U
#define TEMP_SENSOR_ERROR_VALUE -1000.0f

#define FAN_TEMP_START_C 30.0f
#define FAN_TEMP_MAX_C   50.0f
#define FAN_MIN_RPM      60.0f
#define FAN_MAX_RPM      180.0f

static float latest_temperature_c = TEMP_SENSOR_ERROR_VALUE;
static uint8_t temperature_control_enabled = 1U;

static void UART_WriteUnsigned(uint32_t value) {
    char digits[10];
    uint32_t index = 0U;

    if (value == 0U) {
        UART2_WriteChar('0');
        return;
    }

    while (value > 0U && index < sizeof(digits)) {
        digits[index++] = (char)('0' + (value % 10U));
        value /= 10U;
    }

    while (index > 0U) {
        UART2_WriteChar(digits[--index]);
    }
}

static void UART_WriteSigned(int32_t value) {
    if (value < 0) {
        UART2_WriteChar('-');
        UART_WriteUnsigned((uint32_t)(-value));
    } else {
        UART_WriteUnsigned((uint32_t)value);
    }
}

static void UART_WriteScaled(float value, uint32_t decimals) {
    uint32_t scale = 1U;
    for (uint32_t i = 0U; i < decimals; i++) {
        scale *= 10U;
    }

    int32_t scaled = (int32_t)(value * (float)scale + (value >= 0.0f ? 0.5f : -0.5f));
    if (scaled < 0) {
        UART2_WriteChar('-');
        scaled = -scaled;
    }

    UART_WriteUnsigned((uint32_t)scaled / scale);
    if (decimals > 0U) {
        UART2_WriteChar('.');
        uint32_t fraction = (uint32_t)scaled % scale;
        uint32_t divisor = scale / 10U;
        while (divisor > 0U) {
            UART2_WriteChar((char)('0' + (fraction / divisor) % 10U));
            divisor /= 10U;
        }
    }
}

static void TemperatureControl_Update(void) {
    static uint32_t last_temperature_ms = 0U;
    uint32_t now = data_time_ms;
    float target_rpm = 0.0f;

    if ((now - last_temperature_ms) < TEMP_CONTROL_PERIOD_MS) {
        return;
    }
    last_temperature_ms = now;

    latest_temperature_c = Sensor_ReadTemperature();

    if (latest_temperature_c == TEMP_SENSOR_ERROR_VALUE) {
        if (temperature_control_enabled != 0U) {
            PID_SetTargetRPM(0.0f);
        }
        return;
    }

    if (latest_temperature_c <= FAN_TEMP_START_C) {
        target_rpm = 0.0f;
    } else if (latest_temperature_c >= FAN_TEMP_MAX_C) {
        target_rpm = FAN_MAX_RPM;
    } else {
        float ratio = (latest_temperature_c - FAN_TEMP_START_C) / (FAN_TEMP_MAX_C - FAN_TEMP_START_C);
        target_rpm = FAN_MIN_RPM + (ratio * (FAN_MAX_RPM - FAN_MIN_RPM));
    }

    if (temperature_control_enabled != 0U) {
        PID_SetTargetRPM(target_rpm);
    }
}

static void SendTelemetry(void) {
    float rpm = current_speed;
    float rps = rpm / 60.0f;

    UART2_WriteString("FAN,");
    UART_WriteUnsigned(data_time_ms);
    UART2_WriteChar(',');
    UART_WriteScaled(rps, 2U);
    UART2_WriteChar(',');
    UART_WriteScaled(rpm, 1U);
    UART2_WriteChar(',');
    UART_WriteScaled(setpoint, 1U);
    UART2_WriteChar(',');
    UART_WriteSigned(pwm_duty);
    UART2_WriteChar(',');
    UART_WriteScaled(latest_temperature_c, 1U);
    UART2_WriteChar(',');
    UART_WriteUnsigned(fault_code);
    UART2_WriteChar(',');
    UART2_WriteString(PID_GetStateName());
    UART2_WriteString("\r\n");
}

static void SendHelp(void) {
    UART2_WriteString("Commands: a auto temp, m manual, s150 set RPM, p35 set Kp, i100 set Ki, d0.5 set Kd, x stop, r reset, ? help\r\n");
}

static void SendAck(const char *message) {
    UART2_WriteString("ACK,");
    UART2_WriteString(message);
    UART2_WriteString("\r\n");
}

static void ProcessCommand(char *cmd) {
    if (cmd[0] == '\0') {
        return;
    }

    float value = strtof(&cmd[1], 0);
    switch (cmd[0]) {
        case 's':
        case 'S':
            temperature_control_enabled = 0U;
            PID_SetTargetRPM(value);
            SendAck("target_rpm");
            break;
        case 'a':
        case 'A':
            temperature_control_enabled = 1U;
            SendAck("auto_temperature");
            break;
        case 'm':
        case 'M':
            temperature_control_enabled = 0U;
            SendAck("manual");
            break;
        case 'p':
        case 'P':
            PID_SetTunings(value, pid_ki, pid_kd);
            SendAck("kp");
            break;
        case 'i':
        case 'I':
            PID_SetTunings(pid_kp, value, pid_kd);
            SendAck("ki");
            break;
        case 'd':
        case 'D':
            PID_SetTunings(pid_kp, pid_ki, value);
            SendAck("kd");
            break;
        case 'x':
        case 'X':
            temperature_control_enabled = 0U;
            PID_SetTargetRPM(0.0f);
            SendAck("stop");
            break;
        case 'r':
        case 'R':
            PID_ResetFaults();
            SendAck("reset");
            break;
        case '?':
            SendHelp();
            break;
        default:
            UART2_WriteString("ERR,unknown_command\r\n");
            break;
    }
}

static void PollCommands(void) {
    static char buffer[CMD_BUFFER_SIZE];
    static uint32_t index = 0U;
    char ch;

    while (UART2_ReadChar(&ch)) {
        if (ch == '\r' || ch == '\n') {
            buffer[index] = '\0';
            ProcessCommand(buffer);
            index = 0U;
        } else if (index < (CMD_BUFFER_SIZE - 1U)) {
            buffer[index++] = ch;
        } else {
            index = 0U;
            UART2_WriteString("ERR,command_too_long\r\n");
        }
    }
}

int main(void) {
    HAL_Init();
    System_Init();
    Sensor_Init();
    UART2_WriteString("STM32 Smart Fan Ready\r\n");
    SendHelp();

    uint32_t last_telemetry_ms = 0U;

    while (1) {
        PollCommands();
        TemperatureControl_Update();

        uint32_t now = data_time_ms;
        if ((now - last_telemetry_ms) >= TELEMETRY_PERIOD_MS) {
            last_telemetry_ms = now;
            SendTelemetry();
        }
    }
}
