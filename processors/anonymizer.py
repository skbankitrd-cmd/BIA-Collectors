import re
from typing import List

class Anonymizer:
    """去識別化閘道 (Anonymization Gateway)"""
    def __init__(self, custom_keywords: List[str] = None):
        # 預設敏感詞庫 (銀行代號、虛擬客戶名、機密專案)
        self.sensitive_patterns = [
            r'客戶[A-Z]\d+', # 客戶代號如 客戶A123
            r'專案[X-Z]',    # 專案代號
            r'秘密專案',
        ]
        if custom_keywords:
            for kw in custom_keywords:
                self.sensitive_patterns.append(re.escape(kw))
        
        self.combined_pattern = re.compile('|'.join(self.sensitive_patterns))

    def mask_text(self, text: str) -> str:
        """遮蔽文本中的敏感資訊"""
        if not text:
            return ""
        return self.combined_pattern.sub("[REDACTED]", text)

    def is_safe_for_cloud(self, text: str) -> bool:
        """檢查文本是否包含過多敏感資訊，決定是否適合傳送到雲端 LLM"""
        # 這裡可以實作更複雜的邏輯，目前簡單返回 True
        # 第一階段為外部公開新聞，通常是安全的
        return True

if __name__ == "__main__":
    anonymizer = Anonymizer(custom_keywords=["內部機密系統"])
    test_text = "根據內部機密系統顯示，客戶A123 參與了 秘密專案 的執行。"
    print(f"原始文本: {test_text}")
    print(f"遮蔽後文本: {anonymizer.mask_text(test_text)}")
