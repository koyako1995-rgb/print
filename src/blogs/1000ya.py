import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "1000ya"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        # 目次ページURL
        url = "https://1000ya.isis.ne.jp/souran/index.php?vol=102"
        
        response = requests.get(url)
        response.encoding = "utf-8" 
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 目次からリンクをスキャン
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "1000ya.isis.ne.jp/" in href and href.endswith(".html"):
                title = a_tag.get_text(strip=True)
                if title and not title.isdigit() and "千夜千冊" not in title:
                    posts.append({
                        "title": title,
                        "url": href
                    })
        
        # 【ここが秘密兵器！】
        # 1000以上ある記事リストの中から、最新の「上位30件だけ」にバッサリ切り落とします
        filtered_posts = posts[:30]
        
        print(f"[事前選別] 目次にある膨大な記事から、最新の {len(filtered_posts)} 件だけをダウンロード対象に指定しました。")
        return filtered_posts

class Processor(BlogProcessor):
    name = "1000ya"

    def extract_markdown(self, html: str) -> str:
        # 30個しかダウンロードされないので、シンプルに中身をパースするだけでOKになります
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", class_="main-content") or soup.find("body")
        return content.get_text() if content else ""

class Scorer(BlogScorer):
    name = "1000ya"

    def get_recommended_slugs(self) -> set[str]:
        # すでにSource段階で30個に絞られているため、ここはすべて通してOKになります
        html_dir = "data/1000ya/html"
        import os
        if not os.path.exists(html_dir):
            return set()
        return {f.replace(".html", "") for f in os.listdir(html_dir) if f.endswith(".html")}

    def get_base_url(self) -> str:
        return "1000ya.isis.ne.jp"

TOPICS = {"All Essays": []}
METADATA = {
    "title": "松岡正剛の千夜千冊",
    "author": "松岡正剛",
    "cover_image": None
}
