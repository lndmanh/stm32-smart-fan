import { useCallback, useEffect, useState } from 'react';
import { api, getApiBaseUrl } from '../api/client';
import type { MonitorStatus, PidSettings } from '../types/api';
import { clampFanPercent } from '../utils/fanSpeed';

const POLL_INTERVAL_MS = 3000;

type MonitorData = {
  status: MonitorStatus | null;
  temperaturePoints: number[];
  fanSpeedPoints: number[];
  pwmPoints: number[];
  loading: boolean;
  error: string | null;
  modePending: boolean;
  fanMinSpeed: number;
  fanMaxSpeed: number;
  refresh: () => Promise<void>;
  setControlMode: (mode: 'auto' | 'manual') => Promise<void>;
  setFanSpeed: (fanSpeed: number) => Promise<void>;
  resetFault: () => Promise<void>;
};

export function useMonitorData(): MonitorData {
  const [status, setStatus] = useState<MonitorStatus | null>(null);
  const [temperaturePoints, setTemperaturePoints] = useState<number[]>([]);
  const [fanSpeedPoints, setFanSpeedPoints] = useState<number[]>([]);
  const [pwmPoints, setPwmPoints] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modePending, setModePending] = useState(false);
  const [fanMinSpeed, setFanMinSpeed] = useState(0);
  const [fanMaxSpeed, setFanMaxSpeed] = useState(100);

  const refresh = useCallback(async () => {
    try {
      const [nextStatus, tempHistory, fanHistory, pwmHistory, pidSettings] =
        await Promise.all([
          api.getStatus(),
          api.getTemperatureHistory(20),
          api.getFanSpeedHistory(20),
          api.getPwmHistory(20),
          api.getPidSettings(),
        ]);
      setStatus(nextStatus);
      setTemperaturePoints(tempHistory.points);
      setFanSpeedPoints(fanHistory.points);
      setPwmPoints(pwmHistory.points);
      setFanMinSpeed(pidSettings.fanMinSpeed);
      setFanMaxSpeed(pidSettings.fanMaxSpeed);
      setError(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Không thể kết nối backend';
      setError(`${message}\n→ ${getApiBaseUrl()}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const setControlMode = useCallback(async (mode: 'auto' | 'manual') => {
    if (modePending) {
      return;
    }

    const previous = status;
    setModePending(true);
    setStatus((current) =>
      current ? { ...current, controlMode: mode } : current,
    );

    try {
      const updated = await api.setControlMode(mode);
      setStatus((current) =>
        current ? { ...current, ...updated } : updated,
      );
      setError(null);
    } catch (err) {
      setStatus(previous);
      const message =
        err instanceof Error ? err.message : 'Không thể đổi chế độ';
      setError(`${message}\n→ ${getApiBaseUrl()}`);
    } finally {
      setModePending(false);
    }
  }, [modePending, status]);

  const setFanSpeed = useCallback(async (fanSpeed: number) => {
    const clamped = clampFanPercent(fanSpeed, fanMinSpeed, fanMaxSpeed);
    const previous = status;

    setStatus((current) =>
      current
        ? { ...current, fanSpeed: clamped, pwm: clamped, controlMode: 'manual' }
        : current,
    );

    try {
      const updated = await api.setFanSpeed(clamped);
      setStatus((current) =>
        current ? { ...current, ...updated } : updated,
      );
      setError(null);
    } catch (err) {
      setStatus(previous);
      const message =
        err instanceof Error ? err.message : 'Không thể đặt tốc độ quạt';
      setError(`${message}\n→ ${getApiBaseUrl()}`);
    }
  }, [status, fanMinSpeed, fanMaxSpeed]);

  const resetFault = useCallback(async () => {
    try {
      const updated = await api.resetFault();
      setStatus((current) =>
        current ? { ...current, ...updated } : updated,
      );
      setError(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Không thể reset lỗi';
      setError(`${message}\n→ ${getApiBaseUrl()}`);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [refresh]);

  return {
    status,
    temperaturePoints,
    fanSpeedPoints,
    pwmPoints,
    loading,
    error,
    modePending,
    fanMinSpeed,
    fanMaxSpeed,
    refresh,
    setControlMode,
    setFanSpeed,
    resetFault,
  };
}

type SettingsData = {
  settings: PidSettings | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  saveSettings: (settings: PidSettings) => Promise<boolean>;
  reload: () => Promise<void>;
};

export function usePidSettings(): SettingsData {
  const [settings, setSettings] = useState<PidSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const next = await api.getPidSettings();
      setSettings(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể tải cài đặt');
    } finally {
      setLoading(false);
    }
  }, []);

  const saveSettings = useCallback(async (next: PidSettings) => {
    setSaving(true);
    try {
      const saved = await api.updatePidSettings(next);
      setSettings(saved);
      setError(null);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không thể lưu cài đặt');
      return false;
    } finally {
      setSaving(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { settings, loading, saving, error, saveSettings, reload };
}
