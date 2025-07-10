#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🔐 Real Telegram Authentication Backend
Fixed version with proper asyncio handling and code obfuscation
"""

import os
import logging
import hashlib
import secrets
import random
import asyncio
import re
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import redis

from telethon import TelegramClient, errors
from telethon.sessions import StringSession

# Import forwarder manager
from forwarder_manager import ForwarderManager
from message_listener_manager import MessageListenerManager

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# Error Messages in Italian for better UX
# ============================================

ERROR_MESSAGES = {
    'REQUIRED_FIELDS': 'Tutti i campi sono obbligatori',
    'INVALID_API_ID': 'Formato API ID non valido. Deve essere un numero',
    'INVALID_PHONE': 'Formato numero di telefono non valido. Usa il formato +39xxxxxxxxx',
    'PHONE_EXISTS': 'Un utente con questo numero di telefono esiste già',
    'REGISTRATION_FAILED': 'Registrazione fallita. Riprova più tardi',
    'DB_CONNECTION_FAILED': 'Connessione al database fallita',
    'REDIS_CONNECTION_FAILED': 'Connessione al sistema di cache fallita',
    'TELEGRAM_CLIENT_FAILED': 'Impossibile inizializzare il client Telegram',
    'PHONE_INVALID': 'Numero di telefono non valido o non registrato su Telegram',
    'API_CREDENTIALS_INVALID': 'Credenziali API Telegram non valide. Controlla API ID e API Hash su https://my.telegram.org',
    'VERIFICATION_CODE_INVALID': 'Codice di verifica non valido',
    'VERIFICATION_EXPIRED': 'Richiesta di verifica scaduta. Effettua nuovamente il login',
    'PASSWORD_2FA_REQUIRED': 'Password 2FA richiesta ma non fornita',
    'PASSWORD_2FA_INVALID': 'Password 2FA non valida',
    'AUTH_RESTART_REQUIRED': 'Errore di autenticazione. Riprova il login',
    'FLOOD_WAIT': 'Troppe richieste. Attendi qualche minuto prima di riprovare',
    'UNAUTHORIZED': 'Autorizzazione persa. Effettua nuovamente il login',
    'PHONE_PASSWORD_REQUIRED': 'Numero di telefono e password sono obbligatori',
    'INVALID_CREDENTIALS': 'Numero di telefono o password non validi',
    'API_CREDENTIALS_NOT_SET': 'Credenziali API non impostate per questo utente',
    'PHONE_CODE_REQUIRED': 'Numero di telefono e codice sono obbligatori',
    'ASYNCIO_LOOP_ERROR': 'Problema di connessione rilevato. Tutti i dati sono stati puliti, riprova il login',
    'UNEXPECTED_ERROR': 'Errore inaspettato: {error}'
}

def get_error_message(key: str, **kwargs) -> str:
    """Get error message with optional formatting"""
    message = ERROR_MESSAGES.get(key, f'Errore sconosciuto: {key}')
    return message.format(**kwargs) if kwargs else message

# Environment-based configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://solanagram_user:solanagram_password@solanagram-db:5432/solanagram_db')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY') # Must be set in .env
    
    # ============================================
    # 📱 MULTI-CHANNEL CONFIGURATION
    # ============================================
    PRIMARY_CHANNEL_ID = os.environ.get('PRIMARY_CHANNEL_ID')
    SECONDARY_CHANNEL_ID = os.environ.get('SECONDARY_CHANNEL_ID')
    BACKUP_CHANNEL_ID = os.environ.get('BACKUP_CHANNEL_ID')
    
    # Canali configurati come lista per iterazione
    CONFIGURED_CHANNELS = [
        {"id": PRIMARY_CHANNEL_ID, "name": "primary", "priority": 1},
        {"id": SECONDARY_CHANNEL_ID, "name": "secondary", "priority": 2},
        {"id": BACKUP_CHANNEL_ID, "name": "backup", "priority": 3}
    ]

    if not ENCRYPTION_KEY:
        raise ValueError("ENCRYPTION_KEY is not set in the environment variables.")

    try:
        fernet = Fernet(ENCRYPTION_KEY.encode())
    except Exception as e:
        raise ValueError(f"Invalid ENCRYPTION_KEY format. Must be a valid Fernet key: {e}")


# Telethon is available and will be used
TELETHON_AVAILABLE = True

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, origins=["http://localhost:8082"], supports_credentials=True, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
jwt = JWTManager(app)

# Directory for Telethon session files
SESSION_DIR = 'telethon_sessions'
os.makedirs(SESSION_DIR, exist_ok=True)

# In-memory cache for active Telethon clients to maintain sessions
active_clients: Dict[str, TelegramClient] = {}
client_locks: Dict[str, asyncio.Lock] = {}


# ============================================
#  Encryption Utilities
# ============================================

def encrypt_api_hash(api_hash: str) -> str:
    """Encrypts the API hash for secure storage."""
    try:
        return Config.fernet.encrypt(api_hash.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt API hash: {e}")
        raise ValueError("Encryption failed")

def decrypt_api_hash(encrypted_hash: str) -> str:
    """Decrypts the API hash for use."""
    try:
        return Config.fernet.decrypt(encrypted_hash.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt API hash: {e}")
        raise ValueError("Decryption failed")


# ============================================
#  Database & Redis Connections
# ============================================

def get_db_connection():
    """Establishes a new database connection if one doesn't exist for the current context."""
    if 'db' not in g:
        try:
            g.db = psycopg2.connect(
                Config.DATABASE_URL,
                cursor_factory=RealDictCursor,
                connect_timeout=10,
                application_name='telegram_chat_manager'
            )
            g.db.autocommit = False
            logger.info("Database connection successful.")
        except (psycopg2.OperationalError, psycopg2.DatabaseError) as e:
            logger.error(f"Could not connect to database: {e}")
            g.db = None
    return g.db

def get_redis_connection():
    """Establishes a new Redis connection if one doesn't exist for the current context."""
    if 'redis_client' not in g:
        try:
            g.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5
            )
            g.redis_client.ping()
            logger.info("Redis connection successful.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to Redis: {e}")
            g.redis_client = None
    return g.redis_client

@app.teardown_appcontext
def teardown_db(exception=None):
    """Closes database and other connections at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            if not db.closed:
                db.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    # No need to explicitly close Redis connections managed by the library pool


# ============================================
#  Telethon Client Management
# ============================================

def hash_phone_number(phone: str) -> str:
    """Hashes the phone number for privacy when used in filenames."""
    return hashlib.sha256(phone.encode()).hexdigest()

async def cleanup_phone_completely(phone: str):
    """
    Completely cleans up all data for a phone number to solve asyncio loop issues.
    This includes client disconnection, session file removal, and cache cleanup.
    """
    try:
        # Disconnect and remove from active clients
        if phone in active_clients:
            try:
                client = active_clients[phone]
                if client.is_connected():
                    await client.disconnect()
                logger.info(f"Disconnected client for {phone}")
            except Exception as e:
                logger.warning(f"Error disconnecting client for {phone}: {e}")
            finally:
                del active_clients[phone]
        
        # Remove client lock if exists
        if phone in client_locks:
            del client_locks[phone]
        
        # Remove session file
        session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.info(f"Removed session file for {phone}")
        
        # Clear Redis verification data
        redis_conn = get_redis_connection()
        if redis_conn:
            verification_key = f"verification:{phone}"
            redis_conn.delete(verification_key)
            logger.info(f"Cleared Redis data for {phone}")
            
        logger.info(f"Complete cleanup performed for {phone}")
    except Exception as e:
        logger.error(f"Error during complete cleanup for {phone}: {e}")

async def get_telethon_client(phone: str, api_id: int, api_hash: str, use_string_session: bool = False) -> Optional[TelegramClient]:
    """
    Creates a new Telethon client for a given phone number.
    OPTIMIZED: Uses intelligent caching and reduced timeouts for better performance.
    """
    try:
        # Check cache first
        cached_client = get_cached_client(phone)
        if cached_client:
            logger.info(f"Using cached client for {phone}")
            return cached_client

        logger.info(f"Creating a new Telethon client for phone {phone} (string_session={use_string_session})")
        
        if use_string_session:
            # For StringSession, first check if we have a saved session
            session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
            session_string = ""
            
            # Try to load existing session string if we have a file session
            if os.path.exists(session_file):
                try:
                    # Create a temporary client to extract the session string
                    temp_client = TelegramClient(session_file, api_id, api_hash)
                    await asyncio.wait_for(temp_client.connect(), timeout=5.0)  # Reduced from 10.0 to 5.0
                    if temp_client.is_connected():
                        session_string = temp_client.session.save()
                        await temp_client.disconnect()
                        logger.info(f"Extracted session string from file for {phone}, length: {len(session_string)}")
                except Exception as e:
                    logger.warning(f"Could not extract session string from file for {phone}: {e}")
                    # Remove corrupted session file
                    try:
                        os.remove(session_file)
                        logger.info(f"Removed corrupted session file for {phone}")
                    except:
                        pass
            
            # Create client with StringSession
            from telethon.sessions import StringSession
            client = TelegramClient(StringSession(session_string), api_id, api_hash)
        else:
            # Normal file-based session
            session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
            
            # Check if session file is locked and remove if necessary
            if os.path.exists(session_file):
                try:
                    # Test if session can be opened without issues
                    test_client = TelegramClient(session_file + "_test", api_id, api_hash)
                    await asyncio.wait_for(test_client.connect(), timeout=5.0)  # Reduced from 10.0 to 5.0
                    await test_client.disconnect()
                    # Remove test session
                    test_session = session_file + "_test.session"
                    if os.path.exists(test_session):
                        os.remove(test_session)
                except Exception as e:
                    logger.warning(f"Session file {session_file} appears corrupted: {e}. Removing...")
                    # Remove corrupted session files
                    for f in [session_file, session_file + "-journal", session_file + "-wal", session_file + "-shm"]:
                        try:
                            if os.path.exists(f):
                                os.remove(f)
                                logger.info(f"Removed corrupted session file: {f}")
                        except Exception as remove_e:
                            logger.warning(f"Could not remove {f}: {remove_e}")
            
            client = TelegramClient(session_file, api_id, api_hash)
        
        # OPTIMIZED: Reduced timeout and simplified connection
        try:
            await asyncio.wait_for(client.connect(), timeout=8.0)  # Reduced from 15.0 to 8.0
        except asyncio.TimeoutError:
            logger.warning(f"First connection attempt timed out for {phone}, retrying...")
            # Second attempt with fresh client
            if not use_string_session:
                session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
                client = TelegramClient(session_file, api_id, api_hash)
            await asyncio.wait_for(client.connect(), timeout=5.0)  # Reduced from 10.0 to 5.0
        
        if not client.is_connected():
            raise Exception("Failed to establish connection to Telegram servers")
        
        # OPTIMIZED: Simplified connection verification with single attempt
        try:
            await asyncio.wait_for(client.get_me(), timeout=5.0)  # Reduced from 8.0 to 5.0
            logger.info(f"Client connection verified for {phone}")
        except Exception as verify_error:
            logger.warning(f"Connection verification failed for {phone}: {verify_error}")
            # Continue anyway as the client might still work for basic operations
        
        # Cache the new client
        cache_client(phone, client)
        logger.info(f"New client for {phone} created, connected, and cached.")
        return client
        
    except asyncio.TimeoutError:
        logger.error(f"Timeout connecting to Telegram for {phone}")
        return None
    except errors.ApiIdInvalidError:
        logger.error(f"Invalid API ID for {phone}")
        return None
    except Exception as e:
        logger.error(f"Fatal error connecting new Telethon client for {phone}: {e}")
        # Cleanup on failure
        if phone in active_clients:
            del active_clients[phone]
        return None


async def ensure_client_connected(client: TelegramClient, phone: str, max_attempts: int = 3) -> bool:
    """
    FIXED: Ensure the Telegram client is connected and working before operations.
    Returns True if client is ready, False if all attempts failed.
    """
    for attempt in range(max_attempts):
        try:
            if not client.is_connected():
                logger.info(f"Client not connected for {phone}, attempting to connect (attempt {attempt + 1})")
                await asyncio.wait_for(client.connect(), timeout=10.0)
            
            if client.is_connected():
                # Test the connection with a simple operation
                await asyncio.wait_for(client.get_me(), timeout=5.0)
                logger.info(f"Client connection confirmed for {phone}")
                return True
                
        except Exception as e:
            logger.warning(f"Connection attempt {attempt + 1} failed for {phone}: {e}")
            if attempt < max_attempts - 1:  # Not the last attempt
                try:
                    await client.disconnect()
                    await asyncio.sleep(1.0)  # Wait before retry
                except:
                    pass
    
    logger.error(f"All {max_attempts} connection attempts failed for {phone}")
    return False

# ========================================================================================
# CODE CACHING SYSTEM
# ========================================================================================

def get_cached_code(phone: str) -> dict:
    """Get cached verification code for a phone number"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return None
    
    cache_key = f"cached_code:{phone}"
    cached_data = redis_conn.get(cache_key)
    
    if cached_data:
        try:
            data = json.loads(cached_data)
            # Check if code is still valid (not expired)
            if data.get('expires_at', 0) > time.time():
                return data
            else:
                # Clean up expired code
                redis_conn.delete(cache_key)
        except (json.JSONDecodeError, KeyError):
            redis_conn.delete(cache_key)
    
    return None

