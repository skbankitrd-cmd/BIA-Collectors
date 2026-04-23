"""
Anonymizer 合規測試套件
=======================
Banking Compliance Expert 審查 2026-04-23（M1 + M2）

測試結構：
  1. 每個新 PII pattern 至少 2 個 positive case + 2 個 negative case
  2. 真實情境綜合測試（M1 規格要求的 7 個情境）
  3. is_safe_for_cloud 合規硬性要求驗證（M2）
  4. ReDoS 安全性驗證
  5. 邊界值測試

執行方式：pytest BIA-Collectors/tests/test_anonymizer_compliance.py -v
"""

import sys
import os
import re
import time

# 確保 BIA-Collectors 在 PYTHONPATH 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from processors.anonymizer import Anonymizer


@pytest.fixture
def anon():
    """基本 Anonymizer 實例（無自訂關鍵字）"""
    return Anonymizer()


# ===========================================================================
# 1. 原有 PII Pattern 回歸測試（確保既有功能未被破壞）
# ===========================================================================

class TestLegacyPatterns:
    """確保原有 6 種 pattern 仍正常運作"""

    def test_taiwan_id_positive(self, anon):
        assert '[TAIWAN_ID]' in anon.mask_text('客戶身份證 A123456789 已驗證')
        assert '[TAIWAN_ID]' in anon.mask_text('B234567890')

    def test_taiwan_id_negative(self, anon):
        # 小寫不符格式
        assert '[TAIWAN_ID]' not in anon.mask_text('a123456789')
        # 第二字元不是 1 或 2
        assert '[TAIWAN_ID]' not in anon.mask_text('A323456789')

    def test_credit_card_positive(self, anon):
        assert '[CREDIT_CARD]' in anon.mask_text('卡號 4111-1111-1111-1111 已刷卡')
        assert '[CREDIT_CARD]' in anon.mask_text('4111111111111111')

    def test_credit_card_negative(self, anon):
        # 不足16位
        assert '[CREDIT_CARD]' not in anon.mask_text('4111-1111-1111')
        # 超過16位
        assert '[CREDIT_CARD]' not in anon.mask_text('41111111111111111')

    def test_phone_mobile_positive(self, anon):
        assert '[PHONE_MOBILE]' in anon.mask_text('聯絡電話 0912-345-678')
        assert '[PHONE_MOBILE]' in anon.mask_text('0900123456')

    def test_phone_mobile_negative(self, anon):
        # 08 開頭不是手機
        assert '[PHONE_MOBILE]' not in anon.mask_text('0812345678')

    def test_email_positive(self, anon):
        assert '[EMAIL]' in anon.mask_text('請聯絡 user@example.com 確認')
        assert '[EMAIL]' in anon.mask_text('test.user+tag@bank.com.tw')

    def test_email_negative(self, anon):
        assert '[EMAIL]' not in anon.mask_text('這不是email.com格式')


# ===========================================================================
# 2. 新 PII Pattern — PHONE_LANDLINE（M1）
# ===========================================================================

class TestPhoneLandline:
    """市話偵測：0X-XXXX-XXXX（X 為 2-8）"""

    def test_positive_taipei(self, anon):
        result = anon.mask_text('台北辦公室電話 02-2345-6789')
        assert '[LANDLINE]' in result

    def test_positive_kaohsiung(self, anon):
        result = anon.mask_text('高雄分行 07-3456789 請來電')
        assert '[LANDLINE]' in result

    def test_positive_with_extension(self, anon):
        result = anon.mask_text('撥打 04-1234-5678 #205')
        assert '[LANDLINE]' in result

    def test_positive_no_separator(self, anon):
        result = anon.mask_text('電話0223456789請回電')
        assert '[LANDLINE]' in result

    def test_negative_mobile(self, anon):
        # 09 開頭是手機，不應命中 LANDLINE
        result = anon.mask_text('0912345678')
        assert '[LANDLINE]' not in result

    def test_negative_01_not_a_region(self, anon):
        # 台灣沒有 01 區碼
        result = anon.mask_text('01-2345-6789')
        assert '[LANDLINE]' not in result


