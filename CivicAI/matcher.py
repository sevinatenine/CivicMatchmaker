"""
CivicMatchmaker matching engine.

A decision model (Julia 1 locally, or Microsoft-Decision-1 / Jev 1.14 through OpenRouter,
see llm.py) is a classifier, not a reasoner, so it only gets jobs it is built for:

  1. ROUTE      which of the candidate's recorded positions is about the same
                issue as an app question?            (choice among 2-20 options)
  2. DIRECTION  if the candidate says "yes" to that position, is that the same
                side as the app statement or the opposite side? (3-way choice)
  3. STANCE     for free-text candidate answers ("Yes, with conditions"),
                supports / opposes / mixed.           (3-way choice)

Most app questions mirror a Vote Smart question exactly (DIRECT below) and need no model.
The arithmetic (user's 1-5 answer vs candidate stance) is plain code.
Only the app's SCALE questions are scored; choice ("which should be prioritized")
questions have no support/oppose direction, so they are ignored for now.
"""

import logging
import re

import config
import llm
from ballot import ballot_candidates, ballot_measures, fetch_ballot, registry_candidates, same_person
from candidates import load_candidates
from location import in_area, resolve_location

log = logging.getLogger("matcher")

DEBUG = config.DEBUG
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


def qkey(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def lookup(d, qid, key):
    """d: {normalized question: value}. Exact question first, then known alternate wordings."""
    if key and key in d:
        return d[key]
    for prefix in ALIASES.get(qid, ()):
        for k, v in d.items():
            if k.startswith(prefix):
                return v
    return None


# ------------------------------------------------------------------ decision model jobs
_cache = {}


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def _short(text, n=OPTION_CHARS):
    return text if len(text) <= n else text[: n - 1] + "…"


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
        r = llm.predict(
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
        a = llm.predict(
            f"Statement: {statement}",
            {"m": {
                "type": "choice",
                "instructions": "Which option asks about the same issue as the statement?",
                "criteria": criteria,
            }},
        )["m"]
        if a["choice"] == "none":
            return None
        return int(a["choice"][1:]), float(a["max_probability"])

    # Cache the option number, not the position index: candidates with the same option texts
    # store those positions at different indexes.
    picked = _cached(("route", statement, tuple(criteria.values())), run)
    return None if picked is None else (options[picked[0]][0], picked[1])


def same_issue(statement, question):
    """Second opinion: is `question` really about the same specific issue? -> probability."""
    def run():
        a = llm.predict(
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
        a = llm.predict(
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
        by_key.setdefault(qkey(p[1]), i)
    raw_keys = {qkey(q) for _, q, _ in cand["positions"]}
    raw_map = {k: True for k in raw_keys}
    # "Standard test" = most of this candidate's questions are ones the app mirrors. Candidates who took a
    # different version of the test (e.g. some Senate files) share only a couple, so for them the
    # app questions fall back to the model instead of being skipped.
    uses_pct = len(raw_keys & {qkey(v) for v in DIRECT.values()}) >= 0.5 * max(len(raw_keys), 1)

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
        except Exception as e:  # e.g. strict-encoding overflow, or an OpenRouter error
            log.warning("skipped %r: %s", it["id"], e)
            return None

    pairs = []
    for it in items:
        if cancelled is not None and cancelled.is_set():
            break
        key = qkey(DIRECT.get(it["id"], ""))
        found = lookup(by_key, it["id"], key) if key else None
        if found is not None:
            idx, p_match, d = found, 1.0, (1, 1.0)         # the same question: no model needed
        elif key and (uses_pct or lookup(raw_map, it["id"], key)):
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
        raise ValueError("No candidates found. Run scraper/pct_scraper.py to create candidate "
                         "JSON files (folder CivicAI/scraped or $CANDIDATES_DIR).")
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
             if not any(same_person(b["name"], m["name"]) for m in out)]
    out += extra

    return {
        "matches": out,
        "answered": len(items),
        "location": {**loc, "districtKnown": loc["district"] is not None},
        "ballot": {"loaded": bool(contests), "note": ballot_note,
                   "elections": elections_found, "extra": len(extra),
                   "measures": ballot_measures(contests)},
    }
