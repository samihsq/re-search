-- Migration: Add opportunity tracking fields
-- Run this in your Supabase SQL Editor or PostgreSQL database

-- Add new tracking columns to opportunities table
ALTER TABLE public.opportunities 
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active',
ADD COLUMN IF NOT EXISTS consecutive_missing_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS similarity_group_id VARCHAR(64);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_opportunities_content_hash ON public.opportunities(content_hash);
CREATE INDEX IF NOT EXISTS idx_opportunities_status ON public.opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunities_first_seen_at ON public.opportunities(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_last_seen_at ON public.opportunities(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_opportunities_similarity_group_id ON public.opportunities(similarity_group_id);

-- Update existing opportunities with initial values
UPDATE public.opportunities 
SET 
    first_seen_at = COALESCE(scraped_at, CURRENT_TIMESTAMP),
    last_seen_at = COALESCE(scraped_at, CURRENT_TIMESTAMP),
    last_updated_at = COALESCE(scraped_at, CURRENT_TIMESTAMP),
    status = CASE 
        WHEN is_active = true THEN 'active'
        ELSE 'removed'
    END,
    consecutive_missing_count = 0
WHERE content_hash IS NULL;

-- Create a function to generate content hash for existing opportunities
CREATE OR REPLACE FUNCTION generate_opportunity_content_hash(
    p_title TEXT,
    p_description TEXT,
    p_department TEXT,
    p_source_url TEXT,
    p_deadline TEXT,
    p_funding_amount TEXT
) RETURNS VARCHAR(64) AS $$
BEGIN
    RETURN encode(
        sha256(
            CONCAT(
                LOWER(TRIM(COALESCE(p_title, ''))), '|',
                LOWER(TRIM(LEFT(COALESCE(p_description, ''), 500))), '|',
                LOWER(TRIM(COALESCE(p_department, ''))), '|',
                COALESCE(p_source_url, ''), '|',
                TRIM(COALESCE(p_deadline, '')), '|',
                TRIM(COALESCE(p_funding_amount, ''))
            )::bytea
        ),
        'hex'
    );
END;
$$ LANGUAGE plpgsql;

-- Generate content hashes for existing opportunities
UPDATE public.opportunities 
SET content_hash = generate_opportunity_content_hash(
    title, 
    description, 
    department, 
    source_url, 
    deadline, 
    funding_amount
)
WHERE content_hash IS NULL;

-- Create a function to generate similarity group ID
CREATE OR REPLACE FUNCTION generate_similarity_group_id(
    p_title TEXT,
    p_department TEXT,
    p_source_url TEXT
) RETURNS VARCHAR(64) AS $$
DECLARE
    domain TEXT;
BEGIN
    -- Extract domain from URL
    domain := CASE 
        WHEN p_source_url ~ '^https?://([^/]+)' THEN 
            LOWER(substring(p_source_url from '^https?://([^/]+)'))
        ELSE 
            LEFT(p_source_url, 50)
    END;
    
    RETURN encode(
        digest(
            CONCAT(
                LEFT(LOWER(TRIM(COALESCE(p_title, ''))), 100), '|',
                LOWER(TRIM(COALESCE(p_department, ''))), '|',
                COALESCE(domain, '')
            ),
            'md5'
        ),
        'hex'
    )::VARCHAR(16);
END;
$$ LANGUAGE plpgsql;

-- Generate similarity group IDs for existing opportunities
UPDATE public.opportunities 
SET similarity_group_id = generate_similarity_group_id(
    title, 
    department, 
    source_url
)
WHERE similarity_group_id IS NULL;

-- Drop the helper functions (optional - keep if you want to use them later)
-- DROP FUNCTION generate_opportunity_content_hash(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT);
-- DROP FUNCTION generate_similarity_group_id(TEXT, TEXT, TEXT);

-- Update the search vector trigger to include new fields in the index
DROP TRIGGER IF EXISTS opportunities_search_vector_update ON public.opportunities;

CREATE OR REPLACE FUNCTION public.opportunities_search_vector_update() 
RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.department, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.opportunity_type, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.eligibility_requirements, '')), 'D') ||
        setweight(to_tsvector('english', array_to_string(COALESCE(NEW.tags, ARRAY[]::text[]), ' ')), 'B');
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER opportunities_search_vector_update
    BEFORE INSERT OR UPDATE ON public.opportunities
    FOR EACH ROW
    EXECUTE FUNCTION public.opportunities_search_vector_update();

-- Grant permissions (adjust based on your setup)
GRANT SELECT, INSERT, UPDATE ON public.opportunities TO authenticated;

-- Create a view for opportunity status summary
CREATE OR REPLACE VIEW public.opportunity_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentage
FROM public.opportunities 
WHERE is_active = true
GROUP BY status
ORDER BY count DESC; 