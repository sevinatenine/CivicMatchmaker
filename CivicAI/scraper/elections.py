#!/usr/bin/env python3
"""
List upcoming US elections (national, state, county, local, ballot measures) and the
candidates running, using the Google Civic Information API.

Usage:
    export GOOGLE_CIVIC_API_KEY=...        # or --key KEY / --key-file key.txt
    python elections.py --state CO --city Broomfield
    python elections.py --state CO --city Broomfield --address "1 Main St"   # best results
    python elections.py --state CO --elections-only                          # just list elections
    python elections.py --state CO --city Broomfield -o ../elections/broomfield.json

Notes:
  * The API's voterinfo endpoint wants a street address to work out which districts
    you're in. A bare "City, ST" often works for statewide/federal races but may
    return few or no local contests. Pass --address for a full picture.
  * Ballot data is only loaded by Google close to election day, and local coverage
    varies by county. An empty result usually means "not loaded yet", not "no election".
  * The old /representatives endpoint was shut down in 2025, so this only covers
    elections (which is what you asked for).
  * If ../scraped/index.json from pct_scraper.py exists, candidates you've already
    scraped are marked with their Vote Smart id.

No third-party dependencies (stdlib only).
"""
import argparse
import json
import os
import re
import sys
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://www.googleapis.com/civicinfo/v2"
TEST_ELECTION_ID = "2000"  # Google's "VIP Test Election"; never real

CATEGORY_ORDER = ["National", "State", "County", "Local", "Regional / special district",
                  "Other", "Ballot measures"]
LEVEL_TO_CATEGORY = {
    "country": "National",
    "administrativeArea1": "State",
    "administrativeArea2": "County",
    "locality": "Local",
    "subLocality1": "Local",
    "subLocality2": "Local",
    "regional": "Regional / special district",
    "special": "Regional / special district",
}
SCOPE_TO_CATEGORY = {
    "congressional": "National",
    "statewide": "State",
    "stateUpper": "State",
    "stateLower": "State",
    "countywide": "County",
    "countyCouncil": "County",
    "citywide": "Local",
    "cityCouncil": "Local",
    "ward": "Local",
    "municipal": "Local",
}


class ApiError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def api_get(path: str, params: dict) -> dict:
    url = f"{API}{path}?{urlencode(params)}"
    try:
        with urlopen(Request(url, headers={"Accept": "application/json"}), timeout=30) as r:
            return json.load(r)
    except HTTPError as e:
        try:
            msg = json.load(e)["error"]["message"]
        except Exception:
            msg = str(e.reason)
        raise ApiError(e.code, msg)
    except URLError as e:
        sys.exit(f"Network error: {e.reason}")


def get_key(args) -> str:
    key = args.key or os.environ.get("GOOGLE_CIVIC_API_KEY")
    if args.key_file:
        with open(args.key_file, encoding="utf-8") as f:
            key = f.read().strip()
    if not key:
        sys.exit("No API key. Use --key, --key-file, or set GOOGLE_CIVIC_API_KEY.")
    return key


def upcoming_elections(key: str, state: str) -> list:
    """Elections that are in the future and apply to this state (or the whole US)."""
    elections = api_get("/elections", {"key": key}).get("elections", [])
    today = date.today().isoformat()
    out = []
    for e in elections:
        if e.get("id") == TEST_ELECTION_ID or "test" in e.get("name", "").lower():
            continue
        if e.get("electionDay", "") < today:
            continue
        m = re.search(r"/state:([a-z]{2})(?:/|$)", e.get("ocdDivisionId", ""))
        if m and m.group(1) != state.lower():
            continue
        out.append(e)
    return sorted(out, key=lambda e: e.get("electionDay", ""))


def categorize(contest: dict) -> str:
    if contest.get("type") == "Referendum" or contest.get("referendumTitle"):
        return "Ballot measures"
    for level in contest.get("level", []):
        if level in LEVEL_TO_CATEGORY:
            return LEVEL_TO_CATEGORY[level]
    scope = contest.get("district", {}).get("scope", "")
    return SCOPE_TO_CATEGORY.get(scope, "Other")


def normalize_contest(c: dict) -> dict:
    return {
        "category": categorize(c),
        "type": c.get("type", ""),
        "office": c.get("office") or c.get("referendumTitle") or c.get("ballotTitle", ""),
        "district": c.get("district", {}).get("name", ""),
        "primary_party": c.get("primaryParty", ""),
        "vote_for": c.get("numberVotingFor") or c.get("numberElected") or "",
        "referendum_subtitle": c.get("referendumSubtitle", ""),
        "referendum_url": c.get("referendumUrl", ""),
        "candidates": [
            {"name": cand.get("name", ""),
             "party": cand.get("party", ""),
             "url": cand.get("candidateUrl", "")}
            for cand in c.get("candidates", [])
        ],
    }


