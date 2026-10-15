#!/usr/bin/env python3
"""
Look up the stored federal candidates for a location (or by name) and show their FEC ids,
Vote Smart ids and where the scraped PCT JSON lives. Reads ../scraped/candidates.json
(built by midterms.py) and ../scraped/index.json (built by pct_scraper.py).

Usage:
    python3 lookup.py --state CO --address "123 Main St" --city Broomfield --zip 80020
    python3 lookup.py --state CO --district 02        # no network needed
    python3 lookup.py --state CO                      # every candidate in the state
    python3 lookup.py --name neguse                   # search by name (add --state to narrow)
    python3 lookup.py --state CO --district 02 --json # machine-readable output

Only the address -> district step touches the network (Census geocoder). If a city/state
isn't enough to pin a House district (cities can span several), pass --address or --district.
Governor / state legislature / local races aren't in the registry (FEC is federal only).
"""
import argparse
import json
import os
import sys

from midterms import (FetchError, default_out_dir, geocode, load_pct_index, load_registry,
                      likely_on_ballot)

def pct_info(c: dict, index: dict, out_dir: str) -> dict:
    pid = c.get("pct_id")
    info = {"id": pid, "status": c.get("pct_status") or "not_linked_yet",
            "scraped": bool(c.get("pct_scraped"))}
    if pid and pid in index:
        e = index[pid]
        info.update({"name": e.get("name"), "last_updated": e.get("last_updated"),
                     "positions": e.get("positions"),
                     "file": os.path.abspath(os.path.join(out_dir, e.get("file", f"{pid}.json")))})
    elif pid and c.get("pct_file"):
        info["file"] = os.path.abspath(os.path.join(out_dir, c["pct_file"]))
    if c.get("pct_status") == "ambiguous":
        info["possible"] = c.get("pct_candidates", [])
    return info


def row(c: dict, index: dict, out_dir: str) -> dict:
    return {
        "name": c["name"], "party": c.get("party", ""), "state": c["state"],
        "office": "U.S. Senate" if c["office"] == "S" else "U.S. House",
        "district": c.get("district", ""), "incumbent": c.get("incumbent", ""),
        "fec_id": c["fec_id"], "fec_url": c.get("fec_url", ""),
        "vote_smart": pct_info(c, index, out_dir),
        "raised": c.get("raised", 0),
    }


def describe_pct(p: dict) -> str:
    if p["id"] and p["status"] == "linked":
        if p.get("scraped"):
            when = (p.get("last_updated") or "")[:10]
            n = f", {p['positions']} answers" if p.get("positions") else ""
            return f"Vote Smart id {p['id']} (PCT scraped {when}{n})"
        return f"Vote Smart id {p['id']} (no PCT answers on file)"
    if p["status"] == "ambiguous":
        opts = ", ".join(f"{o['id']}={o['name']}" for o in p.get("possible", [])[:3])
        return f"Vote Smart: ambiguous ({opts}); set pct_id in candidates.json"
    if p["status"] == "not_found":
        return "Vote Smart: no match found"
    return "Vote Smart: not linked yet (run: midterms.py --pct-only)"


def print_group(title: str, rows: list) -> None:
    print(f"\n== {title} ==")
    if not rows:
        print("  (none stored)")
    for r in sorted(rows, key=lambda r: (not r["incumbent"].lower().startswith("incumbent"), r["name"])):
        tag = f"  [{r['incumbent'].lower()}]" if r["incumbent"] and r["incumbent"].lower() != "challenger" else ""
        party = f" ({r['party']})" if r["party"] else ""
        print(f"  - {r['name']}{party}{tag}")
        print(f"  - {r['name']}{party}{tag}  ${r['raised']:,.0f} raised")
        print(f"      FEC {r['fec_id']}  |  {describe_pct(r['vote_smart'])}")
        if r["vote_smart"].get("file"):
            print(f"      {r['vote_smart']['file']}")


