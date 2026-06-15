export type MonitorStatus = {
  temperature: number;
  fanSpeed: number;
  pwm: number;
  warning: string;
  controlMode: 'auto' | 'manual';
  dataSource?: 'serial' | 'simulator';
  deviceConnected?: boolean;
  rpm?: number | null;
  targetRpm?: number | null;
  faultCode?: number | null;
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
