import { useRouter } from 'expo-router';
import { useTheme } from 'expo-router/react-navigation';
import { Button, Image, StyleSheet, Text, View } from 'react-native';

export default function Home() {
  const router = useRouter(); 
  const { colors } = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.h1, { color: colors.text }]}>Welcome to CivicMatchmaker</Text>
      
      <Image 
        source={require("@/assets/front-image.png")} 
        style={styles.frontImage}
        resizeMode="contain"
      />
      
      <Button 
        title="Get started" 
        onPress={() => router.push('/locationSelect')} 
        color={colors.primary}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1, 
    justifyContent: 'center', 
    alignItems: 'center', 
    flexDirection: 'column', 
    gap: 16,
    padding: 16
  },
  h1: { 
    fontSize: 32, 
    fontWeight: 'bold', 
    marginVertical: 10, 
    textAlign: 'center'
  },
  frontImage: { 
    flex: 1, 
    width: "100%" 
  }
});
