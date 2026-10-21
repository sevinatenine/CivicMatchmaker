"""
CivicMatchmaker matching engine, powered by Supersonic Labs' Julia 1.

Julia 1 is a small classifier, not a reasoner, so it only gets jobs it is built for:

  1. ROUTE      which of the candidate's recorded positions is about the same
                issue as an app question?            (choice among 2-20 options)
  2. DIRECTION  if the candidate says "yes" to that position, is that the same
                side as the app statement or the opposite side? (3-way choice)
  3. STANCE     for free-text candidate answers ("Yes, with conditions"),
                supports / opposes / mixed.           (3-way choice)

The arithmetic (user's 1-5 answer vs candidate stance) is plain code.
Only the app's SCALE questions are scored; choice ("which should be prioritized")
questions have no support/oppose direction, so they are ignored for now.

LOCATION
    The app sends {"state", "city", optional "address", optional "zip"}.
    * state       -> only candidates for that state (plus national ones, e.g. President)
    * address+zip -> Census geocoder finds the U.S. House district, and House
                     candidates from other districts are dropped
    Each candidate also carries a `level` (Federal / State / Local / Other) and a
    `position` (U.S. Senate, U.S. House, Governor, ...) so the app can filter.

BALLOT (local/state races)
    With GOOGLE_CIVIC_API_KEY set and a street address given, ballot_candidates() adds
    the races on the user's real ballot (mayor, county, school board, ...) via elections.py.
    Candidates are loaded from JSON files made by pct_scraper.py (folder ../scraped,
or $CANDIDATES_DIR). If candidates.json (made by midterms.py) sits in the same folder,
it supplies the exact office + district. With no files, the mock candidates in
peopleTest.py are used.

Env vars (optional):
    JULIA_MODEL_DIR   path to the downloaded Julia-1 repo   (default: Julia-1)
    JULIA_DEVICE      "cpu" or "cuda"                       (default: cpu)
    CANDIDATES_DIR    folder of candidate JSON files
    JULIA_DEBUG=1     print every pairing the model made
"""

import json
import logging
import os
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("ai")

MODEL_DIR = os.environ.get("JULIA_MODEL_DIR", "Julia-1")
DEVICE = os.environ.get("JULIA_DEVICE", "cpu")
DEBUG = os.environ.get("JULIA_DEBUG") == "1"

MATCH_MIN = 0.6      # minimum confidence that a position is about the same issue
SAME_MIN = 0.7       # minimum confidence in the second-opinion "same issue?" check
DIR_MIN = 0.65       # minimum confidence in the same-side / opposite-side call
OPTION_CHARS = 140   # Julia 1 limits each option to ~48 tokens

# App section -> Vote Smart categories whose positions could be relevant
SECTION_TO_VS = {
    "Education": ["Education"],
    "Housing": ["Economy"],
    "Taxes & Government Spending": ["Budget, Spending, and Taxes", "Economy"],
    "Environment & Energy": ["Energy & Environment"],
    "Healthcare": ["Health Care"],
    "Transportation & Infrastructure": ["Economy"],
    "Technology & AI": ["Technology and Communication"],
    "Public Safety & Criminal Justice": ["Crime & Public Safety", "Guns"],
    "Democracy & Voting": ["Elections", "Campaign Finance"],
    "Immigration": ["Immigration"],
    "Young People & College": ["Education", "Economy"],
    "Abortion": ["Abortion and Reproductive Health"],
    "Economy": ["Economy"],
    "Defense & National Security": ["Defense", "National Security"],
}

# peopleTest.py (NPAT) section name -> Vote Smart category
NPAT_SECTION_TO_VS = {
    "Budget/Economy": "Economy",
    "Taxes": "Budget, Spending, and Taxes",
    "Education": "Education",
    "Environment": "Energy & Environment",
    "Healthcare": "Health Care",
}

