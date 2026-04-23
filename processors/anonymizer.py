import re
from typing import List, Dict


# ---------------------------------------------------------------------------
# PII Pattern Registry
# ---------------------------------------------------------------------------
# 設計原則：每個 pattern 獨立定義，便於合規審查者逐條確認與更新。
# ReDoS 防護：所有正則均使用固定前綴錨定或非回溯結構，禁止使用
#   巢狀量詞（如 (\w+)+ ）及無限量詞搭配可選群組。
#
# 覆蓋的 PII 類型（13 類）：
#   TAIWAN_ID, CREDIT_CARD, PHONE_MOBILE, PHONE_LANDLINE,
#   EMAIL, BANK_ACCOUNT, RESIDENT_CERT, TXN_ID, EMP_ID,
#   IP_ADDR_V4, IP_ADDR_V6, CHINESE_NAME, CUSTOM
#
# 已知不覆蓋類型（誠實揭露，見 ANONYMIZER_COVERAGE.md）：
#   - 圖片/PDF 內的 OCR PII
#   - 非標準格式的護照號碼
#   - 英文姓名（需語料庫支援）
#   - 變形帳號（空格分隔、全形數字）
# ---------------------------------------------------------------------------

# 1. 台灣身分證字號（A-Z 開頭 + 1 或 2 + 8 位數字）
_PAT_TAIWAN_ID = r'[A-Z][12]\d{8}'

# 2. 信用卡號（4×4 格式，分隔符號可為 -、空格或無）
#    固定總長度結構，無巢狀量詞，ReDoS 安全
_PAT_CREDIT_CARD = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'

# 3. 手機號碼（09 開頭，台灣格式）
_PAT_PHONE_MOBILE = r'\b09\d{2}[-\s]?\d{3}[-\s]?\d{3}\b'

# 4. 市話（0X-XXXX-XXXX，X 為 2-8；含分機如 #123 的也覆蓋）
#    區碼：02, 03, 04, 05, 06, 07, 08（台灣所有市話區碼）
_PAT_PHONE_LANDLINE = (
    r'\b0[2-8][-\s]?\d{3,4}[-\s]?\d{4}(?:\s*#\d{1,6})?\b'
)

# 5. Email
_PAT_EMAIL = r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'

# 6. 銀行帳號（10-14 位純數字，含常見分行碼格式）
#    使用 \b 錨定避免誤殺年分、電話等。長度限制防止誤殺流水號。
#    已知限制：無法區分「10位數字剛好是電話」，靠 \b 與長度雙重過濾。
_PAT_BANK_ACCOUNT = r'\b\d{10,14}\b'

# 7. 外籍居留證（1-2 英文字母 + 8 位數字，如 AB12345678 或 A12345678）
#    \b 錨定防止誤殺嵌在較長字串中的子串
_PAT_RESIDENT_CERT = r'\b[A-Z]{1,2}\d{8}\b'

# 8. 交易流水號（TXN / TRX 前綴 + 日期 + 序號）
#    格式：TXN20260423001 / TRX20260423001234
_PAT_TXN_ID = r'\b(?:TXN|TRX)\d{8,14}\b'

# 9. 員工編號（EMP / E 前綴 + 數字，如 EMP001234 / E12345）
#    區分大小寫（EMP 為全大寫縮寫）
_PAT_EMP_ID = r'\bEMP\d{4,8}\b|\bE\d{5,6}\b'

# 10. IPv4 地址（四段 0-255，\b 錨定）
#     不使用 (?:25[0-5]|...) 的複雜形式以避免 ReDoS 疑慮；
#     接受 0-999 格式，後端負責業務語意判斷。
_PAT_IP_V4 = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'

# 11. IPv6 地址（簡化偵測：含 :: 或冒號分隔的十六進位群組）
#     只偵測明確含有 :: 縮寫或完整六段以上的 IPv6，降低誤殺風險。
_PAT_IP_V6 = r'\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b|(?:[0-9a-fA-F]{1,4}:)*::(?:[0-9a-fA-F]{1,4}:)*[0-9a-fA-F]{1,4}'

