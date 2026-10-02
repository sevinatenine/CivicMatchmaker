import { Colors } from '@/constants/Colors';
import { Stack } from 'expo-router';
import { DefaultTheme, ThemeProvider } from 'expo-router/react-navigation';

const CustomTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: Colors.background,
    background2: Colors.top,
    card: Colors.top,
    text: Colors.text,
    primary: Colors.button,
  },
};

export default function RootLayout() {
  return (
    <ThemeProvider value={CustomTheme}>
      <Stack
        screenOptions={{
          contentStyle: {
            backgroundColor: CustomTheme.colors.background,
          },
          headerStyle: {
            backgroundColor: CustomTheme.colors.card, 
          },
          headerTitleStyle: {
            color: CustomTheme.colors.text,
          },
          headerTintColor: CustomTheme.colors.text,
        }}
      >
        <Stack.Screen name="index" options={{ title: 'Civic Matchmaker' }} />
        <Stack.Screen name="locationSelect" options={{ title: 'Select your location' }} />
        <Stack.Screen name="about" options={{ title: 'About Us' }} />
      </Stack>
    </ThemeProvider>
  );
}
