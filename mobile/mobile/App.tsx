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
          onOpenSettings={() => setScreen('settings')}
          onOpenFanControl={() => setScreen('fan')}
          onRefresh={monitor.refresh}
        />
      ) : null}
      {screen === 'fan' ? (
        <FanControlScreen
          status={monitor.status}
          fanPoints={monitor.fanSpeedPoints}
          onBack={() => setScreen('home')}
          onUpdated={monitor.refresh}
        />
      ) : null}
      {screen === 'settings' ? (
        <SettingsScreen onBack={() => setScreen('home')} />
      ) : null}
      <StatusBar style="light" />
    </View>
  );
}
