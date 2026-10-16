// Where the Python server runs.
// - iOS simulator:        http://localhost:4000
// - Android emulator:     http://10.0.2.2:4000
// - Physical phone:       http://<your laptop's LAN IP>:4000  (same Wi-Fi)
// Set it without editing code:  EXPO_PUBLIC_API_URL=http://192.168.1.20:4000 npx expo start
   export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.0.104:4001';