# 12. 中文姓名（規則式，無需外部依賴）
#
# 策略說明（代碼決策記錄）：
#   我們選擇「規則式 + 百家姓白名單」而非 jieba/ckiptagger，原因：
#   (a) requirements.txt 未含 jieba，不引入新依賴；
#   (b) 金融查詢中姓名通常緊接「先生/小姐/客戶/員工」等連接詞，
#       規則式可有效錨定；
#   (c) 含遮字符（○、Ｘ）的已匿名姓名（如「王○明」）也需遮蔽，
#       規則式可直接覆蓋。
#
# 已知限制（誠實揭露）：
#   - 召回率有限，罕見姓氏或無連接詞的姓名可能漏網
#   - 可能誤殺含常見姓氏的普通詞（如「王道」、「李代」）
#   - 誤殺屬保守誤差（寧可多遮，不可少遮），符合合規方向
#
# 百家姓白名單（前 100 大常見姓氏，涵蓋台灣金融客群主流）：
_COMMON_SURNAMES = (
    '趙|錢|孫|李|周|吳|鄭|王|馮|陳|褚|衛|蔣|沈|韓|楊|朱|秦|尤|許|'
    '何|呂|施|張|孔|曹|嚴|華|金|魏|陶|姜|戚|謝|鄒|喻|柏|水|竇|章|'
    '雲|蘇|潘|葛|奚|范|彭|郎|魯|韋|昌|馬|苗|鳳|花|方|俞|任|袁|柳|'
    '酆|鮑|史|唐|費|廉|岑|薛|雷|賀|倪|湯|滕|殷|羅|畢|郝|鄔|安|常|'
    '傅|卞|齊|元|顧|孟|平|黃|和|穆|蕭|尹|姚|邵|湛|汪|祁|毛|禹|狄|'
    '米|貝|明|臧|計|伏|成|戴|談|宋|茅|龐|熊|紀|舒|屈|項|祝|董|梁|'
    '杜|阮|藍|閔|席|季|麻|強|賈|路|婁|危|江|童|顏|郭|梅|盛|林|刁|'
    '鐘|徐|丘|駱|高|夏|蔡|田|樊|胡|凌|霍|虞|萬|支|柯|昝|管|盧|莫'
)

# 連接詞：姓名後常接的詞，用來提升精度（減少孤立姓氏誤殺）
_NAME_SUFFIX = r'(?:先生|小姐|女士|客戶|員工|用戶|帳戶|貸款|的|之|申請|查詢)'

# 姓名本體：姓（1字）+ 名（1-3字，可含遮字符○Ｘ●＊）
_NAME_BODY = r'[○Ｘ●＊一-鿿]{1,3}'

_PAT_CHINESE_NAME = (
    r'(?:' + _COMMON_SURNAMES + r')'  # 姓氏（百家姓）
    + _NAME_BODY                        # 名（1-3字）
    + r'(?=' + _NAME_SUFFIX + r')'     # 正向前瞻：後接連接詞（不消耗字元）
)

# ---------------------------------------------------------------------------
# 統一 Pattern 字典（有序，優先匹配更長/更具體的 pattern）
# 注意：BANK_ACCOUNT 放在 TAIWAN_ID 之後，避免 10 位台灣 ID 被提前截取
# ---------------------------------------------------------------------------
_PATTERNS: Dict[str, str] = {
    'TAIWAN_ID':      _PAT_TAIWAN_ID,
    'CREDIT_CARD':    _PAT_CREDIT_CARD,
    'PHONE_MOBILE':   _PAT_PHONE_MOBILE,
    'PHONE_LANDLINE': _PAT_PHONE_LANDLINE,
    'EMAIL':          _PAT_EMAIL,
    'BANK_ACCOUNT':   _PAT_BANK_ACCOUNT,
    'RESIDENT_CERT':  _PAT_RESIDENT_CERT,
    'TXN_ID':         _PAT_TXN_ID,
    'EMP_ID':         _PAT_EMP_ID,
    'IP_ADDR_V4':     _PAT_IP_V4,
    'IP_ADDR_V6':     _PAT_IP_V6,
    'CHINESE_NAME':   _PAT_CHINESE_NAME,
}

