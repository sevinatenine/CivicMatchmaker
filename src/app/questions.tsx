import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

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

function Question({
  question,
  value,
  onChange,
}: {
  question: string;
  value: number | null;
  onChange: (value: number) => void;
}) {
  return (
    <View style={styles.question}>
      <Text style={styles.questionTitle}>{question}</Text>
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
        <Text style={styles.scaleLabel}>Lowest</Text>
        <Text style={styles.scaleLabel}>Highest</Text>
      </View>
    </View>
  );
}

export default function QuestionsPage() {
  const [experience, setExperience] = useState<number | null>(null);

  return (
    <Screen>
      <ScreenTitle>Questions</ScreenTitle>
      <ScreenSubtitle>
        We will ask you a series of questions to help match you with candidates.
      </ScreenSubtitle>
      <Question
        question="What is your experience level?"
        value={experience}
        onChange={setExperience}
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
});