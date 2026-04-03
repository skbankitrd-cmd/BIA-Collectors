-- BIA 2.0 完整資料庫初始化腳本 (一次性執行)

-- 1. 啟用必要的擴充功能 (向量搜尋與 UUID)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. 建立「使用者角色」表格
CREATE TABLE IF NOT EXISTS public.user_roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. 建立「智慧情報饋送」主表
CREATE TABLE IF NOT EXISTS public.intelligence_feed (
    feed_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dedup_key VARCHAR(255) UNIQUE,          -- 去重金鑰 (MD5)
    source_name TEXT NOT NULL,              -- 來源 (如: 金管會)
    source_url TEXT,                        -- 原始網址
    title TEXT NOT NULL,                    -- 標題
    published_date TIMESTAMPTZ,             -- 官方發布日期
    fetched_at TIMESTAMPTZ DEFAULT now(),   -- 系統抓取日期
    raw_content TEXT,                       -- 原始內文
    summary TEXT,                           -- AI 生成摘要
    ai_summary TEXT,                        -- 小秘書語音摘要 (100字內)
    category TEXT,                          -- 分類 (如: 法規遵循)
    importance_score SMALLINT,              -- 重要性 (1-10)
    sentiment_score SMALLINT,               -- 情緒分數 (-5 到 5)
    entities JSONB DEFAULT '[]'::jsonb,     -- 實體辨識 (NER)
    tags TEXT[] DEFAULT '{}',               -- 標籤陣列
    target_roles UUID[],                    -- 目標角色 ID 陣列
    embedding vector(768),                  -- 向量資料 (Gemini Embedding 768維)
    is_featured BOOLEAN DEFAULT false       -- 是否入選精選
);

-- 4. 建立索引以提升搜尋效能
CREATE INDEX IF NOT EXISTS idx_feed_published_date ON public.intelligence_feed (published_date DESC);
CREATE INDEX IF NOT EXISTS idx_feed_importance ON public.intelligence_feed (importance_score DESC);

-- 5. 插入初始角色資料 (這對前端顯示至關重要)
INSERT INTO public.user_roles (role_name, description) VALUES
('董事長', '決策核心，關注總體策略與重大風險'),
('法遵長', '合規把關，關注金管會裁罰與法規更新'),
('資訊長', '技術引領，關注資安、金融科技與 AI 發展'),
('營運長', '業務推動，關注同業動態與市場營運'),
('風險長', '風險控管，關注信用、市場及營運風險')
ON CONFLICT (role_name) DO NOTHING;
