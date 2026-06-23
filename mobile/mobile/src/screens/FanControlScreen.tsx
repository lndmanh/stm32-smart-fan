import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import {
  LayoutAnimation,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  UIManager,
  View,
} from 'react-native';
import FanSpinner from '../components/FanSpinner';
import LineChart from '../components/LineChart';
import ModeToggle from '../components/ModeToggle';
import { colors } from '../constants/theme';
import type { MonitorStatus } from '../types/api';
import { buildFanPresets, clampFanPercent } from '../utils/fanSpeed';

if (
  Platform.OS === 'android' &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type FanControlScreenProps = {
  status: MonitorStatus | null;
  fanPoints: number[];
  modePending: boolean;
  fanMinSpeed: number;
  fanMaxSpeed: number;
  onBack: () => void;
  onSetControlMode: (mode: 'auto' | 'manual') => Promise<void>;
  onSetFanSpeed: (fanSpeed: number) => Promise<void>;
};

export default function FanControlScreen({
  status,
  fanPoints,
  modePending,
  fanMinSpeed,
  fanMaxSpeed,
  onBack,
  onSetControlMode,
  onSetFanSpeed,
}: FanControlScreenProps) {
  const mode = status?.controlMode ?? 'auto';
  const fanSpeed = status?.fanSpeed ?? 0;
  const [localFanSpeed, setLocalFanSpeed] = useState(fanSpeed);

  useEffect(() => {
    setLocalFanSpeed(fanSpeed);
  }, [fanSpeed]);

  const switchMode = (next: 'auto' | 'manual') => {
    if (next === mode) {
      return;
    }
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    void onSetControlMode(next);
  };

  const applyFanSpeed = (next: number) => {
    const clamped = clampFanPercent(next, fanMinSpeed, fanMaxSpeed);
    setLocalFanSpeed(clamped);
    void onSetFanSpeed(clamped);
  };

  const presets = buildFanPresets(fanMinSpeed, fanMaxSpeed);

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
        <ModeToggle
          mode={mode}
          onChange={switchMode}
          pending={modePending}
        />

        <View style={styles.fanBox}>
          <FanSpinner speed={fanSpeed} size={72} />
          <Text style={styles.fanValue}>{fanSpeed} %</Text>
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
            <Text style={styles.limitHint}>
              Giới hạn: {fanMinSpeed}% – {fanMaxSpeed}%
            </Text>
            <View style={styles.stepRow}>
              <StepButton label="-10" onPress={() => applyFanSpeed(localFanSpeed - 10)} />
              <StepButton label="-5" onPress={() => applyFanSpeed(localFanSpeed - 5)} />
              <Text style={styles.stepValue}>{localFanSpeed}%</Text>
              <StepButton label="+5" onPress={() => applyFanSpeed(localFanSpeed + 5)} />
              <StepButton label="+10" onPress={() => applyFanSpeed(localFanSpeed + 10)} />
            </View>
            <View style={styles.presetRow}>
              {presets.map((preset) => (
                <TouchableOpacity
                  key={preset}
                  style={[
                    styles.presetButton,
                    localFanSpeed === preset && styles.presetButtonActive,
                  ]}
                  onPress={() => applyFanSpeed(preset)}
                >
                  <Text
                    style={[
                      styles.presetText,
                      localFanSpeed === preset && styles.presetTextActive,
                    ]}
                  >
                    {preset}%
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        ) : null}
      </ScrollView>
    </View>
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
  limitHint: {
    fontSize: 12,
    color: colors.textSecondary,
    marginBottom: 10,
    marginTop: -6,
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
});
