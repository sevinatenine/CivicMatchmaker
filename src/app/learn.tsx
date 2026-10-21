// app/learn.tsx
import { PrimaryButton } from '@/components/PrimaryButton';
import { Screen, ScreenSubtitle, ScreenTitle } from '@/components/Screen';
import { Colors } from '@/constants/Colors';
import { typography } from '@/theme/typography';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

type Tab = 'prereg' | 'vote' | 'basics';

const TABS: { key: Tab; label: string }[] = [
  { key: 'prereg', label: 'Pre-register' },
  { key: 'vote', label: 'How to vote' },
  { key: 'basics', label: 'Politics 101' },
];

type Block = { title: string; body: string };

const PREREG: Block[] = [
  {
    title: 'What is pre-registering?',
    body: 'In many states, you can sign up to vote before you turn 18 (often at 16 or 17). Your registration is then activated automatically once you are old enough. Rules differ by state, so check yours.',
  },
  {
    title: 'Who can register?',
    body: 'You must be a U.S. citizen and meet your state’s age and residency rules. In most states you need to be 18 by Election Day to vote. Some states let 17-year-olds vote in a primary if they will be 18 by the general election.',
  },
  {
    title: '1. Check your state’s rules',
    body: 'Go to vote.gov and pick your state. It shows the minimum age to pre-register, deadlines, and whether you can sign up online, by mail, or in person.',
  },
  {
    title: '2. Gather what you need',
    body: 'Usually a driver’s license or state ID number, or the last 4 digits of your Social Security number, plus your home address and date of birth.',
  },
  {
    title: '3. Register',
    body: 'Fill out the form online, by mail, or in person at a DMV, library, or election office. Some states also offer pre-registration at school or when you get your driver’s license.',
  },
  {
    title: '4. Confirm it went through',
    body: 'Look yourself up on your state’s voter lookup tool a week or two later. Update your registration any time you move.',
  },
];

const VOTE: Block[] = [
  {
    title: 'Before Election Day',
    body: 'Confirm you are registered, find your polling place, and look up your sample ballot so you know every race and ballot measure ahead of time. Vote.gov and your state election office both have tools for this.',
  },
  {
    title: 'Pick how you will vote',
    body: 'Depending on your state: in person on Election Day, early voting at an early-vote site, or voting by mail (some states mail every voter a ballot). Check deadlines for requesting and returning mail ballots.',
  },
  {
    title: 'Voting in person',
    body: 'Go to your assigned polling place, check in with a poll worker, and show ID if your state requires it. You will get a paper ballot or use a voting machine. Mark your choices, then submit it.',
  },
  {
    title: 'Voting by mail',
    body: 'Fill out the ballot exactly as instructed, sign the envelope if required, and return it by mail or at an official drop box before the deadline. Many states let you track your ballot online.',
  },
  {
    title: 'Good to know',
    body: 'You do not have to vote on every race. If you are in line when polls close, stay in line: you still get to vote. If you run into a problem, you can ask for a provisional ballot.',
  },
  {
    title: 'Do your homework',
    body: 'Your matches in this app are a starting point, not a final answer. Read candidates’ own websites and nonpartisan sources like Vote Smart and Ballotpedia before deciding.',
  },
];

const BASICS: Block[] = [
  {
    title: 'Three branches of government',
    body: 'Legislative (Congress) makes laws. Executive (the President) carries them out. Judicial (the courts) interprets them. Each branch can check the others so no one holds all the power.',
  },
  {
    title: 'Congress',
    body: 'The House of Representatives has 435 members, with seats divided by state population and a two-year term. The Senate has 100 members, two per state, with six-year terms. A bill must pass both chambers and be signed by the President to become law.',
  },
  {
    title: 'Federal, state, and local',
    body: 'Federal government handles things like national defense and immigration. States handle things like most education rules, driver’s licenses, and elections. Cities and counties run schools, police, zoning, and local services. Local elections often affect your daily life the most.',
  },
  {
    title: 'Midterms vs. presidential elections',
    body: 'Presidential elections happen every four years. Midterm elections fall in between and decide all House seats, about a third of the Senate, many governors, and lots of state and local offices.',
  },
  {
    title: 'Primaries and general elections',
    body: 'Parties often hold primaries to choose their nominee. The general election is when everyone chooses among the nominees. Rules for who can vote in a primary differ by state.',
  },
  {
    title: 'Left, right, and in between',
    body: 'People often describe views as liberal (left) or conservative (right), but most people hold a mix of positions. Parties are coalitions, and many issues don’t fit neatly on one line, which is why this app compares you issue by issue.',
  },
  {
    title: 'Ballot measures',
    body: 'In many states, voters also decide questions directly, like new taxes or state laws. Read the full text and official summary, since wording can be confusing.',
  },
];

