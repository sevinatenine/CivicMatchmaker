#!/usr/bin/env python3
"""
Scrape a Vote Smart "Political Courage Test" (Issue Positions) page.

Usage:
    python pct_scraper.py https://justfacts.votesmart.org/candidate/political-courage-test/151075/joe-neguse \
        --cookie-file cookie.txt
    python pct_scraper.py "joe neguse" --cookie-file cookie.txt   # name: local index first, then Vote Smart search
    python pct_scraper.py "mike bare" --pick 2 --cookie-file cookie.txt
    python pct_scraper.py 151075 --cookie-file cookie.txt          # by candidate id
    python pct_scraper.py saved_page.html                          # parse a locally saved copy

    python pct_scraper.py --lookup neguse     # search the local index (no network)
    python pct_scraper.py --list              # show everything in the local index

Output goes to ../scraped/<candidate_id>.json (relative to this script), and every
scrape is recorded in ../scraped/index.json (id, name, office, url, last_updated).
Use -d DIR to change the folder, --csv to also write a CSV.

cookie.txt should contain just the value of the browser's Cookie request header
(one line). Keep it out of git and never share it: it is your logged-in session.

Requires: pip install curl_cffi beautifulsoup4
"""
import argparse
import csv
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import quote

from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; pct-scraper/1.0; personal research)"}


BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36")


BASE = "https://justfacts.votesmart.org"

INDEX_FILE = "index.json"


# --------------------------------------------------------------------------- #
# Local index: candidate_id -> {name, office, url, last_updated, ...}
# --------------------------------------------------------------------------- #
def default_out_dir() -> str:
    return os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scraped"))


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_index(out_dir: str) -> dict:
    path = os.path.join(out_dir, INDEX_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        backup = path + ".bak"
        os.replace(path, backup)
        print(f"Warning: {path} was unreadable; moved it to {backup} and starting fresh.",
              file=sys.stderr)
        return {}


def save_index(out_dir: str, index: dict) -> None:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, INDEX_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)  # atomic, so a crash can't leave a half-written index


def update_index(out_dir: str, data: dict) -> dict:
    """Record/refresh this candidate in the index and return the entry."""
    index = load_index(out_dir)
    cid = data["candidate_id"]
    prev = index.get(cid, {})
    entry = {
        "name": data.get("name", ""),
        "office": data.get("office", ""),
        "on_the_ballot": data.get("on_the_ballot", ""),
        "test_year": data.get("test_year", ""),
        "positions": len(data.get("positions", [])),
        "url": data.get("source", ""),
        "file": f"{cid}.json",
        "first_scraped": prev.get("first_scraped", data["scraped_at"]),
        "last_updated": data["scraped_at"],
    }
    index[cid] = entry
    save_index(out_dir, index)
    return entry


def find_in_index(index: dict, query: str) -> list:
    """Match by exact id, or by every word of the query appearing in the name."""
    q = query.strip().lower()
    if q in index:
        return [(q, index[q])]
    tokens = q.split()
    if not tokens:
        return []
    hits = [(cid, e) for cid, e in index.items()
            if all(t in e.get("name", "").lower() for t in tokens)]
    return sorted(hits, key=lambda h: h[1].get("name", ""))


def print_entries(entries: list) -> None:
    if not entries:
        print("No matches in the local index.")
        return
    for cid, e in entries:
        print(f"{cid:>8}  {e.get('name', '?'):<28} {e.get('office', '')[:40]:<40} "
              f"updated {e.get('last_updated', '?')}")


