#include "pid_controller.h"
#include "hardware.h"
#include "stm32f401xe.h"

#define SYS_CLOCK        16000000U
#define PWM_FREQ         10000U
#define PWM_ARR          ((SYS_CLOCK / PWM_FREQ) - 1U)

#define TS_SEC           0.01f
#define PPR              2800.0f

#define PID_SETPOINT_RPM 50.0f
#define PID_KP           8.0f
#define PID_KI           30.0f
#define PID_KD           0.5f

volatile float setpoint = PID_SETPOINT_RPM;
volatile float current_speed = 0.0f;
volatile float pid_kp = PID_KP;
volatile float pid_ki = PID_KI;
volatile float pid_kd = PID_KD;
volatile int32_t pwm_duty = 0;
volatile uint32_t data_time_ms = 0U;
volatile uint8_t fault_code = 0U;

static float i_term = 0.0f;
static float last_speed = 0.0f;
static int32_t last_encoder_cnt = 0;
static uint16_t stall_ticks = 0U;

static float abs_float(float value) {
    return value < 0.0f ? -value : value;
}

void PID_Control_Update(void) {
    data_time_ms += 10U;

    int32_t current_cnt = (int32_t)TIM2->CNT;
    int32_t delta_cnt = current_cnt - last_encoder_cnt;
    last_encoder_cnt = current_cnt;

    current_speed = ((float)delta_cnt * 60.0f) / (PPR * TS_SEC);

    if (abs_float(current_speed) > 190.0f) {
        fault_code = 1U;
    }

    if (fault_code != 0U) {
        pwm_duty = 0;
        Set_Motor_Output(0);
        last_speed = current_speed;
        return;
    }

    float error = setpoint - current_speed;
    float p_term = pid_kp * error;
    i_term += pid_ki * error * TS_SEC;
    float d_term = -pid_kd * (current_speed - last_speed) / TS_SEC;

    float control_u = p_term + i_term + d_term;

    if (control_u > (float)PWM_ARR) {
        control_u = (float)PWM_ARR;
        i_term -= pid_ki * error * TS_SEC;
    } else if (control_u < -(float)PWM_ARR) {
        control_u = -(float)PWM_ARR;
        i_term -= pid_ki * error * TS_SEC;
    }

    pwm_duty = (int32_t)control_u;

    if (abs_float((float)pwm_duty) > 800.0f && abs_float(current_speed) < 5.0f && setpoint > 20.0f) {
        stall_ticks++;
        if (stall_ticks >= 20U) {
            fault_code = 2U;
            pwm_duty = 0;
        }
    } else {
        stall_ticks = 0U;
    }

    Set_Motor_Output(pwm_duty);
    last_speed = current_speed;
}

void PID_SetTargetRPM(float rpm) {
    if (rpm < 0.0f) {
        rpm = 0.0f;
    } else if (rpm > 190.0f) {
        rpm = 190.0f;
    }

    setpoint = rpm;
}

void PID_SetTunings(float kp, float ki, float kd) {
    if (kp >= 0.0f) {
        pid_kp = kp;
    }
    if (ki >= 0.0f) {
        pid_ki = ki;
    }
    if (kd >= 0.0f) {
        pid_kd = kd;
    }
}

void PID_ResetFaults(void) {
    fault_code = 0U;
    i_term = 0.0f;
    last_speed = current_speed;
    stall_ticks = 0U;
}

const char *PID_GetStateName(void) {
    if (fault_code != 0U) {
        return "FAULT";
    }
    if (setpoint <= 0.5f) {
        return "IDLE";
    }
    return "RUN";
}
