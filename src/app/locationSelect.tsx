import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { City, State } from 'country-state-city';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  FlatList,
  Modal,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

type Option = { label: string; value: string };
type Location = {
  country: string | null;
  state: string | null;
  city: string | null;
  address: string | null;
  zip: string | null;
};

function SelectField({
  label,
  value,
  placeholder,
  options,
  onSelect,
  disabled,
}: {
  label: string;
  value: string;
  placeholder: string;
  options: Option[];
  onSelect: (v: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selected = options.find((o) => o.value === value);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? options.filter((o) => o.label.toLowerCase().includes(q)) : options;
  }, [options, query]);

  const close = () => {
    setOpen(false);
    setQuery('');
  };

  return (
    <View style={{ opacity: disabled ? 0.4 : 1 }}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Pressable
        disabled={disabled}
        onPress={() => setOpen(true)}
        style={({ pressed }) => [styles.field, pressed && { backgroundColor: Colors.cardAlt }]}
      >
        <Text
          style={[styles.fieldText, !selected && { color: Colors.textMuted }]}
          numberOfLines={1}
        >
          {selected?.label ?? placeholder}
        </Text>
        <Text style={styles.chevron}>⌄</Text>
      </Pressable>

      <Modal
        visible={open}
        animationType="slide"
        presentationStyle="pageSheet"
        onRequestClose={close}
      >
        <SafeAreaView style={styles.sheet}>
          <View style={styles.sheetHeader}>
            <Text style={styles.sheetTitle}>{label}</Text>
            <Pressable onPress={close} hitSlop={12}>
              <Text style={styles.sheetDone}>Done</Text>
            </Pressable>
          </View>

          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder={`Search ${label.toLowerCase()}...`}
            placeholderTextColor={Colors.textMuted}
            selectionColor={Colors.button}
            keyboardAppearance="dark"
            autoCorrect={false}
            style={styles.search}
          />

          <FlatList
            data={filtered}
            keyExtractor={(o, i) => `${o.value}-${i}`}
            keyboardShouldPersistTaps="handled"
            initialNumToRender={20}
            renderItem={({ item }) => {
              const isSelected = item.value === value;
              return (
                <Pressable
                  onPress={() => {
                    onSelect(item.value);
                    close();
                  }}
                  style={({ pressed }) => [
                    styles.row,
                    isSelected && { backgroundColor: Colors.buttonSoft },
                    pressed && { backgroundColor: Colors.cardAlt },
                  ]}
                >
                  <Text style={[styles.rowText, isSelected && { color: Colors.button }]}>
                    {item.label}
                  </Text>
                  {isSelected && <Text style={styles.check}>✓</Text>}
                </Pressable>
              );
            }}
            ListEmptyComponent={<Text style={styles.empty}>No results</Text>}
          />
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function TextField({
  label,
  value,
  placeholder,
  onChangeText,
  keyboardType,
  autoComplete,
}: {
  label: string;
  value: string;
  placeholder: string;
  onChangeText: (v: string) => void;
  keyboardType?: 'default' | 'number-pad';
  autoComplete?: 'street-address' | 'postal-code';
}) {
  return (
    <View>
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

const COUNTRY_CODE = 'US';

export function LocationForm({ onChange }: { onChange?: (l: Location) => void }) {
  const [stateCode, setStateCode] = useState('');
  const [city, setCity] = useState('');
  const [address, setAddress] = useState('');
  const [zip, setZip] = useState('');

  const states = useMemo(() => {
    // Collect every state code that has at least one city
    const stateCodesWithCities = new Set(
      (City.getCitiesOfCountry(COUNTRY_CODE) ?? []).map((c) => c.stateCode),
    );

    return State.getStatesOfCountry(COUNTRY_CODE)
      .filter((s) => stateCodesWithCities.has(s.isoCode))
      .map((s) => ({ label: s.name, value: s.isoCode }));
  }, []);

  const cities = useMemo(
    () =>
      stateCode
        ? City.getCitiesOfState(COUNTRY_CODE, stateCode).map((c) => ({
            label: c.name,
            value: c.name,
          }))
        : [],
    [stateCode],
  );

  const emit = (s: string, ci: string, a: string, z: string) =>
    onChange?.({
      country: 'United States',
      state: s ? State.getStateByCodeAndCountry(s, COUNTRY_CODE)?.name ?? null : null,
      city: ci || null,
      address: a.trim() || null,
      zip: z.trim() || null,
    });

  return (
    <View style={styles.form}>
      <SelectField
        label="State"
        placeholder="Select state"
        value={stateCode}
        options={states}
        onSelect={(v) => {
          setStateCode(v);
          setCity('');
          emit(v, '', address, zip);
        }}
      />
      <SelectField
        label="City"
        placeholder="Select city"
        value={city}
        options={cities}
        disabled={!stateCode || cities.length === 0}
        onSelect={(v) => {
          setCity(v);
          emit(stateCode, v, address, zip);
        }}
      />

      <Text style={styles.hint}>
        Optional: add your street address and ZIP so we can find your exact U.S. House district.
        Without it, we show House candidates from every district in your state.
      </Text>

      <TextField
        label="Street address (optional)"
        placeholder="123 Main St"
        value={address}
        autoComplete="street-address"
        onChangeText={(v) => {
          setAddress(v);
          emit(stateCode, city, v, zip);
        }}
      />
      <TextField
        label="ZIP code (optional)"
        placeholder="80020"
        value={zip}
        keyboardType="number-pad"
        autoComplete="postal-code"
        onChangeText={(v) => {
          setZip(v);
          emit(stateCode, city, address, v);
        }}
      />
    </View>
  );
}

export default function LocationSelectPage() {
  const router = useRouter();
  const [location, setLocation] = useState<Location>({
    country: null,
    state: null,
    city: null,
    address: null,
    zip: null,
  });

  const isFormValid = !!(location.state && location.city);

  return (
    <Screen scroll>
      <ScreenTitle>Select your location</ScreenTitle>
      <ScreenSubtitle>
        We ask this so we can find candidates near you. Note: This is only available for US
        citizens.
      </ScreenSubtitle>

      <LocationForm onChange={setLocation} />

      <View style={{ height: 24 }} />

      <PrimaryButton
        title="Continue"
        disabled={!isFormValid}
        onPress={() =>
          router.navigate({
            pathname: '/questions',
            params: {
              state: location.state!,
              city: location.city!,
              address: location.address ?? '',
              zip: location.zip ?? '',
            },
          })
        }
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  form: { gap: 20 },
  fieldLabel: {
    ...typography.label,
    color: Colors.textMuted,
    marginBottom: 8,
  },
  hint: { ...typography.label, color: Colors.textMuted, lineHeight: 18 },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 16,
    backgroundColor: Colors.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    borderRadius: 14,
  },
  fieldText: { flex: 1, fontSize: 16, color: Colors.text },
  chevron: { color: Colors.red, fontSize: 18 },
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

  sheet: { flex: 1, backgroundColor: Colors.background },
  sheetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 18,
  },
  sheetTitle: { ...typography.heading, fontSize: 20, color: Colors.text },
  sheetDone: { color: Colors.red, fontSize: 16, fontWeight: '600' },
  search: {
    marginHorizontal: 20,
    marginBottom: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    backgroundColor: Colors.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    borderRadius: 12,
    fontSize: 16,
    color: Colors.text,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  rowText: { flex: 1, fontSize: 16, color: Colors.text },
  check: { color: Colors.button, fontSize: 18 },
  empty: { color: Colors.textMuted, textAlign: 'center', marginTop: 32 },
});