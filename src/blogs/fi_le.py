"""fi-le.net writings — self-contained blog module.

Exposes: Source, Processor, Scorer, TOPICS, METADATA
"""

import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from base import DATA_DIR, BlogSource, BlogProcessor, BlogScorer

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

METADATA = {
    "title": "From the Blog",
    "author": "Lennart Finke",
    "cover_image": "images/8.png",
    "flat_chapters": True,
    "reverse_chronological": True,
}

# ---------------------------------------------------------------------------
# Clusters
# ---------------------------------------------------------------------------

TOPICS: dict[str, list[str]] = {
    "AI & Models": [
        "casuism",
        "asymptotics",
        "chomsky",
    ],
    "Technology & Interfaces": [
        "recommendationless",
        "spell",
    ],
    "Economics & Society": [
        "degrowth",
        "love",
        "margin",
        "keynes",
        "stonks",
        "air",
    ],
    "Culture & Practice": [
        "nobo",
        "travel",
        "japanese",
        "shoes",
        "pueckler",
    ],
    "History & Knowledge": [
        "hilbert",
        "squiggly",
    ],
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

_BASE = "https://fi-le.net"
_FEED_URL = "https://fi-le.net/feed.xml"
_EXCLUDE_SLUGS = {
    "oss",
    "baba",
    "pypi",
    "history",
    "stamps",
    "byzantine",
    "safety-blogs",
}


class Source(BlogSource):
    name = "fi_le"

    def get_essay_urls(self) -> list[dict]:
        r = requests.get(_FEED_URL, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "xml")

        seen: set[str] = set()
        essays = []
        for item in soup.find_all("item"):
            title_tag = item.find("title")
            link_tag = item.find("link")
            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(" ", strip=True)
            url = link_tag.get_text(strip=True)
            if not title or not url.startswith(_BASE + "/"):
                continue

            slug = self.slug_from_url(url)
            if slug in seen or slug in _EXCLUDE_SLUGS:
                continue
            seen.add(slug)
            essays.append({"title": title, "url": url})

        return essays


# ---------------------------------------------------------------------------
# Process
# ---------------------------------------------------------------------------


class Processor(BlogProcessor):
    name = "fi_le"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")

        article = soup.find("section") or soup.find("main") or soup.find("body")
        if not article:
            return ""

        og_url_tag = soup.find("meta", property="og:url")
        canon_url = (
            og_url_tag["content"]
            if og_url_tag and og_url_tag.get("content")
            else _BASE + "/"
        )

        title_tag = article.find("h1")
        if not title_tag:
            return ""
        title = title_tag.get_text(" ", strip=True)
        title_tag.decompose()

        date_str = ""
        subtitle = article.find(class_="subtitle")
        if subtitle:
            date_str = self._normalise_date(subtitle.get_text(" ", strip=True))
            subtitle.decompose()
        if not date_str:
            for candidate in article.find_all(["p", "h2", "h3", "h4"], limit=5):
                maybe_date = self._normalise_date(candidate.get_text(" ", strip=True))
                if maybe_date:
                    date_str = maybe_date
                    candidate.decompose()
                    break

        for el in article.find_all(["script", "style", "iframe", "form", "button"]):
            el.decompose()
        for el in article.find_all(["label", "input"], class_="margin-toggle"):
            el.decompose()
        for el in article.find_all(
            class_=["header", "footer", "github-box", "video-container"]
        ):
            el.decompose()

        for embed in article.find_all("embed"):
            src = embed.get("src", "").strip()
            if not src:
                embed.decompose()
                continue
            image_path = self._render_embed(canon_url, src)
            if image_path:
                embed.replace_with(
                    "\n\n```{=typst}\n"
                    f'#block(width: 100%)[#align(center)[#image("/{image_path}", width: 100%)]]\n'
                    "```\n\n"
                )
            else:
                embed.decompose()

        for email in article.find_all("div", class_="email-ui"):
            for a in email.find_all("a"):
                a.replace_with(a.get_text(" ", strip=True))
            subject = email.find(class_="email-subject")
            body = email.find(class_="email-body")
            email_text = []
            if subject:
                email_text.append(subject.get_text(" ", strip=True))
            if body:
                email_text.append(body.get_text("", strip=False).strip())
            if email_text:
                email.replace_with("\n\n```\n" + "\n\n".join(email_text) + "\n```\n\n")
            else:
                email.decompose()

        for sn in article.find_all("span", class_="sidenote"):
            sn.replace_with(f" ({sn.get_text(' ', strip=True)})")
        for mn in article.find_all("span", class_="marginnote"):
            mn.decompose()

        for img in article.find_all("img"):
            alt = img.get("alt", "").strip()
            img.replace_with(f"\n\nImage: {alt}\n\n" if alt else "")

        for fig in article.find_all("figure"):
            text = fig.get_text(" ", strip=True)
            if text:
                fig.replace_with(f"\n\n{text}\n\n")

        for bq in reversed(article.find_all("blockquote")):
            lines = bq.get_text("\n", strip=True).splitlines()
            quoted = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in lines)
            bq.replace_with(f"\n{quoted}\n")

        for tbl in reversed(article.find_all("table")):
            rows = tbl.find_all("tr")
            if not rows:
                tbl.decompose()
                continue
            md_rows = []
            for i, row in enumerate(rows):
                if i > 20:
                    break
                cells = [
                    td.get_text(" ", strip=True) for td in row.find_all(["th", "td"])
                ]
                if not cells:
                    continue
                md_rows.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    md_rows.append("| " + " | ".join("---" for _ in cells) + " |")
            tbl.replace_with("\n" + "\n".join(md_rows) + "\n")

        for a in article.find_all("a"):
            href = a.get("href", "")
            text = a.get_text(" ", strip=True)
            if href.startswith("#") or not href:
                a.replace_with(text)
            else:
                abs_href = urljoin(canon_url, href)
                if len(abs_href) > 500:
                    a.replace_with(text)
                else:
                    a.replace_with(f"[{text}]({abs_href})")

        for b in article.find_all(["b", "strong"]):
            b.replace_with(f"**{b.get_text(' ', strip=True)}**")
        for i in article.find_all(["i", "em"]):
            i.replace_with(f"*{i.get_text(' ', strip=True)}*")

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

        inner = str(article)
        inner = re.sub(r"<br\s*/?>", "\n", inner)
        inner = re.sub(r"<p[^>]*>", "\n\n", inner)
        inner = re.sub(r"<h2[^>]*>", "\n\n## ", inner)
        inner = re.sub(r"<h3[^>]*>", "\n\n### ", inner)
        inner = re.sub(r"<h[4-6][^>]*>", "\n\n#### ", inner)
        inner = re.sub(r"</h[1-6]>", "\n\n", inner)
        md = BeautifulSoup(inner, "html.parser").get_text()

        md = self._normalise_lines(md)
        md = re.sub(r"\n{3,}", "\n\n", md).strip()
        md = re.sub(r"(?m)^([A-HJ-Z])\s+([a-z])", r"\1\2", md)
        md = re.sub(r"(^|[\s\[(\"])@([A-Za-z_])", r"\1\\@\2", md, flags=re.MULTILINE)
        md = re.sub(r"(?m)(.+?)\s+•\s+•\s+•$", r"\1\n\n{{DOT_BREAK}}", md)
        md = re.sub(r"(?m)^•\s+•\s+•$", "{{DOT_BREAK}}", md)
        if title == "Air to Bread":
            md = re.sub(r"(?m)^(>.*) \[\.\.\.\]$", r"\1\n\n{{DOT_BREAK}}", md)
            md = md.replace("[...]", "{{DOT_BREAK}}")

        if date_str:
            return f"# {title}\n\n{date_str}\n\n{md}"
        return f"# {title}\n\n{md}"

    def _render_embed(self, canon_url: str, src: str) -> str:
        embed_url = urljoin(canon_url, src)
        slug = self._slug_from_canon_url(canon_url)
        stem = Path(src).stem
        media_dir = DATA_DIR / self.name / "media" / slug
        media_dir.mkdir(parents=True, exist_ok=True)
        png_path = media_dir / f"{stem}.png"
        html_path = media_dir / f"{stem}.html"

        if png_path.exists():
            return str(png_path.relative_to(DATA_DIR.parent))

        try:
            r = requests.get(embed_url, timeout=20)
            r.raise_for_status()
            html_path.write_text(r.text)

            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    executable_path="/opt/homebrew/bin/chromium",
                    args=["--no-sandbox"],
                )
                page = browser.new_page(
                    viewport={"width": 1100, "height": 520}, device_scale_factor=2
                )
                page.goto(
                    html_path.resolve().as_uri(),
                    wait_until="networkidle",
                    timeout=30000,
                )
                page.wait_for_selector(
                    ".plotly-graph-div svg, .plotly-graph-div canvas", timeout=30000
                )
                page.locator(".plotly-graph-div").screenshot(path=str(png_path))
                browser.close()
        except Exception as e:
            print(
                f"[{self.name}] Warning: could not render embedded figure {embed_url}: {e}"
            )
            return ""

        return str(png_path.relative_to(DATA_DIR.parent))

    @staticmethod
    def _slug_from_canon_url(canon_url: str) -> str:
        return canon_url.rstrip("/").split("/")[-1] or "index"

    @staticmethod
    def _normalise_date(raw_date: str) -> str:
        date = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1", raw_date)
        date = date.replace(",", " ")
        date = re.sub(r"\s+", " ", date).strip()
        for fmt in ("%d of %B %Y", "%B %d %Y"):
            try:
                return datetime.strptime(date, fmt).strftime("%B %Y")
            except ValueError:
                continue
        return ""

    @staticmethod
    def _normalise_lines(md: str) -> str:
        lines = [line.strip() for line in md.splitlines()]
        blocks: list[str] = []
        paragraph: list[str] = []
        code_block: list[str] = []
        in_code = False

        def flush_paragraph():
            if paragraph:
                blocks.append(" ".join(paragraph))
                paragraph.clear()

        for line in lines:
            if line.startswith("```"):
                if in_code:
                    code_block.append(line)
                    blocks.append("\n".join(code_block))
                    code_block.clear()
                    in_code = False
                else:
                    flush_paragraph()
                    code_block.append(line)
                    in_code = True
                continue
            if in_code:
                code_block.append(line)
                continue
            if not line:
                flush_paragraph()
                continue
            if re.match(r"^(#{1,6} |[-*] |\d+\. |> |\| |Image:)", line):
                flush_paragraph()
                if blocks and (
                    (line.startswith("| ") and blocks[-1].startswith("| "))
                    or (line.startswith("> ") and blocks[-1].startswith("> "))
                    or (line.startswith("- ") and blocks[-1].startswith("- "))
                    or (re.match(r"^\d+\. ", line) and re.match(r"^\d+\. ", blocks[-1]))
                ):
                    blocks[-1] += "\n" + line
                else:
                    blocks.append(line)
            else:
                paragraph.append(line)

        flush_paragraph()
        if code_block:
            blocks.append("\n".join(code_block))
        return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# Score
# ---------------------------------------------------------------------------


class Scorer(BlogScorer):
    name = "fi_le"

    def get_base_url(self) -> str:
        return "fi-le.net"

    def get_recommended_slugs(self) -> set[str]:
        # Slugs from fi-le.net/hn/, the author's popularity page for posts
        # that reached the Hacker News front page.
        return {
            "margin",
            "squiggly",
            "pueckler",
            "recommendationless",
            "stonks",
        }
