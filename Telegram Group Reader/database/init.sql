-- 🗄️ Telegram Chat Manager - Database Schema
-- Initial database setup for development

-- ============================================
-- 🔐 Create Extensions
-- ============================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 👤 Users Table
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(15) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- 📱 Telegram API Credentials (stored encrypted)
    api_id INTEGER,
    api_hash_encrypted TEXT,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Indexes for performance
    CONSTRAINT users_phone_check CHECK (phone ~ '^\+?[1-9]\d{1,14}$')
);

-- ============================================
-- 📱 User Sessions Table (for web sessions, not Telegram)
-- ============================================
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_agent TEXT,
    ip_address INET
);

-- ============================================
-- 📊 Usage Statistics (optional)
-- ============================================
CREATE TABLE IF NOT EXISTS usage_stats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 📋 Indexes for Performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_usage_stats_user_id ON usage_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_action ON usage_stats(action);
CREATE INDEX IF NOT EXISTS idx_usage_stats_created_at ON usage_stats(created_at);

-- ============================================
-- 🔧 Functions and Triggers
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to clean expired sessions
CREATE OR REPLACE FUNCTION clean_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 👤 Create Default Admin User (Development Only)
-- ============================================
DO $$
BEGIN
    -- Only insert if no users exist (fresh database)
    IF NOT EXISTS (SELECT 1 FROM users LIMIT 1) THEN
        INSERT INTO users (phone, password_hash, created_at) VALUES
        ('+393123456789', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdSGY2h3JDPLz4e', NOW())
        ON CONFLICT (phone) DO NOTHING;
        
        -- Log admin user creation
        RAISE NOTICE 'Admin user created: +393123456789 / password: admin123';
    END IF;
END $$;

-- ============================================
-- 📊 Sample Data for Development
-- ============================================
DO $$
BEGIN
    -- Insert some sample usage stats if in development
    IF NOT EXISTS (SELECT 1 FROM usage_stats LIMIT 1) THEN
        INSERT INTO usage_stats (user_id, action, details) VALUES
        (1, 'login', '{"ip": "127.0.0.1", "user_agent": "Mozilla/5.0"}'),
        (1, 'telegram_session_created', '{"success": true}'),
        (1, 'command_executed', '{"command": "@testchannel", "success": true}')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- ============================================
-- 🔍 Views for Analytics
-- ============================================

-- Active users view
CREATE OR REPLACE VIEW active_users AS
SELECT 
    u.id,
    u.phone,
    u.created_at,
    u.last_login,
    COUNT(us.action) as total_actions
FROM users u
LEFT JOIN usage_stats us ON u.id = us.user_id
WHERE u.is_active = true
GROUP BY u.id, u.phone, u.created_at, u.last_login
ORDER BY u.last_login DESC NULLS LAST;

-- Daily usage stats
CREATE OR REPLACE VIEW daily_usage AS
SELECT 
    DATE(created_at) as date,
    action,
    COUNT(*) as count
FROM usage_stats
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at), action
ORDER BY date DESC, count DESC;

-- ============================================
-- 🧹 Cleanup Procedures
-- ============================================

-- Procedure to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS TABLE(sessions_cleaned INTEGER, stats_cleaned INTEGER) AS $$
DECLARE
    session_count INTEGER;
    stats_count INTEGER;
BEGIN
    -- Clean expired sessions
    session_count := clean_expired_sessions();
    
    -- Clean old usage stats (keep last 90 days)
    DELETE FROM usage_stats 
    WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS stats_count = ROW_COUNT;
    
    RETURN QUERY SELECT session_count, stats_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 🔐 Security Settings
-- ============================================

-- Revoke public access
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC;

-- Grant necessary permissions to chatmanager user
GRANT CONNECT ON DATABASE chatmanager TO chatmanager;
GRANT USAGE ON SCHEMA public TO chatmanager;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chatmanager;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chatmanager;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO chatmanager;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO chatmanager;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO chatmanager;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO chatmanager;

-- ============================================
-- 📝 Database Info
-- ============================================

-- Create info table with current schema version
CREATE TABLE IF NOT EXISTS db_info (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO db_info (key, value) VALUES 
    ('schema_version', '1.0.0'),
    ('created_at', NOW()::TEXT),
    ('description', 'Telegram Chat Manager Database Schema')
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = NOW();

-- Final success message
DO $$
BEGIN
    RAISE NOTICE '🚀 Database schema initialized successfully!';
    RAISE NOTICE '📊 Tables created: users, user_sessions, usage_stats';
    RAISE NOTICE '🔍 Views created: active_users, daily_usage';
    RAISE NOTICE '🧹 Cleanup functions available: cleanup_old_data()';
    RAISE NOTICE '👤 Default admin user: +393123456789 / admin123';
END $$; 