-- ============================================
-- 🎯 Message Listeners and Elaborations
-- ============================================
-- New architecture for unified message processing

-- ============================================
-- 📡 Message Listeners Table
-- ============================================
-- Container that listen to messages from a chat
CREATE TABLE IF NOT EXISTS message_listeners (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Source chat information
    source_chat_id BIGINT NOT NULL,
    source_chat_title VARCHAR(255) NOT NULL,
    source_chat_type VARCHAR(50),
    
    -- Container information
    container_name VARCHAR(255) UNIQUE NOT NULL,
    container_status VARCHAR(50) DEFAULT 'stopped' CHECK (container_status IN ('running', 'stopped', 'error', 'creating')),
    
    -- Configuration
    is_active BOOLEAN DEFAULT TRUE,
    save_messages BOOLEAN DEFAULT TRUE,
    
    -- Statistics
    messages_received INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT unique_user_chat_listener UNIQUE (user_id, source_chat_id)
);

-- ============================================
-- 🔧 Message Elaborations Table
-- ============================================
-- Processing rules for messages (extractor or redirect)
CREATE TABLE IF NOT EXISTS message_elaborations (
    id SERIAL PRIMARY KEY,
    listener_id INTEGER NOT NULL REFERENCES message_listeners(id) ON DELETE CASCADE,
    
    -- Elaboration type
    elaboration_type VARCHAR(50) NOT NULL CHECK (elaboration_type IN ('extractor', 'redirect')),
    elaboration_name VARCHAR(255) NOT NULL,
    
    -- Configuration based on type
    -- For 'extractor': {"rules": [{"search_text": "addr", "extract_length": 43}]}
    -- For 'redirect': {"target_type": "group", "target_id": "123456", "target_name": "MyGroup"}
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- For execution order
    
    -- Statistics
    processed_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_processed_at TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    last_error_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_listener_elaboration_name UNIQUE (listener_id, elaboration_name),
    -- Only one redirect per listener
    CONSTRAINT single_redirect_per_listener EXCLUDE (listener_id WITH =) WHERE (elaboration_type = 'redirect')
);

-- ============================================
-- 📝 Saved Messages Table
-- ============================================
-- Raw messages saved from listeners
CREATE TABLE IF NOT EXISTS saved_messages (
    id SERIAL PRIMARY KEY,
    listener_id INTEGER NOT NULL REFERENCES message_listeners(id) ON DELETE CASCADE,
    
    -- Message data
    message_id BIGINT NOT NULL,
    message_text TEXT,
    message_data JSONB, -- Full message object
    sender_id BIGINT,
    sender_name VARCHAR(255),
    
    -- Timestamps
    message_date TIMESTAMP WITH TIME ZONE,
    saved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT unique_listener_message UNIQUE (listener_id, message_id)
);

