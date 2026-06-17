import { MaterialCommunityIcons } from '@expo/vector-icons';
import {
  ActivityIndicator,
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
import MonitorCard from '../components/MonitorCard';
import { FanGauge, PwmBars, StatusCheck } from '../components/CardVisuals';
import { colors } from '../constants/theme';
import type { MonitorStatus } from '../types/api';

if (
  Platform.OS === 'android' &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

type HomeScreenProps = {
  status: MonitorStatus | null;
  temperaturePoints: number[];
  fanSpeedPoints: number[];
  pwmPoints: number[];
  loading: boolean;
  error: string | null;
  modePending: boolean;
  onOpenSettings: () => void;
  onOpenFanControl: () => void;
  onSetControlMode: (mode: 'auto' | 'manual') => Promise<void>;
};

export default function HomeScreen({
  status,
  temperaturePoints,
  fanSpeedPoints,
  pwmPoints,
  loading,
  error,
  modePending,
  onOpenSettings,
  onOpenFanControl,
  onSetControlMode,
}: HomeScreenProps) {
  if (loading && !status) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Đang kết nối backend...</Text>
      </View>
    );
  }

  const data = status ?? {
    temperature: 0,
    fanSpeed: 0,
    pwm: 0,
    warning: 'Không có',
    controlMode: 'auto' as const,
    dataSource: 'serial' as const,
    deviceConnected: false,
    rpm: 0,
    targetRpm: 0,
    faultCode: 0,
    state: null,
  };
  const hasWarning = data.warning !== 'Không có';
  const fanModeLabel =
    data.controlMode === 'auto' ? 'Tự động theo nhiệt độ' : 'Điều khiển thủ công';
  const sourceLabel = data.deviceConnected
    ? 'STM32 đã kết nối'
    : 'STM32 chưa kết nối';

  const switchMode = (next: 'auto' | 'manual') => {
    if (next === data.controlMode) {
      return;
    }
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    void onSetControlMode(next);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.primary} />

      <View style={styles.header}>
        <View style={styles.headerSpacer} />
        <Text style={styles.headerTitle}>APP GIÁM SÁT</Text>
        <TouchableOpacity style={styles.menuButton} activeOpacity={0.7}>
          <MaterialCommunityIcons name="menu" size={26} color="#fff" />
        </TouchableOpacity>
      </View>

      {error ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      ) : null}

      <View style={styles.sourceBanner}>
        <Text style={styles.sourceText}>
          {sourceLabel}
          {` · ${(data.rpm ?? 0).toFixed(1)} RPM`}
          {data.state ? ` · ${data.state}` : ''}
        </Text>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <ModeToggle
          mode={data.controlMode}
          onChange={switchMode}
          pending={modePending}
        />

        <MonitorCard
          icon={
            <MaterialCommunityIcons
              name="thermometer"
              size={32}
              color={colors.red}
            />
          }
          label="Nhiệt độ"
          value={`${data.temperature} °C`}
          valueColor={colors.red}
          chart={
            <LineChart
              points={temperaturePoints}
              color={colors.red}
              height={90}
              unit="°C"
              label="Đồ thị nhiệt độ theo thời gian"
            />
          }
        />

        <MonitorCard
          icon={
            <MaterialCommunityIcons name="fan" size={32} color={colors.blue} />
          }
          label="Tốc độ quạt"
          value={`${data.fanSpeed} %`}
          valueColor={colors.blue}
          rightContent={<FanGauge percent={data.fanSpeed} />}
          chart={
            <View>
              <FanSpinner speed={data.fanSpeed} size={40} />
              <LineChart
                points={fanSpeedPoints}
                color={colors.blue}
                height={80}
                unit="%"
                label="Đồ thị tốc độ quạt"
              />
            </View>
          }
          hint={`${fanModeLabel} · Bấm để điều khiển`}
          onPress={onOpenFanControl}
        />

        <MonitorCard
          icon={
            <MaterialCommunityIcons
              name="sine-wave"
              size={32}
              color={colors.blue}
            />
          }
          label="Mức điều khiển (PWM)"
          value={`${data.pwm} %`}
          valueColor={colors.blue}
          rightContent={<PwmBars percent={data.pwm} />}
          chart={
            <LineChart
              points={pwmPoints}
              color={colors.blue}
              height={80}
              unit="%"
              label="Đồ thị tín hiệu PWM"
            />
          }
        />

        <MonitorCard
          icon={
            <MaterialCommunityIcons
              name="alert"
              size={32}
              color={colors.red}
            />
          }
          label="Cảnh báo"
          value={data.warning}
          valueColor={hasWarning ? colors.red : colors.green}
          rightContent={<StatusCheck active={hasWarning} />}
          chart={
            <LineChart
              points={temperaturePoints}
              color={hasWarning ? colors.red : colors.green}
              height={70}
              unit="°C"
              label="Nhiệt độ (liên quan cảnh báo)"
            />
          }
        />

        <MonitorCard
          icon={
            <MaterialCommunityIcons name="cog" size={32} color={colors.blue} />
          }
          label="Cài đặt PID / ngưỡng"
          rightContent={
            <MaterialCommunityIcons
              name="chevron-right"
              size={32}
              color={colors.blue}
            />
          }
          hint="Điều chỉnh tham số điều khiển tự động"
          onPress={onOpenSettings}
        />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  center: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: colors.text,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: colors.primary,
    paddingTop: 48,
    paddingBottom: 14,
    paddingHorizontal: 16,
  },
  headerSpacer: {
    width: 40,
  },
  headerTitle: {
    flex: 1,
    textAlign: 'center',
    fontSize: 18,
    fontWeight: '700',
    color: '#fff',
    letterSpacing: 0.5,
  },
  menuButton: {
    width: 40,
    alignItems: 'flex-end',
  },
  errorBanner: {
    backgroundColor: '#FFEBEE',
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  sourceBanner: {
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  sourceText: {
    color: colors.green,
    fontSize: 12,
    fontWeight: '600',
  },
  errorText: {
    color: colors.red,
    fontSize: 13,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 32,
  },
});
