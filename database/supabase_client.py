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

    def batch_check_exists(self, urls: List[str]) -> List[str]:
        """批次檢查多個 URL 是否已存在，回傳已存在的 URL 列表"""
        if not urls: return []
        try:
            # 使用 in_ 查詢一次抓回所有符合的紀錄
            response = self.client.table("intel_items").select("url").in_("url", urls).execute()
            return [item["url"] for item in response.data]
        except Exception as e:
            logger.error(f"批次 URL 檢查失敗: {e}")
            return []

    def get_role_mapping(self) -> Dict[str, str]:
        """獲取角色名稱對應的 UUID"""
        response = self.client.table("user_roles").select("role_id, role_name").execute()
        return {item["role_name"]: item["role_id"] for item in response.data}

    def get_user_preferences(self, role_name: str) -> Dict[str, Any]:
        """獲取指定角色的個性化喜好"""
        try:
            # 假設有一個 user_preferences 資料表，以 role_name 為 key
            response = self.client.table("user_preferences").select("*").eq("role_name", role_name).execute()
            return response.data[0] if response.data else {}
        except Exception:
            return {}

    def update_user_preferences(self, role_name: str, preferences: Dict[str, Any]) -> bool:
        """更新指定角色的個性化喜好 (Upsert)"""
        try:
            from datetime import datetime, timezone
            payload = {"role_name": role_name, **preferences, "updated_at": datetime.now(timezone.utc).isoformat()}
            self.client.table("user_preferences").upsert(payload, on_conflict="role_name").execute()
            logger.info(f"成功更新 {role_name} 的個性化喜好。")
            return True
        except Exception as e:
            logger.error(f"更新喜好失敗: {e}")
            return False

    def query_intelligence(self, query: str = None, category: str = None, role_name: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        [Agent Skill 專用] 查詢情報資料表 (intel_items)
        """
        try:
            # 移除 target_roles 欄位以避免 400 錯誤
            builder = self.client.table("intel_items").select("title, summary, importance, category, published_at, url")
            
            # 1. 關鍵字過濾 (僅針對標題，避免欄位名稱錯誤)
            if query:
                builder = builder.ilike("title", f"%{query}%")
            
            # 2. 類別過濾
            if category:
                builder = builder.eq("category", category)
            
            # 3. 排序與數量
            builder = builder.order("published_at", desc=True).limit(limit)
            
            result = builder.execute()
            data = result.data
            
            # 4. 角色過濾 (Post-processing)
            if role_name:
                role_map = self.get_role_mapping()
                target_role_id = role_map.get(role_name)
                if target_role_id:
                    # 過濾出 target_roles 為空 (公開) 或 包含目標角色 ID 的項目
                    data = [
                        item for item in data 
                        if not item.get("target_roles") or target_role_id in item["target_roles"]
                    ]
            
            return data
        except Exception as e:
            logger.error(f"查詢 intel_items 失敗: {e}")
            return []

    def insert_intel_item(self, item: Any, embedding: List[float] = None):
        """將 IntelItem 物件寫入資料庫 (含自動欄位校驗)"""
        try:
            payload = item.to_dict()
            if embedding:
                payload["embedding"] = embedding

            # --- [容錯修復: 動態過濾掉資料庫中不存在的欄位] ---
            # 這裡我們手動定義一個「保險欄位名單」
            safe_columns = [
                "id", "source", "title", "category", "summary", "body", "url", 
                "published_at", "importance", "dedup_key", "is_analyzed", 
                "sentiment_score", "tags", "entities", "ai_summary", "pipeline_run_id", "embedding"
            ]
            final_payload = {k: v for k, v in payload.items() if k in safe_columns}
            # ---------------------------------------------

            result = self.client.table("intel_items").upsert(final_payload, on_conflict="dedup_key").execute()
            logger.info(f"成功存入情報: {item.title[:30]}...")
            return result
        except Exception as e:
            logger.error(f"存入 intel_items 失敗: {e}")
            return None


if __name__ == "__main__":
    # 測試用範例 (需先設定環境變數)
    db = SupabaseDB()
    exists = db.is_news_exists("https://test.com/news1")
    print(f"URL 是否已存在: {exists}")
    role_map = db.get_role_mapping()
    print(f"角色對照表: {role_map}")
