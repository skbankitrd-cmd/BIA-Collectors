# BIA-Collectors（情報採集雷達）

BIA 生產線的第一層（Layer 1）。負責從外部自動採集金融法規、新聞與總體經濟資料，
經安全去識別化後存入 Supabase，供 AutoAgentBuilder 蒸餾使用。

---

## 系統需求

- Python 3.10+
- Redis（用於採集任務串流）
- Supabase 專案（`intel_items` 資料表 + pgvector extension）

```bash
pip install -r requirements.txt
```

設定環境變數（`.env`）：

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
REDIS_URL=redis://localhost:6379/0
GOOGLE_API_KEY=your-gemini-api-key   # 供 LLMProcessor 使用
```

---

## 採集管線

```
外部來源
  ├── FSCCollector     金管會官網（法規公告、裁罰動態）
  └── MacroCollector   宏觀經濟數據（利率、匯率、GDP）
        │
        ▼
  Redis Stream（raw_intel）   ← 非同步緩衝，pipeline_worker.py 消費
        │
        ▼
  Anonymizer（PII 去識別化）
  ├── is_safe_for_cloud()    高敏內容偵測，攔截不上雲端
  └── mask_text()            遮蔽身分證、卡號、電話（ReDoS 防護）
        │
        ▼
  LLMProcessor（AI 分析）
  ├── analyze_news()         摘要、重要性評分、情緒分析、標籤、實體抽取
  └── generate_embedding()   生成 768-dim 向量（供 pgvector 語意搜尋）
        │
        ▼
  SupabaseDB.insert_intel_item()
  └── intel_items 資料表（SHA-256 去重）
```

---

## 核心模組

| 模組 | 路徑 | 職責 |
|------|------|------|
| `FSCCollector` | `collectors/fsc_collector.py` | 金管會法規爬蟲（SSRF 白名單門控） |
| `MacroCollector` | `collectors/macro_collector.py` | 宏觀經濟數據採集 |
| `Anonymizer` | `processors/anonymizer.py` | PII 去識別化 + ReDoS 防護 |
| `GapAnalyzer` | `processors/gap_analyzer.py` | 外部新法規 vs. 現行規章落差分析 |
| `LLMProcessor` | `processors/llm_processor.py` | AI 分析（摘要/評分/向量化） |
| `SupabaseDB` | `database/supabase_client.py` | Supabase 讀寫介面 |
| `ReportGenerator` | `utils/report_generator.py` | 多格式報告生成協調器 |
| Excel/PDF/PPT/Word Exporter | `utils/exporters/` | 各格式輸出實作 |

---

## intel_items 資料架構（Layer 1 Spec）

```sql
-- database/00_init_schema.sql
intel_items (
  id              UUID PRIMARY KEY,
  source          VARCHAR,          -- 來源：fsc / macro / ...
  title           TEXT,
  body            TEXT,             -- 原始內容（未去識別化）
  summary         TEXT,             -- AI 摘要
  ai_summary      TEXT,             -- 詳細 AI 分析
  importance      INTEGER,          -- 重要性評分（0-100）
  sentiment_score FLOAT,            -- 情緒分數
  tags            JSONB,            -- 標籤清單
  entities        JSONB,            -- 實體清單（機構/人名/法條）
  sha256_hash     CHAR(64) UNIQUE,  -- SHA-256 去重（防 Hash 碰撞）
  embedding       vector(768),      -- pgvector 語意向量（需 pgvector extension）
  is_analyzed     BOOLEAN,
  analyzed_at     TIMESTAMP,
  created_at      TIMESTAMP
)
```

**安全向量空間**：當內容過於敏感無法上雲端處理時，
自動填入 `[1e-5]*768` 的安全向量，防止全零向量導致 pgvector 除零崩潰。

---

## 安全規範

### SSRF 防護（Guard 模式）
- 所有採集 URL 通過白名單驗證
- 監測 HTTP 重定向路徑，防止繞過白名單進入內網
- 禁止存取私有 IP 段（127.x / 10.x / 172.16-31.x / 192.168.x）

### PII 去識別化（Anonymizer — Reviewer 模式）
- 檢查清單與遮蔽邏輯硬性拆分，確保可獨立更新（`_PATTERNS` / `_PLACEHOLDERS`）
- 覆蓋 13 類 PII pattern（2026-04-23 合規審查擴充後）：
  - **基礎**：台灣身分證字號、信用卡號（PCI DSS、ReDoS hardened）、手機（09X-XXX-XXXX）、email、地址片段、客戶 ID
  - **新增**（合規 MUST M1）：中文姓名（百家姓 + 連接詞啟發式）、銀行帳號（10-14 位）、市話（0X-XXXX-XXXX）、外籍居留證、交易流水號（TXN/TRX）、員工編號（EMP/E）、IPv4/IPv6
- `is_safe_for_cloud()` 嚴格判定：**任何 PII 命中即 False**（合規硬性要求，禁止放寬）
- ReDoS 防護：所有正則表達式做複雜度限制，防止 Catastrophic Backtracking
- 詳細覆蓋度與已知盲區見 [`processors/ANONYMIZER_COVERAGE.md`](./processors/ANONYMIZER_COVERAGE.md)
- 合規測試：`tests/test_anonymizer_compliance.py`（70 個 case，含倒退防護）

---

## 執行

```bash
# 完整採集管線（採集 + 分析 + 入庫）
python main.py

# 背景 Worker（消費 Redis Stream）
python pipeline_worker.py
```

---

## 與下游的介面契約

輸出給 AutoAgentBuilder 蒸餾的資料必須滿足：

| 要求 | 原因 |
|------|------|
| `body` / `summary` 長度 ≥ 300 字 | AutoAgentBuilder SanityChecker 最低門檻 |
| `sha256_hash` 唯一 | 防止 ChromaDB 向量重複 |
| `embedding` 768 維，無全零向量 | pgvector 穩定性 |
| PII 完全去識別化 | 內容進入 LLM 前必須乾淨 |

---

**Disclaimer:** All collection activities comply with public data accessibility guidelines.
