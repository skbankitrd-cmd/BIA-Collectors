import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FSCCollector:
    """金管會新聞稿採集器 (HTML 爬取版)"""
    # 直接爬取新聞列表網頁，避免 RSS 轉向問題
    LIST_URL = "https://www.fsc.gov.tw/ch/home.jsp?id=2&parentpath=0"
    BASE_URL = "https://www.fsc.gov.tw"

    async def fetch_rss_entries(self) -> List[Dict[str, Any]]:
        """獲取新聞列表 (改為解析 HTML)"""
        logger.info(f"正在從 {self.LIST_URL} 爬取新聞列表...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
                response = await client.get(self.LIST_URL, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                entries = []
                
                # 尋找新聞列表區域 (通常在 .news_list 或 table 內)
                # 根據金管會結構，尋找帶有標題的 <a> 標籤
                links = soup.select('.news_list a, .page_content a[title], .list_table a')
                
                for link in links:
                    title = link.get('title') or link.text.strip()
                    href = link.get('href')
                    
                    if not href or 'jsp?id=' not in href:
                        continue
                        
                    # 處理相對路徑
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}/ch/{href}"
                    
                    # 避免抓到重複的連結
                    if any(e['url'] == full_url for e in entries):
                        continue
                        
                    entries.append({
                        "title": title,
                        "url": full_url,
                        "published_date": datetime.now().strftime("%Y-%m-%d"), # 列表若無日期則填今日
                    })
                
                logger.info(f"成功爬取到 {len(entries)} 條新聞項目。")
                return entries
            except Exception as e:
                logger.error(f"爬取新聞列表失敗: {e}")
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
