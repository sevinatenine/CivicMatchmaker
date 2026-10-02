import { useTheme } from 'expo-router/react-navigation';
import { StyleSheet, Text, View } from 'react-native';

export default function AboutPage() {
  const { colors } = useTheme();

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text }]}>About Us</Text>
      <Text style={{ color: colors.text }}>Welcome to the About Page!</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
  }
});
