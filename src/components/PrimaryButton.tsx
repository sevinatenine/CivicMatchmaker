import { Colors } from '@/constants/Colors';
import { useState } from 'react';
import { Pressable, StyleProp, StyleSheet, Text, ViewStyle } from 'react-native';

export function PrimaryButton({
  title,
  onPress,
  disabled,
  tone = 'blue',
  variant = 'solid',
  style,
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  tone?: 'blue' | 'red';
  variant?: 'solid' | 'ghost';
  style?: StyleProp<ViewStyle>;
}) {
  const [hovered, setHovered] = useState(false); // web / mouse only
  const color = Colors[tone];
  const ghost = variant === 'ghost';

  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      style={({ pressed }) => [
        styles.button,
        ghost ? { borderColor: color, borderWidth: 1.5 } : { backgroundColor: color },
        hovered && !disabled && (ghost ? { backgroundColor: Colors[`${tone}Soft`] } : styles.hovered),
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
        style,
      ]}
    >
      <Text
        style={[styles.text, ghost && { color }, disabled && styles.textDisabled]}
        numberOfLines={1}
      >
        {title}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hovered: { opacity: 0.9, transform: [{ translateY: -1 }] },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  disabled: { backgroundColor: Colors.card, borderColor: Colors.border },
  text: { color: Colors.onButton, fontSize: 17, fontWeight: '700' },
  textDisabled: { color: Colors.textMuted },
});
