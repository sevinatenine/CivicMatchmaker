"""
Where to vote / drop off a ballot, from the Google Civic Information API (voterinfo).

    lookup(address, city, state, zip) -> {
        "election":  "2026 General Election" | None,
        "electionDay": "2026-11-03" | None,
        "origin":    {"lat", "lng"} | None,      # the voter's address, for sorting / the map
        "dropOff":   [place, ...],               # ballot drop boxes / drop-off sites
        "earlyVote": [place, ...],
        "polling":   [place, ...],               # Election Day polling place(s)
        "totals":    {"dropOff": n, ...},        # how many Google listed, before the limit
        "mailOnly":  bool,
        "officialUrl": str | None,               # county/state "find where to vote" page
        "officialName": str | None,
        "note":      str | None,                 # why the lists are empty, if they are
    }
    place = {"name", "address", "lat", "lng", "hours", "notes", "startDate", "endDate",
             "distanceMiles"}

Each list holds at most MAX_PER_KIND places, nearest first.

Needs GOOGLE_CIVIC_API_KEY (same key as the ballot lookup in ballot.py). Google only loads
this data close to an election, and coverage varies by county, so empty lists are normal.
"""

import json
import math
import time
import urllib.parse
import urllib.request

import config
from scraper import elections as civic

CENSUS_LOCATIONS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
FALLBACK_URL = "https://www.vote.org/polling-place-locator/"
CACHE_SECONDS = 60 * 60   # hours and sites change during early voting, so don't keep forever
MAX_PER_KIND = 10         # nearest N per list; the app shows them all on the map

_cache = {}


def _one_line(address, city, state, zip_):
    return ", ".join(p for p in [address, city, f"{state} {zip_}".strip()] if p)


def _geocode_point(full_address):
    """-> {"lat", "lng"} or None. Census geocoder, no key needed."""
    params = {"address": full_address, "benchmark": "Public_AR_Current", "format": "json"}
    req = urllib.request.Request(f"{CENSUS_LOCATIONS}?{urllib.parse.urlencode(params)}",
                                 headers={"User-Agent": "civicmatchmaker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            matches = json.load(r).get("result", {}).get("addressMatches", [])
    except Exception:  # noqa: BLE001  the map still works without the voter's own pin
        return None
    if not matches:
        return None
    c = matches[0].get("coordinates") or {}
    if c.get("x") is None or c.get("y") is None:
        return None
    return {"lat": float(c["y"]), "lng": float(c["x"])}


def _miles(a, b):
    """Great-circle distance between two {"lat", "lng"} points."""
    lat1, lat2 = math.radians(a["lat"]), math.radians(b["lat"])
    dlat = lat2 - lat1
    dlng = math.radians(b["lng"] - a["lng"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def _place(raw, origin):
    addr = raw.get("address") or {}
    street = ", ".join(p for p in [addr.get("line1"), addr.get("line2"), addr.get("line3")] if p)
    state_zip = " ".join(p for p in [addr.get("state"), addr.get("zip")] if p)
    city_line = ", ".join(p for p in [addr.get("city"), state_zip] if p)
    lat, lng = raw.get("latitude"), raw.get("longitude")
    has_point = lat is not None and lng is not None
    return {
        "name": raw.get("name") or addr.get("locationName") or street or "Voting location",
        "address": ", ".join(p for p in [street, city_line] if p),
        "lat": float(lat) if has_point else None,
        "lng": float(lng) if has_point else None,
        "hours": raw.get("pollingHours") or None,
        "notes": raw.get("notes") or None,
        "startDate": raw.get("startDate") or None,
        "endDate": raw.get("endDate") or None,
        "distanceMiles": (round(_miles(origin, {"lat": float(lat), "lng": float(lng)}), 1)
                          if origin and has_point else None),
    }


def _places(raws, origin):
    out = [_place(r, origin) for r in raws or []]
    # Nearest first; places with no coordinates go last
    out.sort(key=lambda p: (p["distanceMiles"] is None, p["distanceMiles"] or 0))
    return out[:MAX_PER_KIND]


def _admin(data):
    """The most local election office that gives a link, falling back to the state's."""
    for st in data.get("state") or []:
        for body in [(st.get("local_jurisdiction") or {}).get("electionAdministrationBody"),
                     st.get("electionAdministrationBody")]:
            body = body or {}
            url = (body.get("votingLocationFinderUrl") or body.get("electionInfoUrl")
                   or body.get("absenteeVotingInfoUrl"))
            if url:
                return url, body.get("name") or None
    return None, None


def _empty(note, origin=None):
    return {"election": None, "electionDay": None, "origin": origin, "dropOff": [],
            "earlyVote": [], "polling": [], "mailOnly": False,
            "totals": {"dropOff": 0, "earlyVote": 0, "polling": 0},
            "officialUrl": FALLBACK_URL, "officialName": None, "note": note}


def lookup(address, city, state, zip_):
    """Never raises; problems come back in "note"."""
    key = config.GOOGLE_CIVIC_API_KEY
    if not key:
        return _empty("Voting locations are off: set GOOGLE_CIVIC_API_KEY on the server.")
    if not address or not state:
        return _empty("Enter your street address to find places to vote near you.")

    full = _one_line(address, city, state, zip_)
    cache_key = full.lower()
    hit = _cache.get(cache_key)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]

    origin = _geocode_point(full)
    try:
        upcoming = civic.upcoming_elections(key, state)[:3]
        if not upcoming:
            return _empty(f"Google doesn't list an upcoming election for {state}.", origin)

        result = None
        for e in upcoming:
            try:
                data = civic.api_get("/voterinfo", {"key": key, "address": full,
                                                    "electionId": e["id"]})
            except civic.ApiError as err:
                print(f"[voting places] skipped {e.get('name')}: {err}", flush=True)
                continue
            url, office = _admin(data)
            found = {
                "election": e.get("name"), "electionDay": e.get("electionDay"),
                "origin": origin,
                "dropOff": _places(data.get("dropOffLocations"), origin),
                "earlyVote": _places(data.get("earlyVoteSites"), origin),
                "polling": _places(data.get("pollingLocations"), origin),
                "mailOnly": bool(data.get("mailOnly")),
                "totals": {"dropOff": len(data.get("dropOffLocations") or []),
                           "earlyVote": len(data.get("earlyVoteSites") or []),
                           "polling": len(data.get("pollingLocations") or [])},
                "officialUrl": url or FALLBACK_URL, "officialName": office, "note": None,
            }
            if found["dropOff"] or found["earlyVote"] or found["polling"]:
                result = found
                break
            result = result or found   # keep the official link even if no sites came back
    except (Exception, SystemExit) as err:  # noqa: BLE001  api_get() sys.exit()s on network errors
        print(f"[voting places] failed: {err}", flush=True)
        return _empty(f"Could not load voting locations: {err}", origin)

    if result is None:
        return _empty("Google couldn't find that address. Check the street and ZIP.", origin)
    if not (result["dropOff"] or result["earlyVote"] or result["polling"]):
        result["note"] = ("Google doesn't have voting locations for this address yet. Coverage "
                          "varies by county, so check your election office's website.")
    _cache[cache_key] = (time.time(), result)
    print(f"[voting places] {full!r}: {len(result['dropOff'])} drop-off, "
          f"{len(result['earlyVote'])} early, {len(result['polling'])} polling", flush=True)
    return result
