import { useLayout } from '@/lib/useLayout';
import { Children, ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

/** Full-width stack of buttons on phones, a two-column grid on wider screens. */
export function ButtonGroup({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const { isWide } = useLayout();
  return (
    <View style={[styles.group, isWide && styles.row, style]}>
      {Children.map(children, (child) =>
        child ? <View style={isWide ? styles.cell : undefined}>{child}</View> : null,
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: 12 },
  row: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { flexGrow: 1, flexBasis: '45%' },
});
