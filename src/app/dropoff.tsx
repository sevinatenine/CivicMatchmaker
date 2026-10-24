import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { VotingMap } from '@/components/VotingMap';
import { Colors } from '@/constants/Colors';
import { getLastResult } from '@/lib/lastResult';
import { fetchVotingPlaces, VotingPlace, VotingPlaces } from '@/lib/votingPlacesApi';
import { typography } from '@/theme/typography';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

type Tab = 'dropOff' | 'earlyVote' | 'polling';
const TABS: { key: Tab; label: string }[] = [
  { key: 'dropOff', label: 'Drop off ballot' },
  { key: 'earlyVote', label: 'Vote early' },
  { key: 'polling', label: 'Election Day' },
];
const ACCENTS = [Colors.red, Colors.blue];

const noSubscribe = () => () => {};

/** "123 MAIN ST, BROOMFIELD, CO, 80020" (Census matched address) -> street + ZIP. */
function splitMatchedAddress(matched: string | null | undefined) {
  const parts = (matched ?? '').split(',').map((s) => s.trim());
  const zip = /^\d{5}/.test(parts[parts.length - 1] ?? '') ? parts[parts.length - 1] : '';
  return { street: parts.length > 1 ? parts[0] : '', zip };
}

function shortDate(iso: string | null): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? '');
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])); // local time, not UTC
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function openDirections(place: VotingPlace) {
  const dest =
    place.lat !== null && place.lng !== null
      ? `${place.lat},${place.lng}`
      : encodeURIComponent(place.address || place.name);
  // In a phone browser, check the device: iPhones open Apple Maps, everything else Google Maps
  const isApple =
    Platform.OS === 'ios' ||
    (Platform.OS === 'web' &&
      typeof navigator !== 'undefined' &&
      /iPhone|iPad|iPod|Macintosh/.test(navigator.userAgent) &&
      'ontouchend' in document);
  const url = isApple
    ? `https://maps.apple.com/?daddr=${dest}`
    : `https://www.google.com/maps/dir/?api=1&destination=${dest}`;
  Linking.openURL(url);
}

/* ---------- Pieces ---------- */

function Field({
  label,
  value,
  placeholder,
  onChangeText,
  keyboardType,
  autoComplete,
  style,
}: {
  label: string;
  value: string;
  placeholder: string;
  onChangeText: (v: string) => void;
  keyboardType?: 'default' | 'number-pad';
  autoComplete?: 'street-address' | 'postal-code';
  style?: object;
}) {
  return (
    <View style={style}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={Colors.textMuted}
        selectionColor={Colors.button}
        keyboardAppearance="dark"
        keyboardType={keyboardType}
        autoComplete={autoComplete}
        autoCorrect={false}
        style={styles.input}
      />
    </View>
  );
}

function PlaceCard({
  place,
  accent,
  selected,
  onPress,
}: {
  place: VotingPlace;
  accent: string;
  selected: boolean;
  onPress: () => void;
}) {
  const start = shortDate(place.startDate);
  const end = shortDate(place.endDate);
  const dates = start && end ? (start === end ? start : `${start} – ${end}`) : (start ?? end);

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.card,
        { borderLeftColor: accent },
        selected && { backgroundColor: Colors.redSoft, borderColor: Colors.red },
        pressed && { backgroundColor: Colors.cardAlt },
      ]}
    >
      <View style={styles.cardTop}>
        <Text style={styles.placeName}>{place.name}</Text>
        {place.distanceMiles !== null && (
          <Text style={styles.distance}>{place.distanceMiles} mi</Text>
        )}
      </View>
      {!!place.address && <Text style={styles.placeText}>{place.address}</Text>}
      {!!dates && <Text style={styles.placeMeta}>Open {dates}</Text>}
      {!!place.hours && <Text style={styles.placeMeta}>{place.hours}</Text>}
      {!!place.notes && <Text style={styles.placeText}>{place.notes}</Text>}
      <Pressable onPress={() => openDirections(place)} hitSlop={8}>
        <Text style={[styles.link, { color: accent }]}>Get directions</Text>
      </Pressable>
    </Pressable>
  );
}

