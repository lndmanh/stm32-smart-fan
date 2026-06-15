import Constants from 'expo-constants';
import { Platform } from 'react-native';
import type {
  MonitorStatus,
  PidSettings,
  TelemetryHistory,
} from '../types/api';

function getMetroHost(): string | undefined {
  const expoGo = Constants.expoGoConfig as { debuggerHost?: string } | null;
  if (expoGo?.debuggerHost) {
    return expoGo.debuggerHost;
  }

  const manifest = Constants.manifest as { debuggerHost?: string } | null;
  return manifest?.debuggerHost;
}

export function getApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
  if (fromEnv) {
    return fromEnv;
  }

  const metroHost = getMetroHost();
  if (metroHost) {
    const [host] = metroHost.split(':');
    return `http://${host}:3000`;
  }

  if (Platform.OS === 'android' && !Constants.isDevice) {
    return 'http://10.0.2.2:3000';
  }

  return 'http://localhost:3000';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  getStatus: () => request<MonitorStatus>('/api/status'),
  getTemperatureHistory: (limit = 20) =>
    request<TelemetryHistory>(`/api/telemetry/temperature?limit=${limit}`),
  getFanSpeedHistory: (limit = 20) =>
    request<TelemetryHistory>(`/api/telemetry/fan-speed?limit=${limit}`),
  getPwmHistory: (limit = 20) =>
    request<TelemetryHistory>(`/api/telemetry/pwm?limit=${limit}`),
  setFanSpeed: (fanSpeed: number) =>
    request<MonitorStatus>('/api/status/fan', {
      method: 'PUT',
      body: JSON.stringify({ fanSpeed }),
    }),
  setControlMode: (mode: 'auto' | 'manual') =>
    request<MonitorStatus>('/api/status/mode', {
      method: 'PUT',
      body: JSON.stringify({ mode }),
    }),
  getPidSettings: () => request<PidSettings>('/api/settings/pid'),
  updatePidSettings: (settings: PidSettings) =>
    request<PidSettings>('/api/settings/pid', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),
};
