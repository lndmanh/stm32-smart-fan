import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors } from '../constants/theme';

type ControlMode = 'auto' | 'manual';

type ModeToggleProps = {
  mode: ControlMode;
  onChange: (mode: ControlMode) => void;
  disabled?: boolean;
  pending?: boolean;
};

const TRACK_PADDING = 3;

export default function ModeToggle({
  mode,
  onChange,
  disabled,
  pending,
}: ModeToggleProps) {
  const [trackWidth, setTrackWidth] = useState(0);
  const slide = useRef(new Animated.Value(mode === 'auto' ? 0 : 1)).current;

  useEffect(() => {
    Animated.spring(slide, {
      toValue: mode === 'auto' ? 0 : 1,
      useNativeDriver: true,
      tension: 180,
      friction: 18,
    }).start();
  }, [mode, slide]);

  const segmentWidth = trackWidth > 0 ? (trackWidth - TRACK_PADDING * 2) / 2 : 0;

  const translateX = slide.interpolate({
    inputRange: [0, 1],
    outputRange: [0, segmentWidth],
  });

  const onTrackLayout = (event: LayoutChangeEvent) => {
    setTrackWidth(event.nativeEvent.layout.width);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.label}>Chế độ điều khiển</Text>
      <View
        style={[styles.track, pending && styles.trackPending]}
        onLayout={onTrackLayout}
      >
        {segmentWidth > 0 ? (
          <Animated.View
            style={[
              styles.indicator,
              {
                width: segmentWidth,
                transform: [{ translateX }],
              },
            ]}
          />
        ) : null}

        <Pressable
          style={styles.segment}
          onPress={() => onChange('auto')}
          disabled={disabled || pending || mode === 'auto'}
        >
          <Text style={[styles.segmentLabel, mode === 'auto' && styles.segmentLabelActive]}>
            Tự động
          </Text>
          <Text style={[styles.segmentSub, mode === 'auto' && styles.segmentSubActive]}>
            Theo nhiệt độ
          </Text>
        </Pressable>

        <Pressable
          style={styles.segment}
          onPress={() => onChange('manual')}
          disabled={disabled || pending || mode === 'manual'}
        >
          <Text style={[styles.segmentLabel, mode === 'manual' && styles.segmentLabelActive]}>
            Thủ công
          </Text>
          <Text style={[styles.segmentSub, mode === 'manual' && styles.segmentSubActive]}>
            Tự chỉnh tốc độ
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.card,
    borderRadius: 12,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: colors.border,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: colors.text,
    marginBottom: 10,
  },
  track: {
    flexDirection: 'row',
    backgroundColor: colors.background,
    borderRadius: 10,
    padding: TRACK_PADDING,
    position: 'relative',
    borderWidth: 1,
    borderColor: colors.border,
  },
  trackPending: {
    opacity: 0.85,
  },
  indicator: {
    position: 'absolute',
    top: TRACK_PADDING,
    left: TRACK_PADDING,
    bottom: TRACK_PADDING,
    backgroundColor: colors.primary,
    borderRadius: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.12,
    shadowRadius: 2,
    elevation: 2,
  },
  segment: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 8,
    alignItems: 'center',
    zIndex: 1,
  },
  segmentLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: colors.text,
  },
  segmentLabelActive: {
    color: '#fff',
  },
  segmentSub: {
    fontSize: 11,
    color: colors.textSecondary,
    marginTop: 2,
  },
  segmentSubActive: {
    color: '#E3F2FD',
  },
});
