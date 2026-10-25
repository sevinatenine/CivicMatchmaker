import { API_URL } from '@/constants/api';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useEffect, useState } from 'react';

/** Counts kept by the API (CivicAI/stats.py). They survive redeploys. */
export type UsageStats = {
  opens: number;
  decisions: number;
  unique_ips: number;
  unique_devices: number;
  persistent: boolean;
};

const DEVICE_KEY = 'deviceId';

const randomId = () =>
  Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');

/**
 * A random ID made the first time this device opens the app, so the server can count
 * different devices. Lives in localStorage on web and app storage on phones. If storage
 * isn't available (e.g. a private window that blocks it), this launch gets a fresh ID.
 */
async function getDeviceId(): Promise<string> {
  try {
    const saved = await AsyncStorage.getItem(DEVICE_KEY);
    if (saved) return saved;
    const id = randomId();
    await AsyncStorage.setItem(DEVICE_KEY, id);
    return id;
  } catch {
    return randomId();
  }
}

let visit: Promise<UsageStats | null> | null = null;

/** Counts this launch once (later calls share the same request) and resolves to the counts,
 *  or null if the server can't be reached. */
export function recordVisit(): Promise<UsageStats | null> {
  visit ??= getDeviceId()
    .then((device) =>
      fetch(`${API_URL}/visit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device }),
      }),
    )
    .then((res) => (res.ok ? (res.json() as Promise<UsageStats>) : null))
    .catch(() => null);
  return visit;
}

/** The usage counts, or null until they arrive (or if the server is down). */
export function useUsageStats(): UsageStats | null {
  const [stats, setStats] = useState<UsageStats | null>(null);
  useEffect(() => {
    let cancelled = false;
    recordVisit().then((s) => {
      if (!cancelled) setStats(s);
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return stats;
}
