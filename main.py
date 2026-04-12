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

async def process_and_save_item(db, anonymizer, llm_processor, item):
    """通用的處理與儲存函式 (DRY 原則)"""
    try:
        logger.info(f"正在分析: {item.title[:30]}")
        
        # 1. 敏感度檢查
        if not anonymizer.is_safe_for_cloud(item.body):
            logger.warning(f"偵測到高敏內容，跳過雲端處理: {item.title[:30]}")
            item.summary = "[內容過於敏感，地端隔離處理中]"
            item.importance = 10
            db.insert_intel_item(item, embedding=[0.0]*768)
            return

        # 2. 去識別化
        masked_body = anonymizer.mask_text(item.body)
        
        # 3. AI 分析
        analysis = await llm_processor.analyze_news(item.title, masked_body)
        
        # 4. 填充分析結果
        item.summary = analysis.get("summary", item.summary)
        item.importance = analysis.get("importance_score")
        item.sentiment_score = analysis.get("sentiment_score")
        item.tags = analysis.get("tags", [])
        item.entities = analysis.get("entities", [])
        item.ai_summary = analysis.get("ai_summary")
        item.analyzed_at = datetime.now(timezone.utc)
        item.is_analyzed = True
        
        # 5. 生成向量與存儲
        embedding = await llm_processor.generate_embedding(f"{item.title} {item.summary}")
        db.insert_intel_item(item, embedding=embedding)
        logger.info(f"分析完成並入庫: {item.title[:30]}")
    except Exception as e:
        logger.error(f"單筆處理失敗: {e}")

async def run_pipeline():
    """執行採集管線 (優化版：批次重複檢查 + 統一處理流程)"""
    pipeline_run_id = uuid.uuid4()
    logger.info(f"===== 啟動 BIA 採集管線 [ID: {pipeline_run_id}] =====")
    
    db = SupabaseDB()
    anonymizer = Anonymizer()
    llm_processor = LLMProcessor()
    
    # 1. 執行採集
    fsc_collector = FSCCollector(pipeline_run_id=pipeline_run_id)
    macro_collector = MacroCollector(pipeline_run_id=pipeline_run_id)
    
    fsc_items, macro_items = await asyncio.gather(
        fsc_collector.collect_intel(limit=10),
        macro_collector.collect_intel(limit=10)
    )
    all_items = fsc_items + macro_items
    
    # 2. 批次重複檢查 (避免 N+1 查詢)
    all_urls = [item.url for item in all_items]
    existing_urls = db.batch_check_exists(all_urls) # 假設我們在 DB Client 實作了批次檢查
    
    new_items = [i for i in all_items if i.url not in existing_urls]
    logger.info(f"採集總數: {len(all_items)}, 新項目: {len(new_items)}")
    
    # 3. 處理新項目
    # 嘗試連接 Redis 判斷模式
    r = None
    try:
        r = aioredis.from_url(REDIS_URL, socket_timeout=1)
        await r.ping()
        logger.info("成功連接 Redis，推送至 Streams 佇列。")
        for item in new_items:
            payload = {"title": item.title, "url": item.url, "body": item.body, "dedup_key": item.dedup_key}
            await r.xadd(STREAM_NAME, {
                "source": item.source,
                "payload": json.dumps(payload, ensure_ascii=False),
                "pipeline_run_id": str(pipeline_run_id)
            })
    except Exception:
        logger.warning("Redis 無法連線，執行直接分析模式。")
        # 併發處理以加速
        tasks = [process_and_save_item(db, anonymizer, llm_processor, item) for item in new_items]
        await asyncio.gather(*tasks)

    logger.info(f"===== 管線 [ID: {pipeline_run_id}] 執行完畢 =====")
    if r: await r.aclose()
        
    except Exception as e:
        logger.error(f"管線執行失敗: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