# A candidate position may only be paired with an app question if its text mentions the
# app section's topic. Several app sections share one broad Vote Smart category
# ("Economy" holds housing, transportation AND inflation questions), so without this the
# model was forced to pair a transit statement with, say, a Federal Reserve question.
_SECTION_WORDS = {
    "Education": r"educat|school|teacher|student|college|universit|tuition|pre-?k|preschool|charter|curricul|class size|literacy|scholarship|vocational|head start|k-12",
    "Housing": r"hous|\brent|zoning|mortgage|homeless|tenant|landlord|home ?owner|eviction|real estate|affordable home",
    "Taxes & Government Spending": r"\btax|budget|deficit|spending|surplus|\bdebt|revenue|fiscal|appropriat|audit|entitlement|safety net|social security|medicare|funding",
    "Abortion": r"abortion|\broe\b|pro-?choice|pro-?life|reproductive|planned parenthood|contracept",
    "Economy": r"econom|inflation|federal reserve|\bgrants?\b|incentive|\bjobs?\b",
    "Defense & National Security": r"defense|military|ukraine|sanction|national security|\bwar\b|troops|nato|international|foreign",
    "Environment & Energy": r"environment|climate|carbon|emission|energy|renewable|solar|wind (power|energy|farm|turbine)|\boil\b|\bgas\b|drilling|fossil|\bcoal\b|pollution|clean (air|water|energy)|conservation|public lands|nuclear|pipeline|fracking|\bepa\b",
    "Healthcare": r"health|medic|insur|hospital|prescription|drug pric|pharma|pre-?existing|single-?payer|public option|obamacare|affordable care",
    "Transportation & Infrastructure": r"transport|transit|infrastructure|highway|\broads?\b|\brail|bridge|airport|\bbus(es)?\b|public works|amtrak|electric vehicle|high-?speed|\bports?\b",
    "Technology & AI": r"artificial intelligence|\bai\b|technolog|internet|privacy|\bdata\b|cyber|broadband|social media|algorithm|big tech|telecom|net neutrality|surveillance|encrypt",
    "Public Safety & Criminal Justice": r"crim|polic|prison|incarcerat|sentenc|justice|\bguns?\b|firearm|law enforcement|death penalty|capital punishment|\bbail\b|background check|offender|sheriff",
    "Democracy & Voting": r"\bvot|elect|ballot|campaign|citizens united|gerrymander|redistrict|term limit|registration|dark money|super pac|lobby",
    "Immigration": r"immigra|border|asylum|\bvisa|\bdaca\b|dreamer|undocumented|deport|citizenship|refugee|green card|legal status|guest worker|sanctuary",
    "Young People & College": r"college|tuition|student|\bloans?\b|universit|vocational|apprentic|\bpell\b|scholarship|trade school|youth|young|job training|workforce|internship|minimum wage",
}
_SECTION_RE = {k: re.compile(v, re.I) for k, v in _SECTION_WORDS.items()}


def on_topic(section, text):
    rx = _SECTION_RE.get(section)
    return True if rx is None else bool(rx.search(text or ""))


STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

# FEC office code (from midterms.py's candidates.json) -> (level, position)
OFFICE_CODES = {
    "S": ("Federal", "U.S. Senate"),
    "H": ("Federal", "U.S. House"),
    "P": ("Federal", "President"),
}


# Each app question id -> the exact Vote Smart Political Courage Test question it mirrors.
# Every app statement is worded so that "Yes" to the Vote Smart question means agreeing with it,
# so these pairs need no model: the match and the direction are known.
DIRECT = {
    "roe-wade": "Do you support the Supreme Court's decision to overturn Roe v. Wade?",
    "safety-net": "Do you support expanding federal funding to support social safety net programs such as Social Security and Medicare?",
    "income-tax-cut": "Do you support a decrease in income taxes in order to balance the budget?",
    "wealth-tax": "Do you support a wealth tax in order to pay for public programs?",
    "growth-spending": "Do you support federal spending as a means of promoting economic growth (e.g. grants, tax incentives)?",
    "inflation-action": "Do you support the federal government taking action, beyond those of the Federal Reserve, to alleviate inflation?",
    "affordable-housing": "Do you support the federal government increasing funding for affordable housing programs?",
    "student-loans": "Do you support the forgiveness of federal student loan debt?",
    "voter-id": "Do you support requiring a government-issued identification in order to vote at the polls?",
    "campaign-finance": "Do you support the regulation of indirect campaign contributions from corporations, unions, and individuals?",
    "officer-liability": "Do you support protecting government officials, including law enforcement officers, from personal liability in civil lawsuits concerning alleged misconduct?",
    "gun-control": "Do you generally support gun-control legislation (e.g. red flag laws, boyfriend loopholes)?",
    "defense-spending": "Do you support increasing defense spending?",
    "economic-intervention": "Do you support economic intervention as a means of resolving international conflicts?",
    "ukraine-aid": "Do you support the US providing increased offensive military aid to Ukraine?",
    "renewables-funding": "Do you support government funding for the development of renewable energy (e.g. solar, wind, geo-thermal)?",
    "drilling-permits": "Do you support the federal government allowing permits for drilling on public lands?",
    "single-payer": "Do you support a government-run (e.g. single-payer) healthcare program, such as Medicare-for-All?",
    "paid-leave": "Do you support expanding paid family AND/OR medical leave benefits (e.g. maternity leave)?",
    "drug-prices": "Should the government be able to regulate the cost of prescription drugs?",
    "border-security": "Do you support increasing security along the southern US border?",
    "return-for-citizenship": "Do you support requiring immigrants to return to their country of origin before they are eligible for citizenship, regardless of their immigration status?",
    "social-media": "Do you generally support increased regulations on social media companies (e.g. Tik Tok, Facebook, etc.)?",
}