const CONTENT: Record<Tab, Block[]> = { prereg: PREREG, vote: VOTE, basics: BASICS };

const LINKS: Record<Tab, { label: string; url: string }[]> = {
  prereg: [
    { label: 'Register to vote (vote.gov)', url: 'https://vote.gov' },
    { label: 'Find your state election office', url: 'https://www.usa.gov/state-election-office' },
  ],
  vote: [
    { label: 'Voting & election info (vote.gov)', url: 'https://vote.gov' },
    { label: 'See your sample ballot (Ballotpedia)', url: 'https://ballotpedia.org/Sample_Ballot_Lookup' },
  ],
  basics: [
    { label: 'How government works (usa.gov)', url: 'https://www.usa.gov/branches-of-government' },
    { label: 'Candidate positions (Vote Smart)', url: 'https://justfacts.votesmart.org' },
  ],
};

export default function LearnPage() {
  const router = useRouter();
  const { state } = useLocalSearchParams<{ state?: string }>();
  const [tab, setTab] = useState<Tab>('prereg');

  return (
    <Screen scroll>
      <ScreenTitle>Ready to vote?</ScreenTitle>
      <ScreenSubtitle>
        {state ? `Rules vary by state, so double-check the details for ${state}.` : 'Rules vary by state, so double-check the details for yours.'}
      </ScreenSubtitle>

      <View style={styles.tabs}>
        {TABS.map((t) => {
          const selected = t.key === tab;
          return (
            <Pressable
              key={t.key}
              accessibilityRole="tab"
              accessibilityState={{ selected }}
              onPress={() => setTab(t.key)}
              style={[styles.tab, selected && styles.tabSelected]}
            >
              <Text style={[styles.tabText, selected && styles.tabTextSelected]}>{t.label}</Text>
            </Pressable>
          );
        })}
      </View>

      {CONTENT[tab].map((b) => (
        <View key={b.title} style={styles.card}>
          <Text style={styles.cardTitle}>{b.title}</Text>
          <Text style={styles.cardBody}>{b.body}</Text>
        </View>
      ))}

      <Text style={styles.sectionTitle}>Official resources</Text>
      {LINKS[tab].map((l) => (
        <Pressable
          key={l.url + l.label}
          onPress={() => Linking.openURL(l.url)}
          style={({ pressed }) => [styles.link, pressed && { backgroundColor: Colors.cardAlt }]}
        >
          <Text style={styles.linkText}>{l.label}</Text>
          <Text style={styles.linkArrow}>↗</Text>
        </Pressable>
      ))}

      <Text style={styles.footnote}>
        This is general information, not legal advice. Deadlines and ID rules change, so confirm
        with your state election office.
      </Text>

      <PrimaryButton tone="red" title="Back to start" onPress={() => router.dismissAll()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  tabs: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 20,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.card,
    alignItems: 'center',
  },
  tabSelected: { backgroundColor: Colors.blue, borderColor: Colors.blue },
  tabText: { ...typography.label, color: Colors.text },
  tabTextSelected: { color: Colors.onButton },
  card: {
    backgroundColor: Colors.card,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    padding: 18,
    marginBottom: 14,
    gap: 8,
  },
  cardTitle: { ...typography.heading, color: Colors.text },
  cardBody: { ...typography.body, color: Colors.textMuted },
  sectionTitle: {
    ...typography.label,
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginTop: 10,
    marginBottom: 10,
  },
  link: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    backgroundColor: Colors.card,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: Colors.border,
    borderRadius: 14,
    marginBottom: 10,
  },
  linkText: { flex: 1, fontSize: 16, color: Colors.button, fontWeight: '500' },
  linkArrow: { color: Colors.red, fontSize: 16 },
  footnote: { ...typography.label, color: Colors.textMuted, marginTop: 10, marginBottom: 24 },
});