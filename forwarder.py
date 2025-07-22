#!/usr/bin/env python3
import asyncio
import os
import json
import logging
import sys
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramForwarder:
    def __init__(self):
        self.config_file = os.environ.get('CONFIG_FILE', '/app/configs/config.json')
        self.phone = os.environ.get('TELEGRAM_PHONE')
        self.api_id = int(os.environ.get('TELEGRAM_API_ID', 0))
        self.api_hash = os.environ.get('TELEGRAM_API_HASH')
        self.session_string = os.environ.get('TELEGRAM_SESSION')
        self.session_file = os.environ.get('SESSION_FILE')
        self.message_count = 0
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Validate environment variables
        logger.info(f"Phone: {self.phone}")
        logger.info(f"API ID: {self.api_id}")
        logger.info(f"API Hash present: {'Yes' if self.api_hash else 'No'}")
        
        if self.session_file:
            logger.info(f"Using session file: {self.session_file}")
            logger.info(f"Session file exists: {os.path.exists(self.session_file)}")
        else:
            logger.info(f"Session string length: {len(self.session_string) if self.session_string else 0}")
        
        if not self.phone or not self.api_id or not self.api_hash:
            logger.error("Missing required environment variables!")
            logger.error(f"TELEGRAM_PHONE: {self.phone}")
            logger.error(f"TELEGRAM_API_ID: {self.api_id}")
            logger.error(f"TELEGRAM_API_HASH: {'SET' if self.api_hash else 'NOT SET'}")
            sys.exit(1)
            
        if not self.session_string and not self.session_file:
            logger.error("Neither TELEGRAM_SESSION nor SESSION_FILE is set!")
            sys.exit(1)
        
    async def run(self):
        """Main forwarding loop with auto-reconnection"""
        # Load config
        with open(self.config_file, 'r') as f:
            config = json.load(f)
        
        logger.info(f"✓ Configurazione caricata da {self.config_file}")
        
        source_chat_id = int(config['source_chat_id'])
        target_type = config['target_type']
        target_id = config['target_id']
        
        # Create client
        if self.session_file and os.path.exists(self.session_file):
            # Use file session
            client = TelegramClient(
                self.session_file,
                self.api_id,
                self.api_hash
            )
        else:
            # Use string session
            client = TelegramClient(
                StringSession(self.session_string),
                self.api_id,
                self.api_hash
            )
        
        logger.info("Connessione in corso...")
        
        # Connetti prima per verificare lo stato
        await client.connect()
        
        # Verifica se la sessione è autorizzata
        if not await client.is_user_authorized():
            logger.error("ERRORE: La sessione non è autorizzata!")
            logger.error("Il file di sessione esiste ma non contiene una sessione valida.")
            logger.error("Probabilmente il codice di verifica non è stato inserito correttamente.")
            logger.error("Rimuovi questo forwarder e ricrealo inserendo il codice corretto.")
            sys.exit(1)
        
        logger.info(f"✓ Client autenticato!")
        
        # Get target entity
        if target_type == 'user' and target_id.startswith('@'):
            target_entity = await client.get_entity(target_id)
        else:
            target_entity = await client.get_entity(int(target_id))
        
        logger.info(f"✓ Chat di destinazione: {getattr(target_entity, 'title', getattr(target_entity, 'username', target_id))}")
        
        # Message handler with error handling
        @client.on(events.NewMessage(chats=[source_chat_id]))
        async def handler(event):
            try:
                message = event.message
                if not message.text:
                    return
                
                logger.info(f"📨 Nuovo messaggio: {message.text[:50]}...")
                
                # Forward with retry logic
                for attempt in range(3):
                    try:
                        await client.send_message(target_entity, message.text)
                        break
                    except FloodWaitError as e:
                        logger.warning(f"Flood wait, sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except (ConnectionError, OSError) as e:
                        logger.warning(f"Connection error on attempt {attempt + 1}: {e}")
                        if attempt < 2:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            logger.error(f"Failed to send message after 3 attempts: {e}")
                            return
                    except Exception as e:
                        logger.error(f"Error forwarding message: {e}")
                        return
                
                self.message_count += 1
                logger.info("✅ Messaggio inoltrato")
                
                # Update count file for external monitoring
                try:
                    with open('/app/configs/count.txt', 'w') as f:
                        f.write(str(self.message_count))
                except:
                    pass  # Don't fail if we can't update count
                    
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
        
        logger.info(f"🚀 Forwarding attivo: {config['source_chat_title']} -> {getattr(target_entity, 'title', getattr(target_entity, 'username', target_id))}")
        logger.info("Container in esecuzione... Premi Ctrl+C per fermare")
        
        # Main loop with auto-reconnection
        while True:
            try:
                await client.run_until_disconnected()
                break  # Normal disconnection
            except (ConnectionError, OSError) as e:
                self.reconnect_attempts += 1
                if self.reconnect_attempts > self.max_reconnect_attempts:
                    logger.error(f"Max reconnection attempts reached ({self.max_reconnect_attempts})")
                    break
                
                wait_time = min(60, 5 * self.reconnect_attempts)
                logger.warning(f"Server closed the connection: {e}")
                logger.info(f"Attempting reconnection #{self.reconnect_attempts} in {wait_time} seconds...")
                
                await asyncio.sleep(wait_time)
                
                try:
                    if not client.is_connected():
                        await client.connect()
                    logger.info("✓ Riconnesso al server Telegram")
                    self.reconnect_attempts = 0  # Reset counter on successful reconnection
                except Exception as reconnect_error:
                    logger.error(f"Reconnection failed: {reconnect_error}")
            except KeyboardInterrupt:
                logger.info("\n⏹️ Forwarding fermato dall'utente")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(10)
        
        # Cleanup
        if client:
            try:
                await client.disconnect()
            except:
                pass

if __name__ == "__main__":
    forwarder = TelegramForwarder()
    asyncio.run(forwarder.run())