# Other versions of the test word some questions slightly differently (e.g. "entitlement programs"
# instead of "social safety net programs"). These prefixes are treated as the same question, with
# the same Yes = agree meaning. Only add one when "Yes" to the old wording clearly means agreeing.
ALIASES = {
    "safety-net": ["do you support expanding federal funding to support entitlement programs"],
    "campaign-finance": ["do you support the regulation of indirect campaign contributions"],
    "officer-liability": ["do you support the protection of government officials"],
    "growth-spending": ["do you support federal spending as a means of promoting economic growth"],
    "gun-control": ["do you generally support gun control legislation"],
    # "Pro-choice" / "Pro-life" answers are mapped to a stance in stance() below
    "roe-wade": ["do you generally support pro choice or pro life legislation"],
}


def _qkey(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _lookup(d, qid, key):
    """d: {normalized question: value}. Exact question first, then known alternate wordings."""
    if key and key in d:
        return d[key]
    for prefix in ALIASES.get(qid, ()):
        for k, v in d.items():
            if k.startswith(prefix):
                return v
    return None


# ------------------------------------------------------------------ model
_engine = None
_engine_lock = threading.Lock()
_predict_lock = threading.Lock()   # server runs several workers; keep inference serial


def get_engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            from julia import load_model  # provided by the Julia-1 repo
            _engine = load_model(
                MODEL_DIR, device=DEVICE, strict_encoding=True,
                max_length=8192, head_length=1024,
            )
        return _engine


def warmup():
    get_engine()


def _predict(state, questions):
    with _predict_lock:
        return get_engine().predict(state=state, questions=questions)["answers"]


def _short(text, n=OPTION_CHARS):
    return text if len(text) <= n else text[: n - 1] + "…"


# ------------------------------------------------------------------ office classification
_STATEWIDE = [
    ("lieutenant governor", "Lt. Governor"),
    ("attorney general", "Attorney General"),
    ("secretary of state", "Secretary of State"),
    ("treasurer", "Treasurer"),
    ("auditor", "Auditor"),
    ("comptroller", "Comptroller"),
    ("superintendent", "Superintendent"),
]

_LOCAL = [
    ("mayor", "Mayor"),
    ("council", "City Council"),
    ("school board", "School Board"),
    ("sheriff", "Sheriff"),
    ("district attorney", "District Attorney"),
    ("county", "County Office"),
    ("commission", "Commissioner"),
]


def classify_office(text):
    """Guess (level, position) from an office string like 'U.S. House (CO)'."""
    t = (text or "").lower()
    federal = bool(re.search(r"\bu\.?s\.?\b|united states|\bfederal\b", t))

    if "vice president" in t:
        return "Federal", "Vice President"
    if "president" in t:
        return "Federal", "President"

    # local offices first ("county commissioner", "city council", ...)
    for key, label in _LOCAL:
        if key in t:
            return "Local", label
    if re.search(r"\bcity\b|township|\btown\b|municipal|alderm|\bclerk\b|assessor|coroner", t):
        return "Local", "Other local office"

    if re.search(r"supreme court|\bjustice\b", t):
        return ("Federal" if federal else "State"), "Supreme Court"
    if re.search(r"\bjudge\b|judicial|\bcourt\b", t):
        return ("Federal" if federal else "State"), "Judge"

    if "governor" in t and "lieutenant" not in t:
        return "State", "Governor"
    for key, label in _STATEWIDE:
        if key in t:
            return "State", label

    if "senat" in t:
        if not federal and re.search(r"\bstate\b|legislat", t):
            return "State", "State Senate"
        return "Federal", "U.S. Senate"

    if re.search(r"house|representative|assembly|delegate|congress", t):
        if not federal and re.search(r"\bstate\b|assembly|delegate|legislat", t):
            return "State", "State House"
        return "Federal", "U.S. House"

    return "Other", "Other"


# ------------------------------------------------------------------ candidates
def _clean_name(name):
    """'Shawn Harris' Issue Positions (Political Courage Test)' -> 'Shawn Harris'."""
    return re.sub(r"[\u2019']s?\s+Issue Positions.*$", "", name or "").strip() or "Unknown"


def _from_scraped(d, reg=None):
    """d: a pct_scraper JSON file. reg: matching record from candidates.json (optional)."""
    ballot_txt = d.get("on_the_ballot", "")
    office = d.get("office") or ""
    if not office:  # some files only have "Running, Republican for U.S. House (AZ) - District 4"
        m_off = re.search(r"\bfor\s+(.+)$", ballot_txt)
        office = m_off.group(1).strip() if m_off else ""
    st = re.search(r"\(([A-Z]{2})\)", office)
    party_m = re.search(r"Running,\s*(.+?)\s+for\b", ballot_txt)
    party = party_m.group(1) if party_m else None
    state = st.group(1) if st else None
    level, position = classify_office(office)
    dm = re.search(r"district\s*(\d+)", office, re.I)
    district = dm.group(1) if dm else None

    if reg:
        if reg.get("office") in OFFICE_CODES:
            level, position = OFFICE_CODES[reg["office"]]
        state = reg.get("state") or state
        district = reg.get("district") or district
        party = party or reg.get("party") or None

    return {
        "id": str(d.get("candidate_id") or d.get("name")),
        "name": _clean_name(d.get("name")),
        "office": office,
        "party": party,
        "state": state,
        "level": level,
        "position": position,
        "district": district,
        # Vote Smart says "Running, ..." for people on the 2026 ballot; current officeholders
        # who aren't running say "Not on the 2026 ballot"
        "onBallot": not ballot_txt.startswith("Not on"),
        "positions": [(p["category"], p["question"], p["answer"]) for p in d["positions"]],
    }


def _from_npat(d):
    n = d["npat"]
    c = n["candidate"]
    positions = []
    for s in n["sections"]:
        for q in s["questions"]:
            if s["sectionName"] == "Housing/Immigration":
                cat = "Immigration" if "immigra" in q["text"].lower() else "Economy"
            else:
                cat = NPAT_SECTION_TO_VS.get(s["sectionName"])
            if cat:
                positions.append((cat, q["text"], q["answer"]))
    state = c.get("state")
    office = c.get("office", "")
    level, position = classify_office(office)
    return {
        "id": str(c.get("candidateId")),
        "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
        "office": office,
        "party": c.get("party"),
        "state": state if state and state != "US" else None,
        "level": level,
        "position": position,
        "district": c.get("district") or None,
        "positions": positions,
    }


def _registry_by_pct(folder):
    """Vote Smart id -> record from candidates.json (made by midterms.py)."""
    try:
        with open(os.path.join(folder, "candidates.json"), encoding="utf-8") as f:
            reg = json.load(f)
        return {str(r["pct_id"]): r for r in reg.get("candidates", {}).values() if r.get("pct_id")}
    except (OSError, ValueError, AttributeError):
        return {}


def _candidate_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [os.environ.get("CANDIDATES_DIR"), os.path.join(here, "..", "scraped"),
            os.path.join(here, "scraped"), here]
    return [os.path.normpath(d) for d in dirs if d]


def load_registry():
    """Every record in the first candidates.json found (made by midterms.py), or []."""
    for d in _candidate_dirs():
        try:
            with open(os.path.join(d, "candidates.json"), encoding="utf-8") as f:
                return list(json.load(f).get("candidates", {}).values())
        except (OSError, ValueError, AttributeError):
            continue
    return []


def load_candidates():
    found = []
    for d in _candidate_dirs():
        if not os.path.isdir(d):
            continue
        by_pct = _registry_by_pct(d)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and "positions" in data:
                found.append(_from_scraped(data, by_pct.get(str(data.get("candidate_id")))))
            elif isinstance(data, dict) and "npat" in data:
                found.append(_from_npat(data))
        if found:
            return found

    try:  # demo fallback: mock candidates
        import peopleTest
        for raw in (peopleTest.obama, peopleTest.trump, peopleTest.neguse, peopleTest.degette):
            found.append(_from_npat(json.loads(raw)))
    except ImportError:
        pass
    return found


def _state_abbr(value):
    if not value:
        return None
    value = value.strip()
    return value.upper() if len(value) == 2 else STATES.get(value)


# ------------------------------------------------------------------ location
CENSUS_GEO = "https://geocoding.geo.census.gov/geocoder/geographies"
_geo_cache = {}


def _dnum(value):
    """'02' / '2' / 2 -> 2.  None if there's no number."""
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits) if digits else None


