import { type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { colors } from '../constants/theme';

type MonitorCardProps = {
  icon: ReactNode;
  label: string;
  value?: string;
  valueColor?: string;
  rightContent?: ReactNode;
  chart?: ReactNode;
  hint?: string;
  onPress?: () => void;
};

export default function MonitorCard({
  icon,
  label,
  value,
  valueColor = colors.text,
  rightContent,
  chart,
  hint,
  onPress,
}: MonitorCardProps) {
  const content = (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={styles.iconBox}>{icon}</View>
        <View style={styles.info}>
          <Text style={styles.label}>{label}</Text>
          {value ? (
            <Text style={[styles.value, { color: valueColor }]}>{value}</Text>
          ) : null}
        </View>
        {rightContent ? <View style={styles.right}>{rightContent}</View> : null}
      </View>
      {chart ? <View style={styles.chartArea}>{chart}</View> : null}
      {hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => (pressed ? styles.pressed : undefined)}
      >
        {content}
      </Pressable>
    );
  }

  return content;
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 3,
    elevation: 2,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  pressed: {
    opacity: 0.85,
  },
  iconBox: {
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: {
    flex: 1,
    paddingHorizontal: 8,
  },
  label: {
    fontSize: 15,
    color: colors.text,
    fontWeight: '500',
    marginBottom: 4,
  },
  value: {
    fontSize: 26,
    fontWeight: '700',
  },
  right: {
    width: 72,
    alignItems: 'center',
    justifyContent: 'center',
  },
  chartArea: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  hint: {
    marginTop: 8,
    fontSize: 12,
    color: colors.textSecondary,
  },
});
