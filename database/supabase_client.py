import os
import logging
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseDB:
    """Supabase 資料庫操作層"""
    def __init__(self, url: str = None, key: str = None):
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") # 需要具備寫入權限的 key
        
        if not self.url or not self.key:
            raise ValueError("未設置 SUPABASE_URL 或 SUPABASE_SERVICE_ROLE_KEY")
        
        self.client: Client = create_client(self.url, self.key)

    def is_news_exists(self, url: str) -> bool:
        """根據 URL 檢查新聞是否已存在 (對齊規範使用 intel_items)"""
        response = self.client.table("intel_items").select("id").eq("url", url).execute()
        return len(response.data) > 0

    def get_role_mapping(self) -> Dict[str, str]:
        """獲取角色名稱對應的 UUID"""
        response = self.client.table("user_roles").select("role_id, role_name").execute()
        return {item["role_name"]: item["role_id"] for item in response.data}

    def insert_intelligence(self, data: Dict[str, Any], pipeline_run_id: str = None):
        """將分析後的資料寫入資料庫 (完全遵照天條規範)"""
        try:
            # 計算去重金鑰 (MD5 32字元)
            raw_key = data.get("title", "") + data.get("url", "")
            dedup_key = hashlib.md5(raw_key.encode('utf-8')).hexdigest()

            # 轉換角色名稱為 UUID
            role_map = self.get_role_mapping()
            target_roles_uuids = [role_map.get(role) for role in data.get("target_roles", []) if role in role_map]
            
            # 準備插入資料 (對齊 2.1 intel_items 核心欄位)
            payload = {
                "dedup_key": dedup_key,
                "source": data["source_name"][:60],
                "url": data["url"],
                "title": data["title"],
                "body": data.get("raw_content", ""),
                "summary": data["summary"],
                "category": "scrape", # 預設為 scrape
                "published_at": data["published_date"],
                "fetched_at": datetime.now().isoformat(),
                "analyzed_at": datetime.now().isoformat(),
                "importance": data["importance_score"],
                "sentiment_score": data.get("sentiment_score", 0),
                "entities": data.get("entities", []),
                "tags": data.get("tags", []),
                "ai_summary": data.get("ai_summary", ""),
                "is_analyzed": True,
                "pipeline_run_id": pipeline_run_id,
                "embedding": data["embedding"]
            }
            
            result = self.client.table("intel_items").insert(payload).execute()
            logger.info(f"成功存入新聞 (天條版): {data['title']}")
            return result
        except Exception as e:
            logger.error(f"存入 Supabase 失敗: {e}")
            return None

if __name__ == "__main__":
    # 測試用範例 (需先設定環境變數)
    db = SupabaseDB()
    exists = db.is_news_exists("https://test.com/news1")
    print(f"URL 是否已存在: {exists}")
    role_map = db.get_role_mapping()
    print(f"角色對照表: {role_map}")
