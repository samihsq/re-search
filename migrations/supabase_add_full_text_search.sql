-- Supabase Migration: Add full-text search capabilities to opportunities table
-- Run this in your Supabase SQL Editor

-- Add the search_vector column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'opportunities' 
        AND column_name = 'search_vector'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.opportunities ADD COLUMN search_vector tsvector;
    END IF;
END
$$;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_opportunities_search_vector 
ON public.opportunities USING GIN(search_vector);

-- Update existing rows with search vectors
-- This combines multiple fields with different weights:
-- A = highest priority (title)
-- B = high priority (description, tags)
-- C = medium priority (department, opportunity_type)
-- D = low priority (eligibility_requirements)
UPDATE public.opportunities SET search_vector = 
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(department, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(opportunity_type, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(eligibility_requirements, '')), 'D') ||
    setweight(to_tsvector('english', array_to_string(COALESCE(tags, ARRAY[]::text[]), ' ')), 'B')
WHERE search_vector IS NULL;

-- Create function to automatically update search vector
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

-- Create trigger to automatically update search vector on insert or update
DROP TRIGGER IF EXISTS opportunities_search_vector_update ON public.opportunities;
CREATE TRIGGER opportunities_search_vector_update
    BEFORE INSERT OR UPDATE ON public.opportunities
    FOR EACH ROW
    EXECUTE FUNCTION public.opportunities_search_vector_update();

-- Grant necessary permissions (adjust based on your Supabase setup)
-- These might not be needed depending on your RLS policies
GRANT SELECT ON public.opportunities TO anon, authenticated;
GRANT INSERT, UPDATE ON public.opportunities TO authenticated;

-- Optional: Create a view for testing search functionality
CREATE OR REPLACE VIEW public.search_test AS
SELECT 
    id,
    title,
    description,
    department,
    ts_rank(search_vector, to_tsquery('english', 'research')) as rank
FROM public.opportunities 
WHERE search_vector @@ to_tsquery('english', 'research')
ORDER BY rank DESC;

-- Test query example (you can run this to verify it works):
-- SELECT id, title, department, 
--        ts_rank(search_vector, to_tsquery('english', 'machine & learning')) as rank
-- FROM public.opportunities 
-- WHERE search_vector @@ to_tsquery('english', 'machine & learning')
-- ORDER BY rank DESC
-- LIMIT 10; 