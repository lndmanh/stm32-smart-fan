#include "pid_controller.h"
#include "hardware.h"
#include "stm32f401xe.h"
#include "system_config.h"

volatile float setpoint = PID_SETPOINT_RPM;
volatile float current_speed = 0.0f;
volatile int32_t pwm_duty = 0;
volatile uint32_t data_time_ms = 0U;

static float i_term = 0.0f;
static float last_speed = 0.0f;
static int32_t last_encoder_cnt = 0;

void TIM3_IRQHandler(void) {
    if ((TIM3->SR & TIM_SR_UIF) == 0U) {
        return;
    }

    TIM3->SR &= ~TIM_SR_UIF;
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
