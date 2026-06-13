import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { api } from '../api/client';
import FanSpinner from '../components/FanSpinner';
import LineChart from '../components/LineChart';
import { colors } from '../constants/theme';
import type { MonitorStatus } from '../types/api';

type FanControlScreenProps = {
  status: MonitorStatus | null;
  fanPoints: number[];
  onBack: () => void;
  onUpdated: () => Promise<void>;
};

export default function FanControlScreen({
  status,
  fanPoints,
  onBack,
  onUpdated,
}: FanControlScreenProps) {
  const [fanSpeed, setFanSpeed] = useState(status?.fanSpeed ?? 0);
  const [mode, setMode] = useState<'auto' | 'manual'>(status?.controlMode ?? 'auto');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (status) {
      setFanSpeed(status.fanSpeed);
      setMode(status.controlMode);
    }
  }, [status]);

  const applyFanSpeed = async (next: number) => {
    const clamped = Math.min(100, Math.max(0, next));
    setFanSpeed(clamped);
    setSaving(true);
    try {
      await api.setFanSpeed(clamped);
      await onUpdated();
    } finally {
      setSaving(false);
    }
  };

  const switchMode = async (next: 'auto' | 'manual') => {
    setMode(next);
    setSaving(true);
    try {
      await api.setControlMode(next);
      await onUpdated();
    } finally {
      setSaving(false);
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.primary} />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={26} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>ĐIỀU KHIỂN QUẠT</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.modeRow}>
          <ModeButton
            label="Tự động"
            sub="Theo nhiệt độ"
            active={mode === 'auto'}
            onPress={() => switchMode('auto')}
            disabled={saving}
          />
          <ModeButton
            label="Thủ công"
            sub="Tự chỉnh tốc độ"
            active={mode === 'manual'}
            onPress={() => switchMode('manual')}
            disabled={saving}
          />
        </View>

        <View style={styles.fanBox}>
          <FanSpinner speed={mode === 'auto' ? (status?.fanSpeed ?? 0) : fanSpeed} size={72} />
          <Text style={styles.fanValue}>{status?.fanSpeed ?? fanSpeed} %</Text>
          <Text style={styles.fanHint}>
            {mode === 'auto'
              ? 'Nhiệt cao → quạt quay nhanh hơn'
              : 'Đang điều khiển thủ công'}
          </Text>
        </View>

        <View style={styles.chartCard}>
          <Text style={styles.sectionTitle}>Đồ thị tốc độ quạt</Text>
          <LineChart
            points={fanPoints}
            color={colors.blue}
            height={100}
            unit="%"
            label="20 mẫu gần nhất"
          />
        </View>

        {mode === 'manual' ? (
          <View style={styles.controlCard}>
            <Text style={styles.sectionTitle}>Chỉnh tốc độ quạt</Text>
            <View style={styles.stepRow}>
              <StepButton label="-10" onPress={() => applyFanSpeed(fanSpeed - 10)} />
              <StepButton label="-5" onPress={() => applyFanSpeed(fanSpeed - 5)} />
              <Text style={styles.stepValue}>{fanSpeed}%</Text>
              <StepButton label="+5" onPress={() => applyFanSpeed(fanSpeed + 5)} />
              <StepButton label="+10" onPress={() => applyFanSpeed(fanSpeed + 10)} />
            </View>
            <View style={styles.presetRow}>
              {[0, 30, 50, 70, 100].map((preset) => (
                <TouchableOpacity
                  key={preset}
                  style={[
                    styles.presetButton,
                    fanSpeed === preset && styles.presetButtonActive,
                  ]}
                  onPress={() => applyFanSpeed(preset)}
                >
                  <Text
                    style={[
                      styles.presetText,
                      fanSpeed === preset && styles.presetTextActive,
                    ]}
                  >
                    {preset}%
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : null}

        {saving ? (
          <ActivityIndicator style={styles.saving} color={colors.primary} />
        ) : null}
      </ScrollView>
    </View>
  );
}

function ModeButton({
  label,
  sub,
  active,
  onPress,
  disabled,
}: {
  label: string;
  sub: string;
  active: boolean;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <TouchableOpacity
      style={[styles.modeButton, active && styles.modeButtonActive]}
      onPress={onPress}
      disabled={disabled}
    >
      <Text style={[styles.modeLabel, active && styles.modeLabelActive]}>{label}</Text>
      <Text style={[styles.modeSub, active && styles.modeSubActive]}>{sub}</Text>
    </TouchableOpacity>
  );
}

function StepButton({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <TouchableOpacity style={styles.stepButton} onPress={onPress}>
      <Text style={styles.stepButtonText}>{label}</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.primary,
    paddingTop: 48,
    paddingBottom: 14,
    paddingHorizontal: 16,
  },
  backButton: {
    width: 40,
  },
  headerTitle: {
    flex: 1,
    textAlign: 'center',
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
  },
  headerSpacer: {
    width: 40,
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  modeRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 16,
  },
  modeButton: {
    flex: 1,
    backgroundColor: colors.card,
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.border,
  },
  modeButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  modeLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.text,
  },
  modeLabelActive: {
    color: '#fff',
  },
  modeSub: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 4,
  },
  modeSubActive: {
    color: '#E3F2FD',
  },
  fanBox: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  fanValue: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.blue,
    marginTop: 8,
  },
  fanHint: {
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 4,
  },
  chartCard: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  controlCard: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 12,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 14,
  },
  stepButton: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
  },
  stepButtonText: {
    color: colors.blue,
    fontWeight: '700',
  },
  stepValue: {
    fontSize: 22,
    fontWeight: '700',
    color: colors.text,
    minWidth: 64,
    textAlign: 'center',
  },
  presetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 6,
  },
  presetButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: colors.background,
    alignItems: 'center',
  },
  presetButtonActive: {
    backgroundColor: colors.blue,
  },
  presetText: {
    fontSize: 12,
    fontWeight: '600',
    color: colors.text,
  },
  presetTextActive: {
    color: '#fff',
  },
  saving: {
    marginTop: 12,
  },
});
