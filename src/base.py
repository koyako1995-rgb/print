"""
Shared abstract base classes and utilities for the blog printing pipeline.

Each blog lives in blogs/<name>.py and must expose:
    Source    - subclass of BlogSource
    Processor - subclass of BlogProcessor
    Scorer    - subclass of BlogScorer
    TOPICS    - dict[str, list[str]]  chapter -> slug list
    METADATA  - dict with keys: title, author, cover_image (str | None)
"""

import importlib
import json
import os
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
BLOGS_DIR = Path(__file__).parent / "blogs"


def load_blog(name: str):
    """Dynamically import blogs/<name>.py and return the module."""
    if not (BLOGS_DIR / f"{name}.py").exists():
        available = sorted(
            p.stem for p in BLOGS_DIR.glob("*.py") if p.stem != "__init__"
        )
        print(f"Unknown blog: {name!r}. Available: {', '.join(available)}")
        sys.exit(1)
    return importlib.import_module(f"blogs.{name}")


def list_blogs() -> list[str]:
    return sorted(p.stem for p in BLOGS_DIR.glob("*.py") if p.stem != "__init__")


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


class BlogSource(ABC):
    """Base class for a blog source. Subclass to add new blogs."""

    name: str

    @abstractmethod
    def get_essay_urls(self) -> list[dict]:
        """Return list of {"title": ..., "url": ...} dicts."""
        ...

    def cache_dir(self) -> Path:
        d = DATA_DIR / self.name / "html"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def manifest_path(self) -> Path:
        return DATA_DIR / self.name / "manifest.json"

    def load_manifest(self) -> dict:
        if self.manifest_path().exists():
            return json.loads(self.manifest_path().read_text())
        return {}

    def save_manifest(self, manifest: dict):
        self.manifest_path().write_text(json.dumps(manifest, indent=2))

    @staticmethod
    def slug_from_url(url: str) -> str:
        return url.rstrip("/").split("/")[-1].replace(".html", "")

    def fetch_all(self, delay: float = 1.0):
        essays = self.get_essay_urls()
        manifest = self.load_manifest()
        print(
            f"[{self.name}] {len(essays)} essays found, {len(manifest)} already cached"
        )

        for i, essay in enumerate(essays):
            slug = self.slug_from_url(essay["url"])
            if slug in manifest:
                continue

            print(f"  [{i+1}/{len(essays)}] {essay['title']}")
            try:
                r = requests.get(essay["url"], timeout=15)
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"    SKIP (error: {e})")
                continue

            (self.cache_dir() / f"{slug}.html").write_text(r.text)
            manifest[slug] = {"title": essay["title"], "url": essay["url"]}
            self.save_manifest(manifest)
            time.sleep(delay)

        print(f"[{self.name}] Done. {len(manifest)} essays cached.")


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class BlogProcessor(ABC):
    """Base class for HTML-to-markdown conversion."""

    name: str

    @abstractmethod
    def extract_markdown(self, html: str) -> str:
        """Given raw HTML, return clean markdown."""
        ...

    def base_dir(self) -> Path:
        return DATA_DIR / self.name

    def cache_dir(self) -> Path:
        return self.base_dir() / "html"

    def md_dir(self) -> Path:
        d = self.base_dir() / "md"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def manifest_path(self) -> Path:
        return self.base_dir() / "manifest.json"

    def load_manifest(self) -> dict:
        if self.manifest_path().exists():
            return json.loads(self.manifest_path().read_text())
        return {}

    def save_manifest(self, manifest: dict):
        self.manifest_path().write_text(json.dumps(manifest, indent=2))

    def process_all(self):
        manifest = self.load_manifest()
        processed = 0
        skipped = 0

        for slug, meta in manifest.items():
            html_file = self.cache_dir() / f"{slug}.html"
            if not html_file.exists():
                continue

            md = self.extract_markdown(html_file.read_text())
            if not md.strip():
                skipped += 1
                continue

            (self.md_dir() / f"{slug}.md").write_text(md)
            meta["words"] = len(md.split())
            processed += 1

        self.save_manifest(manifest)
        total_words = sum(m.get("words", 0) for m in manifest.values())
        print(
            f"[{self.name}] {processed} processed, {skipped} skipped, {total_words:,} words total."
        )


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class BlogScorer(ABC):
    name: str

    def base_dir(self) -> Path:
        return DATA_DIR / self.name

    def manifest_path(self) -> Path:
        return self.base_dir() / "manifest.json"

    def cache_dir(self) -> Path:
        d = self.base_dir() / "search_cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def load_manifest(self) -> dict:
        if self.manifest_path().exists():
            return json.loads(self.manifest_path().read_text())
        return {}

    def save_manifest(self, manifest: dict):
        self.manifest_path().write_text(json.dumps(manifest, indent=2))

    @abstractmethod
    def get_recommended_slugs(self) -> set[str]:
        """Return slugs that are author-recommended (earn 1 point)."""
        ...

    @abstractmethod
    def get_base_url(self) -> str:
        """Domain to query Google for, e.g. 'paulgraham.com'."""
        ...

    def fetch_google_search_results(self) -> list[str]:
        """Query Google Custom Search API for site:{base_url}. Cached."""
        cache_file = self.cache_dir() / "google_search.json"
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        api_key = os.environ.get("GOOGLE_API_KEY")
        cx = (
            os.environ.get("GOOGLE_CX")
            or os.environ.get("GOOGLE_CSE_ID")
            or os.environ.get("GOOGLE_SEARCH_CX")
        )

        if not api_key:
            print(
                "WARNING: GOOGLE_API_KEY not found in .env. Skipping Google search scoring."
            )
            return []
        if not cx:
            print(
                "WARNING: GOOGLE_CX not found in .env. Skipping Google search scoring."
            )
            return []

        query = f"site:{self.get_base_url()}"
        urls = []
        for start in range(1, 100, 10):
            print(f"[{self.name}] Fetching Google search results (start={start})...")
            try:
                r = requests.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": api_key,
                        "cx": cx,
                        "q": query,
                        "start": start,
                        "num": 10,
                    },
                    timeout=15,
                )
                r.raise_for_status()
                items = r.json().get("items", [])
                for item in items:
                    urls.append(item.get("link"))
                if not items:
                    break
            except requests.RequestException as e:
                print(f"[{self.name}] Google Search API error: {e}")
                break

        cache_file.write_text(json.dumps(urls, indent=2))
        return urls

    def score_all(self):
        manifest = self.load_manifest()
        if not manifest:
            print(
                f"[{self.name}] No manifest found. Please run fetch and process first."
            )
            return

        recommended = self.get_recommended_slugs()
        ranked_urls = self.fetch_google_search_results()

        url_to_rank = {}
        for i, url in enumerate(ranked_urls):
            if url not in url_to_rank:
                url_to_rank[url] = i + 1

        def normalize_url(u):
            if not u:
                return ""
            u = u.replace("http://", "").replace("https://", "")
            if u.startswith("www."):
                u = u[4:]
            return u.rstrip("/")

        b = float(os.environ.get("SCORE_BIAS", 0))
        for slug, meta in manifest.items():
            score = 1.0 if slug in recommended else 0.0
            norm_url = normalize_url(meta.get("url"))
            rank = next(
                (
                    r_idx
                    for r_url, r_idx in url_to_rank.items()
                    if norm_url and norm_url == normalize_url(r_url)
                ),
                None,
            )
            if rank is not None:
                score += 1.0 / (rank + b)
            meta["score"] = score

        self.save_manifest(manifest)
        print(f"[{self.name}] Scored {len(manifest)} essays.")

        sorted_essays = sorted(
            manifest.values(), key=lambda x: x.get("score", 0), reverse=True
        )
        print("\nTop 10 essays by score:")
        for i, essay in enumerate(sorted_essays[:10]):
            print(f"{i+1}. {essay['title']} (Score: {essay.get('score', 0):.3f})")