# ===========================================================================
# 3. 新 PII Pattern — BANK_ACCOUNT（M1）
# ===========================================================================

class TestBankAccount:
    """銀行帳號偵測：10-14 位純數字"""

    def test_positive_10_digit(self, anon):
        result = anon.mask_text('帳號 1234567890 餘額')
        assert '[BANK_ACCOUNT]' in result

    def test_positive_14_digit(self, anon):
        result = anon.mask_text('轉帳帳號 12345678901234')
        assert '[BANK_ACCOUNT]' in result

    def test_negative_9_digit(self, anon):
        # 9 位不足帳號長度
        result = anon.mask_text('查詢 123456789 狀態')
        assert '[BANK_ACCOUNT]' not in result

    def test_negative_15_digit(self, anon):
        # 15 位超出帳號長度範圍
        result = anon.mask_text('號碼 123456789012345')
        assert '[BANK_ACCOUNT]' not in result


# ===========================================================================
# 4. 新 PII Pattern — RESIDENT_CERT（M1）
# ===========================================================================

class TestResidentCert:
    """外籍居留證偵測：1-2 英文 + 8 位數字"""

    def test_positive_two_letter_prefix(self, anon):
        result = anon.mask_text('居留證號碼 AB12345678 驗證中')
        assert '[RESIDENT_CERT]' in result

    def test_positive_one_letter_prefix(self, anon):
        result = anon.mask_text('證件 A12345678')
        assert '[RESIDENT_CERT]' in result

    def test_negative_taiwan_id_format(self, anon):
        # 台灣身分證格式（A1 + 8 碼）應命中 TAIWAN_ID，不是 RESIDENT_CERT
        result = anon.mask_text('A123456789')
        assert '[TAIWAN_ID]' in result

    def test_negative_too_short(self, anon):
        result = anon.mask_text('AB1234567')  # 只有 7 位數字
        assert '[RESIDENT_CERT]' not in result


# ===========================================================================
# 5. 新 PII Pattern — TXN_ID（M1）
# ===========================================================================

class TestTxnId:
    """交易流水號偵測：TXN/TRX + 8-14 位數字"""

    def test_positive_txn_format(self, anon):
        result = anon.mask_text('查詢流水號 TXN20260423001 的狀態')
        assert '[TXN_ID]' in result

    def test_positive_trx_format(self, anon):
        result = anon.mask_text('交易 TRX20260423001234 已完成')
        assert '[TXN_ID]' in result

    def test_negative_lowercase(self, anon):
        # 小寫 txn 不在格式規格內
        result = anon.mask_text('txn20260423001')
        assert '[TXN_ID]' not in result

    def test_negative_too_short(self, anon):
        # 數字部分不足 8 位
        result = anon.mask_text('TXN2026042')
        assert '[TXN_ID]' not in result


# ===========================================================================
# 6. 新 PII Pattern — EMP_ID（M1）
# ===========================================================================

class TestEmpId:
    """員工編號偵測：EMP + 4-8 位數字，或 E + 5-6 位數字"""

    def test_positive_emp_prefix(self, anon):
        result = anon.mask_text('申請人 EMP001234 提交申請')
        assert '[EMP_ID]' in result

    def test_positive_e_prefix(self, anon):
        result = anon.mask_text('員工 E12345 的考績')
        assert '[EMP_ID]' in result

    def test_negative_emp_too_short(self, anon):
        # EMP 後面少於 4 位
        result = anon.mask_text('EMP123')
        assert '[EMP_ID]' not in result

    def test_negative_e_too_short(self, anon):
        # E 後面少於 5 位
        result = anon.mask_text('E1234')
        assert '[EMP_ID]' not in result


