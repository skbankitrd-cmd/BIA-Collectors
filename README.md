# BIA-Collectors (Banking Intelligence Agent - Pipeline)

This repository hosts the data collection and AI processing pipeline for the Banking Intelligence Agent (BIA) system. It is designed to provide strategic decision support for high-level executives in the financial sector.

## Core Features
1. **Data Collection:** Automated scraping of financial regulatory news (e.g., FSC) and public financial media.
2. **Anonymization:** A local rule engine to redact sensitive information before sending data to cloud LLMs, ensuring data sovereignty.
3. **AI Analysis:** Leverages Gemini 1.5 Pro to generate professional financial summaries, classification, and importance scoring.
4. **Vectorization:** Generates 768-dimensional embeddings for every feed to support semantic search.
5. **Storage:** Seamless integration with Supabase (PostgreSQL + pgvector).

## Quick Start

### 1. Environment Setup
Create a `.env` file with the following:
```bash
GEMINI_API_KEY=your_gemini_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database (Supabase SQL)
Execute the following in your Supabase SQL Editor:

```sql
-- 1. Enable Vector Extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create Roles Table
CREATE TABLE public.user_roles (
    role_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create Intelligence Feed Table
CREATE TABLE public.intelligence_feed (
    feed_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name VARCHAR(100) NOT NULL,
    source_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    published_date TIMESTAMP WITH TIME ZONE,
    raw_content TEXT,
    summary TEXT NOT NULL,
    category VARCHAR(50),
    importance_score INTEGER CHECK (importance_score >= 1 AND importance_score <= 10),
    target_roles UUID[], 
    embedding VECTOR(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create Vector Index
CREATE INDEX ON public.intelligence_feed USING hnsw (embedding vector_cosine_ops);
```

### 4. Run Pipeline
```bash
# Initialize default roles
python utils/db_init.py

# Execute crawling and AI analysis
python main.py
```

## Automation (GitHub Actions)
The repository includes a GitHub Actions workflow. Set your environment variables in `Settings > Secrets > Actions` to enable daily automated runs at 00:00 UTC.

---
**Security Note:** All data sent to cloud LLMs is processed through an anonymization layer to protect privacy.
