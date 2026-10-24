"""
Where the user votes.

The app sends {"state", "city", optional "address", optional "zip"}.
  * state       -> only candidates for that state (plus national ones, e.g. President)
  * address+zip -> the Census geocoder finds the U.S. House district, and House
                   candidates from other districts are dropped
A city alone can't pin a House district, because cities can span several.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("location")

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


def state_abbr(value):
    if not value:
        return None
    value = value.strip()
    return value.upper() if len(value) == 2 else STATES.get(value)


def dnum(value):
    """'02' / '2' / 2 -> 2.  None if there's no number."""
    digits = re.sub(r"\D", "", str(value or ""))
    return int(digits) if digits else None


# ------------------------------------------------------------------ Census geocoder
CENSUS_GEO = "https://geocoding.geo.census.gov/geocoder/geographies"
CENSUS_TIMEOUT = 10   # seconds per request; the Census API sometimes stalls
CENSUS_TRIES = 2      # per query shape, so one stall doesn't fail the lookup
_geo_cache = {}


def _census(endpoint, params, layers="54,82"):
    """layers: 54 = current Congressional Districts, 82 = Counties (much smaller than "all")."""
    params = {**params, "benchmark": "Public_AR_Current", "vintage": "Current_Current",
              "layers": layers, "format": "json"}
    url = f"{CENSUS_GEO}/{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "civicmatchmaker/1.0"})
    last = None
    for _ in range(CENSUS_TRIES):
        try:
            with urllib.request.urlopen(req, timeout=CENSUS_TIMEOUT) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500:
                raise
            last = e
        except (TimeoutError, urllib.error.URLError, OSError) as e:
            last = e
    raise last


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
            if info and info["district"] is None:   # layer IDs moved? fall back to everything
                info = _parse_geo(_census(endpoint, params, layers="all")) or info
        except urllib.error.HTTPError as e:
            last_error = f"Census geocoder error (HTTP {e.code})."
            continue
        except Exception as e:  # noqa: BLE001  (timeout, no internet, bad JSON...)
            last_error = f"Could not reach the Census geocoder: {e}"
            break                     # a network problem won't be fixed by rephrasing the address
        if info and info["district"] is not None:
            return info, None
        if info:
            last_error = "The address matched, but no congressional district came back."
    return None, last_error


def resolve_location(data):
    """Works out the user's state and (if a street address was given) U.S. House district."""
    state = state_abbr(data.get("state"))
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
            and dnum(cand["district"]) is not None):
        return dnum(cand["district"]) == dnum(loc["district"])
    return True