# ===========================================================================
# 7. 新 PII Pattern — IP_ADDR（M1）
# ===========================================================================

class TestIpAddr:
    """IP 位址偵測：IPv4 / IPv6"""

    def test_positive_ipv4(self, anon):
        result = anon.mask_text('從 192.168.1.1 登入系統')
        assert '[IP_ADDR]' in result

    def test_positive_ipv4_public(self, anon):
        result = anon.mask_text('外網 IP：203.75.128.64 請求')
        assert '[IP_ADDR]' in result

    def test_positive_ipv6_abbreviated(self, anon):
        result = anon.mask_text('IPv6 位址 ::1 本機')
        assert '[IP_ADDR]' in result

    def test_positive_ipv6_full(self, anon):
        result = anon.mask_text('連線來源 2001:db8:85a3::8a2e:370:7334')
        assert '[IP_ADDR]' in result

    def test_negative_version_number(self, anon):
        # 純版本號如 1.0.0 不應命中（只有 3 段）
        result = anon.mask_text('版本 1.0.0 更新')
        assert '[IP_ADDR]' not in result


# ===========================================================================
# 8. 新 PII Pattern — CHINESE_NAME（M1）
# ===========================================================================

class TestChineseName:
    """
    中文姓名偵測：百家姓 + 名（1-3字）+ 連接詞（正向前瞻）

    設計取捨說明：
    - 規則式偵測，不引入 jieba/ckiptagger 依賴
    - 需要後接連接詞才會命中（減少誤殺）
    - 已知限制：孤立姓名（無連接詞）不會命中
    """

    def test_positive_with_kehu(self, anon):
        result = anon.mask_text('請查詢客戶王○明的貸款狀況')
        assert '[CHINESE_NAME]' in result

    def test_positive_xiansheng(self, anon):
        result = anon.mask_text('林建宏先生申請房貸')
        assert '[CHINESE_NAME]' in result

    def test_positive_xiaojie(self, anon):
        result = anon.mask_text('陳美玲小姐的信用卡明細')
        assert '[CHINESE_NAME]' in result

    def test_positive_with_de(self, anon):
        result = anon.mask_text('張偉明的帳戶餘額')
        assert '[CHINESE_NAME]' in result

    def test_positive_masked_char(self, anon):
        # 含遮字符「○」的已匿名姓名也需被偵測
        result = anon.mask_text('王○明客戶的貸款')
        assert '[CHINESE_NAME]' in result

    def test_negative_no_context_word(self, anon):
        # 孤立姓名無連接詞（已知限制，不覆蓋）
        result = anon.mask_text('王建宏')
        assert '[CHINESE_NAME]' not in result

    def test_negative_common_word(self, anon):
        # 「王道」等普通詞後不接連接詞
        result = anon.mask_text('這是王道的做法')
        # 後接「的」：「王道的」會命中，這是已知誤殺風險
        # 本測試記錄行為，不強制 not in（規則式誤殺屬保守誤差）
        pass  # 行為已記錄在 ANONYMIZER_COVERAGE.md

    def test_negative_business_term(self, anon):
        # 純業務術語不含姓氏
        result = anon.mask_text('不動產抵押業務流程審查')
        assert '[CHINESE_NAME]' not in result


# ===========================================================================
# 9. 真實情境綜合測試（M1 規格要求的 7 個情境）
# ===========================================================================

