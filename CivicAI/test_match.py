"""
Run the matcher without the server or the app:

    JULIA_DEBUG=1 python test_match.py

Uses the same payload shape the app sends. The fake user is progressive
(supports taxing high earners, renewables, public healthcare, easier voting,
legal immigration pathways; opposes expanding fossil fuels).
"""
import threading

import ai

ANSWERS = [
    ("higher-income-taxes", "Taxes & Government Spending",
     "The U.S. federal government should increase taxes on higher-income households to fund public programs.", 5),
    ("renewable-transition", "Environment & Energy",
     "The U.S. federal government should accelerate its transition toward renewable energy, even if it increases short-term costs.", 5),
    ("energy-costs-fossil", "Environment & Energy",
     "The U.S. federal government should prioritize reducing energy costs even if that means expanding the use of fossil fuels.", 1),
    ("healthcare-affordability", "Healthcare",
     "The government should expand programs that help people afford healthcare, even if government spending increases.", 5),
    ("easier-voting", "Democracy & Voting",
     "Voting should be made easier through measures such as expanded early voting and easier voter registration.", 5),
    ("legal-pathways", "Immigration",
     "The United States should expand legal pathways for immigrants to enter the country and work legally.", 5),
    ("college-aid", "Young People & College",
     "The government should provide more financial assistance to make college and vocational education more affordable.", 5),
]

payload = {
    "state": "Colorado",
    "city": "Boulder",
    "answers": [
        {"id": i, "section": s, "type": "scale", "question": q, "answer": v}
        for i, s, q, v in ANSWERS
    ],
}

if __name__ == "__main__":
    result = ai.run_match(payload, lambda e, p: print(e, p), threading.Event())
    print()
    for m in result["matches"]:
        score = "n/a" if m["score"] is None else f"{m['score']}%"
        print(f"{m['name']:<22} {score:>5}   ({m['coverage']} positions matched)  {m['office']}")
        for r in m["reasons"]:
            print(f"    - answered {r['candidateAnswer']!r} to: {r['candidateQuestion']}  [{r['agreement']}% agreement]")