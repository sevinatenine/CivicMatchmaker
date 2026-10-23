import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors, partyColor } from '@/constants/Colors';
import { getLastResult } from '@/lib/lastResult';
import { BallotMeasure, CandidateMatch, Level } from '@/lib/matchApi';
import { typography } from '@/theme/typography';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

const LEVEL_ORDER: Level[] = ['Federal', 'State', 'Local', 'Other'];
const LEVEL_TITLE: Record<Level, string> = {
  Federal: 'Federal offices',
  State: 'State offices',
  Local: 'Local offices',
  Other: 'Other offices',
};
// Federal races in the order they appear on a real ballot
const FEDERAL_ORDER = ['President', 'Vice President', 'U.S. Senate', 'U.S. House'];
const ACCENTS = [Colors.red, Colors.blue];

type Race = {
  key: string;
  level: Level;
  title: string;
  subtitle: string;
  candidates: CandidateMatch[];
  isHouse: boolean;
};

function districtNumber(d: string | null): number | null {
  const n = parseInt(d ?? '', 10);
  return Number.isNaN(n) ? null : n;
}

/** Group the matched candidates into the races you'd see on a ballot. */
function buildRaces(matches: CandidateMatch[], yourDistrict: string | null): Race[] {
  const races = new Map<string, Race>();
  for (const m of matches) {
    if (m.onBallot === false) continue; // current officeholders who aren't running
    const federal = m.level === 'Federal' && FEDERAL_ORDER.includes(m.position);
    const isHouse = federal && m.position === 'U.S. House';
    const dn = isHouse ? (districtNumber(m.district) ?? districtNumber(yourDistrict)) : null;

    let key: string;
    let title: string;
    let subtitle: string;
    if (federal) {
      key = `${m.position}|${m.state ?? ''}|${dn ?? ''}`;
      title = m.position === 'U.S. Senate' ? 'United States Senator' : m.position;
      if (m.position === 'U.S. House') title = 'U.S. Representative';
      subtitle = isHouse
        ? dn
          ? `${m.state ?? ''} · District ${dn}`
          : `${m.state ?? ''} · At-large`
        : (m.state ?? '');
    } else {
      key = `${m.level}|${m.office}`; // from the ballot lookup: office already includes the district
      title = m.office || m.position;
      subtitle = m.state ?? '';
    }

    const race = races.get(key) ?? {
      key,
      level: m.level,
      title,
      subtitle,
      candidates: [],
      isHouse,
    };
    if (!race.candidates.some((c) => c.name === m.name)) race.candidates.push(m);
    races.set(key, race);
  }

  const federalRank = (r: Race) => {
    const i = FEDERAL_ORDER.findIndex((p) => r.key.startsWith(`${p}|`));
    return i === -1 ? FEDERAL_ORDER.length : i;
  };
  return Array.from(races.values())
    .map((r) => ({
      ...r,
      // Alphabetical by last name, like most printed ballots
      candidates: [...r.candidates].sort((a, b) =>
        lastName(a.name).localeCompare(lastName(b.name)),
      ),
    }))
    .sort(
      (a, b) =>
        LEVEL_ORDER.indexOf(a.level) - LEVEL_ORDER.indexOf(b.level) ||
        federalRank(a) - federalRank(b) ||
        a.subtitle.localeCompare(b.subtitle, undefined, { numeric: true }) ||
        a.title.localeCompare(b.title),
    );
}

function lastName(name: string): string {
  const words = name.replace(/,?\s+(jr|sr|ii|iii|iv)\.?$/i, '').trim().split(/\s+/);
  return words[words.length - 1] ?? name;
}

/* ---------- Pieces ---------- */

function Oval({ filled, color }: { filled: boolean; color: string }) {
  return (
    <View style={[styles.oval, { borderColor: filled ? color : Colors.textMuted }]}>
      {filled && <View style={[styles.ovalFill, { backgroundColor: color }]} />}
    </View>
  );
}

function CandidateRow({
  cand,
  marked,
  best,
  accent,
  onPress,
}: {
  cand: CandidateMatch;
  marked: boolean;
  best: boolean;
  accent: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ selected: marked, checked: marked }}
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && { backgroundColor: Colors.cardAlt }]}
    >
      <Oval filled={marked} color={accent} />
      <View style={{ flex: 1 }}>
        <Text style={styles.candName}>{cand.name}</Text>
        {!!cand.party && (
          <Text style={[styles.party, { color: partyColor(cand.party) }]}>{cand.party}</Text>
        )}
      </View>
      <View style={{ alignItems: 'flex-end', gap: 2 }}>
        <Text style={styles.match}>{cand.score === null ? '—' : `${cand.score}%`}</Text>
        <Text style={best ? [styles.matchLabel, { color: accent }] : styles.matchLabel}>
          {best ? 'Best match' : cand.score === null ? 'No score' : 'match'}
        </Text>
      </View>
    </Pressable>
  );
}

