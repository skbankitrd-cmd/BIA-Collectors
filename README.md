# BIA-Collectors (Banking Intelligence Agent - 採集與分析端)

此儲存庫負責「BankingIntelligenceAgent (BIA)」系統的資料採集、AI 處理與儲存流程。

## 核心功能
1. **採集 (Collect):** 自動化抓取金管會新聞稿及其他金融公開資訊。
2. **去識別化 (Anonymize):** 透過地端規則引擎遮蔽敏感字串。
3. **AI 分析 (Process):** 利用 Gemini 1.5 Pro 生成專業摘要、分類與評分。
4. **向量化 (Embed):** 生成文本向量，支援前端 RAG 語意搜尋。
5. **儲存 (Store):** 將處理後的情報存入 Supabase (PostgreSQL + pgvector)。

## 快速開始

### 1. 環境設定
複製 `.env.example` 並重新命名為 `.env`，填入您的 API Key：
```bash
GEMINI_API_KEY=您的_Gemini_API_Key
SUPABASE_URL=您的_Supabase_URL
SUPABASE_SERVICE_ROLE_KEY=您的_Supabase_Service_Role_Key
```

### 2. 安裝依賴
```bash
pip install -r requirements.txt
```

### 3. 初始化資料庫 (Supabase)
請先在 Supabase 執行以下 SQL (Schema 定義)：

```sql
-- 啟用向量擴充
CREATE EXTENSION IF NOT EXISTS vector;

-- 使用者角色表
CREATE TABLE public.user_roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 外部情報來源表
CREATE TABLE public.intelligence_feed (
    feed_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name VARCHAR(100) NOT NULL,
    source_url TEXT UNIQUE NOT NULL, -- 確保 URL 不重複
    title TEXT NOT NULL,
    published_date TIMESTAMP WITH TIME ZONE,
    raw_content TEXT,
    summary TEXT NOT NULL,
    category VARCHAR(50),
    importance_score INTEGER CHECK (importance_score >= 1 AND importance_score <= 10),
    target_roles UUID[], -- 關聯的角色 UUID 陣列
    embedding VECTOR(768), -- Gemini Embedding 維度通常為 768
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 建立索引
CREATE INDEX ON public.intelligence_feed USING hnsw (embedding vector_cosine_ops);
```

執行初始化腳本以新增預設角色：
```bash
python utils/db_init.py
```

### 4. 執行採集管線
```bash
python main.py
```

## 自動化排程 (GitHub Actions)
專案已內建 GitHub Actions 設定，會於每日台灣時間早上 08:00 自動執行。

### 如何設定 Secrets：
當您將此儲存庫上傳至 GitHub 後，請至：
`Settings > Secrets and variables > Actions > New repository secret`

新增以下三個 Secrets：
1. `GEMINI_API_KEY`: 您的 Gemini API Key。
2. `SUPABASE_URL`: 您的 Supabase Project URL。
3. `SUPABASE_SERVICE_ROLE_KEY`: 您的 Supabase Service Role Key (秘密金鑰)。

設定完成後，您可以至 GitHub 的 `Actions` 分頁，點擊 `BIA Daily Intelligence Crawl` 並選擇 `Run workflow` 進行手動測試。

---
**備註：** 本系統嚴格遵守「邏輯分離」原則，所有傳送到雲端 LLM 的數據均經過 Anonymizer 模組處理。
