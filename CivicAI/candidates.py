"""
Candidate data.

Candidates are loaded from the JSON files pct_scraper.py writes to CANDIDATES_DIR
(default CivicAI/scraped). If candidates.json (made by scraper/midterms.py) sits in the same
folder, it supplies the exact office + district. With no files, the mock candidates in
sample_candidates.py are used.

Each candidate carries a `level` (Federal / State / Local / Other) and a `position`
(U.S. Senate, U.S. House, Governor, ...) so the app can filter.

Files are read once and kept in memory; restart the server after re-scraping.
"""

import functools
import json
import os
import re

import config

# FEC office code (from midterms.py's candidates.json) -> (level, position)
OFFICE_CODES = {
    "S": ("Federal", "U.S. Senate"),
    "H": ("Federal", "U.S. House"),
    "P": ("Federal", "President"),
}

# sample_candidates.py (NPAT) section name -> Vote Smart category
NPAT_SECTION_TO_VS = {
    "Budget/Economy": "Economy",
    "Taxes": "Budget, Spending, and Taxes",
    "Education": "Education",
    "Environment": "Energy & Environment",
    "Healthcare": "Health Care",
}


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


# ------------------------------------------------------------------ file formats
def _clean_name(name):
    """'Shawn Harris' Issue Positions (Political Courage Test)' -> 'Shawn Harris'."""
    return re.sub(r"[’']s?\s+Issue Positions.*$", "", name or "").strip() or "Unknown"


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


# ------------------------------------------------------------------ loading
@functools.lru_cache(maxsize=1)
def load_registry():
    """Every record in candidates.json (made by midterms.py), or []."""
    try:
        with open(os.path.join(config.CANDIDATES_DIR, "candidates.json"), encoding="utf-8") as f:
            return list(json.load(f).get("candidates", {}).values())
    except (OSError, ValueError, AttributeError):
        return []


@functools.lru_cache(maxsize=1)
def load_candidates():
    """Every candidate with recorded positions. Callers must not modify the result."""
    found = []
    folder = config.CANDIDATES_DIR
    if os.path.isdir(folder):
        by_pct = {str(r["pct_id"]): r for r in load_registry() if r.get("pct_id")}
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(folder, fn), encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and "positions" in data:
                found.append(_from_scraped(data, by_pct.get(str(data.get("candidate_id")))))
            elif isinstance(data, dict) and "npat" in data:
                found.append(_from_npat(data))
    if found:
        return found

    import sample_candidates   # demo fallback: mock candidates
    return [_from_npat(json.loads(raw)) for raw in sample_candidates.ALL]
