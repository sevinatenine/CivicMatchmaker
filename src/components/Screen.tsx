import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { useHeaderHeight } from 'expo-router/react-navigation';
import { ReactNode } from 'react';
import { KeyboardAvoidingView, ScrollView, StyleSheet, Text } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

export function Screen({ children, scroll = false }: { children: ReactNode; scroll?: boolean }) {
  // The keyboard's position is measured from the top of the screen, but this view starts
  // below the header, so offset by the header's height. On Android, if the window already
  // shrank for the keyboard, there's no overlap and this adds nothing.
  const headerHeight = useHeaderHeight();

  if (scroll) {
    return (
      <KeyboardAvoidingView
        style={styles.screen}
        behavior="padding"
        keyboardVerticalOffset={headerHeight}
      >
        <SafeAreaView style={styles.screen}>
          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            keyboardDismissMode="on-drag"
          >
            <Animated.View entering={FadeInDown.duration(350)}>{children}</Animated.View>
          </ScrollView>
        </SafeAreaView>
      </KeyboardAvoidingView>
    );
  }

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

// ScreenTitle and ScreenSubtitle unchanged

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  content: { flex: 1, paddingHorizontal: 24, paddingTop: 12, paddingBottom: 16 },
  scroll: { flex: 1 },
  scrollContent: { paddingHorizontal: 24, paddingTop: 12, paddingBottom: 40 },
  title: { ...typography.title, color: Colors.text, marginTop: 8 },
  subtitle: {
    ...typography.body,
    color: Colors.textMuted,
    marginTop: 8,
    marginBottom: 28,
  },
});