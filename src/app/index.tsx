import { PartyStripe } from '@/components/PartyStripe';
import { PrimaryButton } from '@/components/PrimaryButton';
import { Colors } from '@/constants/Colors';
import { useLayout } from '@/lib/useLayout';
import { typography } from '@/theme/typography';
import { Href, useRouter } from 'expo-router';
import { Image, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { SafeAreaView } from 'react-native-safe-area-context';

const STEPS = [
  {
    title: 'Tell us where you vote',
    body: 'Pick your state and city. Add a street address to narrow House races to your district.',
  },
  {
    title: 'Answer issue questions',
    body: 'Share where you stand on the economy, healthcare, climate and more, and mark what matters most.',
  },
  {
    title: 'See your matches',
    body: 'Candidates ranked by how closely their recorded positions line up with yours.',
  },
];

const FEATURES: { title: string; body: string; cta?: { label: string; href: Href } }[] = [
  {
    title: 'Your whole ballot',
    body: 'Federal, state and local races, plus a sample ballot laid out the way you’ll see it.',
  },
  {
    title: 'Every score explained',
    body: 'Tap “Why this score?” to see exactly which answers you agree and disagree on.',
  },
  {
    title: 'Plan your vote',
    body: 'Find drop boxes, early voting sites and your polling place on a map.',
    cta: { label: 'Find where to vote', href: '/dropoff' },
  },
];

const ACCENTS = [Colors.red, Colors.blue];

function Glow({ size }: { size: number }) {
  // Two soft, offset color washes behind the hero art
  return (
    <View style={[StyleSheet.absoluteFill, styles.glowWrap]}>
      <View
        style={[
          styles.glow,
          { width: size * 0.7, height: size * 0.7, left: 0, top: size * 0.1 },
          { backgroundColor: Colors.redSoft, boxShadow: `0 0 ${size / 4}px ${size / 8}px ${Colors.redSoft}` },
        ]}
      />
      <View
        style={[
          styles.glow,
          { width: size * 0.7, height: size * 0.7, right: 0, bottom: size * 0.05 },
          { backgroundColor: Colors.blueSoft, boxShadow: `0 0 ${size / 4}px ${size / 8}px ${Colors.blueSoft}` },
        ]}
      />
    </View>
  );
}

export default function Home() {
  const router = useRouter();
  const { isWide, isDesktop, gutter } = useLayout();
  const artSize = isDesktop ? 440 : isWide ? 340 : 260;
  const column = { paddingHorizontal: gutter };

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {/* Top bar */}
        <View style={[styles.column, styles.topBar, column]}>
          <View>
            <Text style={styles.wordmark}>CivicMatchmaker</Text>
            <PartyStripe style={styles.wordmarkStripe} />
          </View>
          <Pressable onPress={() => router.push('/about')} hitSlop={10}>
            {({ hovered }) => (
              <Text style={[styles.navLink, hovered && { color: Colors.text }]}>About</Text>
            )}
          </Pressable>
        </View>

        {/* Hero */}
        <View
          style={[
            styles.column,
            styles.hero,
            column,
            isDesktop && styles.heroRow,
            { paddingTop: isDesktop ? 72 : isWide ? 48 : 28 },
          ]}
        >
          <Animated.View
            entering={FadeInDown.duration(450)}
            style={[styles.heroText, isDesktop && { flex: 1 }, !isDesktop && styles.centered]}
          >
            <View style={[styles.eyebrow, { alignSelf: isDesktop ? 'flex-start' : 'center' }]}>
              <View style={[styles.dot, { backgroundColor: Colors.red }]} />
              <View style={[styles.dot, { backgroundColor: Colors.blue, marginLeft: -3 }]} />
              <Text style={styles.eyebrowText}>Nonpartisan · 2026 elections</Text>
            </View>

            <Text
              style={[
                styles.headline,
                isDesktop && styles.headlineLarge,
                !isDesktop && { textAlign: 'center' },
              ]}
            >
              Find the candidates who actually{' '}
              <Text style={{ color: Colors.red }}>agree</Text> with{' '}
              <Text style={{ color: Colors.blue }}>you</Text>.
            </Text>

            <Text style={[styles.lede, !isDesktop && { textAlign: 'center' }]}>
              Answer a few questions about the issues you care about. We compare your answers with
              every candidate on your ballot and show you who fits best — no party labels steering
              the way.
            </Text>

            <View style={[styles.ctas, !isWide && styles.ctasStacked]}>
              <PrimaryButton
                tone="red"
                title="Get matched"
                onPress={() => router.push('/locationSelect')}
                style={isWide ? styles.ctaWide : undefined}
              />
              <PrimaryButton
                variant="ghost"
                title="How to vote"
                onPress={() => router.push('/learn')}
                style={isWide ? styles.ctaWide : undefined}
              />
            </View>

            <Text style={[styles.trust, !isDesktop && { textAlign: 'center' }]}>
              About 5 minutes · No sign-up · Free
            </Text>
          </Animated.View>

          <Animated.View
            entering={FadeIn.duration(700).delay(150)}
            style={[styles.art, { width: artSize, height: artSize }]}
          >
            <Glow size={artSize} />
            <Image
              source={require('@/assets/front-image.png')}
              style={{ width: artSize, height: artSize }}
              resizeMode="contain"
              accessibilityIgnoresInvertColors
            />
          </Animated.View>
        </View>

        {/* How it works */}
        <View style={[styles.column, styles.section, column]}>
          <Text style={styles.sectionEyebrow}>How it works</Text>
          <Text style={styles.sectionTitle}>Three steps to an informed vote</Text>
          <View style={[styles.grid, isWide && styles.gridRow]}>
            {STEPS.map((s, i) => (
              <Animated.View
                key={s.title}
                entering={FadeInDown.duration(450).delay(200 + i * 100)}
                style={[styles.card, isWide && styles.gridCell]}
              >
                <View style={[styles.stepNumber, { backgroundColor: ACCENTS[i % 2] }]}>
                  <Text style={styles.stepNumberText}>{i + 1}</Text>
                </View>
                <Text style={styles.cardTitle}>{s.title}</Text>
                <Text style={styles.cardBody}>{s.body}</Text>
              </Animated.View>
            ))}
          </View>
        </View>

        {/* Features */}
        <View style={[styles.column, styles.section, column]}>
          <Text style={styles.sectionEyebrow}>What you get</Text>
          <Text style={styles.sectionTitle}>More than a match score</Text>
          <View style={[styles.grid, isWide && styles.gridRow]}>
            {FEATURES.map((f, i) => (
              <View
                key={f.title}
                style={[styles.card, styles.featureCard, isWide && styles.gridCell, { borderTopColor: ACCENTS[i % 2] }]}
              >
                <Text style={styles.cardTitle}>{f.title}</Text>
                <Text style={styles.cardBody}>{f.body}</Text>
                {f.cta && (
                  <Pressable onPress={() => router.push(f.cta!.href)} hitSlop={8}>
                    <Text style={[styles.cardLink, { color: ACCENTS[i % 2] }]}>{f.cta.label} →</Text>
                  </Pressable>
                )}
              </View>
            ))}
          </View>
        </View>

        {/* Closing call to action */}
        <View style={[styles.column, column]}>
          <View style={[styles.banner, isWide && styles.bannerRow]}>
            <View style={{ flex: isWide ? 1 : undefined, gap: 6 }}>
              <Text style={styles.bannerTitle}>Ready to see who fits you?</Text>
              <Text style={styles.cardBody}>It only takes a few minutes.</Text>
            </View>
            <PrimaryButton
              tone="red"
              title="Start now"
              onPress={() => router.push('/locationSelect')}
              style={isWide ? styles.ctaWide : undefined}
            />
          </View>
        </View>

        {/* Footer */}
        <View style={[styles.column, styles.footer, column]}>
          <PartyStripe style={styles.footerStripe} />
          <Text style={styles.footerText}>
            CivicMatchmaker is not affiliated with any party or campaign. Scores are based on
            candidates’ publicly recorded positions.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { paddingBottom: 32 },
  column: { width: '100%', maxWidth: 1120, alignSelf: 'center' },
  centered: { alignItems: 'center' },

  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 16,
  },
  wordmark: { fontSize: 18, fontWeight: '800', letterSpacing: -0.3, color: Colors.text },
  wordmarkStripe: { marginTop: 4, width: 40, borderRadius: 2, overflow: 'hidden' },
  navLink: { ...typography.label, fontSize: 15, color: Colors.textMuted },

  hero: { alignItems: 'center', gap: 32, paddingBottom: 24 },
  heroRow: { flexDirection: 'row', gap: 56 },
  heroText: { gap: 20, maxWidth: 620 },
  eyebrow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
  },
  dot: { width: 8, height: 8, borderRadius: 4 },
  eyebrowText: { ...typography.eyebrow, color: Colors.textMuted },
  headline: { ...typography.display, fontSize: 36, lineHeight: 42, color: Colors.text },
  headlineLarge: { fontSize: 56, lineHeight: 62, letterSpacing: -1.8 },
  lede: { ...typography.body, fontSize: 17, lineHeight: 26, color: Colors.textMuted },
  ctas: { flexDirection: 'row', gap: 12, marginTop: 4 },
  ctasStacked: { flexDirection: 'column', alignSelf: 'stretch' },
  ctaWide: { minWidth: 180 },
  trust: { ...typography.label, color: Colors.textMuted },

  art: { alignItems: 'center', justifyContent: 'center' },
  glowWrap: { overflow: 'visible', pointerEvents: 'none' },
  glow: { position: 'absolute', borderRadius: 9999 },

  section: { marginTop: 56, gap: 8 },
  sectionEyebrow: { ...typography.eyebrow, color: Colors.red },
  sectionTitle: { ...typography.title, fontSize: 26, lineHeight: 32, color: Colors.text, marginBottom: 12 },
  grid: { gap: 14 },
  gridRow: { flexDirection: 'row' },
  gridCell: { flex: 1 },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 20,
    gap: 8,
  },
  featureCard: { borderTopWidth: 3 },
  stepNumber: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  stepNumberText: { fontSize: 15, fontWeight: '800', color: Colors.onButton },
  cardTitle: { ...typography.heading, color: Colors.text },
  cardBody: { fontSize: 15, lineHeight: 22, color: Colors.textMuted },
  cardLink: { ...typography.label, fontSize: 14, marginTop: 4 },

  banner: {
    marginTop: 56,
    padding: 24,
    gap: 16,
    borderRadius: 22,
    backgroundColor: Colors.top,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
  },
  bannerRow: { flexDirection: 'row', alignItems: 'center', padding: 32 },
  bannerTitle: { ...typography.title, fontSize: 24, lineHeight: 30, color: Colors.text },

  footer: { marginTop: 48, gap: 14 },
  footerStripe: { borderRadius: 2, overflow: 'hidden' },
  footerText: { ...typography.label, fontWeight: '500', lineHeight: 19, color: Colors.textMuted },
});
