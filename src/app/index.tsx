import { Screen, ScreenTitle } from '@/components/Screen';
import { useRouter } from 'expo-router';
import { useTheme } from 'expo-router/react-navigation';
import { Button, Image, StyleSheet } from 'react-native';

export default function Home() {
  const router = useRouter();
  const { colors } = useTheme();

  return (
    <Screen>
      <ScreenTitle>Welcome to CivicMatchmaker</ScreenTitle>

      <Image
        source={require('@/assets/front-image.png')}
        style={styles.frontImage}
        resizeMode="contain"
      />

      <Button
        title="Get started"
        onPress={() => router.push('/locationSelect')}
        color={colors.primary}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  frontImage: {
    flex: 1,
    width: '100%',
    marginVertical: 16,
  },
});