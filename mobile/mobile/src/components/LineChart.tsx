import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../constants/theme';

type LineChartProps = {
  points: number[];
  color?: string;
  height?: number;
  unit?: string;
  label?: string;
};

export default function LineChart({
  points,
  color = colors.blue,
  height = 72,
  unit = '',
  label,
}: LineChartProps) {
  const data = points.length > 0 ? points : [0];
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const chartHeight = height - 18;

  return (
    <View style={styles.wrap}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={[styles.chart, { height: chartHeight }]}>
        {data.map((value, index) => {
          const barHeight = ((value - min) / range) * (chartHeight - 8) + 8;
          const isLast = index === data.length - 1;

          return (
            <View key={index} style={styles.column}>
              <View
                style={[
                  styles.bar,
                  {
                    height: barHeight,
                    backgroundColor: isLast ? color : `${color}88`,
                  },
                ]}
              />
            </View>
          );
        })}
      </View>
      <View style={styles.axis}>
        <Text style={styles.axisText}>
          {min.toFixed(1)}
          {unit}
        </Text>
        <Text style={styles.axisText}>
          {max.toFixed(1)}
          {unit}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    width: '100%',
  },
  label: {
    fontSize: 11,
    color: colors.textSecondary,
    marginBottom: 6,
  },
  chart: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 3,
  },
  column: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  bar: {
    width: '100%',
    maxWidth: 14,
    borderRadius: 4,
    minHeight: 4,
  },
  axis: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  axisText: {
    fontSize: 10,
    color: colors.textSecondary,
  },
});
