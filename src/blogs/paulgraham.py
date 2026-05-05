"""Paul Graham essays — self-contained blog module.

Exposes: Source, Processor, Scorer, TOPICS, METADATA
"""

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from base import BlogSource, BlogProcessor, BlogScorer

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

METADATA = {
    "title": "Selected Essays",
    "author": "Paul Graham",
    "cover_image": "https://s.turbifycdn.com/aah/paulgraham/still-life-20.gif",
}

# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

TOPICS: dict[str, list[str]] = {
    "The Founder": [
        "foundermode",
        "greatwork",
        "when",
        "fp",
        "fn",
        "users",
        "google",
        "airbnbs",
        "airbnb",
        "jessica",
        "aord",
        "work",
        "safe",
        "name",
        "ronco",
        "corpdev",
        "pinch",
        "before",
        "fr",
        "convince",
        "ds",
        "invtrend",
        "startupideas",
        "growth",
        "swan",
        "pgh",
        "ambitious",
        "schlep",
        "vw",
        "hubs",
        "patentpledge",
        "control",
        "founders",
        "seesv",
        "hiresfund",
        "yahoo",
        "future",
        "organic",
        "really",
        "kate",
        "ramenprofitable",
        "5founders",
        "relres",
        "angelinvesting",
        "maybe",
        "13sentences",
        "artistsship",
        "badeconomy",
        "fundraising",
        "prcmc",
        "googles",
        "startuphubs",
        "webstartups",
        "die",
        "guidetoinvestors",
        "notnot",
        "foundersatwork",
        "startupmistakes",
        "mit",
        "investors",
        "island",
        "america",
        "siliconvalley",
        "startuplessons",
        "startupfunding",
        "vcsqueeze",
        "ideas",
        "sfp",
        "hiring",
        "venturecapital",
        "start",
        "laundry",
        "word",
        "selfindulgence",
        "love",
    ],
    "The Investor": [
        "herd",
        "ycombinator",
        "whyyc",
        "ycstart",
        "superangels",
        "equity",
        "divergence",
    ],
    "The Artist": [
        "goodwriting",
        "field",
        "writes",
        "best",
        "words",
        "goodtaste",
        "simply",
        "speak",
        "talk",
        "useful",
        "sun",
        "discover",
        "publishing",
        "nthings",
        "goodart",
        "copy",
        "desres",
        "taste",
        "essay",
        "writing44",
        "read",
        "noop",
    ],
    "The Hacker": [
        "weird",
        "hw",
        "mac",
        "fix",
        "diff",
        "progbot",
        "web20",
        "reddits",
        "hp",
        "altair",
        "tablets",
        "hackernews",
        "head",
        "microsoft",
        "apple",
        "segway",
        "convergence",
        "opensource",
        "pypar",
        "gh",
        "gba",
        "ffb",
        "iflisp",
        "hundred",
        "better",
        "spam",
        "icad",
        "power",
        "road",
        "rootsoflisp",
        "langdes",
        "popular",
        "javacover",
        "avg",
        "lwba",
        "nft",
    ],
    "The Worker": [
        "do",
        "persistence",
        "hwh",
        "own",
        "procrastination",
        "genius",
        "earnest",
        "early",
        "noob",
        "disc",
        "todo",
        "top",
        "determination",
        "makersschedule",
        "distraction",
        "boss",
        "newthings",
        "judgement",
        "bronze",
        "getideas",
        "worked",
        "ecw",
        "lesson",
    ],
    "The Citizen": [
        "brandage",
        "woke",
        "kids",
        "superlinear",
        "want",
        "alien",
        "heresy",
        "smart",
        "newideas",
        "real",
        "richnow",
        "donate",
        "ace",
        "think",
        "wtax",
        "conformism",
        "orth",
        "cred",
        "fh",
        "mod",
        "nov",
        "pow",
        "vb",
        "ineq",
        "re",
        "bias",
        "mean",
        "95",
        "know",
        "property",
        "addiction",
        "identity",
        "credentials",
        "highres",
        "cities",
        "lies",
        "good",
        "heroes",
        "disagree",
        "trolls",
        "philosophy",
        "colleges",
        "stuff",
        "unions",
        "wisdom",
        "marginal",
        "randomness",
        "softwarepatents",
        "6631327",
        "inequality",
        "ladder",
        "submarine",
        "college",
        "hs",
        "usa",
        "charisma",
        "polls",
        "bubble",
        "gap",
        "wealth",
        "say",
        "nerds",
        "foundervisa",
        "revolution",
        "twitter",
        "hackernews",
        "jessica",
        "ineq",
        "prop62",
    ],
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


class Source(BlogSource):
    name = "paulgraham"
    INDEX_URL = "https://paulgraham.com/articles.html"

    _SKIP = frozenset(
        {
            "index.html",
            "articles.html",
            "books.html",
            "arc.html",
            "bel.html",
            "lisp.html",
            "antispam.html",
            "faq.html",
            "raq.html",
            "quo.html",
            "rss.html",
            "bio.html",
            "kedrosky.html",
        }
    )

    def get_essay_urls(self) -> list[dict]:
        r = requests.get(self.INDEX_URL, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        seen: set[str] = set()
        essays = []
        for a in soup.find_all("a"):
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not href or not title:
                continue
            if href.startswith("http") or not href.endswith(".html"):
                continue
            if href in self._SKIP:
                continue
            url = urljoin(self.INDEX_URL, href)
            if url not in seen:
                seen.add(url)
                essays.append({"title": title, "url": url})
        return essays


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class Processor(BlogProcessor):
    name = "paulgraham"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        td = soup.find("td", width="435")
        if not td:
            return ""

        # Remove promotional banners (colored background tables)
        for table in td.find_all("table"):
            if table.find("td", bgcolor=True):
                table.decompose()

        # Convert footnote refs to markdown-safe placeholders
        for font in td.find_all("font", color="#999999"):
            a = font.find("a")
            if a and a.get("href", "").startswith("#f"):
                n = a.get_text(strip=True)
                font.replace_with(f" \u200b[{n}]")

        # Convert <b>: block-level bold becomes ## heading, inline becomes **bold**
        for b in td.find_all("b"):
            text = b.get_text(strip=True)
            if not text:
                continue
            prev = b.previous_sibling
            while (
                prev is not None
                and getattr(prev, "name", None) is None
                and str(prev).strip() == ""
            ):
                prev = prev.previous_sibling
            nxt = b.next_sibling
            while (
                nxt is not None
                and getattr(nxt, "name", None) is None
                and str(nxt).strip() == ""
            ):
                nxt = nxt.next_sibling
            prev_is_break = prev is None or getattr(prev, "name", "") == "br"
            next_is_break = nxt is not None and getattr(nxt, "name", "") == "br"
            if prev_is_break and next_is_break and len(text) < 80:
                b.replace_with(f"\n\n## {text}\n\n")
            else:
                b.replace_with(f"**{text}**")

        for i in td.find_all("i"):
            i.replace_with(f"*{i.get_text()}*")

        for a in td.find_all("a"):
            href = a.get("href", "")
            text = a.get_text()
            if href.startswith("#"):
                a.replace_with(text)
            elif href:
                a.replace_with(f"[{text}]({href})")

        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        inner = str(td)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        inner = re.sub(r"<p[^>]*>", "\n\n", inner)
        md = BeautifulSoup(inner, "html.parser").get_text()

        lines = [line.rstrip() for line in md.splitlines()]
        md = "\n".join(lines)

        md = re.sub(r"\*\*New:\*\*\s*\[Download On Lisp for Free\]\([^)]+\)\.", "", md)
        md = re.sub(r"\[\s*Comment\s*\]\([^)]+\)\s*on this essay\.?", "", md)
        md = re.sub(r"\[\s*Comment on this essay\.?\s*\]\([^)]+\)", "", md)
        md = re.sub(r"Comment on this essay\.?", "", md)
        md = re.sub(r"\[\]\(http://reddit\.com\)", "", md)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()

        if title:
            md = f"# {title}\n\n" + md
        return md


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class Scorer(BlogScorer):
    name = "paulgraham"

    def get_base_url(self) -> str:
        return "paulgraham.com"

    def get_recommended_slugs(self) -> set[str]:
        recommended: set[str] = set()

        cache_dir = self.cache_dir()

        index_cache = cache_dir / "index.html"
        if not index_cache.exists():
            r = requests.get("https://paulgraham.com/index.html", timeout=15)
            r.raise_for_status()
            index_cache.write_text(r.text)
        for a in BeautifulSoup(index_cache.read_text(), "html.parser").find_all("a"):
            href = a.get("href", "")
            if href.endswith(".html") and not href.startswith("http"):
                slug = href.replace(".html", "")
                if slug not in (
                    "index",
                    "articles",
                    "books",
                    "arc",
                    "bel",
                    "lisp",
                    "antispam",
                    "faq",
                    "raq",
                    "quo",
                    "rss",
                    "bio",
                    "kedrosky",
                ):
                    recommended.add(slug)

        articles_cache = cache_dir / "articles.html"
        if not articles_cache.exists():
            r = requests.get("https://paulgraham.com/articles.html", timeout=15)
            r.raise_for_status()
            articles_cache.write_text(r.text)
        html_articles = articles_cache.read_text()
        if "If you're not sure which to read" in html_articles:
            part = html_articles.split("If you're not sure which to read")[1]
            count = 0
            for a in BeautifulSoup(part, "html.parser").find_all("a"):
                href = a.get("href", "")
                if href.endswith(".html") and not href.startswith("http"):
                    recommended.add(href.replace(".html", ""))
                    count += 1
                if count >= 3:
                    break

        return recommended
