-- =========================================================
-- BIA 系統最終資料庫架構 (V2 FINAL)
-- 適用於：通用系統轉生引擎 & 金融情報雷達
-- 修正內容：
-- 1. 統一表名為 intel_items
-- 2. 修正 UUID 與 dedup_key 長度限制
-- 3. 補齊 target_roles (UUID 陣列) 欄位
-- 4. 預設啟用 vector 與 pgcrypto 擴充
-- =========================================================

-- [1] 清理舊架構 (危險操作，請謹慎執行)
DROP TABLE IF EXISTS public.intel_items CASCADE;
DROP TABLE IF EXISTS public.user_roles CASCADE;

-- [2] 啟用擴充功能
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- [3] 建立使用者角色表 (RBAC 核心)
CREATE TABLE public.user_roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- [4] 建立情報項目表 (Layer 1 規範)
CREATE TABLE public.intel_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT,
    summary TEXT,
    body TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    importance SMALLINT DEFAULT 5,
    target_roles UUID[] DEFAULT '{}',      -- 儲存授權存取此情報的角色 ID
    dedup_key TEXT UNIQUE,                  -- 去重索引 (使用 TEXT 避免長度限制)
    is_analyzed BOOLEAN DEFAULT false,
    sentiment_score FLOAT DEFAULT 0.0,
    tags TEXT[] DEFAULT '{}',
    entities JSONB DEFAULT '[]'::jsonb,
    ai_summary TEXT,                        -- 語音摘要
    pipeline_run_id UUID,
    embedding vector(768),                  -- Gemini 1.5 Embedding (768維)
    created_at TIMESTAMPTZ DEFAULT now()
);

-- [5] 建立效能索引
CREATE INDEX IF NOT EXISTS idx_intel_published_at ON public.intel_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_intel_importance ON public.intel_items (importance DESC);
CREATE INDEX IF NOT EXISTS idx_intel_dedup ON public.intel_items (dedup_key);

-- [6] 安全設定 (Row Level Security)
ALTER TABLE public.intel_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public Read Access" ON public.intel_items FOR SELECT USING (true);

-- [7] 注入初始金融角色資料
INSERT INTO public.user_roles (role_name, description) VALUES
('董事長', '決策核心，關注總體策略與重大風險'),
('法遵長', '合規把關，關注金管會裁罰與法規更新'),
('資訊長', '技術引領，關注資安、金融科技與 AI 發展'),
('營運長', '業務推動，關注同業動態與市場營運'),
('風險長', '風險控管，關注信用、市場及營運風險')
ON CONFLICT (role_name) DO NOTHING;

-- =========================================================
-- SQL 腳本結束
-- =========================================================