def save_cached_code(phone: str, code: str, phone_code_hash: str, api_id: int, api_hash: str, password: str = None) -> None:
    """Save verification code to cache with expiration"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return
    
    # Cache code for 5 minutes (300 seconds)
    expires_at = time.time() + 300
    
    cache_data = {
        'code': code,
        'phone_code_hash': phone_code_hash,
        'api_id': api_id,
        'api_hash': api_hash,
        'password': password,
        'expires_at': expires_at,
        'created_at': time.time()
    }
    
    cache_key = f"cached_code:{phone}"
    redis_conn.setex(cache_key, 300, json.dumps(cache_data))
    logger.info(f"Cached verification code for {phone}")

def clear_cached_code(phone: str) -> None:
    """Clear cached verification code for a phone number"""
    redis_conn = get_redis_connection()
    if redis_conn:
        cache_key = f"cached_code:{phone}"
        redis_conn.delete(cache_key)
        logger.info(f"Cleared cached code for {phone}")

# ========================================================================================
# ASYNC TELETHON HELPERS
# ========================================================================================

async def send_telegram_code_async(phone: str, api_id: int, api_hash: str, password: str) -> dict:
    """
    Initializes a client, sends a verification code, and stores necessary data in Redis.
    OPTIMIZED: Reduced timeouts and improved connection handling for better performance.
    """
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"success": False, "status": "error", "error": get_error_message('REDIS_CONNECTION_FAILED')}

    # Check if we have a cached code first
    cached_code_data = get_cached_code(phone)
    if cached_code_data:
        logger.info(f"Found cached code for {phone}, reusing without requesting new one")
        
        # Store verification data in Redis for verification step
        verification_key = f"verification:{phone}"
        verification_data = {
            "api_id": cached_code_data["api_id"],
            "api_hash": cached_code_data["api_hash"],
            "phone_code_hash": cached_code_data["phone_code_hash"],
            "password": cached_code_data.get("password"),
            "cached_code": cached_code_data["code"]  # Include the cached code
        }
        redis_conn.set(verification_key, json.dumps(verification_data), ex=600)  # 10-minute expiry
        
        # Get counter status without incrementing (since we're reusing cached code)
        counter_status = get_sms_code_counter(phone)
        
        return {
            "success": True, 
            "status": "success", 
            "message": f"Codice di verifica disponibile per {phone} (riutilizzato da cache)",
            "rate_limit": counter_status,
            "cached": True
        }

    # OPTIMIZED: Reduced retries and improved error handling
    max_retries = 1  # Reduced from 2 to 1 for faster response
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1} for sending code to {phone}")
                # Clean up any existing clients before retry
                if phone in active_clients:
                    try:
                        await active_clients[phone].disconnect()
                    except:
                        pass
                    del active_clients[phone]
                
                # Shorter delay before retry
                await asyncio.sleep(0.5)  # Reduced from 1.0 to 0.5
            
            client = await get_telethon_client(phone, api_id, api_hash)
            if not client:
                last_error = get_error_message('TELEGRAM_CLIENT_FAILED')
                if attempt == max_retries - 1:
                    return {"success": False, "status": "error", "error": last_error}
                continue

            # OPTIMIZED: Simplified connection verification
            if not client.is_connected():
                try:
                    await asyncio.wait_for(client.connect(), timeout=8.0)  # Reduced from 15.0 to 8.0
                except asyncio.TimeoutError:
                    last_error = "Timeout nella connessione a Telegram"
                    if attempt == max_retries - 1:
                        return {"success": False, "status": "error", "error": last_error}
                    continue

            # OPTIMIZED: Faster send_code_request with shorter timeout
            try:
                # Send the code request with reduced timeout
                result = await asyncio.wait_for(client.send_code_request(phone, force_sms=True), timeout=8.0)  # Reduced from 15.0 to 8.0
                
            except asyncio.TimeoutError:
                last_error = "Timeout durante l'invio del codice di verifica"
                if attempt == max_retries - 1:
                    return {"success": False, "status": "error", "error": last_error}
                continue
            except Exception as e:
                error_str = str(e).lower()
                # Handle specific disconnection errors with detailed logging
                if any(phrase in error_str for phrase in [
                    "cannot send requests while disconnected",
                    "disconnected", 
                    "not connected",
                    "connection lost",
                    "connection closed"
                ]):
                    logger.warning(f"🔌 Disconnection detected during send_code_request for {phone}: {e}")
                    last_error = "Connessione a Telegram interrotta. Il sistema riproverà automaticamente..."
                    
                    # Clean up the disconnected client before retry
                    if phone in active_clients:
                        try:
                            await active_clients[phone].disconnect()
                        except:
                            pass
                        del active_clients[phone]
                    
                elif "flood" in error_str:
                    logger.warning(f"🚫 Flood wait detected for {phone}: {e}")
                    last_error = f"Limite Telegram raggiunto: {str(e)}"
                else:
                    logger.error(f"❌ Unexpected error during send_code_request for {phone}: {e}")
                    last_error = f"Errore inaspettato: {str(e)}"
                
                if attempt == max_retries - 1:
                    return {"success": False, "status": "error", "error": last_error}
                continue
            
            # Success! Increment counter and store verification data
            counter_status = increment_sms_code_counter(phone)
            
            verification_key = f"verification:{phone}"
            verification_data = {
                "api_id": api_id,
                "api_hash": api_hash,
                "phone_code_hash": result.phone_code_hash,
                "password": password,  # Store password for 2FA verification
            }
            redis_conn.set(verification_key, json.dumps(verification_data), ex=600)  # 10-minute expiry

            logger.info(f"Successfully sent code to {phone} and stored verification data in Redis (attempt {attempt + 1}).")
            
            # Prepare response with counter info
            response = {
                "success": True, 
                "status": "success", 
                "message": f"Codice di verifica inviato a {phone}",
                "rate_limit": counter_status
            }
            
            # Add warning if approaching limit
            if counter_status["count"] >= SMS_CODE_WARNING_THRESHOLD:
                response["warning"] = f"Attenzione: hai fatto {counter_status['count']} richieste su {counter_status['limit']}. Limite raggiunto tra {counter_status['remaining']} richieste."
            
            return response
            
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed for {phone}: {e}")
            if attempt == max_retries - 1:
                break
    
    # All attempts failed
    logger.error(f"All {max_retries} attempts failed for sending code to {phone}. Last error: {last_error}")
    return {"success": False, "status": "error", "error": last_error or "Errore nell'invio del codice di verifica"}

async def verify_telegram_code_async(phone: str, code: str) -> dict:
    """
    Asynchronously verifies the Telegram code using data from Redis.
    Enhanced with detailed error messages and code caching.
    """
    redis_conn = get_redis_connection()
    verification_key = f"verification:{phone}"
    
    if not redis_conn or not redis_conn.exists(verification_key):
        logger.error(f"No verification data found in Redis for phone {phone}.")
        return {"success": False, "status": "error", "error": get_error_message('VERIFICATION_EXPIRED')}

    verification_data = json.loads(redis_conn.get(verification_key))
    api_id = verification_data["api_id"]
    api_hash = verification_data["api_hash"]
    phone_code_hash = verification_data["phone_code_hash"]
    password = verification_data.get("password")
    cached_code = verification_data.get("cached_code")

    # FIXED: Create a fresh client for verification to avoid asyncio loop conflicts
    try:
        # Clean up any existing client for this phone to avoid conflicts
        if phone in active_clients:
            try:
                existing_client = active_clients[phone]
                if existing_client.is_connected():
                    await existing_client.disconnect()
                del active_clients[phone]
                logger.info(f"Cleaned up existing client for {phone}")
            except Exception as e:
                logger.warning(f"Error cleaning up existing client for {phone}: {e}")
        
        # Create a new client specifically for verification
        session_file = os.path.join(SESSION_DIR, f"user_{hash_phone_number(phone)}.session")
        client = TelegramClient(session_file, api_id, api_hash)
        
        # Connect the new client
        await client.connect()
        logger.info(f"Created fresh client for verification of {phone}")
        
    except Exception as e:
        logger.error(f"Failed to create client for verification of {phone}: {e}")
        return {"success": False, "status": "error", "error": get_error_message('TELEGRAM_CLIENT_FAILED')}
        
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        logger.info(f"Successfully signed in user {phone}.")
        
        # If this is a new code (not from cache), save it for future use
        if not cached_code:
            save_cached_code(phone, code, phone_code_hash, api_id, api_hash, password)
            logger.info(f"Saved new verification code for {phone} to cache")
        
    except errors.SessionPasswordNeededError:
        logger.info(f"2FA password needed for {phone}. Trying to supply stored password.")
        if not password:
            return {"success": False, "status": "error", "error": get_error_message('PASSWORD_2FA_REQUIRED')}
        try:
            await client.sign_in(password=password)
            logger.info(f"Successfully signed in user {phone} with 2FA password.")
            
            # If this is a new code (not from cache), save it for future use
            if not cached_code:
                save_cached_code(phone, code, phone_code_hash, api_id, api_hash, password)
                logger.info(f"Saved new verification code for {phone} to cache (with 2FA)")
                
        except errors.PasswordHashInvalidError:
            logger.error(f"Invalid 2FA password for user {phone}.")
            return {"success": False, "status": "error", "error": get_error_message('PASSWORD_2FA_INVALID')}
        except Exception as e:
            logger.error(f"An error occurred during 2FA sign in for {phone}: {e}")
            return {"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}

    except errors.PhoneCodeInvalidError:
        logger.error(f"Invalid verification code for phone {phone}.")
        return {"success": False, "status": "error", "error": get_error_message('VERIFICATION_CODE_INVALID')}

    except errors.FloodWaitError as e:
        logger.error(f"Flood wait error during verification for {phone}: {e.seconds} seconds")
        return {"success": False, "status": "error", "error": f"{get_error_message('FLOOD_WAIT')} (Attendi {e.seconds} secondi)"}
        
    except Exception as e:
        error_str = str(e).lower()
        # FIXED: Handle disconnection errors during code verification
        if any(phrase in error_str for phrase in [
            "cannot send requests while disconnected",
            "disconnected", 
            "not connected",
            "connection lost",
            "connection closed"
        ]):
            logger.warning(f"🔌 Connection lost during code verification for {phone}: {e}")
            return {"success": False, "status": "error", "error": "Connessione persa durante la verifica. Riprova l'operazione."}
        else:
            logger.error(f"An error occurred during sign in for {phone}: {e}")
            return {"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}

    # If sign in is successful, clean up Redis and find user in DB
    redis_conn.delete(verification_key)
    
    # Clean up the verification client
    try:
        if client.is_connected():
            await client.disconnect()
        logger.info(f"Cleaned up verification client for {phone}")
    except Exception as e:
        logger.warning(f"Error cleaning up verification client for {phone}: {e}")
    db = get_db_connection()
    if not db:
        return {"success": False, "status": "error", "error": get_error_message('DB_CONNECTION_FAILED')}
        
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, phone FROM users WHERE phone = %s", (phone,))
            user = cursor.fetchone()
        
        if not user:
            return {"success": False, "status": "error", "error": "Utente non trovato nel database"}
            
        return {"success": True, "status": "success", "user": user}
    except Exception as e:
        logger.error(f"Database error during verification for {phone}: {e}")
        return {"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}


async def get_user_chats_async(phone: str) -> dict:
    """
    Asynchronously fetches user's dialogs/chats from Telegram.
    Uses file-based sessions for better compatibility with chat loading.
    """
    db = get_db_connection()
    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT api_id, api_hash_encrypted FROM users WHERE phone = %s", (phone,))
        user_creds = cursor.fetchone()

    if not user_creds or not user_creds['api_id'] or not user_creds['api_hash_encrypted']:
        return {"success": False, "error": "API credentials not found for this user."}

    api_id = user_creds['api_id']
    api_hash = decrypt_api_hash(user_creds['api_hash_encrypted'])

    # Use file-based sessions for chat loading (like the working system)
    # Clean up any existing client to avoid event loop conflicts
    if phone in active_clients:
        try:
            await cleanup_phone_completely(phone)
        except:
            pass  # Ignore cleanup errors
    
    client = await get_telethon_client(phone, api_id, api_hash)
    if not client or not await client.is_user_authorized():
        logger.error(f"User {phone} is not authorized. Please log in again.")
        return {"success": False, "error": "Authorization lost. Please log in again."}

    chats = []
    try:
        async for dialog in client.iter_dialogs():
            # Include TUTTE le chat: gruppi, canali, persone e bot
            entity = dialog.entity
            
            # Determina il tipo di chat
            chat_type = "private"
            if dialog.is_channel:
                chat_type = "channel"
            elif dialog.is_group:
                chat_type = "supergroup" if hasattr(entity, 'megagroup') and entity.megagroup else "group"
            elif hasattr(entity, 'bot') and entity.bot:
                chat_type = "bot"
            elif hasattr(entity, 'user_id'):
                chat_type = "user"
            
            # Determina il titolo
            title = dialog.name
            if not title and hasattr(entity, 'first_name'):
                title = entity.first_name
                if hasattr(entity, 'last_name') and entity.last_name:
                    title += f" {entity.last_name}"
            if not title:
                title = "Unnamed Chat"
            
            chat_data = {
                "id": dialog.id,
                "title": title,
                "type": chat_type,
                "username": getattr(entity, 'username', None),
                "members_count": getattr(entity, 'participants_count', None),
                "description": getattr(entity, 'about', None),
                "unread_count": dialog.unread_count if hasattr(dialog, 'unread_count') else 0,
                "last_message_date": dialog.date.isoformat() if dialog.date else None,
                "is_bot": getattr(entity, 'bot', False),
                "is_user": hasattr(entity, 'user_id') and not getattr(entity, 'bot', False)
            }
            chats.append(chat_data)
        
        logger.info(f"Found {len(chats)} chats for user {phone}")
        return {"success": True, "chats": chats}
    except Exception as e:
        logger.error(f"Failed to fetch chats for {phone}: {e}")
        return {"success": False, "error": "Failed to fetch chats. Please try logging in again."}

# ============================================
# 📱 MULTI-CHANNEL ENDPOINTS
# ============================================

@app.route('/api/telegram/get-configured-channels', methods=['GET'])
@jwt_required()
def get_configured_channels():
    """Restituisce i canali configurati nell'ambiente"""
    try:
        phone = get_jwt_identity()
        if not phone:
            return jsonify({'error': get_error_message('UNAUTHORIZED')}), 401
        
        configured_channels = []
        for channel in Config.CONFIGURED_CHANNELS:
            if channel["id"]:  # Solo se l'ID è impostato
                configured_channels.append({
                    "id": channel["id"],
                    "name": channel["name"],
                    "priority": channel["priority"],
                    "configured": True
                })
        
        return jsonify({
            'success': True,
            'configured_channels': configured_channels,
            'total_configured': len(configured_channels)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching configured channels: {e}")
        return jsonify({'error': get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/telegram/channel-action', methods=['POST'])
@jwt_required()
def channel_action():
    """Esegue azioni specifiche su un canale configurato"""
    try:
        phone = get_jwt_identity()
        if not phone:
            return jsonify({'error': get_error_message('UNAUTHORIZED')}), 401
        
        data = request.get_json()
        channel_id = data.get('channel_id')
        action = data.get('action')  # 'info', 'members', 'recent_messages'
        
        if not channel_id or not action:
            return jsonify({'error': 'channel_id e action sono obbligatori'}), 400
        
        # Verifica che il canale sia tra quelli configurati
        is_configured = any(
            str(ch["id"]) == str(channel_id) 
            for ch in Config.CONFIGURED_CHANNELS 
            if ch["id"]
        )
        
        if not is_configured:
            return jsonify({'error': 'Canale non configurato nel sistema'}), 403
        
        # Esegui l'azione richiesta
        result = asyncio.run(execute_channel_action_async(phone, channel_id, action))
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        logger.error(f"Error in channel action: {e}")
        return jsonify({'error': get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

async def execute_channel_action_async(phone: str, channel_id: str, action: str) -> dict:
    """Esegue azioni specifiche su un canale"""
    db = get_db_connection()
    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT api_id, api_hash_encrypted FROM users WHERE phone = %s", (phone,))
        user_creds = cursor.fetchone()

    if not user_creds:
        return {"success": False, "error": "Credenziali utente non trovate"}

    api_id = user_creds['api_id']
    api_hash = decrypt_api_hash(user_creds['api_hash_encrypted'])

    # Use file-based sessions for channel actions (like the working system)
    client = await get_telethon_client(phone, api_id, api_hash)
    if not client or not await client.is_user_authorized():
        return {"success": False, "error": "Autorizzazione Telegram persa"}

    try:
        channel_entity = await client.get_entity(int(channel_id))
        
        if action == 'info':
            return {
                "success": True,
                "action": "info",
                "channel": {
                    "id": channel_entity.id,
                    "title": channel_entity.title,
                    "username": getattr(channel_entity, 'username', None),
                    "participants_count": getattr(channel_entity, 'participants_count', None),
                    "description": getattr(channel_entity, 'about', None),
                    "is_channel": hasattr(channel_entity, 'broadcast'),
                    "is_group": hasattr(channel_entity, 'megagroup')
                }
            }
        
        elif action == 'members':
            participants = []
            async for user in client.iter_participants(channel_entity, limit=100):
                participants.append({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_bot": user.bot
                })
            
            return {
                "success": True,
                "action": "members",
                "channel_id": channel_id,
                "members": participants,
                "total_shown": len(participants)
            }
        
        elif action == 'recent_messages':
            messages = []
            async for message in client.iter_messages(channel_entity, limit=10):
                messages.append({
                    "id": message.id,
                    "text": message.text or "[Media/File]",
                    "date": message.date.isoformat() if message.date else None,
                    "sender_id": message.sender_id,
                    "views": getattr(message, 'views', None)
                })
            
            return {
                "success": True,
                "action": "recent_messages",
                "channel_id": channel_id,
                "messages": messages,
                "total_shown": len(messages)
            }
        
        else:
            return {"success": False, "error": f"Azione '{action}' non supportata"}
    
    except Exception as e:
        logger.error(f"Error executing channel action {action} on {channel_id}: {e}")
        return {"success": False, "error": f"Errore durante l'esecuzione: {str(e)}"}

# ============================================
# 📱 RATE LIMITING SYSTEM
# ============================================

# Constants for rate limiting
SMS_CODE_LIMIT = 30  # Maximum SMS code requests before FLOOD_WAIT (more realistic)
SMS_CODE_RESET_HOURS = 24  # Hours to reset the counter
SMS_CODE_WARNING_THRESHOLD = 20  # Show warning when approaching limit

def get_sms_code_counter(phone: str) -> dict:
    """Get SMS code request counter for a phone number"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"count": 0, "reset_time": None, "remaining": SMS_CODE_LIMIT}
    
    counter_key = f"sms_counter:{phone}"
    reset_key = f"sms_reset:{phone}"
    
    # Get current count
    count = int(redis_conn.get(counter_key) or 0)
    
    # Get reset time
    reset_time = redis_conn.get(reset_key)
    if reset_time:
        reset_time = int(reset_time)
        # Check if reset time has passed
        if time.time() > reset_time:
            # Reset counter
            redis_conn.delete(counter_key)
            redis_conn.delete(reset_key)
            count = 0
            reset_time = None
    
    remaining = max(0, SMS_CODE_LIMIT - count)
    
    return {
        "count": count,
        "reset_time": reset_time,
        "remaining": remaining,
        "limit": SMS_CODE_LIMIT
    }

def increment_sms_code_counter(phone: str) -> dict:
    """Increment SMS code request counter and return current status"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"count": 1, "reset_time": None, "remaining": SMS_CODE_LIMIT - 1}
    
    counter_key = f"sms_counter:{phone}"
    reset_key = f"sms_reset:{phone}"
    
    # Get current status
    current = get_sms_code_counter(phone)
    
    # Increment counter
    new_count = current["count"] + 1
    redis_conn.set(counter_key, new_count)
    
    # Set reset time if not already set
    if not current["reset_time"]:
        reset_time = int(time.time() + (SMS_CODE_RESET_HOURS * 3600))
        redis_conn.set(reset_key, reset_time)
        current["reset_time"] = reset_time
    
    current["count"] = new_count
    current["remaining"] = max(0, SMS_CODE_LIMIT - new_count)
    
    return current

def can_request_sms_code(phone: str) -> dict:
    """Check if SMS code can be requested for this phone"""
    counter = get_sms_code_counter(phone)
    
    if counter["count"] >= SMS_CODE_LIMIT:
        # Calculate time remaining
        if counter["reset_time"]:
            time_remaining = counter["reset_time"] - int(time.time())
            if time_remaining > 0:
                hours = time_remaining // 3600
                minutes = (time_remaining % 3600) // 60
                return {
                    "can_request": False,
                    "reason": "limit_exceeded",
                    "time_remaining": time_remaining,
                    "time_formatted": f"{hours}h {minutes}m",
                    "counter": counter
                }
    
    return {
        "can_request": True,
        "counter": counter
    }

def sync_flood_wait_from_telegram(phone: str, flood_wait_seconds: int) -> dict:
    """Sync our counter with Telegram's FLOOD_WAIT response"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"count": 0, "reset_time": None, "remaining": SMS_CODE_LIMIT}
    
    counter_key = f"sms_counter:{phone}"
    reset_key = f"sms_reset:{phone}"
    
    # Calculate when the FLOOD_WAIT will expire
    reset_time = int(time.time() + flood_wait_seconds)
    
    # Set counter to limit and reset time
    redis_conn.set(counter_key, SMS_CODE_LIMIT)
    redis_conn.set(reset_key, reset_time)
    
    # Calculate time remaining
    hours = flood_wait_seconds // 3600
    minutes = (flood_wait_seconds % 3600) // 60
    
    return {
        "count": SMS_CODE_LIMIT,
        "reset_time": reset_time,
        "remaining": 0,
        "limit": SMS_CODE_LIMIT,
        "telegram_flood_wait": True,
        "time_formatted": f"{hours}h {minutes}m"
    }

# ============================================
#  API Endpoints
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker container monitoring."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {}
    }
    
    # Check database connection
    try:
        db = get_db_connection()
        if db and not db.closed:
            with db.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            health_status["services"]["database"] = "healthy"
        else:
            health_status["services"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis connection
    try:
        redis_conn = get_redis_connection()
        if redis_conn:
            redis_conn.ping()
            health_status["services"]["redis"] = "healthy"
        else:
            health_status["services"]["redis"] = "unhealthy"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] != "unhealthy" else 503
    return jsonify(health_status), status_code

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user with phone, password, and Telegram API credentials."""
    data = request.get_json()
    
    # Supporta sia 'phone' che 'phone_number' per compatibilità
    phone = data.get('phone') or data.get('phone_number')
    password = data.get('password')
    api_id = data.get('api_id')
    api_hash = data.get('api_hash')
    
    logger.info(f"Registration attempt for phone: {phone}")
    
    if not all([phone, password, api_id, api_hash]):
        logger.error(f"Missing required fields. phone: {bool(phone)}, password: {bool(password)}, api_id: {bool(api_id)}, api_hash: {bool(api_hash)}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('REQUIRED_FIELDS')}), 400
    
    try:
        api_id = int(api_id)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid API ID format: {api_id}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('INVALID_API_ID')}), 400
    
    # Validate phone format
    if not re.match(r'^\+\d{10,15}$', phone):
        logger.error(f"Invalid phone number format: {phone}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('INVALID_PHONE')}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "status": "error", "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if user already exists
            cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            existing_user = cursor.fetchone()
            if existing_user:
                return jsonify({"success": False, "status": "error", "error": get_error_message('PHONE_EXISTS')}), 409
            
            # Hash password and encrypt API hash
            password_hash = generate_password_hash(password)
            api_hash_encrypted = encrypt_api_hash(api_hash)
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (phone, password_hash, api_id, api_hash_encrypted, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (phone, password_hash, api_id, api_hash_encrypted, datetime.now(timezone.utc)))
            
            result = cursor.fetchone()
            if not result:
                raise Exception("Failed to insert user - no ID returned")
                
            user_id = result['id']
            db.commit()
            
            logger.info(f"New user registered: {phone} (ID: {user_id})")
            return jsonify({
                "success": True,
                "status": "success", 
                "message": "User registered successfully",
                "user_id": user_id
            }), 201
            
    except Exception as e:
        db.rollback()
        logger.error(f"Registration failed for {phone}: {e}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('REGISTRATION_FAILED')}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Handles user login. Does not start Telegram session, just verifies DB user
    and sends a verification code via Telegram.
    OPTIMIZED: Includes performance metrics tracking.
    """
    start_time = time.time()
    
    data = request.get_json()
    # Supporta sia 'phone' che 'phone_number' per compatibilità
    phone = data.get('phone') or data.get('phone_number')
    password = data.get('password')

    if not phone or not password:
        response_time = time.time() - start_time
        record_login_metric(False, response_time)
        return jsonify({"success": False, "status": "error", "error": get_error_message('PHONE_PASSWORD_REQUIRED')}), 400

    db = get_db_connection()
    if not db:
        response_time = time.time() - start_time
        record_login_metric(False, response_time)
        return jsonify({"success": False, "status": "error", "error": get_error_message('DB_CONNECTION_FAILED')}), 500
        
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE phone = %s", (phone,))
            user = cursor.fetchone()

        logger.info(f"Login attempt for phone: {phone}")
        logger.info(f"User found: {user is not None}")
        if user:
            logger.info(f"User ID: {user['id']}")
            logger.info(f"Has password hash: {user.get('password_hash') is not None}")
            logger.info(f"Has API ID: {user.get('api_id') is not None}")
            logger.info(f"Has API hash: {user.get('api_hash_encrypted') is not None}")

        if user and check_password_hash(user['password_hash'], password):
            if not user.get('api_id') or not user.get('api_hash_encrypted'):
                response_time = time.time() - start_time
                record_login_metric(False, response_time)
                return jsonify({"success": False, "status": "error", "error": get_error_message('API_CREDENTIALS_NOT_SET')}), 400

            api_id = user['api_id']
            api_hash = decrypt_api_hash(user['api_hash_encrypted'])
            
            # OPTIMIZED: Better event loop management to avoid conflicts
            try:
                # Try to get existing event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, use asyncio.create_task for better performance
                    import concurrent.futures
                    
                    # Use thread pool for async operation to avoid loop conflicts
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            send_telegram_code_async(phone, api_id, api_hash, password)
                        )
                        result = future.result(timeout=30)  # Reduced from 60 to 30 seconds
                else:
                    # No running loop, safe to use asyncio.run()
                    result = asyncio.run(send_telegram_code_async(phone, api_id, api_hash, password))
            except RuntimeError:
                # Fallback to creating new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(send_telegram_code_async(phone, api_id, api_hash, password))
                finally:
                    loop.close()
            
            response_time = time.time() - start_time
            
            if result.get("success"):
                record_login_metric(True, response_time)
                return jsonify({"success": True, "status": "success", "message": result.get("message")})
            else:
                record_login_metric(False, response_time)
                return jsonify(result), 400
        else:
            response_time = time.time() - start_time
            record_login_metric(False, response_time)
            return jsonify({"success": False, "status": "error", "error": get_error_message('INVALID_CREDENTIALS')}), 401
    except Exception as e:
        response_time = time.time() - start_time
        record_login_metric(False, response_time)
        logger.error(f"Login error for {phone}: {e}")
        return jsonify({"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Changes the user's password after verifying the current password
    """
    current_user_id = get_jwt_identity()
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({"success": False, "error": "Password attuale e nuova password sono obbligatorie"}), 400
    
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "La nuova password deve essere di almeno 6 caratteri"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get current user data
            cursor.execute("SELECT * FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"success": False, "error": "Utente non trovato"}), 404
            
            # Verify current password
            if not check_password_hash(user['password_hash'], current_password):
                return jsonify({"success": False, "error": "Password attuale non corretta"}), 401
            
            # Check if new password is different from current
            if check_password_hash(user['password_hash'], new_password):
                return jsonify({"success": False, "error": "La nuova password deve essere diversa da quella attuale"}), 400
            
            # Generate new password hash
            new_password_hash = generate_password_hash(new_password)
            
            # Update password in database
            cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, current_user_id))
            db.commit()
            
            logger.info(f"Password changed successfully for user ID {current_user_id}")
            
            return jsonify({
                "success": True,
                "message": "Password cambiata con successo"
            }), 200
            
    except Exception as e:
        db.rollback()
        logger.error(f"Error changing password for user ID {current_user_id}: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/auth/verify-code', methods=['POST'])
def verify_code():
    """
    Verifies the Telegram login code provided by the user.
    """
    data = request.get_json()
    # Supporta sia 'phone' che 'phone_number' per compatibilità
    phone = data.get('phone') or data.get('phone_number')
    code = data.get('code')
    
    if not phone or not code:
        return jsonify({"success": False, "status": "error", "error": get_error_message('PHONE_CODE_REQUIRED')}), 400

    logger.info(f"Attempting to verify code for phone: {phone}")
    
    try:
        result = asyncio.run(verify_telegram_code_async(phone, code))
        
        if result.get("success"):
            user = result.get("user")
            access_token = create_access_token(identity=user['id'])
            return jsonify({
                "success": True,
                "status": "success",
                "message": "Verifica completata con successo",
                "access_token": access_token,
                "user": {
                    "id": user['id'],
                    "phone": user['phone'],
                }
            })
        else:
            return jsonify(result), 401
    except Exception as e:
        logger.error(f"Error verifying code: {e}", exc_info=True)
        return jsonify({"success": False, "status": "error", "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/user/profile', methods=['GET', 'PUT'])
@jwt_required()
def user_profile():
    """Get or update user profile information"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    if request.method == 'GET':
        try:
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, phone, api_id, created_at, last_login, is_active 
                    FROM users WHERE id = %s
                """, (current_user_id,))
                user = cursor.fetchone()
            
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            # Convert datetime objects to strings for JSON serialization
            user_data = dict(user)
            if user_data.get('created_at'):
                user_data['created_at'] = user_data['created_at'].isoformat()
            if user_data.get('last_login'):
                user_data['last_login'] = user_data['last_login'].isoformat()
            
            return jsonify({
                "success": True,
                "user": user_data
            }), 200
            
        except Exception as e:
            logger.error(f"Error fetching user profile for ID {current_user_id}: {e}")
            return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500
    
    elif request.method == 'PUT':
        # Handle profile updates (e.g., API credentials)
        data = request.get_json()
        api_id = data.get('api_id')
        api_hash = data.get('api_hash')
        
        if not api_id or not api_hash:
            return jsonify({"success": False, "error": "API ID and API Hash are required"}), 400
        
        try:
            api_id = int(api_id)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": get_error_message('INVALID_API_ID')}), 400
        
        try:
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                # Encrypt the new API hash
                api_hash_encrypted = encrypt_api_hash(api_hash)
                
                cursor.execute("""
                    UPDATE users 
                    SET api_id = %s, api_hash_encrypted = %s 
                    WHERE id = %s
                """, (api_id, api_hash_encrypted, current_user_id))
                
                db.commit()
                
                logger.info(f"Updated API credentials for user ID {current_user_id}")
                return jsonify({
                    "success": True,
                    "message": "API credentials updated successfully",
                    "api_id": api_id
                }), 200
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user profile for ID {current_user_id}: {e}")
            return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500



@app.route('/api/user/chats', methods=['GET'])
@jwt_required()
def get_user_chats():
    """
    Fetches the list of chats for the authenticated user.
    """
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    with db.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
        user_record = cursor.fetchone()
    
    if not user_record:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    phone = user_record['phone']
    logger.info(f"Fetching chats for user {phone} (ID: {current_user_id})")

    try:
        # Gestione event loop per evitare conflitti
        try:
            # Prova prima con un nuovo loop isolato
            result = asyncio.run(get_user_chats_async(phone))
        except RuntimeError as e:
            if "event loop is already running" in str(e):
                # Se c'è già un loop attivo, usa un nuovo thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, get_user_chats_async(phone))
                    result = future.result(timeout=60)
            else:
                raise e
            
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching user chats: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500

# ============================================
# 🔄 FORWARDER ENDPOINTS
# ============================================

@app.route('/api/forwarders/<source_chat_id>', methods=['GET'])
@jwt_required()
def get_forwarders(source_chat_id):
    """Get all forwarders for a specific chat"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, source_chat_id, source_chat_title, target_type, 
                       target_id, target_name, container_name, container_status, 
                       messages_forwarded, created_at, last_forwarded_at
                FROM forwarders 
                WHERE user_id = %s AND source_chat_id = %s
                ORDER BY created_at DESC
            """, (current_user_id, source_chat_id))
            forwarders = cursor.fetchall()
        
        # Get container status for each forwarder
        forwarder_manager = ForwarderManager()
        for forwarder in forwarders:
            if forwarder['container_name']:
                container_status = forwarder_manager.get_container_status(forwarder['container_name'])
                forwarder['container_status'] = container_status['status']
                forwarder['message_count'] = container_status.get('message_count', forwarder['messages_forwarded'])
                forwarder['is_running'] = container_status.get('running', False)
            else:
                forwarder['container_status'] = 'not_created'
                forwarder['is_running'] = False
            
            # Convert datetime to ISO format
            if forwarder.get('created_at'):
                forwarder['created_at'] = forwarder['created_at'].isoformat()
            if forwarder.get('last_forwarded_at'):
                forwarder['last_message_at'] = forwarder['last_forwarded_at'].isoformat()
            else:
                forwarder['last_message_at'] = None
        
        return jsonify({
            "success": True,
            "forwarders": forwarders,
            "total": len(forwarders)
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching forwarders: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/auth/reactivate-session', methods=['POST'])
@jwt_required()
def reactivate_telegram_session():
    """Send verification code to reactivate Telegram session"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted, password_hash
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        api_id = user['api_id']
        api_hash = decrypt_api_hash(user['api_hash_encrypted'])
        
        # Send verification code
        result = asyncio.run(send_telegram_code_async(phone, api_id, api_hash, "temp_password"))
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": "Codice di verifica inviato",
                "phone": phone  # Return phone for frontend use
            }), 200
        else:
            return jsonify({"success": False, "error": result.get("error", "Errore invio codice")}), 400
            
    except Exception as e:
        logger.error(f"Error reactivating session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/verify-session-code', methods=['POST'])
@jwt_required()
def verify_session_code():
    """Verify code to reactivate Telegram session"""
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({"success": False, "error": "Codice richiesto"}), 400
    
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        
        # Verify the code
        result = asyncio.run(verify_telegram_code_async(phone, code))
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": "Sessione riattivata con successo"
            }), 200
        else:
            return jsonify({"success": False, "error": result.get("error", "Codice non valido")}), 400
            
    except Exception as e:
        logger.error(f"Error verifying session code: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/check-session', methods=['POST'])
@jwt_required()
def check_telegram_session():
    """Check if user has an active Telegram session"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        
        # Check if client exists and is authorized
        if phone in active_clients:
            client = active_clients[phone]
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                is_authorized = loop.run_until_complete(client.is_user_authorized())
                loop.close()
                
                if is_authorized:
                    return jsonify({
                        "success": True, 
                        "session_active": True,
                        "message": "Sessione Telegram attiva"
                    }), 200
            except:
                pass
        
        return jsonify({
            "success": True,
            "session_active": False,
            "message": "Sessione Telegram non attiva. È necessario effettuare l'accesso."
        }), 200
        
    except Exception as e:
        logger.error(f"Error checking session: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/forwarders/prepare', methods=['POST'])
@jwt_required()
def prepare_forwarder():
    """Prepare forwarder session - send verification code"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['source_chat_id', 'source_chat_title']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Campo richiesto: {field}"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Get user credentials
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        api_id = user['api_id']
        api_hash = decrypt_api_hash(user['api_hash_encrypted'])
        source_chat_id = data['source_chat_id']
        
        # --- Gestione automatica della sessione forwarder ----------------------------------
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        session_file = os.path.join(SESSION_DIR, f"{session_name}.session")

        code_from_client: Optional[str] = data.get('code')

        # Controlliamo se esiste già una sessione forwarder valida
        session_exists_and_valid = False
        if os.path.exists(session_file):
            try:
                async def _check_session():
                    client = TelegramClient(session_file, api_id, api_hash)
                    await client.connect()
                    authorized = await client.is_user_authorized()
                    await client.disconnect()
                    return authorized

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                session_exists_and_valid = loop.run_until_complete(_check_session())
                loop.close()
                logger.info(f"Session {session_name} exists and is valid: {session_exists_and_valid}")
            except Exception as e:
                logger.warning(f"Session {session_name} exists but is invalid: {e}")
                # Rimuoviamo il file di sessione corrotto
                os.remove(session_file)
                session_exists_and_valid = False

        # Se la sessione è valida, non serve richiedere il codice
        if session_exists_and_valid:
            logger.info(f"Using existing valid session for {session_name}")
            # For now, we'll use empty session string as we're using file session
            session_string = ""
        else:
            # SEMPRE chiediamo il codice per un nuovo forwarder
            verification_key = f"forwarder_verification:{current_user_id}:{source_chat_id}"
            redis_conn = get_redis_connection()

            # 1) L'utente NON ha inviato alcun codice -> inviamo codice e salviamo phone_code_hash
            if not code_from_client:
                # Check rate limiting first
                rate_check = can_request_sms_code(phone)
                if not rate_check["can_request"]:
                    return jsonify({
                        "success": False, 
                        "error": f"Limite SMS raggiunto. Riprova tra {rate_check['time_formatted']}",
                        "rate_limit": rate_check
                    }), 429
                
                try:
                    async def _send_code():
                        # Se esiste già un file sessione, rimuoviamolo per iniziare da zero
                        if os.path.exists(session_file):
                            os.remove(session_file)
                            logger.info(f"Removed existing session file for {session_name}")
                        
                        client = TelegramClient(session_file, api_id, api_hash)
                        await client.connect()
                        result = await client.send_code_request(phone)

                        if redis_conn:
                            verification_data = {
                                "phone_code_hash": result.phone_code_hash,
                                "session_name": session_name,
                                "api_id": api_id,
                                "api_hash": api_hash
                            }
                            redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
                        await client.disconnect()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_send_code())
                    loop.close()

                    # Increment counter after successful request
                    counter_status = increment_sms_code_counter(phone)
                    
                    # Prepare response with counter info
                    response = {
                        "success": True,
                        "code_sent": True,
                        "message": f"Codice di verifica inviato a {phone}",
                        "phone": phone,
                        "rate_limit": counter_status
                    }
                    
                    # Add warning if approaching limit
                    if counter_status["count"] >= SMS_CODE_WARNING_THRESHOLD:
                        response["warning"] = f"Attenzione: hai fatto {counter_status['count']} richieste su {counter_status['limit']}. Limite raggiunto tra {counter_status['remaining']} richieste."

                    return jsonify(response), 202  # 202 Accepted -> client deve inviare 'code'
                except Exception as e:
                    logger.error(f"Error sending code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # 2) Abbiamo ricevuto un codice -> verifichiamo
            else:
                if not redis_conn or not redis_conn.exists(verification_key):
                    return jsonify({"success": False, "error": "Richiesta di verifica scaduta o assente"}), 400

                try:
                    verification_data = json.loads(redis_conn.get(verification_key))

                    async def _verify_code():
                        client = TelegramClient(session_file, verification_data['api_id'], verification_data['api_hash'])
                        await client.connect()
                        await client.sign_in(phone, code_from_client, phone_code_hash=verification_data['phone_code_hash'])
                        authorized = await client.is_user_authorized()
                        await client.disconnect()
                        return authorized

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ok = loop.run_until_complete(_verify_code())
                    loop.close()

                    if not ok:
                        return jsonify({"success": False, "error": "Codice non valido"}), 400

                    # Puliamo la chiave redis e proseguiamo con la creazione del container
                    redis_conn.delete(verification_key)
                    logger.info(f"Forwarder session created for {session_name}")
                except Exception as e:
                    logger.error(f"Error verifying code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # For now, we'll use empty session string as we're using file session
            session_string = ""
        
        # Resolve target name if not provided
        target_name = data.get('target_name', '')
        if not target_name:
            try:
                # Try to get target entity name
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def get_target_name():
                    try:
                        if data['target_type'] == 'user' and data['target_id'].startswith('@'):
                            entity = await client.get_entity(data['target_id'])
                        else:
                            entity = await client.get_entity(int(data['target_id']))
                        
                        if hasattr(entity, 'username') and entity.username:
                            return f"@{entity.username}"
                        elif hasattr(entity, 'first_name'):
                            return f"{entity.first_name} {getattr(entity, 'last_name', '')}".strip()
                        elif hasattr(entity, 'title'):
                            return entity.title
                        else:
                            return data['target_id']
                    except:
                        return data['target_id']
                
                target_name = loop.run_until_complete(get_target_name())
                loop.close()
            except:
                target_name = data['target_id']
        
        # Build forwarder image if needed
        forwarder_manager = ForwarderManager()
        # Image is ensured in ForwarderManager.__init__()
        
        # Get forwarder-specific session file path
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        forwarder_session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
        
        # Create container
        success, container_name, message = forwarder_manager.create_forwarder_container(
            user_id=current_user_id,
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            source_chat_id=data['source_chat_id'],
            source_chat_title=data['source_chat_title'],
            target_type=data['target_type'],
            target_id=data['target_id'],
            target_name=target_name,
            session_file_path=forwarder_session_file
        )
        
        if not success:
            return jsonify({"success": False, "error": f"Errore creazione container: {message}"}), 500
        
        # Save to database
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                INSERT INTO forwarders (
                    user_id, source_chat_id, source_chat_title, 
                    target_type, target_id, target_name, 
                    container_name, container_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                current_user_id, data['source_chat_id'], data['source_chat_title'],
                data['target_type'], data['target_id'], target_name,
                container_name, 'running'
            ))
            
            forwarder_id = cursor.fetchone()['id']
            db.commit()
        
        logger.info(f"Created forwarder {forwarder_id} with container {container_name}")
        
        return jsonify({
            "success": True,
            "message": "Inoltro creato con successo",
            "forwarder_id": forwarder_id,
            "container_name": container_name
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error preparing forwarder: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/verify-code', methods=['POST'])
@jwt_required()
def verify_forwarder_code():
    """Verify code and create forwarder session"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('code') or not data.get('source_chat_id'):
        return jsonify({"success": False, "error": "Codice e source_chat_id richiesti"}), 400
    
    redis_conn = get_redis_connection()
    verification_key = f"forwarder_verification:{current_user_id}:{data['source_chat_id']}"
    
    if not redis_conn or not redis_conn.exists(verification_key):
        return jsonify({"success": False, "error": "Richiesta di verifica scaduta"}), 400
    
    try:
        verification_data = json.loads(redis_conn.get(verification_key))
        session_name = verification_data['session_name']
        session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
        
        async def verify_and_save():
            client = TelegramClient(
                session_file,
                verification_data['api_id'],
                verification_data['api_hash']
            )
            await client.connect()
            
            db = get_db_connection()
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
                user = cursor.fetchone()
            
            await client.sign_in(
                user['phone'],
                data['code'],
                phone_code_hash=verification_data['phone_code_hash']
            )
            
            is_authorized = await client.is_user_authorized()
            await client.disconnect()
            return is_authorized
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        is_authorized = loop.run_until_complete(verify_and_save())
        loop.close()
        
        if is_authorized:
            redis_conn.delete(verification_key)
            return jsonify({
                "success": True,
                "message": "Sessione creata con successo"
            }), 200
        else:
            return jsonify({"success": False, "error": "Autorizzazione fallita"}), 400
            
    except Exception as e:
        logger.error(f"Error verifying code: {e}")
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/forwarders', methods=['POST'])
@jwt_required()
def create_forwarder():
    """Create a new forwarder"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['source_chat_id', 'source_chat_title', 'target_type', 'target_id']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Campo richiesto: {field}"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Get user credentials
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        api_id = user['api_id']
        api_hash = decrypt_api_hash(user['api_hash_encrypted'])
        source_chat_id = data['source_chat_id']
        
        # --- Gestione automatica della sessione forwarder ----------------------------------
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        session_file = os.path.join(SESSION_DIR, f"{session_name}.session")

        code_from_client: Optional[str] = data.get('code')

        # Controlliamo se esiste già una sessione forwarder valida
        session_exists_and_valid = False
        if os.path.exists(session_file):
            try:
                async def _check_session():
                    client = TelegramClient(session_file, api_id, api_hash)
                    await client.connect()
                    authorized = await client.is_user_authorized()
                    await client.disconnect()
                    return authorized

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                session_exists_and_valid = loop.run_until_complete(_check_session())
                loop.close()
                logger.info(f"Session {session_name} exists and is valid: {session_exists_and_valid}")
            except Exception as e:
                logger.warning(f"Session {session_name} exists but is invalid: {e}")
                # Rimuoviamo il file di sessione corrotto
                os.remove(session_file)
                session_exists_and_valid = False

        # Se la sessione è valida, non serve richiedere il codice
        if session_exists_and_valid:
            logger.info(f"Using existing valid session for {session_name}")
            # For now, we'll use empty session string as we're using file session
            session_string = ""
        else:
            # SEMPRE chiediamo il codice per un nuovo forwarder
            verification_key = f"forwarder_verification:{current_user_id}:{source_chat_id}"
            redis_conn = get_redis_connection()

            # 1) L'utente NON ha inviato alcun codice -> inviamo codice e salviamo phone_code_hash
            if not code_from_client:
                # Check rate limiting first
                rate_check = can_request_sms_code(phone)
                if not rate_check["can_request"]:
                    return jsonify({
                        "success": False, 
                        "error": f"Limite SMS raggiunto. Riprova tra {rate_check['time_formatted']}",
                        "rate_limit": rate_check
                    }), 429
                
                try:
                    async def _send_code():
                        # Se esiste già un file sessione, rimuoviamolo per iniziare da zero
                        if os.path.exists(session_file):
                            os.remove(session_file)
                            logger.info(f"Removed existing session file for {session_name}")
                        
                        client = TelegramClient(session_file, api_id, api_hash)
                        await client.connect()
                        result = await client.send_code_request(phone)

                        if redis_conn:
                            verification_data = {
                                "phone_code_hash": result.phone_code_hash,
                                "session_name": session_name,
                                "api_id": api_id,
                                "api_hash": api_hash
                            }
                            redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
                        await client.disconnect()

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(_send_code())
                    loop.close()

                    # Increment counter after successful request
                    counter_status = increment_sms_code_counter(phone)
                    
                    # Prepare response with counter info
                    response = {
                        "success": True,
                        "code_sent": True,
                        "message": f"Codice di verifica inviato a {phone}",
                        "phone": phone,
                        "rate_limit": counter_status
                    }
                    
                    # Add warning if approaching limit
                    if counter_status["count"] >= SMS_CODE_WARNING_THRESHOLD:
                        response["warning"] = f"Attenzione: hai fatto {counter_status['count']} richieste su {counter_status['limit']}. Limite raggiunto tra {counter_status['remaining']} richieste."

                    return jsonify(response), 202  # 202 Accepted -> client deve inviare 'code'
                except Exception as e:
                    logger.error(f"Error sending code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # 2) Abbiamo ricevuto un codice -> verifichiamo
            else:
                if not redis_conn or not redis_conn.exists(verification_key):
                    return jsonify({"success": False, "error": "Richiesta di verifica scaduta o assente"}), 400

                try:
                    verification_data = json.loads(redis_conn.get(verification_key))

                    async def _verify_code():
                        client = TelegramClient(session_file, verification_data['api_id'], verification_data['api_hash'])
                        await client.connect()
                        await client.sign_in(phone, code_from_client, phone_code_hash=verification_data['phone_code_hash'])
                        authorized = await client.is_user_authorized()
                        await client.disconnect()
                        return authorized

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ok = loop.run_until_complete(_verify_code())
                    loop.close()

                    if not ok:
                        return jsonify({"success": False, "error": "Codice non valido"}), 400

                    # Puliamo la chiave redis e proseguiamo con la creazione del container
                    redis_conn.delete(verification_key)
                    logger.info(f"Forwarder session created for {session_name}")
                except Exception as e:
                    logger.error(f"Error verifying code for forwarder session: {e}")
                    return jsonify({"success": False, "error": str(e)}), 500

            # For now, we'll use empty session string as we're using file session
            session_string = ""
        
        # Resolve target name if not provided
        target_name = data.get('target_name', '')
        if not target_name:
            try:
                # Try to get target entity name
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def get_target_name():
                    try:
                        if data['target_type'] == 'user' and data['target_id'].startswith('@'):
                            entity = await client.get_entity(data['target_id'])
                        else:
                            entity = await client.get_entity(int(data['target_id']))
                        
                        if hasattr(entity, 'username') and entity.username:
                            return f"@{entity.username}"
                        elif hasattr(entity, 'first_name'):
                            return f"{entity.first_name} {getattr(entity, 'last_name', '')}".strip()
                        elif hasattr(entity, 'title'):
                            return entity.title
                        else:
                            return data['target_id']
                    except:
                        return data['target_id']
                
                target_name = loop.run_until_complete(get_target_name())
                loop.close()
            except:
                target_name = data['target_id']
        
        # Build forwarder image if needed
        forwarder_manager = ForwarderManager()
        # Image is ensured in ForwarderManager.__init__()
        
        # Get forwarder-specific session file path
        session_name = f"forwarder_{hash_phone_number(phone)}_{source_chat_id}"
        forwarder_session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
        
        # Create container
        success, container_name, message = forwarder_manager.create_forwarder_container(
            user_id=current_user_id,
            phone=phone,
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            source_chat_id=data['source_chat_id'],
            source_chat_title=data['source_chat_title'],
            target_type=data['target_type'],
            target_id=data['target_id'],
            target_name=target_name,
            session_file_path=forwarder_session_file
        )
        
        if not success:
            return jsonify({"success": False, "error": f"Errore creazione container: {message}"}), 500
        
        # Save to database
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                INSERT INTO forwarders (
                    user_id, source_chat_id, source_chat_title, 
                    target_type, target_id, target_name, 
                    container_name, container_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                current_user_id, data['source_chat_id'], data['source_chat_title'],
                data['target_type'], data['target_id'], target_name,
                container_name, 'running'
            ))
            
            forwarder_id = cursor.fetchone()['id']
            db.commit()
        
        logger.info(f"Created forwarder {forwarder_id} with container {container_name}")
        
        return jsonify({
            "success": True,
            "message": "Inoltro creato con successo",
            "forwarder_id": forwarder_id,
            "container_name": container_name
        }), 201
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error creating forwarder: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/<int:forwarder_id>', methods=['DELETE'])
@jwt_required()
def delete_forwarder(forwarder_id):
    """Delete a forwarder and its container"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Verify ownership
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT container_name 
                FROM forwarders 
                WHERE id = %s AND user_id = %s
            """, (forwarder_id, current_user_id))
            forwarder = cursor.fetchone()
        
        if not forwarder:
            logger.warning(f"Forwarder {forwarder_id} not found for user {current_user_id}")
            return jsonify({"success": False, "error": "Inoltro non trovato"}), 404
        
        container_name = forwarder['container_name']
        logger.info(f"Attempting to delete forwarder {forwarder_id} with container {container_name}")
        
        # Stop and remove container (this will succeed even if container doesn't exist)
        forwarder_manager = ForwarderManager()
        success, message = forwarder_manager.stop_and_remove_container(container_name)
        
        logger.info(f"Container removal result: success={success}, message={message}")
        
        # Delete from database regardless of container removal status
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM forwarders WHERE id = %s", (forwarder_id,))
            db.commit()
        
        # Force a small delay to ensure transaction is visible
        time.sleep(0.1)
        
        logger.info(f"Successfully deleted forwarder {forwarder_id} from database")
        
        return jsonify({
            "success": True,
            "message": "Inoltro eliminato con successo",
            "container_removed": success,
            "container_message": message
        }), 200
            
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error deleting forwarder {forwarder_id}: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/<int:forwarder_id>/restart', methods=['POST'])
@jwt_required()
def restart_forwarder(forwarder_id):
    """Restart a forwarder container"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Verify ownership
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT container_name 
                FROM forwarders 
                WHERE id = %s AND user_id = %s
            """, (forwarder_id, current_user_id))
            forwarder = cursor.fetchone()
        
        if not forwarder:
            return jsonify({"success": False, "error": "Inoltro non trovato"}), 404
        
        # Restart container
        forwarder_manager = ForwarderManager()
        success, message = forwarder_manager.restart_container(forwarder['container_name'])
        
        if success:
            # Update status in database
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE forwarders 
                    SET container_status = 'running' 
                    WHERE id = %s
                """, (forwarder_id,))
                db.commit()
            
            return jsonify({
                "success": True,
                "message": "Container riavviato con successo"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"Errore riavvio: {message}"
            }), 500
            
    except Exception as e:
        logger.error(f"Error restarting forwarder: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

@app.route('/api/forwarders/cleanup-orphaned', methods=['POST'])
@jwt_required()
def cleanup_orphaned_forwarders():
    """Clean up forwarders that exist in database but don't have containers"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": get_error_message('DB_CONNECTION_FAILED')}), 500
    
    try:
        # Get all forwarders for the user
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, container_name 
                FROM forwarders 
                WHERE user_id = %s
            """, (current_user_id,))
            forwarders = cursor.fetchall()
        
        orphaned_count = 0
        forwarder_manager = ForwarderManager()
        
        for forwarder in forwarders:
            container_status = forwarder_manager.get_container_status(forwarder['container_name'])
            
            # If container doesn't exist, mark as orphaned
            if container_status['status'] == 'not_found':
                logger.info(f"Found orphaned forwarder {forwarder['id']} with container {forwarder['container_name']}")
                
                # Delete from database
                with db.cursor() as cursor:
                    cursor.execute("DELETE FROM forwarders WHERE id = %s", (forwarder['id'],))
                
                orphaned_count += 1
        
        if orphaned_count > 0:
            db.commit()
            logger.info(f"Cleaned up {orphaned_count} orphaned forwarders for user {current_user_id}")
        
        return jsonify({
            "success": True,
            "message": f"Pulizia completata. Rimossi {orphaned_count} inoltri orfani.",
            "orphaned_count": orphaned_count
        }), 200
        
    except Exception as e:
        if db:
            db.rollback()
        logger.error(f"Error cleaning up orphaned forwarders: {e}")
        return jsonify({"success": False, "error": get_error_message('UNEXPECTED_ERROR', error=str(e))}), 500

# ============================================
# Application Bootstrap
# ============================================

def create_app():
    with app.app_context():
        get_db_connection()
        get_redis_connection()
    return app

@app.route('/api/auth/sms-status', methods=['GET'])
@jwt_required()
def get_sms_status():
    """Get SMS code request status for current user"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        rate_check = can_request_sms_code(phone)
        
        return jsonify({
            "success": True,
            "phone": phone,
            "rate_limit": rate_check
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting SMS status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/reset-sms-counter', methods=['POST'])
@jwt_required()
def reset_sms_counter():
    """Force reset SMS code counter for current user (for testing)"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({"success": False, "error": "Utente non trovato"}), 404
        
        phone = user['phone']
        redis_conn = get_redis_connection()
        
        if redis_conn:
            # Reset counter
            counter_key = f"sms_counter:{phone}"
            reset_key = f"sms_reset:{phone}"
            redis_conn.delete(counter_key)
            redis_conn.delete(reset_key)
            
            logger.info(f"Reset SMS counter for {phone}")
        
        return jsonify({
            "success": True,
            "message": "Contatore SMS resettato",
            "phone": phone
        }), 200
        
    except Exception as e:
        logger.error(f"Error resetting SMS counter: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/check-cached-code', methods=['GET'])
def check_cached_code():
    """Check if there's a cached verification code available for a phone number"""
    phone = request.args.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Numero di telefono richiesto"}), 400
    
    redis_conn = get_redis_connection()
    if not redis_conn:
        return jsonify({"success": False, "error": "Errore di connessione Redis"}), 500
    
    # Check both cached_code and verification keys
    cached_code_data = get_cached_code(phone)
    verification_key = f"verification:{phone}"
    verification_data = redis_conn.get(verification_key)
    
    if cached_code_data:
        # Calculate remaining time
        remaining_time = int(cached_code_data['expires_at'] - time.time())
        if remaining_time > 0:
            return jsonify({
                "success": True,
                "has_cached_code": True,
                "remaining_time": remaining_time,
                "message": f"Codice in cache disponibile per {remaining_time} secondi"
            })
    
    if verification_data:
        try:
            # Check if verification data exists and is still valid (10 minutes)
            data = json.loads(verification_data)
            return jsonify({
                "success": True,
                "has_cached_code": True,
                "remaining_time": 600,  # 10 minutes
                "message": "Codice di verifica disponibile (dati di sessione)"
            })
        except (json.JSONDecodeError, KeyError):
            pass
    
    return jsonify({
        "success": True,
        "has_cached_code": False,
        "message": "Nessun codice in cache disponibile"
    })

@app.route('/api/auth/use-cached-code', methods=['POST'])
def use_cached_code():
    """Use a cached verification code instead of requesting a new one"""
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Numero di telefono richiesto"}), 400
    
    cached_code_data = get_cached_code(phone)
    
    if not cached_code_data:
        return jsonify({"success": False, "error": "Nessun codice in cache disponibile"}), 404
    
    # Store verification data in Redis for verification step
    redis_conn = get_redis_connection()
    if not redis_conn:
        return jsonify({"success": False, "error": "Errore di connessione Redis"}), 500
    
    verification_key = f"verification:{phone}"
    verification_data = {
        "api_id": cached_code_data["api_id"],
        "api_hash": cached_code_data["api_hash"],
        "phone_code_hash": cached_code_data["phone_code_hash"],
        "password": cached_code_data.get("password"),
        "cached_code": cached_code_data["code"]
    }
    redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
    
    # Get counter status without incrementing
    counter_status = get_sms_code_counter(phone)
    
    return jsonify({
        "success": True,
        "message": f"Codice in cache attivato per {phone}",
        "rate_limit": counter_status,
        "cached": True
    })

@app.route('/api/auth/clear-cached-code', methods=['POST'])
def clear_cached_code():
    """Clear cached verification code for a phone number"""
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({"success": False, "error": "Numero di telefono richiesto"}), 400
    
    clear_cached_code(phone)
    
    return jsonify({
        "success": True,
        "message": f"Codice in cache cancellato per {phone}"
    })

@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user and clear session"""
    current_user_id = get_jwt_identity()
    
    try:
        # Get user phone for logging
        db = get_db_connection()
        if db:
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT phone FROM users WHERE id = %s", (current_user_id,))
                user = cursor.fetchone()
            
            if user:
                phone = user['phone']
                logger.info(f"User logged out: {hash_phone_number(phone)}")
        
        # Clear any active sessions or tokens
        # Note: JWT tokens are stateless, so we rely on client-side cleanup
        
        return jsonify({
            "success": True,
            "message": "Logout completato con successo"
        }), 200
        
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/validate-session', methods=['GET'])
@jwt_required()
def validate_session():
    """Validate if the current JWT session is still valid"""
    current_user_id = get_jwt_identity()
    
    try:
        # Get user info to verify the user still exists
        db = get_db_connection()
        if not db:
            return jsonify({"success": False, "error": "Database connection failed"}), 500
        
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, phone, created_at, last_login 
                FROM users WHERE id = %s
            """, (current_user_id,))
            user = cursor.fetchone()
        
        if not user:
            return jsonify({
                "success": False,
                "session_valid": False,
                "error": "Utente non trovato"
            }), 404
        
        # Check if user has been deleted or deactivated
        # For now, we just verify the user exists
        # In the future, you could add additional checks like:
        # - Account status (active/inactive)
        # - Last activity timestamp
        # - Session expiration based on last_login
        
        return jsonify({
            "success": True,
            "session_valid": True,
            "user_id": user['id'],
            "phone": hash_phone_number(user['phone']),
            "last_login": user['last_login'].isoformat() if user['last_login'] else None
        }), 200
        
    except Exception as e:
        logger.error(f"Error validating session: {e}")
        return jsonify({
            "success": False,
            "session_valid": False,
            "error": str(e)
        }), 500

# ============================================
# Crypto Signal Processing Endpoints
# ============================================

@app.route('/api/crypto/processors', methods=['GET'])
@jwt_required()
def get_crypto_processors():
    """Get all crypto processors for current user"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        from crypto.processor import CryptoSignalProcessor
        processor = CryptoSignalProcessor(db)
        
        processors = processor.get_all_processors(current_user_id)
        
        return jsonify({
            "success": True,
            "processors": processors
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting crypto processors: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/processors', methods=['POST'])
@jwt_required()
def create_crypto_processor():
    """Create or update a crypto processor for a chat"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data.get('source_chat_id'):
        return jsonify({"success": False, "error": "source_chat_id richiesto"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        from crypto.processor import CryptoSignalProcessor
        processor = CryptoSignalProcessor(db)
        
        config = data.get('config', {})
        processor_name = data.get('processor_name', 'Crypto Signal Parser')
        
        success = processor.save_processor_config(
            current_user_id,
            data['source_chat_id'],
            processor_name,
            config
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "Processore crypto configurato con successo"
            }), 201
        else:
            return jsonify({
                "success": False,
                "error": "Errore nel salvataggio della configurazione"
            }), 500
            
    except Exception as e:
        logger.error(f"Error creating crypto processor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/test-parse', methods=['POST'])
@jwt_required()
def test_crypto_parse():
    """Test parsing a crypto signal message"""
    data = request.get_json()
    
    if not data.get('message'):
        return jsonify({"success": False, "error": "Messaggio richiesto"}), 400
    
    try:
        from crypto.parser import CryptoSignalParser
        parser = CryptoSignalParser()
        
        result = parser.parse_signal(data['message'])
        summary = parser.format_signal_summary(result)
        
        return jsonify({
            "success": True,
            "parsed_data": result,
            "summary": summary
        }), 200
        
    except Exception as e:
        logger.error(f"Error testing crypto parse: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/signals/<source_chat_id>', methods=['GET'])
@jwt_required()
def get_crypto_signals(source_chat_id):
    """Get crypto signals for a specific chat"""
    current_user_id = get_jwt_identity()
    hours = request.args.get('hours', 24, type=int)
    signal_type = request.args.get('type')
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        from crypto.processor import CryptoSignalProcessor
        processor = CryptoSignalProcessor(db)
        
        signals = processor.get_signals_by_chat(current_user_id, int(source_chat_id), hours, signal_type)
        
        return jsonify({
            "success": True,
            "signals": signals,
            "count": len(signals)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting crypto signals: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/top-performers', methods=['GET'])
@jwt_required()
def get_top_performers():
    """Get top performing crypto tokens"""
    current_user_id = get_jwt_identity()
    limit = request.args.get('limit', 10, type=int)
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        from crypto.processor import CryptoSignalProcessor
        processor = CryptoSignalProcessor(db)
        
        top_performers = processor.get_top_performers(current_user_id, limit)
        
        return jsonify({
            "success": True,
            "performers": top_performers
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting top performers: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/process-message', methods=['POST'])
@jwt_required()
def process_crypto_message():
    """Manually process a crypto signal message"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    required_fields = ['source_chat_id', 'message']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"{field} richiesto"}), 400
    
    db = get_db_connection()
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        from crypto.processor import CryptoSignalProcessor
        processor = CryptoSignalProcessor(db)
        
        result = processor.process_message(
            current_user_id,
            data['source_chat_id'],
            data['message']
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error processing crypto message: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/processors/<int:processor_id>', methods=['DELETE'])
@jwt_required()
def delete_crypto_processor(processor_id):
    """Delete a crypto processor"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        from crypto.processor import CryptoSignalProcessor
        processor = CryptoSignalProcessor(db)
        
        success = processor.delete_processor(current_user_id, processor_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Processore eliminato con successo"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Processore non trovato o non autorizzato"
            }), 404
            
    except Exception as e:
        logger.error(f"Error deleting crypto processor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/rules', methods=['GET', 'POST'])
@jwt_required()
def manage_crypto_rules():
    """Manage crypto extraction rules"""
    current_user_id = get_jwt_identity()
    logger.info(f"=== CRYPTO RULES ENDPOINT CALLED ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"User ID: {current_user_id}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    db = get_db_connection()
    if not db:
        logger.error("Database connection failed")
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        if request.method == 'GET':
            logger.info("GET request - fetching rules")
            chat_id = request.args.get('chat_id')
            logger.info(f"Chat ID from args: {chat_id}")
            
            if not chat_id:
                logger.error("No chat_id provided")
                return jsonify({"success": False, "error": "chat_id richiesto"}), 400
            
            with db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM extraction_rules
                    WHERE user_id = %s AND source_chat_id = %s
                    ORDER BY created_at DESC
                """, (current_user_id, chat_id))
                rules = cursor.fetchall()
            
            logger.info(f"Found {len(rules)} rules for user {current_user_id}, chat {chat_id}")
            return jsonify({
                "success": True,
                "rules": rules
            }), 200
        
        elif request.method == 'POST':
            logger.info("POST request - saving rules")
            
            # Check if request has JSON content
            if not request.is_json:
                logger.error("Request is not JSON")
                return jsonify({"success": False, "error": "Content-Type must be application/json"}), 400
            
            data = request.get_json()
            logger.info(f"Request data: {data}")
            
            source_chat_id = data.get('source_chat_id')
            rules = data.get('rules', [])
            
            logger.info(f"Source chat ID: {source_chat_id}")
            logger.info(f"Rules count: {len(rules)}")
            logger.info(f"Rules: {rules}")
            
            if not source_chat_id or not rules:
                logger.error(f"Missing required data: source_chat_id={source_chat_id}, rules={rules}")
                return jsonify({"success": False, "error": "source_chat_id e rules richiesti"}), 400
            
            # Get chat title
            source_chat_title = data.get('source_chat_title', '')
            if not source_chat_title:
                source_chat_title = f"Group_{source_chat_id}"
            
            logger.info(f"Chat title: {source_chat_title}")
            
            # Delete existing rules for this chat
            with db.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM extraction_rules
                    WHERE user_id = %s AND source_chat_id = %s
                """, (current_user_id, source_chat_id))
                deleted_count = cursor.rowcount
                logger.info(f"Deleted {deleted_count} existing rules")
                
                # Insert new rules
                for i, rule in enumerate(rules):
                    logger.info(f"Inserting rule {i+1}: {rule}")
                    cursor.execute("""
                        INSERT INTO extraction_rules (user_id, source_chat_id, rule_name, search_text, value_length)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        current_user_id,
                        source_chat_id,
                        rule['rule_name'],
                        rule['search_text'],
                        rule['value_length']
                    ))
                
                db.commit()
                logger.info(f"Successfully saved {len(rules)} rules to database")
            
            # ---- Avvio container estrattore crypto ----
            container_name = None
            try:
                logger.info("Starting extractor container creation")
                
                # Get user info
                with db.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT phone, api_id, api_hash_encrypted FROM users WHERE id = %s", (current_user_id,))
                    user = cursor.fetchone()
                
                if not user:
                    logger.error(f"User not found for id {current_user_id}")
                    return jsonify({"success": False, "error": "User not found"}), 404
                
                # Check if user sent a code
                code_from_client = data.get('code')
                
                # Create session name for this extractor
                session_name = f"extractor_{hash_phone_number(user['phone'])}_{source_chat_id}"
                session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
                
                # Check if session already exists and is valid
                session_exists_and_valid = False
                if os.path.exists(session_file):
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        async def _check_session():
                            client = TelegramClient(session_file, user['api_id'], decrypt_api_hash(user['api_hash_encrypted']))
                            await client.connect()
                            authorized = await client.is_user_authorized()
                            await client.disconnect()
                            return authorized
                        
                        session_exists_and_valid = loop.run_until_complete(_check_session())
                        loop.close()
                        logger.info(f"Session check for {session_name}: {'valid' if session_exists_and_valid else 'invalid'}")
                    except Exception as e:
                        logger.error(f"Error checking session: {e}")
                        session_exists_and_valid = False
                
                # If session is valid, proceed with container creation
                if session_exists_and_valid:
                    logger.info(f"Using existing valid session for {session_name}")
                    
                    from crypto.extractor_manager import ExtractorManager
                    extractor_mgr = ExtractorManager()
                    
                    ok, container_name, msg = extractor_mgr.create_extractor_container(
                        user_id=current_user_id,
                        source_chat_id=source_chat_id,
                        source_chat_title=source_chat_title,
                        rules=rules,
                        db_url=os.getenv('DATABASE_URL', ''),
                        api_id=user['api_id'],
                        api_hash=decrypt_api_hash(user['api_hash_encrypted']),
                        session_string='',  # We use file session
                        session_file_path=session_file
                    )
                    logger.info(f"Extractor container result: {ok}, {container_name}, {msg}")
                    
                    if ok and container_name:
                        # Save container info
                        with db.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO crypto_processors (user_id, source_chat_id, processor_name, is_active, config)
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (user_id, source_chat_id) 
                                DO UPDATE SET 
                                    processor_name = EXCLUDED.processor_name,
                                    is_active = EXCLUDED.is_active,
                                    config = EXCLUDED.config,
                                    updated_at = CURRENT_TIMESTAMP
                            """, (
                                current_user_id,
                                source_chat_id,
                                f"Extractor: {source_chat_title}",
                                True,
                                json.dumps({
                                    "container_name": container_name,
                                    "rules": rules,
                                    "source_chat_title": source_chat_title
                                })
                            ))
                            db.commit()
                else:
                    # Need to create session - handle code flow
                    verification_key = f"extractor_verification:{current_user_id}:{source_chat_id}"
                    redis_conn = get_redis_connection()
                    
                    if not code_from_client:
                        # Send code
                        logger.info("No code provided, sending verification code")
                        
                        # Check rate limiting
                        rate_check = can_request_sms_code(user['phone'])
                        if not rate_check["can_request"]:
                            return jsonify({
                                "success": False,
                                "error": f"Limite SMS raggiunto. Riprova tra {rate_check['time_formatted']}",
                                "rate_limit": rate_check
                            }), 429
                        
                        try:
                            async def _send_code():
                                if os.path.exists(session_file):
                                    os.remove(session_file)
                                    logger.info(f"Removed existing session file for {session_name}")
                                
                                client = TelegramClient(session_file, user['api_id'], decrypt_api_hash(user['api_hash_encrypted']))
                                await client.connect()
                                result = await client.send_code_request(user['phone'])
                                
                                if redis_conn:
                                    verification_data = {
                                        "phone_code_hash": result.phone_code_hash,
                                        "session_name": session_name,
                                        "api_id": user['api_id'],
                                        "api_hash": user['api_hash_encrypted'],
                                        "rules": rules,
                                        "source_chat_title": source_chat_title
                                    }
                                    redis_conn.set(verification_key, json.dumps(verification_data), ex=600)
                                await client.disconnect()
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(_send_code())
                            loop.close()
                            
                            # Increment counter
                            counter_status = increment_sms_code_counter(user['phone'])
                            
                            return jsonify({
                                "success": True,
                                "code_sent": True,
                                "message": f"Codice di verifica inviato a {user['phone']}",
                                "phone": user['phone'],
                                "rate_limit": counter_status,
                                "rules_saved": len(rules)
                            }), 200
                            
                        except errors.FloodWaitError as e:
                            sync_flood_wait_from_telegram(user['phone'], e.seconds)
                            return jsonify({
                                "success": False,
                                "error": f"Troppi tentativi. Riprova tra {e.seconds} secondi",
                                "flood_wait": e.seconds
                            }), 429
                        except Exception as e:
                            logger.error(f"Error sending code: {e}")
                            return jsonify({"success": False, "error": str(e)}), 500
                    
                    else:
                        # Verify code
                        logger.info("Code provided, verifying")
                        
                        if not redis_conn or not redis_conn.exists(verification_key):
                            return jsonify({"success": False, "error": "Richiesta di verifica scaduta"}), 400
                        
                        try:
                            verification_data = json.loads(redis_conn.get(verification_key))
                            
                            async def _verify_code():
                                client = TelegramClient(session_file, verification_data['api_id'], decrypt_api_hash(verification_data['api_hash']))
                                await client.connect()
                                await client.sign_in(user['phone'], code_from_client, phone_code_hash=verification_data['phone_code_hash'])
                                authorized = await client.is_user_authorized()
                                await client.disconnect()
                                return authorized
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            ok = loop.run_until_complete(_verify_code())
                            loop.close()
                            
                            if not ok:
                                return jsonify({"success": False, "error": "Codice non valido"}), 400
                            
                            # Code verified, create container
                            redis_conn.delete(verification_key)
                            logger.info(f"Extractor session created for {session_name}")
                            
                            from crypto.extractor_manager import ExtractorManager
                            extractor_mgr = ExtractorManager()
                            
                            ok, container_name, msg = extractor_mgr.create_extractor_container(
                                user_id=current_user_id,
                                source_chat_id=source_chat_id,
                                source_chat_title=verification_data['source_chat_title'],
                                rules=verification_data['rules'],
                                db_url=os.getenv('DATABASE_URL', ''),
                                api_id=verification_data['api_id'],
                                api_hash=decrypt_api_hash(verification_data['api_hash']),
                                session_string='',  # We use file session
                                session_file_path=session_file
                            )
                            
                            if ok and container_name:
                                # Save container info
                                with db.cursor() as cursor:
                                    cursor.execute("""
                                        INSERT INTO crypto_processors (user_id, source_chat_id, processor_name, is_active, config)
                                        VALUES (%s, %s, %s, %s, %s)
                                        ON CONFLICT (user_id, source_chat_id) 
                                        DO UPDATE SET 
                                            processor_name = EXCLUDED.processor_name,
                                            is_active = EXCLUDED.is_active,
                                            config = EXCLUDED.config,
                                            updated_at = CURRENT_TIMESTAMP
                                    """, (
                                        current_user_id,
                                        source_chat_id,
                                        f"Extractor: {verification_data['source_chat_title']}",
                                        True,
                                        json.dumps({
                                            "container_name": container_name,
                                            "rules": verification_data['rules'],
                                            "source_chat_title": verification_data['source_chat_title']
                                        })
                                    ))
                                    db.commit()
                                    
                        except Exception as e:
                            logger.error(f"Error verifying code: {e}")
                            return jsonify({"success": False, "error": str(e)}), 500

            except Exception as e:
                logger.error(f"Failed to start extractor container: {e}")
                import traceback
                logger.error(f"Extractor error traceback: {traceback.format_exc()}")

            logger.info(f"Returning success response with {len(rules)} rules saved")
            return jsonify({
                "success": True,
                "message": f"Salvate {len(rules)} regole per il gruppo",
                "container_name": container_name
            }), 201
            
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error managing crypto rules: {e}")
        logger.error(f"Full traceback: {tb}")
        if db:
            db.rollback()
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": tb.split("\n")[-3:]
        }), 500

@app.route('/api/crypto/rules/<int:rule_id>', methods=['DELETE'])
@jwt_required()
def delete_crypto_rule(rule_id):
    """Delete a specific extraction rule"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                DELETE FROM extraction_rules
                WHERE id = %s AND user_id = %s
            """, (rule_id, current_user_id))
            
            if cursor.rowcount == 0:
                return jsonify({
                    "success": False,
                    "error": "Regola non trovata o non autorizzato"
                }), 404
            
            db.commit()
            
        return jsonify({
            "success": True,
            "message": "Regola eliminata con successo"
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting crypto rule: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/extractors/<source_chat_id>/status', methods=['GET'])
@jwt_required()
def get_extractor_status(source_chat_id):
    """Get status of crypto extractor container for a chat"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        # Get container name from crypto_processors config
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT config 
                FROM crypto_processors 
                WHERE user_id = %s AND source_chat_id = %s
            """, (current_user_id, source_chat_id))
            
            processor = cursor.fetchone()
            
        if not processor:
            return jsonify({
                "success": True,
                "status": "not_configured",
                "message": "Nessun extractor configurato per questo gruppo"
            }), 200
            
        config = processor.get('config', {})
        if isinstance(config, str):
            config = json.loads(config)
            
        container_name = config.get('container_name')
        
        if not container_name:
            return jsonify({
                "success": True,
                "status": "not_created",
                "message": "Container non creato"
            }), 200
            
        # Get container status
        from crypto.extractor_manager import ExtractorManager
        extractor_mgr = ExtractorManager()
        status = extractor_mgr.get_container_status(container_name)
        
        return jsonify({
            "success": True,
            "container_name": container_name,
            **status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting extractor status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/extractors/<source_chat_id>/restart', methods=['POST'])
@jwt_required()
def restart_extractor(source_chat_id):
    """Restart crypto extractor container"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        # Get container name from crypto_processors config
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT config 
                FROM crypto_processors 
                WHERE user_id = %s AND source_chat_id = %s
            """, (current_user_id, source_chat_id))
            
            processor = cursor.fetchone()
            
        if not processor:
            return jsonify({"success": False, "error": "Extractor non trovato"}), 404
            
        config = processor.get('config', {})
        if isinstance(config, str):
            config = json.loads(config)
            
        container_name = config.get('container_name')
        
        if not container_name:
            return jsonify({"success": False, "error": "Container non configurato"}), 400
            
        # Restart container
        from crypto.extractor_manager import ExtractorManager
        extractor_mgr = ExtractorManager()
        success, message = extractor_mgr.restart_container(container_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Extractor riavviato con successo"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 500
            
    except Exception as e:
        logger.error(f"Error restarting extractor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/crypto/extractors/<source_chat_id>/stop', methods=['POST'])
@jwt_required()
def stop_extractor(source_chat_id):
    """Stop and remove crypto extractor container"""
    current_user_id = get_jwt_identity()
    db = get_db_connection()
    
    if not db:
        return jsonify({"success": False, "error": "Database connection failed"}), 500
    
    try:
        # Get container name from crypto_processors config
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT config 
                FROM crypto_processors 
                WHERE user_id = %s AND source_chat_id = %s
            """, (current_user_id, source_chat_id))
            
            processor = cursor.fetchone()
            
        if not processor:
            return jsonify({"success": False, "error": "Extractor non trovato"}), 404
            
        config = processor.get('config', {})
        if isinstance(config, str):
            config = json.loads(config)
            
        container_name = config.get('container_name')
        
        if not container_name:
            return jsonify({"success": False, "error": "Container non configurato"}), 400
            
        # Stop and remove container
        from crypto.extractor_manager import ExtractorManager
        extractor_mgr = ExtractorManager()
        success, message = extractor_mgr.stop_and_remove_container(container_name)
        
        if success:
            # Update processor config to remove container_name
            config.pop('container_name', None)
            with db.cursor() as cursor:
                cursor.execute("""
                    UPDATE crypto_processors 
                    SET config = %s, is_active = false, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = %s AND source_chat_id = %s
                """, (json.dumps(config), current_user_id, source_chat_id))
                db.commit()
                
            return jsonify({
                "success": True,
                "message": "Extractor fermato e rimosso"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 500
            
    except Exception as e:
        logger.error(f"Error stopping extractor: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/debug/log', methods=['POST'])
@jwt_required()
def debug_log():
    """Debug endpoint for frontend logging"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    logger.info(f"=== FRONTEND DEBUG LOG ===")
    logger.info(f"User ID: {current_user_id}")
    logger.info(f"Message: {data.get('message', 'No message')}")
    logger.info(f"Data: {data.get('data', {})}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    return jsonify({"success": True}), 200

# ============================================
# MESSAGE LISTENERS ENDPOINTS
# ============================================

@app.route('/api/message-listeners', methods=['GET'])
@jwt_required()
def get_message_listeners():
    """Get all message listeners for the current user"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get listeners with elaboration counts using the view
            cursor.execute("""
                SELECT * FROM active_listeners_summary
                WHERE user_id = %s
                ORDER BY source_chat_title
            """, (current_user_id,))
            
            listeners = cursor.fetchall()
            
            # Convert datetime to ISO format
            for listener in listeners:
                if listener.get('last_message_at'):
                    listener['last_message_at'] = listener['last_message_at'].isoformat()
            
            return jsonify({
                "success": True,
                "listeners": listeners
            }), 200
            
    except Exception as e:
        logger.error(f"Error fetching message listeners: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/message-listeners', methods=['POST'])
@jwt_required()
def create_message_listener():
    """Create a new message listener"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['source_chat_id', 'source_chat_title']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"success": False, "error": f"{field} is required"}), 400
    
    try:
        db = get_db_connection()
        redis_conn = get_redis_connection()
        
        # Get user details
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (current_user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            # Check if listener already exists
            cursor.execute("""
                SELECT id FROM message_listeners 
                WHERE user_id = %s AND source_chat_id = %s
            """, (current_user_id, data['source_chat_id']))
            
            existing = cursor.fetchone()
            if existing:
                return jsonify({
                    "success": False, 
                    "error": "Listener già esistente per questa chat"
                }), 409
            
            # Create listener in database
            cursor.execute("""
                INSERT INTO message_listeners (
                    user_id, source_chat_id, source_chat_title, source_chat_type,
                    container_name, container_status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                current_user_id,
                data['source_chat_id'],
                data['source_chat_title'],
                data.get('source_chat_type', 'unknown'),
                '',  # Container name will be set after creation
                'creating'
            ))
            
            listener_id = cursor.fetchone()['id']
            db.commit()
            
            # Create container
            listener_manager = MessageListenerManager()
            
            # Check for existing session file
            session_name = f"user_{hash_phone_number(user['phone'])}"
            session_file = os.path.join(SESSION_DIR, f"{session_name}.session")
            
            # Database URL for the container
            db_url = Config.DATABASE_URL
            
            success, container_name, message = listener_manager.create_listener_container(
                user_id=current_user_id,
                phone=user['phone'],
                api_id=user['api_id'],
                api_hash=decrypt_api_hash(user['api_hash_encrypted']),
                session_string="",  # Will be handled by session file
                source_chat_id=str(data['source_chat_id']),
                source_chat_title=data['source_chat_title'],
                source_chat_type=data.get('source_chat_type', 'unknown'),
                db_url=db_url,
                listener_id=listener_id,
                session_file_path=session_file if os.path.exists(session_file) else None
            )
            
            if success:
                # Update listener with container name
                cursor.execute("""
                    UPDATE message_listeners
                    SET container_name = %s, container_status = 'running'
                    WHERE id = %s
                """, (container_name, listener_id))
                db.commit()
                
                return jsonify({
                    "success": True,
                    "listener_id": listener_id,
                    "container_name": container_name,
                    "message": "Listener creato e avviato con successo"
                }), 201
            else:
                # Delete listener if container creation failed
                cursor.execute("DELETE FROM message_listeners WHERE id = %s", (listener_id,))
                db.commit()
                
                return jsonify({
                    "success": False,
                    "error": f"Errore creazione container: {message}"
                }), 500
                
    except Exception as e:
        logger.error(f"Error creating message listener: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/message-listeners/<int:listener_id>/start', methods=['POST'])
@jwt_required()
def start_message_listener(listener_id):
    """Start a stopped message listener"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get listener
            cursor.execute("""
                SELECT * FROM message_listeners
                WHERE id = %s AND user_id = %s
            """, (listener_id, current_user_id))
            
            listener = cursor.fetchone()
            if not listener:
                return jsonify({"success": False, "error": "Listener not found"}), 404
            
            # Start container
            listener_manager = MessageListenerManager()
            success, message = listener_manager.start_container(listener['container_name'])
            
            if success:
                # Update status
                cursor.execute("""
                    UPDATE message_listeners
                    SET container_status = 'running'
                    WHERE id = %s
                """, (listener_id,))
                db.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Listener avviato con successo"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": message
                }), 500
                
    except Exception as e:
        logger.error(f"Error starting message listener: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/message-listeners/<int:listener_id>/stop', methods=['POST'])
@jwt_required()
def stop_message_listener(listener_id):
    """Stop a running message listener"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get listener
            cursor.execute("""
                SELECT * FROM message_listeners
                WHERE id = %s AND user_id = %s
            """, (listener_id, current_user_id))
            
            listener = cursor.fetchone()
            if not listener:
                return jsonify({"success": False, "error": "Listener not found"}), 404
            
            # Stop container
            listener_manager = MessageListenerManager()
            success, message = listener_manager.stop_container(listener['container_name'])
            
            if success:
                # Update status
                cursor.execute("""
                    UPDATE message_listeners
                    SET container_status = 'stopped'
                    WHERE id = %s
                """, (listener_id,))
                db.commit()
                
                return jsonify({
                    "success": True,
                    "message": "Listener fermato con successo"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": message
                }), 500
                
    except Exception as e:
        logger.error(f"Error stopping message listener: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/message-listeners/<int:listener_id>', methods=['DELETE'])
@jwt_required()
def delete_message_listener(listener_id):
    """Delete a message listener and its container"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get listener
            cursor.execute("""
                SELECT * FROM message_listeners
                WHERE id = %s AND user_id = %s
            """, (listener_id, current_user_id))
            
            listener = cursor.fetchone()
            if not listener:
                return jsonify({"success": False, "error": "Listener not found"}), 404
            
            # Stop and remove container
            listener_manager = MessageListenerManager()
            listener_manager.stop_container(listener['container_name'])
            listener_manager.remove_container(listener['container_name'])
            
            # Delete from database (cascades to elaborations and messages)
            cursor.execute("DELETE FROM message_listeners WHERE id = %s", (listener_id,))
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Listener eliminato con successo"
            }), 200
                
    except Exception as e:
        logger.error(f"Error deleting message listener: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================
# MESSAGE ELABORATIONS ENDPOINTS
# ============================================

@app.route('/api/message-listeners/<int:listener_id>/elaborations', methods=['GET'])
@jwt_required()
def get_message_elaborations(listener_id):
    """Get all elaborations for a message listener"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify listener ownership
            cursor.execute("""
                SELECT id FROM message_listeners
                WHERE id = %s AND user_id = %s
            """, (listener_id, current_user_id))
            
            if not cursor.fetchone():
                return jsonify({"success": False, "error": "Listener not found"}), 404
            
            # Get elaborations
            cursor.execute("""
                SELECT * FROM message_elaborations
                WHERE listener_id = %s
                ORDER BY priority, created_at
            """, (listener_id,))
            
            elaborations = cursor.fetchall()
            
            # Convert datetime to ISO format
            for elab in elaborations:
                if elab.get('created_at'):
                    elab['created_at'] = elab['created_at'].isoformat()
                if elab.get('last_processed_at'):
                    elab['last_processed_at'] = elab['last_processed_at'].isoformat()
                if elab.get('last_error_at'):
                    elab['last_error_at'] = elab['last_error_at'].isoformat()
            
            return jsonify({
                "success": True,
                "elaborations": elaborations
            }), 200
            
    except Exception as e:
        logger.error(f"Error fetching elaborations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/message-listeners/<int:listener_id>/elaborations', methods=['POST'])
@jwt_required()
def create_message_elaboration(listener_id):
    """Create a new elaboration for a message listener"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['elaboration_type', 'elaboration_name', 'config']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"success": False, "error": f"{field} is required"}), 400
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify listener ownership
            cursor.execute("""
                SELECT id, container_name FROM message_listeners
                WHERE id = %s AND user_id = %s
            """, (listener_id, current_user_id))
            
            listener = cursor.fetchone()
            if not listener:
                return jsonify({"success": False, "error": "Listener not found"}), 404
            
            # Create elaboration
            cursor.execute("""
                INSERT INTO message_elaborations (
                    listener_id, elaboration_type, elaboration_name, config
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                listener_id,
                data['elaboration_type'],
                data['elaboration_name'],
                json.dumps(data['config'])
            ))
            
            elaboration_id = cursor.fetchone()['id']
            db.commit()
            
            # Update listener container with new elaborations
            listener_manager = MessageListenerManager()
            
            # Get all elaborations for the listener
            cursor.execute("""
                SELECT * FROM message_elaborations
                WHERE listener_id = %s AND is_active = true
                ORDER BY priority
            """, (listener_id,))
            
            elaborations = cursor.fetchall()
            
            # Format elaborations for the container
            formatted_elaborations = []
            for elab in elaborations:
                formatted_elaborations.append({
                    'id': elab['id'],
                    'type': elab['elaboration_type'],
                    'config': elab['config'] if isinstance(elab['config'], dict) else json.loads(elab['config'])
                })
            
            # Update container configuration
            success, message = listener_manager.update_listener_elaborations(
                listener['container_name'],
                formatted_elaborations
            )
            
            if not success:
                logger.warning(f"Failed to update container elaborations: {message}")
            
            return jsonify({
                "success": True,
                "elaboration_id": elaboration_id,
                "message": "Elaborazione creata con successo"
            }), 201
                
    except Exception as e:
        logger.error(f"Error creating elaboration: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/elaborations/<int:elaboration_id>/activate', methods=['POST'])
@jwt_required()
def activate_elaboration(elaboration_id):
    """Activate an elaboration"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify ownership
            cursor.execute("""
                SELECT e.*, l.container_name
                FROM message_elaborations e
                JOIN message_listeners l ON e.listener_id = l.id
                WHERE e.id = %s AND l.user_id = %s
            """, (elaboration_id, current_user_id))
            
            elaboration = cursor.fetchone()
            if not elaboration:
                return jsonify({"success": False, "error": "Elaboration not found"}), 404
            
            # Update status
            cursor.execute("""
                UPDATE message_elaborations
                SET is_active = true
                WHERE id = %s
            """, (elaboration_id,))
            db.commit()
            
            # Update container
            _update_container_elaborations(cursor, elaboration['listener_id'], elaboration['container_name'])
            
            return jsonify({
                "success": True,
                "message": "Elaborazione attivata con successo"
            }), 200
                
    except Exception as e:
        logger.error(f"Error activating elaboration: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/elaborations/<int:elaboration_id>/deactivate', methods=['POST'])
@jwt_required()
def deactivate_elaboration(elaboration_id):
    """Deactivate an elaboration"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify ownership
            cursor.execute("""
                SELECT e.*, l.container_name
                FROM message_elaborations e
                JOIN message_listeners l ON e.listener_id = l.id
                WHERE e.id = %s AND l.user_id = %s
            """, (elaboration_id, current_user_id))
            
            elaboration = cursor.fetchone()
            if not elaboration:
                return jsonify({"success": False, "error": "Elaboration not found"}), 404
            
            # Update status
            cursor.execute("""
                UPDATE message_elaborations
                SET is_active = false
                WHERE id = %s
            """, (elaboration_id,))
            db.commit()
            
            # Update container
            _update_container_elaborations(cursor, elaboration['listener_id'], elaboration['container_name'])
            
            return jsonify({
                "success": True,
                "message": "Elaborazione disattivata con successo"
            }), 200
                
    except Exception as e:
        logger.error(f"Error deactivating elaboration: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/elaborations/<int:elaboration_id>', methods=['DELETE'])
@jwt_required()
def delete_elaboration(elaboration_id):
    """Delete an elaboration"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify ownership
            cursor.execute("""
                SELECT e.*, l.container_name
                FROM message_elaborations e
                JOIN message_listeners l ON e.listener_id = l.id
                WHERE e.id = %s AND l.user_id = %s
            """, (elaboration_id, current_user_id))
            
            elaboration = cursor.fetchone()
            if not elaboration:
                return jsonify({"success": False, "error": "Elaboration not found"}), 404
            
            listener_id = elaboration['listener_id']
            container_name = elaboration['container_name']
            
            # Delete elaboration
            cursor.execute("DELETE FROM message_elaborations WHERE id = %s", (elaboration_id,))
            db.commit()
            
            # Update container
            _update_container_elaborations(cursor, listener_id, container_name)
            
            return jsonify({
                "success": True,
                "message": "Elaborazione eliminata con successo"
            }), 200
                
    except Exception as e:
        logger.error(f"Error deleting elaboration: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

def _update_container_elaborations(cursor, listener_id, container_name):
    """Helper function to update container elaborations"""
    try:
        # Get all active elaborations
        cursor.execute("""
            SELECT * FROM message_elaborations
            WHERE listener_id = %s AND is_active = true
            ORDER BY priority
        """, (listener_id,))
        
        elaborations = cursor.fetchall()
        
        # Format elaborations for the container
        formatted_elaborations = []
        for elab in elaborations:
            formatted_elaborations.append({
                'id': elab['id'],
                'type': elab['elaboration_type'],
                'config': elab['config'] if isinstance(elab['config'], dict) else json.loads(elab['config'])
            })
        
        # Update container
        listener_manager = MessageListenerManager()
        success, message = listener_manager.update_listener_elaborations(
            container_name,
            formatted_elaborations
        )
        
        if not success:
            logger.warning(f"Failed to update container elaborations: {message}")
            
    except Exception as e:
        logger.error(f"Error updating container elaborations: {e}")

# ============================================
# 📝 LOGGING SYSTEM ENDPOINTS
# ============================================

@app.route('/api/logging/sessions', methods=['GET'])
@jwt_required()
def get_logging_sessions():
    """Get all logging sessions for the current user"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ls.*, 
                       COUNT(ml.id) as total_messages,
                       MAX(ml.message_date) as last_message_date
                FROM logging_sessions ls
                LEFT JOIN message_logs ml ON ls.id = ml.logging_session_id
                WHERE ls.user_id = %s
                GROUP BY ls.id
                ORDER BY ls.created_at DESC
            """, (current_user_id,))
            
            sessions = cursor.fetchall()
            
            return jsonify({
                "success": True,
                "sessions": [dict(session) for session in sessions]
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting logging sessions: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logging/sessions', methods=['POST'])
@jwt_required()
def create_logging_session():
    """Create a new logging session for a chat"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'chat_id' not in data:
        return jsonify({"success": False, "error": "chat_id is required"}), 400
    
    chat_id = data['chat_id']
    chat_title = data.get('chat_title', '')
    chat_username = data.get('chat_username', '')
    chat_type = data.get('chat_type', 'unknown')
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check if user already has an active session for this chat
            cursor.execute("""
                SELECT id FROM logging_sessions
                WHERE user_id = %s AND chat_id = %s AND is_active = true
            """, (current_user_id, chat_id))
            
            if cursor.fetchone():
                return jsonify({
                    "success": False, 
                    "error": "Già esiste una sessione di logging attiva per questa chat"
                }), 400
            
            # Get user credentials
            cursor.execute("""
                SELECT phone, api_id, api_hash_encrypted
                FROM users WHERE id = %s
            """, (current_user_id,))
            
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "error": "User not found"}), 404
            
            # Decrypt API hash
            api_hash = decrypt_api_hash(user['api_hash_encrypted'])
            
            # Create logging container
            from logging_manager import LoggingManager
            logging_manager = LoggingManager()
            
            # Generate session string (you might want to implement this)
            session_string = f"session_{current_user_id}_{chat_id}"
            
            success, message, container_name = logging_manager.create_logging_container(
                user_id=current_user_id,
                phone=user['phone'],
                api_id=user['api_id'],
                api_hash=api_hash,
                session_string=session_string,
                chat_id=str(chat_id),
                chat_title=chat_title,
                chat_username=chat_username,
                chat_type=chat_type
            )
            
            if not success:
                return jsonify({"success": False, "error": message}), 500
            
            # Create logging session in database
            cursor.execute("""
                INSERT INTO logging_sessions 
                (user_id, chat_id, chat_title, chat_username, chat_type, container_name, container_status)
                VALUES (%s, %s, %s, %s, %s, %s, 'running')
                RETURNING id
            """, (current_user_id, chat_id, chat_title, chat_username, chat_type, container_name))
            
            session_id = cursor.fetchone()['id']
            db.commit()
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "container_name": container_name,
                "message": "Sessione di logging creata con successo"
            }), 201
            
    except Exception as e:
        logger.error(f"Error creating logging session: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logging/sessions/<int:session_id>/stop', methods=['POST'])
@jwt_required()
def stop_logging_session(session_id):
    """Stop a logging session"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify ownership and get session info
            cursor.execute("""
                SELECT * FROM logging_sessions
                WHERE id = %s AND user_id = %s
            """, (session_id, current_user_id))
            
            session = cursor.fetchone()
            if not session:
                return jsonify({"success": False, "error": "Session not found"}), 404
            
            if not session['is_active']:
                return jsonify({"success": False, "error": "Session already stopped"}), 400
            
            # Stop container
            from logging_manager import LoggingManager
            logging_manager = LoggingManager()
            
            success, message = logging_manager.stop_and_remove_container(session['container_name'])
            
            # Update session status
            cursor.execute("""
                UPDATE logging_sessions
                SET is_active = false, container_status = 'stopped', updated_at = NOW()
                WHERE id = %s
            """, (session_id,))
            
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Sessione di logging fermata con successo"
            }), 200
            
    except Exception as e:
        logger.error(f"Error stopping logging session: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logging/sessions/<int:session_id>', methods=['DELETE'])
@jwt_required()
def delete_logging_session(session_id):
    """Delete a logging session and all its logs"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify ownership
            cursor.execute("""
                SELECT * FROM logging_sessions
                WHERE id = %s AND user_id = %s
            """, (session_id, current_user_id))
            
            session = cursor.fetchone()
            if not session:
                return jsonify({"success": False, "error": "Session not found"}), 404
            
            # Stop container if still running
            if session['is_active'] and session['container_name']:
                from logging_manager import LoggingManager
                logging_manager = LoggingManager()
                logging_manager.stop_and_remove_container(session['container_name'])
            
            # Delete all logs for this session
            cursor.execute("DELETE FROM message_logs WHERE logging_session_id = %s", (session_id,))
            
            # Delete session
            cursor.execute("DELETE FROM logging_sessions WHERE id = %s", (session_id,))
            
            db.commit()
            
            return jsonify({
                "success": True,
                "message": "Sessione di logging eliminata con successo"
            }), 200
            
    except Exception as e:
        logger.error(f"Error deleting logging session: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logging/messages/<int:session_id>', methods=['GET'])
@jwt_required()
def get_logged_messages(session_id):
    """Get logged messages for a specific session"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Verify ownership
            cursor.execute("""
                SELECT ls.* FROM logging_sessions ls
                WHERE ls.id = %s AND ls.user_id = %s
            """, (session_id, current_user_id))
            
            session = cursor.fetchone()
            if not session:
                return jsonify({"success": False, "error": "Session not found"}), 404
            
            # Get messages with pagination
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            offset = (page - 1) * per_page
            
            cursor.execute("""
                SELECT * FROM message_logs
                WHERE logging_session_id = %s
                ORDER BY message_date DESC
                LIMIT %s OFFSET %s
            """, (session_id, per_page, offset))
            
            messages = cursor.fetchall()
            
            # Get total count
            cursor.execute("""
                SELECT COUNT(*) as total FROM message_logs
                WHERE logging_session_id = %s
            """, (session_id,))
            
            total = cursor.fetchone()['total']
            
            return jsonify({
                "success": True,
                "messages": [dict(msg) for msg in messages],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page
                }
            }), 200
            
    except Exception as e:
        logger.error(f"Error getting logged messages: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logging/chat/<chat_id>/status', methods=['GET'])
@jwt_required()
def get_chat_logging_status(chat_id):
    """Get logging status for a specific chat"""
    current_user_id = get_jwt_identity()
    
    try:
        db = get_db_connection()
        with db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ls.*, COUNT(ml.id) as total_messages
                FROM logging_sessions ls
                LEFT JOIN message_logs ml ON ls.id = ml.logging_session_id
                WHERE ls.user_id = %s AND ls.chat_id = %s
                GROUP BY ls.id
                ORDER BY ls.created_at DESC
                LIMIT 1
            """, (current_user_id, chat_id))
            
            session = cursor.fetchone()
            
            if session:
                return jsonify({
                    "success": True,
                    "has_active_session": session['is_active'],
                    "session": dict(session)
                }), 200
            else:
                return jsonify({
                    "success": True,
                    "has_active_session": False,
                    "session": None
                }), 200
            
    except Exception as e:
        logger.error(f"Error getting chat logging status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# ========================================================================================
# CLIENT CACHE SYSTEM
# ========================================================================================

# Global client cache to avoid recreating clients unnecessarily
active_clients = {}
client_cache_ttl = 300  # 5 minutes cache TTL

async def cleanup_expired_clients():
    """Clean up expired clients from cache"""
    current_time = time.time()
    expired_phones = []
    
    for phone, client_data in active_clients.items():
        if current_time - client_data.get('created_at', 0) > client_cache_ttl:
            expired_phones.append(phone)
    
    for phone in expired_phones:
        try:
            client = active_clients[phone]['client']
            if client.is_connected():
                await client.disconnect()
        except:
            pass
        finally:
            del active_clients[phone]
            logger.info(f"Cleaned up expired client for {phone}")

def get_cached_client(phone: str) -> Optional[TelegramClient]:
    """Get cached client if still valid"""
    if phone in active_clients:
        client_data = active_clients[phone]
        current_time = time.time()
        
        # Check if client is still within TTL
        if current_time - client_data.get('created_at', 0) <= client_cache_ttl:
            client = client_data['client']
            if client.is_connected():
                return client
    
    return None

def cache_client(phone: str, client: TelegramClient):
    """Cache a client with timestamp"""
    active_clients[phone] = {
        'client': client,
        'created_at': time.time()
    }

# ========================================================================================
# AUTOMATIC CLEANUP SYSTEM
# ========================================================================================

import threading
import time

def start_cleanup_thread():
    """Start background thread for cleaning up expired clients"""
    def cleanup_loop():
        while True:
            try:
                # Run cleanup every 2 minutes
                time.sleep(120)
                asyncio.run(cleanup_expired_clients())
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
    cleanup_thread.start()
    logger.info("Started automatic client cleanup thread")

# Start cleanup thread when module is imported
start_cleanup_thread()

# ========================================================================================
# PERFORMANCE METRICS
# ========================================================================================

import time
from collections import defaultdict

# Performance metrics storage
login_metrics = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'average_response_time': 0,
    'response_times': [],
    'last_10_times': []
}

def record_login_metric(success: bool, response_time: float):
    """Record login performance metric"""
    login_metrics['total_requests'] += 1
    login_metrics['response_times'].append(response_time)
    
    if success:
        login_metrics['successful_requests'] += 1
    else:
        login_metrics['failed_requests'] += 1
    
    # Keep only last 100 response times
    if len(login_metrics['response_times']) > 100:
        login_metrics['response_times'] = login_metrics['response_times'][-100:]
    
    # Calculate average
    if login_metrics['response_times']:
        login_metrics['average_response_time'] = sum(login_metrics['response_times']) / len(login_metrics['response_times'])
    
    # Keep last 10 times for recent performance
    login_metrics['last_10_times'] = login_metrics['response_times'][-10:]

@app.route('/api/metrics/login-performance', methods=['GET'])
def get_login_metrics():
    """Get login performance metrics"""
    return jsonify({
        "success": True,
        "metrics": login_metrics,
        "success_rate": (login_metrics['successful_requests'] / max(login_metrics['total_requests'], 1)) * 100,
        "recent_average": sum(login_metrics['last_10_times']) / max(len(login_metrics['last_10_times']), 1)
    })

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True) 