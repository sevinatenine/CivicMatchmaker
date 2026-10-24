import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

/**
 * Shown on the results screen while the match waits for a free server slot. The job stays
 * queued only while this screen is open, so the results replace this card when they arrive.
 * position: place in line, or null when unknown (the server's line was full and we're retrying).
 */
export function QueueNotice({ position }: { position: number | null }) {
  return (
    <View style={styles.card}>
      <View style={styles.top}>
        <ActivityIndicator color={Colors.button} />
        <Text style={styles.title}>You’re in line</Text>
      </View>
      <Text style={styles.body}>
        CivicMatchmaker is a self-funded project built by Peak to Peak students, so we can only match a
        few people at a time.
      </Text>
      <Text style={styles.body}>
        {position ? `You’re number ${position} in the queue.` : 'You’re in the queue.'} Please wait about
        30 seconds.
      </Text>
      <Text style={styles.note}>Keep this page open. Your results will appear here automatically.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 18,
    marginVertical: 16,
    gap: 10,
  },
  top: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  title: { ...typography.heading, color: Colors.text },
  body: { ...typography.body, color: Colors.text },
  note: { ...typography.label, color: Colors.textMuted },
});
