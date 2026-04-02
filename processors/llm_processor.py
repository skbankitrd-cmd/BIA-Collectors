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
        """分析新聞內容並生成結構化數據"""
        prompt = f"""
        你是一位頂尖金融戰略顧問。請針對以下新聞內容進行深度分析，並提供給銀行高階主管。
        
        新聞標題：{title}
        新聞內文：
        {content[:3000]}
        
        請以 JSON 格式回傳以下欄位：
        1. summary: 約 150 字的摘要，需聚焦於對金融業的影響與決策建議。
        2. category: 分類，僅限於 ['法規遵循', '總體經濟', '同業動態', '資安風險', '金融科技', 'ESG'] 其中之一。
        3. importance_score: 整數 1-10，代表對決策的重要性。
        4. target_roles: 陣列，適合閱讀此內容的角色名稱。可選值：['董事長', '法遵長', '資訊長', '營運長', '風險長']。
        
        請僅回傳 JSON，不要有額外描述。
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
