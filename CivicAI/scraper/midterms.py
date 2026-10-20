#!/usr/bin/env python3
"""
Federal midterm candidates (U.S. Senate + U.S. House) from the free OpenFEC API, stored in a
local registry and linked to Vote Smart Political Courage Test data.

Everything lives in ../scraped/ (relative to this script; change with --out-dir):
    candidates.json   registry: every candidate with FEC id, state/district, Vote Smart id, status
    index.json        pct_scraper's index (Vote Smart id -> name, last_updated, ...)
    <vs_id>.json      the scraped PCT answers for each linked candidate

Typical workflow
    export FEC_API_KEY=...                       # free: https://api.data.gov/signup/
    python3 midterms.py --all-states             # 1) fetch every state's candidates -> candidates.json
    python3 midterms.py --pct-only --cookie-file cookie.txt --pct-limit 200
                                                 # 2) find each candidate's Vote Smart id + scrape PCT
                                                 #    (resumable: rerun to continue / refresh)
    python3 lookup.py --state CO --address "123 Main St" --zip 80020   # 3) look up by location

Other modes
    python3 midterms.py --state CO --address "123 Main St" --city Broomfield --zip 80020
        show one location's federal races (add --store to save them to the registry)
    python3 midterms.py --states CO,TX           # fetch only these states
    python3 midterms.py --state CO --district 02 # skip geocoding

Safe to rerun / run alongside other runs
    * The registry is READ FROM DISK before every save and only the records this run changed
      are merged in, under a file lock. Candidates added by another run are never lost.
    * Short rate limits (HTTP 429/5xx) are retried with backoff instead of ending the run.
    * States already fetched are skipped; rerun --all-states to continue where it stopped
      (add --refetch to refresh them).

Vote Smart linking (--pct / --pct-only):
    * searches Vote Smart by name, then scores results on state, office, district, last name,
      first initial and party. Clear winners are "linked" and their PCT is scraped.
    * unclear results are stored as "ambiguous" (with the top matches) and no-hits as
      "not_found". To fix one by hand, put the right Vote Smart id in that candidate's `pct_id`
      in candidates.json; the next --pct run scrapes it.
    * Not every candidate has taken the PCT, so "linked" does not guarantee answers exist
      (`pct_scraped` says whether they did).

Caveats
    * FEC only knows FEDERAL candidates (not governor, state legislature, local, ballot measures).
    * FEC lists everyone who filed and raised money this cycle, including primary losers.

Stdlib only for the FEC part; --pct needs pct_scraper.py's deps (curl_cffi, beautifulsoup4).
"""
import argparse
import fcntl
import json
import os
import re
import sys
import time
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FEC_API = "https://api.open.fec.gov/v1"
CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies/address"
UA = "midterms-lookup/1.0 (personal research)"
NAME_NOISE = {"MR", "MRS", "MS", "DR", "HON", "JR", "SR", "II", "III", "IV"}
REGISTRY_FILE = "candidates.json"
STATES = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
          "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC AS GU MP PR VI").split()


class FetchError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def default_out_dir() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scraped"))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def age_days(iso: str) -> float:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() / 86400
    except (TypeError, ValueError):
        return 1e9


def http_json(url: str, params: dict, label: str, retries: int = 3) -> dict:
    """GET JSON. Retries rate limits / server errors with backoff before giving up."""
    req = Request(f"{url}?{urlencode(params)}",
                  headers={"Accept": "application/json", "User-Agent": UA})
    for attempt in range(retries + 1):
        try:
            with urlopen(req, timeout=30) as r:
                return json.load(r)
        except HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                ra = e.headers.get("Retry-After") if e.headers else None
                wait = int(ra) if ra and ra.isdigit() else (60 if e.code == 429 else 5) * (attempt + 1)
                if wait <= 300:  # a long Retry-After means a daily cap: don't sit here
                    print(f"{label}: HTTP {e.code}, waiting {wait}s "
                          f"(retry {attempt + 1}/{retries})", file=sys.stderr)
                    time.sleep(wait)
                    continue
            hint = ""
            if e.code == 429:
                hint = " (rate limited: slow down or get a free key at https://api.data.gov/signup/)"
            elif e.code in (400, 403):
                hint = " (check the API key / parameters)"
            raise FetchError(f"{label}: HTTP {e.code}{hint}", e.code)
        except URLError as e:
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
                continue
            raise FetchError(f"{label}: network error: {e.reason}")
        except ValueError:
            raise FetchError(f"{label}: response was not JSON")


