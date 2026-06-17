export type MonitorStatus = {
  temperature: number;
  fanSpeed: number;
  pwm: number;
  warning: string;
  controlMode: 'auto' | 'manual';
  dataSource?: 'serial';
  deviceConnected?: boolean;
  rpm?: number;
  targetRpm?: number;
  faultCode?: number;
  state?: string | null;
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
