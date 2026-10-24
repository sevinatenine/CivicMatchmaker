import { TextStyle } from 'react-native';

export const typography = {
  display: {
    fontSize: 44,
    fontWeight: '800',
    letterSpacing: -1.4,
    lineHeight: 50,
  } as TextStyle,
  title: {
    fontSize: 30,
    fontWeight: '700',
    letterSpacing: -0.6,
    lineHeight: 36,
  } as TextStyle,
  heading: {
    fontSize: 19,
    fontWeight: '600',
    letterSpacing: -0.2,
    lineHeight: 25,
  } as TextStyle,
  body: {
    fontSize: 16,
    lineHeight: 23,
  } as TextStyle,
  label: {
    fontSize: 13,
    fontWeight: '600',
    letterSpacing: 0.2,
  } as TextStyle,
  eyebrow: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
  } as TextStyle,
};
