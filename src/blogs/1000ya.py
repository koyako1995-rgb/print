import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "1000ya"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        # 【ここを修正】1夜からすべての目次が載っている完全版URL（vol=100）に変更します
        url = "https://1000ya.isis.ne.jp/souran/index.php?vol=100"
        
        response = requests.get(url)
        response.encoding = "utf-8" 
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 目次からすべての記事リンク（第1夜〜最新夜まで）をスキャン
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "1000ya.isis.ne.jp/" in href and href.endswith(".html"):
                title = a_tag.get_text(strip=True)
                if title and not title.isdigit() and "千夜千冊" not in title:
                    posts.append({
                        "title": title,
                        "url": href,
                        "title_len": len(title)
                    })
        
        # 【自動選別アルゴリズム】
        # 全1800マイル以上の記事から、タイトルが詳しく、情報量が多そうな記事を優先してソート
        posts.sort(key=lambda x: x["title_len"], reverse=True)
        
        # 全体の中から本当のトップ30件だけを厳選抽出
        top_posts = []
        for p in posts[:30]:
            top_posts.append({
                "title": p["title"],
                "url": p["url"]
            })
        
        print(f"[事前選別] 第1夜からすべての記事を対象に判定し、最も読み応えの期待値が高い「真のトップ {len(top_posts)} 件」を自動抽出しました。")
        return top_posts

class Processor(BlogProcessor):
    name = "1000ya"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", class_="main-content") or soup.find("body")
        return content.get_text() if content else ""

class Scorer(BlogScorer):
    name = "1000ya"

    def get_recommended_slugs(self) -> set[str]:
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
