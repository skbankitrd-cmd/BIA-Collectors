# 📡 BIA-Collectors (情報採集雷達)

負責自動化抓取外部金融法規、新聞與總體經濟資料，並透過雲端 LLM 進行結構化分析與 Layer 1 標準化。

---

## 🛠️ 核心功能

### 1. 多樣化採集器 (Collectors) -【Guard 模式】
- **SSRF 深度門控**：作為 Harness 的 **Guard (守衛層)**，實作對網址白名單與重定向路徑的即時監測，確保情報來源安全。
- **FSCCollector / MacroCollector**：專業領域採集器，負責獲取金管會法規與宏觀經濟數據。

### 2. 安全去識別化閘道 (Anonymizer) -【Reviewer 模式】
- **硬性拆分檢查與方法**：實作 **Reviewer (審查員模式)**。將 PII (個人識別資訊) 的檢查清單與遮蔽邏輯分離，確保隱私審核標準可隨時更新。
- **ReDoS 防護**：作為安控的一環，防止正則表達式攻擊癱瘓系統資源。

---

## 🏗️ 資料庫規範 (Layer 1 Spec)
本模組嚴格遵循 `intel_items` 資料架構，支援：
- **SHA-256 去重**：防範 Hash 碰撞，確保情報唯一性。
- **pgvector**：支援 768 維語意檢索向量。
- **安全向量空間**：防止異常向量導致檢索崩潰。

---

## 🚀 執行
```bash
# 執行採集管線
python main.py
```

---
**Disclaimer:** All collection activities comply with public data accessibility guidelines.
