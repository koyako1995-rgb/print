"""Alexey Guzey's blog — self-contained blog module.

Exposes: Source, Processor, Scorer, TOPICS, METADATA
"""

import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from base import BlogSource, BlogProcessor, BlogScorer

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

METADATA = {
    "title": "the essential guzey",
    "author": "Alexey Guzey",
    "cover_image": "images/printer.jpg",  # needs to be downloaded
    "flat_chapters": True,
}

# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

TOPICS: dict[str, list[str]] = {
    "AI": [
        "why-i-believe-in-agi-again",
        "ai-views-every-year",
        "alignment-on-track",
        "two-sentence-universal-jailbreak",
        "planes-vs-birds",
        "alignment-alchemy",
        "human-general-intelligence-estimate",
        "moon-gravity",
        "why-ai-experts-jobs-are-always-decades-away-from-being-automated",
    ],
    "Science & Sleep": [
        "why-we-sleep",
        "how-life-sciences-actually-work",
        "14-day-sleep-deprivation-self-experiment",
        "theses-on-sleep",
        "scientific-experiments-i-want-to-fund",
        "abolish-the-nih",
        "bloom",
        "is-anything-inherently-difficult",
        "dont-believe-self-reported-data",
        "patronage-and-research-labs",
        "neurodiversity",
    ],
    "Productivity & Advice": [
        "productivity",
        "advice",
        "lifehacks",
        "advice-from-tyler-cowen",
        "advice-from-guest-04",
        "follow-up",
        "how-to-make-friends-over-the-internet",
        "writing-advice",
        "co-working",
        "cargo-cult-productivity",
        "playing-with-identity",
        "2022-lessons",
        "college",
        "why-have-a-blog",
        "what-should-you-do-with-your-life",
    ],
    "Personal": [
        "q-and-a-with-my-high-school-self",
        "friendship",
        "my-journal",
        "people-re-god",
        "what-im-thinking-about",
        "people",
        "old-people",
        "existential-risk",
        "impact",
        "talent",
        "cursed-talent",
        "genius",
        "questions",
        "research-ideas",
    ],
    "Ideas & Society": [
        "what-is-the-alternative-to-utilitarianism",
        "morale",
        "why-is-there-only-one-elon-musk",
        "autistic-leaders",
        "ideas-not-mattering-is-a-psyop",
        "napoleon",
        "longtermism",
        "contra-tails-coming-apart",
        "fun-economic-facts",
        "doing-good-better",
        "why-we-underappreciate-technological-progress",
        "where-does-talent-come-from",
        "substack-earnings",
        "three-questions-for-russia",
        "neurodiversity",
        "hierarchies-of-status",
        "twitter-link-rot",
    ],
    "Curated Reads": [
        "best-of-holden-karnofsky-and-sam-altman",
        "gwern",
        "slate-star-codex",
        "awakening",
        "troublemakers",
    ],
    "Fiction & Art": [
        "dating",
        "tinder",
        "hntop1",
        "pulp-fiction",
        "poems",
        "jaynes",
        "philosophers-for-sale",
    ],
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

_BASE = "https://guzey.com"
_ARCHIVE_URL = "https://guzey.com/archive/"


class Source(BlogSource):
    name = "guzey"

    # Non-essay pages to skip (interactive art, index pages, nav pages)
    _SKIP_PATHS = {
        "x",
        "snake",
        "archive",
        "vibes",
        "2024vibes",
        "tools-gear",
        "favorite/media",
        "advice-invitation",
    }

    # Posts that mostly consist of curated links to other people's work,
    # book excerpts, or recommendation lists — poor reading in print.
    _EXCLUDE_SLUGS = {
        "gwern",  # Gwern's Most Important Writing
        "slate-star-codex",  # Most Important Slate Star Codex Posts
        "best-of-holden-karnofsky-and-sam-altman",  # Best of Holden & Sam
        "awakening",  # Highlights from Gerasimov's Awakening (book excerpts)
        "courses",  # Online courses and textbooks I recommend
        "funding",  # People and Things I Would Fund
        "media",  # My Favorite Movies, TV Shows, Books…
        "people",  # People who are going to change the world (pure link list)
        "my-computer-setup",  # Monitor/gear setup post (list with video)
    }

    def get_essay_urls(self) -> list[dict]:
        r = requests.get(_ARCHIVE_URL, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Only look inside the archive article body (skips header/footer nav)
        article = soup.find("article", class_="article")
        if not article:
            raise RuntimeError("Could not find archive article on guzey.com/archive/")

        seen_slugs: set[str] = set()
        essays = []

        for li in article.find_all("li"):
            a = li.find("a", href=True)
            if not a:
                continue
            href = a["href"].strip()
            title = a.get_text(strip=True)
            if not href or not title:
                continue

            url = urljoin(_ARCHIVE_URL, href)

            # Only include guzey.com essays (skip external links)
            if not url.startswith(_BASE + "/"):
                continue

            # Skip PDFs
            if url.endswith(".pdf"):
                continue

            path = url[len(_BASE) :].strip("/")

            # Skip non-essay pages
            if path in self._SKIP_PATHS:
                continue
            # Skip link-roundup posts (links/YYYY/N)
            if re.match(r"links/", path):
                continue

            slug = self.slug_from_url(url)
            if slug in seen_slugs or slug in self._EXCLUDE_SLUGS:
                continue
            seen_slugs.add(slug)
            essays.append({"title": title, "url": url})

        return essays


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class Processor(BlogProcessor):
    name = "guzey"

    _TRUNCATE_RE = re.compile(
        r"(?im)^\s{0,3}(?:#{1,6}\s+)?(?:ap{1,2}endix|addendum)\s*:\s*|^\s{0,3}(?:#{1,6}\s+)?citation\s*$"
    )

    # Remove forum/discussion call-to-action paragraphs (not useful in print).
    # We match on the first non-empty line of a paragraph.
    _FORUM_PROMO_RE = re.compile(r"(?i)^(see discussion on\b|discuss\b.*\bforum\b)")

    _PERMA_TOKEN_LINK_RE = re.compile(
        r"(?i)\[\s*(?:a|perma)\s*\]\(https?://perma\.cc/[^)]+\)"
    )
    _PERMA_TOKEN_PAREN_RE = re.compile(
        r"(?i)\(\s*\[\s*(?:a|perma)\s*\]\(https?://perma\.cc/[^)]+\)\s*\)"
    )
    # Remove leftover citation-style (a) tokens only when they're used like
    # a permalink marker (i.e., followed by punctuation/end), not when they
    # introduce (a)/(b) lists inside sentences.
    _CITATION_A_TOKEN_RE = re.compile(r"(?i)\(\s*a\s*\)(?=\s*(?:[\)\]\}\.,;:!?]|$))")

    # Posts where images are mostly decorative / low value for print.
    _STRIP_IMAGE_SLUGS: frozenset[str] = frozenset(
        {
            "dating",
            "hntop1",
            "morale",
        }
    )

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        article = soup.find("article", class_="article")
        if not article:
            return ""

        # Resolve the post's canonical URL from og:url meta tag so we can
        # make relative hrefs absolute (e.g. ../../books/why-we-sleep/).
        og_url_tag = soup.find("meta", property="og:url")
        canon_url = _BASE + (og_url_tag["content"] if og_url_tag else "/")
        slug = canon_url.rstrip("/").split("/")[-1].replace(".html", "")

        def best_img_src(img_tag) -> str:
            src = (
                img_tag.get("src")
                or img_tag.get("data-src")
                or img_tag.get("data-original")
                or ""
            ).strip()
            if not src:
                # srcset looks like: "url1 800w, url2 1600w". Prefer the first url.
                srcset = (img_tag.get("srcset") or "").strip()
                if srcset:
                    first = srcset.split(",", 1)[0].strip()
                    src = first.split()[0].strip() if first else ""
            return src

        # Title
        title_tag = article.find("h1", class_="article-title")
        if not title_tag:
            return ""
        title = title_tag.get_text(strip=True)
        title_tag.decompose()

        # Date: first <time> inside <span class="post-date">
        date_str = ""
        post_date = article.find("span", class_="post-date")
        if post_date:
            time_tag = post_date.find("time")
            if time_tag:
                raw_date = time_tag.get_text(strip=True).split()[0]  # e.g. "2023-08-28"
                try:
                    dt = datetime.strptime(raw_date, "%Y-%m-%d")
                    date_str = dt.strftime("%B %Y")
                except ValueError:
                    date_str = ""
            post_date.decompose()

        # Strip navigation, sidebars, and chrome
        for el in article.find_all("div", class_="toc_outside"):
            el.decompose()
        for el in article.find_all("aside"):
            el.decompose()
        for el in article.find_all("nav"):
            el.decompose()

        # Inline sidenotes: <span class="sidenote">...</span> → (note: ...)
        # Strip the associated <label> and <input> toggle controls
        for el in article.find_all("label", class_="margin-toggle"):
            el.decompose()
        for el in article.find_all("input", class_="margin-toggle"):
            el.decompose()
        for sn in article.find_all("span", class_="sidenote"):
            sn.replace_with(f" ({sn.get_text(strip=True)})")
        for mn in article.find_all("span", class_="marginnote"):
            mn.replace_with(f" ({mn.get_text(strip=True)})")

        if slug in self._STRIP_IMAGE_SLUGS:
            for img in article.find_all("img"):
                img.decompose()
        else:
            # Keep figures: convert <img> to markdown image syntax.
            # (We later run pandoc with --extract-media to download remote images.)
            for img in article.find_all("img"):
                src = best_img_src(img)
                if not src:
                    img.decompose()
                    continue
                abs_src = urljoin(canon_url, src)
                alt = (img.get("alt") or "").strip()
                img.replace_with(f"![{alt}]({abs_src})")

        # Convert blockquotes to markdown > prefix
        for bq in reversed(article.find_all("blockquote")):
            lines = bq.get_text("\n", strip=True).splitlines()
            quoted = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in lines)
            bq.replace_with(f"\n{quoted}\n")

        # Convert tables to simple pipe-table markdown
        for tbl in reversed(article.find_all("table")):
            rows = tbl.find_all("tr")
            if not rows:
                tbl.decompose()
                continue
            md_rows = []
            for i, row in enumerate(rows):
                cells = [
                    td.get_text(" ", strip=True) for td in row.find_all(["th", "td"])
                ]
                md_rows.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    md_rows.append("| " + " | ".join("---" for _ in cells) + " |")
            tbl.replace_with("\n" + "\n".join(md_rows) + "\n")

        # Convert links: strip anchor-only links; make relative links absolute
        for a in article.find_all("a"):
            href = a.get("href", "")
            text = a.get_text()
            if href.startswith("#"):
                a.replace_with(text)
            elif text.lstrip().startswith("!["):
                # Avoid wrapping images in links; keep just the image.
                a.replace_with(text)
            elif href:
                abs_href = urljoin(canon_url, href)
                a.replace_with(f"[{text}]({abs_href})")

        # Bold and italic
        for b in article.find_all(["b", "strong"]):
            b.replace_with(f"**{b.get_text()}**")
        for i in article.find_all(["i", "em"]):
            i.replace_with(f"*{i.get_text()}*")

        # Convert lists to markdown before stripping tags (process deepest first)
        def list_to_md(tag, ordered: bool) -> str:
            lines = []
            for idx, li in enumerate(tag.find_all("li", recursive=False), start=1):
                prefix = f"{idx}." if ordered else "-"
                lines.append(f"{prefix} {li.get_text(' ', strip=True)}")
            return "\n" + "\n".join(lines) + "\n"

        for ol in reversed(article.find_all("ol")):
            ol.replace_with(list_to_md(ol, ordered=True))
        for ul in reversed(article.find_all("ul")):
            ul.replace_with(list_to_md(ul, ordered=False))

        # Convert <br> to newlines and block-level tags to paragraph breaks
        inner = str(article)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        inner = re.sub(r"<p[^>]*>", "\n\n", inner)
        inner = re.sub(r"<h2[^>]*>", "\n\n## ", inner)
        inner = re.sub(r"<h3[^>]*>", "\n\n### ", inner)
        inner = re.sub(r"<h[4-6][^>]*>", "\n\n#### ", inner)
        inner = re.sub(r"</h[1-6]>", "\n\n", inner)
        md = BeautifulSoup(inner, "html.parser").get_text()

        # Normalise whitespace
        lines = [line.rstrip() for line in md.splitlines()]
        md = "\n".join(lines)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()

        # Guzey essays often include long appendices/addenda. For print purposes
        # we clip everything after the first "Appendix:" / "Apendix:" / "Addendum:" heading.
        truncate_match = self._TRUNCATE_RE.search(md)
        if truncate_match:
            md = md[: truncate_match.start()].rstrip()

        # Drop short forum/discussion promo paragraphs.
        if md:
            cleaned_paragraphs = []
            for para in re.split(r"\n{2,}", md):
                if not para.strip():
                    continue
                first_line = ""
                for ln in para.splitlines():
                    if ln.strip():
                        first_line = ln.strip()
                        break
                # Many promos are Markdown links like "[Discuss...](...)".
                check_line = re.sub(r"^[\s>*\-\[(]+", "", first_line).strip()
                if check_line and self._FORUM_PROMO_RE.match(check_line):
                    continue
                cleaned_paragraphs.append(para.strip())
            md = "\n\n".join(cleaned_paragraphs).strip()

            # Remove perma.cc token links like "([a](...))" / "([perma](...))".
            # Keep other perma.cc links (where the anchor text is meaningful).
            md = self._PERMA_TOKEN_PAREN_RE.sub("", md)
            md = self._PERMA_TOKEN_LINK_RE.sub("", md)
            md = self._CITATION_A_TOKEN_RE.sub("", md)
            md = re.sub(r"\(\s*\)", "", md)
            md = re.sub(r"[ \t]{2,}", " ", md)
            md = re.sub(r"\n{3,}", "\n\n", md).strip()

        # Escape @-mentions so pandoc/Typst doesn't treat them as citation keys.
        # Pandoc recognises @key, [@key], and (@key) as citations, so we must
        # cover whitespace, [, (, and start-of-line as preceding characters.
        # We intentionally exclude @ preceded by alphanumerics (e.g. email addresses).
        md = re.sub(r"(^|[\s\[(\"])@([A-Za-z_])", r"\1\\@\2", md, flags=re.MULTILINE)

        if date_str:
            return f"# {title}\n\n{date_str}\n\n{md}"
        return f"# {title}\n\n{md}"


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class Scorer(BlogScorer):
    name = "guzey"

    def get_base_url(self) -> str:
        return "guzey.com"

    def get_recommended_slugs(self) -> set[str]:
        # Slugs from "personal favorites" + "most notable" sections on guzey.com homepage
        return {
            "talent",
            "genius",
            "people",
            "why-have-a-blog",
            "what-im-thinking-about",
            "why-we-sleep",
            "questions",
            "how-life-sciences-actually-work",
            "14-day-sleep-deprivation-self-experiment",
            "what-is-the-alternative-to-utilitarianism",
            "neurodiversity",
            "advice",
            "morale",
            "bloom",
            "research-ideas",
            "best-of-holden-karnofsky-and-sam-altman",
            "gwern",
            "slate-star-codex",
            "dont-believe-self-reported-data",
            "doing-good-better",
        }
