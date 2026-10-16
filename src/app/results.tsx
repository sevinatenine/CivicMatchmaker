import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import { QUESTIONS } from '@/constants/questions';
import { CandidateMatch, MatchResult, runMatch } from '@/lib/matchApi';
import { typography } from '@/theme/typography';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

const LABELS = ['Strongly oppose', 'Oppose', 'Neutral', 'Support', 'Strongly support'];

function ScoreBar({ score }: { score: number }) {
  return (
    <View style={styles.track}>
      <View style={[styles.fill, { width: `${Math.max(2, score)}%` }]} />
    </View>
  );
}

function CandidateCard({ match }: { match: CandidateMatch }) {
  const [open, setOpen] = useState(false);
  const meta = [match.party, match.office].filter(Boolean).join(' · ');

  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{match.name}</Text>
          {!!meta && <Text style={styles.meta}>{meta}</Text>}
        </View>
        <Text style={styles.score}>{match.score === null ? '—' : `${match.score}%`}</Text>
      </View>

      {match.score === null ? (
        <Text style={styles.meta}>Not enough overlapping positions to compare.</Text>
      ) : (
        <>
          <ScoreBar score={match.score} />
          <Text style={styles.meta}>
            Based on {match.coverage} matching position{match.coverage === 1 ? '' : 's'}
          </Text>

          <Pressable onPress={() => setOpen((o) => !o)} hitSlop={8}>
            <Text style={styles.toggle}>{open ? 'Hide details' : 'Why this score?'}</Text>
          </Pressable>

          {open && (
            <View style={styles.details}>
              {Object.entries(match.sections).map(([section, s]) => (
                <Text key={section} style={styles.detailLine}>
                  {section}: {s === null ? '—' : `${s}%`}
                </Text>
              ))}
              {match.reasons.map((r, i) => (
                <View key={i} style={styles.reason}>
                  <Text style={styles.reasonText}>
                    You ({LABELS[r.yourAnswer - 1]}): {r.statement}
                  </Text>
                  <Text style={styles.reasonSub}>
                    They answered “{r.candidateAnswer}” to: {r.candidateQuestion} · {r.agreement}%
                    agreement
                  </Text>
                </View>
              ))}
            </View>
          )}
        </>
      )}
    </View>
  );
}

export default function ResultsPage() {
  const router = useRouter();
  const { state, city, answers } = useLocalSearchParams<{
    state: string;
    city: string;
    answers: string;
  }>();

  const [status, setStatus] = useState('Connecting…');
  const [result, setResult] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    const parsed: Record<string, number | string> = answers ? JSON.parse(answers) : {};

    const payload = {
      state,
      city,
      answers: QUESTIONS.filter((q) => parsed[q.id] !== undefined).map((q) => ({
        id: q.id,
        section: q.section,
        type: q.type,
        question: q.question,
        answer: parsed[q.id],
      })),
    };

    setResult(null);
    setError(null);
    setStatus('Connecting…');

    runMatch(
      payload,
      ({ event, data }) => {
        if (event === 'queued') setStatus(`Waiting in line (position ${data.position})…`);
        else if (event === 'started') setStatus('Matching your answers…');
        else if (event === 'progress' && data.candidate)
          setStatus(`Checked ${data.candidate} (${data.done}/${data.of})`);
        else if (event === 'result') setResult(data);
        else if (event === 'error') setError(data.message);
      },
      ctrl.signal,
    ).catch((e) => {
      if (!ctrl.signal.aborted) setError(e?.message ?? String(e));
    });

    return () => ctrl.abort(); // leaving the screen cancels the job on the server
  }, [state, city, answers]);

  return (
    <Screen scroll>
      <ScreenTitle>Your matches</ScreenTitle>
      <ScreenSubtitle>
        {city}, {state}
      </ScreenSubtitle>

      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : !result ? (
        <View style={styles.loading}>
          <ActivityIndicator color={Colors.button} />
          <Text style={styles.meta}>{status}</Text>
        </View>
      ) : (
        <>
          {result.matches.map((m) => (
            <CandidateCard key={m.id} match={m} />
          ))}
          <Text style={styles.footnote}>
            Scores compare your support/oppose answers to candidates’ recorded positions. They only
            cover issues where a matching position was found.
          </Text>
        </>
      )}

      <PrimaryButton title="Back to start" onPress={() => router.dismissAll()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: 'center', gap: 12, paddingVertical: 32 },
  error: { ...typography.body, color: '#E8A0A0', marginBottom: 24 },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 18,
    marginBottom: 16,
    gap: 10,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  name: { ...typography.heading, color: Colors.text },
  meta: { ...typography.label, color: Colors.textMuted },
  score: { ...typography.title, color: Colors.button },
  track: { height: 8, borderRadius: 4, backgroundColor: Colors.background, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4, backgroundColor: Colors.button },
  toggle: { ...typography.label, color: Colors.button },
  details: { gap: 8, marginTop: 4 },
  detailLine: { ...typography.label, color: Colors.text },
  reason: { backgroundColor: Colors.background, borderRadius: 12, padding: 12, gap: 4 },
  reasonText: { fontSize: 14, color: Colors.text },
  reasonSub: { fontSize: 13, color: Colors.textMuted },
  footnote: { ...typography.label, color: Colors.textMuted, marginBottom: 24 },
});