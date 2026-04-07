import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List, Optional
import logging
import uuid
from models.intel_item import IntelItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MacroCollector:
    """中央銀行新聞稿採集器 (總體經濟情報)"""
    LIST_URL = "https://www.cbc.gov.tw/tw/lp-302-1.html"
    BASE_URL = "https://www.cbc.gov.tw"

    def __init__(self, pipeline_run_id: Optional[uuid.UUID] = None):
        self.pipeline_run_id = pipeline_run_id or uuid.uuid4()

    async def fetch_news_entries(self) -> List[dict]:
        """獲取中央銀行新聞列表"""
        logger.info(f"正在從 {self.LIST_URL} 採集總經新聞列表...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = await client.get(self.LIST_URL, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                entries = []
                
                # 央行列表通常在 class 為 'list' 的 div 中
                list_area = soup.find('div', class_='list') or soup
                links = list_area.select('a[title]')
                
                for link in links:
                    title = link.get('title', '').strip()
                    href = link.get('href', '').strip()
                    
                    if not href or 'cp-302-' not in href: continue
                    
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}/tw/{href}"
                    if any(e['url'] == full_url for e in entries): continue
                        
                    entries.append({
                        "title": title,
                        "url": full_url,
                    })
                
                return entries
            except Exception as e:
                logger.error(f"中央銀行列表採集失敗: {e}")
                return []

    async def fetch_full_content(self, url: str) -> str:
        """獲取新聞全文內容"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 央行全文通常在 class 為 'cp' 或 'content' 的 div 中
                content_div = soup.find('div', class_='cp') or \
                              soup.find('section', class_='cp') or \
                              soup.find('div', id='content')
                
                if content_div:
                    # 移除不必要的標籤
                    for tag in content_div(['script', 'style', 'nav']): tag.decompose()
                    return content_div.get_text(separator='\n', strip=True)
                return ""
            except Exception as e:
                logger.error(f"獲取中央銀行內容失敗 ({url}): {e}")
                return ""

    async def collect_intel(self, limit: int = 5) -> List[IntelItem]:
        """執行採集並封裝為 IntelItem 物件"""
        entries = await self.fetch_news_entries()
        items = []
        
        for entry in entries[:limit]:
            body = await self.fetch_full_content(entry["url"])
            
            # 建立符合規範的 IntelItem
            item = IntelItem(
                source="中央銀行",
                title=entry["title"],
                category="scrape",
                summary=body[:600],
                body=body,
                url=entry["url"],
                published_at=datetime.now(timezone.utc),
                pipeline_run_id=self.pipeline_run_id
            )
            items.append(item)
            
        logger.info(f"Macro 採集完成，共計 {len(items)} 筆標準化物件。")
        return items

if __name__ == "__main__":
    import asyncio
    collector = MacroCollector()
    items = asyncio.run(collector.collect_intel(limit=2))
    for item in items:
        print(f"Title: {item.title}")
        print(f"Source: {item.source}")
        print("-" * 20)
