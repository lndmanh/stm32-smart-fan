export const MAX_RPM = 190;
export const PWM_LIMIT = 1599;

export type FanTelemetrySample = {
  timestampMs: number;
  rps: number;
  rpm: number;
  targetRpm: number;
  pwm: number;
  temperatureC: number;
  faultCode: number;
  state: string;
};

export function parseFanTelemetryLine(raw: string): FanTelemetrySample | null {
  const parts = raw.trim().split(',');
  if (parts.length !== 9 || parts[0] !== 'FAN') {
    return null;
  }

  try {
    const pwmRaw = Number(parts[5]);
    const pwm = Math.max(-PWM_LIMIT, Math.min(PWM_LIMIT, Math.trunc(pwmRaw)));
    return {
      timestampMs: Number(parts[1]),
      rps: Number(parts[2]),
      rpm: Number(parts[3]),
      targetRpm: Number(parts[4]),
      pwm,
      temperatureC: Number(parts[6]),
      faultCode: Number(parts[7]),
      state: parts[8].trim() || 'UNKNOWN',
    };
  } catch {
    return null;
  }
}

export function rpmToPercent(rpm: number): number {
  return Math.round(Math.max(0, Math.min(100, (rpm / MAX_RPM) * 100)));
}

export function clampFanPercent(
  percent: number,
  min = 0,
  max = 100,
): number {
  const lo = Math.max(0, Math.min(100, Math.round(min)));
  const hi = Math.max(lo, Math.min(100, Math.round(max)));
  return Math.round(Math.max(lo, Math.min(hi, percent)));
}

export function percentToRpm(percent: number): number {
  return Math.round(Math.max(0, Math.min(MAX_RPM, (percent / 100) * MAX_RPM)));
}

export function pwmToPercent(pwm: number): number {
  return Math.round(
    Math.max(0, Math.min(100, (Math.abs(pwm) / PWM_LIMIT) * 100)),
  );
}

export function buildSetSpeedCommand(rpm: number): string {
  const target = Math.round(Math.max(0, Math.min(MAX_RPM, rpm)));
  return `s${target}\n`;
}

export function buildPidCommand(
  gain: 'kp' | 'ki' | 'kd',
  value: number,
): string {
  const prefix = gain === 'kp' ? 'p' : gain === 'ki' ? 'i' : 'd';
  const formatted = Number.isInteger(value) ? String(value) : String(value);
  return `${prefix}${formatted}\n`;
}

export function buildStopCommand(): string {
  return 'x\n';
}

export function buildResetFaultsCommand(): string {
  return 'r\n';
}

export function buildAutoModeCommand(): string {
  return 'a\n';
}

export function buildManualModeCommand(): string {
  return 'm\n';
}