def election_contests(key: str, address: str, election_id: str) -> list:
    data = api_get("/voterinfo", {"key": key, "address": address, "electionId": election_id})
    return [normalize_contest(c) for c in data.get("contests", [])]


def load_pct_lookup() -> dict:
    """normalized candidate name -> Vote Smart id, from the pct_scraper index (optional)."""
    try:
        import pct_scraper
        index = pct_scraper.load_index(pct_scraper.default_out_dir())
    except Exception:
        return {}
    norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
    return {norm(e.get("name", "")): cid for cid, e in index.items() if e.get("name")}


def print_election(e: dict, contests: list, pct: dict, note: str = "", has_street: bool = False) -> None:
    print(f"\n{'=' * 70}\n{e['name']}  —  {e['electionDay']}  (id {e['id']})\n{'=' * 70}")
    if note:
        print(f"  {note}")
        return
    if not contests:
        print("  No contests returned for this address.")
        if not has_street:
            print("  Google needs a street address to find your districts. "
                  "Re-run with --address \"123 Main St\" --zip 80020.")
        else:
            print("  Ballot data may not be loaded for this address yet.")
        return
    norm = lambda s: re.sub(r"[^a-z]", "", s.lower())
    for cat in CATEGORY_ORDER:
        group = [c for c in contests if c["category"] == cat]
        if not group:
            continue
        print(f"\n[{cat}]")
        for c in group:
            head = c["office"] or "(untitled contest)"
            if c["district"]:
                head += f" — {c['district']}"
            if c["primary_party"]:
                head += f" ({c['primary_party']} primary)"
            if c["vote_for"]:
                head += f"  [vote for {c['vote_for']}]"
            print(f"  • {head}")
            if c["referendum_subtitle"]:
                print(f"      {c['referendum_subtitle']}")
            for cand in c["candidates"]:
                party = f" ({cand['party']})" if cand["party"] else ""
                pid = pct.get(norm(cand["name"]))
                tag = f"  [PCT id {pid}]" if pid else ""
                print(f"      - {cand['name']}{party}{tag}")


def main():
    ap = argparse.ArgumentParser(description="Find upcoming US elections + candidates (Google Civic API)")
    ap.add_argument("--state", required=True, help="Two-letter state code, e.g. CO")
    ap.add_argument("--city", help="City name, e.g. Broomfield")
    ap.add_argument("--address", help="Street address (recommended; improves local coverage)")
    ap.add_argument("--zip", help="ZIP code to append to the address/city")
    ap.add_argument("--election-id", help="Only fetch this election id")
    ap.add_argument("--elections-only", action="store_true",
                    help="Just list upcoming elections; don't fetch contests")
    ap.add_argument("-o", "--output", help="Also save the results as JSON to this path")
    ap.add_argument("--key", help="Google Civic API key (or GOOGLE_CIVIC_API_KEY env var)")
    ap.add_argument("--key-file", help="Text file containing the API key")
    args = ap.parse_args()

    state = args.state.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", state):
        sys.exit("--state must be a two-letter code like CO.")
    if not args.city and not args.address:
        sys.exit("Provide --city and/or --address.")

    key = get_key(args)

    if args.address:
        address = args.address
        if args.city and args.city.lower() not in address.lower():
            address += f", {args.city}"
        if state not in address.upper():
            address += f", {state}"
    else:
        address = f"{args.city}, {state}"
    if args.zip:
        address += f" {args.zip}"

    try:
        elections = upcoming_elections(key, state)
    except ApiError as e:
        sys.exit(f"Elections lookup failed ({e.code}): {e}")
    if args.election_id:
        elections = [e for e in elections if e["id"] == args.election_id]

    if not elections:
        sys.exit(f"No upcoming elections listed by Google for {state}.")

    print(f"Address used: {address}")
    print(f"{len(elections)} upcoming election(s) for {state}:")
    for e in elections:
        print(f"  {e['electionDay']}  {e['name']}  (id {e['id']})")

    results = []
    if not args.elections_only:
        pct = load_pct_lookup()
        for e in elections:
            contests, note = [], ""
            try:
                contests = election_contests(key, address, e["id"])
            except ApiError as err:
                note = f"Skipped ({err.code}): {err}"
            print_election(e, contests, pct, note, bool(args.address))
            results.append({"election": e, "contests": contests, "error": note})
    else:
        results = [{"election": e, "contests": [], "error": ""} for e in elections]

    if args.output:
        out = {"state": state, "city": args.city, "address_used": address,
               "fetched": date.today().isoformat(), "elections": results}
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()