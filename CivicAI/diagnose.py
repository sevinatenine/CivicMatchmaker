"""
Shows why a candidate has few matching positions.

    python diagnose.py hickenlooper
    CANDIDATES_DIR=/path/to/scraped python diagnose.py "john hickenlooper"

For every app question it prints one of:
    MATCH     the candidate answered Yes/No to the exact Vote Smart question
    unknown   Vote Smart asked them but has no answer ("Unknown Position")
    other     answered, but not a plain Yes/No (e.g. free text), which needs the model
    not asked their file does not contain that question at all
"""
import re
import sys

import matcher
from candidates import load_candidates


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python diagnose.py <part of a candidate's name>")
    words = sys.argv[1].lower().split()
    hits = [c for c in load_candidates() if all(w in c["name"].lower() for w in words)]
    if not hits:
        names = ", ".join(sorted(c["name"] for c in load_candidates())[:25])
        sys.exit(f"No candidate matches {sys.argv[1]!r}. Loaded: {names}")

    for c in hits:
        by = {matcher.qkey(q): a for _, q, a in c["positions"]}
        asked = sum(1 for k in by if k in {matcher.qkey(v) for v in matcher.DIRECT.values()})
        print(f"\n{c['name']}  |  {c['office']}  |  {c['level']} / {c['position']}  |  state={c['state']} district={c['district']}")
        print(f"file has {len(c['positions'])} questions; {asked} of them are in the app's question set\n")
        matched = 0
        for qid, vs_q in matcher.DIRECT.items():
            a = matcher.lookup(by, qid, matcher.qkey(vs_q))
            low = (a or "").strip().lower()
            if a is None:
                status = "not asked"
            elif not low or "unknown" in low:
                status = "unknown"
            elif re.match(r"^(yes|no)\b", low):
                status, matched = f"MATCH ({a})", matched + 1
            else:
                status = f"other ({a[:40]})"
            print(f"  {qid:<24} {status}")
        print(f"\n=> {matched} of {len(matcher.DIRECT)} app questions can be scored directly")
        mirrored = {matcher.qkey(v) for v in matcher.DIRECT.values()}
        standard = asked >= 0.5 * max(len(c["positions"]), 1)
        print("=> " + ("Standard Vote Smart test: unanswered questions are skipped."
                       if standard else
                       "Different version of the test: app questions fall back to the model (strict)."))
        others = [(cat, q, a) for cat, q, a in c["positions"] if matcher.qkey(q) not in mirrored]
        if others:
            print(f"\nQuestions in this file that the app does NOT ask ({len(others)}):")
            for cat, q, a in others:
                print(f"     [{cat[:18]}] {q[:100]}  -> {a[:28]}")


if __name__ == "__main__":
    main()