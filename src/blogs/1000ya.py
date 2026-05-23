import os
import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "1000ya"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        url = "https://1000ya.isis.ne.jp/souran/index.php?vol=102"
        response = requests.get(url)
        response.encoding = "utf-8" 
        soup = BeautifulSoup(response.content, "html.parser")
        
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if "1000ya.isis.ne.jp/" in href and href.endswith(".html"):
                title = a_tag.get_text(strip=True)
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
        content = soup.find("div", class_="main-content") or soup.find("body")
        return content.get_text() if content else ""

class Scorer(BlogScorer):
    name = "1000ya"

    def get_recommended_slugs(self) -> set[str]:
        """
        【自動選別アルゴリズム】
        ダウンロード済みのHTMLファイルの中から、文字数が多く（中谷宇吉郎などの名作、
        あるいは内容が濃いもの）、かつノイズでない上位30件を自動で抽出します。
        """
        html_dir = os.path.join("data", "1000ya", "html")
        if not os.path.exists(html_dir):
            return set()

        scored_posts = []
        for filename in os.listdir(html_dir):
            if not filename.endswith(".html"):
                continue
            
            slug = filename.replace(".html", "")
            file_path = os.path.join(html_dir, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                
                # 文字数を「読み応え（価値）」の基準として簡易計算
                word_count = len(html_content)
                
                # あまりに短すぎるインデックスページや、バグファイルを自動除外
                if word_count > 5000:
                    scored_posts.append((slug, word_count))
            except Exception:
                continue

        # 文字数（内容の濃さ）が多い順に並び替える
        scored_posts.sort(key=lambda x: x[1], reverse=True)
        
        # 上位30件だけを「印刷に値する記事」として自動抽出！
        top_30_slugs = {slug for slug, score in scored_posts[:30]}
        
        print(f"[自動抽出] 1000個以上の記事から、読み応えのある上位 {len(top_30_slugs)} 件を自動選別しました。")
        return top_30_slugs

    def get_base_url(self) -> str:
        return "1000ya.isis.ne.jp"

TOPICS = {"All Essays": []}
METADATA = {
    "title": "松岡正剛の千夜千冊",
    "author": "松岡正剛",
    "cover_image": None
}
