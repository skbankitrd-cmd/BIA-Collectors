import asyncio
import json
import logging
import uuid
import os
import redis.asyncio as aioredis
from datetime import datetime, timezone
from dotenv import load_dotenv

from processors.anonymizer import Anonymizer
from processors.llm_processor import LLMProcessor
from database.supabase_client import SupabaseDB
from models.intel_item import IntelItem

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BIA-Worker")

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_NAME = "raw_intel"
GROUP_NAME = "analyzer_group"
CONSUMER_NAME = f"worker-{uuid.uuid4().hex[:6]}"

async def process_message(id, fields, anonymizer, llm_processor, db):
    """處理單筆來自 Redis 的原始情報"""
    try:
        source = fields.get(b"source", b"unknown").decode()
        payload = json.loads(fields.get(b"payload", b"{}").decode())
        pipeline_run_id = fields.get(b"pipeline_run_id", b"").decode()
        
        title = payload.get("title", "")
        url = payload.get("url", "")
        body = payload.get("body", "")
        
        # 1. 檢查是否存在 (冪等性)
        if db.is_news_exists(url):
            logger.info(f"情報已在資料庫中: {title[:30]}")
            return True
            
        logger.info(f"正在分析情報: {title[:30]}")
        
        # 2. 去識別化
        masked_body = anonymizer.mask_text(body)
        
        # 3. LLM 深度分析
        analysis = await llm_processor.analyze_news(title, masked_body)
        
        # 4. 建立標準化 IntelItem
        item = IntelItem(
            source=source,
            title=title,
            category="scrape", # 規範定義
            summary=analysis.get("summary", body[:600]),
            body=masked_body,
            url=url,
            pipeline_run_id=uuid.UUID(pipeline_run_id) if pipeline_run_id else None
        )
        
        # 更新分析欄位
        item.importance = analysis.get("importance_score")
        item.sentiment_score = analysis.get("sentiment_score")
        item.tags = analysis.get("tags", [])
        item.entities = analysis.get("entities", [])
        item.ai_summary = analysis.get("ai_summary")
        item.analyzed_at = datetime.now(timezone.utc)
        item.is_analyzed = True
        
        # 5. 生成向量
        embedding = await llm_processor.generate_embedding(f"{item.title} {item.summary}")
        
        # 6. 存入 Supabase (intel_items)
        db.insert_intel_item(item, embedding=embedding)
        return True
    except Exception as e:
        logger.error(f"處理訊息時發生錯誤: {e}")
        return False

async def run_worker():
    """啟動 Redis Streams 消費者"""
    r = await aioredis.from_url(REDIS_URL)
    anonymizer = Anonymizer()
    llm_processor = LLMProcessor()
    db = SupabaseDB()
    
    # 建立消費群組 (如果不存在)
    try:
        await r.xgroup_create(STREAM_NAME, GROUP_NAME, mkstream=True)
    except Exception:
        pass # 群組已存在
        
    logger.info(f"Worker {CONSUMER_NAME} 已啟動，等待任務中...")
    
    while True:
        try:
            # 從 Stream 讀取訊息
            streams = await r.xreadgroup(GROUP_NAME, CONSUMER_NAME, {STREAM_NAME: ">"}, count=1, block=5000)
            
            for stream_name, messages in streams:
                for message_id, fields in messages:
                    success = await process_message(message_id, fields, anonymizer, llm_processor, db)
                    if success:
                        # 認可訊息 (Ack)
                        await r.xack(STREAM_NAME, GROUP_NAME, message_id)
                        
        except Exception as e:
            logger.error(f"Worker 循環錯誤: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_worker())
