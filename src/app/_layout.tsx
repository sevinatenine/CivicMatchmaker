import { PartyStripe } from '@/components/PartyStripe';
import { Colors } from '@/constants/Colors';
import { recordVisit } from '@/lib/usageStats';
import { keepFocusedInputVisible } from '@/lib/webSetup';
import { PrimaryButton } from '@/components/PrimaryButton';
import { DefaultTheme, ErrorBoundaryProps, Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { ScrollView, Text, View } from 'react-native';

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
  // The stack is for screenshots from phones we can't attach a debugger to. Drop the long
  // bundle URLs so each frame fits on one line: "fn@entry-abc123.js:2:34567".
  const stack = (error.stack ?? '')
    .split('\n')
    .slice(0, 40)
    .map((line) => line.replace(/https?:\/\/[^\s)]*\//g, ''))
    .join('\n');

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
      <Text style={{ color: Colors.textMuted, fontSize: 15 }} selectable>
        {error.message}
      </Text>
      {!!stack && (
        <ScrollView style={{ maxHeight: 360, marginBottom: 12 }}>
          <Text
            style={{ color: Colors.textMuted, fontSize: 10, fontFamily: 'monospace' }}
            selectable
          >
            {stack}
          </Text>
        </ScrollView>
      )}
      <PrimaryButton title="Try again" onPress={retry} />
    </View>
  );
}

export default function RootLayout() {
  useEffect(() => keepFocusedInputVisible(), []);
  useEffect(() => {
    recordVisit(); // count this launch, whichever screen it opens on
  }, []);

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