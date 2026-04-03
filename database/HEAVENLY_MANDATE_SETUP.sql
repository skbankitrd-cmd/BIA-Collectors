-- BIA 2.0 規格大對齊 (完全遵照 Layer 1 儲存設計文件)

-- 1. 啟用必要的擴充功能
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. 建立「天條規範」的 intel_items 表格
DROP TABLE IF EXISTS public.intelligence_feed; -- 刪除舊表
DROP TABLE IF EXISTS public.intel_items;      -- 確保乾淨

CREATE TABLE public.intel_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dedup_key CHAR(32) UNIQUE,              -- MD5(title+url) 自然鍵
    source VARCHAR(60) NOT NULL,            -- 來源名稱
    category TEXT CHECK (category IN ('rss', 'scrape', 'api')) DEFAULT 'rss',
    title TEXT NOT NULL,
    summary TEXT,
    body TEXT,                              -- 原始內文 (全文)
    url TEXT,                               -- 原文連結
    published_at TIMESTAMPTZ,               -- 媒體原始發布時間
    fetched_at TIMESTAMPTZ DEFAULT now(),   -- 採集器取得時間
    analyzed_at TIMESTAMPTZ,                -- 分析完成時間
    expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '90 days'), -- 自動清理時間
    importance SMALLINT DEFAULT 0,          -- 0無關 10危機
    sentiment_score SMALLINT,               -- -5~+5
    tags TEXT[] DEFAULT '{}',               -- 標籤陣列
    entities JSONB DEFAULT '[]'::jsonb,     -- NER 實體辨識
    ai_summary TEXT,                        -- Claude/Gemini 生成的精華摘要
    is_analyzed BOOLEAN DEFAULT FALSE,      -- 是否已完成分析
    is_featured BOOLEAN DEFAULT FALSE,      -- 是否入選當日晨報
    pipeline_run_id UUID,                   -- 採集批次 ID
    embedding vector(768)                   -- 向量支援
);

-- 3. 建立規範要求的索引
CREATE INDEX idx_fetched ON public.intel_items (fetched_at DESC);
CREATE INDEX idx_imp ON public.intel_items (importance DESC, fetched_at DESC) WHERE is_analyzed = TRUE;

-- 4. 使用者角色表保持不變，但確保資料存在
CREATE TABLE IF NOT EXISTS public.user_roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO public.user_roles (role_name, description) VALUES
('董事長', '決策核心'), ('法遵長', '合規把關'), ('資訊長', '技術引領'), ('營運長', '業務推動'), ('風險長', '風險控管')
ON CONFLICT (role_name) DO NOTHING;
