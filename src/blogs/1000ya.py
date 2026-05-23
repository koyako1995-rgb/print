import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "1000ya"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        # 全1800夜以上が網羅されているインデックスページ
        url = "https://1000ya.isis.ne.jp/souran/index.php?vol=100"
        
        response = requests.get(url)
        response.encoding = "utf-8" 
        soup = BeautifulSoup(response.content, "html.parser")
        
        # vol=100のページ構造（aタグのhref属性）に最適化したスキャン
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            
            # 各「夜」の記事リンクのパターン（相対パスや絶対パスの揺らぎに対応）
            if "1000ya.isis.ne.jp/" in href or href.startswith("/") or href.endswith(".html"):
                title = a_tag.get_text(strip=True)
                
                # 不要なナビゲーションや数字だけのリンクを除外
                if title and not title.isdigit() and "千夜千冊" not in title and len(title) > 2:
                    # 正しいURLの形に整形
                    full_url = href
                    if not href.startswith("http"):
                        if href.startswith("/"):
                            full_url = f"https://1000ya.isis.ne.jp{href}"
                        else:
                            full_url = f"https://1000ya.isis.ne.jp/souran/{href}"
                            
                    posts.append({
                        "title": title,
                        "url": full_url,
                        "title_len": len(title)
                    })
        
        # 重複するリンクを綺麗に排除
        unique_posts = {p["url"]: p for p in posts}.values()
        posts = list(unique_posts)

        # 【自動選別アルゴリズム】 タイトルの文字数が長い（情報が最も詰まっている）順にソート
        posts.sort(key=lambda x: x["title_len"], reverse=True)
        
        # 上位30件を厳選
        top_posts = posts[:30]
        
        print(f"[事前選別] 全歴史から読み応え（情報量）の期待値が高い「真のトップ {len(top_posts)} 件」を自動抽出しました。")
        return [{"title": p["title"], "url": p["url"]} for p in top_posts]

class Processor(BlogProcessor):
    name = "1000ya"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        # 千夜千冊の本編テキストが格納されている一般的なエリアを広くカバー
        content = soup.find("div", class_="main-content") or soup.find("div", id="main") or soup.find("body")
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
