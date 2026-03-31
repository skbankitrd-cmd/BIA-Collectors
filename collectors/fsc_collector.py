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
    RSS_URL = "https://www.fsc.gov.tw/ch/home.jsp?id=2&parentpath=0&mcustomize=news_rss.jsp"

    def fetch_rss_entries(self) -> List[Dict[str, Any]]:
        """獲取 RSS 列表"""
        logger.info(f"正在從 {self.RSS_URL} 獲取 RSS 列表...")
        feed = feedparser.parse(self.RSS_URL)
        entries = []
        for entry in feed.entries:
            entries.append({
                "title": entry.title,
                "url": entry.link,
                "published_date": entry.published if hasattr(entry, 'published') else None,
            })
        logger.info(f"獲取到 {len(entries)} 條新聞項目。")
        return entries

    async def fetch_full_content(self, url: str) -> str:
        """獲取新聞稿詳細內容"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 針對金管會官網的內容區域進行抓取
                # 通常在 .content_block 或特定 ID 的 div 中
                content_div = soup.find('div', class_='content_block') or \
                              soup.find('div', id='content') or \
                              soup.find('div', class_='page_content')
                
                if content_div:
                    # 移除不必要的標籤 (script, style)
                    for tag in content_div(['script', 'style']):
                        tag.decompose()
                    return content_div.get_text(separator='\n', strip=True)
                return ""
            except Exception as e:
                logger.error(f"獲取新聞內容失敗 ({url}): {e}")
                return ""

    async def collect_recent_news(self, limit: int = 5) -> List[Dict[str, Any]]:
        """採集最近的新聞並包含完整內容"""
        entries = self.fetch_rss_entries()
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
