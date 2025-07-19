-- =====================================================
-- COMPLETE FRESH MIGRATION: Opportunity Tracking
-- =====================================================
-- 
-- This migration safely adds opportunity tracking to your existing database.
-- It checks what already exists and only adds what's missing.
-- SAFE TO RUN multiple times - won't break existing data.
--
-- =====================================================

-- First, let's see what we're working with
DO $$
DECLARE
    table_exists BOOLEAN;
    col_count INTEGER;
BEGIN
    -- Check if opportunities table exists
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'opportunities'
    ) INTO table_exists;
    
    IF table_exists THEN
        SELECT COUNT(*) INTO col_count FROM public.opportunities;
        RAISE NOTICE '✅ Found opportunities table with % records', col_count;
    ELSE
        RAISE EXCEPTION 'opportunities table not found! Please check your database.';
    END IF;
END $$;

-- Step 1: Add new tracking columns (safe - only adds if missing)
-- -------------------------------------------------------------
DO $$ 
DECLARE
    col_exists BOOLEAN;
BEGIN
    RAISE NOTICE '📋 Adding tracking columns...';
    
    -- Check and add content_hash
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='content_hash'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN content_hash VARCHAR(64);
        RAISE NOTICE '  ✅ Added content_hash column';
    ELSE
        RAISE NOTICE '  ⏭️  content_hash column already exists';
    END IF;
    
    -- Check and add first_seen_at
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='first_seen_at'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE '  ✅ Added first_seen_at column';
    ELSE
        RAISE NOTICE '  ⏭️  first_seen_at column already exists';
    END IF;
    
    -- Check and add last_seen_at
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='last_seen_at'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE '  ✅ Added last_seen_at column';
    ELSE
        RAISE NOTICE '  ⏭️  last_seen_at column already exists';
    END IF;
    
    -- Check and add last_updated_at
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='last_updated_at'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN last_updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        RAISE NOTICE '  ✅ Added last_updated_at column';
    ELSE
        RAISE NOTICE '  ⏭️  last_updated_at column already exists';
    END IF;
    
    -- Check and add status
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='status'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN status VARCHAR(20) DEFAULT 'active';
        RAISE NOTICE '  ✅ Added status column';
    ELSE
        RAISE NOTICE '  ⏭️  status column already exists';
    END IF;
    
    -- Check and add consecutive_missing_count
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='consecutive_missing_count'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN consecutive_missing_count INTEGER DEFAULT 0;
        RAISE NOTICE '  ✅ Added consecutive_missing_count column';
    ELSE
        RAISE NOTICE '  ⏭️  consecutive_missing_count column already exists';
    END IF;
    
    -- Check and add similarity_group_id
    SELECT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name='opportunities' AND column_name='similarity_group_id'
    ) INTO col_exists;
    
    IF NOT col_exists THEN
        ALTER TABLE public.opportunities ADD COLUMN similarity_group_id VARCHAR(64);
        RAISE NOTICE '  ✅ Added similarity_group_id column';
    ELSE
        RAISE NOTICE '  ⏭️  similarity_group_id column already exists';
    END IF;
    
    RAISE NOTICE '📋 Column setup complete!';
END $$;

