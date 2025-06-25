-- Add forwarders table for message forwarding functionality
CREATE TABLE IF NOT EXISTS forwarders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source_chat_id VARCHAR(50) NOT NULL,
    source_chat_title VARCHAR(255) NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('user', 'group', 'channel')),
    target_id VARCHAR(100) NOT NULL,
    target_name VARCHAR(255),
    container_name VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'stopped' CHECK (status IN ('running', 'stopped', 'error')),
    message_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, source_chat_id, target_id)
);

-- Index for faster queries
CREATE INDEX idx_forwarders_user_id ON forwarders(user_id);
CREATE INDEX idx_forwarders_source_chat_id ON forwarders(source_chat_id);
CREATE INDEX idx_forwarders_status ON forwarders(status);

-- Add comment
COMMENT ON TABLE forwarders IS 'Stores message forwarding configurations for Telegram chats'; 