def _census(endpoint, params):
    params = {**params, "benchmark": "Public_AR_Current", "vintage": "Current_Current",
              "layers": "all", "format": "json"}
    url = f"{CENSUS_GEO}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "civicmatchmaker/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def _parse_geo(data):
    matches = data.get("result", {}).get("addressMatches", [])
    if not matches:
        return None
    m = matches[0]
    info = {"matched": m.get("matchedAddress", ""), "district": None, "county": None}
    for key, rows in (m.get("geographies") or {}).items():
        if not rows:
            continue
        row = rows[0]
        if "Congressional District" in key and info["district"] is None:
            geoid = str(row.get("GEOID") or "")
            info["district"] = geoid[2:] if len(geoid) >= 4 else (row.get("BASENAME") or None)
        elif key == "Counties":
            info["county"] = row.get("NAME", "")
    return info


def geocode_address(address, city, state, zip_):
    """
    Returns (info, error). info = {"matched", "district", "county"} or None.
    Tries several query shapes, because a mismatched city name makes the Census API
    return no match even when the street + ZIP are fine.
    """
    attempts = []
    if zip_:
        attempts.append(("address", {"street": address, "zip": zip_, "state": state}))
    if city:
        attempts.append(("address", {"street": address, "city": city, "state": state}))
    one_line = ", ".join(p for p in [address, city, f"{state} {zip_}".strip()] if p)
    attempts.append(("onelineaddress", {"address": one_line}))

    last_error = "The Census geocoder found no match for that address."
    for endpoint, params in attempts:
        try:
            info = _parse_geo(_census(endpoint, params))
        except urllib.error.HTTPError as e:
            last_error = f"Census geocoder error (HTTP {e.code})."
            continue
        except Exception as e:  # noqa: BLE001  (timeout, no internet, bad JSON...)
            last_error = f"Could not reach the Census geocoder: {e}"
            continue
        if info and info["district"] is not None:
            return info, None
        if info:
            last_error = "The address matched, but no congressional district came back."
    return None, last_error


