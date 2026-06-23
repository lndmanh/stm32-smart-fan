import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useFonts } from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { colors } from './src/constants/theme';
import { useMonitorData } from './src/hooks/useMonitorData';
import FanControlScreen from './src/screens/FanControlScreen';
import HomeScreen from './src/screens/HomeScreen';
import SettingsScreen from './src/screens/SettingsScreen';

type Screen = 'home' | 'fan' | 'settings';

export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const monitor = useMonitorData();
  const [fontsLoaded] = useFonts({
    ...MaterialCommunityIcons.font,
  });

  if (!fontsLoaded) {
    return (
      <View
        style={{
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: colors.background,
        }}
      >
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      {screen === 'home' ? (
        <HomeScreen
          status={monitor.status}
          temperaturePoints={monitor.temperaturePoints}
          fanSpeedPoints={monitor.fanSpeedPoints}
          pwmPoints={monitor.pwmPoints}
          loading={monitor.loading}
          error={monitor.error}
          modePending={monitor.modePending}
          onOpenSettings={() => setScreen('settings')}
          onOpenFanControl={() => setScreen('fan')}
          onSetControlMode={monitor.setControlMode}
          onResetFault={monitor.resetFault}
        />
      ) : null}
      {screen === 'fan' ? (
        <FanControlScreen
          status={monitor.status}
          fanPoints={monitor.fanSpeedPoints}
          modePending={monitor.modePending}
          fanMinSpeed={monitor.fanMinSpeed}
          fanMaxSpeed={monitor.fanMaxSpeed}
          onBack={() => setScreen('home')}
          onSetControlMode={monitor.setControlMode}
          onSetFanSpeed={monitor.setFanSpeed}
        />
      ) : null}
      {screen === 'settings' ? (
        <SettingsScreen onBack={() => setScreen('home')} />
      ) : null}
      <StatusBar style="light" />
    </View>
  );
}
