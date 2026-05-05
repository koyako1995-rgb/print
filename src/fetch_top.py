"""Score the marginalrevolution URL cache via Google Search and fetch the top N posts.

Usage:
    python fetch_top.py [N]   (default N=100)
"""

import json
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from blogs.marginalrevolution import _HEADERS

DATA_DIR = Path(__file__).parent.parent / "data" / "marginalrevolution"
URL_CACHE = DATA_DIR / "url_cache.json"
HTML_DIR = DATA_DIR / "html"
MANIFEST = DATA_DIR / "manifest.json"
SEARCH_CACHE = DATA_DIR / "search_cache" / "google_search.json"

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100


def normalize(url: str) -> str:
    url = url.replace("https://", "").replace("http://", "")
    url = url.replace("www.", "")
    return url.rstrip("/").split("?")[0]


def load_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


# ── 1. Load URL cache ──────────────────────────────────────────────────────
essays = load_json(URL_CACHE, [])
if not essays:
    print("No url_cache.json found. Run URL discovery first.")
    sys.exit(1)
print(f"Loaded {len(essays)} URLs from cache.")

# ── 2. Fetch Google search results (cached) ────────────────────────────────
SEARCH_CACHE.parent.mkdir(parents=True, exist_ok=True)
if SEARCH_CACHE.exists():
    google_urls = load_json(SEARCH_CACHE, [])
    print(f"Loaded {len(google_urls)} Google results from cache.")
else:
    api_key = os.environ.get("GOOGLE_API_KEY")
    cx = (
        os.environ.get("GOOGLE_SEARCH_CX")
        or os.environ.get("GOOGLE_CX")
        or os.environ.get("GOOGLE_CSE_ID")
    )
    if not api_key or not cx:
        print("ERROR: GOOGLE_API_KEY / GOOGLE_SEARCH_CX not set in .env")
        sys.exit(1)

    google_urls = []
    for start in range(1, 100, 10):
        print(f"  Google API query (start={start})…")
        try:
            r = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": api_key,
                    "cx": cx,
                    "q": "site:marginalrevolution.com",
                    "start": start,
                    "num": 10,
                },
                timeout=15,
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            for item in items:
                google_urls.append(item["link"])
            if not items:
                break
        except Exception as e:
            print(f"  Google API error: {e}")
            break
        time.sleep(0.5)

    SEARCH_CACHE.write_text(json.dumps(google_urls, indent=2))
    print(f"Fetched {len(google_urls)} Google results, saved to cache.")

# ── 3. Score every cached URL ──────────────────────────────────────────────
google_norm = {normalize(u): i + 1 for i, u in enumerate(google_urls)}

scored = []
for essay in essays:
    rank = google_norm.get(normalize(essay["url"]))
    score = (1.0 / rank) if rank else 0.0
    scored.append({**essay, "score": score, "google_rank": rank})

scored.sort(key=lambda x: x["score"], reverse=True)

in_google = sum(1 for s in scored if s["google_rank"])
print(f"\n{in_google} of {len(scored)} cached URLs appear in Google top-100.")
print(f"\nTop {N} posts to fetch:")
for i, s in enumerate(scored[:N]):
    rank_str = (
        f"rank #{s['google_rank']}" if s["google_rank"] else "not in Google top-100"
    )
    print(f"  {i+1:3d}. [{rank_str}] {s['title'][:65]}")

# ── 4. Fetch the top N HTML files ──────────────────────────────────────────
HTML_DIR.mkdir(parents=True, exist_ok=True)
manifest = load_json(MANIFEST, {})

session = requests.Session()
session.headers.update(_HEADERS)

def slug_of(url):
    return url.rstrip("/").split("/")[-1].replace(".html", "")

to_fetch = [s for s in scored[:N] if slug_of(s["url"]) not in manifest]
print(f"\n{len(manifest)} already cached, fetching {len(to_fetch)} new posts…\n")

for i, essay in enumerate(to_fetch):
    slug = slug_of(essay["url"])
    print(f"  [{i+1}/{len(to_fetch)}] {essay['title'][:70]}")
    try:
        r = session.get(essay["url"], timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"    SKIP ({e})")
        continue

    (HTML_DIR / f"{slug}.html").write_text(r.text)
    manifest[slug] = {
        "title": essay["title"],
        "url": essay["url"],
        "score": essay["score"],
        "google_rank": essay["google_rank"],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2))
    time.sleep(1.0)

print(f"\nDone. {len(manifest)} posts cached in {HTML_DIR}.")