def resolve_location(data):
    """
    Works out the user's state and (if a street address was given) U.S. House district.
    A city alone can't pin a House district, because cities can span several.
    """
    state = _state_abbr(data.get("state"))
    address = (data.get("address") or "").strip()
    zip_ = (data.get("zip") or "").strip()
    city = (data.get("city") or "").strip()
    loc = {"state": state, "city": city, "district": None, "county": None,
           "addressGiven": bool(address), "geocodeError": None, "matchedAddress": None}

    if not address:
        return loc
    if not state:
        loc["geocodeError"] = "Your state wasn't recognized."
        return loc

    key = (address.lower(), city.lower(), state, zip_)
    if key not in _geo_cache:
        info, err = geocode_address(address, city, state, zip_)
        if info:                      # only cache successes, so failures retry
            _geo_cache[key] = info
        else:
            log.warning("district lookup failed for %r (%s, %s %s): %s",
                        address, city, state, zip_, err)
            print(f"[location] district lookup failed for {address!r}: {err}", flush=True)
            loc["geocodeError"] = err
            return loc

    info = _geo_cache[key]
    loc["district"] = info["district"]
    loc["county"] = info["county"]
    loc["matchedAddress"] = info["matched"]
    print(f"[location] {address!r} -> district {info['district']} ({info['matched']})", flush=True)
    return loc


