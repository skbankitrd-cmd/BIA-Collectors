import google.generativeai as genai
import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMProcessor:
    """AI 分析層：動態探測可用模型 (Flash/Pro)"""
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("未設置 GEMINI_API_KEY 環境變數")
        
        genai.configure(api_key=self.api_key)
        
        # 動態探測可用模型
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            logger.info(f"可用模型清單: {available_models}")
            
            if 'models/gemini-1.5-pro' in available_models:
                self.model_name = 'gemini-1.5-pro'
            elif 'models/gemini-1.5-flash' in available_models:
                self.model_name = 'gemini-1.5-flash'
            elif 'models/gemini-pro' in available_models:
                self.model_name = 'gemini-pro'
            else:
                self.model_name = available_models[0].replace('models/', '') if available_models else 'gemini-1.5-flash'
        except Exception as e:
            logger.warning(f"探測模型失敗: {e}，將使用預設值")
            self.model_name = 'gemini-1.5-flash'
            
        logger.info(f"最終選定分析模型: {self.model_name}")
        self.model = genai.GenerativeModel(self.model_name)
        
        # Embedding 模型固定使用最新穩定版
        self.embed_model = 'models/text-embedding-004'
        logger.info(f"最終選定向量模型: {self.embed_model}")

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
        5. sentiment_score: 整數 -5 到 5。-5 代表極度負面（如重罰、危機），5 代表極度正面（如放寬限制、獲利），0 為中性。
        6. entities: JSON 陣列，擷取重要實體（機構、人物、數據、風險）。格式：[{{"type": "org|person|event|figure|risk", "name": "實體名稱", "context": "說明"}}]。
        7. tags: 字串陣列，給予 2-4 個關鍵字標籤（如 ["法規", "資安", "裁罰"]）。
        8. ai_summary: 80字以內的精煉摘要。語氣需像『金控戰略秘書』向董事長進行口頭晨報：
           - 必須以「報告主管/長官」開頭。
           - 內容直接切入事件對本集團或台灣金融業的實質影響。
           - 語氣必須沈穩專業，嚴禁任何輕率的助詞。


        請僅回傳 JSON 格式，嚴禁任何 Markdown 標記或額外文字說明。
        """
        
        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(clean_text)
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
