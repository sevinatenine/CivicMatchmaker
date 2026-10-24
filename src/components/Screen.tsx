import { Colors } from '@/constants/Colors';
import { useLayout } from '@/lib/useLayout';
import { typography } from '@/theme/typography';
import { useHeaderHeight } from 'expo-router/react-navigation';
import { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text } from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

// Content column widths: narrow for short forms, wide for grids, normal for everything else
const MAX_WIDTH = { narrow: 560, normal: 720, wide: 1120 };
export type ScreenWidth = keyof typeof MAX_WIDTH;

export function Screen({
  children,
  scroll = false,
  width = 'normal',
}: {
  children: ReactNode;
  scroll?: boolean;
  width?: ScreenWidth;
}) {
  // The keyboard's position is measured from the top of the screen, but this view starts
  // below the header, so offset by the header's height. On Android, if the window already
  // shrank for the keyboard, there's no overlap and this adds nothing.
  const headerHeight = useHeaderHeight();
  const { gutter, isWide } = useLayout();
  const column = {
    maxWidth: MAX_WIDTH[width],
    paddingHorizontal: gutter,
    paddingTop: isWide ? 32 : 12,
  };

  if (scroll) {
    return (
      <KeyboardAvoidingView
        style={styles.screen}
        behavior="padding"
        keyboardVerticalOffset={headerHeight}
      >
        <SafeAreaView style={styles.screen} edges={['bottom', 'left', 'right']}>
          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
            // On web, react-native-web dismisses on *any* scroll, including the one that brings a
            // focused text box into view above a tablet's keyboard, so the box loses focus at once
            keyboardDismissMode={Platform.OS === 'web' ? 'none' : 'on-drag'}
          >
            <Animated.View entering={FadeInDown.duration(350)} style={[styles.column, column]}>
              {children}
            </Animated.View>
          </ScrollView>
        </SafeAreaView>
      </KeyboardAvoidingView>
    );
  }

  return (
    <SafeAreaView style={styles.screen} edges={['bottom', 'left', 'right']}>
      <Animated.View
        entering={FadeInDown.duration(350)}
        style={[styles.column, styles.content, column]}
      >
        {children}
      </Animated.View>
    </SafeAreaView>
  );
}

export function ScreenTitle({ children }: { children: ReactNode }) {
  const { isDesktop } = useLayout();
  return <Text style={[styles.title, isDesktop && styles.titleLarge]}>{children}</Text>;
}

export function ScreenSubtitle({ children }: { children: ReactNode }) {
  return <Text style={styles.subtitle}>{children}</Text>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  column: { width: '100%', alignSelf: 'center' },
  content: { flex: 1, paddingBottom: 16 },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 48 },
  title: { ...typography.title, color: Colors.text, marginTop: 8 },
  titleLarge: { fontSize: 38, lineHeight: 44, letterSpacing: -0.9 },
  subtitle: {
    ...typography.body,
    color: Colors.textMuted,
    marginTop: 8,
    marginBottom: 28,
    maxWidth: 620,
  },
});
