import google.generativeai as genai
import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMProcessor:
    """AI 分析層：鎖定 flash 模型並強制 JSON 輸出"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("未設置 GEMINI_API_KEY 環境變數")
        
        genai.configure(api_key=self.api_key)
        
        # 鎖定模型與結構化輸出規範
        self.model_name = 'gemini-1.5-flash'
        self.generation_config = {
            "temperature": 0.1,
            "top_p": 0.95,
            "max_output_tokens": 2048,
            "response_mime_type": "application/json",
        }
        
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config
        )
        
        # Embedding 模型固定使用最新穩定版 (維度: 768)
        self.embed_model = 'models/text-embedding-004'
        logger.info(f"LLM 處理器初始化完成: {self.model_name} / {self.embed_model}")

    async def analyze_news(self, title: str, content: str) -> Dict[str, Any]:
        """分析新聞內容並生成結構化數據，具備細緻分類邏輯"""
        prompt = f"""
        你是一位專精於台灣金融業的頂尖戰略顧問。請針對以下新聞內容進行深度分析。

        新聞標題：{title}
        新聞內文：
        {content[:3000]}

        請以 JSON 格式回傳以下欄位：
        - summary (string): 約 150 字的專業分析與建議。
        - category (string): 必須為 ['法規遵循', '總體經濟', '資安與韌性', '市場與同業', '永續金融', '風險管理'] 其中之一。
        - importance_score (integer): 1-10。
        - target_roles (array of strings): 選自 ['董事長', '法遵長', '資訊長', '營運長', '風險長']。
        - sentiment_score (integer): -5 到 5。
        - entities (array of objects): [{{ "type": "org|person|event|figure|risk", "name": "...", "context": "..." }}]。
        - tags (array of strings): 2-4 個關鍵字標籤。
        - ai_summary (string): 80字以內的精煉摘要，必須以「報告主管」開頭。
        """
        
        try:
            # 由於我們設定了 response_mime_type: "application/json"，Gemini 會保證回傳 JSON
            response = self.model.generate_content(prompt)
            result = json.loads(response.text)
            logger.info(f"AI 分析成功: {result.get('category')} - {result.get('importance_score')}分")
            return result
        except Exception as e:
            logger.error(f"LLM 分析失敗: {e}")
            return {
                "summary": "AI 分析失敗，請查閱原始內文。",
                "category": "未分類",
                "importance_score": 5,
                "target_roles": [],
                "sentiment_score": 0,
                "entities": [],
                "tags": [],
                "ai_summary": "抱歉，報告生成失敗，請稍後重試。"
            }

    async def generate_embedding(self, text: str) -> List[float]:
        """為文本生成向量 Embedding (帶有錯誤備援)"""
        try:
            result = genai.embed_content(
                model=self.embed_model,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"生成向量失敗 ({self.embed_model}): {e}")
            # 如果失敗，回傳 768 維的零向量，確保資料庫能成功寫入
            return [0.0] * 768

if __name__ == "__main__":
    import asyncio
    processor = LLMProcessor()
    test_title = "金管會強化銀行資安防護要求"
    test_content = "金管會今日發布新聞稿，要求各銀行需在年底前完成關鍵系統的弱點掃描與異地備援測試..."
    
    async def run_test():
        analysis = await processor.analyze_news(test_title, test_content)
        print(f"分析結果: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
        
        embedding = await processor.generate_embedding(test_title + " " + analysis['summary'])
        print(f"向量維度: {len(embedding)}")

    asyncio.run(run_test())
