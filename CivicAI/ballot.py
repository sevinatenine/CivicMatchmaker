"""
Races on the user's ballot that have no scored positions.

FEC only knows federal candidates. Local and state races (mayor, county, school board, ...)
come from the Google Civic Information API via scraper/elections.py, which needs a street
address and GOOGLE_CIVIC_API_KEY ("Google Civic Information API" enabled).
These candidates usually have no recorded issue positions, so they are listed
unscored ("ballotOnly") unless a scraped Vote Smart file exists for the same person.
"""

import logging
import re

import config
from candidates import OFFICE_CODES, classify_office, load_registry
from location import dnum, in_area

log = logging.getLogger("ballot")

CIVIC_CATEGORY_TO_LEVEL = {
    "National": "Federal", "State": "State", "County": "Local",
    "Local": "Local", "Regional / special district": "Local",
}


def _name_words(s):
    return re.sub(r"[^a-z ]", "", (s or "").lower()).split()


def same_person(a, b):
    x, y = _name_words(a), _name_words(b)
    return bool(x and y and x[-1] == y[-1] and x[0][:1] == y[0][:1])


def fetch_ballot(loc, address, city, zip_):
    """-> (contests, election_names, note). Never raises."""
    key = config.GOOGLE_CIVIC_API_KEY
    if not key:
        return [], [], "Local races are off: set GOOGLE_CIVIC_API_KEY on the server."
    if not address:
        return [], [], "Add a street address and ZIP to see the local races on your ballot."
    state = loc["state"]
    if not state:
        return [], [], "Your state wasn't recognized, so local races can't be loaded."
    full = ", ".join(p for p in [address, city, f"{state} {zip_}".strip()] if p)
    try:
        from scraper import elections as civic   # stdlib-only helper in scraper/
        contests, names = [], []
        for e in civic.upcoming_elections(key, state)[:3]:
            try:
                got = civic.election_contests(key, full, e["id"])
            except civic.ApiError as err:
                log.warning("ballot lookup skipped %s: %s", e.get("name"), err)
                print(f"[ballot] skipped {e.get('name')}: {err}", flush=True)
                continue
            if got:
                names.append(e["name"])
                contests += got
    except (Exception, SystemExit) as err:  # api_get() calls sys.exit() on network errors
        print(f"[ballot] failed: {err}", flush=True)
        return [], [], f"Could not load ballot data: {err}"
    if not contests:
        return [], [], ("Google has no ballot data for that address yet. It is usually loaded "
                        "close to election day, and local coverage varies by county.")
    print(f"[ballot] {len(contests)} contests for {full!r}", flush=True)
    return contests, names, None


def registry_candidates(loc, scored):
    """
    Federal candidates from candidates.json with no Vote Smart answers (e.g. they never took
    the Political Courage Test), listed unscored so they don't silently disappear.
    FEC also lists primary losers and paper filings, so only the top fundraiser per party in
    each race is kept (a proxy for the nominee); ties, e.g. nobody raised money, keep everyone.
    """
    races = {}
    for r in load_registry():
        if r.get("office") not in OFFICE_CODES:
            continue
        level, position = OFFICE_CODES[r["office"]]
        district = r.get("district") if r["office"] == "H" else None
        if not in_area({"state": r.get("state"), "position": position, "district": district}, loc):
            continue
        key = (r.get("state"), r["office"], district or "", r.get("party_code") or r.get("party"))
        races.setdefault(key, []).append((r, level, position, district))

    out, seen, seen_ids = [], [m["name"] for m in scored], set()
    for group in races.values():
        top = max(g[0].get("raised") or 0 for g in group)
        for r, level, position, district in group:
            if (r.get("raised") or 0) < top:
                continue
            if r.get("pct_scraped") or any(same_person(r["name"], n) for n in seen):
                continue                  # already scored from a Vote Smart file
            if r.get("pct_id") and r["pct_id"] in seen_ids:
                continue                  # same person filed twice with FEC
            seen.append(r["name"])
            seen_ids.add(r.get("pct_id"))
            office = f"{position} ({r['state']})" + (f" - District {dnum(district)}" if district else "")
            out.append({
                "id": f"fec-{r['fec_id']}", "name": r["name"], "office": office,
                "party": r.get("party") or None, "level": level, "position": position,
                "district": district, "state": r.get("state"),
                "score": None, "coverage": 0, "sections": {}, "reasons": [],
                "ballotOnly": True, "onBallot": True,
                "url": None,   # the app labels url "Campaign website"
            })
    return out


def ballot_measures(contests):
    """Referendums / ballot questions from the Google Civic contests."""
    return [{"title": c["office"], "subtitle": c["referendum_subtitle"] or None,
             "district": c["district"] or None, "url": c["referendum_url"] or None}
            for c in contests if c["category"] == "Ballot measures" and c["office"]]


def ballot_candidates(contests, state):
    out, seen = [], set()
    for c in contests:
        if c["category"] == "Ballot measures" or not c["candidates"]:
            continue
        office = c["office"] or ""
        guess_level, position = classify_office(office)
        level = CIVIC_CATEGORY_TO_LEVEL.get(c["category"], guess_level)
        if position == "Other":
            position = office[:40] or "Other"
        label = f"{office} — {c['district']}" if c["district"] else office
        for cand in c["candidates"]:
            cid = f"ballot-{'-'.join(_name_words(cand['name']))}-{'-'.join(_name_words(office))}"
            if not cand["name"] or cid in seen:
                continue
            seen.add(cid)
            out.append({
                "id": cid, "name": cand["name"], "office": label,
                "party": cand["party"] or None, "level": level, "position": position,
                "district": None, "state": state,
                "score": None, "coverage": 0, "sections": {}, "reasons": [],
                "ballotOnly": True, "onBallot": True, "url": cand["url"] or None,
            })
    return out
