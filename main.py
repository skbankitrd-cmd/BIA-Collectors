import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

from collectors.fsc_collector import FSCCollector
from processors.anonymizer import Anonymizer
from processors.llm_processor import LLMProcessor
from database.supabase_client import SupabaseDB

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BIA-Pipeline")

load_dotenv()

async def run_pipeline():
    """執行完整情報採集管線"""
    logger.info("===== 啟動 BIA 情報採集管線 =====")
    
    try:
        # 1. 初始化元件
        fsc_collector = FSCCollector()
        anonymizer = Anonymizer()
        llm_processor = LLMProcessor()
        db = SupabaseDB()
        
        # 2. 獲取最近的新聞 (目前限制前 3 條，避免測試時 Token 消耗過快)
        recent_news = await fsc_collector.collect_recent_news(limit=3)
        
        for news_item in recent_news:
            title = news_item["title"]
            url = news_item["url"]
            
            # 3. 檢查是否已存在
            if db.is_news_exists(url):
                logger.info(f"新聞已存在，略過：{title}")
                continue
                
            logger.info(f"正在處理新情報：{title}")
            
            # 4. 去識別化 (儘管是公開資料，仍作為標準流程)
            masked_content = anonymizer.mask_text(news_item["raw_content"])
            
            # 5. LLM 分析 (摘要、分類、重要性)
            analysis_result = await llm_processor.analyze_news(title, masked_content)
            
            # 6. 生成向量 Embedding (結合標題與摘要)
            embedding_text = f"{title} {analysis_result['summary']}"
            embedding = await llm_processor.generate_embedding(embedding_text)
            
            # 7. 合併資料並存入資料庫
            processed_data = {
                **news_item,
                **analysis_result,
                "embedding": embedding,
                "raw_content": masked_content # 存入遮蔽後的內容
            }
            
            # 處理日期格式 (轉換為 ISO 格式供 PostgreSQL 使用)
            # RSS 日期格式可能多變，這裡做簡單處理
            try:
                if news_item.get("published_date"):
                    # 若日期格式特殊可在此擴充解析邏輯
                    processed_data["published_date"] = news_item["published_date"]
                else:
                    processed_data["published_date"] = datetime.now().isoformat()
            except Exception:
                processed_data["published_date"] = datetime.now().isoformat()

            # 存入資料庫
            db.insert_intelligence(processed_data)
            
        logger.info("===== 情報採集管線執行完畢 =====")
        
    except Exception as e:
        logger.error(f"管線執行過程中發生錯誤: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
