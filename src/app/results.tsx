import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import { QUESTIONS } from '@/constants/questions';
import { CandidateMatch, Level, MatchResult, runMatch } from '@/lib/matchApi';
import { typography } from '@/theme/typography';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

const LABELS = ['Strongly oppose', 'Oppose', 'Neutral', 'Support', 'Strongly support'];
const LEVEL_ORDER: Level[] = ['Federal', 'State', 'Local', 'Other'];

function importanceLabel(w?: number): string | null {
  if (!w || w === 1) return null;
  if (w >= 3) return 'Top priority for you';
  if (w >= 2) return 'High priority for you';
  return w < 1 ? 'Low priority for you' : null;
}

function districtLabel(m: CandidateMatch): string {
  if (m.position !== 'U.S. House' || m.district === null) return m.position;
  const n = parseInt(m.district, 10);
  return Number.isNaN(n) || n === 0
    ? `${m.position} · At-large`
    : `${m.position} · District ${n}`;
}

function Chip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        selected && styles.chipSelected,
        pressed && !selected && { backgroundColor: Colors.cardAlt },
      ]}
    >
      <Text style={[styles.chipText, selected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

function ChipRow({
  title,
  options,
  value,
  onChange,
}: {
  title: string;
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <View style={{ gap: 8 }}>
      <Text style={styles.filterTitle}>{title}</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
        {options.map((o) => (
          <Chip
            key={o.value}
            label={o.label}
            selected={value === o.value}
            onPress={() => onChange(o.value)}
          />
        ))}
      </ScrollView>
    </View>
  );
}

function ScoreBar({ score }: { score: number }) {
  return (
    <View style={styles.track}>
      <View style={[styles.fill, { width: `${Math.max(2, score)}%` }]} />
    </View>
  );
}

function CandidateCard({ match }: { match: CandidateMatch }) {
  const [open, setOpen] = useState(false);
  const meta = [match.party, districtLabel(match)].filter(Boolean).join(' · ');

  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{match.name}</Text>
          {!!meta && <Text style={styles.meta}>{meta}</Text>}
          <Text style={styles.level}>{match.level}</Text>
        </View>
        <Text style={styles.score}>{match.score === null ? '—' : `${match.score}%`}</Text>
      </View>

      {match.ballotOnly ? (
        <>
          <Text style={styles.meta}>
            On your ballot. No recorded issue positions, so there is no match score.
          </Text>
          {!!match.url && (
            <Pressable onPress={() => Linking.openURL(match.url!)} hitSlop={8}>
              <Text style={styles.toggle}>Campaign website</Text>
            </Pressable>
          )}
        </>
      ) : match.score === null ? (
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
                  {!!importanceLabel(r.importance) && (
                    <Text style={styles.reasonTag}>{importanceLabel(r.importance)}</Text>
                  )}
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
  const { state, city, address, zip, answers, weights } = useLocalSearchParams<{
    state: string;
    city: string;
    address?: string;
    zip?: string;
    answers: string;
    weights?: string;
  }>();

  const [status, setStatus] = useState('Connecting…');
  const [result, setResult] = useState<MatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [level, setLevel] = useState<string>('All');
  const [position, setPosition] = useState<string>('All');

  useEffect(() => {
    const ctrl = new AbortController();
    const parsed: Record<string, number | string> = answers ? JSON.parse(answers) : {};
    const parsedWeights: Record<string, number> = weights ? JSON.parse(weights) : {};

    const payload = {
      state,
      city,
      address: address || undefined,
      zip: zip || undefined,
      answers: QUESTIONS.filter((q) => parsed[q.id] !== undefined).map((q) => ({
        id: q.id,
        section: q.section,
        type: q.type,
        question: q.question,
        answer: parsed[q.id],
        weight: parsedWeights[q.id] ?? 1,
      })),
    };

    setResult(null);
    setError(null);
    setStatus('Connecting…');
    setLevel('All');
    setPosition('All');

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
  }, [state, city, address, zip, answers, weights]);

  const matches = useMemo(() => result?.matches ?? [], [result]);

  // Level chips: only levels that actually have candidates
  const levelOptions = useMemo(
    () => [
      { value: 'All', label: `All (${matches.length})` },
      ...LEVEL_ORDER.filter((l) => matches.some((m) => m.level === l)).map((l) => ({
        value: l,
        label: `${l} (${matches.filter((m) => m.level === l).length})`,
      })),
    ],
    [matches],
  );

  // Position chips: positions that exist within the chosen level
  const positionOptions = useMemo(() => {
    const inLevel = matches.filter((m) => level === 'All' || m.level === level);
    const names = Array.from(new Set(inLevel.map((m) => m.position)));
    return [
      { value: 'All', label: `All (${inLevel.length})` },
      ...names.map((p) => ({
        value: p,
        label: `${p} (${inLevel.filter((m) => m.position === p).length})`,
      })),
    ];
  }, [matches, level]);

  const visible = useMemo(
    () =>
      matches.filter(
        (m) => (level === 'All' || m.level === level) && (position === 'All' || m.position === position),
      ),
    [matches, level, position],
  );

  const loc = result?.location;

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
          {loc &&
            (loc.districtKnown ? (
              <Text style={styles.locNote}>
                Showing U.S. House district {parseInt(loc.district ?? '0', 10) || 'at-large'}
                {loc.county ? ` · ${loc.county}` : ''}
                {loc.matchedAddress ? ` (matched: ${loc.matchedAddress})` : ''}, plus statewide and
                national races.
              </Text>
            ) : loc.addressGiven ? (
              <Text style={styles.locNote}>
                We couldn’t find your district from that address. {loc.geocodeError ?? ''} Every
                House race in {state} is shown. Go back and double-check the street address and
                ZIP.
              </Text>
            ) : (
              <Text style={styles.locNote}>
                We don’t know your exact district, so every House race in {state} is shown. Go back
                and add a street address + ZIP to narrow it to yours.
              </Text>
            ))}

          {result.ballot?.note ? (
            <Text style={styles.locNote}>{result.ballot.note}</Text>
          ) : result.ballot?.loaded ? (
            <Text style={styles.locNote}>
              Local and state races from your ballot ({result.ballot.elections.join(', ')}) are
              listed without scores.
            </Text>
          ) : null}

          <View style={styles.filters}>
            <ChipRow
              title="Level"
              options={levelOptions}
              value={level}
              onChange={(v) => {
                setLevel(v);
                setPosition('All'); // positions depend on the level
              }}
            />
            <ChipRow
              title="Position"
              options={positionOptions}
              value={position}
              onChange={setPosition}
            />
          </View>

          {visible.length === 0 ? (
            <Text style={styles.meta}>No candidates match these filters.</Text>
          ) : (
            visible.map((m) => <CandidateCard key={m.id} match={m} />)
          )}

          <Text style={styles.footnote}>
            Scores compare your support/oppose answers to candidates’ recorded positions. They only
            cover issues where a matching position was found. Questions you marked as more
            important count for more.
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
  locNote: { ...typography.label, color: Colors.textMuted, lineHeight: 18, marginBottom: 16 },
  filters: { gap: 14, marginBottom: 20 },
  filterTitle: {
    ...typography.label,
    color: Colors.textMuted,
    textTransform: 'uppercase',
  },
  chips: { gap: 8, paddingRight: 8 },
  chip: {
    paddingVertical: 9,
    paddingHorizontal: 14,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
  },
  chipSelected: { backgroundColor: Colors.button, borderColor: Colors.button },
  chipText: { fontSize: 14, fontWeight: '600', color: Colors.text },
  chipTextSelected: { color: Colors.onButton },
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
  level: { ...typography.label, color: Colors.button, marginTop: 2 },
  score: { ...typography.title, color: Colors.button },
  track: { height: 8, borderRadius: 4, backgroundColor: Colors.background, overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4, backgroundColor: Colors.button },
  toggle: { ...typography.label, color: Colors.button },
  details: { gap: 8, marginTop: 4 },
  detailLine: { ...typography.label, color: Colors.text },
  reason: { backgroundColor: Colors.background, borderRadius: 12, padding: 12, gap: 4 },
  reasonTag: { ...typography.label, color: Colors.button },
  reasonText: { fontSize: 14, color: Colors.text },
  reasonSub: { fontSize: 13, color: Colors.textMuted },
  footnote: { ...typography.label, color: Colors.textMuted, marginBottom: 24 },
});