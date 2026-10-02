import { Screen, ScreenTitle } from '@/components/Screen';
import { useTheme } from 'expo-router/react-navigation';
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
  const { colors } = useTheme();

  return (
    <Pressable
      style={({ pressed }) => [
        styles.button,
        {
          backgroundColor: selected ? colors.primary : colors.card,
          borderColor: selected ? colors.primary : colors.border,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
      onPress={onPress}
    >
      <Text style={[styles.buttonTitle, { color: selected ? colors.background : colors.text }]}>
        {title}
      </Text>
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
  const { colors } = useTheme();

  return (
    <View style={styles.question}>
      <Text style={[styles.questionTitle, { color: colors.text }]}>{question}</Text>
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
    </View>
  );
}

export default function QuestionsPage() {
  const { colors } = useTheme();
  const [experience, setExperience] = useState<number | null>(null);

  return (
    <Screen>
      <ScreenTitle>Questions</ScreenTitle>
      <Text style={{ color: colors.text }}>
        We will ask you a series of questions to help match you with candidates.
      </Text>
      <Question
        question="What is your experience level?"
        value={experience}
        onChange={setExperience}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  questionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 10,
  },
  buttonTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  question: {
    marginVertical: 10,
    alignSelf: 'stretch',
  },
  options: {
    flexDirection: 'row',
    gap: 8,
  },
  button: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});