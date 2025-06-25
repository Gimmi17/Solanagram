-- Update users table for Telegram authentication
-- Add necessary columns for the auth system

-- Add missing columns to users table
ALTER TABLE users 
  ADD COLUMN IF NOT EXISTS user_id INTEGER,
  ADD COLUMN IF NOT EXISTS phone_number VARCHAR(15),
  ADD COLUMN IF NOT EXISTS api_id INTEGER,
  ADD COLUMN IF NOT EXISTS api_hash VARCHAR(32),
  ADD COLUMN IF NOT EXISTS landing TEXT,
  ADD COLUMN IF NOT EXISTS telegram_session TEXT;

-- Set user_id as alias for id
UPDATE users SET user_id = id WHERE user_id IS NULL;
UPDATE users SET phone_number = phone WHERE phone_number IS NULL;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number);
CREATE INDEX IF NOT EXISTS idx_users_api_id ON users(api_id);

-- Allow NULL for password_hash since we use Telegram auth
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

COMMIT; 