def main():
    ap = argparse.ArgumentParser(description="Look up stored candidates by location or name")
    ap.add_argument("--state", help="Two-letter state code")
    ap.add_argument("--address", help="Street address (finds your House district)")
    ap.add_argument("--city")
    ap.add_argument("--zip")
    ap.add_argument("--district", help="U.S. House district number, e.g. 2 or 02")
    ap.add_argument("--name", help="Search candidates by name (any word of the name)")
    ap.add_argument("--year", type=int, help="Election year (default: latest in the registry)")
    ap.add_argument("--json", action="store_true", help="Print JSON instead of text")
    ap.add_argument("-d", "--out-dir", help="Data folder (default: ../scraped relative to this script)")
    ap.add_argument("--min-raised", type=float, default=0, help="Hide candidates who raised less than this ($)")
    ap.add_argument("--likely-ballot", action="store_true", help="Only the top fundraiser per party per race")
    args = ap.parse_args()

    out_dir = os.path.normpath(args.out_dir) if args.out_dir else default_out_dir()
    reg = load_registry(out_dir)
    if not reg["candidates"]:
        sys.exit(f"No candidates stored in {out_dir}. Run: python3 midterms.py --all-states")
    index = load_pct_index(out_dir)

    year = args.year or reg["meta"].get("year") or max(c.get("year", 0) for c in reg["candidates"].values())
    cands = [c for c in reg["candidates"].values() if c.get("year") == year]
    state = args.state.strip().upper() if args.state else None
    if state:
        cands = [c for c in cands if c["state"] == state]

    geo, district = None, None
    result = {"year": year, "state": state, "district": None, "geography": None}

    if args.name:
        toks = args.name.lower().split()
        cands = [c for c in cands
                 if all(t in (c["name"] + " " + c.get("fec_name", "")).lower() for t in toks)]
        if args.likely_ballot:
            keep = likely_on_ballot(cands)
            cands = [c for c in cands if c["fec_id"] in keep]
        cands = [c for c in cands if (c.get("raised") or 0) >= args.min_raised]
        rows = [row(c, index, out_dir) for c in cands]
        result["candidates"] = rows
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        print(f"{len(rows)} match(es) for {args.name!r} ({year})")
        for r in sorted(rows, key=lambda r: (r["state"], r["office"], r["district"], r["name"])):
            where = r["state"] + ("" if r["office"] == "U.S. Senate" else f"-{r['district']}")
            print_group(f"{r['office']} {where}", [r])
        return

    if not state:
        ap.error("give --state (with --address/--district/--city) or --name")

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
            print("Warning: couldn't find a district for that address; showing every House race in the state.",
                  file=sys.stderr)
    elif args.city:
        print(f"Note: a city alone can't pin a House district; showing the whole state. "
              f"Pass --address or --district for {args.city}.", file=sys.stderr)

    senate = [row(c, index, out_dir) for c in cands if c["office"] == "S"]
    houses = {}
    for c in cands:
        if c["office"] == "H":
            houses.setdefault(c.get("district") or "00", []).append(row(c, index, out_dir))
    show = [district] if district else sorted(houses)

    result.update({"district": district, "geography": geo, "senate": senate,
                   "house": {d: houses.get(d, []) for d in show}})
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(f"{year} candidates for {state}" + (f", House district {district}" if district else ""))
    if geo:
        bits = [geo.get("county", ""), geo.get("state_senate", ""), geo.get("state_house", "")]
        print("Your area: " + " · ".join(b for b in bits if b))
    print_group(f"U.S. Senate ({state})", senate)
    for d in show:
        label = "at-large" if d == "00" else f"District {d}"
        print_group(f"U.S. House — {state} {label}", houses.get(d, []))
    fetched = reg["meta"].get("states", {}).get(state)
    print(f"\nRegistry last fetched for {state}: {fetched or 'never'}. "
          "Only federal races are stored (no governor/state/local).")


if __name__ == "__main__":
    main()