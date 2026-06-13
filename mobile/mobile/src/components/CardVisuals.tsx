import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../constants/theme';

const DEFAULT_POINTS = [8, 14, 10, 18, 12, 22, 16, 28, 20, 32];

export function TemperatureChart({ points = DEFAULT_POINTS }: { points?: number[] }) {
  const chartPoints = points.length > 0 ? points : DEFAULT_POINTS;
  const max = Math.max(...chartPoints);
  const min = Math.min(...chartPoints);
  const range = max - min || 1;

  return (
    <View style={styles.chart}>
      {chartPoints.map((point, index) => (
        <View
          key={index}
          style={[
            styles.chartBar,
            {
              height: ((point - min) / range) * 36 + 4,
              backgroundColor: colors.red,
            },
          ]}
        />
      ))}
    </View>
  );
}

export function FanGauge({ percent }: { percent: number }) {
  const rotation = -90 + (percent / 100) * 180;

  return (
    <View style={styles.gaugeWrap}>
      <View style={styles.gaugeArc} />
      <View
        style={[
          styles.gaugeNeedle,
          { transform: [{ rotate: `${rotation}deg` }] },
        ]}
      />
      <View style={styles.gaugeCenter} />
    </View>
  );
}

export function PwmBars({ percent }: { percent: number }) {
  const filled = Math.round((percent / 100) * 5);

  return (
    <View style={styles.bars}>
      {Array.from({ length: 5 }).map((_, index) => (
        <View
          key={index}
          style={[
            styles.bar,
            index < filled ? styles.barFilled : styles.barEmpty,
          ]}
        />
      ))}
    </View>
  );
}

export function StatusCheck({ active = false }: { active?: boolean }) {
  return (
    <View
      style={[
        styles.checkCircle,
        { backgroundColor: active ? colors.red : colors.green },
      ]}
    >
      {active ? (
        <Text style={styles.alertMark}>!</Text>
      ) : (
        <View style={styles.checkMark} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  chart: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 40,
    gap: 2,
  },
  chartBar: {
    width: 4,
    borderRadius: 2,
    minHeight: 4,
  },
  gaugeWrap: {
    width: 56,
    height: 36,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  gaugeArc: {
    position: 'absolute',
    top: 4,
    width: 52,
    height: 26,
    borderTopLeftRadius: 26,
    borderTopRightRadius: 26,
    borderWidth: 4,
    borderBottomWidth: 0,
    borderColor: colors.blue,
  },
  gaugeNeedle: {
    position: 'absolute',
    bottom: 2,
    width: 2,
    height: 22,
    backgroundColor: colors.blue,
    borderRadius: 1,
  },
  gaugeCenter: {
    position: 'absolute',
    bottom: 0,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.blue,
  },
  bars: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 4,
    height: 40,
  },
  bar: {
    width: 8,
    borderRadius: 2,
  },
  barFilled: {
    height: 36,
    backgroundColor: colors.blue,
  },
  barEmpty: {
    height: 16,
    backgroundColor: '#BBDEFB',
  },
  checkCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.green,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkMark: {
    width: 10,
    height: 6,
    borderLeftWidth: 2.5,
    borderBottomWidth: 2.5,
    borderColor: '#fff',
    transform: [{ rotate: '-45deg' }, { translateY: -1 }],
  },
  alertMark: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '700',
    lineHeight: 22,
  },
});
