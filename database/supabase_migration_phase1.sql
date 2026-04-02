-- BIA 2.0 資料庫升級腳本 (Phase 1)
-- 請複製以下語法並貼上至 Supabase 的 SQL Editor 執行

-- 1. 新增去重用的 dedup_key，並設定為 UNIQUE 確保不重複寫入
ALTER TABLE public.intelligence_feed
ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(255) UNIQUE;

-- 2. 新增情緒分數，範圍設定為 -5 (極度負面) 到 5 (極度正面)
ALTER TABLE public.intelligence_feed
ADD COLUMN IF NOT EXISTS sentiment_score SMALLINT;

-- 3. 新增實體辨識 (NER) 結果，儲存如 {"type":"org", "name":"金管會"} 的 JSON 陣列
ALTER TABLE public.intelligence_feed
ADD COLUMN IF NOT EXISTS entities JSONB DEFAULT '[]'::jsonb;

-- 4. 新增標籤陣列，便於前端進行快速過濾 (如 ['資安', '罰款'])
ALTER TABLE public.intelligence_feed
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';

-- 5. 新增 AI 精煉摘要 (100字內短摘要，供小秘書對話泡泡使用)
ALTER TABLE public.intelligence_feed
ADD COLUMN IF NOT EXISTS ai_summary TEXT;
