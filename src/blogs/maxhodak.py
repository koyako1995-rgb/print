"""Max Hodak writings — self-contained blog module.

Exposes: Source, Processor, Scorer, TOPICS, METADATA
"""

import re

import requests
from bs4 import BeautifulSoup, NavigableString

from base import BlogSource, BlogProcessor, BlogScorer

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

METADATA = {
    "title": "The Blog",
    "author": "Max Hodak",
    "cover_image": "images/eakins.jpg",
    "flat_chapters": True,
}

# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

TOPICS: dict[str, list[str]] = {
    "Science & Philosophy": [
        "the-binding-problem",
        "uncertainty",
        "epistemology",
        "relativity",
        "simulation",
        "simulation-reality-constraints",
        "the-hard-problem-of-brain-machine-interfacing",
        "are-you-sick",
        "medical-math",
        "family-medicine",
        "the-brain-dreams",
        "the-vanishing-computer",
        "shared-realities",
        "do-words-mean-anything",
        "is-it-true",
        "the-next-button",
    ],
    "Technology & AI": [
        "agi-soon",
        "buggy-technology-malware",
        "defensive-code",
        "security",
        "insecure-banking",
        "bitcoin",
        "five-things",
        "frequent-flyer-hacks",
    ],
    "Startups & Investing": [
        "how-i-invest",
        "advice-for-prospective-startup-founders",
        "fast-progress-requires-strong-gradients",
        "signaling-of-secrecy",
        "transcriptic-culture",
        "avoid-little-leagues",
        "management-by-laziness",
        "speed-limits",
        "cosmic-games",
        "mindstate-design",
        "synchron",
        "science",
        "decoupling-medicinal-chemistry",
    ],
    "Society & Ideas": [
        "thinking-of-the-children",
        "what-does-twitter-asymptote-to",
        "what-we-owe-to-each-other",
        "ideal-body-plans",
        "where-is-the-border",
        "dont-give-up",
        "the-future",
    ],
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


class Source(BlogSource):
    name = "maxhodak"
    INDEX_URL = "https://maxhodak.com/writings/"
    _BASE = "https://maxhodak.com"

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
            if href.startswith("/"):
                href = self._BASE + href
            if not href.startswith("https://maxhodak.com/writings/20"):
                continue
            if href not in seen:
                seen.add(href)
                essays.append({"title": title, "url": href})
        return essays


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class Processor(BlogProcessor):
    name = "maxhodak"

    # Promotional / boilerplate paragraphs to strip (substring match)
    _STRIP_PARAGRAPHS = [
        "It is central to our mission at Science to develop the tools required to solve these problems",
    ]

    @staticmethod
    def _code_language(code_tag) -> str:
        for class_name in code_tag.get("class", []):
            if class_name.startswith("language-"):
                lang = class_name.removeprefix("language-")
                return "" if lang == "plaintext" else lang
        return ""

    @staticmethod
    def _normalize_markdown(md: str) -> str:
        lines = [line.rstrip() for line in md.splitlines()]
        md = "\n".join(lines)

        parts = re.split(r"(```[\s\S]*?```)", md)
        normalized = []
        for part in parts:
            if part.startswith("```"):
                normalized.append(part.strip("\n"))
            else:
                normalized.append(re.sub(r"\n{3,}", "\n\n", part))
        return "".join(normalized).strip()

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        # Title: the standalone <h2> (outside #post)
        title_tag = soup.find("h2")
        if not title_tag:
            return ""
        title = title_tag.get_text(strip=True)

        # Date: <h4 class="dateline"> e.g. "July 2020"
        date_str = ""
        date_tag = soup.find("h4", class_="dateline")
        if date_tag:
            date_str = date_tag.get_text(strip=True)

        # Article body lives in <div id="post">
        content = soup.find("div", id="post")
        if not content:
            return ""

        for p in content.find_all("p"):
            text = p.get_text()
            if any(snippet in text for snippet in self._STRIP_PARAGRAPHS):
                p.decompose()
                continue
            # Strip alert/callout boxes
            if p.get("class") and any("alert" in c for c in p.get("class", [])):
                p.decompose()
                continue
            # Strip paragraphs whose sole content is a link to a PDF
            links = p.find_all("a")
            if (
                len(links) == 1
                and links[0].get("href", "").endswith(".pdf")
                and p.get_text(strip=True) == links[0].get_text(strip=True)
            ):
                p.decompose()

        for code in content.find_all("code"):
            if code.find_parent("pre"):
                continue
            text = code.get_text()
            code.replace_with(f"`{text}`")

        for pre in content.find_all("pre"):
            code = pre.find("code")
            code_text = (code or pre).get_text().strip("\n")
            lang = self._code_language(code) if code else ""
            pre_parent = pre.parent
            fenced = NavigableString(f"\n\n```{lang}\n{code_text}\n```\n\n")
            if pre_parent and pre_parent.name == "figure":
                pre_parent.replace_with(fenced)
            else:
                pre.replace_with(fenced)

        for a in content.find_all("a"):
            href = a.get("href", "")
            text = a.get_text()
            if href.startswith("#"):
                a.replace_with(text)
            elif href:
                a.replace_with(f"[{text}]({href})")

        for b in content.find_all(["b", "strong"]):
            b.replace_with(f"**{b.get_text()}**")

        for i in content.find_all(["i", "em"]):
            i.replace_with(f"*{i.get_text()}*")

        inner = str(content)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        inner = re.sub(r"<p[^>]*>", "\n\n", inner)
        md = BeautifulSoup(inner, "html.parser").get_text()
        md = self._normalize_markdown(md)

        # Escape bare @-mentions so pandoc doesn't treat them as citation keys
        md = re.sub(r"(^|\s)@([A-Za-z])", r"\1\\@\2", md, flags=re.MULTILINE)

        if date_str:
            return f"# {title}\n\n{date_str}\n\n{md}"
        return f"# {title}\n\n{md}"


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class Scorer(BlogScorer):
    name = "maxhodak"

    def get_base_url(self) -> str:
        return "maxhodak.com"

    def get_recommended_slugs(self) -> set[str]:
        return set()
