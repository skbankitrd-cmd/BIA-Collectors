import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FSCCollector:
    """金管會新聞稿採集器"""
    # 更換為更穩定的 RSS 端點 (參考技術手冊)
    RSS_URL = "https://www.fsc.gov.tw/ch/news/rss.aspx"

    async def fetch_rss_entries(self) -> List[Dict[str, Any]]:
        """獲取 RSS 列表 (加入 User-Agent 偽裝)"""
        logger.info(f"正在從 {self.RSS_URL} 獲取 RSS 列表...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # 偽裝成一般瀏覽器，避免被擋
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = await client.get(self.RSS_URL, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                # 使用 feedparser 解析抓回來的內容
                feed = feedparser.parse(response.text)
                entries = []
                for entry in feed.entries:
                    entries.append({
                        "title": entry.title,
                        "url": entry.link,
                        "published_date": entry.published if hasattr(entry, 'published') else None,
                    })
                logger.info(f"成功獲取到 {len(entries)} 條新聞項目。")
                return entries
            except Exception as e:
                logger.error(f"獲取 RSS 列表失敗: {e}")
                return []

    async def fetch_full_content(self, url: str) -> str:
        """獲取新聞稿詳細內容"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 針對金管會官網的內容區域進行抓取
                content_div = soup.find('div', class_='content_block') or \
                              soup.find('div', id='content') or \
                              soup.find('div', class_='page_content')
                
                if content_div:
                    for tag in content_div(['script', 'style']):
                        tag.decompose()
                    return content_div.get_text(separator='\n', strip=True)
                return ""
            except Exception as e:
                logger.error(f"獲取新聞內容失敗 ({url}): {e}")
                return ""

    async def collect_recent_news(self, limit: int = 5) -> List[Dict[str, Any]]:
        """採集最近的新聞並包含完整內容"""
        # 注意：這裡改為 await
        entries = await self.fetch_rss_entries()
        results = []
        for entry in entries[:limit]:
            content = await self.fetch_full_content(entry["url"])
            entry["raw_content"] = content
            entry["source_name"] = "金管會"
            results.append(entry)
        return results

if __name__ == "__main__":
    import asyncio
    collector = FSCCollector()
    news = asyncio.run(collector.collect_recent_news(limit=2))
    for n in news:
        print(f"標題: {n['title']}")
        print(f"內文長度: {len(n['raw_content'])}")
        print("-" * 20)