/* ---------- Page ---------- */

export default function DropOffPage() {
  const router = useRouter();
  const params = useLocalSearchParams<{
    state?: string;
    city?: string;
    address?: string;
    zip?: string;
  }>();
  const saved = getLastResult();
  const fromMatch = splitMatchedAddress(saved?.result.location.matchedAddress);

  const state = params.state || saved?.state || '';
  const city = params.city || saved?.city || '';
  const [street, setStreet] = useState(params.address || fromMatch.street);
  const [zip, setZip] = useState(params.zip || fromMatch.zip);

  const [data, setData] = useState<VotingPlaces | null>(null);
  // Starts true when we already know your address, since the first search runs on open
  const [loading, setLoading] = useState(() => !!street.trim());
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('dropOff');
  const [selected, setSelected] = useState<number | null>(null);
  const abort = useRef<AbortController | null>(null);

  /** Starts a request, cancelling any earlier one. State is only set once it settles. */
  const load = useCallback(
    (address: string, zipCode: string) => {
      abort.current?.abort();
      const controller = new AbortController();
      abort.current = controller;
      fetchVotingPlaces(
        { state, city, address: address.trim(), zip: zipCode.trim() },
        controller.signal,
      )
        .then((res) => {
          setData(res);
          setError(null);
          // Open the first tab that has anything in it
          setTab(TABS.find((t) => res[t.key].length > 0)?.key ?? 'dropOff');
        })
        .catch((e) => {
          if (e?.name !== 'AbortError') setError(e?.message ?? 'Could not reach the server.');
        })
        .finally(() => {
          if (abort.current === controller) setLoading(false);
        });
    },
    [state, city],
  );

  const search = (address: string, zipCode: string) => {
    setLoading(true);
    setError(null);
    setSelected(null);
    load(address, zipCode);
  };

  // Search right away when we already know your address
  useEffect(() => {
    if (street.trim()) load(street, zip);
    return () => abort.current?.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only on first open
  }, []);

  // On web, the static HTML is built without the URL's ?state=&address=, so render a neutral
  // placeholder until we're in the browser; otherwise opening a shared link mismatches it.
  const inBrowser = useSyncExternalStore(noSubscribe, () => true, () => false);
  if (!inBrowser) {
    return (
      <Screen>
        <ScreenTitle>Where to vote</ScreenTitle>
      </Screen>
    );
  }

  if (!state) {
    return (
      <Screen>
        <ScreenTitle>Where to vote</ScreenTitle>
        <ScreenSubtitle>
          Pick your location first so we know which state’s election to look up.
        </ScreenSubtitle>
        <PrimaryButton title="Back to start" onPress={() => router.dismissAll()} />
      </Screen>
    );
  }

  const places = data ? data[tab] : [];
  const anyPlaces = !!data && TABS.some((t) => data[t.key].length > 0);
  const officialUrl = data?.officialUrl ?? 'https://www.vote.org/polling-place-locator/';

  return (
    <Screen scroll>
      <ScreenTitle>Where to vote</ScreenTitle>
      <ScreenSubtitle>
        Find ballot drop boxes, early voting sites, and your Election Day polling place near{' '}
        {[city, state].filter(Boolean).join(', ')}.
      </ScreenSubtitle>

      <View style={styles.form}>
        <Field
          label="Street address"
          placeholder="123 Main St"
          value={street}
          autoComplete="street-address"
          onChangeText={setStreet}
        />
        <Field
          label="ZIP code"
          placeholder="80020"
          value={zip}
          keyboardType="number-pad"
          autoComplete="postal-code"
          onChangeText={setZip}
        />
        <PrimaryButton
          title={loading ? 'Searching…' : 'Find places near me'}
          disabled={loading || !street.trim()}
          onPress={() => search(street, zip)}
        />
      </View>

      {loading && (
        <View style={styles.loading}>
          <ActivityIndicator color={Colors.button} />
        </View>
      )}

      {!!error && <Text style={styles.error}>{error}</Text>}

      {data && !loading && (
        <>
          {!!data.election && (
            <Text style={styles.section}>
              {data.election}
              {data.electionDay ? ` · ${shortDate(data.electionDay)}` : ''}
            </Text>
          )}

          {data.mailOnly && (
            <Text style={styles.placeText}>
              Your area votes by mail. Mail your ballot back, or return it at a drop-off location.
            </Text>
          )}

          {anyPlaces && (
            <>
              <View style={styles.tabs}>
                {TABS.map((t) => {
                  const active = t.key === tab;
                  return (
                    <Pressable
                      key={t.key}
                      accessibilityRole="tab"
                      accessibilityState={{ selected: active }}
                      onPress={() => {
                        setTab(t.key);
                        setSelected(null);
                      }}
                      style={[styles.tab, active && styles.tabActive]}
                    >
                      <Text style={[styles.tabText, active && { color: Colors.onButton }]}>
                        {t.label} ({data[t.key].length})
                      </Text>
                    </Pressable>
                  );
                })}
              </View>

              {/* totals is optional so an older server without it still works */}
              {(data.totals?.[tab] ?? 0) > places.length && (
                <Text style={[styles.placeText, { marginBottom: 12 }]}>
                  Showing the {places.length} nearest of {data.totals[tab]}.
                </Text>
              )}

              <VotingMap
                places={places}
                origin={data.origin}
                selected={selected}
                onSelect={setSelected}
              />

              {places.length === 0 && (
                <Text style={styles.empty}>No locations of this kind were listed for you.</Text>
              )}
              {places.map((p, i) => (
                <PlaceCard
                  key={`${tab}-${i}-${p.name}`}
                  place={p}
                  accent={ACCENTS[i % ACCENTS.length]}
                  selected={selected === i}
                  onPress={() => setSelected(i)}
                />
              ))}
            </>
          )}

          {!!data.note && <Text style={styles.empty}>{data.note}</Text>}
        </>
      )}

      <View style={styles.notice}>
        <Text style={styles.noticeText}>
          Locations and hours come from Google’s Civic Information data and can change. Always
          confirm with your election office before you go.
        </Text>
        <Pressable onPress={() => Linking.openURL(officialUrl)} hitSlop={8}>
          <Text style={[styles.link, { color: Colors.red }]}>
            {data?.officialName ? `Check with ${data.officialName}` : 'Look up your official voting locations'}
          </Text>
        </Pressable>
      </View>

      <View style={styles.buttons}>
        <PrimaryButton tone="red" title="Back" onPress={() => router.back()} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  form: { gap: 16, marginBottom: 8 },
  fieldLabel: { ...typography.label, color: Colors.textMuted, marginBottom: 8 },
  input: {
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: Colors.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    borderRadius: 14,
    fontSize: 16,
    color: Colors.text,
  },
  loading: { alignItems: 'center', paddingVertical: 24 },
  error: { ...typography.body, color: Colors.red, marginVertical: 16 },
  section: {
    ...typography.label,
    color: Colors.red,
    textTransform: 'uppercase',
    marginTop: 20,
    marginBottom: 10,
  },
  tabs: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8, marginBottom: 16 },
  tab: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 999,
    backgroundColor: Colors.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  tabActive: { backgroundColor: Colors.red, borderColor: Colors.red },
  tabText: { ...typography.label, color: Colors.text },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    borderLeftWidth: 4,
    padding: 16,
    marginBottom: 12,
    gap: 4,
  },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  placeName: { flex: 1, fontSize: 16, fontWeight: '600', color: Colors.text },
  distance: { fontSize: 14, fontWeight: '700', color: Colors.text },
  placeText: { fontSize: 14, lineHeight: 20, color: Colors.textMuted },
  placeMeta: { ...typography.label, color: Colors.text },
  link: { ...typography.label, marginTop: 6 },
  empty: { ...typography.body, color: Colors.textMuted, marginVertical: 16 },
  notice: {
    backgroundColor: Colors.card,
    borderRadius: 14,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 14,
    gap: 8,
    marginTop: 16,
  },
  noticeText: { fontSize: 13, lineHeight: 19, color: Colors.textMuted },
  buttons: { gap: 12, marginTop: 24 },
});
