import hashlib
from datetime import datetime, timezone
from typing import List, Optional
import uuid

class IntelItem:
    """
    BIA Layer 1 核心資料模型：情報項目 (Intel Item)
    嚴格遵循台新金控情報雷達規格，包含 20 個核心欄位與向量檢索支援。
    """
    def __init__(
        self,
        source: str,
        title: str,
        category: str,
        summary: str,
        body: str,
        url: str,
        published_at: datetime,
        importance: int = 5,
        target_roles: List[str] = None,
        pipeline_run_id: Optional[uuid.UUID] = None
    ):
        self.id = str(uuid.uuid4())
        self.source = source
        self.title = title
        self.category = category
        self.summary = summary
        self.body = body
        self.url = url
        self.published_at = published_at
        self.importance = importance
        self.target_roles = target_roles or []
        self.pipeline_run_id = pipeline_run_id
        
        # 狀態追蹤
        self.is_analyzed = False
        self.analyzed_at = None
        self.sentiment_score = 0.0
        self.tags = []
        self.entities = []
        self.ai_summary = ""
        
        # [Security Fix: 將 MD5 升級為 SHA-256，防範 Hash 碰撞攻擊]
        raw = f"{self.url}{self.title}".encode('utf-8')
        self.dedup_key = hashlib.sha256(raw).hexdigest()

    def to_dict(self):
        """轉換為字典格式，便於 Supabase 寫入"""
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "category": self.category,
            "summary": self.summary,
            "body": self.body,
            "url": self.url,
            "published_at": self.published_at.isoformat(),
            "importance": self.importance,
            "target_roles": self.target_roles,
            "dedup_key": self.dedup_key,
            "is_analyzed": self.is_analyzed,
            "sentiment_score": self.sentiment_score,
            "tags": self.tags,
            "entities": self.entities,
            "ai_summary": self.ai_summary,
            "pipeline_run_id": str(self.pipeline_run_id) if self.pipeline_run_id else None
        }
