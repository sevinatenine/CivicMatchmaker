import { MatchResult } from '@/lib/matchApi';

/** The most recent match result, so other screens (e.g. the sample ballot) can reuse it
 *  without re-running the match on the server. Lives in memory only. */
type Saved = { result: MatchResult; state: string; city: string };

let saved: Saved | null = null;

export function setLastResult(value: Saved | null) {
  saved = value;
}

export function getLastResult(): Saved | null {
  return saved;
}
