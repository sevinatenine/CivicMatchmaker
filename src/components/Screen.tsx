import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { ReactNode } from 'react';
import { StyleSheet, Text } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

export function Screen({ children }: { children: ReactNode }) {
  return (
    <SafeAreaView style={styles.screen}>
      <Animated.View entering={FadeInDown.duration(350)} style={styles.content}>
        {children}
      </Animated.View>
    </SafeAreaView>
  );
}

export function ScreenTitle({ children }: { children: ReactNode }) {
  return <Text style={styles.title}>{children}</Text>;
}

export function ScreenSubtitle({ children }: { children: ReactNode }) {
  return <Text style={styles.subtitle}>{children}</Text>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  content: { flex: 1, paddingHorizontal: 24, paddingTop: 12, paddingBottom: 16 },
  title: { ...typography.title, color: Colors.text, marginTop: 8 },
  subtitle: {
    ...typography.body,
    color: Colors.textMuted,
    marginTop: 8,
    marginBottom: 28,
  },
});