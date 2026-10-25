import { PartyStripe } from '@/components/PartyStripe';
import { Colors } from '@/constants/Colors';
import { keepFocusedInputVisible } from '@/lib/webSetup';
import { PrimaryButton } from '@/components/PrimaryButton';
import { DefaultTheme, ErrorBoundaryProps, Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { Text, View } from 'react-native';

function HeaderBackground() {
  return (
    <View style={{ flex: 1, backgroundColor: Colors.top }}>
      <PartyStripe style={{ position: 'absolute', left: 0, right: 0, bottom: 0 }} />
    </View>
  );
}

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

/**
 * Shown when any screen throws, instead of an empty gray page. Plain Views, not Screen:
 * this renders outside the Stack, where the header hooks Screen uses aren't available.
 */
export function ErrorBoundary({ error, retry }: ErrorBoundaryProps) {
  return (
    <View
      style={{
        flex: 1,
        backgroundColor: Colors.background,
        justifyContent: 'center',
        padding: 24,
        gap: 12,
      }}
    >
      <StatusBar style="light" />
      <Text style={{ color: Colors.text, fontSize: 24, fontWeight: '700' }}>
        Something went wrong
      </Text>
      <Text style={{ color: Colors.textMuted, fontSize: 15, marginBottom: 12 }} selectable>
        {error.message}
      </Text>
      <PrimaryButton title="Try again" onPress={retry} />
    </View>
  );
}

export default function RootLayout() {
  useEffect(() => keepFocusedInputVisible(), []);

  return (
    <ThemeProvider value={CustomTheme}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          animation: 'slide_from_right',
          contentStyle: { backgroundColor: Colors.background },
          headerStyle: { backgroundColor: Colors.top },
          headerBackground: HeaderBackground,
          headerShadowVisible: false,
          headerTitleStyle: { color: Colors.text, fontWeight: '600' },
          headerTintColor: Colors.button,
        }}
      >
        <Stack.Screen name="index" options={{ title: 'Civic Matchmaker', headerShown: false }} />
        <Stack.Screen name="locationSelect" options={{ title: 'Your location' }} />
        <Stack.Screen name="about" options={{ title: 'About Us' }} />
        <Stack.Screen name="questions" options={{ title: 'Questions' }} />
        <Stack.Screen name="selectType" options={{ title: 'Select type' }} />
        <Stack.Screen name="results" options={{ title: 'Your matches' }} />
        <Stack.Screen name="ballot" options={{ title: 'Sample ballot' }} />
        <Stack.Screen name="dropoff" options={{ title: 'Where to vote' }} />
      </Stack>
    </ThemeProvider>
  );
}