-- Step 2: Create indexes (safe - only creates if missing)
-- -------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE '🔍 Creating indexes...';
    
    -- Create indexes only if they don't exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_opportunities_content_hash') THEN
        CREATE INDEX idx_opportunities_content_hash ON public.opportunities(content_hash);
        RAISE NOTICE '  ✅ Created content_hash index';
    ELSE
        RAISE NOTICE '  ⏭️  content_hash index already exists';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_opportunities_status') THEN
        CREATE INDEX idx_opportunities_status ON public.opportunities(status);
        RAISE NOTICE '  ✅ Created status index';
    ELSE
        RAISE NOTICE '  ⏭️  status index already exists';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_opportunities_first_seen_at') THEN
        CREATE INDEX idx_opportunities_first_seen_at ON public.opportunities(first_seen_at);
        RAISE NOTICE '  ✅ Created first_seen_at index';
    ELSE
        RAISE NOTICE '  ⏭️  first_seen_at index already exists';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_opportunities_last_seen_at') THEN
        CREATE INDEX idx_opportunities_last_seen_at ON public.opportunities(last_seen_at);
        RAISE NOTICE '  ✅ Created last_seen_at index';
    ELSE
        RAISE NOTICE '  ⏭️  last_seen_at index already exists';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_opportunities_similarity_group_id') THEN
        CREATE INDEX idx_opportunities_similarity_group_id ON public.opportunities(similarity_group_id);
        RAISE NOTICE '  ✅ Created similarity_group_id index';
    ELSE
        RAISE NOTICE '  ⏭️  similarity_group_id index already exists';
    END IF;
    
    RAISE NOTICE '🔍 Index setup complete!';
END $$;

-- Step 3: Create helper functions (safe - replaces if exists)
-- -----------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE '⚙️ Creating helper functions...';
END $$;

