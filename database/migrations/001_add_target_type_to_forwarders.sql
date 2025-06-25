-- ============================================
-- 🔧 Add target_type to forwarders
-- ============================================
-- Adds the target_type column to distinguish between destination types (user, channel, etc.)

ALTER TABLE forwarders
ADD COLUMN IF NOT EXISTS target_type VARCHAR(50) DEFAULT 'unknown';

COMMENT ON COLUMN forwarders.target_type IS 'Type of the destination (e.g., user, group, channel)';

-- Update existing rows to have a default value
UPDATE forwarders
SET target_type = 'unknown'
WHERE target_type IS NULL;

-- ============================================
-- 📝 Update schema version
-- ============================================
UPDATE db_info SET value = '1.1.1', updated_at = NOW() WHERE key = 'schema_version';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Column "target_type" added to "forwarders" table successfully!';
    RAISE NOTICE '📝 Schema version updated to 1.1.1';
END $$; 