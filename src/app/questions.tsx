import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import {
  ChoiceQuestionDef,
  QUESTIONS,
  QuestionDef,
  ScaleQuestionDef,
} from '@/constants/questions';
import { typography } from '@/theme/typography';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Fragment, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

type Answers = Record<string, number | string>;

/* ---------- How much does this question matter? ---------- */

const IMPORTANCE = [
  { label: 'Low', value: 0.5 },
  { label: 'Normal', value: 1 },
  { label: 'High', value: 2 },
  { label: 'Top priority', value: 3 },
];

function ImportanceRow({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  return (
    <View style={styles.importance}>
      <Text style={styles.importanceTitle}>How much does this matter to you?</Text>
      <View style={styles.importanceOptions}>
        {IMPORTANCE.map((o) => {
          const selected = value === o.value;
          return (
            <Pressable
              key={o.label}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              onPress={() => onChange(o.value)}
              style={({ pressed }) => [
                styles.importanceChip,
                selected && styles.importanceChipSelected,
                pressed && !selected && styles.buttonPressed,
              ]}
            >
              <Text style={[styles.importanceText, selected && styles.importanceTextSelected]}>
                {o.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

/* ---------- Question title + (i) explanation ---------- */

function QuestionHeader({ title, info }: { title: string; info?: string }) {
  const [open, setOpen] = useState(false);

  return (
    <View style={styles.header}>
      <View style={styles.headerRow}>
        <Text style={styles.questionTitle}>{title}</Text>
        {!!info && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={open ? 'Hide explanation' : 'What does this mean?'}
            accessibilityState={{ expanded: open }}
            hitSlop={10}
            onPress={() => setOpen((o) => !o)}
            style={({ pressed }) => [
              styles.infoButton,
              open && styles.infoButtonOpen,
              pressed && { opacity: 0.7 },
            ]}
          >
            <Text style={[styles.infoIcon, open && styles.infoIconOpen]}>i</Text>
          </Pressable>
        )}
      </View>
      {open && !!info && (
        <View style={styles.infoBox}>
          <Text style={styles.infoText}>{info}</Text>
        </View>
      )}
    </View>
  );
}

/* ---------- Scale question ---------- */

function QuestionButton({
  title,
  selected,
  onPress,
}: {
  title: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={({ pressed }) => [
        styles.button,
        selected && styles.buttonSelected,
        pressed && !selected && styles.buttonPressed,
      ]}
      onPress={onPress}
    >
      <Text style={[styles.buttonTitle, selected && styles.buttonTitleSelected]}>{title}</Text>
    </Pressable>
  );
}

function ScaleQuestion({
  def,
  value,
  onChange,
  importance,
  onImportance,
}: {
  def: ScaleQuestionDef;
  value: number | undefined;
  onChange: (value: number) => void;
  importance: number;
  onImportance: (value: number) => void;
}) {
  return (
    <View style={styles.question}>
      <QuestionHeader title={def.question} info={def.info} />
      <View style={styles.options}>
        {[1, 2, 3, 4, 5].map((n) => (
          <QuestionButton
            key={n}
            title={String(n)}
            selected={value === n}
            onPress={() => onChange(n)}
          />
        ))}
      </View>
      <View style={styles.scaleLabels}>
        <Text style={[styles.scaleLabel, styles.scaleLabelSide]}>{def.lowLabel ?? 'Lowest'}</Text>
        {def.midLabel && (
          <Text style={[styles.scaleLabel, styles.scaleLabelMid]}>{def.midLabel}</Text>
        )}
        <Text style={[styles.scaleLabel, styles.scaleLabelSide, { textAlign: 'right' }]}>
          {def.highLabel ?? 'Highest'}
        </Text>
      </View>
      <ImportanceRow value={importance} onChange={onImportance} />
    </View>
  );
}

/* ---------- Choice question ---------- */

function ChoiceOption({
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
      accessibilityRole="radio"
      accessibilityState={{ selected, checked: selected }}
      style={({ pressed }) => [
        styles.choice,
        selected && styles.choiceSelected,
        pressed && !selected && styles.buttonPressed,
      ]}
      onPress={onPress}
    >
      <View style={[styles.radio, selected && styles.radioSelected]}>
        {selected && <View style={styles.radioDot} />}
      </View>
      <Text style={[styles.choiceLabel, selected && styles.choiceLabelSelected]}>{label}</Text>
    </Pressable>
  );
}

function ChoiceQuestion({
  def,
  value,
  onChange,
}: {
  def: ChoiceQuestionDef;
  value: string | undefined;
  onChange: (value: string) => void;
}) {
  return (
    <View style={styles.question} accessibilityRole="radiogroup">
      <QuestionHeader title={def.question} info={def.info} />
      <View style={styles.choices}>
        {def.choices.map((choice) => (
          <ChoiceOption
            key={choice}
            label={choice}
            selected={value === choice}
            onPress={() => onChange(choice)}
          />
        ))}
      </View>
    </View>
  );
}

/* ---------- Renders the right component for each question ---------- */

function QuestionRenderer({
  def,
  value,
  onChange,
  importance,
  onImportance,
}: {
  def: QuestionDef;
  value: number | string | undefined;
  onChange: (value: number | string) => void;
  importance: number;
  onImportance: (value: number) => void;
}) {
  switch (def.type) {
    case 'scale':
      return (
        <ScaleQuestion
          def={def}
          value={value as number | undefined}
          onChange={onChange}
          importance={importance}
          onImportance={onImportance}
        />
      );
    case 'choice':
      return <ChoiceQuestion def={def} value={value as string | undefined} onChange={onChange} />;
  }
}

/* ---------- Page ---------- */

export default function QuestionsPage() {
  const router = useRouter();
  const { state, city, address, zip } = useLocalSearchParams<{
    state: string;
    city: string;
    address?: string;
    zip?: string;
  }>();
  const [answers, setAnswers] = useState<Answers>({});
  const [weights, setWeights] = useState<Record<string, number>>({}); // missing = Normal (1)

  const setAnswer = (id: string, value: number | string) =>
    setAnswers((prev) => ({ ...prev, [id]: value }));

  const setWeight = (id: string, value: number) =>
    setWeights((prev) => ({ ...prev, [id]: value }));

  const isFormValid = QUESTIONS.every((q) => answers[q.id] !== undefined);

  return (
    <Screen scroll>
      <ScreenTitle>Questions</ScreenTitle>
      <ScreenSubtitle>
        Tap the (i) on any question for a plain-language explanation. You can also mark how much
        each question matters to you, and the important ones will count for more.
      </ScreenSubtitle>
      {QUESTIONS.map((def, i) => (
        <Fragment key={def.id}>
          {def.section !== QUESTIONS[i - 1]?.section && (
            <Text style={styles.sectionTitle}>{def.section}</Text>
          )}
          <QuestionRenderer
            def={def}
            value={answers[def.id]}
            onChange={(value) => setAnswer(def.id, value)}
            importance={weights[def.id] ?? 1}
            onImportance={(value) => setWeight(def.id, value)}
          />
        </Fragment>
      ))}
      <PrimaryButton
        title="Continue"
        disabled={!isFormValid}
        onPress={() =>
          router.navigate({
            pathname: '/results',
            params: {
              state,
              city,
              address: address ?? '',
              zip: zip ?? '',
              answers: JSON.stringify(answers),
              weights: JSON.stringify(weights),
            },
          })
        }
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  question: {
    alignSelf: 'stretch',
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 18,
    marginBottom: 16,
  },

  // Title + info button
  header: { marginBottom: 16 },
  headerRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
  questionTitle: {
    ...typography.heading,
    color: Colors.text,
    flex: 1,
  },
  infoButton: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: Colors.button,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  infoButtonOpen: { backgroundColor: Colors.button },
  infoIcon: { color: Colors.button, fontSize: 15, fontWeight: '700' },
  infoIconOpen: { color: Colors.onButton },
  infoBox: {
    marginTop: 12,
    padding: 14,
    borderRadius: 12,
    backgroundColor: Colors.background,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  infoText: { fontSize: 14, lineHeight: 21, color: Colors.textMuted },

  // Importance
  importance: {
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: Colors.border,
    gap: 10,
  },
  importanceTitle: { ...typography.label, color: Colors.textMuted },
  importanceOptions: { flexDirection: 'row', gap: 6 },
  importanceChip: {
    flex: 1,
    paddingVertical: 9,
    paddingHorizontal: 4,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  importanceChipSelected: { backgroundColor: Colors.buttonSoft, borderColor: Colors.button },
  importanceText: { fontSize: 12, fontWeight: '600', color: Colors.textMuted, textAlign: 'center' },
  importanceTextSelected: { color: Colors.button },

  options: { flexDirection: 'row', gap: 8 },
  button: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonPressed: { backgroundColor: Colors.cardAlt },
  buttonSelected: {
    backgroundColor: Colors.button,
    borderColor: Colors.button,
  },
  buttonTitle: { fontSize: 17, fontWeight: '600', color: Colors.text },
  buttonTitleSelected: { color: Colors.onButton },
  scaleLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  scaleLabel: { ...typography.label, color: Colors.textMuted },

  // Choice question
  choices: { gap: 8 },
  choice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 14,
    paddingHorizontal: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.background,
  },
  choiceSelected: {
    backgroundColor: Colors.button,
    borderColor: Colors.button,
  },
  choiceLabel: { flex: 1, fontSize: 16, fontWeight: '500', color: Colors.text },
  choiceLabelSelected: { color: Colors.onButton },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: Colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  radioSelected: { borderColor: Colors.onButton },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: Colors.onButton,
  },
  sectionTitle: {
    ...typography.label,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginTop: 8,
    marginBottom: 10,
  },
  scaleLabelSide: { flex: 1 },
  scaleLabelMid: { flex: 1, textAlign: 'center' },
});