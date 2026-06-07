#ifndef SYSTEM_CONFIG_H
#define SYSTEM_CONFIG_H

#define SYS_CLOCK       16000000U
#define PWM_FREQ        10000U
#define PWM_ARR         ((SYS_CLOCK / PWM_FREQ) - 1U)

#define TS_SEC          0.01f
#define PPR             2800.0f

#define PID_SETPOINT_RPM 50.0f
#define PID_KP           8.0f
#define PID_KI           30.0f
#define PID_KD           0.5f

#endif /* SYSTEM_CONFIG_H */
