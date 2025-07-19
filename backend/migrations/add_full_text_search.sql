-- Add full-text search capabilities to opportunities table

-- Add the search_vector column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'opportunities' 
        AND column_name = 'search_vector'
    ) THEN
        ALTER TABLE opportunities ADD COLUMN search_vector tsvector;
    END IF;
END
$$;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_opportunities_search_vector ON opportunities USING GIN(search_vector);

-- Update existing rows with search vectors
UPDATE opportunities SET search_vector = 
    setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
    setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
    setweight(to_tsvector('english', COALESCE(department, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(opportunity_type, '')), 'C') ||
    setweight(to_tsvector('english', COALESCE(eligibility_requirements, '')), 'D') ||
    setweight(to_tsvector('english', array_to_string(COALESCE(tags, ARRAY[]::text[]), ' ')), 'B');

-- Create function to automatically update search vector
CREATE OR REPLACE FUNCTION opportunities_search_vector_update() RETURNS trigger AS $$
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
DROP TRIGGER IF EXISTS opportunities_search_vector_update ON opportunities;
CREATE TRIGGER opportunities_search_vector_update
    BEFORE INSERT OR UPDATE ON opportunities
    FOR EACH ROW
    EXECUTE FUNCTION opportunities_search_vector_update(); 