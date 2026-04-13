-- BIA 2.0 核心資料庫架構 (Layer 1 規範版)

-- 1. 擴充功能
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. 角色表
CREATE TABLE IF NOT EXISTS public.user_roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. 情報項目表 (intel_items)
-- 對齊 IntelItem.to_dict() 欄位
CREATE TABLE IF NOT EXISTS public.intel_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    summary TEXT,
    body TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    importance SMALLINT DEFAULT 5,
    target_roles UUID[] DEFAULT '{}', -- 儲存角色 ID 陣列
    dedup_key TEXT UNIQUE,
    is_analyzed BOOLEAN DEFAULT false,
    sentiment_score FLOAT DEFAULT 0.0,
    tags TEXT[] DEFAULT '{}',
    entities JSONB DEFAULT '[]'::jsonb,
    ai_summary TEXT,
    pipeline_run_id UUID,
    embedding vector(768), -- 向量支援
    created_at TIMESTAMPTZ DEFAULT now()
);

-- [Security] RLS
ALTER TABLE public.intel_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Read Access" ON public.intel_items FOR SELECT USING (true);

-- 4. 索引
CREATE INDEX IF NOT EXISTS idx_intel_published_at ON public.intel_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_intel_importance ON public.intel_items (importance DESC);

-- 5. 初始資料
INSERT INTO public.user_roles (role_name, description) VALUES
('董事長', '決策核心'),
('法遵長', '合規把關'),
('資訊長', '技術引領'),
('營運長', '業務推動'),
('風險長', '風險控管')
ON CONFLICT (role_name) DO NOTHING;
