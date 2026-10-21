import { Colors } from '@/constants/Colors';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

/** Thin half red, half blue bar. */
export function PartyStripe({ style }: { style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.stripe, style]}>
      <View style={[styles.half, { backgroundColor: Colors.red }]} />
      <View style={[styles.half, { backgroundColor: Colors.blue }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  stripe: { flexDirection: 'row', height: 3 },
  half: { flex: 1 },
});
