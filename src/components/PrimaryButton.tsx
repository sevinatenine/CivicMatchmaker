import { Colors } from '@/constants/Colors';
import { Pressable, StyleSheet, Text } from 'react-native';

export function PrimaryButton({
  title,
  onPress,
  disabled,
  tone = 'blue',
}: {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  tone?: 'blue' | 'red';
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: Colors[tone] },
        disabled && styles.disabled,
        pressed && !disabled && styles.pressed,
      ]}
    >
      <Text style={[styles.text, disabled && styles.textDisabled]}>{title}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  disabled: { backgroundColor: Colors.card },
  text: { color: Colors.onButton, fontSize: 17, fontWeight: '700' },
  textDisabled: { color: Colors.textMuted },
});