# --------------------------------------------------------------------------- #
# Fetching / parsing
# --------------------------------------------------------------------------- #
def fetch(url: str, cookie: str = None, user_agent: str = None, accept: str = None):
    """GET a URL with a Chrome-like TLS fingerprint + the user's cookie. Returns the response."""
    try:
        # Cloudflare fingerprints the TLS handshake; plain `requests` is flagged as a bot.
        # curl_cffi reproduces Chrome's handshake. Install: pip install curl_cffi
        from curl_cffi import requests
        impersonate = {"impersonate": "chrome"}
    except ImportError:
        import requests
        impersonate = {}
        print("Tip: pip install curl_cffi  (plain requests is usually blocked with a 403)",
              file=sys.stderr)
    headers = {
        "User-Agent": user_agent or BROWSER_UA,
        "Accept": accept or "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BASE + "/",
    }
    if cookie:
        headers["Cookie"] = cookie.strip()
    resp = requests.get(url, headers=headers, timeout=30, **impersonate)
    if resp.status_code in (403, 429, 503):
        cf = "cloudflare" in resp.headers.get("server", "").lower() or "cf-ray" in resp.headers
        sys.exit(
            f"HTTP {resp.status_code} from the server" + (" (Cloudflare challenge)" if cf else "") + ".\n"
            "Try: (1) pip install curl_cffi, (2) re-copy a FRESH cookie from the browser "
            "(cf_clearance and access_token expire quickly), (3) run from the same network as "
            "the browser, or (4) save the page from the browser and pass the .html file."
        )
    resp.raise_for_status()
    return resp


def login_wall(text: str) -> bool:
    return "loginFormPageLimitModal" in text and "Issue Positions" not in text


def load_html(source: str, cookie: str = None, user_agent: str = None) -> str:
    if os.path.exists(source):
        with open(source, encoding="utf-8") as f:
            return f.read()
    text = fetch(source, cookie, user_agent).text
    if login_wall(text):
        print("Warning: got the login/view-limit page. Your cookie may be missing or expired.",
              file=sys.stderr)
    return text


def search_candidates(name: str, cookie: str = None, user_agent: str = None) -> list:
    """Raw Vote Smart name search (/x/search?s=<name>). Returns the list of result dicts."""
    url = f"{BASE}/x/search?s={quote(name)}"
    resp = fetch(url, cookie, user_agent, accept="application/json, text/plain, */*")
    try:
        return resp.json().get("results", [])
    except ValueError:
        raise RuntimeError("Search did not return JSON (login page or Cloudflare challenge?). "
                           "Check your cookie.")


def search_candidate(name: str, cookie: str = None, user_agent: str = None, pick: int = 0) -> dict:
    """Look a name up and return the pick-th result (default: first). Exits if none."""
    try:
        results = search_candidates(name, cookie, user_agent)
    except RuntimeError as e:
        sys.exit(str(e))
    if not results:
        sys.exit(f"No candidates found for {name!r}.")

    def label(r):
        return (f"{r['name']} ({r.get('party') or '?'}, {r.get('office') or '?'} "
                f"{r.get('state_id') or ''} {r.get('district') or ''}".strip() + f") id={r['candidate_id']}")

    print(f"{len(results)} result(s) for {name!r}; top matches:", file=sys.stderr)
    for i, r in enumerate(results[:5]):
        print(f"  {'->' if i == pick else '  '} [{i}] {label(r)}", file=sys.stderr)
    if pick >= len(results):
        sys.exit(f"--pick {pick} is out of range ({len(results)} results).")
    return results[pick]


def pct_url(candidate_id, name: str = "") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{BASE}/candidate/political-courage-test/{candidate_id}/{slug}".rstrip("/")


def clean(text: str) -> str:
    # The site double-escapes some entities (e.g. "&amp;amp;"), so unescape twice
    text = html.unescape(html.unescape(text or ""))
    return re.sub(r"\s+", " ", text).strip()


def position_type(icon) -> str:
    """Map the icon in the row to Vote Smart's key."""
    classes = icon.get("class", []) if icon else []
    if "fa-adjust" in classes:
        return "inferred"          # Vote Smart inferred it from public record
    if "fa-circle" in classes:
        return "unknown" if "far" in classes else "official"  # far = hollow circle
    return "unknown"