def in_area(cand, loc):
    if loc["state"] and cand["state"] and cand["state"] != loc["state"]:
        return False
    if (cand["position"] == "U.S. House" and loc["district"] is not None
            and _dnum(cand["district"]) is not None):
        return _dnum(cand["district"]) == _dnum(loc["district"])
    return True


# ------------------------------------------------------------------ ballot (local races)
# FEC only knows federal candidates. Local and state races come from the Google Civic
# Information API (via elections.py), which needs a street address and a key:
#     export GOOGLE_CIVIC_API_KEY=...      (enable "Google Civic Information API")
# These candidates usually have no recorded issue positions, so they are listed
# unscored ("ballotOnly") unless a scraped Vote Smart file exists for the same person.
CIVIC_CATEGORY_TO_LEVEL = {
    "National": "Federal", "State": "State", "County": "Local",
    "Local": "Local", "Regional / special district": "Local",
}


def _name_words(s):
    return re.sub(r"[^a-z ]", "", (s or "").lower()).split()


def _same_person(a, b):
    x, y = _name_words(a), _name_words(b)
    return bool(x and y and x[-1] == y[-1] and x[0][:1] == y[0][:1])


def fetch_ballot(loc, address, city, zip_):
    """-> (contests, election_names, note). Never raises."""
    key = os.environ.get("GOOGLE_CIVIC_API_KEY")
    if not key:
        return [], [], "Local races are off: set GOOGLE_CIVIC_API_KEY on the server."
    if not address:
        return [], [], "Add a street address and ZIP to see the local races on your ballot."
    state = loc["state"]
    if not state:
        return [], [], "Your state wasn't recognized, so local races can't be loaded."
    full = ", ".join(p for p in [address, city, f"{state} {zip_}".strip()] if p)
    try:
        import elections as civic          # stdlib-only helper next to ai.py
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
            if r.get("pct_scraped") or any(_same_person(r["name"], n) for n in seen):
                continue                  # already scored from a Vote Smart file
            if r.get("pct_id") and r["pct_id"] in seen_ids:
                continue                  # same person filed twice with FEC
            seen.append(r["name"])
            seen_ids.add(r.get("pct_id"))
            office = f"{position} ({r['state']})" + (f" - District {_dnum(district)}" if district else "")
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
        label = f"{office} \u2014 {c['district']}" if c["district"] else office
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


# ------------------------------------------------------------------ Julia 1 jobs
_cache = {}
_MISS = object()


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def stance(question, answer):
    """Candidate stance in [-1, 1], or None if unknown."""
    a = (answer or "").strip()
    low = a.lower()
    if not a or "unknown" in low:
        return None
    if re.match(r"^yes\b", low):
        return 1.0
    if re.match(r"^no\b", low):
        return -1.0
    # answers to "pro-choice or pro-life?", expressed as a stance on overturning Roe v. Wade
    if re.match(r"^pro[- ]?choice\b", low):
        return -1.0
    if re.match(r"^pro[- ]?life\b", low):
        return 1.0

    def run():
        r = _predict(
            f"Question: {question}\nAnswer: {a}",
            {"s": {
                "type": "choice",
                "instructions": "What position does the candidate's answer take on the question?",
                "criteria": {
                    "supports": "The candidate supports it.",
                    "opposes": "The candidate opposes it.",
                    "mixed": "The candidate's position is mixed, conditional, or unclear.",
                },
            }},
        )["s"]["probabilities"]
        return float(r["supports"]) - float(r["opposes"])

    return _cached(("stance", question, a), run)


