-- ============================================
-- 🔧 Add missing columns to forwarders table
-- ============================================
-- Adds target_id and target_name columns that the application expects

ALTER TABLE forwarders
ADD COLUMN IF NOT EXISTS target_id BIGINT;

ALTER TABLE forwarders  
ADD COLUMN IF NOT EXISTS target_name VARCHAR(255);

-- Add comments for clarity
COMMENT ON COLUMN forwarders.target_id IS 'ID of the target chat/user';
COMMENT ON COLUMN forwarders.target_name IS 'Name of the target chat/user';

-- Update existing rows to have sensible default values
UPDATE forwarders
SET target_id = destination_chat_id
WHERE target_id IS NULL;

UPDATE forwarders
SET target_name = destination_chat_title
WHERE target_name IS NULL;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Missing columns added to "forwarders" table successfully!';
    RAISE NOTICE '📝 Added: target_id, target_name';
END $$; 