function RaceCard({
  race,
  accent,
  marked,
  onMark,
}: {
  race: Race;
  accent: string;
  marked: string | undefined;
  onMark: (id: string) => void;
}) {
  const scores = race.candidates.map((c) => c.score ?? -1);
  const top = Math.max(...scores);
  const bestCount = scores.filter((s) => s === top).length;

  return (
    <View style={[styles.card, { borderLeftColor: accent }]} accessibilityRole="radiogroup">
      <View style={styles.cardHead}>
        <Text style={styles.raceTitle}>{race.title}</Text>
        {!!race.subtitle && <Text style={styles.raceSub}>{race.subtitle}</Text>}
        <Text style={styles.voteFor}>Vote for one</Text>
      </View>
      {race.candidates.map((c) => (
        <CandidateRow
          key={c.id}
          cand={c}
          marked={marked === c.id}
          best={top >= 0 && bestCount === 1 && c.score === top}
          accent={accent}
          onPress={() => onMark(c.id)}
        />
      ))}
    </View>
  );
}

function MeasureCard({
  measure,
  accent,
  marked,
  onMark,
}: {
  measure: BallotMeasure;
  accent: string;
  marked: string | undefined;
  onMark: (v: string) => void;
}) {
  return (
    <View style={[styles.card, { borderLeftColor: accent }]} accessibilityRole="radiogroup">
      <View style={styles.cardHead}>
        <Text style={styles.raceTitle}>{measure.title}</Text>
        {!!measure.district && <Text style={styles.raceSub}>{measure.district}</Text>}
        {!!measure.subtitle && <Text style={styles.measureText}>{measure.subtitle}</Text>}
        {!!measure.url && (
          <Pressable onPress={() => Linking.openURL(measure.url!)} hitSlop={8}>
            <Text style={[styles.link, { color: accent }]}>Read the full text</Text>
          </Pressable>
        )}
      </View>
      {['Yes', 'No'].map((v) => (
        <Pressable
          key={v}
          accessibilityRole="radio"
          accessibilityState={{ selected: marked === v, checked: marked === v }}
          onPress={() => onMark(v)}
          style={({ pressed }) => [styles.row, pressed && { backgroundColor: Colors.cardAlt }]}
        >
          <Oval filled={marked === v} color={accent} />
          <Text style={styles.candName}>{v}</Text>
        </Pressable>
      ))}
    </View>
  );
}

/* ---------- Page ---------- */

