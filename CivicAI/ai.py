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

Candidates are loaded from JSON files made by pct_scraper.py (folder ../scraped,
or $CANDIDATES_DIR). With no files, the mock candidates in peopleTest.py are used.

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


# ------------------------------------------------------------------ candidates
def _from_scraped(d):
    st = re.search(r"\(([A-Z]{2})\)", d.get("office", ""))
    party = re.search(r"Running,\s*(.+?)\s+for\b", d.get("on_the_ballot", ""))
    return {
        "id": str(d.get("candidate_id") or d.get("name")),
        "name": d.get("name", "Unknown"),
        "office": d.get("office", ""),
        "party": party.group(1) if party else None,
        "state": st.group(1) if st else None,
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
    return {
        "id": str(c.get("candidateId")),
        "name": f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
        "office": c.get("office", ""),
        "party": c.get("party"),
        "state": state if state and state != "US" else None,
        "positions": positions,
    }


def load_candidates():
    here = os.path.dirname(os.path.abspath(__file__))
    dirs = [os.environ.get("CANDIDATES_DIR"), os.path.join(here, "..", "scraped"),
            os.path.join(here, "scraped"), here]
    found = []
    for d in filter(None, dirs):
        d = os.path.normpath(d)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fn), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and "positions" in data:
                found.append(_from_scraped(data))
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
    data: {"state": "Colorado", "city": "...",
           "answers": [{"id", "section", "type", "question", "answer"}, ...]}
    """
    items = []
    for a in data.get("answers", []):
        if a.get("type") == "scale" and isinstance(a.get("answer"), (int, float)) and 1 <= a["answer"] <= 5:
            items.append({"id": a["id"], "section": a["section"],
                          "question": a["question"], "value": float(a["answer"])})
    if not items:
        raise ValueError("No scale answers were received.")

    st = _state_abbr(data.get("state"))
    candidates = [c for c in load_candidates() if not st or not c["state"] or c["state"] == st]
    if not candidates:
        raise ValueError("No candidates found. Run pct_scraper.py to create candidate JSON files "
                         "(folder ../scraped or $CANDIDATES_DIR).")

    emit("progress", {"stage": "start", "candidates": len(candidates), "questions": len(items)})
    out = []
    for i, cand in enumerate(candidates, 1):
        if cancelled.is_set():
            return None
        res = score_candidate(cand, items, cancelled)
        out.append({"id": cand["id"], "name": cand["name"], "office": cand["office"],
                    "party": cand["party"], **res})
        emit("progress", {"done": i, "of": len(candidates), "candidate": cand["name"]})

    out.sort(key=lambda m: (m["score"] is None, -(m["score"] or 0)))
    return {"matches": out, "answered": len(items)}