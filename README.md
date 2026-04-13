# 📡 BIA-Collectors (情報採集雷達)

負責自動化抓取外部金融法規、新聞與總體經濟資料，並透過雲端 LLM 進行結構化分析與 Layer 1 標準化。

---

## 🛠️ 核心功能

### 1. 多樣化採集器 (Collectors)
- **FSCCollector**：自動擷取台灣金管會最新公告、裁罰與法規。
- **MacroCollector**：監控全球重要財經數據。
- **SSRF 防禦機制**：內建網址白名單與重定向校驗，防止內網刺探攻擊。

### 2. 安全去識別化閘道 (Anonymizer)
- **PII 遮蔽**：自動識別並遮蔽身分證字號、信用卡號、EMAIL 等敏感資訊。
- **ReDoS 防護**：優化後的正規表示式，能防範「正則炸彈」導致的 CPU 癱瘓攻擊。

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
