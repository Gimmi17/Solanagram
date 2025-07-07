#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Solanagram Crypto Extractor Container Entrypoint
------------------------------------------------
• Ascolta un gruppo Telegram (SOURCE_CHAT_ID)
• Applica regole JSON (RULES_JSON)
• Quando trova valori, inserisce riga in extracted_values
• Logga su stdout per debug
"""
import os
import json
import asyncio
import logging
from datetime import datetime
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from telethon import TelegramClient, events
from telethon.sessions import StringSession

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("extractor")

# ---- Environment variables ----
SOURCE_CHAT_ID = int(os.getenv("SOURCE_CHAT_ID", "0"))
RULES_JSON = os.getenv("RULES_JSON", "[]")
DATABASE_URL = os.getenv("DATABASE_URL")
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_STR = os.getenv("TELEGRAM_SESSION")

if not (SOURCE_CHAT_ID and DATABASE_URL and API_ID and API_HASH and SESSION_STR):
    logger.error("Missing mandatory environment variables")
    exit(1)

try:
    RULES = json.loads(RULES_JSON)
except Exception as e:
    logger.error(f"Invalid RULES_JSON: {e}")
    RULES = []

logger.info(f"Loaded {len(RULES)} extraction rules for chat {SOURCE_CHAT_ID}")

# ---- Database ----
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

# Get user_id from session (we'll need it for inserting data)
USER_ID = None
try:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id FROM users 
            WHERE session_string = %s 
            LIMIT 1
        """, (SESSION_STR,))
        result = cur.fetchone()
        if result:
            USER_ID = result[0]
            logger.info(f"Found user_id: {USER_ID}")
except Exception as e:
    logger.warning(f"Could not determine user_id: {e}")

async def main():
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    await client.start()
    logger.info("Extractor connected to Telegram API")

    @client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
    async def handler(event):
        text = event.raw_text or ""
        message_id = event.id
        sender_id = event.sender_id if event.sender_id else 0
        
        found_any = False
        extracted_data = {}
        
        # Apply all rules to extract data
        for rule in RULES:
            name = rule.get('rule_name')
            search_text = rule.get('search_text')
            length = int(rule.get('value_length', 0))
            
            if not (name and search_text and length):
                continue
                
            # Find all occurrences of the search text
            for match in re.finditer(re.escape(search_text), text):
                start = match.end()
                value = text[start:start+length].strip()
                
                if value:
                    extracted_data[name] = value
                    found_any = True
                    logger.info(f"Found {name}: {value}")
        
        if found_any:
            logger.info(f"Extracted {len(extracted_data)} values from message {message_id}")
            
            try:
                with conn.cursor() as cur:
                    # Insert into crypto_signals table
                    cur.execute("""
                        INSERT INTO crypto_signals (
                            user_id, 
                            source_chat_id, 
                            signal_type,
                            token_address,
                            parsed_data,
                            raw_message,
                            created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s) 
                        RETURNING id
                    """, (
                        USER_ID or 0,
                        SOURCE_CHAT_ID,
                        'EXTRACTED',  # Signal type for extracted data
                        extracted_data.get('token_address', extracted_data.get('contract_address', 'UNKNOWN')),
                        json.dumps(extracted_data),
                        text,
                        datetime.now()
                    ))
                    
                    signal_id = cur.fetchone()[0]
                    
                    # For each extracted value, also save in extracted_values table
                    for rule in RULES:
                        rule_name = rule.get('rule_name')
                        if rule_name in extracted_data:
                            try:
                                # Get rule_id
                                cur.execute("""
                                    SELECT id FROM extraction_rules 
                                    WHERE user_id = %s 
                                    AND source_chat_id = %s 
                                    AND rule_name = %s
                                    LIMIT 1
                                """, (USER_ID or 0, SOURCE_CHAT_ID, rule_name))
                                
                                rule_result = cur.fetchone()
                                if rule_result:
                                    rule_id = rule_result[0]
                                    
                                    cur.execute("""
                                        INSERT INTO extracted_values (
                                            message_id, 
                                            rule_id, 
                                            occurrence_index, 
                                            extracted_value
                                        ) VALUES (%s, %s, %s, %s)
                                    """, (signal_id, rule_id, 0, extracted_data[rule_name]))
                                    
                                    logger.info(f"Saved extracted value for rule '{rule_name}'")
                            except Exception as e:
                                logger.warning(f"Failed to insert extracted value for rule '{rule_name}': {e}")
                    
                    logger.info(f"Saved signal with ID: {signal_id}")
                    
            except Exception as e:
                logger.error(f"Failed to save extracted data: {e}")
        else:
            logger.debug(f"No rules matched for message {message_id}")

    logger.info(f"Starting to listen for messages in chat {SOURCE_CHAT_ID}")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main()) 