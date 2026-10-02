import { City, State } from 'country-state-city';
import { useRouter } from 'expo-router';
import { useTheme } from 'expo-router/react-navigation';
import { useMemo, useState } from 'react';
import {
  Button,
  FlatList, Modal, Pressable, SafeAreaView, StyleSheet, Text, TextInput, View
} from 'react-native';

type Option = { label: string; value: string };
type Location = { country: string | null; state: string | null; city: string | null };

function SelectField({
  label, value, placeholder, options, onSelect, disabled,
}: {
  label: string;
  value: string;
  placeholder: string;
  options: Option[];
  onSelect: (v: string) => void;
  disabled?: boolean;
}) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selected = options.find(o => o.value === value);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? options.filter(o => o.label.toLowerCase().includes(q)) : options;
  }, [options, query]);

  const close = () => { setOpen(false); setQuery(''); };

  return (
    <View style={{ opacity: disabled ? 0.4 : 1 }}>
      <Text style={[styles.fieldLabel, { color: colors.text }]}>{label}</Text>
      <Pressable
        disabled={disabled}
        onPress={() => setOpen(true)}
        style={[styles.field, { backgroundColor: colors.card, borderColor: colors.border }]}
      >
        <Text style={{ color: selected ? colors.text : colors.text + '80', fontSize: 16, flex: 1 }} numberOfLines={1}>
          {selected?.label ?? placeholder}
        </Text>
        <Text style={{ color: colors.text + '80', fontSize: 18 }}>⌄</Text>
      </Pressable>

      <Modal visible={open} animationType="slide" presentationStyle="pageSheet" onRequestClose={close}>
        <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
          <View style={styles.sheetHeader}>
            <Text style={[styles.sheetTitle, { color: colors.text }]}>{label}</Text>
            <Pressable onPress={close} hitSlop={12}>
              <Text style={{ color: colors.primary, fontSize: 16, fontWeight: '600' }}>Done</Text>
            </Pressable>
          </View>

          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder={`Search ${label.toLowerCase()}...`}
            placeholderTextColor={colors.text + '80'}
            autoCorrect={false}
            style={[styles.search, { backgroundColor: colors.card, borderColor: colors.border, color: colors.text }]}
          />

          <FlatList
            data={filtered}
            keyExtractor={(o, i) => `${o.value}-${i}`}
            keyboardShouldPersistTaps="handled"
            initialNumToRender={20}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => { onSelect(item.value); close(); }}
                style={[styles.row, { borderBottomColor: colors.border }]}
              >
                <Text style={{ color: colors.text, fontSize: 16, flex: 1 }}>{item.label}</Text>
                {item.value === value && <Text style={{ color: colors.primary, fontSize: 18 }}>✓</Text>}
              </Pressable>
            )}
            ListEmptyComponent={
              <Text style={{ color: colors.text + '80', textAlign: 'center', marginTop: 32 }}>No results</Text>
            }
          />
        </SafeAreaView>
      </Modal>
    </View>
  );
}
const COUNTRY_CODE = 'US';

export function LocationForm({ onChange }: { onChange?: (l: Location) => void }) {
  const [stateCode, setStateCode] = useState('');
  const [city, setCity] = useState('');

  const states = useMemo(
    () => State.getStatesOfCountry(COUNTRY_CODE).map(s => ({ label: s.name, value: s.isoCode })),
    []
  );
  const cities = useMemo(
    () => (stateCode
      ? City.getCitiesOfState(COUNTRY_CODE, stateCode).map(c => ({ label: c.name, value: c.name }))
      : []),
    [stateCode]
  );

  const emit = (s: string, ci: string) =>
    onChange?.({
      country: 'United States',
      state: s ? State.getStateByCodeAndCountry(s, COUNTRY_CODE)?.name ?? null : null,
      city: ci || null,
    });

  return (
    <View style={styles.form}>
      <SelectField
        label="State" placeholder="Select state" value={stateCode} options={states}
        onSelect={(v) => { setStateCode(v); setCity(''); emit(v, ''); }}
      />
      <SelectField
        label="City" placeholder="Select city" value={city} options={cities}
        disabled={!stateCode || cities.length === 0}
        onSelect={(v) => { setCity(v); emit(stateCode, v); }}
      />
    </View>
  );
}

export default function LocationSelectPage() {
  const { colors } = useTheme();
  const router = useRouter(); 
  const [location, setLocation] = useState<Location | null>(null);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={[styles.container]}>
        <Text style={[styles.title, { color: colors.text }]}>Select your location</Text>
        <Text style={[styles.subtitle, { color: colors.text }]}>
          We ask this so we can find candidates near you. Note: This is only available for US citizens.
        </Text>

        <LocationForm onChange={setLocation} />

        <Text style={[styles.result, { color: colors.text }]}>
          {[location?.city, location?.state, location?.country].filter(Boolean).join(', ') || 'Nothing selected yet'}
        </Text>

        <Button 
          title="Continue" 
          onPress={() => router.push('/locationSelect')} 
          color={colors.primary}
        />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 28, fontWeight: '700', marginTop: 16 },
  subtitle: { fontSize: 15, opacity: 0.7, marginTop: 6, marginBottom: 28 },
  form: { gap: 18 },
  fieldLabel: { fontSize: 13, fontWeight: '600', opacity: 0.7, marginBottom: 6 },
  field: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 14, paddingVertical: 14,
    borderWidth: StyleSheet.hairlineWidth, borderRadius: 12,
  },
  sheetHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 16,
  },
  sheetTitle: { fontSize: 20, fontWeight: '700' },
  search: {
    marginHorizontal: 20, marginBottom: 8, paddingHorizontal: 14, paddingVertical: 12,
    borderWidth: StyleSheet.hairlineWidth, borderRadius: 12, fontSize: 16,
  },
  row: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 16, borderBottomWidth: StyleSheet.hairlineWidth,
  },
  result: { marginTop: 32, fontSize: 16, textAlign: 'center', opacity: 0.8 },
});