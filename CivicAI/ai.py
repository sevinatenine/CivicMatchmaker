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

log = logging.getLogger("ai")

MODEL_DIR = os.environ.get("JULIA_MODEL_DIR", "Julia-1")
DEVICE = os.environ.get("JULIA_DEVICE", "cpu")
DEBUG = os.environ.get("JULIA_DEBUG") == "1"

MATCH_MIN = 0.5      # minimum confidence that a position is about the same issue
DIR_MIN = 0.6        # minimum confidence in the same-side / opposite-side call
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
}

# peopleTest.py (NPAT) section name -> Vote Smart category
NPAT_SECTION_TO_VS = {
    "Budget/Economy": "Economy",
    "Taxes": "Budget, Spending, and Taxes",
    "Education": "Education",
    "Environment": "Energy & Environment",
    "Healthcare": "Health Care",
}

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
def _from_scraped(d, reg=None):
    """d: a pct_scraper JSON file. reg: matching record from candidates.json (optional)."""
    office = d.get("office", "")
    st = re.search(r"\(([A-Z]{2})\)", office)
    party_m = re.search(r"Running,\s*(.+?)\s+for\b", d.get("on_the_ballot", ""))
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
        "name": d.get("name", "Unknown"),
        "office": office,
        "party": party,
        "state": state,
        "level": level,
        "position": position,
        "district": district,
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


def load_candidates():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [os.environ.get("CANDIDATES_DIR"), os.path.join(here, "..", "scraped"),
            os.path.join(here, "scraped"), here]
    found = []
    for d in filter(None, dirs):
        d = os.path.normpath(d)
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
_geo_cache = {}


def _dnum(value):
    """'02' / '2' / 2 -> 2.  None if there's no number."""
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits) if digits else None


def resolve_location(data):
    """
    Works out the user's state and (if a street address was given) U.S. House district.
    A city alone can't pin a House district, because cities can span several.
    """
    state = _state_abbr(data.get("state"))
    address = (data.get("address") or "").strip()
    zip_ = (data.get("zip") or "").strip()
    city = (data.get("city") or "").strip()
    district, county = None, None

    if state and address:
        key = (address.lower(), city.lower(), state, zip_)
        if key not in _geo_cache:
            try:
                from midterms import geocode   # Census geocoder, stdlib only
                _geo_cache[key] = geocode(address, city or None, state, zip_ or None)
            except Exception as e:  # noqa: BLE001  (network error, no match...)
                log.warning("geocode failed for %r: %s", address, e)
                return {"state": state, "city": city, "district": None, "county": None}
        geo = _geo_cache[key]
        if geo:
            district = geo.get("congressional_district")
            county = geo.get("county")

    return {"state": state, "city": city, "district": district, "county": county}


def in_area(cand, loc):
    if loc["state"] and cand["state"] and cand["state"] != loc["state"]:
        return False
    if (cand["position"] == "U.S. House" and loc["district"] is not None
            and _dnum(cand["district"]) is not None):
        return _dnum(cand["district"]) == _dnum(loc["district"])
    return True


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

    pairs = []
    for it in items:
        if cancelled is not None and cancelled.is_set():
            break
        cats = SECTION_TO_VS.get(it["section"])
        options = [(i, p[1]) for i, p in enumerate(pos) if cats is None or p[0] in cats][:19]
        if not options:
            continue
        try:
            routed = route(it["question"], options)
            if not routed or routed[1] < MATCH_MIN:
                continue
            idx, p_match = routed
            d = direction(it["question"], pos[idx][1])
            if not d or d[1] < DIR_MIN:
                continue
        except Exception as e:  # e.g. strict-encoding overflow
            log.warning("skipped %r: %s", it["id"], e)
            continue

        _, q, a, c = pos[idx]
        s = (it["value"] - 3) / 2                      # user: -1 (oppose) .. +1 (support)
        agreement = 1 - abs(s - d[0] * c) / 2          # 1 = same side, 0 = opposite
        weight = p_match * d[1] * max(abs(s), 0.25)    # strong opinions count more
        pairs.append({
            "section": it["section"], "weight": weight, "agreement": agreement,
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
             "agreement": round(100 * p["agreement"])}
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
            items.append({"id": a["id"], "section": a["section"],
                          "question": a["question"], "value": float(a["answer"])})
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
                    "state": cand["state"], **res})
        emit("progress", {"done": i, "of": len(candidates), "candidate": cand["name"]})

    out.sort(key=lambda m: (m["score"] is None, -(m["score"] or 0)))
    return {
        "matches": out,
        "answered": len(items),
        "location": {**loc, "districtKnown": loc["district"] is not None},
    }