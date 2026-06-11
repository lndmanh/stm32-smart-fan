#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H

#include <stdint.h>

extern volatile float setpoint;
extern volatile float current_speed;
extern volatile float pid_kp;
extern volatile float pid_ki;
extern volatile float pid_kd;
extern volatile int32_t pwm_duty;
extern volatile uint32_t data_time_ms;
extern volatile uint8_t fault_code;

void PID_SetTargetRPM(float rpm);
void PID_SetTunings(float kp, float ki, float kd);
void PID_ResetFaults(void);
const char *PID_GetStateName(void);

void PID_Control_Update(void);

#endif /* PID_CONTROLLER_H */
