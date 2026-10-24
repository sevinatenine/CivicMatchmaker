import { API_URL } from '@/constants/api';

export type VotingPlace = {
  name: string;
  address: string;
  lat: number | null;
  lng: number | null;
  hours: string | null;
  notes: string | null;
  startDate: string | null; // "2026-10-19"
  endDate: string | null;
  distanceMiles: number | null; // null when we couldn't place you or the site on a map
};

export type VotingPlaces = {
  election: string | null;
  electionDay: string | null;
  origin: { lat: number; lng: number } | null; // your address
  dropOff: VotingPlace[]; // nearest first, at most 10 (the server's MAX_PER_KIND)
  earlyVote: VotingPlace[];
  polling: VotingPlace[];
  totals: { dropOff: number; earlyVote: number; polling: number }; // before the limit
  mailOnly: boolean;
  officialUrl: string | null; // county/state "where to vote" page
  officialName: string | null;
  note: string | null; // why the lists are empty, if they are
};

export type VotingPlacesQuery = { state: string; city: string; address: string; zip: string };

/** GETs /voting-places: ballot drop-off, early voting, and Election Day sites for an address. */
export async function fetchVotingPlaces(
  query: VotingPlacesQuery,
  signal?: AbortSignal,
): Promise<VotingPlaces> {
  const params = new URLSearchParams(query).toString();
  const res = await fetch(`${API_URL}/voting-places?${params}`, { signal });
  if (!res.ok) throw new Error(`Server error (${res.status})`);
  return res.json();
}
