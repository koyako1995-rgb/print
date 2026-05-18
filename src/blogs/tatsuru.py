from datetime import datetime
import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "tatsuru"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        response = requests.get("http://blog.tatsuru.com/")
        # 文字化け対策
        response.encoding = response.apparent_encoding 
        soup = BeautifulSoup(response.content, "html.parser")

        for a_tag in soup.find_all("a", href=True):
            if "blog.tatsuru.com/" in a_tag["href"] and a_tag["href"].endswith(".html"):
                posts.append({
                    "title": a_tag.get_text(strip=True) or "No Title",
                    "url": a_tag["href"]
                })
        return posts

class Processor(BlogProcessor):
    name = "tatsuru"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        # 本文が入っている主要な部分を簡易的に抽出
        content = soup.find("div", class_="content") or soup.find("body")
        return content.get_text() if content else ""

class Scorer(BlogScorer):
    name = "tatsuru"

    def get_recommended_slugs(self) -> set[str]:
        return set()

    def get_base_url(self) -> str:
        return "blog.tatsuru.com"

TOPICS = {"All Essays": []}
METADATA = {
    "title": "内田樹の研究室",
    "author": "内田樹",
    "cover_image": None
}
