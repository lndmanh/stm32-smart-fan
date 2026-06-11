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
volatile int32_t pwm_duty = 0;
volatile uint32_t data_time_ms = 0U;

static float i_term = 0.0f;
static float last_speed = 0.0f;
static int32_t last_encoder_cnt = 0;

void PID_Control_Update(void) {
    data_time_ms += 10U;

    int32_t current_cnt = (int32_t)TIM2->CNT;
    int32_t delta_cnt = current_cnt - last_encoder_cnt;
    last_encoder_cnt = current_cnt;

    current_speed = ((float)delta_cnt * 60.0f) / (PPR * TS_SEC);

    float error = setpoint - current_speed;
    float p_term = PID_KP * error;
    i_term += PID_KI * error * TS_SEC;
    float d_term = -PID_KD * (current_speed - last_speed) / TS_SEC;

    float control_u = p_term + i_term + d_term;

    if (control_u > (float)PWM_ARR) {
        control_u = (float)PWM_ARR;
        i_term -= PID_KI * error * TS_SEC;
    } else if (control_u < -(float)PWM_ARR) {
        control_u = -(float)PWM_ARR;
        i_term -= PID_KI * error * TS_SEC;
    }

    pwm_duty = (int32_t)control_u;
    Set_Motor_Output(pwm_duty);
    last_speed = current_speed;
}
