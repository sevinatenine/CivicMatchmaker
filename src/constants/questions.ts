export type ScaleQuestionDef = {
  id: string;
  type: 'scale';
  section: string;
  question: string;
  info?: string; // plain-language explanation shown behind the (i) button
  // 1 = Strongly oppose ... 5 = Strongly support
  lowLabel?: string;
  midLabel?: string;
  highLabel?: string;
};

export type ChoiceQuestionDef = {
  id: string;
  type: 'choice';
  section: string;
  question: string;
  info?: string;
  choices: string[];
};

export type QuestionDef = ScaleQuestionDef | ChoiceQuestionDef;

const scale = (id: string, section: string, question: string, info?: string): ScaleQuestionDef => ({
  id,
  type: 'scale',
  section,
  question,
  info,
  lowLabel: 'Strongly oppose',
  midLabel: 'Neutral/unsure',
  highLabel: 'Strongly support',
});

// Every statement below mirrors one question from Vote Smart's Political Courage Test,
// worded so that a candidate answering "Yes" to that question AGREES with the statement.
// The server (ai.py) pairs them by id, so keep the ids in sync with DIRECT in ai.py.
// You can freely reword `question` and `info`; just don't change the ids.
export const QUESTIONS: QuestionDef[] = [
  // Abortion
  scale(
    'roe-wade',
    'Abortion',
    'The Supreme Court was right to overturn Roe v. Wade.',
    'In 2022 the Supreme Court overturned Roe v. Wade (1973), which had protected a nationwide right to abortion. Since then, each state sets its own abortion laws. Supporting means you agree with that decision; opposing means you think abortion rights should be protected nationally.',
  ),

  // Taxes & Government Spending
  scale(
    'safety-net',
    'Taxes & Government Spending',
    'The government should spend more on programs like Social Security and Medicare.',
    'Social Security pays retirement and disability income, and Medicare covers health care for older Americans. This asks whether Congress should put more money into these and similar programs. Supporters say they protect people who need help; opponents worry about the cost and the national debt.',
  ),
  scale(
    'income-tax-cut',
    'Taxes & Government Spending',
    'Lowering income taxes would help balance the budget.',
    'Income tax is the tax taken from paychecks. A balanced budget means the government spends no more than it collects. Supporters say lower taxes grow the economy, which brings in more money; opponents say tax cuts reduce revenue unless spending is cut too.',
  ),
  scale(
    'wealth-tax',
    'Taxes & Government Spending',
    'The government should tax the wealth of the richest people to pay for public programs.',
    'A wealth tax is a yearly tax on the total value of what very rich people own, such as stocks, property and businesses, not just their income. Supporters say it would fund public programs and reduce inequality; opponents say it is hard to enforce and could drive money out of the country.',
  ),

  // Economy
  scale(
    'growth-spending',
    'Economy',
    'The government should spend money or offer tax breaks to help the economy grow.',
    'This covers things like grants and tax incentives that the government gives to businesses or industries to create jobs. Supporters say it boosts the economy; opponents say it picks winners and adds to the deficit.',
  ),
  scale(
    'inflation-action',
    'Economy',
    'The government should do more to fight inflation than just what the Federal Reserve does.',
    'Inflation is when prices rise over time. The Federal Reserve already fights it, mainly by changing interest rates. This asks whether Congress and the president should also act, for example through spending or other policies. Supporters say more action is needed; opponents say extra government action may backfire.',
  ),

  // Housing
  scale(
    'affordable-housing',
    'Housing',
    'The federal government should spend more on affordable housing.',
    'Federal affordable housing programs include rental vouchers and money to build lower-cost homes. Supporters say they help people afford a place to live; opponents say they are costly and that fewer building rules would do more.',
  ),

  // Education
  scale(
    'student-loans',
    'Education',
    'Federal student loan debt should be forgiven.',
    'Forgiveness would cancel some or all of the money people owe on federal student loans. Supporters say it relieves a heavy burden; opponents say it is unfair to people who paid their loans off or never went to college, and that taxpayers would cover the cost.',
  ),

  // Democracy & Voting
  scale(
    'voter-id',
    'Democracy & Voting',
    'People should have to show a government ID to vote in person.',
    'Some states require voters to show a photo ID or a similar document at the polls. Supporters say it prevents fraud and builds trust in elections; opponents say fraud is rare and that IDs can be hard for some people to get.',
  ),
  scale(
    'campaign-finance',
    'Democracy & Voting',
    'The government should regulate indirect campaign donations from corporations, unions and individuals.',
    '"Indirect" donations are money spent to support a candidate by outside groups, such as super PACs, rather than given to the campaign directly. Supporters say regulating it reduces the influence of big donors; opponents say it limits free speech.',
  ),

  // Public Safety & Criminal Justice
  scale(
    'officer-liability',
    'Public Safety & Criminal Justice',
    'Police and other officials should be protected from being personally sued over misconduct claims.',
    'Rules such as "qualified immunity" can shield officials from having to pay damages out of their own pocket in civil lawsuits. Supporters say it lets officers do their jobs without fear of lawsuits; opponents say it makes it hard to hold officials accountable.',
  ),
  scale(
    'gun-control',
    'Public Safety & Criminal Justice',
    'The government should pass gun-control laws, like red flag laws.',
    '"Red flag" laws let a court temporarily take guns from someone judged to be a danger to themselves or others. Another example is closing the "boyfriend loophole," which would bar people convicted of abusing a dating partner from owning guns. Supporters say these laws reduce gun deaths; opponents say they infringe on Second Amendment rights.',
  ),

  // Defense & National Security
  scale(
    'defense-spending',
    'Defense & National Security',
    'The U.S. should spend more on defense.',
    'Defense spending pays for the military, including troops, equipment and weapons. Supporters say a strong military keeps the country safe; opponents say the budget is already large and the money is better used elsewhere.',
  ),
  scale(
    'economic-intervention',
    'Defense & National Security',
    'The U.S. should use sanctions and other economic pressure to resolve conflicts between countries.',
    'This means using tools like sanctions, trade limits or frozen assets instead of military force. Supporters say it pressures governments without going to war; opponents say sanctions often do not work and can hurt ordinary people.',
  ),
  scale(
    'ukraine-aid',
    'Defense & National Security',
    'The U.S. should send more offensive weapons and military aid to Ukraine.',
    'Offensive aid means weapons that can strike targets, not only defensive equipment. Supporters say it helps Ukraine resist Russia\u2019s invasion; opponents say it costs too much or risks a wider war.',
  ),

  // Environment & Energy
  scale(
    'renewables-funding',
    'Environment & Energy',
    'The government should pay to develop renewable energy like solar and wind.',
    'Renewable energy comes from sources that do not run out, such as solar, wind and geothermal (heat from underground). Supporters say funding it cuts pollution and creates jobs; opponents say private companies should pay for it, or that it costs too much.',
  ),
  scale(
    'drilling-permits',
    'Environment & Energy',
    'The federal government should let companies drill for oil and gas on public lands.',
    'The federal government owns large areas of public land and can allow drilling there by granting permits. Supporters say it boosts energy supply and jobs; opponents say it harms the environment and the climate.',
  ),

  // Healthcare
  scale(
    'single-payer',
    'Healthcare',
    'The U.S. should have a government-run health care system, like Medicare-for-All.',
    'In a "single-payer" system such as Medicare-for-All, the government rather than private insurance companies pays for health care for everyone. Supporters say it covers everyone and lowers costs; opponents say it means higher taxes and less choice.',
  ),
  scale(
    'paid-leave',
    'Healthcare',
    'The government should expand paid family and medical leave.',
    'Paid leave means workers keep getting paid while they take time off for a new baby, a sick family member, or their own illness. Supporters say it helps families; opponents say it burdens employers or taxpayers.',
  ),
  scale(
    'drug-prices',
    'Healthcare',
    'The government should be able to regulate prescription drug prices.',
    'This asks whether the government should be able to limit or negotiate what drug companies charge. Supporters say it lowers costs for patients; opponents say it could reduce the money available to develop new medicines.',
  ),

  // Immigration
  scale(
    'border-security',
    'Immigration',
    'The U.S. should increase security along the southern border.',
    'Border security can include more agents, barriers, technology and inspections along the U.S.\u2013Mexico border. Supporters say it controls illegal crossings and drug smuggling; opponents say the money would be better spent on other things, such as improving legal immigration.',
  ),
  scale(
    'return-for-citizenship',
    'Immigration',
    'Immigrants should have to go back to their home country before they can become citizens.',
    'This would require even people already living in the U.S. to leave and apply from abroad, whatever their current immigration status. Supporters say it makes everyone follow the same process; opponents say it would separate families and disrupt communities.',
  ),

  // Technology & AI
  scale(
    'social-media',
    'Technology & AI',
    'The government should put more regulations on social media companies.',
    'Rules could cover things like children\u2019s safety, data privacy, or what content platforms must remove. Supporters say these companies have too much power and influence; opponents say regulation limits free speech and innovation.',
  ),
];