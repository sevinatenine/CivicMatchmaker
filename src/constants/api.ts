import Constants from 'expo-constants';
import { Platform } from 'react-native';

// Where the API server is. Set by `npm start|web|android|ios` from APP_ENV in .env, and by render.yaml
// for the hosted web build:
// - local:  http://<this computer's LAN IP>:4000      (reachable from emulators and phones on the same Wi-Fi)
// - hosted: https://civicmatchmaker-api.onrender.com  (BACKEND_URL)
// Without it (e.g. plain `npx expo start`), use port 4000 on the machine serving the app. On a
// phone "localhost" is the phone itself, so take the dev server's host from Expo instead.
function devApiUrl() {
  const host =
    Platform.OS === 'web'
      ? typeof window !== 'undefined'
        ? window.location.hostname
        : 'localhost'
      : Constants.expoConfig?.hostUri?.split(':')[0];
  return `http://${host || 'localhost'}:4000`;
}

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? devApiUrl();
