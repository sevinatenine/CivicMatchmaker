import { useWindowDimensions } from 'react-native';

/** Breakpoints shared by every screen so phone, tablet and laptop layouts stay consistent. */
export function useLayout() {
  const { width } = useWindowDimensions();
  const isWide = width >= 768;
  const isDesktop = width >= 1024;
  return { width, isWide, isDesktop, gutter: isDesktop ? 32 : isWide ? 24 : 16 };
}
