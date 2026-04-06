import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Any

@dataclass
class IntelItem:
    # --- 必填欄位 (採集器填入) ---
    source: str
    title: str
    category: str = "rss"  # rss / scrape / api
    summary: str = ""
    body: str = ""         # 全文 (爬蟲才有)
    url: str = ""
    published_at: Optional[datetime] = None
    
    # --- 系統自動生成欄位 ---
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    dedup_key: str = field(default="")
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=90))
    pipeline_run_id: Optional[uuid.UUID] = None
    
    # --- 分析結果 (由分析器非同步填入) ---
    analyzed_at: Optional[datetime] = None
    importance: Optional[int] = None
    sentiment_score: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    entities: List[Any] = field(default_factory=list)
    ai_summary: Optional[str] = None
    is_analyzed: bool = False
    is_featured: bool = False

    def __post_init__(self):
        # 實作手冊 3.1 節要求：MD5(title + url) 作為去重鍵
        if not self.dedup_key:
            raw = (self.title + self.url).encode('utf-8')
            self.dedup_key = hashlib.md5(raw).hexdigest()
            
    def to_dict(self) -> dict:
        """轉為與資料庫欄位對應的字典"""
        return {
            "id": str(self.id),
            "dedup_key": self.dedup_key,
            "source": self.source,
            "category": self.category,
            "title": self.title[:500],
            "summary": self.summary[:600],
            "body": self.body,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "fetched_at": self.fetched_at.isoformat(),
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "expires_at": self.expires_at.isoformat(),
            "importance": self.importance,
            "sentiment_score": self.sentiment_score,
            "tags": self.tags,
            "entities": self.entities,
            "ai_summary": self.ai_summary,
            "is_analyzed": self.is_analyzed,
            "is_featured": self.is_featured,
            "pipeline_run_id": str(self.pipeline_run_id) if self.pipeline_run_id else None
        }
