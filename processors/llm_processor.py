import google.generativeai as genai
import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMProcessor:
    """AI 分析層：使用 Gemini 2.0 Flash Lite 進行處理 (免費額度 RPD=500)"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("未設置 GEMINI_API_KEY 環境變數")
        
        genai.configure(api_key=self.api_key)
        # 更新為 2.0 Flash Lite 以確保每日有足夠的免費額度 (500 RPD)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite-preview-02-05')
        self.embed_model = "models/text-embedding-004"

    async def analyze_news(self, title: str, content: str) -> Dict[str, Any]:
        """分析新聞內容並生成結構化數據，具備細緻分類邏輯"""
        prompt = f"""
        你是一位專精於台灣金融業的頂尖戰略顧問。請針對以下新聞內容進行深度分析，並提供給銀行高階主管（如董事長、法遵長、資訊長）。

        新聞標題：{title}
        新聞內文：
        {content[:3000]}

        請根據以下標準，以 JSON 格式回傳精確分析：

        1. summary: 約 150 字的摘要。需聚焦於「對銀行業的具體影響」與「高階主管的行動建議」。
        2. category: 精確分類，必須從以下選取最合適的一個：
           - '法規遵循': 涉及處分、法律條文修正、監理申報、反洗錢等。
           - '總體經濟': 涉及利率、通膨、貨幣政策、匯率趨勢等。
           - '資安與韌性': 涉及系統故障、駭客攻擊、資安防護規範、數位韌性。
           - '市場與同業': 涉及銀行合併、新業務推出、同業競爭態勢、市場變動。
           - '永續金融': 涉及 ESG、綠色金融、氣候變遷風險、社會責任。
           - '風險管理': 涉及信用風險、市場風險、流動性管理。
        3. importance_score: 整數 1-10。10 分代表極度緊急或涉及重大處罰；1 分代表一般性新聞。
        4. target_roles: 適合閱讀此內容的角色。請根據內容屬性精準選擇，可複選：['董事長', '法遵長', '資訊長', '營運長', '風險長']。
           - 涉及處分或法規：必選 '法遵長'、'董事長'。
           - 涉及技術或系統：必選 '資訊長'。
           - 涉及獲利或策略：必選 '董事長'、'營運長'。

        請僅回傳 JSON 格式，嚴禁任何 Markdown 標記或額外文字說明。
        """
        
        try:
            response = self.model.generate_content(prompt)
            # 移除 Markdown 的 JSON 標籤
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean_text)
            return result
        except Exception as e:
            logger.error(f"LLM 分析失敗: {e}")
            return {
                "summary": "AI 分析失敗，請查閱原始內文。",
                "category": "未分類",
                "importance_score": 5,
                "target_roles": []
            }

    async def generate_embedding(self, text: str) -> List[float]:
        """為文本生成向量 Embedding"""
        try:
            result = genai.embed_content(
                model=self.embed_model,
                content=text,
                task_type="retrieval_document",
                title="Banking Intelligence Feed"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"生成向量失敗: {e}")
            return []

if __name__ == "__main__":
    import asyncio
    # 注意：需先設定 GEMINI_API_KEY 環境變數
    processor = LLMProcessor()
    test_title = "金管會強化銀行資安防護要求"
    test_content = "金管會今日發布新聞稿，要求各銀行需在年底前完成關鍵系統的弱點掃描與異地備援測試..."
    
    async def run_test():
        analysis = await processor.analyze_news(test_title, test_content)
        print(f"分析結果: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
        
        embedding = await processor.generate_embedding(test_title + " " + analysis['summary'])
        print(f"向量維度: {len(embedding)}")

    asyncio.run(run_test())
