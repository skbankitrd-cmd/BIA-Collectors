import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List, Optional
import logging
import uuid
from models.intel_item import IntelItem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FSCCollector:
    """金管會新聞稿採集器 (符合 Layer 1 規範)"""
    LIST_URL = "https://www.fsc.gov.tw/ch/home.jsp?id=2&parentpath=0"
    BASE_URL = "https://www.fsc.gov.tw"

    def __init__(self, pipeline_run_id: Optional[uuid.UUID] = None):
        self.pipeline_run_id = pipeline_run_id or uuid.uuid4()

    async def fetch_news_entries(self) -> List[dict]:
        """獲取新聞列表"""
        logger.info(f"正在從 {self.LIST_URL} 採集新聞列表...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = await client.get(self.LIST_URL, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                entries = []
                
                content_area = soup.find('div', id='content') or soup.find('div', class_='page_content') or soup
                links = content_area.select('a[title]')
                
                for link in links:
                    title = link.get('title', '').strip()
                    href = link.get('href', '').strip()
                    
                    if not href or 'id=' not in href: continue
                    if any(x in title for x in ['回首頁', '網站導覽', 'English', '常見問答', '聯絡我們', '機關介紹']): continue
                    if 'parentpath=0,2' not in href and 'id=2&' not in href and 'id=17&' not in href: continue
                    
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}/ch/{href}"
                    if any(e['url'] == full_url for e in entries): continue
                        
                    entries.append({
                        "title": title,
                        "url": full_url,
                    })
                
                return entries
            except Exception as e:
                logger.error(f"採集列表失敗: {e}")
                return []

    async def fetch_full_content(self, url: str) -> str:
        """獲取詳細全文內容"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                content_div = soup.find('div', class_='content_block') or \
                              soup.find('div', id='content') or \
                              soup.find('div', class_='page_content')
                
                if content_div:
                    for tag in content_div(['script', 'style']): tag.decompose()
                    return content_div.get_text(separator='\n', strip=True)
                return ""
            except Exception as e:
                logger.error(f"獲取內容失敗 ({url}): {e}")
                return ""

    async def collect_intel(self, limit: int = 5) -> List[IntelItem]:
        """執行採集並封裝為 IntelItem 物件"""
        entries = await self.fetch_news_entries()
        items = []
        
        for entry in entries[:limit]:
            body = await self.fetch_full_content(entry["url"])
            
            # 建立符合規範的 IntelItem
            item = IntelItem(
                source="金管會",
                title=entry["title"],
                category="scrape",           # HTML 爬取歸類為 scrape
                summary=body[:600],          # 手冊規範: summary 取前 600 字
                body=body,
                url=entry["url"],
                published_at=datetime.now(timezone.utc), # 預設當前，稍後由分析器校準
                pipeline_run_id=self.pipeline_run_id
            )
            items.append(item)
            
        logger.info(f"FSC 採集完成，共計 {len(items)} 筆標準化物件。")
        return items

if __name__ == "__main__":
    import asyncio
    collector = FSCCollector()
    items = asyncio.run(collector.collect_intel(limit=2))
    for item in items:
        print(f"DedupKey: {item.dedup_key}")
        print(f"Title: {item.title}")
        print("-" * 20)