# --------------------------------------------------------------------------- #
# Registry (../scraped/candidates.json) and pct index
# --------------------------------------------------------------------------- #
@contextmanager
def registry_lock(out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, ".candidates.lock"), "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def load_registry(out_dir: str) -> dict:
    path = os.path.join(out_dir, REGISTRY_FILE)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                reg = json.load(f)
            reg.setdefault("meta", {})
            reg.setdefault("candidates", {})
            return reg
        except (ValueError, OSError, AttributeError) as e:
            # never silently start fresh: that's how a registry gets wiped
            sys.exit(f"{path} is unreadable ({e}). Fix or restore it (check for a .bak) "
                     f"and rerun; refusing to overwrite it.")
    return {"meta": {}, "candidates": {}}


def mark_dirty(reg: dict, fec_id: str) -> None:
    reg.setdefault("_dirty", set()).add(fec_id)


def save_registry(out_dir: str, reg: dict) -> None:
    """Re-read the file under a lock, merge in only the records this run touched
    (reg['_dirty']), and write atomically. Other runs' candidates are kept."""
    dirty = reg.setdefault("_dirty", set())
    with registry_lock(out_dir):
        disk = load_registry(out_dir)
        for fid in dirty:
            if fid in reg["candidates"]:
                disk["candidates"][fid] = reg["candidates"][fid]
        states = disk["meta"].setdefault("states", {})
        for s, t in reg["meta"].get("states", {}).items():
            if t > states.get(s, ""):
                states[s] = t
        for k, v in reg["meta"].items():
            if k != "states":
                disk["meta"][k] = v
        path = os.path.join(out_dir, REGISTRY_FILE)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(disk, f, indent=2, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, path)  # atomic: Ctrl-C can't leave a half-written file
    # pick up anything other runs added, keeping object identity for records in use
    for fid, rec in disk["candidates"].items():
        mine = reg["candidates"].get(fid)
        if mine is None:
            reg["candidates"][fid] = rec
        elif fid not in dirty and mine is not rec:
            mine.clear()
            mine.update(rec)
    reg["meta"] = disk["meta"]
    dirty.clear()