def evidence_type(text: str) -> str:
    t = text.lower()
    if t.startswith("voted"):
        return "vote"
    if t.startswith("rated"):
        return "rating"
    return "statement"


def parse_header(soup: BeautifulSoup) -> dict:
    info = {}
    title = soup.select_one("h2.card-title")
    if title:
        t = clean(title.get_text())
        info["name"] = re.sub(r"[’']s?\s+Issue Positions.*$", "", t)
        info["page_title"] = t

    # Office + ballot status
    office = soup.select_one(".candidate-header-text ul li span")
    if office:
        info["office"] = clean(office.get_text())
    for p in soup.select("p.card-text"):
        if "On The Ballot" in p.get_text():
            info["on_the_ballot"] = clean(p.get_text().replace("On The Ballot:", ""))

    # Candidate id from the image/URL if present
    img = soup.select_one("#candidateHeaderCandidateImage")
    if img and img.get("src"):
        m = re.search(r"/(\d+)\.jpg", img["src"])
        if m:
            info["candidate_id"] = m.group(1)

    note = soup.find(string=re.compile(r"These issue\s+positions are from"))
    if note:
        m = re.search(r"from (\d{4})", clean(note))
        if m:
            info["test_year"] = m.group(1)
    return info


def parse_positions(soup: BeautifulSoup) -> list:
    results = []
    accordion = soup.select_one("#accordion")
    if not accordion:
        return results

    for card in accordion.select("div.card.card-plain"):
        header = card.select_one(".card-header")
        if not header:
            continue

        # Answer + icon (page repeats them for mobile layout; take the first of each)
        answer_el = header.select_one(".pct-accordion-assigned-item-pre-break")
        answer = clean(answer_el.get_text()) if answer_el else ""
        icon = header.select_one(".pct-accordion-assigned-item-pre-break i")

        # Category + question
        q_el = header.select_one("div.col-lg-8")
        category, question = "", ""
        if q_el:
            b = q_el.find("b")
            category = clean(b.get_text()) if b else ""
            full = clean(q_el.get_text())
            question = full[len(category):].lstrip(" :") if category else full

        # Supporting evidence
        evidence = []
        for li in card.select(".collapse ul li"):
            link = li.find("a")
            source_url = link.get("href") if link else None
            source_name = clean(link.get_text()) if link else None
            if link:
                link.extract()
            text = clean(li.get_text()).rstrip("() ").strip()
            if not text:
                continue
            evidence.append({
                "type": evidence_type(text),
                "text": text,
                "source": source_name,
                "url": source_url,
            })

        results.append({
            "category": category,
            "question": question,
            "answer": answer,
            "position_type": position_type(icon),
            "evidence": evidence,
        })
    return results


def scrape(source: str, cookie: str = None, user_agent: str = None) -> dict:
    text = load_html(source, cookie, user_agent)
    soup = BeautifulSoup(text, "html.parser")
    data = parse_header(soup)
    data["source"] = source
    data["positions"] = parse_positions(soup)
    data["_login_wall"] = login_wall(text)   # internal flag; never written to disk
    return data


def save_scrape(data: dict, out_dir: str, source: str = "", make_csv: bool = False):
    """Write <id>.json (+ optional CSV) and update index.json. Returns (cid, json_path, index_entry)."""
    cid = data.get("candidate_id")
    if not cid:
        m = re.search(r"/political-courage-test/(\d+)", source or data.get("source", ""))
        cid = m.group(1) if m else "unknown"
    data["candidate_id"] = cid
    data["scraped_at"] = now_iso()
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{cid}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in data.items() if not k.startswith("_")},
                  f, indent=2, ensure_ascii=False)
    entry = update_index(out_dir, data) if cid != "unknown" else None
    if make_csv:
        write_csv(data, os.path.join(out_dir, f"{cid}.csv"))
    return cid, json_path, entry


