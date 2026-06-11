#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H

#include <stdint.h>

extern volatile float setpoint;
extern volatile float current_speed;
extern volatile int32_t pwm_duty;
extern volatile uint32_t data_time_ms;

void PID_Control_Update(void);

#endif /* PID_CONTROLLER_H */
