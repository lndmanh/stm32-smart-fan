export type MonitorStatus = {
  temperature: number;
  fanSpeed: number;
  pwm: number;
  warning: string;
  controlMode: 'auto' | 'manual';
};

export type TelemetryHistory = {
  points: number[];
};

export type PidSettings = {
  kp: number;
  ki: number;
  kd: number;
  temperatureThreshold: number;
  fanMinSpeed: number;
  fanMaxSpeed: number;
};
