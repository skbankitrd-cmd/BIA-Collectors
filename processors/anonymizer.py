import re
from typing import List

class Anonymizer:
    """去識別化閘道 (Anonymization Gateway)"""
    def __init__(self, custom_keywords: List[str] = None):
        # 強化敏感詞庫 (Harness: PII & Financial Data Patterns)
        self.patterns = {
            'TAIWAN_ID': r'[A-Z][12]\d{8}',                # 台灣身分證字號
            'CREDIT_CARD': r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}', # 信用卡號
            'PHONE': r'09\d{2}-?\d{3}-?\d{3}',             # 手機號碼
            'EMAIL': r'[\w\.-]+@[\w\.-]+\.\w+',            # 電子郵件
            'ACCOUNT': r'客戶[A-Z]\d+',                     # 銀行客戶代號
            'PROJECT': r'專案[X-Z]|秘密專案'                 # 機密專案
        }
        
        if custom_keywords:
            self.patterns['CUSTOM'] = '|'.join([re.escape(kw) for kw in custom_keywords])
        
        # 建立一個大正則，並使用命名群組以便識別類型 (選擇性，目前統一遮蔽)
        self.combined_pattern = re.compile('|'.join([f'(?P<{k}>{v})' for k, v in self.patterns.items()]))

    def mask_text(self, text: str) -> str:
        """遮蔽文本中的敏感資訊 (Harness: Context-Aware Masking)"""
        if not text:
            return ""
        
        def replace_func(match):
            for name, value in match.groupdict().items():
                if value:
                    return f"[REDACTED_{name}]"
            return "[REDACTED]"

        return self.combined_pattern.sub(replace_func, text)

    def is_safe_for_cloud(self, text: str) -> bool:
        """檢查文本是否包含過多敏感資訊，決定是否適合傳送到雲端 LLM"""
        if not text:
            return True
        
        # 統計敏感詞出現次數
        matches = self.combined_pattern.findall(text)
        
        # 建立一個簡單的評分機制
        score = 0
        for m in matches:
            # findall 返回的是 tuple 列表（如果有多個 group）或字串列表
            # 我們這裡只需要算總數
            score += 1
            
        # 閾值設定：如果一段文字中出現超過 5 個敏感實體，視為不安全
        if score > 5:
            return False
            
        return True

    def get_sensitive_report(self, text: str) -> dict:
        """產出敏感度分析報告"""
        matches = self.combined_pattern.finditer(text)
        report = {}
        for match in matches:
            kind = match.lastgroup
            report[kind] = report.get(kind, 0) + 1
        return report

if __name__ == "__main__":
    anonymizer = Anonymizer(custom_keywords=["內部機密系統"])
    test_text = "根據內部機密系統顯示，客戶A123 參與了 秘密專案 的執行。"
    print(f"原始文本: {test_text}")
    print(f"遮蔽後文本: {anonymizer.mask_text(test_text)}")
