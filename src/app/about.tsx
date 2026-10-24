import { PartyStripe } from '@/components/PartyStripe';
import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

const SECTIONS = [
  {
    title: 'What we do',
    body: 'CivicMatchmaker compares your views on the issues with the recorded positions of the candidates on your ballot, then ranks them by how closely they line up. You also get a sample ballot, a map of places to vote, and a plain-language guide to voting.',
  },
  {
    title: 'Where the data comes from',
    body: 'Candidate positions come from how candidates answered Vote Smart’s Political Courage Test, a public issue survey. Ballot contests and voting locations come from public election data. Coverage varies, so some candidates have fewer positions to compare.',
  },
  {
    title: 'Nonpartisan by design',
    body: 'We are not affiliated with any party, campaign or candidate. Scores only reflect how your answers compare with candidates’ stated positions, never a recommendation of who to vote for.',
  },
];

export default function AboutPage() {
  const router = useRouter();

  return (
    <Screen scroll>
      <ScreenTitle>About CivicMatchmaker</ScreenTitle>
      <ScreenSubtitle>
        A simple way to see which candidates share your priorities before you fill in your ballot.
      </ScreenSubtitle>

      {SECTIONS.map((s) => (
        <View key={s.title} style={styles.card}>
          <Text style={styles.cardTitle}>{s.title}</Text>
          <Text style={styles.cardBody}>{s.body}</Text>
        </View>
      ))}

      <PartyStripe style={styles.stripe} />

      <PrimaryButton tone="red" title="Get matched" onPress={() => router.replace('/locationSelect')} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 18,
    marginBottom: 14,
    gap: 8,
  },
  cardTitle: { ...typography.heading, color: Colors.text },
  cardBody: { ...typography.body, color: Colors.textMuted },
  stripe: { borderRadius: 2, overflow: 'hidden', marginVertical: 20 },
});
