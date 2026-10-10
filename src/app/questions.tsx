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
}: {
  def: ScaleQuestionDef;
  value: number | undefined;
  onChange: (value: number) => void;
}) {
  return (
    <View style={styles.question}>
      <Text style={styles.questionTitle}>{def.question}</Text>
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
      <Text style={styles.questionTitle}>{def.question}</Text>
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
}: {
  def: QuestionDef;
  value: number | string | undefined;
  onChange: (value: number | string) => void;
}) {
  switch (def.type) {
    case 'scale':
      return <ScaleQuestion def={def} value={value as number | undefined} onChange={onChange} />;
    case 'choice':
      return <ChoiceQuestion def={def} value={value as string | undefined} onChange={onChange} />;
  }
}

/* ---------- Page ---------- */

export default function QuestionsPage() {
  const router = useRouter();
  const { state, city } = useLocalSearchParams<{ state: string; city: string }>();
  const [answers, setAnswers] = useState<Answers>({});

  const setAnswer = (id: string, value: number | string) =>
    setAnswers((prev) => ({ ...prev, [id]: value }));

  const isFormValid = QUESTIONS.every((q) => answers[q.id] !== undefined);

  return (
    <Screen scroll>
        <ScreenTitle>Questions</ScreenTitle>
        <ScreenSubtitle>
          We will ask you a series of questions to help match you with candidates.
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
            />
          </Fragment>
        ))}
        <PrimaryButton
        title="Continue"
        disabled={!isFormValid}
        onPress={() =>
          router.navigate({
            pathname: '/selectType',
            params: { state, city, answers: JSON.stringify(answers) },
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
  questionTitle: {
    ...typography.heading,
    color: Colors.text,
    marginBottom: 16,
  },
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
  scroll: { alignSelf: 'stretch', flex: 1 },
  scrollContent: { paddingBottom: 40 },
});