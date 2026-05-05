"""Marginal Revolution — self-contained blog module.

Exposes: Source, Processor, Scorer, TOPICS, METADATA

Uses a hardcoded canon of 40 hand-picked articles rather than
crawling the full RSS feed (which is blocked by Cloudflare).
"""

import re
import time as _time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from base import BlogSource, BlogProcessor, BlogScorer

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

METADATA = {
    "title": "Selected Posts from\nMarginal Revolution",
    "author": "Alex Tabarrok & Tyler Cowen",
    "cover_image": "images/marginal.svg",
}

# ---------------------------------------------------------------------------
# Hardcoded canon
# Each entry: title, url, author (short form for the date line), topic chapter
# ---------------------------------------------------------------------------

_CANON = [
    # ── Tyler: Politics & Ideas ──────────────────────────────────────────────
    {
        "title": "Firefighters Don't Fight Fires",
        "url": "https://marginalrevolution.com/marginalrevolution/2012/07/firefighters-dont-fight-fires.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "A Bet is a Tax on Bullshit",
        "url": "https://marginalrevolution.com/marginalrevolution/2012/11/a-bet-is-a-tax-on-bullshit.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "Tesla versus the Rent Seekers",
        "url": "https://marginalrevolution.com/marginalrevolution/2014/03/tesla-versus-the-rent-seekers.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "Ferguson and the Modern Debtor's Prison",
        "url": "https://marginalrevolution.com/marginalrevolution/2014/08/ferguson-and-the-debtors-prison.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The FTX Debacle ELI5",
        "url": "https://marginalrevolution.com/marginalrevolution/2022/11/the-ftx-debacle-eli5.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "College has been oversold",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/11/college-has-been-oversold.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "Teachers Don't Like Creative Students",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/12/teachers-dont-like-creative-students.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "Apple Should Buy a University",
        "url": "https://marginalrevolution.com/marginalrevolution/2015/10/apple-should-buy-a-university.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "What Was Gary Becker's Biggest Mistake?",
        "url": "https://marginalrevolution.com/marginalrevolution/2015/09/what-was-gary-beckers-biggest-mistake.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The Student Loan Giveaway is Much Bigger Than You Think",
        "url": "https://marginalrevolution.com/marginalrevolution/2022/08/the-student-loan-giveaway-its-much-bigger-than-you-think.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "India's Voluntary City",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/06/indias-voluntary-city.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "Cities as hotels",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/09/cities-as-hotels.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The War on Roommates: Why Is Sharing a House Illegal?",
        "url": "https://marginalrevolution.com/marginalrevolution/2025/08/the-war-on-roommates-why-is-sharing-a-house-illegal.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The Great (Male) Stagnation",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/06/the-great-male-stagnation.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The Economics of the California Water Shortage",
        "url": "https://marginalrevolution.com/marginalrevolution/2015/03/the-california-water-shortage-again.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The Misallocation of Water",
        "url": "https://marginalrevolution.com/marginalrevolution/2015/03/the-misallocation-of-water.html",
        "author": "Alex Tabarrok",
        "topic": "Alex Tabarrok",
    },
    {
        "title": "The fallacy of mood affiliation",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/03/the-fallacy-of-mood-affiliation.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "What libertarianism has become and will become — State Capacity Libertarianism",
        "url": "https://marginalrevolution.com/marginalrevolution/2020/01/what-libertarianism-has-become-and-will-become-state-capacity-libertarianism.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "What the hell is going on?",
        "url": "https://marginalrevolution.com/marginalrevolution/2016/05/what-in-the-hell-is-going-on.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Classical liberalism vs. The New Right",
        "url": "https://marginalrevolution.com/marginalrevolution/2022/10/classical-liberalism-vs-the-new-right.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "The changes in vibes — why did they happen?",
        "url": "https://marginalrevolution.com/marginalrevolution/2024/07/the-changes-in-vibes-why-did-they-happen.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Trumpian policy as cultural policy",
        "url": "https://marginalrevolution.com/marginalrevolution/2025/02/trumpian-policy-as-cultural-policy.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Putin as a man of ideas",
        "url": "https://marginalrevolution.com/marginalrevolution/2022/02/putin-as-a-man-of-ideas.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "How did the IR community get Russia/Ukraine so wrong?",
        "url": "https://marginalrevolution.com/marginalrevolution/2022/05/how-did-the-ir-community-get-russia-ukraine-so-wrong.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Tyler Cowen's three laws",
        "url": "https://marginalrevolution.com/marginalrevolution/2015/04/tyler-cowens-three-laws.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "A simple theory of why so many smart young people go into finance, law, and consulting",
        "url": "https://marginalrevolution.com/marginalrevolution/2012/01/a-simple-theory-of-why-so-many-smart-young-people-go-into-finance-law-and-consulting.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Why economic mobility measures are overrated",
        "url": "https://marginalrevolution.com/marginalrevolution/2012/01/why-economic-mobility-measures-are-overrated.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "How much have white Americans benefited from slavery and its legacy?",
        "url": "https://marginalrevolution.com/marginalrevolution/2014/05/how-much-have-white-americans-benefited-from-slavery-and-its-legacy.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "The fragility of herd immunity",
        "url": "https://marginalrevolution.com/marginalrevolution/2020/09/the-fragility-of-herd-immunity.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "How we should update our views on immigration",
        "url": "https://marginalrevolution.com/marginalrevolution/2024/07/how-we-should-update-our-views-on-immigration.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Taxing unrealized capital gains is a terrible idea",
        "url": "https://marginalrevolution.com/marginalrevolution/2024/09/taxing-unrealized-capital-gains-is-a-terrible-idea.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Common mistakes of left-wing economists?",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/03/in-which-ways-do-left-wing-economists-deny-or-refuse-to-recognize-science.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Common mistakes of right-wing and market-oriented economists?",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/03/fallacies-committed-by-right-wing-and-market-oriented-economists.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Why I think AI take-off is relatively slow",
        "url": "https://marginalrevolution.com/marginalrevolution/2025/02/why-i-think-ai-take-off-is-relatively-slow.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Existential risk, AI, and the inevitable turn in human history",
        "url": "https://marginalrevolution.com/marginalrevolution/2023/03/existential-risk-and-the-turn-in-human-history.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "How I practice at what I do",
        "url": "https://marginalrevolution.com/marginalrevolution/2019/07/how-i-practice-at-what-i-do.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Work on these things",
        "url": "https://marginalrevolution.com/marginalrevolution/2019/12/work-on-these-things.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "What will you do to stay weird?",
        "url": "https://marginalrevolution.com/marginalrevolution/2019/12/what-will-you-do-to-stay-weird.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
    {
        "title": "Explaining France, a reader request",
        "url": "https://marginalrevolution.com/marginalrevolution/2011/01/explaining-france-a-reader-request.html",
        "author": "Tyler Cowen",
        "topic": "Tyler Cowen",
    },
]

# Lookup: slug → author
_SLUG_AUTHOR: dict[str, str] = {}
for _entry in _CANON:
    _slug = _entry["url"].rstrip("/").split("/")[-1].replace(".html", "")
    _SLUG_AUTHOR[_slug] = _entry["author"]

# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

TOPICS: dict[str, list[str]] = {}
for _entry in _CANON:
    _slug = _entry["url"].rstrip("/").split("/")[-1].replace(".html", "")
    TOPICS.setdefault(_entry["topic"], []).append(_slug)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Only these posts keep ![](…) / ![alt](…) lines in the PDF pipeline.
_KEEP_MARKDOWN_IMAGE_SLUGS: frozenset[str] = frozenset(
    {
        "college-has-been-oversold",
        "firefighters-dont-fight-fires",
        "the-great-male-stagnation",
    }
)

_IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_BEFORE_IMAGE_RE = re.compile(r"([^\n])(\!\[[^\]]*\]\([^)]*\))")
_IMAGE_MD_CAPTURE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def _split_inline_markdown_images(md: str) -> str:
    """If ![](…) / ![alt](…) is glued to the previous character, start it on a new paragraph."""
    while True:
        new = _BEFORE_IMAGE_RE.sub(r"\1\n\n\2", md)
        if new == md:
            return new
        md = new


def _strip_markdown_images(md: str) -> str:
    """Remove markdown image syntax; collapse extra blank lines."""
    md = _IMAGE_MD_RE.sub("", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _render_images_as_centered_typst(md: str, *, slug: str, base_dir: Path) -> str:
    """Download images locally and render them via a centered Typst block.

    Typst can't fetch remote HTTP(S) images by default, so we download the
    assets into `data/<blog>/media/<slug>/` and reference them as local files.
    """

    session = requests.Session()
    session.headers.update(_HEADERS)

    media_dir = base_dir / "media" / slug
    media_dir.mkdir(parents=True, exist_ok=True)
    project_root = Path(__file__).parent.parent.parent.resolve()

    def repl(m: re.Match) -> str:
        url = (m.group(2) or "").strip()
        if not url:
            return ""

        # Choose a stable filename from the URL path.
        name = url.split("?")[0].rstrip("/").split("/")[-1] or "image"
        local_path = media_dir / name

        if not local_path.exists():
            try:
                r = session.get(url, timeout=20)
                r.raise_for_status()
                local_path.write_bytes(r.content)
            except requests.RequestException:
                # If it can't be fetched, drop the image rather than failing PDF build.
                return ""

        try:
            rel_path = local_path.resolve().relative_to(project_root).as_posix()
        except ValueError:
            rel_path = local_path.name
        rooted = "/" + rel_path.lstrip("/")
        return (
            "\n\n```{=typst}\n"
            f'#align(center)[#image("{rooted}", height: 9cm, fit: "contain")]\n'
            "```\n\n"
        )

    md2 = _IMAGE_MD_CAPTURE_RE.sub(repl, md)
    md2 = re.sub(r"\n{3,}", "\n\n", md2).strip()
    return md2


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


class Source(BlogSource):
    name = "marginalrevolution"

    def get_essay_urls(self) -> list[dict]:
        return [{"title": e["title"], "url": e["url"]} for e in _CANON]

    def fetch_all(self, delay: float = 1.5):
        essays = self.get_essay_urls()
        manifest = self.load_manifest()
        print(
            f"[{self.name}] {len(essays)} essays in canon, {len(manifest)} already cached"
        )

        session = requests.Session()
        session.headers.update(_HEADERS)

        for i, essay in enumerate(essays):
            slug = self.slug_from_url(essay["url"])
            if slug in manifest:
                continue

            print(f"  [{i+1}/{len(essays)}] {essay['title']}")
            try:
                r = session.get(essay["url"], timeout=20)
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"    SKIP (error: {e})")
                continue

            (self.cache_dir() / f"{slug}.html").write_text(r.text, encoding="utf-8")
            manifest[slug] = {
                "title": essay["title"],
                "url": essay["url"],
                "author": _SLUG_AUTHOR.get(slug, ""),
            }
            self.save_manifest(manifest)
            _time.sleep(delay)

        print(f"[{self.name}] Done. {len(manifest)} essays cached.")


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class Processor(BlogProcessor):
    name = "marginalrevolution"

    _STRIP_CLASSES = [
        "sharedaddy",
        "jp-relatedposts",
        "wpcnt",
        "mru-widget",
        "mercatus-widget",
    ]

    def extract_markdown(self, html: str, author: str = "") -> str:  # type: ignore[override]
        soup = BeautifulSoup(html, "html.parser")

        # Title
        title_tag = soup.find("h1", class_="entry-title")
        if not title_tag:
            return ""
        title = title_tag.get_text(strip=True)

        # Date
        date_str = ""
        time_tag = soup.find("time", class_="entry-date")
        if time_tag:
            dt_attr = time_tag.get("datetime", "")
            try:
                dt = datetime.strptime(dt_attr[:10], "%Y-%m-%d")
                date_str = dt.strftime("%B %Y")
            except ValueError:
                pass

        # Article body
        content = soup.find("div", class_="entry-content")
        if not content:
            return ""

        # Reject posts that are nearly entirely block-quoted external content.
        # Threshold is high (90%) because canon posts often quote sources heavily
        # before adding commentary.
        total_words = len(content.get_text().split())
        quote_words = sum(
            len(bq.get_text().split()) for bq in content.find_all("blockquote")
        )
        if total_words and quote_words / total_words > 0.90:
            return ""

        # Remove injected promo / share widgets
        for cls in self._STRIP_CLASSES:
            for el in content.find_all(class_=cls):
                el.decompose()
        for tag in content.find_all(["script", "style"]):
            tag.decompose()

        # Strip alert/callout boxes and lone PDF-link paragraphs
        for p in content.find_all("p"):
            if p.get("class") and any("alert" in c for c in p.get("class", [])):
                p.decompose()
                continue
            links = p.find_all("a")
            if (
                len(links) == 1
                and links[0].get("href", "").endswith(".pdf")
                and p.get_text(strip=True) == links[0].get_text(strip=True)
            ):
                p.decompose()

        # Images: WordPress often wraps <img> in <a href="…">; converting <a> first
        # yields "[](url)" because the img has no link text. Unwrap to markdown images.
        for a in list(content.find_all("a")):
            imgs = a.find_all("img", recursive=False)
            if len(imgs) != 1:
                imgs = a.find_all("img")
            if len(imgs) != 1:
                continue
            img = imgs[0]
            anchor_text = a.get_text(strip=True)
            img_alt = (img.get("alt") or "").strip()
            if anchor_text and anchor_text != img_alt:
                continue
            src = (img.get("src") or a.get("href") or "").strip()
            if not src:
                continue
            alt_esc = img_alt.replace("]", "\\]")
            a.replace_with(f"![{alt_esc}]({src})")

        for img in list(content.find_all("img")):
            src = (img.get("src") or "").strip()
            if not src:
                img.decompose()
                continue
            alt_esc = (img.get("alt") or "").strip().replace("]", "\\]")
            img.replace_with(f"![{alt_esc}]({src})")

        # Convert inline markup
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

        for h in content.find_all(["h2", "h3", "h4"]):
            level = int(h.name[1])
            h.replace_with(f"\n\n{'#' * level} {h.get_text(strip=True)}\n\n")

        # Convert blockquotes to markdown > lines before serialisation
        for bq in content.find_all("blockquote"):
            bq_inner = str(bq)
            bq_inner = re.sub(r"<br\s*/?>", "\n", bq_inner)
            bq_inner = re.sub(r"<p[^>]*>", "\n\n", bq_inner)
            bq_text = BeautifulSoup(bq_inner, "html.parser").get_text()
            quoted_lines = []
            for line in bq_text.strip().splitlines():
                quoted_lines.append(f"> {line}" if line.strip() else ">")
            bq.replace_with("\n\n" + "\n".join(quoted_lines) + "\n\n")

        inner = str(content)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        inner = re.sub(r"<p[^>]*>", "\n\n", inner)
        md = BeautifulSoup(inner, "html.parser").get_text()

        lines = [line.rstrip() for line in md.splitlines()]
        md = "\n".join(lines)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        md = re.sub(r"(^|\s|\[)@([A-Za-z])", r"\1\\@\2", md, flags=re.MULTILINE)

        # Build the dateline: "January 2020 · Tyler Cowen"
        if date_str and author:
            dateline = f"{date_str} · {author}"
        elif date_str:
            dateline = date_str
        else:
            dateline = ""

        if dateline:
            return f"# {title}\n\n{dateline}\n\n{md}"
        return f"# {title}\n\n{md}"

    def process_all(self):
        """Override to pass author from manifest into extract_markdown."""
        manifest = self.load_manifest()
        processed = 0
        skipped = 0

        for slug, meta in manifest.items():
            html_file = self.cache_dir() / f"{slug}.html"
            if not html_file.exists():
                continue

            author = meta.get("author") or _SLUG_AUTHOR.get(slug, "")
            md = self.extract_markdown(
                html_file.read_text(encoding="utf-8"), author=author
            )
            if not md.strip():
                skipped += 1
                continue

            md = _split_inline_markdown_images(md)

            if slug in _KEEP_MARKDOWN_IMAGE_SLUGS:
                md = _render_images_as_centered_typst(
                    md, slug=slug, base_dir=self.base_dir()
                )
            else:
                md = _strip_markdown_images(md)

            (self.md_dir() / f"{slug}.md").write_text(md)
            meta["words"] = len(md.split())
            processed += 1

        self.save_manifest(manifest)
        total_words = sum(m.get("words", 0) for m in manifest.values())
        print(
            f"[{self.name}] {processed} processed, {skipped} skipped, "
            f"{total_words:,} words total."
        )


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class Scorer(BlogScorer):
    name = "marginalrevolution"

    def get_base_url(self) -> str:
        return "marginalrevolution.com"

    def get_recommended_slugs(self) -> set[str]:
        """All canon articles are recommended — ensures they score highly."""
        return set(_SLUG_AUTHOR.keys())
