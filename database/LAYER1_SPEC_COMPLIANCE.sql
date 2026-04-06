-- Layer 1 資料儲存標準化腳本 (符合 3.layer1_storage_design.html 規範)

-- 1. 啟用 UUID 擴充
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. 建立 intel_items 主表
CREATE TABLE IF NOT EXISTS public.intel_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dedup_key CHAR(32) UNIQUE NOT NULL,      -- MD5(title + url)
    source VARCHAR(60) NOT NULL,             -- 來源名稱 (如: 金管會)
    category VARCHAR(20) NOT NULL,           -- rss / scrape / api
    title TEXT NOT NULL,                     -- 標題 (上限 500 字)
    summary TEXT,                            -- RSS 摘要或爬蟲前 600 字
    body TEXT,                               -- 全文 (爬蟲才有)
    url TEXT,                                -- 原始連結
    published_at TIMESTAMPTZ,                -- 媒體原始發布時間
    fetched_at TIMESTAMPTZ DEFAULT now(),    -- 採集器取得時間
    analyzed_at TIMESTAMPTZ,                 -- 分析完成時間
    expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '90 days'), -- 自動清理時間
    importance SMALLINT CHECK (importance >= 0 AND importance <= 10), -- 0-10
    sentiment_score SMALLINT CHECK (sentiment_score >= -5 AND sentiment_score <= 5), -- -5~+5
    tags TEXT[] DEFAULT '{}',                -- 標籤陣列
    entities JSONB DEFAULT '[]'::jsonb,      -- NER 實體辨識結果
    ai_summary TEXT,                         -- Claude 生成的精華摘要
    is_analyzed BOOLEAN DEFAULT FALSE,       -- 是否已完成分析
    is_featured BOOLEAN DEFAULT FALSE,       -- 是否入選晨報
    pipeline_run_id UUID                     -- 採集批次 ID (稽核追溯)
);

-- 3. 建立效能索引 (完全遵循手冊 3.2 節)
CREATE INDEX IF NOT EXISTS idx_intel_fetched ON public.intel_items (fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_intel_importance ON public.intel_items (importance DESC, fetched_at DESC) WHERE is_analyzed = TRUE;
CREATE INDEX IF NOT EXISTS idx_intel_pipeline ON public.intel_items (pipeline_run_id);
