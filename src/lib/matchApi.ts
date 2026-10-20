import { API_URL } from '@/constants/api';
import { fetch } from 'expo/fetch'; // streaming fetch (plain RN fetch can't read SSE)

export type Reason = {
  statement: string;
  yourAnswer: number; // 1-5
  candidateQuestion: string;
  candidateAnswer: string;
  agreement: number; // 0-100
  importance?: number; // how much you said this question matters (1 = normal)
};

export type Level = 'Federal' | 'State' | 'Local' | 'Other';

export type CandidateMatch = {
  id: string;
  name: string;
  office: string;
  party: string | null;
  level: Level;
  position: string; // "U.S. Senate", "U.S. House", "Governor", "State Senate", ...
  district: string | null;
  state: string | null;
  score: number | null; // null = not enough overlapping positions
  coverage: number;
  sections: Record<string, number | null>;
  reasons: Reason[];
  ballotOnly?: boolean; // on your ballot, but no recorded positions to score
  url?: string | null; // campaign website, when known
};

export type MatchLocation = {
  state: string | null;
  city: string;
  district: string | null;
  county: string | null;
  districtKnown: boolean;
  addressGiven: boolean;
  geocodeError: string | null;
  matchedAddress: string | null;
};

export type BallotInfo = {
  loaded: boolean;
  note: string | null;
  elections: string[];
  extra: number;
};

export type MatchResult = {
  matches: CandidateMatch[];
  answered: number;
  location: MatchLocation;
  ballot?: BallotInfo;
};

export type MatchPayload = {
  state: string;
  city: string;
  address?: string; // optional: lets the server find your U.S. House district
  zip?: string;
  answers: {
    id: string;
    section: string;
    type: 'scale' | 'choice';
    question: string;
    answer: number | string;
    weight?: number; // 0.5 low, 1 normal, 2 high, 3 top priority
  }[];
};

export type MatchEvent = { event: string; data: any };

/** POSTs to /run and calls onEvent for every server-sent event. Resolves when the stream ends. */
export async function runMatch(
  payload: MatchPayload,
  onEvent: (e: MatchEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    signal,
  });

  if (!res.ok || !res.body) {
    let msg = `Server error (${res.status})`;
    try {
      msg = (await res.json()).error ?? msg;
    } catch {}
    throw new Error(msg);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let end: number;
    while ((end = buffer.indexOf('\n\n')) !== -1) {
      const raw = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);

      let event = '';
      let data = '';
      for (const line of raw.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
        // lines starting with ":" are keepalive comments
      }
      if (event) onEvent({ event, data: data ? JSON.parse(data) : null });
    }
  }
}