def route(statement, options):
    """options: [(position_index, text)]. -> (position_index, confidence) or None."""
    criteria = {f"c{i}": _short(t) for i, (_, t) in enumerate(options)}
    criteria["none"] = "None of the other options is about the same issue as the statement."

    def run():
        a = _predict(
            f"Statement: {statement}",
            {"m": {
                "type": "choice",
                "instructions": "Which option asks about the same issue as the statement?",
                "criteria": criteria,
            }},
        )["m"]
        if a["choice"] == "none":
            return None
        return options[int(a["choice"][1:])][0], float(a["max_probability"])

    return _cached(("route", statement, tuple(criteria.values())), run)


def same_issue(statement, question):
    """Second opinion: is `question` really about the same specific issue? -> probability."""
    def run():
        a = _predict(
            f"Statement: {statement}\nQuestion: {question}",
            {"v": {
                "type": "choice",
                "instructions": "Does the question ask about the same specific policy issue as the statement?",
                "criteria": {
                    "same": "Yes: the question is about the same specific policy issue, so a person's answer to the question tells you their view on the statement.",
                    "different": "No: the question is about a different policy issue, even if the broad topic is similar.",
                },
            }},
        )["v"]
        return float(a["probabilities"]["same"])

    return _cached(("same", statement, question), run)


def direction(statement, question):
    """+1 if answering yes to `question` means agreeing with `statement`, -1 if opposite."""
    def run():
        a = _predict(
            f"Statement: {statement}\nQuestion: {question}",
            {"d": {
                "type": "choice",
                "instructions": "Suppose someone answers yes to the question. How does that relate to the statement?",
                "criteria": {
                    "agree": "Saying yes to the question means agreeing with the statement.",
                    "oppose": "Saying yes to the question means disagreeing with the statement.",
                    "unrelated": "The question and the statement are about different things.",
                },
            }},
        )["d"]
        sign = {"agree": 1, "oppose": -1}.get(a["choice"])
        return None if sign is None else (sign, float(a["max_probability"]))

    return _cached(("dir", statement, question), run)


# ------------------------------------------------------------------ scoring
def score_candidate(cand, items, cancelled=None):
    pos = []   # (category, question, answer, stance)
    for cat, q, a in cand["positions"]:
        s = stance(q, a)
        if s is not None:
            pos.append((cat, q, a, s))

    by_key = {}                                  # normalized question -> index into pos
    for i, p in enumerate(pos):
        by_key.setdefault(_qkey(p[1]), i)
    raw_keys = {_qkey(q) for _, q, _ in cand["positions"]}
    raw_map = {k: True for k in raw_keys}
    # "Standard test" = most of this candidate's questions are ones the app mirrors. Candidates who took a
    # different version of the test (e.g. some Senate files) share only a couple, so for them the
    # app questions fall back to the model instead of being skipped.
    uses_pct = len(raw_keys & {_qkey(v) for v in DIRECT.values()}) >= 0.5 * max(len(raw_keys), 1)

    def model_match(it):
        """Fallback for app questions with no exact Vote Smart twin. -> (idx, p_match, d) or None."""
        cats = SECTION_TO_VS.get(it["section"])
        options = [(i, p[1]) for i, p in enumerate(pos)
                   if (cats is None or p[0] in cats) and on_topic(it["section"], p[1])][:19]
        if not options:
            return None
        try:
            routed = route(it["question"], options)
            if not routed or routed[1] < MATCH_MIN:
                return None
            idx, p_match = routed
            if same_issue(it["question"], pos[idx][1]) < SAME_MIN:
                if DEBUG:
                    print(f"[{cand['name']}] {it['id']} rejected: {pos[idx][1]!r} not the same issue")
                return None
            d = direction(it["question"], pos[idx][1])
            if not d or d[1] < DIR_MIN:
                return None
            return idx, p_match, d
        except Exception as e:  # e.g. strict-encoding overflow
            log.warning("skipped %r: %s", it["id"], e)
            return None

    pairs = []
    for it in items:
        if cancelled is not None and cancelled.is_set():
            break
        key = _qkey(DIRECT.get(it["id"], ""))
        found = _lookup(by_key, it["id"], key) if key else None
        if found is not None:
            idx, p_match, d = found, 1.0, (1, 1.0)         # the same question: no model needed
        elif key and (uses_pct or _lookup(raw_map, it["id"], key)):
            continue                                        # "Unknown", or not on their version of the test
        else:
            m = model_match(it)
            if m is None:
                continue
            idx, p_match, d = m

        _, q, a, c = pos[idx]
        s = (it["value"] - 3) / 2                      # user: -1 (oppose) .. +1 (support)
        agreement = 1 - abs(s - d[0] * c) / 2          # 1 = same side, 0 = opposite
        # strong opinions count more, and so do questions the user marked as more important
        weight = p_match * d[1] * max(abs(s), 0.25) * it.get("weight", 1.0)
        pairs.append({
            "section": it["section"], "weight": weight, "agreement": agreement,
            "importance": it.get("weight", 1.0),
            "statement": it["question"], "yourAnswer": it["value"],
            "candidateQuestion": q, "candidateAnswer": a,
        })
        if DEBUG:
            print(f"[{cand['name']}] {it['id']} ~ {q!r} -> {a!r} "
                  f"(match {p_match:.2f}, dir {d[0]:+d}@{d[1]:.2f}) agreement={agreement:.2f}")

    def pct(ps):
        w = sum(p["weight"] for p in ps)
        return round(100 * sum(p["weight"] * p["agreement"] for p in ps) / w) if w else None

    sections = {}
    for sec in {p["section"] for p in pairs}:
        sections[sec] = pct([p for p in pairs if p["section"] == sec])

    top = sorted(pairs, key=lambda p: -p["weight"])[:3]
    return {
        "score": pct(pairs),
        "coverage": len(pairs),
        "sections": sections,
        "reasons": [
            {"statement": p["statement"], "yourAnswer": p["yourAnswer"],
             "candidateQuestion": p["candidateQuestion"], "candidateAnswer": p["candidateAnswer"],
             "agreement": round(100 * p["agreement"]), "importance": p["importance"]}
            for p in top
        ],
    }


