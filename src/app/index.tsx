import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { useRouter } from 'expo-router';
import { Image, StyleSheet } from 'react-native';

export default function Home() {
  const router = useRouter(); 

  return (
    <Screen>
      <ScreenTitle>Welcome to CivicMatchmaker</ScreenTitle>
      <ScreenSubtitle>Answer a few questions about the issues you care about and get matched with the candidates who fit you best. Unbiased and non-partisan.</ScreenSubtitle>

      <Image
        source={require('@/assets/front-image.png')}
        style={styles.frontImage}
        resizeMode="contain"
      />

      <PrimaryButton tone="red" title="Get started" onPress={() => router.push('/locationSelect')} />
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