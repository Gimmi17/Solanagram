-- ============================================
-- 📝 Message Logging Table
-- ============================================
-- This table stores all logged messages from Telegram chats

CREATE TABLE IF NOT EXISTS message_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Chat information
    chat_id BIGINT NOT NULL,
    chat_title VARCHAR(255),
    chat_username VARCHAR(255),
    chat_type VARCHAR(50), -- 'private', 'group', 'supergroup', 'channel'
    
    -- Message information
    message_id BIGINT NOT NULL,
    sender_id BIGINT,
    sender_name VARCHAR(255),
    sender_username VARCHAR(255),
    
    -- Message content
    message_text TEXT,
    message_type VARCHAR(50), -- 'text', 'photo', 'video', 'document', 'sticker', etc.
    media_file_id VARCHAR(255),
    
    -- Timestamps
    message_date TIMESTAMP WITH TIME ZONE NOT NULL,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Logging session info
    logging_session_id INTEGER NOT NULL,
    
    -- Constraints
    CONSTRAINT unique_message_log UNIQUE (chat_id, message_id, logging_session_id)
);

-- ============================================
-- 🔍 Logging Sessions Table
-- ============================================
-- This table tracks active logging sessions

CREATE TABLE IF NOT EXISTS logging_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Chat being logged
    chat_id BIGINT NOT NULL,
    chat_title VARCHAR(255),
    chat_username VARCHAR(255),
    chat_type VARCHAR(50),
    
    -- Session status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Docker container info
    container_name VARCHAR(255),
    container_id VARCHAR(64),
    container_status VARCHAR(50) DEFAULT 'created',
    
    -- Statistics
    messages_logged INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints - only one active session per chat per user
    CONSTRAINT unique_active_session UNIQUE (user_id, chat_id, is_active)
);

-- ============================================
-- 📋 Indexes for Performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_message_logs_user_id ON message_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_chat_id ON message_logs(chat_id);
CREATE INDEX IF NOT EXISTS idx_message_logs_message_date ON message_logs(message_date);
CREATE INDEX IF NOT EXISTS idx_message_logs_logged_at ON message_logs(logged_at);
CREATE INDEX IF NOT EXISTS idx_message_logs_logging_session_id ON message_logs(logging_session_id);

CREATE INDEX IF NOT EXISTS idx_logging_sessions_user_id ON logging_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_logging_sessions_chat_id ON logging_sessions(chat_id);
CREATE INDEX IF NOT EXISTS idx_logging_sessions_is_active ON logging_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_logging_sessions_container_name ON logging_sessions(container_name);
CREATE INDEX IF NOT EXISTS idx_logging_sessions_created_at ON logging_sessions(created_at);

-- ============================================
-- 🔧 Triggers for updated_at
-- ============================================
DROP TRIGGER IF EXISTS update_logging_sessions_updated_at ON logging_sessions;
CREATE TRIGGER update_logging_sessions_updated_at
    BEFORE UPDATE ON logging_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 📊 Views for Analytics
-- ============================================
CREATE OR REPLACE VIEW active_logging_sessions AS
SELECT 
    ls.*,
    u.phone as user_phone,
    COUNT(ml.id) as total_messages
FROM logging_sessions ls
JOIN users u ON ls.user_id = u.id
LEFT JOIN message_logs ml ON ls.id = ml.logging_session_id
WHERE ls.is_active = true
GROUP BY ls.id, u.phone
ORDER BY ls.created_at DESC;

CREATE OR REPLACE VIEW chat_logging_stats AS
SELECT 
    chat_id,
    chat_title,
    chat_type,
    COUNT(DISTINCT ls.id) as total_sessions,
    COUNT(ml.id) as total_messages,
    MAX(ml.message_date) as last_message_date,
    MAX(ls.created_at) as last_session_created
FROM logging_sessions ls
LEFT JOIN message_logs ml ON ls.id = ml.logging_session_id
GROUP BY chat_id, chat_title, chat_type
ORDER BY total_messages DESC;

-- ============================================
-- 🧹 Functions for cleanup and management
-- ============================================
CREATE OR REPLACE FUNCTION cleanup_orphaned_logging_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Deactivate sessions where container doesn't exist anymore
    UPDATE logging_sessions 
    SET is_active = false, 
        container_status = 'removed',
        updated_at = NOW()
    WHERE container_status = 'error' 
    AND last_error_at < NOW() - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_logging_session_id(user_id INTEGER, chat_id BIGINT)
RETURNS INTEGER AS $$
DECLARE
    session_id INTEGER;
BEGIN
    SELECT id INTO session_id
    FROM logging_sessions
    WHERE user_id = $1 AND chat_id = $2 AND is_active = true
    LIMIT 1;
    
    RETURN session_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 🔐 Grant permissions
-- ============================================
GRANT ALL PRIVILEGES ON message_logs TO solanagram_user;
GRANT ALL PRIVILEGES ON message_logs_id_seq TO solanagram_user;
GRANT ALL PRIVILEGES ON logging_sessions TO solanagram_user;
GRANT ALL PRIVILEGES ON logging_sessions_id_seq TO solanagram_user;

-- ============================================
-- 📝 Update schema version
-- ============================================
UPDATE db_info SET value = '1.2.0', updated_at = NOW() WHERE key = 'schema_version';

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Message logging tables created successfully!';
    RAISE NOTICE '📊 New tables: message_logs, logging_sessions';
    RAISE NOTICE '🔍 New views: active_logging_sessions, chat_logging_stats';
    RAISE NOTICE '🧹 New cleanup function: cleanup_orphaned_logging_sessions()';
    RAISE NOTICE '📝 Schema version updated to 1.2.0';
END $$;