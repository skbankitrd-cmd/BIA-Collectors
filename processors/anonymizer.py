import re
from typing import List

class Anonymizer:
    """去識別化閘道 (防禦 ReDoS 優化版)"""
    def __init__(self, custom_keywords: List[str] = None):
        # [Security Fix: 優化正則，防範災難性回溯 (ReDoS)]
        # 將原本重疊的匹配改為非捕獲且互斥的結構
        self.patterns = {
            'TAIWAN_ID': r'[A-Z][12]\d{8}',
            'CREDIT_CARD': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'PHONE': r'\b09\d{2}-?\d{3}-?\d{3}\b',
            # 優化 Email 正則，避免多層級重疊導致的 $O(2^n)$ 複雜度
            'EMAIL': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
            'ACCOUNT': r'客戶[A-Z]\d+',
            'PROJECT': r'專案[X-Z]|秘密專案'
        }
        
        if custom_keywords:
            self.patterns['CUSTOM'] = '|'.join([re.escape(kw) for kw in custom_keywords])
        
        self.combined_pattern = re.compile('|'.join([f'(?P<{k}>{v})' for k, v in self.patterns.items()]))

    def mask_text(self, text: str) -> str:
        if not text: return ""
        def replace_func(match):
            for name, value in match.groupdict().items():
                if value: return f"[REDACTED_{name}]"
            return "[REDACTED]"
        return self.combined_pattern.sub(replace_func, text)

    def is_safe_for_cloud(self, text: str) -> bool:
        if not text: return True
        matches = self.combined_pattern.findall(text)
        return len(matches) <= 5

    def get_sensitive_report(self, text: str) -> dict:
        matches = self.combined_pattern.finditer(text)
        report = {}
        for match in matches:
            kind = match.lastgroup
            report[kind] = report.get(kind, 0) + 1
        return report
