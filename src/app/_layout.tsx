import { Colors } from '@/constants/Colors';
import { Stack } from 'expo-router';
import { DefaultTheme, ThemeProvider } from 'expo-router/react-navigation';
import { StatusBar } from 'expo-status-bar';

const CustomTheme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    background: Colors.background,
    card: Colors.top,
    text: Colors.text,
    border: Colors.border,
    primary: Colors.button,
  },
};

export default function RootLayout() {
  return (
    <ThemeProvider value={CustomTheme}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          animation: 'slide_from_right',
          contentStyle: { backgroundColor: Colors.background },
          headerStyle: { backgroundColor: Colors.top },
          headerShadowVisible: false,
          headerTitleStyle: { color: Colors.text, fontWeight: '600' },
          headerTintColor: Colors.button,
        }}
      >
        <Stack.Screen name="index" options={{ title: 'Civic Matchmaker' }} />
        <Stack.Screen name="locationSelect" options={{ title: 'Your location' }} />
        <Stack.Screen name="about" options={{ title: 'About Us' }} />
        <Stack.Screen name="questions" options={{ title: 'Questions' }} />
        <Stack.Screen name="selectType" options={{ title: 'Select type' }} />
        <Stack.Screen name="results" options={{ title: 'Your matches' }} />
      </Stack>
    </ThemeProvider>
  );
}