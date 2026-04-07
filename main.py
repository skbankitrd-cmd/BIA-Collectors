import asyncio
import logging
import uuid
import json
import os
import redis.asyncio as aioredis
from datetime import datetime, timezone
from dotenv import load_dotenv

from collectors.fsc_collector import FSCCollector
from collectors.macro_collector import MacroCollector
from database.supabase_client import SupabaseDB
from processors.anonymizer import Anonymizer
from processors.llm_processor import LLMProcessor

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BIA-Pipeline")

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_NAME = "raw_intel"

async def run_pipeline():
    """執行採集管線 (支援 Redis Streams 緩衝與直接模式雙切換)"""
    pipeline_run_id = uuid.uuid4()
    logger.info(f"===== 啟動 BIA 採集管線 [ID: {pipeline_run_id}] =====")
    
    # 1. 初始化元件
    db = SupabaseDB()
    fsc_collector = FSCCollector(pipeline_run_id=pipeline_run_id)
    macro_collector = MacroCollector(pipeline_run_id=pipeline_run_id)
    
    # 嘗試連接 Redis
    r = None
    use_redis = False
    try:
        r = aioredis.from_url(REDIS_URL, socket_timeout=2)
        await r.ping()
        use_redis = True
        logger.info("成功連接 Redis，啟用緩衝模式 (Streams)。")
    except Exception:
        logger.warning("無法連接 Redis，切換為「直接模式」(採集後立即分析)。")

    try:
        # 2. 執行採集 (併發執行多個採集器)
        fsc_items, macro_items = await asyncio.gather(
            fsc_collector.collect_intel(limit=5),
            macro_collector.collect_intel(limit=5)
        )
        intel_items = fsc_items + macro_items
        logger.info(f"採集總數: {len(intel_items)} 筆 (FSC: {len(fsc_items)}, Macro: {len(macro_items)})")
        
        if not use_redis:
            # 模式 A: 直接模式 (無 Redis 時)
            anonymizer = Anonymizer()
            llm_processor = LLMProcessor()
            
            for item in intel_items:
                if db.is_news_exists(item.url):
                    logger.info(f"情報已存在，略過: {item.title[:30]}")
                    continue
                
                logger.info(f"直接模式: 正在分析 {item.title[:30]}")
                item.body = anonymizer.mask_text(item.body)
                analysis = await llm_processor.analyze_news(item.title, item.body)
                
                # 填充分析結果 (對齊規範)
                item.summary = analysis.get("summary", item.summary)
                item.importance = analysis.get("importance_score")
                item.sentiment_score = analysis.get("sentiment_score")
                item.tags = analysis.get("tags", [])
                item.entities = analysis.get("entities", [])
                item.ai_summary = analysis.get("ai_summary")
                item.analyzed_at = datetime.now(timezone.utc)
                item.is_analyzed = True
                
                embedding = await llm_processor.generate_embedding(f"{item.title} {item.summary}")
                db.insert_intel_item(item, embedding=embedding)
        else:
            # 模式 B: 緩衝模式 (有 Redis 時)
            for item in intel_items:
                if db.is_news_exists(item.url): continue
                
                payload = {"title": item.title, "url": item.url, "body": item.body, "dedup_key": item.dedup_key}
                await r.xadd(STREAM_NAME, {
                    "source": item.source,
                    "payload": json.dumps(payload, ensure_ascii=False),
                    "pipeline_run_id": str(pipeline_run_id),
                    "ts": datetime.now(timezone.utc).isoformat()
                })
                logger.info(f"任務已派發至 Redis: {item.title[:30]}")

        logger.info(f"===== 管線 [ID: {pipeline_run_id}] 執行完畢 =====")
        if r: await r.aclose()
        
    except Exception as e:
        logger.error(f"管線執行失敗: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
