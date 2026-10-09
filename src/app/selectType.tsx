// app/selectType.tsx
import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { useLocalSearchParams, useRouter } from 'expo-router';

export default function SelectTypePage() {
  const router = useRouter();
  const { state, city, answers } = useLocalSearchParams<{
    state: string;
    city: string;
    answers: string;
  }>();

  const parsed = answers ? JSON.parse(answers) : {};

  return (
    <Screen>
      <ScreenTitle>Select type</ScreenTitle>
      <ScreenSubtitle>
        {city}, {state} · {Object.keys(parsed).length} answers received
      </ScreenSubtitle>

      <PrimaryButton title="Back to start" onPress={() => router.dismissAll()} />
    </Screen>
  );
}