def load_pct_index(out_dir: str) -> dict:
    path = os.path.join(out_dir, "index.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def upsert(reg: dict, cands: list, state: str, year: int) -> tuple:
    """Merge freshly fetched FEC candidates into the registry, keeping any pct_* fields."""
    now = now_iso()
    new = 0
    for c in cands:
        old = reg["candidates"].get(c["fec_id"])
        if old is None:
            new += 1
        rec = dict(old or {})
        rec.update(c)
        rec["first_seen"] = (old or {}).get("first_seen", now)
        rec["last_seen"] = now
        reg["candidates"][c["fec_id"]] = rec
        mark_dirty(reg, c["fec_id"])
    reg["meta"].setdefault("states", {})[state] = now
    reg["meta"]["year"] = year
    reg["meta"]["last_fetched"] = now
    return new, len(cands) - new


# --------------------------------------------------------------------------- #
# Districts from a street address (Census geocoder)
# --------------------------------------------------------------------------- #
def geocode(street, city, state, zip_):
    params = {"street": street, "city": city, "state": state, "zip": zip_,
              "benchmark": "Public_AR_Current", "vintage": "Current_Current",
              "layers": "all", "format": "json"}
    params = {k: v for k, v in params.items() if v}
    data = http_json(CENSUS, params, "Census geocoder")
    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    m = matches[0]
    info = {"matched_address": m.get("matchedAddress", "")}
    for key, rows in (m.get("geographies") or {}).items():
        if not rows:
            continue
        row = rows[0]
        if "Congressional Districts" in key and row.get("GEOID"):
            info["congressional_district"] = row["GEOID"][2:].zfill(2)  # state fips (2) + district (2)
        elif "Legislative Districts - Upper" in key:
            info["state_senate"] = row.get("NAME", "")
        elif "Legislative Districts - Lower" in key:
            info["state_house"] = row.get("NAME", "")
        elif key == "Counties":
            info["county"] = row.get("NAME", "")
    return info


# --------------------------------------------------------------------------- #
# Candidates (OpenFEC)
# --------------------------------------------------------------------------- #
def fec_candidates(key, state, year, office, include_all):
    out, page = [], 1
    while True:
        params = {"api_key": key, "state": state, "election_year": year, "office": office,
                  "per_page": 100, "page": page, "sort": "name"}
        if not include_all:
            params["candidate_status"] = "C"
            params["has_raised_funds"] = "true"
        data = http_json(f"{FEC_API}/candidates/search/", params, f"OpenFEC {state}/{office}")
        out += data.get("results", [])
        if page >= data.get("pagination", {}).get("pages", 1):
            break
        page += 1
        time.sleep(0.2)
    return out


def fec_raised(key, state, year, office):
    """candidate_id -> total receipts (money raised) for this cycle."""
    out, page = {}, 1
    while True:
        params = {"api_key": key, "state": state, "election_year": year, "office": office,
                  "per_page": 100, "page": page, "sort": "-receipts"}
        data = http_json(f"{FEC_API}/candidates/totals/", params, f"OpenFEC totals {state}/{office}")
        for r in data.get("results", []):
            cid = r.get("candidate_id")
            out[cid] = max(out.get(cid, 0), r.get("receipts") or 0)
        if page >= data.get("pagination", {}).get("pages", 1):
            break
        page += 1
        time.sleep(0.2)
    return out


def pretty_name(fec_name: str) -> str:
    """'NEGUSE, JOSEPH D. MR.' -> 'Joseph Neguse' (good enough to search Vote Smart)."""
    if "," not in fec_name:
        return fec_name.title()
    last, rest = [p.strip() for p in fec_name.split(",", 1)]
    toks = [t for t in rest.replace(".", "").split()
            if len(t) > 1 and t.upper() not in NAME_NOISE]
    first = toks[0] if toks else ""
    return f"{first} {last}".title().strip()


def shape(c: dict, year: int, state: str) -> dict:
    name = pretty_name(c.get("name", ""))
    fid = c.get("candidate_id", "")
    return {
        "fec_id": fid,
        "name": name,
        "search_name": name,
        "fec_name": c.get("name", ""),
        "party": (c.get("party_full") or c.get("party") or "").title(),
        "party_code": c.get("party") or "",
        "state": c.get("state") or state,
        "office": c.get("office", ""),
        "district": c.get("district") or "",
        "incumbent": c.get("incumbent_challenge_full") or "",
        "year": year,
        "fec_url": f"https://www.fec.gov/data/candidate/{fid}/",
    }


def fetch_state(key, state, year, include_all):
    out = []
    for office in ("S", "H"):
        raised = fec_raised(key, state, year, office)
        for c in fec_candidates(key, state, year, office, include_all):
            rec = shape(c, year, state)
            rec["raised"] = raised.get(rec["fec_id"], 0)
            out.append(rec)
        time.sleep(0.2)
    return out


# --------------------------------------------------------------------------- #
# Vote Smart linking + PCT scraping
# --------------------------------------------------------------------------- #
NAME_SUFFIX = {"jr", "sr", "ii", "iii", "iv", "md", "dr"}


def _words(s: str) -> list:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return [w for w in re.sub(r"[^a-z ]", "", s.lower()).split() if w not in NAME_SUFFIX]


def score(c: dict, r: dict) -> int:
    """How well a Vote Smart search result r matches FEC candidate c (-1 = reject)."""
    s = 0
    st = (r.get("state_id") or "").upper()
    if st:
        if st != c["state"]:
            return -1
        s += 3
    cn, rn = _words(c["search_name"]), _words(r.get("name", ""))
    if not cn or not rn or cn[-1] != rn[-1]:
        return -1
    s += 2
    if len(cn) > 1 and cn[0][0] == rn[0][0]:
        s += 1
    office = (r.get("office") or "").lower()
    is_senate = "senat" in office and "state" not in office
    is_house = ("house" in office or "represent" in office) and "state" not in office
    if c["office"] == "S":
        s += 2 if is_senate else 0
    else:
        s += 2 if is_house else 0
    d = re.sub(r"\D", "", str(r.get("district") or ""))
    if c["office"] == "H" and is_house and d and c["district"]:
        s += 2 if int(d) == int(c["district"]) else -1
    if (r.get("party") or "")[:1].upper() == (c.get("party_code") or "")[:1].upper():
        s += 1
    return s


def choose(c: dict, results: list):
    scored = sorted(((score(c, r), r) for r in results), key=lambda x: -x[0])
    scored = [(s, r) for s, r in scored if s > 0]
    if not scored:
        return "not_found", None, []
    top = [{"id": str(r.get("candidate_id")), "name": r.get("name"), "office": r.get("office"),
            "party": r.get("party"), "state": r.get("state_id"), "district": r.get("district"),
            "score": s} for s, r in scored[:3]]
    best_s, best = scored[0]
    if best_s < 5:                      # only weak matches (e.g. a state legislator with the same name)
        return "not_found", None, []
    clear = len(scored) == 1 or best_s - scored[1][0] >= 2
    if best_s >= 6 and clear:
        return "linked", best, top
    return "ambiguous", None, top


def vs_results_for(c, ps, cookie, ua, delay):
    seen = {}
    last = c["search_name"].split()[-1]
    for q in dict.fromkeys([c["search_name"], last]):
        for r in ps.search_candidates(q, cookie, ua):
            seen.setdefault(str(r.get("candidate_id")), r)
        time.sleep(delay)
        if any(score(c, r) >= 6 for r in seen.values()):
            break   # full-name query already found a good match; skip the broader one
    return list(seen.values())


def process_candidate(c, ps, out_dir, cookie, ua, delay) -> bool:
    """Link (if needed) and scrape one candidate, mutating the registry record.
    Returns True if Vote Smart showed a login/view-limit wall."""
    now = now_iso()
    if not c.get("pct_id"):
        results = vs_results_for(c, ps, cookie, ua, delay)
        status, best, top = choose(c, results)
        c["pct_status"] = status
        c["pct_candidates"] = top if status == "ambiguous" else []
        c["pct_checked"] = now
        if best:
            c["pct_id"] = str(best["candidate_id"])
            c["pct_name"] = best.get("name") or c["name"]
        if status != "linked":
            return False
    elif c.get("pct_status") != "linked":
        c["pct_status"] = "linked"      # id filled in by hand
    url = ps.pct_url(c["pct_id"], c.get("pct_name") or c["name"])
    data = ps.scrape(url, cookie, ua)
    if data.get("_login_wall"):
        c.pop("pct_checked", None)      # not really checked, so retry on the next run
        return True
    c["pct_checked"] = now
    if data["positions"]:
        ps.save_scrape(data, out_dir, url)
        c["pct_scraped"] = True
        c["pct_last_updated"] = data["scraped_at"]
        c["pct_file"] = f"{c['pct_id']}.json"
    else:
        c["pct_scraped"] = False
    time.sleep(delay)
    return False


def pct_needs(c: dict, refresh_days: float, retry_missing: bool) -> bool:
    if c.get("pct_id") and c.get("pct_status") != "linked":
        return True                       # id was filled in by hand
    if not c.get("pct_checked"):
        return True
    if c.get("pct_status") in ("not_found", "ambiguous"):
        return retry_missing
    return age_days(c["pct_checked"]) >= refresh_days


def likely_on_ballot(cands):
    """fec_ids of the top fundraiser per (state, office, district, party): a proxy for general-election nominees."""
    best = {}
    for c in cands:
        key = (c["state"], c["office"], c.get("district") or "", c.get("party_code") or c.get("party"))
        if key not in best or (c.get("raised") or 0) > (best[key].get("raised") or 0):
            best[key] = c
    return {c["fec_id"] for c in best.values()}


def run_pct(reg, out_dir, scope, year, args):
    try:
        import pct_scraper as ps
    except ImportError as e:
        sys.exit(f"--pct needs pct_scraper.py next to this script and its dependencies ({e}).")
    cookie = args.cookie or os.environ.get("VS_COOKIE")
    if args.cookie_file:
        with open(args.cookie_file, encoding="utf-8") as f:
            cookie = f.read().strip()
    if not cookie:
        print("Warning: no cookie given (--cookie-file / VS_COOKIE); Vote Smart will likely block you.",
              file=sys.stderr)

    pool = [c for c in reg["candidates"].values() if c.get("year") == year]
    ballot = likely_on_ballot(pool) if args.likely_ballot else None
    todo = [c for c in pool
            if (scope is None or c["state"] in scope)
            and (ballot is None or c["fec_id"] in ballot)
            and (c.get("raised") or 0) >= args.min_raised
            and pct_needs(c, args.refresh_days, args.retry_missing)]
    todo.sort(key=lambda c: (-(c.get("raised") or 0), c["state"], c["name"]))
    if args.pct_limit:
        todo = todo[:args.pct_limit]
    print(f"Vote Smart: {len(todo)} candidate(s) to process "
          f"(min raised ${args.min_raised:,.0f}; delay {args.pct_delay}s each; "
          f"Ctrl-C is safe, progress is saved).", file=sys.stderr)

    walls, done = 0, 0
    try:
        for i, c in enumerate(todo, 1):
            label = f"{c['state']} {c['office']}{'-' + c['district'] if c['office'] == 'H' else ''}"
            try:
                wall = process_candidate(c, ps, out_dir, cookie, args.user_agent, args.pct_delay)
            except RuntimeError as e:           # search returned a non-JSON page
                print(f"Stopping: {e}", file=sys.stderr)
                break
            except SystemExit as e:             # fetch() exits on 403/429/503
                print(f"Stopping: {e}", file=sys.stderr)
                break
            mark_dirty(reg, c["fec_id"])
            save_registry(out_dir, reg)
            if wall:
                walls += 1
                print(f"[{i}/{len(todo)}] {label} {c['name']}: login/view-limit wall", file=sys.stderr)
                if walls >= 2:
                    print("Stopping: Vote Smart is showing the login wall. Refresh your cookie "
                          "(or wait for the view limit to reset) and rerun.", file=sys.stderr)
                    break
                continue
            walls = 0
            done += 1
            extra = ""
            if c.get("pct_status") == "linked":
                extra = f" id={c['pct_id']} pct={'yes' if c.get('pct_scraped') else 'none filled out'}"
            raised = f" ${c.get('raised') or 0:,.0f}"
            print(f"[{i}/{len(todo)}] {label} {c['name']}{raised}: {c.get('pct_status')}{extra}",
                  file=sys.stderr)
    except KeyboardInterrupt:
        print("\nInterrupted; progress saved.", file=sys.stderr)
    save_registry(out_dir, reg)
    stats = {}
    for c in reg["candidates"].values():
        if scope is None or c["state"] in scope:
            k = c.get("pct_status", "unprocessed")
            stats[k] = stats.get(k, 0) + 1
    print(f"Processed {done} this run. Registry status counts: {stats}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Display mode (one location)
# --------------------------------------------------------------------------- #
def sort_key(c):
    return (0 if c["incumbent"].lower().startswith("incumbent") else 1, c["name"])


def print_race(title, cands):
    print(f"\n== {title} ==")
    if not cands:
        print("  (no candidates found)")
    for c in sorted(cands, key=sort_key):
        tags = []
        if c["incumbent"] and c["incumbent"].lower() != "challenger":
            tags.append(c["incumbent"].lower())
        if c.get("pct_id"):
            tags.append(f"Vote Smart id {c['pct_id']}")
        tag = f"  [{', '.join(tags)}]" if tags else ""
        party = f" ({c['party']})" if c["party"] else ""
        print(f"  - {c['name']}{party}{tag}")
        print(f"      {c['fec_url']}")


def run_display(args, key, year, state, reg, out_dir):
    geo, district = None, None
    if args.district:
        district = args.district.strip().zfill(2)
    elif args.address:
        try:
            geo = geocode(args.address, args.city, state, args.zip)
        except FetchError as e:
            print(f"Warning: {e}", file=sys.stderr)
        if geo and geo.get("congressional_district"):
            district = geo["congressional_district"]
        else:
            print("Warning: couldn't work out your district from that address; "
                  "showing all House races (or pass --district).", file=sys.stderr)

    try:
        cands = fetch_state(key, state, year, args.all)
        cands = [c for c in cands if (c.get("raised") or 0) >= args.min_raised]
    except FetchError as e:
        sys.exit(str(e))

    for c in cands:    # attach Vote Smart ids we already know
        c["pct_id"] = (reg["candidates"].get(c["fec_id"]) or {}).get("pct_id")
    if args.store:
        new, upd = upsert(reg, cands, state, year)
        for c in cands:   # drop empty pct_id values so they don't shadow a later link
            if not reg["candidates"][c["fec_id"]].get("pct_id"):
                reg["candidates"][c["fec_id"]].pop("pct_id", None)
        save_registry(out_dir, reg)
        print(f"Stored {len(cands)} candidates ({new} new) in {os.path.join(out_dir, REGISTRY_FILE)}",
              file=sys.stderr)

    senate = [c for c in cands if c["office"] == "S"]
    houses = {}
    for c in cands:
        if c["office"] == "H":
            houses.setdefault(c["district"] or "00", []).append(c)

    print(f"{year} federal races in {state}  (source: FEC)")
    if geo:
        bits = [f"U.S. House district {district}" if district else "",
                geo.get("county", ""), geo.get("state_senate", ""), geo.get("state_house", "")]
        print("Your districts: " + " · ".join(b for b in bits if b))
        print("  (state senate/house races aren't in FEC; those need your Secretary of State or Ballotpedia)")
    elif district:
        print(f"Using U.S. House district {district}")

    print_race(f"U.S. Senate ({state})", senate)
    show = sorted(houses) if (args.all_districts or not district) else [district]
    for d in show:
        label = "at-large" if d == "00" else f"District {d}"
        mine = "   <- your district" if d == district else ""
        print_race(f"U.S. House — {state} {label}{mine}", houses.get(d, []))
    if district and not args.all_districts and district not in houses:
        print(f"\n(no House candidates found for district {district}; try --all or check the district number)")
    print("\nNot covered here: governor, state legislature, county/local offices, ballot measures. "
          "FEC also keeps people who lost their primary on file.")

    if args.output:
        out = {"state": state, "year": year, "district": district, "geography": geo,
               "senate": senate, "house": {d: houses[d] for d in show if d in houses},
               "fetched": date.today().isoformat(), "source": "OpenFEC"}
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"Saved to {args.output}")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Federal midterm candidates (OpenFEC) + Vote Smart linking")
    g = ap.add_argument_group("what to fetch")
    g.add_argument("--state", help="One state (two-letter code) to show/fetch")
    g.add_argument("--all-states", action="store_true", help="Fetch every state/territory into the registry")
    g.add_argument("--states", help="Comma-separated list of states to fetch, e.g. CO,TX,WY")
    g.add_argument("--year", type=int, help="Election year (default: the current/next even year)")
    g.add_argument("--all", action="store_true",
                   help="Include everyone FEC has on file, even with no money raised / not yet statutory")
    g.add_argument("--refetch", action="store_true",
                   help="Re-fetch states even if they already have raised data")
    g.add_argument("--min-raised", type=float, default=0,
                   help="Only process/show candidates who raised at least this many dollars (e.g. 250000)")
    g.add_argument("--fec-key", help="OpenFEC/api.data.gov key (or FEC_API_KEY env var)")
    d = ap.add_argument_group("single-location display")
    d.add_argument("--address", help="Street address (used to find your districts)")
    d.add_argument("--city", help="City (helps the geocoder)")
    d.add_argument("--zip", help="ZIP code (helps the geocoder)")
    d.add_argument("--district", help="U.S. House district number, e.g. 2 or 02 (skips geocoding)")
    d.add_argument("--all-districts", action="store_true", help="Show every House district in the state")
    d.add_argument("--store", action="store_true", help="Also save the displayed candidates to the registry")
    d.add_argument("-o", "--output", help="Also save the displayed results as JSON")
    p = ap.add_argument_group("Vote Smart linking + PCT scraping")
    p.add_argument("--pct", action="store_true", help="After fetching, link candidates to Vote Smart and scrape their PCT")
    p.add_argument("--pct-only", action="store_true", help="Skip FEC; just process the registry (resume/refresh)")
    p.add_argument("--pct-limit", type=int, default=0, help="Process at most N candidates this run")
    p.add_argument("--pct-delay", type=float, default=2.0, help="Seconds to wait between Vote Smart requests (default 2)")
    p.add_argument("--refresh-days", type=float, default=30, help="Re-scrape linked candidates older than this (default 30)")
    p.add_argument("--retry-missing", action="store_true", help="Retry candidates marked not_found/ambiguous")
    p.add_argument("--cookie", help="Vote Smart Cookie header (or VS_COOKIE env var)")
    p.add_argument("--cookie-file", help="Text file containing the Vote Smart Cookie header")
    p.add_argument("--user-agent", help="Override the User-Agent (match your browser)")
    p.add_argument("--likely-ballot", action="store_true",
                   help="Only the top fundraiser per party in each race (likely general-election nominees)")
    ap.add_argument("-d", "--out-dir", help="Data folder (default: ../scraped relative to this script)")
    args = ap.parse_args()

    out_dir = os.path.normpath(args.out_dir) if args.out_dir else default_out_dir()
    year = args.year or (date.today().year + date.today().year % 2)

    if args.all_states:
        scope = STATES[:]
    elif args.states:
        scope = [s.strip().upper() for s in args.states.split(",") if s.strip()]
    elif args.state:
        scope = [args.state.strip().upper()]
    else:
        scope = None
    for s in scope or []:
        if s not in STATES:
            sys.exit(f"Unknown state/territory code: {s}")
    bulk = args.all_states or bool(args.states)

    if not args.pct_only and scope is None:
        ap.error("give --state, --states, --all-states, or --pct-only")

    reg = load_registry(out_dir)

    if not args.pct_only:
        key = args.fec_key or os.environ.get("FEC_API_KEY")
        if not key:
            if bulk:
                sys.exit("--all-states/--states needs a real FEC key (DEMO_KEY allows ~10 requests/hour). "
                         "Free key: https://api.data.gov/signup/  then set FEC_API_KEY.")
            key = "DEMO_KEY"
            print("Note: no FEC key set; using DEMO_KEY (about 10 requests/hour). "
                  "Free key: https://api.data.gov/signup/", file=sys.stderr)

        if bulk:
            total = 0
            for i, st in enumerate(scope, 1):
                have = [c for c in reg["candidates"].values() if c["state"] == st and c.get("year") == year]
                if have and all("raised" in c for c in have) and not args.refetch:
                    print(f"[{i}/{len(scope)}] {st}: already has raised data, skipping", file=sys.stderr)
                    continue
                try:
                    cands = fetch_state(key, st, year, args.all)
                except FetchError as e:
                    print(f"[{i}/{len(scope)}] {st}: {e}", file=sys.stderr)
                    if e.code == 429:
                        print("Stopping: rate limited (retries exhausted). Wait and rerun "
                              "--all-states; finished states are skipped.", file=sys.stderr)
                        break
                    continue
                new, upd = upsert(reg, cands, st, year)
                save_registry(out_dir, reg)   # saved per state so a failure keeps earlier states
                total += len(cands)
                print(f"[{i}/{len(scope)}] {st}: {len(cands)} candidates ({new} new, {upd} updated)",
                      file=sys.stderr)
            print(f"Registry: {len(reg['candidates'])} candidates in {os.path.join(out_dir, REGISTRY_FILE)}",
                  file=sys.stderr)
        else:
            run_display(args, key, year, scope[0], reg, out_dir)

    if args.pct or args.pct_only:
        run_pct(reg, out_dir, scope, year, args)


if __name__ == "__main__":
    main()