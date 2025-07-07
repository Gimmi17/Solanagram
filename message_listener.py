#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solanagram Message Listener Container
------------------------------------
• Ascolta messaggi da un gruppo Telegram specifico
• Salva tutti i messaggi nel database
• Applica elaborazioni configurate (extractor/redirect)
• Supporta più elaborazioni sullo stesso messaggio
• Configurazione dinamica via file JSON
"""

import os
import json
import asyncio
import logging
import signal
from datetime import datetime
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat
from telethon.errors import PeerIdInvalidError, ChatWriteForbiddenError

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("message_listener")

class MessageListener:
    def __init__(self):
        # Environment variables
        self.phone = os.getenv("TELEGRAM_PHONE")
        self.api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.session_str = os.getenv("TELEGRAM_SESSION")
        self.database_url = os.getenv("DATABASE_URL")
        self.config_file = os.getenv("CONFIG_FILE", "/app/configs/config.json")
        self.elaborations_file = "/app/configs/elaborations.json"
        
        # Config data
        self.config = {}
        self.elaborations = []
        self.listener_id = None
        self.user_id = None
        self.source_chat_id = None
        
        # Telethon client
        self.client = None
        self.db_conn = None
        
        # Reload flag
        self.should_reload = False
        
        # Validate environment
        if not all([self.api_id, self.api_hash, self.database_url]):
            logger.error("Missing mandatory environment variables")
            exit(1)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown and config reload"""
        def signal_handler(signum, frame):
            if signum == signal.SIGHUP:
                logger.info("Received SIGHUP, marking for configuration reload")
                self.should_reload = True
            elif signum in [signal.SIGTERM, signal.SIGINT]:
                logger.info(f"Received signal {signum}, shutting down...")
                asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGHUP, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler) 
        signal.signal(signal.SIGINT, signal_handler)
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                
                self.listener_id = self.config.get('listener_id')
                self.user_id = self.config.get('user_id')
                self.source_chat_id = int(self.config.get('source_chat_id', 0))
                
                logger.info(f"Loaded config: listener_id={self.listener_id}, source_chat_id={self.source_chat_id}")
            else:
                logger.error(f"Config file not found: {self.config_file}")
                return False
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return False
        
        return True
    
    def load_elaborations(self):
        """Load elaborations from JSON file"""
        try:
            if os.path.exists(self.elaborations_file):
                with open(self.elaborations_file, 'r') as f:
                    self.elaborations = json.load(f)
                logger.info(f"Loaded {len(self.elaborations)} elaborations")
            else:
                logger.info("No elaborations file found, starting with empty elaborations")
                self.elaborations = []
        except Exception as e:
            logger.error(f"Failed to load elaborations: {e}")
            self.elaborations = []
    
    async def setup_database(self):
        """Setup database connection"""
        try:
            self.db_conn = psycopg2.connect(self.database_url)
            self.db_conn.autocommit = True
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def setup_telegram(self):
        """Setup Telegram client"""
        try:
            # Use session file if available, otherwise use session string
            session_file = os.getenv("SESSION_FILE")
            if session_file and os.path.exists(session_file):
                logger.info(f"Using session file: {session_file}")
                self.client = TelegramClient(session_file, self.api_id, self.api_hash)
            elif self.session_str:
                logger.info("Using session string")
                self.client = TelegramClient(StringSession(self.session_str), self.api_id, self.api_hash)
            else:
                logger.error("No session available")
                return False
            
            await self.client.start()
            
            # Verify we can access the source chat
            if self.source_chat_id:
                try:
                    entity = await self.client.get_entity(self.source_chat_id)
                    logger.info(f"Connected to chat: {getattr(entity, 'title', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"Could not get chat info: {e}")
            
            logger.info("Connected to Telegram")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Telegram client: {e}")
            return False
    
    async def save_message(self, event):
        """Save message to database"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO saved_messages (
                        listener_id, user_id, message_id, sender_id, 
                        message_text, message_data, received_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    self.listener_id,
                    self.user_id,
                    event.id,
                    event.sender_id or 0,
                    event.raw_text or "",
                    json.dumps({
                        'chat_id': getattr(event.chat, 'id', 0),
                        'date': event.date.isoformat() if event.date else None,
                        'out': event.out,
                        'mentioned': event.mentioned,
                        'media_unread': event.media_unread,
                        'silent': event.silent,
                        'post': event.post,
                        'from_scheduled': event.from_scheduled,
                        'legacy': event.legacy,
                        'edit_hide': event.edit_hide,
                        'pinned': event.pinned,
                        'noforwards': event.noforwards,
                        'invert_media': event.invert_media
                    }),
                    datetime.now()
                ))
                
                saved_message_id = cur.fetchone()['id']
                logger.debug(f"Saved message {event.id} as {saved_message_id}")
                return saved_message_id
                
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            return None
    
    async def apply_extractor_elaboration(self, elaboration, message_text, saved_message_id):
        """Apply extractor elaboration to message"""
        try:
            config = elaboration.get('config', {})
            rules = config.get('extraction_rules', [])
            
            extracted_values = []
            
            for rule in rules:
                search_text = rule.get('search_text', '')
                extract_length = int(rule.get('extract_length', 0))
                rule_name = rule.get('rule_name', '')
                
                if not all([search_text, extract_length, rule_name]):
                    continue
                
                # Find all occurrences
                for match in re.finditer(re.escape(search_text), message_text):
                    start = match.end()
                    value = message_text[start:start+extract_length].strip()
                    
                    if value:
                        extracted_values.append({
                            'rule_name': rule_name,
                            'search_text': search_text,
                            'extracted_value': value,
                            'position': start
                        })
                        
                        logger.info(f"Extracted '{rule_name}': {value}")
            
            # Save extracted values to database
            if extracted_values:
                with self.db_conn.cursor() as cur:
                    for extracted in extracted_values:
                        cur.execute("""
                            INSERT INTO elaboration_extracted_values (
                                elaboration_id, saved_message_id, rule_name,
                                search_text, extracted_value, extraction_position,
                                extracted_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (
                            elaboration['id'],
                            saved_message_id,
                            extracted['rule_name'],
                            extracted['search_text'],
                            extracted['extracted_value'],
                            extracted['position'],
                            datetime.now()
                        ))
                
                logger.info(f"Saved {len(extracted_values)} extracted values for elaboration {elaboration['id']}")
                
        except Exception as e:
            logger.error(f"Failed to apply extractor elaboration: {e}")
    
    async def apply_redirect_elaboration(self, elaboration, event):
        """Apply redirect elaboration to message"""
        try:
            config = elaboration.get('config', {})
            target_chat_id = config.get('target_chat_id')
            
            if not target_chat_id:
                logger.warning(f"No target_chat_id in redirect elaboration {elaboration['id']}")
                return
            
            # Forward the message to target chat
            try:
                target_entity = await self.client.get_entity(int(target_chat_id))
                await self.client.forward_messages(target_entity, event.message)
                logger.info(f"Forwarded message to {target_chat_id}")
                
                # Update elaboration stats
                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        UPDATE message_elaborations 
                        SET last_processed_at = %s, processed_count = processed_count + 1
                        WHERE id = %s
                    """, (datetime.now(), elaboration['id']))
                    
            except (PeerIdInvalidError, ChatWriteForbiddenError) as e:
                logger.error(f"Cannot forward to {target_chat_id}: {e}")
                
                # Update error stats
                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        UPDATE message_elaborations 
                        SET last_error_at = %s, error_count = error_count + 1,
                            last_error_message = %s
                        WHERE id = %s
                    """, (datetime.now(), str(e), elaboration['id']))
                
        except Exception as e:
            logger.error(f"Failed to apply redirect elaboration: {e}")
    
    async def process_message(self, event):
        """Process a new message with all elaborations"""
        message_text = event.raw_text or ""
        message_id = event.id
        
        logger.info(f"Processing message {message_id}: {message_text[:100]}...")
        
        # Save message to database
        saved_message_id = await self.save_message(event)
        if not saved_message_id:
            return
        
        # Apply all active elaborations
        for elaboration in self.elaborations:
            if not elaboration.get('is_active', True):
                continue
                
            elaboration_type = elaboration.get('type')
            elaboration_id = elaboration.get('id')
            
            try:
                if elaboration_type == 'extractor':
                    await self.apply_extractor_elaboration(elaboration, message_text, saved_message_id)
                elif elaboration_type == 'redirect':
                    await self.apply_redirect_elaboration(elaboration, event)
                else:
                    logger.warning(f"Unknown elaboration type: {elaboration_type}")
                    
            except Exception as e:
                logger.error(f"Failed to apply elaboration {elaboration_id}: {e}")
                
                # Update error stats
                with self.db_conn.cursor() as cur:
                    cur.execute("""
                        UPDATE message_elaborations 
                        SET last_error_at = %s, error_count = error_count + 1,
                            last_error_message = %s
                        WHERE id = %s
                    """, (datetime.now(), str(e), elaboration_id))
    
    async def reload_configuration(self):
        """Reload configuration and elaborations"""
        logger.info("Reloading configuration...")
        self.load_config()
        self.load_elaborations()
        self.should_reload = False
        logger.info("Configuration reloaded")
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down...")
        if self.client:
            await self.client.disconnect()
        if self.db_conn:
            self.db_conn.close()
        logger.info("Shutdown complete")
    
    async def run(self):
        """Main run loop"""
        logger.info("Starting Message Listener...")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Load initial configuration
        if not self.load_config():
            return
        self.load_elaborations()
        
        # Setup connections
        if not await self.setup_database():
            return
        if not await self.setup_telegram():
            return
        
        # Setup message handler
        @self.client.on(events.NewMessage(chats=self.source_chat_id))
        async def message_handler(event):
            # Check if we need to reload config
            if self.should_reload:
                await self.reload_configuration()
            
            await self.process_message(event)
        
        logger.info(f"Listening for messages in chat {self.source_chat_id}")
        
        # Main loop with periodic config check
        try:
            while True:
                if self.should_reload:
                    await self.reload_configuration()
                
                # Sleep for a bit to avoid busy waiting
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            await self.shutdown()

async def main():
    listener = MessageListener()
    await listener.run()

if __name__ == "__main__":
    asyncio.run(main()) 