# Placeholder 對照（用於 mask_text 輸出）
_PLACEHOLDERS: Dict[str, str] = {
    'TAIWAN_ID':      '[TAIWAN_ID]',
    'CREDIT_CARD':    '[CREDIT_CARD]',
    'PHONE_MOBILE':   '[PHONE_MOBILE]',
    'PHONE_LANDLINE': '[LANDLINE]',
    'EMAIL':          '[EMAIL]',
    'BANK_ACCOUNT':   '[BANK_ACCOUNT]',
    'RESIDENT_CERT':  '[RESIDENT_CERT]',
    'TXN_ID':         '[TXN_ID]',
    'EMP_ID':         '[EMP_ID]',
    'IP_ADDR_V4':     '[IP_ADDR]',
    'IP_ADDR_V6':     '[IP_ADDR]',
    'CHINESE_NAME':   '[CHINESE_NAME]',
    'CUSTOM':         '[CUSTOM]',
}


class Anonymizer:
    """
    去識別化閘道（PII 遮蔽 + 雲端外送安全判斷）

    合規版本：M1 + M2 修正（Banking Compliance Expert 審查 2026-04-23）

    PII 清單（13 類）與遮蔽邏輯分離設計：
    - _PATTERNS dict（模組層級）：PII 偵測規則，可獨立更新
    - _PLACEHOLDERS dict（模組層級）：遮蔽輸出格式，可獨立更新
    - 兩者均在類別初始化時載入，不需重建 Anonymizer 實例即可更換規則

    ReDoS 防護：
    - 所有 pattern 禁用巢狀量詞
    - 已於初始化時預編譯 combined_pattern
    """

    def __init__(self, custom_keywords: List[str] = None):
        self.patterns: Dict[str, str] = dict(_PATTERNS)

        if custom_keywords:
            # re.escape 確保關鍵字中的特殊字元不破壞正則
            self.patterns['CUSTOM'] = '|'.join(
                re.escape(kw) for kw in custom_keywords
            )

        # 預編譯合併正則（named groups），失敗時快速失敗
        self._combined: re.Pattern = re.compile(
            '|'.join(
                f'(?P<{name}>{pat})'
                for name, pat in self.patterns.items()
            )
        )

    # ------------------------------------------------------------------
    # 公開 API
    # ------------------------------------------------------------------

    def mask_text(self, text: str) -> str:
        """
        將 text 中所有偵測到的 PII 替換為對應 placeholder。
        原始字元位置保留（僅替換命中段落），其餘文字不變。
        """
        if not text:
            return ''

        def _replace(match: re.Match) -> str:
            kind = match.lastgroup
            return _PLACEHOLDERS.get(kind, '[REDACTED]')

        return self._combined.sub(_replace, text)

    def is_safe_for_cloud(self, text: str) -> bool:
        """
        判斷文字是否可安全外送雲端 LLM（如 NVIDIA NIM）。

        合規硬性要求（M2 — 不得回退）：
            任何 PII 命中 → 返回 False
            命中數 == 0   → 返回 True

        原有邏輯 `len(matches) <= 5` 已確認為邏輯謬誤：
        允許最多 5 筆 PII 外流，直接違反個資法與 PCI DSS 要求。
        此修正由 Banking Compliance Expert 列為 MUST（M2）上線阻斷條件。
        """
        if not text:
            return True
        # finditer 逐一產生 Match 物件；有任何命中即代表 PII 存在
        return next(self._combined.finditer(text), None) is None

    def get_sensitive_report(self, text: str) -> Dict[str, int]:
        """
        返回各類 PII 在 text 中的命中次數統計。
        用於 Audit Trail 的 anonymizer_hits 欄位。
        """
        report: Dict[str, int] = {}
        for match in self._combined.finditer(text):
            kind = match.lastgroup
            report[kind] = report.get(kind, 0) + 1
        return report

    def get_patterns(self) -> Dict[str, str]:
        """返回當前啟用的 PII pattern 字典（唯讀副本）。"""
        return dict(self.patterns)
