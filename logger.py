#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Message Logger - Container per il logging dei messaggi Telegram
"""

import asyncio
import logging
import os
import sys
import json
import psycopg2
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramLogger:
    """Logger per i messaggi Telegram"""
    
    def __init__(self):
        self.client = None
        self.db_conn = None
        self.logging_session_id = None
        
        # Environment variables
        self.user_id = int(os.getenv('USER_ID', 0))
        self.phone = os.getenv('PHONE', '')
        self.api_id = int(os.getenv('API_ID', 0))
        self.api_hash = os.getenv('API_HASH', '')
        self.session_string = os.getenv('SESSION_STRING', '')
        self.chat_id = int(os.getenv('CHAT_ID', 0))
        self.chat_title = os.getenv('CHAT_TITLE', '')
        self.chat_username = os.getenv('CHAT_USERNAME', '')
        self.chat_type = os.getenv('CHAT_TYPE', 'unknown')
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'chatmanager'),
            'user': os.getenv('DB_USER', 'solanagram_user'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        # Backend URL for health checks
        self.backend_url = os.getenv('BACKEND_URL', 'http://localhost:8000')
        
        logger.info(f"Initializing logger for chat: {self.chat_title} (ID: {self.chat_id})")
    
    async def initialize(self):
        """Initialize the logger"""
        try:
            # Connect to database
            await self.connect_database()
            
            # Create or get logging session
            await self.setup_logging_session()
            
            # Initialize Telegram client
            await self.setup_telegram_client()
            
            logger.info("Logger initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize logger: {e}")
            return False
    
    async def connect_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.db_conn = psycopg2.connect(**self.db_config)
            self.db_conn.autocommit = False
            logger.info("Connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def setup_logging_session(self):
        """Setup logging session in database"""
        try:
            with self.db_conn.cursor() as cursor:
                # Check if session already exists
                cursor.execute("""
                    SELECT id FROM logging_sessions
                    WHERE user_id = %s AND chat_id = %s AND is_active = true
                """, (self.user_id, self.chat_id))
                
                existing_session = cursor.fetchone()
                
                if existing_session:
                    self.logging_session_id = existing_session[0]
                    logger.info(f"Using existing logging session: {self.logging_session_id}")
                else:
                    # Create new session
                    cursor.execute("""
                        INSERT INTO logging_sessions 
                        (user_id, chat_id, chat_title, chat_username, chat_type, container_status)
                        VALUES (%s, %s, %s, %s, %s, 'running')
                        RETURNING id
                    """, (self.user_id, self.chat_id, self.chat_title, self.chat_username, self.chat_type))
                    
                    self.logging_session_id = cursor.fetchone()[0]
                    self.db_conn.commit()
                    logger.info(f"Created new logging session: {self.logging_session_id}")
                    
        except Exception as e:
            logger.error(f"Failed to setup logging session: {e}")
            raise
    
    async def setup_telegram_client(self):
        """Setup Telegram client"""
        try:
            # Create client with string session
            self.client = TelegramClient(
                StringSession(self.session_string),
                self.api_id,
                self.api_hash
            )
            
            # Connect to Telegram
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error("Telegram client not authorized")
                raise Exception("Telegram client not authorized")
            
            logger.info("Telegram client connected and authorized")
            
            # Setup message handler
            @self.client.on(events.NewMessage(chats=self.chat_id))
            async def handle_new_message(event):
                await self.log_message(event.message)
            
            logger.info(f"Message handler setup for chat: {self.chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup Telegram client: {e}")
            raise
    
    async def log_message(self, message):
        """Log a message to the database"""
        try:
            # Extract message information
            message_id = message.id
            sender_id = message.sender_id.user_id if message.sender_id else None
            
            # Get sender information
            sender_name = "Unknown"
            sender_username = None
            
            if message.sender_id:
                try:
                    sender = await self.client.get_entity(message.sender_id)
                    sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', '') or 'Unknown'
                    sender_username = getattr(sender, 'username', None)
                except Exception as e:
                    logger.warning(f"Failed to get sender info: {e}")
            
            # Extract message content
            message_text = message.text if message.text else None
            message_type = 'text'
            media_file_id = None
            
            # Check for media
            if message.photo:
                message_type = 'photo'
                media_file_id = message.photo.id
            elif message.video:
                message_type = 'video'
                media_file_id = message.video.id
            elif message.document:
                message_type = 'document'
                media_file_id = message.document.id
            elif message.sticker:
                message_type = 'sticker'
                media_file_id = message.sticker.id
            elif message.voice:
                message_type = 'voice'
                media_file_id = message.voice.id
            elif message.audio:
                message_type = 'audio'
                media_file_id = message.audio.id
            
            # Insert into database
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO message_logs 
                    (user_id, chat_id, chat_title, chat_username, chat_type, message_id, 
                     sender_id, sender_name, sender_username, message_text, message_type, 
                     media_file_id, message_date, logging_session_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chat_id, message_id, logging_session_id) DO NOTHING
                """, (
                    self.user_id, self.chat_id, self.chat_title, self.chat_username, self.chat_type,
                    message_id, sender_id, sender_name, sender_username, message_text, message_type,
                    media_file_id, message.date, self.logging_session_id
                ))
                
                # Update session statistics
                cursor.execute("""
                    UPDATE logging_sessions
                    SET messages_logged = messages_logged + 1,
                        last_message_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                """, (self.logging_session_id,))
                
                self.db_conn.commit()
                
                logger.info(f"Logged message {message_id} from {sender_name} ({message_type})")
                
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
            # Update error count
            try:
                with self.db_conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE logging_sessions
                        SET errors_count = errors_count + 1,
                            last_error = %s,
                            last_error_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                    """, (str(e), self.logging_session_id))
                    self.db_conn.commit()
            except Exception as update_error:
                logger.error(f"Failed to update error count: {update_error}")
    
    async def run(self):
        """Run the logger"""
        try:
            logger.info("Starting Telegram message logger...")
            
            # Start the client
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            logger.info("Logger stopped by user")
        except Exception as e:
            logger.error(f"Logger error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            # Update session status
            if self.logging_session_id and self.db_conn:
                with self.db_conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE logging_sessions
                        SET is_active = false,
                            container_status = 'stopped',
                            updated_at = NOW()
                        WHERE id = %s
                    """, (self.logging_session_id,))
                    self.db_conn.commit()
            
            # Close database connection
            if self.db_conn:
                self.db_conn.close()
            
            # Disconnect Telegram client
            if self.client:
                await self.client.disconnect()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

async def main():
    """Main function"""
    logger = TelegramLogger()
    
    if await logger.initialize():
        await logger.run()
    else:
        logger.error("Failed to initialize logger")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())