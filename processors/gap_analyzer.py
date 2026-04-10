import logging
import os
import sys
from typing import List, Dict

# 引入相關模組
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(os.path.join(PROJECT_ROOT, 'BIA-Collectors'))
sys.path.append(PROJECT_ROOT)

from database.supabase_client import SupabaseDB
from AutoAgentBuilder.core.vector_store import LocalVectorStore
from AutoAgentBuilder.core.llm_client import LLMClient
from utils.exporters.excel_exporter import ExcelExporter

logger = logging.getLogger("GapAnalyzer")

class ComplianceGapAnalyzer:
    """法規聯防落差分析器：外部法規 vs 內部系統規格"""
    
    def __init__(self, system_id: str):
        self.system_id = system_id
        self.db = SupabaseDB()
        self.local_store = LocalVectorStore(system_id)
        self.llm = LLMClient()

    async def run_analysis(self) -> str:
        logger.info(f"🧐 正在執行 {self.system_id} 的法規符合度落差分析...")
        
        # 1. 獲取最新外部法規 (例如: 重要性 > 8 的資安法規)
        external_news = self.db.query_intelligence(query="資安", category="法遵", limit=3)
        if not external_news:
            return "目前無重大相關法規異動。"

        analysis_results = []
        for news in external_news:
            regulation = news['summary']
            
            # 2. 檢索內部系統相關規格 (RAG)
            internal_context = self.local_store.query(regulation, n_results=3)
            internal_docs = str(internal_context['documents'][0])
            
            # 3. 呼叫 Qwen 進行對比分析
            prompt = f"""
            你是一位金控資安合規專家。請比對以下「外部法規」與「內部系統現況」，找出潛在的落差(Gap)。
            【外部法規】: {regulation}
            【內部系統現況】: {internal_docs}
            
            請產出：1. 法規要求 2. 內部現況 3. 符合程度(高/中/低) 4. 改善建議。
            """
            result = self.llm.ask(prompt, "請執行專業分析。")
            analysis_results.append({
                "來源法規": news['title'],
                "分析結果": result,
                "重要性": news['importance']
            })

        # 4. 自動產出落差盤點報表
        exporter = ExcelExporter()
        report_url = exporter.export(analysis_results, report_title=f"Gap_Analysis_{self.system_id}")
        
        logger.info(f"✅ 落差分析完成，報表已產出: {report_url}")
        return report_url
