import requests
from bs4 import BeautifulSoup
from base import BlogSource, BlogProcessor, BlogScorer

class Source(BlogSource):
    name = "1000ya"

    def get_essay_urls(self) -> list[dict]:
        posts = []
        # 全1800夜以上が1ページに網羅されている目次URL
        url = "https://1000ya.isis.ne.jp/souran/index.php?vol=100"
        
        response = requests.get(url)
        response.encoding = "utf-8" 
        soup = BeautifulSoup(response.content, "html.parser")
        
        # ページ内のすべてのリンクをチェック
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            title = a_tag.get_text(strip=True)
            
            # 末尾が「.html」で終わるリンク、または数字が含まれる記事リンクを広く拾う
            if href.endswith(".html") or "1000ya.isis.ne.jp" in href:
                # ナビゲーション用の不要な文字列や数字だけのリンクを完全に除外
                if title and not title.isdigit() and "千夜千冊" not in title and len(title) > 3:
                    
                    # URLの形式を正しい絶対パスに整形する
                    full_url = href
                    if not href.startswith("http"):
                        # 相対パスの揺らぎをすべて吸収します
                        clean_href = href.lstrip("./").lstrip("/")
                        if "souran" in clean_href:
                            full_url = f"https://1000ya.isis.ne.jp/{clean_href}"
                        else:
                            full_url = f"https://1000ya.isis.ne.jp/souran/{clean_href}"
                            
                    posts.append({
                        "title": title,
                        "url": full_url,
                        "title_len": len(title)  # タイトルの文字数を「情報の濃さ」のスコアにする
                    })
        
        # 重複して拾ってしまったリンクを綺麗に1本化
        unique_posts = {}
        for p in posts:
            unique_posts[p["url"]] = p
        
        valid_posts = list(unique_posts.values())

        # 【自動選別アルゴリズム】タイトルの文字数が長い（本の情報が最も濃い）順に並び替え
        valid_posts.sort(key=lambda x: x["title_len"], reverse=True)
        
        # 全歴史の中から、上位30件だけを厳選
        top_posts = valid_posts[:30]
        
        print(f"[事前選別] 全歴史から読み応え（情報量）の期待値が高い「真のトップ {len(top_posts)} 件」を自動抽出しました。")
        return [{"title": p["title"], "url": p["url"]} for p in top_posts]

class Processor(BlogProcessor):
    name = "1000ya"

    def extract_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        # 本文エリアを広く抽出
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
