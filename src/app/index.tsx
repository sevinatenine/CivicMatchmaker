import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { useRouter } from 'expo-router';
import { Image, StyleSheet } from 'react-native';

export default function Home() {
  const router = useRouter(); 

  return (
    <Screen>
      <ScreenTitle>Welcome to CivicMatchmaker</ScreenTitle>
      <ScreenSubtitle>Answer a lot of usless, boring questions and meet the candidates who fit/hate you, and will take your money. Just like Donald Trump. Don't vote for him.</ScreenSubtitle>

      <Image
        source={require('@/assets/front-image.png')}
        style={styles.frontImage}
        resizeMode="contain"
      />

      <PrimaryButton title="Get started" onPress={() => router.push('/locationSelect')} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  frontImage: {
    flex: 1,
    width: '100%',
    marginBottom: 24,
  },
});