export default function BallotPage() {
  const router = useRouter();
  const saved = getLastResult();
  const [marks, setMarks] = useState<Record<string, string>>({});
  const [showAllHouse, setShowAllHouse] = useState(false);

  const races = useMemo(
    () => (saved ? buildRaces(saved.result.matches, saved.result.location.district) : []),
    [saved],
  );
  const measures = saved?.result.ballot?.measures ?? [];

  if (!saved) {
    return (
      <Screen>
        <ScreenTitle>Sample ballot</ScreenTitle>
        <ScreenSubtitle>
          Finish the questions first. Your sample ballot is built from your location and matches.
        </ScreenSubtitle>
        <PrimaryButton title="Back to start" onPress={() => router.dismissAll()} />
      </Screen>
    );
  }

  const { result, state, city } = saved;
  const loc = result.location;
  const houseRaces = races.filter((r) => r.isHouse);
  // Without a street address we can't tell which House district you're in
  const hideHouse = !loc.districtKnown && houseRaces.length > 1 && !showAllHouse;
  const shown = hideHouse ? races.filter((r) => !r.isHouse) : races;
  const elections = result.ballot?.elections?.length
    ? result.ballot.elections.join(' · ')
    : 'General election · November 3, 2026';

  const mark = (key: string, value: string) => setMarks((prev) => ({ ...prev, [key]: value }));
  const total = shown.length + measures.length;
  const done = Object.keys(marks).length;

  let accentIndex = 0;
  const nextAccent = () => ACCENTS[accentIndex++ % ACCENTS.length];

  return (
    <Screen scroll>
      <ScreenTitle>Sample ballot</ScreenTitle>
      <ScreenSubtitle>
        {[city, state].filter(Boolean).join(', ')}
        {loc.districtKnown ? ` · District ${districtNumber(loc.district) || 'at-large'}` : ''}
        {'\n'}
        {elections}
      </ScreenSubtitle>

      <View style={styles.notice}>
        <Text style={styles.noticeText}>
          This is a practice ballot built from candidate filings near you. It is not your official
          ballot, and tapping an oval doesn’t record a vote. Check your county election office for
          the official sample ballot.
        </Text>
        <Pressable onPress={() => Linking.openURL('https://vote.gov')} hitSlop={8}>
          <Text style={[styles.link, { color: Colors.blue }]}>Find your official ballot at vote.gov</Text>
        </Pressable>
      </View>

      {total === 0 && !hideHouse && (
        <Text style={styles.empty}>We didn’t find any races on the 2026 ballot for this location.</Text>
      )}

      {LEVEL_ORDER.map((level) => {
        const group = shown.filter((r) => r.level === level);
        const houseNote = level === 'Federal' && hideHouse;
        if (!group.length && !houseNote) return null;
        return (
          <View key={level}>
            <Text style={styles.section}>{LEVEL_TITLE[level]}</Text>
            {group.map((r) => (
              <RaceCard
                key={r.key}
                race={r}
                accent={nextAccent()}
                marked={marks[r.key]}
                onMark={(id) => mark(r.key, id)}
              />
            ))}
            {houseNote && (
              <View style={[styles.card, { borderLeftColor: Colors.border }]}>
                <Text style={styles.raceTitle}>U.S. Representative</Text>
                <Text style={styles.measureText}>
                  {state} has {houseRaces.length} House districts and we don’t know which one is
                  yours. Go back and add your street address and ZIP to see just your race.
                </Text>
                <Pressable onPress={() => setShowAllHouse(true)} hitSlop={8}>
                  <Text style={[styles.link, { color: Colors.red }]}>
                    Show all {houseRaces.length} districts
                  </Text>
                </Pressable>
              </View>
            )}
          </View>
        );
      })}

      {measures.length > 0 && (
        <View>
          <Text style={styles.section}>Ballot measures</Text>
          {measures.map((m, i) => {
            const key = `measure|${i}|${m.title}`;
            return (
              <MeasureCard
                key={key}
                measure={m}
                accent={nextAccent()}
                marked={marks[key]}
                onMark={(v) => mark(key, v)}
              />
            );
          })}
        </View>
      )}

      {!result.ballot?.loaded && (
        <Text style={styles.footnote}>
          State and local races and ballot measures appear here when ballot data is available for
          your street address. {result.ballot?.note ?? ''}
        </Text>
      )}

      {total > 0 && (
        <Text style={styles.footnote}>
          You’ve marked {done} of {total} {total === 1 ? 'contest' : 'contests'}. Match scores
          come from your answers; candidates are listed alphabetically.
        </Text>
      )}

      <View style={styles.buttons}>
        <PrimaryButton
          tone="red"
          title="Find where to drop off your ballot"
          onPress={() => router.push('/dropoff')}
        />
        <PrimaryButton tone="red" title="Back to matches" onPress={() => router.back()} />
        <PrimaryButton title="Back to start" onPress={() => router.dismissAll()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  notice: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 14,
    gap: 8,
    marginBottom: 8,
  },
  noticeText: { fontSize: 13, lineHeight: 19, color: Colors.textMuted },
  link: { ...typography.label },
  empty: { ...typography.body, color: Colors.textMuted, marginVertical: 16 },
  section: {
    ...typography.label,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginTop: 20,
    marginBottom: 10,
  },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    borderLeftWidth: 4,
    paddingVertical: 14,
    paddingHorizontal: 14,
    marginBottom: 14,
    gap: 4,
  },
  cardHead: {
    gap: 4,
    paddingHorizontal: 4,
    paddingBottom: 10,
    marginBottom: 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  raceTitle: { ...typography.heading, color: Colors.text },
  raceSub: { ...typography.label, color: Colors.textMuted },
  voteFor: { fontSize: 12, fontStyle: 'italic', color: Colors.textMuted, marginTop: 2 },
  measureText: { fontSize: 14, lineHeight: 20, color: Colors.textMuted },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 12,
    paddingHorizontal: 4,
    borderRadius: 10,
  },
  oval: {
    width: 30,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  ovalFill: { width: 20, height: 10, borderRadius: 5 },
  candName: { fontSize: 16, fontWeight: '600', color: Colors.text },
  party: { ...typography.label, marginTop: 2 },
  match: { fontSize: 16, fontWeight: '700', color: Colors.text },
  matchLabel: { fontSize: 11, fontWeight: '600', color: Colors.textMuted },
  footnote: { ...typography.label, color: Colors.textMuted, marginTop: 12, lineHeight: 18 },
  buttons: { gap: 12, marginTop: 24 },
});
