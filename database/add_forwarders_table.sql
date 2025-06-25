-- ============================================
-- 📤 Forwarders Table
-- ============================================
-- This table stores the configuration for message forwarding between groups

CREATE TABLE IF NOT EXISTS forwarders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Source group information
    source_chat_id BIGINT NOT NULL,
    source_chat_title VARCHAR(255),
    source_chat_username VARCHAR(255),
    
    -- Destination group information
    destination_chat_id BIGINT NOT NULL,
    destination_chat_title VARCHAR(255),
    destination_chat_username VARCHAR(255),
    
    -- Forwarder configuration
    is_active BOOLEAN DEFAULT TRUE,
    forward_media BOOLEAN DEFAULT TRUE,
    forward_text BOOLEAN DEFAULT TRUE,
    forward_stickers BOOLEAN DEFAULT TRUE,
    forward_documents BOOLEAN DEFAULT TRUE,
    add_source_info BOOLEAN DEFAULT TRUE,
    
    -- Docker container info
    container_name VARCHAR(255),
    container_id VARCHAR(64),
    container_status VARCHAR(50) DEFAULT 'created',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_forwarded_at TIMESTAMP WITH TIME ZONE,
    
    -- Statistics
    messages_forwarded INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT unique_user_source_dest UNIQUE (user_id, source_chat_id, destination_chat_id)
);

-- ============================================
-- 📋 Indexes for Performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_forwarders_user_id ON forwarders(user_id);
CREATE INDEX IF NOT EXISTS idx_forwarders_source_chat_id ON forwarders(source_chat_id);
CREATE INDEX IF NOT EXISTS idx_forwarders_destination_chat_id ON forwarders(destination_chat_id);
CREATE INDEX IF NOT EXISTS idx_forwarders_is_active ON forwarders(is_active);
CREATE INDEX IF NOT EXISTS idx_forwarders_container_name ON forwarders(container_name);
CREATE INDEX IF NOT EXISTS idx_forwarders_created_at ON forwarders(created_at);

-- ============================================
-- 🔧 Trigger for updated_at
-- ============================================
DROP TRIGGER IF EXISTS update_forwarders_updated_at ON forwarders;
CREATE TRIGGER update_forwarders_updated_at
    BEFORE UPDATE ON forwarders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 📊 View for Active Forwarders
-- ============================================
CREATE OR REPLACE VIEW active_forwarders AS
SELECT 
    f.*,
    u.phone as user_phone
FROM forwarders f
JOIN users u ON f.user_id = u.id
WHERE f.is_active = true
ORDER BY f.created_at DESC;

-- ============================================
-- 🧹 Function to clean orphaned forwarders
-- ============================================
CREATE OR REPLACE FUNCTION cleanup_orphaned_forwarders()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete forwarders where container doesn't exist anymore
    DELETE FROM forwarders 
    WHERE container_status = 'removed' 
    OR (container_status = 'error' AND last_error_at < NOW() - INTERVAL '7 days');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 🔐 Grant permissions
-- ============================================
GRANT ALL PRIVILEGES ON forwarders TO solanagram_user;
GRANT ALL PRIVILEGES ON forwarders_id_seq TO solanagram_user;

-- ============================================
-- 📝 Update schema version
-- ============================================
UPDATE db_info SET value = '1.1.0', updated_at = NOW() WHERE key = 'schema_version';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Forwarders table created successfully!';
    RAISE NOTICE '📊 New table: forwarders';
    RAISE NOTICE '🔍 New view: active_forwarders';
    RAISE NOTICE '🧹 New cleanup function: cleanup_orphaned_forwarders()';
    RAISE NOTICE '📝 Schema version updated to 1.1.0';
END $$; 