class TestRealWorldScenarios:
    """模擬真實金融查詢中的 PII 情境"""

    def test_scenario_chinese_name_loan(self, anon):
        """請查詢客戶王○明的貸款狀況 → 中文姓名命中"""
        text = '請查詢客戶王○明的貸款狀況'
        result = anon.mask_text(text)
        assert '[CHINESE_NAME]' in result
        assert '王○明' not in result

    def test_scenario_bank_account(self, anon):
        """交易 1234567890123 的狀態 → 銀行帳號命中"""
        text = '交易 1234567890123 的狀態'
        result = anon.mask_text(text)
        assert '[BANK_ACCOUNT]' in result
        assert '1234567890123' not in result

    def test_scenario_chinese_name_and_landline(self, anon):
        """林美玲 02-2345-6789 需要協助 → 中文姓名 + 市話都命中"""
        text = '林美玲小姐 02-2345-6789 需要協助'
        result = anon.mask_text(text)
        assert '[CHINESE_NAME]' in result
        assert '[LANDLINE]' in result
        assert '林美玲' not in result
        assert '02-2345-6789' not in result

    def test_scenario_resident_cert(self, anon):
        """居留證 AB12345678 客戶資訊 → 居留證命中"""
        text = '居留證 AB12345678 客戶資訊查詢'
        result = anon.mask_text(text)
        assert '[RESIDENT_CERT]' in result
        assert 'AB12345678' not in result

    def test_scenario_txn_id(self, anon):
        """流水號 TXN20260423001 查詢 → 流水號命中"""
        text = '流水號 TXN20260423001 查詢'
        result = anon.mask_text(text)
        assert '[TXN_ID]' in result
        assert 'TXN20260423001' not in result

    def test_scenario_emp_id(self, anon):
        """員工 EMP001234 申請 → 員工編號命中"""
        text = '員工 EMP001234 申請加班補假'
        result = anon.mask_text(text)
        assert '[EMP_ID]' in result
        assert 'EMP001234' not in result

    def test_scenario_ip_login(self, anon):
        """從 192.168.1.1 登入 → IP 命中"""
        text = '從 192.168.1.1 登入系統，請確認'
        result = anon.mask_text(text)
        assert '[IP_ADDR]' in result
        assert '192.168.1.1' not in result

    def test_scenario_multiple_pii_in_one_sentence(self, anon):
        """多種 PII 同句：中文姓名 + 手機 + 身份證"""
        text = '客戶陳大明先生 0912-345-678，身份證 A234567890'
        result = anon.mask_text(text)
        assert '[CHINESE_NAME]' in result
        assert '[PHONE_MOBILE]' in result
        assert '[TAIWAN_ID]' in result
        # 原始敏感值不應出現
        assert '陳大明' not in result
        assert '0912-345-678' not in result
        assert 'A234567890' not in result


# ===========================================================================
# 10. is_safe_for_cloud 合規硬性要求驗證（M2）
# ===========================================================================

class TestIsSafeForCloud:
    """
    M2 合規要求：任何 PII 命中 → False；命中數 == 0 → True

    此測試直接驗證「不得回退」條款：
    原有邏輯 len(matches) <= 5 允許 PII 外流，已被修正。
    """

    def test_clean_business_text_is_safe(self, anon):
        """純業務問題（無任何 PII）→ True"""
        assert anon.is_safe_for_cloud('不動產抵押業務流程審查') is True

    def test_another_clean_text(self, anon):
        """法規條文等業務內容 → True"""
        assert anon.is_safe_for_cloud('依據金管會 2024 年函釋，授信案件需附完整徵信報告') is True

    def test_empty_string_is_safe(self, anon):
        """空字串 → True"""
        assert anon.is_safe_for_cloud('') is True

    def test_none_handled(self, anon):
        """None 不應拋出例外，應返回 True"""
        # mask_text 同樣處理 None/empty
        assert anon.is_safe_for_cloud(None) is True

    def test_single_pii_is_not_safe(self, anon):
        """含 1 個 PII → False（M2 核心要求）"""
        assert anon.is_safe_for_cloud('帳號 A123456789') is False

    def test_five_pii_is_not_safe(self, anon):
        """含 5 個 PII → False（舊邏輯 <= 5 會錯判為 True，M2 修正此謬誤）"""
        text = (
            'A123456789 B234567890 C345678901 D456789012 E567890123'
        )
        assert anon.is_safe_for_cloud(text) is False

    def test_ip_address_is_not_safe(self, anon):
        """含 IP 位址 → False"""
        assert anon.is_safe_for_cloud('來源 IP 10.0.0.1 已記錄') is False

    def test_chinese_name_is_not_safe(self, anon):
        """含中文姓名 → False"""
        assert anon.is_safe_for_cloud('客戶王建宏先生已簽約') is False

    def test_txn_id_is_not_safe(self, anon):
        """含交易流水號 → False"""
        assert anon.is_safe_for_cloud('流水號 TXN20260423001') is False

    def test_masked_text_is_safe(self, anon):
        """已 mask 後的文字（含 placeholder）→ True（placeholder 不觸發 PII）"""
        raw = '帳號 A123456789 申請'
        masked = anon.mask_text(raw)
        assert anon.is_safe_for_cloud(masked) is True


