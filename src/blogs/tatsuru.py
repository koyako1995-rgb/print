from datetime import datetime
import requests
from bs4 import BeautifulSoup
from src.base import BaseBlog  # 実際の基底クラスのパスに合わせてください

class TatsuruBlog(BaseBlog):
    # プログラムが識別するためのユニークなIDとURLを設定
    id = "tatsuru"
    base_url = "http://blog.tatsuru.com/"

    def get_all_posts(self):
        """
        すべての記事、またはアーカイブから記事のURL、タイトル、日付の一覧を取得する
        """
        posts = []
        # 例として、トップページやバックナンバーのページを取得
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 内田樹氏のブログのHTML構造に合わせてリンク（aタグ）を抽出
        # 例: サイドバーの最近のエントリやアーカイブからURLを拾うロジックをここに書きます
        for a_tag in soup.find_all("a", href=True):
            if "blog.tatsuru.com/" in a_tag["href"] and a_tag["href"].endswith(".html"):
                url = a_tag["href"]
                title = a_tag.get_text(strip=True)
                # 仮の日付
                date = datetime.now() 
                
                posts.append({
                    "url": url,
                    "title": title,
                    "date": date
                })
        return posts

    def fetch_post_content(self, url):
        """
        特定の記事ページから、本文（HTML/テキスト）を抽出する
        """
        response = requests.get(url)
        # サイトの文字コード（EUC-JPやShift_JIS、UTF-8など）に合わせてデコード
        # 内田樹氏のブログは古いデザインの場合、文字化けに注意が必要です
        response.encoding = response.apparent_encoding 
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 内田樹氏のブログの本文が入っているdivタグを特定します
        # 通常、class="content" や id="center"、あるいは特定のテーブルの中にあります
        # ここで不要なサイドバー、コメント、広告、ナビゲーション等を除去（extract）します
        
        content_div = soup.find("div", class_="content") # ※実際の構造に合わせて変更してください
        
        if content_div:
            return str(content_div)
        return ""
