# 📡 BIA-Collectors (外部情報採集與處理)

負責自動化抓取外部金融法規、新聞與總體經濟數據，並透過雲端 LLM 進行結構化分析。

---

## 🛠️ 核心功能

### 1. 採集器 (Collectors)
- **FSCCollector**：定期擷取台灣金管會 RSS 指令、法律修正與裁罰公告。
- **MacroCollector**：監控全球重要財經數據。

### 2. 安全去識別化閘道 (Anonymizer)
- **PII 攔截**：偵測身分證、信用卡、帳號等敏感資訊。
- **雲端安全門控**：若文本敏感度過高（Match 數 > 5），自動攔截發送到雲端，改由地端處理。

### 3. AI 分析層 (LLMProcessor)
- **結構化輸出**：使用 Gemini 1.5 Flash 搭配強制 JSON Schema。
- **專業分析**：自動生成 150 字戰略摘要、重要性評分 (1-10) 與目標角色建議。
- **向量化**：使用 `text-embedding-004` (768維) 產出向量存入 Supabase。

---

## 🚀 快速啟動

### 環境配置
建立 `.env` 檔案：
```bash
GEMINI_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

### 執行管線
```bash
pip install -r requirements.txt
python main.py
```

---

## 🏗️ 資料庫規範 (Layer 1 Spec)
本模組嚴格遵循 `intel_items` 20 個核心欄位規範，支援：
- **pgvector** 語意檢索。
- **MD5 去重** 機制。
- **批次檢查**：優化 N+1 查詢效能。

---
**Disclaimer:** All collection activities comply with public data accessibility guidelines.
