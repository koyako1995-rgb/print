from datetime import datetime
import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "1000ya"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        # ご提示いただいた「全読譜（vol=102）」のURLを指定します
        url = "https://1000ya.isis.ne.jp/souran/index.php?vol=102"
        
        response = requests.get(url)
        # 千夜千冊のサイトの文字コード（UTF-8）を設定
        response.encoding = "utf-8" 
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # ページ内のリンクから、各「夜」の記事へのリンク（例: /1000夜/xxx.html）を探します
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # 記事のURLのパターンに一致するものを抽出
            if "1000ya.isis.ne.jp/" in href and href.endswith(".html"):
                title = a_tag.get_text(strip=True)
                # タイトルが空でなく、目次のノイズを除外
                if title and not title.isdigit() and "千夜千冊" not in title:
                    posts.append({
                        "title": title,
                        "url": href
                    })
        return posts

class Processor(BlogProcessor):
    name = "1000ya"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        # 本文が書かれている主要なエリア（千夜千冊の標準的なクラス名など）を抽出
        content = soup.find("div", class_="main-content") or soup.find("body")
        return content.get_text() if content else ""

class Scorer(BlogScorer):
    name = "1000ya"

    def get_recommended_slugs(self) -> set[str]:
        return set()

    def get_base_url(self) -> str:
        return "1000ya.isis.ne.jp"

TOPICS = {"All Essays": []}
METADATA = {
    "title": "松岡正剛の千夜千冊",
    "author": "松岡正剛",
    "cover_image": None
}