def run_match(data, emit, cancelled):
    """
    data: {"state": "Colorado", "city": "...", "address": "...", "zip": "...",
           "answers": [{"id", "section", "type", "question", "answer"}, ...]}
    """
    items = []
    for a in data.get("answers", []):
        if a.get("type") == "scale" and isinstance(a.get("answer"), (int, float)) and 1 <= a["answer"] <= 5:
            w = a.get("weight")                       # how much the user says this question matters
            w = float(w) if isinstance(w, (int, float)) and 0 <= w <= 5 else 1.0
            items.append({"id": a["id"], "section": a["section"],
                          "question": a["question"], "value": float(a["answer"]), "weight": w})
    if not items:
        raise ValueError("No scale answers were received.")

    loc = resolve_location(data)
    all_candidates = load_candidates()
    if not all_candidates:
        raise ValueError("No candidates found. Run pct_scraper.py to create candidate JSON files "
                         "(folder ../scraped or $CANDIDATES_DIR).")
    candidates = [c for c in all_candidates if in_area(c, loc)]
    if not candidates:
        raise ValueError(f"No candidates found for {data.get('city') or ''} {data.get('state') or ''}.".strip())

    emit("progress", {"stage": "start", "candidates": len(candidates), "questions": len(items)})
    out = []
    for i, cand in enumerate(candidates, 1):
        if cancelled.is_set():
            return None
        res = score_candidate(cand, items, cancelled)
        out.append({"id": cand["id"], "name": cand["name"], "office": cand["office"],
                    "party": cand["party"], "level": cand["level"],
                    "position": cand["position"], "district": cand["district"],
                    "state": cand["state"], "onBallot": cand.get("onBallot", True), **res})
        emit("progress", {"done": i, "of": len(candidates), "candidate": cand["name"]})

    out.sort(key=lambda m: (m["score"] is None, -(m["score"] or 0)))
    out += registry_candidates(loc, out)

    contests, elections_found, ballot_note = fetch_ballot(
        loc, (data.get("address") or "").strip(), (data.get("city") or "").strip(),
        (data.get("zip") or "").strip())
    extra = [b for b in ballot_candidates(contests, loc["state"])
             if not any(_same_person(b["name"], m["name"]) for m in out)]
    out += extra

    return {
        "matches": out,
        "answered": len(items),
        "location": {**loc, "districtKnown": loc["district"] is not None},
        "ballot": {"loaded": bool(contests), "note": ballot_note,
                   "elections": elections_found, "extra": len(extra),
                   "measures": ballot_measures(contests)},
    }