def write_csv(data: dict, path: str) -> None:
    """One row per piece of evidence (or one row for questions with none)."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "question", "answer", "position_type",
                    "evidence_type", "evidence_text", "evidence_source", "evidence_url"])
        for p in data["positions"]:
            base = [p["category"], p["question"], p["answer"], p["position_type"]]
            if not p["evidence"]:
                w.writerow(base + ["", "", "", ""])
            for e in p["evidence"]:
                w.writerow(base + [e["type"], e["text"], e["source"], e["url"]])


def main():
    ap = argparse.ArgumentParser(description="Scrape a Vote Smart Political Courage Test page")
    ap.add_argument("source", nargs="?",
                    help="A candidate NAME (checks the local index, then searches Vote Smart), "
                         "a numeric candidate ID, a page URL, or a path to a saved .html file")
    ap.add_argument("--pick", type=int, default=0,
                    help="When searching by name, use this result index instead of the first "
                         "(skips the local index)")
    ap.add_argument("--online", action="store_true",
                    help="Force a Vote Smart search even if the name is in the local index")
    ap.add_argument("--lookup", metavar="QUERY",
                    help="Search the local index by name or id and exit (no network)")
    ap.add_argument("--list", action="store_true", help="List the local index and exit")
    ap.add_argument("-d", "--out-dir", help="Output directory (default: ../scraped, relative to this script)")
    ap.add_argument("--csv", action="store_true", help="Also write <id>.csv next to the JSON")
    ap.add_argument("--cookie", help="Cookie header string copied from your browser "
                                     "(or set the VS_COOKIE env var)")
    ap.add_argument("--cookie-file", help="Text file containing the Cookie header string")
    ap.add_argument("--user-agent", help="Override the User-Agent (use the same one as the "
                                         "browser the cookies came from)")
    args = ap.parse_args()

    out_dir = os.path.normpath(args.out_dir) if args.out_dir else default_out_dir()
    index = load_index(out_dir)

    # ---- local-only commands ----
    if args.list:
        print_entries(sorted(index.items(), key=lambda kv: kv[1].get("name", "")))
        return
    if args.lookup:
        print_entries(find_in_index(index, args.lookup))
        return
    if not args.source:
        ap.error("a source (name, id, URL, or .html file) is required unless using --list/--lookup")

    cookie = args.cookie or os.environ.get("VS_COOKIE")
    if args.cookie_file:
        with open(args.cookie_file, encoding="utf-8") as f:
            cookie = f.read().strip()

    source = args.source
    if not os.path.exists(source) and not source.lower().startswith("http"):
        if source.isdigit():
            known = index.get(source, {})
            source = known.get("url") or pct_url(source, known.get("name", ""))
        else:
            matches = [] if (args.online or args.pick) else find_in_index(index, source)
            if matches:
                cid, entry = matches[0]
                if len(matches) > 1:
                    print(f"{len(matches)} local matches; using the first "
                          f"(use --online or an id to pick another):", file=sys.stderr)
                    for c, e in matches[:5]:
                        print(f"    {c}  {e['name']}", file=sys.stderr)
                source = entry.get("url") or pct_url(cid, entry["name"])
                print(f"Found in local index: {entry['name']} -> {source}", file=sys.stderr)
            else:
                hit = search_candidate(source, cookie, args.user_agent, args.pick)
                source = pct_url(hit["candidate_id"], hit["name"])
                print(f"Using {hit['name']} -> {source}", file=sys.stderr)

    data = scrape(source, cookie, args.user_agent)
    if not data["positions"]:
        sys.exit("No positions found. If you hit the free-view limit or a login wall, "
                 "save the page from your browser and pass the .html file instead.")

    cid, json_path, entry = save_scrape(data, out_dir, source, make_csv=args.csv)
    print(f"Saved {len(data['positions'])} positions to {json_path}")
    if entry:
        print(f"Index updated: {cid} = {entry['name']!r} (last_updated {entry['last_updated']})")
    if args.csv:
        print(f"Saved CSV to {os.path.join(out_dir, cid + '.csv')}")

if __name__ == "__main__":
    main()