export type ScaleQuestionDef = {
  id: string;
  type: 'scale';
  section: string;
  question: string;
  // 1 = Strongly support ... 5 = Strongly oppose
  lowLabel?: string;
  midLabel?: string;
  highLabel?: string;
};

export type ChoiceQuestionDef = {
  id: string;
  type: 'choice';
  section: string;
  question: string;
  choices: string[];
};

export type QuestionDef = ScaleQuestionDef | ChoiceQuestionDef;

const scale = (id: string, section: string, question: string): ScaleQuestionDef => ({
  id,
  type: 'scale',
  section,
  question,
  lowLabel: 'Strongly oppose',
  midLabel: 'Neutral/unsure',
  highLabel: 'Strongly support',
});

const choice = (
  id: string,
  section: string,
  question: string,
  choices: string[],
): ChoiceQuestionDef => ({ id, type: 'choice', section, question, choices });

export const QUESTIONS: QuestionDef[] = [
  // Education
  scale(
    'k12-funding',
    'Education',
    'Your local government should increase funding for public K–12 schools, even if doing so requires higher state taxes.',
  ),
  scale(
    'school-spending-freedom',
    'Education',
    'Public schools should have more freedom to choose how they spend government funding, even if that means less centralized oversight.',
  ),
  choice('education-priority', 'Education', 'Which should the government prioritize more?', [
    'Increasing teacher pay',
    'Reducing class sizes',
    'Expanding academic programs',
    'Increasing school safety/resources',
    'Keeping taxes lower',
    'Balance all of these',
  ]),

  // Housing
  scale(
    'zoning',
    'Housing',
    'Local governments should make it easier to build more housing, even if this means changing some local zoning restrictions.',
  ),
  choice(
    'housing-priority',
    'Housing',
    'What should the government prioritize most when addressing housing affordability?',
    [
      'Building more housing',
      'Providing financial assistance to renters/buyers',
      'Limiting rent increases',
      'Reducing regulations and development costs',
      'A combination of these',
    ],
  ),

  // Taxes & Government Spending
  scale(
    'higher-income-taxes',
    'Taxes & Government Spending',
    'The U.S. federal government should increase taxes on higher-income households to fund public programs.',
  ),
  choice(
    'surplus-priority',
    'Taxes & Government Spending',
    'If the government has a budget surplus, what should it prioritize?',
    [
      'Tax reductions',
      'Education and infrastructure',
      'Healthcare/social programs',
      'Saving the money',
      'A combination',
    ],
  ),
  choice('government-size', 'Taxes & Government Spending', 'Which statement is closest to your view?', [
    'The government should generally provide more services, even if taxes increase.',
    'The government should provide a balance of services and taxation.',
    'The government should generally limit spending and keep taxes lower.',
    'Unsure',
  ]),

  // Environment & Energy
  scale(
    'renewable-transition',
    'Environment & Energy',
    'The U.S. federal government should accelerate its transition toward renewable energy, even if it increases short-term costs.',
  ),
  scale(
    'energy-costs-fossil',
    'Environment & Energy',
    'The U.S. federal government should prioritize reducing energy costs even if that means expanding the use of fossil fuels.',
  ),
  choice(
    'energy-priority',
    'Environment & Energy',
    "Which should be the government's highest priority for energy policy?",
    [
      'Reducing climate change',
      'Keeping energy affordable',
      'Energy independence/reliability',
      'Creating clean-energy jobs',
      'Balancing all four',
    ],
  ),

  // Healthcare
  scale(
    'healthcare-affordability',
    'Healthcare',
    'The government should expand programs that help people afford healthcare, even if government spending increases.',
  ),
  choice(
    'healthcare-costs-approach',
    'Healthcare',
    'Which approach should the government emphasize most to reduce healthcare costs?',
    [
      'Greater government involvement',
      'Greater competition between healthcare providers',
      'Negotiating/controlling prices',
      'Increasing subsidies for consumers',
      'A combination',
      'Unsure',
    ],
  ),

  // Transportation & Infrastructure
  scale(
    'public-transit',
    'Transportation & Infrastructure',
    'The federal government should spend more public money on public transportation, even if this means less funding for roads.',
  ),
  scale(
    'maintain-infrastructure',
    'Transportation & Infrastructure',
    'The U.S. federal government should prioritize maintaining existing infrastructure before building new major projects.',
  ),

  // Technology & AI
  scale(
    'ai-regulation',
    'Technology & AI',
    'The government should place stronger regulations on artificial intelligence companies to protect privacy, workers, and consumers.',
  ),
  choice('ai-priority', 'Technology & AI', 'Which should the government prioritize when regulating AI?', [
    'Innovation and economic growth',
    'Privacy and consumer protection',
    'Preventing job displacement',
    'Preventing misinformation',
    'National security',
    'Balance these priorities',
  ]),

  // Public Safety & Criminal Justice
  scale(
    'incarceration-alternatives',
    'Public Safety & Criminal Justice',
    'The government should invest more in alternatives to incarceration for people convicted of nonviolent offenses.',
  ),
  choice(
    'criminal-justice-priority',
    'Public Safety & Criminal Justice',
    'Which should be prioritized most when developing criminal-justice policy?',
    [
      'Reducing crime',
      'Rehabilitation',
      'Preventing wrongful convictions',
      'Reducing incarceration',
      'A balance of these',
    ],
  ),

  // Democracy & Voting
  scale(
    'easier-voting',
    'Democracy & Voting',
    'Voting should be made easier through measures such as expanded early voting and easier voter registration.',
  ),
  choice(
    'election-priority',
    'Democracy & Voting',
    'Which should be prioritized more when designing election rules?',
    [
      'Making voting as accessible as possible',
      'Strengthening election security',
      'Making both priorities equal',
      'Unsure',
    ],
  ),

  // Immigration
  scale(
    'legal-pathways',
    'Immigration',
    'The United States should expand legal pathways for immigrants to enter the country and work legally.',
  ),
  choice(
    'immigration-priority',
    'Immigration',
    "Which should be the government's highest priority for immigration policy?",
    [
      'Stronger border enforcement',
      'Expanding legal immigration',
      'Faster processing of immigration applications',
      'Providing pathways to legal status for some undocumented immigrants',
      'A combination',
      'Unsure',
    ],
  ),

  // Young People & College
  scale(
    'college-aid',
    'Young People & College',
    'The government should provide more financial assistance to make college and vocational education more affordable.',
  ),
  choice(
    'young-people-priority',
    'Young People & College',
    'Which issue should the government prioritize most for young people?',
    [
      'College affordability',
      'Job opportunities/wages',
      'Housing affordability',
      'Climate/environment',
      'Healthcare',
      'Education',
      'Mental-health services',
      'Other',
    ],
  ),
];