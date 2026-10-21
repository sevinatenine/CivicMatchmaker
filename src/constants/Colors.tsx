// Light black + pastel gray, with a pastel blue and a pastel red for a bipartisan feel
const blue = '#A9C7EE'; // pastel blue
const red = '#F2A7A7'; // pastel red

export const Colors = {
  background: '#1C1E22', // light black
  top: '#23262B', // header / bars
  card: '#292D33', // surfaces, inputs
  cardAlt: '#32373E', // pressed / raised surfaces
  border: '#3C424A',

  text: '#E8EAED', // pastel gray, main text
  textMuted: '#9AA1AB', // pastel gray, secondary text

  blue,
  blueSoft: 'rgba(169, 199, 238, 0.16)', // tinted blue wash
  red,
  redSoft: 'rgba(242, 167, 167, 0.16)', // tinted red wash

  button: blue, // main accent
  onButton: '#1C1E22', // text on either accent
  buttonSoft: 'rgba(169, 199, 238, 0.16)',
};

/** Pastel red for Republicans, pastel blue for Democrats, muted gray for everyone else. */
export function partyColor(party?: string | null): string {
  const p = (party ?? '').toLowerCase();
  if (p.includes('republican')) return Colors.red;
  if (p.includes('democrat')) return Colors.blue;
  return Colors.textMuted;
}
