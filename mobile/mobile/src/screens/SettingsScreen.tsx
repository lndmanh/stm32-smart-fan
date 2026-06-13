import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { colors } from '../constants/theme';
import { usePidSettings } from '../hooks/useMonitorData';
import type { PidSettings } from '../types/api';

type SettingsScreenProps = {
  onBack: () => void;
};

export default function SettingsScreen({ onBack }: SettingsScreenProps) {
  const { settings, loading, saving, error, saveSettings } = usePidSettings();
  const [form, setForm] = useState<PidSettings | null>(null);

  useEffect(() => {
    if (settings) {
      setForm(settings);
    }
  }, [settings]);

  const updateField = (key: keyof PidSettings, value: string) => {
    if (!form) return;
    setForm({ ...form, [key]: value });
  };

  const handleSave = async () => {
    if (!form) return;

    const payload: PidSettings = {
      kp: Number(form.kp),
      ki: Number(form.ki),
      kd: Number(form.kd),
      temperatureThreshold: Number(form.temperatureThreshold),
      fanMinSpeed: Number(form.fanMinSpeed),
      fanMaxSpeed: Number(form.fanMaxSpeed),
    };

    const ok = await saveSettings(payload);
    if (ok) {
      Alert.alert('Thành công', 'Đã lưu cài đặt PID / ngưỡng');
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={colors.primary} />

      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={26} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>CÀI ĐẶT PID</Text>
        <View style={styles.headerSpacer} />
      </View>

      {loading || !form ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.content}>
          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Field
            label="Kp"
            value={String(form.kp)}
            onChangeText={(v) => updateField('kp', v)}
          />
          <Field
            label="Ki"
            value={String(form.ki)}
            onChangeText={(v) => updateField('ki', v)}
          />
          <Field
            label="Kd"
            value={String(form.kd)}
            onChangeText={(v) => updateField('kd', v)}
          />
          <Field
            label="Ngưỡng nhiệt độ (°C)"
            value={String(form.temperatureThreshold)}
            onChangeText={(v) => updateField('temperatureThreshold', v)}
          />
          <Field
            label="Tốc độ quạt tối thiểu (%)"
            value={String(form.fanMinSpeed)}
            onChangeText={(v) => updateField('fanMinSpeed', v)}
          />
          <Field
            label="Tốc độ quạt tối đa (%)"
            value={String(form.fanMaxSpeed)}
            onChangeText={(v) => updateField('fanMaxSpeed', v)}
          />

          <TouchableOpacity
            style={[styles.saveButton, saving && styles.saveButtonDisabled]}
            onPress={handleSave}
            disabled={saving}
          >
            {saving ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.saveText}>Lưu cài đặt</Text>
            )}
          </TouchableOpacity>
        </ScrollView>
      )}
    </View>
  );
}

function Field({
  label,
  value,
  onChangeText,
}: {
  label: string;
  value: string;
  onChangeText: (value: string) => void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        keyboardType="decimal-pad"
      />
    </View>
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
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  field: {
    marginBottom: 14,
  },
  label: {
    fontSize: 14,
    color: colors.text,
    marginBottom: 6,
    fontWeight: '500',
  },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
  },
  saveButton: {
    marginTop: 8,
    backgroundColor: colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.7,
  },
  saveText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  error: {
    color: colors.red,
    marginBottom: 12,
  },
});