-- ============================================
-- 🔍 Extracted Values Table
-- ============================================
-- Values extracted by extractor elaborations
CREATE TABLE IF NOT EXISTS elaboration_extracted_values (
    id SERIAL PRIMARY KEY,
    elaboration_id INTEGER NOT NULL REFERENCES message_elaborations(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES saved_messages(id) ON DELETE CASCADE,
    
    -- Extraction data
    rule_name VARCHAR(255),
    extracted_value TEXT,
    occurrence_index INTEGER DEFAULT 0,
    
    -- Timestamps
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes
    CONSTRAINT unique_extraction UNIQUE (elaboration_id, message_id, rule_name, occurrence_index)
);

-- ============================================
-- 📋 Indexes for Performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_message_listeners_user_id ON message_listeners(user_id);
CREATE INDEX IF NOT EXISTS idx_message_listeners_source_chat_id ON message_listeners(source_chat_id);
CREATE INDEX IF NOT EXISTS idx_message_listeners_container_status ON message_listeners(container_status);
CREATE INDEX IF NOT EXISTS idx_message_listeners_is_active ON message_listeners(is_active);

CREATE INDEX IF NOT EXISTS idx_message_elaborations_listener_id ON message_elaborations(listener_id);
CREATE INDEX IF NOT EXISTS idx_message_elaborations_type ON message_elaborations(elaboration_type);
CREATE INDEX IF NOT EXISTS idx_message_elaborations_is_active ON message_elaborations(is_active);
CREATE INDEX IF NOT EXISTS idx_message_elaborations_priority ON message_elaborations(priority);

CREATE INDEX IF NOT EXISTS idx_saved_messages_listener_id ON saved_messages(listener_id);
CREATE INDEX IF NOT EXISTS idx_saved_messages_message_date ON saved_messages(message_date);
CREATE INDEX IF NOT EXISTS idx_saved_messages_sender_id ON saved_messages(sender_id);

CREATE INDEX IF NOT EXISTS idx_extracted_values_elaboration_id ON elaboration_extracted_values(elaboration_id);
CREATE INDEX IF NOT EXISTS idx_extracted_values_message_id ON elaboration_extracted_values(message_id);

-- ============================================
-- 🔧 Triggers for updated_at
-- ============================================
DROP TRIGGER IF EXISTS update_message_listeners_updated_at ON message_listeners;
CREATE TRIGGER update_message_listeners_updated_at
    BEFORE UPDATE ON message_listeners
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_message_elaborations_updated_at ON message_elaborations;
CREATE TRIGGER update_message_elaborations_updated_at
    BEFORE UPDATE ON message_elaborations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 📊 Views for Dashboard
-- ============================================
CREATE OR REPLACE VIEW active_listeners_summary AS
SELECT 
    ml.id,
    ml.user_id,
    ml.source_chat_id,
    ml.source_chat_title,
    ml.source_chat_type,
    ml.container_status,
    ml.messages_received,
    ml.last_message_at,
    COUNT(DISTINCT me.id) as elaboration_count,
    COUNT(DISTINCT CASE WHEN me.elaboration_type = 'extractor' THEN me.id END) as extractor_count,
    COUNT(DISTINCT CASE WHEN me.elaboration_type = 'redirect' THEN me.id END) as redirect_count
FROM message_listeners ml
LEFT JOIN message_elaborations me ON ml.id = me.listener_id AND me.is_active = true
WHERE ml.is_active = true
GROUP BY ml.id;

-- ============================================
-- 🧹 Cleanup Functions
-- ============================================
CREATE OR REPLACE FUNCTION cleanup_old_saved_messages()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete messages older than 30 days
    DELETE FROM saved_messages 
    WHERE saved_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 🔐 Grant permissions
-- ============================================
GRANT ALL PRIVILEGES ON message_listeners TO solanagram_user;
GRANT ALL PRIVILEGES ON message_listeners_id_seq TO solanagram_user;
GRANT ALL PRIVILEGES ON message_elaborations TO solanagram_user;
GRANT ALL PRIVILEGES ON message_elaborations_id_seq TO solanagram_user;
GRANT ALL PRIVILEGES ON saved_messages TO solanagram_user;
GRANT ALL PRIVILEGES ON saved_messages_id_seq TO solanagram_user;
GRANT ALL PRIVILEGES ON elaboration_extracted_values TO solanagram_user;
GRANT ALL PRIVILEGES ON elaboration_extracted_values_id_seq TO solanagram_user;

-- ============================================
-- 📝 Update schema version
-- ============================================
UPDATE db_info SET value = '1.2.0', updated_at = NOW() WHERE key = 'schema_version';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Message listeners and elaborations tables created successfully!';
    RAISE NOTICE '📊 New tables: message_listeners, message_elaborations, saved_messages, elaboration_extracted_values';
    RAISE NOTICE '🔍 New view: active_listeners_summary';
    RAISE NOTICE '🧹 New cleanup function: cleanup_old_saved_messages()';
    RAISE NOTICE '📝 Schema version updated to 1.2.0';
END $$; 