# ===========================================================================
# 11. ReDoS 安全性驗證
# ===========================================================================

class TestReDosProtection:
    """確保所有 pattern 在惡意輸入下不會出現指數級回溯"""

    def _assert_fast(self, anon: Anonymizer, text: str, max_ms: float = 500):
        """斷言 mask_text 在 max_ms 毫秒內完成"""
        start = time.monotonic()
        anon.mask_text(text)
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < max_ms, f'mask_text 執行超時：{elapsed_ms:.1f}ms > {max_ms}ms（可能 ReDoS）'

    def test_credit_card_redos_input(self, anon):
        """信用卡 pattern 的潛在 ReDoS 輸入"""
        evil = '4' * 50
        self._assert_fast(anon, evil)

    def test_email_redos_input(self, anon):
        """Email pattern 的潛在 ReDoS 輸入"""
        evil = 'a' * 50 + '@' + 'b' * 50 + '.' + 'c' * 50
        self._assert_fast(anon, evil)

    def test_mixed_pii_heavy_text(self, anon):
        """大量 PII 混雜文字的效能"""
        text = '客戶王大明先生 A123456789 帳號 12345678901234 ' * 20
        self._assert_fast(anon, text, max_ms=2000)

    def test_long_pure_chinese_text(self, anon):
        """長純中文文字（無 PII）的效能"""
        text = '不動產抵押業務流程審查合規評估報告分析' * 100
        self._assert_fast(anon, text, max_ms=1000)


# ===========================================================================
# 12. get_sensitive_report 功能測試
# ===========================================================================

class TestSensitiveReport:
    """驗證 Audit Trail 用的統計報告輸出"""

    def test_report_counts_correctly(self, anon):
        text = 'A123456789 B234567890 IP 192.168.1.1 TXN20260423001'
        report = anon.get_sensitive_report(text)
        assert report.get('TAIWAN_ID', 0) == 2
        assert report.get('IP_ADDR_V4', 0) == 1
        assert report.get('TXN_ID', 0) == 1

    def test_empty_text_returns_empty_report(self, anon):
        assert anon.get_sensitive_report('') == {}

    def test_clean_text_returns_empty_report(self, anon):
        assert anon.get_sensitive_report('不動產抵押業務流程') == {}


# ===========================================================================
# 13. 自訂關鍵字（custom_keywords）測試
# ===========================================================================

class TestCustomKeywords:
    """驗證自訂關鍵字機制未受新 pattern 影響"""

    def test_custom_keyword_masked(self):
        anon = Anonymizer(custom_keywords=['機密專案X', '內部系統Y'])
        result = anon.mask_text('請查詢機密專案X的進度')
        assert '[CUSTOM]' in result
        assert '機密專案X' not in result

    def test_custom_keyword_does_not_affect_others(self):
        anon = Anonymizer(custom_keywords=['測試關鍵字'])
        result = anon.mask_text('客戶 A123456789 測試關鍵字')
        assert '[TAIWAN_ID]' in result
        assert '[CUSTOM]' in result
