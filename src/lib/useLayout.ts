import { useSyncExternalStore } from 'react';
import { useWindowDimensions } from 'react-native';

// The static web export renders every page at width 0 (the phone layout). If the browser's
// first render used the real width instead, React would keep the prerendered styles anyway,
// because hydration doesn't patch mismatched attributes, so a laptop got stuck on the phone
// layout. useSyncExternalStore returns the server value (false) while hydrating, then
// re-renders with true; screens that mount later, and native apps, get true right away.
const noSubscribe = () => () => {};
const useHydrated = () =>
  useSyncExternalStore(
    noSubscribe,
    () => true,
    () => false,
  );

/** Breakpoints shared by every screen so phone, tablet and laptop layouts stay consistent. */
export function useLayout() {
  const { width: windowWidth } = useWindowDimensions();
  const width = useHydrated() ? windowWidth : 0;
  const isWide = width >= 768;
  const isDesktop = width >= 1024;
  return { width, isWide, isDesktop, gutter: isDesktop ? 32 : isWide ? 24 : 16 };
}
