import importlib
import json
import time
from abc import ABC, abstractmethod
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# Source                                                                      #
# --------------------------------------------------------------------------- #


class BlogSource(ABC):
    """Base class for fetching raw HTML from a blog."""

    name: str

    @abstractmethod
    def get_essay_urls(self) -> list[dict]:
        """Return a list of dicts with 'title' and 'url' keys."""
        ...

    def base_dir(self) -> Path:
        return DATA_DIR / self.name

    def cache_dir(self) -> Path:
        d = self.base_dir() / "html"
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

    @staticmethod
    def slug_from_url(url: str) -> str:
        return url.rstrip("/").split("/")[-1].replace(".html", "")

    def fetch_all(self, delay: float = 1.0):
        essays = self.get_essay_urls()
        manifest = self.load_manifest()

        print(f"[{self.name}] {len(essays)} essays found, {len(manifest)} already cached")

        for i, essay in enumerate(essays):
            slug = self.slug_from_url(essay["url"])
            if slug in manifest:
                continue

            print(f"  [{i+1}/{len(essays)}] {essay['title']}")
            try:
                r = requests.get(essay["url"], timeout=15)
                # 内田樹氏のブログ(tatsuru)の場合はEUC-JPでデコードする
                if self.name == "tatsuru":
                    r.encoding = "euc-jp"
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"    SKIP (error: {e})")
                continue

            # 保存時は一貫して utf-8 を指定
            (self.cache_dir() / f"{slug}.html").write_text(r.text, encoding="utf-8")
            manifest[slug] = {"title": essay["title"], "url": essay["url"]}
            self.save_manifest(manifest)
            time.sleep(delay)

        print(f"[{self.name}] Done. {len(manifest)} essays cached.")


# --------------------------------------------------------------------------- #
# Process                                                                     #
# --------------------------------------------------------------------------- #


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

    def manifest_path(self) ->