-- Function to generate content hash for opportunities
CREATE OR REPLACE FUNCTION public.generate_opportunity_content_hash(
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
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to generate similarity group ID
CREATE OR REPLACE FUNCTION public.generate_similarity_group_id(
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
            LEFT(COALESCE(p_source_url, ''), 50)
    END;
    
    RETURN LEFT(
        encode(
            digest(
                CONCAT(
                    LEFT(LOWER(TRIM(COALESCE(p_title, ''))), 100), '|',
                    LOWER(TRIM(COALESCE(p_department, ''))), '|',
                    COALESCE(domain, '')
                ),
                'md5'
            ),
            'hex'
        ), 16
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DO $$
BEGIN
    RAISE NOTICE '⚙️ Helper functions created!';
END $$;

-- Step 4: Update existing opportunities with initial tracking data
-- ----------------------------------------------------------------
DO $$
DECLARE
    batch_size INTEGER := 100;
    total_rows INTEGER;
    processed INTEGER := 0;
    rows_to_update INTEGER;
BEGIN
    -- Count opportunities that need initial tracking data
    SELECT COUNT(*) INTO total_rows FROM public.opportunities;
    SELECT COUNT(*) INTO rows_to_update FROM public.opportunities 
    WHERE first_seen_at IS NULL OR last_seen_at IS NULL OR status IS NULL;
    
    RAISE NOTICE '📊 Found % total opportunities, % need initial tracking data', total_rows, rows_to_update;
    
    IF rows_to_update > 0 THEN
        RAISE NOTICE '🔄 Updating opportunities with initial tracking data...';
        
        -- Process in batches to avoid timeouts
        WHILE processed < rows_to_update LOOP
            -- Update batch with initial tracking values
            UPDATE public.opportunities 
            SET 
                first_seen_at = COALESCE(first_seen_at, scraped_at, CURRENT_TIMESTAMP),
                last_seen_at = COALESCE(last_seen_at, scraped_at, CURRENT_TIMESTAMP),
                last_updated_at = COALESCE(last_updated_at, scraped_at, CURRENT_TIMESTAMP),
                status = COALESCE(status, CASE 
                    WHEN is_active = true THEN 'active'
                    ELSE 'removed'
                END),
                consecutive_missing_count = COALESCE(consecutive_missing_count, 0)
            WHERE id IN (
                SELECT id 
                FROM public.opportunities 
                WHERE first_seen_at IS NULL OR last_seen_at IS NULL OR status IS NULL
                ORDER BY id
                LIMIT batch_size
                OFFSET processed
            );
            
            processed := processed + batch_size;
            
            RAISE NOTICE '  📝 Processed % / % opportunities', LEAST(processed, rows_to_update), rows_to_update;
        END LOOP;
    ELSE
        RAISE NOTICE '⏭️  All opportunities already have tracking data';
    END IF;
END $$;

-- Step 5: Generate content hashes for existing opportunities
-- ----------------------------------------------------------
DO $$
DECLARE
    batch_size INTEGER := 100;
    total_rows INTEGER;
    processed INTEGER := 0;
BEGIN
    -- Get total number of opportunities needing content hashes
    SELECT COUNT(*) INTO total_rows FROM public.opportunities WHERE content_hash IS NULL;
    
    IF total_rows > 0 THEN
        RAISE NOTICE '🔐 Generating content hashes for % opportunities...', total_rows;
        
        -- Process in batches
        WHILE processed < total_rows LOOP
            -- Update batch with content hashes
            UPDATE public.opportunities 
            SET content_hash = public.generate_opportunity_content_hash(
                title, 
                description, 
                department, 
                source_url, 
                deadline, 
                funding_amount
            )
            WHERE id IN (
                SELECT id 
                FROM public.opportunities 
                WHERE content_hash IS NULL
                ORDER BY id
                LIMIT batch_size
                OFFSET processed
            );
            
            processed := processed + batch_size;
            
            RAISE NOTICE '  🔐 Generated hashes for % / % opportunities', LEAST(processed, total_rows), total_rows;
        END LOOP;
    ELSE
        RAISE NOTICE '⏭️  All opportunities already have content hashes';
    END IF;
END $$;

-- Step 6: Generate similarity group IDs for existing opportunities
-- ----------------------------------------------------------------
DO $$
DECLARE
    batch_size INTEGER := 100;
    total_rows INTEGER;
    processed INTEGER := 0;
BEGIN
    -- Get total number of opportunities needing similarity group IDs
    SELECT COUNT(*) INTO total_rows FROM public.opportunities WHERE similarity_group_id IS NULL;
    
    IF total_rows > 0 THEN
        RAISE NOTICE '🏷️  Generating similarity group IDs for % opportunities...', total_rows;
        
        -- Process in batches
        WHILE processed < total_rows LOOP
            -- Update batch with similarity group IDs
            UPDATE public.opportunities 
            SET similarity_group_id = public.generate_similarity_group_id(
                title, 
                department, 
                source_url
            )
            WHERE id IN (
                SELECT id 
                FROM public.opportunities 
                WHERE similarity_group_id IS NULL
                ORDER BY id
                LIMIT batch_size
                OFFSET processed
            );
            
            processed := processed + batch_size;
            
            RAISE NOTICE '  🏷️  Generated group IDs for % / % opportunities', LEAST(processed, total_rows), total_rows;
        END LOOP;
    ELSE
        RAISE NOTICE '⏭️  All opportunities already have similarity group IDs';
    END IF;
END $$;

-- Step 7: Create monitoring views (safe - replaces if exists)
-- -----------------------------------------------------------
DO $$
BEGIN
    RAISE NOTICE '📊 Creating monitoring views...';
END $$;

-- View for opportunity status summary
CREATE OR REPLACE VIEW public.opportunity_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM public.opportunities 
WHERE is_active = true
GROUP BY status
ORDER BY count DESC;

-- View for recent activity
CREATE OR REPLACE VIEW public.recent_opportunity_activity AS
SELECT 
    'new' as activity_type,
    COUNT(*) as count,
    'Opportunities discovered in last 7 days' as description
FROM public.opportunities 
WHERE first_seen_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
    AND is_active = true

UNION ALL

SELECT 
    'updated' as activity_type,
    COUNT(*) as count,
    'Opportunities updated in last 7 days' as description
FROM public.opportunities 
WHERE last_updated_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
    AND last_updated_at != first_seen_at
    AND is_active = true

UNION ALL

SELECT 
    'missing' as activity_type,
    COUNT(*) as count,
    'Opportunities currently missing from scrapes' as description
FROM public.opportunities 
WHERE status = 'missing'
    AND is_active = true;

DO $$
BEGIN
    RAISE NOTICE '📊 Monitoring views created!';
END $$;

-- Step 8: Grant permissions (safe - updates if exists)
-- ----------------------------------------------------

-- Grant permissions to authenticated users
DO $$
BEGIN
    RAISE NOTICE '🔐 Setting up permissions...';
    
    -- Try to grant permissions, ignore if role doesn't exist
    BEGIN
        GRANT SELECT ON public.opportunity_status_summary TO authenticated;
        GRANT SELECT ON public.recent_opportunity_activity TO authenticated;
        GRANT EXECUTE ON FUNCTION public.generate_opportunity_content_hash(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT) TO authenticated;
        GRANT EXECUTE ON FUNCTION public.generate_similarity_group_id(TEXT, TEXT, TEXT) TO authenticated;
        RAISE NOTICE '  ✅ Granted permissions to authenticated role';
    EXCEPTION WHEN undefined_object THEN
        RAISE NOTICE '  ⏭️  authenticated role not found, skipping';
    END;
    
    -- Try to grant permissions to service_role
    BEGIN
        GRANT SELECT, INSERT, UPDATE ON public.opportunities TO service_role;
        GRANT SELECT ON public.opportunity_status_summary TO service_role;
        GRANT SELECT ON public.recent_opportunity_activity TO service_role;
        GRANT EXECUTE ON FUNCTION public.generate_opportunity_content_hash(TEXT, TEXT, TEXT, TEXT, TEXT, TEXT) TO service_role;
        GRANT EXECUTE ON FUNCTION public.generate_similarity_group_id(TEXT, TEXT, TEXT) TO service_role;
        RAISE NOTICE '  ✅ Granted permissions to service_role';
    EXCEPTION WHEN undefined_object THEN
        RAISE NOTICE '  ⏭️  service_role not found, skipping';
    END;
END $$;

-- Step 9: Final verification and summary
-- --------------------------------------
DO $$
DECLARE
    total_opportunities INTEGER;
    opportunities_with_hashes INTEGER;
    opportunities_with_groups INTEGER;
    status_counts RECORD;
BEGIN
    -- Get counts for verification
    SELECT COUNT(*) INTO total_opportunities FROM public.opportunities;
    SELECT COUNT(*) INTO opportunities_with_hashes FROM public.opportunities WHERE content_hash IS NOT NULL;
    SELECT COUNT(*) INTO opportunities_with_groups FROM public.opportunities WHERE similarity_group_id IS NOT NULL;
    
    RAISE NOTICE '';
    RAISE NOTICE '🎉 === MIGRATION COMPLETE === 🎉';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Summary:';
    RAISE NOTICE '   Total opportunities: %', total_opportunities;
    RAISE NOTICE '   With content hashes: %', opportunities_with_hashes;
    RAISE NOTICE '   With similarity groups: %', opportunities_with_groups;
    RAISE NOTICE '';
    
    RAISE NOTICE '📈 Status breakdown:';
    FOR status_counts IN 
        SELECT status, count 
        FROM public.opportunity_status_summary 
        ORDER BY count DESC
    LOOP
        RAISE NOTICE '   %: %', status_counts.status, status_counts.count;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE '✅ Your database now supports opportunity tracking!';
    RAISE NOTICE '🔍 New features available:';
    RAISE NOTICE '   - Duplicate detection via content hashing';
    RAISE NOTICE '   - Status tracking (new/active/missing/removed)';
    RAISE NOTICE '   - Timeline tracking (first/last seen, updated)';
    RAISE NOTICE '   - Similarity grouping for related opportunities';
    RAISE NOTICE '   - Analytics views for monitoring';
    RAISE NOTICE '';
    RAISE NOTICE '📊 Check your new views:';
    RAISE NOTICE '   SELECT * FROM opportunity_status_summary;';
    RAISE NOTICE '   SELECT * FROM recent_opportunity_activity;';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Ready for enhanced opportunity tracking!';
END $$; 